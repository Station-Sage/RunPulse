"""계획 조정 제안·수락·되돌리기 (plan_adjustments, ADR-035). 원본 planned_workouts 는 수정하지 않는다."""
from __future__ import annotations

import json
import sqlite3
from datetime import date as _date

from src.training.adjuster import adjust_todays_plan

RULE_VERSION = "adjuster_v1"
VIAS = ("plan", "session", "today", "coach")
_COLS = ("id, goal_id, workout_id, date, source, op, before_json, after_json, reasons_json, rule_version,"
         " decision, rev, accepted_at, decided_at, decided_via, created_at, updated_at")


class AdjustmentConflict(Exception):
    """code: REV_MISMATCH | LOCKED | STALE | INVALID_TRANSITION | NOT_FOUND"""

    def __init__(self, code: str, message: str = "", current: dict | None = None):
        super().__init__(message or code)
        self.code = code
        self.current = current


def _today(today: str | None) -> str:
    return today or _date.today().isoformat()


def _to_dict(r: tuple) -> dict:
    keys = [c.strip() for c in _COLS.split(",")]
    d = dict(zip(keys, r))
    for k in ("before", "after", "reasons"):
        d[k] = json.loads(d.pop(f"{k}_json") or ("[]" if k == "reasons" else "{}"))
    return d


def _get(conn: sqlite3.Connection, adj_id: int) -> dict | None:
    r = conn.execute(f"SELECT {_COLS} FROM plan_adjustments WHERE id = ?", (adj_id,)).fetchone()
    return _to_dict(r) if r else None


def _is_stale(conn: sqlite3.Connection, adj: dict) -> bool:
    r = conn.execute("SELECT date, workout_type, distance_km FROM planned_workouts WHERE id = ?",
                     (adj["workout_id"],)).fetchone()
    b = adj["before"]
    return not r or r[0] != adj["date"] or r[1] != b.get("workout_type") or r[2] != b.get("distance_km")


def state_of(conn: sqlite3.Connection, adj: dict, today: str) -> str:
    """저장하지 않고 계산하는 표시 상태."""
    if adj["decision"] == "reverted":
        return "undone" if adj["accepted_at"] else "declined"
    if _is_stale(conn, adj):
        return "stale"
    if adj["decision"] == "proposed" and adj["date"] < today:
        return "expired"
    return adj["decision"]


def _view(conn: sqlite3.Connection, adj: dict, today: str) -> dict:
    return {**adj, "state": state_of(conn, adj, today)}


def _build(w: dict) -> tuple[dict, dict, list]:
    before = {k: w.get(k) for k in ("workout_type", "distance_km", "target_pace_min",
                                    "target_pace_max", "description")}
    to_rest = w["adjusted_type"] == "rest"
    after = {**before, "workout_type": w["adjusted_type"], "target_pace_min": None, "target_pace_max": None,
             "distance_km": None if to_rest else before["distance_km"]}
    reasons = [{"key": "readiness", "label": p} for p in w.get("adjustment_reason_parts") or []]
    if w.get("adjustment_reason"):
        reasons.insert(0, {"key": "summary", "label": w["adjustment_reason"]})
    return before, after, reasons


def _live(conn: sqlite3.Connection, date: str) -> dict | None:
    r = conn.execute(f"SELECT {_COLS} FROM plan_adjustments WHERE date = ? AND source = 'crs'"
                     " ORDER BY (decision = 'accepted') DESC, id DESC LIMIT 1", (date,)).fetchone()
    return _to_dict(r) if r else None


def ensure_proposal(conn: sqlite3.Connection, date: str, *, today: str | None = None) -> dict | None:
    """당일 조정 제안을 멱등 upsert. accepted·reverted 행이 있으면 그대로 두고 반환한다."""
    today = _today(today)
    cur = _live(conn, date)
    if cur and cur["decision"] != "proposed":
        return cur
    if date != today:
        return cur
    try:
        w = adjust_todays_plan(conn, date=date)
    except Exception:
        return cur
    if not w or not w.get("adjusted"):
        return cur
    before, after, reasons = _build(w)
    if cur and cur["decision"] == "proposed" and cur["workout_id"] == w["id"]:
        if cur["after"] != after or cur["reasons"] != reasons or cur["before"] != before:
            conn.execute("UPDATE plan_adjustments SET before_json=?, after_json=?, reasons_json=?, rev=rev+1,"
                         " updated_at=datetime('now') WHERE id=?",
                         (json.dumps(before), json.dumps(after), json.dumps(reasons, ensure_ascii=False), cur["id"]))
            conn.commit()
            return _get(conn, cur["id"])
        return cur
    if cur and cur["decision"] == "proposed":
        conn.execute("UPDATE plan_adjustments SET decision='reverted', decided_at=datetime('now') WHERE id=?",
                     (cur["id"],))
    goal = conn.execute("SELECT id FROM goals WHERE status='active' ORDER BY id DESC LIMIT 1").fetchone()
    cur_id = conn.execute(
        "INSERT INTO plan_adjustments(goal_id, workout_id, date, source, op, before_json, after_json,"
        " reasons_json, rule_version) VALUES (?,?,?,'crs',?,?,?,?,?)",
        (goal[0] if goal else None, w["id"], date, "rest" if after["workout_type"] == "rest" else "replace",
         json.dumps(before), json.dumps(after), json.dumps(reasons, ensure_ascii=False), RULE_VERSION)).lastrowid
    conn.commit()
    return _get(conn, cur_id)


def get_day_adjustment(conn: sqlite3.Connection, date: str, *, ensure: bool = True,
                       today: str | None = None) -> dict:
    """{state, adjustment|None}. state: none|future|proposed|accepted|declined|undone|expired|stale."""
    today = _today(today)
    adj = ensure_proposal(conn, date, today=today) if ensure else _live(conn, date)
    if adj is None:
        return {"state": "future" if date > today else "none", "adjustment": None}
    return {"state": state_of(conn, adj, today), "adjustment": adj}


def _load_for_decision(conn: sqlite3.Connection, adj_id: int, today: str | None) -> tuple[dict, str]:
    adj = _get(conn, adj_id)
    if adj is None:
        raise AdjustmentConflict("NOT_FOUND", "조정을 찾을 수 없어요")
    return adj, _today(today)


def _decide(conn: sqlite3.Connection, adj: dict, decision: str, via: str | None, today: str) -> dict:
    via = via if via in VIAS else None
    accepted_at = "datetime('now')" if decision == "accepted" else "accepted_at"
    try:
        conn.execute(f"UPDATE plan_adjustments SET decision=?, decided_via=?, decided_at=datetime('now'),"
                     f" accepted_at={accepted_at}, updated_at=datetime('now') WHERE id=?",
                     (decision, via, adj["id"]))
    except sqlite3.IntegrityError:
        conn.rollback()
        raise AdjustmentConflict("INVALID_TRANSITION", "이미 적용 중인 조정이 있어요", _get(conn, adj["id"]))
    conn.commit()
    return _view(conn, _get(conn, adj["id"]), today)


def accept(conn: sqlite3.Connection, adj_id: int, *, rev: int, via: str | None = None,
           today: str | None = None) -> dict:
    """proposed|reverted(당일) → accepted. 이미 accepted 면 그대로 반환(멱등)."""
    adj, today = _load_for_decision(conn, adj_id, today)
    if adj["rev"] != rev:
        raise AdjustmentConflict("REV_MISMATCH", "제안이 바뀌었어요", _view(conn, adj, today))
    if adj["decision"] == "accepted":
        return _view(conn, adj, today)
    if adj["date"] != today:
        raise AdjustmentConflict("LOCKED", "당일만 바꿀 수 있어요", _view(conn, adj, today))
    if _is_stale(conn, adj):
        raise AdjustmentConflict("STALE", "원본 계획이 바뀌었어요", _view(conn, adj, today))
    return _decide(conn, adj, "accepted", via, today)


def revert(conn: sqlite3.Connection, adj_id: int, *, via: str | None = None, today: str | None = None) -> dict:
    """proposed → reverted(거절), accepted → reverted(되돌리기). 당일만. 이미 reverted 면 그대로."""
    adj, today = _load_for_decision(conn, adj_id, today)
    if adj["decision"] == "reverted":
        return _view(conn, adj, today)
    if adj["date"] != today:
        raise AdjustmentConflict("LOCKED", "당일만 바꿀 수 있어요", _view(conn, adj, today))
    return _decide(conn, adj, "reverted", via, today)


def list_adjustments(conn: sqlite3.Connection, *, goal_id: int | None, start: str, end: str,
                     today: str | None = None) -> list[dict]:
    """[start, end] 기간 이력(최신순), 표시 상태 포함."""
    today = _today(today)
    q = f"SELECT {_COLS} FROM plan_adjustments WHERE date BETWEEN ? AND ?"
    args: list = [start, end]
    if goal_id is not None:
        q += " AND goal_id = ?"
        args.append(goal_id)
    rows = conn.execute(q + " ORDER BY date DESC, id DESC", args).fetchall()
    return [_view(conn, _to_dict(r), today) for r in rows]
