"""daniels_table 유틸리티 테스트."""
import pytest
from src.utils.daniels_table import (
    get_training_paces, get_race_predictions,
    get_marathon_volume_targets, get_race_volume_targets,
    vdot_to_t_pace, t_pace_to_vdot,
    VDOT_PACE_TABLE,
)


class TestTrainingPaces:
    def test_vdot_50_paces(self):
        p = get_training_paces(50)
        assert p["E"] == 303
        assert p["M"] == 259
        assert p["T"] == 239
        assert p["I"] == 222
        assert p["R_400m"] == 50

    def test_interpolation(self):
        """중간 VDOT에서 보간 작동"""
        p = get_training_paces(47.5)
        assert p["E"] > 0
        # 47과 48 사이
        assert get_training_paces(47)["E"] >= p["E"] >= get_training_paces(48)["E"]

    def test_boundary_low(self):
        p = get_training_paces(20)  # 테이블 최소 30 미만
        assert "E" in p  # 최소값 반환

    def test_boundary_high(self):
        p = get_training_paces(90)  # 테이블 최대 85 초과
        assert "E" in p


class TestRacePredictions:
    def test_vdot_50_predictions(self):
        r = get_race_predictions(50)
        assert "5k" in r and "10k" in r and "half" in r and "full" in r
        assert r["5k"] < r["10k"] < r["half"] < r["full"]

    def test_sub3_marathon(self):
        """VDOT 55 → 풀마라톤 약 3:30 이내"""
        r = get_race_predictions(55)
        assert r["full"] < 4 * 3600  # 4시간 미만


class TestVolume:
    def test_marathon_volume(self):
        v = get_marathon_volume_targets(50)
        assert v["weekly_min"] > 0
        assert v["weekly_max"] > v["weekly_min"]
        assert "weekly_target" in v

    def test_race_volume_half(self):
        v = get_race_volume_targets(50, 21.1)
        assert v["weekly_target"] < get_marathon_volume_targets(50)["weekly_target"]

    def test_race_volume_10k(self):
        v = get_race_volume_targets(50, 10)
        assert v["weekly_target"] < get_race_volume_targets(50, 21.1)["weekly_target"]


class TestTpaceConversion:
    def test_vdot_to_t_pace(self):
        t = vdot_to_t_pace(50)
        assert t == 239

    def test_t_pace_to_vdot_roundtrip(self):
        """VDOT → T-pace → VDOT 왕복"""
        t = vdot_to_t_pace(50)
        v = t_pace_to_vdot(t)
        assert abs(v - 50) < 1.0

    def test_t_pace_to_vdot_interpolated(self):
        v = t_pace_to_vdot(250)  # 테이블 사이값
        assert v is not None
        assert 40 < v < 55
