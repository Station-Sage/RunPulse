"""metric_labels SSOT 일관성 + 지표가 이름 때문에 사라지지 않음 검증 (ADR-018)."""
import re
from collections import Counter

from src.services.metric_display import display_name
from src.utils.metric_labels import METRIC_LABELS, label_for
from src.utils.metric_registry import METRIC_REGISTRY

_DAILY = {n for n, d in METRIC_REGISTRY.items() if d.scope == "daily"}


def test_keys_subset_of_registry():
    assert set(METRIC_LABELS) <= set(METRIC_REGISTRY)


def test_all_daily_metrics_registered():
    assert sorted(_DAILY - set(METRIC_LABELS)) == []


def test_label_shape():
    for name, lab in METRIC_LABELS.items():
        assert lab.name_ko.strip(), name
        assert "(" not in lab.name_ko and "parent" not in lab.name_ko, name
        if lab.abbr is not None:
            assert re.fullmatch(r"[A-Za-z0-9/]{1,8}", lab.abbr), (name, lab.abbr)


def test_no_duplicate_name_ko_within_category():
    seen = Counter((METRIC_REGISTRY[n].category, lab.name_ko) for n, lab in METRIC_LABELS.items())
    assert [k for k, c in seen.items() if c > 1] == []


def test_core_terms_pinned():
    assert METRIC_LABELS["ctl"][:2] == ("체력", "CTL")
    assert METRIC_LABELS["atl"][:2] == ("피로", "ATL")
    assert METRIC_LABELS["tsb"][:2] == ("폼", "TSB")
    assert METRIC_LABELS["utrs"][:2] == ("훈련 준비도", "UTRS")
    assert METRIC_LABELS["cirs"][:2] == ("부상 위험", "CIRS")


def test_fallback_strips_parent_and_uses_name_last():
    assert label_for("x_unknown", "무언가 (parent: utrs)") == ("무언가", None)
    assert label_for("x_unknown", "") == ("x_unknown", None)


def test_every_registry_metric_has_displayable_name():
    for name, d in METRIC_REGISTRY.items():
        name_ko, _ = display_name(name, d.description)
        assert name_ko and "(parent:" not in name_ko, name
