"""훈련 방식 레지스트리 — 목표 거리별 선택 가능한 훈련 철학(ADR-060, DESIGN-PLAN-METHODS).

`PlanMethod`(frozen) 를 `registry.METHODS` 에 등록한다. `balanced` 는 현행 규칙 그대로(회귀 기준)이며,
방식은 `plan_rules_version`(규칙 세대)과 직교하는 축이다. 방식 변경은 재계획 경로로만(anchor 이후 주에만 적용).
"""
from .registry import (DEFAULT_METHOD, METHODS, PlanMethod, candidates_for, effective_method, get_method,
                       goal_method)

__all__ = ["DEFAULT_METHOD", "METHODS", "PlanMethod", "candidates_for", "effective_method", "get_method",
           "goal_method"]
