"""메트릭 브라우저 표시 분류·정렬 — 8의도 그룹 slug 매핑 + 당일 주목도(salience) 정렬.

registry `category`(저장 분류)는 건드리지 않고, 표시 전용 그룹(`group`)과 tier(P 대표/D 세부/C 숨김)를 slug 단위로 둔다.
설계: ux-review-2026-09/DESIGN-S4S5-IMPL.md §1~2. 순수 함수(DB 접근 없음).
"""
from __future__ import annotations

import math
from datetime import date as _date, timedelta

GROUPS: list[tuple[str, str]] = [
    ("today", "오늘 상태"),
    ("load", "훈련 부하"),
    ("race", "레이스 예측"),
    ("ability", "능력·효율"),
    ("sleep", "수면"),
    ("vitals", "생체 신호"),
    ("hr_ref", "심박 기준값"),
    ("env", "환경"),
    ("other", "기타"),
]
GROUP_LABELS = dict(GROUPS)

# group -> (대표 P, 세부 D, 구성요소 C=목록 숨김)
_SPEC: dict[str, tuple[str, str, str]] = {
    "today": (
        "utrs cirs crs rri",
        "training_readiness_score training_readiness_level",
        "utrs_body_battery utrs_tsb utrs_sleep utrs_hrv utrs_stress cirs_acwr cirs_lsi cirs_consecutive cirs_fatigue "
        "training_readiness_hrv_factor training_readiness_sleep_factor training_readiness_recovery_factor",
    ),
    "load": (
        "acwr tsb ctl atl garmin_acute_load garmin_chronic_load",
        "ramp_rate rtti lsi monotony training_strain running_tolerance_load running_tolerance_score training_response",
        "running_tolerance_optimal_min running_tolerance_optimal_max",
    ),
    "race": (
        "race_pred_marathon_sec race_pred_half_sec race_pred_10k_sec race_pred_5k_sec",
        "race_pred_vdot vdot_adj marathon_shape",
        "",
    ),
    "ability": ("vo2max rec critical_power eftp", "garmin_ftp lt_speed_ref sapi", ""),
    "sleep": (
        "sleep_score sleep_duration_sec sleep_deep_sec sleep_rem_sec",
        "sleep_light_sec sleep_awake_sec sleep_avg_hr sleep_body_battery_change",
        "sleep_start_time",
    ),
    "vitals": (
        "body_battery_high avg_stress avg_spo2 skin_temp_deviation",
        "body_battery_low min_spo2 avg_respiration_sleep min_respiration_sleep steps active_calories weight_kg",
        "stress_high_duration_sec stress_medium_duration_sec stress_low_duration_sec stress_rest_duration_sec",
    ),
    "hr_ref": (
        "resting_hr hrv_last_night hrv_weekly_avg hrmax_self",
        "lthr_self hrmax_ref lthr_ref hrv_5min_high hrv_status",
        "hrv_baseline_low hrv_baseline_balanced_low hrv_baseline_balanced_upper hr_profile",
    ),
    "env": ("heat_model", "", ""),
}

# slug -> (group, tier) — tier: "primary" | "detail" | "hidden"
SLUG_GROUP: dict[str, tuple[str, str]] = {}
for _g, (_p, _d, _c) in _SPEC.items():
    for _tier, _names in (("primary", _p), ("detail", _d), ("hidden", _c)):
        for _n in _names.split():
            SLUG_GROUP[_n] = (_g, _tier)

_BASELINE_DAYS = 28
_MIN_BASELINE = 7


def classify(slug: str) -> tuple[str, str]:
    """(group, tier). 미분류는 ("other","detail") — 숨기지 않는다(테스트가 누락을 잡는다)."""
    return SLUG_GROUP.get(slug, ("other", "detail"))


def baseline_z(rows: list[tuple[str, float]], date: str, floor: float) -> float | None:
    """기준일 값의 평소(d-28..d-1) 대비 편차 z. 기준일 값이 없거나 평소 표본 7일 미만이면 None."""
    if not rows or rows[-1][0] != date:
        return None
    d0 = _date.fromisoformat(date)
    lo = str(d0 - timedelta(days=_BASELINE_DAYS))
    base = [v for d, v in rows[:-1] if lo <= d < date]
    if len(base) < _MIN_BASELINE:
        return None
    mean = sum(base) / len(base)
    sd = math.sqrt(sum((v - mean) ** 2 for v in base) / len(base))
    return (rows[-1][1] - mean) / max(sd, floor, 1e-9)


def salience_key(entry: dict, registry_index: int) -> tuple:
    """사전식 정렬 키 — ①당일 값 ②경고 상태 ③|z| 큰 순 ④대표>세부 ⑤registry 순."""
    sal = entry["salience"]
    z = sal["z"]
    return (
        0 if sal["fresh"] else 1,
        0 if entry.get("status") in ("poor", "caution") else 1,
        -round(abs(z), 1) if z is not None else math.inf,
        0 if entry["tier"] == "primary" else 1,
        registry_index,
    )
