"""인증 없이 열린 경로 목록(공개 경로)과 `next` 리다이렉트 검증. 그 외 모든 경로는 active 세션이 필요하다."""
from __future__ import annotations

import re

# 접두 일치: v2 정적 셸·에셋(데이터 없음), 토큰 인증 캘린더 피드.
_PUBLIC_PREFIXES = ("/v2/", "/feeds/cal/")
# 정확 일치(메서드 무관): 세션 상태 조회(캐시 금지), 랜딩 리다이렉트, 원격 MCP(Bearer 토큰이 유일 신원).
_PUBLIC_EXACT = {"/", "/v2", "/mcp", "/mcp/", "/api/v1/auth/session"}
# 메서드까지 일치: 로그아웃(쿠키만 지움), Garmin 로컬 동기화(body 의 sync_key 로 2차 인증).
_PUBLIC_METHOD = {("POST", "/auth/logout"), ("POST", "/api/garmin/local-sync")}
# pending 계정도 허용(활성화 전 단계).
_PENDING_OK = {("GET", "/auth/start"), ("POST", "/auth/logout"), ("POST", "/api/v1/auth/invite")}
_NEXT_RE = re.compile(r"/v2/[A-Za-z0-9/_-]*")
DEFAULT_NEXT = "/v2/today"


def is_public(method: str, path: str) -> bool:
    return path.startswith(_PUBLIC_PREFIXES) or path in _PUBLIC_EXACT or (method, path) in _PUBLIC_METHOD


def pending_allowed(method: str, path: str) -> bool:
    return (method, path) in _PENDING_OK


def safe_next(value: str | None) -> str:
    """오픈 리다이렉트 방지 — `/v2/...` 안전 문자만 허용, 그 외(스킴·`//`·`\\`)는 기본값."""
    if value and _NEXT_RE.fullmatch(value) and "//" not in value:
        return value
    return DEFAULT_NEXT
