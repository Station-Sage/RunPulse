"""AI Function Calling 도구 진입점 — 선언 재노출 + 실행 디스패치.

도구 선언은 tool_declarations.py, 실행기는 tool_exec_activity.py(활동·기간 목록),
tool_exec_laps.py(랩·세트), tool_exec_context.py(일별·기간), tool_exec_summary.py(요약).
응답 압축·롤업 공통 로직은 tool_format.py.
"""
from __future__ import annotations

import json
import logging
import sqlite3

from src.ai.tool_declarations import TOOL_DECLARATIONS  # noqa: F401 (re-export)
from src.ai import tool_exec_activity as _act
from src.ai import tool_exec_laps as _laps
from src.ai import tool_exec_summary as _summary
from src.ai import tool_exec_context as _ctx

log = logging.getLogger(__name__)

_DISPATCH = {
    "get_activity": _act._exec_get_activity,
    "get_activities_range": _act._exec_get_activities_range,
    "get_activity_detail": _act._exec_get_activity_detail,
    "get_activity_laps": _laps._exec_get_activity_laps,
    "compare_workout_sets": _laps._exec_compare_workout_sets,
    "get_training_summary": _summary._exec_get_training_summary,
    "get_metrics": _ctx._exec_get_metrics,
    "get_metrics_trend": _ctx._exec_get_metrics_trend,
    "get_wellness": _ctx._exec_get_wellness,
    "get_fitness": _ctx._exec_get_fitness,
    "get_race_history": _ctx._exec_get_race_history,
    "compare_periods": _ctx._exec_compare_periods,
    "get_training_plan": _ctx._exec_get_training_plan,
    "get_runner_profile": _ctx._exec_get_runner_profile,
    "get_weather": _ctx._exec_get_weather,
}


def execute_tool(conn: sqlite3.Connection, name: str, args: dict) -> str:
    """AI가 호출한 도구를 실행하고 결과를 JSON 문자열로 반환."""
    fn = _DISPATCH.get(name)
    if not fn:
        return json.dumps({"error": f"알 수 없는 도구: {name}"}, ensure_ascii=False)
    try:
        result = fn(conn, args)
        return json.dumps(result, ensure_ascii=False, default=str, separators=(",", ":"))
    except Exception as exc:
        log.warning("도구 실행 실패 (%s): %s", name, exc)
        return json.dumps({"error": str(exc)}, ensure_ascii=False)
