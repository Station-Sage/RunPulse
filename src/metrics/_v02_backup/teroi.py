"""TEROI (Training Effect Return On Investment) — 훈련 효과 투자 수익률.

공식: TEROI = (CTL 변화량 / 기간 총 TRIMP) × 1000
- CTL 변화량: 기간 말 CTL - 기간 초 CTL (피트니스 향상)
- 총 TRIMP: 기간 동안 투입한 총 훈련 부하
- ×1000 스케일링 (읽기 편하게)

높을수록 적은 훈련으로 큰 효과. 음수면 피트니스 하락.
28일 단위로 계산.
저장: computed_metrics (date, 'TEROI', value, extra_json)
"""
from __future__ import annotations

import sqlite3
from datetime import date, timedelta

from src.metrics.store import save_metric


def calc_teroi(ctl_start: float, ctl_end: float, total_trimp: float) -> float | None:
    """TEROI 계산 (순수 함수).

    Returns:
        TEROI 값 또는 None (TRIMP 없을 때).
    """
    if total_trimp <= 0:
        return None
    ctl_delta = ctl_end - ctl_start
    return round(ctl_delta / total_trimp * 1000, 2)


def calc_and_save_teroi(conn: sqlite3.Connection, target_date: str,
                        period_days: int = 28) -> float | None:
    """TEROI 계산 후 저장.

    Args:
        conn: SQLite 커넥션.
        target_date: 기준 날짜 (기간 끝).
        period_days: 평가 기간 (기본 28일).

    Returns:
        TEROI 값 또는 None.
    """
    td = date.fromisoformat(target_date)
    start = (td - timedelta(days=period_days)).isoformat()

    # CTL 시작/끝
    ctl_start_row = conn.execute(
        "SELECT ctl FROM daily_fitness WHERE date>=? AND ctl IS NOT NULL ORDER BY date ASC LIMIT 1",
        (start,),
    ).fetchone()
    ctl_end_row = conn.execute(
        "SELECT ctl FROM daily_fitness WHERE date<=? AND ctl IS NOT NULL ORDER BY date DESC LIMIT 1",
        (target_date,),
    ).fetchone()
    if not ctl_start_row or not ctl_end_row:
        return None
    ctl_start = float(ctl_start_row[0])
    ctl_end = float(ctl_end_row[0])

    # 기간 총 TRIMP
    trimp_row = conn.execute(
        "SELECT COALESCE(SUM(metric_value), 0) FROM computed_metrics "
        "WHERE metric_name='DailyTRIMP' AND activity_id IS NULL "
        "AND date BETWEEN ? AND ?",
        (start, target_date),
    ).fetchone()
    total_trimp = float(trimp_row[0]) if trimp_row else 0.0

    teroi = calc_teroi(ctl_start, ctl_end, total_trimp)
    if teroi is None:
        return None

    save_metric(conn, target_date, "TEROI", teroi, extra_json={
        "ctl_start": round(ctl_start, 1),
        "ctl_end": round(ctl_end, 1),
        "ctl_delta": round(ctl_end - ctl_start, 1),
        "total_trimp": round(total_trimp, 0),
        "period_days": period_days,
    })
    return teroi
