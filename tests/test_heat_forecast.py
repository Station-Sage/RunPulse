"""예보 기온 → 폭염 보정(E10) 순수 변환."""
from src.services import heat_forecast as H


def test_morning_temps_and_pct():
    h = {"time": ["2026-10-12T05:00", "2026-10-12T06:00", "2026-10-12T08:00", "2026-10-12T12:00"],
         "temperature_2m": [10, 24, 26, 35]}
    t = H.morning_temps(h)
    assert t == {"2026-10-12": 25.0}
    assert H.heat_pcts(t) == {"2026-10-12": 6.2}
    assert H.heat_pcts({"d": 12.0}) == {"d": 0.0}


def _coords_conn():
    import sqlite3
    c = sqlite3.connect(":memory:")
    c.execute("CREATE TABLE v_canonical_activities (start_lat REAL, start_lon REAL, activity_type TEXT,"
              " start_time TEXT)")
    c.execute("INSERT INTO v_canonical_activities VALUES (37.56661, 126.97801, 'running', '2026-11-01')")
    return c


def test_forecast_cache_hit_skips_getter():
    from datetime import date
    H.clear_cache()
    calls = []
    raw = {"hourly": {"time": ["2026-11-06T07:00"], "temperature_2m": [25]}}
    getter = lambda url, params=None: calls.append(params) or raw  # noqa: E731
    conn, day, t = _coords_conn(), date(2026, 11, 6), [0.0]
    first = H.forecast_heat_pct(conn, getter, day, monotonic=lambda: t[0])
    t[0] = 3 * 3600 - 1
    assert H.forecast_heat_pct(conn, getter, day, monotonic=lambda: t[0]) == first
    assert len(calls) == 1                              # 적중 → getter 0회
    t[0] = 3 * 3600 + 1
    H.forecast_heat_pct(conn, getter, day, monotonic=lambda: t[0])
    assert len(calls) == 2                              # TTL 3h 만료
    H.forecast_heat_pct(conn, getter, date(2026, 11, 7), monotonic=lambda: t[0])
    assert len(calls) == 3                              # 날짜가 키


def test_forecast_failure_not_cached():
    from datetime import date
    H.clear_cache()
    calls = []

    def bad(url, params=None):
        calls.append(1)
        raise OSError("net")
    conn = _coords_conn()
    assert H.forecast_heat_pct(conn, bad, date(2026, 11, 6)) == {}
    assert H.forecast_heat_pct(conn, bad, date(2026, 11, 6)) == {}
    assert len(calls) == 2
    assert H.cache_key(37.566, 126.978, date(2026, 11, 6)) == (37.57, 126.98, "2026-11-06")
