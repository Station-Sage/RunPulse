"""수락된 계획 조정(plan_adjustments)을 planned_workouts 행에 읽기 시점으로 겹쳐 적용 (ADR-035)."""
from __future__ import annotations

import json
import sqlite3

_FIELDS = ("workout_type", "distance_km", "target_pace_min", "target_pace_max", "description",
           "interval_prescription", "structure_json")


def live_adjustments(conn: sqlite3.Connection, start: str, end: str) -> dict[int, list[dict]]:
    """[start, end) 안의 accepted 조정을 {workout_id: [행...]}로. 적용 순서: move → 그 밖 op(workout당 최신 1건)."""
    rows = conn.execute(
        """SELECT id, workout_id, date, source, op, before_json, after_json, decided_at
           FROM plan_adjustments WHERE decision = 'accepted' AND date >= ? AND date < ?
           ORDER BY id""", (start, end)).fetchall()
    moves: dict[int, dict] = {}
    others: dict[int, dict] = {}
    for r in rows:
        adj = {"id": r[0], "workout_id": r[1], "date": r[2], "source": r[3], "op": r[4],
               "before": json.loads(r[5] or "{}"), "after": json.loads(r[6] or "{}"), "decided_at": r[7]}
        (moves if r[4] == "move" else others)[r[1]] = adj
    return {wid: [a for a in (moves.get(wid), others.get(wid)) if a] for wid in {*moves, *others}}


def _matches(row: dict, adj: dict, *dates: str) -> bool:
    b = adj["before"]
    return adj["date"] in dates and row.get("workout_type") == b.get("workout_type") \
        and row.get("distance_km") == b.get("distance_km")


def _meta(adj: dict) -> dict:
    return {k: adj[k] for k in ("id", "source", "op", "decided_at")}


def apply(rows: list[dict], adjs: dict[int, list[dict]]) -> list[dict]:
    """원본 dict 를 복사해 after 값을 덮어쓴다. 지문이 다르면 적용하지 않고 adjustment_stale=True.

    move 는 date 를 바꾸고(original.date 에 원래 날짜), 이후 같은 workout 의 다른 op 는 옮겨진 날짜로 지문을 본다.
    """
    out, moved = [], False
    for r in rows:
        chain = adjs.get(r["id"])
        if not chain:
            out.append(r)
            continue
        w = dict(r)
        w["original"] = {k: r.get(k) for k in (*_FIELDS, "date")}
        cur_date = r["date"]
        for adj in chain:
            if not _matches(r, adj, *({r["date"]} if adj["op"] == "move" else {r["date"], cur_date})):
                out.append({**r, "adjustment_stale": True})
                break
            if adj["op"] == "move":
                w["date"] = cur_date = adj["after"]["date"]
                moved = True
            else:
                for k in _FIELDS:
                    if k in adj["after"]:
                        w[k] = adj["after"][k]
            w["adjusted"] = True
            w["adjustment"] = _meta(adj)
        else:
            out.append(w)
    return sorted(out, key=lambda x: x["date"]) if moved else out
