"""감사 사이클 1회 — 페이싱 확인 → 고아 정리 → 브라우저 스윕(필수) → 관점 감사 + 독립 검토 → 텔레그램 요약 + 사이클 로그.

사용: .venv/bin/python -m scripts.audit.cycle [--force] [--perspectives ui,ux] [--limit N]
무한 반복 아님: 한 번 호출에 한 사이클이며, pacing(세션·주간 사용률)과 최소 간격(CYCLE_MIN_INTERVAL_MIN)이 막으면 사유만 기록하고 끝난다.
브라우저 스윕은 건너뛸 수 없다 — 실패하거나 셀이 0이면 낡은 원장으로 에이전트 감사를 하지 않고 sweep_failed 로 기록·알림한다.
결과는 BACKLOG 후보((판단 필요))로만 남기고 자동 수정은 하지 않는다.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time

from scripts.audit import agents, inventory, procs
from scripts.autopilot import notify, pacing, settings

CYCLES_PATH = inventory.LEDGER_PATH.parent / "cycles.jsonl"


def _log(entry: dict) -> None:
    CYCLES_PATH.parent.mkdir(parents=True, exist_ok=True)
    with CYCLES_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def last_cycle_ts() -> float:
    try:
        lines = CYCLES_PATH.read_text(encoding="utf-8").splitlines()
        return max((json.loads(ln).get("ts", 0) for ln in lines if ln.strip() and json.loads(ln).get("ran")), default=0)
    except (OSError, ValueError):
        return 0


def skip_reason(now: float, force: bool = False) -> str | None:
    if force:
        return None
    p = pacing.check(now)
    if not p.allowed:
        return p.reason
    wait = settings.CYCLE_MIN_INTERVAL_MIN * 60 - (now - last_cycle_ts())
    return f"최소 간격 미달 — {wait / 60:.0f}분 후" if wait > 0 else None


def run_cycle(force: bool = False, perspectives: str | None = None, limit: int | None = None, release: bool = False) -> dict:
    now = time.time()
    entry: dict = {"ts": now, "ran": False}
    reason = skip_reason(now, force)
    if reason:
        entry["reason"] = reason
        _log(entry)
        return entry
    entry["reaped"] = procs.reap()
    entry["ran"] = True
    entry["release"] = release
    swept, err = browser_sweep(limit)
    entry["swept"] = swept
    if err:
        entry.update(outcome="sweep_failed", reason=err, elapsed_sec=round(time.time() - now))
        _log(entry)
        notify.send(f"[감사] 브라우저 스윕 실패 — 에이전트 감사 생략: {err}")
        return entry
    groups = agents.group_issues(inventory.load_ledger())
    args = ["--backlog", "--review"] + (["--perspectives", perspectives] if perspectives else []) + (["--release"] if release else [])
    entry["issue_kinds"] = {k: len(v) for k, v in groups.items()}
    entry["agents_rc"] = agents.main(args)
    entry["outcome"] = "done"
    entry["findings"] = _count_findings()
    entry["confirmed"] = _count_findings(confirmed_only=True)
    entry["elapsed_sec"] = round(time.time() - now)
    _log(entry)
    notify.send(summary(entry))
    return entry


def _count_findings(confirmed_only: bool = False) -> int:
    try:
        items = json.loads(agents.FINDINGS_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return 0
    return len([f for f in items if not confirmed_only or f.get("review", {}).get("verdict") == "confirm"])


def summary(e: dict) -> str:
    kinds = ", ".join(f"{k}×{n}" for k, n in e.get("issue_kinds", {}).items()) or "없음"
    return (f"[감사] 스윕 {e.get('swept', 0)}셀 · 이슈 유형: {kinds}\n"
            f"후보 {e.get('findings', 0)}건 중 독립 검토 통과 {e.get('confirmed', 0)}건 · {e.get('elapsed_sec', 0)}초")


def browser_sweep(limit: int | None = None) -> tuple[int, str | None]:
    """브라우저 스윕 실행 — (셀 수, 실패 사유). 사유가 None 일 때만 성공. 생략 경로는 없다."""
    if not shutil.which("node"):
        return 0, "node 없음"
    cmd = [sys.executable, "-m", "scripts.audit.sweep"] + (["--limit", str(limit)] if limit else [])
    r = subprocess.run(cmd, cwd=inventory.ROOT, capture_output=True, text=True)
    sys.stdout.write(r.stdout)
    swept, failed = 0, []
    for ln in reversed(r.stdout.splitlines()):
        try:
            d = json.loads(ln)
            swept, failed = d.get("swept", 0), d.get("failed", [])
            break
        except ValueError:
            continue
    if r.returncode != 0 or swept == 0:
        return swept, (failed[0] if failed else (r.stderr.strip().splitlines() or ["셀 0개"])[-1])[:200]
    return swept, None


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--force", action="store_true", help="페이싱·간격 무시(수동 점검용)")
    ap.add_argument("--perspectives")
    ap.add_argument("--limit", type=int)
    a = ap.parse_args(argv)
    e = run_cycle(a.force, a.perspectives, a.limit)
    print(json.dumps(e, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
