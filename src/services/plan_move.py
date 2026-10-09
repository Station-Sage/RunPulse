"""일정 이동(move) 조정 — 오늘 세션을 같은 주 가까운 날로 옮기거나 쉬운 날과 맞바꾼다 (ADR-035 후속, DESIGN-PLAN-ROW-ACTION-COACHING §1)."""
from __future__ import annotations

from src.training.goals import get_active_goal
import json
import sqlite3
from datetime import date as _date, timedelta

HARD = {"interval", "tempo", "threshold", "marathon", "long_mp", "long", "race"}
Q_TYPES = HARD - {"long", "race"}
EASY = {"easy", "recovery"}
MAX_AHEAD_DAYS = 3
_FIELDS = ("workout_type", "distance_km", "target_pace_min", "target_pace_max", "description")


def _fail(code: str, message: str):
    from src.services.plan_adjustment_service import AdjustmentConflict
    raise AdjustmentConflict(code, message)


def _live_moves(conn: sqlite3.Connection, workout_id: int) -> list[tuple[int, str, str]]:
    """(id, 원래 날짜, 옮겨진 날짜) — accepted move 행."""
    rows = conn.execute("SELECT id, date, json_extract(after_json,'$.date') FROM plan_adjustments"
                        " WHERE workout_id=? AND op='move' AND decision='accepted'", (workout_id,)).fetchall()
    return [tuple(r) for r in rows]


def overlay_date(conn: sqlite3.Connection, workout_id: int, raw_date: str) -> str:
    """수락된 move 가 적용된 세션의 표시 날짜. 없으면 원본 날짜."""
    for _id, origin, dest in _live_moves(conn, workout_id):
        if origin == raw_date and dest:
            return dest
    return raw_date


def date_ok(conn: sqlite3.Connection, adj: dict, raw_date: str) -> bool:
    """조정 행의 날짜가 원본 행과 맞는지 — 원본 날짜이거나, 그 날짜로 옮겨진 move 의 원래 날짜."""
    if raw_date == adj["date"]:
        return True
    return any(origin == raw_date and dest == adj["date"] for _id, origin, dest in _live_moves(conn, adj["workout_id"]))


def _effective_types(conn: sqlite3.Connection, start: _date, end: _date) -> dict[str, dict]:
    """[start,end] 날짜별 조정 반영 유효 계획 행."""
    from src.training.planned_query import get_planned_workouts
    from src.training.week_compliance import _effective
    by_date: dict[str, list[dict]] = {}
    ws = start - timedelta(days=start.weekday())
    while ws <= end:
        for w in get_planned_workouts(conn, ws):
            if not w.get("superseded"):
                by_date.setdefault(w["date"], []).append(w)
        ws += timedelta(days=7)
    return {d: _effective(rows)[0] for d, rows in by_date.items()}


def _race_date(conn: sqlite3.Connection) -> str | None:
    g = get_active_goal(conn)
    return g["race_date"] if g and g["race_date"] else None


def validate(conn: sqlite3.Connection, workout_id: int, to_date: str, reason: str | None,
             today: str) -> tuple[dict, dict | None]:
    """M1~M10 검증. (출발 유효 행, 도착 유효 행|None) 반환, 거부 시 AdjustmentConflict(code)."""
    try:
        to = _date.fromisoformat(to_date)
    except (TypeError, ValueError):
        raise ValueError("to_date(YYYY-MM-DD) 필요")
    td = _date.fromisoformat(today)
    plans = _effective_types(conn, td - timedelta(days=1), to + timedelta(days=1))
    src = plans.get(today)
    if src is None or src["id"] != workout_id:
        _fail("ALREADY_MOVED" if any(d == today for _i, _o, d in _live_moves(conn, workout_id)) else "NOT_TODAY",
              "이미 옮겨진 세션이에요" if _live_moves(conn, workout_id) else "오늘 세션만 옮길 수 있어요")
    stype = src["workout_type"]
    if stype == "race":
        _fail("RACE_FIXED", "레이스는 옮길 수 없어요")
    if reason == "pain":
        _fail("PAIN_NO_MOVE", "통증이 있으면 옮기지 말고 쉬어 주세요")
    if not td < to <= td + timedelta(days=MAX_AHEAD_DAYS):
        _fail("OUT_OF_RANGE", f"내일부터 {MAX_AHEAD_DAYS}일 이내로만 옮길 수 있어요")
    if to.isocalendar()[:2] != td.isocalendar()[:2]:
        _fail("CROSS_WEEK", "같은 주 안에서만 옮길 수 있어요")
    race = _race_date(conn)
    if race:
        rd = _date.fromisoformat(race)
        if (stype in Q_TYPES and to >= rd - timedelta(days=3)) or (stype == "long" and to >= rd - timedelta(days=10)):
            _fail("TAPER_LOCK", "대회 직전 테이퍼 기간에는 옮길 수 없어요")
    tgt = plans.get(to_date)
    if tgt and (tgt.get("completed") or tgt.get("matched_activity_id")):
        _fail("TARGET_DONE", "이미 수행한 날이에요")
    if tgt and tgt["workout_type"] not in EASY | {"rest"}:
        _fail("TARGET_HARD", "그날도 강한 훈련이 있어요")
    if stype in HARD:
        for n in (to - timedelta(days=1), to + timedelta(days=1)):
            nw = plans.get(n.isoformat())
            if n.isoformat() != today and nw and nw["workout_type"] in HARD:
                _fail("HARD_SPACING", "강한 훈련이 연속돼요 · 다른 날을 골라 주세요")
    swap = tgt if tgt and tgt["workout_type"] in EASY else None
    return src, swap


def _fields(w: dict) -> dict:
    return {k: w.get(k) for k in _FIELDS}


def create_move(conn: sqlite3.Connection, workout_id: int, params: dict, *, via: str | None, today: str,
                goal_id: int | None) -> int:
    """검증 후 move(+swap) 행을 한 트랜잭션으로 accepted 저장. 이동 행 id 반환 (commit 은 호출자)."""
    to_date = str(params.get("to_date") or "")
    reason = params.get("reason")
    src, swap = validate(conn, workout_id, to_date, reason, today)
    raw = conn.execute("SELECT date, workout_type, distance_km FROM planned_workouts WHERE id=?",
                       (workout_id,)).fetchone()
    reasons = [{"key": "user", "label": str(reason)}] if reason else []
    ins = ("INSERT INTO plan_adjustments(goal_id, workout_id, date, source, op, before_json, after_json,"
           " reasons_json, rule_version, decision, decided_via, accepted_at, decided_at)"
           " VALUES (?,?,?,'user','move',?,?,?,'user_v1','accepted',?,datetime('now'),datetime('now'))")
    before = {"workout_type": raw[1], "distance_km": raw[2]}
    move_id = conn.execute(ins, (goal_id, workout_id, raw[0], json.dumps(before),
                                 json.dumps({**_fields(src), "date": to_date}),
                                 json.dumps(reasons, ensure_ascii=False), via)).lastrowid
    if swap:
        sraw = conn.execute("SELECT date, workout_type, distance_km FROM planned_workouts WHERE id=?",
                            (swap["id"],)).fetchone()
        swap_id = conn.execute(ins, (goal_id, swap["id"], sraw[0], json.dumps({"workout_type": sraw[1],
                               "distance_km": sraw[2]}), json.dumps({**_fields(swap), "date": today}),
                               json.dumps([{"key": "pair", "adj_id": move_id}], ensure_ascii=False), via)).lastrowid
        conn.execute("UPDATE plan_adjustments SET reasons_json=? WHERE id=?",
                     (json.dumps(reasons + [{"key": "pair", "adj_id": swap_id}], ensure_ascii=False), move_id))
    return move_id


def partner_id(adj: dict) -> int | None:
    return next((r.get("adj_id") for r in adj.get("reasons") or [] if r.get("key") == "pair"), None)


def revert_dependents(conn: sqlite3.Connection, adj: dict, partner: dict | None) -> None:
    """move 쌍을 되돌릴 때 그 뒤에 쌓인 같은 workout 의 다른 조정(줄이기 등)도 함께 되돌린다."""
    ids = [adj["workout_id"]] + ([partner["workout_id"]] if partner else [])
    marks = ",".join("?" * len(ids))
    conn.execute(f"UPDATE plan_adjustments SET decision='reverted', decided_at=datetime('now') WHERE workout_id IN ({marks})"
                 " AND op != 'move' AND id > ? AND decision IN ('proposed','accepted')", (*ids, min(adj["id"], partner["id"] if partner else adj["id"])))
