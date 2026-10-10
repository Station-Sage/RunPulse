"""기간 동기화 — parse_range·estimate·trigger_range·POST/GET API."""
from __future__ import annotations

from datetime import date, datetime, timedelta
from types import SimpleNamespace

import pytest
from flask import Flask

from src.api import api_bp
from src.services import sync_range_service as rs
from src.services.sync_trigger_service import SkipReason, TriggerResult

TODAY = date(2026, 10, 7)


def test_parse_range_errors():
    assert rs.parse_range("2026-10-01", "2026-10-05", TODAY)[2] is None
    assert rs.parse_range("x", "2026-10-05", TODAY)[2]
    assert rs.parse_range("2026-10-06", "2026-10-05", TODAY)[2]
    assert rs.parse_range("2026-10-01", "2026-10-09", TODAY)[2]


def test_estimate_counts_and_limits(monkeypatch):
    import src.utils.sync_jobs as sj
    now = datetime(2026, 10, 7, 12, 0)
    jobs = [SimpleNamespace(updated_at=(now - timedelta(minutes=5)).isoformat(), req_count=30),
            SimpleNamespace(updated_at=(now - timedelta(hours=3)).isoformat(), req_count=100)]
    monkeypatch.setattr(sj, "list_recent_jobs", lambda s, limit=10: jobs)
    e = rs.estimate("strava", "2026-09-01", "2026-09-28", now)
    assert e["days"] == 28 and e["batches"] == 2 and e["requests"] == 30
    assert e["rate_limit"] == {"window_15m_left": 70, "daily_left": 870}
    assert e["allowed"] is True
    assert rs.estimate("garmin", "2026-01-01", "2026-09-28", now)["allowed"] is False


def _patch(monkeypatch, connected=("garmin", "strava"), running=()):
    monkeypatch.setattr(rs, "_checkers", lambda: {
        s: (lambda c, s=s: {"ok": s in connected, "status": "ok"})
        for s in ("garmin", "strava", "intervals", "runalyze")})
    import src.utils.config as cfg
    monkeypatch.setattr(cfg, "enabled_sources", lambda c: ["garmin"])
    import src.utils.sync_state as ss
    monkeypatch.setattr(ss, "is_running", lambda s, u=None: s in running)
    import src.utils.sync_gates as sg
    monkeypatch.setattr(sg, "wait_sec", lambda s, u=None: 0)
    import src.utils.sync_jobs as sj
    monkeypatch.setattr(sj, "get_active_job", lambda s: None)


def test_trigger_range_skips_and_starts(monkeypatch):
    _patch(monkeypatch)
    import src.web.bg_sync as bg
    calls = []
    monkeypatch.setattr(bg, "_start_or_existing",
                        lambda s, f, t, c, u, p: calls.append((s, f, t, p)) or ("j1", True))
    res = rs.trigger_range({}, "u", ["garmin", "strava", "runalyze"], "2026-09-01", "2026-09-10")
    assert [r["provider"] for r in res.runs] == ["garmin"]
    assert calls == [("garmin", "2026-09-01", "2026-09-10", "range")]
    assert {s.provider: s.code for s in res.skipped} == {"strava": "disabled", "runalyze": "not_connected"}


def test_trigger_range_too_large_and_running(monkeypatch):
    _patch(monkeypatch, running=("garmin",))
    res = rs.trigger_range({}, "u", ["garmin"], "2026-09-01", "2026-09-10")
    assert res.skipped[0].code == "running"
    _patch(monkeypatch)
    res = rs.trigger_range({}, "u", ["garmin"], "2025-01-01", "2026-09-10")
    assert res.skipped[0].code == "range_too_large"


@pytest.fixture
def client(tmp_path, monkeypatch):
    db = tmp_path / "running.db"
    db.write_bytes(b"")
    import src.api.routes_data as rd
    monkeypatch.setattr(rd, "db_path", lambda: db)
    monkeypatch.setattr(rd, "get_current_user_id", lambda: "u")
    monkeypatch.setattr(rd, "load_config", lambda user_id=None: {})
    app = Flask(__name__)
    app.register_blueprint(api_bp)
    with app.test_client() as c:
        yield c


def test_api_range_validation(client):
    post = lambda b: client.post("/api/v1/data/sync", json=b)  # noqa: E731
    assert post({"mode": "range", "from": "2026-09-01", "to": "2026-09-02"}).status_code == 400
    assert post({"mode": "range", "sources": ["garmin"], "from": "2026-09-09", "to": "2026-09-02"}).status_code == 400
    assert post({"mode": "bogus"}).status_code == 400


def test_api_range_202_and_too_large(client, monkeypatch):
    seen = {}
    def fake(config, uid, sources, frm, to):
        seen.update(sources=sources, frm=frm, to=to)
        return TriggerResult([{"id": "j", "provider": "garmin", "state": "queued"}], [])
    monkeypatch.setattr(rs, "trigger_range", fake)
    r = client.post("/api/v1/data/sync", json={"mode": "range", "sources": ["garmin"],
                                               "from": "2026-09-01", "to": "2026-09-02"})
    assert r.status_code == 202 and seen["frm"] == "2026-09-01"
    monkeypatch.setattr(rs, "trigger_range", lambda *a: TriggerResult(
        [], [SkipReason("garmin", "range_too_large", "너무 길어요")]))
    r = client.post("/api/v1/data/sync", json={"mode": "range", "sources": ["garmin"],
                                               "from": "2026-01-01", "to": "2026-09-02"})
    assert r.status_code == 400


def test_api_estimate(client):
    r = client.get("/api/v1/data/sync/estimate?provider=intervals&from=2026-09-01&to=2026-09-30")
    assert r.status_code == 200 and r.get_json()["data"]["days"] == 30
    assert client.get("/api/v1/data/sync/estimate?provider=x&from=2026-09-01&to=2026-09-30").status_code == 400
    assert client.get("/api/v1/data/sync/estimate?provider=garmin&from=bad&to=2026-09-30").status_code == 400


def test_auto_sync_connected_sources_respects_enabled():
    from src.web.auto_sync import _connected_sources
    cfg = {"garmin": {"email": "a"}, "strava": {"refresh_token": "t"}, "sync_sources": ["garmin"]}
    assert _connected_sources(cfg) == ["garmin"]
