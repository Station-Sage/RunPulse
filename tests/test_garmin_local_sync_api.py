"""POST /api/garmin/local-sync 엔드포인트 테스트.

최소 Flask 앱으로 격리 테스트 (src.web.app 전체 로딩 불필요).
"""
from __future__ import annotations

import hmac
import json
import os
import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock, patch

import pytest
from flask import Flask, Response, jsonify, request, session

# garminconnect stub
if "garminconnect" not in sys.modules:
    _stub = ModuleType("garminconnect")
    _stub.Garmin = MagicMock  # type: ignore[attr-defined]
    sys.modules["garminconnect"] = _stub


VALID_TOKEN = {
    "access_token": "at_abc123",
    "refresh_token": "rt_xyz",
    "expires_at": 9999999999,
}

VALID_TOKEN_COMBINED = {
    "oauth1_token": {"oauth_token": "ot_abc", "oauth_token_secret": "ots_abc"},
    "oauth2_token": {
        "access_token": "at_combined123",
        "refresh_token": "rt_combined",
        "expires_at": 9999999999,
    },
}


def _make_app(tmp_path, start_job_fn=None):
    """최소 Flask 앱에 /api/garmin/local-sync 엔드포인트 등록."""
    from datetime import date as _date, timedelta

    app = Flask(__name__)
    app.secret_key = "test-secret"
    app.config["TESTING"] = True

    # bg_sync stub
    _start_job = start_job_fn or (lambda *a, **k: "j-test-001")

    @app.before_request
    def _set_session():
        session["user_id"] = "test_at_example.com"

    @app.post("/api/garmin/local-sync")
    def garmin_local_sync():
        data = request.get_json(silent=True) or {}
        token = data.get("token")
        if not isinstance(token, dict) or not token:
            return jsonify({"error": "token 필드가 없거나 올바른 형식이 아닙니다."}), 400

        try:
            days = max(1, min(int(data.get("days", 30)), 90))
        except (TypeError, ValueError):
            days = 30

        user_id = data.get("user_id") or session.get("user_id", "default")
        tokenstore = tmp_path / "users" / user_id / ".garminconnect"
        tokenstore.mkdir(parents=True, exist_ok=True)

        try:
            with open(tokenstore / "garmin_tokens.json", "w") as f:
                json.dump(token, f)
            _t2 = token.get("oauth2_token")
            if isinstance(_t2, dict):
                with open(tokenstore / "oauth2_token.json", "w") as f:
                    json.dump(_t2, f)
                _t1 = token.get("oauth1_token")
                if isinstance(_t1, dict):
                    with open(tokenstore / "oauth1_token.json", "w") as f:
                        json.dump(_t1, f)
            else:
                with open(tokenstore / "oauth2_token.json", "w") as f:
                    json.dump(token, f)
        except OSError as e:
            return jsonify({"error": f"토큰 저장 실패: {e}"}), 500

        to_date = _date.today().isoformat()
        from_date = (_date.today() - timedelta(days=days)).isoformat()
        job_id = _start_job("garmin", from_date, to_date, {}, user_id=user_id)

        return jsonify({
            "status": "sync_started",
            "days": days,
            "job_id": job_id,
            "message": f"토큰 저장 완료. Garmin {days}일 동기화 시작됨.",
        }), 202

    return app


# ── 유효 토큰 POST ────────────────────────────────────────────────────────────

class TestGarminLocalSyncEndpoint:
    def test_returns_202_on_valid_token(self, tmp_path):
        """유효한 token + days → 202 + job_id 반환."""
        app = _make_app(tmp_path, start_job_fn=lambda *a, **k: "bg-001")
        with app.test_client() as client:
            r = client.post(
                "/api/garmin/local-sync",
                data=json.dumps({"token": VALID_TOKEN, "days": 14}),
                content_type="application/json",
            )
        assert r.status_code == 202
        body = r.get_json()
        assert body["job_id"] == "bg-001"
        assert body["days"] == 14

    def test_missing_token_returns_400(self, tmp_path):
        """token 필드 없음 → 400."""
        app = _make_app(tmp_path)
        with app.test_client() as client:
            r = client.post(
                "/api/garmin/local-sync",
                data=json.dumps({"days": 7}),
                content_type="application/json",
            )
        assert r.status_code == 400

    def test_empty_token_dict_returns_400(self, tmp_path):
        """token이 빈 dict → access_token 없음 → 400."""
        app = _make_app(tmp_path)
        with app.test_client() as client:
            r = client.post(
                "/api/garmin/local-sync",
                data=json.dumps({"token": {}, "days": 7}),
                content_type="application/json",
            )
        assert r.status_code == 400

    def test_days_clamped_to_90(self, tmp_path):
        """days=999 → 90으로 클램핑."""
        called = {}

        def _capture(*a, **k):
            from datetime import date, timedelta
            called["from_date"] = a[1] if len(a) > 1 else k.get("from_date")
            called["to_date"] = a[2] if len(a) > 2 else k.get("to_date")
            return "j-clamp"

        app = _make_app(tmp_path, start_job_fn=_capture)
        with app.test_client() as client:
            r = client.post(
                "/api/garmin/local-sync",
                data=json.dumps({"token": VALID_TOKEN, "days": 999}),
                content_type="application/json",
            )
        assert r.status_code == 202
        assert r.get_json()["days"] == 90

    def test_di_access_token_accepted(self, tmp_path):
        """di_access_token만 있어도 유효한 토큰으로 처리."""
        app = _make_app(tmp_path)
        token = {"di_access_token": "di_tok_abc"}
        with app.test_client() as client:
            r = client.post(
                "/api/garmin/local-sync",
                data=json.dumps({"token": token, "days": 7}),
                content_type="application/json",
            )
        assert r.status_code == 202

    def test_token_saved_to_disk(self, tmp_path):
        """평면 토큰 → garmin_tokens.json + oauth2_token.json(동일 내용) 저장."""
        app = _make_app(tmp_path)
        with app.test_client() as client:
            client.post(
                "/api/garmin/local-sync",
                data=json.dumps({"token": VALID_TOKEN, "days": 3}),
                content_type="application/json",
            )
        # garmin_tokens.json 생성 확인
        saved_files = list(tmp_path.rglob("garmin_tokens.json"))
        assert len(saved_files) == 1
        saved = json.loads(saved_files[0].read_text())
        assert saved["access_token"] == VALID_TOKEN["access_token"]

    def test_combined_token_saved_to_disk(self, tmp_path):
        """combined 토큰(oauth1+oauth2 중첩) → garmin_tokens.json + split 파일 저장."""
        app = _make_app(tmp_path)
        with app.test_client() as client:
            r = client.post(
                "/api/garmin/local-sync",
                data=json.dumps({"token": VALID_TOKEN_COMBINED, "days": 3}),
                content_type="application/json",
            )
        assert r.status_code == 202
        # garmin_tokens.json: 전체 combined 토큰
        combined_files = list(tmp_path.rglob("garmin_tokens.json"))
        assert len(combined_files) == 1
        saved = json.loads(combined_files[0].read_text())
        assert saved["oauth2_token"]["access_token"] == VALID_TOKEN_COMBINED["oauth2_token"]["access_token"]
        # oauth2_token.json: oauth2 부분만
        oauth2_files = list(tmp_path.rglob("oauth2_token.json"))
        assert len(oauth2_files) == 1
        saved2 = json.loads(oauth2_files[0].read_text())
        assert saved2["access_token"] == VALID_TOKEN_COMBINED["oauth2_token"]["access_token"]
        # oauth1_token.json: oauth1 부분만
        oauth1_files = list(tmp_path.rglob("oauth1_token.json"))
        assert len(oauth1_files) == 1

    def test_combined_token_accepted(self, tmp_path):
        """garmin_tokens.json 형식(중첩 oauth2_token) → 202."""
        app = _make_app(tmp_path)
        with app.test_client() as client:
            r = client.post(
                "/api/garmin/local-sync",
                data=json.dumps({"token": VALID_TOKEN_COMBINED, "days": 7}),
                content_type="application/json",
            )
        assert r.status_code == 202

    def test_non_json_body_returns_400(self, tmp_path):
        """JSON이 아닌 body → get_json(silent=True)가 None → 400."""
        app = _make_app(tmp_path)
        with app.test_client() as client:
            r = client.post(
                "/api/garmin/local-sync",
                data="not-json",
                content_type="application/json",
            )
        assert r.status_code == 400


# ── trigger_sync 옵션 (views_settings_garmin) ─────────────────────────────────

class TestUploadTokenTriggerSync:
    """upload-token, paste-token POST에서 trigger_sync=1 시 bg_sync 호출 검증."""

    @pytest.fixture()
    def garmin_settings_app(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "src.web.views_settings_garmin.load_config",
            lambda **k: {"garmin": {"email": "u@t.com", "tokenstore": str(tmp_path)}},
        )
        monkeypatch.setattr("src.web.views_settings_garmin.update_service_config", lambda *a, **k: None)
        monkeypatch.setattr("src.web.views_settings_garmin._auto_user_id", lambda _: "u_at_t.com")
        monkeypatch.setattr(
            "src.web.views_settings_garmin.render_template",
            lambda *a, **kw: kw.get("body", ""),
        )

        app = Flask(__name__)
        app.secret_key = "test-secret"
        app.config["TESTING"] = True

        from src.web.views_settings_garmin import settings_garmin_bp
        app.register_blueprint(settings_garmin_bp)

        with app.test_client() as client:
            yield client, tmp_path

    def test_upload_with_trigger_sync_redirects(self, garmin_settings_app, monkeypatch):
        """upload-token + trigger_sync=1 → _trigger_sync_and_redirect 호출."""
        import io
        import flask as _flask
        import src.web.views_settings_garmin as _vsg

        client, tmp_path = garmin_settings_app
        called = {"count": 0}

        def _fake_trigger(uid, days):
            called["count"] += 1
            called["uid"] = uid
            called["days"] = days
            return _flask.redirect("/connect/garmin?msg=ok")

        monkeypatch.setattr(_vsg, "_trigger_sync_and_redirect", _fake_trigger)

        r = client.post(
            "/connect/garmin/upload-token",
            data={
                "trigger_sync": "1",
                "days": "14",
                "token": (io.BytesIO(json.dumps(VALID_TOKEN).encode()), "garmin_tokens.json"),
            },
            content_type="multipart/form-data",
        )
        assert r.status_code == 302
        assert called["count"] == 1
        assert called["days"] == 14

    def test_paste_without_trigger_sync_no_bg_job(self, garmin_settings_app, monkeypatch):
        """paste-token trigger_sync 없음 → _trigger_sync_and_redirect 호출 안 됨."""
        import flask as _flask
        import src.web.views_settings_garmin as _vsg

        client, tmp_path = garmin_settings_app
        called = {"count": 0}

        def _fake_trigger(uid, days):
            called["count"] += 1
            return _flask.redirect("/connect/garmin?msg=ok")

        monkeypatch.setattr(_vsg, "_trigger_sync_and_redirect", _fake_trigger)

        r = client.post(
            "/connect/garmin/paste-token",
            data={"oauth2_json": json.dumps(VALID_TOKEN)},
        )
        assert r.status_code == 302
        assert called["count"] == 0

    def test_paste_with_trigger_sync_calls_redirect(self, garmin_settings_app, monkeypatch):
        """paste-token + trigger_sync=1 → _trigger_sync_and_redirect 호출."""
        import flask as _flask
        import src.web.views_settings_garmin as _vsg

        client, tmp_path = garmin_settings_app
        called = {"count": 0}

        def _fake_trigger(uid, days):
            called["count"] += 1
            return _flask.redirect("/connect/garmin?msg=ok")

        monkeypatch.setattr(_vsg, "_trigger_sync_and_redirect", _fake_trigger)

        r = client.post(
            "/connect/garmin/paste-token",
            data={"oauth2_json": json.dumps(VALID_TOKEN), "trigger_sync": "1", "days": "7"},
        )
        assert r.status_code == 302
        assert called["count"] == 1


# ── CF 설정 저장 + 다운로드 엔드포인트 ───────────────────────────────────────────

class TestCfSettingsAndDownload:
    """POST /cf-settings, GET /download-script, GET /download-env 검증."""

    @pytest.fixture()
    def garmin_app(self, tmp_path, monkeypatch):
        saved_cf = {}

        def _fake_update(section, data, **kwargs):
            saved_cf.update(data)

        monkeypatch.setattr("src.web.views_settings_garmin.load_config", lambda **k: {
            "garmin": {"email": "u@t.com"},
            "cf": {"service_client_id": "id.access", "service_client_secret": "sec"},
        })
        monkeypatch.setattr("src.web.views_settings_garmin.update_service_config", _fake_update)
        monkeypatch.setattr("src.web.views_settings_garmin._auto_user_id", lambda _: "u_at_t.com")
        monkeypatch.setattr(
            "src.web.views_settings_garmin.render_template",
            lambda *a, **kw: kw.get("body", ""),
        )

        app = Flask(__name__)
        app.secret_key = "test-secret"
        app.config["TESTING"] = True

        from src.web.views_settings_garmin import settings_garmin_bp
        app.register_blueprint(settings_garmin_bp)

        with app.test_client() as client:
            yield client, saved_cf

    def test_cf_settings_saves_and_redirects(self, garmin_app):
        """POST /connect/garmin/cf-settings → update_service_config 호출 후 302."""
        client, saved_cf = garmin_app
        r = client.post(
            "/connect/garmin/cf-settings",
            data={"cf_client_id": "new-id.access", "cf_client_secret": "new-secret"},
        )
        assert r.status_code == 302
        assert saved_cf.get("service_client_id") == "new-id.access"
        assert saved_cf.get("service_client_secret") == "new-secret"

    def test_cf_settings_strips_header_prefix(self, garmin_app):
        """'CF-Access-Client-Id: xxx' 형식 붙여넣기 → prefix 제거 후 저장."""
        client, saved_cf = garmin_app
        r = client.post(
            "/connect/garmin/cf-settings",
            data={
                "cf_client_id": "CF-Access-Client-Id: my-id.access",
                "cf_client_secret": "CF-Access-Client-Secret: my-secret",
            },
        )
        assert r.status_code == 302
        assert saved_cf.get("service_client_id") == "my-id.access"
        assert saved_cf.get("service_client_secret") == "my-secret"

    def test_cf_settings_missing_fields_returns_error_redirect(self, garmin_app):
        """cf_client_id 누락 → error 파라미터 포함 302."""
        client, _ = garmin_app
        r = client.post(
            "/connect/garmin/cf-settings",
            data={"cf_client_id": "", "cf_client_secret": "sec"},
        )
        assert r.status_code == 302
        assert "error" in r.headers["Location"]

    def test_download_script_returns_python_file(self, garmin_app):
        """GET /download-script → garmin_local_sync.py 첨부 파일 응답."""
        client, _ = garmin_app
        r = client.get("/connect/garmin/download-script")
        assert r.status_code == 200
        assert b"garmin_local_sync" in r.data or b"def main" in r.data
        assert "attachment" in r.headers.get("Content-Disposition", "")

    def test_download_env_contains_cf_values(self, garmin_app):
        """GET /download-env → CF 토큰 + email이 포함된 .env 텍스트 반환."""
        client, _ = garmin_app
        r = client.get("/connect/garmin/download-env")
        assert r.status_code == 200
        text = r.data.decode()
        assert "CF_SERVICE_CLIENT_ID=id.access" in text
        assert "CF_SERVICE_CLIENT_SECRET=sec" in text
        assert "GARMIN_EMAIL=u@t.com" in text
        assert "GARMIN_VPS_URL" not in text or text.startswith("#")  # VPS URL은 주석으로만
        assert "attachment" in r.headers.get("Content-Disposition", "")
        assert ".env" in r.headers.get("Content-Disposition", "")


# ── sync_key 검증 ────────────────────────────────────────────────────────────

_SECRET = "test-cf-service-secret-64chars-0000000000000000000000000000000"


def _make_app_with_sync_key(tmp_path, app_env="development", cf_secret=_SECRET):
    """sync_key 인증 로직 포함한 최소 Flask 앱."""
    app = Flask(__name__)
    app.secret_key = "test-secret"
    app.config["TESTING"] = True

    @app.post("/api/garmin/local-sync")
    def garmin_local_sync():
        data = request.get_json(silent=True) or {}

        # app.py와 동일한 sync_key 검증 로직
        sync_key = data.get("sync_key", "")
        is_prod = app_env == "production"
        expected_key = cf_secret
        if expected_key:
            if not sync_key or not hmac.compare_digest(sync_key, expected_key):
                return jsonify({"error": "sync_key 인증 실패"}), 401
        elif is_prod:
            return jsonify({"error": "서버 CF 설정 없음"}), 500

        token = data.get("token")
        if not token or not isinstance(token, dict) or not token.get("access_token"):
            return jsonify({"error": "token 필드가 없습니다."}), 400

        return jsonify({"status": "sync_started", "job_id": "j-001"}), 202

    return app


class TestSyncKeyValidation:
    def test_valid_sync_key_returns_202(self, tmp_path):
        """올바른 sync_key → 202."""
        app = _make_app_with_sync_key(tmp_path)
        with app.test_client() as c:
            r = c.post(
                "/api/garmin/local-sync",
                data=json.dumps({"token": VALID_TOKEN, "sync_key": _SECRET}),
                content_type="application/json",
            )
        assert r.status_code == 202

    def test_missing_sync_key_returns_401(self, tmp_path):
        """sync_key 없음 → 401."""
        app = _make_app_with_sync_key(tmp_path)
        with app.test_client() as c:
            r = c.post(
                "/api/garmin/local-sync",
                data=json.dumps({"token": VALID_TOKEN}),
                content_type="application/json",
            )
        assert r.status_code == 401

    def test_wrong_sync_key_returns_401(self, tmp_path):
        """잘못된 sync_key → 401."""
        app = _make_app_with_sync_key(tmp_path)
        with app.test_client() as c:
            r = c.post(
                "/api/garmin/local-sync",
                data=json.dumps({"token": VALID_TOKEN, "sync_key": "wrong-secret"}),
                content_type="application/json",
            )
        assert r.status_code == 401

    def test_no_cf_config_dev_allows_any_key(self, tmp_path):
        """cf_secret 없는 개발환경 → sync_key 검증 생략 → 202."""
        app = _make_app_with_sync_key(tmp_path, app_env="development", cf_secret="")
        with app.test_client() as c:
            r = c.post(
                "/api/garmin/local-sync",
                data=json.dumps({"token": VALID_TOKEN}),
                content_type="application/json",
            )
        assert r.status_code == 202

    def test_no_cf_config_production_returns_500(self, tmp_path):
        """cf_secret 없는 production → 500."""
        app = _make_app_with_sync_key(tmp_path, app_env="production", cf_secret="")
        with app.test_client() as c:
            r = c.post(
                "/api/garmin/local-sync",
                data=json.dumps({"token": VALID_TOKEN}),
                content_type="application/json",
            )
        assert r.status_code == 500


# ── auth_cf.py: /api/garmin/local-sync 경로 우회 ─────────────────────────────

class TestAuthCfBypass:
    def _make_cf_app(self, monkeypatch, app_env="production"):
        monkeypatch.setenv("APP_ENV", app_env)
        # auth_cf 모듈 재로드 없이 _IS_PRODUCTION 패치
        import src.web.auth_cf as _acf
        monkeypatch.setattr(_acf, "_IS_PRODUCTION", app_env == "production")

        app = Flask(__name__)
        app.secret_key = "test-secret"
        app.config["TESTING"] = True

        from src.web.auth_cf import init_cf_auth
        init_cf_auth(app)

        @app.post("/api/garmin/local-sync")
        def garmin_local_sync():
            return jsonify({"ok": True}), 200

        @app.get("/other")
        def other():
            return jsonify({"ok": True}), 200

        return app

    def test_local_sync_path_bypasses_auth(self, monkeypatch):
        """production에서 /api/garmin/local-sync → auth 우회 → 200."""
        app = self._make_cf_app(monkeypatch, app_env="production")
        with app.test_client() as c:
            r = c.post("/api/garmin/local-sync", data=json.dumps({}), content_type="application/json")
        assert r.status_code == 200

    def test_other_path_blocked_in_production(self, monkeypatch):
        """production에서 다른 경로 + CF 헤더 없음 → 401."""
        app = self._make_cf_app(monkeypatch, app_env="production")
        with app.test_client() as c:
            r = c.get("/other")
        assert r.status_code == 401
