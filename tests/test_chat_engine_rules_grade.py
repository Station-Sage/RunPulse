"""tests/test_chat_engine_rules_grade.py — 규칙 코치 회복 등급 매핑 회귀 테스트.

회복 등급 코드 산출값·라벨과, 훈련 추천이 등급이 아닌 readiness_decision을 쓰는지 검증한다
(2026-09-27 UX 리뷰 F-DATA-01 재발 방지).
"""
from unittest.mock import patch

from src.ai import chat_engine_rules as rules
from src.analysis.recovery import (
    GRADE_EXCELLENT,
    GRADE_GOOD,
    GRADE_MODERATE,
    GRADE_POOR,
    _recovery_grade,
    grade_label,
)


def test_training_recommendation_uses_readiness_decision():
    """회복 등급이 아니라 readiness_decision 판정(Today와 동일)을 그대로 쓴다 — 등급 매핑 버그 재발 방지."""
    ctx = {"recovery": {"grade": GRADE_POOR},
           "readiness_decision": {"headline": "HEADLINE", "evidence": [{"label": "TSB -30"}]}}
    parts: list[str] = []
    rules._respond_training_recommendation(parts, ctx)
    assert parts[1:3] == ["HEADLINE", "- TSB -30"]


def test_training_recommendation_without_decision():
    parts: list[str] = []
    rules._respond_training_recommendation(parts, {"recovery": {"grade": None}})
    assert "판정할 수 없" in parts[1]


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
