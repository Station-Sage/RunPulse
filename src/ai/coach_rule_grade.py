"""Coach 규칙 답변 — 회복 등급 → 오늘 강도 매핑 (30-coach-chat design §7.2).

등급은 `RecoveryGrade` 한 곳에서만 해석한다(문자열 A/B/C 없음). 판정 흐름:
회복 등급 → 강도 단계 → 피로 수준(readiness)으로 상한 → 체크인(피로·통증)으로 하향.
"""
from __future__ import annotations

from enum import Enum


class RecoveryGrade(str, Enum):
    EXCELLENT = "excellent"
    GOOD = "good"
    MODERATE = "moderate"
    POOR = "poor"

    @classmethod
    def parse(cls, raw) -> "RecoveryGrade | None":
        try:
            return cls(raw)
        except ValueError:
            return None


NO_RECOVERY_DATA = "회복 데이터 없음 — 부하 지표로만 판단"

INTENSITY_LABELS = ("회복", "중강도", "고강도 가능")

_GRADE_STEP = {
    RecoveryGrade.EXCELLENT: 2, RecoveryGrade.GOOD: 2, RecoveryGrade.MODERATE: 1, RecoveryGrade.POOR: 0,
}
_FATIGUE_CAP = {"low": 2, "moderate": 1, "high": 0}
_FATIGUE_TO_GRADE = {"low": RecoveryGrade.GOOD, "moderate": RecoveryGrade.MODERATE, "high": RecoveryGrade.POOR}


def checkin_drop(checkin: dict | None) -> int:
    """체크인이 낮추는 단계 수 — 통증 또는 피로 7 이상 1단계, 피로 9 이상 추가 1단계."""
    if not checkin:
        return 0
    f = checkin.get("fatigue")
    drop = 1 if (checkin.get("pain") or (isinstance(f, (int, float)) and f >= 7)) else 0
    if isinstance(f, (int, float)) and f >= 9:
        drop += 1
    return drop


def intensity_step(grade: RecoveryGrade | None, fatigue_level: str | None, checkin: dict | None = None) -> int:
    """0(회복)·1(중강도)·2(고강도 가능). 등급이 없으면 피로 수준으로 대신 판단한다."""
    grade = grade or _FATIGUE_TO_GRADE.get(fatigue_level or "low", RecoveryGrade.GOOD)
    step = min(_GRADE_STEP[grade], _FATIGUE_CAP.get(fatigue_level or "low", 2))
    return max(0, step - checkin_drop(checkin))


def intensity_label(step: int) -> str:
    return INTENSITY_LABELS[max(0, min(step, 2))]
