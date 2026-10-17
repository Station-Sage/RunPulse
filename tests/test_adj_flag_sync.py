"""R3 — adj_accepted 가 plan_adjustments(accepted) 와 동기화된다."""
from __future__ import annotations

import sqlite3

from src.db_setup import create_tables, migrate_db
from src.services.plan_adj_flag import sync_adj_flag


def _adj(c, wid, decision):
    c.execute("INSERT INTO plan_adjustments (goal_id, workout_id, date, source, before_json, after_json, rule_version, decision)"
              " VALUES (1, ?, '2026-10-20', 'user', '{}', '{}', 'v', ?)", (wid, decision))


def test_flag_follows_accepted_adjustment():
    c = sqlite3.connect(":memory:")
    create_tables(c)
    migrate_db(c)
    c.execute("INSERT INTO goals (id, name, distance_km, status) VALUES (1, 'g', 21.1, 'active')")
    c.execute("INSERT INTO planned_workouts (id, date, workout_type, distance_km, source, goal_id) VALUES"
              " (1, '2026-10-20', 'easy', 8, 'planner', 1)")
    sync_adj_flag(c, [1])
    assert c.execute("SELECT adj_accepted FROM planned_workouts WHERE id=1").fetchone()[0] == 0
    _adj(c, 1, "proposed")
    sync_adj_flag(c, [1])
    assert c.execute("SELECT adj_accepted FROM planned_workouts WHERE id=1").fetchone()[0] == 0
    c.execute("UPDATE plan_adjustments SET decision='accepted'")
    sync_adj_flag(c, [1, None])
    assert c.execute("SELECT adj_accepted FROM planned_workouts WHERE id=1").fetchone()[0] == 1
    c.execute("UPDATE plan_adjustments SET decision='reverted'")
    sync_adj_flag(c, [1])
    assert c.execute("SELECT adj_accepted FROM planned_workouts WHERE id=1").fetchone()[0] == 0
