"""메트릭 정의 — Layer 1 (activity_summaries·daily_wellness 컬럼). metric_registry가 합쳐서 사용."""
from __future__ import annotations

from src.utils.metric_def import MetricDef

LAYER1_DEFS: list[MetricDef] = [

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
    MetricDef("workout_label", "meta", "activity_summary", "", "워크아웃 레이블"),
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
    MetricDef("hrv_5min_high", "hr", "metric", "ms", "HRV 야간 최고 5분", scope="daily",
              aliases={"garmin": "lastNight5MinHigh"}),
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
]
