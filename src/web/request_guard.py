"""요청 경계 보호 — 봉투 경로 규칙·403 응답 (SRV 2.1, ADR-048). 앱 셸(`src/web/`) 전용.

S3 3단계: 봉투 경로 상수와 403 응답 헬퍼만 있다(uid 규칙 위반 403 이 먼저 필요).
S3 4단계에서 Origin 관문(`same_origin`·`init_request_guard`·observe/enforce)이 이 모듈에 추가된다.
"""
from __future__ import annotations

from flask import Response, jsonify, request

# `{error:{code,message}}` 봉투로 응답하는 경로(NEW-40). `/api/v1` 밖에 봉투 API 를 두면 여기에 추가한다.
ENVELOPE_PATH_PREFIXES = ("/api/v1/", "/api/context-episodes")


def is_envelope_path(path: str) -> bool:
    return path.startswith(ENVELOPE_PATH_PREFIXES)


def forbidden_response(code: str, message: str) -> Response:
    """403 — 봉투 경로는 `{error:{code,message}}` JSON, 그 외는 text/plain (S3-2)."""
    if is_envelope_path(request.path):
        resp = jsonify({"error": {"code": code, "message": message}})
        resp.status_code = 403
        return resp
    return Response(message, status=403, mimetype="text/plain")
