"""tests/test_provider_diff.py — 소스 비교 항목별 임계·정규화(UX 리뷰 20 F-DATA-03)."""
from src.services.provider_diff import diff, normalize
from src.utils.metric_groups import SEMANTIC_GROUPS


def test_small_elevation_gap_is_not_significant():
    assert diff([5.3, 5.0], "elevation_gain")["significant"] is False   # 7.6%지만 0.3m
    assert diff([135, 496], "elevation_gain")["significant"] is True


def test_temperature_uses_absolute_threshold():
    assert diff([21.0, 22.5], "avg_temperature")["significant"] is False
    assert diff([21.0, 23.5], "avg_temperature")["significant"] is True


def test_duration_one_percent():
    assert diff([3318, 3436], "duration_sec")["significant"] is True


def test_single_leg_cadence_normalized():
    assert normalize("avg_cadence", 87) == 174
    assert normalize("avg_cadence", 173) == 173
    assert normalize("avg_hr", 87) == 87


def test_different_quantities_not_compared():
    assert not SEMANTIC_GROUPS["training_load"].get("comparable")
    assert not SEMANTIC_GROUPS["running_efficiency"].get("comparable")
    members = {m for m, _ in SEMANTIC_GROUPS["vo2max"]["members"]}
    assert "runpulse_vdot" not in members  # VDOT(전력 가정)과 기기 VO2max는 다른 양
