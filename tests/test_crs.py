import sqlite3
import json
import pytest
from src.db_setup import create_tables
from src.utils.db_helpers import upsert_metric
from src.metrics.base import CalcContext
from src.metrics.crs import CRSCalculator, evaluate

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


class TestCRS:
    def test_full_level(self):
        conn = _conn()
        _seed_wellness(conn, "2026-04-01", body_battery_high=80, hrv_weekly_avg=55)
        _seed_daily_metrics(conn, "2026-04-01",
                            acwr=1.1, tsb=5.0, cirs=20.0, utrs=75.0)
        ctx = CalcContext(conn=conn, scope_type="daily", scope_id="2026-04-01")
        results = CRSCalculator().compute(ctx)
        assert len(results) == 1
        jv = json.loads(results[0].json_value) if isinstance(results[0].json_value, str) else results[0].json_value
        assert jv["level"] >= 3

    def test_high_acwr_restricts(self):
        conn = _conn()
        _seed_wellness(conn, "2026-04-01")
        _seed_daily_metrics(conn, "2026-04-01",
                            acwr=1.8, tsb=-10.0, cirs=30.0, utrs=60.0)
        ctx = CalcContext(conn=conn, scope_type="daily", scope_id="2026-04-01")
        results = CRSCalculator().compute(ctx)
        jv = json.loads(results[0].json_value) if isinstance(results[0].json_value, str) else results[0].json_value
        assert jv["level"] <= 1

    def test_low_body_battery(self):
        conn = _conn()
        _seed_wellness(conn, "2026-04-01", body_battery_high=15)
        _seed_daily_metrics(conn, "2026-04-01",
                            acwr=1.0, tsb=0.0, cirs=20.0, utrs=60.0)
        ctx = CalcContext(conn=conn, scope_type="daily", scope_id="2026-04-01")
        results = CRSCalculator().compute(ctx)
        jv = json.loads(results[0].json_value) if isinstance(results[0].json_value, str) else results[0].json_value
        assert jv["level"] == 0

    def test_boost_condition(self):
        conn = _conn()
        _seed_wellness(conn, "2026-04-01", body_battery_high=90, hrv_weekly_avg=60)
        _seed_daily_metrics(conn, "2026-04-01",
                            acwr=1.1, tsb=10.0, cirs=10.0, utrs=85.0)
        ctx = CalcContext(conn=conn, scope_type="daily", scope_id="2026-04-01")
        results = CRSCalculator().compute(ctx)
        jv = json.loads(results[0].json_value) if isinstance(results[0].json_value, str) else results[0].json_value
        assert jv["level"] == 4
        assert jv["boost_allowed"] is True

    def test_no_signals(self):
        conn = _conn()
        _seed_wellness(conn, "2026-04-01")
        ctx = CalcContext(conn=conn, scope_type="daily", scope_id="2026-04-01")
        results = CRSCalculator().compute(ctx)
        assert len(results) == 1
        jv = json.loads(results[0].json_value) if isinstance(results[0].json_value, str) else results[0].json_value
        assert jv["level"] >= 3

    def test_category(self):
        conn = _conn()
        _seed_wellness(conn, "2026-04-01")
        _seed_daily_metrics(conn, "2026-04-01", acwr=1.1, utrs=70.0)
        ctx = CalcContext(conn=conn, scope_type="daily", scope_id="2026-04-01")
        results = CRSCalculator().compute(ctx)
        assert results[0].category == "readiness"


# ── evaluate(): 저장된 CRS 읽기 ────────────────────────────────────────

D = "2026-04-01"


def _store_crs(conn, d, jv, provider="runpulse:formula_v1"):
    upsert_metric(conn, "daily", d, "crs", provider, numeric_value=60.0,
                  category="readiness", json_value=jv)


def _raw_crs(conn, d, raw_json, provider="runpulse:formula_v1"):
    """손상 JSON 주입용 직접 INSERT (upsert_metric 은 dict 만 받는다)."""
    conn.execute(
        "INSERT INTO metric_store (scope_type, scope_id, metric_name, category, provider, "
        "json_value, is_primary) VALUES ('daily', ?, 'crs', 'readiness', ?, ?, 1)",
        (d, provider, raw_json))
    conn.commit()


class TestEvaluate:
    def test_roundtrip_matches_calculator_output(self):
        conn = _conn()
        _seed_wellness(conn, D, body_battery_high=80, hrv_weekly_avg=55)
        _seed_daily_metrics(conn, D, acwr=1.1, tsb=5.0, cirs=20.0, utrs=75.0)
        ctx = CalcContext(conn=conn, scope_type="daily", scope_id=D)
        r = CRSCalculator().compute(ctx)[0]
        jv = json.loads(r.json_value) if isinstance(r.json_value, str) else r.json_value
        _store_crs(conn, D, jv)
        got = evaluate(conn, D)
        assert got["level"] == jv["level"] and got["level_label"] == jv["level_label"]
        assert got["crs"] == jv["crs"] and got["gates"] == jv["gates"]
        assert got["signals"] == jv["signals"] and got["boost_allowed"] == jv["boost_allowed"]

    def test_no_row_returns_none(self):
        assert evaluate(_conn(), D) is None

    def test_exact_date_only(self):
        conn = _conn()
        _store_crs(conn, "2026-03-31", {"level": 1, "crs": 40.0})
        _store_crs(conn, "2026-04-02", {"level": 1, "crs": 40.0})
        assert evaluate(conn, D) is None
        assert evaluate(conn, "2026-03-31")["level"] == 1

    def test_ignores_non_primary_other_metric_and_scope(self):
        conn = _conn()
        _store_crs(conn, D, {"level": 1, "crs": 40.0})
        conn.execute("UPDATE metric_store SET is_primary=0")
        upsert_metric(conn, "daily", D, "utrs", "runpulse:formula_v1",
                      numeric_value=70.0, json_value={"level": 2})
        upsert_metric(conn, "activity", D, "crs", "runpulse:formula_v1",
                      numeric_value=70.0, json_value={"level": 2})
        conn.execute("UPDATE metric_store SET is_primary=1 WHERE metric_name!='crs' OR scope_type!='daily'")
        assert evaluate(conn, D) is None

    def test_newest_primary_row_wins_on_same_date(self):
        # resolve_primary 가 보통 1개만 두지만, 복수일 때도 결정적이어야 한다
        conn = _conn()
        _raw_crs(conn, D, json.dumps({"level": 1}))
        _raw_crs(conn, D, json.dumps({"level": 3}), provider="other")
        assert evaluate(conn, D)["level"] == 3

    @pytest.mark.parametrize("raw", [
        "{not json", "[]", "null", "5", "{}",
        json.dumps({"level": "1"}), json.dumps({"level": 9}),
        json.dumps({"level": -1}), json.dumps({"level": True}),
        json.dumps({"level": 1.0}),
    ])
    def test_invalid_data_returns_none(self, raw):
        conn = _conn()
        _raw_crs(conn, D, raw)
        assert evaluate(conn, D) is None

    def test_field_defaults_and_type_normalization(self):
        conn = _conn()
        _raw_crs(conn, D, json.dumps({"level": 0, "crs": "x", "gates": "g",
                                      "signals": [1], "level_label": ""}))
        got = evaluate(conn, D)
        assert got == {"level": 0, "level_label": "휴식", "crs": None, "gates": [],
                       "signals": {}, "boost_allowed": False}

    def test_db_error_propagates(self):
        conn = sqlite3.connect(":memory:")   # metric_store 없음
        with pytest.raises(sqlite3.OperationalError):
            evaluate(conn, D)

    def test_does_not_write(self):
        conn = _conn()
        _store_crs(conn, D, {"level": 2, "crs": 50.0})
        before = conn.total_changes
        evaluate(conn, D)
        evaluate(conn, "2026-01-01")
        assert conn.total_changes == before


class TestCRSConfidence:
    def _jv(self, r):
        return json.loads(r.json_value) if isinstance(r.json_value, str) else r.json_value

    def test_full_inputs_with_rolling_confidence_one(self):
        conn = _conn()
        for d in ("2026-03-30", "2026-03-31", "2026-04-01"):
            _seed_wellness(conn, d, body_battery_high=80, hrv_weekly_avg=55)
        _seed_daily_metrics(conn, "2026-04-01", acwr=1.1, tsb=5.0, cirs=20.0, utrs=75.0)
        r = CRSCalculator().compute(CalcContext(conn=conn, scope_type="daily", scope_id="2026-04-01"))[0]
        assert r.confidence == pytest.approx(1.0)
        assert self._jv(r)["signals"]["hrv_rolling_days"] == 3

    def test_short_rolling_marks_estimated(self):
        conn = _conn()
        _seed_wellness(conn, "2026-04-01", body_battery_high=80, hrv_weekly_avg=55)
        _seed_daily_metrics(conn, "2026-04-01", acwr=1.1, tsb=5.0, cirs=20.0, utrs=75.0)
        r = CRSCalculator().compute(CalcContext(conn=conn, scope_type="daily", scope_id="2026-04-01"))[0]
        assert r.confidence < 1.0
        assert self._jv(r)["signals"]["hrv_rolling_days"] == 1

    def test_no_signals_confidence_zero_row_kept(self):
        conn = _conn()
        _seed_wellness(conn, "2026-04-01")
        r = CRSCalculator().compute(CalcContext(conn=conn, scope_type="daily", scope_id="2026-04-01"))[0]
        assert r.confidence == 0.0
        assert self._jv(r)["signals"]["hrv_rolling_days"] == 0
