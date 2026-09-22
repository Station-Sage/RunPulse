"""tests/test_ai_context.py — Phase 5-D AI 컨텍스트 빌더 테스트."""
import pytest

from src.ai.ai_context import (
    build_activity_analysis,
    build_ai_context,
    build_context,
    build_daily_briefing,
    format_activity_context,
    format_context_text,
)

DATE = "2026-04-03"


@pytest.fixture
def conn(db_conn):
    c = db_conn

    c.execute("""
        INSERT INTO activity_summaries
            (source, source_id, name, activity_type, start_time,
             distance_m, duration_sec, avg_pace_sec_km, avg_hr, max_hr, elevation_gain)
        VALUES ('garmin', 'g1', '오후 달리기', 'running', '2026-04-03T18:00:00Z',
                10020, 3135, 312.8, 155, 178, 120.5)
    """)
    act_id = c.execute(
        "SELECT id FROM activity_summaries WHERE source='garmin'"
    ).fetchone()[0]

    c.execute("""
        INSERT INTO daily_wellness
            (date, sleep_score, sleep_duration_sec, hrv_last_night, resting_hr, avg_stress)
        VALUES (?, 82, 25920, 42.0, 52, 32)
    """, (DATE,))

    daily_metrics = [
        ("daily", DATE, "utrs",         "readiness",  "runpulse:formula_v1", 72.3, None, None, 0.8, 1),
        ("daily", DATE, "cirs",         "readiness",  "runpulse:formula_v1", 28.1, None, None, None, 1),
        ("daily", DATE, "crs",          "readiness",  "runpulse:formula_v1", 65.0, None, None, None, 1),
        ("daily", DATE, "ctl",          "load",       "runpulse:formula_v1", 45.2, None, None, None, 1),
        ("daily", DATE, "atl",          "load",       "runpulse:formula_v1", 52.1, None, None, None, 1),
        ("daily", DATE, "tsb",          "load",       "runpulse:formula_v1", -6.9, None, None, None, 1),
        ("daily", DATE, "ramp_rate",    "load",       "runpulse:formula_v1",  2.3, None, None, None, 1),
        ("daily", DATE, "darp_5k_sec",  "prediction", "runpulse:formula_v1", 1335, None, None, None, 1),
        ("daily", DATE, "darp_marathon_sec", "prediction", "runpulse:formula_v1", 12900, None, None, None, 1),
    ]
    act_metrics = [
        ("activity", str(act_id), "trimp", "load", "runpulse:formula_v1", 91.2, None, None, 0.9, 1),
    ]
    c.executemany(
        "INSERT INTO metric_store"
        " (scope_type, scope_id, metric_name, category, provider,"
        "  numeric_value, text_value, json_value, confidence, is_primary)"
        " VALUES (?,?,?,?,?,?,?,?,?,?)",
        daily_metrics + act_metrics,
    )
    c.commit()
    return c, act_id


# build_daily_briefing

def test_build_daily_briefing_full(conn):
    c, _ = conn
    result = build_daily_briefing(c, DATE)
    assert isinstance(result, str)
    assert len(result) > 0
    assert DATE in result


def test_build_daily_briefing_contains_readiness(conn):
    c, _ = conn
    result = build_daily_briefing(c, DATE)
    assert "UTRS" in result
    assert "CIRS" in result


def test_build_daily_briefing_contains_fitness(conn):
    c, _ = conn
    result = build_daily_briefing(c, DATE)
    assert "CTL" in result
    assert "ATL" in result
    assert "TSB" in result


def test_build_daily_briefing_no_wellness(db_conn):
    """데이터 없어도 에러 없이 빈 섹션 처리."""
    result = build_daily_briefing(db_conn, DATE)
    assert isinstance(result, str)
    assert DATE in result


def test_build_daily_briefing_race_predictions(conn):
    c, _ = conn
    result = build_daily_briefing(c, DATE)
    assert "5K" in result or "DARP" in result or "레이스" in result


def test_build_daily_briefing_format(conn):
    """None 메트릭은 출력하지 않음 — 빈 줄 최소화."""
    c, _ = conn
    result = build_daily_briefing(c, DATE)
    # 연속된 빈 줄이 없어야 함
    assert "\n\n\n" not in result


# build_activity_analysis

def test_build_activity_analysis_full(conn):
    c, act_id = conn
    result = build_activity_analysis(c, act_id)
    assert isinstance(result, str)
    assert "오후 달리기" in result


def test_build_activity_analysis_contains_core(conn):
    c, act_id = conn
    result = build_activity_analysis(c, act_id)
    assert "km" in result  # 거리 포맷
    assert "bpm" in result  # 심박


def test_build_activity_analysis_no_rp_metrics(db_conn):
    """활동 없으면 에러 없이 빈 분석 반환."""
    result = build_activity_analysis(db_conn, 9999)
    assert isinstance(result, str)


# build_ai_context

def test_build_ai_context_daily_only(conn):
    c, _ = conn
    result = build_ai_context(c, DATE)
    assert DATE in result
    assert "---" not in result  # activity 없으면 구분선 없음


def test_build_ai_context_with_activity(conn):
    c, act_id = conn
    result = build_ai_context(c, DATE, activity_id=act_id)
    assert "---" in result  # briefing + analysis 구분선 포함
    assert "오후 달리기" in result


# build_context (BUG-CHAT-RULE-FALLBACK 수정 — chat_engine_rules.rule_based_response·
# briefing.py가 쓰는 dict 컨텍스트)

def test_build_context_today_activity(conn):
    c, _ = conn
    ctx = build_context(c, DATE)
    assert ctx["date"] == DATE
    act = ctx["today_activity"]
    assert act is not None
    assert act["distance_km"] == pytest.approx(10.02)
    assert act["avg_hr"] == 155


def test_build_context_no_activity(db_conn):
    ctx = build_context(db_conn, DATE)
    assert ctx["today_activity"] is None


def test_build_context_fitness(conn):
    c, _ = conn
    ctx = build_context(c, DATE)
    assert ctx["fitness"]["ctl"] == pytest.approx(45.2)
    assert ctx["fitness"]["atl"] == pytest.approx(52.1)
    assert ctx["fitness"]["tsb"] == pytest.approx(-6.9)


def test_build_context_no_data_graceful(db_conn):
    """데이터 없어도 에러 없이 빈/None 값으로 채워짐 (calculate_weekly_score는 0점짜리
    유효한 결과를 반환하므로 weekly는 dict 형태 유지, 나머지는 None/빈 리스트)."""
    ctx = build_context(db_conn, DATE)
    assert ctx["fitness"] == {
        "ctl": None, "atl": None, "tsb": None,
        "vo2max_garmin": None, "vo2max_runalyze": None,
    }
    assert isinstance(ctx["weekly"], dict)
    assert isinstance(ctx["trends_4w"], list)
    assert ctx["goal"] is None


def test_format_context_text_is_string(conn):
    c, _ = conn
    ctx = build_context(c, DATE)
    text = format_context_text(ctx)
    assert isinstance(text, str)
    assert DATE in text
    assert "CTL" in text


def test_format_context_text_no_data_graceful(db_conn):
    ctx = build_context(db_conn, DATE)
    text = format_context_text(ctx)
    assert isinstance(text, str)
    assert "오늘 활동: 없음" in text


def test_format_activity_context_is_string(conn):
    c, act_id = conn
    text = format_activity_context(c, act_id)
    assert isinstance(text, str)
    assert "km" in text


def test_format_activity_context_missing_activity(db_conn):
    text = format_activity_context(db_conn, 9999)
    assert isinstance(text, str)
    assert "없음" in text


# rule_based_response — BUG-CHAT-RULE-FALLBACK 회귀 테스트 (ImportError 재발 방지)

def test_rule_based_response_does_not_raise(conn):
    from src.ai.chat_engine_rules import rule_based_response

    c, _ = conn
    result = rule_based_response(c, "오늘 훈련 강도는 어느 정도가 좋을까?")
    assert isinstance(result, str)
    assert len(result) > 0


def test_rule_based_response_no_data_graceful(db_conn):
    from src.ai.chat_engine_rules import rule_based_response

    result = rule_based_response(db_conn, "이번주 어때?")
    assert isinstance(result, str)
