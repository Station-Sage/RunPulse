"""POST /coach/plan 생성 — 단일 트랜잭션·이전 목표 미래 행 정리 (ADR-035 부록 R T6)."""
from datetime import date, timedelta

import pytest

from src.services import plan_template_service as svc
from src.training import planner
from src.training.goals import add_goal, get_active_goal
from tests.helpers_pred import mem_conn


def _race(days=70):
    return (date.today() + timedelta(days=days)).isoformat()


def test_create_cancels_old_goal_and_clears_its_future_rows():
    c = mem_conn()
    old = svc.create_plan_from_template(c, 21.0975, _race(40), 5, name="old")
    fut = (date.today() + timedelta(days=3)).isoformat()
    c.execute("INSERT INTO planned_workouts(date,workout_type,distance_km,source,completed) VALUES (?, 'easy', 5, 'planner', 1)",
              (fut,))
    c.commit()
    new = svc.create_plan_from_template(c, 42.195, _race(70), 8, name="new")
    assert get_active_goal(c)["id"] == new != old
    assert c.execute("SELECT status FROM goals WHERE id=?", (old,)).fetchone()[0] == "cancelled"
    # 이력(completed) 행은 보존
    assert c.execute("SELECT count(*) FROM planned_workouts WHERE date=? AND completed=1", (fut,)).fetchone()[0] == 1


def test_failure_rolls_back_goal_and_plan(monkeypatch):
    c = mem_conn()
    keep = add_goal(c, "keep", 10, _race(30))
    before = c.execute("SELECT count(*) FROM planned_workouts").fetchone()[0]
    calls = {"n": 0}
    real = planner.generate_weekly_plan

    def boom(*a, **k):
        calls["n"] += 1
        if calls["n"] == 3:
            raise RuntimeError("x")
        return real(*a, **k)

    monkeypatch.setattr(svc, "generate_weekly_plan", boom)
    with pytest.raises(RuntimeError):
        svc.create_plan_from_template(c, 42.195, _race(70), 8, name="bad")
    assert get_active_goal(c)["id"] == keep
    assert c.execute("SELECT count(*) FROM goals").fetchone()[0] == 1
    assert c.execute("SELECT count(*) FROM planned_workouts").fetchone()[0] == before


def test_commit_false_defers_to_caller():
    c = mem_conn()
    c.commit()
    add_goal(c, "g", 10, _race(30), commit=False)
    c.rollback()
    assert c.execute("SELECT count(*) FROM goals").fetchone()[0] == 0
