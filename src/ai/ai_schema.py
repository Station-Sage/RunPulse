"""AI 훈련 계획 JSON 스키마 정의 및 검증."""
from __future__ import annotations

from datetime import date

VALID_TYPES = {"rest", "easy", "tempo", "interval", "long"}


def _safe_float(v) -> float | None:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _safe_int(v) -> int | None:
    if v is None:
        return None
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _validate_workout(w: dict, idx: int) -> list[str]:
    """개별 워크아웃 dict 유효성 검사.

    Returns:
        오류 메시지 리스트 (비어있으면 유효).
    """
    errors: list[str] = []
    prefix = f"workouts[{idx}]"

    # 날짜
    d = w.get("date")
    if not d:
        errors.append(f"{prefix}.date 누락")
    else:
        try:
            date.fromisoformat(str(d))
        except ValueError:
            errors.append(f"{prefix}.date 형식 오류: '{d}'")

    # 훈련 유형
    wtype = w.get("type") or w.get("workout_type")
    if wtype not in VALID_TYPES:
        errors.append(
            f"{prefix}.type 유효하지 않음: '{wtype}'. 허용값: {sorted(VALID_TYPES)}"
        )

    # 거리 (rest 제외)
    if wtype != "rest":
        dist = w.get("distance_km")
        if dist is not None:
            try:
                d_f = float(dist)
                if not (0 < d_f <= 100):
                    errors.append(f"{prefix}.distance_km 범위 오류: {d_f}")
            except (TypeError, ValueError):
                errors.append(f"{prefix}.distance_km 숫자 아님: '{dist}'")

    return errors


def validate_weekly_plan(data: dict) -> tuple[bool, list[str]]:
    """주간 계획 dict 유효성 검사.

    Args:
        data: AI 응답에서 파싱된 dict.

    Returns:
        (is_valid, error_list) 튜플.
    """
    if not isinstance(data, dict):
        return False, ["데이터가 dict 형식이 아닙니다."]

    errors: list[str] = []

    ws = data.get("week_start")
    if ws:
        try:
            date.fromisoformat(str(ws))
        except ValueError:
            errors.append(f"week_start 형식 오류: '{ws}'")

    workouts = data.get("workouts")
    if not workouts:
        errors.append("workouts 배열이 없거나 비어있습니다.")
    elif not isinstance(workouts, list):
        errors.append("workouts가 배열 형식이 아닙니다.")
    else:
        if len(workouts) > 7:
            errors.append(f"workouts 항목이 7개 초과: {len(workouts)}")
        for i, w in enumerate(workouts):
            if isinstance(w, dict):
                errors.extend(_validate_workout(w, i))
            else:
                errors.append(f"workouts[{i}]가 dict 형식이 아닙니다.")

    return len(errors) == 0, errors


def normalize_workout(w: dict) -> dict:
    """워크아웃 dict를 planned_workouts 삽입 표준 형식으로 정규화.

    AI가 type / workout_type 등 다양한 키명을 쓰는 경우를 통일.
    """
    return {
        "date": str(w.get("date", "")),
        "workout_type": str(w.get("type") or w.get("workout_type") or "rest"),
        "distance_km": _safe_float(w.get("distance_km")),
        "target_pace_min": _safe_int(w.get("target_pace_min")),
        "target_pace_max": _safe_int(w.get("target_pace_max")),
        "target_hr_zone": _safe_int(w.get("target_hr_zone")),
        "description": str(w.get("description") or ""),
        "rationale": str(w.get("rationale") or ""),
        "source": "ai",
        "ai_model": str(w.get("ai_model") or ""),
    }
