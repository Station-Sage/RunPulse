"""shoe_service/shoe_query — CRUD·기본 신발 교체(이력 고정)·merge·import-gear·배정·조회."""
import sqlite3

import pytest

from src.db_setup import create_tables
from src.services import shoe_query as q
from src.services import shoe_service as svc
from tests.test_shoe_assignment import act, gear

T = "2026-05-10"


@pytest.fixture
def c():
    conn = sqlite3.connect(":memory:")
    create_tables(conn)
    return conn


def _mileage(c, sid):
    return q.get_shoe(c, sid, T)["mileage_km"]


def test_create_update_delete(c):
    sid = svc.create(c, {"name": "Peg", "initial_distance_km": 300, "category": "race"}, T)
    v = q.get_shoe(c, sid, T)
    assert v["mileage_km"] == 300 and v["retire_km"] == 400 and v["status"] == "ok"
    svc.update(c, sid, {"retire_km": 350}, T)
    assert q.get_shoe(c, sid, T)["status"] == "soon"
    with pytest.raises(svc.ShoeError):
        svc.update(c, sid, {"name": None}, T)
    gear(c, "strava", "g1", sid)
    svc.delete(c, sid)
    assert q.get_shoe(c, sid, T) is None
    assert c.execute("SELECT shoe_id FROM gear").fetchone() == (None,)
    with pytest.raises(svc.ShoeError) as e:
        svc.delete(c, sid)
    assert e.value.http == 404


def test_default_switch_freezes_history(c):
    old = svc.create(c, {"name": "Old", "default_for": "road"}, "2026-05-01")
    act(c, "garmin", "a1", "2026-05-02", dist=10000)
    new = svc.create(c, {"name": "New", "default_for": "road"}, "2026-05-05")
    act(c, "garmin", "a2", "2026-05-06", dist=8000)
    assert q.get_shoe(c, old, T)["default_for"] is None
    assert _mileage(c, old) == 10.0 and _mileage(c, new) == 8.0
    assert c.execute("SELECT origin FROM activity_shoe").fetchall() == [("rule",)]


def test_retire_releases_default_and_unretire(c):
    sid = svc.create(c, {"name": "A", "default_for": "trail"}, T)
    svc.update(c, sid, {"retired_at": T}, T)
    v = q.get_shoe(c, sid, T)
    assert v["status"] == "retired" and v["default_for"] is None
    with pytest.raises(svc.ShoeError) as e:
        svc.update(c, sid, {"default_for": "road"}, T)
    assert e.value.code == "RETIRED_DEFAULT"
    svc.update(c, sid, {"retired_at": None, "default_for": "road"}, T)
    assert q.get_shoe(c, sid, T)["default_for"] == "road"
    with pytest.raises(svc.ShoeError):
        svc.update(c, sid, {"start_date": "2026-06-01", "retired_at": "2026-05-01"}, T)


def test_merge_moves_links_and_assignments(c):
    a = svc.create(c, {"name": "A"}, T)
    b = svc.create(c, {"name": "B", "initial_distance_km": 50, "default_for": "road"}, T)
    gear(c, "garmin", "1", b)
    x = act(c, "garmin", "a1", "2026-05-01")
    svc.set_activity_shoe(c, x, b)
    svc.merge(c, a, b)
    assert q.require(c, b) is None
    v = q.get_shoe(c, a, T)
    assert v["initial_km"] == 50 and v["default_for"] == "road" and len(v["sources"]) == 1
    assert v["activity_count"] == 1
    with pytest.raises(svc.ShoeError):
        svc.merge(c, a, a)


def test_import_gear_groups_names_and_is_idempotent(c):
    c.execute("INSERT INTO gear (source, source_gear_id, name, brand, gear_type) VALUES"
              " ('strava','g1','Peg 40','Nike','shoes'), ('garmin','9','peg40',NULL,'shoes'),"
              " ('strava','b1','Bike','X','bike')")
    c.execute("INSERT INTO gear (source, source_gear_id, name, gear_type, status) VALUES"
              " ('strava','g2','Old','shoes','inactive')")
    assert svc.import_gear(c, T) == {"created": 2, "linked": 3}
    assert svc.import_gear(c, T) == {"created": 0, "linked": 0}
    rows = dict(c.execute("SELECT name, retired_at FROM user_shoes").fetchall())
    assert rows == {"Peg 40": None, "Old": T}
    assert q.list_shoes(c, T)["suggestions"] == []


def test_manual_assign_group_and_clear(c):
    sid = svc.create(c, {"name": "A"}, T)
    g = act(c, "garmin", "a1", "2026-05-01", group="G")
    s = act(c, "strava", "s1", "2026-05-01", group="G")
    svc.set_activity_shoe(c, s, sid)  # 사본 id 로 배정해도 canonical 에 저장
    assert c.execute("SELECT activity_id FROM activity_shoe").fetchall() == [(g,)]
    assert q.activity_shoe_view(c, s)["method"] == "manual"
    svc.clear_activity_shoe(c, s)
    assert q.activity_shoe_view(c, g)["method"] == "none"
    swim = act(c, "garmin", "w1", "2026-05-01", typ="swimming")
    with pytest.raises(svc.ShoeError) as e:
        svc.set_activity_shoe(c, swim, sid)
    assert e.value.code == "NOT_RUNNING"
    assert q.activity_shoe_view(c, swim) is None


def test_bulk_assign_and_unassigned(c):
    sid = svc.create(c, {"name": "A"}, T)
    ids = [act(c, "garmin", f"a{i}", f"2026-05-0{i + 1}") for i in range(3)]
    swim = act(c, "garmin", "w", "2026-05-05", typ="swimming")
    assert q.unassigned_activities(c)["total"] == 3
    r = svc.assign_bulk(c, sid, [*ids[:2], swim, 99999])
    assert r == {"assigned": 2, "skipped_non_running": 1, "skipped_missing": 1}
    un = q.unassigned_activities(c)
    assert un["total"] == 1 and un["activities"][0]["id"] == ids[2]
    acts = q.shoe_activities(c, sid, 0, 1)
    assert acts["total"] == 2 and acts["next_cursor"] == 1 and acts["activities"][0]["method"] == "manual"


def test_link_unlink_gear(c):
    a, b = svc.create(c, {"name": "A"}, T), svc.create(c, {"name": "B"}, T)
    c.execute("INSERT INTO gear (id, source, source_gear_id) VALUES (5, 'strava', 'g5')")
    svc.link_gear(c, a, 5)
    with pytest.raises(svc.ShoeError) as e:
        svc.link_gear(c, b, 5)
    assert e.value.code == "GEAR_LINKED" and e.value.http == 409
    svc.unlink_gear(c, a, 5)
    with pytest.raises(svc.ShoeError):
        svc.unlink_gear(c, a, 5)


def test_today_alert_and_race_note(c):
    sid = svc.create(c, {"name": "Race", "category": "race", "initial_distance_km": 395}, T)
    act(c, "garmin", "a1", "2026-05-08", dist=10000)
    svc.set_activity_shoe(c, c.execute("SELECT id FROM activity_summaries").fetchone()[0], sid)
    c.execute("INSERT INTO goals (name, distance_km, race_date, status) VALUES ('g', 42.195, '2026-05-20', 'active')")
    assert q.today_alert(c, T)["id"] == sid
    assert q.get_shoe(c, sid, T)["note"]
    assert q.today_alert(c, "2026-05-30") is None  # 최근 7일 미사용
    assert q.list_shoes(c, T)["headline"] == "Race, 교체를 권해요"


def test_gear_label_falls_back_to_source_and_id():
    assert q.gear_label("strava", "g1", "Peg 40") == "Peg 40"
    assert q.gear_label("intervals", "34377", None) == "Intervals 신발 #34377"
    assert q.gear_label("garmin", "9", "  ") == "Garmin 신발 #9"
    assert q.gear_label("newsrc", "x1", None) == "newsrc 신발 #x1"
    assert q.gear_label("intervals", None, None) == "이름 없는 신발"


def test_nameless_gear_get_distinct_suggestion_and_shoe_names(c):
    # Intervals 숫자 id 처럼 이름 없는 gear 두 개 — 같은 '이름 없는 신발' 두 켤레가 생기지 않는다
    c.execute("INSERT INTO gear (source, source_gear_id, name, gear_type) VALUES"
              " ('intervals','34377',NULL,'shoes'), ('intervals','34378',NULL,'shoes')")
    names = sorted(s["name"] for s in q.list_shoes(c, T)["suggestions"])
    assert names == ["Intervals 신발 #34377", "Intervals 신발 #34378"]
    assert svc.import_gear(c, T)["created"] == 2
    created = sorted(r[0] for r in c.execute("SELECT name FROM user_shoes"))
    assert created == names
    sid = c.execute("SELECT id FROM user_shoes WHERE name=?", (names[0],)).fetchone()[0]
    assert q.get_shoe(c, sid, T)["sources"][0]["name"] == names[0]
