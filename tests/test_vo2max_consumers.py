"""VO2max 소비처가 일별 정밀값을 쓰는지 회귀 확인."""
from src.analysis.race_readiness import assess_race_readiness
from src.analysis.trends import fitness_trend
from src.utils.metric_groups import SEMANTIC_GROUPS


def _daily(conn, day, val):
    conn.execute(
        "INSERT INTO metric_store (scope_type, scope_id, metric_name, provider, numeric_value)"
        " VALUES ('daily', ?, 'vo2max', 'garmin', ?)", (day, val),
    )


def test_fitness_trend_uses_precise(db_conn):
    from datetime import date
    _daily(db_conn, date.today().isoformat(), 53.9)
    assert fitness_trend(db_conn, weeks=1)[-1]["garmin_vo2max"] == 53.9


def test_race_readiness_uses_precise(db_conn):
    _daily(db_conn, "2026-10-09", 53.9)
    res = assess_race_readiness(db_conn)
    assert res["metrics"]["vo2max"] == 53.9


def test_semantic_group_has_daily_member():
    assert ("vo2max", "garmin") in SEMANTIC_GROUPS["vo2max"]["members"]
