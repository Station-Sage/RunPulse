from src.training import plan_backtest as B


def _grid(**kw):
    return next(s for s in B.grid_scenarios() if all(getattr(s, k) == v for k, v in kw.items()))


def test_rest_mask_leaves_requested_days():
    assert bin(~B.rest_mask(4) & 0x7F).count("1") == 4


def test_grid_size():
    assert len(B.grid_scenarios()) == 5 * 3 * 4 * 4 * 2


def test_v1_full_plan_fails_marathon_gates():
    r = B.run_scenario(_grid(distance="full", plan_weeks=12, days=5, start_km=55, long_start=18), None)
    assert r["gates"]["G4"]["violations"] > 0      # v1 은 MP 세션이 없다(하네스 자체 검증)
    assert len(r["weeks"]) == 12 and not r["pass"]


def test_deterministic():
    s = _grid(distance="half", plan_weeks=8, days=4, start_km=40, long_start=10)
    assert B.run_scenario(s, None)["gates"]["G8"]["violations"] == 0


def test_summarize_counts():
    out = B.summarize([{"gates": {"G1": {"violations": 2, "worst": "x"}}, "pass": False},
                       {"gates": {"G1": {"violations": 0, "worst": ""}}, "pass": True}])
    assert out["total"] == 2 and out["passed"] == 1 and out["gates"]["G1"]["scenarios_failed"] == 1
