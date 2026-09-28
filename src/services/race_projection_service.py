"""레이스 아침 폼 예측 — 현재 CTL/ATL에서 테이퍼 유무 두 시나리오로 TSB를 전방 투영한다."""
from __future__ import annotations

import sqlite3
from datetime import date as _date, timedelta

from src.metrics.bands import with_grade
from src.metrics.pmc import ATL_DAYS, CTL_DAYS
LOOKBACK_DAYS = 28
MAX_HORIZON_DAYS = 120

# 레이스까지 남은 일수(d) 구간별 부하 배율(테이퍼): 15일 이상 전은 평소대로
_TAPER = [(14, 1.0), (7, 0.75), (3, 0.55), (0, 0.35)]


def _taper_factor(days_to_race: int) -> float:
    """days_to_race: 그날부터 레이스까지 남은 일수(레이스 전날=1)."""
    if days_to_race > 14:
        return 1.0
    if days_to_race > 7:
        return 0.75
    if days_to_race > 3:
        return 0.55
    return 0.35


def _latest(conn: sqlite3.Connection, name: str, date: str) -> float | None:
    row = conn.execute(
        "SELECT numeric_value FROM metric_store WHERE metric_name = ? AND scope_type = 'daily'"
        " AND is_primary = 1 AND numeric_value IS NOT NULL AND scope_id <= ?"
        " ORDER BY scope_id DESC LIMIT 1",
        (name, date),
    ).fetchone()
    return float(row[0]) if row else None


def _avg_daily_load(conn: sqlite3.Connection, date: str) -> float:
    """최근 28일 하루 평균 TRIMP(휴식일 포함) — PMC와 같은 부하원(activity trimp, primary)."""
    start = (_date.fromisoformat(date) - timedelta(days=LOOKBACK_DAYS)).isoformat()
    row = conn.execute(
        "SELECT COALESCE(SUM(m.numeric_value), 0) FROM metric_store m"
        " JOIN v_canonical_activities a ON CAST(m.scope_id AS INTEGER) = a.id"
        " WHERE m.scope_type = 'activity' AND m.metric_name = 'trimp' AND m.is_primary = 1"
        "   AND substr(a.start_time, 1, 10) > ? AND substr(a.start_time, 1, 10) <= ?",
        (start, date),
    ).fetchone()
    return float(row[0] or 0) / LOOKBACK_DAYS


def _run(ctl: float, atl: float, base: float, start: _date, race: _date, taper: bool) -> dict:
    # PMC와 같은 α = 1/τ(DECISIONS D1) — 투영이 현재 CTL/TSB와 같은 척도여야 한다.
    a_atl = 1.0 / ATL_DAYS
    a_ctl = 1.0 / CTL_DAYS
    series = []
    day = start + timedelta(days=1)
    while day < race:  # 레이스 당일 훈련 부하는 반영하지 않음 = 레이스 아침 상태
        load = base * (_taper_factor((race - day).days) if taper else 1.0)
        atl = atl * (1 - a_atl) + load * a_atl
        ctl = ctl * (1 - a_ctl) + load * a_ctl
        series.append({"date": day.isoformat(), "value": round(ctl - atl, 1)})
        day += timedelta(days=1)
    return {"ctl": round(ctl, 1), "atl": round(atl, 1), "tsb": round(ctl - atl, 1), "series": series}


def project_race_form(conn: sqlite3.Connection, race_date: str, date: str | None = None) -> dict | None:
    """레이스 아침(전날까지 반영)의 CTL/ATL/TSB를 두 시나리오로 예측.

    - keep: 최근 28일 평균 부하를 레이스 전날까지 유지
    - taper: 15일 전까지 평소대로, 이후 부하 배율 0.75(14~8일 전) → 0.55(7~4일) → 0.35(3~1일)
    현재 CTL/ATL이 없거나 레이스가 오늘 이전/당일이거나 120일 넘게 남았으면 None.
    """
    today = _date.fromisoformat(date) if date else _date.today()
    race = _date.fromisoformat(race_date)
    days_left = (race - today).days
    if days_left <= 0 or days_left > MAX_HORIZON_DAYS:
        return None
    ds = today.isoformat()
    ctl0 = _latest(conn, "ctl", ds)
    atl0 = _latest(conn, "atl", ds)
    if ctl0 is None or atl0 is None:
        return None
    base = _avg_daily_load(conn, ds)
    return {
        "as_of": ds,
        "race_date": race_date,
        "days_left": days_left,
        "base_daily_load": round(base, 1),
        "current": {"ctl": round(ctl0, 1), "atl": round(atl0, 1), "tsb": round(ctl0 - atl0, 1)},
        "assumptions": "최근 28일 하루 평균 부하 기준 · 테이퍼: 14~8일 전 75% → 7~4일 전 55% → 3~1일 전 35%",
        "scenarios": [
            _graded({"key": "taper", "label": "테이퍼 적용", **_run(ctl0, atl0, base, today, race, True)}),
            _graded({"key": "keep", "label": "지금처럼 유지", **_run(ctl0, atl0, base, today, race, False)}),
        ],
    }


def _graded(scenario: dict) -> dict:
    """레이스 아침 TSB 등급(bands.py, 레이스 국면)을 status·status_label로 붙인다."""
    return with_grade(scenario, "tsb", scenario.get("tsb"), phase="race")
