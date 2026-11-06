"""Training Balance Radar 조립 — 기존 메트릭(tids·marathon_shape·acwr)·wellness·계획·목표로 6축 (07 §7d).

설계: v0.3/data/phase-7-ui-renewal/design-2026-11-features/balance-radar.md. 새 Calculator 없이 표시 시점에 계산한다
(target 이 플랜·목표 같은 사용자 설정에 의존하므로). 모든 조회는 as_of(포함) 이전 값만 읽는다 — compare 누수 방지.
계획은 사용자 설정이라 as_of 이후 계획 행도 목표(target)로 읽는다.
"""
from __future__ import annotations

import sqlite3
from datetime import date, timedelta

from src.services import metrics_service, plan_load, wellness_service
from src.services import training_balance_axes as ax
from src.services.metric_freshness import BADGE_TEXT
from src.training.goals import get_active_goal

WINDOW_WEEKS = 8
HISTORY_DAYS = 182      # A1 ② 개인 최고 지속 볼륨 창(26주)
LONG_PLAN_DAYS = 84     # A2 ① 활성 플랜 최장 롱런: as_of ±12주
WELLNESS_DAYS = 60
MAX_COMPARE_DAYS = 84


def _shift(day: str, days: int) -> str:
    return (date.fromisoformat(day) + timedelta(days=days)).isoformat()


def _goal_distance(conn: sqlite3.Connection, as_of: str) -> float | None:
    """활성 목표 거리. 이미 지난 대회 목표는 무시."""
    g = get_active_goal(conn)
    if not g or (g.get("race_date") and str(g["race_date"])[:10] < as_of):
        return None
    return g.get("distance_km")


def _active_plan_long(conn: sqlite3.Connection, as_of: str) -> float | None:
    """A2 ①: as_of 이후 계획이 남아 있는(활성) 플랜만 — 끝난 플랜의 롱런은 목표로 쓰지 않는다."""
    if not plan_load.weekly_planned_km(conn, as_of, _shift(as_of, LONG_PLAN_DAYS + 1)):
        return None
    return plan_load.longest_planned_long_km(conn, _shift(as_of, -LONG_PLAN_DAYS), _shift(as_of, LONG_PLAN_DAYS + 1))


def _volume_long(conn: sqlite3.Connection, as_of: str) -> tuple[dict, dict, dict | None]:
    shape = metrics_service.get_daily_metric_as_of(conn, "marathon_shape", as_of)
    js = (shape or {}).get("json") or {}
    plan_weeks = plan_load.weekly_planned_km(conn, _shift(as_of, -7 * WINDOW_WEEKS + 1), _shift(as_of, 1))
    hist = [(p["date"], (p["json"] or {}).get("weekly_km_8w"))
            for p in metrics_service.get_daily_series(conn, "marathon_shape", _shift(as_of, -HISTORY_DAYS), as_of)]
    v_tgt, v_basis, v_reason = ax.volume_target(plan_weeks, hist)
    on = shape["date"] if shape else None
    src = ["marathon_shape"] + (["planned_workouts"] if v_basis == "plan" else [])
    volume = ax.build_axis("volume", as_of, js.get("weekly_km_8w"), v_tgt, v_basis,
                           reason="no_shape" if not shape else v_reason, source=src, computed_on=on)
    plan_long = _active_plan_long(conn, as_of)
    l_tgt, l_basis = ax.long_run_target(plan_long, _goal_distance(conn, as_of), v_tgt)
    long_run = ax.build_axis("long_run", as_of, js.get("longest_12w_km"), l_tgt, l_basis, reason="no_shape",
                             source=["marathon_shape"] + (["planned_workouts"] if l_basis == "plan" else []),
                             computed_on=on)
    return volume, long_run, (js or None)


def _intensity(conn: sqlite3.Connection, as_of: str) -> tuple[dict, dict, dict | None]:
    tids = metrics_service.get_daily_metric_as_of(conn, "tids", as_of)
    js = (tids or {}).get("json") or {}
    on = tids["date"] if tids else None
    low = js.get("low_pct")
    quality = (js["mid_pct"] + js["high_pct"]) if js.get("mid_pct") is not None and js.get("high_pct") is not None else None
    easy = ax.build_axis("easy_base", as_of, low, ax.EASY_TARGET_PCT, "default_rule", reason="insufficient_runs",
                         source=["tids"], computed_on=on)
    qual = ax.build_axis("quality", as_of, quality, ax.QUALITY_TARGET_PCT, "default_rule", reason="insufficient_runs",
                         source=["tids"], computed_on=on)
    return easy, qual, (js or None)


def _load(conn: sqlite3.Connection, as_of: str) -> dict:
    acwr = metrics_service.get_daily_metric_as_of(conn, "acwr", as_of)
    return ax.build_axis("load", as_of, (acwr or {}).get("value"), ax.ACWR_TARGET, "default_rule",
                         reason="acwr_warmup", source=["acwr"], computed_on=acwr["date"] if acwr else None, ndigits=2)


def _recovery(conn: sqlite3.Connection, as_of: str) -> dict:
    tr = wellness_service.get_wellness_trend(conn, days=WELLNESS_DAYS, end=as_of)
    actual, last = ax.recovery_ratio(tr.get("dates", []), tr, as_of)
    return ax.build_axis("recovery", as_of, actual, 1.0, "personal_baseline", reason="no_wellness",
                         source=["daily_wellness"], computed_on=last, ndigits=3)


def compute_axes(conn: sqlite3.Connection, as_of: str) -> tuple[list[dict], dict, dict]:
    """as_of 기준 6축 + 보조 json(shape·tids). 축 순서는 ax.ORDER."""
    volume, long_run, shape_js = _volume_long(conn, as_of)
    easy, quality, tids_js = _intensity(conn, as_of)
    return [volume, long_run, easy, quality, _load(conn, as_of), _recovery(conn, as_of)], shape_js or {}, tids_js or {}


def _aux(conn: sqlite3.Connection, as_of: str, shape_js: dict, tids_js: dict) -> dict:
    def num(name: str) -> float | None:
        p = metrics_service.get_daily_metric_as_of(conn, name, as_of, max_age_days=7)
        return p["value"] if p else None
    return {"tsb": num("tsb"), "monotony": num("monotony"), "tanda_required_km": shape_js.get("tanda_required_km"),
            "tids_pattern": tids_js.get("pattern"), "race_share_of_quality": None}  # D3: 레이스 분리는 후속


def _notes(axes: list[dict]) -> list[str]:
    by = {a["key"]: a for a in axes}
    notes: list[str] = []
    if by["quality"]["score"] is not None:
        notes += ["zone_boundary_vdot", "quality_includes_races"]
    if by["long_run"]["score"] is not None:
        notes.append("long_run_includes_races")
    if by["volume"]["basis"] == "personal_peak" and by["volume"]["score"] is not None:
        notes.append("volume_personal_peak")
    return notes


def get_training_balance(conn: sqlite3.Connection, as_of: str, compare_days: int = 28) -> dict:
    """GET /library/metrics/training-balance 응답 data. 데이터 부족은 state 로 표현(에러 아님)."""
    axes, shape_js, tids_js = compute_axes(conn, as_of)
    compare = None
    if compare_days > 0:
        c_as_of = _shift(as_of, -compare_days)
        c_axes, _, _ = compute_axes(conn, c_as_of)
        compare = {"as_of": c_as_of, "axes": [{"key": a["key"], "score": a["score"]} for a in c_axes]}
    return {
        "as_of": as_of, "window_weeks": WINDOW_WEEKS, "state": ax.overall_state(axes), "axes": axes,
        "compare": compare, "aux": _aux(conn, as_of, shape_js, tids_js), "notes": _notes(axes),
        "stale_text": BADGE_TEXT["stale"],
    }
