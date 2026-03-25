"""Strava 인증 및 엔드포인트 테스트."""
import time
import pytest

from src.sync.strava import check_strava_connection, _BASE_URL


# ── 엔드포인트 URL 검증 ─────────────────────────────────────────────
def test_activity_list_endpoint():
    """활동 목록 엔드포인트가 /athlete/activities 이다."""
    import inspect, src.sync.strava as m
    src_text = inspect.getsource(m)
    assert "/athlete/activities" in src_text
    # 잘못된 이전 엔드포인트가 없어야 함
    assert "/athlete/activity_summaries" not in src_text


def test_activity_detail_endpoint():
    """활동 상세 엔드포인트가 /activities/{id} 이다."""
    import inspect, src.sync.strava as m
    src_text = inspect.getsource(m)
    assert "/activities/{source_id}" in src_text or "activities/" in src_text
    assert "/activity_summaries/" not in src_text


def test_stream_endpoint():
    """스트림 엔드포인트가 /activities/{id}/streams 이다."""
    import inspect, src.sync.strava as m
    src_text = inspect.getsource(m)
    assert "activities/{source_id}/streams" in src_text
    assert "activity_summaries/{source_id}/streams" not in src_text


# ── check_strava_connection ─────────────────────────────────────────
def test_strava_no_config():
    """client_id/secret 없으면 설정 누락."""
    result = check_strava_connection({"strava": {}})
    assert result["ok"] is False
    assert "누락" in result["status"]


def test_strava_no_refresh_token():
    """client_id/secret 있어도 refresh_token 없으면 재연동 필요."""
    cfg = {"strava": {"client_id": "123", "client_secret": "sec"}}
    result = check_strava_connection(cfg)
    assert result["ok"] is False
    assert "재연동" in result["status"]


def test_strava_expired_token():
    """만료된 access_token은 '토큰 만료' 상태."""
    cfg = {
        "strava": {
            "client_id": "123",
            "client_secret": "sec",
            "refresh_token": "rt",
            "access_token": "at",
            "expires_at": int(time.time()) - 1000,  # 과거
        }
    }
    result = check_strava_connection(cfg)
    assert result["ok"] is True  # 갱신 가능이므로 ok=True
    assert "만료" in result["status"]


def test_strava_connected():
    """유효한 토큰은 '연결됨' 상태."""
    cfg = {
        "strava": {
            "client_id": "123",
            "client_secret": "sec",
            "refresh_token": "rt",
            "access_token": "at",
            "expires_at": int(time.time()) + 3600,  # 미래
        }
    }
    result = check_strava_connection(cfg)
    assert result["ok"] is True
    assert "연결됨" in result["status"]


def test_strava_no_access_token_but_has_refresh():
    """refresh_token만 있으면 갱신 필요 상태 (ok=True)."""
    cfg = {
        "strava": {
            "client_id": "123",
            "client_secret": "sec",
            "refresh_token": "rt",
        }
    }
    result = check_strava_connection(cfg)
    assert result["ok"] is True


# ── _refresh_token이 update_service_config를 사용하는지 확인 ─────────
def test_refresh_uses_shared_config_helper():
    """_refresh_token이 ad hoc 파일 직접 쓰기 대신 update_service_config를 사용한다."""
    import inspect, src.sync.strava as m
    src_text = inspect.getsource(m._refresh_token)
    # 직접 파일 오픈 방식이 제거되었어야 함
    assert "open(config_path" not in src_text
    assert "update_service_config" in src_text
