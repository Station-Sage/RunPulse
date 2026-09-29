"""Phase 7 서비스 레이어 - Coach 스레드 CRUD + AI 호출 래핑.

첫 번째 인자는 sqlite3.Connection. 반환값은 dict/list (snake_case 키).
읽기 전용이 아니다 — Coach는 대화를 저장해야 하므로 D5의 다른 서비스와 달리 쓰기를
포함한다(07-migration-roadmap.md가 명시한 예외, save_checkin과 동일 취급).

AI 응답은 src/ai/chat_engine.chat_result()(엔진 상태 포함)로 생성한다 — v1 /ai-coach와 같은 provider
체인(선택 provider → gemini → groq → rule)이되, coach_consent 동의가 없으면 외부 호출 0회.
여기서 추가한 건 스레드 개념(chat_threads + chat_messages.thread_id, D3)과 엔진 상태 저장뿐이다.

스레드 제목은 규칙 기반(첫 메시지 앞부분 절단)이다 — AI 자동 요약 제목은 범위 밖.

설계 문서: v0.3/data/phase-7-ui-renewal/06-data-layer-extensions.md (D5), 03e-coach.md
"""
from __future__ import annotations

import json
import logging
import sqlite3

log = logging.getLogger(__name__)

_TITLE_MAX_LEN = 30


def build_evidence(conn: sqlite3.Connection) -> list[dict]:
    """오늘 브리핑의 근거를 Coach 답변 근거로 재사용 — 실패하면 빈 리스트."""
    try:
        from src.services.today_service import get_today_briefing
        return get_today_briefing(conn)["evidence"][:5]
    except Exception:
        return []


def _derive_title(message: str) -> str:
    """규칙 기반 스레드 제목 — 첫 메시지 앞부분 절단."""
    text = message.strip().replace("\n", " ")
    if len(text) <= _TITLE_MAX_LEN:
        return text
    return text[:_TITLE_MAX_LEN].rstrip() + "…"


def list_threads(conn: sqlite3.Connection) -> list[dict]:
    """스레드 목록 — 각 스레드의 마지막 메시지 미리보기 포함, 최근 활동순."""
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """
        SELECT
            t.id, t.title, t.created_at, t.updated_at,
            (SELECT content FROM chat_messages m
             WHERE m.thread_id = t.id ORDER BY m.id DESC LIMIT 1) AS last_message,
            (SELECT created_at FROM chat_messages m
             WHERE m.thread_id = t.id ORDER BY m.id DESC LIMIT 1) AS last_message_at
        FROM chat_threads t
        ORDER BY t.updated_at DESC
        """
    ).fetchall()
    return [dict(r) for r in rows]


def _message_view(row: sqlite3.Row) -> dict:
    """chat_messages 행 → API 메시지 dict(evidence·engine·sent_scope 파싱)."""
    from src.services.coach_engine_health import message_engine_view
    msg = dict(row)
    raw = msg.pop("evidence_json", None)
    try:
        msg["evidence"] = json.loads(raw) if raw else []
    except Exception:
        msg["evidence"] = []
    engine_json = msg.pop("engine_json", None)
    scope_raw = msg.pop("sent_scope_json", None)
    try:
        msg["sent_scope"] = json.loads(scope_raw) if scope_raw else None
    except Exception:
        msg["sent_scope"] = None
    if msg["role"] == "assistant":
        msg["engine"] = message_engine_view(engine_json, msg.get("ai_model"))
    return msg


_MESSAGE_COLUMNS = ("id, role, content, ai_model, evidence_json, created_at, status,"
                    " engine_json, as_of, sent_scope_json, thread_id")


def get_thread(conn: sqlite3.Connection, thread_id: int) -> dict | None:
    """스레드 상세 + 전체 메시지 목록. 스레드 없으면 None."""
    conn.row_factory = sqlite3.Row
    thread = conn.execute(
        "SELECT id, title, created_at, updated_at FROM chat_threads WHERE id = ?",
        (thread_id,),
    ).fetchone()
    if not thread:
        return None
    messages = conn.execute(
        f"SELECT {_MESSAGE_COLUMNS} FROM chat_messages WHERE thread_id = ? ORDER BY id",
        (thread_id,),
    ).fetchall()
    return {"thread": dict(thread), "messages": [_message_view(m) for m in messages]}


def _generate(conn: sqlite3.Connection, thread_id: int, user_text: str, config: dict | None):
    """동의 저장소의 설정으로 엔진을 호출한다 — 동의가 없으면 외부 호출 0회(design §4.3)."""
    from src.ai import chat_engine
    from src.services.coach_consent import get_consent
    return chat_engine.chat_result(conn, user_text, config=config, thread_id=thread_id,
                                   consent=get_consent(conn), require_consent=True)


def _store_reply(conn: sqlite3.Connection, thread_id: int, result, message_id: int | None = None) -> dict:
    """assistant 메시지 저장(message_id가 있으면 그 행을 덮어씀 = 다시 생성) 후 API 뷰 반환."""
    evidence = build_evidence(conn)
    values = (
        result.text, result.engine.provider, json.dumps(evidence, ensure_ascii=False) if evidence else None,
        "done", json.dumps(result.engine_dict(), ensure_ascii=False), result.as_of,
        json.dumps(result.sent_scope, ensure_ascii=False) if result.sent_scope is not None else None,
    )
    if message_id is None:
        message_id = conn.execute(
            "INSERT INTO chat_messages (content, ai_model, evidence_json, status, engine_json, as_of,"
            " sent_scope_json, role, thread_id) VALUES (?, ?, ?, ?, ?, ?, ?, 'assistant', ?)",
            (*values, thread_id),
        ).lastrowid
    else:
        conn.execute(
            "UPDATE chat_messages SET content=?, ai_model=?, evidence_json=?, status=?, engine_json=?,"
            " as_of=?, sent_scope_json=?, created_at=datetime('now') WHERE id = ?",
            (*values, message_id),
        )
    conn.execute("UPDATE chat_threads SET updated_at = datetime('now') WHERE id = ?", (thread_id,))
    conn.commit()
    conn.row_factory = sqlite3.Row
    row = conn.execute(f"SELECT {_MESSAGE_COLUMNS} FROM chat_messages WHERE id = ?", (message_id,)).fetchone()
    return _message_view(row)


def create_thread(conn: sqlite3.Connection, initial_message: str, config: dict | None = None) -> dict:
    """새 스레드 생성 — 첫 메시지 저장 → AI 응답 생성·저장 → 스레드+메시지 반환."""
    title = _derive_title(initial_message)
    thread_id = conn.execute("INSERT INTO chat_threads (title) VALUES (?)", (title,)).lastrowid
    conn.execute(
        "INSERT INTO chat_messages (role, content, thread_id) VALUES ('user', ?, ?)",
        (initial_message, thread_id),
    )
    conn.commit()
    message = _store_reply(conn, thread_id, _generate(conn, thread_id, initial_message, config))
    return {"thread": {"id": thread_id, "title": title}, "message": message}


def add_message(
    conn: sqlite3.Connection, thread_id: int, content: str, config: dict | None = None,
) -> dict:
    """기존 스레드에 메시지 추가 — AI 응답 생성·저장 → 응답 메시지 반환."""
    conn.execute(
        "INSERT INTO chat_messages (role, content, thread_id) VALUES ('user', ?, ?)",
        (content, thread_id),
    )
    conn.commit()
    return _store_reply(conn, thread_id, _generate(conn, thread_id, content, config))


def regenerate(conn: sqlite3.Connection, thread_id: int, message_id: int,
               config: dict | None = None) -> dict | None:
    """assistant 메시지를 같은 자리에서 다시 생성(동기, design §7.2). 대상이 없으면 None."""
    row = conn.execute(
        "SELECT id FROM chat_messages WHERE id = ? AND thread_id = ? AND role = 'assistant'",
        (message_id, thread_id),
    ).fetchone()
    if not row:
        return None
    prev = conn.execute(
        "SELECT content FROM chat_messages WHERE thread_id = ? AND id < ? AND role = 'user'"
        " ORDER BY id DESC LIMIT 1", (thread_id, message_id),
    ).fetchone()
    if not prev:
        return None
    return _store_reply(conn, thread_id, _generate(conn, thread_id, prev[0], config), message_id)
