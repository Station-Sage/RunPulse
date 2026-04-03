"""RunPulse v0.3 Extractor 모듈.

각 소스(Garmin, Strava, Intervals, Runalyze)의 raw JSON을
DB에 독립적인 dict/list로 변환하는 순수 함수 모듈입니다.
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

__all__ = [
    "BaseExtractor",
    "MetricRecord",
    "GarminExtractor",
    "StravaExtractor",
    "IntervalsExtractor",
    "RunalyzeExtractor",
    "EXTRACTORS",
]
