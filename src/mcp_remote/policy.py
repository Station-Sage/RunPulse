"""원격(HTTP) 노출 도구 정책 — 모든 도구는 REMOTE_TOOLS 또는 REMOTE_DENIED 중 하나로 분류돼야 한다."""
from __future__ import annotations

REMOTE_TOOLS: frozenset[str] = frozenset({
    "get_activity", "get_activities_range", "get_activity_detail", "get_activity_laps",
    "compare_workout_sets", "get_training_summary", "get_metrics", "get_metrics_trend",
    "get_wellness", "get_fitness", "get_race_history", "compare_periods",
    "get_training_plan", "get_runner_profile", "get_weather",
})
REMOTE_DENIED: frozenset[str] = frozenset()


def unclassified_tools() -> set[str]:
    """_DISPATCH에 있으나 어느 쪽에도 분류되지 않은 도구 (테스트가 빈 집합을 강제)."""
    from src.ai.tools import _DISPATCH

    return set(_DISPATCH) - REMOTE_TOOLS - REMOTE_DENIED
