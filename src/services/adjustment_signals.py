"""조정 신호 수집·분류 (ADR-035 개정, ADJ §3.6) — 읽기 전용, 외부 호출 없음. 수집기별 실패는 freshness='missing' 으로 격리한다.

신호 항목: {signal, role, value, detail, as_of, freshness, provider}. role 은 classify() 가 채운다.
"""
from __future__ import annotations

import sqlite3
from datetime import date as _date

from src.services import adjustment_triggers_v3 as T
from src.services.adjustment_signals_context import collect_context
from src.services.adjustment_signals_race import collect_race


def _item(signal: str, value, provider: str, day: str, *, detail=None, fresh: str = "fresh", as_of: str | None = None):
    return {"signal": signal, "role": None, "value": value, "detail": detail, "as_of": as_of or day,
            "freshness": fresh, "provider": provider}


def _missing(signal: str, provider: str, day: str) -> dict:
    return _item(signal, None, provider, day, fresh="missing")


def _checkin(conn, day):
    from src.services.today_service import get_todays_checkin
    c = get_todays_checkin(conn, day)
    if c is None:
        return [_missing("checkin_pain", "user_inputs", day), _missing("checkin_fatigue", "user_inputs", day)]
    pain = c.get("pain") or "none"
    return [_item("checkin_pain", pain, "user_inputs", day),
            _item("checkin_fatigue", c.get("fatigue"), "user_inputs", day,
                  fresh="fresh" if c.get("fatigue") is not None else "missing")]


def _crs(conn, day, crs):
    from src.metrics import crs as crs_mod
    r = crs if crs is not None else crs_mod.evaluate(conn, day)
    if r is None:
        return [_missing("crs", "metric_store", day)]
    return [_item("crs", r["level"], "metric_store", day, detail={"label": r.get("level_label"), "crs": r.get("crs")})]


def _acwr(conn, day):
    row = conn.execute("SELECT scope_id, numeric_value FROM metric_store WHERE scope_type='daily' AND metric_name='acwr'"
                       " AND is_primary=1 AND scope_id<=? AND numeric_value IS NOT NULL ORDER BY scope_id DESC LIMIT 1",
                       (day,)).fetchone()
    if row is None:
        return [_missing("acwr", "metric_store", day)]
    stale = (_date.fromisoformat(day) - _date.fromisoformat(row[0])).days > 0
    return [_item("acwr", round(float(row[1]), 2), "metric_store", day, as_of=row[0], fresh="stale" if stale else "fresh")]


def _pain(conn, day):
    from src.services import plan_pain
    p = plan_pain.proposal(conn, day)
    if p is None:
        return [_item("pain", False, "plan_adjustments", day)]
    return [_item("pain", True, "plan_adjustments", day, detail={"op": p["adjusted_type"]})]


def _readiness(conn, day, readiness):
    from src.training.fatigue import readiness_decision
    r = readiness if readiness is not None else readiness_decision(conn, date=day)
    return [_item("readiness", r.get("fatigue_level"), "fatigue", day, detail={"tsb": r.get("tsb")})]


def _hold(conn, day, hold):
    from src.services.metric_freshness import crs_boost_hold
    h = hold if hold is not None else crs_boost_hold(conn, day)
    it = _item("boost_hold", bool(h.get("hold")), "metric_freshness", day, detail={"reasons": h.get("reasons")})
    it["role"] = "hold"
    return [it]


def collect(conn: sqlite3.Connection, day: str, *, readiness: dict | None = None, crs: dict | None = None,
            hold: dict | None = None) -> list[dict]:
    """day 의 모든 신호(role 미분류 또는 hold). 수집기 예외는 해당 신호를 missing 으로 만든다."""
    steps = [("checkin_pain", lambda: _checkin(conn, day)), ("crs", lambda: _crs(conn, day, crs)),
             ("acwr", lambda: _acwr(conn, day)), ("pain", lambda: _pain(conn, day)),
             ("context", lambda: collect_context(conn, day)), ("readiness", lambda: _readiness(conn, day, readiness)),
             ("boost_hold", lambda: _hold(conn, day, hold)),
             ("race_plan", lambda: [r] if (r := collect_race(conn, day)) else [])]
    out: list[dict] = []
    for name, fn in steps:
        try:
            out += fn()
        except Exception:
            out.append(_missing(name, "error", day))
    return out


def evaluate(signals: list[dict]) -> dict:
    """{triggers, source, intensity, signals(분류됨)}. 트리거 없으면 source/intensity=None."""
    trig = T.triggered(signals)
    return {"triggers": trig, "source": T.primary(trig),
            "intensity": T.intensity(signals, trig) if trig else None, "signals": T.classify(signals, trig)}
