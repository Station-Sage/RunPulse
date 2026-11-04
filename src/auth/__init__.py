"""AUTH-2026-11 — 다중 IdP·신규 가입 신원 계층 (CF Access 를 IdP 브로커로 쓰고 앱이 JWT 를 검증).

- cf_jwt.py      : `Cf-Access-Jwt-Assertion` 서명·aud·iss·exp 검증(PyJWT, 팀 도메인 certs 캐시)
- registry.py    : 계정 레지스트리 DB(data/auth.db) — accounts·identities·invites·auth_events
- public_paths.py: 인증 없이 열린 경로 목록과 `next` 검증
- identify.py    : `AUTH_MODE=registry` 일 때의 before_request 신원 해석(anonymous|pending|active)
- routes.py      : `/auth/start`·`/auth/logout` 블루프린트
- `AUTH_MODE=legacy`(기본)면 이 패키지는 로드되지 않고 기존 `src/web/auth_cf.py` 동작 그대로다(롤백 경로).
설계: v0.3/data/phase-7-ui-renewal/design-2026-11-auth/README.md
"""
import os


def auth_mode() -> str:
    """`AUTH_MODE` — legacy(기본) | registry. 알 수 없는 값은 legacy 로 취급한다."""
    return "registry" if os.environ.get("AUTH_MODE", "legacy").strip().lower() == "registry" else "legacy"
