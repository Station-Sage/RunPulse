"""여행·고지대 자동 감지 + RHR/HRV 질문 (NEW-2·8)."""
from datetime import date, timedelta

from src.services import context_autodetect as ca
from tests.helpers_pred import mem_conn, seed_run

TODAY = date(2026, 10, 17)


def _d(n):
    return (TODAY - timedelta(days=n)).isoformat()


def _tz(c, aid, v):
    c.execute("INSERT INTO metric_store(scope_type,scope_id,metric_name,provider,numeric_value)"
              " VALUES('activity',?,'timezone_offset','garmin',?)", (str(aid), v))



def test_detect_travel_flags_large_tz_shift():
    c = mem_conn()
    for n in range(5, 15):
        _tz(c, seed_run(c, sid=f"h{n}", date=_d(n)), 9.0)
    _tz(c, seed_run(c, sid="t", date=_d(0)), -5.0)
    r = ca.detect_travel(c, TODAY.isoformat())
    assert r["direction"] == "west" and r["delta_h"] == 14.0 and r["from_offset"] == 9.0


def test_detect_travel_ignores_small_shift_and_no_data():
    c = mem_conn()
    assert ca.detect_travel(c, TODAY.isoformat()) is None
    for n in range(5, 10):
        _tz(c, seed_run(c, sid=f"h{n}", date=_d(n)), 9.0)
    _tz(c, seed_run(c, sid="t", date=_d(0)), 8.0)
    assert ca.detect_travel(c, TODAY.isoformat()) is None


def _stream(c, aid, alt):
    for i in range(40):
        c.execute("INSERT INTO activity_streams(activity_id,source,elapsed_sec,altitude_m) VALUES(?,?,?,?)",
                  (aid, "garmin", i, alt))


def test_detect_altitude_needs_threshold_and_delta():
    c = mem_conn()
    _stream(c, seed_run(c, sid="h", date=_d(6)), 40.0)
    _stream(c, seed_run(c, sid="a", date=_d(0)), 2000.0)
    r = ca.detect_altitude(c, TODAY.isoformat())
    assert r["altitude_m"] == 2000 and r["home_m"] == 40
    c2 = mem_conn()
    _stream(c2, seed_run(c2, sid="h", date=_d(6)), 1900.0)
    _stream(c2, seed_run(c2, sid="a", date=_d(0)), 2000.0)
    assert ca.detect_altitude(c2, TODAY.isoformat()) is None


def test_rhr_hrv_question_requires_both():
    c = mem_conn()
    for n in range(0, 31):
        up = n <= 2
        for m, v in (("resting_hr", 60 if up else 50), ("hrv_last_night", 40 if up else 60)):
            c.execute("INSERT INTO metric_store(scope_type,scope_id,metric_name,provider,numeric_value)"
                      " VALUES('daily',?,?,'garmin',?)", (_d(n), m, v))
    assert ca.rhr_hrv_question(c, TODAY.isoformat()) is True
    assert ca.rhr_hrv_question(mem_conn(), TODAY.isoformat()) is False


def test_run_creates_candidates_once():
    c = mem_conn()
    for n in range(5, 15):
        _tz(c, seed_run(c, sid=f"h{n}", date=_d(n)), 9.0)
    _tz(c, seed_run(c, sid="t", date=_d(0)), -5.0)
    first = ca.run(c)
    assert "travel" in first["created"]
    assert ca.run(c)["created"] == {}
    row = c.execute("SELECT origin,status FROM context_episodes").fetchone()
    assert row == ("auto", "candidate")
