"""scheduler_policy(T3) — 휴면 경계·백오프·지터·인증 중지·정렬 표 기반 검사."""
import random
from datetime import datetime, timedelta

import pytest

from src.sync import scheduler_policy as P

NOW = datetime(2026, 11, 6, 12, 0, 0)


@pytest.mark.parametrize("days,tier", [(6.9, "active"), (7.1, "slow"), (29.9, "slow"), (30.1, "dormant")])
def test_activity_tier_boundaries(days, tier):
    assert P.activity_tier(NOW - timedelta(days=days), NOW) == tier


def test_tier_no_record_and_pinned_are_active():
    assert P.activity_tier(None, NOW) == "active"
    assert P.activity_tier(NOW - timedelta(days=100), NOW, pinned=True) == "active"


@pytest.mark.parametrize("n,hours", [(0, 4), (1, 8), (2, 16), (3, 24), (4, 24), (5, 24), (6, 24)])
def test_backoff_interval(n, hours):
    assert P.backoff_interval(4, n) == timedelta(hours=hours)


def test_backoff_daily_interval_stays_24h():
    assert P.backoff_interval(24, 0) == timedelta(hours=24)
    assert P.backoff_interval(24, 3) == timedelta(hours=24)


def test_effective_interval_slow():
    assert P.effective_interval_h(4, "slow") == 24
    assert P.effective_interval_h(4, "active") == 4


def test_jitter_bounds_and_seeded():
    a = [P.jitter(4, random.Random(1)) for _ in range(3)]
    assert a[0] == a[1] == a[2]
    for h, cap in ((1, 360), (4, 600), (24, 600)):
        rng = random.Random(7)
        assert all(timedelta(0) <= P.jitter(h, rng) <= timedelta(seconds=cap) for _ in range(200))


def test_initial_due_matches_legacy():
    last = NOW - timedelta(hours=3)
    assert P.initial_due(last, 4, NOW) == last + timedelta(hours=4)
    assert P.initial_due(None, 4, NOW) == NOW


def test_next_due_slow_uses_24h():
    d = P.next_due(NOW, 4, fail_streak=0, tier="slow", rng=random.Random(0))
    assert timedelta(hours=24) <= d - NOW <= timedelta(hours=24, minutes=10)


def test_classify():
    assert P.classify({"garmin": "completed", "strava": "failed"}) == "ok"
    assert P.classify({"garmin": "auth_required", "strava": "auth_required"}) == "auth"
    assert P.classify({"garmin": "auth_required", "strava": "failed"}) == "fail"
    assert P.classify({}) == "fail"


def test_auth_streak_suspends_at_three_and_resets_on_success():
    s, sus = {}, []
    for _ in range(3):
        s, sus = P.update_auth_streak(s, {"garmin": "auth_required", "strava": "completed"})
    assert s == {"garmin": 3} and sus == ["garmin"]
    s, sus = P.update_auth_streak(s, {"garmin": "completed"})
    assert s == {} and sus == []


def test_next_fail_streak():
    assert P.next_fail_streak("ok", 5) == 0
    assert P.next_fail_streak("timeout", 1) == 2
    assert P.next_fail_streak("skipped_busy", 2) == 2


def test_order_candidates_overdue_first():
    due = {"b": NOW - timedelta(hours=1), "a": NOW - timedelta(hours=5), "c": NOW + timedelta(hours=1)}
    assert P.order_candidates(due, NOW) == ["a", "b"]


def test_pinned_uids_and_auto_cfg():
    assert P.pinned_uids(" a@x.com, ,b ") == frozenset({"a@x.com", "b"})
    assert P.auto_cfg({}) == (True, 4, 2)
    assert P.auto_cfg({"auto_sync": {"enabled": False, "interval_hours": 0, "days": 5}}) == (False, 1, 5)
