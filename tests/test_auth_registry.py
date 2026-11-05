"""AUTH-2026-11 stage 1 — registry 모드 신원 해석·공개 경로·F1~F4 방어."""
import pytest
from flask import Flask, g, session

from src.auth import auth_mode, cf_jwt, identify, registry
from src.auth.public_paths import is_public, safe_next
from src.utils.user_context import NoUserContext, get_current_user_id

JWT = {"Cf-Access-Jwt-Assertion": "tok"}
ORIGIN = {"Origin": "http://localhost"}


@pytest.fixture()
def app(isolated_users_root, monkeypatch):
    monkeypatch.setenv("AUTH_MODE", "registry")
    monkeypatch.setattr(identify, "_IS_PRODUCTION", True)
    claims = {"sub": "s1", "email": "Alice@Example.com"}
    monkeypatch.setattr(cf_jwt, "verify", lambda t: dict(claims) if t == "tok" else (_ for _ in ()).throw(cf_jwt.CfJwtError("bad")))
    a = Flask(__name__)
    a.secret_key = "x"
    a.config["TESTING"] = True
    a.claims = claims
    identify.init_registry_auth(a)
    from src.auth.routes import auth_bp
    from src.api.routes_auth import get_auth_session  # noqa: F401
    a.register_blueprint(auth_bp)

    @a.get("/data")
    def data():
        return {"uid": get_current_user_id()}

    @a.get("/v2/x")
    def v2():
        return {"state": g.auth_state}

    @a.get("/api/v1/auth/session")
    def sess():
        return {"state": g.auth_state, "email": g.auth_email}

    return a


def _activate(email="alice@example.com"):
    conn = registry.connect()
    registry.create_pending(conn, email)
    registry.activate(conn, email)
    conn.close()


def test_auth_mode_default_legacy(monkeypatch):
    monkeypatch.delenv("AUTH_MODE", raising=False)
    assert auth_mode() == "legacy"
    monkeypatch.setenv("AUTH_MODE", "REGISTRY")
    assert auth_mode() == "registry"


def test_safe_next_blocks_open_redirect():
    assert safe_next("/v2/plan") == "/v2/plan"
    for bad in ("//evil.com", "https://evil.com", "/\\evil", "/v2//x", "/api/x", None, ""):
        assert safe_next(bad) == "/v2/today"


def test_is_public():
    assert is_public("GET", "/v2/today") and is_public("GET", "/") and is_public("POST", "/auth/logout")
    assert not is_public("GET", "/api/v1/today") and not is_public("GET", "/auth/logout")


def test_anonymous_private_path_401(app):
    assert app.test_client().get("/data").status_code == 401


def test_header_email_without_jwt_is_ignored(app):
    r = app.test_client().get("/data", headers={"CF-Access-Authenticated-User-Email": "alice@example.com"})
    assert r.status_code == 401


def test_invalid_jwt_401(app):
    assert app.test_client().get("/data", headers={"Cf-Access-Jwt-Assertion": "forged"}).status_code == 401


def test_public_path_anonymous_has_no_user(app):
    r = app.test_client().get("/v2/x")
    assert r.get_json() == {"state": "anonymous"}


def test_new_signup_is_pending_without_user_id(app):
    c = app.test_client()
    r = c.get("/data", headers=JWT)
    assert r.status_code == 403
    conn = registry.connect()
    assert registry.account_by_email(conn, "alice@example.com")["status"] == "pending"
    conn.close()
    with c.session_transaction() as s:
        assert "user_id" not in s and s["pending_sub"] == "s1"
    assert c.get("/api/v1/auth/session").get_json()["state"] == "pending"


def test_active_account_reaches_data(app):
    _activate()
    r = app.test_client().get("/data", headers=JWT)
    assert r.get_json() == {"uid": "alice@example.com"}


def test_session_alone_not_enough_on_private_path(app):
    _activate()
    c = app.test_client()
    assert c.get("/data", headers=JWT).status_code == 200
    assert c.get("/data").status_code == 401  # F2: JWT 없이 세션만으로는 불가


def test_disabled_account_403(app):
    _activate()
    conn = registry.connect()
    conn.execute("UPDATE accounts SET status='disabled'")
    conn.commit()
    conn.close()
    r = app.test_client().get("/data", headers=JWT)
    assert r.status_code == 403


def test_identity_switch_clears_previous_session(app):
    _activate()
    c = app.test_client()
    c.get("/data", headers=JWT)
    app.claims.update(sub="s2", email="bob@example.com")
    c.get("/data", headers=JWT)
    with c.session_transaction() as s:
        assert s.get("user_id") is None and s["pending_sub"] == "s2"


def test_backfilled_account_links_new_identity(app):
    _activate()
    conn = registry.connect()
    registry.link_identity(conn, "alice@example.com", "other", "alice@example.com")
    conn.close()
    app.claims["sub"] = "google-sub"
    assert app.test_client().get("/data", headers=JWT).status_code == 200


def test_invalid_uid_email_403(app):
    app.claims["email"] = "bad email@x.com"
    assert app.test_client().get("/data", headers=JWT).status_code == 403


def test_pending_cannot_use_private_path_but_start_ok(app):
    c = app.test_client()
    assert c.get("/auth/start?next=/v2/plan", headers=JWT).headers["Location"] == "/v2/plan"


def test_logout_clears_session(app):
    _activate()
    c = app.test_client()
    c.get("/data", headers=JWT)
    r = c.post("/auth/logout", headers=ORIGIN)
    assert r.status_code == 303 and "/cdn-cgi/access/logout" in r.headers["Location"]
    with c.session_transaction() as s:
        assert "user_id" not in s


def test_no_user_context_not_default(app):
    with app.test_request_context():
        g.auth_state = "anonymous"
        with pytest.raises(NoUserContext):
            get_current_user_id()
    assert get_current_user_id() == "default"  # 요청 컨텍스트 밖(CLI)


def test_backfill_filters_and_collisions(isolated_users_root):
    for n in ("a@b.com", "A@B.com", "runner", "x@example.com", "u"):
        (isolated_users_root / n).mkdir(parents=True, exist_ok=True)
    conn = registry.connect()
    dry = registry.backfill(conn, apply=False)
    assert not conn.execute("SELECT 1 FROM accounts").fetchall()
    res = registry.backfill(conn, apply=True)
    assert "runner" in res["skipped"] and "x@example.com" in res["skipped"]
    assert len(res["backfilled"]) + len(res["collided"]) == len(dry["backfilled"]) + len(dry["collided"])
    assert conn.execute("SELECT COUNT(*) FROM accounts WHERE status='active'").fetchone()[0] >= 1
    conn.close()


def test_cf_jwt_unconfigured_fails_closed(monkeypatch):
    monkeypatch.delenv("CF_ACCESS_AUD", raising=False)
    monkeypatch.delenv("CF_ACCESS_TEAM", raising=False)
    with pytest.raises(cf_jwt.CfJwtError):
        cf_jwt.verify("x")


def test_real_session_endpoint_reports_mode(app):
    from src.api.routes_auth import get_auth_session

    app.view_functions.pop("sess", None)
    with app.test_request_context("/api/v1/auth/session"):
        g.auth_state = "anonymous"
        g.auth_email = None
        resp, status = get_auth_session()
        body = resp.get_json()["data"]
    assert status == 200 and resp.headers["Cache-Control"] == "no-store"
    assert body == {"mode": "registry", "state": "anonymous", "email": None}
