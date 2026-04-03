"""RTTI (Running Tolerance Training Index) — 달리기 내성 훈련 지수.

1차: Garmin running_tolerance_load / optimal_max_load × 100
2차 (fallback): ATL / (CTL × wellness_factor) × 100 — Garmin 데이터 없을 때 자체 추정

100이면 적정 훈련량, 100 초과 시 과부하, 70 미만 시 여유.
저장: computed_metrics (date, 'RTTI', value, extra_json)
"""
from __future__ import annotations

import json
import sqlite3
from datetime import date, timedelta

from src.metrics.store import save_metric


def calc_rtti(load: float, optimal_max: float) -> float:
    """RTTI 계산 (순수 함수).

    Args:
        load: 실제 훈련 부하.
        optimal_max: 권장 최대 부하.

    Returns:
        RTTI 값 (%). 100 = 최대 권장치.
    """
    if optimal_max <= 0:
        return 0.0
    return round(load / optimal_max * 100, 1)


def _calc_rtti_from_fitness(
    atl: float, ctl: float,
    body_battery: float | None = None,
    sleep_score: float | None = None,
) -> tuple[float, dict]:
    """CTL/ATL + 웰니스 기반 자체 RTTI 추정.

    공식: RTTI = ATL / (CTL × wellness_factor) × 100
    - CTL이 0이면 ATL 기반 추정 (기초 체력 없으므로 부하 = 과부하)
    - wellness_factor: 1.0 기본, BB/수면 나쁘면 0.8~0.9 (내성 감소)

    Returns:
        (rtti_value, extra_json_dict)
    """
    # 웰니스 보정 계수
    wf = 1.0
    if body_battery is not None:
        if body_battery < 30:
            wf *= 0.8
        elif body_battery < 50:
            wf *= 0.9
    if sleep_score is not None:
        if sleep_score < 40:
            wf *= 0.85
        elif sleep_score < 60:
            wf *= 0.92

    # CTL 기반 용량 추정
    if ctl <= 0:
        # 기초 체력 없음 → ATL이 있으면 무조건 과부하
        capacity = max(atl * 0.5, 10.0)
    else:
        capacity = ctl * wf

    rtti = round(atl / capacity * 100, 1) if capacity > 0 else 0.0
    # 상한 200
    rtti = min(rtti, 200.0)

    extra = {
        "source": "estimated",
        "atl": round(atl, 1),
        "ctl": round(ctl, 1),
        "wellness_factor": round(wf, 2),
        "capacity": round(capacity, 1),
    }
    if body_battery is not None:
        extra["body_battery"] = body_battery
    if sleep_score is not None:
        extra["sleep_score"] = sleep_score

    return rtti, extra


def calc_and_save_rtti(conn: sqlite3.Connection, target_date: str) -> float | None:
    """RTTI 계산 후 저장. Garmin 우선, 없으면 CTL/ATL 자체 추정.

    Args:
        conn: SQLite 커넥션.
        target_date: YYYY-MM-DD.

    Returns:
        RTTI 값 또는 None.
    """
    td = date.fromisoformat(target_date)

    # 1차: Garmin running_tolerance 데이터
    for delta in range(8):
        check_date = (td - timedelta(days=delta)).isoformat()
        row = conn.execute(
            """SELECT metric_name, metric_value FROM daily_detail_metrics
               WHERE date=? AND metric_name IN (
                 'running_tolerance_load',
                 'running_tolerance_optimal_max',
                 'running_tolerance_score'
               )""",
            (check_date,),
        ).fetchall()
        if not row:
            continue
        m = {r[0]: r[1] for r in row if r[1] is not None}
        load = m.get("running_tolerance_load")
        opt_max = m.get("running_tolerance_optimal_max")
        if load is not None and opt_max is not None and opt_max > 0:
            rtti = calc_rtti(float(load), float(opt_max))
            extra = {
                "source": "garmin",
                "load": float(load),
                "optimal_max": float(opt_max),
                "score": m.get("running_tolerance_score"),
                "source_date": check_date,
            }
            save_metric(conn, date=target_date, metric_name="RTTI", value=rtti, extra_json=extra)
            return rtti

    # 2차 fallback: CTL/ATL 기반 자체 추정
    try:
        return _fallback_rtti(conn, target_date)
    except Exception:
        return None


def _fallback_rtti(conn: sqlite3.Connection, target_date: str) -> float | None:
    """CTL/ATL 기반 RTTI fallback."""
    fit_row = conn.execute(
        "SELECT ctl, atl FROM daily_fitness WHERE date<=? ORDER BY date DESC LIMIT 1",
        (target_date,),
    ).fetchone()
    if not fit_row or fit_row[0] is None or fit_row[1] is None:
        return None

    ctl, atl = float(fit_row[0]), float(fit_row[1])
    if ctl <= 0 and atl <= 0:
        return None

    # 웰니스 데이터 (있으면 보정)
    well_row = conn.execute(
        "SELECT body_battery, sleep_score FROM daily_wellness "
        "WHERE source='garmin' AND date<=? ORDER BY date DESC LIMIT 1",
        (target_date,),
    ).fetchone()
    bb = float(well_row[0]) if well_row and well_row[0] is not None else None
    sleep = float(well_row[1]) if well_row and well_row[1] is not None else None

    rtti, extra = _calc_rtti_from_fitness(atl, ctl, bb, sleep)
    save_metric(conn, date=target_date, metric_name="RTTI", value=rtti, extra_json=extra)
    return rtti

# Note: calc_and_save_rtti ends at the try/except above.
# _fallback_rtti is a helper called from there.
