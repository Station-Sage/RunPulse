"""날짜 기반 계획 ↔ 실제 활동 자동 매칭 + session_outcomes 저장.

매칭 후 session_outcomes 테이블에 성과 기록:
  - 계획 vs 실제 거리/페이스/심박 비교
  - 훈련 당시 CRS/TSB/HRV/BB 스냅샷 (ML 피처)
  - outcome_label 자동 분류

outcome_label 분류 기준:
  - 'on_target':      dist_ratio 0.90~1.10, pace_delta_pct ±5%
  - 'overperformed':  dist_ratio > 1.10 또는 pace_delta_pct < -5% (더 빠름)
  - 'underperformed': dist_ratio < 0.90 또는 pace_delta_pct > +5% (더 느림)
  - 'skipped':        completed = -1
  - 'modified':       타입 변경 등 기타
"""
from __future__ import annotations

import logging
import sqlite3
from datetime import date, timedelta

log = logging.getLogger(__name__)

_RUN_TYPES = (
    "('running','run','virtualrun','treadmill','highintensityintervaltraining')"
)


# ── 활동 매칭 ─────────────────────────────────────────────────────────────

def match_week_activities(
    conn: sqlite3.Connection,
    week_start: date,
) -> int:
    """한 주 계획↔활동 매칭 후 completed/matched_activity_id 업데이트.

    매칭 성공 시 session_outcomes 저장도 함께 수행.

    Returns:
        매칭된 워크아웃 수.
    """
    week_end = week_start + timedelta(days=6)

    plans = conn.execute(
        "SELECT id, date, workout_type, distance_km, target_pace_min, target_pace_max, "
        "target_hr_zone FROM planned_workouts "
        "WHERE date BETWEEN ? AND ? AND workout_type != 'rest' AND completed != 1",
        (week_start.isoformat(), week_end.isoformat()),
    ).fetchall()

    if not plans:
        return 0

    acts = conn.execute(
        f"SELECT id, DATE(start_time) as d, distance_km, avg_pace_sec_km, avg_hr, "
        f"duration_sec, activity_type "
        f"FROM v_canonical_activities "
        f"WHERE activity_type IN {_RUN_TYPES} "
        f"AND DATE(start_time) BETWEEN ? AND ?",
        (week_start.isoformat(), week_end.isoformat()),
    ).fetchall()

    acts_by_date: dict[str, list[tuple]] = {}
    for a in acts:
        acts_by_date.setdefault(a[1], []).append(a)

    matched = 0
    for plan_row in plans:
        plan_id, plan_date, plan_type, plan_dist, pace_min, pace_max, hr_zone = plan_row
        day_acts = acts_by_date.get(plan_date, [])
        if not day_acts:
            continue

        best = (
            min(day_acts, key=lambda a: abs((a[2] or 0) - plan_dist))
            if plan_dist else day_acts[0]
        )

        if best:
            conn.execute(
                "UPDATE planned_workouts SET completed=1, matched_activity_id=?, "
                "updated_at=datetime('now') WHERE id=? AND completed != 1",
                (best[0], plan_id),
            )
            # session_outcomes 저장
            _save_session_outcome(
                conn, plan_id=plan_id, activity_id=best[0], plan_date=plan_date,
                plan_dist=plan_dist, plan_pace=pace_min, plan_hr_zone=hr_zone,
                act_row=best,
            )
            matched += 1

    if matched:
        conn.commit()
    return matched


# ── session_outcomes 저장 ─────────────────────────────────────────────────

def _save_session_outcome(
    conn: sqlite3.Connection,
    plan_id: int,
    activity_id: int,
    plan_date: str,
    plan_dist: float | None,
    plan_pace: int | None,
    plan_hr_zone: int | None,
    act_row: tuple,
) -> None:
    """session_outcomes 레코드 생성.

    Args:
        act_row: (id, date, distance_km, avg_pace_sec_km, avg_hr, duration_sec, type)
    """
    act_id, _, act_dist, act_pace, act_hr, _, _ = act_row

    # 달성률 (Buchheit & Laursen 2013: 세션 볼륨 대비)
    dist_ratio = (act_dist / plan_dist) if (plan_dist and act_dist) else None

    # 페이스 편차 (Daniels 처방 대비)
    pace_delta_pct = None
    if plan_pace and act_pace:
        pace_delta_pct = round((act_pace - plan_pace) / plan_pace * 100, 2)

    # HR zone 분포 (activity_streams에서 조회, 없으면 None)
    hr_z1, hr_z2, hr_z3, hr_delta = _get_hr_zone_dist(
        conn, activity_id, act_hr, plan_hr_zone
    )

    # AerobicDecoupling (Friel 5% 기준)
    dec_row = conn.execute(
        "SELECT metric_value FROM computed_metrics "
        "WHERE metric_name='AerobicDecoupling' AND activity_id=? LIMIT 1",
        (activity_id,),
    ).fetchone()
    decoupling = float(dec_row[0]) if dec_row else None

    # TRIMP
    trimp_row = conn.execute(
        "SELECT metric_value FROM computed_metrics "
        "WHERE metric_name='TRIMP' AND activity_id=? LIMIT 1",
        (activity_id,),
    ).fetchone()
    trimp = float(trimp_row[0]) if trimp_row else None

    # 컨디션 스냅샷 (훈련 당일 기준)
    crs_snap, tsb_snap, hrv_snap, bb_snap, acwr_snap = _get_condition_snapshot(
        conn, plan_date
    )

    # outcome_label 분류
    label = _classify_outcome(dist_ratio, pace_delta_pct)

    # 기존 레코드 있으면 업데이트, 없으면 삽입
    conn.execute(
        """INSERT INTO session_outcomes
           (planned_id, activity_id, date,
            planned_dist_km, actual_dist_km, dist_ratio,
            planned_pace, actual_pace, pace_delta_pct,
            hr_z1_pct, hr_z2_pct, hr_z3_pct,
            target_zone, actual_avg_hr, hr_delta,
            decoupling_pct, trimp,
            crs_at_session, tsb_at_session, hrv_at_session,
            bb_at_session, acwr_at_session, outcome_label)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
           ON CONFLICT(planned_id) DO UPDATE SET
               activity_id=excluded.activity_id,
               actual_dist_km=excluded.actual_dist_km,
               dist_ratio=excluded.dist_ratio,
               actual_pace=excluded.actual_pace,
               pace_delta_pct=excluded.pace_delta_pct,
               hr_z1_pct=excluded.hr_z1_pct,
               hr_z2_pct=excluded.hr_z2_pct,
               hr_z3_pct=excluded.hr_z3_pct,
               actual_avg_hr=excluded.actual_avg_hr,
               hr_delta=excluded.hr_delta,
               decoupling_pct=excluded.decoupling_pct,
               trimp=excluded.trimp,
               outcome_label=excluded.outcome_label,
               computed_at=datetime('now')""",
        (
            plan_id, activity_id, plan_date,
            plan_dist, act_dist, dist_ratio,
            plan_pace, act_pace, pace_delta_pct,
            hr_z1, hr_z2, hr_z3,
            plan_hr_zone, act_hr, hr_delta,
            decoupling, trimp,
            crs_snap, tsb_snap, hrv_snap, bb_snap, acwr_snap,
            label,
        ),
    )


def _get_hr_zone_dist(
    conn: sqlite3.Connection,
    activity_id: int,
    avg_hr: int | None,
    plan_hr_zone: int | None,
) -> tuple[float | None, float | None, float | None, int | None]:
    """HR zone 분포 + hr_delta 계산.

    Seiler 2010 3존 기준:
    - Z1 (저강도): < VT1
    - Z2 (중간): VT1~VT2
    - Z3 (고강도): > VT2

    HR zone 경계는 computed_metrics 또는 maxHR 기반 추정.
    """
    hr_delta = None
    # plan HR zone → 대표 HR 역산 (zone * 10 + 기준 근사)
    zone_hr_approx = {1: 120, 2: 140, 3: 155, 4: 168, 5: 180}
    if plan_hr_zone and avg_hr:
        target_hr = zone_hr_approx.get(plan_hr_zone, 140)
        hr_delta = int(avg_hr) - target_hr

    # activity_streams에서 HR 데이터 조회 (있을 경우만)
    try:
        rows = conn.execute(
            "SELECT heart_rate FROM activity_streams "
            "WHERE activity_id=? AND source='garmin' AND heart_rate IS NOT NULL",
            (activity_id,),
        ).fetchall()
        if not rows:
            return None, None, None, hr_delta

        # maxHR 조회 (Zone 경계 계산용)
        max_hr_row = conn.execute(
            "SELECT metric_value FROM computed_metrics "
            "WHERE metric_name='maxHR' ORDER BY date DESC LIMIT 1"
        ).fetchone()
        max_hr = float(max_hr_row[0]) if max_hr_row else 185.0

        # Seiler 2010: VT1 ≈ 77% HRmax, VT2 ≈ 92% HRmax
        vt1 = max_hr * 0.77
        vt2 = max_hr * 0.92

        hrs = [r[0] for r in rows if r[0]]
        total = len(hrs)
        if total == 0:
            return None, None, None, hr_delta

        z1 = sum(1 for h in hrs if h < vt1) / total * 100
        z2 = sum(1 for h in hrs if vt1 <= h < vt2) / total * 100
        z3 = sum(1 for h in hrs if h >= vt2) / total * 100
        return round(z1, 1), round(z2, 1), round(z3, 1), hr_delta
    except Exception:
        return None, None, None, hr_delta


def _get_condition_snapshot(
    conn: sqlite3.Connection,
    target_date: str,
) -> tuple[float | None, float | None, float | None, int | None, float | None]:
    """훈련 당일 컨디션 스냅샷 (CRS, TSB, HRV, BB, ACWR)."""
    # CRS
    try:
        from src.metrics.crs import evaluate as crs_eval
        crs_result = crs_eval(conn, target_date)
        crs = crs_result.get("crs")
    except Exception:
        crs = None

    # TSB
    tsb_row = conn.execute(
        "SELECT tsb FROM daily_fitness WHERE date<=? AND tsb IS NOT NULL "
        "ORDER BY date DESC LIMIT 1", (target_date,)
    ).fetchone()
    tsb = float(tsb_row[0]) if tsb_row else None

    # HRV
    hrv_row = conn.execute(
        "SELECT hrv_value FROM daily_wellness WHERE date=? AND hrv_value IS NOT NULL "
        "LIMIT 1", (target_date,)
    ).fetchone()
    hrv = float(hrv_row[0]) if hrv_row else None

    # Body Battery
    bb_row = conn.execute(
        "SELECT body_battery FROM daily_wellness WHERE date=? AND body_battery IS NOT NULL "
        "LIMIT 1", (target_date,)
    ).fetchone()
    bb = int(bb_row[0]) if bb_row else None

    # ACWR
    acwr_row = conn.execute(
        "SELECT metric_value FROM computed_metrics "
        "WHERE metric_name='ACWR' AND date<=? AND metric_value IS NOT NULL "
        "ORDER BY date DESC LIMIT 1", (target_date,)
    ).fetchone()
    acwr = float(acwr_row[0]) if acwr_row else None

    return crs, tsb, hrv, bb, acwr


def _classify_outcome(
    dist_ratio: float | None,
    pace_delta_pct: float | None,
) -> str:
    """outcome_label 자동 분류."""
    if dist_ratio is None:
        return "modified"
    if dist_ratio < 0.50:
        return "skipped"
    if dist_ratio > 1.10 or (pace_delta_pct is not None and pace_delta_pct < -5.0):
        return "overperformed"
    if dist_ratio < 0.85 or (pace_delta_pct is not None and pace_delta_pct > 5.0):
        return "underperformed"
    return "on_target"


def save_skipped_outcome(
    conn: sqlite3.Connection,
    plan_id: int,
    plan_date: str,
    plan_dist: float | None,
) -> None:
    """건너뜀 시 session_outcomes에 'skipped' 레코드 저장."""
    crs, tsb, hrv, bb, acwr = _get_condition_snapshot(conn, plan_date)
    conn.execute(
        """INSERT INTO session_outcomes
           (planned_id, activity_id, date, planned_dist_km,
            crs_at_session, tsb_at_session, hrv_at_session,
            bb_at_session, acwr_at_session, outcome_label)
           VALUES (?,NULL,?,?,?,?,?,?,?,'skipped')
           ON CONFLICT(planned_id) DO UPDATE SET
               outcome_label='skipped', computed_at=datetime('now')""",
        (plan_id, plan_date, plan_dist, crs, tsb, hrv, bb, acwr),
    )
    conn.commit()


# ── 주간 실제 활동 조회 ───────────────────────────────────────────────────

def get_actual_activities_for_week(
    conn: sqlite3.Connection,
    week_start: date,
) -> dict[str, dict]:
    """주간 날짜별 실제 활동 딕셔너리.

    Returns:
        {"2026-03-25": {"id": 123, "km": 10.5, "pace": 305, "hr": 148}, ...}
    """
    week_end = week_start + timedelta(days=6)
    rows = conn.execute(
        f"SELECT id, DATE(start_time) as d, distance_km, avg_pace_sec_km, avg_hr, "
        f"duration_sec, activity_type "
        f"FROM v_canonical_activities "
        f"WHERE activity_type IN {_RUN_TYPES} "
        f"AND DATE(start_time) BETWEEN ? AND ? "
        f"ORDER BY start_time",
        (week_start.isoformat(), week_end.isoformat()),
    ).fetchall()

    result: dict[str, dict] = {}
    for r in rows:
        result[r[1]] = {
            "id": r[0], "km": r[2], "pace": r[3],
            "hr": r[4], "sec": r[5], "type": r[6],
        }
    return result
