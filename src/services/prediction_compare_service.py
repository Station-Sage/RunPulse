"""레이스 예측 3경로 비교(P7-PRED-71) — (a) Garmin 예측, (b) RunPulse·기기 심박 기준, (c) RunPulse·자체 추정(기본, r3)
+ 값이 있으면 r4 섀도 후보 2개(candidate=True, 기본 표시 아님 — REVIEW-07 §R4-8(4)).

같은 metric_name(race_pred_{bucket}_sec)을 provider 로 구분해 읽고, 차이의 이유를 규칙으로 만든다(LLM 없음).
"""
from __future__ import annotations

import json
import sqlite3
from datetime import date as _date

PATHS = (("garmin", "garmin", "Garmin 예측"),
         ("ref", "runpulse:ref_garmin", "RunPulse · 기기 심박 기준"),
         ("self", "runpulse:formula_v1", "RunPulse · 자체 추정"))
CANDIDATES = (("r4", "runpulse:shadow_r4", "후보 r4 · 섀도"),
              ("r4_asym", "runpulse:shadow_r4_asym", "후보 r4 비대칭 · 섀도"))
STALE_DAYS = 14
SMALL_PCT = 1.0


def _latest(conn, metric: str, provider: str, as_of: str):
    return conn.execute(
        "SELECT scope_id, numeric_value, json_value FROM metric_store WHERE scope_type='daily' AND metric_name=? "
        "AND provider=? AND numeric_value IS NOT NULL AND scope_id <= ? ORDER BY scope_id DESC LIMIT 1",
        (metric, provider, as_of)).fetchone()


def _pct(a: float, b: float) -> float:
    return round((a / b - 1) * 100, 1)


def compare(conn: sqlite3.Connection, bucket: str, as_of: str | None = None) -> dict:
    as_of = as_of or _date.today().isoformat()
    metric = f"race_pred_{bucket}_sec"
    rows = []
    for key, prov, label in PATHS + CANDIDATES:
        r = _latest(conn, metric, prov, as_of)
        cand = (key, prov, label) in CANDIDATES
        if r is None:
            if not cand:                      # 섀도 값이 없으면 행 자체를 두지 않는다
                rows.append({"key": key, "label": label, "provider": prov, "value_sec": None})
            continue
        j = json.loads(r[2]) if r[2] else {}
        rows.append({"key": key, "label": label, "provider": prov, "value_sec": int(round(r[1])), "as_of": r[0],
                     "stale_days": (_date.fromisoformat(as_of) - _date.fromisoformat(r[0])).days,
                     "low_sec": j.get("low_s"), "high_sec": j.get("high_s"), "confidence": j.get("confidence"),
                     "reasons": j.get("reasons", []), "contributions": j.get("contributions"),
                     **({"candidate": True} if cand else {})})
    by = {r["key"]: r for r in rows}
    hp = _latest(conn, "hr_profile", "runpulse:formula_v1", as_of)
    hj = json.loads(hp[2]) if hp and hp[2] else {}
    hr_basis = {"self_lthr": (hj.get("self") or {}).get("lthr"), "ref_lthr": (hj.get("ref") or {}).get("lthr"),
                "lthr_gap": hj.get("lthr_gap")}
    return {"bucket": bucket, "as_of": as_of, "rows": rows, "hr_basis": hr_basis, "notes": _notes(by, hr_basis)}


def _notes(by: dict, hb: dict) -> list[str]:
    out = []
    s, g, r = by["self"].get("value_sec"), by["garmin"].get("value_sec"), by["ref"].get("value_sec")
    if g and s:
        d = _pct(g, s)
        out.append(f"Garmin 예측이 자체 추정보다 {abs(d)}% {'느림' if d > 0 else '빠름'} — Garmin은 VO2max 추정 기반, "
                   "RunPulse는 최근 전력 대회·품질 세트(휴식 보정 Daniels 강도)·심박-속도 관계 기반")
        if by["garmin"]["stale_days"] > STALE_DAYS:
            out.append(f"Garmin 값은 {by['garmin']['stale_days']}일 전 스냅샷")
    elif not g:
        out.append("Garmin 예측 없음(동기화 필요)")
    if r and s:
        d = _pct(r, s)
        gap = hb.get("lthr_gap")
        if abs(d) < SMALL_PCT:
            out.append(f"심박 기준(자체 LTHR {hb.get('self_lthr')} vs 기기 {hb.get('ref_lthr')})에 따른 차이 {abs(d)}% — 영향 작음")
        else:
            out.append(f"기기 심박 기준 예측이 {abs(d)}% {'느림' if d > 0 else '빠름'} — LTHR 차이 {gap} bpm 이 "
                       "심박 신호(H)·세트 품질 가중을 바꿈")
    elif not r:
        out.append("기기 심박 기준값 없음 — 기기 LTHR 미수집")
    return out


def profile(conn: sqlite3.Connection, as_of: str | None = None) -> dict:
    """P7-PRED-74 카드용: 최신 hr_profile·heat_model·training_response json(없으면 None)."""
    as_of = as_of or _date.today().isoformat()
    out = {"as_of": as_of}
    for key in ("hr_profile", "heat_model", "training_response"):
        r = _latest(conn, key, "runpulse:formula_v1", as_of)
        out[key] = ({"date": r[0], **json.loads(r[2])} if r and r[2] else None)
    return out
