"""P7-PRED-51: DARP r4 섀도 — 칼만 결합, 비대칭·유지 앵커 변형, T0 동작, 섀도는 primary 가 아님."""
import json

from src.metrics.base import CalcContext
from src.metrics.darp_r4 import DARPShadowAsymCalculator, DARPShadowCalculator as DARPCalculator
from src.metrics.prediction import core_r4 as pc
from src.utils.metric_priority import get_provider_priority
from src.utils.db_helpers import upsert_metric
from tests.helpers_pred import mem_conn, seed_laps, seed_run

DAY = "2026-09-26"
INTER = [(2000, 720, 130, "WARMUP", None, None)] + [(1000, 250, 168, "ACTIVE", None, 182), (300, 150, 140, "RECOVERY", None, None)] * 5 \
    + [(1500, 540, 135, "COOLDOWN", None, None)]


def _seed(c, with_ref=False, hr=True):
    rid = seed_run(c, sid="race", date="2026-08-01", name="여름 10K 대회", dist=10000.0, moving=2700,
                   avg_hr=176 if hr else None, max_hr=190 if hr else None, event_type="race")
    c.execute("INSERT INTO race_results (activity_id, distance_m, official_time_sec, effort) VALUES (?,?,?, 'allout')",
              (rid, 10000.0, 2700))
    upsert_metric(c, "activity", str(rid), "weather_temp_c", "open_meteo", numeric_value=25.0)
    tid = seed_run(c, sid="tempo", date="2026-09-20", name="템포", dist=6000.0, moving=1560, avg_hr=170, max_hr=180)
    seed_laps(c, tid, [(1000, 360, 140, "WARMUP", None, None)] + [(1000, 262, 172, "ACTIVE", None, None)] * 4
              + [(1000, 360, 150, "COOLDOWN", None, None)])
    iid = seed_run(c, sid="int", date="2026-09-12", name="인터벌", dist=8800.0, moving=3300, avg_hr=155, max_hr=182)
    seed_laps(c, iid, INTER)
    if hr:
        prof = {"self": {"hrmax": 190.0, "lthr": 175.0},
                "ref": {"source": "garmin", "lthr": 177.0, "hrmax": None} if with_ref else None}
        upsert_metric(c, "daily", DAY, "hr_profile", "runpulse:formula_v1", numeric_value=175.0, json_value=prof)


def _res(calc, c):
    return {r.metric_name: r for r in calc.compute(CalcContext(conn=c, scope_type="daily", scope_id=DAY))}


def test_path_c_kalman_combination():
    c = mem_conn()
    _seed(c)
    res = _res(DARPCalculator(), c)
    base = json.loads(res["race_pred_vdot"].json_value)
    assert base["n_obs"] == 3 and set(base["weights"]) == {"race", "T", "I"} and abs(sum(base["weights"].values()) - 1) < 0.01
    assert [s["zone"] for s in base["recent_sets"]] == ["I", "T"] and base["k"] == 1.06 and base["k_pairs"] == 0
    a15 = pc.vdot_at_15c(10000, 2700, 25.0, -0.62, -0.84)
    assert min(a15, 47.0) - 3 < res["race_pred_vdot"].numeric_value < max(a15, 50.0)
    js = json.loads(res["race_pred_10k_sec"].json_value)
    assert js["low_s"] < res["race_pred_10k_sec"].numeric_value < js["high_s"] and 0 < js["confidence"] < 1
    assert js["by_temp"]["15"] == res["race_pred_10k_sec"].numeric_value and js["by_temp"]["25"] > js["by_temp"]["15"]
    assert set(js["signals_s"]) == {"race", "T", "I"} and js["contributions"] == base["weights"]
    mj = json.loads(res["race_pred_marathon_sec"].json_value)          # 8주 주평균 3km → Tanda 미적용
    assert "tanda_s" not in mj and any("Tanda" in x for x in mj["reasons"])
    assert any("외삽" in x for x in mj["reasons"])                     # 최장 10km < 42.2km


def test_shadow_providers_never_primary():
    assert get_provider_priority(DARPCalculator.provider) > get_provider_priority("runpulse:formula_v1")
    assert get_provider_priority(DARPShadowAsymCalculator.provider) > get_provider_priority("runpulse:formula_v1")


def test_asym_maint_variant():
    c = mem_conn()
    _seed(c)
    upsert_metric(c, "daily", "2026-08-01", "ctl", "runpulse:formula_v1", numeric_value=60.0)
    upsert_metric(c, "daily", "2026-09-25", "ctl", "runpulse:formula_v1", numeric_value=30.0)   # 대회 후 CTL 절반
    base = json.loads(_res(DARPCalculator(), c)["race_pred_vdot"].json_value)
    asym = _res(DARPShadowAsymCalculator(), c)
    aj = json.loads(asym["race_pred_vdot"].json_value)
    assert base["variant"] == "base" and aj["variant"] == "asym_maint"
    assert aj["vdot15"] != base["vdot15"]


def test_maint_loss_only_when_ctl_drops():
    from src.metrics.prediction import signals_r4 as sg
    runs = [{"id": 1, "date": "2026-08-01", "nominal_m": 10000.0, "is_race": True, "avg_hr": None, "perf_time_s": 2700,
             "effort": "allout", "official_time_s": None, "ambient_c": 15.0}]
    up = sg.allout_races(runs, DAY, None, -0.62, -0.84, lambda d: 60.0 if d == "2026-08-01" else 70.0)
    down = sg.allout_races(runs, DAY, None, -0.62, -0.84, lambda d: 60.0 if d == "2026-08-01" else 30.0)
    assert up[0]["maint_loss"] == 0.0 and abs(down[0]["maint_loss"] - pc.MAINT_ALPHA * 0.5) < 1e-9
    assert down[0]["vdot15"] < up[0]["vdot15"]


def test_t0_without_heart_rate():
    c = mem_conn()
    _seed(c, hr=False)
    res = _res(DARPCalculator(), c)                                  # hr_profile 없음 → H 없음, 세트·대회만
    base = json.loads(res["race_pred_vdot"].json_value)
    assert base["hr"] is None and base["lthr"] is None and "race_pred_5k_sec" in res
    assert set(base["weights"]) == {"race", "T", "I"}


def test_no_data_returns_empty():
    assert DARPCalculator().compute(CalcContext(conn=mem_conn(), scope_type="daily", scope_id=DAY)) == []


def test_paced_race_is_lower_bound_not_anchor():
    c = mem_conn()
    _seed(c)
    pid = seed_run(c, sid="paced", date="2026-09-05", name="숲길 10K 대회", dist=10000.0, moving=2820, avg_hr=163, max_hr=178,
                   event_type="race")
    c.execute("INSERT INTO race_results (activity_id, distance_m, effort) VALUES (?, 10000, 'paced')", (pid,))
    base = json.loads(_res(DARPCalculator(), c)["race_pred_vdot"].json_value)
    assert "paced" in base["weights"] and base["n_obs"] == 4


def test_auto_effort_by_duration():
    from src.metrics.prediction import signals_r4 as sg
    race = {"id": 1, "date": "2026-09-12", "nominal_m": 10000.0, "is_race": True, "avg_hr": 163, "max_hr": 178,
            "perf_time_s": 2818, "effort": None, "official_time_s": None, "ambient_c": 18.6}
    assert not sg.allout_races([race], DAY, 192.0, -0.62, -0.84, lthr=177.6)          # 9/12 → 자동 submax
    assert not sg.paced_races([race], DAY, -0.62, -0.84, 192.0, 177.6)                  # submax 는 하한으로도 안 씀
    mara = dict(race, id=2, nominal_m=42195.0, avg_hr=147, max_hr=158, perf_time_s=13332, date="2026-06-01")
    p = sg.paced_races([mara], DAY, -0.62, -0.84, 185.0, 170.8)                          # 풀: uncertain → 하한 + 확인 요청
    assert p and p[0]["uncertain"] and not sg.allout_races([mara], DAY, 185.0, -0.62, -0.84, lthr=170.8)
    assert sg.allout_races([dict(race, effort="allout")], DAY, 192.0, -0.62, -0.84, lthr=177.6)   # 사용자 입력 우선
