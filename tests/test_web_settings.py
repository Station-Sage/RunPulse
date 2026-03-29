"""views_settings.py 라우트 통합 테스트."""
import json
import pytest
from unittest.mock import patch

from src.web.app import create_app


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


# ── /settings ───────────────────────────────────────────────────────
def test_settings_page_loads(client):
    """/settings 페이지가 200을 반환한다."""
    resp = client.get("/settings")
    assert resp.status_code == 200
    assert "서비스 연동 설정" in resp.data.decode("utf-8")


def test_settings_shows_all_services(client):
    """/settings에 4개 서비스가 모두 표시된다."""
    body = client.get("/settings").data.decode("utf-8")
    assert "Garmin" in body
    assert "Strava" in body
    assert "Intervals" in body
    assert "Runalyze" in body


# ── /connect/garmin ─────────────────────────────────────────────────
def test_garmin_connect_page_loads(client):
    """/connect/garmin GET 요청이 폼을 반환한다."""
    resp = client.get("/connect/garmin")
    assert resp.status_code == 200
    assert "Garmin" in resp.data.decode("utf-8")
    assert "이메일" in resp.data.decode("utf-8")


def test_garmin_connect_post_save(client, tmp_path):
    """POST /connect/garmin?action=save가 저장 후 리다이렉트한다."""
    config_file = tmp_path / "config.json"
    with patch("src.web.views_settings_garmin.update_service_config") as mock_update:
        resp = client.post("/connect/garmin", data={
            "email": "test@test.com",
            "password": "pw",
            "tokenstore": "~/.garth",
            "action": "save",
        })
    assert resp.status_code == 302
    mock_update.assert_called_once()
    call_args = mock_update.call_args
    assert call_args[0][0] == "garmin"
    assert call_args[0][1]["email"] == "test@test.com"


def test_garmin_connect_post_no_email(client):
    """이메일 없이 POST하면 오류 리다이렉트."""
    resp = client.post("/connect/garmin", data={"email": "", "action": "save"})
    assert resp.status_code == 302
    assert "error" in resp.headers["Location"]


def test_garmin_disconnect(client):
    """POST /connect/garmin/disconnect가 /settings로 리다이렉트한다."""
    with patch("src.web.views_settings_garmin.update_service_config"):
        resp = client.post("/connect/garmin/disconnect")
    assert resp.status_code == 302
    assert "/settings" in resp.headers["Location"]


# ── /connect/strava ─────────────────────────────────────────────────
def test_strava_connect_page_loads(client):
    """/connect/strava GET 요청이 200을 반환한다."""
    resp = client.get("/connect/strava")
    assert resp.status_code == 200
    assert "Strava" in resp.data.decode("utf-8")
    assert "Client ID" in resp.data.decode("utf-8")


def test_strava_save_app_missing_client_id(client):
    """client_id 없이 POST하면 오류 리다이렉트."""
    resp = client.post("/connect/strava/save-app", data={"client_id": ""})
    assert resp.status_code == 302
    assert "error" in resp.headers["Location"]


def test_strava_oauth_start_no_client_id(client):
    """client_id 없으면 OAuth 시작 시 오류 리다이렉트."""
    with patch("src.web.views_settings_integrations.load_config", return_value={"strava": {}}):
        resp = client.get("/connect/strava/oauth-start")
    assert resp.status_code == 302
    assert "error" in resp.headers["Location"]


def test_strava_oauth_start_redirects(client):
    """client_id 있으면 strava.com으로 리다이렉트."""
    with patch("src.web.views_settings_integrations.load_config", return_value={"strava": {"client_id": "123"}}):
        resp = client.get("/connect/strava/oauth-start")
    assert resp.status_code == 302
    assert "strava.com" in resp.headers["Location"]


def test_strava_disconnect(client):
    """POST /connect/strava/disconnect가 /settings로 리다이렉트."""
    with patch("src.web.views_settings_integrations.update_service_config"):
        resp = client.post("/connect/strava/disconnect")
    assert resp.status_code == 302


# ── /connect/intervals ───────────────────────────────────────────────
def test_intervals_connect_page_loads(client):
    """/connect/intervals GET 200 반환."""
    resp = client.get("/connect/intervals")
    assert resp.status_code == 200
    assert "Intervals" in resp.data.decode("utf-8")


def test_intervals_connect_missing_fields(client):
    """athlete_id 또는 api_key 없으면 오류 리다이렉트."""
    resp = client.post("/connect/intervals", data={"athlete_id": "", "api_key": ""})
    assert resp.status_code == 302
    assert "error" in resp.headers["Location"]


def test_intervals_connect_save(client):
    """올바른 입력으로 POST 시 저장 후 리다이렉트."""
    with patch("src.web.views_settings_integrations.update_service_config") as mock_upd:
        resp = client.post("/connect/intervals", data={
            "athlete_id": "i123",
            "api_key": "mykey",
            "action": "save",
        })
    assert resp.status_code == 302
    mock_upd.assert_called_once()


def test_intervals_connect_test_success(client):
    """연결 테스트 성공 시 msg 리다이렉트."""
    with patch("src.web.views_settings_integrations.update_service_config"):
        with patch("src.web.views_settings_integrations.check_intervals_connection",
                   return_value={"ok": True, "status": "연결됨", "detail": "athlete: X"}):
            resp = client.post("/connect/intervals", data={
                "athlete_id": "i123",
                "api_key": "key",
                "action": "save_and_test",
            })
    assert resp.status_code == 302
    assert "msg" in resp.headers["Location"]


def test_intervals_disconnect(client):
    """POST /connect/intervals/disconnect가 /settings로 리다이렉트."""
    with patch("src.web.views_settings_integrations.update_service_config"):
        resp = client.post("/connect/intervals/disconnect")
    assert resp.status_code == 302


# ── /connect/runalyze ────────────────────────────────────────────────
def test_runalyze_connect_page_loads(client):
    """/connect/runalyze GET 200 반환."""
    resp = client.get("/connect/runalyze")
    assert resp.status_code == 200
    assert "Runalyze" in resp.data.decode("utf-8")


def test_runalyze_connect_missing_token(client):
    """토큰 없으면 오류 리다이렉트."""
    resp = client.post("/connect/runalyze", data={"token": ""})
    assert resp.status_code == 302
    assert "error" in resp.headers["Location"]


def test_runalyze_connect_save(client):
    """올바른 토큰으로 POST 시 저장."""
    with patch("src.web.views_settings_integrations.update_service_config") as mock_upd:
        resp = client.post("/connect/runalyze", data={
            "token": "valid_token",
            "action": "save",
        })
    assert resp.status_code == 302
    mock_upd.assert_called_once()
    assert mock_upd.call_args[0][1]["token"] == "valid_token"


def test_runalyze_connect_test_failure(client):
    """연결 테스트 실패 시 error 리다이렉트."""
    with patch("src.web.views_settings_integrations.update_service_config"):
        with patch("src.web.views_settings_integrations.check_runalyze_connection",
                   return_value={"ok": False, "status": "토큰 오류", "detail": "401"}):
            resp = client.post("/connect/runalyze", data={
                "token": "bad_token",
                "action": "save_and_test",
            })
    assert resp.status_code == 302
    assert "error" in resp.headers["Location"]


def test_runalyze_disconnect(client):
    """POST /connect/runalyze/disconnect가 /settings로 리다이렉트."""
    with patch("src.web.views_settings.update_service_config"):
        resp = client.post("/connect/runalyze/disconnect")
    assert resp.status_code == 302
