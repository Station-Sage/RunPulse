"""garmin_connect_service(T2~T4) — 로그인·MFA·토큰 붙여넣기·해제. Garmin 은 전부 가짜(tests/helpers_garmin)."""
from __future__ import annotations

import json

import pytest

from src.services import data_connect_service as dcs
from src.services import garmin_connect_service as svc
from src.services import garmin_mfa_store as store
from src.sync.garmin_auth import check_garmin_connection
from src.utils import rate_window
from src.utils.config import load_config, update_service_config
from tests.helpers_garmin import AUTH, CONN, TOO_MANY, install

UID = "u1@x.com"
PW = "s3cret-PW!"


@pytest.fixture(autouse=True)
def env(isolated_users_root, monkeypatch):
    rate_window.reset()
    store.reset()
    store.set_multi_worker(False)
    yield isolated_users_root
    rate_window.reset()
    store.reset()


def _tok(uid=UID):
    return svc.token_dir(uid) / "garmin_tokens.json"


def _cfg(uid=UID):
    return json.loads((svc.token_dir(uid).parent / "config.json").read_text())


def test_token_dir_rules(env):
    assert svc.token_dir(UID) == env / UID / ".garminconnect"
    with pytest.raises(ValueError):
        svc.token_dir("../evil")


def test_login_success_persists_and_clears_explicit_paths(monkeypatch):
    update_service_config("garmin", {"tokenstore": "/root/.garminconnect/x", "password": "enc:old"}, user_id=UID)
    cfg, calls = install(monkeypatch, svc)
    data, fail = svc.start_login(UID, " a@x.com ", PW)
    assert fail is None and data["status"] == "connected"
    assert ("login", None) in calls and ("init", "a@x.com", True) in calls
    assert _tok().exists()
    g = _cfg()["garmin"]
    assert g["tokenstore"] == "" and g["password"] == "" and g["email"] == "a@x.com"
    assert PW not in json.dumps(_cfg()) and PW not in json.dumps(data)


def test_login_needs_mfa_clears_password(monkeypatch):
    install(monkeypatch, svc, {"login": ("needs_mfa", None)})
    data, fail = svc.start_login(UID, "a@x.com", PW)
    assert fail is None and data["status"] == "needs_mfa" and data["expires_in"] == 300
    p = store.get(UID, data["mfa_ticket"])
    assert p is not None and p.client.password is None
    assert not _tok().exists()


@pytest.mark.parametrize("exc,code,status", [
    (AUTH("bad pw secret-detail"), "GARMIN_AUTH_FAILED", 401),
    (TOO_MANY("429"), "GARMIN_RATE_LIMITED", 503),
    (CONN("down"), "GARMIN_UPSTREAM", 502),
    (RuntimeError("boom"), "GARMIN_UPSTREAM", 502),
])
def test_login_error_mapping_keeps_existing_token(monkeypatch, exc, code, status):
    _tok().parent.mkdir(parents=True, exist_ok=True)
    _tok().write_text('{"di_token": "OLD"}')
    install(monkeypatch, svc, {"login": exc})
    data, fail = svc.start_login(UID, "a@x.com", PW)
    assert data is None and (fail.code, fail.status) == (code, status)
    assert "secret-detail" not in fail.message
    assert json.loads(_tok().read_text())["di_token"] == "OLD"


def test_login_validation():
    for email, pw in [("", PW), ("a@x.com", ""), ("a" * 255, PW), ("a@x.com", "p" * 257), (None, PW)]:
        assert svc.start_login(UID, email, pw)[1].code == "INVALID_PARAM"


def test_cooldown_blocks_garmin_calls(monkeypatch):
    _, calls = install(monkeypatch, svc, {"login": TOO_MANY("429")})
    assert svc.start_login(UID, "a@x.com", PW)[1].retry_after == 900
    n = len(calls)
    fail = svc.start_login(UID, "a@x.com", PW)[1]
    assert fail.code == "GARMIN_RATE_LIMITED" and len(calls) == n


def test_import_error_maps_upstream_503(monkeypatch):
    def boom():
        raise ImportError("no lib")
    monkeypatch.setattr(svc, "_garmin_cls", boom)
    fail = svc.start_login(UID, "a@x.com", PW)[1]
    assert (fail.code, fail.status) == ("GARMIN_UPSTREAM", 503)


def test_dump_oserror_maps_internal(monkeypatch):
    install(monkeypatch, svc, {"dump_error": OSError("disk")})
    fail = svc.start_login(UID, "a@x.com", PW)[1]
    assert (fail.code, fail.status) == ("INTERNAL", 500)


def test_multi_worker_returns_mfa_unavailable(monkeypatch):
    install(monkeypatch, svc, {"login": ("needs_mfa", None)})
    store.set_multi_worker(True)
    assert svc.start_login(UID, "a@x.com", PW)[1].code == "MFA_UNAVAILABLE"
    assert svc.complete_mfa(UID, "t", "123456")[1].code == "MFA_UNAVAILABLE"


def _pending(monkeypatch, resume=None):
    cfg, calls = install(monkeypatch, svc, {"login": ("needs_mfa", None), "resume": resume or []})
    return svc.start_login(UID, "a@x.com", PW)[0]["mfa_ticket"], calls


def test_mfa_success_persists(monkeypatch):
    ticket, calls = _pending(monkeypatch)
    data, fail = svc.complete_mfa(UID, ticket, " 123456 ")
    assert fail is None and data["status"] == "connected" and ("resume", "123456") in calls
    assert _tok().exists() and store.get(UID, ticket) is None


def test_mfa_wrong_code_keeps_pending_then_expires(monkeypatch):
    ticket, _ = _pending(monkeypatch, [AUTH("bad")] * 5)
    fail = svc.complete_mfa(UID, ticket, "111111")[1]
    assert (fail.code, fail.status, fail.details) == ("MFA_INVALID", 422, {"attempts_left": 4})
    for _ in range(3):
        svc.complete_mfa(UID, ticket, "111111")
    assert svc.complete_mfa(UID, ticket, "111111")[1].code == "MFA_EXPIRED"
    assert svc.complete_mfa(UID, ticket, "111111")[1].status == 410


def test_mfa_rate_limited_keeps_pending(monkeypatch):
    ticket, _ = _pending(monkeypatch, [TOO_MANY("429")])
    fail = svc.complete_mfa(UID, ticket, "123456")[1]
    assert fail.code == "GARMIN_RATE_LIMITED" and fail.retry_after == 900
    assert svc.complete_mfa(UID, ticket, "123456")[0]["status"] == "connected"


def test_mfa_upstream_error_discards(monkeypatch):
    ticket, _ = _pending(monkeypatch, [CONN("x")])
    assert svc.complete_mfa(UID, ticket, "123456")[1].code == "GARMIN_UPSTREAM"
    assert svc.complete_mfa(UID, ticket, "123456")[1].code == "MFA_EXPIRED"


def test_mfa_validation_and_other_user(monkeypatch):
    ticket, _ = _pending(monkeypatch)
    assert svc.complete_mfa(UID, ticket, "12ab56")[1].code == "INVALID_PARAM"
    assert svc.complete_mfa(UID, None, "123456")[1].code == "INVALID_PARAM"
    assert svc.complete_mfa("u2@x.com", ticket, "123456")[1].code == "MFA_EXPIRED"
    assert svc.cancel(UID) == {"status": "disconnected"} and svc.cancel(UID)["status"] == "disconnected"
    assert svc.complete_mfa(UID, ticket, "123456")[1].code == "MFA_EXPIRED"


@pytest.mark.parametrize("raw,ok", [
    ('{"di_token": "a", "di_refresh_token": "b", "evil": 1}', True),
    ('{"di_refresh_token": "b"}', True),
    ('{"oauth2_token": {"access_token": "x"}}', False),
    ("[1, 2]", False), ("not json", False), ("", False), (None, False),
    ('{"di_token": "' + "x" * (16 * 1024) + '"}', False),
])
def test_parse_token(raw, ok):
    tok, err = svc.parse_token(raw)
    assert (tok is not None) is ok and (err is None) is ok
    if ok:
        assert set(tok) <= {"di_token", "di_refresh_token", "di_client_id"}


def test_submit_token_verifies_inline_then_saves(monkeypatch):
    _, calls = install(monkeypatch, svc)
    data, fail = svc.submit_token(UID, '{"di_token": "a", "evil": "zz"}')
    assert fail is None and data["status"] == "connected" and _tok().exists()
    sent = json.loads([c for c in calls if c[0] == "login"][0][1])
    assert sent == {"di_token": "a"}


def test_submit_token_rejected_not_saved(monkeypatch):
    install(monkeypatch, svc, {"login": AUTH("expired")})
    fail = svc.submit_token(UID, '{"di_token": "a"}')[1]
    assert (fail.code, fail.status) == ("GARMIN_AUTH_FAILED", 401) and not _tok().exists()


def test_disconnect_removes_tokens_and_clears_config(monkeypatch, env):
    install(monkeypatch, svc)
    svc.start_login(UID, "a@x.com", PW)
    legacy = env.parent / "legacy" / UID
    legacy.mkdir(parents=True)
    (legacy / "garmin_tokens.json").write_text('{"di_token": "L"}')
    update_service_config("garmin", {"tokenstore": str(legacy), "password": "old"}, user_id=UID)
    store.put(UID, object(), "a@x.com")
    assert dcs.disconnect("garmin", UID) == {"provider": "garmin", "keep_data": True}
    assert not _tok().exists() and not (legacy / "garmin_tokens.json").exists()
    g = _cfg()["garmin"]
    assert (g["email"], g["tokenstore"], g["password"]) == ("", "", "")
    assert store._items == {}
    assert check_garmin_connection(load_config(user_id=UID))["ok"] is False


def test_connected_token_readable_by_sync_rules(monkeypatch):
    install(monkeypatch, svc)
    svc.start_login(UID, "a@x.com", PW)
    assert check_garmin_connection(load_config(user_id=UID))["ok"] is True


def test_data_connect_delegates_garmin(monkeypatch):
    install(monkeypatch, svc, {"login": AUTH("x")})
    payload, code = dcs.connect("garmin", UID, {"email": "a@x.com", "password": PW})
    assert code == "GARMIN_AUTH_FAILED" and PW not in json.dumps(payload)


def test_mask_email():
    assert svc.mask_email("abc@d.com") == "a***@d.com" and svc.mask_email("x") == "***"


def test_rate_window_remaining_counts_from_latest_hit():
    rate_window.hit("k", 5, 900, now=100.0)
    rate_window.hit("k", 5, 900, now=400.0)
    assert rate_window.remaining("k", 900, now=500.0) == 800.0
    assert rate_window.remaining("k", 900, now=1400.0) == 0.0
    assert rate_window.remaining("none", 900, now=0.0) == 0.0


def test_cooldown_retry_after_is_actual_remaining(monkeypatch):
    clock = {"t": 1000.0}
    monkeypatch.setattr(rate_window.time, "monotonic", lambda: clock["t"])
    install(monkeypatch, svc, {"login": TOO_MANY("429")})
    first = svc.start_login(UID, "a@x.com", PW)[1]
    assert first.retry_after == 900 and first.details == {"retry_after_sec": 900}
    assert "15분" in first.message
    clock["t"] += 600.5  # 10분 경과 → 남은 299.5초 → 올림 300
    again = svc.start_login(UID, "a@x.com", PW)[1]
    assert again.code == "GARMIN_RATE_LIMITED"
    assert again.retry_after == 300 and again.details == {"retry_after_sec": 300}
    assert "5분" in again.message
    assert svc.cooldown_remaining(UID) == 300
    clock["t"] += 300
    assert svc.cooldown_remaining(UID) == 0 and not svc.in_cooldown(UID)
