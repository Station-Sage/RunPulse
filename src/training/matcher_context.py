"""세션 결과 컨텍스트 — 활동 HR 존 분포·훈련 당일 컨디션 스냅샷(matcher.py 에서 분리)."""
from __future__ import annotations

import sqlite3


def canonical_activity_id(conn: sqlite3.Connection, activity_id: int) -> int:
    """활동 id → 같은 그룹의 현재 canonical 활동 id. 그룹이 재편돼 저장된 id 가 낡아도 같은 활동으로 취급한다."""
    row = conn.execute(
        "SELECT c.id FROM activity_summaries a JOIN v_canonical_activities c "
        "  ON COALESCE(c.matched_group_id, 'solo_'||c.id) = COALESCE(a.matched_group_id, 'solo_'||a.id) "
        "WHERE a.id=? LIMIT 1", (activity_id,)).fetchone()
    return row[0] if row else activity_id


def _classified_kinds(conn: sqlite3.Connection, activity_ids: list[int]) -> dict[int, str]:
    """활동 id → 세션 분류(workout_type_classified). 분류 없는 활동은 빠진다."""
    if not activity_ids:
        return {}
    q = ",".join("?" for _ in activity_ids)
    rows = conn.execute(
        "SELECT scope_id, text_value FROM metric_store WHERE scope_type='activity' AND metric_name='workout_type_classified' "
        f"AND is_primary=1 AND scope_id IN ({q})", [str(i) for i in activity_ids]).fetchall()
    return {int(r[0]): r[1] for r in rows if r[1]}


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
            "SELECT numeric_value FROM metric_store"
            " WHERE metric_name='maxHR' AND scope_type='daily' AND is_primary=1"
            "   AND numeric_value IS NOT NULL ORDER BY scope_id DESC LIMIT 1"
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
        "SELECT numeric_value FROM metric_store"
        " WHERE metric_name='tsb' AND scope_type='daily' AND is_primary=1"
        "   AND scope_id<=? AND numeric_value IS NOT NULL ORDER BY scope_id DESC LIMIT 1",
        (target_date,)
    ).fetchone()
    tsb = float(tsb_row[0]) if tsb_row else None

    # HRV
    hrv_row = conn.execute(
        "SELECT hrv_last_night FROM daily_wellness WHERE date=? AND hrv_last_night IS NOT NULL "
        "LIMIT 1", (target_date,)
    ).fetchone()
    hrv = float(hrv_row[0]) if hrv_row else None

    # Body Battery
    bb_row = conn.execute(
        "SELECT body_battery_high FROM daily_wellness WHERE date=? AND body_battery_high IS NOT NULL "
        "LIMIT 1", (target_date,)
    ).fetchone()
    bb = int(bb_row[0]) if bb_row else None

    # ACWR
    acwr_row = conn.execute(
        "SELECT numeric_value FROM metric_store"
        " WHERE metric_name='acwr' AND scope_type='daily' AND is_primary=1"
        "   AND scope_id<=? AND numeric_value IS NOT NULL ORDER BY scope_id DESC LIMIT 1",
        (target_date,)
    ).fetchone()
    acwr = float(acwr_row[0]) if acwr_row else None

    return crs, tsb, hrv, bb, acwr
