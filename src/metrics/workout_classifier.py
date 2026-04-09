"""운동 유형 분류 상수 — TAG_COLORS, TAG_LABELS, _EFFECTS.

UI 렌더링(views_guide, views_activities_helpers)에서 사용.
"""
from __future__ import annotations

# 분류별 훈련 효과
_EFFECTS: dict[str, str] = {
    "easy": "유산소 기반 강화",
    "tempo": "젖산역치 개선",
    "threshold": "역치 페이스 향상",
    "interval": "VO2Max 자극",
    "long": "지구력/지방 연소",
    "race": "최대 퍼포먼스",
    "recovery": "피로 해소",
}

# 분류별 태그 색상
TAG_COLORS: dict[str, str] = {
    "easy": "#27ae60",
    "tempo": "#e67e22",
    "threshold": "#8e44ad",
    "interval": "#e74c3c",
    "long": "#2980b9",
    "race": "#c0392b",
    "recovery": "#7f8c8d",
}

# 분류별 한국어 라벨
TAG_LABELS: dict[str, str] = {
    "easy": "이지런",
    "tempo": "템포",
    "threshold": "역치",
    "interval": "인터벌",
    "long": "장거리",
    "race": "레이스",
    "recovery": "회복",
}
