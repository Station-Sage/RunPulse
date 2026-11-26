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

from scripts.audit import agents, inventory, known, procs, progress
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
    progress.mark(f"[감사] 브라우저 스윕 시작{' (릴리스·Opus)' if release else ''}")
    progress.event("sub", step="sweep", state="start")
    swept, err = browser_sweep(limit)
    progress.event("sub", step="sweep", state="end", ok=not err)
    entry["swept"] = swept
    progress.mark(f"[감사] 스윕 종료 — {swept}셀" + (f" 실패: {err}" if err else ""))
    if err:
        entry.update(outcome="sweep_failed", reason=err, elapsed_sec=round(time.time() - now))
        _log(entry)
        notify.send(f"[감사] 브라우저 스윕 실패 — 에이전트 감사 생략: {err}" + notify.console_hint())
        return entry
    groups = agents.group_issues(inventory.load_ledger())
    entry["reverify"] = {k: len(v) for k, v in known.reverify(groups).items()}
    args = ["--backlog", "--review", "--discover"] + (["--perspectives", perspectives] if perspectives else []) + (["--release"] if release else [])
    entry["issue_kinds"] = {k: len(v) for k, v in groups.items()}
    progress.mark(f"[감사] 관점 감사 + 독립 검토 시작 — 이슈 유형 {len(groups)}종")
    progress.event("sub", step="audit", state="start")
    entry["agents_rc"] = agents.main(args)
    progress.event("sub", step="review", state="end")
    entry["outcome"] = "done"
    entry["findings"] = _count_findings()
    entry["confirmed"] = _count_findings(confirmed_only=True)
    entry["elapsed_sec"] = round(time.time() - now)
    _log(entry)
    notify.send(summary(entry) + notify.console_hint())
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


def _sweep_once(limit: int | None, screens: list[str] | None = None) -> tuple[int, str | None]:
    cmd = [sys.executable, "-m", "scripts.audit.sweep"] + (["--limit", str(limit)] if limit else []) + (["--screens", ",".join(screens)] if screens else [])
    p = subprocess.Popen(cmd, cwd=inventory.ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    lines: list[str] = []
    for ln in p.stdout:  # 진행 로그를 저널에 즉시 흘린다(끝난 뒤 한꺼번에 쓰지 않음)
        sys.stdout.write(ln)
        sys.stdout.flush()
        lines.append(ln.rstrip("\n"))
        if ln.startswith("[sweep] "):
            progress.event("step", text=ln[8:].strip(), bad=("실패" in ln))
    rc = p.wait()
    swept, failed = 0, []
    for ln in reversed(lines):
        try:
            d = json.loads(ln)
            swept, failed = d.get("swept", 0), d.get("failed", [])
            break
        except ValueError:
            continue
    if rc != 0 or swept == 0:
        tail = " | ".join([x for x in lines if x.strip()][-3:])  # 마지막 3줄 — 원인 줄이 끝 한 줄이 아닌 경우가 많다
        return swept, (str(failed[0]) if failed else tail or "셀 0개")[:300]
    return swept, None


def browser_sweep(limit: int | None = None, screens: list[str] | None = None) -> tuple[int, str | None]:
    """브라우저 스윕 — (셀 수, 실패 사유). 일시 실패(서버 기동·브라우저)는 1회 재시도, 사유엔 stderr 끝 3줄. 생략 경로는 없다."""
    if not shutil.which("node"):
        return 0, "node 없음"
    swept, err = _sweep_once(limit, screens)
    if err:
        swept, err2 = _sweep_once(limit, screens)
        err = None if err2 is None else f"재시도 후에도 실패: {err2}"
    return swept, err


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
