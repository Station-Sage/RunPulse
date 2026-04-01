"""credential_store.py 테스트 — Fernet 암호화/복호화 라운드트립."""

import os
import pytest

from cryptography.fernet import Fernet


# ── 픽스처 ─────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _reset_warned():
    """_KEY_WARNED 플래그를 테스트별로 초기화."""
    import src.utils.credential_store as cs
    cs._KEY_WARNED = False
    yield
    cs._KEY_WARNED = False


@pytest.fixture()
def fernet_key() -> str:
    return Fernet.generate_key().decode()


@pytest.fixture()
def with_key(fernet_key, monkeypatch):
    """CREDENTIAL_ENCRYPTION_KEY 환경변수를 세팅한 상태."""
    monkeypatch.setenv("CREDENTIAL_ENCRYPTION_KEY", fernet_key)
    monkeypatch.setenv("APP_ENV", "development")
    # _get_fernet 캐시 우회를 위해 모듈 재임포트가 아닌 env 변경으로 처리
    yield fernet_key


@pytest.fixture()
def without_key(monkeypatch):
    """CREDENTIAL_ENCRYPTION_KEY 없는 개발 환경."""
    monkeypatch.delenv("CREDENTIAL_ENCRYPTION_KEY", raising=False)
    monkeypatch.setenv("APP_ENV", "development")
    yield


@pytest.fixture()
def production_without_key(monkeypatch):
    """CREDENTIAL_ENCRYPTION_KEY 없는 production 환경."""
    monkeypatch.delenv("CREDENTIAL_ENCRYPTION_KEY", raising=False)
    monkeypatch.setenv("APP_ENV", "production")
    yield


# ── 헬퍼 ───────────────────────────────────────────────────────────────────

def _sample_config() -> dict:
    return {
        "garmin": {"email": "user@example.com", "password": "secret123"},
        "strava": {
            "client_id": "12345",
            "client_secret": "strava_secret",
            "refresh_token": "refresh_abc",
            "access_token": "access_xyz",
        },
        "intervals": {"athlete_id": "i123", "api_key": "int_key"},
        "runalyze": {"token": "run_token"},
        "ai": {"api_key": "ai_key"},
        "mapbox": {"token": "map_token"},
        "user": {"max_hr": 190, "threshold_pace": 300},
    }


# ── 암호화/복호화 라운드트립 ──────────────────────────────────────────────

def test_roundtrip(with_key):
    """암호화 후 복호화하면 원본 값이 복원된다."""
    from src.utils.credential_store import (
        encrypt_config_credentials,
        decrypt_config_credentials,
    )
    original = _sample_config()
    encrypted = encrypt_config_credentials(original)
    decrypted = decrypt_config_credentials(encrypted)

    assert decrypted["garmin"]["password"] == "secret123"
    assert decrypted["strava"]["client_secret"] == "strava_secret"
    assert decrypted["strava"]["refresh_token"] == "refresh_abc"
    assert decrypted["strava"]["access_token"] == "access_xyz"
    assert decrypted["intervals"]["api_key"] == "int_key"
    assert decrypted["runalyze"]["token"] == "run_token"
    assert decrypted["ai"]["api_key"] == "ai_key"
    assert decrypted["mapbox"]["token"] == "map_token"


def test_non_sensitive_fields_unchanged(with_key):
    """민감하지 않은 필드는 암호화되지 않는다."""
    from src.utils.credential_store import encrypt_config_credentials
    original = _sample_config()
    encrypted = encrypt_config_credentials(original)

    assert encrypted["garmin"]["email"] == "user@example.com"
    assert encrypted["strava"]["client_id"] == "12345"
    assert encrypted["user"]["max_hr"] == 190
    assert encrypted["intervals"]["athlete_id"] == "i123"


def test_encrypted_values_have_prefix(with_key):
    """암호화된 값은 'enc:' prefix를 가진다."""
    from src.utils.credential_store import encrypt_config_credentials, _ENC_PREFIX
    encrypted = encrypt_config_credentials(_sample_config())

    # garmin.password는 더 이상 암호화 대상이 아님
    assert encrypted["strava"]["client_secret"].startswith(_ENC_PREFIX)
    assert encrypted["intervals"]["api_key"].startswith(_ENC_PREFIX)
    assert encrypted["runalyze"]["token"].startswith(_ENC_PREFIX)


def test_no_double_encryption(with_key):
    """이미 암호화된 값은 재암호화하지 않는다."""
    from src.utils.credential_store import encrypt_config_credentials, _ENC_PREFIX
    config = _sample_config()
    first = encrypt_config_credentials(config)
    second = encrypt_config_credentials(first)

    # 두 번 암호화해도 동일한 enc: 값 (prefix 중첩 없음)
    assert not second["garmin"]["password"].startswith(_ENC_PREFIX + _ENC_PREFIX)
    assert second["garmin"]["password"] == first["garmin"]["password"]


def test_empty_values_not_encrypted(with_key):
    """빈 문자열 자격증명은 암호화 대상에서 제외된다."""
    from src.utils.credential_store import encrypt_config_credentials, _ENC_PREFIX
    config = _sample_config()
    config["garmin"]["password"] = ""
    encrypted = encrypt_config_credentials(config)

    assert encrypted["garmin"]["password"] == ""
    assert not encrypted["garmin"]["password"].startswith(_ENC_PREFIX)


def test_plaintext_passthrough_on_decrypt(with_key):
    """enc: prefix 없는 평문 값은 복호화 시 그대로 통과한다 (마이그레이션 전 하위 호환)."""
    from src.utils.credential_store import decrypt_config_credentials
    config = _sample_config()  # 평문 상태
    result = decrypt_config_credentials(config)

    assert result["garmin"]["password"] == "secret123"


# ── KEY 없는 개발 환경 ────────────────────────────────────────────────────

def test_no_key_development_passthrough(without_key):
    """개발 환경에서 KEY 없으면 평문 그대로 반환 (경고만 출력)."""
    from src.utils.credential_store import encrypt_config_credentials
    config = _sample_config()
    result = encrypt_config_credentials(config)

    assert result["garmin"]["password"] == "secret123"
    assert result is config  # 동일 객체 반환


def test_no_key_production_raises(production_without_key):
    """production 환경에서 KEY 없으면 RuntimeError 발생."""
    import importlib
    import src.utils.credential_store as cs

    # _IS_PRODUCTION을 monkeypatch로 강제 설정
    original = cs._IS_PRODUCTION
    cs._IS_PRODUCTION = True
    try:
        with pytest.raises(RuntimeError, match="CREDENTIAL_ENCRYPTION_KEY"):
            cs._get_fernet()
    finally:
        cs._IS_PRODUCTION = original


# ── generate_key ─────────────────────────────────────────────────────────

def test_generate_key_is_valid_fernet_key():
    """generate_key()가 유효한 Fernet 키를 반환한다."""
    from src.utils.credential_store import generate_key
    key = generate_key()
    assert isinstance(key, str)
    assert len(key) == 44  # URL-safe base64, 32바이트 → 44자
    # 실제로 Fernet에 사용 가능한지 검증
    f = Fernet(key.encode())
    token = f.encrypt(b"test")
    assert f.decrypt(token) == b"test"


# ── 원본 불변성 ──────────────────────────────────────────────────────────

def test_original_config_not_mutated(with_key):
    """encrypt_config_credentials는 원본 dict를 수정하지 않는다."""
    from src.utils.credential_store import encrypt_config_credentials
    original = _sample_config()
    original_pw = original["garmin"]["password"]
    encrypt_config_credentials(original)
    assert original["garmin"]["password"] == original_pw
