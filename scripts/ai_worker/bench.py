"""Claude 큐 워커 벤치 — 같은 DB 로 ping 잡 n개를 순차 실행해 큐 지연·총 소요를 잰다.

사용: python3 scripts/ai_worker/bench.py --db <running.db> [--model sonnet] [-n 5]
(워커가 해당 uid 로 떠 있어야 한다.)
"""
from __future__ import annotations

import argparse
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from src.ai import claude_queue as cq  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    ap.add_argument("--model", default="sonnet")
    ap.add_argument("-n", type=int, default=5)
    a = ap.parse_args()
    totals, queues, fails = [], [], 0
    for _ in range(a.n):
        t = time.monotonic()
        r = cq.run_job(a.db, kind="ping", model=a.model, prompt="Reply with exactly: pong", deadline_sec=60)
        totals.append(time.monotonic() - t)
        queues.append(r.get("queue_ms") or 0)
        fails += 0 if r["ok"] else 1
    print(f"model={a.model} n={a.n} fail={fails} total_s median={statistics.median(totals):.2f} "
          f"max={max(totals):.2f} queue_ms median={statistics.median(queues):.0f} max={max(queues)}")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
