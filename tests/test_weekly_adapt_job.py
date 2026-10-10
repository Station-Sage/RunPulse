"""주간 적응 잡(E9) — 멱등, 완료·수동 행 보존, v1 목표 무변경."""
from datetime import date, timedelta

from src.services import weekly_adapt_job as J
from src.training.goals import add_goal
from src.training.planner import generate_weekly_plan, save_weekly_plan
from tests.helpers_pred import mem_conn

TODAY = date.today()
MON = TODAY - timedelta(days=TODAY.weekday())


def _setup(version=2):
    c = mem_conn()
    add_goal(c, "g", 42.195, (MON + timedelta(weeks=12)).isoformat(), 14400, rules_version=version)
    save_weekly_plan(c, generate_weekly_plan(c, week_start=MON))
    return c


def _cut(monkeypatch):
    def fake(conn, goal, rows, ws, dl, vdot, injury_flag=False):
        return [dict(r, distance_km=round((r.get("distance_km") or 0) * 0.8, 1), rationale=(r.get("rationale") or "") + " 적응")
                if r["workout_type"] not in ("rest", "race") else r for r in rows]
    monkeypatch.setattr("src.services.weekly_adapt_service.adapt_plan", fake)


def _snap(c):
    return c.execute("SELECT date, distance_km, rationale FROM planned_workouts ORDER BY date").fetchall()


def test_idempotent_and_applies(monkeypatch):
    c = _setup()
    _cut(monkeypatch)
    before = _snap(c)
    n = J.run(c, MON)
    after = _snap(c)
    assert n > 0 and after != before and all("적응" in r[2] for r in after if (r[1] or 0) > 0)
    assert J.run(c, MON) == 0 and _snap(c) == after


def test_completed_and_manual_rows_kept(monkeypatch):
    c = _setup()
    _cut(monkeypatch)
    c.execute("UPDATE planned_workouts SET completed=1 WHERE date=?", (MON.isoformat(),))
    c.execute("UPDATE planned_workouts SET source='manual' WHERE date=?", ((MON + timedelta(days=1)).isoformat(),))
    keep = c.execute("SELECT date, distance_km, rationale FROM planned_workouts WHERE date IN (?,?)",
                     (MON.isoformat(), (MON + timedelta(days=1)).isoformat())).fetchall()
    J.run(c, MON)
    got = c.execute("SELECT date, distance_km, rationale FROM planned_workouts WHERE date IN (?,?)",
                    (MON.isoformat(), (MON + timedelta(days=1)).isoformat())).fetchall()
    assert sorted(got) == sorted(keep)


def test_v1_goal_untouched(monkeypatch):
    c = _setup(version=1)
    _cut(monkeypatch)
    before = _snap(c)
    assert J.run(c, MON) == 0 and _snap(c) == before


def test_heat_forecast_slows_pace_only_and_idempotent():
    c = _setup()
    c.execute("INSERT INTO activity_summaries (source, source_id, activity_type, start_time, distance_m, start_lat, start_lon)"
              " VALUES ('garmin','x','running','2026-01-01T07:00:00',5000,37.5,127.0)")
    hours = [f"{MON + timedelta(days=d):%Y-%m-%d}T{h:02d}:00" for d in range(7) for h in (6, 7, 8)]
    calls = []

    def getter(url, params=None):
        calls.append(params)
        return {"hourly": {"time": hours, "temperature_2m": [25.0] * len(hours)}}

    before = c.execute("SELECT date, distance_km, target_pace_min FROM planned_workouts WHERE target_pace_min IS NOT NULL").fetchall()
    n = J.run(c, MON, getter=getter)
    after = {r[0]: r for r in c.execute("SELECT date, distance_km, target_pace_min FROM planned_workouts WHERE target_pace_min IS NOT NULL")}
    assert n > 0 and calls[0]["forecast_days"] == 7
    assert all(after[d][1] == km and after[d][2] > p for d, km, p in before)
    assert J.run(c, MON, getter=getter) == 0


def test_heat_forecast_failure_changes_nothing():
    c = _setup()
    def boom(url, params=None):
        raise RuntimeError("offline")
    assert J.run(c, MON, getter=boom) == 0
