"""Coach 규칙 답변 — 회복 등급 → 강도 매핑과 오늘 판정 일치 (design 30-coach-chat §7.2, §8).

5단계 등급 parametrize, 체크인 하향, 코드에 A/B/C 문자열이 없음을 검증한다.
"""
import re
from pathlib import Path

import pytest

from src.ai.coach_rule_grade import (
    NO_RECOVERY_DATA, RecoveryGrade, checkin_drop, intensity_label, intensity_step,
)
from src.analysis.recovery import _recovery_grade


@pytest.mark.parametrize("raw,label", [
    ("excellent", "고강도 가능"), ("good", "고강도 가능"), ("moderate", "중강도"), ("poor", "회복"),
])
def test_grade_to_intensity(raw, label):
    assert intensity_label(intensity_step(RecoveryGrade.parse(raw), "low")) == label


def test_no_grade_uses_fatigue_level():
    assert RecoveryGrade.parse(None) is None
    assert intensity_label(intensity_step(None, "low")) == "고강도 가능"
    assert intensity_label(intensity_step(None, "high")) == "회복"
    assert "회복 데이터 없음" in NO_RECOVERY_DATA


def test_grade_codes_match_recovery_output():
    """등급 enum이 recovery 모듈이 실제로 산출하는 코드와 같아야 한다."""
    produced = {_recovery_grade(s) for s in (95, 70, 50, 10)}
    assert produced == {g.value for g in RecoveryGrade}


def test_fatigue_level_caps_good_grade():
    assert intensity_step(RecoveryGrade.EXCELLENT, "moderate") == 1
    assert intensity_step(RecoveryGrade.EXCELLENT, "high") == 0


def test_checkin_steps_down_at_least_one_level():
    base = intensity_step(RecoveryGrade.GOOD, "low")
    assert intensity_step(RecoveryGrade.GOOD, "low", {"fatigue": 8, "pain": 0}) == base - 1
    assert intensity_step(RecoveryGrade.GOOD, "low", {"fatigue": 9}) == base - 2
    assert intensity_step(RecoveryGrade.GOOD, "low", {"fatigue": 3}) == base
    assert checkin_drop({"pain": 1, "fatigue": None}) == 1
    assert checkin_drop(None) == 0
    assert intensity_step(RecoveryGrade.POOR, "high", {"fatigue": 9}) == 0


def test_no_abc_grade_strings_in_rule_modules():
    for name in ("coach_rule_grade", "coach_rule_handlers", "coach_rule_plan_handlers", "chat_engine_rules"):
        src = Path(f"src/ai/{name}.py").read_text(encoding="utf-8")
        assert not re.search(r"""['"][ABC]['"]""", src), name
