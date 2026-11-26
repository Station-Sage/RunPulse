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


def test_tsb_band_ranges_expose_race_optimal_window():
    """formChart 레이스 최적 음영 [5,25] 는 프론트 상수가 아니라 tsb 밴드(신선 구간)에서 와야 한다."""
    from src.metrics.bands import band_ranges

    fresh = [r for r in band_ranges("tsb") if r["status"] == "excellent"]
    assert [(r["from"], r["to"]) for r in fresh] == [(5, 25)]


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


@pytest.mark.parametrize("name,value,status", [
    ("sleep_score", 55, "poor"), ("sleep_score", 85, "good"), ("sleep_score", 95, "excellent"),
    ("training_readiness_score", 20, "poor"), ("training_readiness_score", 80, "good"),
    ("body_battery_high", 20, "poor"), ("body_battery_high", 90, "good"),
    ("avg_stress", 20, "excellent"), ("avg_stress", 80, "poor"),
    ("sleep_duration_sec", 5 * 3600, "poor"), ("sleep_duration_sec", 8 * 3600, "good"),
    ("monotony", 1.0, "good"), ("monotony", 2.5, "caution"),
    ("rtti", 85, "good"), ("rtti", 140, "poor"),
    ("lsi", 1.0, "good"), ("lsi", 1.6, "poor"),
    ("marathon_shape", 50, "caution"), ("marathon_shape", 120, "excellent"),
])
def test_c1_new_bands(name, value, status):
    assert grade(name, value)["status"] == status


def test_c1_hints_exist_for_new_bands():
    from src.services.metric_display import action_hint
    for name in ("sleep_score", "avg_stress", "rtti", "lsi", "monotony", "marathon_shape"):
        status = grade(name, 1.0 if name in ("lsi", "monotony") else 50)["status"]
        assert action_hint(name, status), (name, status)
