"""REC (Running Efficiency Composite) — 통합 러닝 효율성 지수.

공식: REC = EF × (1 - Decoupling/100) × pace_factor × form_factor
- EF: 효율 계수 (speed/hr)
- Decoupling: 심박-페이스 분리율 (낮을수록 좋음)
- pace_factor: 현재 eFTP 대비 페이스 효율 (1.0 = 역치 수준)
- form_factor: GCT/수직비율 기반 폼 보정 (선택, 없으면 1.0)

0~100 스케일 정규화. 높을수록 효율적.
저장: computed_metrics (date, 'REC', value, extra_json)
"""
from __future__ import annotations

import sqlite3
from datetime import date, timedelta

from src.metrics.store import save_metric


def _get_latest(conn: sqlite3.Connection, target_date: str, metric_name: str,
                activity_based: bool = False) -> float | None:
    """최근 메트릭 값 조회."""
    if activity_based:
        row = conn.execute(
            "SELECT metric_value FROM computed_metrics WHERE metric_name=? "
            "AND activity_id IS NOT NULL AND date<=? AND metric_value IS NOT NULL "
            "ORDER BY date DESC LIMIT 1",
            (metric_name, target_date),
        ).fetchone()
    else:
        row = conn.execute(
            "SELECT metric_value FROM computed_metrics WHERE metric_name=? "
            "AND activity_id IS NULL AND date<=? AND metric_value IS NOT NULL "
            "ORDER BY date DESC LIMIT 1",
            (metric_name, target_date),
        ).fetchone()
    return float(row[0]) if row and row[0] is not None else None


def calc_rec(ef: float, decoupling: float, pace_ratio: float = 1.0,
             form_factor: float = 1.0) -> float:
    """REC 계산 (순수 함수).

    Returns:
        0~100 정규화된 효율성 점수.
    """
    # Decoupling 보정 (0~20% 범위 → 1.0~0.8 계수)
    dec_factor = max(0.5, 1.0 - decoupling / 100)
    raw = ef * dec_factor * pace_ratio * form_factor
    # EF 일반 범위 1.0~2.0 → 0~100 매핑
    normalized = min(100, max(0, (raw - 0.8) / 1.2 * 100))
    return round(normalized, 1)


def calc_and_save_rec(conn: sqlite3.Connection, target_date: str) -> float | None:
    """REC 계산 후 저장.

    최근 7일 평균 EF/Decoupling 사용.

    Returns:
        REC 값 (0~100) 또는 None.
    """
    td = date.fromisoformat(target_date)
    start = (td - timedelta(days=7)).isoformat()

    # EF 최근 값들
    ef_rows = conn.execute(
        "SELECT metric_value FROM computed_metrics WHERE metric_name='EF' "
        "AND activity_id IS NOT NULL AND date BETWEEN ? AND ? AND metric_value IS NOT NULL",
        (start, target_date),
    ).fetchall()
    if not ef_rows:
        return None
    ef_avg = sum(r[0] for r in ef_rows) / len(ef_rows)

    # Decoupling 최근 값들
    dec_rows = conn.execute(
        "SELECT metric_value FROM computed_metrics WHERE metric_name='AerobicDecoupling' "
        "AND activity_id IS NOT NULL AND date BETWEEN ? AND ? AND metric_value IS NOT NULL",
        (start, target_date),
    ).fetchall()
    dec_avg = sum(r[0] for r in dec_rows) / len(dec_rows) if dec_rows else 5.0

    # 폼 팩터: GCT/수직비율 (있으면 보정)
    form_factor = 1.0
    gct_row = conn.execute(
        "SELECT AVG(m.metric_value) FROM activity_detail_metrics m "
        "JOIN activity_summaries a ON a.id=m.activity_id "
        "WHERE m.metric_name='avg_ground_contact_time_ms' "
        "AND a.start_time BETWEEN ? AND ?",
        (start, target_date + "T23:59:59"),
    ).fetchone()
    if gct_row and gct_row[0]:
        gct = float(gct_row[0])
        # GCT 220~280ms 범위 → 1.1~0.9 계수 (짧을수록 좋음)
        form_factor = max(0.8, min(1.2, 1.0 - (gct - 250) / 300))

    rec = calc_rec(ef_avg, dec_avg, form_factor=form_factor)
    save_metric(conn, target_date, "REC", rec, extra_json={
        "ef_avg": round(ef_avg, 4),
        "dec_avg": round(dec_avg, 1),
        "form_factor": round(form_factor, 3),
        "ef_count": len(ef_rows),
    })
    return rec
