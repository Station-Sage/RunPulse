"""CIRS (Composite Injury Risk Score) — 복합 부상 위험 점수.

CIRS = ACWR_risk × 0.4 + Monotony_risk × 0.2 + Spike_risk × 0.3 + Asym_risk × 0.1

등급: 0-20(안전), 21-50(주의), 51-80(경고), 81-100(위험)

Asym_risk: Garmin GCT 데이터 없으면 0, 나머지 3요소 정규화.
"""
from __future__ import annotations

import sqlite3
from datetime import date, timedelta

from src.metrics.acwr import acwr_risk_level, calc_and_save_acwr
from src.metrics.lsi import calc_lsi
from src.metrics.monotony import calc_and_save_monotony, get_monotony
from src.metrics.store import load_metric, save_metric
from src.metrics.trimp import get_trimp_series


def calc_cirs(
    acwr: float | None,
    monotony: float | None,
    lsi_weekly: float | None,
    asym_pct: float | None = None,
) -> dict:
    """CIRS 계산 (순수 함수).

    Args:
        acwr: ACWR 값.
        monotony: Monotony 값.
        lsi_weekly: 이번 주 / 지난 주 부하 비율 (LSI 주간 버전).
        asym_pct: GCT 좌우 비대칭 (%). None이면 Asym_risk=0.

    Returns:
        {cirs, acwr_risk, mono_risk, spike_risk, asym_risk, grade, has_asym_data}
    """
    # ACWR_risk
    if acwr is not None:
        acwr_risk = 100 if acwr > 1.5 else 70 if acwr > 1.3 else 30 if acwr < 0.8 else 0
    else:
        acwr_risk = 0

    # Monotony_risk
    if monotony is not None:
        mono_risk = 100 if monotony > 2.0 else 60 if monotony > 1.5 else 0
    else:
        mono_risk = 0

    # Spike_risk (LSI 주간)
    if lsi_weekly is not None:
        spike_risk = 100 if lsi_weekly > 1.3 else 50 if lsi_weekly > 1.1 else 0
    else:
        spike_risk = 0

    # Asym_risk (GCT 기반)
    has_asym = asym_pct is not None
    if has_asym:
        asym_risk = min(100.0, asym_pct * 5.0)  # 20% = 100점
    else:
        asym_risk = 0.0

    if has_asym:
        cirs = acwr_risk * 0.4 + mono_risk * 0.2 + spike_risk * 0.3 + asym_risk * 0.1
    else:
        # Asym 없으면 나머지 3요소 가중치 정규화 (합 = 1.0)
        cirs = acwr_risk * (0.4 / 0.9) + mono_risk * (0.2 / 0.9) + spike_risk * (0.3 / 0.9)

    return {
        "cirs": round(cirs, 1),
        "acwr_risk": acwr_risk,
        "mono_risk": mono_risk,
        "spike_risk": spike_risk,
        "asym_risk": round(asym_risk, 1),
        "has_asym_data": has_asym,
        "grade": cirs_grade(cirs),
    }


def cirs_grade(cirs: float) -> str:
    """CIRS 등급 분류."""
    if cirs <= 20:
        return "safe"
    if cirs <= 50:
        return "caution"
    if cirs <= 80:
        return "warning"
    return "danger"


def _get_weekly_lsi(conn: sqlite3.Connection, target_date: str) -> float | None:
    """이번 주 TRIMP 합 / 지난 주 TRIMP 합 (LSI 주간 버전)."""
    td = date.fromisoformat(target_date)
    this_week_start = (td - timedelta(days=6)).isoformat()
    last_week_start = (td - timedelta(days=13)).isoformat()
    last_week_end = (td - timedelta(days=7)).isoformat()

    this_week = sum(get_trimp_series(conn, this_week_start, target_date))
    last_week = sum(get_trimp_series(conn, last_week_start, last_week_end))

    if last_week <= 0:
        return None
    return this_week / last_week


def _get_gct_asymmetry(conn: sqlite3.Connection, target_date: str) -> float | None:
    """최근 7일 평균 GCT 좌우 비대칭 (%).

    activity_detail_metrics에서 gct_left_ms, gct_right_ms 조회.
    """
    rows = conn.execute(
        """SELECT
             AVG(CASE WHEN m.metric_name='gct_left_ms' THEN m.metric_value END),
             AVG(CASE WHEN m.metric_name='gct_right_ms' THEN m.metric_value END)
           FROM activity_detail_metrics m
           JOIN activity_summaries a ON a.id = m.activity_id
           WHERE m.metric_name IN ('gct_left_ms', 'gct_right_ms')
             AND DATE(a.start_time) BETWEEN ? AND ?""",
        ((date.fromisoformat(target_date) - timedelta(days=6)).isoformat(), target_date),
    ).fetchone()

    if rows is None or rows[0] is None or rows[1] is None:
        return None

    gct_l, gct_r = float(rows[0]), float(rows[1])
    avg_gct = (gct_l + gct_r) / 2.0
    if avg_gct <= 0:
        return None
    return abs(gct_l - gct_r) / avg_gct * 100.0


def calc_and_save_cirs(conn: sqlite3.Connection, target_date: str) -> float | None:
    """CIRS 계산 후 computed_metrics에 저장.

    선행 계산: ACWR, Monotony가 없으면 여기서 계산.

    Args:
        conn: SQLite 커넥션.
        target_date: YYYY-MM-DD.

    Returns:
        CIRS 값 또는 None.
    """
    # ACWR (없으면 계산)
    acwr = load_metric(conn, target_date, "ACWR")
    if acwr is None:
        acwr = calc_and_save_acwr(conn, target_date)

    # Monotony (없으면 계산)
    monotony = get_monotony(conn, target_date)
    if monotony is None:
        result = calc_and_save_monotony(conn, target_date)
        monotony = result["monotony"] if result else None

    lsi_weekly = _get_weekly_lsi(conn, target_date)
    asym_pct = _get_gct_asymmetry(conn, target_date)

    result = calc_cirs(acwr, monotony, lsi_weekly, asym_pct)

    save_metric(
        conn,
        date=target_date,
        metric_name="CIRS",
        value=result["cirs"],
        extra_json=result,
    )
    return result["cirs"]
