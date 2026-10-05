"""레이스 예측(race_pred_*_sec) 분해 v2 — 신호별 환산 기록·가중치·범위·신뢰 제한 요인을 evidence로 제공."""
from __future__ import annotations

import sqlite3

from src.services.metrics_basis_events import load_json as _js
from src.utils.db_helpers import get_primary_metric

_SIGNAL_LABEL = {"race": "대회 기록", "work": "훈련 강도 환산", "hr": "심박-페이스 환산", "best_effort": "5K 최고 구간"}
_DIST_LABEL = {"race_pred_5k_sec": "5K", "race_pred_10k_sec": "10K", "race_pred_half_sec": "하프", "race_pred_marathon_sec": "마라톤"}


def explain_prediction(conn: sqlite3.Connection, scope_type: str, scope_id: str, slug: str):
    """(terms, sources, formula_text, evidence). json이 비면 terms=[] — 값만 있는 카드로 남는다."""
    js = _js(get_primary_metric(conn, scope_type, scope_id, slug))
    base = _js(get_primary_metric(conn, scope_type, scope_id, "race_pred_vdot"))
    weights = js.get("contributions") or {}
    signals_s = js.get("signals_s") or {}

    terms = []
    for key, sec in signals_s.items():
        w = weights.get(key)
        terms.append({
            "slug": key, "label": _SIGNAL_LABEL.get(key, key), "raw": sec, "weight": w,
            "contribution": round(sec * w) if w is not None else None,
        })

    sources = []
    anchor, work = base.get("anchor") or {}, base.get("work") or {}
    if anchor.get("activity_id"):
        sources.append({"type": "activity", "id": anchor["activity_id"], "date": anchor.get("date"),
                        "label": "기준 대회", "value": anchor.get("vdot15"), "unit": "VDOT", "effect": ""})
    if work.get("activity_id"):
        sources.append({"type": "activity", "id": work["activity_id"], "label": "훈련 강도 신호",
                        "value": work.get("vdot"), "unit": "VDOT", "effect": ""})

    evidence: dict = {"distance": _DIST_LABEL.get(slug, slug)}
    if js.get("low_s") is not None and js.get("high_s") is not None:
        evidence["range"] = {"low": js["low_s"], "high": js["high_s"]}
    if js.get("confidence") is not None:
        evidence["confidence"] = js["confidence"]
    if js.get("reasons"):
        evidence["limiting"] = js["reasons"]
    if js.get("daniels_s") is not None and js.get("tanda_s") is not None:
        evidence["models"] = [{"name": "다니엘스", "sec": js["daniels_s"]}, {"name": "탄다", "sec": js["tanda_s"]}]
    if js.get("by_temp"):
        evidence["by_temp"] = js["by_temp"]
    if weights:
        evidence["weights"] = weights

    text = "예측 = 대회·훈련·심박 신호를 가중 결합한 VDOT를 목표 거리 기록으로 환산 (기온 15°C 기준)"
    return terms, sources, text, evidence
