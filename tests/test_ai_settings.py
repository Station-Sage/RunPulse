"""ai_settings_service + /data/settings/ai 라우트 — 키 값 비노출, PATCH 검증, 사용량, 연결 테스트."""
from __future__ import annotations

import json
import sqlite3

import pytest

from src.ai.provider_common import ProviderError
from src.services import ai_settings_service as svc

CFG = {"ai": {"provider": "gemini", "gemini_api_key": "AIzaSECRET1234"}}


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.execute("CREATE TABLE chat_messages (id INTEGER PRIMARY KEY, role TEXT, engine_json TEXT, created_at TEXT)")
    c.execute("CREATE TABLE coach_consent (id INTEGER PRIMARY KEY, provider TEXT, accepted_at TEXT DEFAULT CURRENT_TIMESTAMP,"
              " exclude_notes INTEGER, tools_enabled INTEGER, fallback_enabled INTEGER)")
    yield c
    c.close()


def _msg(c, eng, when="datetime('now')"):
    c.execute(f"INSERT INTO chat_messages (role, engine_json, created_at) VALUES ('assistant', ?, {when})", (json.dumps(eng),))


def test_mask_and_validate():
    assert svc.mask_key("AIzaSECRET1234") == "••••1234" and svc.mask_key("") == "" and svc.mask_key("abc") == "••••"
    out, err = svc.validate_patch({"provider": "groq", "keys": {"groq": " k ", "gemini": ""}, "exclude_notes": True})
    assert err is None and out["keys"] == {"groq": "k"}
    for bad in ({}, {"provider": "x"}, {"keys": {"x": "a"}}, {"keys": {"groq": 1}}, {"exclude_notes": "y"}):
        assert svc.validate_patch(bad)[1]


def test_view_never_leaks_key_and_usage(conn):
    _msg(conn, {"status": "ok", "provider": "gemini", "tool_calls": 2})
    _msg(conn, {"status": "fallback", "fallback_reason": "http_429"})
    _msg(conn, {"status": "ok", "provider": "groq"}, "datetime('now','-9 days')")
    view = svc.build_view(conn, CFG)
    assert "SECRET" not in json.dumps(view)
    g = next(p for p in view["providers"] if p["provider"] == "gemini")
    assert g["key_state"] == "set" and g["key_mask"] == "••••1234"
    assert next(p for p in view["providers"] if p["provider"] == "groq")["key_state"] == "missing"
    assert view["usage_7d"] == {"messages": 2, "by_provider": {"gemini": 1}, "fallback": 1, "rule": 0, "tool_calls": 2}


def test_apply_patch_updates_config_and_consent(conn, monkeypatch):
    saved = []
    monkeypatch.setattr(svc, "save_config", lambda c, user_id=None: saved.append(1))
    cfg = {"ai": {"provider": "rule"}}
    svc.apply_patch(conn, cfg, "u", {"provider": "groq", "keys": {"groq": "kk"}, "exclude_notes": True})
    assert cfg["ai"]["groq_api_key"] == "kk" and cfg["ai"]["provider"] == "groq" and saved
    view = svc.build_view(conn, cfg)
    assert view["exclude_notes"] is True and view["consented"] is True
    assert any(s["optional"] and not s["enabled"] for s in view["scope"])
    svc.apply_patch(conn, cfg, "u", {"provider": "rule"})
    assert svc.build_view(conn, cfg)["mode"] == "rule_by_choice"


def test_connection_test(monkeypatch):
    import src.ai.chat_engine_providers as cep

    assert svc.test_connection("groq", CFG)["reason"] == "no_key"
    monkeypatch.setattr(cep, "complete", lambda *a, **k: "pong")
    assert svc.test_connection("gemini", CFG)["ok"] is True

    def boom(*a, **k):
        raise ProviderError("http_401", 401, "x")
    monkeypatch.setattr(cep, "complete", boom)
    r = svc.test_connection("gemini", CFG)
    assert r["ok"] is False and r["http_status"] == 401


def test_routes(monkeypatch, tmp_path, conn):
    from flask import Flask

    import src.api.routes_data_ai as r
    from src.api import api_bp

    f = sqlite3.connect(tmp_path / "x.db")
    f.executescript("\n".join(conn.iterdump()))
    f.close()
    cfg = {"ai": {"provider": "rule"}}
    monkeypatch.setattr(r, "db_path", lambda: tmp_path / "x.db")
    monkeypatch.setattr(r, "get_current_user_id", lambda: "u")
    monkeypatch.setattr(r, "load_config", lambda user_id=None: cfg)
    monkeypatch.setattr(svc, "save_config", lambda c, user_id=None: None)
    app = Flask(__name__)
    app.register_blueprint(api_bp)
    with app.test_client() as c:
        assert c.get("/api/v1/data/settings/ai").get_json()["data"]["mode"] == "rule_by_choice"
        assert c.patch("/api/v1/data/settings/ai", json={}).status_code == 400
        resp = c.patch("/api/v1/data/settings/ai", json={"provider": "gemini", "keys": {"gemini": "SECRETKEY99"}})
        assert resp.status_code == 200 and "SECRETKEY99" not in resp.get_data(as_text=True)
        assert c.post("/api/v1/data/settings/ai/test", json={"provider": "nope"}).status_code == 400
