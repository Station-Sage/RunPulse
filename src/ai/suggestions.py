"""추천 칩 레지스트리 — 칩 id → 라벨·프롬프트 템플릿 이름.

규칙 기반 칩 선택(get_runner_state·rule_based_chips)은 v2 suggestion_chips·
coach_rule_handlers.answerable_chips 로 대체되어 제거했다(V1S-4). 레지스트리만 남는다.
"""
from __future__ import annotations

# 칩 레지스트리: id → {label, template}
# template은 briefing.py가 prompt_templates/<template>.txt를 로드하는 데 사용
CHIP_REGISTRY: dict[str, dict] = {
    "today_deep":      {"label": "오늘 훈련 상세 분석",          "template": "deep_analysis"},
    "weekly_review":   {"label": "이번 주 훈련 리뷰",            "template": "weekly_review"},
    "weekly_plan":     {"label": "다음 주 훈련 계획 만들어줘",   "template": "weekly_plan"},
    "recovery_advice": {"label": "컨디션/회복 조언",             "template": "recovery_advice"},
    "race_predict":    {"label": "레이스 준비도 / 예상 기록",    "template": "race_predict"},
    "injury_risk":     {"label": "부상 위험도 체크",             "template": "injury_risk"},
    "goal_setting":    {"label": "목표 설정 도움",               "template": "goal_setting"},
    "pace_zones":      {"label": "페이스/HR 존 분석",            "template": "pace_zones"},
    "season_review":   {"label": "시즌 전체 리뷰",              "template": "season_review"},
}
