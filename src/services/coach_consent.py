"""Coach LLM 전송 동의 저장소 — coach_consent 단일 행(30-coach-chat design §4.3).

동의는 계정당 1회, provider가 바뀌면 다시 받는다(동의 전 외부 호출 0회는 chat_engine_result.build_chain이 강제).
"""
from __future__ import annotations

import sqlite3

from src.ai.provider_common import LLM_PROVIDERS


def get_consent(conn: sqlite3.Connection) -> dict | None:
    row = conn.execute(
        "SELECT provider, accepted_at, exclude_notes, tools_enabled, fallback_enabled"
        " FROM coach_consent WHERE id = 1"
    ).fetchone()
    if not row:
        return None
    return {
        "provider": row[0], "accepted_at": row[1], "exclude_notes": bool(row[2]),
        "tools_enabled": bool(row[3]), "fallback_enabled": bool(row[4]),
    }


# C-17(ADR-055): 다른 제공자로의 재시도는 opt-in(기본 끔), 메모·주관 입력은 기본 제외.
DEFAULT_EXCLUDE_NOTES = True
DEFAULT_FALLBACK_ENABLED = False


def save_consent(conn: sqlite3.Connection, provider: str, exclude_notes: bool = DEFAULT_EXCLUDE_NOTES,
                 tools_enabled: bool = True, fallback_enabled: bool = DEFAULT_FALLBACK_ENABLED) -> dict:
    """동의 저장(upsert). provider가 LLM이 아니면 ValueError. 이미 저장된 동의 행은 바꾸지 않는다(기존 사용자 유지)."""
    if provider not in LLM_PROVIDERS:
        raise ValueError(f"지원하지 않는 provider: {provider}")
    conn.execute(
        "INSERT INTO coach_consent (id, provider, exclude_notes, tools_enabled, fallback_enabled)"
        " VALUES (1, ?, ?, ?, ?)"
        " ON CONFLICT(id) DO UPDATE SET provider=excluded.provider,"
        " accepted_at=CASE WHEN coach_consent.provider = excluded.provider"
        "   THEN coach_consent.accepted_at ELSE datetime('now') END,"
        " exclude_notes=excluded.exclude_notes, tools_enabled=excluded.tools_enabled,"
        " fallback_enabled=excluded.fallback_enabled",
        (provider, int(exclude_notes), int(tools_enabled), int(fallback_enabled)),
    )
    conn.commit()
    return get_consent(conn) or {}
