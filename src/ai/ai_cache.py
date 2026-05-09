"""AI 캐시 관리 — DB 기반 AI 해석 결과 저장/조회/갱신.

ai_cache 테이블에 탭별 AI 해석을 저장한다.

캐시 무효화 조건 (ADR-011):
  1. 신규 활동 추가   — activity_summaries.MAX(id) 변경
  2. 신규 웰니스 레코드 — daily_wellness.MAX(date) 변경
  3. 날짜 변경       — 새로운 날 = 코칭 컨텍스트 갱신
  4. TTL 초과        — 8시간 safety net
  5. 명시적 refresh  — invalidate() 직접 호출 (사용자 요청)
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta

_TTL_HOURS = 8


def get_cached(conn: sqlite3.Connection, tab: str, cache_key: str = "default") -> dict | None:
    """캐시된 AI 해석 조회. 유효하면 dict, 아니면 None."""
    try:
        row = conn.execute(
            "SELECT content_json, generated_at, data_fingerprint FROM ai_cache"
            " WHERE tab=? AND cache_key=?",
            (tab, cache_key),
        ).fetchone()
    except sqlite3.OperationalError:
        _ensure_table(conn)
        return None

    if not row:
        return None

    content, generated_at, stored_fp = row
    if not _is_fresh(generated_at, stored_fp, conn):
        return None

    try:
        return json.loads(content)
    except (json.JSONDecodeError, TypeError):
        return None


def set_cached(conn: sqlite3.Connection, tab: str, cache_key: str,
               content: dict) -> None:
    """AI 해석 결과를 캐시에 저장 (UPSERT). 현재 데이터 핑거프린트 함께 저장."""
    _ensure_table(conn)
    content_json = json.dumps(content, ensure_ascii=False)
    now = datetime.now().isoformat(timespec="seconds")
    fingerprint = _compute_fingerprint(conn)
    conn.execute(
        """INSERT INTO ai_cache (tab, cache_key, content_json, generated_at, data_fingerprint)
           VALUES (?, ?, ?, ?, ?)
           ON CONFLICT(tab, cache_key) DO UPDATE SET
               content_json=excluded.content_json,
               generated_at=excluded.generated_at,
               data_fingerprint=excluded.data_fingerprint""",
        (tab, cache_key, content_json, now, fingerprint),
    )
    conn.commit()


def get_cache_age(conn: sqlite3.Connection, tab: str,
                  cache_key: str = "default") -> str | None:
    """캐시 생성 시점의 상대 시간 문자열 반환. 없으면 None."""
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
    """캐시 명시적 무효화. tab 지정 시 해당 탭만, 없으면 전체."""
    _ensure_table(conn)
    if tab:
        conn.execute("DELETE FROM ai_cache WHERE tab=?", (tab,))
    else:
        conn.execute("DELETE FROM ai_cache")
    conn.commit()


# ── 내부 헬퍼 ──────────────────────────────────────────────────────────────

def _compute_fingerprint(conn: sqlite3.Connection) -> str:
    """데이터 상태 핑거프린트 — 의미 있는 변화(활동·웰니스·날짜)만 감지."""
    from datetime import date
    today = date.today().isoformat()
    try:
        act_max = conn.execute(
            "SELECT COALESCE(MAX(id), 0) FROM activity_summaries"
        ).fetchone()[0]
        well_max = conn.execute(
            "SELECT COALESCE(MAX(date), '') FROM daily_wellness"
        ).fetchone()[0]
        return f"{today}|{act_max}|{well_max}"
    except Exception:
        return today


def _is_fresh(generated_at: str, stored_fp: str | None,
              conn: sqlite3.Connection) -> bool:
    """캐시 유효 여부 판단.

    1) TTL(8h) 초과 → stale
    2) 데이터 핑거프린트 불일치 → stale (신규 활동·웰니스·날짜 변경)
    """
    try:
        gen_time = datetime.fromisoformat(generated_at)
    except (ValueError, TypeError):
        return False

    if datetime.now() - gen_time > timedelta(hours=_TTL_HOURS):
        return False

    current_fp = _compute_fingerprint(conn)
    if stored_fp != current_fp:
        return False

    return True


def _ensure_table(conn: sqlite3.Connection) -> None:
    """ai_cache 테이블 존재 보장. 기존 테이블에 data_fingerprint 컬럼 추가."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ai_cache (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            tab             TEXT NOT NULL,
            cache_key       TEXT NOT NULL,
            content_json    TEXT NOT NULL,
            generated_at    TEXT NOT NULL,
            data_fingerprint TEXT,
            UNIQUE(tab, cache_key)
        )
    """)
    try:
        conn.execute("ALTER TABLE ai_cache ADD COLUMN data_fingerprint TEXT")
    except sqlite3.OperationalError:
        pass  # 이미 존재
