"""수락된 계획 조정(plan_adjustments)을 planned_workouts 행에 읽기 시점으로 겹쳐 적용 (ADR-035)."""
from __future__ import annotations

import json
import sqlite3

_FIELDS = ("workout_type", "distance_km", "target_pace_min", "target_pace_max", "description")


def live_adjustments(conn: sqlite3.Connection, start: str, end: str) -> dict[int, dict]:
    """[start, end) 안의 accepted 조정을 {workout_id: row}로. 한 workout 에 여럿이면 최신 id."""
    rows = conn.execute(
        """SELECT id, workout_id, date, source, op, before_json, after_json, decided_at
           FROM plan_adjustments WHERE decision = 'accepted' AND date >= ? AND date < ?
           ORDER BY id""", (start, end)).fetchall()
    out: dict[int, dict] = {}
    for r in rows:
        out[r[1]] = {"id": r[0], "workout_id": r[1], "date": r[2], "source": r[3], "op": r[4],
                     "before": json.loads(r[5] or "{}"), "after": json.loads(r[6] or "{}"),
                     "decided_at": r[7]}
    return out


def _matches(row: dict, adj: dict) -> bool:
    b = adj["before"]
    return row["date"] == adj["date"] and row.get("workout_type") == b.get("workout_type") \
        and row.get("distance_km") == b.get("distance_km")


def apply(rows: list[dict], adjs: dict[int, dict]) -> list[dict]:
    """원본 dict 를 복사해 after 값을 덮어쓴다. 지문이 다르면 적용하지 않고 adjustment_stale=True.

    v1 은 move 를 적용하지 않는다(행 액션 T8 이후).
    """
    out = []
    for r in rows:
        adj = adjs.get(r["id"])
        if not adj or adj["op"] == "move":
            out.append(r)
            continue
        w = dict(r)
        if not _matches(r, adj):
            w["adjustment_stale"] = True
            out.append(w)
            continue
        w["original"] = {k: r.get(k) for k in _FIELDS}
        for k in _FIELDS:
            if k in adj["after"]:
                w[k] = adj["after"][k]
        w["adjusted"] = True
        w["adjustment"] = {k: adj[k] for k in ("id", "source", "op", "decided_at")}
        out.append(w)
    return out
