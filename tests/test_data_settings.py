"""PATCH /data/sources/<p>, /data/sync/auto — 소스 on/off·자동 동기화 설정."""
from __future__ import annotations

from datetime import datetime

import pytest
from flask import Flask

from src.api import api_bp
from src.services import data_settings_service as svc


@pytest.fixture
def env(monkeypatch):
    import src.api.routes_data as rd
    cfg = {"sync_sources": ["garmin", "strava"]}
    saved, stopped, restarted = [], [], []
    monkeypatch.setattr(rd, "get_current_user_id", lambda: "u")
    monkeypatch.setattr(rd, "load_config", lambda user_id=None: cfg)
    monkeypatch.setattr(svc, "save_config", lambda c, user_id=None: saved.append(dict(c)))
    monkeypatch.setattr(svc, "_stop_pending", lambda p, u: stopped.append(p))
    import src.web.auto_sync as asy
    monkeypatch.setattr(asy, "restart", lambda c, u: restarted.append(c.get("auto_sync")))
    import src.utils.sync_state as ss
    monkeypatch.setattr(ss, "get_last_auto_sync", lambda u=None: datetime(2026, 10, 7, 12, 0))
    app = Flask(__name__)
    app.register_blueprint(api_bp)
    with app.test_client() as c:
        yield c, cfg, saved, stopped, restarted


def test_disable_source_stops_pending(env):
    c, cfg, saved, stopped, _ = env
    r = c.patch("/api/v1/data/sources/strava", json={"sync_enabled": False})
    assert r.status_code == 200
    assert r.get_json()["data"] == {"provider": "strava", "sync_enabled": False}
    assert cfg["sync_sources"] == ["garmin"] and saved and stopped == ["strava"]


def test_enable_source_does_not_stop(env):
    c, _, _, stopped, _ = env
    r = c.patch("/api/v1/data/sources/runalyze", json={"sync_enabled": True})
    assert r.get_json()["data"]["sync_enabled"] is True and stopped == []


def test_source_validation(env):
    c = env[0]
    assert c.patch("/api/v1/data/sources/nope", json={"sync_enabled": True}).status_code == 404
    assert c.patch("/api/v1/data/sources/garmin", json={"sync_enabled": "x"}).status_code == 400


def test_auto_patch_saves_and_restarts(env):
    c, cfg, saved, _, restarted = env
    r = c.patch("/api/v1/data/sync/auto", json={"enabled": True, "interval_h": 2, "window_days": 14})
    d = r.get_json()["data"]
    assert (d["interval_h"], d["window_days"], d["enabled"]) == (2, 14, True)
    assert cfg["auto_sync"]["interval_hours"] == 2 and cfg["auto_sync"]["days"] == 14
    assert saved and restarted


@pytest.mark.parametrize("body", [{}, {"interval_h": 3}, {"window_days": 31}, {"window_days": 0}, {"enabled": "y"}])
def test_auto_patch_rejects(env, body):
    assert env[0].patch("/api/v1/data/sync/auto", json=body).status_code == 400


def test_auto_settings_next_run():
    cfg = {"auto_sync": {"enabled": True, "interval_hours": 4, "days": 2}}
    now = datetime(2026, 10, 7, 13, 0)
    d = svc.auto_settings(cfg, datetime(2026, 10, 7, 12, 0), now)
    assert d["next_run_at"] == "2026-10-07T16:00:00"
    cfg["auto_sync"]["enabled"] = False
    assert svc.auto_settings(cfg, None, now)["next_run_at"] is None
