"""metric_display.action_hint — CRS 힌트의 신선도·BOOST hold 처리 (FRS F3)."""
from src.services.metric_display import action_hint


def test_crs_hint_by_level():
    assert action_hint("crs", "x", level=4) == action_hint("crs", "x", level=4, assertive=True)
    assert action_hint("crs", "x", level=4) is not None


def test_crs_hint_omitted_when_not_assertive_or_no_level():
    assert action_hint("crs", "x", level=4, assertive=False) is None
    assert action_hint("crs", "x", level=None) is None


def test_crs_boost_hold_caps_level():
    assert action_hint("crs", "x", level=4, boost_hold=True) == action_hint("crs", "x", level=3)
    assert action_hint("crs", "x", level=2, boost_hold=True) == action_hint("crs", "x", level=2)


def test_non_crs_hint_by_status_only():
    assert action_hint("utrs", None) is None
