"""plan_anchor — anchor 이전 주 불변, 이후 주 새 시작 부하, 주 index 유지, 쓰기 없음(ADR-035 부록 R)."""
from datetime import date

from src.training import planner_schedule as S
from src.training.goals import add_goal
from src.training.plan_anchor import Anchor, fold, load_anchors
from tests.helpers_pred import mem_conn

RACE = "2030-11-24"
TODAY = date(2030, 1, 1)
START = date(2030, 9, 2)      # 대회 주 월요일(11-18)에서 11주 전 = 12주 계획 시작


def _goal(c, rv=2):
    gid = add_goal(c, "g", 21.0975, RACE, None, rules_version=rv)
    c.execute("UPDATE goals SET plan_weeks=12, distance_label='half' WHERE id=?", (gid,))
    c.commit()
    return {"id": gid, "race_date": RACE, "plan_weeks": 12, "distance_km": 21.0975}


def _anchor(c, gid, monday, km, long_km=None, status="applied"):
    c.execute("INSERT INTO plan_replans(goal_id, anchor_monday, start_km, start_long_km, start_source, status)"
              " VALUES (?,?,?,?,'user',?)", (gid, monday, km, long_km, status))
    c.commit()


def test_no_anchor_is_identical():
    c = mem_conn()
    g = _goal(c)
    assert S.schedule_for_goal(c, g, "half", None, TODAY) == S.schedule_for_goal(c, g, "half", None, TODAY, None)
    assert load_anchors(c, g["id"]) == [] and load_anchors(c, None) == []


def test_applied_anchor_replaces_only_later_weeks():
    c = mem_conn()
    g = _goal(c)
    base = S.schedule_for_goal(c, g, "half", None, TODAY)
    _anchor(c, g["id"], "2030-09-30", 20.0, 12.0)        # idx 4
    folded = S.schedule_for_goal(c, g, "half", None, TODAY)
    assert folded[:4] == base[:4] and len(folded) == 12
    assert [w.index for w in folded] == list(range(12))
    assert [w.weeks_to_race for w in folded] == [w.weeks_to_race for w in base]
    assert folded[4].weekly_km == 20.0 and folded[4] != base[4]


def test_unapplied_and_out_of_range_ignored():
    c = mem_conn()
    g = _goal(c)
    base = S.schedule_for_goal(c, g, "half", None, TODAY)
    _anchor(c, g["id"], "2030-09-30", 30.0, status="undone")
    assert S.schedule_for_goal(c, g, "half", None, TODAY) == base
    assert fold(base, START, [Anchor(date(2031, 1, 6), 30.0)], lambda a, n: base[:n]) == base


def test_extra_anchor_preview_writes_nothing():
    c = mem_conn()
    g = _goal(c)
    before = c.total_changes
    folded = S.schedule_for_goal(c, g, "half", None, TODAY, Anchor(date(2030, 9, 30), 20.0, 12.0))
    assert folded[4].weekly_km == 20.0 and c.total_changes == before
    assert c.execute("SELECT COUNT(*) FROM plan_replans").fetchone()[0] == 0
