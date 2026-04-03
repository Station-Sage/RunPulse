"""metric_registry.py 단위 테스트 — Phase 1 조건 5, 6"""
import pytest
from src.utils.metric_registry import (
    METRIC_REGISTRY, _ALIAS_MAP, METRIC_CATEGORIES,
    canonicalize, get_metric, list_by_category, list_by_scope,
)


class TestMetricDefinitions:
    """조건 5: 120+ 메트릭 정의, alias 충돌 없음"""

    def test_metric_count_minimum(self):
        assert len(METRIC_REGISTRY) >= 120, (
            f"메트릭 {len(METRIC_REGISTRY)}개 — 120개 이상 필요"
        )

    def test_no_alias_collision(self):
        """서로 다른 canonical name이 같은 alias를 공유하면 안 됨"""
        seen = {}
        for alias, canonical in _ALIAS_MAP.items():
            if alias in seen and seen[alias] != canonical:
                pytest.fail(
                    f"alias '{alias}' → '{seen[alias]}' vs '{canonical}' 충돌"
                )
            seen[alias] = canonical

    def test_all_metrics_have_category(self):
        for name, mdef in METRIC_REGISTRY.items():
            assert mdef.category, f"{name} has no category"

    def test_all_metrics_have_unit(self):
        for name, mdef in METRIC_REGISTRY.items():
            assert mdef.unit is not None, f"{name} has no unit"

    def test_categories_non_empty(self):
        assert len(METRIC_CATEGORIES) > 0


class TestCanonicalize:

    def test_canonical_name_returns_itself(self):
        for name in list(METRIC_REGISTRY.keys())[:10]:
            result_name, result_cat = canonicalize(name)
            assert result_name == name

    def test_alias_resolves(self):
        if _ALIAS_MAP:
            key = next(iter(_ALIAS_MAP.keys()))          # "garmin::hrTimeInZone_0"
            expected_canonical = _ALIAS_MAP[key]          # "hr_zone_1_sec"
            source, raw = key.split("::", 1)
            result_name, result_cat = canonicalize(raw, source=source)
            assert result_name == expected_canonical

    def test_unknown_returns_none_or_input(self):
        result_name, result_cat = canonicalize("__nonexistent_metric_xyz__")
        assert result_name == "__nonexistent_metric_xyz__"
        assert result_cat == "_unmapped"

    def test_get_metric_returns_metric_def(self):
        name = next(iter(METRIC_REGISTRY))
        mdef = get_metric(name)
        assert mdef is not None
        assert mdef.name == name                         # canonical_name → name

