"""재계획 백테스트(E7) — v1 계획 중간 anchor 에서 v2 로 전환한 꼬리가 하드 게이트를 통과한다."""
from src.training import plan_backtest as B
from src.training import plan_backtest_replan as RP


def test_replan_grid_skips_cold_and_short_tails():
    g = RP.replan_grid()
    assert g and all(s.start_km > 0 and s.plan_weeks - k >= RP.MIN_TAIL_WEEKS for s, k in g)


def test_replan_tail_passes_hard_gates_sample():
    items = [(s, k) for s, k in RP.replan_grid() if s.distance == "full" and s.days == 4][:6]
    for s, k in items:
        r = RP.run_replan_scenario(B.Scenario(**{**s.__dict__, "aux": {}}), k)
        assert r["pass"], (s.start_km, s.plan_weeks, k, {g: v["worst"] for g, v in r["gates"].items() if v["violations"]})
