"""레포트 섹션 — 데이터 로더.

views_report_sections.py에서 분리.
TIDS/TRIMP/Risk/ADTI/DARP/Fitness 데이터 조회.
"""
from __future__ import annotations

import json
import sqlite3


def _load_tids_data(conn: sqlite3.Connection, start: str, end: str) -> dict | None:
    """기간 내 최신 TIDS metric_json 조회."""
    row = conn.execute(
        """SELECT metric_json FROM computed_metrics
           WHERE metric_name = 'TIDS' AND activity_id IS NULL AND date BETWEEN ? AND ?
           ORDER BY date DESC LIMIT 1""",
        (start, end),
    ).fetchone()
    if row and row[0]:
        try:
            return json.loads(row[0])
        except Exception:
            return None
    return None


def _load_trimp_weekly(conn: sqlite3.Connection, start: str, end: str) -> list[dict]:
    """주별 TRIMP 합계 (활동별 합산)."""
    rows = conn.execute(
        """SELECT strftime('%Y-%W', date) AS week, COALESCE(SUM(metric_value), 0) AS total
           FROM computed_metrics
           WHERE metric_name = 'TRIMP' AND activity_id IS NOT NULL AND date BETWEEN ? AND ?
           GROUP BY week ORDER BY week ASC""",
        (start, end),
    ).fetchall()
    return [{"week": r[0], "trimp": round(float(r[1]), 1)} for r in rows]


def _load_risk_overview(conn: sqlite3.Connection, start: str, end: str) -> dict:
    """기간 내 ACWR / LSI / Monotony / CIRS 평균 및 최고값."""
    rows = conn.execute(
        """SELECT metric_name, AVG(metric_value), MAX(metric_value)
           FROM computed_metrics
           WHERE metric_name IN ('ACWR', 'LSI', 'Monotony', 'CIRS')
             AND activity_id IS NULL AND date BETWEEN ? AND ?
           GROUP BY metric_name""",
        (start, end),
    ).fetchall()
    return {r[0]: {"avg": float(r[1]), "max": float(r[2])} for r in rows}


def _load_adti(conn: sqlite3.Connection, end: str) -> float | None:
    """최신 ADTI (유산소 분리 추세) 값 조회."""
    row = conn.execute(
        """SELECT metric_value FROM computed_metrics
           WHERE metric_name = 'ADTI' AND activity_id IS NULL AND date <= ?
           ORDER BY date DESC LIMIT 1""",
        (end,),
    ).fetchone()
    return float(row[0]) if row and row[0] is not None else None


def _load_darp_latest(conn: sqlite3.Connection, end: str) -> dict:
    """최신 DARP 거리별 예측값 조회."""
    result = {}
    for key in ("DARP_5k", "DARP_10k", "DARP_half", "DARP_full"):
        row = conn.execute(
            """SELECT metric_value, metric_json FROM computed_metrics
               WHERE metric_name = ? AND activity_id IS NULL AND date <= ?
               ORDER BY date DESC LIMIT 1""",
            (key, end),
        ).fetchone()
        if row and row[0] is not None:
            dist_key = key.split("_", 1)[1]
            try:
                mj = json.loads(row[1]) if row[1] else {}
            except Exception:
                mj = {}
            result[dist_key] = mj or {"pace_sec_km": float(row[0])}
    return result


def _load_fitness_data(conn: sqlite3.Connection, end: str) -> tuple[float | None, float | None]:
    """VDOT + Marathon Shape 최신값. computed_metrics 우선 → Runalyze → Garmin fallback."""
    vdot = None
    cm_row = conn.execute(
        "SELECT metric_value FROM computed_metrics WHERE metric_name='VDOT' "
        "AND metric_value IS NOT NULL AND date<=? ORDER BY date DESC LIMIT 1",
        (end,),
    ).fetchone()
    if cm_row and cm_row[0]:
        vdot = float(cm_row[0])
    else:
        vdot_row = conn.execute(
            "SELECT runalyze_vdot, garmin_vo2max FROM daily_fitness "
            "WHERE (runalyze_vdot IS NOT NULL OR garmin_vo2max IS NOT NULL) "
            "AND date<=? ORDER BY date DESC LIMIT 1",
            (end,),
        ).fetchone()
        if vdot_row:
            vdot = float(vdot_row[0]) if vdot_row[0] is not None else (
                float(vdot_row[1]) if vdot_row[1] is not None else None
            )
    shape_row = conn.execute(
        """SELECT metric_value FROM computed_metrics
           WHERE metric_name='MarathonShape' AND activity_id IS NULL AND date<=?
           ORDER BY date DESC LIMIT 1""",
        (end,),
    ).fetchone()
    return (vdot,
            float(shape_row[0]) if shape_row and shape_row[0] is not None else None)
