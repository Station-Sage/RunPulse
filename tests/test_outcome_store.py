"""P7-PRED-43: 매칭 → 세그먼트 이행률 저장."""
import json
from datetime import date

from src.training.matcher import match_week_activities
from src.utils.db_helpers import upsert_metric
from tests.helpers_pred import mem_conn, seed_laps, seed_run
from tests.test_outcome_v2 import PLAN


def _setup(structure=True):
    c = mem_conn()
    aid = seed_run(c, sid="1", date="2026-09-22", dist=9000.0, moving=2700)
    seed_laps(c, aid, [(1000, 250, 170, "INTERVAL", None, None)] * 2)
    c.execute("UPDATE activity_laps SET compliance_score=80, wkt_step_index=1 WHERE activity_id=?", (aid,))
    bouts = [{"dist_m": 1000.0, "dur_s": 250.0, "speed_ms": 4.0, "hr": 172}] * 5
    upsert_metric(c, "activity", str(aid), "workout_type_classified", "runpulse:rule_v2", text_value="interval",
                  json_value={"type": "interval", "bouts": bouts})
    c.execute("INSERT INTO planned_workouts (date, workout_type, distance_km, source, structure_json, source_system) "
              "VALUES ('2026-09-22', 'interval', 9.0, 'planner', ?, 'runpulse')",
              (json.dumps(PLAN) if structure else None,))
    return c, aid


def test_structured_plan_gets_compliance():
    c, aid = _setup()
    assert match_week_activities(c, date(2026, 9, 21)) == 1
    row = c.execute("SELECT compliance_pct, source_compliance, source_system, outcome_label, segment_match_json "
                    "FROM session_outcomes").fetchone()
    assert row[:4] == (93.3, 80.0, "runpulse", "on_target")
    assert json.loads(row[4])["sets_done"] == 5


def test_unstructured_plan_keeps_legacy_label():
    c, aid = _setup(structure=False)
    match_week_activities(c, date(2026, 9, 21))
    row = c.execute("SELECT compliance_pct, source_compliance, outcome_label FROM session_outcomes").fetchone()
    assert row[0] is None and row[1] == 80.0 and row[2] is not None
