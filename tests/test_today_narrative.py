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


def test_cache_key_has_r2_suffix(db_conn):
    config = {"ai": {"provider": "gemini", "gemini_api_key": "key"}}
    with patch("src.ai.chat_engine._call_provider", return_value="AI"):
        today_service.get_today_narrative(db_conn, date="2026-09-22", config=config)
    assert ai_cache.get_cached(db_conn, "today_narrative", "2026-09-01:2026-09-22:r2") is not None
    assert ai_cache.get_cached(db_conn, "today_narrative", "2026-09-01:2026-09-22") is None
