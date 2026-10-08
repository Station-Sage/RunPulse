"""Story 기간 통계 조회 — 거리·CTL·강도 분포·위험 피크·핵심 세션 (story_service 하위 모듈)."""
from __future__ import annotations

import sqlite3
from typing import Any


def _get_period_activity_stats(
    conn: sqlite3.Connection,
    start_date: str,
    end_date: str,
) -> dict[str, Any]:
    """기간 내 러닝 활동 통계 — 거리, 횟수, 강도 분포, 대표 세션 등.

    v_canonical_activities만 집계(중복 제거됨).
    """
    row = conn.execute(
        """SELECT COUNT(*), COALESCE(SUM(distance_m), 0), COALESCE(MAX(distance_m), 0)
           FROM v_canonical_activities
           WHERE DATE(start_time) >= ? AND DATE(start_time) <= ?""",
        (start_date, end_date),
    ).fetchone()

    count = int(row[0]) if row else 0
    distance_m = float(row[1]) if row and row[1] else 0.0
    distance_km = round(distance_m / 1000.0, 1)
    longest_run_km = round(float(row[2]) / 1000.0, 1) if row and row[2] else 0.0

    return {
        "count": count,
        "distance_km": distance_km,
        "longest_run_km": longest_run_km,
    }


def _get_ctl_range(
    conn: sqlite3.Connection,
    start_date: str,
    end_date: str,
) -> dict[str, Any]:
    """CTL 시작값, 종료값, 최댓값."""
    row_start = conn.execute(
        "SELECT numeric_value FROM metric_store"
        " WHERE scope_type='daily' AND metric_name='ctl' AND is_primary=1"
        " AND scope_id >= ? ORDER BY scope_id LIMIT 1",
        (start_date,),
    ).fetchone()

    row_end = conn.execute(
        "SELECT numeric_value FROM metric_store"
        " WHERE scope_type='daily' AND metric_name='ctl' AND is_primary=1"
        " AND scope_id >= ? AND scope_id <= ? ORDER BY scope_id DESC LIMIT 1",
        (start_date, end_date),
    ).fetchone()

    row_max = conn.execute(
        "SELECT MAX(numeric_value) FROM metric_store"
        " WHERE scope_type='daily' AND metric_name='ctl' AND is_primary=1"
        " AND scope_id >= ? AND scope_id <= ?",
        (start_date, end_date),
    ).fetchone()

    ctl_start = float(row_start[0]) if row_start and row_start[0] is not None else None
    ctl_end = float(row_end[0]) if row_end and row_end[0] is not None else None
    ctl_peak = float(row_max[0]) if row_max and row_max[0] is not None else None

    return {
        "ctl_start": ctl_start,
        "ctl_end": ctl_end,
        "ctl_peak": ctl_peak,
    }


def _get_intensity_distribution(
    conn: sqlite3.Connection,
    start_date: str,
    end_date: str,
) -> dict[str, Any]:
    """HR 존별 시간 분포 — Z1-2, Z3, Z4-5 (활동별 존 시간 합산).

    존 데이터가 있는 활동이 전체 시간의 50% 미만이면 'insufficient'.
    """
    from src.services.activity_summary_extras import build_hr_zones

    acts = conn.execute(
        """SELECT id, COALESCE(duration_sec, 0) FROM v_canonical_activities
           WHERE DATE(start_time) >= ? AND DATE(start_time) <= ?""",
        (start_date, end_date),
    ).fetchall()
    total_sec = float(sum(d for _, d in acts))
    z12 = z3 = z45 = 0
    covered = 0.0
    for aid, dur in acts:
        zones = build_hr_zones(conn, [aid])
        if not zones or len(zones["sec"]) < 5 or sum(zones["sec"]) <= 0:
            continue
        sec = zones["sec"]
        z12 += sec[0] + sec[1]
        z3 += sec[2]
        z45 += sec[3] + sec[4]
        covered += dur
    zone_total = z12 + z3 + z45
    if total_sec < 1 or zone_total <= 0 or covered / total_sec < 0.5:
        return {"status": "insufficient", "z12_pct": 0, "z3_pct": 0, "z45_pct": 0}
    return {
        "status": "ok",
        "z12_pct": round(100 * z12 / zone_total),
        "z3_pct": round(100 * z3 / zone_total),
        "z45_pct": round(100 * z45 / zone_total),
        "coverage": round(100 * covered / total_sec),
    }


def _get_risk_peak(
    conn: sqlite3.Connection,
    start_date: str,
    end_date: str,
) -> dict[str, Any] | None:
    """위험도 최고 날 — ACWR 규칙 기반 (값만 아직 미구현, 설계에서 "규칙 최고 등급" 참고).

    Returns: {slug, value, date} 또는 None.
    """
    row = conn.execute(
        """SELECT numeric_value, scope_id FROM metric_store
           WHERE scope_type='daily' AND metric_name='acwr' AND is_primary=1
             AND scope_id >= ? AND scope_id <= ?
           ORDER BY numeric_value DESC LIMIT 1""",
        (start_date, end_date),
    ).fetchone()

    if not row or row[0] is None:
        return None

    acwr_value = float(row[0])
    acwr_date = row[1]

    return {
        "slug": "acwr",
        "value": round(acwr_value, 2),
        "date": acwr_date,
    }


def _get_key_sessions(
    conn: sqlite3.Connection,
    start_date: str,
    end_date: str,
    limit: int = 3,
) -> list[dict]:
    """대표 세션 3: 최장, 품질 최고(workout_label), 레이스.

    각 항목은 {id, name, date, distance_km, type, workout_label}.
    """
    sessions = []

    # 최장 러닝
    row_long = conn.execute(
        """SELECT id, name, DATE(start_time), distance_m, activity_type, workout_label
           FROM v_canonical_activities
           WHERE DATE(start_time) >= ? AND DATE(start_time) <= ?
           ORDER BY distance_m DESC LIMIT 1""",
        (start_date, end_date),
    ).fetchone()

    if row_long:
        sessions.append({
            "id": row_long[0],
            "name": row_long[1] or "",
            "date": row_long[2],
            "distance_km": round(float(row_long[3]) / 1000.0, 1),
            "type": row_long[4],
            "workout_label": row_long[5],
        })

    # 품질 최고 (workout_label != None, 정렬은 distance 역순)
    row_quality = conn.execute(
        """SELECT id, name, DATE(start_time), distance_m, activity_type, workout_label
           FROM v_canonical_activities
           WHERE DATE(start_time) >= ? AND DATE(start_time) <= ? AND workout_label IS NOT NULL
           ORDER BY distance_m DESC LIMIT 1""",
        (start_date, end_date),
    ).fetchone()

    if row_quality and (not row_long or row_quality[0] != row_long[0]):
        sessions.append({
            "id": row_quality[0],
            "name": row_quality[1] or "",
            "date": row_quality[2],
            "distance_km": round(float(row_quality[3]) / 1000.0, 1),
            "type": row_quality[4],
            "workout_label": row_quality[5],
        })

    # 레이스 (event_type='race')
    row_race = conn.execute(
        """SELECT id, name, DATE(start_time), distance_m, activity_type, workout_label
           FROM activity_summaries
           WHERE DATE(start_time) >= ? AND DATE(start_time) <= ? AND event_type='race'
           ORDER BY start_time DESC LIMIT 1""",
        (start_date, end_date),
    ).fetchone()

    if row_race and (not row_long or row_race[0] != row_long[0]):
        sessions.append({
            "id": row_race[0],
            "name": row_race[1] or "",
            "date": row_race[2],
            "distance_km": round(float(row_race[3]) / 1000.0, 1),
            "type": row_race[4],
            "workout_label": row_race[5],
        })

    return sessions[:limit]
