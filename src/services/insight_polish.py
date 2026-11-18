"""능동 인사이트 문장 다듬기 (V2-REPAIR D4) — 규칙 템플릿 문장을 LLM 으로 1~2문장 다듬는다.

사건 발생 판정은 규칙이 하고 LLM 은 문장만 바꾼다. LLM 이 없거나(provider 없음)·예산 거부·응답이 검증을
통과하지 못하면 규칙 문장을 그대로 쓴다(저장 안 함). 결과는 text_ai/text_src 에 저장하고, 규칙 문장이
바뀌면(text != text_src) 자동으로 무효가 된다.
"""
from __future__ import annotations

import json
import logging
import re
import sqlite3
import threading
from pathlib import Path

log = logging.getLogger(__name__)

_TEMPLATE = Path(__file__).resolve().parents[1] / "ai" / "prompt_templates" / "insight_polish.txt"
_TEMPLATE_BATCH = _TEMPLATE.with_name("insight_polish_batch.txt")
_MAX_LEN = 120
_NUM = re.compile(r"\d+(?:\.\d+)?")


def validate(src: str, out: str | None) -> str | None:
    """다듬은 문장이 안전하면 정리해 반환, 아니면 None(→ 규칙 문장 유지)."""
    if not out:
        return None
    t = out.strip().strip("\"'“”`")
    if not t or "\n\n" in t or len(t) > _MAX_LEN or t.startswith(("#", "-", "*", "[")):
        return None
    if not set(_NUM.findall(t)) <= set(_NUM.findall(src)):
        return None
    return t


def polish_text(text: str, config: dict | None, caller=None) -> str | None:
    """규칙 문장 → 다듬은 문장(실패 시 None). caller(prompt)->str|None 은 테스트용 주입."""
    prompt = _TEMPLATE.read_text(encoding="utf-8").replace("{{TEXT}}", text)
    if caller is not None:
        return validate(text, caller(prompt))
    from src.ai import llm_budget
    from src.ai.chat_engine import _build_chat_provider_chain, _call_provider, get_ai_provider
    chain = _build_chat_provider_chain(get_ai_provider(config), config)
    if not chain:
        return None
    with llm_budget.ensure_scope("insight_polish") as sc:
        for prov in chain:
            out = _call_provider(prov, prompt, config)
            if out:
                return validate(text, out)
            if sc.refused:
                break
    return None


def _polish_batch_queue(conn: sqlite3.Connection, config: dict | None, rows: list) -> int | None:
    """claude_queue 가 가용하면 사건 전체를 job 1건(polish_v1)으로 다듬는다. 큐 불가·실패면 None(→ 기존 경로)."""
    from src.ai import provider_claude_queue as pcq
    if not pcq.available(conn, config):
        return None
    items = [{"id": r[0], "text": r[1]} for r in rows]
    prompt = _TEMPLATE_BATCH.read_text(encoding="utf-8").replace(
        "{{ITEMS}}", json.dumps(items, ensure_ascii=False))
    out = pcq.try_complete(conn, config, kind="insight_polish", prompt=prompt)
    if not out:
        return None
    done = 0
    src = {r[0]: r[1] for r in rows}
    for it in parse_batch(out):
        eid = it.get("id")
        if eid in src and (t := validate(src[eid], it.get("text"))):
            conn.execute("UPDATE insight_events SET text_ai=?, text_src=? WHERE id=?", (t, src[eid], eid))
            done += 1
    conn.commit()
    return done


def parse_batch(out: str) -> list[dict]:
    """응답에서 JSON 배열을 꺼낸다(코드펜스 허용). 실패는 빈 리스트."""
    m = re.search(r"\[.*\]", out, re.S)
    try:
        data = json.loads(m.group(0)) if m else []
    except ValueError:
        return []
    return [d for d in data if isinstance(d, dict)] if isinstance(data, list) else []


def polish_open_events(conn: sqlite3.Connection, config: dict | None, caller=None) -> int:
    """열린 사건 중 아직 다듬지 않은 것만 처리하고 성공 건수를 반환한다. 실패는 삼킨다."""
    done = 0
    rows = conn.execute("SELECT id, text FROM insight_events WHERE state IN ('open','seen') "
                        "AND (text_src IS NULL OR text_src != text)").fetchall()
    if rows and caller is None:
        batched = _polish_batch_queue(conn, config, rows)
        if batched is not None:
            return batched
    for eid, text in rows:
        try:
            out = polish_text(text, config, caller)
        except Exception:  # noqa: BLE001
            log.warning("insight polish failed", exc_info=True)
            break
        if out:
            conn.execute("UPDATE insight_events SET text_ai=?, text_src=? WHERE id=?", (out, text, eid))
            done += 1
    conn.commit()
    return done


def polish_in_background(db_path: str, config: dict | None) -> None:
    """동기화 경로를 막지 않도록 별도 스레드·별도 연결로 다듬는다. 예외는 전파하지 않는다."""
    def _run() -> None:
        try:
            with sqlite3.connect(db_path, timeout=30) as c:
                polish_open_events(c, config)
        except Exception:  # noqa: BLE001
            log.warning("insight polish thread failed", exc_info=True)
    threading.Thread(target=_run, daemon=True, name="insight-polish").start()
