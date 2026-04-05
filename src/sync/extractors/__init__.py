"""RunPulse v0.3 Extractor 모듈.

각 소스(Garmin, Strava, Intervals, Runalyze)의 raw JSON을
DB에 독립적인 dict/list로 변환하는 순수 함수 모듈입니다.

설계 문서: v0.3/data/phase-2.md
의존: src/utils/metric_registry.py
주의: 순수 함수 — DB/API 접근 금지.
      거리는 meters, 시간은 seconds (SI).
      activity_summaries에 있는 값은 metric_store에 중복 저장 금지.
"""

from src.sync.extractors.base import BaseExtractor, MetricRecord
from src.sync.extractors.garmin_extractor import GarminExtractor
from src.sync.extractors.strava_extractor import StravaExtractor
from src.sync.extractors.intervals_extractor import IntervalsExtractor
from src.sync.extractors.runalyze_extractor import RunalyzeExtractor

EXTRACTORS: dict[str, type[BaseExtractor]] = {
    "garmin": GarminExtractor,
    "strava": StravaExtractor,
    "intervals": IntervalsExtractor,
    "runalyze": RunalyzeExtractor,
}


def get_extractor(source: str) -> BaseExtractor:
    """소스 이름으로 Extractor 인스턴스 반환.

    Args:
        source: 'garmin' | 'strava' | 'intervals' | 'runalyze'

    Returns:
        해당 소스의 Extractor 인스턴스.

    Raises:
        KeyError: 등록되지 않은 소스.
    """
    key = source.lower().strip()
    if key not in EXTRACTORS:
        raise KeyError(
            f"Unknown source '{source}'. "
            f"Available: {', '.join(EXTRACTORS.keys())}"
        )
    return EXTRACTORS[key]()


__all__ = [
    "BaseExtractor",
    "MetricRecord",
    "GarminExtractor",
    "StravaExtractor",
    "IntervalsExtractor",
    "RunalyzeExtractor",
    "EXTRACTORS",
    "get_extractor",
]
