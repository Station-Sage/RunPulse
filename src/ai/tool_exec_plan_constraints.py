"""get_plan_constraints 도구 실행기 — 계획 초안이 지켜야 할 사용자 선호·게이트 한계값(읽기 전용)."""
from __future__ import annotations

import sqlite3

_DAY = ["월", "화", "수", "목", "금", "토", "일"]


def _days(mask) -> list[str]:
    return [_DAY[i] for i in range(7) if (mask or 0) & (1 << i)]


def _exec_get_plan_constraints(conn: sqlite3.Connection, args: dict) -> dict:
    from src.training import long_run_rules as lr
    from src.training import plan_gates as pg
    from src.training.goals import get_active_goal
    from src.training.planner_config import DISTANCE_LABEL_KM, MAX_Q_DAYS_BY_LABEL, load_prefs
    prefs = load_prefs(conn)
    goal = get_active_goal(conn)
    km = float((goal or {}).get("distance_km") or 0)
    label = next((k for k, v in DISTANCE_LABEL_KM.items() if abs(v - km) < 0.5), "custom")
    return {
        "goal": {k: goal.get(k) for k in ("id", "race_date", "distance_km", "target_time_sec")} | {"distance_label": label} if goal else None,
        "prefs": {
            "workout_weekdays": _days(prefs.get("workout_weekdays_mask")),
            "rest_weekdays": _days(prefs.get("rest_weekdays_mask")),
            "long_run_weekdays": _days(prefs.get("long_run_weekday_mask")),
            "blocked_dates": prefs.get("blocked_dates") or [],
            "max_q_days": prefs.get("max_q_days") or MAX_Q_DAYS_BY_LABEL.get(label, 2),
        },
        "limits": {
            "min_session_km": pg.MIN_SESSION_KM, "min_session_min": pg.MIN_SESSION_MIN,
            "easy_max_km": lr.EASY_MAX_KM, "weekly_ramp_max": pg.RAMP_MAX,
            "long_tol_km": pg.LONG_TOL_KM, "mp_session_min_km": pg.MP_MIN_SESSION_KM,
            "mp_fastest_gap_sec": pg.MP_FASTEST_GAP, "long_abs_cap_km": lr.ABS_CAP.get(label),
            "long_time_cap_min": lr.TIME_CAP_MIN.get(label),
        },
        "rules": ["운동 요일 밖 배치 금지", "차단 날짜 배치 금지", "대회일 이후 세션 금지"],
    }
