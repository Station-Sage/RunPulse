"""RateLimiter 단위 테스트."""

from src.sync.rate_limiter import RateLimiter, RateLimitPolicy, RATE_POLICIES


class TestRateLimitPolicy:
    def test_four_sources_defined(self):
        for s in ("garmin", "strava", "intervals", "runalyze"):
            assert s in RATE_POLICIES

    def test_garmin_conservative(self):
        p = RATE_POLICIES["garmin"]
        assert p.per_request_sleep >= 2.0
        assert p.backoff_base >= 120

    def test_strava_window(self):
        p = RATE_POLICIES["strava"]
        assert p.window_limit == 200
        assert p.window_seconds == 900


class TestRateLimiter:
    def test_call_count(self):
        rl = RateLimiter("garmin", sleep_fn=lambda _: None)
        assert rl.call_count == 0
        rl.pre_request()
        rl.post_request(True)
        assert rl.call_count == 1

    def test_handle_rate_limit_retry(self):
        rl = RateLimiter("garmin", sleep_fn=lambda _: None)
        assert rl.handle_rate_limit() is True  # 1st retry
        assert rl.handle_rate_limit() is True  # 2nd
        assert rl.handle_rate_limit() is True  # 3rd
        assert rl.handle_rate_limit() is False  # 4th → exceeded

    def test_429_reset_on_success(self):
        rl = RateLimiter("garmin", sleep_fn=lambda _: None)
        rl.handle_rate_limit()
        rl.post_request(success=True)
        assert rl._consecutive_429 == 0

    def test_should_stop_daily(self):
        rl = RateLimiter("strava", sleep_fn=lambda _: None)
        rl._call_count = 1999
        assert rl.should_stop() is False
        rl._call_count = 2000
        assert rl.should_stop() is True

    def test_unknown_source_default(self):
        rl = RateLimiter("coros", sleep_fn=lambda _: None)
        assert rl.policy.per_request_sleep == 1.0
