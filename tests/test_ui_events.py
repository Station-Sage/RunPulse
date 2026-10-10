"""스키마 v36 ui_events — DDL·서비스·API·전 사용자 집계(G5 게이트)."""
import sqlite3

import pytest
from flask import Flask

from src.db_schema_v36 import ensure_v36
from src.services import ui_events_service as svc

TODAY = "2026-10-10"


def _conn():
    c = sqlite3.connect(":memory:")
    ensure_v36(c)
    return c


def test_ensure_v36_idempotent():
    c = _conn()
    ensure_v36(c)
    assert "ui_events" in [r[0] for r in c.execute("SELECT name FROM sqlite_master")]


def test_visit_once_per_day():
    c = _conn()
    assert svc.record_visit(c, TODAY) is True
    assert svc.record_visit(c, TODAY) is False
    assert svc.record_visit(c, "2026-10-09") is True


def test_rollback_validates_and_trims():
    c = _conn()
    with pytest.raises(ValueError):
        svc.record_rollback(c, "bogus")
    svc.record_rollback(c, "hard_to_use", "  a\n b  " + "x" * 300, TODAY)
    note = c.execute("SELECT reason_note FROM ui_events").fetchone()[0]
    assert note.startswith("a b ") and len(note) == 200


def test_summarize_window():
    c = _conn()
    svc.record_visit(c, TODAY)
    svc.record_visit(c, "2026-09-01")
    svc.record_rollback(c, "missing_feature", None, TODAY)
    svc.record_rollback(c, None, None, TODAY)
    svc.record_rollback(c, "just_looking", None, "2026-09-01")
    s = svc.summarize(c, 14, TODAY)
    assert s["v2_visit_days"] == 1 and s["rollback_count"] == 2 and s["rolled_back"]
    assert s["rollback_by_reason"]["missing_feature"] == 1
    assert s["rollback_by_reason"]["skipped"] == 1
    assert s["from"] == "2026-09-27"


def _user(root, uid, visit=True, rollback=False, ddl=True):
    d = root / uid
    d.mkdir()
    c = sqlite3.connect(d / "running.db")
    if ddl:
        ensure_v36(c)
        if visit:
            svc.record_visit(c, TODAY)
        if rollback:
            svc.record_rollback(c, "slow_or_error", "느림", TODAY)
    c.close()


def test_summarize_all_users(tmp_path):
    empty = svc.summarize_all_users(tmp_path, 14, TODAY)
    assert empty["rate"] is None and empty["verdict"] == "미판정"
    _user(tmp_path, "a", rollback=True)
    _user(tmp_path, "b")
    _user(tmp_path, "c", ddl=False)  # v35 DB: 건너뜀
    _user(tmp_path, "d", visit=False, rollback=True)
    r = svc.summarize_all_users(tmp_path, 14, TODAY)
    assert r["active_users"] == 2 and r["rolled_back_users"] == 2
    assert r["orphan_rollback_users"] == 1 and r["small_sample"]
    assert r["verdict"] == "미달" and r["recent_notes"][0]["note"] == "느림"


@pytest.fixture
def client(tmp_path, monkeypatch):
    f = tmp_path / "running.db"
    c = sqlite3.connect(f)
    ensure_v36(c)
    c.close()
    import src.api.routes_ui_events as r
    monkeypatch.setattr(r, "db_path", lambda: f)
    app = Flask(__name__)
    from src.api import api_bp
    app.register_blueprint(api_bp)
    with app.test_client() as cl:
        yield cl


def test_api_visit_and_rollback(client):
    url = "/api/v1/me/ui-events"
    assert client.post(url, json={"kind": "v2_visit"}).get_json()["data"]["recorded"] is True
    assert client.post(url, json={"kind": "v2_visit"}).get_json()["data"]["recorded"] is False
    assert client.post(url, json={"kind": "v1_rollback", "reason": "hard_to_use"}).status_code == 200
    d = client.get(url + "/summary").get_json()["data"]
    assert d["v2_visit_days"] == 1 and d["rollback_count"] == 1


def test_api_validation(client):
    url = "/api/v1/me/ui-events"
    assert client.post(url, json={"kind": "x"}).status_code == 400
    assert client.post(url, json={"kind": "v1_rollback", "reason": "x"}).status_code == 400
    assert client.get(url + "/summary?days=a").status_code == 400
