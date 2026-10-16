"""planned_workouts.adj_accepted 동기화 (PLN-34 b) — 불변식: adj_accepted=1 ⇔ 그 행에 decision='accepted' 조정이 존재.

토글이 아니라 EXISTS 재계산이므로 여러 조정이 공존해도 맞다. plan_adjustments 를 쓴 직후, commit 전에 호출한다.
"""
from __future__ import annotations

import sqlite3
from typing import Iterable


def sync_adj_flag(conn: sqlite3.Connection, workout_ids: Iterable[int | None]) -> None:
    """workout_ids 각 행의 adj_accepted 를 plan_adjustments 기준으로 다시 계산한다."""
    ids = sorted({int(i) for i in workout_ids if i is not None})
    if not ids:
        return
    ph = ",".join("?" * len(ids))
    conn.execute(
        f"UPDATE planned_workouts SET adj_accepted = EXISTS("
        f"SELECT 1 FROM plan_adjustments a WHERE a.workout_id = planned_workouts.id AND a.decision = 'accepted')"
        f" WHERE id IN ({ph})", ids)
