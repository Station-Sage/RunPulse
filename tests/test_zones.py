"""zones 유틸리티 테스트."""

from src.utils.zones import hr_zones, get_hr_zone, pace_zones, get_pace_zone


class TestHrZones:
    def test_returns_5_zones(self):
        zones = hr_zones(200)
        assert len(zones) == 5

    def test_zone_boundaries(self):
        zones = hr_zones(200)
        assert zones[0] == (100, 120)  # Zone 1: 50-60%
        assert zones[4] == (180, 200)  # Zone 5: 90-100%

    def test_zones_ascending(self):
        zones = hr_zones(190)
        for i in range(4):
            assert zones[i][1] <= zones[i + 1][1]


class TestGetHrZone:
    def test_zone1(self):
        assert get_hr_zone(110, 200) == 1

    def test_zone3(self):
        assert get_hr_zone(150, 200) == 3

    def test_zone5(self):
        assert get_hr_zone(195, 200) == 5

    def test_zero_hr(self):
        assert get_hr_zone(0, 200) == 0

    def test_above_max(self):
        assert get_hr_zone(210, 200) == 5


class TestPaceZones:
    def test_returns_5_zones(self):
        zones = pace_zones(300)
        assert len(zones) == 5

    def test_zone1_slowest(self):
        """Zone 1이 가장 느린 (큰 수치) 페이스."""
        zones = pace_zones(300)
        assert zones[0][1] > zones[4][1]


class TestGetPaceZone:
    def test_easy_pace(self):
        # 300 * 1.30 = 390 → Zone 1
        assert get_pace_zone(390, 300) == 1

    def test_threshold_pace(self):
        # 300 * 0.98 = 294 → Zone 4
        assert get_pace_zone(294, 300) == 4

    def test_vo2max_pace(self):
        # 300 * 0.90 = 270 → Zone 5
        assert get_pace_zone(270, 300) == 5

    def test_zero_pace(self):
        assert get_pace_zone(0, 300) == 0
