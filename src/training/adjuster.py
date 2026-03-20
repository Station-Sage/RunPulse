"""컨디션 기반 당일 훈련 계획 조정."""

import sqlite3
from datetime import date


# 피로도 높음: interval/tempo → rest, long → easy
_DOWNGRADE_HIGH: dict[str, str] = {
    "interval": "rest", "tempo": "rest", "long": "easy",
    "easy": "easy", "rest": "rest",
}

# 피로도 중간: interval/tempo/long → easy
_DOWNGRADE_MOD: dict[str, str] = {
    "interval": "easy", "tempo": "easy", "long": "easy",
    "easy": "easy", "rest": "rest",
}


def _get_todays_wellness(conn: sqlite3.Connection) -> dict:
    """오늘 Garmin 웰니스 데이터 조회."""
    today = date.today().isoformat()
    row = conn.execute(
        "SELECT body_battery, sleep_score, sleep_hours, hrv_value, stress_avg "
        "FROM daily_wellness WHERE date = ? AND source = 'garmin'",
        (today,),
    ).fetchone()
    if row:
        return {
            "body_battery": row[0], "sleep_score": row[1],
            "sleep_hours": row[2], "hrv_value": row[3], "stress_avg": row[4],
        }
    return {}


def _get_latest_tsb(conn: sqlite3.Connection) -> float | None:
    """최근 TSB 조회."""
    row = conn.execute(
        "SELECT tsb FROM daily_fitness ORDER BY date DESC LIMIT 1"
    ).fetchone()
    return row[0] if row else None


def _fatigue_level(wellness: dict, tsb: float | None) -> str:
    """피로도 수준 판정.

    Returns:
        'high' | 'moderate' | 'low'
    """
    score = 0

    bb = wellness.get("body_battery")
    if bb is not None:
        if bb < 30:
            score += 2
        elif bb < 50:
            score += 1

    ss = wellness.get("sleep_score")
    if ss is not None:
        if ss < 40:
            score += 2
        elif ss < 60:
            score += 1

    stress = wellness.get("stress_avg")
    if stress is not None and stress > 75:
        score += 1

    if tsb is not None:
        if tsb < -25:
            score += 2
        elif tsb < -15:
            score += 1

    if score >= 4:
        return "high"
    if score >= 2:
        return "moderate"
    return "low"


def adjust_todays_plan(
    conn: sqlite3.Connection,
    config: dict | None = None,
) -> dict | None:
    """오늘 계획된 운동을 컨디션 기반으로 조정.

    Args:
        conn: SQLite 연결.
        config: 설정 딕셔너리 (현재 미사용, 확장용).

    Returns:
        조정된 workout dict.
        추가 필드: original_type, adjusted_type, adjusted, adjustment_reason,
                   fatigue_level, volume_boost, wellness, tsb.
        오늘 계획 없으면 None.
    """
    today = date.today().isoformat()
    row = conn.execute(
        """SELECT id, date, workout_type, distance_km, target_pace_min, target_pace_max,
                  target_hr_zone, description, rationale
           FROM planned_workouts
           WHERE date = ?
           ORDER BY id DESC LIMIT 1""",
        (today,),
    ).fetchone()

    if not row:
        return None

    keys = ["id", "date", "workout_type", "distance_km", "target_pace_min",
            "target_pace_max", "target_hr_zone", "description", "rationale"]
    workout = dict(zip(keys, row))

    wellness = _get_todays_wellness(conn)
    tsb = _get_latest_tsb(conn)
    fatigue = _fatigue_level(wellness, tsb)

    original_type = workout["workout_type"]
    adjusted_type = original_type
    adjustment_reason = None
    adjusted = False

    def _reason_parts() -> list[str]:
        parts = []
        bb = wellness.get("body_battery")
        ss = wellness.get("sleep_score")
        if bb is not None and bb < 50:
            parts.append(f"Body Battery {bb}")
        if ss is not None and ss < 60:
            parts.append(f"수면 점수 {ss}")
        if tsb is not None and tsb < -15:
            parts.append(f"TSB {tsb:.1f}")
        return parts

    if fatigue == "high":
        adjusted_type = _DOWNGRADE_HIGH.get(original_type, original_type)
        parts = _reason_parts()
        adjustment_reason = "피로도 높음" + (": " + ", ".join(parts) if parts else "")
    elif fatigue == "moderate":
        adjusted_type = _DOWNGRADE_MOD.get(original_type, original_type)
        parts = _reason_parts()
        adjustment_reason = "중간 피로" + (": " + ", ".join(parts) if parts else "")

    if adjusted_type != original_type:
        adjusted = True

    # 컨디션 양호: TSB > 10 + body_battery > 70 → 볼륨 소폭 추가 가능
    bb = wellness.get("body_battery")
    volume_boost = (
        tsb is not None and tsb > 10
        and bb is not None and bb > 70
        and original_type not in ("rest",)
    )

    workout.update({
        "original_type": original_type,
        "adjusted_type": adjusted_type,
        "adjusted": adjusted,
        "adjustment_reason": adjustment_reason,
        "fatigue_level": fatigue,
        "volume_boost": volume_boost,
        "wellness": wellness,
        "tsb": tsb,
    })
    return workout
