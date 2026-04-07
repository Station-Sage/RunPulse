"""RunPulse 메트릭 레지스트리 v0.3.1

모든 메트릭과 Layer 1 컬럼의 정규 이름, 카테고리, 저장 위치, 단위, 소스별 별칭을 정의합니다.
이 파일이 데이터 정의의 Single Source of Truth(SSOT)입니다.

사용법:
    from src.utils.metric_registry import canonicalize, get_metric, METRIC_REGISTRY

    name, category = canonicalize("aerobicTrainingEffect", source="garmin")
    metric = get_metric("trimp")
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


# ─────────────────────────────────────────────────────────────────────────────
# 데이터 구조
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class MetricDef:
    """메트릭/컬럼 정의.

    storage 값:
        "activity_summary" — activity_summaries 테이블 컬럼 (Layer 1)
        "wellness"         — daily_wellness 테이블 컬럼 (Layer 1)
        "metric"           — metric_store 테이블 행 (Layer 2)
    """
    name: str                                 # 정규 이름 (canonical)
    category: str                             # 도메인 카테고리
    storage: str = "metric"                   # 저장 위치
    unit: str = ""                            # 표시 단위
    description: str = ""                     # 한국어 설명
    scope: str = "activity"                   # 'activity' | 'daily' | 'weekly' | 'athlete'
    aliases: dict[str, str] = field(default_factory=dict)
    # aliases = {"garmin": "rawFieldName", "strava": "raw_name", ...}


# ─────────────────────────────────────────────────────────────────────────────
# 카테고리 정의 (16 도메인)
# ─────────────────────────────────────────────────────────────────────────────

METRIC_CATEGORIES: dict[str, str] = {
    "hr":               "심박",
    "power":            "파워",
    "pace":             "페이스",
    "running_dynamics":  "러닝 다이내믹스",
    "volume":           "운동량",
    "load":             "부하",
    "efficiency":       "효율성",
    "capacity":         "체력/역량",
    "prediction":       "예측",
    "sleep":            "수면",
    "stress":           "스트레스",
    "readiness":        "준비도",
    "weather":          "날씨/환경",
    "body":             "신체",
    "meta":             "메타/분류",
    "athlete":          "선수 설정",
    "_unmapped":        "미매핑 (개발용)",
}


# ─────────────────────────────────────────────────────────────────────────────
# 메트릭 정의
# ─────────────────────────────────────────────────────────────────────────────

_DEFINITIONS: list[MetricDef] = [

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Layer 1: activity_summaries 컬럼 (storage="activity_summary")
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    # ── meta ──
    MetricDef("name", "meta", "activity_summary", "", "활동 이름"),
    MetricDef("activity_type", "meta", "activity_summary", "", "활동 유형"),
    MetricDef("start_time", "meta", "activity_summary", "", "시작 시간"),
    MetricDef("start_lat", "meta", "activity_summary", "°", "시작 위도"),
    MetricDef("start_lon", "meta", "activity_summary", "°", "시작 경도"),
    MetricDef("end_lat", "meta", "activity_summary", "°", "종료 위도"),
    MetricDef("end_lon", "meta", "activity_summary", "°", "종료 경도"),
    MetricDef("description", "meta", "activity_summary", "", "활동 설명"),
    MetricDef("event_type", "meta", "activity_summary", "", "이벤트 유형"),
    MetricDef("device_name", "meta", "activity_summary", "", "기기명"),
    MetricDef("gear_id", "meta", "activity_summary", "", "장비 FK"),
    MetricDef("source_url", "meta", "activity_summary", "", "원본 URL"),

    # ── volume ──
    MetricDef("distance_m", "volume", "activity_summary", "m", "거리"),
    MetricDef("duration_sec", "volume", "activity_summary", "sec", "총 시간"),
    MetricDef("moving_time_sec", "volume", "activity_summary", "sec", "이동 시간"),
    MetricDef("elapsed_time_sec", "volume", "activity_summary", "sec", "경과 시간"),
    MetricDef("elevation_gain", "volume", "activity_summary", "m", "누적 상승고도"),
    MetricDef("elevation_loss", "volume", "activity_summary", "m", "누적 하강고도"),

    # ── pace ──
    MetricDef("avg_speed_ms", "pace", "activity_summary", "m/s", "평균 속도"),
    MetricDef("max_speed_ms", "pace", "activity_summary", "m/s", "최대 속도"),
    MetricDef("avg_pace_sec_km", "pace", "activity_summary", "sec/km", "평균 페이스"),

    # ── hr ──
    MetricDef("avg_hr", "hr", "activity_summary", "bpm", "평균 심박수"),
    MetricDef("max_hr", "hr", "activity_summary", "bpm", "최대 심박수"),

    # ── running_dynamics ──
    MetricDef("avg_cadence", "running_dynamics", "activity_summary", "spm", "평균 케이던스"),
    MetricDef("max_cadence", "running_dynamics", "activity_summary", "spm", "최대 케이던스"),
    MetricDef("avg_ground_contact_time_ms", "running_dynamics", "activity_summary", "ms", "평균 지면 접촉 시간"),
    MetricDef("avg_stride_length_cm", "running_dynamics", "activity_summary", "cm", "평균 보폭"),
    MetricDef("avg_vertical_oscillation_cm", "running_dynamics", "activity_summary", "cm", "평균 수직 진폭"),
    MetricDef("avg_vertical_ratio_pct", "running_dynamics", "activity_summary", "%", "평균 수직비"),

    # ── power ──
    MetricDef("avg_power", "power", "activity_summary", "W", "평균 파워"),
    MetricDef("max_power", "power", "activity_summary", "W", "최대 파워"),

    # ── weather ──
    MetricDef("avg_temperature", "weather", "activity_summary", "°C", "평균 기온"),

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Layer 1: daily_wellness 컬럼 (storage="wellness")
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    # ── sleep ──
    MetricDef("sleep_score", "sleep", "wellness", "", "수면 점수", scope="daily"),
    MetricDef("sleep_duration_sec", "sleep", "wellness", "sec", "총 수면 시간", scope="daily"),
    MetricDef("sleep_start_time", "sleep", "wellness", "", "취침 시각", scope="daily"),

    # ── hr ──
    MetricDef("hrv_weekly_avg", "hr", "wellness", "ms", "HRV 주간 평균", scope="daily"),
    MetricDef("hrv_last_night", "hr", "wellness", "ms", "HRV 전날 밤", scope="daily"),
    MetricDef("resting_hr", "hr", "wellness", "bpm", "안정시 심박수", scope="daily"),
    # HRV 상세 (metric_store)
    MetricDef("hrv_status", "hr", "metric", "", "HRV 상태 텍스트 (balanced 등)", scope="daily"),
    MetricDef("hrv_baseline_low", "hr", "metric", "ms", "HRV 기준선 하한", scope="daily"),
    MetricDef("hrv_baseline_balanced_low", "hr", "metric", "ms", "HRV 균형 기준선 하한", scope="daily"),
    MetricDef("hrv_baseline_balanced_upper", "hr", "metric", "ms", "HRV 균형 기준선 상한", scope="daily"),

    # ── body ──
    MetricDef("body_battery_high", "body", "wellness", "", "Body Battery 최고", scope="daily"),
    MetricDef("body_battery_low", "body", "wellness", "", "Body Battery 최저", scope="daily"),
    MetricDef("steps", "body", "wellness", "count", "일일 걸음 수", scope="daily"),
    MetricDef("active_calories", "body", "wellness", "kcal", "활동 칼로리", scope="daily"),
    MetricDef("weight_kg", "body", "wellness", "kg", "체중", scope="daily"),

    # ── stress ──
    MetricDef("avg_stress", "stress", "wellness", "", "평균 스트레스", scope="daily"),

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Layer 2: metric_store (storage="metric")
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    # ── hr (zone 분포) ──
    MetricDef("hr_zone_1_sec", "hr", "metric", "sec", "HR Zone 1 체류 시간",
              aliases={"garmin": "hrTimeInZone_0"}),
    MetricDef("hr_zone_2_sec", "hr", "metric", "sec", "HR Zone 2 체류 시간",
              aliases={"garmin": "hrTimeInZone_1"}),
    MetricDef("hr_zone_3_sec", "hr", "metric", "sec", "HR Zone 3 체류 시간",
              aliases={"garmin": "hrTimeInZone_2"}),
    MetricDef("hr_zone_4_sec", "hr", "metric", "sec", "HR Zone 4 체류 시간",
              aliases={"garmin": "hrTimeInZone_3"}),
    MetricDef("hr_zone_5_sec", "hr", "metric", "sec", "HR Zone 5 체류 시간",
              aliases={"garmin": "hrTimeInZone_4"}),
    MetricDef("hr_zone_1_pct", "hr", "metric", "%", "HR Zone 1 비율"),
    MetricDef("hr_zone_2_pct", "hr", "metric", "%", "HR Zone 2 비율"),
    MetricDef("hr_zone_3_pct", "hr", "metric", "%", "HR Zone 3 비율"),
    MetricDef("hr_zone_4_pct", "hr", "metric", "%", "HR Zone 4 비율"),
    MetricDef("hr_zone_5_pct", "hr", "metric", "%", "HR Zone 5 비율"),
    MetricDef("hr_zones_detail", "hr", "metric", "json", "HR Zone 전체 상세",
              aliases={"garmin": "hrTimeInZone"}),

    # ── power (zone + 설정) ──
    MetricDef("power_zone_1_sec", "power", "metric", "sec", "Power Zone 1 체류 시간",
              aliases={"garmin": "powerTimeInZone_0"}),
    MetricDef("power_zone_2_sec", "power", "metric", "sec", "Power Zone 2 체류 시간",
              aliases={"garmin": "powerTimeInZone_1"}),
    MetricDef("power_zone_3_sec", "power", "metric", "sec", "Power Zone 3 체류 시간",
              aliases={"garmin": "powerTimeInZone_2"}),
    MetricDef("power_zone_4_sec", "power", "metric", "sec", "Power Zone 4 체류 시간",
              aliases={"garmin": "powerTimeInZone_3"}),
    MetricDef("power_zone_5_sec", "power", "metric", "sec", "Power Zone 5 체류 시간",
              aliases={"garmin": "powerTimeInZone_4"}),
    MetricDef("icu_ftp", "power", "metric", "W", "Intervals FTP",
              aliases={"intervals": "icu_ftp"}),
    MetricDef("icu_w_prime", "power", "metric", "kJ", "Intervals W'",
              aliases={"intervals": "icu_w_prime"}),

    # ── pace (구간 페이스) ──
    MetricDef("pace_1k", "pace", "metric", "sec/km", "1km 페이스"),
    MetricDef("pace_5k", "pace", "metric", "sec/km", "5km 페이스"),
    MetricDef("pace_10k", "pace", "metric", "sec/km", "10km 페이스"),
    MetricDef("negative_split_ratio", "pace", "metric", "ratio", "네거티브 스플릿 비율"),

    # ── running_dynamics (확장) ──
    MetricDef("ground_contact_balance", "running_dynamics", "metric", "%", "지면 접촉 밸런스 (L/R)",
              aliases={"garmin": "avgGroundContactBalance"}),
    MetricDef("avg_respiration_rate", "running_dynamics", "metric", "brpm", "평균 호흡수",
              aliases={"garmin": "avgRespirationRate"}),
    MetricDef("ground_contact_time_balance", "running_dynamics", "metric", "%", "GCT 밸런스"),
    MetricDef("stance_time", "running_dynamics", "metric", "ms", "스탠스 타임"),
    MetricDef("leg_spring_stiffness", "running_dynamics", "metric", "kN/m", "다리 스프링 강성"),
    MetricDef("form_power", "running_dynamics", "metric", "W", "폼 파워"),
    MetricDef("impact_loading_rate", "running_dynamics", "metric", "BW/s", "충격 부하율"),

    # ── volume (metric_store) ──
    MetricDef("steps_activity", "volume", "metric", "count", "활동 중 걸음수",
              aliases={"garmin": "steps"}),

    # ── load (훈련 부하) ──
    MetricDef("trimp", "load", "metric", "score", "TRIMP (Banister)",
              aliases={"intervals": "icu_trimp"}),
    MetricDef("hrss", "load", "metric", "score", "HR Stress Score",
              aliases={"intervals": "icu_hrss"}),
    MetricDef("rtss", "load", "metric", "score", "Running TSS (rTSS)"),
    MetricDef("intensity_factor", "load", "metric", "", "Intensity Factor (IF)",
              aliases={"intervals": "icu_intensity"}),
    MetricDef("training_stress_score", "load", "metric", "score", "TSS",
              aliases={"garmin": "trainingStressScore"}),
    MetricDef("training_effect_aerobic", "load", "metric", "", "유산소 훈련 효과"),
    MetricDef("training_effect_anaerobic", "load", "metric", "", "무산소 훈련 효과"),
    MetricDef("training_load_peak", "load", "metric", "", "최대 훈련 부하"),
    MetricDef("performance_condition", "load", "metric", "", "퍼포먼스 컨디션",
              aliases={"garmin": "performanceCondition"}),
    MetricDef("relative_effort", "load", "metric", "AU", "Relative Effort (심박존 기반)"),
    MetricDef("wlei", "load", "metric", "AU", "WLEI (날씨 가중 노력 지수)"),
    MetricDef("icu_feel", "load", "metric", "", "체감 (Intervals Feel)",
              aliases={"intervals": "icu_feel"}),
    MetricDef("icu_rpe", "load", "metric", "", "주관적 운동 강도 (RPE)",
              aliases={"intervals": "icu_rpe", "garmin": "averageRPE", "strava": "perceived_exertion"}),
    MetricDef("intensity_mins_moderate", "load", "metric", "min", "중강도 활동 시간",
              aliases={"garmin": "moderateIntensityMinutes"}),
    MetricDef("intensity_mins_vigorous", "load", "metric", "min", "고강도 활동 시간",
              aliases={"garmin": "vigorousIntensityMinutes"}),
    MetricDef("kilojoules", "load", "metric", "kJ", "에너지 출력 (사이클링)",
              aliases={"strava": "kilojoules"}),
    # daily load
    MetricDef("ctl", "load", "metric", "", "Chronic Training Load", scope="daily"),
    MetricDef("atl", "load", "metric", "", "Acute Training Load", scope="daily"),
    MetricDef("tsb", "load", "metric", "", "Training Stress Balance", scope="daily"),
    MetricDef("ramp_rate", "load", "metric", "", "CTL 증가율", scope="daily"),
    MetricDef("acwr", "load", "metric", "", "Acute:Chronic Workload Ratio", scope="daily"),
    MetricDef("lsi", "load", "metric", "", "Load Spike Index", scope="daily"),
    MetricDef("monotony", "load", "metric", "", "훈련 단조로움", scope="daily"),
    MetricDef("training_strain", "load", "metric", "", "훈련 스트레인", scope="daily"),
    MetricDef("rtti", "load", "metric", "%", "달리기 내성 지수 (RTTI)", scope="daily"),
    # weekly load
    MetricDef("tids", "load", "metric", "", "Training Intensity Distribution Score", scope="weekly"),
    MetricDef("adti", "load", "metric", "", "Aerobic Decoupling Trend Index", scope="weekly"),

    # ── efficiency ──
    MetricDef("efficiency_factor", "efficiency", "metric", "", "Efficiency Factor (NGP/HR)",
              aliases={"intervals": "icu_efficiency_factor"}),
    MetricDef("aerobic_decoupling", "efficiency", "metric", "%", "Aerobic Decoupling (%)",
              aliases={"intervals": "icu_decoupling"}),
    MetricDef("variability_index", "efficiency", "metric", "", "Variability Index (NP/AP)"),
    MetricDef("pace_variation", "efficiency", "metric", "", "Pace Variation",
              aliases={"intervals": "pace_variation"}),
    MetricDef("aerobic_decoupling_rp", "efficiency", "metric", "%", "RunPulse 유산소 분리"),
    MetricDef("efficiency_factor_rp", "efficiency", "metric", "", "RunPulse 효율 계수 (EF)"),
    MetricDef("teroi", "efficiency", "metric", "", "TEROI (훈련 효과 ROI)"),
    MetricDef("tpdi", "efficiency", "metric", "%", "TPDI (실내/실외 격차 지수)"),
    MetricDef("rec", "efficiency", "metric", "", "REC (통합 러닝 효율성)", scope="daily"),

    # ── capacity (체력/역량) ──
    MetricDef("vo2max_activity", "capacity", "metric", "ml/kg/min", "활동별 VO2Max 추정치",
              aliases={"garmin": "vO2MaxValue"}),
    MetricDef("vdot", "capacity", "metric", "", "Jack Daniels VDOT"),
    MetricDef("gap", "capacity", "metric", "sec/km", "Grade Adjusted Pace",
              aliases={"intervals": "icu_gap", "garmin": "avgGradeAdjustedSpeed"}),
    MetricDef("endurance_score", "capacity", "metric", "", "Garmin 지구력 점수",
              aliases={"garmin": "enduranceScore"}),
    MetricDef("effective_vo2max", "capacity", "metric", "ml/kg/min", "Runalyze eVO2Max",
              aliases={"runalyze": "effective_vo2max"}),
    MetricDef("lactate_threshold_hr", "capacity", "metric", "bpm", "젖산 역치 심박수",
              aliases={"garmin": "lactateThresholdBpm"}),
    MetricDef("lactate_threshold_speed", "capacity", "metric", "m/s", "젖산 역치 속도",
              aliases={"garmin": "lactateThresholdSpeed"}),
    MetricDef("gap_rp", "capacity", "metric", "sec/km", "RunPulse GAP (경사 보정 페이스)"),
    MetricDef("runpulse_vdot", "capacity", "metric", "", "RunPulse VDOT (Daniels)"),
    MetricDef("fearp", "capacity", "metric", "sec/km", "Field-Equivalent Adjusted Running Pace"),
    MetricDef("critical_power", "capacity", "metric", "W", "Critical Power (CP)", scope="daily"),
    MetricDef("eftp", "capacity", "metric", "sec/km", "eFTP (역치 페이스)", scope="daily"),
    MetricDef("vdot_adj", "capacity", "metric", "", "VDOT 보정", scope="daily"),
    MetricDef("marathon_shape", "capacity", "metric", "%", "Marathon Shape (훈련 완성도)", scope="daily"),
    MetricDef("sapi", "capacity", "metric", "", "SAPI (계절 성과 비교)", scope="daily"),
    MetricDef("rri", "capacity", "metric", "", "RRI (레이스 준비도)", scope="daily"),
    MetricDef("di", "capacity", "metric", "", "Durability Index", scope="weekly"),

    # ── prediction ──
    MetricDef("predicted_5k_sec", "prediction", "metric", "sec", "Garmin 5K 예측"),
    MetricDef("predicted_10k_sec", "prediction", "metric", "sec", "Garmin 10K 예측"),
    MetricDef("predicted_half_sec", "prediction", "metric", "sec", "Garmin 하프 예측"),
    MetricDef("predicted_full_sec", "prediction", "metric", "sec", "Garmin 마라톤 예측"),
    MetricDef("race_pred_5k_sec", "prediction", "metric", "sec", "5K 예측 기록", scope="daily",
              aliases={"garmin": "raceTime5K", "runalyze": "prediction_5k"}),
    MetricDef("race_pred_10k_sec", "prediction", "metric", "sec", "10K 예측 기록", scope="daily",
              aliases={"garmin": "raceTime10K", "runalyze": "prediction_10k"}),
    MetricDef("race_pred_half_sec", "prediction", "metric", "sec", "하프마라톤 예측 기록", scope="daily",
              aliases={"garmin": "raceTimeHalf", "runalyze": "prediction_half"}),
    MetricDef("race_pred_marathon_sec", "prediction", "metric", "sec", "마라톤 예측 기록", scope="daily",
              aliases={"garmin": "raceTimeMarathon", "runalyze": "prediction_marathon"}),
    MetricDef("darp_5k_sec", "prediction", "metric", "sec", "DARP 5K 예측", scope="daily"),
    MetricDef("darp_10k_sec", "prediction", "metric", "sec", "DARP 10K 예측", scope="daily"),
    MetricDef("darp_half_sec", "prediction", "metric", "sec", "DARP 하프 예측", scope="daily"),
    MetricDef("darp_marathon_sec", "prediction", "metric", "sec", "DARP 마라톤 예측", scope="daily"),

    # ── sleep (metric_store 보충) ──
    MetricDef("sleep_deep_sec", "sleep", "metric", "sec", "깊은 수면 시간", scope="daily",
              aliases={"garmin": "deepSleepSeconds"}),
    MetricDef("sleep_light_sec", "sleep", "metric", "sec", "얕은 수면 시간", scope="daily",
              aliases={"garmin": "lightSleepSeconds"}),
    MetricDef("sleep_rem_sec", "sleep", "metric", "sec", "REM 수면 시간", scope="daily",
              aliases={"garmin": "remSleepSeconds"}),
    MetricDef("sleep_awake_sec", "sleep", "metric", "sec", "깨어있던 시간", scope="daily",
              aliases={"garmin": "awakeSleepSeconds"}),
    MetricDef("avg_spo2", "sleep", "metric", "%", "평균 SpO2", scope="daily",
              aliases={"garmin": "averageSpO2"}),
    MetricDef("min_spo2", "sleep", "metric", "%", "최저 SpO2", scope="daily",
              aliases={"garmin": "lowestSpO2"}),
    MetricDef("avg_respiration_sleep", "sleep", "metric", "brpm", "수면 중 평균 호흡수", scope="daily",
              aliases={"garmin": "averageRespiration"}),
    MetricDef("sleep_deep_score", "sleep", "metric", "", "깊은 수면 점수", scope="daily"),
    MetricDef("sleep_rem_score", "sleep", "metric", "", "REM 수면 점수", scope="daily"),
    MetricDef("sleep_recovery_score", "sleep", "metric", "", "수면 회복 점수", scope="daily"),

    # ── stress (상세) ──
    MetricDef("stress_high_duration_sec", "stress", "metric", "sec", "고스트레스 시간", scope="daily",
              aliases={"garmin": "highStressDuration"}),
    MetricDef("stress_medium_duration_sec", "stress", "metric", "sec", "중스트레스 시간", scope="daily",
              aliases={"garmin": "mediumStressDuration"}),
    MetricDef("stress_low_duration_sec", "stress", "metric", "sec", "저스트레스 시간", scope="daily",
              aliases={"garmin": "lowStressDuration"}),
    MetricDef("stress_rest_duration_sec", "stress", "metric", "sec", "휴식 시간", scope="daily",
              aliases={"garmin": "restStressDuration"}),

    # ── readiness ──
    MetricDef("training_readiness_score", "readiness", "metric", "", "Garmin 훈련 준비도 점수", scope="daily",
              aliases={"garmin": "score"}),
    MetricDef("training_readiness_level", "readiness", "metric", "", "Garmin 훈련 준비도 레벨", scope="daily",
              aliases={"garmin": "level"}),
    MetricDef("training_readiness_hrv_factor", "readiness", "metric", "%", "훈련 준비도 HRV 요인", scope="daily",
              aliases={"garmin": "hrvFactorPercent"}),
    MetricDef("training_readiness_sleep_factor", "readiness", "metric", "%", "훈련 준비도 수면 요인", scope="daily",
              aliases={"garmin": "sleepScoreFactorPercent"}),
    MetricDef("training_readiness_recovery_factor", "readiness", "metric", "%", "훈련 준비도 회복 요인", scope="daily",
              aliases={"garmin": "recoveryFactorPercent"}),
    MetricDef("crs", "readiness", "metric", "", "CRS (복합 준비도 게이트)", scope="daily"),
    MetricDef("utrs", "readiness", "metric", "", "Unified Training Readiness Score", scope="daily"),
    MetricDef("cirs", "readiness", "metric", "", "Composite Injury Risk Score", scope="daily"),
    MetricDef("rmr", "readiness", "metric", "json", "Runner Maturity Radar", scope="weekly"),

    # ── weather (metric_store) ──
    MetricDef("weather_temp_c", "weather", "metric", "°C", "기온"),
    MetricDef("weather_humidity_pct", "weather", "metric", "%", "습도"),
    MetricDef("weather_dew_point_c", "weather", "metric", "°C", "이슬점"),
    MetricDef("weather_wind_speed_ms", "weather", "metric", "m/s", "풍속"),
    MetricDef("weather_wind_direction_deg", "weather", "metric", "°", "풍향"),
    MetricDef("weather_pressure_hpa", "weather", "metric", "hPa", "기압"),
    MetricDef("weather_condition", "weather", "metric", "", "날씨 상태 텍스트"),

    # ── body (metric_store) ──
    MetricDef("body_battery_diff", "body", "metric", "", "활동 중 Body Battery 변화",
              aliases={"garmin": "differenceBodyBattery"}),
    MetricDef("calories_active", "body", "metric", "kcal", "활동 칼로리"),
    MetricDef("calories_total", "body", "metric", "kcal", "총 칼로리"),
    MetricDef("floors_climbed", "body", "metric", "count", "오른 층수"),
    MetricDef("intensity_minutes", "body", "metric", "min", "강도 활동 분"),
    MetricDef("respiration_rate", "body", "metric", "brpm", "호흡수"),
    MetricDef("spo2_avg", "body", "metric", "%", "평균 SpO2"),
    MetricDef("water_estimated_ml", "body", "metric", "ml", "추정 수분 소모량",
              aliases={"garmin": "waterEstimated"}),

    # ── meta (metric_store) ──
    MetricDef("source_event_type", "meta", "metric", "", "소스 원본 이벤트 분류",
              aliases={"garmin": "eventType", "strava": "workout_type"}),
    MetricDef("source_sport_type", "meta", "metric", "", "소스 원본 스포츠 하위 분류",
              aliases={"garmin": "sportType", "strava": "sport_type"}),
    MetricDef("achievement_count", "meta", "metric", "", "Strava 업적 수",
              aliases={"strava": "achievement_count"}),
    MetricDef("kudos_count", "meta", "metric", "", "Strava Kudos",
              aliases={"strava": "kudos_count"}),
    MetricDef("pr_count", "meta", "metric", "", "Strava PR 수",
              aliases={"strava": "pr_count"}),
    MetricDef("timezone_offset", "meta", "metric", "", "타임존 오프셋"),
    MetricDef("workout_type_classified", "meta", "metric", "", "RunPulse 워크아웃 분류"),

    # ── athlete ──
    MetricDef("max_hr_setting", "athlete", "metric", "bpm", "설정 최대 심박수", scope="athlete"),
    MetricDef("rest_hr_setting", "athlete", "metric", "bpm", "설정 안정시 심박수", scope="athlete"),
    MetricDef("threshold_pace_setting", "athlete", "metric", "sec/km", "설정 역치 페이스", scope="athlete"),
    MetricDef("weight_setting", "athlete", "metric", "kg", "설정 체중", scope="athlete"),
    MetricDef("ftp_setting", "athlete", "metric", "W", "설정 FTP", scope="athlete"),
    MetricDef("lthr_setting", "athlete", "metric", "bpm", "설정 LTHR", scope="athlete"),
]


# ─────────────────────────────────────────────────────────────────────────────
# 인덱스 빌드 (모듈 로드 시 1회)
# ─────────────────────────────────────────────────────────────────────────────

METRIC_REGISTRY: dict[str, MetricDef] = {}
_ALIAS_MAP: dict[str, str] = {}  # "source::rawName" → canonical_name

for _md in _DEFINITIONS:
    METRIC_REGISTRY[_md.name] = _md
    for _src, _raw in _md.aliases.items():
        _ALIAS_MAP[f"{_src}::{_raw}"] = _md.name


# ─────────────────────────────────────────────────────────────────────────────
# 공개 API
# ─────────────────────────────────────────────────────────────────────────────

def canonicalize(raw_name: str, source: str | None = None) -> tuple[str, str]:
    """소스 raw 필드명 → (정규 이름, 카테고리).

    1) source가 있으면 alias map 먼저 조회
    2) raw_name이 정규 이름이면 직접 반환
    3) 못 찾으면 source가 있으면 "{source}__{raw_name}", 없으면 raw_name 그대로 반환
    """
    if source:
        key = f"{source}::{raw_name}"
        if key in _ALIAS_MAP:
            canonical = _ALIAS_MAP[key]
            return canonical, METRIC_REGISTRY[canonical].category
    if raw_name in METRIC_REGISTRY:
        return raw_name, METRIC_REGISTRY[raw_name].category
    unmapped_name = f"{source}__{raw_name}" if source else raw_name
    return unmapped_name, "_unmapped"


def get_metric(name: str) -> Optional[MetricDef]:
    """정규 이름으로 MetricDef 조회."""
    return METRIC_REGISTRY.get(name)


def list_by_category(category: str) -> list[MetricDef]:
    """카테고리에 속하는 모든 MetricDef 반환."""
    return [md for md in METRIC_REGISTRY.values() if md.category == category]


def list_by_scope(scope: str) -> list[MetricDef]:
    """스코프에 속하는 모든 MetricDef 반환."""
    return [md for md in METRIC_REGISTRY.values() if md.scope == scope]


def list_by_storage(storage: str) -> list[MetricDef]:
    """저장 위치별 모든 MetricDef 반환."""
    return [md for md in METRIC_REGISTRY.values() if md.storage == storage]


# 하위 호환 alias
get_by_category = list_by_category
get_by_scope = list_by_scope
get_by_storage = list_by_storage
