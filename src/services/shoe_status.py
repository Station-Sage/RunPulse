"""신발 교체 임계값·상태·문구 — 순수 함수(DB 없음). 설계 shoes.md §5.

상태 3단계: ok(<80%) · soon(80~99%) · replace(≥100%). 은퇴 신발은 'retired'(알림 제외).
"""
from __future__ import annotations

CATEGORIES = ("daily", "tempo", "race", "trail", "other")
CATEGORY_LABELS = {"daily": "데일리", "tempo": "템포·경량", "race": "레이스(카본)", "trail": "트레일", "other": "기타"}
DEFAULT_RETIRE_KM = {"daily": 700, "tempo": 600, "race": 400, "trail": 700, "other": 700}
WARN_RATIO = 0.8
RACE_PREP_DAYS = 21
STATUS_ORDER = {"replace": 0, "soon": 1, "ok": 2, "retired": 3}


def effective_retire_km(category: str | None, retire_km: int | None) -> int:
    """사용자 지정 `retire_km` 우선, 없으면 카테고리 기본값(미지 카테고리는 'other')."""
    if retire_km:
        return int(retire_km)
    return DEFAULT_RETIRE_KM.get(category or "other", DEFAULT_RETIRE_KM["other"])


def status_of(mileage_km: float, retire_km: int) -> str:
    ratio = mileage_km / retire_km if retire_km > 0 else 0.0
    if ratio >= 1.0:
        return "replace"
    if ratio >= WARN_RATIO:
        return "soon"
    return "ok"


def status_message(status: str, mileage_km: float, retire_km: int) -> str | None:
    """의미 문구(숫자는 괄호 보조). 은퇴 신발은 None."""
    if status == "ok":
        return "아직 충분해요"
    if status == "soon":
        return f"교체를 준비할 때예요 (남은 약 {max(0, round(retire_km - mileage_km))} km)"
    if status == "replace":
        return f"교체를 권해요 (임계값 +{max(0, round(mileage_km - retire_km))} km)"
    return None


def race_prep_note(category: str | None, status: str, days_to_race: int | None) -> str | None:
    """활성 목표 대회가 21일 이내이고 레이스화가 soon 이상이면 길들이기 보조 문구."""
    if category != "race" or status not in ("soon", "replace") or days_to_race is None:
        return None
    if 0 <= days_to_race <= RACE_PREP_DAYS:
        return "대회 전 새 레이스화 길들이기(최소 2~3회 주행) 시간을 확보하세요"
    return None


def shoe_state(category: str | None, retire_km: int | None, retired_at: str | None,
               mileage_km: float, days_to_race: int | None = None) -> dict:
    """카드·상세 공통 계산값: retire_km(유효값)·status·remaining_km·message·note."""
    limit = effective_retire_km(category, retire_km)
    if retired_at:
        return {"retire_km": limit, "status": "retired", "remaining_km": None, "message": None, "note": None}
    st = status_of(mileage_km, limit)
    return {
        "retire_km": limit,
        "status": st,
        "remaining_km": round(limit - mileage_km, 1),
        "message": status_message(st, mileage_km, limit),
        "note": race_prep_note(category, st, days_to_race),
    }


def sort_key(shoe: dict) -> tuple:
    """replace → soon → ok → retired, 같은 상태는 최근 사용 순(미사용은 뒤)."""
    last = shoe.get("last_used") or ""
    return (STATUS_ORDER.get(shoe.get("status"), 9), "" if last else "1", _neg(last))


def _neg(s: str) -> str:
    # 문자열 내림차순 정렬용 — 각 문자를 보수로 바꾼다(ISO 날짜 비교 전용).
    return "".join(chr(0x10FFFF - ord(c)) for c in s)


def headline(shoes: list[dict]) -> str:
    """Level 0 — 가장 급한 활성 신발 1개의 의미 문구."""
    active = sorted((s for s in shoes if s.get("status") in ("replace", "soon")), key=sort_key)
    if not active:
        return "모든 신발이 충분히 남았어요"
    top = active[0]
    text = "교체를 권해요" if top["status"] == "replace" else "교체를 준비할 때예요"
    return f"{top['name']}, {text}"
