"""Extractor 공통 인터페이스 및 MetricRecord 데이터 구조.

모든 소스 extractor는 BaseExtractor를 상속하고,
extract_activity_core / extract_activity_metrics를 구현합니다.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class MetricRecord:
    """metric_store에 들어갈 한 행의 데이터."""

    metric_name: str
    category: str
    numeric_value: Optional[float] = None
    text_value: Optional[str] = None
    json_value: Optional[str] = None       # JSON 문자열
    raw_name: Optional[str] = None
    algorithm_version: str = "1.0"
    confidence: Optional[float] = None
    parent_metric_id: Optional[int] = None

    def is_empty(self) -> bool:
        return (
            self.numeric_value is None
            and self.text_value is None
            and self.json_value is None
        )


class BaseExtractor(ABC):
    """모든 소스 extractor의 기본 클래스."""

    SOURCE: str = ""

    # ── Activity ──

    @abstractmethod
    def extract_activity_core(self, raw: dict) -> dict:
        """raw API JSON → activity_summaries INSERT용 dict.

        반환 dict의 key는 activity_summaries 컬럼명과 정확히 일치해야 함.
        반드시 포함: source, source_id, activity_type, start_time.
        """
        ...

    @abstractmethod
    def extract_activity_metrics(
        self, summary_raw: dict, detail_raw: dict | None = None
    ) -> list[MetricRecord]:
        """raw API JSON → metric_store INSERT용 MetricRecord 리스트.

        activity_summaries에 이미 들어간 값은 여기에 넣지 않음 (이중 저장 금지).
        """
        ...

    def extract_activity_laps(self, detail_raw: dict) -> list[dict]:
        """→ activity_laps INSERT용 dict 리스트. 기본: 빈 리스트."""
        return []

    def extract_activity_streams(self, streams_raw: dict | list) -> list[dict]:
        """→ activity_streams INSERT용 dict 리스트. 기본: 빈 리스트."""
        return []

    def extract_best_efforts(self, raw: dict) -> list[dict]:
        """→ activity_best_efforts INSERT용 dict 리스트. 기본: 빈 리스트."""
        return []

    # ── Wellness (Daily) ──

    def extract_wellness_core(self, date: str, **raw_payloads) -> dict:
        """→ daily_wellness INSERT/MERGE용 dict. 기본: 빈 dict."""
        return {}

    def extract_wellness_metrics(
        self, date: str, **raw_payloads
    ) -> list[MetricRecord]:
        """→ metric_store INSERT용 (scope_type='daily') MetricRecord 리스트."""
        return []

    # ── Fitness (Daily) ──

    def extract_fitness(self, date: str, raw: dict) -> dict:
        """→ daily_fitness INSERT용 dict. 기본: 빈 dict."""
        return {}

    # ── Helpers ──

    def _metric(
        self,
        name: str,
        value=None,
        *,
        text: str | None = None,
        json_val=None,
        category: str | None = None,
        raw_name: str | None = None,
        version: str = "1.0",
        confidence: float | None = None,
    ) -> MetricRecord | None:
        """MetricRecord 생성 헬퍼. 모든 값이 None이면 None 반환."""
        if value is None and text is None and json_val is None:
            return None

        # category가 명시되지 않으면 registry에서 조회
        if category is None:
            try:
                from src.utils.metric_registry import get_metric
                md = get_metric(name)
                category = md.category if md else "_unmapped"
            except ImportError:
                category = "_unmapped"

        json_str = (
            json.dumps(json_val, ensure_ascii=False)
            if json_val is not None
            else None
        )

        return MetricRecord(
            metric_name=name,
            category=category,
            numeric_value=float(value) if value is not None else None,
            text_value=text,
            json_value=json_str,
            raw_name=raw_name or name,
            algorithm_version=version,
            confidence=confidence,
        )

    def _collect(self, *records: MetricRecord | None) -> list[MetricRecord]:
        """None이 아니고 비어있지 않은 MetricRecord만 수집."""
        return [r for r in records if r is not None and not r.is_empty()]
