"""P7-PRED-62: 수용 백테스트 스크립트 — 대회 없음이면 n=0."""
import importlib.util
from pathlib import Path

from tests.helpers_pred import mem_conn, seed_run

_spec = importlib.util.spec_from_file_location("pred_backtest", Path(__file__).parent.parent / "scripts" / "pred_backtest.py")
pb = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pb)


def test_no_races():
    c = mem_conn()
    seed_run(c, sid="a", date="2026-09-01", max_hr=190)
    seed_run(c, sid="b", date="2026-09-02", max_hr=192)
    r = pb.backtest(c, "2026-01-01", "2026-09-26")
    assert r["D-0"] == {"n": 0, "mae": None, "max": None, "errors": [], "bias": None}
    allr = pb.backtest_all(c, "2026-01-01", "2026-09-26")
    assert set(allr) == {"r3", "r4", "r4_asym"} and all(v["D-28"]["n"] == 0 for v in allr.values())
