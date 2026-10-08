"""POST /mcp — 킬 스위치, 토큰 인증(세션 무시), 제한, 감사, auth_cf 예외."""
from __future__ import annotations

import sqlite3

import pytest
from flask import Flask, session

from src.mcp_remote import audit
from src.mcp_remote import token_index as ti
from src.utils import rate_window
from src.web import views_mcp_remote as v

H = {"MCP-Protocol-Version": "2025-03-26"}


def _rpc(method, params=None, i=1):
    return {"jsonrpc": "2.0", "id": i, "method": method, "params": params or {}}


@pytest.fixture
def env(monkeypatch, tmp_path):
    monkeypatch.setattr(ti, "index_path", lambda: tmp_path / "mcp_tokens.db")
    users = tmp_path / "users"

    def gdp(uid=None, *, create=True):
        return users / (uid or "default") / "running.db"

    monkeypatch.setattr(ti, "get_db_path", gdp)
    monkeypatch.setattr(v, "get_db_path", gdp)
    from src.db_setup import create_tables
    for u in ("a", "b"):
        (users / u).mkdir(parents=True)
        c = sqlite3.connect(users / u / "running.db")
        create_tables(c)
        c.commit()
        c.close()
    monkeypatch.setattr(audit, "_last_purge_day", "9999")
    monkeypatch.setattr(v, "enabled", lambda: True)
    rate_window.reset()
    app = Flask(__name__)
    app.secret_key = "k"
    app.register_blueprint(v.mcp_remote_bp)
    return app


def _auth(uid="a"):
    tok, meta = ti.issue(uid, "t")
    return {"Authorization": f"Bearer {tok}", **H}, meta["token_id"]


def test_disabled_returns_404(env, monkeypatch):
    monkeypatch.setattr(v, "enabled", lambda: False)
    h, _ = _auth()
    assert env.test_client().post("/mcp", json=_rpc("ping"), headers=h).status_code == 404


def test_no_or_bad_token_same_401(env):
    c = env.test_client()
    r1 = c.post("/mcp", json=_rpc("ping"), headers=H)
    r2 = c.post("/mcp", json=_rpc("ping"), headers={**H, "Authorization": "Bearer rpmcp_" + "A" * 43})
    assert r1.status_code == r2.status_code == 401
    assert r1.get_data() == r2.get_data() and r1.headers["WWW-Authenticate"] == "Bearer"
    assert {r["status"] for r in audit.query()} == {"auth_fail"}


def test_cookie_only_is_rejected_and_no_set_cookie(env):
    c = env.test_client()
    with c.session_transaction() as s:
        s["user_id"] = "a"
    r = c.post("/mcp", json=_rpc("tools/list"), headers=H)
    assert r.status_code == 401 and "Set-Cookie" not in r.headers
    assert r.headers["Cache-Control"] == "no-store"


def test_tools_list_and_audit_record(env):
    h, tid = _auth()
    r = env.test_client().post("/mcp", json=_rpc("tools/list"), headers=h)
    assert r.status_code == 200 and r.json["result"]["tools"]
    assert "Set-Cookie" not in r.headers
    (row,) = audit.query("a")
    assert row["method"] == "tools/list" and row["token_id"] == tid and row["status"] == "ok"
    assert ti.list_tokens("a")[0]["last_used_at"]


def test_ping_not_audited_and_notification_202(env):
    h, _ = _auth()
    c = env.test_client()
    assert c.post("/mcp", json=_rpc("ping"), headers=h).status_code == 200
    r = c.post("/mcp", json={"jsonrpc": "2.0", "method": "notifications/initialized"}, headers=h)
    assert r.status_code == 202
    assert [x["method"] for x in audit.query()] == ["notifications/initialized"]


def test_disallowed_tool_is_tool_error(env):
    h, _ = _auth()
    r = env.test_client().post("/mcp", json=_rpc("tools/call", {"name": "execute_sql", "arguments": {}}), headers=h)
    assert r.json["result"]["isError"] is True
    assert audit.query("a")[0]["status"] == "tool_error"


def test_tool_call_uses_token_user_not_session_or_config(env, monkeypatch):
    def boom(*a, **k):
        raise AssertionError("세션/설정 의존 금지")
    monkeypatch.setattr("src.utils.config.load_config", boom)
    monkeypatch.setattr("src.web.helpers.get_current_user_id", boom, raising=False)
    used = []
    real = v.get_db_path
    monkeypatch.setattr(v, "get_db_path", lambda uid=None, **k: used.append(uid) or real(uid, **k))
    h, _ = _auth("b")
    c = env.test_client()
    with c.session_transaction() as s:
        s["user_id"] = "a"
    r = c.post("/mcp", json=_rpc("tools/call", {"name": "get_runner_profile", "arguments": {}}), headers=h)
    assert r.status_code == 200 and used == ["b"]


def test_batch_and_bad_json_rejected(env):
    h, _ = _auth()
    c = env.test_client()
    assert c.post("/mcp", json=[_rpc("ping")], headers=h).status_code == 400
    assert c.post("/mcp", data="{", content_type="application/json", headers=h).status_code == 400


def test_body_too_large_and_origin_and_version(env):
    h, _ = _auth()
    c = env.test_client()
    assert c.post("/mcp", data=b"x" * (v.MAX_BODY + 1), content_type="application/json", headers=h).status_code == 413
    assert c.post("/mcp", json=_rpc("ping"), headers={**h, "Origin": "https://evil.example"}).status_code == 403
    assert c.post("/mcp", json=_rpc("ping"), headers={**h, "MCP-Protocol-Version": "1999-01-01"}).status_code == 400


def test_get_and_delete_405(env):
    c = env.test_client()
    assert c.get("/mcp").status_code == 405 and c.delete("/mcp").status_code == 405


def test_call_rate_limit_429(env, monkeypatch):
    monkeypatch.setattr(v, "CALL_LIMITS", ((2, 600), (100, 86400)))
    h, _ = _auth()
    c = env.test_client()
    body = _rpc("tools/call", {"name": "get_runner_profile", "arguments": {}})
    assert [c.post("/mcp", json=body, headers=h).status_code for _ in range(3)] == [200, 200, 429]
    assert audit.query("a")[0]["status"] == "rate_limited"


def test_auth_failure_ip_block(env, monkeypatch):
    monkeypatch.setattr(v, "FAIL_LIMIT", (3, 600))
    c = env.test_client()
    ip = {"CF-Connecting-IP": "9.9.9.9", **H}
    codes = [c.post("/mcp", json=_rpc("ping"), headers=ip).status_code for _ in range(4)]
    assert codes == [401, 401, 401, 429]
    h, _ = _auth()
    assert c.post("/mcp", json=_rpc("ping"), headers={**h, "CF-Connecting-IP": "9.9.9.9"}).status_code == 429
    assert c.post("/mcp", json=_rpc("ping"), headers={**h, "CF-Connecting-IP": "8.8.8.8"}).status_code == 200


def test_auth_cf_exempts_mcp_exact_only(monkeypatch):
    from src.web import auth_cf
    monkeypatch.setattr(auth_cf, "_IS_PRODUCTION", True)
    init_cf_auth = auth_cf.init_cf_auth
    app = Flask(__name__)
    app.secret_key = "k"
    init_cf_auth(app, {"cf": {}})
    app.add_url_rule("/mcp", "m", lambda: "ok", methods=["POST"])
    app.add_url_rule("/mcpx", "mx", lambda: "ok", methods=["POST"])
    c = app.test_client()
    assert c.post("/mcp").status_code == 200
    assert c.post("/mcpx").status_code == 401
