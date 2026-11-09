"""today_narrative 테스트 — 위임 경로, 비러닝 별도 한 줄(ADR-051), 규칙 fallback."""
from __future__ import annotations

from unittest.mock import patch

from src.services import today_narrative, today_service
from src.ai import ai_cache


def _seed(conn, aid, atype, start, dist, dur):
    conn.execute(
        "INSERT INTO activity_summaries (id, source, source_id, name, activity_type, "
        "start_time, distance_m, duration_sec) VALUES (?, 'garmin', ?, 'x', ?, ?, ?, ?)",
        (aid, str(aid), atype, start, dist, dur),
    )


def test_service_delegates_to_narrative_module(db_conn):
    with patch.object(today_narrative, "get_today_narrative", return_value={"ok": 1}) as m:
        out = today_service.get_today_narrative(db_conn, date="2026-09-22")
    assert out == {"ok": 1}
    assert m.call_args.kwargs["date"] == "2026-09-22"


def test_highlights_other_carries_non_running(db_conn):
    _seed(db_conn, 1, "running", "2026-09-10T07:00:00", 10000, 3000)
    _seed(db_conn, 2, "lap_swimming", "2026-09-11T07:00:00", 1000, 1800)
    db_conn.commit()
    out = today_service.get_today_narrative(db_conn, date="2026-09-22", config=None)
    hl = out["highlights"]
    assert hl["activity_count"] == 1
    assert hl["total_distance_km"] == 10.0
    assert [o["family"] for o in hl["other"]] == ["swimming"]


def test_prompt_includes_other_line(db_conn):
    _seed(db_conn, 1, "running", "2026-09-10T07:00:00", 10000, 3000)
    _seed(db_conn, 2, "lap_swimming", "2026-09-11T07:00:00", 1000, 1800)
    db_conn.commit()
    config = {"ai": {"provider": "gemini", "gemini_api_key": "key"}}
    seen = {}

    def fake(prov, prompt, cfg):
        seen["p"] = prompt
        return "AI"

    with patch("src.ai.chat_engine._call_provider", side_effect=fake):
        today_service.get_today_narrative(db_conn, date="2026-09-22", config=config)
    assert "그 외 수영 1회" in seen["p"]


def test_rule_fallback_source_and_no_other(db_conn):
    out = today_service.get_today_narrative(db_conn, date="2026-09-22", config=None)
    assert out["source"] == "rule"
    assert out["highlights"]["other"] == []


def test_cache_key_has_r3_suffix(db_conn):
    _seed(db_conn, 902, "running", "2026-09-10T06:00:00", 5000, 1800)
    config = {"ai": {"provider": "gemini", "gemini_api_key": "key"}}
    with patch("src.ai.chat_engine._call_provider", return_value="AI"):
        today_service.get_today_narrative(db_conn, date="2026-09-22", config=config)
    assert ai_cache.get_cached(db_conn, "today_narrative", "2026-09-01:2026-09-22:cur:r3") is not None
    assert ai_cache.get_cached(db_conn, "today_narrative", "2026-09-01:2026-09-22:r2") is None


def test_empty_month_skips_ai_and_is_neutral(db_conn):
    """활동 0건인 달은 AI 를 부르지 않고 미수집/미기록을 구분한 중립 문구(T-26·T-21)."""
    config = {"ai": {"provider": "gemini", "gemini_api_key": "key"}}
    with patch("src.ai.chat_engine._call_provider", return_value="러닝이 전혀 없었다") as call:
        out = today_service.get_today_narrative(db_conn, config=config, year=2026, month=5)
    call.assert_not_called()
    assert out["source"] == "rule" and "아직 수집된 활동이 없어요" in out["text"]


def test_empty_month_with_other_data_names_period(db_conn):
    """다른 달에 활동이 있으면 '그 달에는 기록된 활동이 없어요'(평가 없이)."""
    _seed(db_conn, 901, "running", "2026-09-10T06:00:00", 5000, 1800)
    out = today_service.get_today_narrative(db_conn, config=None, year=2026, month=5)
    assert out["text"] == "2026년 5월에는 기록된 활동이 없어요."
