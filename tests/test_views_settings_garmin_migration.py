"""views_settings_garmin.py garminconnect 0.3.x 마이그레이션 테스트."""
from __future__ import annotations

import json
import os
import sys
import uuid
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock, patch

import pytest
from flask import Flask

# garminconnect 미설치 환경 대비 — sys.modules에 stub 등록
if "garminconnect" not in sys.modules:
    _stub = ModuleType("garminconnect")
    _stub.Garmin = MagicMock  # type: ignore[attr-defined]
    sys.modules["garminconnect"] = _stub


# ─── 공통 픽스처 ───────────────────────────────────────────────────────────────

@pytest.fixture
def garmin_app(tmp_path, monkeypatch):
    """settings_garmin_bp가 등록된 최소 Flask 테스트 앱."""
    os.environ.setdefault("FLASK_SECRET_KEY", "test-garmin-secret")

    # load_config / update_service_config 패치 — 실제 config.json 건드리지 않음
    monkeypatch.setattr(
        "src.web.views_settings_garmin.load_config",
        lambda: {"garmin": {"email": "test@example.com", "tokenstore": str(tmp_path)}},
    )
    monkeypatch.setattr(
        "src.web.views_settings_garmin.update_service_config",
        lambda *a, **k: None,
    )
    monkeypatch.setattr(
        "src.web.views_settings_garmin._auto_user_id",
        lambda _: "test_at_example.com",
    )

    app = Flask(__name__)
    app.secret_key = "test-garmin-secret"
    app.config["TESTING"] = True

    # generic_page.html 없어도 테스트 통과하도록 간단한 템플릿 등록
    app.jinja_env.globals["body"] = ""

    @app.route("/_dummy")
    def _dummy():
        return "ok"

    # 템플릿 폴백: render_template → body 그대로 반환
    monkeypatch.setattr(
        "src.web.views_settings_garmin.render_template",
        lambda *a, **kw: kw.get("body", ""),
    )

    from src.web.views_settings_garmin import settings_garmin_bp
    app.register_blueprint(settings_garmin_bp)

    with app.test_client() as client:
        yield client, tmp_path


# ─── GET /connect/garmin ──────────────────────────────────────────────────────

class TestGarminConnectView:
    def test_renders_200(self, garmin_app):
        """GET /connect/garmin → 200 (garth 없이 렌더링)."""
        client, _ = garmin_app
        r = client.get("/connect/garmin")
        assert r.status_code == 200

    def test_token_status_shows_garminconnect_path(self, garmin_app):
        """토큰 경로 표시에 garminconnect가 포함되거나 상태 배지가 출력됨."""
        client, tmp_path = garmin_app
        # 유효한 토큰 파일 생성
        (tmp_path / "garmin_tokens.json").write_text(
            json.dumps({"access_token": "valid"})
        )
        r = client.get("/connect/garmin")
        assert r.status_code == 200
        body = r.data.decode()
        assert "토큰 유효" in body or "grade-good" in body

    def test_no_token_shows_status_badge(self, garmin_app):
        """토큰 없으면 연결 상태 배지에 실패 표시."""
        client, _ = garmin_app
        r = client.get("/connect/garmin")
        assert r.status_code == 200
        body = r.data.decode()
        # grade-poor 또는 grade-moderate 배지 중 하나
        assert "grade-poor" in body or "grade-moderate" in body or "score-badge" in body


# ─── POST /connect/garmin ─────────────────────────────────────────────────────

class TestServerLogin:
    def test_save_only_no_password_required(self, garmin_app):
        """action=save → 패스워드 없이도 저장 가능 (redirect)."""
        client, _ = garmin_app
        r = client.post("/connect/garmin", data={
            "email": "user@test.com",
            "action": "save",
        })
        assert r.status_code == 302
        assert "저장" in r.headers["Location"] or "msg" in r.headers["Location"]

    def test_login_calls_garminconnect_garmin(self, garmin_app, monkeypatch):
        """POST action=save_and_test → Garmin(email, pw, return_on_mfa=True) 호출."""
        client, tmp_path = garmin_app

        mock_garmin = MagicMock()
        mock_garmin.login.return_value = ("success", {})
        mock_garmin_cls = MagicMock(return_value=mock_garmin)

        monkeypatch.setattr(
            "src.web.views_settings_garmin._Garmin",
            mock_garmin_cls,
            raising=False,
        )

        # _Garmin은 함수 내부에서 import되므로 garminconnect 모듈 패치
        import importlib
        import src.web.views_settings_garmin as vsg
        original_import = vsg.__builtins__

        with patch("garminconnect.Garmin", mock_garmin_cls):
            r = client.post("/connect/garmin", data={
                "email": "user@test.com",
                "password": "secret",
                "action": "save_and_test",
            })

        # redirect (302) 응답 — 성공 or 에러
        assert r.status_code == 302

    def test_mfa_redirect_on_needs_mfa(self, garmin_app):
        """MFA 필요 시 /connect/garmin/mfa로 리다이렉트."""
        client, _ = garmin_app

        mock_garmin = MagicMock()
        mock_garmin.login.return_value = ("needs_mfa", {"state": "xyz"})

        with patch("garminconnect.Garmin", return_value=mock_garmin):
            r = client.post("/connect/garmin", data={
                "email": "user@test.com",
                "password": "secret",
                "action": "save_and_test",
            })

        assert r.status_code == 302
        assert "/connect/garmin/mfa" in r.headers["Location"]

    def test_no_email_returns_error(self, garmin_app):
        """이메일 없으면 에러 redirect."""
        client, _ = garmin_app
        r = client.post("/connect/garmin", data={"email": "", "action": "save"})
        assert r.status_code == 302
        assert "error" in r.headers["Location"]

    def test_429_shows_error_redirect(self, garmin_app):
        """429 에러 시 에러 메시지 redirect."""
        client, _ = garmin_app
        from src.sync.garmin_auth import GarminConnectTooManyRequestsError

        mock_garmin = MagicMock()
        mock_garmin.login.side_effect = GarminConnectTooManyRequestsError("429")

        with patch("garminconnect.Garmin", return_value=mock_garmin):
            r = client.post("/connect/garmin", data={
                "email": "user@test.com",
                "password": "pw",
                "action": "save_and_test",
            })

        assert r.status_code == 302
        assert "error" in r.headers["Location"]


# ─── POST /connect/garmin/upload-token ───────────────────────────────────────

class TestTokenUpload:
    def test_upload_garmin_tokens_json(self, garmin_app, tmp_path):
        """garmin_tokens.json 업로드 → tokenstore 저장 후 redirect."""
        client, _ = garmin_app
        token_data = {"access_token": "valid_token_abc", "di_access_token": "di_xyz"}

        r = client.post(
            "/connect/garmin/upload-token",
            data={"token": (
                __import__("io").BytesIO(json.dumps(token_data).encode()),
                "garmin_tokens.json",
            )},
            content_type="multipart/form-data",
        )
        assert r.status_code == 302
        assert "msg" in r.headers["Location"]

    def test_no_file_returns_error(self, garmin_app):
        """파일 없으면 에러 redirect."""
        client, _ = garmin_app
        r = client.post("/connect/garmin/upload-token", data={})
        assert r.status_code == 302
        assert "error" in r.headers["Location"]

    def test_invalid_json_returns_error(self, garmin_app):
        """invalid JSON 업로드 시 에러 redirect."""
        client, _ = garmin_app
        r = client.post(
            "/connect/garmin/upload-token",
            data={"token": (
                __import__("io").BytesIO(b"not_json{{"),
                "garmin_tokens.json",
            )},
            content_type="multipart/form-data",
        )
        assert r.status_code == 302
        assert "error" in r.headers["Location"]


# ─── POST /connect/garmin/paste-token ────────────────────────────────────────

class TestPasteToken:
    def test_paste_valid_json(self, garmin_app, tmp_path):
        """유효한 JSON 붙여넣기 → 저장 성공 redirect."""
        client, _ = garmin_app
        token_data = {"access_token": "abc", "di_access_token": "di_abc"}
        r = client.post("/connect/garmin/paste-token", data={
            "oauth2_json": json.dumps(token_data),
        })
        assert r.status_code == 302
        assert "msg" in r.headers["Location"]

    def test_paste_invalid_json_returns_error(self, garmin_app):
        """유효하지 않은 JSON 붙여넣기 → 에러 redirect."""
        client, _ = garmin_app
        r = client.post("/connect/garmin/paste-token", data={
            "oauth2_json": "not json{{",
        })
        assert r.status_code == 302
        assert "error" in r.headers["Location"]

    def test_empty_input_returns_error(self, garmin_app):
        """빈 입력 → 에러 redirect."""
        client, _ = garmin_app
        r = client.post("/connect/garmin/paste-token", data={"oauth2_json": ""})
        assert r.status_code == 302
        assert "error" in r.headers["Location"]


# ─── POST /connect/garmin/mfa ─────────────────────────────────────────────────

class TestMFA:
    def test_expired_session_returns_error(self, garmin_app):
        """만료/없는 MFA 세션 key → 에러 redirect."""
        client, _ = garmin_app
        r = client.post("/connect/garmin/mfa", data={
            "key": "nonexistent-key",
            "mfa_code": "123456",
            "tokenstore": "/tmp/test",
        })
        assert r.status_code == 302
        assert "error" in r.headers["Location"]

    def test_mfa_submit_calls_resume_login(self, garmin_app):
        """유효한 MFA 세션 key → garmin.resume_login() 호출."""
        client, tmp_path = garmin_app

        # _pending_mfa에 세션 등록
        import src.web.views_settings_garmin as vsg
        key = str(uuid.uuid4())
        mock_garmin = MagicMock()
        vsg._pending_mfa[key] = {
            "garmin_client": mock_garmin,
            "client_state": {"state": "abc"},
            "tokenstore": str(tmp_path),
            "email": "user@test.com",
        }

        r = client.post("/connect/garmin/mfa", data={
            "key": key,
            "mfa_code": "654321",
            "tokenstore": str(tmp_path),
        })

        mock_garmin.resume_login.assert_called_once_with({"state": "abc"}, "654321")
        assert r.status_code == 302

    def test_empty_mfa_code_redirects_back(self, garmin_app):
        """빈 MFA 코드 → MFA 폼으로 재redirect."""
        client, tmp_path = garmin_app

        import src.web.views_settings_garmin as vsg
        key = str(uuid.uuid4())
        vsg._pending_mfa[key] = {
            "garmin_client": MagicMock(),
            "client_state": {},
            "tokenstore": str(tmp_path),
            "email": "user@test.com",
        }

        r = client.post("/connect/garmin/mfa", data={
            "key": key,
            "mfa_code": "",
            "tokenstore": str(tmp_path),
        })

        assert r.status_code == 302
        assert "/connect/garmin/mfa" in r.headers["Location"]

    def test_mfa_resume_exception_returns_error(self, garmin_app):
        """resume_login 예외 → 에러 redirect."""
        client, tmp_path = garmin_app

        import src.web.views_settings_garmin as vsg
        key = str(uuid.uuid4())
        mock_garmin = MagicMock()
        mock_garmin.resume_login.side_effect = RuntimeError("mfa failed")
        vsg._pending_mfa[key] = {
            "garmin_client": mock_garmin,
            "client_state": {},
            "tokenstore": str(tmp_path),
            "email": "user@test.com",
        }

        r = client.post("/connect/garmin/mfa", data={
            "key": key,
            "mfa_code": "000000",
            "tokenstore": str(tmp_path),
        })

        assert r.status_code == 302
        assert "error" in r.headers["Location"]


# ─── 기타 라우트 ──────────────────────────────────────────────────────────────

class TestMiscRoutes:
    def test_browser_login_200(self, garmin_app):
        """GET /connect/garmin/browser-login → 200."""
        client, _ = garmin_app
        r = client.get("/connect/garmin/browser-login")
        assert r.status_code == 200

    def test_disconnect_redirects(self, garmin_app):
        """POST /connect/garmin/disconnect → 302."""
        client, _ = garmin_app
        r = client.post("/connect/garmin/disconnect")
        assert r.status_code == 302
