"""Coach 규칙 답변 — 자유 입력 키워드 → 관련 칩 순서(UX C-14). 답을 추측하지 않고 안내할 칩만 고른다.

설계 §7.3 의 "자유 입력은 키워드로 답을 추측하지 않는다"는 그대로 지킨다: 본문은 여전히 "AI 없이는 답할 수 없다"이고,
키워드는 '지금 데이터로 답할 수 있는 칩' 중 질문과 가까운 것을 앞으로 올리는 데만 쓴다. 맞는 키워드가 없으면 기존 동작.
"""
from __future__ import annotations

# 순서 = 우선순위(구체적인 것 먼저). 키는 소문자 부분 문자열.
_INTENT_RULES: tuple[tuple[tuple[str, ...], tuple[str, ...]], ...] = (
    (("부상", "통증", "아파", "아픈", "다쳤", "injury", "pain"), ("injury_check", "explain_cirs")),
    (("테이퍼", "taper"), ("taper_when", "race_build")),
    (("대회", "레이스", "마라톤", "하프", "풀코스", "목표 기록", "race", "marathon"),
     ("goal_feasibility", "race_build", "explain_rri")),
    (("이번 주", "이번주", "계획", "플랜", "스케줄", "남은 훈련", "plan"), ("week_plan", "today_advice")),
    (("피로", "피곤", "회복", "컨디션", "쉬어", "휴식", "지쳐", "힘들", "fatigue", "recovery", "tsb"),
     ("today_advice", "explain_tsb", "explain_atl")),
    (("페이스", "강도", "오늘", "pace"), ("today_advice",)),
    (("ctl", "체력"), ("explain_ctl",)),
    (("atl",), ("explain_atl",)),
    (("utrs", "준비도"), ("explain_utrs",)),
    (("cirs",), ("explain_cirs",)),
    (("rri",), ("explain_rri",)),
)


def intent_chips(message: str | None) -> list[str]:
    """질문에 든 키워드가 가리키는 chip_id 목록(우선순위 순, 중복 없음). 없으면 []."""
    msg = (message or "").lower()
    if not msg.strip():
        return []
    out: list[str] = []
    for keys, chips in _INTENT_RULES:
        if any(k in msg for k in keys):
            out.extend(c for c in chips if c not in out)
    return out


def rank_followups(message: str | None, answerable: list[str], limit: int = 3) -> tuple[list[str], bool]:
    """답할 수 있는 칩 중 질문과 가까운 것을 앞에 두고 limit 개. 반환 `(칩, 키워드가 맞았는지)`.

    맞는 키워드가 없거나 그 칩들이 지금 답할 수 없으면 기존 순서(answerable 앞 limit 개) 그대로.
    """
    matched = [c for c in intent_chips(message) if c in answerable]
    if not matched:
        return answerable[:limit], False
    rest = [c for c in answerable if c not in matched]
    return (matched + rest)[:limit], True
