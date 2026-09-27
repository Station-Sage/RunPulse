"""목표 대회 역산 계획 생성 — 시작·기간·볼륨 진행."""
from datetime import date, timedelta

from src.services import plan_service, plan_template_service
from src.training.planner_rules import plan_start_monday
from src.training.planner_schedule import recent_load
from tests.helpers_pred import mem_conn, seed_run


def _seed_history(c, weeks=8, km_per_week=40.0):
    """계획 시작 전 최근 수 주 훈련(주 4회) 시드."""
    end = date.today() - timedelta(days=1)
    n = 0
    for w in range(weeks):
        for d in (0, 2, 4, 6):
            day = end - timedelta(weeks=w, days=d)
            long = d == 6
            dist = km_per_week * (0.4 if long else 0.2) * 1000
            seed_run(c, sid=str(n), date=day.isoformat(), dist=dist, moving=int(dist / 3.0))
            n += 1


def test_plan_start_monday():
    assert plan_start_monday("2026-11-22", 9) == date(2026, 9, 21)
    assert plan_start_monday(None, 9) is None and plan_start_monday("2026-11-22", None) is None


def test_recent_load_reads_history():
    c = mem_conn()
    _seed_history(c)
    km, longest = recent_load(c, date.today())
    assert 30 <= km <= 50 and longest >= 15


def test_created_plan_follows_periodization_and_ends_on_race():
    c = mem_conn()
    _seed_history(c)
    race = date.today() + timedelta(days=62)                 # 약 9주 뒤
    gid = plan_template_service.create_plan_from_template(c, 42.195, race.isoformat(), 16, name="m")
    weeks = c.execute("SELECT plan_weeks FROM goals WHERE id=?", (gid,)).fetchone()[0]
    rows = c.execute("SELECT date, workout_type, distance_km FROM planned_workouts WHERE source='planner' "
                     "ORDER BY date").fetchall()
    assert rows[-1][:2] == (race.isoformat(), "race") or rows[-1][1] == "rest"
    assert any(r[1] == "race" and r[0] == race.isoformat() for r in rows)
    by_week: dict[str, float] = {}
    for d, t, km in rows:
        if t not in ("rest", "race"):
            mon = (date.fromisoformat(d) - timedelta(days=date.fromisoformat(d).weekday())).isoformat()
            by_week[mon] = by_week.get(mon, 0.0) + (km or 0.0)
    vols = [by_week[k] for k in sorted(by_week)]
    assert len(vols) == weeks and vols[-1] < max(vols) * 0.7      # 대회 주는 피크보다 크게 낮다
    assert max(vols) <= vols[0] * 1.10 ** (weeks - 3) * 1.05      # 피크까지 주 +10% 안쪽으로 완만히


def test_shorter_plan_starts_in_future_and_week_index_is_zero_before_start():
    c = mem_conn()
    _seed_history(c)
    race = date.today() + timedelta(days=90)
    gid = plan_template_service.create_plan_from_template(c, 10.0, race.isoformat(), 6, name="10k")
    start = plan_start_monday(race.isoformat(), 6)
    assert start > date.today() - timedelta(days=date.today().weekday())
    assert c.execute("SELECT MIN(date) FROM planned_workouts").fetchone()[0] == start.isoformat()
    goal = dict(zip(["id", "name", "race_date", "distance_km", "target_time_sec", "target_pace_sec_km", "status",
                     "created_at", "distance_label", "weekly_km_target", "plan_weeks"],
                    c.execute("SELECT id, name, race_date, distance_km, target_time_sec, target_pace_sec_km, status, "
                              "created_at, distance_label, weekly_km_target, plan_weeks FROM goals WHERE id=?", (gid,)).fetchone()))
    assert plan_service._week_index_for_date(goal, date.today()) <= 0
