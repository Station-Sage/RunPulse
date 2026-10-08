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

from src.training.matcher_context import _classified_kinds, _get_condition_snapshot, _get_hr_zone_dist, canonical_activity_id
from src.training.match_select import classify_outcome, is_done, pick_activity
from src.training.outcome_store import update_outcome_v2

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
        "WHERE date BETWEEN ? AND ? AND workout_type != 'rest' AND completed != 1 "
        "ORDER BY (COALESCE(source_system, source) IN ('planner', 'runpulse')), date",
        (week_start.isoformat(), week_end.isoformat()),
    ).fetchall()

    if not plans:
        return 0

    # 수락된 조정은 유형·거리 게이트에 반영(쓰기는 원본 행). rest 로 조정된 날은 매칭 제외
    from src.training.plan_overlay import apply, live_adjustments
    keys = ("id", "date", "workout_type", "distance_km", "target_pace_min", "target_pace_max", "target_hr_zone")
    adjs = live_adjustments(conn, week_start.isoformat(), (week_end + timedelta(days=1)).isoformat())
    plans = [tuple(d[k] for k in keys) for d in apply([dict(zip(keys, p)) for p in plans], adjs)
             if d["workout_type"] != "rest"]
    if not plans:
        return 0

    acts = conn.execute(
        f"SELECT id, DATE(start_time) as d, distance_m / 1000.0 AS distance_km, avg_pace_sec_km, avg_hr, "
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

        # 다른 계획(명시 연결 포함)이 이미 가져간 활동은 제외
        claimed = {canonical_activity_id(conn, r[0]) for r in conn.execute(
            "SELECT matched_activity_id FROM planned_workouts WHERE id != ? AND date = ? "
            "AND matched_activity_id IS NOT NULL", (plan_id, plan_date))}
        claimed |= {canonical_activity_id(conn, r[0]) for r in conn.execute(
            "SELECT activity_id FROM session_outcomes WHERE planned_id != ? AND date = ? "
            "AND activity_id IS NOT NULL", (plan_id, plan_date))}
        kinds = _classified_kinds(conn, [a[0] for a in day_acts])
        best = pick_activity(plan_dist, day_acts, claimed, plan_type, kinds)

        if best:
            # session_outcomes 저장(거리·페이스 기본 → 구조가 있으면 세트·구간 페이스까지 v2 로 덧씀)
            _save_session_outcome(
                conn, plan_id=plan_id, activity_id=best[0], plan_date=plan_date,
                plan_dist=plan_dist, plan_pace=pace_min, plan_hr_zone=hr_zone,
                act_row=best,
            )
            res = update_outcome_v2(conn, plan_id, best[0])      # 구조화된 계획이면 세트·구간 페이스 이행률(P7-PRED-43)
            # 완료 = 처방한 볼륨(거리/시간)과 세트 수의 75% 이상을 했다. 구조 분석이 없으면 거리로만 본다.
            done = (res["label"] != "skipped" and (res.get("volume_ratio") or 0) >= 0.75
                    and (not res.get("sets_planned") or res["sets_done"] / res["sets_planned"] >= 0.75)) if res \
                else is_done(plan_dist, best[2])
            conn.execute(
                "UPDATE planned_workouts SET completed=?, matched_activity_id=?, "
                "updated_at=datetime('now') WHERE id=? AND completed != 1",
                (1 if done else 0, best[0], plan_id),
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
        "SELECT numeric_value FROM metric_store"
        " WHERE metric_name='aerobic_decoupling_rp' AND scope_type='activity'"
        "   AND scope_id=CAST(? AS TEXT) LIMIT 1",
        (activity_id,),
    ).fetchone()
    decoupling = float(dec_row[0]) if dec_row else None

    # TRIMP
    trimp_row = conn.execute(
        "SELECT numeric_value FROM metric_store"
        " WHERE metric_name='trimp' AND scope_type='activity'"
        "   AND scope_id=CAST(? AS TEXT) LIMIT 1",
        (activity_id,),
    ).fetchone()
    trimp = float(trimp_row[0]) if trimp_row else None

    # 컨디션 스냅샷 (훈련 당일 기준)
    crs_snap, tsb_snap, hrv_snap, bb_snap, acwr_snap = _get_condition_snapshot(
        conn, plan_date
    )

    # outcome_label 분류
    label = classify_outcome(dist_ratio, pace_delta_pct)

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
        f"SELECT id, DATE(start_time) as d, distance_m / 1000.0 AS distance_km, avg_pace_sec_km, avg_hr, "
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
