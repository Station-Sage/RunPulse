"""training_balance_service + T1 조회 함수(metrics_service as-of·plan_load 계획 km) — 빈 DB·정상·누수 (§8 T1·T2)."""
import json
import sqlite3
from datetime import date, timedelta

import pytest

from src.db_setup import create_tables
from src.services import metrics_service, plan_load
from src.services import training_balance_service as svc

AS_OF = "2026-11-06"
D0 = date.fromisoformat(AS_OF)


def _d(n: int) -> str:
    return (D0 - timedelta(days=n)).isoformat()


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    create_tables(c)
    yield c
    c.close()


def _metric(c, day, name, value=None, js=None):
    c.execute("INSERT INTO metric_store(scope_type, scope_id, metric_name, category, provider, numeric_value,"
              " json_value, is_primary) VALUES ('daily', ?, ?, 'load', 'runpulse:formula_v1', ?, ?, 1)",
              (day, name, value, json.dumps(js) if js is not None else None))


def _seed_full(c):
    for w in range(10):  # 10주 이력 marathon_shape (최고 40)
        _metric(c, _d(7 * w), "marathon_shape", 37.0,
                {"weekly_km_8w": 35.5 if w == 0 else 40.0 - (w - 1) * 0.5, "longest_12w_km": 24.2, "tanda_required_km": 96.6})
    _metric(c, AS_OF, "tids", None, {"low_pct": 83.1, "mid_pct": 8.9, "high_pct": 8.0, "pattern": "pyramidal"})
    _metric(c, AS_OF, "acwr", 1.11)
    _metric(c, AS_OF, "tsb", 7.0)
    _metric(c, AS_OF, "monotony", 0.98)
    for i in range(60):
        c.execute("INSERT INTO daily_wellness(date, sleep_score, hrv_last_night, avg_stress) VALUES (?,?,?,?)",
                  (_d(i), 70, 50, 30))
    c.execute("INSERT INTO goals(name, distance_km, race_date, status) VALUES ('풀', 42.195, ?, 'active')",
              ((D0 + timedelta(days=60)).isoformat(),))
    c.commit()


def test_t1_empty_db_returns_empty(conn):
    assert metrics_service.get_daily_metric_as_of(conn, "tids", AS_OF) is None
    assert metrics_service.get_daily_series(conn, "tids", _d(30), AS_OF) == []
    assert plan_load.weekly_planned_km(conn, _d(56), AS_OF) == {}
    assert plan_load.longest_planned_long_km(conn, _d(56), AS_OF) is None


def test_t1_as_of_never_reads_future(conn):
    _metric(conn, _d(3), "acwr", 1.0)
    _metric(conn, (D0 + timedelta(days=1)).isoformat(), "acwr", 2.0)
    p = metrics_service.get_daily_metric_as_of(conn, "acwr", AS_OF)
    assert p == {"date": _d(3), "value": 1.0, "json": None}
    assert metrics_service.get_daily_metric_as_of(conn, "acwr", AS_OF, max_age_days=2) is None


def test_t1_weekly_planned_km_and_longest(conn):
    rows = [("2026-11-02", "easy", 8), ("2026-11-04", "rest", None), ("2026-11-08", "long", 24),
            ("2026-11-10", "long_mp", 28), ("2026-10-27", "rest", None)]
    conn.executemany("INSERT INTO planned_workouts(date, workout_type, distance_km) VALUES (?,?,?)", rows)
    assert plan_load.weekly_planned_km(conn, "2026-10-26", "2026-11-09") == {"2026-10-26": 0.0, "2026-11-02": 32.0}
    assert plan_load.longest_planned_long_km(conn, "2026-10-26", "2026-11-20") == 28.0


def test_empty_db_is_collecting_not_error(conn):
    r = svc.get_training_balance(conn, AS_OF)
    assert r["state"] == "collecting" and len(r["axes"]) == 6
    reasons = {a["key"]: a["reason"] for a in r["axes"]}
    assert reasons == {"volume": "no_shape", "long_run": "no_shape", "easy_base": "insufficient_runs",
                       "quality": "insufficient_runs", "load": "acwr_warmup", "recovery": "no_wellness"}
    assert r["notes"] == []


def test_full_data_ready_and_expected_scores(conn):
    _seed_full(conn)
    r = svc.get_training_balance(conn, AS_OF, compare_days=0)
    by = {a["key"]: a for a in r["axes"]}
    assert r["state"] == "ready" and r["compare"] is None
    assert by["volume"]["basis"] == "personal_peak" and by["volume"]["target"] == 40.0 and by["volume"]["score"] == 88.8
    assert by["long_run"]["basis"] == "goal" and by["long_run"]["score"] == pytest.approx(80.7)
    assert by["easy_base"]["score"] == 103.9 and by["quality"]["score"] == 84.5
    assert by["load"]["score"] == 111.0 and by["recovery"]["score"] == 100.0
    assert r["aux"] == {"tsb": 7.0, "monotony": 0.98, "tanda_required_km": 96.6, "tids_pattern": "pyramidal",
                        "race_share_of_quality": None}
    assert "quality_includes_races" in r["notes"] and "volume_personal_peak" in r["notes"]


def test_plan_target_beats_peak_and_goal(conn):
    _seed_full(conn)
    ws = D0 - timedelta(days=D0.weekday())
    for w in range(4):
        conn.execute("INSERT INTO planned_workouts(date, workout_type, distance_km) VALUES (?, 'easy', 50)",
                     ((ws - timedelta(days=7 * w)).isoformat(),))
    conn.execute("INSERT INTO planned_workouts(date, workout_type, distance_km) VALUES (?, 'long', 32)",
                 ((D0 + timedelta(days=10)).isoformat(),))
    by = {a["key"]: a for a in svc.get_training_balance(conn, AS_OF, 0)["axes"]}
    assert (by["volume"]["basis"], by["volume"]["target"]) == ("plan", 50.0)
    assert (by["long_run"]["basis"], by["long_run"]["target"]) == ("plan", 32.0)
    assert "planned_workouts" in by["volume"]["source"]


def test_partial_state_with_four_axes(conn):
    _seed_full(conn)
    conn.execute("DELETE FROM metric_store WHERE metric_name='acwr'")
    conn.execute("DELETE FROM daily_wellness")
    assert svc.get_training_balance(conn, AS_OF, 0)["state"] == "partial"


def test_compare_does_not_leak_future(conn):
    _metric(conn, AS_OF, "tids", None, {"low_pct": 80.0, "mid_pct": 10.0, "high_pct": 10.0})
    _metric(conn, AS_OF, "acwr", 1.0)
    _metric(conn, _d(30), "acwr", 0.8)
    r = svc.get_training_balance(conn, AS_OF, compare_days=28)
    cmp = {a["key"]: a["score"] for a in r["compare"]["axes"]}
    assert r["compare"]["as_of"] == _d(28)
    assert cmp["easy_base"] is None and cmp["load"] == 80.0


def test_past_goal_ignored(conn):
    _seed_full(conn)
    conn.execute("UPDATE goals SET race_date = ?", (_d(5),))
    by = {a["key"]: a for a in svc.get_training_balance(conn, AS_OF, 0)["axes"]}
    assert by["long_run"]["basis"] == "default_rule" and by["long_run"]["target"] == 12.0


def test_finished_plan_long_run_not_used(conn):
    _seed_full(conn)
    conn.execute("INSERT INTO planned_workouts(date, workout_type, distance_km) VALUES (?, 'long', 14.6)", (_d(12),))
    by = {a["key"]: a for a in svc.get_training_balance(conn, AS_OF, 0)["axes"]}
    assert by["long_run"]["basis"] == "goal"
    conn.execute("INSERT INTO planned_workouts(date, workout_type, distance_km) VALUES (?, 'easy', 8)", (AS_OF,))
    by = {a["key"]: a for a in svc.get_training_balance(conn, AS_OF, 0)["axes"]}
    assert (by["long_run"]["basis"], by["long_run"]["target"]) == ("plan", 14.6)
