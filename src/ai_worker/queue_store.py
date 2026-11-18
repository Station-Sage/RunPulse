"""ai_jobs 큐 저장소 — enqueue·claim·heartbeat·finish·정체 회수·만료·일시정지 (순수 SQL, 앱·워커 공유)."""
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone

STALE_SEC = 60
MAX_ATTEMPTS = 2
HEARTBEAT_FRESH_SEC = 20
DEFAULT_TTL_SEC = 600
BODY_RETENTION_DAYS = 7
TERMINAL = ("done", "failed", "cancelled", "expired")


def now_iso(now: datetime | None = None) -> str:
    return (now or datetime.now(timezone.utc)).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _shift(iso: str, seconds: float) -> str:
    dt = datetime.strptime(iso, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)
    return now_iso(dt + timedelta(seconds=seconds))


def connect(db_path, timeout: float = 5.0) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path), timeout=timeout, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute(f"PRAGMA busy_timeout={int(timeout * 1000)}")
    return conn


def enqueue(conn: sqlite3.Connection, *, kind: str, model: str, input_json: str, priority: int = 5,
            thread_key: str | None = None, system_ctx: str | None = None, ctx_hash: str | None = None,
            tools: str = "none", output_schema: str = "text", ttl_sec: int = DEFAULT_TTL_SEC,
            now: str | None = None) -> int:
    ts = now or now_iso()
    cur = conn.execute(
        "INSERT INTO ai_jobs(kind, thread_key, priority, model, system_ctx, ctx_hash, input_json, tools,"
        " output_schema, created_at, expires_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (kind, thread_key, priority, model, system_ctx, ctx_hash, input_json, tools, output_schema,
         ts, _shift(ts, ttl_sec)),
    )
    return int(cur.lastrowid)


def claim(conn: sqlite3.Connection, worker_id: str, now: str | None = None) -> dict | None:
    """대기 job 1건을 원자적으로 집는다(단일 UPDATE…RETURNING). 없으면 None."""
    ts = now or now_iso()
    row = conn.execute(
        "UPDATE ai_jobs SET state='running', worker_id=?, claimed_at=?, heartbeat_at=?,"
        " attempts=attempts+1, queue_ms=CAST((julianday(?)-julianday(created_at))*86400000 AS INTEGER)"
        " WHERE id=(SELECT id FROM ai_jobs WHERE state='queued' AND cancel_requested=0 AND expires_at>?"
        " ORDER BY priority, id LIMIT 1) AND state='queued' RETURNING *",
        (worker_id, ts, ts, ts, ts),
    ).fetchone()
    return dict(row) if row else None


def heartbeat(conn: sqlite3.Connection, job_ids: list[int], now: str | None = None) -> None:
    if job_ids:
        marks = ",".join("?" for _ in job_ids)
        conn.execute(f"UPDATE ai_jobs SET heartbeat_at=? WHERE state='running' AND id IN ({marks})",
                     [now or now_iso(), *job_ids])


def update_progress(conn: sqlite3.Connection, job_id: int, progress_json: str | None = None,
                    partial_text: str | None = None) -> None:
    conn.execute(
        "UPDATE ai_jobs SET progress_json=COALESCE(?, progress_json), partial_text=COALESCE(?, partial_text)"
        " WHERE id=? AND state='running'", (progress_json, partial_text, job_id))


def cancel_requested(conn: sqlite3.Connection, job_id: int) -> bool:
    row = conn.execute("SELECT cancel_requested FROM ai_jobs WHERE id=?", (job_id,)).fetchone()
    return bool(row and row[0])


def finish(conn: sqlite3.Connection, job_id: int, state: str, *, result_text: str | None = None,
           error_reason: str | None = None, session_id: str | None = None, tokens_in: int | None = None,
           tokens_out: int | None = None, cache_read: int | None = None, tool_calls: int | None = None,
           now: str | None = None) -> bool:
    """running → 종료 상태. 이미 종료된 job(취소 등)은 덮어쓰지 않는다."""
    if state not in TERMINAL:
        raise ValueError(f"not a terminal state: {state}")
    ts = now or now_iso()
    cur = conn.execute(
        "UPDATE ai_jobs SET state=?, result_text=?, error_reason=?, session_id=COALESCE(?, session_id),"
        " tokens_in=?, tokens_out=?, cache_read=?, tool_calls=?, finished_at=?,"
        " run_ms=CAST((julianday(?)-julianday(claimed_at))*86400000 AS INTEGER)"
        " WHERE id=? AND state='running'",
        (state, result_text, error_reason, session_id, tokens_in, tokens_out, cache_read, tool_calls,
         ts, ts, job_id))
    return cur.rowcount == 1


def recover_stale(conn: sqlite3.Connection, worker_id: str | None = None, now: str | None = None,
                  stale_sec: int = STALE_SEC) -> dict[str, int]:
    """heartbeat 가 멈춘 running job 회수. attempts<MAX 면 queued, 아니면 failed(stale).

    worker_id 를 주면 기동 직후처럼 그 워커의 running 행을 heartbeat 와 무관하게 전부 회수한다.
    """
    ts = now or now_iso()
    cond = "worker_id=?" if worker_id else "COALESCE(heartbeat_at, claimed_at) < ?"
    arg = worker_id if worker_id else _shift(ts, -stale_sec)
    requeued = conn.execute(
        f"UPDATE ai_jobs SET state='queued', worker_id=NULL, claimed_at=NULL, heartbeat_at=NULL"
        f" WHERE state='running' AND attempts<? AND {cond}", (MAX_ATTEMPTS, arg)).rowcount
    failed = conn.execute(
        f"UPDATE ai_jobs SET state='failed', error_reason='stale', finished_at=?"
        f" WHERE state='running' AND {cond}", (ts, arg)).rowcount
    return {"requeued": requeued, "failed": failed}


def expire_queued(conn: sqlite3.Connection, now: str | None = None) -> int:
    """만료된 queued → expired, 취소 요청된 queued → cancelled."""
    ts = now or now_iso()
    n = conn.execute("UPDATE ai_jobs SET state='expired', finished_at=? WHERE state='queued' AND expires_at<=?",
                     (ts, ts)).rowcount
    n += conn.execute("UPDATE ai_jobs SET state='cancelled', finished_at=? WHERE state='queued'"
                      " AND cancel_requested=1", (ts,)).rowcount
    return n


def purge_bodies(conn: sqlite3.Connection, now: str | None = None, days: int = BODY_RETENTION_DAYS) -> int:
    """종료 job 의 본문(입력·맥락·결과)을 보존기간 뒤 비운다. 행과 토큰·지연 통계는 남긴다."""
    cutoff = _shift(now or now_iso(), -days * 86400)
    return conn.execute(
        "UPDATE ai_jobs SET input_json='{}', system_ctx=NULL, result_text=NULL, partial_text=NULL"
        " WHERE state IN ('done','failed','cancelled','expired') AND finished_at<?"
        " AND (input_json!='{}' OR result_text IS NOT NULL)", (cutoff,)).rowcount


def upsert_worker_state(conn: sqlite3.Connection, worker_id: str, *, pid: int, cli_version: str,
                        active_jobs: int, started_at: str, now: str | None = None) -> None:
    conn.execute(
        "INSERT INTO ai_worker_state(worker_id, pid, cli_version, started_at, heartbeat_at, active_jobs)"
        " VALUES (?,?,?,?,?,?) ON CONFLICT(worker_id) DO UPDATE SET pid=excluded.pid,"
        " cli_version=excluded.cli_version, heartbeat_at=excluded.heartbeat_at,"
        " active_jobs=excluded.active_jobs", (worker_id, pid, cli_version, started_at, now or now_iso(),
                                              active_jobs))


def set_paused(conn: sqlite3.Connection, worker_id: str, until: str | None, error: str | None = None) -> None:
    conn.execute("UPDATE ai_worker_state SET paused_until=?, last_error=COALESCE(?, last_error)"
                 " WHERE worker_id=?", (until, error, worker_id))


def is_paused(conn: sqlite3.Connection, worker_id: str, now: str | None = None) -> bool:
    row = conn.execute("SELECT paused_until FROM ai_worker_state WHERE worker_id=?", (worker_id,)).fetchone()
    return bool(row and row[0] and row[0] > (now or now_iso()))


def worker_available(conn: sqlite3.Connection, now: str | None = None,
                     fresh_sec: int = HEARTBEAT_FRESH_SEC) -> bool:
    """앱 측 판정: 하트비트가 신선하고 일시정지가 아닌 워커가 하나라도 있는가."""
    ts = now or now_iso()
    row = conn.execute(
        "SELECT 1 FROM ai_worker_state WHERE heartbeat_at>=? AND (paused_until IS NULL OR paused_until<=?)"
        " LIMIT 1", (_shift(ts, -fresh_sec), ts)).fetchone()
    return row is not None
