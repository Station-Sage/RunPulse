"""plan_replan_service — preview 쓰기 없음, apply 보호 행 보존, undo 조건(ADR-035 부록 R)."""
from datetime import date, timedelta

import pytest

from src.services import plan_replan_service as R
from src.training.goals import add_goal
from src.training.planner import generate_weekly_plan, save_weekly_plan
from tests.helpers_pred import mem_conn, with_days

TODAY = date.today()
MON = R.next_monday(TODAY)
RACE = (MON + timedelta(weeks=10, days=5)).isoformat()


@pytest.fixture
def c():
    conn = with_days(mem_conn())
    gid = add_goal(conn, "g", 21.0975, RACE, None, rules_version=2)
    conn.execute("UPDATE goals SET plan_weeks=14, distance_label='half' WHERE id=?", (gid,))
    conn.commit()
    ws = MON - timedelta(weeks=1)
    for i in range(12):
        save_weekly_plan(conn, generate_weekly_plan(conn, gid, week_start=ws + timedelta(weeks=i)), goal_id=gid)
    return conn


def _count(conn):
    return conn.execute("SELECT count(*) FROM planned_workouts").fetchone()[0]


def test_preview_writes_nothing(c):
    snap = c.execute("SELECT id,date,distance_km FROM planned_workouts ORDER BY id").fetchall()
    out = R.preview(c, {"recent_weekly_km": 20}, TODAY)
    assert out["replan_id"] is None and out["anchor_monday"] == MON.isoformat() and out["after"]
    assert c.execute("SELECT count(*) FROM plan_replans").fetchone()[0] == 0
    assert c.execute("SELECT id,date,distance_km FROM planned_workouts ORDER BY id").fetchall() == snap


def test_apply_conflict_and_errors(c):
    with pytest.raises(R.ReplanError) as e:
        R.apply(c, {"expect_anchor": "2000-01-03"}, TODAY)
    assert e.value.code == "CONFLICT"
    with pytest.raises(R.ReplanError) as e:
        R.preview(c, {}, date.fromisoformat(RACE))
    assert e.value.code == "RACE_WEEK"
    c.execute("UPDATE goals SET status='cancelled'")
    with pytest.raises(R.ReplanError) as e:
        R.preview(c, {}, TODAY)
    assert e.value.code == "NO_GOAL"


def test_apply_protects_history_and_keeps_past(c):
    past = c.execute("SELECT id FROM planned_workouts WHERE date < ?", (MON.isoformat(),)).fetchall()
    done = c.execute("SELECT id FROM planned_workouts WHERE date >= ? ORDER BY date LIMIT 1", (MON.isoformat(),)).fetchone()[0]
    c.execute("UPDATE planned_workouts SET completed=1 WHERE id=?", (done,))
    c.commit()
    out = R.apply(c, {"recent_weekly_km": 20, "expect_anchor": MON.isoformat()}, TODAY)
    assert out["replan_id"] and [p["id"] for p in out["preserved"]] == [done]
    assert c.execute("SELECT count(*) FROM planned_workouts WHERE id=?", (done,)).fetchone()[0] == 1
    assert {r[0] for r in past} <= {r[0] for r in c.execute("SELECT id FROM planned_workouts")}
    assert c.execute("SELECT status FROM plan_replans").fetchone()[0] == "applied"


def test_undo_restores_and_locks(c):
    before = c.execute("SELECT date,workout_type,distance_km FROM planned_workouts ORDER BY date,id").fetchall()
    out = R.apply(c, {"recent_weekly_km": 20, "expect_anchor": MON.isoformat()}, TODAY)
    R.undo(c, out["replan_id"], TODAY)
    assert c.execute("SELECT date,workout_type,distance_km FROM planned_workouts ORDER BY date,id").fetchall() == before
    with pytest.raises(R.ReplanError) as e:
        R.undo(c, out["replan_id"], TODAY)
    assert e.value.code == "REPLAN_LOCKED"


def test_undo_locked_after_start_or_new_history(c):
    out = R.apply(c, {"expect_anchor": MON.isoformat()}, TODAY)
    with pytest.raises(R.ReplanError):
        R.undo(c, out["replan_id"], MON)
    c.execute("UPDATE planned_workouts SET completed=1 WHERE date=(SELECT min(date) FROM planned_workouts WHERE date>=?)",
              (MON.isoformat(),))
    with pytest.raises(R.ReplanError) as e:
        R.undo(c, out["replan_id"], TODAY)
    assert e.value.code == "REPLAN_LOCKED"


def test_last_undoable(c):
    assert R.last_undoable(c, TODAY) is None
    a = R.apply(c, {"recent_weekly_km": 20, "expect_anchor": MON.isoformat()}, TODAY)
    last = R.last_undoable(c, TODAY)
    assert last["replan_id"] == a["replan_id"] and last["undo_until"] == (MON - timedelta(days=1)).isoformat()
    assert R.last_undoable(c, MON) is None
    R.undo(c, a["replan_id"], TODAY)
    assert R.last_undoable(c, TODAY) is None


@pytest.fixture
def future(c):
    """시작이 다음 월요일보다 1주 뒤인 플랜(첫 주가 미래). 그 앞 주에는 다른 목표의 행이 있다."""
    c.execute("UPDATE goals SET plan_weeks=10")      # 시작 = MON + 1주
    c.commit()
    return c, MON + timedelta(weeks=1)


def test_replan_anchor_is_plan_start_when_plan_not_started(future):
    c, start = future
    goal = c.execute("SELECT race_date, plan_weeks FROM goals").fetchone()
    assert R.replan_anchor({"race_date": goal[0], "plan_weeks": goal[1]}, TODAY) == start
    assert R.replan_anchor({"race_date": goal[0], "plan_weeks": 14}, TODAY) == MON   # 이미 시작한 플랜
    assert R.replan_anchor(None, TODAY) == MON


def test_preview_future_plan_does_not_add_pre_plan_week(future):
    """S4-86: 첫 주가 미래인 플랜을 다시 맞추면 계획 앞 주(다음 월요일 주)에 폴백 거리 주가 붙던 버그."""
    c, start = future
    pre = c.execute("SELECT id, date, distance_km FROM planned_workouts WHERE date < ? ORDER BY id",
                    (start.isoformat(),)).fetchall()
    out = R.preview(c, {}, TODAY)
    assert out["anchor_monday"] == start.isoformat()
    assert all(w["week_start"] >= start.isoformat() for w in out["after"] + out["before"])
    assert out["after"][0]["week_start"] == start.isoformat()
    applied = R.apply(c, {"expect_anchor": start.isoformat()}, TODAY)
    assert applied["anchor_monday"] == start.isoformat()
    # 계획 앞 주의 기존 행은 지우지도 새로 만들지도 않는다
    assert c.execute("SELECT id, date, distance_km FROM planned_workouts WHERE date < ? ORDER BY id",
                     (start.isoformat(),)).fetchall() == pre
    assert R.last_undoable(c, TODAY)["undo_until"] == (start - timedelta(days=1)).isoformat()


def test_apply_future_plan_rejects_next_monday_anchor(future):
    c, _ = future
    with pytest.raises(R.ReplanError) as e:
        R.apply(c, {"expect_anchor": MON.isoformat()}, TODAY)
    assert e.value.code == "CONFLICT"


def test_preview_holds_write_lock_so_concurrent_commit_cannot_break_it(c, tmp_path, monkeypatch):
    """S4-87: 미리보기가 읽은 뒤 쓰기로 올리는 사이 다른 연결이 커밋하면 'database is locked' 500 이 났다.
    이제 쓰기 잠금을 먼저 잡아, 다른 연결의 쓰기는 기다리고(여기선 짧은 timeout 으로 실패) 미리보기는 끝까지 간다."""
    import sqlite3
    path = tmp_path / "r.db"
    disk = sqlite3.connect(path)
    c.backup(disk)
    disk.execute("PRAGMA journal_mode=WAL")
    disk.close()
    a = sqlite3.connect(path, timeout=1)
    real = R.snapshot
    seen = {}

    def snap(conn, frm, to):
        if "other" not in seen:
            b = sqlite3.connect(path, timeout=0.05)
            try:
                b.execute("UPDATE goals SET name='x'")
                b.commit()
                seen["other"] = "committed"
            except sqlite3.OperationalError:
                seen["other"] = "blocked"
            finally:
                b.close()
        return real(conn, frm, to)

    monkeypatch.setattr(R, "snapshot", snap)
    out = R.preview(a, {}, TODAY)
    assert out["after"] and seen["other"] == "blocked"
    assert not a.in_transaction and a.execute("SELECT count(*) FROM plan_replans").fetchone()[0] == 0
    a.close()
