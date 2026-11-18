"""스키마 v48 — Claude CLI 큐(V2-AI-CLAUDE-QUEUE): ai_jobs·ai_sessions·ai_worker_state·ai_outputs.

앱(컨테이너)과 호스트 워커가 DB 폴링으로 작업을 주고받는다. 가산 테이블, 멱등.
"""
from __future__ import annotations

import sqlite3

AI_JOB_KINDS = ("coach", "insight_polish", "narrative", "adherence", "plan_draft", "deep_analysis", "ping")
AI_JOB_STATES = ("queued", "running", "done", "failed", "cancelled", "expired")


def _in(vals: tuple[str, ...]) -> str:
    return ",".join(f"'{v}'" for v in vals)


def ensure_v48(conn: sqlite3.Connection) -> None:
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS ai_jobs (
            id INTEGER PRIMARY KEY,
            kind TEXT NOT NULL CHECK (kind IN ({_in(AI_JOB_KINDS)})),
            thread_key TEXT,
            priority INTEGER NOT NULL DEFAULT 5,
            state TEXT NOT NULL DEFAULT 'queued' CHECK (state IN ({_in(AI_JOB_STATES)})),
            model TEXT NOT NULL,
            system_ctx TEXT, ctx_hash TEXT,
            input_json TEXT NOT NULL,
            tools TEXT NOT NULL DEFAULT 'none' CHECK (tools IN ('none','read')),
            output_schema TEXT NOT NULL DEFAULT 'text',
            progress_json TEXT, partial_text TEXT,
            result_text TEXT, error_reason TEXT,
            cancel_requested INTEGER NOT NULL DEFAULT 0,
            attempts INTEGER NOT NULL DEFAULT 0, worker_id TEXT, session_id TEXT,
            tokens_in INTEGER, tokens_out INTEGER, cache_read INTEGER, tool_calls INTEGER,
            queue_ms INTEGER, run_ms INTEGER,
            created_at TEXT NOT NULL, claimed_at TEXT, heartbeat_at TEXT, finished_at TEXT,
            expires_at TEXT NOT NULL
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS ix_ai_jobs_queue ON ai_jobs(state, priority, id)")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS ai_sessions (
            thread_key TEXT PRIMARY KEY, session_id TEXT NOT NULL, model TEXT NOT NULL, ctx_hash TEXT,
            turns INTEGER NOT NULL DEFAULT 0, ctx_tokens INTEGER NOT NULL DEFAULT 0,
            state TEXT NOT NULL DEFAULT 'active' CHECK (state IN ('active','retired','broken')),
            retired_reason TEXT, created_at TEXT NOT NULL, last_used_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS ai_worker_state (
            worker_id TEXT PRIMARY KEY, pid INTEGER, cli_version TEXT, started_at TEXT,
            heartbeat_at TEXT, active_jobs INTEGER, paused_until TEXT, last_error TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS ai_outputs (
            kind TEXT NOT NULL, scope_key TEXT NOT NULL, src_hash TEXT NOT NULL,
            body_json TEXT NOT NULL, job_id INTEGER, created_at TEXT NOT NULL,
            PRIMARY KEY (kind, scope_key)
        )
        """
    )
