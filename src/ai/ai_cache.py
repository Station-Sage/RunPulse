"""AI 캐시 관리 — DB 기반 AI 해석 결과 저장/조회/갱신.

ai_cache 테이블에 탭별 AI 해석을 저장하고,
8시간(TTL) 또는 동기화 후 갱신합니다.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta

_TTL_HOURS = 8  # 하루 3회 갱신 (아침/점심/저녁)


def get_cached(conn: sqlite3.Connection, tab: str, cache_key: str = "default") -> dict | None:
    """캐시된 AI 해석 조회. 유효하면 dict, 아니면 None.

    Args:
        conn: SQLite 연결 (running.db).
        tab: 탭 이름 ('dashboard', 'activity', ...).
        cache_key: 탭 내 고유 키 (활동 ID, 기간 등).

    Returns:
        파싱된 JSON dict 또는 None (캐시 없거나 만료).
    """
    try:
        row = conn.execute(
            "SELECT content_json, generated_at FROM ai_cache WHERE tab=? AND cache_key=?",
            (tab, cache_key),
        ).fetchone()
    except sqlite3.OperationalError:
        # 테이블 없음
        _ensure_table(conn)
        return None

    if not row:
        return None

    content, generated_at = row[0], row[1]
    if not _is_fresh(generated_at, conn):
        return None

    try:
        return json.loads(content)
    except (json.JSONDecodeError, TypeError):
        return None


def set_cached(conn: sqlite3.Connection, tab: str, cache_key: str,
               content: dict) -> None:
    """AI 해석 결과를 캐시에 저장 (UPSERT)."""
    _ensure_table(conn)
    content_json = json.dumps(content, ensure_ascii=False)
    now = datetime.now().isoformat(timespec="seconds")
    conn.execute(
        """INSERT INTO ai_cache (tab, cache_key, content_json, generated_at)
           VALUES (?, ?, ?, ?)
           ON CONFLICT(tab, cache_key) DO UPDATE SET
               content_json=excluded.content_json,
               generated_at=excluded.generated_at""",
        (tab, cache_key, content_json, now),
    )
    conn.commit()


def get_cache_age(conn: sqlite3.Connection, tab: str,
                   cache_key: str = "default") -> str | None:
    """캐시 생성 시점의 상대 시간 문자열 반환. 없으면 None.

    Returns:
        '방금 전', '5분 전', '2시간 전' 등.
    """
    try:
        row = conn.execute(
            "SELECT generated_at FROM ai_cache WHERE tab=? AND cache_key=?",
            (tab, cache_key),
        ).fetchone()
    except sqlite3.OperationalError:
        return None

    if not row or not row[0]:
        return None

    try:
        gen_time = datetime.fromisoformat(row[0])
    except (ValueError, TypeError):
        return None

    delta = datetime.now() - gen_time
    secs = int(delta.total_seconds())
    if secs < 60:
        return "방금 전"
    elif secs < 3600:
        return f"{secs // 60}분 전"
    elif secs < 86400:
        return f"{secs // 3600}시간 전"
    else:
        return f"{secs // 86400}일 전"


def invalidate(conn: sqlite3.Connection, tab: str | None = None) -> None:
    """캐시 무효화. tab 지정 시 해당 탭만, 없으면 전체."""
    _ensure_table(conn)
    if tab:
        conn.execute("DELETE FROM ai_cache WHERE tab=?", (tab,))
    else:
        conn.execute("DELETE FROM ai_cache")
    conn.commit()


def invalidate_after_sync(conn: sqlite3.Connection) -> None:
    """동기화 후 전체 캐시 무효화."""
    invalidate(conn)


def _is_fresh(generated_at: str, conn: sqlite3.Connection) -> bool:
    """캐시가 유효한지 확인 (TTL + 동기화 후 여부)."""
    try:
        gen_time = datetime.fromisoformat(generated_at)
    except (ValueError, TypeError):
        return False

    # TTL 체크 (8시간)
    if datetime.now() - gen_time > timedelta(hours=_TTL_HOURS):
        return False

    # 동기화 후 체크: 마지막 동기화가 캐시 생성 이후면 무효
    try:
        from src.utils.sync_jobs import list_recent_jobs
        jobs = list_recent_jobs(limit=1)
        if jobs and jobs[0].updated_at:
            sync_time = datetime.fromisoformat(jobs[0].updated_at)
            if sync_time > gen_time:
                return False
    except Exception:
        pass

    return True


def _ensure_table(conn: sqlite3.Connection) -> None:
    """ai_cache 테이블 존재 보장."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ai_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tab TEXT NOT NULL,
            cache_key TEXT NOT NULL,
            content_json TEXT NOT NULL,
            generated_at TEXT NOT NULL,
            UNIQUE(tab, cache_key)
        )
    """)
