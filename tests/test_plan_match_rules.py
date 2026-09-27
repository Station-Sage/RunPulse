"""A1/A2: 대회일 기준 계획 기간·단계, 매칭 배타·호환 규칙, 결과 라벨, 연속 러닝 이행률."""
import json
from datetime import date, timedelta

from src.services import plan_template_service
from src.training.match_select import classify_outcome, is_done, pick_activity
from src.training.matcher import match_week_activities
from src.training.outcome_v2 import compare_continuous, is_continuous
from src.training.planned_query import get_planned_workouts
from src.training.planner import generate_weekly_plan
from src.training.planner_rules import apply_race_week, plan_weeks_until_race, weeks_to_race
from tests.helpers_pred import mem_conn, seed_run

MON = date(2026, 9, 21)


def test_plan_weeks_until_race_counts_both_ends():
    assert plan_weeks_until_race("2026-11-22", today=date(2026, 9, 27)) == 9     # 9/21주 ~ 11/22주
    assert plan_weeks_until_race("2026-09-27", today=date(2026, 9, 27)) == 1
    assert plan_weeks_until_race("2026-09-01", today=date(2026, 9, 27)) is None


def test_weeks_to_race_is_relative_to_as_of():
    assert weeks_to_race("2026-11-22", as_of=date(2026, 9, 21)) == 8
    assert weeks_to_race("2026-11-22", as_of=date(2026, 11, 16)) == 0


def test_phase_differs_by_week_and_race_week_is_built():
    c = mem_conn()
    c.execute("INSERT INTO goals (name, race_date, distance_km, status) VALUES ('m', '2026-11-22', 42.195, 'active')")
    early = generate_weekly_plan(c, goal_id=1, week_start=date(2026, 9, 21))
    late = generate_weekly_plan(c, goal_id=1, week_start=date(2026, 11, 16))
    assert {w["_phase"] for w in early} != {w["_phase"] for w in late}
    assert late[-1]["workout_type"] == "race" and late[-1]["distance_km"] == 42.2
    assert "long" not in [w["workout_type"] for w in late]        # 대회 주 taper: 롱런 없음


def test_apply_race_week_rests_after_race():
    plan = [{"date": (MON + timedelta(days=i)).isoformat(), "workout_type": "easy", "distance_km": 8.0}
            for i in range(7)]
    apply_race_week(plan, "2026-09-25", 10.0)
    assert [w["workout_type"] for w in plan] == ["easy"] * 4 + ["race", "rest", "rest"]


def test_create_plan_is_clamped_to_race_week():
    c = mem_conn()
    race = (date.today() + timedelta(days=20)).isoformat()
    gid = plan_template_service.create_plan_from_template(c, 10.0, race, 16)
    weeks = c.execute("SELECT plan_weeks FROM goals WHERE id=?", (gid,)).fetchone()[0]
    assert weeks == plan_weeks_until_race(race) and weeks < 16
    assert c.execute("SELECT MAX(date) FROM planned_workouts").fetchone()[0] <= (date.fromisoformat(race) + timedelta(days=6)).isoformat()


def test_templates_are_capped_by_race_date():
    c = mem_conn()
    race = (date.today() + timedelta(days=30)).isoformat()
    avail = plan_weeks_until_race(race)
    ts = plan_template_service.get_static_plan_templates(c, 42.195, None, race)
    assert ts and max(t["weeks"] for t in ts) == avail


def test_pick_activity_skips_claimed_and_incompatible():
    acts = [(1, "d", 9.3), (2, "d", 26.0)]
    assert pick_activity(26.0, acts, set())[0] == 2
    assert pick_activity(26.0, acts, {2}) is None          # 9.3km 는 26km 계획과 다른 세션
    assert pick_activity(11.5, [(1, "d", 7.1)], set())[0] == 1   # 0.62 — 호환(미이행 처리는 is_done)
    assert not is_done(11.5, 7.1) and is_done(10.0, 9.0)


def test_classify_outcome_prioritises_distance():
    assert classify_outcome(0.62, -8.0) == "underperformed"     # 짧고 빠름 ≠ 초과 달성
    assert classify_outcome(0.4, None) == "skipped"
    assert classify_outcome(1.0, -8.0) == "overperformed"
    assert classify_outcome(1.0, 0.0) == "on_target"


def _plan(c, d, wtype, dist, source="planner", ssys=None, structure=None, act_id=None, done=0):
    c.execute("INSERT INTO planned_workouts (date, workout_type, distance_km, source, source_system, structure_json,"
              " matched_activity_id, completed) VALUES (?,?,?,?,?,?,?,?)",
              (d, wtype, dist, source, ssys, structure, act_id, done))


def test_matcher_does_not_steal_activity_claimed_by_external_plan():
    c = mem_conn()
    a = seed_run(c, sid="1", date="2026-09-27", dist=9300.0, moving=3300)
    _plan(c, "2026-09-27", "long", 26.0)
    _plan(c, "2026-09-27", "easy", None, source="garmin", ssys="garmin", act_id=a, done=1)
    assert match_week_activities(c, MON) == 0
    row = c.execute("SELECT completed, matched_activity_id FROM planned_workouts WHERE source='planner'").fetchone()
    assert row == (0, None)
    w = [x for x in get_planned_workouts(c, MON) if x["source"] == "planner"][0]
    assert w["superseded"] is True


def test_matcher_partial_run_is_linked_but_not_completed():
    c = mem_conn()
    a = seed_run(c, sid="1", date="2026-09-26", dist=7100.0, moving=2422)
    _plan(c, "2026-09-26", "easy", 11.5)
    assert match_week_activities(c, MON) == 1
    assert c.execute("SELECT completed, matched_activity_id FROM planned_workouts").fetchone() == (0, a)
    assert c.execute("SELECT outcome_label FROM session_outcomes").fetchone()[0] == "underperformed"


def test_continuous_plan_outcome_uses_duration():
    st = {"steps": [{"type": "work", "dur_s": 4500.0, "speed_lo": 2.8, "speed_hi": 2.9}]}
    assert is_continuous(st)
    assert not is_continuous({"steps": [{"type": "repeat", "count": 2, "steps": [{"type": "work", "dur_s": 60}]}]})
    r = compare_continuous(st, 2422.0, 7100.0)
    assert r["label"] == "underperformed" and r["compliance_pct"] == 53.8
    assert compare_continuous(st, 4500.0, 13000.0)["label"] == "on_target"
    assert compare_continuous({"steps": [{"type": "work"}]}, 100.0, 100.0) is None


def test_continuous_garmin_plan_is_not_marked_skipped_when_executed():
    c = mem_conn()
    a = seed_run(c, sid="1", date="2026-09-27", dist=9300.0, moving=3318)
    st = json.dumps({"steps": [{"type": "work", "dur_s": 2340.0}]})
    _plan(c, "2026-09-27", "easy", None, source="garmin", ssys="garmin", structure=st)
    match_week_activities(c, MON)
    label, comp = c.execute("SELECT outcome_label, compliance_pct FROM session_outcomes").fetchone()
    assert label == "overperformed" and comp == 100.0


def test_rematch_resets_wrong_completion_and_replan_trims_after_race():
    from src.training.rematch import rematch, replan_future
    c = mem_conn()
    a = seed_run(c, sid="1", date="2026-09-27", dist=9300.0, moving=3300)
    _plan(c, "2026-09-27", "long", 26.0, act_id=a, done=1)                       # 잘못된 자동 완료
    _plan(c, "2026-09-26", "easy", 8.0, done=1)                                  # 수동 완료(연결 없음) — 보존
    r = rematch(c, MON, date(2026, 9, 27))
    assert r["reset"] == 1
    assert c.execute("SELECT completed FROM planned_workouts WHERE date='2026-09-27'").fetchone()[0] == 0
    assert c.execute("SELECT completed FROM planned_workouts WHERE date='2026-09-26'").fetchone()[0] == 1
    c.execute("INSERT INTO goals (name, race_date, distance_km, status, created_at, plan_weeks) "
              "VALUES ('m', '2026-11-22', 42.195, 'active', '2026-09-24 10:00:00', 16)")
    _plan(c, "2026-12-01", "easy", 8.0)                                          # 대회 이후 행
    out = replan_future(c, 1, today=date(2026, 9, 27))
    assert out["weeks"] == 9 and out["deleted"] == 1
    assert c.execute("SELECT plan_weeks FROM goals").fetchone()[0] == 9
    assert c.execute("SELECT workout_type FROM planned_workouts WHERE date='2026-11-22'").fetchone()[0] == "race"


def test_taper_wins_over_recovery_week():
    from src.training.planner_rules import training_phase
    assert training_phase(1, 3) == "taper"
    assert training_phase(6, 3) == "recovery_week"
    assert training_phase(6, 0) == "peak" and training_phase(12, 0) == "build" and training_phase(None, 0) == "base"
