"""`POST /api/v1/csp-report` — 브라우저 CSP 위반 보고 수신(로그 전용, DB 저장 없음, D6).

설계: security-headers.md §2.2 (S3 8단계, SRV-12·SEC-12).
- 항상 `204`. 수용 형식(`application/csp-report`, `application/reports+json`) 밖·파싱 불가·크기 초과 본문도
  204 + 로그만 남긴다 — 브라우저 보고 경로라 4xx 를 줘도 읽는 쪽이 없다. 415 검사(`parse_body`)는 쓰지 않는다.
- 본문은 `MAX_BYTES` 까지만 읽는다(Content-Length 를 믿지 않음). 한 요청의 보고는 `MAX_REPORTS` 개까지만 기록한다.
- 확장 프로그램 잡음: `blocked-uri`/`source-file` 이 확장 프로그램 스킴이면 `ext=1` 로 표시해 '위반 0건' 집계에서 제외한다.
- Origin 관문 면제(`request_guard.EXEMPT_PATHS`). 인증(`auth_cf`)은 면제가 아니다 — 실환경 도달 여부는 '미확인'(§2.2).

로그 줄 형식(logger `runpulse.csp`, 의도적 위반 확인 절차 §4-4 의 grep 대상):
    [csp-report] ext=0 directive='script-src-elem' blocked='inline' source='...' doc='...' line=3 disp='report'
집계는 `ext=0` 줄만 센다. 형식 밖 본문: `[csp-report] unaccepted reason=<...> ct='...' bytes=<n>`.
"""
from __future__ import annotations

import json
import logging

from flask import Response, request

from src.web.request_guard import _loggable

from . import api_bp

log = logging.getLogger("runpulse.csp")

MAX_BYTES = 16 * 1024
MAX_REPORTS = 10
ACCEPTED_TYPES = ("application/csp-report", "application/reports+json")
EXTENSION_SCHEMES = (
    "chrome-extension:", "moz-extension:", "safari-web-extension:", "safari-extension:",
    "ms-browser-extension:", "edge-extension:",
)


def _s(value, *, uri: bool = False) -> str:
    """보고 필드 → 로그용 문자열(쿼리·프래그먼트 제거 + 200자 절삭)."""
    if value is None:
        return ""
    return _loggable(str(value), strip_query=uri) or ""


def is_extension(blocked: str, source: str) -> bool:
    """blocked-uri 또는 source-file 이 확장 프로그램 스킴. `inline`·`eval` 은 스킴이 없어 source-file 로만 판정된다."""
    return any(v.lower().startswith(EXTENSION_SCHEMES) for v in (blocked, source) if v)


def _from_legacy(body) -> list[dict]:
    """`application/csp-report`: `{"csp-report": {...}}` (kebab-case)."""
    rep = body.get("csp-report") if isinstance(body, dict) else None
    if not isinstance(rep, dict):
        return []
    return [{
        "directive": rep.get("effective-directive") or rep.get("violated-directive"),
        "blocked": rep.get("blocked-uri"), "source": rep.get("source-file"),
        "doc": rep.get("document-uri"), "line": rep.get("line-number"),
        "disp": rep.get("disposition"),
    }]


def _from_reporting_api(body) -> list[dict]:
    """`application/reports+json`: `[{"type":"csp-violation","body":{...}}]` (camelCase)."""
    items = body if isinstance(body, list) else []
    out = []
    for it in items:
        if not isinstance(it, dict) or it.get("type") != "csp-violation" or not isinstance(it.get("body"), dict):
            continue
        b = it["body"]
        out.append({
            "directive": b.get("effectiveDirective") or b.get("violatedDirective"),
            "blocked": b.get("blockedURL"), "source": b.get("sourceFile"),
            "doc": b.get("documentURL") or it.get("url"), "line": b.get("lineNumber"),
            "disp": b.get("disposition"),
        })
    return out


def parse_reports(content_type: str, raw: bytes) -> list[dict]:
    """본문 → 정규화된 보고 목록. 파싱 불가·형식 밖이면 빈 목록."""
    try:
        body = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        return []
    return _from_legacy(body) if content_type == "application/csp-report" else _from_reporting_api(body)


def _no_content() -> Response:
    return Response(status=204)


@api_bp.post("/csp-report")
def csp_report():
    ctype = (request.mimetype or "").lower()
    raw = request.stream.read(MAX_BYTES + 1)
    if ctype not in ACCEPTED_TYPES:
        log.info("[csp-report] unaccepted reason=content-type ct=%r bytes=%d", _s(request.content_type)[:60], len(raw))
        return _no_content()
    if len(raw) > MAX_BYTES:
        log.info("[csp-report] unaccepted reason=too-large ct=%r bytes>%d", ctype, MAX_BYTES)
        return _no_content()
    reports = parse_reports(ctype, raw)
    if not reports:
        log.info("[csp-report] unaccepted reason=unparsable ct=%r bytes=%d", ctype, len(raw))
        return _no_content()
    for rep in reports[:MAX_REPORTS]:
        blocked, source = _s(rep["blocked"], uri=True), _s(rep["source"], uri=True)
        ext = is_extension(blocked, source)
        line = rep["line"] if isinstance(rep["line"], int) and not isinstance(rep["line"], bool) else 0
        log.log(
            logging.INFO if ext else logging.WARNING,
            "[csp-report] ext=%d directive=%r blocked=%r source=%r doc=%r line=%d disp=%r",
            1 if ext else 0, _s(rep["directive"]), blocked, source, _s(rep["doc"], uri=True), line, _s(rep["disp"]),
        )
    if len(reports) > MAX_REPORTS:
        log.info("[csp-report] truncated extra=%d", len(reports) - MAX_REPORTS)
    return _no_content()
