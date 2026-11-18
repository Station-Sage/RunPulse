"""원격(HTTP) 노출 도구 정책 — 모든 도구는 REMOTE_TOOLS·REMOTE_DENIED·LOCAL_ONLY_TOOLS 중 하나로 분류돼야 한다."""
from __future__ import annotations

REMOTE_TOOLS: frozenset[str] = frozenset({
    "get_activity", "get_activities_range", "get_activity_detail", "get_activity_laps",
    "compare_workout_sets", "get_training_summary", "get_metrics", "get_metrics_trend",
    "get_wellness", "get_fitness", "get_race_history", "compare_periods",
    "get_training_plan", "get_plan_adherence", "get_runner_profile", "get_weather",
    "get_wellness_series", "get_insights", "get_checkins", "get_predictions",
})
REMOTE_DENIED: frozenset[str] = frozenset()
# 로컬 stdio(MCP)·워커 전용 — 원본 payload 는 원격에 노출하지 않는다.
LOCAL_ONLY_TOOLS: frozenset[str] = frozenset({"list_raw_payloads", "get_raw_payload", "get_activity_stream"})


def unclassified_tools() -> set[str]:
    """_DISPATCH에 있으나 어느 쪽에도 분류되지 않은 도구 (테스트가 빈 집합을 강제)."""
    from src.ai.tools import _DISPATCH

    return set(_DISPATCH) - REMOTE_TOOLS - REMOTE_DENIED - LOCAL_ONLY_TOOLS
