"""plan_move: M1~M10 검증, 오버레이(이동·맞교환), 쌍 되돌리기, 이동 후 줄이기."""
import sqlite3

import pytest

from src.db_setup import create_tables, migrate_db
from src.services import plan_adjustment_service as svc
from src.training.planned_query import get_planned_workouts
from datetime import date

TODAY = "2026-10-07"  # 수
WS = date(2026, 10, 5)


def _db(rows):
    c = sqlite3.connect(":memory:")
    create_tables(c)
    migrate_db(c)
    for i, (d, t, km) in enumerate(rows, 1):
        c.execute("INSERT INTO planned_workouts(id,date,workout_type,distance_km,source) VALUES (?,?,?,?,'planner')",
                  (i, d, t, km))
    c.commit()
    return c


def _move(c, wid, to, **kw):
    return svc.create_user_adjustment(c, wid, "move", {"to_date": to, **kw}, today=TODAY)


def _code(c, wid, to, **kw):
    with pytest.raises(svc.AdjustmentConflict) as e:
        _move(c, wid, to, **kw)
    return e.value.code


def test_move_to_empty_day_and_overlay():
    c = _db([(TODAY, "easy", 8.0)])
    a = _move(c, 1, "2026-10-09")
    assert a["state"] == "accepted" and a["after"]["date"] == "2026-10-09"
    ws = get_planned_workouts(c, WS)
    assert [(w["date"], w["workout_type"]) for w in ws] == [("2026-10-09", "easy")]
    assert svc.revert(c, a["id"], today=TODAY)["state"] == "undone"
    assert [w["date"] for w in get_planned_workouts(c, WS)] == [TODAY]


def test_swap_with_easy_and_pair_revert_from_either_row():
    c = _db([(TODAY, "tempo", 8.0), ("2026-10-09", "easy", 6.0)])
    a = _move(c, 1, "2026-10-09")
    got = {(w["date"], w["workout_type"]) for w in get_planned_workouts(c, WS)}
    assert got == {("2026-10-09", "tempo"), (TODAY, "easy")}
    swap = c.execute("SELECT id FROM plan_adjustments WHERE workout_id=2").fetchone()[0]
    svc.revert(c, swap, today=TODAY)
    assert c.execute("SELECT COUNT(*) FROM plan_adjustments WHERE decision='accepted'").fetchone()[0] == 0
    assert {w["date"] for w in get_planned_workouts(c, WS)} == {TODAY, "2026-10-09"}
    assert a["id"]


def test_reduce_after_move_uses_overlay_date():
    c = _db([(TODAY, "easy", 10.0)])
    _move(c, 1, "2026-10-08")
    with pytest.raises(svc.AdjustmentConflict) as e:
        svc.create_user_adjustment(c, 1, "reduce", {"pct": 20}, today=TODAY)
    assert e.value.code == "LOCKED"
    r = svc.create_user_adjustment(c, 1, "reduce", {"pct": 20}, today="2026-10-08")
    assert r["after"]["distance_km"] == 8.0
    w = get_planned_workouts(c, WS)[0]
    assert w["date"] == "2026-10-08" and w["distance_km"] == 8.0


def test_validation_codes():
    c = _db([(TODAY, "tempo", 8.0), ("2026-10-08", "interval", 8.0), ("2026-10-09", "long", 20.0),
             ("2026-10-10", "easy", 5.0), ("2026-10-11", "long", 20.0), (TODAY.replace("07", "06"), "easy", 5.0)])
    assert _code(c, 1, "2026-10-08") == "TARGET_HARD"
    assert _code(c, 1, "2026-10-07") == "OUT_OF_RANGE"
    assert _code(c, 1, "2026-10-12") == "OUT_OF_RANGE"
    assert _code(c, 1, "2026-10-09", reason="pain") == "PAIN_NO_MOVE"
    assert _code(c, 1, "2026-10-09") == "TARGET_HARD"
    c.execute("UPDATE planned_workouts SET workout_type='rest' WHERE id=3")
    assert _code(c, 1, "2026-10-09") == "HARD_SPACING"  # 10-08 interval 이웃
    c.execute("UPDATE planned_workouts SET workout_type='race' WHERE id=1")
    assert _code(c, 1, "2026-10-10") == "RACE_FIXED"


def test_cross_week_taper_and_done():
    c = _db([("2026-10-11", "tempo", 8.0)])
    with pytest.raises(svc.AdjustmentConflict) as e:
        svc.create_user_adjustment(c, 1, "move", {"to_date": "2026-10-12"}, today="2026-10-11")
    assert e.value.code == "CROSS_WEEK"
    c = _db([(TODAY, "tempo", 8.0)])
    c.execute("INSERT INTO goals(name,distance_km,race_date,status) VALUES ('g',42.195,'2026-10-11','active')")
    assert _code(c, 1, "2026-10-09") == "TAPER_LOCK"


def test_already_moved_and_not_found():
    c = _db([(TODAY, "easy", 8.0)])
    _move(c, 1, "2026-10-09")
    with pytest.raises(svc.AdjustmentConflict):
        _move(c, 1, "2026-10-08")
    with pytest.raises(svc.AdjustmentConflict) as e:
        svc.create_user_adjustment(c, 99, "move", {"to_date": "2026-10-09"}, today=TODAY)
    assert e.value.code == "NOT_FOUND"
