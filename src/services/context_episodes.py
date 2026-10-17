"""컨텍스트 에피소드(질병·여행·고도) 저장/조회 (NEW-1~3·9·13·19·22) — '오늘' = reference_today.

confirmed 만 신호의 트리거/근거가 되고 candidate 는 context 다. candidate 는 2일 무응답이면 dismissed.
질병은 자동 종료하지 않는다(종료는 사용자만). 삭제 연쇄는 context_episode_delete.py.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import date, timedelta

from src.utils.reference_day import reference_today

KINDS = ("illness", "travel", "altitude")
CANDIDATE_TTL_DAYS = 2
ILLNESS_RECONFIRM_DAYS = 7
_COLS = "id, kind, start_date, end_date, severity, detail_json, origin, status, last_confirmed_date"


def _row(r) -> dict:
    d = dict(zip(_COLS.replace(" ", "").split(","), r))
    d["detail"] = json.loads(d.pop("detail_json") or "{}")
    return d


def _today(conn) -> str:
    return reference_today(conn)[0]


def open_episode(conn, kind: str, *, start_date: str | None = None, severity: int | None = None,
                 detail: dict | None = None, origin: str = "user", status: str = "confirmed") -> int:
    """에피소드 생성(commit 은 호출자). 같은 kind 의 진행 중 행이 있으면 새로 만들지 않고 그 id 를 돌려준다."""
    if kind not in KINDS:
        raise ValueError("invalid kind")
    day = start_date or _today(conn)
    cur = conn.execute("SELECT id FROM context_episodes WHERE kind=? AND status IN ('candidate','confirmed')"
                       " AND end_date IS NULL ORDER BY id DESC LIMIT 1", (kind,)).fetchone()
    if cur:
        if status == "confirmed":
            confirm(conn, cur[0])
        return cur[0]
    return conn.execute(
        "INSERT INTO context_episodes(kind, start_date, severity, detail_json, origin, status, last_confirmed_date)"
        " VALUES (?,?,?,?,?,?,?)",
        (kind, day, severity, json.dumps(detail or {}, ensure_ascii=False), origin, status,
         day if status == "confirmed" else None)).lastrowid


def confirm(conn, episode_id: int) -> bool:
    """candidate 확정 또는 confirmed 의 '계속' — last_confirmed_date 갱신."""
    day = _today(conn)
    n = conn.execute("UPDATE context_episodes SET status='confirmed', last_confirmed_date=?, updated_at=datetime('now')"
                     " WHERE id=? AND status IN ('candidate','confirmed') AND end_date IS NULL", (day, episode_id)).rowcount
    return n > 0


def dismiss(conn, episode_id: int) -> bool:
    n = conn.execute("UPDATE context_episodes SET status='dismissed', updated_at=datetime('now')"
                     " WHERE id=? AND status='candidate'", (episode_id,)).rowcount
    return n > 0


def close(conn, episode_id: int, end_date: str | None = None) -> bool:
    """'나았어요/귀국' — end_date 기록(시작일보다 앞서지 않게 보정)."""
    row = conn.execute("SELECT start_date FROM context_episodes WHERE id=? AND status='confirmed' AND end_date IS NULL",
                       (episode_id,)).fetchone()
    if row is None:
        return False
    end = max(end_date or _today(conn), row[0])
    conn.execute("UPDATE context_episodes SET end_date=?, updated_at=datetime('now') WHERE id=?", (end, episode_id))
    return True


def expire_candidates(conn) -> int:
    """응답 없이 CANDIDATE_TTL_DAYS 지난 candidate → dismissed (NEW-13). 쓰기 예외: 조회 경로에서 호출 가능."""
    cutoff = (date.fromisoformat(_today(conn)) - timedelta(days=CANDIDATE_TTL_DAYS)).isoformat()
    return conn.execute("UPDATE context_episodes SET status='dismissed', updated_at=datetime('now')"
                        " WHERE status='candidate' AND date(created_at) <= ?", (cutoff,)).rowcount


def list_active(conn) -> list[dict]:
    """진행 중(candidate·confirmed, end_date 없음) 에피소드."""
    expire_candidates(conn)
    return [_row(r) for r in conn.execute(
        f"SELECT {_COLS} FROM context_episodes WHERE status IN ('candidate','confirmed') AND end_date IS NULL"
        " ORDER BY id DESC")]


def list_all(conn, *, include_dismissed: bool = False) -> list[dict]:
    where = "" if include_dismissed else " WHERE status!='dismissed'"
    return [_row(r) for r in conn.execute(f"SELECT {_COLS} FROM context_episodes{where} ORDER BY start_date DESC, id DESC")]


def illness_reconfirm(conn) -> dict | None:
    """last_confirmed_date 로부터 ILLNESS_RECONFIRM_DAYS 이상 지난 진행 중 confirmed 질병(없으면 None). 트리거 지위는 유지."""
    today = date.fromisoformat(_today(conn))
    r = conn.execute("SELECT id, COALESCE(last_confirmed_date, start_date) FROM context_episodes WHERE kind='illness'"
                     " AND status='confirmed' AND end_date IS NULL ORDER BY id DESC LIMIT 1").fetchone()
    if r is None:
        return None
    days = (today - date.fromisoformat(r[1])).days
    return {"episode_id": r[0], "days_since": days} if days >= ILLNESS_RECONFIRM_DAYS else None
