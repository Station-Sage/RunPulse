"""외부 계획 인제스트(P7-PRED-44) — Garmin 실측 응답 형태(2026-09-26) 기반 파서·저장·이행률."""
import json

from src.sync import plan_ingest as pi
from src.sync import plan_ingest_intervals as pii
from tests.helpers_pred import mem_conn, seed_run

# 실측 get_workout_by_id 응답 축약: 1000m×2 + 회복 180초 + 웜업/쿨다운(lap.button)
WORKOUT = {
    "workoutId": 1693421320, "workoutName": "1. 1000m * 2, 템포 감각", "sportType": {"sportTypeKey": "running"},
    "estimatedDistanceInMeters": 0.0,
    "workoutSegments": [{"workoutSteps": [
        {"type": "ExecutableStepDTO", "stepType": {"stepTypeKey": "warmup"}, "endCondition": {"conditionTypeKey": "lap.button"},
         "endConditionValue": 0.0, "targetType": {"workoutTargetTypeKey": "no.target"}, "targetValueOne": None, "targetValueTwo": 0.0},
        {"type": "RepeatGroupDTO", "numberOfIterations": 2, "workoutSteps": [
            {"type": "ExecutableStepDTO", "stepType": {"stepTypeKey": "interval"}, "endCondition": {"conditionTypeKey": "distance"},
             "endConditionValue": 1000.0, "targetType": {"workoutTargetTypeKey": "pace.zone"},
             "targetValueOne": 4.0816327, "targetValueTwo": 3.6363636},
            {"type": "ExecutableStepDTO", "stepType": {"stepTypeKey": "recovery"}, "endCondition": {"conditionTypeKey": "time"},
             "endConditionValue": 180.0, "targetType": {"workoutTargetTypeKey": "pace.zone"},
             "targetValueOne": 2.7777778, "targetValueTwo": 2.2222222}]},
        {"type": "ExecutableStepDTO", "stepType": {"stepTypeKey": "cooldown"}, "endCondition": {"conditionTypeKey": "lap.button"},
         "endConditionValue": 0.0, "targetType": {"workoutTargetTypeKey": "no.target"}, "targetValueOne": None, "targetValueTwo": 0.0},
        {"type": "ExecutableStepDTO", "stepType": {"stepTypeKey": "mystery"}, "endCondition": {"conditionTypeKey": "time"},
         "endConditionValue": 60.0, "targetType": {"workoutTargetTypeKey": "no.target"}},
    ]}],
}
TASK = {"taskWorkout": {"workoutName": "장거리 달리기", "workoutDescription": "5:50/km", "scheduledDate": "2026-09-26T09:36:16.0",
                        "estimatedDurationInSecs": 4500, "workoutPhrase": "LONG_WORKOUT", "restDay": False,
                        "sportType": {"sportTypeKey": "running"}}}


def test_parse_garmin_workout_structure_and_unknown_step_skipped():
    p = pi.parse_garmin_workout(WORKOUT)
    steps = p["structure"]["steps"]
    assert [s["type"] for s in steps] == ["warmup", "repeat", "cooldown"]      # mystery 단계는 work 로 오인하지 않고 제외
    rep = steps[1]
    assert rep["count"] == 2 and [s["type"] for s in rep["steps"]] == ["work", "rest"]
    assert rep["steps"][0] == {"type": "work", "dist_m": 1000.0, "speed_lo": 3.6364, "speed_hi": 4.0816}
    assert rep["steps"][1]["dur_s"] == 180.0
    assert "dur_s" not in steps[0] and "dist_m" not in steps[0]               # lap.button = 열린 종료
    assert p["workout_type"] == "tempo" and p["sport"] == "running"           # 반복 2회(<3) + 이름의 '템포'


def test_parse_adaptive_task_and_rest_day():
    p = pi.parse_garmin_adaptive_task(TASK)
    assert p["date"] == "2026-09-26" and p["workout_type"] == "long"
    assert p["structure"]["steps"] == [{"type": "work", "dur_s": 4500.0, "speed_lo": 2.8571, "speed_hi": 2.8571}]
    assert pi.parse_garmin_adaptive_task({"taskWorkout": {"restDay": True, "scheduledDate": "2026-09-27T00:00:00.0"}}) is None


# 실측 Intervals 이벤트(2026-09-27) 축약: Cruise Intervals — 웜업 + 6×(800m 102~105%pace / 60초 회복) + 쿨다운
IV_EVENT = {"id": 55790880, "start_date_local": "2025-03-04T00:00:00", "name": "Cruise Intervals", "type": "Run", "category": "WORKOUT",
            "distance": 9500.0, "paired_activity_id": "i70000001",
            "workout_doc": {"steps": [
                {"warmup": True, "duration": 600},
                {"reps": 6, "text": "Main set 6x", "steps": [
                    {"pace": {"end": 105, "start": 102, "units": "%pace"}, "distance": 800, "duration": 237},
                    {"pace": {"end": 82, "start": 76, "units": "%pace"}, "duration": 60}]},
                {"cooldown": True, "duration": 300}]}}
IV_EASY = {"id": 55790875, "start_date_local": "2025-02-18T00:00:00", "name": "Easy Run", "type": "Run", "category": "WORKOUT",
           "distance": 7676.47, "paired_activity_id": None,
           "workout_doc": {"steps": [{"warmup": True, "duration": 600},
                                     {"pace": {"end": 92, "start": 82, "units": "%pace"}, "duration": 2700},
                                     {"cooldown": True, "duration": 300}]}}


def test_parse_intervals_event_real_shapes():
    p = pii.parse_intervals_event(IV_EVENT)
    assert p["date"] == "2025-03-04" and p["workout_type"] == "interval" and p["distance_km"] == 9.5
    assert p["structure"]["steps"] == [
        {"type": "warmup", "dur_s": 600.0},
        {"type": "repeat", "count": 6, "steps": [{"type": "work", "dist_m": 800.0}, {"type": "rest", "dur_s": 60.0}]},
        {"type": "cooldown", "dur_s": 300.0}]
    easy = pii.parse_intervals_event(IV_EASY)
    assert easy["structure"] is None and easy["workout_type"] == "easy"        # 느린 본 구간만 있으면 품질 구조 없음
    assert pii.parse_intervals_event({"id": 2, "start_date_local": "2026-10-01", "category": "NOTE"}) is None


def test_ingest_intervals_links_paired_activity():
    c = mem_conn()
    aid = seed_run(c, source="intervals", sid="i70000001", date="2025-03-04", dist=9500.0, moving=3300)
    st = pii.ingest_intervals_events(c, [IV_EVENT, IV_EASY, {"id": 9, "category": "NOTE", "start_date_local": "2025-03-05"}])
    assert st["planned"] == 2 and st["linked"] == 1
    row = c.execute("SELECT completed, matched_activity_id, source_system FROM planned_workouts WHERE external_id='55790880'").fetchone()
    assert row == (1, aid, "intervals")
    assert c.execute("SELECT count(*) FROM session_outcomes").fetchone()[0] == 1
    assert pii.ingest_intervals_events(c, [IV_EVENT])["planned"] == 1 and c.execute("SELECT count(*) FROM planned_workouts").fetchone()[0] == 2


def test_store_planned_upsert_keeps_runpulse_rows():
    c = mem_conn()
    c.execute("INSERT INTO planned_workouts (date, workout_type, source, source_system) VALUES ('2026-09-26','easy','planner','runpulse')")
    parsed = pi.parse_garmin_adaptive_task(TASK)
    a = pi.store_planned(c, source_system="garmin", external_id="fbt:1:2026-09-26", date="2026-09-26", parsed=parsed)
    b = pi.store_planned(c, source_system="garmin", external_id="fbt:1:2026-09-26", date="2026-09-26",
                         parsed=dict(parsed, workout_type="tempo"))
    assert a == b
    rows = c.execute("SELECT source_system, workout_type FROM planned_workouts WHERE date='2026-09-26' ORDER BY id").fetchall()
    assert rows == [("runpulse", "easy"), ("garmin", "tempo")]                # 같은 날짜 앱 계획과 공존


class FakeClient:
    def __init__(self):
        self.calls = []

    def get_workout_by_id(self, wid):
        self.calls.append(wid)
        if wid == 999:
            raise RuntimeError("404")
        return WORKOUT


def test_ingest_garmin_executed_links_by_workout_id_and_skips_deleted():
    c = mem_conn()
    aid = seed_run(c, sid="111", date="2026-09-10", dist=6650.0, moving=2166)
    seed_run(c, sid="222", date="2026-09-11")
    for sid, wid in (("111", 1693421320), ("222", 999)):
        c.execute("INSERT INTO source_payloads (source, entity_type, entity_id, payload) VALUES ('garmin','activity_summary',?,?)",
                  (sid, json.dumps({"activityId": int(sid), "workoutId": wid, "startTimeLocal": "2026-09-10 19:00:00"})))
    st = pi.ingest_garmin_executed(c, FakeClient(), pause_s=0)
    assert st["workouts"] == 1 and st["missing"] == 1 and st["planned"] == 1
    row = c.execute("SELECT external_id, completed, matched_activity_id, garmin_workout_id, source_system FROM planned_workouts").fetchone()
    assert row == ("1693421320@2026-09-10", 1, aid, "1693421320", "garmin")
    assert c.execute("SELECT count(*) FROM session_outcomes WHERE planned_id=1").fetchone()[0] == 1
    st2 = pi.ingest_garmin_executed(c, FakeClient(), pause_s=0)              # 재실행은 중복 행을 만들지 않는다
    assert c.execute("SELECT count(*) FROM planned_workouts").fetchone()[0] == 1 and st2["planned"] == 1
