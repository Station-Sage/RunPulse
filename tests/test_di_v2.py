"""P7-PRED-89: DI v2 — 랩 기반 후반 효율 유지율, 상한 없음."""
import json

from src.metrics.base import CalcContext
from src.metrics.di import DICalculator
from tests.helpers_pred import mem_conn, seed_laps, seed_run


def _long(c, sid, date, hr_late, speed_late_s=300):
    rid = seed_run(c, sid=sid, date=date, name="롱런", dist=20000.0, moving=6000, avg_hr=150, max_hr=165)
    seed_laps(c, rid, [(1000, 300, 140, "ACTIVE", None, None)] * 10 + [(1000, speed_late_s, hr_late, "ACTIVE", None, None)] * 10)


def test_drift_lowers_di_and_no_cap():
    c = mem_conn()
    _long(c, "a", "2026-09-10", 154)          # 후반 HR +10% → 효율 ≈ 91
    r = DICalculator().compute(CalcContext(conn=c, scope_type="daily", scope_id="2026-09-26"))
    assert 88 < r[0].numeric_value < 94 and json.loads(r[0].json_value)["runs"][0]["basis"] == "ef"
    c2 = mem_conn()
    _long(c2, "b", "2026-09-10", 135, 290)    # 후반이 더 빠르고 HR 낮음 → 100 초과
    r2 = DICalculator().compute(CalcContext(conn=c2, scope_type="daily", scope_id="2026-09-26"))
    assert r2[0].numeric_value > 100


def test_short_runs_empty():
    c = mem_conn()
    seed_run(c, sid="s", date="2026-09-10", moving=3000)
    assert DICalculator().compute(CalcContext(conn=c, scope_type="daily", scope_id="2026-09-26")) == []
