"""조정 제안 v3 (ADR-035 개정, ADJ §3.7) — 신호 수집 → 트리거 판정 → adjust_todays_plan 형식 제안 dict.

트리거가 없으면 기존 readiness 하향(adjuster_v2)을 단독 경로로 유지한다. 대회·휴식 행은 조정하지 않는다.
"""
from __future__ import annotations

import sqlite3

from src.services import adjustment_signals as S
from src.services import adjustment_triggers_v3 as T
from src.services.plan_pain import Q_TYPES
from src.training import adjuster

RULE_VERSION = "adjuster_v3"
SKIP_TYPES = ("rest", "race")
LABELS = {"pain": "통증", "illness": "컨디션 이상", "checkin": "체크인", "race": "대회 일정",
          "crs": "회복 준비도(CRS)", "acwr": "급성/만성 부하비(ACWR)", "readiness": "컨디션"}


def _target_type(original: str, intensity: str) -> str:
    if intensity == "rest":
        return "rest"
    return "easy" if original in Q_TYPES else original


def _race_trigger(signals: list[dict], original: str) -> bool:
    r = next((s for s in signals if s["signal"] == "race_plan"), None)
    d = (r or {}).get("detail") or {}
    return bool(r and d.get("phase") == "recovery" and d.get("unplanned") and original in Q_TYPES)


def propose(conn: sqlite3.Connection, day: str, hold: dict | None) -> tuple[dict | None, list[dict]]:
    """(제안 dict 또는 None, 분류된 신호 목록). 오늘 계획이 없거나 휴식·대회면 (None, [])."""
    base = adjuster.adjust_todays_plan(conn, date=day, boost_hold=hold)
    if base is None or base["original_type"] in SKIP_TYPES:
        return None, []
    readiness = {"fatigue_level": base["fatigue_level"], "tsb": base["tsb"], "wellness": base["wellness"]}
    signals = S.collect(conn, day, readiness=readiness, hold=hold)
    ev = S.evaluate(signals)
    trig = list(ev["triggers"])
    if _race_trigger(signals, base["original_type"]):
        trig.append("race_plan")
    if trig:
        inten = ev["intensity"] or "reduce"
        adj = _target_type(base["original_type"], inten)
        if adj == base["original_type"]:
            return None, T.classify(signals, trig)
        source = T.primary(trig)
        labels = [LABELS[T.kind_of(t)] for t in trig]
        base.update({"adjusted_type": adj, "adjusted": True, "source": source, "rule_version": RULE_VERSION,
                     "adjustment_reason": "·".join(dict.fromkeys(labels)) + " 신호",
                     "adjustment_reason_parts": [], "reasons": [{"key": T.kind_of(t), "label": LABELS[T.kind_of(t)]}
                                                                for t in trig]})
        return base, T.classify(signals, trig)
    if base["adjusted"]:
        base.update({"source": "readiness", "rule_version": RULE_VERSION})
        return base, T.classify(signals, ["readiness"])
    return None, []
