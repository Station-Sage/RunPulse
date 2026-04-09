"""하위호환 re-export 심 — 직접 import는 각 모듈을 사용할 것.

- 멀티소스 뷰 로직: src.services.unified_view
- 소스 상수:        src.services.activity_service
- 그룹 관리:        src.utils.dedup
"""
from src.services.unified_view import (  # noqa: F401
    _COLS,
    UnifiedField,
    UnifiedActivity,
    _pick_value,
    build_unified_activity,
    fetch_unified_activities,
    build_source_comparison,
)
from src.services.activity_service import SERVICE_PRIORITY, SOURCE_COLORS  # noqa: F401
from src.utils.dedup import assign_group_to_activities, remove_from_group  # noqa: F401
