"""조정 v3 트리거 신호의 사용자 표시 라벨 (프론트 adjustmentView.CHIP 과 같은 문구)."""
from __future__ import annotations

_FIXED = {"pain": "통증 기록", "illness": "질병 확인", "checkin_pain": "체크인 통증",
          "condition": "컨디션 신호"}


def trigger_label(sig: dict) -> str | None:
    """라벨 정의가 없는 신호는 None."""
    name, v = sig.get("signal"), sig.get("value")
    if name in _FIXED:
        return _FIXED[name]
    if not isinstance(v, (int, float)):
        return None
    if name == "checkin_fatigue":
        return f"체크인 피로 {v:g}/10"
    if name == "crs":
        return f"CRS 레벨 {v:g}"
    if name == "acwr":
        return f"ACWR {v:.2f}"
    return None
