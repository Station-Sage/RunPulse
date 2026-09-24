"""Phase 7 서비스 레이어 - Coach 스레드 CRUD + AI 호출 래핑.

첫 번째 인자는 sqlite3.Connection. 반환값은 dict/list (snake_case 키).
읽기 전용이 아니다 — Coach는 대화를 저장해야 하므로 D5의 다른 서비스와 달리 쓰기를
포함한다(07-migration-roadmap.md가 명시한 예외, save_checkin과 동일 취급).

AI 응답 생성 자체는 새로 만들지 않는다 — 기존 src/ai/chat_engine.chat()을 그대로
사용한다(provider 체인 fallback: 선택 provider → gemini → groq → rule, 이미 구현·
운영 중인 v1 /ai-coach와 동일 엔진). 여기서 추가한 건 스레드 개념(chat_threads +
chat_messages.thread_id, D3)뿐 — chat_engine.chat()의 thread_id 파라미터로 연결한다.

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
        "SELECT id, role, content, ai_model, evidence_json, created_at FROM chat_messages"
        " WHERE thread_id = ? ORDER BY id",
        (thread_id,),
    ).fetchall()
    result_messages = []
    for m in messages:
        msg = dict(m)
        raw = msg.pop("evidence_json", None)
        try:
            msg["evidence"] = json.loads(raw) if raw else []
        except Exception:
            msg["evidence"] = []
        result_messages.append(msg)
    return {"thread": dict(thread), "messages": result_messages}


def create_thread(conn: sqlite3.Connection, initial_message: str, config: dict | None = None) -> dict:
    """새 스레드 생성 — 첫 메시지 저장 → AI 응답 생성·저장 → 스레드+메시지 반환."""
    from src.ai.chat_engine import chat as ai_chat

    title = _derive_title(initial_message)
    thread_id = conn.execute(
        "INSERT INTO chat_threads (title) VALUES (?)", (title,)
    ).lastrowid

    conn.execute(
        "INSERT INTO chat_messages (role, content, thread_id) VALUES ('user', ?, ?)",
        (initial_message, thread_id),
    )
    conn.commit()

    response_text, provider = ai_chat(conn, initial_message, config=config, thread_id=thread_id)

    evidence = build_evidence(conn)
    evidence_json = json.dumps(evidence, ensure_ascii=False) if evidence else None
    message_id = conn.execute(
        "INSERT INTO chat_messages (role, content, thread_id, ai_model, evidence_json) "
        "VALUES ('assistant', ?, ?, ?, ?)",
        (response_text, thread_id, provider, evidence_json),
    ).lastrowid
    conn.execute(
        "UPDATE chat_threads SET updated_at = datetime('now') WHERE id = ?", (thread_id,)
    )
    conn.commit()

    return {
        "thread": {"id": thread_id, "title": title},
        "message": {
            "id": message_id, "role": "assistant", "content": response_text,
            "ai_model": provider, "thread_id": thread_id,
            "evidence": evidence,
        },
    }


def add_message(
    conn: sqlite3.Connection, thread_id: int, content: str, config: dict | None = None,
) -> dict:
    """기존 스레드에 메시지 추가 — AI 응답 생성·저장 → 응답 메시지 반환."""
    from src.ai.chat_engine import chat as ai_chat

    conn.execute(
        "INSERT INTO chat_messages (role, content, thread_id) VALUES ('user', ?, ?)",
        (content, thread_id),
    )
    conn.commit()

    response_text, provider = ai_chat(conn, content, config=config, thread_id=thread_id)

    evidence = build_evidence(conn)
    evidence_json = json.dumps(evidence, ensure_ascii=False) if evidence else None
    message_id = conn.execute(
        "INSERT INTO chat_messages (role, content, thread_id, ai_model, evidence_json) "
        "VALUES ('assistant', ?, ?, ?, ?)",
        (response_text, thread_id, provider, evidence_json),
    ).lastrowid
    conn.execute(
        "UPDATE chat_threads SET updated_at = datetime('now') WHERE id = ?", (thread_id,)
    )
    conn.commit()

    return {
        "id": message_id, "role": "assistant", "content": response_text,
        "ai_model": provider, "thread_id": thread_id,
        "evidence": evidence,
    }
