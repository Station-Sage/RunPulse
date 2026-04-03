"""BaseExtractor와 MetricRecord 단위 테스트."""

import json
import pytest
from src.sync.extractors.base import BaseExtractor, MetricRecord


class DummyExtractor(BaseExtractor):
    SOURCE = "test"

    def extract_activity_core(self, raw):
        return {"source": self.SOURCE, "source_id": "1", "activity_type": "running", "start_time": "2025-01-01"}

    def extract_activity_metrics(self, summary_raw, detail_raw=None):
        return []


class TestMetricRecord:
    def test_is_empty_all_none(self):
        mr = MetricRecord(metric_name="x", category="y")
        assert mr.is_empty()

    def test_is_not_empty_numeric(self):
        mr = MetricRecord(metric_name="x", category="y", numeric_value=1.0)
        assert not mr.is_empty()

    def test_is_not_empty_text(self):
        mr = MetricRecord(metric_name="x", category="y", text_value="hello")
        assert not mr.is_empty()

    def test_is_not_empty_json(self):
        mr = MetricRecord(metric_name="x", category="y", json_value='{"a":1}')
        assert not mr.is_empty()


class TestBaseExtractorHelpers:
    def setup_method(self):
        self.ext = DummyExtractor()

    def test_metric_returns_none_when_all_none(self):
        assert self.ext._metric("test_metric") is None

    def test_metric_returns_record_with_value(self):
        r = self.ext._metric("test_metric", 42.0, category="test")
        assert r is not None
        assert r.metric_name == "test_metric"
        assert r.numeric_value == 42.0
        assert r.category == "test"

    def test_metric_with_text(self):
        r = self.ext._metric("test_metric", text="hello", category="test")
        assert r is not None
        assert r.text_value == "hello"
        assert r.numeric_value is None

    def test_metric_with_json(self):
        r = self.ext._metric("test_metric", json_val={"a": 1}, category="test")
        assert r is not None
        assert r.json_value == '{"a": 1}'

    def test_collect_filters_none(self):
        r1 = self.ext._metric("m1", 1.0, category="c")
        r2 = self.ext._metric("m2")  # None
        r3 = self.ext._metric("m3", 3.0, category="c")
        result = self.ext._collect(r1, r2, r3)
        assert len(result) == 2
        assert result[0].metric_name == "m1"
        assert result[1].metric_name == "m3"

    def test_default_methods_return_empty(self):
        assert self.ext.extract_activity_laps({}) == []
        assert self.ext.extract_activity_streams({}) == []
        assert self.ext.extract_best_efforts({}) == []
        assert self.ext.extract_wellness_core("2025-01-01") == {}
        assert self.ext.extract_wellness_metrics("2025-01-01") == []
        assert self.ext.extract_fitness("2025-01-01", {}) == {}
