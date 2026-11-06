"""shoe_assignment — 그룹 단위 해석(manual > source > rule > none)·충돌·날짜 제약·집계."""
import json
import sqlite3

import pytest

from src.db_setup import create_tables
from src.services import shoe_assignment as sa


@pytest.fixture
def c():
    conn = sqlite3.connect(":memory:")
    create_tables(conn)
    return conn


def act(c, source, sid, day, dist=10000, typ="running", gear=None, group=None, raw_type=None):
    cur = c.execute("INSERT INTO activity_summaries (source, source_id, activity_type, start_time, distance_m,"
                    " gear_id, matched_group_id) VALUES (?,?,?,?,?,?,?)",
                    (source, sid, typ, f"{day}T07:00:00", dist, gear, group))
    if raw_type:
        key = {"garmin": "activityType", "strava": "sport_type", "intervals": "type"}[source]
        payload = {key: {"typeKey": raw_type}} if source == "garmin" else {key: raw_type}
        c.execute("INSERT INTO source_payloads (source, entity_type, entity_id, payload) VALUES (?,?,?,?)",
                  (source, "activity_summary", sid, json.dumps(payload)))
    return cur.lastrowid


def shoe(c, name, **kw):
    cols = ["name", *kw]
    cur = c.execute(f"INSERT INTO user_shoes ({','.join(cols)}) VALUES ({','.join('?' * len(cols))})",
                    [name, *kw.values()])
    return cur.lastrowid


def gear(c, source, gid, shoe_id):
    c.execute("INSERT INTO gear (source, source_gear_id, shoe_id) VALUES (?,?,?)", (source, gid, shoe_id))


def test_kind_of():
    assert sa.kind_of("trail_running") == "trail" and sa.kind_of("TrailRun") == "trail"
    assert sa.kind_of("treadmill_running") == "treadmill" and sa.kind_of("VirtualRun") == "treadmill"
    assert sa.kind_of("indoor_running") == "treadmill" and sa.kind_of("Run") == "road" and sa.kind_of(None) == "road"


def test_gear_lookup_sources():
    assert sa.gear_lookup_sources("intervals", "g123") == ["intervals", "strava"]
    assert sa.gear_lookup_sources("intervals", "34377") == ["intervals"]
    assert sa.gear_lookup_sources("strava", "g1") == ["strava", "strava_export"]


def test_priority_manual_source_rule_none(c):
    a = shoe(c, "A")
    b = shoe(c, "B", default_for="road", default_since="2026-01-01")
    m = shoe(c, "M")
    x1 = act(c, "strava", "s1", "2026-05-01", gear="g1")
    x2 = act(c, "garmin", "g2", "2026-05-02")
    x3 = act(c, "garmin", "g3", "2026-05-03")
    x4 = act(c, "garmin", "g4", "2026-05-04", raw_type="treadmill_running")
    gear(c, "strava", "g1", a)
    c.execute("INSERT INTO activity_shoe (activity_id, shoe_id) VALUES (?, ?)", (x3, m))
    res = sa.resolve(c)
    assert (res[x1].shoe_id, res[x1].method) == (a, "source")
    assert (res[x2].shoe_id, res[x2].method) == (b, "rule")
    assert (res[x3].shoe_id, res[x3].method) == (m, "manual")
    assert (res[x4].shoe_id, res[x4].method) == (None, "none")


def test_manual_null_means_no_shoe(c):
    shoe(c, "B", default_for="road", default_since="2026-01-01")
    x = act(c, "garmin", "g1", "2026-05-01")
    c.execute("INSERT INTO activity_shoe (activity_id, shoe_id) VALUES (?, NULL)", (x,))
    a = sa.resolve(c)[x]
    assert a.shoe_id is None and a.method == "manual"
    assert sa.aggregate({x: a}) == ({}, 0)


def test_manual_survives_canonical_change(c):
    m = shoe(c, "M")
    s = act(c, "strava", "s1", "2026-05-01", group="G")
    c.execute("INSERT INTO activity_shoe (activity_id, shoe_id) VALUES (?, ?)", (s, m))
    g = act(c, "garmin", "a1", "2026-05-01", group="G")  # 이후 Garmin 행이 대표가 됨
    res = sa.resolve(c)
    assert s not in res and (res[g].shoe_id, res[g].method) == (m, "manual")


def test_non_running_excluded(c):
    shoe(c, "B", default_for="road", default_since="2026-01-01")
    x = act(c, "garmin", "g1", "2026-05-01", typ="swimming")
    assert x not in sa.resolve(c)


def test_date_window(c):
    a = shoe(c, "A", start_date="2026-05-02", retired_at="2026-05-10")
    for i, day in enumerate(("2026-05-01", "2026-05-05", "2026-05-11")):
        act(c, "strava", f"s{i}", day, gear="g1")
    gear(c, "strava", "g1", a)
    got = {v.date: v.method for v in sa.resolve(c).values()}
    assert got == {"2026-05-01": "none", "2026-05-05": "source", "2026-05-11": "none"}


def test_default_since_blocks_past(c):
    shoe(c, "B", default_for="road", default_since="2026-05-05")
    x = act(c, "garmin", "g1", "2026-05-04")
    assert sa.resolve(c)[x].method == "none"


def test_conflict_flag_uses_garmin_priority(c):
    a, b = shoe(c, "A"), shoe(c, "B")
    g = act(c, "garmin", "a1", "2026-05-01", gear="111", group="G")
    act(c, "strava", "s1", "2026-05-01", gear="g9", group="G")
    gear(c, "garmin", "111", a)
    gear(c, "strava", "g9", b)
    r = sa.resolve(c)[g]
    assert r.shoe_id == a and r.conflict and r.by_source == {"garmin": a, "strava": b}


def test_rule_history_rows(c):
    b = shoe(c, "B")
    x = act(c, "garmin", "g1", "2026-05-01")
    c.execute("INSERT INTO activity_shoe (activity_id, shoe_id, origin) VALUES (?, ?, 'rule')", (x, b))
    assert (sa.resolve(c)[x].shoe_id, sa.resolve(c)[x].method) == (b, "rule")


def test_aggregate_and_resolve_one(c):
    a = shoe(c, "A", default_for="road", default_since="2026-01-01")
    x = act(c, "garmin", "g1", "2026-05-01", dist=5000)
    act(c, "garmin", "g2", "2026-05-03", dist=7000)
    stats, unassigned = sa.aggregate(sa.resolve(c))
    assert stats[a]["count"] == 2 and stats[a]["assigned_m"] == 12000 and stats[a]["last_used"] == "2026-05-03"
    assert unassigned == 0
    assert sa.resolve_one(c, x).shoe_id == a
    assert sa.resolve_one(c, 9999) is None
