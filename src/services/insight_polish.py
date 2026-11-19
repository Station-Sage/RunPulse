"""능동 인사이트 문장 다듬기 (V2-REPAIR D4, ADR-059 2단계) — 규칙 템플릿 문장을 LLM 으로 1~2문장 다듬는다.

사건 발생 판정은 규칙이 하고 LLM 은 문장만 바꾼다. coach 동의(`ai_wording._consent_ok`)가 있을 때만 다듬고(없으면
규칙 문장만, AI 호출 없음), 비건강 근거 신호·같은 날 계산 지표(`insight_evidence`)를 facts 로 함께 보내
"어떤 신호가 기준을 넘었는지"를 말하게 한다(바꿔 말하기 방지).
프롬프트·검증은 공통 계층(`ai_wording` 기본 템플릿·validate — 숫자 ⊆ 원문+facts, 건강 용어 금지)을 쓴다.
LLM 이 없거나·예산 거부·검증 실패면 규칙 문장을 그대로 쓴다(저장 안 함). 결과는 text_ai/text_src 에 저장하고,
text_src(원문+facts 해시)가 현재 값과 다르면 자동으로 무효가 된다.
"""
from __future__ import annotations

import json
import logging
import sqlite3
import threading
from pathlib import Path

from src.services import ai_wording as aw
from src.services import insight_evidence as ev

log = logging.getLogger(__name__)

_TEMPLATE = Path(__file__).resolve().parents[1] / "ai" / "prompt_templates" / "insight_polish.txt"
_MAX_LEN = 120
_GUIDE = (
    "- 능동 인사이트 알림 문장입니다. facts 는 알림을 만든 근거 신호(acwr 부하비·crs_level/crs_gate 회복 게이트·"
    "fatigue_checkin 피로 체크인·sync_gap_days)와 같은 날 계산 지표(ctl·atl·tsb·utrs·cirs)입니다.\n"
    "- 어떤 신호가 기준을 넘었는지·무엇이 함께 낮거나 높은지를 facts 로 짚고, 원문의 권장 행동을 유지합니다."
)
SURFACE = aw.register(aw.Surface(name="insight", guide=_GUIDE, max_chars=_MAX_LEN, needs_consent=False))
_OPEN_SQL = ("SELECT id, kind, as_of, signals_json, text, text_src FROM insight_events"
             " WHERE state IN ('open','seen')")


def validate(src: str, out: str | None) -> str | None:
    """다듬은 문장이 안전하면 정리해 반환, 아니면 None(→ 규칙 문장 유지). src 는 원문(+facts JSON)."""
    return aw.validate(SURFACE, src, out)


def polish_text(text: str, config: dict | None, caller=None) -> str | None:
    """규칙 문장 → 다듬은 문장(실패 시 None, facts 없음). caller(prompt)->str|None 은 테스트용 주입."""
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


def _payload(eid: int, text: str, facts: dict) -> dict:
    return {"id": str(eid), "text": aw.redact_health_text(text), **({"facts": facts} if facts else {})}


def _polish_batch_queue(conn: sqlite3.Connection, config: dict | None, rows: list[tuple]) -> int | None:
    """claude_queue 가 가용하면 사건 전체를 job 1건으로 다듬는다. 큐 불가·실패면 None(→ 기존 경로).

    rows: (id, text, facts, key). 저장 키는 key(원문+facts 해시).
    """
    from src.ai import provider_claude_queue as pcq
    if not pcq.available(conn, config):
        return None
    payloads = {str(r[0]): _payload(r[0], r[1], r[2]) for r in rows}
    out = pcq.try_complete(conn, config, kind="insight_polish", prompt=aw.build_prompt(SURFACE, list(payloads.values())))
    if not out:
        return None
    done = 0
    by_id = {str(r[0]): r for r in rows}
    for it in parse_batch(out):
        r = by_id.get(str(it.get("id")))
        if r is None:
            continue
        basis = json.dumps({k: v for k, v in payloads[str(r[0])].items() if k != "id"}, ensure_ascii=False, default=str)
        if t := validate(basis, it.get("text")):
            conn.execute("UPDATE insight_events SET text_ai=?, text_src=? WHERE id=?", (t, r[3], r[0]))
            done += 1
    conn.commit()
    return done


def parse_batch(out: str) -> list[dict]:
    """응답에서 JSON 배열을 꺼낸다(코드펜스 허용). 실패는 빈 리스트."""
    return aw.parse_items(out)


def pending(conn: sqlite3.Connection) -> list[tuple]:
    """다듬을 열린 사건 (id, text, facts, key) — 저장 키가 현재 원문+facts 와 다른 것만."""
    out = []
    for eid, kind, as_of, sig, text, src in conn.execute(_OPEN_SQL).fetchall():
        facts = ev.evidence_facts(conn, kind, json.loads(sig or "[]"), as_of)
        key = ev.polish_key(text, facts)
        if src != key:
            out.append((eid, text, facts, key))
    return out


def polish_open_events(conn: sqlite3.Connection, config: dict | None, caller=None) -> int:
    """열린 사건 중 아직 다듬지 않은 것만 처리하고 성공 건수를 반환한다. 실패는 삼킨다."""
    done = 0
    if not ev.facts_enabled(conn):
        return 0   # 동의 없음 → AI 호출 없이 규칙 문장(사용자 결정 2026-11-19)
    rows = pending(conn)
    if rows and caller is None:
        batched = _polish_batch_queue(conn, config, rows)
        if batched is not None:
            return batched
    for eid, text, facts, key in rows:
        if facts:
            continue   # 근거 포함 다듬기는 큐 전용 — 키 기반 체인(facts 미전달)으로 만든 문장은 키가 맞지 않는다
        try:
            out = polish_text(text, config, caller)
        except Exception:  # noqa: BLE001
            log.warning("insight polish failed", exc_info=True)
            break
        if out:
            conn.execute("UPDATE insight_events SET text_ai=?, text_src=? WHERE id=?", (out, key, eid))
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
