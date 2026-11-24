"""pacing.py — 세션·주간 rate_limit 기반 페이싱 판정."""
from datetime import datetime
from zoneinfo import ZoneInfo

from scripts.autopilot import pacing, settings

KST = ZoneInfo("Asia/Seoul")


def _ts(y, m, d, h=0):
    return datetime(y, m, d, h, tzinfo=KST).timestamp()


def _e(rtype, util, reset, status="allowed", ts=0):
    return {"ts": ts, "rate_limit": {"rateLimitType": rtype, "utilization": util, "resetsAt": reset, "status": status}}


def test_week_start_is_previous_thursday_22():
    # 2026-11-23(월) → 직전 목요일 11-19 22:00
    assert pacing.week_start(_ts(2026, 11, 23, 12)) == _ts(2026, 11, 19, 22)
    # 목요일 21시(리셋 전) → 그 전주 목요일
    assert pacing.week_start(_ts(2026, 11, 26, 21)) == _ts(2026, 11, 19, 22)
    assert pacing.week_start(_ts(2026, 11, 26, 23)) == _ts(2026, 11, 26, 22)


def test_session_ceiling_blocks_until_reset():
    now = _ts(2026, 11, 23, 12)
    r = pacing.check(now, [_e("five_hour", 0.9, now + 1800)])
    assert not r.allowed and r.resume_at == now + 1800


def test_expired_observation_ignored():
    now = _ts(2026, 11, 23, 12)
    assert pacing.check(now, [_e("five_hour", 0.99, now - 10)]).allowed


def test_weekly_pace_target_grows_with_time():
    reset = _ts(2026, 11, 26, 22)
    early = pacing.weekly_target(reset - 6.9 * 86400, reset)
    late = pacing.weekly_target(reset - 0.1 * 86400, reset)
    assert settings.PACE_FLOOR <= early < late <= settings.WEEK_CEILING


def test_weekly_over_target_blocks_and_under_allows():
    reset = _ts(2026, 11, 26, 22)
    now = reset - 6 * 86400
    assert not pacing.check(now, [_e("seven_day", 0.7, reset)]).allowed
    assert pacing.check(now, [_e("seven_day", 0.1, reset)]).allowed


def test_fallback_when_no_session_observation(monkeypatch):
    monkeypatch.setattr(settings, "FALLBACK_SESSION_MAX_RUNS", 2)
    now = _ts(2026, 11, 23, 12)
    runs = [{"ts": now - 60, "cost_usd": 0.1}, {"ts": now - 30, "cost_usd": 0.1}]
    assert not pacing.check(now, runs).allowed
    assert pacing.check(now, runs[:1]).allowed


def test_fallback_ignores_entries_before_expired_window_reset():
    import time
    from scripts.autopilot import pacing, settings
    now = time.time()
    rl = {"rateLimitType": "five_hour", "resetsAt": now - 600, "status": "allowed"}
    old = [{"ts": now - 3000 - i, "unit_id": "u", "cost_usd": 0.01} for i in range(settings.FALLBACK_SESSION_MAX_RUNS)]
    old[0]["rate_limit"] = rl
    assert pacing.check(now, sorted(old, key=lambda e: e["ts"])).allowed


def test_fallback_excludes_audit_ask_entries(monkeypatch):
    monkeypatch.setattr(settings, "FALLBACK_SESSION_MAX_RUNS", 2)
    now = _ts(2026, 11, 23, 12)
    runs = [{"ts": now - 60, "unit_id": "audit-ask:sonnet", "cost_usd": 0.1},
            {"ts": now - 30, "unit_id": "audit-ask:sonnet", "cost_usd": 0.1},
            {"ts": now - 20, "unit_id": "AUD-1", "cost_usd": 0.1}]
    assert pacing.check(now, runs).allowed


def test_fallback_limits_tunable_via_tunables_json(tmp_path, monkeypatch):
    import json
    monkeypatch.setattr(settings, "STATE_DIR", tmp_path)
    (tmp_path / "tunables.json").write_text(json.dumps({"FALLBACK_SESSION_MAX_RUNS": 3}))
    assert settings.tunable("FALLBACK_SESSION_MAX_RUNS") == 3
    assert settings.tunable("FALLBACK_SESSION_MAX_USD") == settings.FALLBACK_SESSION_MAX_USD
