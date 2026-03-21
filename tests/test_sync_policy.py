"""sync_policy / sync_state 단위 테스트 — 실제 API 호출 없음 (목업)."""
from __future__ import annotations

import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

from src.utils.sync_policy import (
    POLICIES,
    SyncGuardResult,
    check_incremental_guard,
    check_range_guard,
    should_reduce_expensive_calls,
    _fmt_duration,
)


# ── _fmt_duration ─────────────────────────────────────────────────────────
class TestFmtDuration:
    def test_seconds(self):
        assert _fmt_duration(45) == "45초"

    def test_minutes(self):
        assert _fmt_duration(120) == "2분"

    def test_hours(self):
        assert _fmt_duration(3600) == "1시간"

    def test_hours_and_minutes(self):
        assert _fmt_duration(3660) == "1시간 1분"


# ── check_incremental_guard ───────────────────────────────────────────────
class TestIncrementalGuard:
    def test_no_last_sync_always_allowed(self):
        """마지막 동기화 없으면 항상 허용."""
        result = check_incremental_guard("garmin", last_sync_at=None)
        assert result.allowed is True
        assert result.reason == "ok"

    def test_unknown_service_always_allowed(self):
        """정책 없는 서비스는 항상 허용."""
        result = check_incremental_guard("unknown_svc", last_sync_at=datetime.now())
        assert result.allowed is True

    def test_within_cooldown_blocked(self):
        """cooldown 이내이면 차단."""
        now = datetime.now()
        last = now - timedelta(seconds=30)  # Garmin = 300초 cooldown
        result = check_incremental_guard("garmin", last_sync_at=last, now=now)
        assert result.allowed is False
        assert result.reason == "cooldown"
        assert result.retry_after_sec is not None
        assert result.retry_after_sec > 0
        assert result.message_ko is not None
        assert "Garmin" in result.message_ko

    def test_after_cooldown_allowed(self):
        """cooldown 이후이면 허용."""
        now = datetime.now()
        last = now - timedelta(seconds=400)  # 300초 초과
        result = check_incremental_guard("garmin", last_sync_at=last, now=now)
        assert result.allowed is True
        assert result.reason == "ok"

    @pytest.mark.parametrize("service", ["garmin", "strava", "intervals", "runalyze"])
    def test_all_services_have_policies(self, service):
        """4개 서비스 모두 정책이 정의되어 있어야 함."""
        assert service in POLICIES
        policy = POLICIES[service]
        assert policy.min_incremental_interval_sec > 0
        assert policy.recommended_max_days > 0
        assert policy.hard_max_days >= policy.recommended_max_days

    def test_strava_shorter_cooldown_than_garmin(self):
        """Strava cooldown은 Garmin보다 짧다."""
        assert POLICIES["strava"].min_incremental_interval_sec < POLICIES["garmin"].min_incremental_interval_sec

    def test_runalyze_longest_cooldown(self):
        """Runalyze cooldown이 가장 길다 (free 계정 읽기 제한)."""
        assert POLICIES["runalyze"].min_incremental_interval_sec >= max(
            POLICIES[s].min_incremental_interval_sec for s in ["garmin", "strava", "intervals"]
        )


# ── check_range_guard ─────────────────────────────────────────────────────
class TestRangeGuard:
    def test_within_recommended_ok(self):
        """권장 범위 이내이면 허용."""
        result = check_range_guard("garmin", days=14)
        assert result.allowed is True
        assert result.reason == "ok"

    def test_exceed_hard_max_blocked(self):
        """hard_max 초과 시 차단."""
        result = check_range_guard("garmin", days=200)  # hard_max=90
        assert result.allowed is False
        assert result.reason == "range_too_large"
        assert result.adjusted_days == POLICIES["garmin"].recommended_max_days
        assert "Garmin" in result.message_ko

    def test_between_recommended_and_hard_warned(self):
        """권장~hard_max 사이이면 허용 + 경고."""
        result = check_range_guard("garmin", days=60)  # recommended=30, hard=90
        assert result.allowed is True
        assert result.reason == "range_auto_reduced"
        assert result.message_ko is not None

    def test_unknown_service_always_allowed(self):
        result = check_range_guard("unknown", days=9999)
        assert result.allowed is True

    def test_intervals_most_lenient(self):
        """Intervals.icu hard_max가 가장 크다."""
        assert POLICIES["intervals"].hard_max_days >= max(
            POLICIES[s].hard_max_days for s in ["garmin", "strava", "runalyze"]
        )


# ── should_reduce_expensive_calls ─────────────────────────────────────────
class TestReduceExpensiveCalls:
    def test_below_threshold_false(self):
        """사용량이 임계치 미만이면 False."""
        result = should_reduce_expensive_calls("strava", {"usage": 100, "limit": 200})
        assert result is False

    def test_at_threshold_true(self):
        """사용량이 임계치(80%) 이상이면 True."""
        result = should_reduce_expensive_calls("strava", {"usage": 160, "limit": 200})
        assert result is True

    def test_zero_limit_false(self):
        """limit=0이면 항상 False (0 나누기 방지)."""
        result = should_reduce_expensive_calls("strava", {"usage": 100, "limit": 0})
        assert result is False

    def test_empty_state_false(self):
        """rate_state 없으면 False."""
        result = should_reduce_expensive_calls("strava", {})
        assert result is False

    def test_unknown_service_false(self):
        result = should_reduce_expensive_calls("unknown", {"usage": 999, "limit": 1000})
        assert result is False


# ── sync_state (파일 I/O 목업) ────────────────────────────────────────────
class TestSyncState:
    def test_mark_running_and_finished(self, tmp_path):
        """mark_running → mark_finished 흐름 검증."""
        state_file = tmp_path / "sync_state.json"

        with patch("src.utils.sync_state._state_path", return_value=state_file):
            from src.utils.sync_state import (
                mark_running, mark_finished, is_running, get_last_sync_at
            )
            # 초기 상태
            assert is_running("garmin") is False

            mark_running("garmin", "basic")
            assert is_running("garmin") is True

            mark_finished("garmin", count=5, partial=False)
            assert is_running("garmin") is False

            last = get_last_sync_at("garmin")
            assert last is not None
            assert isinstance(last, datetime)

    def test_set_retry_after(self, tmp_path):
        """set_retry_after → get_retry_after_sec 흐름 검증."""
        state_file = tmp_path / "sync_state.json"

        with patch("src.utils.sync_state._state_path", return_value=state_file):
            from src.utils.sync_state import set_retry_after, get_retry_after_sec, clear_retry_after

            set_retry_after("strava", 900)
            remain = get_retry_after_sec("strava")
            assert remain is not None
            assert 800 < remain <= 900  # 파일 쓰기/읽기 시간 오차 허용

            clear_retry_after("strava")
            assert get_retry_after_sec("strava") is None

    def test_duplicate_running_guard(self, tmp_path):
        """is_running이 True인 상태에서 중복 실행 차단 확인."""
        state_file = tmp_path / "sync_state.json"

        with patch("src.utils.sync_state._state_path", return_value=state_file):
            from src.utils.sync_state import mark_running, is_running

            mark_running("intervals", "basic")
            # 중복 실행 시도 — 웹 레이어에서 is_running으로 차단
            assert is_running("intervals") is True


# ── _parse_rate_limit (strava 내부 함수) ──────────────────────────────────
class TestParseRateLimit:
    def test_parse_valid_headers(self):
        """Strava 표준 rate limit 헤더 파싱."""
        from src.sync.strava import _parse_rate_limit

        headers = {
            "x-ratelimit-limit": "200,2000",
            "x-ratelimit-usage": "150,1500",
        }
        state = _parse_rate_limit(headers)
        assert state["limit"] == 200
        assert state["usage"] == 150
        assert state["daily_limit"] == 2000
        assert state["daily_usage"] == 1500

    def test_parse_empty_headers(self):
        from src.sync.strava import _parse_rate_limit

        state = _parse_rate_limit({})
        assert state == {}

    def test_near_limit_detection(self):
        """rate 80% 이상이면 고비용 호출 축소 판단."""
        from src.sync.strava import _parse_rate_limit

        headers = {
            "x-ratelimit-limit": "200,2000",
            "x-ratelimit-usage": "165,1200",  # 165/200 = 82.5%
        }
        state = _parse_rate_limit(headers)
        assert should_reduce_expensive_calls("strava", state) is True
