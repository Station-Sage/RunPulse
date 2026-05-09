"""garmin_auth.py garminconnect 0.3.x 마이그레이션 테스트."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.sync.garmin_auth import (
    GarminAuthRequired,
    _tokenstore_path,
    check_garmin_connection,
    _login,
)


# ─── _tokenstore_path ────────────────────────────────────────────────────────

class TestTokenstorePath:
    def test_default_path(self):
        """config 없으면 data/users 기반 프로젝트 로컬 경로 반환."""
        from src.utils.config import get_config_path
        expected = get_config_path().parent / ".garminconnect"
        path = _tokenstore_path({})
        assert path == expected

    def test_explicit_path(self, tmp_path):
        """garmin.tokenstore 명시 시 그 경로 반환 (존재 여부 무관)."""
        config = {"garmin": {"tokenstore": str(tmp_path)}}
        assert _tokenstore_path(config) == tmp_path

    def test_user_id_path(self):
        """garmin.user_id 설정 시 data/users/{uid}/.garminconnect 반환."""
        from src.utils.config import get_config_path
        config = {"garmin": {"user_id": "runner"}}
        path = _tokenstore_path(config)
        expected = get_config_path("runner").parent / ".garminconnect"
        assert path == expected

    def test_user_id_email_sanitize(self):
        """user_id가 이메일이어도 그대로 경로에 반영된다."""
        from src.utils.config import get_config_path
        config = {"garmin": {"user_id": "user@example.com"}}
        path = _tokenstore_path(config)
        expected = get_config_path("user@example.com").parent / ".garminconnect"
        assert path == expected

    def test_explicit_takes_precedence_over_user_id(self, tmp_path):
        """tokenstore가 명시되면 user_id보다 우선."""
        config = {"garmin": {"tokenstore": str(tmp_path), "user_id": "other"}}
        assert _tokenstore_path(config) == tmp_path


# ─── _login ──────────────────────────────────────────────────────────────────

class TestLogin:
    def test_no_token_file_raises(self, tmp_path):
        """토큰 파일 없으면 GarminAuthRequired."""
        config = {"garmin": {"tokenstore": str(tmp_path)}}
        # garminconnect 미설치 환경에서도 Garmin을 non-None으로 패치
        with patch("src.sync.garmin_auth.Garmin", MagicMock()):
            with pytest.raises(GarminAuthRequired, match="토큰 없음"):
                _login(config)

    def test_token_file_exists_calls_login(self, tmp_path):
        """토큰 파일 존재 시 Garmin().login(tokenstore=...) 호출."""
        token_file = tmp_path / "garmin_tokens.json"
        token_file.write_text('{"access_token": "abc"}')
        config = {"garmin": {"tokenstore": str(tmp_path)}}

        mock_client = MagicMock()
        mock_garmin_cls = MagicMock(return_value=mock_client)

        with patch("src.sync.garmin_auth.Garmin", mock_garmin_cls):
            result = _login(config)

        mock_garmin_cls.assert_called_once_with()
        mock_client.login.assert_called_once_with(tokenstore=str(tmp_path))
        assert result is mock_client

    def test_token_dump_called_on_success(self, tmp_path):
        """로그인 성공 시 client.client.dump() 호출."""
        (tmp_path / "garmin_tokens.json").write_text('{"access_token": "abc"}')
        config = {"garmin": {"tokenstore": str(tmp_path)}}

        mock_client = MagicMock()
        with patch("src.sync.garmin_auth.Garmin", return_value=mock_client):
            _login(config)

        mock_client.client.dump.assert_called_once_with(str(tmp_path))

    def test_429_propagated(self, tmp_path):
        """GarminConnectTooManyRequestsError는 그대로 전파."""
        from src.sync.garmin_auth import GarminConnectTooManyRequestsError
        (tmp_path / "garmin_tokens.json").write_text('{"access_token": "abc"}')
        config = {"garmin": {"tokenstore": str(tmp_path)}}

        mock_client = MagicMock()
        mock_client.login.side_effect = GarminConnectTooManyRequestsError("429")

        with patch("src.sync.garmin_auth.Garmin", return_value=mock_client):
            with pytest.raises(GarminConnectTooManyRequestsError):
                _login(config)

    def test_auth_error_wraps_to_auth_required(self, tmp_path):
        """GarminConnectAuthenticationError → GarminAuthRequired 변환."""
        from src.sync.garmin_auth import GarminConnectAuthenticationError
        (tmp_path / "garmin_tokens.json").write_text('{"access_token": "abc"}')
        config = {"garmin": {"tokenstore": str(tmp_path)}}

        mock_client = MagicMock()
        mock_client.login.side_effect = GarminConnectAuthenticationError("auth fail")

        with patch("src.sync.garmin_auth.Garmin", return_value=mock_client):
            with pytest.raises(GarminAuthRequired):
                _login(config)

    def test_generic_exception_wraps_to_auth_required(self, tmp_path):
        """예기치 않은 예외 → GarminAuthRequired 변환."""
        (tmp_path / "garmin_tokens.json").write_text('{"access_token": "abc"}')
        config = {"garmin": {"tokenstore": str(tmp_path)}}

        mock_client = MagicMock()
        mock_client.login.side_effect = RuntimeError("unexpected")

        with patch("src.sync.garmin_auth.Garmin", return_value=mock_client):
            with pytest.raises(GarminAuthRequired):
                _login(config)


# ─── check_garmin_connection ──────────────────────────────────────────────────

class TestCheckConnection:
    def test_no_tokenstore_dir(self):
        """존재하지 않는 경로 → 미설정."""
        config = {"garmin": {"tokenstore": "/nonexistent/path/xyz"}}
        result = check_garmin_connection(config)
        assert result["ok"] is False
        assert "미설정" in result["status"]

    def test_dir_exists_no_token_file(self, tmp_path):
        """디렉터리만 존재, 토큰 파일 없음 → 토큰 없음."""
        config = {"garmin": {"tokenstore": str(tmp_path)}}
        result = check_garmin_connection(config)
        assert result["ok"] is False
        assert "토큰 없음" in result["status"]

    def test_old_garth_token_detected(self, tmp_path):
        """oauth2_token.json 존재, garmin_tokens.json 없음 → 마이그레이션 안내."""
        (tmp_path / "oauth2_token.json").write_text('{}')
        config = {"garmin": {"tokenstore": str(tmp_path)}}
        result = check_garmin_connection(config)
        assert result["ok"] is False
        assert "garth" in result["status"] or "마이그레이션" in result["status"]

    def test_valid_token_with_access_token(self, tmp_path):
        """access_token 포함 garmin_tokens.json → ok=True."""
        (tmp_path / "garmin_tokens.json").write_text(
            json.dumps({"access_token": "abc123"})
        )
        config = {"garmin": {"tokenstore": str(tmp_path)}}
        result = check_garmin_connection(config)
        assert result["ok"] is True
        assert result["status"] == "연결됨"

    def test_valid_token_with_di_access_token(self, tmp_path):
        """di_access_token 포함 garmin_tokens.json → ok=True."""
        (tmp_path / "garmin_tokens.json").write_text(
            json.dumps({"di_access_token": "di_abc"})
        )
        config = {"garmin": {"tokenstore": str(tmp_path)}}
        result = check_garmin_connection(config)
        assert result["ok"] is True

    def test_corrupted_token_json(self, tmp_path):
        """garmin_tokens.json JSON 파싱 실패 → 토큰 손상."""
        (tmp_path / "garmin_tokens.json").write_text("not valid json{{")
        config = {"garmin": {"tokenstore": str(tmp_path)}}
        result = check_garmin_connection(config)
        assert result["ok"] is False
        assert "손상" in result["status"]

    def test_token_missing_access_key(self, tmp_path):
        """garmin_tokens.json에 access_token/di_access_token 없음 → 토큰 손상."""
        (tmp_path / "garmin_tokens.json").write_text(json.dumps({"other": "data"}))
        config = {"garmin": {"tokenstore": str(tmp_path)}}
        result = check_garmin_connection(config)
        assert result["ok"] is False
        assert "손상" in result["status"]
