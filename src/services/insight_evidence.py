"""능동 인사이트 다듬기 근거(facts) — 사건의 비건강 신호 + 같은 날 계산 지표(ADR-059 2단계).

회복 사건(recovery_low)에는 웰니스 원값(수면·스트레스·안정시 심박·HRV 와 본인 평균, D15)도 준다.
통증·질병·부상 신호(pain·checkin_pain·illness·injury)는 넣지 않고, pain_flag 사건은 근거 없이 일반 문구만 쓴다
(ADR-057/058). 다듬기 자체가 coach 동의(`ai_wording._consent_ok`, 단일 기준)가 있을 때만 일어나고, 동의가 없으면
화면도 저장된 다듬은 문장 대신 규칙 문장을 쓴다. 유효 키(text_src)는 원문+facts 해시라 근거가 바뀌면 규칙 문장으로 돌아간다.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3

from src.services import ai_wording as aw

SEP = "␟"
# 사건 종류별 함께 줄 계산 지표 — 부하·준비도
_CONTEXT_METRICS = {"load_spike": ("ctl", "atl", "tsb", "cirs"), "recovery_low": ("tsb", "utrs", "acwr")}
_SIGNAL_KEYS = {"acwr": "acwr", "crs": "crs_level", "checkin_fatigue": "fatigue_checkin"}
_NO_FACTS_KINDS = ("pain_flag",)
# 웰니스 원값(그날 값·본인 7·90일 평균, ADR-059 D15)을 함께 주는 종류 — 회복 신호 사건만
_WELLNESS_KINDS = ("recovery_low",)


def _crs_label(level) -> str | None:
    from src.metrics.crs import LEVEL_LABELS
    return LEVEL_LABELS.get(level) if isinstance(level, int) and not isinstance(level, bool) else None


def _metric(conn: sqlite3.Connection, name: str, day: str) -> float | None:
    try:
        r = conn.execute("SELECT numeric_value FROM metric_store WHERE scope_type='daily' AND scope_id<=? AND scope_id>date(?, '-3 days')"
                         " AND metric_name=? AND is_primary=1 AND numeric_value IS NOT NULL ORDER BY scope_id DESC LIMIT 1",
                         (day, day, name)).fetchone()
    except sqlite3.Error:
        return None
    return round(float(r[0]), 2 if abs(r[0]) < 10 else 1) if r else None


def evidence_facts(conn: sqlite3.Connection, kind: str, signals: list[dict], as_of: str) -> dict:
    """사건 1건의 비건강 근거(평면 dict). 건강 사건·근거 없음은 {}."""
    if kind in _NO_FACTS_KINDS:
        return {}
    facts: dict = {}
    for s in signals or []:
        key = _SIGNAL_KEYS.get(s.get("signal"))
        if key and isinstance(s.get("value"), (int, float)) and not isinstance(s.get("value"), bool):
            facts[key] = s["value"]
            if key == "crs_level" and (lab := _crs_label(s["value"])):
                facts["crs_gate"] = lab
        elif str(s.get("signal", "")).startswith("sync_") and isinstance(s.get("value"), int):
            facts["sync_gap_days"] = s["value"]
    for name in _CONTEXT_METRICS.get(kind, ()):
        if name not in facts and (v := _metric(conn, name, as_of)) is not None:
            facts[name] = v
    if kind in _WELLNESS_KINDS:
        from src.services.wellness_facts import wellness_facts
        facts.update({k: v for k, v in wellness_facts(conn, as_of).items() if k not in facts})
    return {k: (aw.redact_health_text(v) if isinstance(v, str) else v) for k, v in facts.items()}


def facts_enabled(conn: sqlite3.Connection) -> bool:
    """인사이트를 AI 로 다듬어도(근거 포함) 되는지 — 공통 계층의 동의 판정을 그대로 쓴다(단일 기준)."""
    return aw._consent_ok(conn)


def polish_key(text: str, facts: dict) -> str:
    """text_src 에 저장·비교하는 유효 키. facts 가 없으면 원문 그대로(기존 행과 호환)."""
    if not facts:
        return text
    blob = json.dumps(facts, sort_keys=True, ensure_ascii=False, default=str)
    return f"{text}{SEP}{hashlib.sha1(blob.encode('utf-8')).hexdigest()[:12]}"
