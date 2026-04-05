"""RunPulse 메트릭 레지스트리 v0.3

모든 메트릭의 정규 이름(canonical name), 카테고리, 단위, 소스별 별칭을 정의합니다.
Extractor가 소스 raw 필드명을 정규 이름으로 변환할 때 이 레지스트리를 참조합니다.

사용법:
    from src.utils.metric_registry import canonicalize, get_metric, METRIC_REGISTRY

    name, category = canonicalize("aerobicTrainingEffect", source="garmin")
    # → ("training_effect_aerobic", "training_effect")

    metric = get_metric("trimp")
    # → MetricDef(name="trimp", category="training_load", ...)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


# ─────────────────────────────────────────────────────────────────────────────
# 데이터 구조
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class MetricDef:
    """메트릭 정의."""
    name: str                                 # 정규 이름 (canonical)
    category: str                             # 의미적 그룹
    unit: str = ""                            # 표시 단위
    description: str = ""                     # 한국어 설명
    scope: str = "activity"                   # 'activity' | 'daily' | 'weekly' | 'athlete'
    aliases: dict[str, str] = field(default_factory=dict)
    # aliases = {"garmin": "rawFieldName", "strava": "raw_name", ...}


# ─────────────────────────────────────────────────────────────────────────────
# 메트릭 정의 — 카테고리별 정리
# ─────────────────────────────────────────────────────────────────────────────

_DEFINITIONS: list[MetricDef] = [
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # HR Zone 분포
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    MetricDef("hr_zone_1_sec", "hr_zone", "sec", "HR Zone 1 체류 시간",
              aliases={"garmin": "hrTimeInZone_0"}),
    MetricDef("hr_zone_2_sec", "hr_zone", "sec", "HR Zone 2 체류 시간",
              aliases={"garmin": "hrTimeInZone_1"}),
    MetricDef("hr_zone_3_sec", "hr_zone", "sec", "HR Zone 3 체류 시간",
              aliases={"garmin": "hrTimeInZone_2"}),
    MetricDef("hr_zone_4_sec", "hr_zone", "sec", "HR Zone 4 체류 시간",
              aliases={"garmin": "hrTimeInZone_3"}),
    MetricDef("hr_zone_5_sec", "hr_zone", "sec", "HR Zone 5 체류 시간",
              aliases={"garmin": "hrTimeInZone_4"}),
    MetricDef("hr_zones_detail", "hr_zone", "json", "HR Zone 전체 상세",
              aliases={"garmin": "hrTimeInZone"}),

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Power Zone 분포
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    MetricDef("power_zone_1_sec", "power_zone", "sec", "Power Zone 1 체류 시간",
              aliases={"garmin": "powerTimeInZone_0"}),
    MetricDef("power_zone_2_sec", "power_zone", "sec", "Power Zone 2 체류 시간",
              aliases={"garmin": "powerTimeInZone_1"}),
    MetricDef("power_zone_3_sec", "power_zone", "sec", "Power Zone 3 체류 시간",
              aliases={"garmin": "powerTimeInZone_2"}),
    MetricDef("power_zone_4_sec", "power_zone", "sec", "Power Zone 4 체류 시간",
              aliases={"garmin": "powerTimeInZone_3"}),
    MetricDef("power_zone_5_sec", "power_zone", "sec", "Power Zone 5 체류 시간",
              aliases={"garmin": "powerTimeInZone_4"}),

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Training Load 계열
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    MetricDef("trimp", "rp_load", "score", "TRIMP (Banister)",
              aliases={"intervals": "icu_trimp"}),
    MetricDef("hrss", "rp_load", "score", "HR Stress Score",
              aliases={"intervals": "icu_hrss"}),
    MetricDef("rtss", "training_load", "score", "Running TSS (rTSS)"),
    MetricDef("intensity_factor", "training_load", "", "Intensity Factor (IF)",
              aliases={"intervals": "icu_intensity"}),
    MetricDef("training_stress_score", "training_load", "score", "TSS",
              aliases={"garmin": "trainingStressScore"}),

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Efficiency & Decoupling
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    MetricDef("efficiency_factor", "efficiency", "", "Efficiency Factor (NGP/HR)",
              aliases={"intervals": "icu_efficiency_factor"}),
    MetricDef("aerobic_decoupling", "efficiency", "%", "Aerobic Decoupling (%)",
              aliases={"intervals": "icu_decoupling"}),
    MetricDef("variability_index", "efficiency", "", "Variability Index (NP/AP)"),
    MetricDef("pace_variation", "efficiency", "", "Pace Variation",
              aliases={"intervals": "pace_variation"}),

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Running Dynamics (metric_store용 — 상세/보충)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    MetricDef("ground_contact_balance", "running_dynamics", "%", "지면 접촉 밸런스 (L/R)",
              aliases={"garmin": "avgGroundContactBalance"}),
    MetricDef("avg_respiration_rate", "running_dynamics", "brpm", "평균 호흡수",
              aliases={"garmin": "avgRespirationRate"}),

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Fitness Indicators (activity scope)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    MetricDef("vo2max_activity", "fitness", "ml/kg/min", "활동별 VO2Max 추정치",
              aliases={"garmin": "vO2MaxValue"}),
    MetricDef("vdot", "fitness", "", "Jack Daniels VDOT"),
    MetricDef("gap", "fitness", "sec/km", "Grade Adjusted Pace",
              aliases={"intervals": "icu_gap", "garmin": "avgGradeAdjustedSpeed"}),
    MetricDef("performance_condition", "fitness", "", "Garmin 퍼포먼스 컨디션",
              aliases={"garmin": "performanceCondition"}),
    MetricDef("endurance_score", "fitness", "", "Garmin 지구력 점수",
              aliases={"garmin": "enduranceScore"}),

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Lactate Threshold
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    MetricDef("lactate_threshold_hr", "threshold", "bpm", "젖산 역치 심박수",
              aliases={"garmin": "lactateThresholdBpm"}),
    MetricDef("lactate_threshold_speed", "threshold", "m/s", "젖산 역치 속도",
              aliases={"garmin": "lactateThresholdSpeed"}),

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Weather / Environment
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    MetricDef("weather_temp_c", "weather", "°C", "기온"),
    MetricDef("weather_humidity_pct", "weather", "%", "습도"),
    MetricDef("weather_dew_point_c", "weather", "°C", "이슬점"),
    MetricDef("weather_wind_speed_ms", "weather", "m/s", "풍속"),
    MetricDef("weather_pressure_hpa", "weather", "hPa", "기압"),
    MetricDef("weather_condition", "weather", "", "날씨 상태 텍스트"),

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Nutrition / General (activity scope)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    MetricDef("water_estimated_ml", "nutrition", "ml", "추정 수분 소모량",
              aliases={"garmin": "waterEstimated"}),
    MetricDef("body_battery_diff", "general", "", "활동 중 Body Battery 변화",
              aliases={"garmin": "differenceBodyBattery"}),
    MetricDef("intensity_mins_moderate", "general", "min", "중강도 활동 시간",
              aliases={"garmin": "moderateIntensityMinutes"}),
    MetricDef("intensity_mins_vigorous", "general", "min", "고강도 활동 시간",
              aliases={"garmin": "vigorousIntensityMinutes"}),
    MetricDef("steps_activity", "general", "", "활동 중 걸음수",
              aliases={"garmin": "steps"}),

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Strava-specific
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    MetricDef("kudos_count", "social", "", "Strava Kudos",
              aliases={"strava": "kudos_count"}),
    MetricDef("achievement_count", "social", "", "Strava 업적 수",
              aliases={"strava": "achievement_count"}),
    MetricDef("pr_count", "social", "", "Strava PR 수",
              aliases={"strava": "pr_count"}),

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Intervals.icu specific
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    MetricDef("icu_ftp", "power", "W", "Intervals FTP",
              aliases={"intervals": "icu_ftp"}),
    MetricDef("icu_w_prime", "power", "kJ", "Intervals W'",
              aliases={"intervals": "icu_w_prime"}),
    MetricDef("icu_rpe", "perception", "", "Intervals RPE",
              aliases={"intervals": "icu_rpe"}),
    MetricDef("icu_feel", "perception", "", "Intervals Feel",
              aliases={"intervals": "icu_feel"}),

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Runalyze specific
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    MetricDef("effective_vo2max", "fitness", "ml/kg/min", "Runalyze eVO2Max",
              aliases={"runalyze": "effective_vo2max"}),
    MetricDef("marathon_shape", "fitness", "%", "Runalyze Marathon Shape",
              aliases={"runalyze": "marathon_shape"}),

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Source workout/event type (원본 분류)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    MetricDef("source_event_type", "classification", "", "소스 원본 이벤트 분류",
              aliases={"garmin": "eventType", "strava": "workout_type"}),
    MetricDef("source_sport_type", "classification", "", "소스 원본 스포츠 하위 분류",
              aliases={"garmin": "sportType", "strava": "sport_type"}),

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Daily Wellness (metric_store 보충 — core는 daily_wellness 테이블)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    MetricDef("sleep_deep_sec", "sleep", "sec", "깊은 수면 시간", scope="daily",
              aliases={"garmin": "deepSleepSeconds"}),
    MetricDef("sleep_light_sec", "sleep", "sec", "얕은 수면 시간", scope="daily",
              aliases={"garmin": "lightSleepSeconds"}),
    MetricDef("sleep_rem_sec", "sleep", "sec", "REM 수면 시간", scope="daily",
              aliases={"garmin": "remSleepSeconds"}),
    MetricDef("sleep_awake_sec", "sleep", "sec", "깨어있던 시간", scope="daily",
              aliases={"garmin": "awakeSleepSeconds"}),
    MetricDef("avg_spo2", "sleep", "%", "평균 SpO2", scope="daily",
              aliases={"garmin": "averageSpO2"}),
    MetricDef("min_spo2", "sleep", "%", "최저 SpO2", scope="daily",
              aliases={"garmin": "lowestSpO2"}),
    MetricDef("avg_respiration_sleep", "sleep", "brpm", "수면 중 평균 호흡수", scope="daily",
              aliases={"garmin": "averageRespiration"}),

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Daily Stress 상세
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    MetricDef("stress_high_duration_sec", "stress", "sec", "고스트레스 시간", scope="daily",
              aliases={"garmin": "highStressDuration"}),
    MetricDef("stress_medium_duration_sec", "stress", "sec", "중스트레스 시간", scope="daily",
              aliases={"garmin": "mediumStressDuration"}),
    MetricDef("stress_low_duration_sec", "stress", "sec", "저스트레스 시간", scope="daily",
              aliases={"garmin": "lowStressDuration"}),
    MetricDef("stress_rest_duration_sec", "stress", "sec", "휴식 시간", scope="daily",
              aliases={"garmin": "restStressDuration"}),

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Training Readiness (Garmin)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    MetricDef("training_readiness_score", "readiness", "", "Garmin 훈련 준비도 점수", scope="daily",
              aliases={"garmin": "score"}),
    MetricDef("training_readiness_level", "readiness", "", "Garmin 훈련 준비도 레벨", scope="daily",
              aliases={"garmin": "level"}),
    MetricDef("training_readiness_hrv_factor", "readiness", "%", "훈련 준비도 HRV 요인", scope="daily",
              aliases={"garmin": "hrvFactorPercent"}),
    MetricDef("training_readiness_sleep_factor", "readiness", "%", "훈련 준비도 수면 요인", scope="daily",
              aliases={"garmin": "sleepScoreFactorPercent"}),
    MetricDef("training_readiness_recovery_factor", "readiness", "%", "훈련 준비도 회복 요인", scope="daily",
              aliases={"garmin": "recoveryFactorPercent"}),

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Race Predictions (Garmin / Runalyze)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    MetricDef("race_pred_5k_sec", "prediction", "sec", "5K 예측 기록", scope="daily",
              aliases={"garmin": "raceTime5K", "runalyze": "prediction_5k"}),
    MetricDef("race_pred_10k_sec", "prediction", "sec", "10K 예측 기록", scope="daily",
              aliases={"garmin": "raceTime10K", "runalyze": "prediction_10k"}),
    MetricDef("race_pred_half_sec", "prediction", "sec", "하프마라톤 예측 기록", scope="daily",
              aliases={"garmin": "raceTimeHalf", "runalyze": "prediction_half"}),
    MetricDef("race_pred_marathon_sec", "prediction", "sec", "마라톤 예측 기록", scope="daily",
              aliases={"garmin": "raceTimeMarathon", "runalyze": "prediction_marathon"}),

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # PMC (daily_fitness에도 있지만, metric_store에서 provider별 비교용)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    MetricDef("ctl", "rp_load", "", "Chronic Training Load", scope="daily"),
    MetricDef("atl", "rp_load", "", "Acute Training Load", scope="daily"),
    MetricDef("tsb", "rp_load", "", "Training Stress Balance", scope="daily"),
    MetricDef("ramp_rate", "rp_load", "", "CTL 증가율", scope="daily"),

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # RunPulse Computed (2차 메트릭)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    MetricDef("utrs", "rp_readiness", "", "Unified Training Readiness Score", scope="daily"),
    MetricDef("cirs", "rp_risk", "", "Composite Injury Risk Score", scope="daily"),
    MetricDef("acwr", "rp_load", "", "Acute:Chronic Workload Ratio", scope="daily"),
    MetricDef("lsi", "rp_load", "", "Load Spike Index", scope="daily"),
    MetricDef("monotony", "rp_load", "", "훈련 단조로움", scope="daily"),
    MetricDef("training_strain", "rp_load", "", "훈련 스트레인", scope="daily"),

    MetricDef("fearp", "rp_performance", "sec/km", "Field-Equivalent Adjusted Running Pace"),
    MetricDef("darp_5k_sec", "rp_performance", "sec", "DARP 5K 예측", scope="daily"),
    MetricDef("darp_10k_sec", "rp_performance", "sec", "DARP 10K 예측", scope="daily"),
    MetricDef("darp_half_sec", "rp_performance", "sec", "DARP 하프 예측", scope="daily"),
    MetricDef("darp_marathon_sec", "rp_performance", "sec", "DARP 마라톤 예측", scope="daily"),
    MetricDef("di", "rp_endurance", "", "Durability Index", scope="weekly"),
    MetricDef("rmr", "rp_recovery", "json", "Runner Maturity Radar", scope="weekly"),

    MetricDef("tids", "rp_distribution", "", "Training Intensity Distribution Score", scope="weekly"),
    MetricDef("adti", "rp_trend", "", "Aerobic Decoupling Trend Index", scope="weekly"),


    # ── Phase 4 기존 calculator (registry 미등록분) ──
    MetricDef("aerobic_decoupling_rp", "rp_efficiency", "%", "RunPulse 유산소 분리"),
    MetricDef("gap_rp", "rp_performance", "sec/km", "RunPulse GAP (경사 보정 페이스)"),
    MetricDef("runpulse_vdot", "rp_performance", "", "RunPulse VDOT (Daniels)"),
    MetricDef("efficiency_factor_rp", "rp_efficiency", "", "RunPulse 효율 계수 (EF)"),

    # ── Phase 4 v0.2 포팅 메트릭 (13개) ──
    MetricDef("relative_effort", "rp_load", "AU", "Relative Effort (심박존 기반)"),
    MetricDef("wlei", "rp_load", "AU", "WLEI (날씨 가중 노력 지수)"),
    MetricDef("teroi", "rp_trend", "", "TEROI (훈련 효과 ROI)"),
    MetricDef("tpdi", "rp_trend", "%", "TPDI (실내/실외 격차 지수)"),
    MetricDef("rec", "rp_efficiency", "", "REC (통합 러닝 효율성)", scope="daily"),
    MetricDef("rtti", "rp_load", "%", "RTTI (달리기 내성 지수)", scope="daily"),
    MetricDef("critical_power", "rp_performance", "W", "Critical Power (CP)", scope="daily"),
    MetricDef("eftp", "rp_performance", "sec/km", "eFTP (역치 페이스)", scope="daily"),
    MetricDef("sapi", "rp_performance", "", "SAPI (계절 성과 비교)", scope="daily"),
    MetricDef("rri", "rp_performance", "", "RRI (레이스 준비도)", scope="daily"),
    MetricDef("vdot_adj", "rp_performance", "", "VDOT 보정", scope="daily"),
    MetricDef("marathon_shape", "rp_performance", "%", "Marathon Shape (훈련 완성도)", scope="daily"),
    MetricDef("crs", "rp_readiness", "", "CRS (복합 준비도 게이트)", scope="daily"),

    MetricDef("workout_type_classified", "rp_classification", "", "RunPulse 워크아웃 분류"),

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Athlete-scope
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    MetricDef("max_hr_setting", "athlete", "bpm", "설정 최대 심박수", scope="athlete"),
    MetricDef("rest_hr_setting", "athlete", "bpm", "설정 안정시 심박수", scope="athlete"),
    MetricDef("threshold_pace_setting", "athlete", "sec/km", "설정 역치 페이스", scope="athlete"),
    MetricDef("weight_setting", "athlete", "kg", "설정 체중", scope="athlete"),
    MetricDef("ftp_setting", "athlete", "W", "설정 FTP", scope="athlete"),
    MetricDef("lthr_setting", "athlete", "bpm", "설정 LTHR", scope="athlete"),

    # ── 추가 메트릭 정의 (기존 _DEFINITIONS 리스트에 append) ──

    # --- Running Dynamics 확장 ---
    MetricDef("ground_contact_time_balance", "dynamics", "activity", "%", ["gct_balance", "ground_contact_balance"]),
    MetricDef("stance_time", "dynamics", "activity", "ms", ["ground_contact_time_left", "ground_contact_time_right"]),
    MetricDef("leg_spring_stiffness", "dynamics", "activity", "kN/m", ["lss"]),
    MetricDef("form_power", "dynamics", "activity", "W", ["running_form_power"]),
    MetricDef("impact_loading_rate", "dynamics", "activity", "BW/s", ["ilr"]),

    # --- HR Zone 확장 ---
    MetricDef("hr_zone_1_sec", "hr_zone", "activity", "s", ["time_in_zone_1", "hr_z1_time"]),
    MetricDef("hr_zone_2_sec", "hr_zone", "activity", "s", ["time_in_zone_2", "hr_z2_time"]),
    MetricDef("hr_zone_3_sec", "hr_zone", "activity", "s", ["time_in_zone_3", "hr_z3_time"]),
    MetricDef("hr_zone_4_sec", "hr_zone", "activity", "s", ["time_in_zone_4", "hr_z4_time"]),
    MetricDef("hr_zone_5_sec", "hr_zone", "activity", "s", ["time_in_zone_5", "hr_z5_time"]),
    MetricDef("hr_zone_1_pct", "hr_zone", "activity", "%", ["pct_hr_zone_1"]),
    MetricDef("hr_zone_2_pct", "hr_zone", "activity", "%", ["pct_hr_zone_2"]),
    MetricDef("hr_zone_3_pct", "hr_zone", "activity", "%", ["pct_hr_zone_3"]),
    MetricDef("hr_zone_4_pct", "hr_zone", "activity", "%", ["pct_hr_zone_4"]),
    MetricDef("hr_zone_5_pct", "hr_zone", "activity", "%", ["pct_hr_zone_5"]),

    # --- Power Zone ---
    MetricDef("power_zone_1_sec", "power_zone", "activity", "s", ["time_in_power_zone_1"]),
    MetricDef("power_zone_2_sec", "power_zone", "activity", "s", ["time_in_power_zone_2"]),
    MetricDef("power_zone_3_sec", "power_zone", "activity", "s", ["time_in_power_zone_3"]),
    MetricDef("power_zone_4_sec", "power_zone", "activity", "s", ["time_in_power_zone_4"]),
    MetricDef("power_zone_5_sec", "power_zone", "activity", "s", ["time_in_power_zone_5"]),

    # --- Pace splits ---
    MetricDef("pace_1k", "pace", "activity", "s/km", ["split_1k_pace"]),
    MetricDef("pace_5k", "pace", "activity", "s/km", ["split_5k_pace"]),
    MetricDef("pace_10k", "pace", "activity", "s/km", ["split_10k_pace"]),
    MetricDef("negative_split_ratio", "pace", "activity", "ratio", ["neg_split"]),

    # --- Wellness 확장 ---
    MetricDef("sleep_deep_sec", "sleep", "daily", "s", ["deep_sleep_duration", "deep_sleep_seconds"]),
    MetricDef("sleep_light_sec", "sleep", "daily", "s", ["light_sleep_duration", "light_sleep_seconds"]),
    MetricDef("sleep_rem_sec", "sleep", "daily", "s", ["rem_sleep_duration", "rem_sleep_seconds"]),
    MetricDef("sleep_awake_sec", "sleep", "daily", "s", ["awake_duration", "awake_seconds"]),
    MetricDef("respiration_rate", "wellness", "daily", "brpm", ["avg_respiration", "breathing_rate"]),
    MetricDef("spo2_avg", "wellness", "daily", "%", ["avg_spo2", "blood_oxygen"]),
    MetricDef("stress_avg", "wellness", "daily", "score", ["avg_stress_level", "stress_level"]),
    MetricDef("calories_active", "wellness", "daily", "kcal", ["active_calories"]),
    MetricDef("calories_total", "wellness", "daily", "kcal", ["total_calories"]),
    MetricDef("steps", "wellness", "daily", "count", ["daily_steps", "step_count"]),
    MetricDef("floors_climbed", "wellness", "daily", "count", ["floors"]),
    MetricDef("intensity_minutes", "wellness", "daily", "min", ["intensity_mins", "vigorous_minutes"]),

    # --- Training Load 확장 ---
    MetricDef("training_effect_aerobic", "training_load", "activity", "score", ["aerobic_te", "aerobic_training_effect"]),
    MetricDef("training_effect_anaerobic", "training_load", "activity", "score", ["anaerobic_te", "anaerobic_training_effect"]),
    MetricDef("training_load_peak", "training_load", "activity", "score", ["peak_training_load"]),
    MetricDef("performance_condition", "training_load", "activity", "score", ["perf_condition"]),

    # --- Race Prediction ---
    MetricDef("predicted_5k_sec", "prediction", "athlete", "s", ["race_pred_5k"]),
    MetricDef("predicted_10k_sec", "prediction", "athlete", "s", ["race_pred_10k"]),
    MetricDef("predicted_half_sec", "prediction", "athlete", "s", ["race_pred_half"]),
    MetricDef("predicted_full_sec", "prediction", "athlete", "s", ["race_pred_marathon"]),

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

# 카테고리 목록
METRIC_CATEGORIES: dict[str, str] = {
    "hr_zone": "심박 존 분포",
    "power_zone": "파워 존 분포",
    "training_load": "훈련 부하",
    "efficiency": "효율성",
    "running_dynamics": "러닝 다이내믹스",
    "fitness": "체력 지표",
    "threshold": "역치",
    "weather": "날씨/환경",
    "nutrition": "영양/수분",
    "general": "일반",
    "social": "소셜",
    "power": "파워",
    "perception": "체감/주관",
    "classification": "분류",
    "sleep": "수면 상세",
    "stress": "스트레스",
    "readiness": "훈련 준비도",
    "prediction": "레이스 예측",
    "pmc": "성과 관리 차트",
    "pace":        "페이스 / 스플릿",
    "dynamics": "러닝 다이내믹스 (확장)", 
    "wellness": "일일 웰니스", 
    "rp_readiness": "RunPulse 준비도",
    "rp_risk": "RunPulse 부상 위험",
    "rp_load": "RunPulse 부하 분석",
    "rp_performance": "RunPulse 퍼포먼스",
    "rp_classification": "RunPulse 분류",
    "rp_recovery": "RunPulse 회복",
    "rp_distribution": "RunPulse 훈련 분포",
    "rp_prediction": "RunPulse 예측",
    "rp_endurance": "RunPulse 지구력",
    "rp_trend": "RunPulse 추세 분석",
    "rp_efficiency": "RunPulse 효율성",
    "rp_distribution": "RunPulse 강도 분포",
    "rp_efficiency": "RunPulse 효율 분석",
    "rp_classification": "RunPulse 분류",
    "athlete": "선수 설정",
    "_unmapped": "미매핑 (정리 필요)",
}


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def canonicalize(raw_name: str, source: str | None = None) -> tuple[str, str]:
    """소스 raw 필드명 → (정규 이름, 카테고리).

    조회 순서:
    1. source::raw_name 별칭 매핑
    2. 정규 이름 직접 매칭
    3. 미등록 → ("{source}__{raw_name}", "_unmapped")
    """
    if source:
        key = f"{source}::{raw_name}"
        if key in _ALIAS_MAP:
            canonical = _ALIAS_MAP[key]
            return canonical, METRIC_REGISTRY[canonical].category

    if raw_name in METRIC_REGISTRY:
        return raw_name, METRIC_REGISTRY[raw_name].category

    unmapped = f"{source}__{raw_name}" if source else raw_name
    return unmapped, "_unmapped"


def get_metric(name: str) -> Optional[MetricDef]:
    """정규 이름으로 MetricDef 반환. 없으면 None."""
    return METRIC_REGISTRY.get(name)


def list_by_category(category: str) -> list[MetricDef]:
    """카테고리에 속하는 메트릭 목록."""
    return [md for md in METRIC_REGISTRY.values() if md.category == category]


def list_by_scope(scope: str) -> list[MetricDef]:
    """scope에 해당하는 메트릭 목록."""
    return [md for md in METRIC_REGISTRY.values() if md.scope == scope]


def list_unmapped_aliases() -> list[str]:
    """등록되지 않은 별칭 키 목록 (디버깅용)."""
    # 이건 runtime에는 빈 리스트. 실제 unmapped는 DB에서 확인.
    return []
