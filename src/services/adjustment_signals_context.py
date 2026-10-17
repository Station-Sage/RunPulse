"""컨텍스트 신호 illness·travel·altitude 수집 (NEW-3·9·19·33·34) — context_episodes(confirmed) 읽기 전용.

illness 는 단독 트리거(값=severity), 종료 후 7일은 context. travel/altitude 는 트리거가 아니며
적응 창 안에서는 BOOST hold, 창 밖 복귀 구간은 context 다. 창 길이 상수는 §2.7 (구현 시 값 확인 필요 표기).
"""
from __future__ import annotations

import math
import sqlite3
from datetime import date, timedelta

ILLNESS_RETURN_CONTEXT_DAYS = 7
TRAVEL_ALTITUDE_RETURN_CONTEXT_DAYS = 3
ALTITUDE_ADAPT_DAYS = 5
_COLS = "id, start_date, end_date, severity, detail_json, last_confirmed_date"


def travel_window_days(delta_h: float) -> int:
    return max(1, math.ceil((abs(delta_h) + 3) / 2))


def return_window_days(window: int) -> int:
    return max(1, window // 2)


def _item(signal: str, value, day: str, detail: dict, *, fresh: str = "fresh", role: str | None = None) -> dict:
    return {"signal": signal, "role": role, "value": value, "detail": detail, "as_of": day,
            "freshness": fresh, "provider": "context_episodes"}


def _rows(conn, kind: str, day: str) -> list[dict]:
    import json
    out = []
    for r in conn.execute(f"SELECT {_COLS} FROM context_episodes WHERE kind=? AND status='confirmed'"
                          " AND start_date<=? ORDER BY id DESC", (kind, day)).fetchall():
        d = dict(zip(_COLS.replace(" ", "").split(","), r))
        d["detail"] = json.loads(d.pop("detail_json") or "{}")
        out.append(d)
    return out


def _days(a: str, b: str) -> int:
    return (date.fromisoformat(a) - date.fromisoformat(b)).days


def collect_illness(conn: sqlite3.Connection, day: str) -> list[dict]:
    rows = _rows(conn, "illness", day)
    for e in rows:
        if e["end_date"] is None or e["end_date"] >= day:
            since = _days(day, e["last_confirmed_date"] or e["start_date"])
            fresh = "fresh" if since <= 0 else "partial" if since <= 2 else "stale"
            det = {"episode_id": e["id"], "day_n": _days(day, e["start_date"]) + 1, "site": e["detail"].get("site"),
                   "reconfirm": since >= 7}
            return [_item("illness", int(e["severity"] or 1), day, det, fresh=fresh)]
    for e in rows:
        if e["end_date"] and 0 < _days(day, e["end_date"]) <= ILLNESS_RETURN_CONTEXT_DAYS:
            return [_item("illness", False, day, {"episode_id": e["id"], "returning": True}, role="context")]
    return [_item("illness", False, day, {})]


def _travel_phase(e: dict, day: str) -> tuple[str, int] | None:
    delta = float(e["detail"].get("delta_h") or 0)
    w = travel_window_days(delta)
    n = _days(day, e["start_date"]) + 1
    end = e["end_date"]
    if end is None or day < end:
        return ("depart", n) if n <= w else None
    rw = return_window_days(w)
    k = _days(day, end)
    if k < rw:
        return "return", k + 1
    if k <= TRAVEL_ALTITUDE_RETURN_CONTEXT_DAYS:
        return "context", k
    return None


def collect_travel(conn: sqlite3.Connection, day: str) -> list[dict]:
    for e in _rows(conn, "travel", day):
        ph = _travel_phase(e, day)
        if ph is None:
            continue
        kind, n = ph
        det = {"episode_id": e["id"], "day_n": n, "direction": e["detail"].get("direction"),
               "origin": e["detail"].get("origin") or "user", "phase": kind}
        return [_item("travel", abs(float(e["detail"].get("delta_h") or 0)), day, det,
                      role="context" if kind == "context" else "hold")]
    return []


def collect_altitude(conn: sqlite3.Connection, day: str) -> list[dict]:
    for e in _rows(conn, "altitude", day):
        n = _days(day, e["start_date"]) + 1
        end = e["end_date"]
        det = {"episode_id": e["id"], "band": e["detail"].get("band"), "origin": e["detail"].get("origin") or "user"}
        val = e["detail"].get("altitude_m")
        if end is None or day < end:
            if n <= ALTITUDE_ADAPT_DAYS:
                return [_item("altitude", val, day, {**det, "day_n": n}, role="hold")]
            continue
        k = _days(day, end)
        if 0 <= k <= TRAVEL_ALTITUDE_RETURN_CONTEXT_DAYS:
            return [_item("altitude", val, day, {**det, "day_n": k, "phase": "return"}, role="context")]
    return []


def collect_context(conn: sqlite3.Connection, day: str) -> list[dict]:
    return collect_illness(conn, day) + collect_travel(conn, day) + collect_altitude(conn, day)
