"""메트릭 정의 — Layer 2 hr~load 도메인. metric_registry가 합쳐서 사용."""
from __future__ import annotations

from src.utils.metric_def import MetricDef

LOAD_DEFS: list[MetricDef] = [
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

    # ── volume (activity) ──
    # activity_summaries → metric_store 이동 (Phase 5-G)
    MetricDef("calories", "volume", "metric", "kcal", "소모 칼로리 (활동)",
              scope="activity",
              aliases={
                  "garmin": "calories",
                  "strava": "calories",
                  "intervals": "calories",
                  "runalyze": "kcal",
              }),
    MetricDef("normalized_power", "power", "metric", "W", "정규화 파워 (NP)",
              scope="activity",
              aliases={
                  "garmin": "normPower",
                  "strava": "weighted_average_watts",
                  "intervals": "icu_weighted_avg_watts",
              }),

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
    # activity_summaries → metric_store 이동 (Phase 5-G)
    MetricDef("training_load", "load", "metric", "score", "훈련 부하 (소스별)",
              scope="activity",
              aliases={
                  "garmin": "activityTrainingLoad",
                  "intervals": "icu_training_load",
                  "runalyze": "trimp",
              }),
    MetricDef("suffer_score", "load", "metric", "score", "Strava Suffer Score",
              scope="activity",
              aliases={"strava": "suffer_score"}),
    MetricDef("trimp", "load", "metric", "score", "TRIMP (Banister)",
              aliases={"intervals": "icu_trimp"}),
    MetricDef("hrss", "load", "metric", "score", "HR Stress Score",
              aliases={"intervals": "icu_hrss"}),
    MetricDef("rtss", "load", "metric", "score", "Running TSS (rTSS)"),
    MetricDef("intensity_factor", "load", "metric", "", "Intensity Factor (IF)",
              aliases={"intervals": "icu_intensity"}),
    MetricDef("training_stress_score", "load", "metric", "score", "TSS",
              aliases={"garmin": "trainingStressScore"}),
    MetricDef("training_effect_aerobic", "load", "metric", "", "유산소 훈련 효과",
              scope="activity",
              aliases={"garmin": "aerobicTrainingEffect"}),
    MetricDef("training_effect_anaerobic", "load", "metric", "", "무산소 훈련 효과",
              scope="activity",
              aliases={"garmin": "anaerobicTrainingEffect"}),
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
    MetricDef("running_tolerance_load", "load", "metric", "score", "러닝 내성 훈련 부하 (Garmin)", scope="daily"),
    MetricDef("running_tolerance_optimal_min", "load", "metric", "score", "러닝 내성 최적 부하 하한 (Garmin)", scope="daily"),
    MetricDef("running_tolerance_optimal_max", "load", "metric", "score", "러닝 내성 최적 부하 상한 (Garmin)", scope="daily"),
    MetricDef("running_tolerance_score", "load", "metric", "score", "러닝 내성 점수 (Garmin)", scope="daily"),
    # weekly load
    MetricDef("tids", "load", "metric", "", "Training Intensity Distribution Score", scope="weekly"),
    MetricDef("adti", "load", "metric", "", "Aerobic Decoupling Trend Index", scope="weekly"),
]
