"""activity_feedback_service 테스트."""
import sqlite3

import pytest

from src.db_setup import create_tables
from src.services import activity_feedback_service as svc


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    create_tables(c)
    rows = [("garmin", "g1", "2026-04-01T08:00:00Z", "grp1"), ("strava", "s1", "2026-04-01T08:00:10Z", "grp1"),
            ("garmin", "g2", "2026-04-01T18:00:00Z", None)]
    for s, sid, st, g in rows:
        c.execute("INSERT INTO activity_summaries(source, source_id, activity_type, start_time, distance_m,"
                  " duration_sec, matched_group_id) VALUES (?,?,'running',?,5000,1800,?)", (s, sid, st, g))
    c.commit()
    return c


def _ids(c):
    return [r[0] for r in c.execute("SELECT id FROM activity_summaries ORDER BY id")]


def test_upsert_and_get(conn):
    a = _ids(conn)[0]
    fb = svc.put_feedback(conn, a, {"rpe": 7, "pain": "mild", "pain_sites": ["knee", "calf", "knee"], "note": " 좋음 "})
    assert fb["rpe"] == 7 and fb["pain_sites"] == ["calf", "knee"] and fb["note"] == "좋음"
    fb2 = svc.put_feedback(conn, a, {"rpe": 8})
    assert fb2["rpe"] == 8 and fb2["pain"] is None
    assert conn.execute("SELECT count(*) FROM activity_feedback").fetchone()[0] == 1


def test_two_activities_same_day_independent(conn):
    a, _, c = _ids(conn)
    svc.put_feedback(conn, a, {"rpe": 3})
    svc.put_feedback(conn, c, {"rpe": 9})
    assert svc.get_feedback(conn, a)["rpe"] == 3 and svc.get_feedback(conn, c)["rpe"] == 9


def test_all_empty_deletes(conn):
    a = _ids(conn)[0]
    svc.put_feedback(conn, a, {"rpe": 5})
    assert svc.put_feedback(conn, a, {"rpe": None, "note": "  "}) is None
    assert svc.get_feedback(conn, a) is None


@pytest.mark.parametrize("payload,code", [
    ({"rpe": 0}, "INVALID_RPE"), ({"rpe": 11}, "INVALID_RPE"), ({"rpe": True}, "INVALID_RPE"),
    ({"pain": "bad"}, "INVALID_PAIN"), ({"pain": "mild", "pain_sites": ["x"]}, "INVALID_SITE"),
    ({"pain": "mild", "pain_sites": ["foot", "ankle", "knee", "hip"]}, "INVALID_SITE"),
    ({"note": "a" * 501}, "NOTE_TOO_LONG"),
])
def test_invalid_rejected(conn, payload, code):
    with pytest.raises(svc.FeedbackError) as e:
        svc.put_feedback(conn, _ids(conn)[0], payload)
    assert e.value.code == code


def test_pain_none_clears_sites():
    assert svc.validate({"pain": "none", "pain_sites": ["knee"]})["pain_sites"] == []


def test_group_member_lookup_and_canonical_cleanup(conn):
    a, b, _ = _ids(conn)
    svc.put_feedback(conn, b, {"rpe": 6})
    assert svc.get_feedback(conn, a)["rpe"] == 6 and svc.get_feedback(conn, b)["rpe"] == 6
    svc.put_feedback(conn, a, {"rpe": 7})
    assert conn.execute("SELECT count(*) FROM activity_feedback").fetchone()[0] == 1


def test_missing_activity_raises(conn):
    with pytest.raises(LookupError):
        svc.put_feedback(conn, 9999, {"rpe": 5})


def test_feedback_for_activities_bulk(conn):
    a, b, c = _ids(conn)
    svc.put_feedback(conn, a, {"rpe": 4})
    out = svc.feedback_for_activities(conn, [a, b, c])
    assert out[a]["rpe"] == 4 and out[b]["rpe"] == 4 and c not in out
    assert svc.feedback_for_activities(conn, []) == {}


def test_delete(conn):
    a = _ids(conn)[0]
    svc.put_feedback(conn, a, {"rpe": 4})
    assert svc.delete_feedback(conn, a) is True and svc.delete_feedback(conn, a) is False
