import sqlite3
import json
import pytest
from src.db_setup import create_tables
from src.utils.db_helpers import upsert_metric
from src.metrics.base import CalcContext
from src.metrics.marathon_shape import MarathonShapeCalculator

def _conn():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    create_tables(conn)
    return conn


def _seed_activity(conn, act_date="2026-04-01", **overrides):
    defaults = {
        "source": "garmin", "source_id": "1", "name": "Test Run",
        "activity_type": "running", "start_time": f"{act_date} 08:00:00",
        "distance_m": 10000, "moving_time_sec": 3000,
        "avg_hr": 155, "max_hr": 185,
    }
    defaults.update(overrides)
    cols = ", ".join(defaults.keys())
    vals = ", ".join("?" * len(defaults))
    conn.execute(f"INSERT INTO activity_summaries ({cols}) VALUES ({vals})",
                 list(defaults.values()))
    conn.commit()
    return conn.execute("SELECT last_insert_rowid()").fetchone()[0]


def _seed_wellness(conn, d="2026-04-01", **overrides):
    defaults = {"date": d, "resting_hr": 55}
    defaults.update(overrides)
    cols = ", ".join(defaults.keys())
    vals = ", ".join("?" * len(defaults))
    conn.execute(f"INSERT OR REPLACE INTO daily_wellness ({cols}) VALUES ({vals})",
                 list(defaults.values()))
    conn.commit()


def _seed_daily_metrics(conn, d, **metrics):
    for name, val in metrics.items():
        upsert_metric(conn, "daily", d, name, "runpulse:formula_v1",
                      numeric_value=val, category="rp_load")


def _seed_block(conn, weeks=8, km=12.0, pace=330, long_km=None):
    from datetime import datetime, timedelta
    n = 0
    for i in range(1, weeks * 7 + 1, 2):                   # 이틀에 한 번
        d = (datetime(2026, 4, 1) - timedelta(days=i)).strftime("%Y-%m-%d")
        dist = (long_km if (long_km and i % 14 == 1) else km) * 1000
        _seed_activity(conn, d, source_id=f"b{i}", distance_m=dist, moving_time_sec=int(dist / 1000 * pace))
        n += 1
    return n


class TestMarathonShape:
    """P7-PRED-52: v2 — Tanda 역산 필요 km 대비 볼륨 충족률, 롱런 구조 json."""

    def test_with_data(self):
        conn = _conn()
        _seed_daily_metrics(conn, "2026-04-01", race_pred_vdot=50.0)
        _seed_block(conn, long_km=24)
        r = MarathonShapeCalculator().compute(CalcContext(conn=conn, scope_type="daily", scope_id="2026-04-01"))
        jv = json.loads(r[0].json_value)
        assert r[0].numeric_value > 0 and jv["label"] in MarathonShapeCalculator.ranges
        assert jv["basis"] == "current_vdot" and jv["long_runs_12w"]["ge_21km"] >= 4 and jv["longest_12w_km"] == 24.0
        assert abs(r[0].numeric_value - jv["weekly_km_8w"] / jv["tanda_required_km"] * 100) < 0.2

    def test_no_vdot(self):
        conn = _conn()
        ctx = CalcContext(conn=conn, scope_type="daily", scope_id="2026-04-01")
        assert MarathonShapeCalculator().compute(ctx) == []

    def test_goal_basis_and_unreachable(self):
        conn = _conn()
        _seed_daily_metrics(conn, "2026-04-01", race_pred_vdot=45.0)
        _seed_block(conn, pace=420)
        conn.execute("INSERT INTO goals (name, race_date, distance_km, target_time_sec, status) "
                     "VALUES ('풀', '2026-11-22', 42.195, 9000, 'active')")      # 2:30 — 볼륨으로 도달 불가
        r = MarathonShapeCalculator().compute(CalcContext(conn=conn, scope_type="daily", scope_id="2026-04-01"))
        jv = json.loads(r[0].json_value)
        assert jv["basis"] == "goal" and jv["tanda_required_km"] is None and r[0].numeric_value is None


def test_tanda_required_roundtrip():
    from src.metrics.marathon_shape import tanda_required_km
    from src.metrics.prediction.core_r4 import tanda_marathon
    k = tanda_required_km(300.0, 330.0)
    assert k and abs(tanda_marathon(k, 330.0) / 42.195 - 300.0) < 0.5
