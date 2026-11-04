"""Cloudflare Access JWT 검증 — 서명(RS256)·aud·iss·exp. 헤더 이메일은 신뢰하지 않는다(F1).

환경변수: `CF_ACCESS_TEAM`(팀 이름, `<team>.cloudflareaccess.com`), `CF_ACCESS_AUD`(애플리케이션 AUD 태그).
PyJWT 는 registry 모드에서만 import 한다(legacy 운영은 PyJWT 없이도 동작).
"""
from __future__ import annotations

import os
from typing import Any

JWT_HEADER = "Cf-Access-Jwt-Assertion"
JWT_COOKIE = "CF_Authorization"
_clients: dict[str, Any] = {}


class CfJwtError(Exception):
    """검증 실패(서명·aud·iss·만료·설정 누락)."""


def team_domain() -> str:
    team = os.environ.get("CF_ACCESS_TEAM", "").strip()
    return f"{team}.cloudflareaccess.com" if team and "." not in team else team


def _signing_key(token: str, domain: str):
    import jwt

    client = _clients.get(domain)
    if client is None:
        client = _clients[domain] = jwt.PyJWKClient(f"https://{domain}/cdn-cgi/access/certs", cache_keys=True, lifespan=3600)
    return client.get_signing_key_from_jwt(token).key


def verify(token: str) -> dict:
    """서명·aud·iss·exp 를 검증하고 claims 를 돌려준다. 설정이 없으면 항상 실패(닫힌 방향)."""
    import jwt

    domain, aud = team_domain(), os.environ.get("CF_ACCESS_AUD", "").strip()
    if not domain or not aud:
        raise CfJwtError("CF_ACCESS_TEAM/CF_ACCESS_AUD 미설정")
    try:
        claims = jwt.decode(
            token, _signing_key(token, domain), algorithms=["RS256"], audience=aud,
            issuer=f"https://{domain}", options={"require": ["exp", "iss", "aud", "sub"]}, leeway=30,
        )
    except Exception as exc:  # PyJWTError·네트워크 오류 모두 거부
        raise CfJwtError(type(exc).__name__) from exc
    return claims
