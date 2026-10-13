"""tests/test_switch_user.py — 개발용 사용자 전환 v2 (V1-8, SRV 2.5, ADR-048 5단계).

서비스(`user_switch_service`)와 v2 엔드포인트(`/api/v1/dev/*`): production 404, uid 규칙, 세션 전환,
Origin 관문 적용, v1 `/switch-user` 삭제. 실제 `data/users` 는 건드리지 않는다(tmp 루트로 격리).
"""
from __future__ import annotations

import logging

import pytest

from src.services import user_switch_service as svc
from src.utils.user_context import InvalidUserId

_UID_HINT = "영문·숫자와 . _ % + @ - 만, 1~254자, 맨 앞 '.' 불가"
ORIGIN = {"Origin": "http://localhost"}
CF = "CF-Access-Authenticated-User-Email"


@pytest.fixture
def root(isolated_users_root):
    return isolated_users_root


def _names(root) -> set[str]:
    """요청이 자동으로 만드는 default(개발 폴백 사용자)는 제외한 디렉터리 이름."""
    return {p.name for p in root.iterdir()} - {"default"}


@pytest.fixture
def app(root, monkeypatch):
    from src.web.app import create_app
    monkeypatch.setenv("FLASK_SECRET_KEY", "k")
    monkeypatch.setenv("APP_ENV", "development")
    a = create_app()
    a.config["TESTING"] = True
    return a


@pytest.fixture
def client(app):
    with app.test_client() as c:
        yield c


def _post(client, uid, **kw):
    return client.post("/api/v1/dev/switch-user", json={"user_id": uid}, headers={**ORIGIN, **kw.pop("headers", {})})


# ── 서비스 ───────────────────────────────────────────────────────────

def test_service_list_users_sorted_and_skips_invalid(root):
    for n in ("b@example.com", "default", "a@example.com", "bad name"):
        (root / n).mkdir()
    (root / "file.txt").write_text("x")
    assert svc.list_users() == ["a@example.com", "b@example.com", "default"]


def test_service_list_users_empty_falls_back_to_default(root):
    assert svc.list_users() == ["default"]


def test_service_switch_creates_db_and_sets_session(root):
    session: dict = {}
    assert svc.switch_user("new@example.com", session) == "new@example.com"
    assert session["user_id"] == "new@example.com"
    assert (root / "new@example.com" / "running.db").exists()


@pytest.mark.parametrize("bad", ["", ".", "..", "../x", "a/b", "a\\b", ".hidden", "a" * 255, "a b", "a\n", "é", None, 5])
def test_service_rejects_invalid_uid_without_touching_session_or_disk(root, bad):
    session = {"user_id": "keep"}
    with pytest.raises(InvalidUserId):
        svc.switch_user(bad, session)
    assert session == {"user_id": "keep"}
    assert list(root.iterdir()) == []  # 서비스 단독 호출은 아무것도 만들지 않는다


@pytest.mark.parametrize("ok", ["default", "user@example.com", "a.b_c-d+e%f@x.co", "a" * 254])
def test_service_accepts_valid_uids(root, ok):
    session: dict = {}
    assert svc.switch_user(ok, session) == ok


def test_service_session_unchanged_when_init_db_fails(root, monkeypatch):
    import src.db_setup as dbs
    monkeypatch.setattr(dbs, "init_db", lambda uid=None: (_ for _ in ()).throw(RuntimeError("disk")))
    session = {"user_id": "keep"}
    with pytest.raises(RuntimeError):
        svc.switch_user("ok@example.com", session)
    assert session == {"user_id": "keep"}


@pytest.mark.parametrize("env,expected", [("production", False), ("PRODUCTION", False),
                                          ("development", True), ("", True), ("staging", True)])
def test_service_dev_switch_enabled_by_app_env(monkeypatch, env, expected):
    monkeypatch.setenv("APP_ENV", env)
    assert svc.dev_switch_enabled() is expected


def test_service_dev_switch_enabled_when_unset(monkeypatch):
    monkeypatch.delenv("APP_ENV", raising=False)
    assert svc.dev_switch_enabled() is True


# ── v2 엔드포인트 ────────────────────────────────────────────────────

def test_get_users_lists_current_and_users(client, root):
    (root / "a@example.com").mkdir()
    (root / "z@example.com").mkdir()
    r = client.get("/api/v1/dev/users", headers={CF: "a@example.com"})
    assert r.status_code == 200
    d = r.get_json()["data"]
    assert d["current"] == "a@example.com"
    assert "z@example.com" in d["users"] and d["users"] == sorted(d["users"])


def test_post_switch_changes_session_user(client, root):
    (root / "a@example.com").mkdir()
    assert client.get("/api/v1/dev/users", headers={CF: "a@example.com"}).get_json()["data"]["current"] == "a@example.com"
    r = _post(client, "b@example.com")
    assert r.status_code == 200
    assert r.get_json()["data"]["user_id"] == "b@example.com"
    assert (root / "b@example.com" / "running.db").exists()
    # 같은 클라이언트(세션 쿠키 유지)의 다음 요청은 새 사용자
    assert client.get("/api/v1/dev/users").get_json()["data"]["current"] == "b@example.com"


def test_switch_overrides_cf_header_on_following_requests(client, root):
    """세션 값이 우선(auth_cf) — 전환 후에는 CF 헤더 이메일이 같아도 전환된 사용자로 동작한다."""
    client.get("/api/v1/dev/users", headers={CF: "a@example.com"})
    _post(client, "b@example.com")
    assert client.get("/api/v1/dev/users", headers={CF: "a@example.com"}).get_json()["data"]["current"] == "b@example.com"


@pytest.mark.parametrize("bad", [".", "..", "../x", "a/b", "a\\b", ".hidden", "a b", "é"])
def test_post_invalid_uid_400_with_details_and_no_dir(client, root, bad):
    r = _post(client, bad)
    assert r.status_code == 400
    err = r.get_json()["error"]
    assert err["code"] == "INVALID_PARAM" and "user_id" in err["details"]
    assert r.get_json()["error"]["details"]["user_id"] == _UID_HINT  # 고정 안내문만 — 입력 원문을 되돌려 주지 않는다
    assert _names(root) == set()


@pytest.mark.parametrize("body", [{}, {"user_id": ""}, {"user_id": None}, {"user_id": "   "}])
def test_post_missing_uid_400(client, root, body):
    r = client.post("/api/v1/dev/switch-user", json=body, headers=ORIGIN)
    assert r.status_code == 400 and r.get_json()["error"]["details"]["user_id"]


def test_post_non_string_uid_400(client, root):
    r = client.post("/api/v1/dev/switch-user", json={"user_id": 123}, headers=ORIGIN)
    assert r.status_code == 400


def test_post_non_json_415_and_broken_json_400(client, root):
    assert client.post("/api/v1/dev/switch-user", data="user_id=a", headers=ORIGIN).status_code == 415
    r = client.post("/api/v1/dev/switch-user", data="{", content_type="application/json", headers=ORIGIN)
    assert r.status_code == 400


def test_post_uid_is_stripped_like_other_str_fields(client, root):
    r = _post(client, "  c@example.com  ")
    assert r.status_code == 200 and r.get_json()["data"]["user_id"] == "c@example.com"


def test_post_rejects_forged_origin_and_missing_origin(client, root):
    r = client.post("/api/v1/dev/switch-user", json={"user_id": "x@example.com"}, headers={"Origin": "https://evil.example"})
    assert r.status_code == 403 and r.get_json()["error"]["code"] == "FORBIDDEN_ORIGIN"
    assert client.post("/api/v1/dev/switch-user", json={"user_id": "x@example.com"}).status_code == 403
    assert _names(root) == set()


# ── production 404 ───────────────────────────────────────────────────

@pytest.fixture
def prod_client(root, monkeypatch):
    from src.web.app import create_app
    import src.web.auth_cf as auth_cf
    monkeypatch.setenv("FLASK_SECRET_KEY", "k")
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setattr(auth_cf, "_IS_PRODUCTION", True)  # 모듈 로드 시 계산되는 값
    a = create_app()
    a.config["TESTING"] = True
    with a.test_client() as c:
        yield c


def test_production_404_envelope_for_both_endpoints(prod_client, root):
    h = {CF: "a@example.com"}
    r = prod_client.get("/api/v1/dev/users", headers=h)
    assert r.status_code == 404 and r.get_json()["error"]["code"] == "NOT_FOUND"
    r = prod_client.post("/api/v1/dev/switch-user", json={"user_id": "x@example.com"}, headers={**h, **ORIGIN})
    assert r.status_code == 404 and r.get_json()["error"]["code"] == "NOT_FOUND"
    assert not (root / "x@example.com").exists()


def test_production_404_is_independent_of_origin_and_body(prod_client, root):
    h = {CF: "a@example.com"}
    assert prod_client.post("/api/v1/dev/switch-user", data="garbage", headers=h).status_code in (403, 404)
    r = prod_client.post("/api/v1/dev/switch-user", data="garbage", headers={**h, **ORIGIN})
    assert r.status_code == 404  # 415/400 보다 먼저 — 존재 자체를 숨긴다


def test_production_other_api_still_works(prod_client, root):
    (root / "a@example.com").mkdir()
    r = prod_client.get("/api/v1/me/preferences", headers={CF: "a@example.com"})
    assert r.status_code != 404


def test_dev_toggle_is_evaluated_per_request(app, root, monkeypatch):
    """production 판정이 요청 시점이라 환경이 바뀌면 즉시 반영된다(앱 재생성 불필요)."""
    with app.test_client() as c:
        assert c.get("/api/v1/dev/users", headers={CF: "a@example.com"}).status_code == 200
        monkeypatch.setenv("APP_ENV", "production")
        assert c.get("/api/v1/dev/users", headers={CF: "a@example.com"}).status_code == 404


# ── v1 라우트 삭제 ───────────────────────────────────────────────────

def test_v1_switch_user_route_removed(client):
    assert not any(r.rule == "/switch-user" for r in client.application.url_map.iter_rules())
    assert client.get("/switch-user", headers={CF: "a@example.com"}).status_code == 404
    assert client.post("/switch-user", data={"user_id": "../x"}, headers={**ORIGIN, CF: "a@example.com"}).status_code == 404


def test_no_dev_route_registered_outside_api_v1(app):
    rules = [r.rule for r in app.url_map.iter_rules() if "switch" in r.rule or "/dev/" in r.rule]
    assert sorted(rules) == ["/api/v1/dev/switch-user", "/api/v1/dev/users"]


def test_invalid_uid_attempt_is_not_logged_with_raw_value(client, root, caplog):
    with caplog.at_level(logging.DEBUG):
        _post(client, "../../etc/passwd")
    assert "etc/passwd" not in caplog.text


def test_post_invalid_uid_response_never_echoes_input(client, root):
    marker = "../ZZ-MARKER-ZZ"
    r = _post(client, marker)
    assert r.status_code == 400 and "ZZ-MARKER-ZZ" not in r.get_data(as_text=True)


def test_post_too_long_uid_400_by_field_length_and_no_dir(client, root):
    r = _post(client, "a" * 255)  # 규칙 이전에 필드 길이(254)에서 걸린다
    assert r.status_code == 400
    assert r.get_json()["error"]["details"]["user_id"] == "254자 이하여야 합니다"
    assert _names(root) == set()
