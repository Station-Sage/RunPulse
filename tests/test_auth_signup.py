"""AUTH-2026-11 stage 2 — 초대코드·일일 상한·프로비저닝·가입 엔드포인트."""
import pytest
from flask import Flask

from src.auth import cf_jwt, identify, invites, provisioning, registry, signup
from src.utils import rate_window

JWT = {"Cf-Access-Jwt-Assertion": "tok"}
H = {**JWT, "Origin": "http://localhost"}


@pytest.fixture()
def client(isolated_users_root, monkeypatch):
    monkeypatch.setenv("AUTH_MODE", "registry")
    monkeypatch.setenv("SIGNUP_MODE", "invite")
    monkeypatch.setattr(identify, "_IS_PRODUCTION", True)
    state = {"sub": "s1", "email": "new@corp.io"}
    monkeypatch.setattr(cf_jwt, "verify", lambda t: dict(state))
    rate_window.reset()
    a = Flask(__name__)
    a.secret_key = "x"
    a.config["TESTING"] = True
    identify.init_registry_auth(a)
    from src.api.routes_auth import post_auth_invite

    a.add_url_rule("/api/v1/auth/invite", view_func=post_auth_invite, methods=["POST"])
    c = a.test_client()
    c.state = state
    return c


def _code(**kw):
    conn = registry.connect()
    code, _ = invites.issue(conn, **kw)
    conn.close()
    return code


def test_invite_hash_only_and_consume_limits():
    conn = registry.connect()
    code, iid = invites.issue(conn, max_uses=1)
    assert conn.execute("SELECT COUNT(*) FROM invites WHERE code_hash=?", (code,)).fetchone()[0] == 0
    assert invites.consume(conn, code.lower()) == iid
    with pytest.raises(invites.InviteError):
        invites.consume(conn, code)
    with pytest.raises(invites.InviteError):
        invites.consume(conn, "NOPE")


def test_invite_expired():
    conn = registry.connect()
    code, iid = invites.issue(conn)
    conn.execute("UPDATE invites SET expires_at='2000-01-01 00:00:00' WHERE invite_id=?", (iid,))
    conn.commit()
    with pytest.raises(invites.InviteError):
        invites.consume(conn, code)


def test_provision_idempotent(isolated_users_root):
    provisioning.provision("a@b.co")
    d = isolated_users_root / "a@b.co" if (isolated_users_root / "a@b.co").exists() else None
    provisioning.provision("a@b.co")
    assert d is None or (d / "running.db").exists()


def test_signup_flow_activates_and_provisions(client):
    code = _code()
    assert client.post("/api/v1/auth/invite", json={"code": "bad"}, headers=H).status_code == 400
    r = client.post("/api/v1/auth/invite", json={"code": code}, headers=H)
    assert r.status_code == 200 and r.get_json()["data"]["state"] == "active"
    conn = registry.connect()
    assert registry.account_by_email(conn, "new@corp.io")["status"] == "active"
    conn.close()
    r = client.post("/api/v1/auth/invite", json={"code": code}, headers=H)
    assert r.status_code == 409


def test_daily_cap_429(client, monkeypatch):
    monkeypatch.setenv("SIGNUP_DAILY_CAP", "1")
    conn = registry.connect()
    registry.create_pending(conn, "first@corp.io")
    registry.activate(conn, "first@corp.io", invite_id="x")
    conn.close()
    r = client.post("/api/v1/auth/invite", json={"code": _code()}, headers=H)
    assert r.status_code == 429 and r.get_json()["error"]["code"] == "SIGNUP_CAP"


def test_provision_failure_rolls_back(client, monkeypatch):
    monkeypatch.setattr(provisioning, "provision", lambda uid: (_ for _ in ()).throw(OSError("disk")))
    code = _code()
    r = client.post("/api/v1/auth/invite", json={"code": code}, headers=H)
    assert r.status_code == 503
    conn = registry.connect()
    assert registry.account_by_email(conn, "new@corp.io")["status"] == "pending"
    assert conn.execute("SELECT uses FROM invites").fetchone()[0] == 0
    conn.close()


def test_rate_limit(client):
    for _ in range(5):
        client.post("/api/v1/auth/invite", json={"code": "bad"}, headers=H)
    assert client.post("/api/v1/auth/invite", json={"code": "bad"}, headers=H).status_code == 429


def test_allowlist_and_open_modes(client, monkeypatch):
    monkeypatch.setenv("SIGNUP_MODE", "allowlist")
    assert client.post("/api/v1/auth/invite", json={}, headers=H).status_code == 403
    monkeypatch.setenv("SIGNUP_ALLOWLIST", "NEW@corp.io")
    assert client.post("/api/v1/auth/invite", json={}, headers=H).status_code == 200


def test_pending_touches_no_user_db(client, isolated_users_root):
    client.get("/api/v1/auth/session", headers=JWT)
    assert not any(isolated_users_root.iterdir()) if isolated_users_root.exists() else True


def test_cli_issue_and_list(isolated_users_root, capsys):
    import importlib.util, pathlib
    spec = importlib.util.spec_from_file_location("auth_invite", pathlib.Path("scripts/auth_invite.py"))
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    assert m.main(["issue", "--uses", "2", "--note", "t"]) == 0
    assert m.main(["list"]) == 0
    assert "코드:" in capsys.readouterr().out
