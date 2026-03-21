"""Runalyze 인증 및 엔드포인트 테스트."""
import pytest
from unittest.mock import patch

from src.sync.runalyze import check_runalyze_connection, _BASE_URL


# ── 엔드포인트 URL 검증 ─────────────────────────────────────────────
def test_activities_endpoint_correct():
    """활동 목록 엔드포인트가 /activities 이다 (activity_summaries 아님)."""
    import inspect, src.sync.runalyze as m
    src_text = inspect.getsource(m.sync_activities)
    # f-string 형태: f"{_BASE_URL}/activities"
    assert "/activities" in src_text
    # 엔드포인트 경로 문자열에 activity_summaries 없어야 함
    assert "activity_summaries\"" not in src_text  # 경로 문자열로 사용 금지


def test_activity_detail_endpoint_correct():
    """활동 상세 엔드포인트가 /activity/{id} 이다 (activity_summaries/{id} 아님)."""
    import inspect, src.sync.runalyze as m
    src_text = inspect.getsource(m.sync_activities)
    assert "/activity/{source_id}" in src_text or "activity/{source_id}" in src_text
    assert "activity_summaries/{source_id}" not in src_text


def test_base_url():
    """_BASE_URL이 올바른 Runalyze API URL이다."""
    assert _BASE_URL == "https://runalyze.com/api/v1"


def test_token_header():
    """인증 헤더가 token 키를 사용한다."""
    import inspect, src.sync.runalyze as m
    src_text = inspect.getsource(m._headers)
    assert '"token"' in src_text


# ── check_runalyze_connection ───────────────────────────────────────
def test_runalyze_no_token():
    """토큰 없으면 토큰 없음 상태."""
    result = check_runalyze_connection({"runalyze": {}})
    assert result["ok"] is False
    assert "토큰 없음" in result["status"]


def test_runalyze_empty_token():
    """빈 토큰도 토큰 없음 상태."""
    result = check_runalyze_connection({"runalyze": {"token": ""}})
    assert result["ok"] is False
    assert "토큰 없음" in result["status"]


def test_runalyze_connection_ok():
    """API 호출 성공 시 ok=True."""
    config = {"runalyze": {"token": "valid_token"}}
    with patch("src.sync.runalyze.api.get", return_value=[]):
        result = check_runalyze_connection(config)
    assert result["ok"] is True
    assert "연결됨" in result["status"]


def test_runalyze_connection_401():
    """401/403 오류 시 토큰 오류 상태."""
    from src.utils.api import ApiError
    config = {"runalyze": {"token": "bad_token"}}
    with patch("src.sync.runalyze.api.get", side_effect=ApiError("401", status_code=401)):
        result = check_runalyze_connection(config)
    assert result["ok"] is False
    assert "토큰 오류" in result["status"]


def test_runalyze_connection_403():
    """403 오류도 토큰 오류 상태."""
    from src.utils.api import ApiError
    config = {"runalyze": {"token": "bad_token"}}
    with patch("src.sync.runalyze.api.get", side_effect=ApiError("403", status_code=403)):
        result = check_runalyze_connection(config)
    assert result["ok"] is False
    assert "토큰 오류" in result["status"]


def test_runalyze_connection_404():
    """404 오류 시 엔드포인트 불일치 상태."""
    from src.utils.api import ApiError
    config = {"runalyze": {"token": "tok"}}
    with patch("src.sync.runalyze.api.get", side_effect=ApiError("404", status_code=404)):
        result = check_runalyze_connection(config)
    assert result["ok"] is False
    assert "엔드포인트" in result["status"]


def test_runalyze_connection_error():
    """네트워크 오류 시 연결 오류 상태."""
    config = {"runalyze": {"token": "tok"}}
    with patch("src.sync.runalyze.api.get", side_effect=Exception("연결 거부")):
        result = check_runalyze_connection(config)
    assert result["ok"] is False
    assert "오류" in result["status"]
