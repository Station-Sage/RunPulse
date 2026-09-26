"""P7-PRED-14: RunHistoryMixin.get_runs / get_active_goal / get_race_results / canonical 시리즈."""
from src.metrics.base import CalcContext
from src.utils.db_helpers import upsert_metric
from tests.helpers_pred import mem_conn, seed_laps, seed_run


def test_get_runs_twin_hr_and_race():
    c = mem_conn()
    g = seed_run(c, sid="g1", name="Forest run", avg_hr=None, max_hr=None, group="G1", event_type="race")
    seed_run(c, source="intervals", sid="i1", name="나는 솔로런 10k", avg_hr=165, max_hr=182, group="G1")
    seed_run(c, source="strava", sid="s1", name="Morning", avg_hr=164, max_hr=186, group="G1")
    ctx = CalcContext(conn=c, scope_type="daily", scope_id="2026-05-10")
    runs = ctx.get_runs(30)
    assert len(runs) == 1
    r = runs[0]
    assert r["id"] == g and r["avg_hr"] == 164 and r["max_hr"] == 186      # intervals 182 절단값 제외
    assert r["is_race"] is True and r["nominal_m"] == 10000.0


def test_get_runs_excludes_end_day_and_laps():
    c = mem_conn()
    a = seed_run(c, sid="a", date="2026-05-09")
    seed_run(c, sid="b", date="2026-05-10")
    seed_laps(c, a, [(1000, 250, 160, "ACTIVE", 4.1, 170), (1000, 360, 140, "RECOVERY", None, 150)])
    ctx = CalcContext(conn=c, scope_type="daily", scope_id="2026-05-10")
    runs = ctx.get_runs(30, with_laps=True, include_end=False)
    assert [x["id"] for x in runs] == [a]
    assert runs[0]["laps"][0]["speed_ms"] == 4.1 and round(runs[0]["laps"][1]["speed_ms"], 3) == 2.778
    assert runs[0]["laps"][0]["itype"] == "ACTIVE"


def test_tempo_name_not_race():
    c = mem_conn()
    seed_run(c, sid="t", name="2. 템포런 10k 빌드")
    ctx = CalcContext(conn=c, scope_type="daily", scope_id="2026-05-10")
    assert ctx.get_runs(5)[0]["is_race"] is False


def test_perf_time_uses_elapsed_when_close():
    c = mem_conn()
    seed_run(c, sid="p", moving=2600, elapsed=2650)
    seed_run(c, sid="q", date="2026-05-08", moving=2600, elapsed=3300)
    ctx = CalcContext(conn=c, scope_type="daily", scope_id="2026-05-10")
    times = {x["date"]: x["perf_time_s"] for x in ctx.get_runs(5)}
    assert times == {"2026-05-09": 2650, "2026-05-08": 2600}


def test_active_goal_and_race_results():
    c = mem_conn()
    c.execute("INSERT INTO goals (name, race_date, distance_km, target_time_sec, status) VALUES ('풀', '2026-11-22', 42.195, 11940, 'active')")
    a = seed_run(c, sid="r")
    c.execute("INSERT INTO race_results (activity_id, distance_m, official_time_sec, effort) VALUES (?, 10000, 2651, 'allout')", (a,))
    ctx = CalcContext(conn=c, scope_type="daily", scope_id="2026-09-26")
    assert ctx.get_active_goal()["target_time_sec"] == 11940
    assert ctx.get_race_results()[a]["effort"] == "allout"


def test_metric_series_canonical_only():
    c = mem_conn()
    a = seed_run(c, sid="g", group="G")
    b = seed_run(c, source="intervals", sid="i", group="G")
    for aid in (a, b):
        upsert_metric(c, "activity", aid, "trimp", "runpulse:formula_v1", numeric_value=100.0)
    ctx = CalcContext(conn=c, scope_type="daily", scope_id="2026-05-10")
    assert len(ctx.get_activity_metric_series("trimp", 5)) == 2
    assert len(ctx.get_activity_metric_series("trimp", 5, canonical_only=True)) == 1
