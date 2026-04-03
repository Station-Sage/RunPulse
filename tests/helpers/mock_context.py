"""DB 없이 calculator를 테스트하기 위한 MockCalcContext (보강 #5)."""
from __future__ import annotations
from typing import Optional
from src.metrics.base import CalcContext


class MockCalcContext(CalcContext):
    """DB 연결 없이 calculator 단위 테스트를 지원하는 mock context."""

    def __init__(self, scope_type="activity", scope_id="1",
                 activity_data=None, metrics=None, wellness_data=None,
                 streams=None):
        super().__init__(conn=None, scope_type=scope_type, scope_id=scope_id)
        self._activity_cache = activity_data or {}
        self._metric_cache = self._build_metric_cache(metrics or {})
        self._stream_cache = streams or []
        self._wellness_data = wellness_data or {}
        # 확장용
        self._mock_activities_range = []
        self._mock_daily_series = {}
        self._mock_activity_metrics = {}

    def _build_metric_cache(self, metrics: dict) -> dict:
        """{'trimp': 85.0} → {('trimp', None): ..., ('trimp', provider): ...}"""
        cache = {}
        for name, value in metrics.items():
            if isinstance(value, dict):
                entry = value
            else:
                entry = {"numeric": value, "text": None, "json": None}
            cache[(name, None)] = entry
            # provider 지정 조회도 지원 (주요 RunPulse provider들)
            for prov in ("runpulse:formula_v1", "runpulse:rule_v1"):
                cache[(name, prov)] = entry
        return cache

    @property
    def activity(self) -> dict:
        return self._activity_cache

    def get_metric(self, metric_name: str, provider: str = None,
                   scope_type: str = None, scope_id: str = None) -> Optional[float]:
        key = (metric_name, provider) if provider else (metric_name, None)
        entry = self._metric_cache.get(key)
        if entry:
            return entry.get("numeric") if isinstance(entry, dict) else entry
        return None

    def get_metric_json(self, metric_name: str, provider: str = None) -> Optional[str]:
        key = (metric_name, provider) if provider else (metric_name, None)
        entry = self._metric_cache.get(key)
        if entry and isinstance(entry, dict):
            return entry.get("json")
        return None

    def get_metric_text(self, metric_name: str) -> Optional[str]:
        entry = self._metric_cache.get((metric_name, None))
        if entry and isinstance(entry, dict):
            return entry.get("text")
        return None

    def get_wellness(self, date: str = None) -> dict:
        return self._wellness_data

    def get_streams(self, activity_id: int = None) -> list[dict]:
        return self._stream_cache

    def get_activities_in_range(self, days: int, activity_type: str = None) -> list[dict]:
        return self._mock_activities_range

    def get_daily_metric_series(self, metric_name: str, days: int,
                                provider: str = None) -> list[tuple[str, float]]:
        return self._mock_daily_series.get(metric_name, [])

    def get_activity_metric(self, activity_id: int, metric_name: str) -> Optional[float]:
        return self._mock_activity_metrics.get((activity_id, metric_name))

    def get_daily_load(self, date_str: str) -> float:
        return self._mock_daily_series.get("_daily_load", {}).get(date_str, 0)

    def get_laps(self, activity_id: int = None) -> list[dict]:
        return []
