"""workout_type_classified 컬럼 버그 수정 회귀 테스트 (BUG-WORKOUT-TYPE-COLUMN).

text_value에 저장된 분류를 올바르게 읽는지 검증한다.
"""
from __future__ import annotations

import pytest

from src.ai.chat_context_builders import _add_today_context, _build_base_context
from src.ai.chat_context_rich import _add_rich_30d_context

DATE = "2026-09-25"
PAST_DATE = "2026-09-10"


def _seed_run(conn, *, act_id, day, name="Easy Run"):
    conn.execute(
        "INSERT INTO activity_summaries (id, source, source_id, name, activity_type, start_time,"
        " distance_m, duration_sec, avg_hr, avg_pace_sec_km, elevation_gain)"
        " VALUES (?, 'garmin', ?, ?, 'running', ?, 10000, 3000, 140, 300, 50)",
        (act_id, str(act_id), name, f"{day}T06:00:00"),
    )


def _seed_classification(conn, act_id, wtype):
    """text_value에 분류 저장, numeric_value는 NULL."""
    conn.execute(
        "INSERT INTO metric_store"
        " (scope_type, scope_id, metric_name, category, provider,"
        "  numeric_value, text_value, json_value, confidence, is_primary)"
        " VALUES ('activity', ?, 'workout_type_classified', 'ai', 'runpulse:ai_v1',"
        "  NULL, ?, NULL, NULL, 1)",
        (str(act_id), wtype),
    )


class TestRaceHistoryFromTextValue:
    """text_value='race'인 활동이 race_history에 포함되는지 검증."""

    def test_race_included_without_name_keyword(self, db_conn):
        """이름에 '레이스/대회/Race' 없어도 text_value='race'면 race_history에 나온다."""
        _seed_run(db_conn, act_id=1, day=DATE, name="Morning Run")
        _seed_classification(db_conn, 1, "race")
        db_conn.commit()

        ctx: dict = {}
        _add_rich_30d_context(db_conn, ctx, DATE)
        assert "race_history" in ctx
        ids = [r["id"] for r in ctx["race_history"]]
        assert 1 in ids

    def test_race_not_included_when_only_numeric_value(self, db_conn):
        """numeric_value에만 'race'가 있고 text_value가 없으면 race_history에서 제외."""
        _seed_run(db_conn, act_id=2, day=DATE, name="Morning Run")
        db_conn.execute(
            "INSERT INTO metric_store"
            " (scope_type, scope_id, metric_name, category, provider,"
            "  numeric_value, text_value, json_value, confidence, is_primary)"
            " VALUES ('activity', '2', 'workout_type_classified', 'ai', 'runpulse:ai_v1',"
            "  NULL, NULL, NULL, NULL, 1)",
        )
        db_conn.commit()

        ctx: dict = {}
        _add_rich_30d_context(db_conn, ctx, DATE)
        # name에도 키워드 없음 → race_history에 포함되면 안 됨
        race_ids = [r["id"] for r in ctx.get("race_history", [])]
        assert 2 not in race_ids


class TestTodayDetailWorkoutType:
    """오늘 활동의 분류가 today_detail.workout_type에 채워지는지 검증."""

    def test_today_detail_has_workout_type(self, db_conn):
        _seed_run(db_conn, act_id=10, day=DATE)
        _seed_classification(db_conn, 10, "easy")
        db_conn.commit()

        ctx = _build_base_context(db_conn, DATE)
        _add_today_context(db_conn, ctx, DATE)
        assert ctx["today_detail"] is not None
        assert ctx["today_detail"].get("workout_type") == "easy"

    def test_today_detail_no_classification_key_absent(self, db_conn):
        """분류 행이 없으면 workout_type 키가 생기지 않는다."""
        _seed_run(db_conn, act_id=11, day=DATE)
        db_conn.commit()

        ctx = _build_base_context(db_conn, DATE)
        _add_today_context(db_conn, ctx, DATE)
        assert ctx["today_detail"] is not None
        assert "workout_type" not in ctx["today_detail"]


class TestSimilarActivities:
    """오늘 분류와 같은 과거 활동이 similar_activities.history에 포함되는지 검증."""

    def test_similar_activities_populated(self, db_conn):
        # 오늘 활동
        _seed_run(db_conn, act_id=20, day=DATE)
        _seed_classification(db_conn, 20, "tempo")
        # 과거 동일 분류 활동
        _seed_run(db_conn, act_id=21, day=PAST_DATE)
        _seed_classification(db_conn, 21, "tempo")
        db_conn.commit()

        ctx: dict = {}
        _add_rich_30d_context(db_conn, ctx, DATE)
        assert "similar_activities" in ctx
        assert ctx["similar_activities"]["type"] == "tempo"
        past_ids = [r["id"] for r in ctx["similar_activities"]["history"]]
        assert 21 in past_ids
        assert 20 not in past_ids  # 오늘 활동은 포함 안 됨

    def test_no_similar_activities_without_classification(self, db_conn):
        """오늘 활동에 분류가 없으면 similar_activities 키가 생기지 않는다."""
        _seed_run(db_conn, act_id=30, day=DATE)
        db_conn.commit()

        ctx: dict = {}
        _add_rich_30d_context(db_conn, ctx, DATE)
        assert "similar_activities" not in ctx
