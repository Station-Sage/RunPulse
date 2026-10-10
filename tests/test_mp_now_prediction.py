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
