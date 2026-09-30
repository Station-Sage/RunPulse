"""한국어 표시 포맷터 — Coach 규칙 답변·근거 칩이 같은 숫자 표기를 쓰도록 하는 단일 소스 (30-coach-chat §4.5).

거리 `10.03km`, 페이스 `5:45/km`, 폼 `−11`(U+2212), 등급·세션 유형은 한국어 라벨. 원시 float·`초/km`·영문 키는 내보내지 않는다.
"""
from __future__ import annotations

import re

MINUS = "−"

WORKOUT_TYPE_KO = {
    "easy": "이지런", "tempo": "템포", "interval": "인터벌", "long": "롱런",
    "recovery": "회복 달리기", "race": "레이스", "rest": "휴식",
}
GRADE_KO = {"excellent": "매우 좋음", "good": "좋음", "moderate": "보통", "poor": "나쁨"}

_RAW_FLOAT = re.compile(r"\d+\.\d{3,}")
_SEC_PER_KM = re.compile(r"(\d+(?:\.\d+)?)\s*초/km")


def fmt_distance(km) -> str:
    """10.03 → '10.03km' (소수 둘째 자리, 끝의 0 제거 없음)."""
    return f"{float(km):.2f}km" if isinstance(km, (int, float)) else "-"


def fmt_pace(sec_per_km) -> str:
    """345 → '5:45/km'."""
    if not isinstance(sec_per_km, (int, float)) or sec_per_km <= 0:
        return "-"
    sec = int(round(sec_per_km))
    return f"{sec // 60}:{sec % 60:02d}/km"


def fmt_duration(sec) -> str:
    """13223 → '3:40:23', 1500 → '25:00'."""
    if not isinstance(sec, (int, float)) or sec <= 0:
        return "-"
    s = int(round(sec))
    h, r = divmod(s, 3600)
    m, s = divmod(r, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def fmt_gap(sec) -> str:
    """차이 초 → '1분 30초' / '45초' (부호 없음)."""
    if not isinstance(sec, (int, float)):
        return "-"
    s = int(round(abs(sec)))
    m, r = divmod(s, 60)
    return f"{m}분 {r}초" if m and r else (f"{m}분" if m else f"{r}초")


def fmt_signed(value) -> str:
    """폼·부호 있는 지표 — |v|≥10 정수, 아니면 소수 1자리. 음수는 U+2212."""
    if not isinstance(value, (int, float)):
        return "-"
    body = f"{abs(value):.0f}" if abs(value) >= 10 else f"{abs(value):.1f}"
    if float(body) == 0:
        return "0"
    return ("+" if value > 0 else MINUS) + body


def fmt_int(value) -> str:
    return f"{value:.0f}" if isinstance(value, (int, float)) else "-"


def workout_ko(workout_type: str | None) -> str:
    return WORKOUT_TYPE_KO.get(workout_type or "", workout_type or "")


def grade_ko(grade: str | None) -> str:
    return GRADE_KO.get(grade or "", "정보 없음")


def sanitize(text: str) -> str:
    """LLM·규칙 본문 후처리 — 3자리 이상 소수는 반올림, 'N초/km'는 페이스로 (§4.5)."""
    text = _SEC_PER_KM.sub(lambda m: fmt_pace(float(m.group(1))), text)
    return _RAW_FLOAT.sub(lambda m: f"{float(m.group(0)):.1f}", text)
