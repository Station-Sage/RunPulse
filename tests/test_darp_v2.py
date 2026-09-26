"""P7-PRED-51: DARP v2 (c)/(b) 경로."""
import json

from src.metrics.base import CalcContext
from src.metrics.darp import DARPCalculator, DARPRefCalculator, sg_pairs
from src.metrics.prediction import core as pc
from src.utils.db_helpers import upsert_metric
from tests.helpers_pred import mem_conn, seed_laps, seed_run

DAY = "2026-09-26"


def _seed(c, with_ref=False):
    rid = seed_run(c, sid="race", date="2026-08-01", name="여름 10K 대회", dist=10000.0, moving=2700,
                   avg_hr=176, max_hr=190, event_type="race")
    c.execute("INSERT INTO race_results (activity_id, distance_m, official_time_sec, effort) VALUES (?,?,?, 'allout')",
              (rid, 10000.0, 2700))
    upsert_metric(c, "activity", str(rid), "weather_temp_c", "open_meteo", numeric_value=25.0)
    tid = seed_run(c, sid="tempo", date="2026-09-20", name="템포", dist=6000.0, moving=1560, avg_hr=170, max_hr=180)
    seed_laps(c, tid, [(1000, 330, 140, "WARMUP", None, None)] + [(1000, 260, 172, "ACTIVE", None, None)] * 4
              + [(1000, 330, 150, "COOLDOWN", None, None)])
    prof = {"self": {"hrmax": 190.0, "lthr": 175.0}, "ref": {"source": "garmin", "lthr": 177.0, "hrmax": 193.0} if with_ref else None}
    upsert_metric(c, "daily", DAY, "hr_profile", "runpulse:formula_v1", numeric_value=175.0, json_value=prof)


def test_path_c_values():
    c = mem_conn()
    _seed(c)
    res = {r.metric_name: r for r in DARPCalculator().compute(CalcContext(conn=c, scope_type="daily", scope_id=DAY))}
    base = json.loads(res["race_pred_vdot"].json_value)
    a15 = pc.vdot_at_15c(10000, 2700, 25.0, -0.62, -0.84)          # 25℃ 45:00 → 15℃ 등가
    assert base["anchor"]["vdot15"] == round(a15, 2) == 48.78        # 45:00 (VDOT 45.3) @25℃ → 15℃ 등가
    assert base["anchor"]["value"] == round(a15 - 0.16, 2)             # 8주 경과 → (8−6)×0.08 감쇠
    w = pc.vdot(4000, 1040)                                        # 템포 4×1km@4:20, HR 172 ≥ 0.92·175
    assert base["work"]["vdot"] == round(w, 2)
    exp, wts = pc.combine(base["anchor"]["value"], w, None)
    assert res["race_pred_vdot"].numeric_value == round(exp, 2) and base["weights"] == wts
    assert res["race_pred_10k_sec"].numeric_value == round(pc.time_for_vdot(exp, 10000))
    js = json.loads(res["race_pred_10k_sec"].json_value)
    assert js["low_s"] < res["race_pred_10k_sec"].numeric_value < js["high_s"]
    assert js["by_temp"]["15"] == res["race_pred_10k_sec"].numeric_value and js["by_temp"]["25"] > js["by_temp"]["15"]
    assert base["k"] == 1.06 and base["k_pairs"] == 0
    mj = json.loads(res["race_pred_marathon_sec"].json_value)          # 8주 16km → Tanda 미적용
    assert "tanda_s" not in mj and any("볼륨" in x for x in mj["reasons"])
    assert res["race_pred_marathon_sec"].numeric_value == round(pc.time_for_vdot(exp, 42195))


def test_path_b_needs_ref():
    c = mem_conn()
    _seed(c)
    ctx = CalcContext(conn=c, scope_type="daily", scope_id=DAY)
    assert DARPRefCalculator().compute(ctx) == []
    c2 = mem_conn()
    _seed(c2, with_ref=True)
    res = {r.metric_name: r for r in DARPRefCalculator().compute(CalcContext(conn=c2, scope_type="daily", scope_id=DAY))}
    b = json.loads(res["race_pred_vdot"].json_value)
    assert b["lthr"] == 177.0 and b["hrmax"] == 193.0                 # 기기 HRmax 없음 → 177/0.917
    assert DARPRefCalculator.provider == "runpulse:ref_garmin"


def test_pairs_same_distance_skipped():
    r = [{"nominal_m": 10000.0, "vdot15": 45, "weeks": 2}, {"nominal_m": 10000.0, "vdot15": 46, "weeks": 5},
         {"nominal_m": 21097.5, "vdot15": 44, "weeks": 4}, {"nominal_m": 5000.0, "vdot15": 44, "weeks": 30}]
    p = sg_pairs(r)                                              # 30주 전 5K 는 26주 창 밖
    assert len(p) == 2 and all(x["d2"] == 21097.5 for x in p) and p[0]["gap_days"] == 14.0


def test_5k_best_effort_signal():
    c = mem_conn()
    _seed(c)
    c.execute("INSERT INTO activity_best_efforts (activity_id, source, effort_name, elapsed_sec, distance_m) "
              "VALUES (2, 'strava', '5K', 1300, 5000)")
    res = {r.metric_name: r for r in DARPCalculator().compute(CalcContext(conn=c, scope_type="daily", scope_id=DAY))}
    j5 = json.loads(res["race_pred_5k_sec"].json_value)
    assert j5["signals_s"]["best_effort"] == 1300 and set(j5["signals_s"]) == {"race", "work", "best_effort"}
    assert "근거 신호 2개" not in j5["reasons"]                       # 신호 3개
    assert "best_effort" not in json.loads(res["race_pred_10k_sec"].json_value)["signals_s"]
