"""tests/test_narrative_cache.py — get_today_narrative() ai_cache 연동 테스트.

ADR-011 무효화 규칙을 탄 ai_cache를 today_narrative 탭으로 재사용하는 것을 검증한다.
"""
from __future__ import annotations

from unittest.mock import patch

import pytest

from src.services import today_service
from src.services._narrative import get_narrative_cache, set_narrative_cache
from src.ai import ai_cache


def _seed_metric(conn, date, name, value):
    conn.execute(
        "INSERT INTO metric_store (scope_type, scope_id, metric_name, provider, "
        "numeric_value, is_primary) VALUES ('daily', ?, ?, 'runpulse', ?, 1)",
        (date, name, value),
    )


class TestNarrativeCacheHelpers:
    def test_cache_miss_returns_none(self, db_conn):
        result = get_narrative_cache(db_conn, "2026-09-01", "2026-09-22")
        assert result is None

    def test_set_then_get_roundtrip(self, db_conn):
        payload = {"date": "2026-09-22", "text": "테스트", "source": "ai",
                   "evidence": [], "milestones": [], "highlights": {}}
        set_narrative_cache(db_conn, "2026-09-01", "2026-09-22", payload)
        result = get_narrative_cache(db_conn, "2026-09-01", "2026-09-22")
        assert result == payload

    def test_different_keys_do_not_collide(self, db_conn):
        payload_sep = {"date": "2026-09-22", "text": "9월", "source": "ai",
                       "evidence": [], "milestones": [], "highlights": {}}
        payload_aug = {"date": "2026-08-31", "text": "8월", "source": "ai",
                       "evidence": [], "milestones": [], "highlights": {}}
        set_narrative_cache(db_conn, "2026-09-01", "2026-09-22", payload_sep)
        set_narrative_cache(db_conn, "2026-08-01", "2026-08-31", payload_aug)
        assert get_narrative_cache(db_conn, "2026-09-01", "2026-09-22") == payload_sep
        assert get_narrative_cache(db_conn, "2026-08-01", "2026-08-31") == payload_aug

    def test_set_cache_failure_is_swallowed(self, db_conn):
        """set_narrative_cache가 예외 발생해도 삼키고 정상 종료한다."""
        with patch("src.ai.ai_cache.set_cached", side_effect=Exception("DB 오류")):
            # 예외 없이 호출돼야 함
            set_narrative_cache(db_conn, "2026-09-01", "2026-09-22", {"text": "x"})


class TestGetTodayNarrativeCache:
    def test_rule_fallback_not_cached(self, db_conn):
        """규칙 기반 fallback(source='rule') 결과는 캐시에 저장되지 않는다."""
        today_service.get_today_narrative(db_conn, date="2026-09-22", config=None)
        assert get_narrative_cache(db_conn, "2026-09-01", "2026-09-22") is None

    def test_ai_result_is_cached(self, db_conn):
        """AI 성공 결과(source='ai')는 캐시에 저장된다."""
        config = {"ai": {"provider": "gemini", "gemini_api_key": "key"}}
        with patch("src.ai.chat_engine._call_provider", return_value="AI 내러티브"):
            today_service.get_today_narrative(db_conn, date="2026-09-22", config=config)
        cached = get_narrative_cache(db_conn, "2026-09-01", "2026-09-22")
        assert cached is not None
        assert cached["source"] == "ai"
        assert cached["text"] == "AI 내러티브"

    def test_cache_hit_skips_ai_call(self, db_conn):
        """캐시 히트 시 AI provider가 호출되지 않는다."""
        payload = {"date": "2026-09-22", "text": "캐시된 내러티브", "source": "ai",
                   "evidence": [], "milestones": [], "highlights": {}}
        set_narrative_cache(db_conn, "2026-09-01", "2026-09-22", payload)

        config = {"ai": {"provider": "gemini", "gemini_api_key": "key"}}
        with patch("src.ai.chat_engine._call_provider") as mock_ai:
            result = today_service.get_today_narrative(db_conn, date="2026-09-22", config=config)
        mock_ai.assert_not_called()
        assert result == payload

    def test_cache_hit_returns_cached_text(self, db_conn):
        """캐시 히트 시 반환값이 캐시 내용과 동일하다."""
        payload = {"date": "2026-09-22", "text": "저장된 텍스트", "source": "ai",
                   "evidence": [], "milestones": [], "highlights": {}}
        set_narrative_cache(db_conn, "2026-09-01", "2026-09-22", payload)

        result = today_service.get_today_narrative(db_conn, date="2026-09-22", config=None)
        assert result["text"] == "저장된 텍스트"
        assert result["source"] == "ai"

    def test_past_month_uses_correct_cache_key(self, db_conn):
        """과거 달(year/month) 조회는 해당 달 시작일·말일 기준으로 별도 캐시 키를 쓴다."""
        payload = {"date": "2026-08-31", "text": "8월 캐시", "source": "ai",
                   "evidence": [], "milestones": [], "highlights": {}}
        set_narrative_cache(db_conn, "2026-08-01", "2026-08-31", payload)

        result = today_service.get_today_narrative(
            db_conn, date="2026-09-22", config=None, year=2026, month=8
        )
        assert result["text"] == "8월 캐시"

    def test_stale_cache_on_new_activity_triggers_ai(self, db_conn):
        """새 활동이 추가되면 핑거프린트가 달라져 캐시가 무효화되고 AI가 다시 호출된다."""
        # 먼저 AI 결과를 캐시
        config = {"ai": {"provider": "gemini", "gemini_api_key": "key"}}
        with patch("src.ai.chat_engine._call_provider", return_value="첫 번째 AI 결과"):
            today_service.get_today_narrative(db_conn, date="2026-09-22", config=config)

        # 새 활동 추가 → 핑거프린트 변경
        db_conn.execute(
            "INSERT INTO activity_summaries (id, source, source_id, name, activity_type, "
            "start_time, distance_m, duration_sec) VALUES (99, 'garmin', '99', 'New Run', "
            "'running', '2026-09-22T07:00:00', 10000, 3000)"
        )
        db_conn.commit()

        call_count = 0
        def _mock_ai(prov, prompt, cfg):
            nonlocal call_count
            call_count += 1
            return "두 번째 AI 결과"

        with patch("src.ai.chat_engine._call_provider", side_effect=_mock_ai):
            result = today_service.get_today_narrative(db_conn, date="2026-09-22", config=config)

        assert call_count >= 1, "캐시 무효화 후 AI가 호출돼야 한다"
        assert result["text"] == "두 번째 AI 결과"

    def test_cache_save_failure_does_not_raise(self, db_conn):
        """캐시 저장 실패 시 예외 없이 AI 결과를 그대로 반환한다."""
        config = {"ai": {"provider": "gemini", "gemini_api_key": "key"}}
        with patch("src.ai.chat_engine._call_provider", return_value="AI 텍스트"), \
             patch("src.ai.ai_cache.set_cached", side_effect=Exception("저장 실패")):
            result = today_service.get_today_narrative(db_conn, date="2026-09-22", config=config)
        assert result["source"] == "ai"
        assert result["text"] == "AI 텍스트"
