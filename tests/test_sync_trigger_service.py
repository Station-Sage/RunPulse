"""sync_trigger_service — 판정 순서·시작 실패 격리·days_since_last_sync."""
from __future__ import annotations

import sqlite3
from datetime import date, timedelta
from types import SimpleNamespace

import pytest

from src.services import sync_trigger_service as svc


def _patch(monkeypatch, *, connected=("garmin", "strava"), enabled=("garmin", "strava"),
           running=(), guard=None, wait=None):
    monkeypatch.setattr(svc, "_checkers", lambda: {
        s: (lambda c, s=s: {"ok": s in connected, "status": "ok" if s in connected else "no_token"})
        for s in svc.ALL_SOURCES})
    import src.utils.config as cfg
    monkeypatch.setattr(cfg, "enabled_sources", lambda c: list(enabled))
    import src.utils.sync_state as ss
    monkeypatch.setattr(ss, "is_running", lambda s, u=None: s in running)
    monkeypatch.setattr(ss, "get_last_sync_at", lambda s, u=None: None)
    import src.utils.sync_gates as sg
    monkeypatch.setattr(sg, "wait_sec", lambda s, u=None: (wait or {}).get(s, 0))
    import src.utils.sync_policy as sp
    monkeypatch.setattr(sp, "check_incremental_guard", lambda s, last: (guard or {}).get(
        s, SimpleNamespace(allowed=True, retry_after_sec=None, message_ko="")))
    import src.web.bg_sync as bg
    monkeypatch.setattr(bg, "get_status", lambda s, u=None: {"active": False})
    import src.utils.sync_jobs as sj
    monkeypatch.setattr(sj, "get_active_job", lambda s: None)


def _plan(tmp_path, sources=None):
    return svc.plan_incremental({}, "u", sources, date(2026, 10, 7), db_file=tmp_path / "x.db")


def test_plan_skip_codes(monkeypatch, tmp_path):
    _patch(monkeypatch, connected=("garmin", "strava", "intervals"), enabled=("garmin", "strava"),
           running=("strava",))
    start, _, skipped = _plan(tmp_path, ["garmin", "strava", "intervals", "runalyze"])
    assert start == ["garmin"]
    assert {s.provider: s.code for s in skipped} == {
        "strava": "running", "intervals": "disabled", "runalyze": "not_connected"}


def test_plan_cooldown_then_rate_limited(monkeypatch, tmp_path):
    guard = {"garmin": SimpleNamespace(allowed=False, retry_after_sec=30, message_ko="쿨다운")}
    _patch(monkeypatch, guard=guard, wait={"strava": 90})
    start, _, skipped = _plan(tmp_path, ["garmin", "strava"])
    assert start == []
    by = {s.provider: s for s in skipped}
    assert by["garmin"].code == "cooldown" and by["garmin"].retry_after_sec == 30
    assert by["strava"].code == "rate_limited" and by["strava"].retry_after_sec == 90


def test_plan_from_date_default_seven_days(monkeypatch, tmp_path):
    _patch(monkeypatch)
    _, from_dates, _ = _plan(tmp_path, ["garmin"])
    assert from_dates["garmin"] == (date(2026, 10, 7) - timedelta(days=7)).isoformat()


def test_days_since_last_sync(tmp_path):
    db = tmp_path / "r.db"
    assert svc.days_since_last_sync(db, ["garmin"]) == 7
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE activity_summaries (source TEXT, start_time TEXT)")
    assert svc.days_since_last_sync(db, ["garmin"]) == 7
    conn.execute("INSERT INTO activity_summaries VALUES ('garmin', ?)",
                 ((date.today() - timedelta(days=3)).isoformat() + "T06:00:00",))
    conn.commit(); conn.close()
    assert svc.days_since_last_sync(db, ["garmin"]) == 5
    assert svc.days_since_last_sync(db, ["strava"]) == 7


def test_trigger_isolates_start_failure(monkeypatch):
    _patch(monkeypatch)
    import src.web.bg_sync as bg

    def fake(src, f, t, cfg, uid, sp):
        if src == "garmin":
            raise RuntimeError("boom")
        return "job-1", True
    monkeypatch.setattr(bg, "_start_or_existing", fake)
    res = svc.trigger_incremental({}, "u", ["garmin", "strava"])
    assert [r["provider"] for r in res.runs] == ["strava"]
    assert res.runs[0]["state"] == "queued"
    assert [(s.provider, s.code) for s in res.skipped] == [("garmin", "start_failed")]


def test_trigger_existing_job_becomes_running_skip(monkeypatch):
    _patch(monkeypatch, connected=("garmin",))
    import src.web.bg_sync as bg
    monkeypatch.setattr(bg, "_start_or_existing", lambda *a: ("j9", False))
    res = svc.trigger_incremental({}, "u", ["garmin"])
    assert res.runs == [] and res.skipped[0].code == "running" and res.skipped[0].job_id == "j9"


def test_skip_reason_to_dict_omits_none():
    d = svc.SkipReason("garmin", "running", "m").to_dict()
    assert d == {"provider": "garmin", "code": "running", "message_ko": "m"}
