"""레이스 예측 설명 근거 — 지표 해석(metric_interp) 표면의 race_pred_* facts 보강 (ADR-059 D18, 3단계 ①).

예측 분해 evidence(모델 범위·신뢰도·신뢰 제한 요인·주 신호)와 같은 거리 활성 목표의 목표 기록·격차를 평면 facts 로
만든다. 예측 값·결정 로직은 건드리지 않는다(AI 는 문장만). 목표·대회 이름(자유 입력)은 넣지 않는다.
시간은 화면과 같은 'h:mm:ss' 문자열이라 해시 반올림(5초)이 그대로 적용된다.
"""
from __future__ import annotations

import sqlite3

_BUCKET = {"race_pred_5k_sec": "5k", "race_pred_10k_sec": "10k", "race_pred_half_sec": "half",
           "race_pred_marathon_sec": "marathon"}


def _hms(sec: float) -> str:
    s = int(round(abs(sec)))
    return f"{s // 3600}:{s % 3600 // 60:02d}:{s % 60:02d}" if s >= 3600 else f"{s // 60}:{s % 60:02d}"


def confidence_label(c: float | None) -> str | None:
    """프런트 predictionCompare.confidenceLabel 과 같은 경계."""
    if c is None:
        return None
    return "높음" if c >= 0.7 else "보통" if c >= 0.45 else "낮음"


def _goal_gap(conn: sqlite3.Connection, slug: str, day: str, value: float | None) -> dict:
    from src.services.race_hub_service import bucket_for_distance
    try:
        rows = conn.execute("SELECT distance_km, target_time_sec FROM goals WHERE status='active' AND race_date >= ?"
                            " AND target_time_sec IS NOT NULL ORDER BY race_date, id DESC", (day,)).fetchall()
    except sqlite3.Error:
        return {}
    for km, target in rows:
        if bucket_for_distance(km) == _BUCKET[slug]:
            out = {"target_time": _hms(target)}
            if value is not None:
                gap = value - target
                out["gap_to_target"] = ("+" if gap > 0 else "-" if gap < 0 else "") + _hms(gap)
                out["gap_direction"] = "목표보다 느림" if gap > 0 else "목표보다 빠름" if gap < 0 else "목표와 같음"
            return out
    return {}


def rule_text(explain: dict) -> str | None:
    """예측 지표에 다른 규칙 해석(밴드·힌트·90일 대비)이 없을 때 쓰는 규칙 문장 — 범위·신뢰도·첫 제한 요인."""
    if explain.get("slug") not in _BUCKET:
        return None
    ev = explain.get("evidence") or {}
    rng, conf = ev.get("range") or {}, confidence_label(ev.get("confidence"))
    if rng.get("low") is None or rng.get("high") is None:
        return None
    head = f"모델 범위는 {_hms(rng['low'])}~{_hms(rng['high'])}" + (f", 신뢰도 {conf}" if conf else "")
    lim = (ev.get("limiting") or [None])[0]
    return f"{head}이에요." + (f" 제한 요인: {lim}." if lim else "")


def prediction_facts(conn: sqlite3.Connection, explain: dict) -> dict:
    """race_pred_* 분해 응답 → 근거(값이 있는 것만). 예측 지표가 아니면 {}."""
    slug = explain.get("slug")
    if slug not in _BUCKET:
        return {}
    ev = explain.get("evidence") or {}
    out: dict = {}
    rng = ev.get("range") or {}
    if rng.get("low") is not None and rng.get("high") is not None:
        out["range_fast"], out["range_slow"] = _hms(rng["low"]), _hms(rng["high"])
    if (lab := confidence_label(ev.get("confidence"))):
        out["confidence"] = lab
    if ev.get("limiting"):
        out["limiting"] = ", ".join(str(r) for r in ev["limiting"][:3])
    terms = [t for t in (explain.get("formula") or {}).get("terms") or [] if t.get("weight")]
    if terms:
        top = max(terms, key=lambda t: t["weight"])
        out["main_signal"] = top.get("label")
        out["main_signal_weight_pct"] = int(round(top["weight"] * 20)) * 5   # 5%p 단위(해시 안정)
        out["signal_count"] = len(terms)
    out.update(_goal_gap(conn, slug, explain["scope"]["id"], explain.get("value")))
    return out
