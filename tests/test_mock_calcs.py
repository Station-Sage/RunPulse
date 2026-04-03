"""MockCalcContext를 활용한 calculator 단위 테스트 (보강 #5)."""
from tests.helpers.mock_context import MockCalcContext
from src.metrics.trimp import TRIMPCalculator
from src.metrics.hrss import HRSSCalculator
from src.metrics.efficiency import EfficiencyFactorCalculator
from src.metrics.vdot import VDOTCalculator
from src.metrics.base import ConfidenceBuilder


class TestTRIMPMock:
    def test_basic(self):
        ctx = MockCalcContext(
            activity_data={
                "avg_hr": 155, "moving_time_sec": 3600,
                "activity_type": "running", "start_time": "2026-04-01 08:00",
            },
            wellness_data={"resting_hr": 55},
        )
        ctx._mock_activities_range = [{"max_hr": 190}]
        results = TRIMPCalculator().compute(ctx)
        assert len(results) == 1
        assert 80 < results[0].numeric_value < 150

    def test_no_hr(self):
        ctx = MockCalcContext(
            activity_data={"moving_time_sec": 3600, "start_time": "2026-04-01"},
        )
        assert TRIMPCalculator().compute(ctx) == []

    def test_short_duration(self):
        ctx = MockCalcContext(
            activity_data={
                "avg_hr": 155, "moving_time_sec": 60,
                "start_time": "2026-04-01",
            },
            wellness_data={"resting_hr": 55},
        )
        ctx._mock_activities_range = [{"max_hr": 190}]
        results = TRIMPCalculator().compute(ctx)
        assert len(results) == 1
        assert results[0].numeric_value < 10


class TestHRSSMock:
    def test_with_trimp(self):
        ctx = MockCalcContext(
            activity_data={
                "avg_hr": 155, "moving_time_sec": 3600,
                "activity_type": "running", "start_time": "2026-04-01",
            },
            metrics={"trimp": {"numeric": 100.0, "text": None, "json": None}},
            wellness_data={"resting_hr": 55},
        )
        ctx._mock_activities_range = [{"max_hr": 190}]
        results = HRSSCalculator().compute(ctx)
        assert len(results) == 1
        assert results[0].numeric_value > 0

    def test_no_trimp(self):
        ctx = MockCalcContext(activity_data={"start_time": "2026-04-01"})
        assert HRSSCalculator().compute(ctx) == []


class TestEFMock:
    def test_basic(self):
        ctx = MockCalcContext(
            activity_data={"avg_speed_ms": 3.33, "avg_hr": 155},
        )
        results = EfficiencyFactorCalculator().compute(ctx)
        assert len(results) == 1
        assert results[0].numeric_value > 0

    def test_no_hr(self):
        ctx = MockCalcContext(activity_data={"avg_speed_ms": 3.33})
        assert EfficiencyFactorCalculator().compute(ctx) == []


class TestVDOTMock:
    def test_10k(self):
        ctx = MockCalcContext(
            activity_data={
                "activity_type": "running",
                "distance_m": 10000, "moving_time_sec": 2700,
            },
        )
        results = VDOTCalculator().compute(ctx)
        assert len(results) == 1
        assert 30 < results[0].numeric_value < 80

    def test_non_running(self):
        ctx = MockCalcContext(
            activity_data={"activity_type": "cycling", "distance_m": 50000, "moving_time_sec": 7200},
        )
        assert VDOTCalculator().compute(ctx) == []


class TestConfidenceBuilder:
    def test_all_available(self):
        cb = ConfidenceBuilder()
        cb.add_input("a", is_available=True, weight=0.5)
        cb.add_input("b", is_available=True, weight=0.5)
        assert cb.compute() == 1.0

    def test_partial_available(self):
        cb = ConfidenceBuilder()
        cb.add_input("a", is_available=True, weight=0.5)
        cb.add_input("b", is_available=False, weight=0.5)
        assert cb.compute() == 0.5

    def test_estimated_penalty(self):
        cb = ConfidenceBuilder()
        cb.add_input("a", is_available=True, weight=1.0, is_estimated=True)
        assert cb.compute() == 0.7

    def test_empty(self):
        assert ConfidenceBuilder().compute() == 0.0

    def test_mixed(self):
        cb = ConfidenceBuilder()
        cb.add_input("hr", is_available=True, weight=0.4)
        cb.add_input("duration", is_available=True, weight=0.3)
        cb.add_input("max_hr", is_available=True, weight=0.2, is_estimated=True)
        cb.add_input("rest_hr", is_available=False, weight=0.1)
        conf = cb.compute()
        assert 0.5 < conf < 1.0


