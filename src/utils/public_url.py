"""외부에 노출되는 앱 기준 URL — PUBLIC_BASE_URL 환경변수 우선, 없으면 요청 url_root."""
from __future__ import annotations

import os


def public_base_url(fallback: str | None = None) -> str:
    env = os.environ.get("PUBLIC_BASE_URL", "").strip().rstrip("/")
    if env:
        return env
    if fallback is not None:
        return fallback.rstrip("/")
    from flask import request
    return request.url_root.rstrip("/")
