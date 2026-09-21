"""기간 요약 도구 실행기 — get_training_summary (주별 볼륨·부하 + 주요 세션).

여러 도구(활동 목록 + 피트니스 + 분류)를 이어 붙여야 하는 "이번 블록 어땠어?" 류의
질문을 1회 호출로 끝내기 위한 도구.
"""
from __future__ import annotations

import sqlite3
from typing import Any

from src.ai.tool_exec_context import fitness_rows
from src.ai.tool_format import (
    DEFAULT_WEEK_START, columnar, num, span_days, weekly_activity_rows, weekly_last,
)
from src.utils.pace import seconds_to_pace

_QUALITY_TYPES = ("race", "interval", "threshold", "tempo")
_NOTABLE_LIMIT = 10

_ACTIVITY_SQL = (
    "SELECT a.id, date(a.start_time), a.distance_m / 1000.0, a.duration_sec, "
    "a.avg_pace_sec_km, a.avg_hr, a.name, "
    "(SELECT m.text_value FROM metric_store m WHERE m.scope_type='activity' "
    "   AND m.scope_id=CAST(a.id AS TEXT) AND m.metric_name='workout_type_classified' LIMIT 1), "
    "(SELECT COUNT(*) FROM activity_laps l WHERE l.activity_id=a.id AND l.lap_trigger='ACTIVE') "
    "FROM v_canonical_activities a "
    "WHERE a.activity_type='running' AND a.start_time>=? AND a.start_time<=? || 'T99' "
    "ORDER BY a.start_time"
)


def _notable(acts: list[tuple]) -> dict[str, Any]:
    """대회 우선, 그다음 퀄리티/구조화 세션 중 최근 순으로 상한까지. 날짜 오름차순으로 반환.

    분류기가 easy로 두는 크루즈·짧은 인터벌도 ACTIVE 랩(sets)이 있으면 포함한다.
    sets>0 이면 get_activity_laps / compare_workout_sets 로 세트를 볼 수 있다는 신호.
    """
    quality = [a for a in acts if a[7] in _QUALITY_TYPES or a[8]]
    ranked = sorted(quality, key=lambda a: (a[7] != "race", _neg_date(a[1])))
    picked = sorted(ranked[:_NOTABLE_LIMIT], key=lambda a: a[1])
    out = columnar(
        ["id", "date", "km", "pace", "type", "sets", "name"],
        [[a[0], a[1], num(a[2], 1), seconds_to_pace(int(a[4])) if a[4] else None,
          a[7], a[8] or None, a[6]]
         for a in picked],
    )
    if len(quality) > len(picked):
        out["omitted"] = len(quality) - len(picked)
    return out


def _neg_date(day: str) -> int:
    """최근 날짜가 앞에 오도록 하는 정렬 키 (YYYY-MM-DD → -YYYYMMDD)."""
    return -int(day.replace("-", ""))


def _exec_get_training_summary(conn: sqlite3.Connection, args: dict) -> dict:
    s, e = args["start_date"], args["end_date"]
    first = args.get("week_start", DEFAULT_WEEK_START)
    acts = conn.execute(_ACTIVITY_SQL, (s, e)).fetchall()

    weekly = weekly_activity_rows([(a[1], a[2], a[3], a[5]) for a in acts], first, (s, e))
    load = {r[0]: r[1:4] for r in weekly_last(fitness_rows(conn, s, e), first)}
    rows = [[*r, *load.get(r[0], (None, None, None))] for r in weekly]

    total_km = sum(a[2] or 0 for a in acts)
    total_sec = sum(a[3] or 0 for a in acts)
    weeks = max(span_days(s, e) / 7.0, 1.0)
    out: dict[str, Any] = {
        "period": f"{s} ~ {e}",
        "unit": f"week({'Mon' if first == 'mon' else 'Sun'}-start), ctl/atl/tsb는 주말 값",
        "totals": {
            "runs": len(acts), "km": num(total_km, 1), "hours": num(total_sec / 3600.0, 1),
            "avg_weekly_km": num(total_km / weeks, 1),
        },
    }
    out.update(columnar(
        ["week", "runs", "km", "min", "pace", "hr", "long_km", "ctl", "atl", "tsb"], rows))
    out["notable"] = _notable(acts)
    return out
