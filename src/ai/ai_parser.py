"""AI 응답에서 JSON 추출 및 훈련 계획/추천 칩 파싱."""
from __future__ import annotations

import json
import re

from .ai_schema import validate_weekly_plan


def extract_json_block(text: str) -> dict | list | None:
    """텍스트에서 ```json … ``` 코드 블록의 JSON을 추출.

    코드 블록이 없으면 첫 번째 { } 또는 [ ] 블록을 시도한다.

    Args:
        text: AI 응답 텍스트.

    Returns:
        파싱된 dict / list. 찾지 못하면 None.
    """
    # ```json ... ``` 또는 ``` ... ``` 블록
    for m in re.finditer(r"```(?:json)?\s*([\s\S]*?)```", text, re.IGNORECASE):
        candidate = m.group(1).strip()
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue

    # 블록 없으면 첫 번째 { } 추출
    m = re.search(r"(\{[\s\S]*\})", text)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass

    # 첫 번째 [ ] 추출
    m = re.search(r"(\[[\s\S]*\])", text)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass

    return None


def parse_weekly_plan(text: str) -> tuple[dict | None, list[str]]:
    """AI 응답에서 주간 훈련 계획 JSON을 추출·검증.

    Args:
        text: AI 응답 텍스트.

    Returns:
        (plan_dict | None, error_list) 튜플.
        - plan_dict: 유효한 경우 정규화 전 원본 dict.
        - error_list: 비어있으면 성공.
    """
    data = extract_json_block(text)
    if data is None:
        return None, ["AI 응답에서 JSON 블록을 찾을 수 없습니다."]

    if not isinstance(data, dict):
        return None, [f"파싱된 JSON이 dict 아님: {type(data).__name__}"]

    is_valid, errors = validate_weekly_plan(data)
    if not is_valid:
        return None, errors

    return data, []


def parse_suggestions(text: str) -> list[str]:
    """AI 응답의 "suggestions" 배열에서 칩 레이블 텍스트 추출.

    파싱 실패 시 빈 리스트 반환 (graceful fallback).

    Returns:
        추천 칩 텍스트 리스트 (최대 5개).
    """
    data = extract_json_block(text)
    if not isinstance(data, dict):
        return []

    raw = data.get("suggestions")
    if not isinstance(raw, list):
        return []

    result: list[str] = []
    for item in raw[:5]:
        if isinstance(item, str) and item.strip():
            result.append(item.strip())
        elif isinstance(item, dict):
            label = item.get("label") or item.get("text") or item.get("question") or ""
            if label:
                result.append(str(label).strip())

    return result


def parse_ai_chips(text: str) -> list[dict]:
    """AI 응답에서 추천 칩 dict 리스트 추출.

    Returns:
        [{"id": "ai_chip_N", "label": "..."}] 리스트. 실패 시 [].
    """
    data = extract_json_block(text)
    if not isinstance(data, dict):
        return []

    chips_raw = data.get("suggestions") or data.get("chips") or []
    if not isinstance(chips_raw, list):
        return []

    chips: list[dict] = []
    for i, item in enumerate(chips_raw[:5]):
        if isinstance(item, str) and item.strip():
            chips.append({"id": f"ai_chip_{i}", "label": item.strip()})
        elif isinstance(item, dict):
            label = item.get("label") or item.get("text") or item.get("question") or ""
            chip_id = item.get("id") or f"ai_chip_{i}"
            if label:
                chips.append({"id": str(chip_id), "label": str(label).strip()})

    return chips
