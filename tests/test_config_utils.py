"""config.py 헬퍼 함수 테스트 — save_config, update_service_config, redact."""
import json
import pytest
from pathlib import Path

from src.utils.config import (
    load_config,
    save_config,
    update_service_config,
    redact_config_for_display,
)


@pytest.fixture
def tmp_config(tmp_path):
    """임시 config.json 경로."""
    return tmp_path / "config.json"


# ── save_config ─────────────────────────────────────────────────────
def test_save_config_creates_file(tmp_config):
    """save_config가 파일을 새로 생성한다."""
    cfg = {"garmin": {"email": "test@test.com"}}
    save_config(cfg, path=tmp_config)
    assert tmp_config.exists()


def test_save_config_roundtrip(tmp_config):
    """저장 후 로드하면 동일한 값이 반환된다."""
    cfg = {"strava": {"client_id": "abc", "expires_at": 9999}}
    save_config(cfg, path=tmp_config)
    loaded = json.loads(tmp_config.read_text(encoding="utf-8"))
    assert loaded["strava"]["client_id"] == "abc"
    assert loaded["strava"]["expires_at"] == 9999


def test_save_config_overwrites(tmp_config):
    """기존 파일이 있으면 덮어쓴다."""
    save_config({"garmin": {"email": "old@test.com"}}, path=tmp_config)
    save_config({"garmin": {"email": "new@test.com"}}, path=tmp_config)
    loaded = json.loads(tmp_config.read_text(encoding="utf-8"))
    assert loaded["garmin"]["email"] == "new@test.com"


# ── update_service_config ───────────────────────────────────────────
def test_update_service_config_creates_file(tmp_config):
    """파일이 없어도 update_service_config가 생성한다."""
    result = update_service_config("intervals", {"athlete_id": "i123", "api_key": "key"}, path=tmp_config)
    assert tmp_config.exists()
    assert result["intervals"]["athlete_id"] == "i123"


def test_update_service_config_partial_update(tmp_config):
    """기존 필드를 유지하면서 지정 필드만 업데이트한다."""
    save_config({"strava": {"client_id": "cid", "client_secret": "secret"}}, path=tmp_config)
    update_service_config("strava", {"access_token": "tok", "expires_at": 1234}, path=tmp_config)
    loaded = json.loads(tmp_config.read_text(encoding="utf-8"))
    assert loaded["strava"]["client_id"] == "cid"      # 기존 유지
    assert loaded["strava"]["access_token"] == "tok"  # 새로 추가


def test_update_service_config_new_service(tmp_config):
    """존재하지 않던 서비스 섹션을 새로 만든다."""
    update_service_config("runalyze", {"token": "tok123"}, path=tmp_config)
    loaded = json.loads(tmp_config.read_text(encoding="utf-8"))
    assert loaded["runalyze"]["token"] == "tok123"


# ── redact_config_for_display ───────────────────────────────────────
def test_redact_masks_password():
    """password 필드를 마스킹한다."""
    cfg = {"garmin": {"email": "test@test.com", "password": "supersecret"}}
    redacted = redact_config_for_display(cfg)
    assert redacted["garmin"]["password"] != "supersecret"
    assert "***" in redacted["garmin"]["password"]
    assert redacted["garmin"]["email"] == "test@test.com"  # 비민감 필드는 유지


def test_redact_masks_token():
    """token 필드를 전체 마스킹한다 (****로 완전 숨김)."""
    cfg = {"runalyze": {"token": "abcdef1234567890"}}
    redacted = redact_config_for_display(cfg)
    assert redacted["runalyze"]["token"] == "****"
    # 원본 값이 노출되지 않아야 함
    assert "abcd" not in redacted["runalyze"]["token"]


def test_redact_does_not_mutate_original():
    """원본 config를 변경하지 않는다."""
    cfg = {"strava": {"access_token": "original_token"}}
    redact_config_for_display(cfg)
    assert cfg["strava"]["access_token"] == "original_token"


def test_redact_empty_value_unchanged():
    """값이 비어있으면 마스킹하지 않는다."""
    cfg = {"garmin": {"password": ""}}
    redacted = redact_config_for_display(cfg)
    assert redacted["garmin"]["password"] == ""
