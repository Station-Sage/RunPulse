"""tests/test_dashboard_service.py — Phase 5-B 서비스 레이어 테스트."""
import pytest

from src.services.dashboard_service import (
    get_dashboard_data,
    get_daily_metric_chart,
    get_pmc_chart_data,
)

DATE = "2026-04-03"


# ─────────────────────────────────────────────────────────────────────────────
# Fixture
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def conn(db_conn):
    c = db_conn

    # 활동
    c.execute("""
        INSERT INTO activity_summaries
            (source, source_id, name, activity_type, start_time,
             distance_m, duration_sec)
        VALUES
            ('garmin', 'g1', '오전 달리기', 'running', '2026-04-03T08:00:00Z', 8000, 2400),
            ('garmin', 'g2', '이전 달리기', 'running', '2026-03-30T08:00:00Z', 10000, 3000)
    """)

    # daily_wellness
    c.execute("""
        INSERT INTO daily_wellness
            (date, sleep_score, sleep_duration_sec, hrv_last_night, resting_hr,
             body_battery_high, avg_stress, steps)
        VALUES (?, 82, 25920, 42.0, 52, 78, 32, 8500)
    """, (DATE,))

    # metric_store — daily scope
    daily_metrics = [
        ("daily", DATE, "utrs",      "readiness",  "runpulse:formula_v1", 72.3, None,
         '{"components":{"sleep":85}}', 0.8, 1),
        ("daily", DATE, "cirs",      "readiness",  "runpulse:formula_v1", 28.1, None, None, None, 1),
        ("daily", DATE, "crs",       "readiness",  "runpulse:formula_v1", 65.0, None, None, None, 1),
        ("daily", DATE, "ctl",       "load",       "runpulse:formula_v1", 45.2, None, None, None, 1),
        ("daily", DATE, "atl",       "load",       "runpulse:formula_v1", 52.1, None, None, None, 1),
        ("daily", DATE, "tsb",       "load",       "runpulse:formula_v1", -6.9, None, None, None, 1),
        ("daily", DATE, "ramp_rate", "load",       "runpulse:formula_v1",  2.3, None, None, None, 1),
        ("daily", DATE, "acwr",      "load",       "runpulse:formula_v1",  1.05,None, None, None, 1),
        ("daily", DATE, "darp_5k_sec",       "prediction", "runpulse:formula_v1", 1335,  None, None, None, 1),
        ("daily", DATE, "darp_10k_sec",      "prediction", "runpulse:formula_v1", 2790,  None, None, None, 1),
        ("daily", DATE, "darp_half_sec",     "prediction", "runpulse:formula_v1", 6130,  None, None, None, 1),
        ("daily", DATE, "darp_marathon_sec", "prediction", "runpulse:formula_v1", 12900, None, None, None, 1),
    ]
    c.executemany(
        "INSERT INTO metric_store"
        " (scope_type, scope_id, metric_name, category, provider,"
        "  numeric_value, text_value, json_value, confidence, is_primary)"
        " VALUES (?,?,?,?,?,?,?,?,?,?)",
        daily_metrics,
    )
    c.commit()
    return c


# ─────────────────────────────────────────────────────────────────────────────
# get_dashboard_data
# ─────────────────────────────────────────────────────────────────────────────

def test_get_dashboard_data_full(conn):
    result = get_dashboard_data(conn, DATE)
    assert result["date"] == DATE
    assert "wellness" in result
    assert "readiness" in result
    assert "training_status" in result
    assert "recent_activities" in result
    assert "race_predictions" in result
    assert "weekly_summary" in result


def test_get_dashboard_data_wellness(conn):
    result = get_dashboard_data(conn, DATE)
    assert result["wellness"]["sleep_score"] == 82
    assert result["wellness"]["resting_hr"] == 52


def test_get_dashboard_data_readiness_values(conn):
    result = get_dashboard_data(conn, DATE)
    utrs = result["readiness"]["utrs"]
    assert utrs is not None
    assert utrs["value"] == 72.3
    assert utrs["level"] == "양호"
    assert "components" in utrs

    cirs = result["readiness"]["cirs"]
    assert cirs["value"] == 28.1
    assert cirs["level"] == "보통"


def test_get_dashboard_data_training_status(conn):
    result = get_dashboard_data(conn, DATE)
    ts = result["training_status"]
    assert ts["ctl"] == 45.2
    assert ts["atl"] == 52.1
    assert ts["tsb"] == -6.9
    assert ts["ramp_rate"] == 2.3
    assert ts["acwr"] == 1.05


def test_get_dashboard_training_phase_maintaining(conn):
    result = get_dashboard_data(conn, DATE)
    # tsb=-6.9(>-5 기준 않됨, >5 안됨), ramp_rate=2.3(<3, >-3) → maintaining
    assert result["training_status"]["training_phase"] == "maintaining"


def test_get_dashboard_data_race_predictions(conn):
    result = get_dashboard_data(conn, DATE)
    rp = result["race_predictions"]
    assert rp["darp_5k"] == 1335
    assert rp["darp_10k"] == 2790
    assert rp["darp_half"] == 6130
    assert rp["darp_marathon"] == 12900


def test_get_dashboard_data_weekly_summary(conn):
    result = get_dashboard_data(conn, DATE)
    ws = result["weekly_summary"]
    assert ws["run_count"] >= 1
    assert ws["total_distance_m"] > 0


def test_get_dashboard_data_no_wellness(db_conn):
    """wellness 데이터 없으면 wellness={}."""
    result = get_dashboard_data(db_conn, DATE)
    assert result["wellness"] == {}


def test_get_dashboard_data_no_metrics(db_conn):
    """메트릭 없으면 readiness 전부 None."""
    result = get_dashboard_data(db_conn, DATE)
    assert result["readiness"]["utrs"] is None
    assert result["readiness"]["cirs"] is None
    assert result["readiness"]["crs"] is None
    assert result["training_status"]["ctl"] is None


def test_get_dashboard_data_default_date(conn):
    """date=None이면 오늘 날짜 사용 (에러 없음)."""
    result = get_dashboard_data(conn, None)
    assert "date" in result
    assert result["date"] is not None


# ─────────────────────────────────────────────────────────────────────────────
# get_pmc_chart_data
# ─────────────────────────────────────────────────────────────────────────────

def test_get_pmc_chart_data(conn):
    rows = get_pmc_chart_data(conn, days=3650)
    assert isinstance(rows, list)
    assert len(rows) >= 1
    row = next(r for r in rows if r["date"] == DATE)
    assert row["ctl"] == 45.2
    assert row["atl"] == 52.1
    assert row["tsb"] == -6.9


def test_get_pmc_chart_data_structure(conn):
    rows = get_pmc_chart_data(conn, days=3650)
    for row in rows:
        assert "date" in row
        assert "ctl" in row
        assert "atl" in row
        assert "tsb" in row


def test_get_pmc_chart_data_empty(db_conn):
    rows = get_pmc_chart_data(db_conn, days=90)
    assert rows == []


# ─────────────────────────────────────────────────────────────────────────────
# get_daily_metric_chart
# ─────────────────────────────────────────────────────────────────────────────

def test_get_daily_metric_chart(conn):
    rows = get_daily_metric_chart(conn, "utrs", days=3650)
    assert len(rows) >= 1
    assert rows[0]["date"] == DATE
    assert rows[0]["value"] == 72.3


def test_get_daily_metric_chart_empty(db_conn):
    rows = get_daily_metric_chart(db_conn, "utrs", days=30)
    assert rows == []


def test_get_daily_metric_chart_nonexistent_metric(conn):
    rows = get_daily_metric_chart(conn, "nonexistent_metric", days=30)
    assert rows == []
