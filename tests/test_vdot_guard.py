"""P7-PRED-84: runpulse_vdot moving_time 붕괴 가드."""
from src.metrics.base import CalcContext
from src.metrics.vdot import VDOTCalculator
from tests.helpers_pred import mem_conn, seed_run


def _vd(moving):
    c = mem_conn()
    aid = seed_run(c, sid="1", dist=10000.0, moving=moving)
    return VDOTCalculator().compute(CalcContext(conn=c, scope_type="activity", scope_id=str(aid)))


def test_normal_value():
    r = _vd(2653)
    assert r and r[0].numeric_value == 46.2


def test_collapsed_moving_time_rejected():
    assert _vd(301) == []        # 10km 5분 → VDOT 수백
