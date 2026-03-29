"""AI 채팅 전용 컨텍스트 빌더 — 의도 감지 → DB 자동 수집.

세부 구현:
  - chat_context_utils.py    : 공통 유틸 (_r1, _ri, seconds_to_pace, _fmt_sec)
  - chat_context_intent.py   : 의도 감지 (detect_intent, _extract_date)
  - chat_context_builders.py : 기본 + 의도별 빌더 5종 (today/race/compare/plan/recovery/lookup)
  - chat_context_rich.py     : Gemini 30d / Claude 14d 빌더 + runner_profile
  - chat_context_format.py   : 컨텍스트 dict → 프롬프트 텍스트
"""
from __future__ import annotations

import logging
import sqlite3
from datetime import date

from .chat_context_builders import _build_base_context, INTENT_BUILDERS
from .chat_context_format import _format_chat_context
from .chat_context_intent import detect_intent
from .chat_context_rich import (
    _add_mid_14d_context,
    _add_rich_30d_context,
    MID_PROVIDERS,
    RICH_PROVIDERS,
)

# Re-export for backward compat
from .chat_context_utils import _fmt_sec, _r1, _ri, seconds_to_pace  # noqa: F401
from .chat_context_intent import _extract_date  # noqa: F401
from .chat_context_rich import _build_runner_profile  # noqa: F401

log = logging.getLogger(__name__)

__all__ = [
    "build_chat_context",
    "detect_intent",
]


def build_chat_context(conn: sqlite3.Connection, message: str,
                       chat_history: list[dict] | None = None,
                       provider: str = "rule") -> str:
    """Provider 컨텍스트 용량에 맞는 채팅 컨텍스트 생성.

    Args:
        conn: DB 연결.
        message: 사용자 메시지.
        chat_history: 최근 대화 이력 (맥락 유지용).
        provider: AI provider 이름 (gemini/groq/claude/openai/rule).
    """
    today = date.today().isoformat()
    intent, target_date = detect_intent(message)

    ctx = _build_base_context(conn, today)
    ctx["intent"] = intent
    if target_date:
        ctx["_target_date"] = target_date

    if provider in RICH_PROVIDERS:
        try:
            _add_rich_30d_context(conn, ctx, today)
        except Exception:
            log.warning("30일 풀 컨텍스트 빌드 실패", exc_info=True)
    elif provider in MID_PROVIDERS:
        try:
            _add_mid_14d_context(conn, ctx, today)
        except Exception:
            log.warning("14일 컨텍스트 빌드 실패", exc_info=True)

    if target_date and intent != "lookup":
        try:
            INTENT_BUILDERS["lookup"](conn, ctx, today)
        except Exception:
            log.warning("lookup 컨텍스트 빌드 실패", exc_info=True)
    builder = INTENT_BUILDERS.get(intent)
    if builder:
        try:
            builder(conn, ctx, today)
        except Exception:
            log.warning("의도별 컨텍스트 빌드 실패 (%s)", intent, exc_info=True)

    return _format_chat_context(ctx, message, chat_history)
