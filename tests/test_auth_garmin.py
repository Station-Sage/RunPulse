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
    """이메일/패스워드도 없고 토큰도 없으면 미설정."""
    config = {"garmin": {}}
    result = check_garmin_connection(config)
    assert result["ok"] is False
    assert "미설정" in result["status"]


def test_check_garmin_email_password_only():
    """이메일/패스워드만 있으면 ok=True, 토큰 없음 안내."""
    config = {"garmin": {"email": "a@b.com", "password": "pw"}}
    result = check_garmin_connection(config)
    assert result["ok"] is True
    assert "이메일" in result["status"] or "패스워드" in result["status"]


def test_check_garmin_tokenstore_exists(tmp_path):
    """tokenstore 디렉터리가 존재하면 ok=True, 토큰 저장소 존재."""
    tokenstore = tmp_path / "garth"
    tokenstore.mkdir()
    config = {"garmin": {"tokenstore": str(tokenstore)}}
    result = check_garmin_connection(config)
    assert result["ok"] is True
    assert "토큰" in result["status"]
    assert str(tokenstore) in result["tokenstore"]


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

    with patch("src.sync.garmin.Garmin", return_value=mock_client) as MockGarmin:
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

    with patch("src.sync.garmin.Garmin", side_effect=mock_garmin):
        from src.sync.garmin import _login
        result = _login(config)
        assert result is mock_client_pw
        assert call_count[0] == 2
