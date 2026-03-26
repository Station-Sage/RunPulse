"""AI 응답 검증 — 포맷 + 길이 + 데이터 정합성.

검증 실패 시 재시도 또는 규칙 기반 fallback.
"""
from __future__ import annotations

import json
import logging
from typing import Any

log = logging.getLogger(__name__)

# 탭별 필수 키
TAB_REQUIRED_KEYS: dict[str, list[str]] = {
    "dashboard": ["recommendation"],
    "activity": ["summary"],
    "report": ["insight"],
    "training": ["coaching"],
    "wellness": ["recovery"],
    "race": ["readiness"],
}

# 항목별 길이 제한
_MIN_LEN = 5
_MAX_LEN = 500


def validate_response(tab: str, response: dict, actual_data: dict | None = None
                      ) -> tuple[bool, str]:
    """AI 응답 3단계 검증.

    Returns:
        (통과 여부, 실패 이유).
    """
    # 1. 포맷 검증
    if not isinstance(response, dict):
        return False, "응답이 dict가 아님"

    required = TAB_REQUIRED_KEYS.get(tab, [])
    for key in required:
        if key not in response:
            return False, f"필수 키 누락: {key}"

    # 2. 길이 검증
    for key, text in response.items():
        if not isinstance(text, str):
            continue
        if len(text) < _MIN_LEN:
            return False, f"{key}: 너무 짧음 ({len(text)}자)"
        if len(text) > _MAX_LEN:
            return False, f"{key}: 너무 김 ({len(text)}자)"

    # 3. 데이터 정합성
    if actual_data:
        ok, reason = _check_consistency(tab, response, actual_data)
        if not ok:
            return False, reason

    return True, ""


def _check_consistency(tab: str, response: dict, data: dict) -> tuple[bool, str]:
    """데이터 정합성 검증 — AI 답변이 실제 데이터와 모순되지 않는지."""
    rules = _CONSISTENCY_RULES.get(tab, [])
    for rule_fn, desc in rules:
        try:
            if not rule_fn(data, response):
                return False, f"정합성 실패: {desc}"
        except Exception:
            pass
    return True, ""


# 정합성 규칙: (검증 함수, 설명)
_CONSISTENCY_RULES: dict[str, list[tuple]] = {
    "dashboard": [
        (lambda d, ai: not (
            (d.get("utrs") or 100) < 40
            and any(w in ai.get("recommendation", "") for w in ["고강도", "인터벌", "레이스페이스"])
        ), "UTRS 낮은데 고강도 추천"),
        (lambda d, ai: not (
            (d.get("cirs") or 0) > 75
            and any(w in ai.get("recommendation", "") for w in ["계획대로", "정상 훈련", "강도 높여"])
        ), "CIRS 위험인데 정상 훈련 권장"),
    ],
    "wellness": [
        (lambda d, ai: not (
            (d.get("bb") or 100) < 30
            and "양호" in ai.get("recovery", "")
        ), "BB 30 미만인데 양호 판정"),
    ],
    "training": [
        (lambda d, ai: not (
            (d.get("cirs") or 0) > 75
            and "계획대로" in ai.get("coaching", "")
        ), "CIRS 위험인데 계획대로 권장"),
    ],
}


def parse_json_response(text: str) -> dict | None:
    """AI 텍스트 응답에서 JSON 추출."""
    if not text:
        return None
    # 직접 파싱 시도
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # ```json ... ``` 블록 추출
    if "```json" in text:
        start = text.find("```json") + 7
        end = text.find("```", start)
        if end > start:
            try:
                return json.loads(text[start:end].strip())
            except json.JSONDecodeError:
                pass
    # { ... } 추출
    start = text.find("{")
    end = text.rfind("}") + 1
    if start >= 0 and end > start:
        try:
            return json.loads(text[start:end])
        except json.JSONDecodeError:
            pass
    return None
