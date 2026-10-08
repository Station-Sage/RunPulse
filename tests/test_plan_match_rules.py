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
    assert r["label"] == "underperformed" and r["compliance_pct"] == 72.3      # 볼륨 54% + 페이스 적중
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


def test_plan_structure_for_each_workout_type():
    from src.training.plan_structure import structure_for_plan
    rx = json.dumps({"sets": 5, "rep_m": 1000, "rest_sec": 120, "interval_pace": 265})
    iv = structure_for_plan("interval", 8.0, 265, 280, rx)
    assert iv["steps"][1]["count"] == 5 and iv["steps"][1]["steps"][0]["dist_m"] == 1000.0
    assert 3.6 < iv["steps"][1]["steps"][0]["speed_lo"] < 3.9
    easy = structure_for_plan("easy", 10.0, 365, 405)
    assert easy["steps"][0]["dist_m"] == 10000.0 and easy["steps"][0]["max_only"] is True
    assert "max_only" not in structure_for_plan("tempo", 8.0, 300, 320)["steps"][0]
    assert structure_for_plan("rest", None, None, None) is None and structure_for_plan("race", 42.2, None, None) is None
    assert structure_for_plan("interval", 8.0, 265, 280, None) is None


def test_easy_run_too_fast_is_modified_not_on_target():
    st = {"steps": [{"type": "work", "dist_m": 10000.0, "speed_lo": 2.47, "speed_hi": 2.74, "max_only": True, "min_share": 0.8}]}
    fast = compare_continuous(st, 2700.0, 10000.0, [(1000.0, 270.0)] * 10)      # 4:30/km — 이지 상한(6:05)보다 훨씬 빠름
    ok = compare_continuous(st, 3800.0, 10000.0, [(1000.0, 380.0)] * 10)        # 6:20/km
    assert fast["label"] == "modified" and fast["target_hit_pct"] == 0.0
    assert ok["label"] == "on_target" and ok["target_hit_pct"] == 100.0 and ok["compliance_pct"] > fast["compliance_pct"]


def test_matcher_rejects_hard_session_for_easy_plan_and_uses_set_analysis():
    from src.utils.db_helpers import upsert_metric
    c = mem_conn()
    a = seed_run(c, sid="1", date="2026-09-22", dist=8000.0, moving=2400)
    upsert_metric(c, "activity", str(a), "workout_type_classified", "runpulse:rule_v2", text_value="interval",
                  json_value={"type": "interval", "bouts": []})
    _plan(c, "2026-09-22", "easy", 8.0)                                           # 이지 계획에 인터벌 활동 — 다른 세션
    assert match_week_activities(c, MON) == 0
    b = seed_run(c, sid="2", date="2026-09-23", dist=8000.0, moving=2700)
    bouts = [{"dist_m": 1000.0, "dur_s": 250.0, "speed_ms": 4.0, "hr": 170}] * 3         # 5세트 계획을 3세트만
    upsert_metric(c, "activity", str(b), "workout_type_classified", "runpulse:rule_v2", text_value="interval",
                  json_value={"type": "interval", "bouts": bouts})
    st = json.dumps({"steps": [{"type": "repeat", "count": 5, "steps": [
        {"type": "work", "dist_m": 1000.0, "speed_lo": 3.8, "speed_hi": 4.1}, {"type": "rest", "dur_s": 90}]}]})
    _plan(c, "2026-09-23", "interval", 8.0, structure=st)
    match_week_activities(c, MON)
    done, label, sets = c.execute("SELECT p.completed, o.outcome_label, json_extract(o.segment_match_json,'$.sets_done') "
                                  "FROM planned_workouts p JOIN session_outcomes o ON o.planned_id=p.id "
                                  "WHERE p.date='2026-09-23'").fetchone()
    assert sets == 3 and label in ("underperformed", "modified") and done == 0       # 3/5세트 → 볼륨 미달로 미이행


def test_adjustment_skips_day_already_executed():
    from src.training.adjuster import adjust_todays_plan
    c = mem_conn()
    a = seed_run(c, sid="1", date="2026-09-27", dist=9300.0, moving=3300)
    _plan(c, "2026-09-27", "long", 26.0)
    assert adjust_todays_plan(c, date="2026-09-27") is not None
    _plan(c, "2026-09-27", "easy", None, source="garmin", ssys="garmin", act_id=a, done=1)
    assert adjust_todays_plan(c, date="2026-09-27") is None


def _accept_adj(c, d, before, after):
    pid = c.execute("SELECT id FROM planned_workouts WHERE date=?", (d,)).fetchone()[0]
    c.execute("INSERT INTO plan_adjustments(workout_id,date,source,op,before_json,after_json,rule_version,decision)"
              " VALUES (?,?,'crs','replace',?,?,'adjuster_v1','accepted')",
              (pid, d, json.dumps(before), json.dumps(after)))


def test_matcher_uses_accepted_adjustment_for_rest_and_distance_gate():
    c = mem_conn()
    seed_run(c, sid="1", date="2026-09-26", dist=7000.0, moving=2400)
    _plan(c, "2026-09-26", "interval", 7.0)
    _accept_adj(c, "2026-09-26", {"workout_type": "interval", "distance_km": 7.0}, {"workout_type": "rest"})
    assert match_week_activities(c, MON) == 0
    c2 = mem_conn()
    a = seed_run(c2, sid="1", date="2026-09-26", dist=7000.0, moving=2400)
    _plan(c2, "2026-09-26", "interval", 7.0)
    _accept_adj(c2, "2026-09-26", {"workout_type": "interval", "distance_km": 7.0},
                {"workout_type": "easy", "distance_km": 7.0})
    assert match_week_activities(c2, MON) == 1
    assert c2.execute("SELECT matched_activity_id FROM planned_workouts").fetchone()[0] == a
