"""POST /api/v1/data/sync — 상태코드 매핑·입력 검증, api_error details."""
from __future__ import annotations

import pytest
from flask import Flask

from src.api import api_bp, api_error
from src.services.sync_trigger_service import SkipReason, TriggerResult


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


def _trigger(monkeypatch, runs=(), skipped=()):
    import src.services.sync_trigger_service as svc
    monkeypatch.setattr(svc, "trigger_incremental",
                        lambda *a, **k: TriggerResult(list(runs), list(skipped)))


def test_202_partial_start(client, monkeypatch):
    _trigger(monkeypatch, [{"id": "j", "provider": "garmin", "state": "queued"}],
             [SkipReason("strava", "cooldown", "m", 10)])
    r = client.post("/api/v1/data/sync", json={})
    assert r.status_code == 202
    d = r.get_json()["data"]
    assert d["runs"][0]["id"] == "j" and d["skipped"][0]["retry_after_sec"] == 10


def test_422_no_sources(client, monkeypatch):
    _trigger(monkeypatch, skipped=[SkipReason("garmin", "not_connected", "m"),
                                   SkipReason("strava", "disabled", "m")])
    r = client.post("/api/v1/data/sync", json={})
    assert r.status_code == 422 and r.get_json()["error"]["code"] == "NO_SOURCES"


def test_409_all_running(client, monkeypatch):
    _trigger(monkeypatch, skipped=[SkipReason("garmin", "running", "m", job_id="j")])
    r = client.post("/api/v1/data/sync")
    assert r.status_code == 409 and r.get_json()["error"]["code"] == "SYNC_RUNNING"


def test_429_cooldown_has_retry_after(client, monkeypatch):
    _trigger(monkeypatch, skipped=[SkipReason("garmin", "cooldown", "m", 30),
                                   SkipReason("strava", "rate_limited", "m", 90)])
    r = client.post("/api/v1/data/sync", json={})
    assert r.status_code == 429
    assert r.headers["Retry-After"] == "30"
    assert r.get_json()["error"]["details"]["retry_after_sec"] == 30


@pytest.mark.parametrize("body", [{"mode": "range"}, {"sources": ["nope"]}, {"sources": []}, {"sources": "garmin"}])
def test_400_invalid(client, body):
    r = client.post("/api/v1/data/sync", json=body)
    assert r.status_code == 400 and r.get_json()["error"]["code"] == "INVALID_PARAM"


def test_non_json_body_is_empty(client, monkeypatch):
    _trigger(monkeypatch, [{"id": "j", "provider": "garmin", "state": "queued"}])
    assert client.post("/api/v1/data/sync", data="x", content_type="text/plain").status_code == 202


def test_503_missing_db(client, monkeypatch, tmp_path):
    import src.api.routes_data as rd
    monkeypatch.setattr(rd, "db_path", lambda: tmp_path / "none.db")
    assert client.post("/api/v1/data/sync", json={}).status_code == 503


def test_api_error_details_optional():
    app = Flask(__name__)
    with app.app_context():
        assert "details" not in api_error("X", "m")[0].get_json()["error"]
        assert api_error("X", "m", 400, {"a": 1})[0].get_json()["error"]["details"] == {"a": 1}


def _job(status):
    from types import SimpleNamespace
    return SimpleNamespace(id="j1", service="garmin", status=status)


def test_cancel_404(client, monkeypatch):
    import src.utils.sync_jobs as sj
    monkeypatch.setattr(sj, "get_job", lambda i: None)
    assert client.post("/api/v1/data/sync/runs/x/cancel").status_code == 404


def test_cancel_running_requests_stop(client, monkeypatch):
    import src.utils.sync_jobs as sj
    import src.web.bg_sync as bg
    calls = []
    monkeypatch.setattr(sj, "get_job", lambda i: _job("running"))
    monkeypatch.setattr(bg, "stop_job", lambda s, u=None: calls.append((s, u)) or True)
    r = client.post("/api/v1/data/sync/runs/j1/cancel")
    assert r.status_code == 202 and r.get_json()["data"]["state"] == "stopping"
    assert calls == [("garmin", "u")]


def test_cancel_finished_is_idempotent(client, monkeypatch):
    import src.utils.sync_jobs as sj
    import src.web.bg_sync as bg
    monkeypatch.setattr(sj, "get_job", lambda i: _job("completed"))
    monkeypatch.setattr(bg, "stop_job", lambda *a, **k: pytest.fail("호출되면 안 됨"))
    r = client.post("/api/v1/data/sync/runs/j1/cancel")
    assert r.status_code == 200 and r.get_json()["data"] == {
        "id": "j1", "provider": "garmin", "state": "completed", "requested": False}
