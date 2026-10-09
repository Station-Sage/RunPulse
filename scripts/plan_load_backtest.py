"""plan_load 모델 백테스트 — 완료된 주마다 계획 기반 추정 부하와 실제 TRIMP 합을 비교한다 (목표: 계획≈실제 km 주의 중앙 절대오차 ≤10%).

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
    errs, all_errs = [], []
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
        km_plan = sum(r["distance_km"] or 0 for r in rows if r["workout_type"] != "rest")
        km_act = sum(r[2] or 0 for r in plan_load._activity_rows(conn, ws, we))
        if planned > 0 and actual > 0:
            all_errs.append(abs(planned - actual) / actual)
        if planned > 0 and actual > 0 and km_act and abs(km_plan - km_act) / km_act <= 0.25:
            errs.append(abs(planned - actual) / actual)
            print(f"{ws} plan_km={km_plan:.0f} act_km={km_act:.0f} plan_load={planned:.0f} act_load={actual:.0f} u={u:.1f}")
    if errs:
        print(f"모델 검증(계획 km≈실제 km ±25%인 주) weeks={len(errs)} median_abs_err={median(errs):.1%}")
        print(f"전체 weeks={len(all_errs)} median_abs_err={median(all_errs):.1%} (계획 이행 편차 포함)")
    else:
        print("비교할 주가 없음")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else date.today().isoformat())
