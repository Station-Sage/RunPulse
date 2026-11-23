"""전체 루프 감시 — 멈춤·정지·타이머 이상을 점검해 문제가 새로 생기거나 바뀔 때만 텔레그램으로 알린다.

사용: .venv/bin/python -m scripts.audit.watch [--status]   (타이머 runpulse-watch 가 30분마다 호출)
점검: 타이머 비활성 / 루프 상태 halted / 루프 프로세스가 도는데 진행 로그가 STALL_MIN 분 넘게 없음 /
      마지막 감사 사이클 실패 / 사용자 결정 대기·blocked 항목 수(정보용, 알림 사유 아님).
같은 문제 조합이 반복되면 재알림하지 않고, 해소되면 복구를 한 번 알린다.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path

from scripts.audit import loop, progress
from scripts.autopilot import notify, queue, settings

STALL_MIN = 45
STATE_PATH = loop.STATE_PATH.parent / "watch_state.json"
CYCLES_PATH = loop.STATE_PATH.parent / "cycles.jsonl"


def _run(args: list[str]) -> tuple[int, str]:
    r = subprocess.run(args, capture_output=True, text=True, timeout=30)
    return r.returncode, r.stdout.strip()


def _last_cycle() -> dict:
    try:
        return json.loads(CYCLES_PATH.read_text(encoding="utf-8").strip().splitlines()[-1])
    except (OSError, ValueError, IndexError):
        return {}


def collect(now: float | None = None, run=_run) -> dict:
    now = now or time.time()
    st = loop.load_state()
    log_age = (now - progress.LOG_PATH.stat().st_mtime) / 60 if progress.LOG_PATH.exists() else None
    items = queue.parse(settings.QUEUE_PATH)
    return {
        "timer": run(["systemctl", "--user", "is-active", "runpulse-audit.timer"])[1],
        "running": run(["pgrep", "-f", "scripts.audit.loop"])[0] == 0,
        "phase": st["phase"], "round": st["round"], "fails": st["fails"], "units_done": st["units_done"],
        "log_age_min": log_age,
        "last_cycle": _last_cycle().get("outcome"),
        "blocked": sum(1 for i in items if i.item_id.startswith("AUD-") and i.stage == "blocked"),
        "queued": sum(1 for i in items if i.item_id.startswith("AUD-") and i.stage == "queued"),
    }


def problems(s: dict) -> list[str]:
    out = []
    if s["timer"] != "active":
        out.append(f"타이머 비활성({s['timer'] or '없음'})")
    if s["phase"] == "halted":
        out.append("루프 정지(halted) — --reset 필요")
    if s["running"] and s["log_age_min"] is not None and s["log_age_min"] > STALL_MIN:
        out.append(f"루프 실행 중인데 진행 로그 {int(s['log_age_min'])}분 정체")
    if s["last_cycle"] not in (None, "done"):
        out.append(f"마지막 감사 사이클 실패({s['last_cycle']})")
    return out


def check(s: dict, path: Path | None = None, send=notify.send) -> list[str]:
    p = path or STATE_PATH
    prev = json.loads(p.read_text(encoding="utf-8")).get("problems", []) if p.exists() else []
    cur = problems(s)
    if cur != prev:
        if cur:
            send("[루프 감시] 문제: " + " / ".join(cur))
        elif prev:
            send("[루프 감시] 복구됨 — 이상 없음")
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps({"problems": cur}, ensure_ascii=False), encoding="utf-8")
    return cur


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--status", action="store_true", help="알림 없이 현황만 출력")
    a = ap.parse_args(argv)
    s = collect()
    print(json.dumps({**s, "problems": problems(s)}, ensure_ascii=False, indent=1))
    if not a.status:
        check(s)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
