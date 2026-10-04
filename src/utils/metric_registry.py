"""RunPulse 메트릭 레지스트리 v0.3.1

모든 메트릭과 Layer 1 컬럼의 정규 이름, 카테고리, 저장 위치, 단위, 소스별 별칭을 정의합니다.
이 파일이 데이터 정의의 Single Source of Truth(SSOT)입니다.

사용법:
    from src.utils.metric_registry import canonicalize, get_metric, METRIC_REGISTRY

    name, category = canonicalize("aerobicTrainingEffect", source="garmin")
    metric = get_metric("trimp")
"""

from __future__ import annotations

from typing import Optional

from src.utils.metric_def import MetricDef  # noqa: F401  재노출
from src.utils.metric_defs_layer1 import LAYER1_DEFS
from src.utils.metric_defs_load import LOAD_DEFS
from src.utils.metric_defs_misc import MISC_DEFS


# ─────────────────────────────────────────────────────────────────────────────
# 카테고리 정의 (16 도메인)
# ─────────────────────────────────────────────────────────────────────────────

METRIC_CATEGORIES: dict[str, str] = {
    "hr":               "심박",
    "power":            "파워",
    "pace":             "페이스",
    "running_dynamics":  "러닝 다이내믹스",
    "volume":           "운동량",
    "load":             "부하",
    "efficiency":       "효율성",
    "capacity":         "체력/역량",
    "prediction":       "예측",
    "sleep":            "수면",
    "stress":           "스트레스",
    "readiness":        "준비도",
    "weather":          "날씨/환경",
    "body":             "신체",
    "meta":             "메타/분류",
    "athlete":          "선수 설정",
    "_unmapped":        "미매핑 (개발용)",
}



_DEFINITIONS: list[MetricDef] = [*LAYER1_DEFS, *LOAD_DEFS, *MISC_DEFS]



# ─────────────────────────────────────────────────────────────────────────────
# 인덱스 빌드 (모듈 로드 시 1회)
# ─────────────────────────────────────────────────────────────────────────────

METRIC_REGISTRY: dict[str, MetricDef] = {}
_ALIAS_MAP: dict[str, str] = {}  # "source::rawName" → canonical_name

for _md in _DEFINITIONS:
    METRIC_REGISTRY[_md.name] = _md
    for _src, _raw in _md.aliases.items():
        _ALIAS_MAP[f"{_src}::{_raw}"] = _md.name


# ─────────────────────────────────────────────────────────────────────────────
# 공개 API
# ─────────────────────────────────────────────────────────────────────────────

def canonicalize(raw_name: str, source: str | None = None) -> tuple[str, str]:
    """소스 raw 필드명 → (정규 이름, 카테고리).

    1) source가 있으면 alias map 먼저 조회
    2) raw_name이 정규 이름이면 직접 반환
    3) 못 찾으면 source가 있으면 "{source}__{raw_name}", 없으면 raw_name 그대로 반환
    """
    if source:
        key = f"{source}::{raw_name}"
        if key in _ALIAS_MAP:
            canonical = _ALIAS_MAP[key]
            return canonical, METRIC_REGISTRY[canonical].category
    if raw_name in METRIC_REGISTRY:
        return raw_name, METRIC_REGISTRY[raw_name].category
    unmapped_name = f"{source}__{raw_name}" if source else raw_name
    return unmapped_name, "_unmapped"


def get_metric(name: str) -> Optional[MetricDef]:
    """정규 이름으로 MetricDef 조회."""
    return METRIC_REGISTRY.get(name)


def list_by_category(category: str) -> list[MetricDef]:
    """카테고리에 속하는 모든 MetricDef 반환."""
    return [md for md in METRIC_REGISTRY.values() if md.category == category]


def list_by_scope(scope: str) -> list[MetricDef]:
    """스코프에 속하는 모든 MetricDef 반환."""
    return [md for md in METRIC_REGISTRY.values() if md.scope == scope]


def list_by_storage(storage: str) -> list[MetricDef]:
    """저장 위치별 모든 MetricDef 반환."""
    return [md for md in METRIC_REGISTRY.values() if md.storage == storage]


# 하위 호환 alias
get_by_category = list_by_category
get_by_scope = list_by_scope
get_by_storage = list_by_storage
