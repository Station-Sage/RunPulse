"""건달프 서브3 방식 adjust — 요일 역할·주간 총량·롱런 상한·테이너 무변경."""
from datetime import date, timedelta

from src.training.methods import candidates_for, get_method
from src.training.plan_finalize import finalize_week

MON = date(2026, 11, 2)   # ISO 주 45(홀수) → 장거리


def _plan(mon, days=(0, 1, 2, 3, 5, 6), km=60.0):
    rows = []
    for i in range(7):
        d = mon + timedelta(days=i)
        on = i in days
        rows.append({"date": d.isoformat(), "workout_type": "easy" if on else "rest",
                     "distance_km": round(km / len(days), 1) if on else 0, "description": "x",
                     "target_pace_min": None, "target_pace_max": None, "target_hr_zone": None,
                     "rationale": "", "source": "t", "interval_prescription": None, "structure": None})
    return rows


def _ctx(mon, phase="build"):
    return {"phase": phase, "vdot": 52.0, "week_start": mon}


def test_registered_full_only_and_run_day_guard():
    m = get_method("gundalf_sub3")
    assert m.id == "gundalf_sub3" and m.distances == frozenset({"full"})
    assert "gundalf_sub3" in [c.id for c in candidates_for("full", 6)]
    assert "gundalf_sub3" not in [c.id for c in candidates_for("full", 3)]
    assert "gundalf_sub3" not in [c.id for c in candidates_for("10k", 6)]


def test_weekday_roles_and_total_kept():
    plan = _plan(MON)
    before = sum(r["distance_km"] for r in plan)
    out = get_method("gundalf_sub3").adjust(plan, _ctx(MON))
    wt = {date.fromisoformat(r["date"]).weekday(): r for r in out}
    assert wt[1]["workout_type"] == "interval" and wt[1]["structure"]
    assert wt[5]["workout_type"] == "long" and wt[5]["distance_km"] <= 0.5 * before + 0.1
    assert wt[4]["workout_type"] == "rest"
    assert wt[2]["distance_km"] <= 20 and wt[6]["distance_km"] <= 20
    after = sum(r["distance_km"] for r in out)
    assert abs(after - before) <= 3.0
    assert finalize_week(out, run_weekdays=[0, 1, 2, 3, 5, 6])


def test_saturday_alternates_by_week_parity():
    a = get_method("gundalf_sub3").adjust(_plan(MON, km=90), _ctx(MON))
    nxt = MON + timedelta(days=7)
    b = get_method("gundalf_sub3").adjust(_plan(nxt, km=90), _ctx(nxt))
    sa = [r for r in a if date.fromisoformat(r["date"]).weekday() == 5][0]
    sb = [r for r in b if date.fromisoformat(r["date"]).weekday() == 5][0]
    assert sa["distance_km"] != sb["distance_km"] and {sa["distance_km"], sb["distance_km"]} == {35.0, 21.0}


def test_saturday_capped_at_half_of_week_when_low_volume():
    out = get_method("gundalf_sub3").adjust(_plan(MON, km=40), _ctx(MON))
    sat = [r for r in out if date.fromisoformat(r["date"]).weekday() == 5][0]
    assert sat["distance_km"] <= 20.1


def test_taper_unchanged_and_missing_run_day_dropped():
    plan = _plan(MON)
    assert get_method("gundalf_sub3").adjust(plan, _ctx(MON, "taper")) is plan
    out = get_method("gundalf_sub3").adjust(_plan(MON, days=(1, 2, 5)), _ctx(MON))
    assert [r["workout_type"] for r in out].count("rest") == 4


# ── gundalf_10k_base ──
import sqlite3

from src.training.methods.gundalf_10k_base import reference_targets
from src.utils.daniels_table import get_race_predictions

TUE_MON = date(2026, 11, 9)


def _acts(rows):
    c = sqlite3.connect(":memory:")
    c.execute("CREATE TABLE activity_summaries (activity_type TEXT, start_time TEXT, distance_m REAL, avg_pace_sec_km REAL)")
    c.executemany("INSERT INTO activity_summaries VALUES ('running',?,?,?)", rows)
    return c


def test_10k_registered_and_guard():
    assert "gundalf_10k_base" in [c.id for c in candidates_for("10k", 5)]
    assert "gundalf_10k_base" not in [c.id for c in candidates_for("full", 5)]


def test_targets_initial_and_independent_success_failure():
    t5 = round(get_race_predictions(50.0)["5k"] / 5.0)
    assert reference_targets(None, 50.0, TUE_MON) == (t5, t5 + 10)
    prev = TUE_MON - timedelta(weeks=1)
    ok = _acts([((prev + timedelta(days=1)).isoformat() + "T07:00", 5000, t5 - 1)])
    assert reference_targets(ok, 50.0, TUE_MON)[0] == t5 - 5
    fail10 = _acts([((prev + timedelta(days=5)).isoformat() + "T07:00", 7000, t5 + 5)])
    a, b = reference_targets(fail10, 50.0, TUE_MON)
    assert a == t5 and b == t5 + 10 + 6          # 남은 3km × 2초


def test_10k_never_faster_than_5k_plus_gap():
    prev = TUE_MON - timedelta(weeks=1)
    c = _acts([((prev + timedelta(days=1)).isoformat() + "T07:00", 2000, 999)])   # 5K 실패 → 5K 목표 상승
    a, b = reference_targets(c, 50.0, TUE_MON)
    assert b >= a + 5


def test_10k_week_layout_and_long_cap():
    plan = _plan(TUE_MON, days=(0, 1, 3, 5, 6), km=45.0)
    out = get_method("gundalf_10k_base").adjust(plan, {"phase": "build", "vdot": 50.0, "week_start": TUE_MON, "conn": None})
    wt = {date.fromisoformat(r["date"]).weekday(): r for r in out}
    assert wt[1]["distance_km"] == 5.0 and wt[5]["distance_km"] == 10.0
    assert wt[6]["workout_type"] == "long" and wt[6]["distance_km"] <= 15.0
    assert get_method("gundalf_10k_base").adjust(plan, {"phase": "taper", "vdot": 50.0, "week_start": TUE_MON}) is plan
