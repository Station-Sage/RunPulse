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


def save_consent(conn: sqlite3.Connection, provider: str, exclude_notes: bool = False,
                 tools_enabled: bool = True, fallback_enabled: bool = True) -> dict:
    """동의 저장(upsert). provider가 LLM이 아니면 ValueError."""
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
