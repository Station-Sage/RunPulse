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


def test_history_scenarios_from_seeded_db():
    from tests.helpers_pred import mem_conn, seed_run
    c = mem_conn()
    for i in range(30):
        seed_run(c, sid=f"a{i}", date=f"2025-0{1 + i // 10}-{1 + (i % 10) * 2:02d}", name="easy", dist=8000.0)
    seed_run(c, sid="race", date="2025-06-01", name="서울 하프 레이스", dist=21100.0, moving=6000)
    c.commit()
    scns = B.history_scenarios(c)
    assert scns and all(s.kind == "history" and s.distance == "half" for s in scns)
    r = B.run_scenario(scns[0], c)
    assert r["inputs"]["start_km"] >= 0 and len(r["weeks"]) == scns[0].plan_weeks


def _v1_signature(scn):
    from tests.helpers_pred import mem_conn
    c = mem_conn()
    B.seed_grid_history(c, scn)
    c.commit()
    weeks, _ = B.engine_v1(scn, c)
    return [[(s.type, round(s.km, 1)) for s in w.days] for w in weeks]


def test_v1_output_snapshot_protects_existing_goals(monkeypatch):
    monkeypatch.delenv("PLAN_RULES_V2_ENABLED", raising=False)
    s = _grid(distance="half", plan_weeks=8, days=4, start_km=40, long_start=10)
    sig = _v1_signature(s)
    assert len(sig) == 8 and _v1_signature(s) == sig
    import hashlib
    assert hashlib.sha1(repr(sig).encode()).hexdigest() == "d73255c6edb611413469b3cb0d881485e32b8481"


def test_seed_grid_history_matches_start_load():
    from datetime import timedelta
    from src.training.planner_schedule import recent_load
    from tests.helpers_pred import mem_conn
    s = _grid(distance="half", plan_weeks=8, days=4, start_km=40, long_start=10)
    c = mem_conn()
    B.seed_grid_history(c, s)
    c.commit()
    km4, long6 = recent_load(c, s.start_monday)
    assert abs(km4 - 40) < 2 and long6 >= 10 - 0.1


def test_engine_v2_grid_passes_gates():
    s = _grid(distance="full", plan_weeks=12, days=4, start_km=40, long_start=18)
    r = B.run_scenario(s, None, engine=B.engine_v2)
    assert r["pass"] and len(r["weeks"]) == 12
