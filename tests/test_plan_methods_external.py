"""외부 방식 7종 adjust — 후보 가드·요일 역할·총량·롱런 상한·테이퍼 무변경·finalize 불변식."""
import copy
from datetime import date

import pytest

from src.training.methods import candidates_for, get_method
from src.training.plan_finalize import finalize_week, week_violations
from tests.test_plan_methods_gundalf import MON, _ctx, _plan

IDS = ["threshold_vo2", "threshold_tempo", "hr_z2", "marathon_specific", "hansons", "first_run3", "higdon_novice"]
DAYS6 = (0, 1, 2, 3, 5, 6)


def _ctx2(phase="build", dl="full"):
    c = _ctx(MON, phase)
    c["dlabel"] = dl
    return c


def _wd(plan):
    return {date.fromisoformat(r["date"]).weekday(): r for r in plan}


def test_candidate_guards():
    ids = lambda d, n: [c.id for c in candidates_for(d, n)]  # noqa: E731
    assert "threshold_vo2" in ids("10k", 4) and "threshold_vo2" not in ids("10k", 3)
    assert "threshold_tempo" in ids("half", 4) and "threshold_tempo" not in ids("full", 6)
    assert "hansons" in ids("full", 6) and "hansons" not in ids("full", 5)
    assert "hr_z2" in ids("full", 3) and "higdon_novice" not in ids("10k", 6)
    assert all("first_run3" in ids(d, 3) for d in ("10k", "half", "full"))


@pytest.mark.parametrize("mid", IDS)
@pytest.mark.parametrize("phase", ["base", "build", "peak", "recovery_week"])
def test_invariants(mid, phase):
    plan = _plan(MON, DAYS6, 60.0)
    out = get_method(mid).adjust(copy.deepcopy(plan), _ctx2(phase))
    out = finalize_week(out, run_weekdays=set(DAYS6))
    assert week_violations(out, set(DAYS6)) == []
    runs = [r for r in out if r["workout_type"] not in ("rest", "race")]
    assert runs and all(r["distance_km"] > 0 for r in runs)
    for r in runs:
        if r["workout_type"] == "interval":
            assert r["structure"] and r["interval_prescription"]


@pytest.mark.parametrize("mid", IDS)
def test_taper_unchanged_except_first_run3(mid):
    if mid == "first_run3":
        return
    plan = _plan(MON, DAYS6, 40.0)
    assert get_method(mid).adjust(copy.deepcopy(plan), _ctx2("taper")) == plan


def test_total_kept_for_slot_methods():
    for mid in ("threshold_vo2", "hr_z2", "higdon_novice", "hansons", "marathon_specific"):
        out = get_method(mid).adjust(_plan(MON, DAYS6, 60.0), _ctx2("build"))
        tot = sum(r["distance_km"] for r in out)
        assert abs(tot - 60.0) <= 6.0, (mid, tot)


def test_higdon_all_easy_and_long_cap():
    out = get_method("higdon_novice").adjust(_plan(MON, DAYS6, 90.0), _ctx2("peak", "half"))
    assert {r["workout_type"] for r in out if r["distance_km"]} == {"easy", "long"}
    assert max(r["distance_km"] for r in out) <= 20.1


def test_hansons_long_cap_and_three_sos():
    out = get_method("hansons").adjust(_plan(MON, DAYS6, 100.0), _ctx2("peak"))
    kinds = [r["workout_type"] for r in out]
    assert kinds.count("interval") == 1 and kinds.count("tempo") == 1 and kinds.count("long") == 1
    assert max(r["distance_km"] for r in out if r["workout_type"] == "long") <= 26.0


def test_first_run3_three_runs_only():
    out = get_method("first_run3").adjust(_plan(MON, DAYS6, 45.0), _ctx2("build", "half"))
    runs = [r for r in out if r["distance_km"] > 0]
    assert sorted(r["workout_type"] for r in runs) == ["interval", "long", "tempo"]
    assert sum(1 for r in out if r["workout_type"] == "rest") == 4
    assert _wd(out)[6]["workout_type"] == "long"


def test_marathon_specific_mp_long_in_peak():
    out = get_method("marathon_specific").adjust(_plan(MON, DAYS6, 100.0), _ctx2("peak"))
    lg = _wd(out)[6]
    assert lg["workout_type"] == "long" and "마라톤 페이스" in lg["description"]
    assert lg["distance_km"] <= 35.0


def test_threshold_base_phase_single_quality():
    out = get_method("threshold_vo2").adjust(_plan(MON, DAYS6, 50.0), _ctx2("base", "10k"))
    assert [r["workout_type"] for r in out].count("interval") == 1
