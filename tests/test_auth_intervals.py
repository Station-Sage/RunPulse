"""Intervals.icu 인증 및 엔드포인트 테스트."""
import pytest
from unittest.mock import patch

from src.sync.intervals import check_intervals_connection, _base_url, _auth


# ── 엔드포인트 URL 검증 ─────────────────────────────────────────────
def test_activities_endpoint_correct():
    """활동 목록 엔드포인트가 /activities 이다 (activity_summaries 아님)."""
    import inspect, src.sync.intervals as m
    src_text = inspect.getsource(m.sync_activities)
    # f-string 형태로 사용: f"{base}/activities"
    assert "/activities" in src_text
    # 엔드포인트 경로에 activity_summaries가 없어야 함 (변수명은 허용)
    # api.get 호출 부분에서 activity_summaries 경로가 없는지 확인
    assert "activity_summaries\"" not in src_text  # 경로 문자열로 사용 금지


def test_base_url_format():
    """_base_url이 올바른 형식을 반환한다."""
    config = {"intervals": {"athlete_id": "i12345", "api_key": "key"}}
    url = _base_url(config)
    assert url == "https://intervals.icu/api/v1/athlete/i12345"


def test_auth_format():
    """_auth가 ('API_KEY', api_key) 튜플을 반환한다."""
    config = {"intervals": {"athlete_id": "i12345", "api_key": "mykey"}}
    auth = _auth(config)
    assert auth == ("API_KEY", "mykey")


# ── check_intervals_connection ──────────────────────────────────────
def test_intervals_no_config():
    """athlete_id, api_key 모두 없으면 설정 누락."""
    result = check_intervals_connection({"intervals": {}})
    assert result["ok"] is False
    assert "누락" in result["status"]
    assert "athlete_id" in result["detail"]
    assert "api_key" in result["detail"]


def test_intervals_missing_athlete_id():
    """athlete_id만 없을 때 메시지에 포함."""
    result = check_intervals_connection({"intervals": {"api_key": "key"}})
    assert result["ok"] is False
    assert "athlete_id" in result["detail"]


def test_intervals_missing_api_key():
    """api_key만 없을 때 메시지에 포함."""
    result = check_intervals_connection({"intervals": {"athlete_id": "i123"}})
    assert result["ok"] is False
    assert "api_key" in result["detail"]


def test_intervals_connection_ok():
    """API 호출 성공 시 ok=True."""
    config = {"intervals": {"athlete_id": "i123", "api_key": "key"}}
    with patch("src.sync.intervals.api.get", return_value={"name": "Test Athlete"}):
        result = check_intervals_connection(config)
    assert result["ok"] is True
    assert "연결됨" in result["status"]


def test_intervals_connection_401():
    """401 오류 시 잘못된 API 키 상태."""
    from src.utils.api import ApiError
    config = {"intervals": {"athlete_id": "i123", "api_key": "wrongkey"}}
    with patch("src.sync.intervals.api.get", side_effect=ApiError("401", status_code=401)):
        result = check_intervals_connection(config)
    assert result["ok"] is False
    assert "API 키" in result["status"]


def test_intervals_connection_404():
    """404 오류 시 잘못된 athlete_id 상태."""
    from src.utils.api import ApiError
    config = {"intervals": {"athlete_id": "bad_id", "api_key": "key"}}
    with patch("src.sync.intervals.api.get", side_effect=ApiError("404", status_code=404)):
        result = check_intervals_connection(config)
    assert result["ok"] is False
    assert "athlete_id" in result["status"]
