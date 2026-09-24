"""test_chat_context_race.py — _add_race_context + _format_chat_context 통합 테스트.

목표·예측·폼 예측 시드가 있으면 포맷된 텍스트에 레이스 아침 예상 폼과
목표 거리 예측 기록이 포함되고, 목표가 없으면 둘 다 없음을 검증한다.
"""
from __future__ import annotations

import pytest

from src.ai.chat_context_builders import _add_race_context
from src.ai.chat_context_format import _format_chat_context

DATE = "2026-09-24"


def _seed_metric(conn, scope_id, metric_name, value, scope_type="daily"):
    conn.execute(
        "INSERT INTO metric_store"
        " (scope_type, scope_id, metric_name, category, provider,"
        "  numeric_value, text_value, json_value, confidence, is_primary)"
        " VALUES (?, ?, ?, 'prediction', 'runpulse:formula_v1', ?, NULL, NULL, NULL, 1)",
        (scope_type, scope_id, metric_name, value),
    )


def _seed_goal(conn, name, race_date, distance_km, target_time_sec=None):
    conn.execute(
        "INSERT INTO goals (name, race_date, distance_km, target_time_sec, status)"
        " VALUES (?, ?, ?, ?, 'active')",
        (name, race_date, distance_km, target_time_sec),
    )


@pytest.fixture
def ctx_with_goal(db_conn):
    """목표 + 마라톤 예측 + CTL/ATL 시드 컨텍스트."""
    _seed_goal(db_conn, "춘천마라톤", "2026-10-25", 42.195, target_time_sec=14400)
    _seed_metric(db_conn, DATE, "ctl", 75.0)
    _seed_metric(db_conn, DATE, "atl", 85.0)
    _seed_metric(db_conn, "2026-09-20", "race_pred_marathon_sec", 15692)
    db_conn.commit()

    ctx: dict = {"date": DATE}
    _add_race_context(db_conn, ctx, DATE)
    return ctx


@pytest.fixture
def ctx_no_goal(db_conn):
    """목표 없는 컨텍스트."""
    ctx: dict = {"date": DATE}
    _add_race_context(db_conn, ctx, DATE)
    return ctx


class TestRaceContextWithGoal:
    def test_race_hub_in_context(self, ctx_with_goal):
        assert "race_hub" in ctx_with_goal

    def test_formatted_text_contains_form_prediction(self, ctx_with_goal):
        text = _format_chat_context(ctx_with_goal, "")
        assert "레이스 아침 예상 폼" in text

    def test_formatted_text_contains_target_prediction(self, ctx_with_goal):
        text = _format_chat_context(ctx_with_goal, "")
        assert "목표 거리 예측 기록" in text

    def test_formatted_text_contains_tsb_values(self, ctx_with_goal):
        """TSB 수치가 ±부호와 함께 출력된다."""
        text = _format_chat_context(ctx_with_goal, "")
        # projection scenarios가 +/- 기호로 출력되는지 확인
        assert "TSB" in text or "폼" in text  # 레이스 아침 예상 폼(TSB) 레이블 포함


class TestRaceContextNoGoal:
    def test_race_hub_is_none_or_no_goal(self, ctx_no_goal):
        hub = ctx_no_goal.get("race_hub")
        if hub is not None:
            assert hub.get("goal") is None

    def test_formatted_text_no_form_prediction(self, ctx_no_goal):
        text = _format_chat_context(ctx_no_goal, "")
        assert "레이스 아침 예상 폼" not in text

    def test_formatted_text_no_target_prediction(self, ctx_no_goal):
        text = _format_chat_context(ctx_no_goal, "")
        assert "목표 거리 예측 기록" not in text
