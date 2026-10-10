"""메트릭 표시 이름 SSOT — 레지스트리 canonical name → (name_ko, abbr). ADR-018.

일별(daily) 지표는 전부 명시 등록한다(tests/test_metric_labels.py가 강제). 그 외 scope는 label_for()의
폴백(description에서 "(parent: …)" 제거 → canonical name)을 쓴다. 폴백은 노출 필터로 쓰지 않는다.
숫자 표기 규칙은 services/metric_display.py, 등급은 metrics/bands.py가 담당한다.
"""
from __future__ import annotations

import re
from typing import NamedTuple


class MetricLabel(NamedTuple):
    name_ko: str
    abbr: str | None = None
    description_short: str | None = None
    action_hint: dict[str, str] | None = None


METRIC_LABELS: dict[str, MetricLabel] = {
    "sleep_score": MetricLabel("수면 점수"),
    "sleep_duration_sec": MetricLabel("총 수면 시간"),
    "sleep_start_time": MetricLabel("취침 시각"),
    "hrv_weekly_avg": MetricLabel("심박변이도 주간 평균", "HRV"),
    "hrv_last_night": MetricLabel("지난밤 심박변이도", "HRV"),
    "resting_hr": MetricLabel("안정시 심박", "RHR"),
    "hrv_status": MetricLabel("심박변이도 상태", "HRV"),
    "hrv_5min_high": MetricLabel("야간 최고 5분 심박변이도", "HRV"),
    "hrv_baseline_low": MetricLabel("심박변이도 기준선 하한", "HRV"),
    "hrv_baseline_balanced_low": MetricLabel("심박변이도 균형 범위 하한", "HRV"),
    "hrv_baseline_balanced_upper": MetricLabel("심박변이도 균형 범위 상한", "HRV"),
    "body_battery_high": MetricLabel("바디 배터리 최고", "BB"),
    "body_battery_low": MetricLabel("바디 배터리 최저", "BB"),
    "steps": MetricLabel("걸음 수"),
    "active_calories": MetricLabel("활동 칼로리"),
    "weight_kg": MetricLabel("체중"),
    "avg_stress": MetricLabel("평균 스트레스"),
    "ctl": MetricLabel("체력", "CTL"),
    "atl": MetricLabel("피로", "ATL"),
    "garmin_acute_load": MetricLabel("가민 급성 부하"),
    "garmin_chronic_load": MetricLabel("가민 만성 부하"),
    "tsb": MetricLabel("폼", "TSB"),
    "ramp_rate": MetricLabel("체력 증가율"),
    "acwr": MetricLabel("급성/만성 부하비", "ACWR"),
    "lsi": MetricLabel("부하 급증 지수", "LSI"),
    "monotony": MetricLabel("훈련 단조로움"),
    "training_strain": MetricLabel("훈련 스트레인"),
    "rtti": MetricLabel("달리기 내성 지수", "RTTI"),
    "running_tolerance_load": MetricLabel("Garmin 러닝 내성 부하"),
    "running_tolerance_optimal_min": MetricLabel("Garmin 러닝 내성 최적 하한"),
    "running_tolerance_optimal_max": MetricLabel("Garmin 러닝 내성 최적 상한"),
    "running_tolerance_score": MetricLabel("Garmin 러닝 내성 점수"),
    "rec": MetricLabel("러닝 효율", "REC"),
    "race_pred_vdot": MetricLabel("예측 VDOT"),
    "hr_profile": MetricLabel("심박 프로필"),
    "hrmax_self": MetricLabel("최대 심박 추정", "HRmax"),
    "lthr_self": MetricLabel("젖산역치 심박 추정", "LTHR"),
    "lthr_ref": MetricLabel("기기 젖산역치 심박", "LTHR"),
    "hrmax_ref": MetricLabel("기기 최대 심박", "HRmax"),
    "lt_speed_ref": MetricLabel("기기 역치 속도"),
    "garmin_ftp": MetricLabel("Garmin 러닝 FTP"),
    "training_response": MetricLabel("훈련 반응"),
    "critical_power": MetricLabel("임계 파워", "CP"),
    "eftp": MetricLabel("역치 페이스 추정", "eFTP"),
    "vdot_adj": MetricLabel("보정 VDOT"),
    "marathon_shape": MetricLabel("마라톤 볼륨 충족률"),
    "sapi": MetricLabel("계절 성과 지수", "SAPI"),
    "rri": MetricLabel("레이스 준비도", "RRI"),
    "vo2max": MetricLabel("최대 산소섭취량", "VO2max"),
    "race_pred_5k_sec": MetricLabel("5K 예측 기록"),
    "race_pred_10k_sec": MetricLabel("10K 예측 기록"),
    "race_pred_half_sec": MetricLabel("하프 예측 기록"),
    "race_pred_marathon_sec": MetricLabel("마라톤 예측 기록"),
    "sleep_deep_sec": MetricLabel("깊은 수면"),
    "sleep_light_sec": MetricLabel("얕은 수면"),
    "sleep_rem_sec": MetricLabel("렘 수면", "REM"),
    "sleep_awake_sec": MetricLabel("수면 중 깬 시간"),
    "avg_spo2": MetricLabel("평균 산소포화도", "SpO2"),
    "min_spo2": MetricLabel("최저 산소포화도", "SpO2"),
    "avg_respiration_sleep": MetricLabel("수면 중 평균 호흡수"),
    "min_respiration_sleep": MetricLabel("수면 중 최저 호흡수"),
    "sleep_avg_hr": MetricLabel("수면 중 평균 심박"),
    "sleep_body_battery_change": MetricLabel("수면 중 바디 배터리 충전", "BB"),
    "skin_temp_deviation": MetricLabel("피부 온도 편차"),
    "stress_high_duration_sec": MetricLabel("높은 스트레스 시간"),
    "stress_medium_duration_sec": MetricLabel("중간 스트레스 시간"),
    "stress_low_duration_sec": MetricLabel("낮은 스트레스 시간"),
    "stress_rest_duration_sec": MetricLabel("휴식 상태 시간"),
    "training_readiness_score": MetricLabel("Garmin 훈련 준비도"),
    "training_readiness_level": MetricLabel("Garmin 훈련 준비도 등급"),
    "training_readiness_hrv_factor": MetricLabel("Garmin 준비도 심박변이도 요인"),
    "training_readiness_sleep_factor": MetricLabel("Garmin 준비도 수면 요인"),
    "training_readiness_recovery_factor": MetricLabel("Garmin 준비도 회복 요인"),
    "crs": MetricLabel("복합 준비도", "CRS"),
    "utrs": MetricLabel("훈련 준비도", "UTRS"),
    "utrs_body_battery": MetricLabel("바디 배터리 요소", "BB"),
    "utrs_tsb": MetricLabel("폼 요소", "TSB"),
    "utrs_sleep": MetricLabel("수면 요소"),
    "utrs_hrv": MetricLabel("심박변이도 요소", "HRV"),
    "utrs_stress": MetricLabel("스트레스 요소"),
    "cirs": MetricLabel("부상 위험", "CIRS"),
    "cirs_acwr": MetricLabel("부하비 위험 요소", "ACWR"),
    "cirs_lsi": MetricLabel("부하 급증 위험 요소", "LSI"),
    "cirs_consecutive": MetricLabel("연속 훈련일 위험 요소"),
    "cirs_fatigue": MetricLabel("피로 누적 위험 요소"),
    "heat_model": MetricLabel("기온 영향 계수"),
    "trimp": MetricLabel("심박 기반 훈련 부하", "TRIMP"),
}

def _merge_texts() -> None:
    from src.utils.metric_label_texts import TEXTS

    for key, (short, hints) in TEXTS.items():
        METRIC_LABELS[key] = METRIC_LABELS[key]._replace(description_short=short, action_hint=hints or None)


_merge_texts()

_PARENT_RE = re.compile(r"\s*\(parent:[^)]*\)")


def label_for(name: str, description: str = "") -> MetricLabel:
    """등록된 라벨, 없으면 description(내부 식별자 제거) → canonical name 폴백. abbr 폴백은 None."""
    found = METRIC_LABELS.get(name)
    if found is not None:
        return found
    return MetricLabel(_PARENT_RE.sub("", description or "").strip() or name)
