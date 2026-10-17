"""계획 조정 제안·수락·되돌리기 (plan_adjustments, ADR-035). 원본 planned_workouts 는 수정하지 않는다."""
from __future__ import annotations

import json
import sqlite3
from datetime import date as _date

from src.services import plan_pain
from src.services.plan_adj_flag import sync_adj_flag
from src.services.plan_adjustment_proposal import RULE_VERSION, ensure_proposal  # noqa: F401
from src.services.plan_adjustment_rows import AUTO_SQL, COLS as _COLS, get_row as _get, live_auto as _live, to_dict as _to_dict
from src.training.goals import get_active_goal

VIAS = ("plan", "session", "today", "coach")

class AdjustmentConflict(Exception):
    """code: REV_MISMATCH | LOCKED | STALE | INVALID_TRANSITION | NOT_FOUND"""

    def __init__(self, code: str, message: str = "", current: dict | None = None):
        super().__init__(message or code)
        self.code = code
        self.current = current


def _today(today: str | None) -> str:
    return today or _date.today().isoformat()


def _is_stale(conn: sqlite3.Connection, adj: dict) -> bool:
    r = conn.execute("SELECT date, workout_type, distance_km FROM planned_workouts WHERE id = ?",
                     (adj["workout_id"],)).fetchone()
    b = adj["before"]
    if not r or r[1] != b.get("workout_type") or r[2] != b.get("distance_km"):
        return True
    if r[0] == adj["date"]:
        return False
    from src.services import plan_move
    return adj["op"] == "move" or not plan_move.date_ok(conn, adj, r[0])


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


def get_day_adjustment(conn: sqlite3.Connection, date: str, *, ensure: bool = True,
                       today: str | None = None) -> dict:
    """{state, adjustment|None}. state: none|future|proposed|accepted|declined|undone|expired|stale."""
    today = _today(today)
    adj = ensure_proposal(conn, date, today=today) if ensure else _live(conn, date)
    if adj is None:
        return {"state": "future" if date > today else "none", "adjustment": None}
    return {"state": state_of(conn, adj, today), "adjustment": adj}


def get_user_adjustment(conn: sqlite3.Connection, date: str, *, today: str | None = None) -> dict | None:
    """해당 날짜의 live 사용자·코치 직접 조정(accepted). 없으면 None."""
    r = conn.execute(f"SELECT {_COLS} FROM plan_adjustments WHERE date=? AND source IN ('user','coach')"
                     " AND decision='accepted' ORDER BY id DESC LIMIT 1", (date,)).fetchone()
    return _view(conn, _to_dict(r), _today(today)) if r else None


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
    sync_adj_flag(conn, [adj["workout_id"]])
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
    partner = None
    if adj["op"] == "move":
        from src.services import plan_move
        pid = plan_move.partner_id(adj)
        partner = _get(conn, pid) if pid else None
        if adj["after"].get("date", "") < adj["date"] and partner:  # swap 행 → 이동 행으로 위임
            return revert(conn, partner["id"], via=via, today=today)
        if adj["date"] == today:
            plan_move.revert_dependents(conn, adj, partner)
            if partner:
                conn.execute("UPDATE plan_adjustments SET decision='reverted', decided_at=datetime('now') WHERE id=?",
                             (partner["id"],))
                sync_adj_flag(conn, [partner["workout_id"]])
    if adj["date"] != today:
        raise AdjustmentConflict("LOCKED", "당일만 바꿀 수 있어요", _view(conn, adj, today))
    return _decide(conn, adj, "reverted", via, today)


USER_OPS = ("reduce", "easy", "rest", "skip", "move")
COACH_OPS = ("reduce", "easy", "rest", "skip")


def _user_after(before: dict, op: str, params: dict) -> dict:
    from src.services import plan_reduce
    if op == "reduce":
        return plan_reduce.reduce_after(before, params)
    if op == "easy":
        return plan_reduce.easy_after(before)
    return {**before, "workout_type": "rest", "distance_km": None, "target_pace_min": None, "target_pace_max": None,
            "interval_prescription": None, "structure_json": None}


_BEFORE_KEYS = ("workout_type", "distance_km", "target_pace_min", "target_pace_max", "description",
                "interval_prescription", "structure_json")


def _planned_row(conn: sqlite3.Connection, workout_id: int) -> tuple:
    r = conn.execute("SELECT date, " + ", ".join(_BEFORE_KEYS) + " FROM planned_workouts WHERE id = ?",
                     (workout_id,)).fetchone()
    if r is None:
        raise AdjustmentConflict("NOT_FOUND", "세션을 찾을 수 없어요")
    return r


def _before_after(conn: sqlite3.Connection, workout_id: int, r: tuple, odate: str, op: str, params: dict):
    before = dict(zip(_BEFORE_KEYS, r[1:8]))
    crs = conn.execute(f"SELECT after_json FROM plan_adjustments WHERE workout_id=? AND date=? AND source IN ({AUTO_SQL})"
                       " AND decision='accepted' ORDER BY id DESC LIMIT 1", (workout_id, odate)).fetchone()
    return before, _user_after({**before, **json.loads(crs[0])} if crs else before, op, params)


def preview_after(conn: sqlite3.Connection, workout_id: int, op: str, params: dict | None = None) -> dict | None:
    """저장 없이 op 적용 후의 세션 값. move 는 부하가 변하지 않으므로 None. 입력 오류는 ValueError."""
    if op not in USER_OPS:
        raise ValueError(f"지원하지 않는 op: {op}")
    r = _planned_row(conn, workout_id)
    if op == "move":
        return None
    from src.services import plan_move
    return _before_after(conn, workout_id, r, plan_move.overlay_date(conn, workout_id, r[0]), op, params or {})[1]


def create_user_adjustment(conn: sqlite3.Connection, workout_id: int, op: str, params: dict | None = None,
                           source: str = "user", *, via: str | None = None, today: str | None = None) -> dict:
    """행 액션·Coach 제안 → 즉시 accepted 조정 생성. 당일만. 기존 live(같은 source) 조정은 reverted 처리.

    op: reduce(pct)|rest|skip|move(to_date, plan_move 참조). coach 는 강도를 올리는 op 를 쓸 수 없다(위 op 는 모두 감소).
    ValueError → 잘못된 입력(400), AdjustmentConflict → NOT_FOUND|LOCKED|move 거부 코드(plan_move.validate).
    """
    params, today = params or {}, _today(today)
    ops = COACH_OPS if source == "coach" else USER_OPS
    if op not in ops or source not in ("user", "coach"):
        raise ValueError(f"지원하지 않는 op: {op}")
    op = plan_pain.resolve(op, params)
    r = _planned_row(conn, workout_id)
    from src.services import plan_move
    odate = plan_move.overlay_date(conn, workout_id, r[0])
    if op == "move":
        if r[0] != today and odate != today:
            raise AdjustmentConflict("LOCKED", "당일만 바꿀 수 있어요")
        goal = get_active_goal(conn)
        try:
            new_id = plan_move.create_move(conn, workout_id, params, via=via if via in VIAS else None,
                                           today=today, goal_id=goal["id"] if goal else None)
        except Exception:
            conn.rollback()
            raise
        conn.commit()
        return _view(conn, _get(conn, new_id), today)
    if odate != today:
        raise AdjustmentConflict("LOCKED", "당일만 바꿀 수 있어요")
    before, after = _before_after(conn, workout_id, r, odate, op, params)
    goal = get_active_goal(conn)
    via = via if via in VIAS else None
    conn.execute("UPDATE plan_adjustments SET decision='reverted', decided_at=datetime('now') WHERE workout_id=?"
                 f" AND date=? AND (source=? OR source IN ({AUTO_SQL})) AND decision IN ('proposed','accepted')",
                 (workout_id, odate, source))
    new_id = conn.execute(
        "INSERT INTO plan_adjustments(goal_id, workout_id, date, source, op, before_json, after_json,"
        " reasons_json, rule_version, decision, decided_via, accepted_at, decided_at)"
        " VALUES (?,?,?,?,?,?,?,?,?,'accepted',?,datetime('now'),datetime('now'))",
        (goal["id"] if goal else None, workout_id, odate, source, "replace" if op == "easy" else op,
         json.dumps(before), json.dumps(after),
         json.dumps(plan_pain.reasons(params), ensure_ascii=False), source + "_v1", via)).lastrowid
    sync_adj_flag(conn, [workout_id])
    conn.commit()
    return _view(conn, _get(conn, new_id), today)


def list_adjustments(conn: sqlite3.Connection, *, goal_id: int | None, start: str, end: str,
                     today: str | None = None) -> list[dict]:
    """[start, end] 기간 이력(최신순), 표시 상태 포함."""
    today = _today(today)
    q = f"SELECT {_COLS} FROM plan_adjustments WHERE date BETWEEN ? AND ?" + (" AND goal_id = ?" if goal_id is not None else "")
    rows = conn.execute(q + " ORDER BY date DESC, id DESC", [start, end] + ([goal_id] if goal_id is not None else [])).fetchall()
    return [_view(conn, _to_dict(r), today) for r in rows]
