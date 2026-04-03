"""소스별 API Rate-Limit 관리.

테스트 시 sleep_fn=lambda _: None 으로 대기를 제거합니다.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Callable, Optional

log = logging.getLogger(__name__)


@dataclass
class RateLimitPolicy:
    """소스별 rate-limit 정책."""

    per_request_sleep: float
    max_retries: int = 3
    backoff_base: float = 60.0
    backoff_multiplier: float = 2.0
    daily_limit: int = 0
    window_limit: int = 0
    window_seconds: int = 900


RATE_POLICIES: dict[str, RateLimitPolicy] = {
    "garmin": RateLimitPolicy(
        per_request_sleep=2.0,
        max_retries=3,
        backoff_base=120.0,
        backoff_multiplier=2.0,
    ),
    "strava": RateLimitPolicy(
        per_request_sleep=0.5,
        max_retries=3,
        backoff_base=60.0,
        daily_limit=2000,
        window_limit=200,
        window_seconds=900,
    ),
    "intervals": RateLimitPolicy(
        per_request_sleep=0.3,
        max_retries=2,
        backoff_base=30.0,
    ),
    "runalyze": RateLimitPolicy(
        per_request_sleep=1.0,
        max_retries=2,
        backoff_base=60.0,
    ),
}


class RateLimiter:
    """소스별 rate-limit 추적 및 대기."""

    def __init__(
        self,
        source: str,
        *,
        sleep_fn: Optional[Callable[[float], None]] = None,
    ):
        self.source = source
        self.policy = RATE_POLICIES.get(
            source, RateLimitPolicy(per_request_sleep=1.0)
        )
        self._call_count = 0
        self._window_calls = 0
        self._window_start = time.time()
        self._consecutive_429 = 0
        self._sleep = sleep_fn or time.sleep

    def pre_request(self):
        """요청 전 호출. 필요하면 대기."""
        if self.policy.window_limit > 0:
            now = time.time()
            if now - self._window_start > self.policy.window_seconds:
                self._window_calls = 0
                self._window_start = now
            if self._window_calls >= self.policy.window_limit:
                wait = self.policy.window_seconds - (now - self._window_start)
                if wait > 0:
                    log.warning(
                        "[%s] Window limit reached. Waiting %ds",
                        self.source, int(wait),
                    )
                    self._sleep(wait)
                    self._window_calls = 0
                    self._window_start = time.time()
        self._sleep(self.policy.per_request_sleep)

    def post_request(self, success: bool = True):
        """요청 후 호출."""
        self._call_count += 1
        self._window_calls += 1
        if success:
            self._consecutive_429 = 0

    def handle_rate_limit(self) -> bool:
        """429 응답 시 호출. True=재시도 가능, False=포기."""
        self._consecutive_429 += 1
        if self._consecutive_429 > self.policy.max_retries:
            log.error(
                "[%s] Max retries (%d) exceeded.",
                self.source, self.policy.max_retries,
            )
            return False
        wait = self.policy.backoff_base * (
            self.policy.backoff_multiplier ** (self._consecutive_429 - 1)
        )
        log.warning(
            "[%s] Rate limited (429). Retry %d/%d. Waiting %ds",
            self.source, self._consecutive_429,
            self.policy.max_retries, int(wait),
        )
        self._sleep(wait)
        return True

    @property
    def call_count(self) -> int:
        return self._call_count

    def should_stop(self) -> bool:
        """일일 제한 도달 여부."""
        if (
            self.policy.daily_limit > 0
            and self._call_count >= self.policy.daily_limit
        ):
            log.warning(
                "[%s] Daily limit (%d) reached.",
                self.source, self.policy.daily_limit,
            )
            return True
        return False
