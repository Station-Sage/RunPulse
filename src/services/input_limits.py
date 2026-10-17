"""쓰기 API 입력의 범위·열거값 상수 — 요청 경계 검증의 SSOT (SRV D4, ADR-048).

`src/api/validation.py` 스키마와 서비스 함수의 최소 불변식(`ValueError`)이 같은 상수를 참조한다.
값은 운영 데이터로 확인한 뒤 조정한다(SRV-4) — 이 모듈만 고치면 된다.

설계 표(SRV 2.2)의 값: FATIGUE_RANGE·PAIN_LEVELS·CHECKIN_NOTE_MAX·COACH_MESSAGE_MAX·DISTANCE_KM·
WEEKS_RANGE·TARGET_TIME_SEC·RACE_DATE_WINDOW.
그 밖의 상수(PLAN_NAME_MAX·CLIENT_MSG_ID_MAX·CONTEXT_*_MAX·REPORTED_KM_MAX)는 구현 중 에이전트가 정한
기본값이다(`decisions-table.md` S3-3, 사용자 확인 대기).
"""
from __future__ import annotations

from datetime import date

FATIGUE_RANGE = (1, 10)
PAIN_LEVELS = ("none", "mild", "moderate", "severe")
CHECKIN_NOTE_MAX = 500

COACH_MESSAGE_MAX = 4000
CLIENT_MSG_ID_MAX = 100
CONTEXT_KIND_MAX = 32
CONTEXT_REF_MAX = 100

DISTANCE_KM_MAX = 250.0  # 0 초과 ~ 250 이하
WEEKS_RANGE = (1, 52)
TARGET_TIME_SEC_MAX = 172_800  # 0 초과 ~ 48시간 이하
RACE_DATE_WINDOW_YEARS = 5  # 오늘(포함) ~ 오늘 + 5년
PLAN_NAME_MAX = 100
CONTEXT_EPISODE_SEVERITY = (1, 2)  # 질병 강도 2단계 (NEW-7)
CONTEXT_SITE_MAX = 32
CONTEXT_TRAVEL_DELTA_H = (1, 14)
CONTEXT_ALTITUDE_M = (0, 6000)
CONTEXT_CHAT_THREADS_MAX = 50
REPORTED_KM_MAX = {"recent_weekly_km": 300.0, "recent_long_km": 60.0}


def race_date_window(today: date | None = None) -> tuple[date, date]:
    """대회일 허용 구간 (오늘 포함, 오늘+5년 포함). 2/29 + 5년이 없는 해는 2/28."""
    today = today or date.today()
    try:
        last = today.replace(year=today.year + RACE_DATE_WINDOW_YEARS)
    except ValueError:
        last = today.replace(year=today.year + RACE_DATE_WINDOW_YEARS, day=28)
    return today, last


def check_checkin(fatigue: int | None, pain: str | None) -> None:
    """서비스 내부 호출(MCP·CLI)용 최소 불변식 — 범위 밖이면 ValueError."""
    if fatigue is not None and not FATIGUE_RANGE[0] <= fatigue <= FATIGUE_RANGE[1]:
        raise ValueError(f"fatigue 는 {FATIGUE_RANGE[0]}~{FATIGUE_RANGE[1]}: {fatigue!r}")
    if pain is not None and pain not in PAIN_LEVELS:
        raise ValueError(f"pain 은 {PAIN_LEVELS} 중 하나: {pain!r}")


def check_plan_request(distance_km: float, weeks: int | None = None) -> None:
    """플랜 생성·템플릿 서비스 내부 호출용 최소 불변식."""
    if not 0 < distance_km <= DISTANCE_KM_MAX:
        raise ValueError(f"distance_km 는 0 초과 {DISTANCE_KM_MAX:g} 이하: {distance_km!r}")
    if weeks is not None and not WEEKS_RANGE[0] <= weeks <= WEEKS_RANGE[1]:
        raise ValueError(f"weeks 는 {WEEKS_RANGE[0]}~{WEEKS_RANGE[1]}: {weeks!r}")
