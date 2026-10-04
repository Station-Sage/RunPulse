"""MetricDef — 메트릭/컬럼 정의 dataclass (metric_registry·metric_defs_* 공용, 순환 import 방지)."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class MetricDef:
    """메트릭/컬럼 정의.

    storage 값:
        "activity_summary" — activity_summaries 테이블 컬럼 (Layer 1)
        "wellness"         — daily_wellness 테이블 컬럼 (Layer 1)
        "metric"           — metric_store 테이블 행 (Layer 2)
    """
    name: str                                 # 정규 이름 (canonical)
    category: str                             # 도메인 카테고리
    storage: str = "metric"                   # 저장 위치
    unit: str = ""                            # 표시 단위
    description: str = ""                     # 한국어 설명
    scope: str = "activity"                   # 'activity' | 'daily' | 'weekly' | 'athlete'
    aliases: dict[str, str] = field(default_factory=dict)
    # aliases = {"garmin": "rawFieldName", "strava": "raw_name", ...}

