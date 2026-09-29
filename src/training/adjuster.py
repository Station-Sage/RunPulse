"""컨디션 기반 당일 훈련 계획 조정.

wellness·TSB 조회, 피로도 판정은 src.training.fatigue로 통합됐다(같은 날 Today
브리핑과 다른 판정을 내리던 문제 제거, [[readiness_decision]]). 이 모듈은 그 판정을
가져다 실제 계획(운동 종류) 다운그레이드에만 쓴다 — 동작은 통합 전과 동일.
"""

import sqlite3
from datetime import date as _date

from src.training.fatigue import fatigue_level as _fatigue_level
from src.training.fatigue import get_latest_tsb as _get_latest_tsb
from src.training.fatigue import get_todays_wellness as _get_todays_wellness

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


def adjust_todays_plan(
    conn: sqlite3.Connection,
    config: dict | None = None,
    date: str | None = None,
) -> dict | None:
    """지정 날짜(기본 오늘)의 계획된 운동을 컨디션 기반으로 조정.

    Args:
        conn: SQLite 연결.
        config: 설정 딕셔너리 (현재 미사용, 확장용).
        date: 조회 날짜 (ISO 문자열). None이면 오늘.

    Returns:
        조정된 workout dict.
        추가 필드: original_type, adjusted_type, adjusted, adjustment_reason,
                   adjustment_reason_parts, fatigue_level, volume_boost, wellness, tsb.
        해당 날짜 계획이 없거나 이미 실행 완료면 None.
    """
    target = date or _date.today().isoformat()
    row = conn.execute(
        """SELECT id, date, workout_type, distance_km, target_pace_min, target_pace_max,
                  target_hr_zone, description, rationale
           FROM planned_workouts p
           WHERE p.date = ? AND p.completed = 0
             AND NOT EXISTS (SELECT 1 FROM planned_workouts o WHERE o.date = p.date
                             AND o.completed = 1 AND o.matched_activity_id IS NOT NULL)
           ORDER BY p.id DESC LIMIT 1""",
        (target,),
    ).fetchone()      # 이미 실행한(다른 계획이 활동을 가져간) 날은 조정 대상이 아니다

    if not row:
        return None

    keys = ["id", "date", "workout_type", "distance_km", "target_pace_min",
            "target_pace_max", "target_hr_zone", "description", "rationale"]
    workout = dict(zip(keys, row))

    wellness = _get_todays_wellness(conn, date=date)
    tsb = _get_latest_tsb(conn, date=date)
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

    reason_parts: list[str] = []
    if fatigue == "high":
        adjusted_type = _DOWNGRADE_HIGH.get(original_type, original_type)
        reason_parts = _reason_parts()
        adjustment_reason = "피로도 높음" + (": " + ", ".join(reason_parts) if reason_parts else "")
    elif fatigue == "moderate":
        adjusted_type = _DOWNGRADE_MOD.get(original_type, original_type)
        reason_parts = _reason_parts()
        adjustment_reason = "중간 피로" + (": " + ", ".join(reason_parts) if reason_parts else "")

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
        "adjustment_reason_parts": reason_parts,
        "fatigue_level": fatigue,
        "volume_boost": volume_boost,
        "wellness": wellness,
        "tsb": tsb,
    })
    return workout
