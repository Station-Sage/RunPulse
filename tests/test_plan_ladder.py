"""품질 사다리 연결(E8) — 단계→처방 구조, 라벨 이력→단계(멱등), 거리에 안 맞으면 v1 유지."""
import json
from datetime import date, timedelta

from src.services import progression_service as PS
from src.training.goals import add_goal
from src.training.ladder_apply import apply_ladder
from tests.helpers_pred import mem_conn


def _interval_row(km=10.0):
    rx = {"sets": 5, "rep_m": 1000, "rest_sec": 120, "interval_pace": 240}
    return {"date": "2026-10-13", "workout_type": "interval", "distance_km": km, "interval_prescription": json.dumps(rx),
            "rationale": "", "target_pace_min": 240, "target_pace_max": 250}


def test_interval_step_changes_structure():
    out = apply_ladder([_interval_row()], {"interval": 3})[0]
    rep = out["structure"]["steps"][1]
    assert rep["count"] == 4 and rep["steps"][0]["dist_m"] == 1600 and "4단계" in out["rationale"]


def test_too_short_row_keeps_v1():
    r = _interval_row(5.0)
    assert apply_ladder([r], {"interval": 3})[0] == r


def test_tempo_reps_and_continuous():
    t = {"date": "2026-10-13", "workout_type": "tempo", "distance_km": 14.0, "target_pace_min": 270, "target_pace_max": 280,
         "rationale": ""}
    a = apply_ladder([t], {"tempo": 2})[0]["structure"]["steps"][1]
    assert a["count"] == 3 and a["steps"][0]["dist_m"] == 3200
    b = apply_ladder([t], {"tempo": 4})[0]["structure"]["steps"]
    assert len(b) == 1 and b[0]["min_share"] >= 0.4


def test_long_mp_ladder_caps_phase_value():
    r = {"date": "2026-10-18", "workout_type": "long_mp", "distance_km": 30.0, "mp_km": 14.0, "_mp_sec": 300,
         "target_pace_min": 330, "target_pace_max": 345, "rationale": ""}
    out = apply_ladder([r], {"long_mp": 1})[0]
    assert out["mp_km"] == 8.0 and sum(s["dist_m"] for s in out["structure"]["steps"]) == 30000


def _setup():
    c = mem_conn()
    gid = add_goal(c, "g", 42.195, (date.today() + timedelta(days=100)).isoformat(), 14400, rules_version=2)
    return c, gid


def _outcome(c, i, label, wtype="interval"):
    d = (date.today() - timedelta(days=20 - i)).isoformat()
    pid = c.execute("INSERT INTO planned_workouts(date, workout_type, source) VALUES(?,?, 'planner')", (d, wtype)).lastrowid
    c.execute("INSERT INTO session_outcomes(planned_id, date, outcome_label) VALUES(?,?,?)", (pid, d, label))
    return pid


def test_recompute_up_and_idempotent_and_down():
    c, gid = _setup()
    _outcome(c, 1, "on_target")
    p2 = _outcome(c, 2, "overperformed")
    assert PS.recompute(c, gid, "interval") == 2
    PS.on_outcome(c, p2)
    assert PS.get_step(c, gid, "interval") == 2
    _outcome(c, 3, "underperformed")
    _outcome(c, 4, "underperformed")
    assert PS.recompute(c, gid, "interval") == 1
