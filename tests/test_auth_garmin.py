"""Garmin 인증 로직 테스트 — 토큰 우선 흐름, fallback, check_garmin_connection."""
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.sync.garmin import check_garmin_connection, _tokenstore_path


# ── _tokenstore_path ────────────────────────────────────────────────
def test_tokenstore_default():
    """기본 경로는 ~/.garth 이다."""
    config = {"garmin": {}}
    path = _tokenstore_path(config)
    assert path == Path("~/.garth").expanduser()


def test_tokenstore_custom():
    """config에 설정된 경로를 사용한다."""
    config = {"garmin": {"tokenstore": "/tmp/my_garth"}}
    path = _tokenstore_path(config)
    assert path == Path("/tmp/my_garth")


# ── check_garmin_connection ─────────────────────────────────────────
def test_check_garmin_no_config():
    """이메일/패스워드도 없고 토큰도 없으면 미설정 or 토큰 없음."""
    config = {"garmin": {}}
    result = check_garmin_connection(config)
    assert result["ok"] is False
    # "미설정" 또는 "토큰 없음" — tokenstore 기본값(~/.garth) 존재 여부에 따라 다름
    assert result["ok"] is False


def test_check_garmin_email_password_only():
    """이메일/패스워드만 있고 tokenstore 없으면 ok=False (로그인 필요 안내)."""
    config = {"garmin": {
        "email": "a@b.com", "password": "pw",
        "tokenstore": "/nonexistent/nowhere/garth",
    }}
    result = check_garmin_connection(config)
    assert result["ok"] is False
    # "미로그인" 상태여야 함
    assert "미로그인" in result["status"] or "미설정" in result["status"]


def test_check_garmin_tokenstore_exists(tmp_path):
    """tokenstore 디렉터리만 있고 oauth2_token.json 없으면 ok=False."""
    tokenstore = tmp_path / "garth"
    tokenstore.mkdir()
    config = {"garmin": {"tokenstore": str(tokenstore)}}
    result = check_garmin_connection(config)
    assert result["ok"] is False
    assert "토큰" in result["status"]


def test_check_garmin_tokenstore_with_valid_token(tmp_path, monkeypatch):
    """oauth2_token.json이 있고 garth 로드 성공 시 ok=True."""
    import time
    import json
    import types

    tokenstore = tmp_path / "garth"
    tokenstore.mkdir()
    (tokenstore / "oauth1_token.json").write_text(json.dumps({
        "oauth_token": "tok", "oauth_token_secret": "sec", "mfa_token": None, "domain": "garmin.com",
    }), encoding="utf-8")
    future = int(time.time()) + 3600
    (tokenstore / "oauth2_token.json").write_text(json.dumps({
        "scope": "read", "jti": "jti", "token_type": "Bearer",
        "access_token": "acc", "refresh_token": "ref",
        "expires_in": 3600, "expires_at": future,
        "refresh_token_expires_in": 7776000, "refresh_token_expires_at": future + 7776000,
    }), encoding="utf-8")

    # garth mock: Client().load()로 토큰 읽기 성공 시뮬레이션
    class _FakeToken:
        expired = False
        refresh_expired = False

    class _FakeClient:
        oauth2_token = _FakeToken()
        def load(self, path):
            pass

    fake_garth = types.ModuleType("garth")
    fake_garth.Client = lambda: _FakeClient()
    monkeypatch.setitem(__import__("sys").modules, "garth", fake_garth)

    config = {"garmin": {"tokenstore": str(tokenstore)}}
    result = check_garmin_connection(config)
    assert result["ok"] is True
    assert "연결됨" in result["status"]


def test_check_garmin_tokenstore_missing_email_missing():
    """tokenstore도 없고 이메일도 없으면 미설정."""
    config = {"garmin": {"tokenstore": "/nonexistent/path"}}
    result = check_garmin_connection(config)
    assert result["ok"] is False


# ── _login 토큰 우선 흐름 (단위 mock) ──────────────────────────────
def test_login_uses_tokenstore_if_exists(tmp_path):
    """tokenstore가 있으면 이메일/패스워드 없이도 Garmin() 호출."""
    tokenstore = tmp_path / "garth"
    tokenstore.mkdir()
    config = {"garmin": {"tokenstore": str(tokenstore)}}

    mock_client = MagicMock()
    mock_client.login.return_value = (None, None)

    with patch("src.sync.garmin_auth.Garmin", return_value=mock_client) as MockGarmin:
        from src.sync.garmin import _login
        result = _login(config)
        # 이메일/패스워드 없이 Garmin() 생성됨
        MockGarmin.assert_called_once_with()
        mock_client.login.assert_called_once_with(tokenstore=str(tokenstore))
        assert result is mock_client


def test_login_falls_back_to_email_pw_if_tokenstore_fails(tmp_path):
    """tokenstore 복구 실패 시 이메일/패스워드로 fallback."""
    tokenstore = tmp_path / "garth"
    tokenstore.mkdir()
    config = {
        "garmin": {
            "tokenstore": str(tokenstore),
            "email": "a@b.com",
            "password": "pw",
        }
    }

    mock_client_token = MagicMock()
    mock_client_token.login.side_effect = Exception("토큰 만료")

    mock_client_pw = MagicMock()
    mock_client_pw.login.return_value = ("access", "refresh")
    mock_client_pw.garth = MagicMock()

    call_count = [0]

    def mock_garmin(*args, **kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            return mock_client_token
        return mock_client_pw

    with patch("src.sync.garmin_auth.Garmin", side_effect=mock_garmin):
        from src.sync.garmin import _login
        result = _login(config)
        assert result is mock_client_pw
        assert call_count[0] == 2
