"""프롬프트 템플릿 관리 — 카드별 AI 프롬프트 정의 + 사용자 커스터마이즈.

config.json의 ai.custom_prompts에 사용자 수정본 저장.
없으면 기본 템플릿 사용.
"""
from __future__ import annotations

from typing import Any

# 카드별 프롬프트 템플릿 (기본값)
DEFAULT_PROMPTS: dict[str, dict[str, str]] = {
    # ── 대시보드 ──
    "dashboard_recommendation": {
        "system": "당신은 경험 많은 러닝 코치입니다.",
        "template": (
            "아래 데이터로 오늘 훈련 조언을 한국어 2문장으로 해주세요. "
            "오늘 계획된 훈련(planned_workout)이 있으면 그것을 기준으로 "
            "현재 컨디션(UTRS/ACWR/CIRS/DI)에 맞게 '그대로 진행', '강도 낮춰 진행', "
            "'더 높여도 됨', '다른 유형으로 대체' 중 하나를 명확히 권장하세요. "
            "계획이 없으면 컨디션 기반으로 적합한 운동 유형과 강도를 권장하세요.\n\n{context}"
        ),
        "max_tokens": 150,
        "description": "대시보드 > 오늘의 훈련 권장",
    },
    "dashboard_risk": {
        "system": "당신은 스포츠 의학 전문가입니다.",
        "template": (
            "아래 리스크 지표와 7일 추세를 분석해 한국어 1~2문장으로 요약하세요. "
            "위험 수준과 대응 조치를 구체적으로.\n\n{context}"
        ),
        "max_tokens": 100,
        "description": "대시보드 > 리스크 상세",
    },
    "dashboard_rmr": {
        "system": "당신은 러닝 코치입니다.",
        "template": (
            "RMR 5축 점수를 분석해 강점 1개, 약점 1개를 한국어 2문장으로.\n\n{context}"
        ),
        "max_tokens": 100,
        "description": "대시보드 > RMR 성숙도",
    },
    "dashboard_fitness": {
        "system": "당신은 러닝 코치입니다.",
        "template": (
            "VDOT/Marathon Shape/eFTP/REC 변화를 한국어 2문장으로 평가.\n\n{context}"
        ),
        "max_tokens": 100,
        "description": "대시보드 > 피트니스 현황",
    },
    # ── 훈련 탭 ──
    "training_coaching": {
        "system": "당신은 개인 러닝 코치입니다. 선수의 현재 상태와 계획을 바탕으로 조언합니다.",
        "template": (
            "아래 데이터로 종합 코칭 메시지를 한국어 3~4문장으로. "
            "이행률 평가, 오늘 조언, 이번 주 남은 계획을 포함하세요.\n\n{context}"
        ),
        "max_tokens": 250,
        "description": "훈련 > AI 종합 코칭",
    },
    "training_adjustment": {
        "system": "당신은 러닝 코치입니다.",
        "template": (
            "오늘 컨디션(웰니스 + CIRS)을 고려해 훈련 조정 조언을 한국어 2문장으로.\n\n{context}"
        ),
        "max_tokens": 120,
        "description": "훈련 > 컨디션 조정",
    },
    "training_weekly": {
        "system": "당신은 러닝 코치입니다.",
        "template": (
            "이번 주 훈련 진행 상황과 남은 일정을 한국어 2문장으로 피드백.\n\n{context}"
        ),
        "max_tokens": 120,
        "description": "훈련 > 주간 피드백",
    },
    # ── AI 코치 ──
    "coach_briefing": {
        "system": "당신은 경험 많은 러닝 코치입니다. 아래 데이터를 바탕으로 오늘의 브리핑을 작성합니다.",
        "template": (
            "다음 항목을 포함한 브리핑을 한국어로 작성하세요:\n"
            "1. 오늘 컨디션 종합 (1~2줄)\n"
            "2. 이번 주 훈련 평가 (1줄)\n"
            "3. 주목할 점 (부상 위험, 과훈련 등) (1줄)\n"
            "4. 오늘 권장 훈련 (구체적) (1~2줄)\n"
            "5. 이번 주 나머지 방향 (1줄)\n\n{context}"
        ),
        "max_tokens": 500,
        "description": "AI 코치 > 일일 브리핑",
    },
    # ── 레포트 ──
    "report_insight": {
        "system": "당신은 러닝 데이터 분석가입니다.",
        "template": (
            "{period} 기간 분석을 5개 핵심 포인트로 한국어 작성.\n"
            "각 포인트는 1줄. 진전/퇴보/주의사항 포함.\n\n{context}"
        ),
        "max_tokens": 300,
        "description": "레포트 > 기간 AI 인사이트",
    },
    # ── 레이스 ──
    "race_readiness": {
        "system": "당신은 레이스 전문 코치입니다.",
        "template": (
            "레이스 준비도를 한국어 3문장으로 평가. "
            "목표 달성 가능성, 핵심 보완점, 남은 기간 조언.\n\n{context}"
        ),
        "max_tokens": 200,
        "description": "레이스 > 준비도 종합",
    },
    # ── 웰니스 ──
    "wellness_recovery": {
        "system": "당신은 스포츠 의학 전문가입니다.",
        "template": (
            "14일 웰니스 추세를 분석해 회복 조언을 한국어 3가지로. "
            "수면, 스트레스, HRV 패턴 참고.\n\n{context}"
        ),
        "max_tokens": 200,
        "description": "웰니스 > 회복 조언",
    },
    # ── 활동 상세 ──
    "activity_analysis": {
        "system": "당신은 러닝 코치입니다.",
        "template": (
            "이 활동을 한국어 3문장으로 분석. "
            "잘한 점, 개선점, 다음 훈련 제안.\n\n{context}"
        ),
        "max_tokens": 200,
        "description": "활동 > 종합 분석",
    },
    # ── 메트릭 해석 (공통) ──
    "metric_interpretation": {
        "system": "당신은 러닝 코치입니다.",
        "template": (
            "메트릭 {metric_name}={value}를 한국어 1문장으로 해석. "
            "러너에게 실질적 조언 포함.\n{extra_context}"
        ),
        "max_tokens": 80,
        "description": "메트릭 해석 (공통)",
    },
}


def get_prompt(card_key: str, config: dict | None = None, **kwargs) -> tuple[str, str]:
    """카드별 프롬프트 반환 (사용자 커스터마이즈 반영).

    Args:
        card_key: DEFAULT_PROMPTS의 키.
        config: 설정 dict (ai.custom_prompts 참조).
        **kwargs: 템플릿 변수 (context, period, metric_name 등).

    Returns:
        (system_prompt, user_prompt) 튜플.
    """
    # 사용자 커스텀 프롬프트 확인
    custom = (config or {}).get("ai", {}).get("custom_prompts", {}).get(card_key, {})
    default = DEFAULT_PROMPTS.get(card_key, {})

    system = custom.get("system", default.get("system", ""))
    template = custom.get("template", default.get("template", "{context}"))

    # 템플릿 변수 치환
    try:
        user_prompt = template.format(**kwargs)
    except KeyError:
        user_prompt = template

    return system, user_prompt


def get_all_prompts(config: dict | None = None) -> dict[str, dict]:
    """모든 프롬프트 목록 (설정 UI용). 커스텀 있으면 병합."""
    result = {}
    custom_all = (config or {}).get("ai", {}).get("custom_prompts", {})
    for key, default in DEFAULT_PROMPTS.items():
        custom = custom_all.get(key, {})
        result[key] = {
            "system": custom.get("system", default["system"]),
            "template": custom.get("template", default["template"]),
            "max_tokens": default.get("max_tokens", 200),
            "description": default.get("description", key),
            "is_custom": bool(custom),
        }
    return result


# ── 탭별 통합 프롬프트 ──────────────────────────────────────────────────

_TAB_PROMPTS: dict[str, str] = {
    "dashboard": (
        "당신은 러닝 코치입니다. 아래 데이터로 4가지 항목을 한국어로 분석하세요.\n"
        "반드시 JSON 형식으로만 답변하세요.\n\n"
        "{context}\n\n"
        "응답 형식:\n"
        '{{"recommendation": "오늘 훈련 조언 2문장", '
        '"risk": "위험 지표 요약 1문장", '
        '"rmr": "RMR 강점/약점 1문장", '
        '"fitness": "체력 변화 평가 1문장"}}'
    ),
    "activity": (
        "당신은 러닝 코치입니다. 아래 활동 데이터를 분석하세요.\n"
        "반드시 JSON 형식으로만 답변하세요.\n\n"
        "{context}\n\n"
        "응답 형식:\n"
        '{{"summary": "활동 종합 분석 3문장", '
        '"metrics": {{"메트릭명": "15자 이내 해석", ...}}}}'
    ),
    "report": (
        "당신은 러닝 데이터 분석가입니다. 아래 기간 데이터를 분석하세요.\n"
        "반드시 JSON 형식으로만 답변하세요.\n\n"
        "{context}\n\n"
        "응답 형식:\n"
        '{{"insight": "5개 핵심 포인트, 각 1줄"}}'
    ),
    "training": (
        "당신은 러닝 코치입니다. 훈련 계획을 평가하세요.\n"
        "반드시 JSON 형식으로만 답변하세요.\n\n"
        "{context}\n\n"
        "응답 형식:\n"
        '{{"coaching": "종합 코칭 3문장", "adjustment": "컨디션 조정 1~2문장"}}'
    ),
    "wellness": (
        "당신은 스포츠 의학 전문가입니다. 회복 상태를 분석하세요.\n"
        "반드시 JSON 형식으로만 답변하세요.\n\n"
        "{context}\n\n"
        "응답 형식:\n"
        '{{"recovery": "회복 조언 2~3문장", "pattern": "패턴 분석 1~2문장"}}'
    ),
    "race": (
        "당신은 레이스 전문 코치입니다. 준비도를 평가하세요.\n"
        "반드시 JSON 형식으로만 답변하세요.\n\n"
        "{context}\n\n"
        "응답 형식:\n"
        '{{"readiness": "준비도 평가 2~3문장", "pacing": "페이스 전략 1~2문장"}}'
    ),
}


def get_tab_prompt(tab: str, **kwargs) -> str:
    """탭별 통합 프롬프트 반환."""
    template = _TAB_PROMPTS.get(tab, "{context}")
    try:
        return template.format(**kwargs)
    except KeyError:
        return template
