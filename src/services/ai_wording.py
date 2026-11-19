"""규칙 문구 AI 다듬기 공통 계층 (ADR-059) — 표면(surface)을 선언하면 캐시 조회·백그라운드 생성·검증·건강 익명화를 공통으로 쓴다.

원칙: 규칙 문구가 기본값이다. 요청 스레드는 `get_cached`/`present` 로 캐시만 읽고(큐를 기다리지 않음), 생성은 `warm`
(백그라운드)에서 동의·큐 가용·전역 사용량·uid 락을 통과할 때만 haiku 큐(job kind 'insight_polish' 재사용)로 한다.
결과는 ai_outputs(kind='w:<표면>', scope_key, src_hash) 에 저장하고, 항목이 선언한 근거(basis, 반올림 —
`ai_wording_basis`)·지침이 바뀌면 src_hash 가 달라져 자동으로 규칙 문구로 돌아간다. 검증 실패(숫자 ⊆ 근거, 길이, 금지어, 마크다운)는 저장하지 않는다.
건강 정보(질병·부상·통증·부위)는 AI 로 보내기 전 '몸 상태 이상 신호' 로 일반화한다(ADR-057/058).
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
import sqlite3
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

log = logging.getLogger(__name__)

_TEMPLATE_DIR = Path(__file__).resolve().parents[1] / "ai" / "prompt_templates"
BASE_TEMPLATE = "wording_base.txt"
KIND_PREFIX = "w:"
GENERIC_HEALTH = "몸 상태 이상 신호가 있어요."
# 질병·부상·통증·진단·부위 — 원문에 있으면 문장 단위로 일반화하고, AI 출력에 나오면 거부한다.
HEALTH_TERMS = ("감기", "독감", "코로나", "몸살", "발열", "열이", "고열", "질병", "질환", "병원", "진단", "처방", "약을",
                "통증", "아파", "아프", "아픔", "부상", "다쳤", "다친", "염증", "골절", "염좌", "근육통", "부위",
                "무릎", "발목", "종아리", "햄스트링", "허리", "고관절", "아킬레스", "발바닥", "족저", "정강이", "허벅지")
_HEALTH_RE = re.compile("|".join(map(re.escape, HEALTH_TERMS)))
_NUM = re.compile(r"\d+(?:\.\d+)?")
_SENT = re.compile(r"(?<=[.!?。])\s+")


@dataclass(frozen=True)
class Surface:
    """AI 다듬기 표면 선언. guide 는 표면별 지침(기본 템플릿의 {{GUIDE}}), template 을 주면 그 파일을 쓴다."""
    name: str
    guide: str
    max_chars: int = 160
    forbidden: tuple[str, ...] = ()
    needs_consent: bool = True      # 사용자 데이터가 들어가면 True(정적 문구만이면 False)
    model: str = "haiku"
    job_kind: str = "insight_polish"  # 기존 haiku 큐 kind 재사용(새 kind 는 AI_JOB_KINDS·DEADLINE 갱신 필요)
    version: str = "v1"             # 올리면 기존 캐시 무효
    template: str = BASE_TEMPLATE
    chunk: int = 20
    redact: Callable[[str], str] | None = None   # 추가 익명화(기본 건강 익명화 뒤에 적용)

    @property
    def kind(self) -> str:
        return KIND_PREFIX + self.name


@dataclass(frozen=True)
class Item:
    """다듬을 한 건. facts 는 AI 가 인용해도 되는 추가 근거(평면 dict, 민감 메모 금지).

    basis 는 재생성 기준(해시 전용, AI 로 보내지 않음). None 이면 `ai_wording_basis.default_basis(rule_text, facts)`
    (반올림 facts + facts 로 설명되지 않는 규칙 숫자). 스냅샷형 표면은 자기 데이터만 담은 basis 를 직접 준다.
    """
    scope_key: str
    rule_text: str
    facts: dict = field(default_factory=dict)
    basis: dict | None = None


_REGISTRY: dict[str, Surface] = {}
_locks: dict[str, threading.Lock] = {}
_locks_guard = threading.Lock()


def register(surface: Surface) -> Surface:
    """표면 등록(모듈 import 시 1회). 같은 이름을 다른 정의로 다시 등록하면 ValueError."""
    old = _REGISTRY.get(surface.name)
    if old is not None and old != surface:
        raise ValueError(f"wording surface already registered: {surface.name}")
    if not (_TEMPLATE_DIR / surface.template).is_file():
        raise ValueError(f"wording template missing: {surface.template}")
    _REGISTRY[surface.name] = surface
    return surface


def get_surface(name: str) -> Surface:
    return _REGISTRY[name]


# ── 건강 익명화·검증 ────────────────────────────────────────────────────────────

def redact_health_text(text: str) -> str:
    """건강 용어가 든 문장을 통째로 일반 문구로 바꾼다(연속 중복은 한 번만)."""
    if not text or not _HEALTH_RE.search(text):
        return text
    out: list[str] = []
    for s in _SENT.split(text.strip()):
        s = GENERIC_HEALTH if _HEALTH_RE.search(s) else s
        if not (out and out[-1] == s == GENERIC_HEALTH):
            out.append(s)
    return " ".join(out)


def _redact_facts(facts: dict) -> dict:
    """문자열 값의 건강 용어는 일반 문구로. 키는 그대로(키는 코드가 정한다)."""
    return {k: (redact_health_text(v) if isinstance(v, str) else v) for k, v in facts.items()}


def _norm(n: str) -> str:
    return n.rstrip("0").rstrip(".") if "." in n else str(int(n))


def numbers_ok(source: str, out: str) -> bool:
    """out 의 모든 숫자가 source 숫자(또는 그 반올림 0·1자리)인지. 12.35 → 12.4·12 허용, 새 숫자는 거부."""
    allowed: set[str] = set()
    for n in _NUM.findall(source or ""):
        allowed.add(_norm(n))
        if "." in n:
            f = float(n)
            allowed |= {_norm(f"{f:.1f}"), str(int(round(f)))}
    return all(_norm(n) in allowed for n in _NUM.findall(out or ""))


def validate(surface: Surface, source: str, out: str | None) -> str | None:
    """안전한 다듬은 문장이면 정리해 반환, 아니면 None(→ 규칙 문구)."""
    if not isinstance(out, str):
        return None
    t = out.strip().strip("\"'“”`")
    if not t or "\n\n" in t or len(t) > surface.max_chars or t.startswith(("#", "-", "*", "[")) or "**" in t:
        return None
    if _HEALTH_RE.search(t) or any(w in t for w in surface.forbidden):
        return None
    return t if numbers_ok(source, t) else None


# ── 캐시(요청 스레드) ───────────────────────────────────────────────────────────

def _payload(surface: Surface, item: Item) -> dict:
    """AI 로 보내는 한 건(익명화 적용) — 해시·검증 근거도 이 값으로 계산한다."""
    text = redact_health_text(item.rule_text)
    facts = _redact_facts(item.facts or {})
    if surface.redact is not None:
        text = surface.redact(text)
        facts = {k: (surface.redact(v) if isinstance(v, str) else v) for k, v in facts.items()}
    return {"id": item.scope_key, "text": text, **({"facts": facts} if facts else {})}


def src_hash(surface: Surface, item: Item) -> str:
    """지침·버전과 항목이 선언한 근거(basis, 반올림)가 바뀔 때만 달라진다(D15). 미세 수치 변화는 같은 해시."""
    from src.services.ai_wording_basis import default_basis
    basis = item.basis if item.basis is not None else default_basis(item.rule_text, item.facts)
    blob = json.dumps([surface.version, surface.guide, surface.max_chars, basis],
                      sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha1(blob.encode("utf-8")).hexdigest()[:16]


def _fresh_body(conn: sqlite3.Connection, surface: Surface, item: Item) -> dict | None:
    """src_hash 가 일치하는 저장 본문(dict) 또는 None."""
    try:
        r = conn.execute("SELECT src_hash, body_json FROM ai_outputs WHERE kind=? AND scope_key=?",
                         (surface.kind, item.scope_key)).fetchone()
    except sqlite3.Error:
        return None
    if not r or r[0] != src_hash(surface, item):
        return None
    try:
        body = json.loads(r[1])
    except ValueError:
        return None
    return body if isinstance(body, dict) else None


def is_fresh(conn: sqlite3.Connection, surface: Surface, item: Item) -> bool:
    """이 항목의 저장 결과(AI 문구 또는 '원문 유지')가 src_hash 와 맞는지 — 참이면 다시 생성할 필요가 없다."""
    return _fresh_body(conn, surface, item) is not None


def get_cached(conn: sqlite3.Connection, surface: Surface, scope_key: str, rule_text: str,
               facts: dict | None = None, basis: dict | None = None) -> str | None:
    """src_hash 가 일치하는 AI 문구만 반환, 없거나 낡았거나 '원문 유지'면 None. 큐·LLM 을 부르지 않는다."""
    body = _fresh_body(conn, surface, Item(scope_key, rule_text, facts or {}, basis))
    return (body or {}).get("text") or None


def present(conn: sqlite3.Connection | None, surface: Surface, scope_key: str, rule_text: str,
            facts: dict | None = None, basis: dict | None = None) -> dict:
    """화면 응답용 {text, source:'ai'|'rule'} — 캐시가 맞으면 AI 문구, 아니면 규칙 문구."""
    ai = get_cached(conn, surface, scope_key, rule_text, facts, basis) if conn is not None and rule_text else None
    return {"text": ai, "source": "ai"} if ai else {"text": rule_text, "source": "rule"}


# ── 생성(백그라운드) ───────────────────────────────────────────────────────────

def _consent_ok(conn: sqlite3.Connection) -> bool:
    """코치 LLM 전송에 어떤 제공자로든 동의했는지(사용자 결정 2026-11-20). 실제 호출은 큐로만 나간다."""
    try:
        from src.services import coach_consent
        c = coach_consent.get_consent(conn)
    except sqlite3.Error:
        return False
    return bool(c) and bool(c.get("provider"))


def gate(conn: sqlite3.Connection, config: dict | None, surface: Surface) -> str | None:
    """생성 차단 사유(no_consent|capped|unavailable) 또는 None(진행 가능)."""
    from src.ai import llm_budget
    from src.ai import provider_claude_queue as pcq
    if surface.needs_consent and not _consent_ok(conn):
        return "no_consent"
    if llm_budget.global_ratio() >= llm_budget.limits()["warm_stop_ratio"]:
        return "capped"
    if not pcq.available(conn, config):
        return "unavailable"
    return None


def build_prompt(surface: Surface, payloads: list[dict]) -> str:
    tpl = (_TEMPLATE_DIR / surface.template).read_text(encoding="utf-8")
    return (tpl.replace("{{GUIDE}}", surface.guide).replace("{{MAX}}", str(surface.max_chars))
            .replace("{{ITEMS}}", json.dumps(payloads, ensure_ascii=False, default=str)))


def parse_items(out: str | None) -> list[dict]:
    """응답에서 JSON 배열을 꺼낸다(코드펜스 허용). 실패는 빈 리스트."""
    m = re.search(r"\[.*\]", out or "", re.S)
    try:
        data = json.loads(m.group(0)) if m else []
    except ValueError:
        return []
    return [d for d in data if isinstance(d, dict)] if isinstance(data, list) else []


def _lock_for(conn: sqlite3.Connection, surface: Surface) -> threading.Lock:
    from src.ai import provider_claude_queue as pcq
    key = f"{pcq.db_path_of(conn) or 'mem'}:{surface.name}"
    with _locks_guard:
        return _locks.setdefault(key, threading.Lock())


def warm(conn: sqlite3.Connection, config: dict | None, surface: Surface, items: list[Item]) -> int:
    """캐시가 없거나 낡은 항목만 큐로 다듬어 저장하고 성공 건수를 반환. 차단·실패는 0(예외는 호출자가 삼킨다)."""
    todo = [it for it in items if it.rule_text and _fresh_body(conn, surface, it) is None]
    if not todo or gate(conn, config, surface) is not None:
        return 0
    lock = _lock_for(conn, surface)
    if not lock.acquire(blocking=False):
        return 0
    try:
        return _warm_locked(conn, config, surface, todo)
    finally:
        lock.release()


def _warm_locked(conn, config, surface: Surface, todo: list[Item]) -> int:
    from src.ai import provider_claude_queue as pcq
    done = 0
    for i in range(0, len(todo), surface.chunk):
        part = todo[i:i + surface.chunk]
        payloads = {it.scope_key: _payload(surface, it) for it in part}
        out = pcq.try_complete(conn, config, kind=surface.job_kind, model=surface.model,
                               prompt=build_prompt(surface, list(payloads.values())))
        if not out:
            break
        by_key = {it.scope_key: it for it in part}
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        for r in parse_items(out):
            it = by_key.get(r.get("id"))
            if it is None:
                continue
            basis = {k: v for k, v in payloads[it.scope_key].items() if k != "id"}   # id(날짜 등)의 숫자는 근거가 아니다
            text = validate(surface, json.dumps(basis, ensure_ascii=False, default=str), r.get("text"))
            if text:
                # 원문과 같으면 '원문 유지'로 기록(재요청 방지, 화면은 규칙 문구·AI 표시 없음)
                body = {"text": None, "unchanged": True} if text == it.rule_text.strip() else {"text": text}
                conn.execute("INSERT OR REPLACE INTO ai_outputs(kind, scope_key, src_hash, body_json, created_at)"
                             " VALUES (?,?,?,?,?)", (surface.kind, it.scope_key, src_hash(surface, it),
                                                     json.dumps(body, ensure_ascii=False), now))
                done += 1
        conn.commit()
    return done


def warm_in_background(db_path: str, config: dict | None, surface: Surface,
                       collect: Callable[[sqlite3.Connection], list[Item]]) -> None:
    """동기화·요청 경로를 막지 않도록 별도 스레드·연결에서 collect(conn) → warm. 예외는 로그만."""
    def _run() -> None:
        try:
            with sqlite3.connect(db_path, timeout=30) as c:
                warm(c, config, surface, collect(c))
        except Exception:  # noqa: BLE001
            log.warning("ai wording warm failed: %s", surface.name, exc_info=True)
    threading.Thread(target=_run, daemon=True, name=f"wording-{surface.name}").start()
