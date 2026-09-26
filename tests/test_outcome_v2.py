"""P7-PRED-42: 계획↔실행 세그먼트 비교."""
from src.training.outcome_v2 import compare, expand_work, prediction_note

PLAN = {"steps": [{"type": "warmup", "dur_s": 600},
                  {"type": "repeat", "count": 6, "steps": [
                      {"type": "work", "dist_m": 1000, "speed_lo": 3.9, "speed_hi": 4.1},
                      {"type": "rest", "dur_s": 90}]},
                  {"type": "cooldown", "dur_s": 600}]}


def _b(d=1000.0, v=4.0, hr=172):
    return {"dist_m": d, "dur_s": d / v, "speed_ms": v, "hr": hr}


def test_expand():
    assert len(expand_work(PLAN["steps"])) == 6


def test_full_on_target():
    r = compare(PLAN, [_b()] * 6)
    assert (r["sets_done"], r["compliance_pct"], r["label"]) == (6, 100.0, "on_target")


def test_five_of_six_sets():                       # 실제 사례: 6회 계획 → 5회 실행
    r = compare(PLAN, [_b()] * 5)
    assert r["compliance_pct"] == round(100 * (0.4 * 5 / 6 + 0.3 + 0.3), 1) == 93.3
    assert r["label"] == "on_target"


def test_slow_and_short():
    r = compare(PLAN, [_b(d=800, v=3.6)] * 4)
    assert r["target_hit_pct"] == 0.0 and r["label"] == "underperformed"
    assert r["compliance_pct"] == round(100 * (0.4 * 4 / 6 + 0.3 * 0.8 + 0), 1)


def test_fast():
    assert compare(PLAN, [_b(v=4.4)] * 6)["label"] == "overperformed"


def test_skipped_and_note():
    assert compare(PLAN, [])["label"] == "skipped"
    outs = [{"compliance_pct": 60, "sets_planned": 6}] * 4
    assert prediction_note(outs) == {"n": 4, "avg_compliance_pct": 60.0, "slow_extra_pct": 1.0,
                                     "reason": "최근 4주 품질 세션 이행률 60%"}
    assert prediction_note(outs[:3]) is None
