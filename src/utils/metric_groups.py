"""메트릭 의미 그룹핑 — 소스 비교 뷰 지원 (보강 #8).

UI에서 같은 개념의 여러 provider 값을 나란히 표시할 때 사용.
"""
from __future__ import annotations

SEMANTIC_GROUPS: dict[str, dict] = {
    "decoupling": {
        "display_name": "유산소 분리",
        "members": [
            ("aerobic_decoupling_rp", "runpulse:formula_v1"),
            ("decoupling", "intervals"),
        ],
        "primary_strategy": "prefer_runpulse",
    },
    "trimp": {
        "display_name": "TRIMP",
        "members": [
            ("trimp", "runpulse:formula_v1"),
            ("trimp", "intervals"),
        ],
        "primary_strategy": "prefer_runpulse",
    },
    "training_load": {
        "display_name": "훈련 부하",
        "members": [
            ("training_load_score", "intervals"),
            ("training_load", "garmin"),
            ("suffer_score", "strava"),
            ("hrss", "runpulse:formula_v1"),
        ],
        "primary_strategy": "show_all",
    },
    "vo2max": {
        "display_name": "VO2Max",
        "members": [
            ("runpulse_vdot", "runpulse:formula_v1"),
            ("vo2max_activity", "garmin"),
            ("effective_vo2max", "runalyze"),
        ],
        "primary_strategy": "show_all",
    },
    "race_prediction": {
        "display_name": "레이스 예측",
        "members": [
            ("darp_5k", "runpulse:formula_v1"),
            ("darp_10k", "runpulse:formula_v1"),
            ("darp_half", "runpulse:formula_v1"),
            ("darp_marathon", "runpulse:formula_v1"),
            ("race_pred_5k_sec", "garmin"),
            ("race_pred_10k_sec", "garmin"),
            ("race_pred_half_sec", "garmin"),
            ("race_pred_marathon_sec", "garmin"),
        ],
        "primary_strategy": "show_all",
    },
    "readiness": {
        "display_name": "훈련 준비도",
        "members": [
            ("utrs", "runpulse:formula_v1"),
            ("training_readiness_score", "garmin"),
        ],
        "primary_strategy": "show_all",
    },
    "recovery": {
        "display_name": "회복 상태",
        "members": [
            ("rmr", "runpulse:formula_v1"),
            ("body_battery_high", "garmin"),
        ],
        "primary_strategy": "show_all",
    },
}


def get_group_for_metric(metric_name: str, provider: str = None) -> str | None:
    """메트릭이 속한 그룹명 반환. 없으면 None."""
    for group_name, group in SEMANTIC_GROUPS.items():
        for m_name, m_prov in group["members"]:
            if m_name == metric_name:
                if provider is None or m_prov == provider:
                    return group_name
    return None


def get_group_members(group_name: str) -> list[tuple[str, str]]:
    """그룹의 (metric_name, provider) 목록 반환."""
    group = SEMANTIC_GROUPS.get(group_name)
    return group["members"] if group else []
