"""다중 사용자 스케줄러 정책 — due·휴면·지터·백오프·인증 중지 순수 함수(부작용·I/O 없음, multiuser-sync §3.3·§3.4)."""
from __future__ import annotations

import os
import random
from datetime import datetime, timedelta

MAX_CONCURRENT_USERS = 2
SERVICE_SLOTS = {"garmin": 1, "strava": 2, "intervals": 2, "runalyze": 2}
JITTER_MAX_SEC = 600            # 10분
JITTER_FRACTION = 0.1           # interval 의 10%
BACKOFF_CAP_H = 24
SLOW_AFTER_DAYS = 7             # 초과 시 24h 주기
DORMANT_AFTER_DAYS = 30         # 초과 시 건너뜀
SLOW_INTERVAL_H = 24
AUTH_SUSPEND_STREAK = 3
AUTH_SUSPEND_SEC = 30 * 86400
BUSY_DEFER_SEC = 15 * 60
RUN_TIMEOUT_SEC = 20 * 60
INTERVAL_CHOICES = (1, 2, 4, 6, 12, 24)
DEFAULT_INTERVAL_H = 4
DEFAULT_DAYS = 2


def pinned_uids(env: str | None = None) -> frozenset[str]:
    """`SYNC_PINNED_UIDS`(콤마 구분) — 휴면 규칙 미적용 uid 집합."""
    raw = os.environ.get("SYNC_PINNED_UIDS", "") if env is None else env
    return frozenset(u.strip() for u in raw.split(",") if u.strip())


def auto_cfg(config: dict) -> tuple[bool, int, int]:
    """config.auto_sync → (enabled, interval_h, days). legacy start() 와 같은 보정(최소 1)."""
    cfg = config.get("auto_sync") or {}
    interval = max(1, int(cfg.get("interval_hours", DEFAULT_INTERVAL_H)))
    days = max(1, int(cfg.get("days", DEFAULT_DAYS)))
    return bool(cfg.get("enabled", True)), interval, days


def activity_tier(last_active: datetime | None, now: datetime, *, pinned: bool = False) -> str:
    """active(≤7일·기록 없음·pinned) | slow(7~30일) | dormant(30일 초과)."""
    if pinned or last_active is None:
        return "active"
    idle = now - last_active
    if idle > timedelta(days=DORMANT_AFTER_DAYS):
        return "dormant"
    if idle > timedelta(days=SLOW_AFTER_DAYS):
        return "slow"
    return "active"


def effective_interval_h(interval_h: int, tier: str) -> int:
    """slow 는 max(interval, 24h). 그 외 설정값 그대로."""
    return max(interval_h, SLOW_INTERVAL_H) if tier == "slow" else interval_h


def backoff_interval(interval_h: int, fail_streak: int) -> timedelta:
    """fail_streak=n → min(interval × 2^n, 24h). n=0 이면 interval."""
    n = max(0, int(fail_streak))
    hours = min(interval_h * (2 ** min(n, 10)), max(BACKOFF_CAP_H, interval_h))
    return timedelta(hours=hours)


def jitter(interval_h: int, rng: random.Random) -> timedelta:
    """uniform(0, min(10분, 0.1 × interval))."""
    return timedelta(seconds=rng.uniform(0, min(JITTER_MAX_SEC, JITTER_FRACTION * interval_h * 3600)))


def initial_due(last_auto_run: datetime | None, interval_h: int, now: datetime) -> datetime:
    """상태 행이 없을 때 원장 기준 due — legacy 루프 판정(last + interval, 없으면 즉시)과 같다."""
    return last_auto_run + timedelta(hours=interval_h) if last_auto_run else now


def next_due(now: datetime, interval_h: int, *, fail_streak: int, tier: str, rng: random.Random) -> datetime:
    """실행 후 다음 due = now + backoff(effective interval) + jitter."""
    eff = effective_interval_h(interval_h, tier)
    return now + backoff_interval(eff, fail_streak) + jitter(eff, rng)


def classify(statuses: dict[str, str | None]) -> str:
    """원장 job 상태들 → ok(하나라도 completed) | auth(전부 auth_required) | fail."""
    vals = list(statuses.values())
    if any(s == "completed" for s in vals):
        return "ok"
    if vals and all(s == "auth_required" for s in vals):
        return "auth"
    return "fail"


def update_auth_streak(streak: dict[str, int], statuses: dict[str, str | None]) -> tuple[dict[str, int], list[str]]:
    """소스별 연속 auth_required 수 갱신. (새 streak, 중지할 소스 목록[≥3])."""
    out = dict(streak)
    for svc, st in statuses.items():
        if st == "auth_required":
            out[svc] = out.get(svc, 0) + 1
        elif st == "completed":
            out.pop(svc, None)
    return out, sorted(s for s, n in out.items() if n >= AUTH_SUSPEND_STREAK and statuses.get(s) == "auth_required")


def next_fail_streak(result: str, fail_streak: int) -> int:
    """ok 면 0, fail/timeout/auth 면 +1, skipped_* 는 유지."""
    if result == "ok":
        return 0
    if result in ("fail", "timeout", "auth"):
        return fail_streak + 1
    return fail_streak


def order_candidates(due: dict[str, datetime], now: datetime) -> list[str]:
    """연체가 긴 순(next_due 오름차순), 동률은 uid 순."""
    return sorted((u for u, d in due.items() if d <= now), key=lambda u: (due[u], u))
