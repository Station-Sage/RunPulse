-- ============================================================
-- RunPulse Superset Schema v2
-- Generated: 2026-03-24
-- Sources: Strava(101col), Garmin(95col+wellness), Intervals(86col), FIT(29+132+97)
-- ============================================================

PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

-- ============================================================
-- 1. activity_summaries 확장 (21 -> ~100)
-- ============================================================
ALTER TABLE activity_summaries ADD COLUMN name TEXT;
ALTER TABLE activity_summaries ADD COLUMN garmin_activity_id INTEGER;
ALTER TABLE activity_summaries ADD COLUMN strava_activity_id INTEGER;
ALTER TABLE activity_summaries ADD COLUMN intervals_activity_id TEXT;
ALTER TABLE activity_summaries ADD COLUMN device_id INTEGER;
ALTER TABLE activity_summaries ADD COLUMN device_name TEXT;
ALTER TABLE activity_summaries ADD COLUMN manufacturer TEXT;
ALTER TABLE activity_summaries ADD COLUMN sport_type TEXT;
ALTER TABLE activity_summaries ADD COLUMN sub_type TEXT;
ALTER TABLE activity_summaries ADD COLUMN moving_time_sec INTEGER;
ALTER TABLE activity_summaries ADD COLUMN elapsed_time_sec INTEGER;
ALTER TABLE activity_summaries ADD COLUMN bmr_calories REAL;
ALTER TABLE activity_summaries ADD COLUMN steps INTEGER;
ALTER TABLE activity_summaries ADD COLUMN lap_count INTEGER;
ALTER TABLE activity_summaries ADD COLUMN favorite INTEGER DEFAULT 0;
ALTER TABLE activity_summaries ADD COLUMN avg_ground_contact_time_ms REAL;
ALTER TABLE activity_summaries ADD COLUMN avg_vertical_oscillation_cm REAL;
ALTER TABLE activity_summaries ADD COLUMN avg_vertical_ratio_pct REAL;
ALTER TABLE activity_summaries ADD COLUMN avg_stride_length_cm REAL;
ALTER TABLE activity_summaries ADD COLUMN avg_double_cadence REAL;
ALTER TABLE activity_summaries ADD COLUMN avg_fractional_cadence REAL;
ALTER TABLE activity_summaries ADD COLUMN max_cadence INTEGER;
ALTER TABLE activity_summaries ADD COLUMN min_hr INTEGER;
ALTER TABLE activity_summaries ADD COLUMN avg_hr_gap REAL;
ALTER TABLE activity_summaries ADD COLUMN aerobic_training_effect REAL;
ALTER TABLE activity_summaries ADD COLUMN anaerobic_training_effect REAL;
ALTER TABLE activity_summaries ADD COLUMN training_load REAL;
ALTER TABLE activity_summaries ADD COLUMN training_effect_label TEXT;
ALTER TABLE activity_summaries ADD COLUMN vo2max_activity REAL;
ALTER TABLE activity_summaries ADD COLUMN suffer_score INTEGER;
ALTER TABLE activity_summaries ADD COLUMN perceived_exertion REAL;
ALTER TABLE activity_summaries ADD COLUMN relative_effort INTEGER;
ALTER TABLE activity_summaries ADD COLUMN icu_training_load REAL;
ALTER TABLE activity_summaries ADD COLUMN icu_intensity REAL;
ALTER TABLE activity_summaries ADD COLUMN icu_variability REAL;
ALTER TABLE activity_summaries ADD COLUMN icu_efficiency REAL;
ALTER TABLE activity_summaries ADD COLUMN icu_ftp INTEGER;
ALTER TABLE activity_summaries ADD COLUMN icu_eftp INTEGER;
ALTER TABLE activity_summaries ADD COLUMN icu_rpe INTEGER;
ALTER TABLE activity_summaries ADD COLUMN icu_fatigue REAL;
ALTER TABLE activity_summaries ADD COLUMN icu_fitness REAL;
ALTER TABLE activity_summaries ADD COLUMN pace_load REAL;
ALTER TABLE activity_summaries ADD COLUMN hr_load REAL;
ALTER TABLE activity_summaries ADD COLUMN power_load REAL;
ALTER TABLE activity_summaries ADD COLUMN threshold_pace_sec_km INTEGER;
ALTER TABLE activity_summaries ADD COLUMN icu_resting_hr INTEGER;
ALTER TABLE activity_summaries ADD COLUMN lthr INTEGER;
ALTER TABLE activity_summaries ADD COLUMN icu_weight REAL;
ALTER TABLE activity_summaries ADD COLUMN compliance REAL;
ALTER TABLE activity_summaries ADD COLUMN race INTEGER DEFAULT 0;
ALTER TABLE activity_summaries ADD COLUMN trainer INTEGER DEFAULT 0;
ALTER TABLE activity_summaries ADD COLUMN paired_event_id TEXT;
ALTER TABLE activity_summaries ADD COLUMN normalized_power INTEGER;
ALTER TABLE activity_summaries ADD COLUMN max_power INTEGER;
ALTER TABLE activity_summaries ADD COLUMN weighted_avg_watts REAL;
ALTER TABLE activity_summaries ADD COLUMN avg_grade_adjusted_speed REAL;
ALTER TABLE activity_summaries ADD COLUMN power_wind_enabled INTEGER DEFAULT 0;
ALTER TABLE activity_summaries ADD COLUMN end_lat REAL;
ALTER TABLE activity_summaries ADD COLUMN end_lon REAL;
ALTER TABLE activity_summaries ADD COLUMN min_lat REAL;
ALTER TABLE activity_summaries ADD COLUMN min_lon REAL;
ALTER TABLE activity_summaries ADD COLUMN max_lat REAL;
ALTER TABLE activity_summaries ADD COLUMN max_lon REAL;
ALTER TABLE activity_summaries ADD COLUMN elevation_loss REAL;
ALTER TABLE activity_summaries ADD COLUMN min_elevation REAL;
ALTER TABLE activity_summaries ADD COLUMN max_elevation REAL;
ALTER TABLE activity_summaries ADD COLUMN max_vertical_speed REAL;
ALTER TABLE activity_summaries ADD COLUMN elevation_corrected INTEGER DEFAULT 0;
ALTER TABLE activity_summaries ADD COLUMN min_temperature REAL;
ALTER TABLE activity_summaries ADD COLUMN max_temperature REAL;
ALTER TABLE activity_summaries ADD COLUMN body_battery_diff INTEGER;
ALTER TABLE activity_summaries ADD COLUMN water_estimated_ml REAL;
ALTER TABLE activity_summaries ADD COLUMN moderate_intensity_min INTEGER;
ALTER TABLE activity_summaries ADD COLUMN vigorous_intensity_min INTEGER;
ALTER TABLE activity_summaries ADD COLUMN commute INTEGER DEFAULT 0;
ALTER TABLE activity_summaries ADD COLUMN from_upload INTEGER DEFAULT 0;
ALTER TABLE activity_summaries ADD COLUMN gear_id TEXT;
ALTER TABLE activity_summaries ADD COLUMN external_id TEXT;
ALTER TABLE activity_summaries ADD COLUMN avg_speed_ms REAL;
ALTER TABLE activity_summaries ADD COLUMN max_speed_ms REAL;
ALTER TABLE activity_summaries ADD COLUMN source_garmin INTEGER DEFAULT 0;
ALTER TABLE activity_summaries ADD COLUMN source_strava INTEGER DEFAULT 0;
ALTER TABLE activity_summaries ADD COLUMN source_intervals INTEGER DEFAULT 0;
ALTER TABLE activity_summaries ADD COLUMN updated_at TEXT;

-- ============================================================
-- 2. activity_laps 확장 (13 -> ~33)
-- ============================================================
ALTER TABLE activity_laps ADD COLUMN max_power INTEGER;
ALTER TABLE activity_laps ADD COLUMN max_cadence INTEGER;
ALTER TABLE activity_laps ADD COLUMN avg_speed_ms REAL;
ALTER TABLE activity_laps ADD COLUMN max_speed_ms REAL;
ALTER TABLE activity_laps ADD COLUMN avg_vertical_oscillation_cm REAL;
ALTER TABLE activity_laps ADD COLUMN avg_ground_contact_time_ms REAL;
ALTER TABLE activity_laps ADD COLUMN avg_stride_length_cm REAL;
ALTER TABLE activity_laps ADD COLUMN avg_vertical_ratio_pct REAL;
ALTER TABLE activity_laps ADD COLUMN total_calories INTEGER;
ALTER TABLE activity_laps ADD COLUMN total_fat_calories INTEGER;
ALTER TABLE activity_laps ADD COLUMN avg_temperature REAL;
ALTER TABLE activity_laps ADD COLUMN max_temperature REAL;
ALTER TABLE activity_laps ADD COLUMN total_ascent REAL;
ALTER TABLE activity_laps ADD COLUMN total_descent REAL;
ALTER TABLE activity_laps ADD COLUMN start_lat REAL;
ALTER TABLE activity_laps ADD COLUMN start_lon REAL;
ALTER TABLE activity_laps ADD COLUMN end_lat REAL;
ALTER TABLE activity_laps ADD COLUMN end_lon REAL;
ALTER TABLE activity_laps ADD COLUMN intensity TEXT;
ALTER TABLE activity_laps ADD COLUMN trigger_method TEXT;

-- ============================================================
-- 3. activity_streams (신규)
-- ============================================================
CREATE TABLE IF NOT EXISTS activity_streams (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    activity_id INTEGER NOT NULL REFERENCES activity_summaries(id) ON DELETE CASCADE,
    elapsed_sec REAL NOT NULL,
    timestamp TEXT,
    latitude REAL,
    longitude REAL,
    altitude REAL,
    enhanced_altitude REAL,
    distance_m REAL,
    heart_rate INTEGER,
    cadence INTEGER,
    fractional_cadence REAL,
    speed_ms REAL,
    enhanced_speed REAL,
    power INTEGER,
    accumulated_power INTEGER,
    temperature REAL,
    vertical_oscillation REAL,
    vertical_ratio REAL,
    stance_time REAL,
    stance_time_balance REAL,
    stance_time_percent REAL,
    step_length REAL,
    activity_type INTEGER,
    grade REAL
);
CREATE INDEX IF NOT EXISTS idx_streams_activity ON activity_streams(activity_id);
CREATE INDEX IF NOT EXISTS idx_streams_activity_elapsed ON activity_streams(activity_id, elapsed_sec);

-- ============================================================
-- 4. activity_zones (신규)
-- ============================================================
CREATE TABLE IF NOT EXISTS activity_zones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    activity_id INTEGER NOT NULL REFERENCES activity_summaries(id) ON DELETE CASCADE,
    zone_type TEXT NOT NULL CHECK(zone_type IN ('hr', 'power', 'pace')),
    zone_index INTEGER NOT NULL,
    zone_low_boundary REAL,
    zone_high_boundary REAL,
    time_in_zone_sec INTEGER,
    UNIQUE(activity_id, zone_type, zone_index)
);
CREATE INDEX IF NOT EXISTS idx_zones_activity ON activity_zones(activity_id);

-- ============================================================
-- 5. sleep_data (신규)
-- ============================================================
CREATE TABLE IF NOT EXISTS sleep_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    calendar_date TEXT NOT NULL UNIQUE,
    sleep_start_gmt TEXT,
    sleep_end_gmt TEXT,
    deep_sleep_sec INTEGER,
    light_sleep_sec INTEGER,
    rem_sleep_sec INTEGER,
    awake_sleep_sec INTEGER,
    unmeasurable_sec INTEGER,
    awake_count INTEGER,
    restless_count INTEGER,
    overall_score INTEGER,
    quality_score INTEGER,
    duration_score INTEGER,
    deep_score INTEGER,
    light_score INTEGER,
    rem_score INTEGER,
    recovery_score INTEGER,
    restfulness_score INTEGER,
    awakenings_count_score INTEGER,
    interruptions_score INTEGER,
    awake_time_score INTEGER,
    combined_awake_score INTEGER,
    feedback TEXT,
    insight TEXT,
    avg_respiration REAL,
    highest_respiration REAL,
    lowest_respiration REAL,
    avg_sleep_stress REAL,
    breathing_disruption TEXT,
    avg_spo2 REAL,
    lowest_spo2 INTEGER,
    avg_sleeping_hr REAL,
    spo2_device_id INTEGER,
    has_nap INTEGER DEFAULT 0,
    confirmation_type TEXT,
    retro INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_sleep_date ON sleep_data(calendar_date);

-- ============================================================
-- 6. health_status (신규)
-- ============================================================
CREATE TABLE IF NOT EXISTS health_status (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    calendar_date TEXT NOT NULL,
    metric_type TEXT NOT NULL CHECK(metric_type IN ('HRV','HR','SPO2','SKIN_TEMP_C','RESPIRATION')),
    value REAL,
    baseline_upper REAL,
    baseline_lower REAL,
    status TEXT,
    percentage REAL,
    feedback_key TEXT,
    UNIQUE(calendar_date, metric_type)
);
CREATE INDEX IF NOT EXISTS idx_health_date ON health_status(calendar_date);

-- ============================================================
-- 7. training_readiness (신규)
-- ============================================================
CREATE TABLE IF NOT EXISTS training_readiness (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    calendar_date TEXT NOT NULL UNIQUE,
    device_id INTEGER,
    level INTEGER,
    feedback_short TEXT,
    feedback_long TEXT,
    sleep_score_factor_pct REAL,
    sleep_score_feedback TEXT,
    recovery_time INTEGER,
    recovery_time_factor_pct REAL,
    recovery_time_feedback TEXT,
    hrv_factor_pct REAL,
    hrv_feedback TEXT,
    sleep_history_factor_pct REAL,
    sleep_history_feedback TEXT,
    training_load_factor_pct REAL,
    training_load_feedback TEXT,
    timestamp TEXT
);
CREATE INDEX IF NOT EXISTS idx_readiness_date ON training_readiness(calendar_date);

-- ============================================================
-- 8. race_predictions (신규)
-- ============================================================
CREATE TABLE IF NOT EXISTS race_predictions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    calendar_date TEXT NOT NULL UNIQUE,
    device_id INTEGER,
    race_time_5k REAL,
    race_time_10k REAL,
    race_time_half REAL,
    race_time_marathon REAL,
    timestamp TEXT
);
CREATE INDEX IF NOT EXISTS idx_race_pred_date ON race_predictions(calendar_date);

-- ============================================================
-- 9. training_load_daily (신규)
-- ============================================================
CREATE TABLE IF NOT EXISTS training_load_daily (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    calendar_date TEXT NOT NULL UNIQUE,
    device_id INTEGER,
    daily_load_acute REAL,
    daily_load_chronic REAL,
    acwr_status TEXT,
    acwr_feedback TEXT,
    timestamp TEXT
);
CREATE INDEX IF NOT EXISTS idx_tload_date ON training_load_daily(calendar_date);

-- ============================================================
-- 10. endurance_hill_score (신규)
-- ============================================================
CREATE TABLE IF NOT EXISTS endurance_hill_score (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    calendar_date TEXT NOT NULL UNIQUE,
    device_id INTEGER,
    endurance_overall INTEGER,
    endurance_classification INTEGER,
    endurance_feedback TEXT,
    hill_overall INTEGER,
    hill_classification INTEGER,
    hill_feedback TEXT,
    hill_endurance INTEGER,
    hill_strength INTEGER,
    timestamp TEXT
);
CREATE INDEX IF NOT EXISTS idx_ehs_date ON endurance_hill_score(calendar_date);

-- ============================================================
-- 11. fitness_age (신규)
-- ============================================================
CREATE TABLE IF NOT EXISTS fitness_age (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    calendar_date TEXT NOT NULL UNIQUE,
    chronological_age REAL,
    fitness_age REAL,
    bmi REAL,
    rhr INTEGER,
    vigorous_days INTEGER,
    vigorous_intensity_min INTEGER,
    num_weeks_for_im INTEGER,
    timestamp TEXT
);
CREATE INDEX IF NOT EXISTS idx_fitness_age_date ON fitness_age(calendar_date);

-- ============================================================
-- 12. bio_metrics_history (신규)
-- ============================================================
CREATE TABLE IF NOT EXISTS bio_metrics_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    calendar_date TEXT NOT NULL,
    source TEXT DEFAULT 'garmin',
    weight_kg REAL,
    height_cm REAL,
    vo2max_running REAL,
    vo2max_cycling REAL,
    lactate_threshold_hr INTEGER,
    lactate_threshold_speed REAL,
    functional_threshold_power INTEGER,
    activity_class INTEGER,
    timestamp TEXT,
    UNIQUE(calendar_date, source)
);
CREATE INDEX IF NOT EXISTS idx_bio_date ON bio_metrics_history(calendar_date);

-- ============================================================
-- 13. personal_records (신규)
-- ============================================================
CREATE TABLE IF NOT EXISTS personal_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    record_id INTEGER,
    activity_id INTEGER,
    record_type TEXT NOT NULL,
    value REAL,
    start_time_gmt TEXT,
    created_date TEXT,
    is_current INTEGER DEFAULT 1,
    confirmed INTEGER DEFAULT 1
);
CREATE INDEX IF NOT EXISTS idx_pr_type ON personal_records(record_type);

-- ============================================================
-- 14. gear (신규)
-- ============================================================
CREATE TABLE IF NOT EXISTS gear (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    garmin_gear_pk INTEGER,
    strava_gear_id TEXT,
    intervals_gear_name TEXT,
    source TEXT NOT NULL,
    gear_type TEXT,
    brand TEXT,
    model TEXT,
    name TEXT,
    custom_make_model TEXT,
    status TEXT DEFAULT 'active',
    date_begin TEXT,
    max_distance_m REAL,
    total_distance_m REAL,
    retired INTEGER DEFAULT 0,
    created_at TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS gear_activities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    gear_id INTEGER NOT NULL REFERENCES gear(id),
    activity_id INTEGER NOT NULL REFERENCES activity_summaries(id),
    UNIQUE(gear_id, activity_id)
);

-- ============================================================
-- 15. daily_wellness 확장
-- ============================================================
ALTER TABLE daily_wellness ADD COLUMN spo2_avg REAL;
ALTER TABLE daily_wellness ADD COLUMN spo2_lowest INTEGER;
ALTER TABLE daily_wellness ADD COLUMN skin_temp_c REAL;
ALTER TABLE daily_wellness ADD COLUMN respiration_avg REAL;
ALTER TABLE daily_wellness ADD COLUMN respiration_high REAL;
ALTER TABLE daily_wellness ADD COLUMN respiration_low REAL;
ALTER TABLE daily_wellness ADD COLUMN sleep_overall_score INTEGER;
ALTER TABLE daily_wellness ADD COLUMN sleep_quality_score INTEGER;
ALTER TABLE daily_wellness ADD COLUMN training_readiness INTEGER;
ALTER TABLE daily_wellness ADD COLUMN calories_consumed INTEGER;

-- ============================================================
-- 16. daily_fitness 확장
-- ============================================================
ALTER TABLE daily_fitness ADD COLUMN vo2max_running REAL;
ALTER TABLE daily_fitness ADD COLUMN endurance_score INTEGER;
ALTER TABLE daily_fitness ADD COLUMN hill_score INTEGER;
ALTER TABLE daily_fitness ADD COLUMN training_readiness INTEGER;
ALTER TABLE daily_fitness ADD COLUMN race_pred_5k_sec REAL;
ALTER TABLE daily_fitness ADD COLUMN race_pred_10k_sec REAL;
ALTER TABLE daily_fitness ADD COLUMN race_pred_half_sec REAL;
ALTER TABLE daily_fitness ADD COLUMN race_pred_marathon_sec REAL;
ALTER TABLE daily_fitness ADD COLUMN fitness_age REAL;
ALTER TABLE daily_fitness ADD COLUMN acwr_status TEXT;

-- ============================================================
-- 17. nutrition_logs (신규)
-- ============================================================
CREATE TABLE IF NOT EXISTS nutrition_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    calendar_date TEXT NOT NULL UNIQUE,
    mfp_calorie INTEGER,
    source TEXT DEFAULT 'garmin'
);

-- ============================================================
-- 18. hydration_logs (신규)
-- ============================================================
CREATE TABLE IF NOT EXISTS hydration_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    calendar_date TEXT NOT NULL UNIQUE,
    intake_ml REAL,
    goal_ml REAL,
    source TEXT DEFAULT 'garmin'
);

-- ============================================================
-- 19. devices (신규)
-- ============================================================
CREATE TABLE IF NOT EXISTS devices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id INTEGER UNIQUE,
    device_name TEXT,
    manufacturer TEXT,
    serial_number TEXT,
    firmware_version TEXT,
    created_at TEXT
);

-- ============================================================
-- 20. heat_altitude_acclimation (신규)
-- ============================================================
CREATE TABLE IF NOT EXISTS heat_altitude_acclimation (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    calendar_date TEXT NOT NULL UNIQUE,
    device_id INTEGER,
    heat_acclimation_pct REAL,
    prev_heat_acclimation_pct REAL,
    altitude_acclimation REAL,
    prev_altitude_acclimation REAL,
    timestamp TEXT
);

-- ============================================================
-- 21. training_history (신규)
-- ============================================================
CREATE TABLE IF NOT EXISTS training_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    calendar_date TEXT NOT NULL UNIQUE,
    device_id INTEGER,
    training_status TEXT,
    feedback_phrase TEXT,
    timestamp TEXT
);

-- ============================================================
-- v_canonical_activities 뷰 재생성
-- ============================================================
DROP VIEW IF EXISTS v_canonical_activities;
CREATE VIEW v_canonical_activities AS
SELECT a.*
FROM activity_summaries a
LEFT JOIN activity_summaries b
    ON  b.matched_group_id = a.matched_group_id
    AND b.matched_group_id IS NOT NULL
    AND (
        CASE b.source WHEN 'garmin' THEN 1 WHEN 'strava' THEN 2
                      WHEN 'intervals' THEN 3 WHEN 'runalyze' THEN 4 ELSE 5 END
        < CASE a.source WHEN 'garmin' THEN 1 WHEN 'strava' THEN 2
                        WHEN 'intervals' THEN 3 WHEN 'runalyze' THEN 4 ELSE 5 END
        OR (
            CASE b.source WHEN 'garmin' THEN 1 WHEN 'strava' THEN 2
                          WHEN 'intervals' THEN 3 WHEN 'runalyze' THEN 4 ELSE 5 END
            = CASE a.source WHEN 'garmin' THEN 1 WHEN 'strava' THEN 2
                            WHEN 'intervals' THEN 3 WHEN 'runalyze' THEN 4 ELSE 5 END
            AND b.id < a.id
        )
    )
WHERE b.id IS NULL;

-- ============================================================
-- 22. Intervals.icu 미매핑 해소 (10개)
-- ============================================================
ALTER TABLE activity_summaries ADD COLUMN icu_joules REAL;
ALTER TABLE activity_summaries ADD COLUMN icu_recording_time INTEGER;
ALTER TABLE activity_summaries ADD COLUMN icu_warmup_time INTEGER;
ALTER TABLE activity_summaries ADD COLUMN icu_cooldown_time INTEGER;
ALTER TABLE activity_summaries ADD COLUMN icu_hrrc REAL;
ALTER TABLE activity_summaries ADD COLUMN icu_hrrc_start_bpm INTEGER;
ALTER TABLE activity_summaries ADD COLUMN icu_pm_ftp INTEGER;
ALTER TABLE activity_summaries ADD COLUMN icu_pm_cp INTEGER;
ALTER TABLE activity_summaries ADD COLUMN icu_pm_w_prime REAL;
ALTER TABLE activity_summaries ADD COLUMN icu_pm_p_max INTEGER;

-- ============================================================
-- 23. Strava 미매핑 해소
-- ============================================================
ALTER TABLE activity_summaries ADD COLUMN max_grade REAL;
ALTER TABLE activity_summaries ADD COLUMN avg_grade REAL;
ALTER TABLE activity_summaries ADD COLUMN tag_with_pet INTEGER;
ALTER TABLE activity_summaries ADD COLUMN tag_with_kid INTEGER;
ALTER TABLE activity_summaries ADD COLUMN avg_temperature REAL;

ALTER TABLE weather_data ADD COLUMN weather_condition TEXT;
ALTER TABLE weather_data ADD COLUMN dewpoint_c REAL;
ALTER TABLE weather_data ADD COLUMN weather_pressure_hpa REAL;
ALTER TABLE weather_data ADD COLUMN wind_bearing_deg INTEGER;
ALTER TABLE weather_data ADD COLUMN wind_gust_ms REAL;
ALTER TABLE weather_data ADD COLUMN precip_intensity_mm REAL;
ALTER TABLE weather_data ADD COLUMN precip_probability_pct REAL;
ALTER TABLE weather_data ADD COLUMN precip_type TEXT;
ALTER TABLE weather_data ADD COLUMN visibility_km REAL;
ALTER TABLE weather_data ADD COLUMN uv_index INTEGER;
ALTER TABLE weather_data ADD COLUMN sunrise_time TEXT;
ALTER TABLE weather_data ADD COLUMN sunset_time TEXT;
ALTER TABLE weather_data ADD COLUMN moon_phase REAL;
ALTER TABLE weather_data ADD COLUMN observation_time TEXT;

-- ============================================================
-- 24. FIT 전체 미매핑 해소 (자전거/수영 포함)
-- ============================================================
-- activity_summaries 29개
ALTER TABLE activity_summaries ADD COLUMN avg_stance_time_percent REAL;
ALTER TABLE activity_summaries ADD COLUMN avg_left_pco REAL;
ALTER TABLE activity_summaries ADD COLUMN avg_right_pco REAL;
ALTER TABLE activity_summaries ADD COLUMN avg_left_pedal_smoothness REAL;
ALTER TABLE activity_summaries ADD COLUMN avg_right_pedal_smoothness REAL;
ALTER TABLE activity_summaries ADD COLUMN avg_combined_pedal_smoothness REAL;
ALTER TABLE activity_summaries ADD COLUMN avg_left_torque_effectiveness REAL;
ALTER TABLE activity_summaries ADD COLUMN avg_right_torque_effectiveness REAL;
ALTER TABLE activity_summaries ADD COLUMN avg_left_power_phase TEXT;
ALTER TABLE activity_summaries ADD COLUMN avg_left_power_phase_peak TEXT;
ALTER TABLE activity_summaries ADD COLUMN avg_right_power_phase TEXT;
ALTER TABLE activity_summaries ADD COLUMN avg_right_power_phase_peak TEXT;
ALTER TABLE activity_summaries ADD COLUMN avg_cadence_position TEXT;
ALTER TABLE activity_summaries ADD COLUMN avg_power_position TEXT;
ALTER TABLE activity_summaries ADD COLUMN max_cadence_position TEXT;
ALTER TABLE activity_summaries ADD COLUMN max_power_position TEXT;
ALTER TABLE activity_summaries ADD COLUMN left_right_balance REAL;
ALTER TABLE activity_summaries ADD COLUMN stand_count INTEGER;
ALTER TABLE activity_summaries ADD COLUMN time_standing REAL;
ALTER TABLE activity_summaries ADD COLUMN avg_stroke_count REAL;
ALTER TABLE activity_summaries ADD COLUMN avg_stroke_distance REAL;
ALTER TABLE activity_summaries ADD COLUMN num_active_lengths INTEGER;
ALTER TABLE activity_summaries ADD COLUMN pool_length REAL;
ALTER TABLE activity_summaries ADD COLUMN pool_length_unit TEXT;
ALTER TABLE activity_summaries ADD COLUMN swim_stroke TEXT;
ALTER TABLE activity_summaries ADD COLUMN total_fractional_cycles REAL;
ALTER TABLE activity_summaries ADD COLUMN total_cycles INTEGER;
ALTER TABLE activity_summaries ADD COLUMN max_fractional_cadence REAL;
ALTER TABLE activity_summaries ADD COLUMN num_laps_fit INTEGER;
-- activity_laps 37개
ALTER TABLE activity_laps ADD COLUMN avg_stance_time_balance REAL;
ALTER TABLE activity_laps ADD COLUMN avg_stance_time_percent REAL;
ALTER TABLE activity_laps ADD COLUMN avg_fractional_cadence REAL;
ALTER TABLE activity_laps ADD COLUMN max_fractional_cadence REAL;
ALTER TABLE activity_laps ADD COLUMN normalized_power INTEGER;
ALTER TABLE activity_laps ADD COLUMN total_work INTEGER;
ALTER TABLE activity_laps ADD COLUMN total_strides INTEGER;
ALTER TABLE activity_laps ADD COLUMN total_moving_time REAL;
ALTER TABLE activity_laps ADD COLUMN enhanced_avg_altitude REAL;
ALTER TABLE activity_laps ADD COLUMN enhanced_max_altitude REAL;
ALTER TABLE activity_laps ADD COLUMN enhanced_min_altitude REAL;
ALTER TABLE activity_laps ADD COLUMN total_fractional_cycles REAL;
ALTER TABLE activity_laps ADD COLUMN total_cycles INTEGER;
ALTER TABLE activity_laps ADD COLUMN sport TEXT;
ALTER TABLE activity_laps ADD COLUMN sub_sport TEXT;
ALTER TABLE activity_laps ADD COLUMN avg_left_pco REAL;
ALTER TABLE activity_laps ADD COLUMN avg_right_pco REAL;
ALTER TABLE activity_laps ADD COLUMN avg_left_pedal_smoothness REAL;
ALTER TABLE activity_laps ADD COLUMN avg_right_pedal_smoothness REAL;
ALTER TABLE activity_laps ADD COLUMN avg_combined_pedal_smoothness REAL;
ALTER TABLE activity_laps ADD COLUMN avg_left_torque_effectiveness REAL;
ALTER TABLE activity_laps ADD COLUMN avg_right_torque_effectiveness REAL;
ALTER TABLE activity_laps ADD COLUMN avg_left_power_phase TEXT;
ALTER TABLE activity_laps ADD COLUMN avg_left_power_phase_peak TEXT;
ALTER TABLE activity_laps ADD COLUMN avg_right_power_phase TEXT;
ALTER TABLE activity_laps ADD COLUMN avg_right_power_phase_peak TEXT;
ALTER TABLE activity_laps ADD COLUMN avg_cadence_position TEXT;
ALTER TABLE activity_laps ADD COLUMN avg_power_position TEXT;
ALTER TABLE activity_laps ADD COLUMN max_cadence_position TEXT;
ALTER TABLE activity_laps ADD COLUMN max_power_position TEXT;
ALTER TABLE activity_laps ADD COLUMN left_right_balance REAL;
ALTER TABLE activity_laps ADD COLUMN stand_count INTEGER;
ALTER TABLE activity_laps ADD COLUMN time_standing REAL;
ALTER TABLE activity_laps ADD COLUMN avg_stroke_distance REAL;
ALTER TABLE activity_laps ADD COLUMN num_active_lengths INTEGER;
ALTER TABLE activity_laps ADD COLUMN num_lengths INTEGER;
ALTER TABLE activity_laps ADD COLUMN swim_stroke TEXT;

-- === API 매핑 누락 컬럼 추가 (v2.4) ===
ALTER TABLE activity_summaries ADD COLUMN max_watts INTEGER;
ALTER TABLE daily_wellness ADD COLUMN total_calories INTEGER;
ALTER TABLE daily_wellness ADD COLUMN active_calories INTEGER;
ALTER TABLE daily_wellness ADD COLUMN total_distance_m REAL;
ALTER TABLE daily_wellness ADD COLUMN highly_active_secs INTEGER;
ALTER TABLE daily_wellness ADD COLUMN active_secs INTEGER;
ALTER TABLE daily_wellness ADD COLUMN sedentary_secs INTEGER;
ALTER TABLE daily_wellness ADD COLUMN sleeping_secs INTEGER;
ALTER TABLE daily_wellness ADD COLUMN stress_level INTEGER;
ALTER TABLE daily_wellness ADD COLUMN rest_stress_duration INTEGER;
ALTER TABLE daily_wellness ADD COLUMN activity_stress_duration INTEGER;
ALTER TABLE daily_wellness ADD COLUMN high_stress_duration INTEGER;
ALTER TABLE daily_wellness ADD COLUMN low_stress_duration INTEGER;
ALTER TABLE daily_wellness ADD COLUMN medium_stress_duration INTEGER;
ALTER TABLE daily_wellness ADD COLUMN moderate_intensity_mins INTEGER;
ALTER TABLE daily_wellness ADD COLUMN vigorous_intensity_mins INTEGER;
ALTER TABLE daily_wellness ADD COLUMN body_battery_change INTEGER;
ALTER TABLE daily_wellness ADD COLUMN body_battery_high INTEGER;
ALTER TABLE daily_wellness ADD COLUMN body_battery_low INTEGER;
ALTER TABLE daily_wellness ADD COLUMN body_battery_latest INTEGER;
ALTER TABLE daily_wellness ADD COLUMN floors_ascended INTEGER;
ALTER TABLE daily_wellness ADD COLUMN floors_descended INTEGER;
ALTER TABLE daily_wellness ADD COLUMN min_hr INTEGER;
ALTER TABLE daily_wellness ADD COLUMN max_hr INTEGER;
ALTER TABLE daily_wellness ADD COLUMN avg_spo2 REAL;
ALTER TABLE daily_wellness ADD COLUMN lowest_spo2 INTEGER;
ALTER TABLE daily_wellness ADD COLUMN activity_level TEXT;
ALTER TABLE daily_wellness ADD COLUMN hrv_status REAL;
ALTER TABLE daily_wellness ADD COLUMN sleep_duration_sec INTEGER;
ALTER TABLE daily_wellness ADD COLUMN sleep_quality TEXT;
ALTER TABLE endurance_hill_score ADD COLUMN hill_strength_score REAL;
ALTER TABLE endurance_hill_score ADD COLUMN hill_endurance_score REAL;
ALTER TABLE endurance_hill_score ADD COLUMN hill_overall_score REAL;
ALTER TABLE fitness_age ADD COLUMN achievable_fitness_age REAL;
ALTER TABLE fitness_age ADD COLUMN previous_fitness_age REAL;
ALTER TABLE personal_records ADD COLUMN achieved_at TEXT;
ALTER TABLE gear ADD COLUMN intervals_gear_id TEXT;
ALTER TABLE gear ADD COLUMN gear_name TEXT;
ALTER TABLE gear ADD COLUMN purchase_date TEXT;
ALTER TABLE gear ADD COLUMN total_time_sec INTEGER;
ALTER TABLE gear ADD COLUMN gear_status TEXT;
ALTER TABLE devices ADD COLUMN device_key TEXT;
ALTER TABLE devices ADD COLUMN device_type_id INTEGER;
ALTER TABLE devices ADD COLUMN last_sync TEXT;
ALTER TABLE weather_data ADD COLUMN avg_temperature REAL;
ALTER TABLE weather_data ADD COLUMN cloud_cover INTEGER;

-- === Intervals activity_detail 추가 컬럼 (v2.5) ===
ALTER TABLE activity_summaries ADD COLUMN coasting_time INTEGER;
ALTER TABLE activity_summaries ADD COLUMN total_elevation_loss REAL;
ALTER TABLE activity_summaries ADD COLUMN gap REAL;
ALTER TABLE activity_summaries ADD COLUMN threshold_pace REAL;
ALTER TABLE activity_summaries ADD COLUMN trimp REAL;
ALTER TABLE activity_summaries ADD COLUMN icu_joules_above_ftp INTEGER;
ALTER TABLE activity_summaries ADD COLUMN icu_max_wbal_depletion INTEGER;
ALTER TABLE activity_summaries ADD COLUMN icu_power_hr_z2 REAL;
ALTER TABLE activity_summaries ADD COLUMN icu_power_hr_z2_mins INTEGER;
ALTER TABLE activity_summaries ADD COLUMN icu_cadence_z2 INTEGER;
ALTER TABLE activity_summaries ADD COLUMN decoupling REAL;
ALTER TABLE activity_summaries ADD COLUMN icu_median_time_delta INTEGER;
ALTER TABLE activity_summaries ADD COLUMN icu_variability_index REAL;
ALTER TABLE activity_summaries ADD COLUMN icu_efficiency_factor REAL;
ALTER TABLE activity_summaries ADD COLUMN icu_power_hr REAL;
ALTER TABLE activity_summaries ADD COLUMN strain_score REAL;
