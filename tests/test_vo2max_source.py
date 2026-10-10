"""vo2max_source — 정밀값/활동값 선택 규칙."""
from src.utils.vo2max_source import garmin_vo2max_asof, garmin_vo2max_between


def _act(conn, aid, day):
    conn.execute(
        "INSERT INTO activity_summaries (id, source, source_id, start_time) VALUES (?,?,?,?)",
        (aid, "garmin", str(aid), f"{day}T07:00:00"),
    )


def _ms(conn, scope, sid, name, val):
    conn.execute(
        "INSERT INTO metric_store (scope_type, scope_id, metric_name, provider, numeric_value)"
        " VALUES (?,?,?, 'garmin', ?)", (scope, sid, name, val),
    )


def test_empty(db_conn):
    assert garmin_vo2max_asof(db_conn) == (None, None)


def test_activity_only(db_conn):
    _act(db_conn, 1, "2026-10-01")
    _ms(db_conn, "activity", "1", "vo2max_activity", 52.0)
    assert garmin_vo2max_asof(db_conn) == (52.0, "activity")


def test_precise_newer_wins(db_conn):
    _act(db_conn, 1, "2026-10-01")
    _ms(db_conn, "activity", "1", "vo2max_activity", 52.0)
    _ms(db_conn, "daily", "2026-10-09", "vo2max", 53.9)
    assert garmin_vo2max_asof(db_conn) == (53.9, "precise")


def test_activity_newer_wins_and_tie_prefers_precise(db_conn):
    _ms(db_conn, "daily", "2026-10-01", "vo2max", 53.9)
    _act(db_conn, 1, "2026-10-05")
    _ms(db_conn, "activity", "1", "vo2max_activity", 54.0)
    assert garmin_vo2max_asof(db_conn) == (54.0, "activity")
    _ms(db_conn, "daily", "2026-10-05", "vo2max", 54.3)
    assert garmin_vo2max_asof(db_conn) == (54.3, "precise")


def test_asof_and_between_bounds(db_conn):
    _ms(db_conn, "daily", "2026-09-01", "vo2max", 52.5)
    _ms(db_conn, "daily", "2026-10-09", "vo2max", 53.9)
    assert garmin_vo2max_asof(db_conn, "2026-09-30") == (52.5, "precise")
    assert garmin_vo2max_between(db_conn, "2026-09-02", "2026-10-01") == (None, None)
