"""동기화 오류 분류 — 예외/결과를 error_code로 정규화하고 한국어 안내 문구를 제공한다."""
from __future__ import annotations

import json

ERROR_CODES = (
    "auth_expired", "subscription_required", "rate_limited",
    "upstream_5xx", "timeout", "network", "parse", "unknown",
)

# code -> (한국어 메시지, 사용자 조치: reconnect | disable | wait | retry)
MESSAGES_KO: dict[str, tuple[str, str]] = {
    "auth_expired": ("인증이 만료되었어요. 계정을 다시 연결해 주세요.", "reconnect"),
    "subscription_required": ("이 서비스의 접근 권한(구독/플랜)이 없어요. 연동을 끄거나 권한을 확인하세요.", "disable"),
    "rate_limited": ("요청 한도를 초과했어요. 잠시 후 자동으로 다시 시도해요.", "wait"),
    "upstream_5xx": ("외부 서비스 장애예요. 잠시 후 다시 시도해 주세요.", "retry"),
    "timeout": ("응답 시간이 초과되었어요. 다시 시도해 주세요.", "retry"),
    "network": ("네트워크 연결에 문제가 있어요. 다시 시도해 주세요.", "retry"),
    "parse": ("응답을 해석하지 못했어요. 다시 시도해 주세요.", "retry"),
    "unknown": ("알 수 없는 오류예요. 다시 시도해 주세요.", "retry"),
}


class SyncSourceError(Exception):
    """소스 전체 실패(0건 동기화 + 실패)를 나타낸다."""

    def __init__(self, code: str, message: str = "", http_status: int | None = None):
        super().__init__(message or code)
        self.code = code
        self.message = message
        self.http_status = http_status


def _status_to_code(status: int) -> str:
    if status == 401:
        return "auth_expired"
    if status == 403:
        return "subscription_required"
    if status == 429:
        return "rate_limited"
    if status >= 500:
        return "upstream_5xx"
    return "unknown"


def classify_exception(exc: BaseException) -> tuple[str, int | None]:
    """예외 → (error_code, http_status)."""
    status = getattr(exc, "status_code", None)
    if status is None:
        status = getattr(getattr(exc, "response", None), "status_code", None)
    if isinstance(status, int):
        return _status_to_code(status), status
    name = type(exc).__name__
    if "Timeout" in name:
        return "timeout", None
    if "ConnectionError" in name or isinstance(exc, (ConnectionError, OSError)):
        return "network", None
    if isinstance(exc, (ValueError, KeyError, json.JSONDecodeError)):
        return "parse", None
    return "unknown", None


def from_result(result) -> SyncSourceError | None:
    """SyncResult가 전체 실패(failed + 0건)면 SyncSourceError, 아니면 None."""
    if getattr(result, "status", None) != "failed" or getattr(result, "synced_count", 0) > 0:
        return None
    return SyncSourceError(
        getattr(result, "error_code", None) or "unknown",
        getattr(result, "last_error", None) or "",
        getattr(result, "http_status", None),
    )
