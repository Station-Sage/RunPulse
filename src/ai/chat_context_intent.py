"""AI 채팅 컨텍스트 — 의도 감지 모듈.

chat_context.py에서 분리 (2026-03-29).
"""
from __future__ import annotations

import re as _re
from datetime import date, timedelta

_INTENT_KEYWORDS: dict[str, list[str]] = {
    "today": ["오늘", "훈련 어떻", "방금", "아까", "분석해", "평가해", "어땠"],
    "race": ["대회", "마라톤", "레이스", "하프", "10k", "5k", "풀코스", "준비도", "예측"],
    "compare": ["비교", "작년", "지난번", "이전", "나아졌", "성장", "변화", "개선", "퇴보"],
    "plan": ["내일", "계획", "조정", "다음", "스케줄", "훈련량", "몇 키로"],
    "recovery": ["회복", "피로", "쉬어", "컨디션", "휴식", "오버", "과훈련", "부상"],
}

_DATE_PATTERNS = [
    _re.compile(r"(\d{4})[-./](\d{1,2})[-./](\d{1,2})"),
    _re.compile(r"(\d{1,2})월\s*(\d{1,2})일"),
    _re.compile(r"(\d{1,2})/(\d{1,2})"),
]

_RELATIVE_DATE_KW: dict[str, int] = {
    "어제": -1, "그제": -2, "그저께": -2, "엊그제": -2,
    "그끄저께": -3, "3일전": -3, "3일 전": -3,
}

_WEEKDAY_KO = {"월": 0, "화": 1, "수": 2, "목": 3, "금": 4, "토": 5, "일": 6}


def _extract_date(message: str) -> str | None:
    """메시지에서 날짜 추출. 없으면 None."""
    today = date.today()

    for kw, delta in _RELATIVE_DATE_KW.items():
        if kw in message:
            return (today + timedelta(days=delta)).isoformat()

    m = _re.search(r"지난\s*주?\s*(월|화|수|목|금|토|일)", message)
    if m:
        wd = _WEEKDAY_KO[m.group(1)]
        last_monday = today - timedelta(days=today.weekday() + 7)
        return (last_monday + timedelta(days=wd)).isoformat()

    for pat in _DATE_PATTERNS:
        m = pat.search(message)
        if m:
            groups = m.groups()
            try:
                if len(groups) == 3:
                    return date(int(groups[0]), int(groups[1]), int(groups[2])).isoformat()
                elif len(groups) == 2:
                    y = today.year
                    d = date(y, int(groups[0]), int(groups[1]))
                    if d > today:
                        d = date(y - 1, int(groups[0]), int(groups[1]))
                    return d.isoformat()
            except ValueError:
                continue

    return None


def detect_intent(message: str) -> tuple[str, str | None]:
    """사용자 메시지에서 의도 + 날짜 감지.

    Returns:
        (intent, target_date) — target_date는 특정 날짜 조회 시 YYYY-MM-DD.
    """
    msg = message.lower()
    target_date = _extract_date(message)

    if target_date:
        for intent, keywords in _INTENT_KEYWORDS.items():
            if any(k in msg for k in keywords):
                return intent, target_date
        return "lookup", target_date

    for intent, keywords in _INTENT_KEYWORDS.items():
        if any(k in msg for k in keywords):
            return intent, None
    return "general", None
