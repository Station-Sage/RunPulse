"""공개 캘린더 피드 라우트 + auth_cf 우회 + gunicorn 로그 마스킹 + rate_window."""
from __future__ import annotations

import sqlite3

import pytest
from cryptography.fernet import Fernet
from flask import Flask

from src.services import calendar_feed_index as idx
from src.utils import rate_window
from src.web import views_calendar_feed as v
from src.web.gunicorn_logging import redact


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setattr(idx, "index_path", lambda: tmp_path / "calendar_feeds.db")
    monkeypatch.setenv("CREDENTIAL_ENCRYPTION_KEY", Fernet.generate_key().decode())
    db = tmp_path / "running.db"
    from src import db_setup
    monkeypatch.setattr(db_setup, "get_db_path", lambda uid=None, create=True: db)
    monkeypatch.setattr(v, "get_db_path", lambda uid=None, create=True: db)
    db_setup.init_db()
    conn = sqlite3.connect(db)
    conn.execute("INSERT INTO planned_workouts (date, workout_type, distance_km, source) "
                 "VALUES (date('now','+1 day'), 'easy', 8, 'planner')")
    conn.commit()
    conn.close()
    rate_window.reset()
    app = Flask(__name__)
    app.register_blueprint(v.calendar_feed_bp)
    return app.test_client()


def test_valid_token_serves_ics_without_cookie(client):
    t = idx.issue("u1")
    r = client.get(f"/feeds/cal/{t}.ics")
    assert r.status_code == 200 and r.mimetype == "text/calendar"
    assert b"BEGIN:VCALENDAR" in r.data and b"SUMMARY:RunPulse" in r.data
    assert "Set-Cookie" not in r.headers
    assert r.headers["Cache-Control"] == "private, no-cache"
    assert "noindex" in r.headers["X-Robots-Tag"]
    assert idx.get_status("u1")["last_access_at"]


def test_etag_304_and_head(client):
    t = idx.issue("u1")
    r = client.get(f"/feeds/cal/{t}.ics")
    r2 = client.get(f"/feeds/cal/{t}.ics", headers={"If-None-Match": r.headers["ETag"]})
    assert r2.status_code == 304
    h = client.head(f"/feeds/cal/{t}.ics")
    assert h.status_code == 200 and h.data == b""


def test_unknown_and_rotated_token_404(client):
    old = idx.issue("u1")
    idx.issue("u1")
    assert client.get(f"/feeds/cal/{old}.ics").status_code == 404
    assert client.get("/feeds/cal/garbage.ics").status_code == 404


def test_ip_404_rate_limit(client):
    codes = [client.get(f"/feeds/cal/bad{i}.ics").status_code for i in range(22)]
    assert codes[:20] == [404] * 20 and codes[20] == 429


def test_token_rate_limit(client, monkeypatch):
    monkeypatch.setattr(v, "_TOKEN_LIMIT", (2, 3600))
    t = idx.issue("u1")
    assert [client.get(f"/feeds/cal/{t}.ics").status_code for _ in range(3)] == [200, 200, 429]


def test_client_family():
    assert v.client_family("Google-Calendar-Importer") == "google"
    assert v.client_family("iOS/17 dataaccessd/1.0") == "apple"
    assert v.client_family("Microsoft Outlook") == "outlook"
    assert v.client_family("curl") == "other"


def test_auth_cf_bypass_on_feed_path(monkeypatch):
    from src.web import auth_cf
    monkeypatch.setattr(auth_cf, "_IS_PRODUCTION", True)
    app = Flask(__name__)
    app.secret_key = "x"
    auth_cf.init_cf_auth(app)

    @app.route("/feeds/cal/<t>.ics")
    def f(t):
        return "ok"

    @app.route("/other")
    def o():
        return "ok"

    c = app.test_client()
    r = c.get("/feeds/cal/abc.ics")
    assert r.status_code == 200 and "Set-Cookie" not in r.headers
    assert c.get("/other").status_code == 401


def test_redact_token_in_logs():
    assert redact('GET /feeds/cal/rpcal_SECRET.ics HTTP/1.1') == 'GET /feeds/cal/[redacted] HTTP/1.1'
    assert "SECRET" not in redact("/feeds/cal/rpcal_SECRET.ics?x=1")


def test_redacting_logger_masks_access(monkeypatch):
    from src.web.gunicorn_logging import RedactingLogger
    seen = {}
    monkeypatch.setattr("gunicorn.glogging.Logger.access",
                        lambda self, resp, req, environ, rt: seen.update(env=dict(environ), uri=req.uri))
    req = type("R", (), {"uri": "/feeds/cal/rpcal_SECRET.ics", "path": "/feeds/cal/rpcal_SECRET.ics"})()
    env = {"RAW_URI": "/feeds/cal/rpcal_SECRET.ics", "PATH_INFO": "/feeds/cal/rpcal_SECRET.ics"}
    RedactingLogger.access(object.__new__(RedactingLogger), None, req, env, 0.0)
    assert "SECRET" not in str(seen)


def test_rate_window_basic():
    rate_window.reset()
    assert rate_window.hit("k", 2, 10, now=0) and rate_window.hit("k", 2, 10, now=1)
    assert not rate_window.hit("k", 2, 10, now=2)
    assert rate_window.hit("k", 2, 10, now=11)
