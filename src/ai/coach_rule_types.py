"""Coach 규칙 답변 공통 타입 — RuleAnswer, 칩 문구 표 (30-coach-chat design §7.3)."""
from __future__ import annotations

from dataclasses import dataclass, field

CHIP_TEXT: dict[str, str] = {
    "today_advice": "오늘 훈련 어떻게 할까요?",
    "goal_feasibility": "목표 달성 가능성은 어떤가요?",
    "race_build": "레이스까지 어떻게 준비해요?",
    "week_plan": "이번 주 남은 훈련은?",
    "taper_when": "테이퍼는 언제부터 하나요?",
    "injury_check": "부상 위험은 없나요?",
    "explain_tsb": "폼(TSB)이 뭔가요?",
    "explain_ctl": "체력(CTL)이 뭔가요?",
    "explain_atl": "피로(ATL)가 뭔가요?",
    "explain_utrs": "훈련 준비도(UTRS)가 뭔가요?",
    "explain_cirs": "부상 위험도(CIRS)가 뭔가요?",
    "explain_rri": "레이스 준비도(RRI)가 뭔가요?",
}

RETRY_TEXT = "AI로 다시 시도"


@dataclass
class RuleAnswer:
    """규칙 답변 — text(본문), evidence(비어 있으면 근거 후보 자동 수집), followups(chip_id 목록, 서버 제공)."""

    text: str
    evidence: list[dict] = field(default_factory=list)
    followups: list[str] = field(default_factory=list)
    links: list[dict] = field(default_factory=list)


def chip_view(chip_id: str) -> dict:
    return {"chip_id": chip_id, "text": CHIP_TEXT.get(chip_id, chip_id)}
