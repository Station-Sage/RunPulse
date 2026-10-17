"""당일 자동 조정 제안 upsert (plan_adjustments, ADR-035) — 통증 제안 우선, 없으면 컨디션 기반 제안."""
from __future__ import annotations

import json
import sqlite3
from datetime import date as _date

from src.services import plan_pain
from src.services.plan_adjustment_rows import get_row, live_auto
from src.services.plan_service import todays_adjustment_with_hold
from src.services.user_settings_service import get_setting
from src.training.goals import get_active_goal

RULE_VERSION = "adjuster_v2"


def build(w: dict) -> tuple[dict, dict, list]:
    before = {k: w.get(k) for k in ("workout_type", "distance_km", "target_pace_min",
                                    "target_pace_max", "description")}
    to_rest = w["adjusted_type"] == "rest"
    after = {**before, "workout_type": w["adjusted_type"], "target_pace_min": None, "target_pace_max": None,
             "distance_km": None if to_rest else w.get("adjusted_distance_km", before["distance_km"])}
    reasons = w.get("reasons") or [{"key": "readiness", "label": p} for p in w.get("adjustment_reason_parts") or []]
    if w.get("adjustment_reason"):
        reasons.insert(0, {"key": "summary", "label": w["adjustment_reason"]})
    return before, after, reasons


def _trigger_set(signals: list[dict]) -> set[str]:
    return {x["signal"] for x in signals if x.get("role") == "trigger"}


def _propose(conn: sqlite3.Connection, date: str) -> tuple[dict | None, list[dict] | None]:
    """adjuster_version 설정(기본 v2)에 따라 제안과 신호 목록을 만든다. v2 는 신호 목록이 없다(None)."""
    if get_setting(conn, "adjuster_version", "v2") == "v3":
        from src.services import adjuster_v3
        from src.services.metric_freshness import crs_boost_hold
        try:
            hold = crs_boost_hold(conn, date)
        except Exception:
            hold = {"hold": True, "reasons": []}
        return adjuster_v3.propose(conn, date, hold)
    return plan_pain.proposal(conn, date) or todays_adjustment_with_hold(conn, date), None


def ensure_proposal(conn: sqlite3.Connection, date: str, *, today: str | None = None) -> dict | None:
    """당일 조정 제안을 멱등 upsert. accepted·reverted 행이 있으면 그대로 두고 반환한다."""
    today = today or _date.today().isoformat()
    cur = live_auto(conn, date)
    if cur and cur["decision"] != "proposed":
        return cur
    if date != today:
        return cur
    try:
        w, signals = _propose(conn, date)
    except Exception:
        return cur
    if not w or not w.get("adjusted"):
        return cur
    before, after, reasons = build(w)
    rule = w.get("rule_version", RULE_VERSION)
    source = w.get("source") or ("pain" if rule == "pain_v1" else "readiness")
    sig_json = json.dumps(signals or [], ensure_ascii=False)
    if cur and cur["decision"] == "proposed" and cur["workout_id"] == w["id"]:
        changed = cur["after"] != after or cur["before"] != before
        if signals is not None:
            changed = changed or _trigger_set(cur.get("signals") or []) != _trigger_set(signals)
        else:
            changed = changed or cur["reasons"] != reasons
        if changed:
            conn.execute("UPDATE plan_adjustments SET source=?, before_json=?, after_json=?, reasons_json=?,"
                         " signals_json=?, rule_version=?, rev=rev+1, updated_at=datetime('now') WHERE id=?",
                         (source, json.dumps(before), json.dumps(after), json.dumps(reasons, ensure_ascii=False),
                          sig_json, rule, cur["id"]))
        elif signals is not None and (cur.get("signals") != signals or cur["reasons"] != reasons):
            conn.execute("UPDATE plan_adjustments SET reasons_json=?, signals_json=?, updated_at=datetime('now')"
                         " WHERE id=?", (json.dumps(reasons, ensure_ascii=False), sig_json, cur["id"]))
        else:
            return cur
        conn.commit()
        return get_row(conn, cur["id"])
    if cur and cur["decision"] == "proposed":
        conn.execute("UPDATE plan_adjustments SET decision='reverted', decided_at=datetime('now') WHERE id=?",
                     (cur["id"],))
    goal = get_active_goal(conn)
    cur_id = conn.execute(
        "INSERT INTO plan_adjustments(goal_id, workout_id, date, source, op, before_json, after_json,"
        " reasons_json, signals_json, rule_version) VALUES (?,?,?,?,?,?,?,?,?,?)",
        (goal["id"] if goal else None, w["id"], date, source, "rest" if after["workout_type"] == "rest" else "replace",
         json.dumps(before), json.dumps(after), json.dumps(reasons, ensure_ascii=False), sig_json,
         rule)).lastrowid
    conn.commit()
    return get_row(conn, cur_id)
