"""자격증명 암호화/복호화 유틸리티 (Fernet AES-128-CBC + HMAC-SHA256).

config.json의 민감 필드를 투명하게 암호화/복호화한다.
암호화된 값은 "enc:" prefix로 식별하여 이중 암호화를 방지한다.

환경변수:
  CREDENTIAL_ENCRYPTION_KEY: Fernet.generate_key() 결과 (base64 URL-safe, 44자)
  APP_ENV: "production"이면 KEY 없을 때 RuntimeError 발생.
           "development"(기본값)이면 경고만 출력하고 평문 통과.

암호화 대상 필드 (service → key_name):
  garmin    : password
  strava    : client_secret, refresh_token, access_token
  intervals : api_key
  runalyze  : token
  ai        : api_key
  mapbox    : token
"""

from __future__ import annotations

import logging
import os
from typing import Any

log = logging.getLogger(__name__)

_ENC_PREFIX = "enc:"

# 암호화할 (서비스, 키) 쌍
_SENSITIVE_FIELDS: set[tuple[str, str]] = {
    # ("garmin", "password"),  ← 제거: 비밀번호 더 이상 저장 안 함
    ("strava", "client_secret"),
    ("strava", "refresh_token"),
    ("strava", "access_token"),
    ("intervals", "api_key"),
    ("runalyze", "token"),
    # AI provider별 키
    ("ai", "api_key"),
    ("ai", "gemini_api_key"),
    ("ai", "groq_api_key"),
    ("ai", "claude_api_key"),
    ("ai", "openai_api_key"),
    ("mapbox", "token"),
}

_IS_PRODUCTION = os.environ.get("APP_ENV", "development").lower() == "production"
_KEY_WARNED = False  # 경고 중복 출력 방지


def _get_fernet():
    """Fernet 인스턴스 반환. KEY 없으면 환경에 따라 None 또는 RuntimeError."""
    global _KEY_WARNED
    raw_key = os.environ.get("CREDENTIAL_ENCRYPTION_KEY", "").strip().encode()
    if raw_key:
        try:
            from cryptography.fernet import Fernet
            return Fernet(raw_key)
        except Exception as e:
            raise ValueError(
                f"CREDENTIAL_ENCRYPTION_KEY가 유효하지 않습니다: {e}\n"
                "python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\" "
                "로 새 키를 생성하세요."
            ) from e

    if _IS_PRODUCTION:
        raise RuntimeError(
            "[credential_store] CREDENTIAL_ENCRYPTION_KEY 환경변수가 설정되지 않았습니다. "
            "production 환경에서는 필수입니다. .env 파일을 확인하세요."
        )

    if not _KEY_WARNED:
        log.warning(
            "[credential_store] CREDENTIAL_ENCRYPTION_KEY 미설정 — "
            "평문 저장 허용 (로컬 개발 전용, production 금지)"
        )
        _KEY_WARNED = True
    return None


def encrypt_config_credentials(config: dict[str, Any]) -> dict[str, Any]:
    """config dict의 민감 필드를 암호화하여 반환.

    이미 암호화된 값("enc:" prefix)은 건너뜀.
    KEY 없는 개발 환경에서는 원본 반환.

    Args:
        config: 서비스별 설정 dict (load_config() 결과 형식).

    Returns:
        민감 필드가 암호화된 새 dict.
    """
    fernet = _get_fernet()
    if fernet is None:
        return config

    import copy
    result = copy.deepcopy(config)

    for service, key_name in _SENSITIVE_FIELDS:
        section = result.get(service)
        if not isinstance(section, dict):
            continue
        value = section.get(key_name)
        if not value or not isinstance(value, str):
            continue
        if value.startswith(_ENC_PREFIX):
            continue  # 이미 암호화됨
        encrypted = fernet.encrypt(value.encode()).decode()
        section[key_name] = f"{_ENC_PREFIX}{encrypted}"

    return result


def decrypt_config_credentials(config: dict[str, Any]) -> dict[str, Any]:
    """config dict의 암호화된 민감 필드를 복호화하여 반환.

    "enc:" prefix가 없는 값은 그대로 통과 (평문 하위 호환).
    복호화 실패 시 경고 로그 + 원본 값 유지.

    Args:
        config: 서비스별 설정 dict (JSON에서 읽은 직후 형식).

    Returns:
        민감 필드가 복호화된 새 dict.
    """
    fernet = _get_fernet()
    if fernet is None:
        return config

    import copy
    result = copy.deepcopy(config)

    for service, key_name in _SENSITIVE_FIELDS:
        section = result.get(service)
        if not isinstance(section, dict):
            continue
        value = section.get(key_name)
        if not value or not isinstance(value, str):
            continue
        if not value.startswith(_ENC_PREFIX):
            continue  # 평문 (마이그레이션 전 하위 호환)
        encrypted_part = value[len(_ENC_PREFIX):]
        try:
            decrypted = fernet.decrypt(encrypted_part.encode()).decode()
            section[key_name] = decrypted
        except Exception as e:
            log.error(
                "[credential_store] 복호화 실패 (service=%s, key=%s): %s — "
                "CREDENTIAL_ENCRYPTION_KEY가 변경되었을 수 있습니다.",
                service, key_name, e,
            )
            # 복호화 실패 시 enc: 값 유지 (빈 값으로 덮어쓰지 않음)

    return result


def generate_key() -> str:
    """새 Fernet 키 생성 후 문자열로 반환 (설정 초기화 시 사용).

    Returns:
        base64 URL-safe 인코딩된 44자 키 문자열.
    """
    from cryptography.fernet import Fernet
    return Fernet.generate_key().decode()
