"""tests/test_chat_engine_rules_grade.py — 규칙 코치 회복 등급 매핑 회귀 테스트.

회복 등급 코드(excellent/good/moderate/poor)와 규칙 코치의 비교값이 어긋나
컨디션과 무관하게 항상 "피로 회복 필요"를 내던 버그(2026-09-27 UX 리뷰 F-DATA-01)를 막는다.
"""
from unittest.mock import patch

import pytest

from src.ai import chat_engine_rules as rules
from src.analysis.recovery import (
    GRADE_EXCELLENT,
    GRADE_GOOD,
    GRADE_MODERATE,
    GRADE_POOR,
    _recovery_grade,
    grade_label,
)


@pytest.mark.parametrize(
    "grade, expected",
    [
        (GRADE_EXCELLENT, "고강도 훈련"),
        (GRADE_GOOD, "고강도 훈련"),
        (GRADE_MODERATE, "중강도"),
        (GRADE_POOR, "피로 회복이 필요"),
        (None, "회복 데이터가 없어"),
    ],
)
def test_training_recommendation_follows_grade(grade, expected):
    parts: list[str] = []
    rules._respond_training_recommendation(parts, {"recovery": {"grade": grade}})
    assert expected in parts[1]


def test_grade_codes_match_recovery_output():
    """규칙 코치가 비교하는 코드 집합이 실제 등급 산출값과 같아야 한다."""
    produced = {_recovery_grade(s) for s in (95, 70, 50, 10)}
    assert produced == {GRADE_EXCELLENT, GRADE_GOOD, GRADE_MODERATE, GRADE_POOR}


def test_grade_label_korean():
    assert grade_label(GRADE_GOOD) == "좋음"
    assert grade_label(None) == "정보 없음"
    assert grade_label("A") == "정보 없음"


def test_today_deep_formats_pace():
    ctx = {"today_activity": {"distance_km": 9.3, "avg_pace_sec_km": 356.8, "avg_hr": 142}}
    with patch("src.ai.ai_context.build_context", return_value=ctx):
        out = rules.rule_based_response(None, "", chip_id="today_deep")
    assert "5:56/km" in out
    assert "초/km" not in out
