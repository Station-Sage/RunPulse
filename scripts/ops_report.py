#!/usr/bin/env python3
"""운영 리포트 — ops.db 읽기 전용: 최근 24h 스케줄러 성공률·p95·연체·휴면, 오늘 LLM 상위 10·전역 사용률 (AUTH-MULTIUSER-SYNC §5).

사용법:
    python scripts/ops_report.py [--db PATH] [--json] [--show-names]

- 파일을 만들거나 바꾸지 않는다(sqlite `mode=ro`). DB 가 없으면 빈 리포트.
- uid 는 기본 마스킹. 전역 한도는 src.ai.llm_budget.limits()(env LLM_LIMITS_JSON 반영).
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.utils.user_context import mask_uid  # noqa: E402


def _p95(values: list[float]) -> float | None:
    if not values:
        return None
    vals = sorted(values)
    return round(vals[min(len(vals) - 1, int(round(0.95 * (len(vals) - 1))))], 1)


def _tables(conn: sqlite3.Connection) -> set[str]:
    return {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}


def build_report(conn: sqlite3.Connection | None, now: datetime, day: str, limits: dict,
                 mask=mask_uid) -> dict:
    """리포트 dict. conn=None 이면 빈 리포트."""
    out = {"generated_at": now.isoformat(timespec="seconds"), "users": [], "dormant": 0,
           "max_overdue_h": 0.0, "llm_top": [], "llm_global": {"calls": 0, "tokens": 0, "ratio": 0.0}}
    if conn is None:
        return out
    tables = _tables(conn)
    if "sched_runs" in tables:
        since = (now - timedelta(hours=24)).isoformat(timespec="seconds")
        per: dict[str, dict] = {}
        for uid, result, dur in conn.execute(
                "SELECT uid, result, duration_s FROM sched_runs WHERE started_at >= ?", (since,)):
            d = per.setdefault(uid, {"runs": 0, "ok": 0, "durs": []})
            if result.startswith("skipped_"):
                continue
            d["runs"] += 1
            d["ok"] += result == "ok"
            if dur is not None:
                d["durs"].append(float(dur))
        out["users"] = [{"uid": mask(u), "runs": d["runs"],
                         "success_rate": round(d["ok"] / d["runs"], 2) if d["runs"] else None,
                         "p95_s": _p95(d["durs"])} for u, d in sorted(per.items())]
    if "sched_state" in tables:
        for next_due, state in conn.execute("SELECT next_due_at, state FROM sched_state"):
            if state == "dormant":
                out["dormant"] += 1
                continue
            late = (now - datetime.fromisoformat(next_due)).total_seconds() / 3600
            out["max_overdue_h"] = max(out["max_overdue_h"], round(late, 1))
    if "llm_usage_daily" in tables:
        out["llm_top"] = [{"uid": mask(r[0]), "calls": r[1], "tokens": r[2], "refused": r[3]} for r in conn.execute(
            "SELECT uid, SUM(calls), SUM(tokens_in+tokens_out), SUM(refused) FROM llm_usage_daily WHERE day=? "
            "GROUP BY uid ORDER BY SUM(calls) DESC LIMIT 10", (day,))]
        calls, tokens = conn.execute("SELECT COALESCE(SUM(calls),0), COALESCE(SUM(tokens_in+tokens_out),0) "
                                     "FROM llm_usage_daily WHERE day=?", (day,)).fetchone()
        ratio = max(calls / limits["global_calls"], tokens / limits["global_tokens"])
        out["llm_global"] = {"calls": calls, "tokens": tokens, "ratio": round(ratio, 3)}
    return out


def open_readonly(path: Path) -> sqlite3.Connection | None:
    if not path.exists():
        return None
    return sqlite3.connect(f"file:{path}?mode=ro", uri=True)


def main(argv: list[str] | None = None) -> int:
    from src.ai.llm_budget import day_of, limits, now_kst
    from src.ops.store import ops_db_path
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--db", type=Path, default=None)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--show-names", action="store_true")
    args = ap.parse_args(argv)
    conn = open_readonly(args.db or ops_db_path())
    try:
        rep = build_report(conn, datetime.now(), day_of(now_kst()), limits(),
                           mask=(lambda u: u) if args.show_names else mask_uid)
    finally:
        if conn is not None:
            conn.close()
    if args.json:
        print(json.dumps(rep, ensure_ascii=False, indent=2))
        return 0
    print(f"[ops_report] {rep['generated_at']}")
    for u in rep["users"]:
        print(f"  {u['uid']}: runs={u['runs']} success={u['success_rate']} p95={u['p95_s']}s")
    print(f"  dormant={rep['dormant']} max_overdue={rep['max_overdue_h']}h")
    g = rep["llm_global"]
    print(f"  LLM today: calls={g['calls']} tokens={g['tokens']} ratio={g['ratio']}")
    for t in rep["llm_top"]:
        print(f"    {t['uid']}: calls={t['calls']} tokens={t['tokens']} refused={t['refused']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
