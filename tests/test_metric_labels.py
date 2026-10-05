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
    assert label_for("x_unknown", "무언가 (parent: utrs)")[:2] == ("무언가", None)
    assert label_for("x_unknown", "")[:2] == ("x_unknown", None)


def test_every_registry_metric_has_displayable_name():
    for name, d in METRIC_REGISTRY.items():
        name_ko, _ = display_name(name, d.description)
        assert name_ko and "(parent:" not in name_ko, name


_FIRST_BATCH = [
    "race_pred_marathon_sec", "race_pred_half_sec", "race_pred_10k_sec", "race_pred_5k_sec", "ctl", "tsb", "utrs",
    "cirs", "atl", "rri", "acwr", "lsi", "monotony", "training_strain", "rtti", "vo2max", "resting_hr",
    "hrv_last_night", "hrv_weekly_avg", "sleep_score", "sleep_duration_sec", "body_battery_high",
    "body_battery_low", "avg_stress", "training_readiness_score", "crs", "ramp_rate", "marathon_shape",
]


def test_first_batch_has_description_short():
    assert [n for n in _FIRST_BATCH if not METRIC_LABELS[n].description_short] == []


def test_texts_within_40_chars():
    for name, lab in METRIC_LABELS.items():
        for text in [lab.description_short, *(lab.action_hint or {}).values()]:
            if text:
                assert len(text) <= 40, (name, text)


def test_action_hint_keys_are_five_level_status():
    from src.metrics.bands import BANDS

    allowed = {"excellent", "good", "neutral", "caution", "poor"}
    for name, lab in METRIC_LABELS.items():
        if lab.action_hint:
            assert set(lab.action_hint) <= (allowed if name != "crs" else {f"level_{i}" for i in range(5)}), name
            assert name in BANDS, name


def test_action_hint_picks_current_status_only():
    from src.services.metric_display import action_hint

    assert action_hint("utrs", "poor") == "오늘은 쉬거나 아주 가볍게만 움직이세요."
    assert action_hint("utrs", None) is None
    assert action_hint("ctl", "good") is None
    assert action_hint("acwr", "excellent") is None


def test_crs_hint_uses_gate_level_not_score_status():
    from src.services.metric_display import action_hint

    assert action_hint("crs", "excellent", 1) == "이지런만 하세요."
    assert action_hint("crs", "excellent", None) is None
    assert action_hint("crs", "poor", 4).startswith("계획대로")


def test_marathon_shape_label_and_new_texts():
    assert METRIC_LABELS["marathon_shape"].name_ko == "마라톤 볼륨 충족률"
    assert METRIC_LABELS["race_pred_vdot"].description_short
