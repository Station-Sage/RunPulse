"""plan_pain — 단계별 op 강제, 직전 2일 제안 우선, 반복 통증 알림."""
import sqlite3
from datetime import date, timedelta

import pytest

from src.db_setup import create_tables, migrate_db
from src.services import plan_adjustment_service as svc
from src.services import plan_pain

TODAY = date.today()
D = lambda n: (TODAY + timedelta(days=n)).isoformat()  # noqa: E731


@pytest.fixture
def conn(tmp_path):
    c = sqlite3.connect(str(tmp_path / "r.db"))
    create_tables(c)
    migrate_db(c)
    rows = [(1, D(-1), "easy", 8.0), (2, D(0), "tempo", 10.0), (3, D(0 + 1), "easy", 10.0)]
    for i, d, t, km in rows:
        c.execute("INSERT INTO planned_workouts(id,date,workout_type,distance_km,source) VALUES (?,?,?,?,'planner')",
                  (i, d, t, km))
    c.commit()
    return c


def test_resolve_levels():
    assert plan_pain.resolve("reduce", {"reason": "fatigue"}) == "reduce"
    assert plan_pain.resolve("reduce", {"reason": "pain", "pain_level": "mild"}) == "reduce"
    assert plan_pain.resolve("reduce", {"reason": "pain", "pain_level": "severe"}) == "rest"
    with pytest.raises(ValueError):
        plan_pain.resolve("rest", {"reason": "pain"})
    with pytest.raises(ValueError):
        plan_pain.resolve("rest", {"reason": "pain", "pain_level": "mild", "pain_sites": ["x"]})


def test_proposal_priority_within_two_days(conn):
    svc.create_user_adjustment(conn, 1, "rest", {"reason": "pain", "pain_level": "moderate"}, today=D(-1))
    w = plan_pain.proposal(conn, D(0))
    assert w["adjusted_type"] == "rest" and w["rule_version"] == "pain_v1"
    p = svc.ensure_proposal(conn, D(0), today=D(0))
    assert p["rule_version"] == "pain_v1" and p["after"]["workout_type"] == "rest"
    w = plan_pain.proposal(conn, D(1))
    assert w["adjusted_type"] == "easy" and w["adjusted_distance_km"] == 6.0
    assert plan_pain.proposal(conn, D(2)) is None


def test_mild_has_no_proposal_and_repeat(conn):
    svc.create_user_adjustment(conn, 1, "reduce", {"reason": "pain", "pain_level": "mild", "pct": 30,
                                                   "pain_sites": ["knee"]}, today=D(-1))
    assert plan_pain.proposal(conn, D(0)) is None
    assert plan_pain.repeat(conn, D(0)) is None
    svc.create_user_adjustment(conn, 2, "rest", {"reason": "pain", "pain_level": "mild", "pain_sites": ["knee"]},
                               today=D(0))
    assert plan_pain.repeat(conn, D(0))["code"] == "PAIN_REPEAT"
