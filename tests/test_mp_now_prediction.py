"""MP_now 출처 — r3 마라톤 예측 우선, 없으면 VDOT M (PLAN-ENGINE E4/X3)."""
from src.training.marathon_rules import mp_now_from_prediction
from tests.helpers_pred import mem_conn


def test_falls_back_to_vdot_when_no_prediction():
    assert mp_now_from_prediction(mem_conn(), 303.0, "2026-10-10") == 303.0
    assert mp_now_from_prediction(None, 303.0) == 303.0


def test_uses_latest_prediction_not_after_as_of():
    c = mem_conn()
    for d, v in (("2026-10-01", 13500.0), ("2026-10-08", 13285.0), ("2026-10-12", 12000.0)):
        c.execute("INSERT INTO metric_store(scope_type, scope_id, metric_name, provider, numeric_value) "
                  "VALUES ('daily', ?, 'race_pred_marathon_sec', 'runpulse:formula_v1', ?)", (d, v))
    assert abs(mp_now_from_prediction(c, 303.0, "2026-10-10") - 13285.0 / 42.195) < 1e-6


def test_run_days_default_uses_median_when_no_rest_mask():
    import sqlite3
    from datetime import date
    from src.training import planner_schedule as S
    from unittest.mock import patch
    conn = sqlite3.connect(":memory:")
    with patch.object(S, "load_prefs", return_value={"rest_weekdays_mask": 0}), \
            patch.object(S, "recent_run_days_per_week", return_value=[5, 5, 5, 4]):
        assert S._run_days(conn, date(2026, 10, 12)) == 5
    with patch.object(S, "load_prefs", return_value={"rest_weekdays_mask": 0b0000011}):
        assert S._run_days(conn) == 5
    with patch.object(S, "load_prefs", return_value={"rest_weekdays_mask": 0}), \
            patch.object(S, "recent_run_days_per_week", return_value=[]):
        assert S._run_days(conn) == 4


def test_finalize_rows_clears_rest_and_adds_mp_segment():
    from src.training.planner_v2 import _finalize_rows
    rows = [
        {"workout_type": "rest", "target_pace_min": 300, "target_pace_max": 330, "rationale": "x", "structure": {"steps": []}},
        {"workout_type": "long_mp", "distance_km": 24.0, "mp_km": 10.0, "target_pace_min": 340, "target_pace_max": 360},
    ]
    _finalize_rows(rows, 300.0)
    assert rows[0]["target_pace_min"] is None and rows[0]["rationale"] == "" and rows[0]["structure"] is None
    steps = rows[1]["structure"]["steps"]
    assert len(steps) == 2 and abs(steps[0]["dist_m"] - 14000) < 1 and abs(steps[1]["dist_m"] - 10000) < 1
