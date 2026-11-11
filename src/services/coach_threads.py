"""Coach 스레드 목록·제목 — coach_service 에서 분리(C-05 페이지 단위·C-11 제목 정리·C-16 정렬 보조 키).

스레드 제목은 규칙 기반(첫 메시지 앞부분)이다 — AI 자동 요약 제목은 범위 밖.
"""
from __future__ import annotations

import re
import sqlite3

TITLE_MAX_LEN = 30
THREADS_PAGE = 30          # C-05: 목록 한 번에 30개 + '더 보기'
THREADS_PAGE_MAX = 100

_IMAGE = re.compile(r"!\[([^\]]*)\]\([^)]*\)")
_LINK = re.compile(r"\[([^\]]*)\]\([^)]*\)")
_TAG = re.compile(r"<[^>]*>")
_MARK = re.compile(r"(^|\s)[#>]+\s*|\*+|`+|~~|__")
_SPACE = re.compile(r"\s+")


def plain_title_text(message: str) -> str:
    """C-11: 마크다운·HTML 태그를 걷어 내고 줄바꿈·연속 공백을 한 칸으로."""
    text = _IMAGE.sub(r"\1", message)
    text = _LINK.sub(r"\1", text)
    text = _TAG.sub(" ", text)
    text = _MARK.sub(r"\1", text)
    return _SPACE.sub(" ", text).strip()


def derive_title(message: str) -> str:
    """규칙 기반 스레드 제목 — 정리한 첫 메시지를 30자에서 자르되 가능하면 낱말 경계에서."""
    text = plain_title_text(message) or message.strip()[:TITLE_MAX_LEN] or "새 대화"
    if len(text) <= TITLE_MAX_LEN:
        return text
    cut = text[:TITLE_MAX_LEN]
    space = cut.rfind(" ")
    if space >= TITLE_MAX_LEN // 2:
        cut = cut[:space]
    return cut.rstrip() + "…"


def list_threads(conn: sqlite3.Connection, limit: int | None = None, offset: int = 0) -> list[dict]:
    """스레드 목록 — 마지막 메시지 미리보기 포함, 최근 활동순(같은 시각이면 id 역순, C-16).

    limit 이 None 이면 전부(내부·테스트 호출 호환).
    """
    conn.row_factory = sqlite3.Row
    sql = """
        SELECT
            t.id, t.title, t.created_at, t.updated_at,
            (SELECT content FROM chat_messages m
             WHERE m.thread_id = t.id ORDER BY m.id DESC LIMIT 1) AS last_message,
            (SELECT created_at FROM chat_messages m
             WHERE m.thread_id = t.id ORDER BY m.id DESC LIMIT 1) AS last_message_at
        FROM chat_threads t
        ORDER BY t.updated_at DESC, t.id DESC
    """
    args: tuple = ()
    if limit is not None:
        sql += " LIMIT ? OFFSET ?"
        args = (limit, max(0, offset))
    return [dict(r) for r in conn.execute(sql, args).fetchall()]


def list_threads_page(conn: sqlite3.Connection, limit: int = THREADS_PAGE, offset: int = 0) -> dict:
    """C-05: 한 페이지 + 다음 페이지 유무. limit+1 행을 읽어 has_more 를 판정한다."""
    rows = list_threads(conn, limit + 1, offset)
    return {"threads": rows[:limit], "has_more": len(rows) > limit, "next_offset": offset + min(len(rows), limit)}
