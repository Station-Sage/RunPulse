"""tests/test_metric_browse_groups.py — 메트릭 브라우저 8의도 그룹 매핑·정렬 단위 테스트."""
from __future__ import annotations

from src.utils.metric_registry import METRIC_REGISTRY
from src.services.metric_browse_groups import GROUPS, SLUG_GROUP, baseline_z, classify, salience_key


def _daily() -> set[str]:
    return {n for n, m in METRIC_REGISTRY.items() if m.scope == "daily"}


def test_every_daily_slug_is_mapped():
    assert _daily() - set(SLUG_GROUP) == set()


def test_no_mapping_key_outside_daily():
    assert set(SLUG_GROUP) - _daily() == set()


def test_groups_are_known():
    keys = {k for k, _ in GROUPS}
    assert {g for g, _ in SLUG_GROUP.values()} <= keys


def test_unknown_slug_goes_to_other_detail():
    assert classify("no_such_metric") == ("other", "detail")


def _rows(vals, start=1):
    return [(f"2026-04-{start + i:02d}", v) for i, v in enumerate(vals)]


def test_baseline_z_null_under_7_days():
    assert baseline_z(_rows([1, 2, 3, 4, 5, 9]), "2026-04-06", 0.1) is None


def test_baseline_z_null_when_not_fresh():
    assert baseline_z(_rows([1] * 8), "2026-04-20", 0.1) is None


def test_baseline_z_sd_zero_uses_floor():
    z = baseline_z(_rows([10] * 7 + [11]), "2026-04-08", 0.5)
    assert z == 2.0


def _e(fresh=True, status="good", z=None, tier="primary"):
    return {"salience": {"fresh": fresh, "z": z}, "status": status, "tier": tier}


def test_fresh_before_stale():
    assert salience_key(_e(True), 5) < salience_key(_e(False, "poor", 9.0), 0)


def test_caution_before_big_z_neutral():
    assert salience_key(_e(status="caution", z=0.1), 5) < salience_key(_e(status="good", z=3.0), 0)


def test_z_null_goes_last_among_same_status():
    assert salience_key(_e(z=0.1), 9) < salience_key(_e(z=None), 0)


def test_tie_then_tier_then_registry():
    assert salience_key(_e(z=1.01, tier="detail"), 0) > salience_key(_e(z=1.04), 9)
    assert salience_key(_e(z=1.0), 1) < salience_key(_e(z=1.0), 2)
