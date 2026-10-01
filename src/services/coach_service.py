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
from datetime import date

log = logging.getLogger(__name__)

_TITLE_MAX_LEN = 30
PENDING_STATUSES = ("pending", "working")


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


def _asked_chips(conn: sqlite3.Connection, thread_id: int) -> set[str]:
    return {r[0] for r in conn.execute(
        "SELECT chip_id FROM chat_messages WHERE thread_id = ? AND role = 'user' AND chip_id IS NOT NULL",
        (thread_id,))}


def _followup_views(raw_engine: str | None, asked: set[str], followups_json: str | None = None) -> list[dict]:
    """서버가 제공한 후속 칩(chip_id) 중 이미 물어본 것을 뺀 최대 3개 — 프런트는 이 목록만 그린다.

    followups_json(v24 컬럼)이 우선이고, 없으면 옛 방식대로 engine_json["followups"]를 쓴다.
    """
    from src.ai.coach_rule_types import chip_view
    from src.services.coach_engine_health import parse_engine
    try:
        ids = json.loads(followups_json) if followups_json else None
    except Exception:
        ids = None
    if ids is None:
        ids = (parse_engine(raw_engine) or {}).get("followups") or []
    return [chip_view(c) for c in ids if c not in asked][:3]


def _message_view(conn: sqlite3.Connection, row: sqlite3.Row, asked: set[str] | None = None) -> dict:
    """chat_messages 행 → API 메시지 dict(evidence·engine·sent_scope·followups 파싱)."""
    from src.services.coach_engine_health import message_engine_view
    from src.services.coach_evidence import view_evidence
    msg = dict(row)
    raw = msg.pop("evidence_json", None)
    try:
        msg["evidence"] = json.loads(raw) if raw else []
    except Exception:
        msg["evidence"] = []
    engine_json = msg.pop("engine_json", None)
    followups_json = msg.pop("followups_json", None)
    msg["followups"] = (_followup_views(engine_json, asked if asked is not None else _asked_chips(
        conn, msg["thread_id"]), followups_json) if msg["role"] == "assistant" else [])
    scope_raw = msg.pop("sent_scope_json", None)
    try:
        msg["sent_scope"] = json.loads(scope_raw) if scope_raw else None
    except Exception:
        msg["sent_scope"] = None
    if msg["role"] == "assistant":
        msg["engine"] = message_engine_view(engine_json, msg.get("ai_model"))
        view_evidence(conn, msg)
        if msg.get("status") in PENDING_STATUSES:
            msg["stream_url"] = f"/api/v1/coach/messages/{msg['id']}/stream"
    return msg


_MESSAGE_COLUMNS = ("id, role, content, ai_model, evidence_json, created_at, status,"
                    " engine_json, as_of, sent_scope_json, thread_id, chip_id,"
                    " client_msg_id, parent_message_id, followups_json")


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
        f"SELECT {_MESSAGE_COLUMNS} FROM chat_messages m WHERE thread_id = ? AND NOT ("
        " role = 'assistant' AND EXISTS (SELECT 1 FROM chat_messages c WHERE c.parent_message_id = m.id"
        " AND c.role = 'assistant' AND c.status NOT IN ('error', 'cancelled'))) ORDER BY id",
        (thread_id,),
    ).fetchall()
    asked = _asked_chips(conn, thread_id)
    return {"thread": dict(thread), "messages": [_message_view(conn, m, asked) for m in messages]}


def _generate(conn: sqlite3.Connection, thread_id: int, user_text: str, config: dict | None,
              chip_id: str | None = None, on_event=None, cancelled=None):
    """동의 저장소의 설정으로 엔진을 호출한다 — 동의가 없으면 외부 호출 0회(design §4.3)."""
    from src.ai import chat_engine
    from src.services.coach_consent import get_consent
    return chat_engine.chat_result(conn, user_text, config=config, chip_id=chip_id, thread_id=thread_id,
                                   consent=get_consent(conn), require_consent=True,
                                   on_event=on_event, cancelled=cancelled)


def _row_view(conn: sqlite3.Connection, message_id: int) -> dict:
    conn.row_factory = sqlite3.Row
    row = conn.execute(f"SELECT {_MESSAGE_COLUMNS} FROM chat_messages WHERE id = ?", (message_id,)).fetchone()
    return _message_view(conn, row)


def _store_reply(conn: sqlite3.Connection, thread_id: int, result, message_id: int,
                 status: str = "done") -> dict:
    """pending assistant 행(message_id)을 완성 답변으로 채우고 API 뷰를 반환한다."""
    from src.services.coach_evidence import build_answer_evidence
    evidence = result.evidence or build_answer_evidence(
        conn, result.text, llm=result.engine.status == "ok", as_of=result.as_of or date.today().isoformat())
    engine = {**result.engine_dict(), "followups": list(result.followups)}
    conn.execute(
        "UPDATE chat_messages SET content=?, ai_model=?, evidence_json=?, status=?, engine_json=?,"
        " as_of=?, sent_scope_json=?, followups_json=?, created_at=datetime('now') WHERE id = ?",
        (result.text, result.engine.provider, json.dumps(evidence, ensure_ascii=False) if evidence else None,
         status, json.dumps(engine, ensure_ascii=False), result.as_of,
         json.dumps(result.sent_scope, ensure_ascii=False) if result.sent_scope is not None else None,
         json.dumps(list(result.followups)), message_id),
    )
    conn.execute("UPDATE chat_threads SET updated_at = datetime('now') WHERE id = ?", (thread_id,))
    conn.commit()
    return _row_view(conn, message_id)


def _resolve_text(message: str | None, chip_id: str | None) -> str:
    """칩을 누르면 본문이 없어도 칩 문구가 사용자 말풍선이 된다."""
    from src.ai.coach_rule_types import CHIP_TEXT
    return (message or "").strip() or CHIP_TEXT.get(chip_id or "", "")


def _insert_user(conn: sqlite3.Connection, thread_id: int, text: str, chip_id: str | None,
                 client_msg_id: str | None = None) -> int:
    mid = conn.execute(
        "INSERT INTO chat_messages (role, content, thread_id, chip_id, client_msg_id) VALUES ('user', ?, ?, ?, ?)",
        (text, thread_id, chip_id, client_msg_id)).lastrowid
    conn.commit()
    return mid


def _insert_pending(conn: sqlite3.Connection, thread_id: int, parent_id: int | None = None) -> int:
    """비어 있는 assistant 행(status=pending) — 답변이 만들어지면 _store_reply가 채운다."""
    mid = conn.execute(
        "INSERT INTO chat_messages (role, content, thread_id, status, parent_message_id)"
        " VALUES ('assistant', '', ?, 'pending', ?)", (thread_id, parent_id)).lastrowid
    conn.commit()
    return mid


def _existing_send(conn: sqlite3.Connection, thread_id: int, client_msg_id: str | None) -> dict | None:
    """같은 client_msg_id로 이미 보낸 메시지가 있으면 그 사용자·assistant 행을 돌려준다(재전송 멱등)."""
    if not client_msg_id:
        return None
    row = conn.execute("SELECT id FROM chat_messages WHERE thread_id = ? AND client_msg_id = ?",
                       (thread_id, client_msg_id)).fetchone()
    if not row:
        return None
    reply = conn.execute("SELECT id FROM chat_messages WHERE thread_id = ? AND role = 'assistant'"
                         " AND parent_message_id = ? ORDER BY id LIMIT 1", (thread_id, row[0])).fetchone()
    return {"user_message": _row_view(conn, row[0]),
            "assistant_message": _row_view(conn, reply[0]) if reply else None, "created": False}


def _send(conn: sqlite3.Connection, thread_id: int, text: str, chip_id: str | None,
          client_msg_id: str | None) -> dict:
    uid = _insert_user(conn, thread_id, text, chip_id, client_msg_id)
    aid = _insert_pending(conn, thread_id, uid)
    conn.execute("UPDATE chat_threads SET updated_at = datetime('now') WHERE id = ?", (thread_id,))
    conn.commit()
    return {"user_message": _row_view(conn, uid), "assistant_message": _row_view(conn, aid), "created": True}


def create_thread(conn: sqlite3.Connection, initial_message: str | None, config: dict | None = None,
                  chip_id: str | None = None, client_msg_id: str | None = None,
                  context: dict | None = None) -> dict:
    """새 스레드 + 첫 사용자 메시지 + pending assistant 행을 즉시 만든다(답변 생성은 generate_reply).

    client_msg_id가 이미 있으면(새 스레드의 첫 메시지 재전송) 새로 만들지 않고 기존 행을 돌려준다.
    """
    text = _resolve_text(initial_message, chip_id)
    if client_msg_id:
        dup = conn.execute("SELECT thread_id FROM chat_messages WHERE client_msg_id = ? AND role = 'user'"
                           " ORDER BY id LIMIT 1", (client_msg_id,)).fetchone()
        if dup:
            found = _existing_send(conn, dup[0], client_msg_id)
            return {"thread": _thread_view(conn, dup[0]), **found}
    title = _derive_title(text)
    ctx = context or {}
    thread_id = conn.execute(
        "INSERT INTO chat_threads (title, context_kind, context_ref) VALUES (?, ?, ?)",
        (title, ctx.get("kind"), ctx.get("ref"))).lastrowid
    conn.commit()
    return {"thread": _thread_view(conn, thread_id), **_send(conn, thread_id, text, chip_id, client_msg_id)}


def _thread_view(conn: sqlite3.Connection, thread_id: int) -> dict:
    row = conn.execute("SELECT title, context_kind, context_ref FROM chat_threads WHERE id = ?",
                       (thread_id,)).fetchone()
    ctx = {"kind": row[1], "ref": row[2]} if row and row[1] else None
    return {"id": thread_id, "title": row[0] if row else None, "context": ctx}


def add_message(
    conn: sqlite3.Connection, thread_id: int, content: str | None, config: dict | None = None,
    chip_id: str | None = None, client_msg_id: str | None = None,
) -> dict:
    """기존 스레드에 사용자 메시지 + pending assistant 행을 즉시 추가한다(답변 생성은 generate_reply)."""
    dup = _existing_send(conn, thread_id, client_msg_id)
    if dup:
        return dup
    return _send(conn, thread_id, _resolve_text(content, chip_id), chip_id, client_msg_id)


def generate_reply(conn: sqlite3.Connection, thread_id: int, assistant_id: int, user_text: str,
                   config: dict | None = None, chip_id: str | None = None, on_event=None,
                   cancelled=None) -> dict:
    """pending assistant 행의 답변을 동기적으로 생성·저장한다. status: done | fallback | cancelled | error."""
    conn.execute("UPDATE chat_messages SET status = 'working' WHERE id = ? AND status = 'pending'", (assistant_id,))
    conn.commit()
    try:
        result = _generate(conn, thread_id, user_text, config, chip_id, on_event, cancelled)
    except Exception as exc:
        log.warning("coach 답변 생성 실패 thread=%s: %s", thread_id, exc, exc_info=True)
        conn.execute("UPDATE chat_messages SET status = 'error', content = '' WHERE id = ?", (assistant_id,))
        conn.commit()
        return _row_view(conn, assistant_id)
    if cancelled and cancelled():
        status = "cancelled"
    else:
        status = "fallback" if result.engine.status == "fallback" else "done"
    return _store_reply(conn, thread_id, result, assistant_id, status)


def get_message(conn: sqlite3.Connection, message_id: int) -> dict | None:
    """메시지 한 건의 API 뷰(폴링·스트림 복원용). 없으면 None."""
    if conn.execute("SELECT 1 FROM chat_messages WHERE id = ?", (message_id,)).fetchone() is None:
        return None
    return _row_view(conn, message_id)


def regenerate(conn: sqlite3.Connection, thread_id: int, message_id: int,
               config: dict | None = None) -> dict | None:
    """assistant 메시지를 다시 생성한다 — 새 pending 행(parent=기존 답변)을 만들어 돌려준다(design §7.2).

    기존 행은 보존하고(실패·중단 답변 포함), get_thread는 성공한 후속 행이 있으면 부모를 숨긴다.
    대상이 없으면 None.
    """
    row = conn.execute(
        "SELECT id FROM chat_messages WHERE id = ? AND thread_id = ? AND role = 'assistant'",
        (message_id, thread_id),
    ).fetchone()
    if not row:
        return None
    prev = conn.execute(
        "SELECT content, chip_id FROM chat_messages WHERE thread_id = ? AND id < ? AND role = 'user'"
        " ORDER BY id DESC LIMIT 1", (thread_id, message_id),
    ).fetchone()
    if not prev:
        return None
    return _row_view(conn, _insert_pending(conn, thread_id, message_id))
