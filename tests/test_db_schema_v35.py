"""스키마 v35 — plan_replans.rules_version, effective_rules_version, anchor 별 규칙 버전."""
from datetime import date

from src.db_schema_v35 import ensure_v35
from src.training import planner_schedule as S
from src.training.goals import effective_rules_version
from src.training.plan_anchor import load_anchors
from tests.helpers_pred import mem_conn
from tests.test_plan_anchor import RACE, START, TODAY, _anchor, _goal


def _set_rv(c, rv, monday="2030-10-14"):
    c.execute("UPDATE plan_replans SET rules_version=? WHERE anchor_monday=?", (rv, monday))
    c.commit()


def test_ensure_v35_idempotent():
    c = mem_conn()
    ensure_v35(c)
    ensure_v35(c)
    assert "rules_version" in [r[1] for r in c.execute("PRAGMA table_info(plan_replans)")]


def test_effective_follows_goal_without_anchor_version():
    c = mem_conn()
    g = _goal(c, rv=1)
    _anchor(c, g["id"], "2030-10-14", 30)
    assert effective_rules_version(c, g["id"], "2030-10-21") == 1
    assert load_anchors(c, g["id"])[0].rules_version is None


def test_effective_by_week_and_undone():
    c = mem_conn()
    g = _goal(c, rv=1)
    _anchor(c, g["id"], "2030-10-14", 30)
    _set_rv(c, 2)
    assert effective_rules_version(c, g["id"], "2030-10-07") == 1
    assert effective_rules_version(c, g["id"], "2030-10-14") == 2
    assert effective_rules_version(c, g["id"]) == 2
    c.execute("UPDATE plan_replans SET status='undone'")
    assert effective_rules_version(c, g["id"], "2030-10-21") == 1


def test_schedule_prefix_unchanged_and_tail_uses_anchor_version():
    c = mem_conn()
    g = _goal(c, rv=1)
    base = S.schedule_for_goal(c, g, "half", None, TODAY)
    _anchor(c, g["id"], "2030-10-14", 30)
    _set_rv(c, 2)
    new = S.schedule_for_goal(c, g, "half", None, TODAY)
    idx = (date(2030, 10, 14) - START).days // 7
    assert new[:idx] == base[:idx] and len(new) == len(base)
    c.execute("UPDATE plan_replans SET status='undone'")
    c.commit()
    assert S.schedule_for_goal(c, g, "half", None, TODAY) == base
