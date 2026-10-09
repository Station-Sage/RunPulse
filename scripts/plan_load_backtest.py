"""plan_load 모델 백테스트 — 완료된 주마다 계획 기반 추정 부하와 실제 TRIMP 합을 비교한다 (목표: 중앙 절대오차 ≤10%).

사용: PYTHONPATH=. python3 scripts/plan_load_backtest.py <running.db> [오늘=YYYY-MM-DD]
"""
from __future__ import annotations

import sqlite3
import sys
from datetime import date, timedelta
from statistics import median

from src.services import plan_load


def main(db: str, today: str) -> None:
    conn = sqlite3.connect(db)
    errs = []
    for ws in sorted({r[0] for r in conn.execute(
            "SELECT date(date, '-' || ((CAST(strftime('%w', date) AS INTEGER) + 6) % 7) || ' days') FROM planned_workouts"
            " WHERE date < ?", (today,))}):
        we = (date.fromisoformat(ws) + timedelta(days=7)).isoformat()
        if we > today:
            continue
        u = plan_load.easy_u(conn, ws)
        rows = plan_load._week_rows(conn, ws, we)
        planned = sum(plan_load.session_load(r["workout_type"], r["distance_km"], u) for r in rows)
        actual = sum(plan_load.daily_actual(conn, ws, we).values())
        if planned > 0 and actual > 0:
            errs.append(abs(planned - actual) / actual)
    if errs:
        print(f"weeks={len(errs)} median_abs_err={median(errs):.1%}")
    else:
        print("비교할 주가 없음")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else date.today().isoformat())
