"""`/` 진입 분기 — 사용자 ui_default → 전역값 → v2(/v2/today)."""
import sqlite3

import pytest

import src.web.app as web_app
from src.db_setup import create_tables
from src.services import user_settings_service as svc


@pytest.fixture
def make_client(monkeypatch, tmp_path):
    db = tmp_path / "running.db"
    monkeypatch.setattr(web_app, "_db_path", lambda: db, raising=False)

    def build(global_value=None, user_value=None):
        conn = sqlite3.connect(str(db))
        create_tables(conn)
        if user_value:
            svc.set_setting(conn, "ui_default", user_value)
        conn.close()
        cfg = {"ui_default_global": global_value} if global_value else {}
        monkeypatch.setattr(web_app, "load_config", lambda user_id=None: cfg)
        app = web_app.create_app()
        app.config["TESTING"] = True
        monkeypatch.setattr(web_app, "_db_path", lambda: db, raising=False)
        return app.test_client()

    return build


def test_default_goes_to_v2(make_client):
    assert make_client().get("/").headers["Location"].endswith("/v2/today")


def test_global_v1_still_goes_to_v2(make_client):
    assert make_client(global_value="v1").get("/").headers["Location"].endswith("/v2/today")


def test_global_v2(make_client):
    assert make_client(global_value="v2").get("/").headers["Location"].endswith("/v2/today")


def test_stored_v1_falls_back_to_v2(make_client):
    assert make_client(global_value="v2", user_value="v1").get("/").headers["Location"].endswith("/v2/today")


def test_v1_pages_helpers(tmp_path):
    from src.api.v1_pages_helpers import scan_history_dir, table
    assert "no rows" in table(["a"], [])
    assert "<td>1</td>" in table(["a"], [(1,)])
    assert scan_history_dir(tmp_path / "none")["exists"] is False
    (tmp_path / "x.fit").write_bytes(b"")
    assert scan_history_dir(tmp_path)["total_files"] == 1
