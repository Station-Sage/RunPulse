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
        "primary_strategy": "prefer_runpulse",
    },
    "race_prediction": {
        "display_name": "레이스 예측",
        "members": [
            ("darp_5k_sec", "runpulse:formula_v1"),
            ("darp_10k_sec", "runpulse:formula_v1"),
            ("darp_half_sec", "runpulse:formula_v1"),
            ("darp_marathon_sec", "runpulse:formula_v1"),
            ("rri", "runpulse:formula_v1"),
            ("marathon_shape", "runpulse:formula_v1"),
        ],
        "primary_strategy": "show_all",
    },
    "readiness": {
        "display_name": "훈련 준비도",
        "members": [
            ("crs", "runpulse:formula_v1"),
            ("utrs", "runpulse:formula_v1"),
            ("training_readiness", "garmin"),
        ],
        "primary_strategy": "prefer_runpulse",
    },
    "recovery": {
        "display_name": "회복 상태",
        "members": [
            ("body_battery_high", "garmin"),
            ("body_battery_low", "garmin"),
            ("rmr", "runpulse:formula_v1"),
        ],
        "primary_strategy": "show_all",
    },
    "relative_effort": {
        "display_name": "상대적 노력도",
        "members": [
            ("relative_effort", "runpulse:formula_v1"),
            ("suffer_score", "strava"),
            ("training_load_score", "intervals"),
        ],
        "primary_strategy": "show_all",
    },
    "threshold_power": {
        "display_name": "임계 파워/페이스",
        "members": [
            ("critical_power", "runpulse:formula_v1"),
            ("eftp", "runpulse:formula_v1"),
            ("icu_ftp", "intervals"),
        ],
        "primary_strategy": "show_all",
    },
    "running_efficiency": {
        "display_name": "러닝 효율성",
        "members": [
            ("rec", "runpulse:formula_v1"),
            ("efficiency_factor_rp", "runpulse:formula_v1"),
            ("efficiency_factor", "intervals"),
        ],
        "primary_strategy": "prefer_runpulse",
    },
    "vdot": {
        "display_name": "VDOT",
        "members": [
            ("runpulse_vdot", "runpulse:formula_v1"),
            ("vdot_adj", "runpulse:formula_v1"),
            ("vo2max_activity", "garmin"),
            ("effective_vo2max", "runalyze"),
        ],
        "primary_strategy": "prefer_runpulse",
    },
}


def get_group_for_metric(metric_name: str, provider: str = None) -> str | None:
    """메트릭이 속한 시맨틱 그룹 이름 반환. 없으면 None."""
    for group_name, group in SEMANTIC_GROUPS.items():
        for member_name, member_provider in group["members"]:
            if member_name == metric_name:
                if provider is None or member_provider == provider:
                    return group_name
    return None


def get_group_members(group_name: str) -> list[tuple[str, str]]:
    """그룹에 속한 (metric_name, provider) 목록 반환."""
    group = SEMANTIC_GROUPS.get(group_name)
    if group is None:
        return []
    return list(group["members"])
