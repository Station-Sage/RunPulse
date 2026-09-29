"""AI 채팅 컨텍스트 — 외부 LLM으로 나가는 항목 목록(sent_scope, 30-coach-chat design §4.3)."""
from __future__ import annotations

# ctx 키 → (화면 표기 항목, 기간, 선택 항목 여부). 선택 항목 = 사용자가 끌 수 있는 것(메모).
_SCOPE_ITEMS: list[tuple[str, str, str, bool]] = [
    ("ctl", "훈련 지표(CTL·TSB·VO2Max)", "오늘", False),
    ("wellness", "웰니스(BB·수면·HRV)", "오늘", False),
    ("wellness_3d", "웰니스(BB·수면·HRV)", "최근 3일", False),
    ("wellness_7d", "웰니스(BB·수면·HRV)", "최근 7일", False),
    ("wellness_14d", "웰니스(BB·수면·HRV)", "최근 14일", False),
    ("wellness_30d", "웰니스(BB·수면·HRV)", "최근 30일", False),
    ("recent_activities", "활동 요약", "최근", False),
    ("activities_14d", "활동 요약", "최근 14일", False),
    ("activities_30d", "활동 요약", "최근 30일", False),
    ("today_detail", "오늘 활동 상세", "오늘", False),
    ("lookup_activities", "조회한 날의 활동", "지정일", False),
    ("fitness_30d", "체력 추이(CTL·ATL·TSB)", "최근 30일", False),
    ("daily_metrics_30d", "일별 지표", "최근 30일", False),
    ("cirs_7d", "부상 위험(CIRS)", "최근 7일", False),
    ("darp_trend", "레이스 예측 추이", "최근", False),
    ("race_history", "대회 기록", "전체", False),
    ("goal", "목표·레이스 허브", "현재", False),
    ("week_plan", "이번 주 훈련 계획", "이번 주", False),
    ("runner_profile", "러너 프로필", "현재", False),
]
_CHECKIN = ("checkin", "오늘 컨디션 입력(피로·통증)", "오늘", False)
_NOTE = ("checkin_note", "체크인 메모", "오늘", True)


def describe_scope(ctx: dict) -> list[dict]:
    """ctx에 실제로 담긴 항목 → [{item, period, optional}] (중복 항목은 가장 긴 기간 하나만 남기지 않고 모두 나열)."""
    out: list[dict] = []
    for key, item, period, optional in _SCOPE_ITEMS:
        if ctx.get(key):
            out.append({"item": item, "period": period, "optional": optional})
    checkin = ctx.get("checkin")
    if checkin:
        out.append({"item": _CHECKIN[1], "period": _CHECKIN[2], "optional": _CHECKIN[3]})
        if (checkin.get("note") or "").strip():
            out.append({"item": _NOTE[1], "period": _NOTE[2], "optional": _NOTE[3]})
    return out


def scope_catalog() -> list[dict]:
    """전송 가능 항목 전체 목록(동의 화면용) — 같은 항목은 가장 긴 기간 하나로 합친다."""
    merged: dict[str, dict] = {}
    for _key, item, period, optional in _SCOPE_ITEMS:
        merged[item] = {"item": item, "period": period, "optional": optional}
    merged[_CHECKIN[1]] = {"item": _CHECKIN[1], "period": _CHECKIN[2], "optional": _CHECKIN[3]}
    merged[_NOTE[1]] = {"item": _NOTE[1], "period": _NOTE[2], "optional": _NOTE[3]}
    return list(merged.values())
