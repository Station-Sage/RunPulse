"""AI 컨텍스트 빌더 진입점 — 레거시 dict 경로 재노출.

build_context()/format_context_text()/format_activity_context()는 레거시 dict 경로로
`ai_context_legacy.py`에 있으며 여기서 재노출한다(briefing.py·테스트 경로 호환).
서비스 레이어 기반 미사용 3함수(build_daily_briefing 등)는 삭제했다(P7-UXR-DESIGN-PENDING-IMPL).

설계 문서: v0.3/data/phase-5-impl/02-ai-context.md
"""
from __future__ import annotations

from src.ai.ai_context_legacy import (  # noqa: F401  재노출
    build_context,
    format_activity_context,
    format_context_text,
)
