"""gunicorn 로거 — 캘린더 구독 토큰(/feeds/cal/<token>.ics)을 접근 로그에서 마스킹."""
from __future__ import annotations

import re

from gunicorn.glogging import Logger

_TOKEN_RE = re.compile(r"(/feeds/cal/)[^/\s?\"]+")


def redact(text: str) -> str:
    return _TOKEN_RE.sub(r"\1[redacted]", text)


class RedactingLogger(Logger):
    def access(self, resp, req, environ, request_time):
        for k in ("RAW_URI", "PATH_INFO", "REQUEST_URI"):
            if isinstance(environ.get(k), str):
                environ[k] = redact(environ[k])
        if getattr(req, "uri", None):
            req.uri = redact(req.uri)
        if getattr(req, "path", None):
            req.path = redact(req.path)
        super().access(resp, req, environ, request_time)
