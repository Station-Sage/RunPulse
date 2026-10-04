"""tests/test_metric_bands.py — 등급 밴드 SSOT(src/metrics/bands.py)."""
import pytest

from src.metrics.bands import BANDS, grade, with_grade


@pytest.mark.parametrize("value, status, label", [
    (-35, "poor", "과부하"), (-20, "good", "생산적 부하"), (0, "neutral", "유지"),
    (10, "excellent", "신선"), (30, "caution", "휴식 과다"),
])
def test_tsb_conventional_bands(value, status, label):
    assert grade("tsb", value) == {"status": status, "label": label}


def test_tsb_race_phase_overrides():
    assert grade("tsb", -20, phase="race") == {"status": "caution", "label": "피로 누적"}
    assert grade("tsb", 10, phase="taper")["label"] == "레이스 최적"


def test_cirs_lower_is_better():
    assert grade("cirs", 20)["status"] == "good"
    assert grade("cirs", 75)["status"] == "poor"


def test_decoupling_uses_absolute_value():
    assert grade("aerobic_decoupling", -12)["status"] == "caution"


def test_unknown_or_missing_returns_none():
    assert grade("ctl", 50) is None
    assert grade("tsb", None) is None
    assert with_grade({"a": 1}, "ctl", 50) == {"a": 1}


def test_utrs_bands_match_calculator_ranges():
    """UTRS 경계가 Calculator ranges와 같다(두 정의 금지)."""
    from src.metrics.utrs import UTRSCalculator
    uppers = [hi for _, (lo, hi) in sorted(UTRSCalculator.ranges.items(), key=lambda kv: kv[1][0])][:-1]
    assert [c[0] for c in BANDS["utrs"][0]] == uppers


@pytest.mark.parametrize("value, status, label", [
    (20, "poor", "부족"), (50, "caution", "준비 중"), (70, "good", "준비됨"), (90, "excellent", "최적"),
])
def test_rri_bands(value, status, label):
    assert grade("rri", value) == {"status": status, "label": label}
