"""OpsStore — 전역 `data/ops.db` 접근(스케줄러 상태·실행 기록·활동 신호·LLM 일 사용량, 멱등 DDL·보존 정리)."""
from __future__ import annotations

import json
import os
import sqlite3
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable

RUNS_RETENTION_DAYS = 14
USAGE_RETENTION_DAYS = 90

_DDL = """
CREATE TABLE IF NOT EXISTS user_activity (uid TEXT PRIMARY KEY, last_active_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS sched_state (
  uid TEXT PRIMARY KEY, next_due_at TEXT NOT NULL, state TEXT NOT NULL DEFAULT 'active',
  fail_streak INTEGER NOT NULL DEFAULT 0, auth_streak_json TEXT, last_result TEXT, updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS sched_runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT, uid TEXT NOT NULL, started_at TEXT NOT NULL, finished_at TEXT,
  result TEXT NOT NULL, sources TEXT, job_ids TEXT, duration_s REAL, detail TEXT);
CREATE INDEX IF NOT EXISTS ix_sched_runs_started ON sched_runs(started_at);
CREATE TABLE IF NOT EXISTS llm_usage_daily (
  day TEXT NOT NULL, uid TEXT NOT NULL, feature TEXT NOT NULL,
  calls INTEGER NOT NULL DEFAULT 0, refused INTEGER NOT NULL DEFAULT 0,
  tokens_in INTEGER NOT NULL DEFAULT 0, tokens_out INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (day, uid, feature));
"""
_STATE_COLS = ("uid", "next_due_at", "state", "fail_streak", "auth_streak_json", "last_result", "updated_at")


def ops_db_path() -> Path:
    """`OPS_DB_PATH` env 우선, 없으면 `<repo>/data/ops.db`."""
    env = os.environ.get("OPS_DB_PATH", "").strip()
    if env:
        return Path(env)
    from src.utils.user_context import project_root
    return project_root() / "data" / "ops.db"


def _iso(dt: datetime) -> str:
    return dt.isoformat(timespec="seconds")


class OpsStore:
    """ops.db 얇은 래퍼. 호출마다 커넥션을 열고 닫는다(스레드 안전, WAL)."""

    def __init__(self, path: str | Path | None = None, clock: Callable[[], datetime] = datetime.now):
        self.path = Path(path) if path else ops_db_path()
        self.clock = clock
        self._ddl_done = False
        self._ddl_lock = threading.Lock()

    def _conn(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.path), timeout=10)
        if not self._ddl_done:
            with self._ddl_lock:
                conn.execute("PRAGMA journal_mode=WAL")
                conn.executescript(_DDL)
                self._ddl_done = True
        return conn

    def _run(self, sql: str, params: tuple = ()) -> list[tuple]:
        conn = self._conn()
        try:
            with conn:
                return conn.execute(sql, params).fetchall()
        finally:
            conn.close()

    # ── 활동 신호 ─────────────────────────────────────────────
    def touch_activity(self, uid: str, at: datetime | None = None) -> datetime | None:
        """last_active_at 갱신. 갱신 전 값을 돌려준다(없으면 None)."""
        prev = self.last_active(uid)
        self._run("INSERT INTO user_activity (uid, last_active_at) VALUES (?, ?) "
                  "ON CONFLICT(uid) DO UPDATE SET last_active_at=excluded.last_active_at",
                  (uid, _iso(at or self.clock())))
        return prev

    def last_active(self, uid: str) -> datetime | None:
        rows = self._run("SELECT last_active_at FROM user_activity WHERE uid=?", (uid,))
        return datetime.fromisoformat(rows[0][0]) if rows else None

    def all_activity(self) -> dict[str, datetime]:
        return {u: datetime.fromisoformat(t) for u, t in self._run("SELECT uid, last_active_at FROM user_activity")}

    # ── 스케줄러 상태 ─────────────────────────────────────────
    def get_state(self, uid: str) -> dict | None:
        rows = self._run(f"SELECT {', '.join(_STATE_COLS)} FROM sched_state WHERE uid=?", (uid,))
        return self._state_dict(rows[0]) if rows else None

    def all_states(self) -> dict[str, dict]:
        rows = self._run(f"SELECT {', '.join(_STATE_COLS)} FROM sched_state")
        return {r[0]: self._state_dict(r) for r in rows}

    @staticmethod
    def _state_dict(row: tuple) -> dict:
        d = dict(zip(_STATE_COLS, row))
        d["next_due_at"] = datetime.fromisoformat(d["next_due_at"])
        d["auth_streak"] = json.loads(d.pop("auth_streak_json") or "{}")
        return d

    def put_state(self, uid: str, *, next_due_at: datetime, state: str = "active", fail_streak: int = 0,
                  auth_streak: dict | None = None, last_result: str | None = None) -> None:
        self._run(
            "INSERT INTO sched_state (uid, next_due_at, state, fail_streak, auth_streak_json, last_result, updated_at) "
            "VALUES (?,?,?,?,?,?,?) ON CONFLICT(uid) DO UPDATE SET next_due_at=excluded.next_due_at, "
            "state=excluded.state, fail_streak=excluded.fail_streak, auth_streak_json=excluded.auth_streak_json, "
            "last_result=excluded.last_result, updated_at=excluded.updated_at",
            (uid, _iso(next_due_at), state, int(fail_streak), json.dumps(auth_streak or {}), last_result,
             _iso(self.clock())))

    def add_run(self, uid: str, *, started_at: datetime, result: str, finished_at: datetime | None = None,
                sources: list[str] | None = None, job_ids: list[str] | None = None,
                detail: str | None = None) -> None:
        dur = (finished_at - started_at).total_seconds() if finished_at else None
        self._run("INSERT INTO sched_runs (uid, started_at, finished_at, result, sources, job_ids, duration_s, detail) "
                  "VALUES (?,?,?,?,?,?,?,?)",
                  (uid, _iso(started_at), _iso(finished_at) if finished_at else None, result,
                   ",".join(sources or []), ",".join(job_ids or []), dur, detail))

    def runs_since(self, since: datetime) -> list[dict]:
        cols = ("uid", "started_at", "finished_at", "result", "sources", "job_ids", "duration_s", "detail")
        rows = self._run(f"SELECT {', '.join(cols)} FROM sched_runs WHERE started_at >= ? ORDER BY id",
                         (_iso(since),))
        return [dict(zip(cols, r)) for r in rows]

    # ── LLM 사용량 ────────────────────────────────────────────
    def add_usage(self, day: str, uid: str, feature: str, *, calls: int = 0, refused: int = 0,
                  tokens_in: int = 0, tokens_out: int = 0) -> None:
        self._run(
            "INSERT INTO llm_usage_daily (day, uid, feature, calls, refused, tokens_in, tokens_out) "
            "VALUES (?,?,?,?,?,?,?) ON CONFLICT(day, uid, feature) DO UPDATE SET "
            "calls=calls+excluded.calls, refused=refused+excluded.refused, "
            "tokens_in=tokens_in+excluded.tokens_in, tokens_out=tokens_out+excluded.tokens_out",
            (day, uid, feature, calls, refused, tokens_in, tokens_out))

    def usage(self, day: str, uid: str | None = None) -> dict:
        """하루 합계 {calls, tokens, refused}. uid=None 이면 전역."""
        where, params = ("day=?", (day,)) if uid is None else ("day=? AND uid=?", (day, uid))
        row = self._run("SELECT COALESCE(SUM(calls),0), COALESCE(SUM(tokens_in+tokens_out),0), "
                        f"COALESCE(SUM(refused),0) FROM llm_usage_daily WHERE {where}", params)[0]
        return {"calls": int(row[0]), "tokens": int(row[1]), "refused": int(row[2])}

    def top_usage(self, day: str, limit: int = 10) -> list[dict]:
        rows = self._run("SELECT uid, SUM(calls), SUM(tokens_in+tokens_out), SUM(refused) FROM llm_usage_daily "
                         "WHERE day=? GROUP BY uid ORDER BY SUM(calls) DESC LIMIT ?", (day, limit))
        return [{"uid": r[0], "calls": r[1], "tokens": r[2], "refused": r[3]} for r in rows]

    # ── 정리 ──────────────────────────────────────────────────
    def purge(self, now: datetime | None = None) -> dict:
        """sched_runs 14일·llm_usage_daily 90일 초과분 삭제. 삭제 건수 반환."""
        now = now or self.clock()
        runs_cut = _iso(now - timedelta(days=RUNS_RETENTION_DAYS))
        usage_cut = (now - timedelta(days=USAGE_RETENTION_DAYS)).date().isoformat()
        conn = self._conn()
        try:
            with conn:
                r = conn.execute("DELETE FROM sched_runs WHERE started_at < ?", (runs_cut,)).rowcount
                u = conn.execute("DELETE FROM llm_usage_daily WHERE day < ?", (usage_cut,)).rowcount
        finally:
            conn.close()
        return {"sched_runs": r, "llm_usage_daily": u}

    def delete_user(self, uid: str) -> None:
        """계정 삭제 시 해당 uid 의 모든 행 제거(§3.5)."""
        conn = self._conn()
        try:
            with conn:
                for table in ("user_activity", "sched_state", "sched_runs", "llm_usage_daily"):
                    conn.execute(f"DELETE FROM {table} WHERE uid=?", (uid,))
        finally:
            conn.close()


_default: OpsStore | None = None
_default_lock = threading.Lock()


def default_store() -> OpsStore:
    """프로세스 공용 OpsStore — 경로(env)가 바뀌면 새로 만든다(테스트 격리)."""
    global _default
    with _default_lock:
        if _default is None or _default.path != ops_db_path():
            _default = OpsStore()
        return _default
