"""감사 사이클 1회 — 페이싱 확인 → 고아 정리 → 스윕 → 관점 감사 → 사이클 로그(cycles.jsonl).

사용: .venv/bin/python -m scripts.audit.cycle [--force] [--perspectives ui,ux] [--limit N]
무한 반복 아님: 한 번 호출에 한 사이클이며, pacing(세션·주간 사용률)과 최소 간격(CYCLE_MIN_INTERVAL_MIN)이 막으면 사유만 기록하고 끝난다.
결과는 BACKLOG 후보((판단 필요))로만 남기고 자동 수정은 하지 않는다.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time

from scripts.audit import agents, inventory, procs
from scripts.autopilot import pacing, settings

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


def run_cycle(force: bool = False, perspectives: str | None = None, limit: int | None = None) -> dict:
    now = time.time()
    entry: dict = {"ts": now, "ran": False}
    reason = skip_reason(now, force)
    if reason:
        entry["reason"] = reason
        _log(entry)
        return entry
    entry["reaped"] = procs.reap()
    cmd = [sys.executable, "-m", "scripts.audit.sweep"] + (["--limit", str(limit)] if limit else [])
    entry["sweep_rc"] = subprocess.run(cmd, cwd=inventory.ROOT).returncode
    groups = agents.group_issues(inventory.load_ledger())
    args = ["--backlog"] + (["--perspectives", perspectives] if perspectives else [])
    entry["issue_kinds"] = {k: len(v) for k, v in groups.items()}
    entry["agents_rc"] = agents.main(args)
    entry["ran"] = True
    entry["findings"] = len(json.loads(agents.FINDINGS_PATH.read_text(encoding="utf-8"))) if agents.FINDINGS_PATH.exists() else 0
    entry["elapsed_sec"] = round(time.time() - now)
    _log(entry)
    return entry


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
