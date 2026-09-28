"""활동 메트릭 표시 규칙 — UX 리뷰 20 design §4-5 (계산은 그대로 두고 화면에 낼지만 정한다).

- VDOT(활동): 전력 주행을 가정한 공식이라 대회·템포 분류일 때만 낸다(F-DATA-07, 이지런 VDOT 금지).
- Relative Effort: 평균 심박 근사(confidence < 0.8)는 존 체류 시간이 없어 오차가 커 숨긴다(F-DATA-01).
"""
from __future__ import annotations

VDOT_WORKOUT_TYPES = {"race", "tempo"}
MIN_RE_CONFIDENCE = 0.8


def visible_activity_metrics(rows: list[dict]) -> list[dict]:
    """metric_store 활동 행 목록 → 표시할 행만."""
    wtype = next((r.get("text_value") for r in rows if r.get("metric_name") == "workout_type_classified"), None)

    def keep(r: dict) -> bool:
        name = r.get("metric_name")
        if name == "runpulse_vdot":
            return wtype in VDOT_WORKOUT_TYPES
        if name == "relative_effort" and r.get("confidence") is not None:
            return r["confidence"] >= MIN_RE_CONFIDENCE
        return True

    return [r for r in rows if keep(r)]
