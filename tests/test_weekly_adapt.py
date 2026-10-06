"""주간 적응 규칙(§3.4) — 표의 행마다 1건 + 경계값, 행 조정, 서비스 가드."""
import sqlite3

from src.services.weekly_adapt_service import adapt_plan
from src.training import weekly_adapt as WA


def _x(**kw):
    base = dict(volume_pct=1.0, quality_pct=1.0, last_actual_km=40.0, this_target_km=42.0,
                sched_next_km=46.0, acwr=1.1, crs_red_days=0, injury_flag=False, next_phase="build")
    base.update(kw)
    return WA.AdaptInput(**base)


def test_decide_table_rows():
    d = WA.decide(_x(injury_flag=True))
    assert (d.rule, d.target_km, d.max_quality, d.freeze_ladder) == ("injury", 36.0, 1, True)
    assert WA.decide(_x(crs_red_days=2)).rule == "injury"
    d = WA.decide(_x(volume_pct=0.5))
    assert (d.rule, d.target_km, d.freeze_ladder) == ("low", 40.0, True)
    d = WA.decide(_x(volume_pct=0.8))
    assert (d.rule, d.target_km) == ("mid", 42.0)
    assert WA.decide(_x()).rule == "proceed"
    d = WA.decide(_x(volume_pct=1.3))
    assert d.rule == "proceed" and d.target_km == 46.0
    assert WA.decide(_x(volume_pct=None)).rule == "no_data"


def test_decide_boundaries_and_gates():
    assert WA.decide(_x(volume_pct=0.70)).rule == "mid"
    assert WA.decide(_x(volume_pct=0.69)).rule == "low"
    assert WA.decide(_x(volume_pct=0.90)).rule == "proceed"
    assert WA.decide(_x(quality_pct=0.4)).rule == "mid"
    assert WA.decide(_x(acwr=1.4)).rule == "mid"
    assert WA.decide(_x(crs_red_days=1)).rule == "proceed"


def test_taper_start_not_pushed_by_repeat():
    d = WA.decide(_x(volume_pct=0.8, this_target_km=60.0, sched_next_km=40.0, next_phase="taper"))
    assert d.target_km == 40.0


def _rows():
    return [{"date": f"2026-10-{12 + i}", "workout_type": t, "distance_km": km, "rationale": "", "structure": {}}
            for i, (t, km) in enumerate([("easy", 8.0), ("tempo", 10.0), ("rest", 0.0), ("interval", 10.0),
                                         ("easy", 8.0), ("rest", 0.0), ("long", 10.0)])]


def test_apply_to_rows_scales_and_limits_quality():
    d = WA.decide(_x(injury_flag=True, last_actual_km=23.4, sched_next_km=46.0))
    out = WA.apply_to_rows(_rows(), d, 46.0)
    assert sum(1 for r in out if r["workout_type"] in ("tempo", "interval")) == 1
    assert round(sum(r["distance_km"] for r in out), 0) <= 22
    assert "주간 적응" in out[0]["rationale"] and out[2]["workout_type"] == "rest"
    assert _rows()[3]["workout_type"] == "interval"      # 입력 불변


def test_adapt_plan_noop_for_v1_or_no_goal():
    conn = sqlite3.connect(":memory:")
    rows = _rows()
    assert adapt_plan(conn, None, rows, __import__("datetime").date(2026, 10, 12), "full", None) is rows
