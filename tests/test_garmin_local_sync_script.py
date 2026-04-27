"""scripts/garmin_local_sync.py 유닛 테스트."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock, patch

import pytest

# ── garminconnect stub ────────────────────────────────────────────────────────

if "garminconnect" not in sys.modules:
    _stub = ModuleType("garminconnect")

    class _FakeTooMany(Exception):
        pass

    _stub.Garmin = MagicMock  # type: ignore[attr-defined]
    _stub.GarminConnectTooManyRequestsError = _FakeTooMany  # type: ignore[attr-defined]
    sys.modules["garminconnect"] = _stub


# ── helpers ───────────────────────────────────────────────────────────────────

def _import_script():
    """scripts/garmin_local_sync.py를 importlib로 로드."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "garmin_local_sync",
        Path(__file__).parents[1] / "scripts" / "garmin_local_sync.py",
    )
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


# ── _ensure_deps ─────────────────────────────────────────────────────────────

class TestEnsureDeps:
    def test_skips_install_when_garminconnect_importable(self, monkeypatch):
        """garminconnect import 성공 → subprocess 호출 없음."""
        mod = _import_script()

        with patch.dict(sys.modules, {"garminconnect": MagicMock()}):
            with patch("subprocess.check_call") as mock_call:
                mod._ensure_deps()
        mock_call.assert_not_called()

    def test_installs_when_garminconnect_missing(self):
        """garminconnect import 실패 → subprocess.check_call 호출."""
        mod = _import_script()

        original = sys.modules.pop("garminconnect", None)
        try:
            with patch("subprocess.check_call") as mock_call:
                mod._ensure_deps()
            mock_call.assert_called_once()
            args = mock_call.call_args[0][0]
            assert sys.executable in args
            assert "pip" in args
            assert any("garminconnect" in a for a in args)
        finally:
            if original is not None:
                sys.modules["garminconnect"] = original


# ── _load_dotenv ──────────────────────────────────────────────────────────────

class TestLoadDotenv:
    def test_loads_from_env_file(self, tmp_path, monkeypatch):
        """스크립트 디렉터리의 .env 파일에서 환경변수를 로드한다."""
        env_file = tmp_path / ".env"
        env_file.write_text('GARMIN_EMAIL=test@example.com\nGARMIN_VPS_URL="https://vps.example.com"\n')

        mod = _import_script()

        # monkeypatch: __file__을 tmp_path로 교체
        with patch.object(mod, "__file__", str(tmp_path / "garmin_local_sync.py")):
            monkeypatch.delenv("GARMIN_EMAIL", raising=False)
            monkeypatch.delenv("GARMIN_VPS_URL", raising=False)
            import os
            mod._load_dotenv()
            assert os.environ.get("GARMIN_EMAIL") == "test@example.com"
            assert os.environ.get("GARMIN_VPS_URL") == "https://vps.example.com"

    def test_ignores_comments_and_blank_lines(self, tmp_path, monkeypatch):
        """# 주석과 빈 줄은 무시한다."""
        env_file = tmp_path / ".env"
        env_file.write_text("# comment\n\nFOO_VAR=bar\n")

        mod = _import_script()
        with patch.object(mod, "__file__", str(tmp_path / "garmin_local_sync.py")):
            monkeypatch.delenv("FOO_VAR", raising=False)
            import os
            mod._load_dotenv()
            assert os.environ.get("FOO_VAR") == "bar"


# ── _garmin_login ─────────────────────────────────────────────────────────────

class TestGarminLogin:
    def test_returns_token_dict_on_success(self, tmp_path, monkeypatch):
        """로그인 성공 시 garmin_tokens.json(DI 형식) 내용을 반환한다."""
        token_data = {"di_token": "di_abc123", "di_refresh_token": "di_xyz", "di_client_id": "cid"}
        mod = _import_script()

        monkeypatch.setenv("GARMIN_TOKENSTORE", str(tmp_path))

        def _fake_login(tokenstore=None):
            (Path(tokenstore) / "garmin_tokens.json").write_text(json.dumps(token_data))
            return (None, None)

        mock_client = MagicMock()
        mock_client.login.side_effect = _fake_login

        with patch.dict(sys.modules, {"garminconnect": MagicMock(
            Garmin=MagicMock(return_value=mock_client),
            GarminConnectTooManyRequestsError=Exception,
        )}):
            result = mod._garmin_login("user@test.com", "pass")

        mock_client.login.assert_called_once_with(tokenstore=str(tmp_path))
        assert result == token_data

    def test_fresh_login_creates_token_file(self, tmp_path, monkeypatch):
        """토큰 없음(첫 실행) → login(tokenstore=...) 호출, garmin_tokens.json 저장."""
        token_data = {"di_token": "fresh_di_tok", "di_refresh_token": "rr", "di_client_id": "cid"}
        mod = _import_script()

        monkeypatch.setenv("GARMIN_TOKENSTORE", str(tmp_path))

        def _fake_login(tokenstore=None):
            (Path(tokenstore) / "garmin_tokens.json").write_text(json.dumps(token_data))
            return (None, None)

        mock_client = MagicMock()
        mock_client.login.side_effect = _fake_login

        with patch.dict(sys.modules, {"garminconnect": MagicMock(
            Garmin=MagicMock(return_value=mock_client),
            GarminConnectTooManyRequestsError=Exception,
        )}):
            result = mod._garmin_login("user@test.com", "pass")

        mock_client.login.assert_called_once_with(tokenstore=str(tmp_path))
        assert result == token_data

    def test_exits_on_too_many_requests(self, tmp_path, monkeypatch):
        """429 에러 시 sys.exit(1)."""
        mod = _import_script()

        monkeypatch.setenv("GARMIN_TOKENSTORE", str(tmp_path))

        class _FakeTooMany(Exception):
            pass

        mock_client = MagicMock()
        mock_client.login.side_effect = _FakeTooMany()

        with patch.dict(sys.modules, {"garminconnect": MagicMock(
            Garmin=MagicMock(return_value=mock_client),
            GarminConnectTooManyRequestsError=_FakeTooMany,
        )}):
            with pytest.raises(SystemExit) as exc:
                mod._garmin_login("u@t.com", "pw")
        assert exc.value.code == 1


# ── _upload_token ─────────────────────────────────────────────────────────────

class TestUploadToken:
    def test_posts_json_with_cf_headers(self):
        """토큰과 CF 헤더를 올바른 URL로 POST한다."""
        mod = _import_script()
        token = {"access_token": "tok"}
        response_body = json.dumps({"message": "sync 시작", "job_id": "j-123"}).encode()

        mock_resp = MagicMock()
        mock_resp.read.return_value = response_body
        mock_resp.status = 202
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        captured = {}

        def _fake_urlopen(req, timeout=None):
            captured["url"] = req.full_url
            captured["headers"] = dict(req.headers)
            captured["method"] = req.method
            captured["data"] = json.loads(req.data.decode())
            return mock_resp

        # curl_cffi 없는 환경을 시뮬레이션 → urllib fallback 경로 테스트
        with patch.dict(sys.modules, {"curl_cffi": None}):
            with patch("urllib.request.urlopen", side_effect=_fake_urlopen):
                mod._upload_token(
                    "https://vps.example.com",
                    token,
                    days=30,
                    cf_id="client.access",
                    cf_secret="secret123",
                    user_id="github@example.com",
                )

        assert captured["url"] == "https://vps.example.com/api/garmin/local-sync"
        assert captured["method"] == "POST"
        assert captured["headers"].get("Cf-access-client-id") == "client.access"
        assert captured["headers"].get("Cf-access-client-secret") == "secret123"
        assert captured["data"]["days"] == 30
        assert captured["data"]["token"] == token
        assert captured["data"]["user_id"] == "github@example.com"

    def test_exits_on_401(self):
        """401 응답 시 sys.exit(1)."""
        mod = _import_script()
        import urllib.error

        err = urllib.error.HTTPError(
            url="https://vps.example.com/api/garmin/local-sync",
            code=401, msg="Unauthorized", hdrs=MagicMock(), fp=None,
        )
        with patch.dict(sys.modules, {"curl_cffi": None}):
            with patch("urllib.request.urlopen", side_effect=err):
                with pytest.raises(SystemExit) as exc:
                    mod._upload_token("https://vps.example.com", {}, 7, "id", "secret", "u@t.com")
        assert exc.value.code == 1


# ── token_only mode ───────────────────────────────────────────────────────────

class TestTokenOnlyMode:
    def test_saves_token_locally(self, tmp_path, monkeypatch):
        """--token-only 플래그 시 garmin_tokens.json 저장 후 종료 (업로드 없음)."""
        token_data = {"access_token": "local_tok"}
        mod = _import_script()

        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(mod, "_ensure_venv", lambda: None)
        monkeypatch.setattr(mod, "_ensure_deps", lambda: None)
        monkeypatch.setattr(mod, "_load_dotenv", lambda: None)
        monkeypatch.setattr(mod, "_garmin_login", lambda e, p: token_data)
        monkeypatch.setattr(sys, "argv", [
            "garmin_local_sync.py", "--email", "u@t.com",
            "--password", "pw", "--token-only",
        ])

        mod.main()

        saved = json.loads((tmp_path / "garmin_tokens.json").read_text())
        assert saved == token_data
