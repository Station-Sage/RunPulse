"""AI 채팅 컨텍스트, 도구 실행, 추천 질문 파싱 테스트."""
from __future__ import annotations

import json
import sqlite3
import sys
from datetime import date, timedelta
from unittest.mock import patch

import pytest

# ── DB fixture ────────────────────────────────────────────────────────

_SCHEMA = """
CREATE TABLE activity_summaries (
    id INTEGER PRIMARY KEY, source TEXT, activity_type TEXT,
    start_time TEXT, distance_km REAL, duration_sec REAL,
    avg_pace_sec_km REAL, avg_hr REAL, max_hr REAL,
    elevation_gain_m REAL, calories REAL, name TEXT,
    matched_group_id TEXT
);
CREATE VIEW v_canonical_activities AS SELECT * FROM activity_summaries;
CREATE TABLE computed_metrics (
    id INTEGER PRIMARY KEY, date TEXT, metric_name TEXT,
    metric_value REAL, metric_json TEXT, activity_id INTEGER
);
CREATE TABLE daily_wellness (
    id INTEGER PRIMARY KEY, date TEXT, source TEXT,
    body_battery REAL, sleep_score REAL, sleep_hours REAL,
    hrv_value REAL, stress_avg REAL, resting_hr REAL
);
CREATE TABLE daily_fitness (
    id INTEGER PRIMARY KEY, date TEXT, ctl REAL, atl REAL, tsb REAL,
    garmin_vo2max REAL, runalyze_evo2max REAL
);
CREATE TABLE daily_detail_metrics (
    id INTEGER PRIMARY KEY, date TEXT, metric_name TEXT, metric_value REAL
);
"""


@pytest.fixture()
def mem_conn() -> sqlite3.Connection:
    """In-memory SQLite DB with schema + sample data."""
    conn = sqlite3.connect(":memory:")
    conn.executescript(_SCHEMA)

    today = date.today().isoformat()
    yesterday = (date.today() - timedelta(days=1)).isoformat()

    # 활동 데이터
    conn.execute(
        "INSERT INTO activity_summaries "
        "(id, source, activity_type, start_time, distance_km, duration_sec, "
        "avg_pace_sec_km, avg_hr, max_hr, elevation_gain_m, calories, name) "
        "VALUES (1,'garmin','running',?,10.0,3000,300,150,170,50,500,'Morning Run')",
        (f"{today}T07:00:00",),
    )
    conn.execute(
        "INSERT INTO activity_summaries "
        "(id, source, activity_type, start_time, distance_km, duration_sec, "
        "avg_pace_sec_km, avg_hr, max_hr, elevation_gain_m, calories, name) "
        "VALUES (2,'garmin','running',?,5.0,1500,300,145,160,20,250,'Easy Run')",
        (f"{yesterday}T06:30:00",),
    )

    # 2차 메트릭 (일별)
    conn.execute(
        "INSERT INTO computed_metrics (date, metric_name, metric_value, activity_id) "
        "VALUES (?, 'UTRS', 72.5, NULL)", (today,),
    )
    conn.execute(
        "INSERT INTO computed_metrics (date, metric_name, metric_value, activity_id) "
        "VALUES (?, 'CIRS', 65.0, NULL)", (today,),
    )
    conn.execute(
        "INSERT INTO computed_metrics (date, metric_name, metric_value, activity_id) "
        "VALUES (?, 'ACWR', 1.1, NULL)", (today,),
    )

    # 활동별 메트릭
    conn.execute(
        "INSERT INTO computed_metrics (date, metric_name, metric_value, activity_id) "
        "VALUES (?, 'EI', 0.85, 1)", (today,),
    )

    # 웰니스
    conn.execute(
        "INSERT INTO daily_wellness (date, source, body_battery, sleep_score, "
        "sleep_hours, hrv_value, stress_avg, resting_hr) "
        "VALUES (?, 'garmin', 75, 82, 7.5, 55, 30, 52)", (today,),
    )

    # 피트니스
    conn.execute(
        "INSERT INTO daily_fitness (date, ctl, atl, tsb, garmin_vo2max) "
        "VALUES (?, 45.2, 52.1, -6.9, 51.0)", (today,),
    )

    conn.commit()
    return conn


# ── 1. Intent Detection ──────────────────────────────────────────────

class TestDetectIntent:
    """detect_intent 함수 테스트."""

    def test_today_intent(self):
        from src.ai.chat_context import detect_intent
        intent, _ = detect_intent("오늘 훈련 어때")
        assert intent == "today"

    def test_race_intent(self):
        from src.ai.chat_context import detect_intent
        intent, _ = detect_intent("마라톤 준비 어떻게 하면 좋을까")
        assert intent == "race"

    def test_compare_intent(self):
        from src.ai.chat_context import detect_intent
        intent, _ = detect_intent("작년보다 나아졌어?")
        assert intent == "compare"

    def test_plan_intent(self):
        from src.ai.chat_context import detect_intent
        intent, _ = detect_intent("내일 뭐해")
        assert intent == "plan"

    def test_recovery_intent(self):
        from src.ai.chat_context import detect_intent
        intent, _ = detect_intent("회복 상태 어때")
        assert intent == "recovery"

    def test_general_intent(self):
        from src.ai.chat_context import detect_intent
        intent, _ = detect_intent("안녕")
        assert intent == "general"

    def test_general_for_unrelated(self):
        from src.ai.chat_context import detect_intent
        intent, _ = detect_intent("날씨 좋다")
        assert intent == "general"


# ── 2. Date Extraction ────────────────────────────────────────────────

class TestExtractDate:
    """_extract_date 함수 테스트."""

    def test_korean_date(self):
        from src.ai.chat_context import _extract_date
        result = _extract_date("3월 15일에 달렸어")
        assert result is not None
        assert result.endswith("-03-15")

    def test_yesterday(self):
        from src.ai.chat_context import _extract_date
        result = _extract_date("어제 운동했어")
        expected = (date.today() - timedelta(days=1)).isoformat()
        assert result == expected

    def test_iso_date(self):
        from src.ai.chat_context import _extract_date
        result = _extract_date("2026-03-20 데이터 보여줘")
        assert result == "2026-03-20"

    def test_slash_date(self):
        from src.ai.chat_context import _extract_date
        result = _extract_date("3/10 기록 확인")
        assert result is not None
        assert "-03-10" in result

    def test_no_date(self):
        from src.ai.chat_context import _extract_date
        result = _extract_date("안녕")
        assert result is None

    def test_day_before_yesterday(self):
        from src.ai.chat_context import _extract_date
        result = _extract_date("그제 달린 거 분석해줘")
        expected = (date.today() - timedelta(days=2)).isoformat()
        assert result == expected

    def test_date_with_intent(self):
        """날짜 + 의도 키워드 조합."""
        from src.ai.chat_context import detect_intent
        intent, target_date = detect_intent("3월 15일 훈련 어땠어")
        assert intent == "today"
        assert target_date is not None
        assert target_date.endswith("-03-15")

    def test_date_only_returns_lookup(self):
        """날짜만 있고 의도 키워드 없으면 lookup."""
        from src.ai.chat_context import detect_intent
        intent, target_date = detect_intent("2026-03-20 데이터")
        assert intent == "lookup"
        assert target_date == "2026-03-20"


# ── 3. Tool Declarations ─────────────────────────────────────────────

class TestToolDeclarations:
    """TOOL_DECLARATIONS 유효성 테스트."""

    def test_is_list(self):
        from src.ai.tools import TOOL_DECLARATIONS
        assert isinstance(TOOL_DECLARATIONS, list)
        assert len(TOOL_DECLARATIONS) > 0

    def test_each_has_required_fields(self):
        from src.ai.tools import TOOL_DECLARATIONS
        for decl in TOOL_DECLARATIONS:
            assert "name" in decl, f"Missing 'name' in {decl}"
            assert "description" in decl, f"Missing 'description' in {decl.get('name')}"
            assert "parameters" in decl, f"Missing 'parameters' in {decl.get('name')}"

    def test_all_names_unique(self):
        from src.ai.tools import TOOL_DECLARATIONS
        names = [d["name"] for d in TOOL_DECLARATIONS]
        assert len(names) == len(set(names)), f"Duplicate tool names: {names}"

    def test_parameters_have_type_object(self):
        from src.ai.tools import TOOL_DECLARATIONS
        for decl in TOOL_DECLARATIONS:
            params = decl["parameters"]
            assert params.get("type") == "object", (
                f"Tool '{decl['name']}' parameters type should be 'object'"
            )

    def test_known_tools_present(self):
        from src.ai.tools import TOOL_DECLARATIONS
        names = {d["name"] for d in TOOL_DECLARATIONS}
        expected = {
            "get_activity", "get_activities_range", "get_metrics",
            "get_metrics_trend", "get_wellness", "get_fitness",
            "get_race_history", "compare_periods", "get_training_plan",
            "get_runner_profile",
        }
        assert expected.issubset(names)


# ── 4. Tool Execution ────────────────────────────────────────────────

class TestExecuteTool:
    """execute_tool 함수 테스트 — in-memory DB."""

    def test_get_activity(self, mem_conn):
        from src.ai.tools import execute_tool
        today = date.today().isoformat()
        result = json.loads(execute_tool(mem_conn, "get_activity", {"date": today}))
        assert result["date"] == today
        assert len(result["activities"]) == 1
        assert result["activities"][0]["distance_km"] == 10.0

    def test_get_activity_no_data(self, mem_conn):
        from src.ai.tools import execute_tool
        result = json.loads(execute_tool(mem_conn, "get_activity", {"date": "2020-01-01"}))
        assert result["activities"] == []
        assert "message" in result

    def test_get_activity_includes_metrics(self, mem_conn):
        from src.ai.tools import execute_tool
        today = date.today().isoformat()
        result = json.loads(execute_tool(mem_conn, "get_activity", {"date": today}))
        act = result["activities"][0]
        assert "metrics" in act
        assert "EI" in act["metrics"]
        assert act["metrics"]["EI"] == 0.85

    def test_get_metrics(self, mem_conn):
        from src.ai.tools import execute_tool
        today = date.today().isoformat()
        result = json.loads(execute_tool(mem_conn, "get_metrics", {"date": today}))
        assert result["date"] == today
        metrics = result["metrics"]
        assert "UTRS" in metrics
        assert metrics["UTRS"] == 72.5

    def test_get_metrics_filtered(self, mem_conn):
        from src.ai.tools import execute_tool
        today = date.today().isoformat()
        result = json.loads(execute_tool(
            mem_conn, "get_metrics",
            {"date": today, "metric_names": ["UTRS"]},
        ))
        assert "UTRS" in result["metrics"]
        assert "CIRS" not in result["metrics"]

    def test_get_wellness(self, mem_conn):
        from src.ai.tools import execute_tool
        today = date.today().isoformat()
        result = json.loads(execute_tool(
            mem_conn, "get_wellness",
            {"start_date": today, "end_date": today},
        ))
        assert len(result["data"]) == 1
        w = result["data"][0]
        assert w["body_battery"] == 75
        assert w["sleep_score"] == 82
        assert w["hrv"] == 55

    def test_get_fitness(self, mem_conn):
        from src.ai.tools import execute_tool
        result = json.loads(execute_tool(mem_conn, "get_fitness", {"days": 7}))
        assert len(result["data"]) >= 1
        d = result["data"][0]
        assert d["ctl"] == 45.2
        assert d["vo2max"] == 51.0

    def test_get_runner_profile(self, mem_conn):
        from src.ai.tools import execute_tool
        # Mock src.training.goals to avoid import errors
        mock_goals = type(sys)("src.training.goals")
        mock_goals.get_active_goal = lambda conn: None
        with patch.dict(sys.modules, {"src.training.goals": mock_goals}):
            result = json.loads(execute_tool(mem_conn, "get_runner_profile", {}))
        assert isinstance(result, dict)
        # Should have some profile data from our test activities
        assert "vo2max" in result or "weekly_avg_km" in result

    def test_unknown_tool_returns_error(self, mem_conn):
        from src.ai.tools import execute_tool
        result = json.loads(execute_tool(mem_conn, "nonexistent_tool", {}))
        assert "error" in result
        assert "알 수 없는 도구" in result["error"]

    def test_get_activities_range(self, mem_conn):
        from src.ai.tools import execute_tool
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        today = date.today().isoformat()
        result = json.loads(execute_tool(
            mem_conn, "get_activities_range",
            {"start_date": yesterday, "end_date": today},
        ))
        assert result["count"] == 2

    def test_get_metrics_trend(self, mem_conn):
        from src.ai.tools import execute_tool
        result = json.loads(execute_tool(
            mem_conn, "get_metrics_trend",
            {"metric_name": "UTRS", "days": 7},
        ))
        assert result["metric"] == "UTRS"
        assert len(result["data"]) >= 1

    def test_compare_periods(self, mem_conn):
        from src.ai.tools import execute_tool
        today = date.today().isoformat()
        week_ago = (date.today() - timedelta(days=7)).isoformat()
        result = json.loads(execute_tool(
            mem_conn, "compare_periods",
            {
                "period_a_start": week_ago,
                "period_a_end": today,
                "period_b_start": today,
                "period_b_end": today,
            },
        ))
        assert "period_a" in result
        assert "period_b" in result


# ── 5. _parse_followup ────────────────────────────────────────────────

class TestParseFollowup:
    """_parse_followup 추천 질문 파싱 테스트."""

    def test_parse_three_questions(self):
        from src.web.views_ai_coach_cards import _parse_followup
        text = "오늘 잘 달렸어요.\n[추천: Q1 | Q2 | Q3]"
        body, questions = _parse_followup(text)
        assert len(questions) == 3
        assert questions[0] == "Q1"
        assert questions[1] == "Q2"
        assert questions[2] == "Q3"
        assert "[추천:" not in body

    def test_no_tag_returns_empty(self):
        from src.web.views_ai_coach_cards import _parse_followup
        text = "일반적인 응답입니다."
        body, questions = _parse_followup(text)
        assert questions == []
        assert body == text

    def test_body_preserved(self):
        from src.web.views_ai_coach_cards import _parse_followup
        text = "분석 결과입니다.\n상세 내용.\n[추천: 다음은? | 비교해줘 | 계획 세워줘]"
        body, questions = _parse_followup(text)
        assert "분석 결과입니다." in body
        assert "상세 내용." in body
        assert len(questions) == 3

    def test_single_question(self):
        from src.web.views_ai_coach_cards import _parse_followup
        text = "응답\n[추천: 하나만]"
        body, questions = _parse_followup(text)
        assert len(questions) == 1
        assert questions[0] == "하나만"

    def test_whitespace_handling(self):
        from src.web.views_ai_coach_cards import _parse_followup
        text = "응답\n[추천:  질문1  |  질문2  ]"
        body, questions = _parse_followup(text)
        assert len(questions) == 2
        assert questions[0] == "질문1"
        assert questions[1] == "질문2"


# ── 6. build_chat_context / _build_base_context ───────────────────────

class TestBuildContext:
    """컨텍스트 빌드 함수 테스트."""

    def test_build_base_context(self, mem_conn):
        from src.ai.chat_context import _build_base_context
        today = date.today().isoformat()
        ctx = _build_base_context(mem_conn, today)
        assert ctx["date"] == today
        assert ctx["UTRS"] == 72.5
        assert ctx["CIRS"] == 65.0
        assert ctx["ctl"] == 45.2
        assert "wellness" in ctx
        assert ctx["wellness"]["bb"] == 75
        assert len(ctx["recent_activities"]) >= 1

    def test_build_runner_profile(self, mem_conn):
        from src.ai.chat_context import _build_runner_profile
        mock_goals = type(sys)("src.training.goals")
        mock_goals.get_active_goal = lambda conn: None
        with patch.dict(sys.modules, {"src.training.goals": mock_goals}):
            profile = _build_runner_profile(mem_conn, date.today().isoformat())
        assert isinstance(profile, dict)
        assert "vo2max" in profile
        assert profile["vo2max"] == 51.0

    def test_build_chat_context_returns_string(self, mem_conn):
        from src.ai.chat_context import build_chat_context
        mock_goals = type(sys)("src.training.goals")
        mock_goals.get_active_goal = lambda conn: None
        with patch.dict(sys.modules, {"src.training.goals": mock_goals}):
            result = build_chat_context(mem_conn, "오늘 훈련 어때", provider="rule")
        assert isinstance(result, str)
        assert len(result) > 0
