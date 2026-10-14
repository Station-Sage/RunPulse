"""메트릭 신선도 평가 (ADR-050) — 값이 오늘의 입력으로 계산됐는지 fresh/partial/stale/missing 으로 판정.

읽기 전용. 이 모듈이 신선도 SQL 의 유일한 위치다(wellness 컬럼별 MAX(date) 1쿼리 + 같은 날 metric_store 1쿼리).
소비처(Today/Library/BOOST 보류)는 결과의 `text` 만 표시하고 판정을 다시 하지 않는다.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import date as _date

from .metric_freshness_spec import (
    FRESHNESS_SPEC, PARTIAL_CONFIDENCE, STALE_DAYS, WELLNESS_LABELS,
)

_ORDER = {"fresh": 0, "partial": 1, "stale": 2, "missing": 3}
BADGE_TEXT = {"stale": "입력이 오래됐어요", "partial": "일부 데이터 없이 계산"}
HOLD_HEADLINE = "최근 데이터가 부족해 참고용이에요"
_HOLD_TEXT = {
    "crs_stale": "컨디션 입력이 오래돼 증량은 보류했어요",
    "crs_missing": "컨디션 점수가 없어 증량은 보류했어요",
    "gate_unknown": "회복 신호 일부가 없어 증량은 보류했어요",
}


def _ver(v: str | None) -> tuple:
    try:
        return tuple(int(p) for p in str(v or "0").split("."))
    except ValueError:
        return (0,)


def _days(a: str, b: str) -> int:
    return (_date.fromisoformat(a) - _date.fromisoformat(b)).days


def _json(row: dict | None) -> dict:
    raw = (row or {}).get("json_value")
    if isinstance(raw, dict):
        return raw
    try:
        data = json.loads(raw) if raw else {}
    except (TypeError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _wellness_last(conn: sqlite3.Connection, cols: list[str], basis: str) -> dict[str, str | None]:
    """컬럼별 basis 이하 마지막 non-null 날짜 — 쿼리 1회."""
    sel = ", ".join(f"MAX(CASE WHEN {c} IS NOT NULL THEN date END)" for c in cols)
    row = conn.execute(f"SELECT {sel} FROM daily_wellness WHERE date <= ?", (basis,)).fetchone()
    return dict(zip(cols, row or [None] * len(cols)))


def _same_day_metrics(conn: sqlite3.Connection, names: list[str], basis: str) -> set[str]:
    if not names:
        return set()
    ph = ",".join("?" * len(names))
    rows = conn.execute(
        f"SELECT DISTINCT metric_name FROM metric_store WHERE scope_type='daily' AND scope_id=?"
        f" AND is_primary=1 AND numeric_value IS NOT NULL AND metric_name IN ({ph})",
        [basis, *names],
    ).fetchall()
    return {r[0] for r in rows}


def _missing_inputs(spec: dict, data: dict) -> list[str] | None:
    """행 JSON 에서 읽은 누락 wellness 컬럼. 읽을 수 없으면 None."""
    role = spec["wellness_role"]
    if role == "modifier":
        if "wellness_used" not in data:
            return None
        return [c for c in spec["wellness"] if c not in data["wellness_used"]]
    if role == "gate":
        sig = data.get("signals")
        if not isinstance(sig, dict):
            return None
        return [col for k, col in spec["signal_map"].items() if sig.get(k) is None]
    comps = data.get("components")
    if not isinstance(comps, dict):
        return None
    return [col for k, col in spec["component_map"].items() if k not in comps]


def _badge(level: str, reasons: list[dict]) -> dict | None:
    text = BADGE_TEXT.get(level)
    return {"code": level, "params": {}, "text": text} if text else None


def _assess(spec: dict, name: str, basis: str, row: dict | None,
            last: dict[str, str | None], present: set[str], upstream: dict[str, dict]) -> dict:
    out = {"level": "missing", "value_date": None, "age_days": None,
           "inputs": {"wellness": {"last_date": None, "days": None}}, "coverage": None,
           "used_inputs": [], "reasons": [], "assertive": False, "missing_inputs": [],
           "unknown_gates": [], "badge": None}
    if row is None or row.get("numeric_value") is None:
        out["reasons"].append({"code": "metric_missing", "metric": name, "text": "값이 아직 없어요"})
        return out
    vdate = str(row.get("scope_id") or basis)
    out["value_date"], out["age_days"] = vdate, max(_days(basis, vdate), 0)
    reasons: list[dict] = out["reasons"]
    level = "fresh"

    def worsen(to: str) -> None:
        nonlocal level
        if _ORDER[to] > _ORDER[level]:
            level = to

    dates = [d for c, d in last.items() if c in spec["wellness"] and d]
    freshest = max(dates) if dates else None
    wdays = _days(basis, freshest) if freshest else None
    out["inputs"]["wellness"] = {"last_date": freshest, "days": wdays}
    role = spec["wellness_role"]
    if role != "modifier" and wdays is not None and wdays >= STALE_DAYS:
        reasons.append({"code": "wellness_stale", "days": wdays,
                        "text": f"컨디션 입력이 {wdays}일 전 기록이에요"})
        worsen("stale")

    coverage = row.get("confidence")
    if "min_version" in spec and _ver(row.get("algorithm_version")) < _ver(spec["min_version"]):
        coverage = None
        reasons.append({"code": "coverage_unknown", "text": "이전 계산 방식이라 입력 범위를 알 수 없어요"})
        if role == "gate":
            out["unknown_gates"] = list(spec["wellness"])
            reasons.append({"code": "gate_unknown", "text": _HOLD_TEXT["gate_unknown"]})
            worsen("partial")
    out["coverage"] = coverage
    if coverage is not None and coverage < PARTIAL_CONFIDENCE:
        reasons.append({"code": "low_coverage", "coverage": coverage, "text": "계산에 쓴 입력이 적어요"})
        worsen("partial")

    miss = _missing_inputs(spec, _json(row)) if coverage is not None or role == "modifier" else None
    if miss is not None:
        out["missing_inputs"] = miss
        out["used_inputs"] = [c for c in spec["wellness"] if c not in miss]
        if miss and role == "gate":
            out["unknown_gates"] = miss
            reasons.append({"code": "gate_unknown", "text": _HOLD_TEXT["gate_unknown"]})
            worsen("partial")
        elif miss and len(miss) == len(spec["wellness"]):
            reasons.append({"code": "modifier_missing" if role == "modifier" else "wellness_missing",
                            "text": "컨디션 입력 없이 계산했어요"})
            worsen("partial")
        elif miss:
            labels = ", ".join(WELLNESS_LABELS.get(c, c) for c in miss)
            reasons.append({"code": "input_missing", "inputs": miss, "text": f"{labels} 없이 계산했어요"})

    for m in spec["metrics"]:
        if m not in present:
            reasons.append({"code": "metric_missing", "metric": m, "text": f"{m.upper()} 값이 오늘 없어요"})
            worsen("partial")
    for up_name, up in upstream.items():
        if _ORDER[up["level"]] > _ORDER[level]:
            reasons.append({"code": "upstream", "metric": up_name, "text": f"{up_name.upper()} 입력이 부족해요"})
            worsen(up["level"] if up["level"] != "missing" else "partial")

    out["level"], out["assertive"] = level, level == "fresh"
    out["badge"] = _badge(level, reasons)
    return out


def assess_many(conn: sqlite3.Connection, names: list[str], basis_date: str,
                rows: dict[str, dict | None]) -> dict[str, dict]:
    """names 각각의 신선도. rows 는 metric_name → metric_store 행(없으면 None). 쿼리는 고정 2회."""
    need: dict[str, dict] = {}
    for n in names:
        need[n] = FRESHNESS_SPEC[n]
        for up in need[n].get("upstream", []):
            need[up] = FRESHNESS_SPEC[up]
    cols = sorted({c for s in need.values() for c in s["wellness"]})
    last = _wellness_last(conn, cols, basis_date)
    present = _same_day_metrics(conn, sorted({m for s in need.values() for m in s["metrics"]}), basis_date)
    done: dict[str, dict] = {}

    def run(n: str, stack: tuple = ()) -> dict:
        assert n not in stack, f"freshness upstream cycle: {stack + (n,)}"
        if n not in done:
            ups = {u: run(u, stack + (n,)) for u in need[n].get("upstream", [])}
            done[n] = _assess(need[n], n, basis_date, rows.get(n), last, present, ups)
        return done[n]

    return {n: run(n) for n in names}


def assess(conn: sqlite3.Connection, metric_name: str, basis_date: str, row: dict | None) -> dict:
    """단일 메트릭 신선도. 선행(upstream) 행은 row 와 같은 날 primary 행에서 읽는다."""
    rows = {metric_name: row}
    for up in FRESHNESS_SPEC[metric_name].get("upstream", []):
        r = conn.execute(
            "SELECT * FROM metric_store WHERE scope_type='daily' AND scope_id=? AND metric_name=? AND is_primary=1",
            (basis_date, up)).fetchone()
        if r is not None:
            cols = [d[0] for d in conn.execute("SELECT * FROM metric_store LIMIT 0").description]
            rows[up] = dict(zip(cols, r)) if not isinstance(r, sqlite3.Row) else dict(r)
    return assess_many(conn, [metric_name], basis_date, rows)[metric_name]


def boost_hold(fr: dict) -> dict:
    """CRS 신선도 평가 → 증량(BOOST) 보류 판단 {"hold": bool, "reasons": [{code, params, text}]}."""
    reasons: list[dict] = []
    codes = {r["code"] for r in fr["reasons"]}
    if fr["level"] == "missing":
        reasons.append("crs_missing")
    else:
        if "wellness_stale" in codes or fr["level"] == "stale":
            reasons.append("crs_stale")
        if fr["unknown_gates"] or "gate_unknown" in codes or fr["level"] != "fresh":
            if "crs_stale" not in reasons or fr["unknown_gates"]:
                reasons.append("gate_unknown")
    reasons = list(dict.fromkeys(reasons))
    return {"hold": bool(reasons), "reasons": [{"code": c, "params": {}, "text": _HOLD_TEXT[c]} for c in reasons]}


def boost_hold_text(code: str, params: dict | None = None) -> str:
    return _HOLD_TEXT.get(code, "증량은 보류했어요")


def crs_boost_hold(conn: sqlite3.Connection, date: str) -> dict:
    """date 의 CRS 로 BOOST 보류 여부 판단. 해제 조건: CRS fresh + 신호 non-null + hrv_rolling_days>=3."""
    row = conn.execute(
        "SELECT * FROM metric_store WHERE scope_type='daily' AND scope_id=? AND metric_name='crs' AND is_primary=1",
        (date,)).fetchone()
    cols = [d[0] for d in conn.execute("SELECT * FROM metric_store LIMIT 0").description]
    d = None if row is None else dict(zip(cols, tuple(row)))
    fr = assess(conn, "crs", date, d)
    hold = boost_hold(fr)
    if not hold["hold"]:
        sig = _json(d).get("signals") or {}
        if (sig.get("hrv_rolling_days") or 0) < 3:
            hold = {"hold": True, "reasons": [{"code": "gate_unknown", "params": {}, "text": _HOLD_TEXT["gate_unknown"]}]}
    return hold
