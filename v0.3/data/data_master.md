# RunPulse v0.3 데이터 마스터 시트

> 자동 생성: `scripts/gen_data_master.py` | SSOT: `src/utils/metric_registry.py`

## 요약

- 전체 MetricDef: **184**
  - activity_summary: 32
  - wellness: 12
  - metric: 140
- 카테고리: **16** (+ _unmapped)
- DDL 테이블: **17**
- 불일치: **2**

## 섹션 1: 카테고리 정의

| category | 설명 | 메트릭 수 |
|----------|------|-----------|
| `hr` | 심박 | 16 |
| `power` | 파워 | 9 |
| `pace` | 페이스 | 7 |
| `running_dynamics` | 러닝 다이내믹스 | 13 |
| `volume` | 운동량 | 7 |
| `load` | 부하 | 26 |
| `efficiency` | 효율성 | 9 |
| `capacity` | 체력/역량 | 17 |
| `prediction` | 예측 | 12 |
| `sleep` | 수면 | 10 |
| `stress` | 스트레스 | 5 |
| `readiness` | 준비도 | 9 |
| `weather` | 날씨/환경 | 7 |
| `body` | 신체 | 13 |
| `meta` | 메타/분류 | 18 |
| `athlete` | 선수 설정 | 6 |

## 섹션 2: Layer 1 — activity_summaries (storage=activity_summary)

| column | category | unit | description |
|--------|----------|------|-------------|
| `activity_type` | meta |  | 활동 유형 |
| `avg_cadence` | running_dynamics | spm | 평균 케이던스 |
| `avg_ground_contact_time_ms` | running_dynamics | ms | 평균 지면 접촉 시간 |
| `avg_hr` | hr | bpm | 평균 심박수 |
| `avg_pace_sec_km` | pace | sec/km | 평균 페이스 |
| `avg_power` | power | W | 평균 파워 |
| `avg_speed_ms` | pace | m/s | 평균 속도 |
| `avg_stride_length_cm` | running_dynamics | cm | 평균 보폭 |
| `avg_temperature` | weather | °C | 평균 기온 |
| `avg_vertical_oscillation_cm` | running_dynamics | cm | 평균 수직 진폭 |
| `avg_vertical_ratio_pct` | running_dynamics | % | 평균 수직비 |
| `description` | meta |  | 활동 설명 |
| `device_name` | meta |  | 기기명 |
| `distance_m` | volume | m | 거리 |
| `duration_sec` | volume | sec | 총 시간 |
| `elapsed_time_sec` | volume | sec | 경과 시간 |
| `elevation_gain` | volume | m | 누적 상승고도 |
| `elevation_loss` | volume | m | 누적 하강고도 |
| `end_lat` | meta | ° | 종료 위도 |
| `end_lon` | meta | ° | 종료 경도 |
| `event_type` | meta |  | 이벤트 유형 |
| `gear_id` | meta |  | 장비 FK |
| `max_cadence` | running_dynamics | spm | 최대 케이던스 |
| `max_hr` | hr | bpm | 최대 심박수 |
| `max_power` | power | W | 최대 파워 |
| `max_speed_ms` | pace | m/s | 최대 속도 |
| `moving_time_sec` | volume | sec | 이동 시간 |
| `name` | meta |  | 활동 이름 |
| `source_url` | meta |  | 원본 URL |
| `start_lat` | meta | ° | 시작 위도 |
| `start_lon` | meta | ° | 시작 경도 |
| `start_time` | meta |  | 시작 시간 |

## 섹션 3: Layer 1 — daily_wellness (storage=wellness)

| column | category | unit | description | scope |
|--------|----------|------|-------------|-------|
| `active_calories` | body | kcal | 활동 칼로리 | daily |
| `avg_stress` | stress |  | 평균 스트레스 | daily |
| `body_battery_high` | body |  | Body Battery 최고 | daily |
| `body_battery_low` | body |  | Body Battery 최저 | daily |
| `hrv_last_night` | hr | ms | HRV 전날 밤 | daily |
| `hrv_weekly_avg` | hr | ms | HRV 주간 평균 | daily |
| `resting_hr` | hr | bpm | 안정시 심박수 | daily |
| `sleep_duration_sec` | sleep | sec | 총 수면 시간 | daily |
| `sleep_score` | sleep |  | 수면 점수 | daily |
| `sleep_start_time` | sleep |  | 취침 시각 | daily |
| `steps` | body | count | 일일 걸음 수 | daily |
| `weight_kg` | body | kg | 체중 | daily |

## 섹션 4: Layer 2 — metric_store (storage=metric)

| metric_name | category | scope | unit | description | aliases |
|-------------|----------|-------|------|-------------|---------|
| `ftp_setting` | **athlete** | athlete | W | 설정 FTP |  |
| `lthr_setting` | athlete | athlete | bpm | 설정 LTHR |  |
| `max_hr_setting` | athlete | athlete | bpm | 설정 최대 심박수 |  |
| `rest_hr_setting` | athlete | athlete | bpm | 설정 안정시 심박수 |  |
| `threshold_pace_setting` | athlete | athlete | sec/km | 설정 역치 페이스 |  |
| `weight_setting` | athlete | athlete | kg | 설정 체중 |  |
| `body_battery_diff` | **body** | activity |  | 활동 중 Body Battery 변화 | garmin:`differenceBodyBattery` |
| `calories_active` | body | activity | kcal | 활동 칼로리 |  |
| `calories_total` | body | activity | kcal | 총 칼로리 |  |
| `floors_climbed` | body | activity | count | 오른 층수 |  |
| `intensity_minutes` | body | activity | min | 강도 활동 분 |  |
| `respiration_rate` | body | activity | brpm | 호흡수 |  |
| `spo2_avg` | body | activity | % | 평균 SpO2 |  |
| `water_estimated_ml` | body | activity | ml | 추정 수분 소모량 | garmin:`waterEstimated` |
| `effective_vo2max` | **capacity** | activity | ml/kg/min | Runalyze eVO2Max | runalyze:`effective_vo2max` |
| `endurance_score` | capacity | activity |  | Garmin 지구력 점수 | garmin:`enduranceScore` |
| `fearp` | capacity | activity | sec/km | Field-Equivalent Adjusted Running Pace |  |
| `gap` | capacity | activity | sec/km | Grade Adjusted Pace | intervals:`icu_gap`, garmin:`avgGradeAdjustedSpeed` |
| `gap_rp` | capacity | activity | sec/km | RunPulse GAP (경사 보정 페이스) |  |
| `lactate_threshold_hr` | capacity | activity | bpm | 젖산 역치 심박수 | garmin:`lactateThresholdBpm` |
| `lactate_threshold_speed` | capacity | activity | m/s | 젖산 역치 속도 | garmin:`lactateThresholdSpeed` |
| `runpulse_vdot` | capacity | activity |  | RunPulse VDOT (Daniels) |  |
| `vdot` | capacity | activity |  | Jack Daniels VDOT |  |
| `vo2max_activity` | capacity | activity | ml/kg/min | 활동별 VO2Max 추정치 | garmin:`vO2MaxValue` |
| `critical_power` | capacity | daily | W | Critical Power (CP) |  |
| `eftp` | capacity | daily | sec/km | eFTP (역치 페이스) |  |
| `marathon_shape` | capacity | daily | % | Marathon Shape (훈련 완성도) |  |
| `rri` | capacity | daily |  | RRI (레이스 준비도) |  |
| `sapi` | capacity | daily |  | SAPI (계절 성과 비교) |  |
| `vdot_adj` | capacity | daily |  | VDOT 보정 |  |
| `di` | capacity | weekly |  | Durability Index |  |
| `aerobic_decoupling` | **efficiency** | activity | % | Aerobic Decoupling (%) | intervals:`icu_decoupling` |
| `aerobic_decoupling_rp` | efficiency | activity | % | RunPulse 유산소 분리 |  |
| `efficiency_factor` | efficiency | activity |  | Efficiency Factor (NGP/HR) | intervals:`icu_efficiency_factor` |
| `efficiency_factor_rp` | efficiency | activity |  | RunPulse 효율 계수 (EF) |  |
| `pace_variation` | efficiency | activity |  | Pace Variation | intervals:`pace_variation` |
| `teroi` | efficiency | activity |  | TEROI (훈련 효과 ROI) |  |
| `tpdi` | efficiency | activity | % | TPDI (실내/실외 격차 지수) |  |
| `variability_index` | efficiency | activity |  | Variability Index (NP/AP) |  |
| `rec` | efficiency | daily |  | REC (통합 러닝 효율성) |  |
| `hr_zone_1_pct` | **hr** | activity | % | HR Zone 1 비율 |  |
| `hr_zone_1_sec` | hr | activity | sec | HR Zone 1 체류 시간 | garmin:`hrTimeInZone_0` |
| `hr_zone_2_pct` | hr | activity | % | HR Zone 2 비율 |  |
| `hr_zone_2_sec` | hr | activity | sec | HR Zone 2 체류 시간 | garmin:`hrTimeInZone_1` |
| `hr_zone_3_pct` | hr | activity | % | HR Zone 3 비율 |  |
| `hr_zone_3_sec` | hr | activity | sec | HR Zone 3 체류 시간 | garmin:`hrTimeInZone_2` |
| `hr_zone_4_pct` | hr | activity | % | HR Zone 4 비율 |  |
| `hr_zone_4_sec` | hr | activity | sec | HR Zone 4 체류 시간 | garmin:`hrTimeInZone_3` |
| `hr_zone_5_pct` | hr | activity | % | HR Zone 5 비율 |  |
| `hr_zone_5_sec` | hr | activity | sec | HR Zone 5 체류 시간 | garmin:`hrTimeInZone_4` |
| `hr_zones_detail` | hr | activity | json | HR Zone 전체 상세 | garmin:`hrTimeInZone` |
| `hrss` | **load** | activity | score | HR Stress Score | intervals:`icu_hrss` |
| `icu_feel` | load | activity |  | 체감 (Intervals Feel) | intervals:`icu_feel` |
| `icu_rpe` | load | activity |  | 주관적 운동 강도 (Intervals RPE) | intervals:`icu_rpe` |
| `intensity_factor` | load | activity |  | Intensity Factor (IF) | intervals:`icu_intensity` |
| `intensity_mins_moderate` | load | activity | min | 중강도 활동 시간 | garmin:`moderateIntensityMinutes` |
| `intensity_mins_vigorous` | load | activity | min | 고강도 활동 시간 | garmin:`vigorousIntensityMinutes` |
| `performance_condition` | load | activity |  | 퍼포먼스 컨디션 | garmin:`performanceCondition` |
| `relative_effort` | load | activity | AU | Relative Effort (심박존 기반) |  |
| `rtss` | load | activity | score | Running TSS (rTSS) |  |
| `training_effect_aerobic` | load | activity |  | 유산소 훈련 효과 |  |
| `training_effect_anaerobic` | load | activity |  | 무산소 훈련 효과 |  |
| `training_load_peak` | load | activity |  | 최대 훈련 부하 |  |
| `training_stress_score` | load | activity | score | TSS | garmin:`trainingStressScore` |
| `trimp` | load | activity | score | TRIMP (Banister) | intervals:`icu_trimp` |
| `wlei` | load | activity | AU | WLEI (날씨 가중 노력 지수) |  |
| `acwr` | load | daily |  | Acute:Chronic Workload Ratio |  |
| `atl` | load | daily |  | Acute Training Load |  |
| `ctl` | load | daily |  | Chronic Training Load |  |
| `lsi` | load | daily |  | Load Spike Index |  |
| `monotony` | load | daily |  | 훈련 단조로움 |  |
| `ramp_rate` | load | daily |  | CTL 증가율 |  |
| `rtti` | load | daily | % | 달리기 내성 지수 (RTTI) |  |
| `training_strain` | load | daily |  | 훈련 스트레인 |  |
| `tsb` | load | daily |  | Training Stress Balance |  |
| `adti` | load | weekly |  | Aerobic Decoupling Trend Index |  |
| `tids` | load | weekly |  | Training Intensity Distribution Score |  |
| `achievement_count` | **meta** | activity |  | Strava 업적 수 | strava:`achievement_count` |
| `kudos_count` | meta | activity |  | Strava Kudos | strava:`kudos_count` |
| `pr_count` | meta | activity |  | Strava PR 수 | strava:`pr_count` |
| `source_event_type` | meta | activity |  | 소스 원본 이벤트 분류 | garmin:`eventType`, strava:`workout_type` |
| `source_sport_type` | meta | activity |  | 소스 원본 스포츠 하위 분류 | garmin:`sportType`, strava:`sport_type` |
| `workout_type_classified` | meta | activity |  | RunPulse 워크아웃 분류 |  |
| `negative_split_ratio` | **pace** | activity | ratio | 네거티브 스플릿 비율 |  |
| `pace_10k` | pace | activity | sec/km | 10km 페이스 |  |
| `pace_1k` | pace | activity | sec/km | 1km 페이스 |  |
| `pace_5k` | pace | activity | sec/km | 5km 페이스 |  |
| `icu_ftp` | **power** | activity | W | Intervals FTP | intervals:`icu_ftp` |
| `icu_w_prime` | power | activity | kJ | Intervals W' | intervals:`icu_w_prime` |
| `power_zone_1_sec` | power | activity | sec | Power Zone 1 체류 시간 | garmin:`powerTimeInZone_0` |
| `power_zone_2_sec` | power | activity | sec | Power Zone 2 체류 시간 | garmin:`powerTimeInZone_1` |
| `power_zone_3_sec` | power | activity | sec | Power Zone 3 체류 시간 | garmin:`powerTimeInZone_2` |
| `power_zone_4_sec` | power | activity | sec | Power Zone 4 체류 시간 | garmin:`powerTimeInZone_3` |
| `power_zone_5_sec` | power | activity | sec | Power Zone 5 체류 시간 | garmin:`powerTimeInZone_4` |
| `predicted_10k_sec` | **prediction** | activity | sec | Garmin 10K 예측 |  |
| `predicted_5k_sec` | prediction | activity | sec | Garmin 5K 예측 |  |
| `predicted_full_sec` | prediction | activity | sec | Garmin 마라톤 예측 |  |
| `predicted_half_sec` | prediction | activity | sec | Garmin 하프 예측 |  |
| `race_pred_10k_sec` | prediction | daily | sec | 10K 예측 기록 | garmin:`raceTime10K`, runalyze:`prediction_10k` |
| `race_pred_5k_sec` | prediction | daily | sec | 5K 예측 기록 | garmin:`raceTime5K`, runalyze:`prediction_5k` |
| `race_pred_half_sec` | prediction | daily | sec | 하프마라톤 예측 기록 | garmin:`raceTimeHalf`, runalyze:`prediction_half` |
| `race_pred_marathon_sec` | prediction | daily | sec | 마라톤 예측 기록 | garmin:`raceTimeMarathon`, runalyze:`prediction_marathon` |
| `cirs` | **readiness** | daily |  | Composite Injury Risk Score |  |
| `crs` | readiness | daily |  | CRS (복합 준비도 게이트) |  |
| `training_readiness_hrv_factor` | readiness | daily | % | 훈련 준비도 HRV 요인 | garmin:`hrvFactorPercent` |
| `training_readiness_level` | readiness | daily |  | Garmin 훈련 준비도 레벨 | garmin:`level` |
| `training_readiness_recovery_factor` | readiness | daily | % | 훈련 준비도 회복 요인 | garmin:`recoveryFactorPercent` |
| `training_readiness_score` | readiness | daily |  | Garmin 훈련 준비도 점수 | garmin:`score` |
| `training_readiness_sleep_factor` | readiness | daily | % | 훈련 준비도 수면 요인 | garmin:`sleepScoreFactorPercent` |
| `utrs` | readiness | daily |  | Unified Training Readiness Score |  |
| `rmr` | readiness | weekly | json | Runner Maturity Radar |  |
| `avg_respiration_rate` | **running_dynamics** | activity | brpm | 평균 호흡수 | garmin:`avgRespirationRate` |
| `form_power` | running_dynamics | activity | W | 폼 파워 |  |
| `ground_contact_balance` | running_dynamics | activity | % | 지면 접촉 밸런스 (L/R) | garmin:`avgGroundContactBalance` |
| `ground_contact_time_balance` | running_dynamics | activity | % | GCT 밸런스 |  |
| `impact_loading_rate` | running_dynamics | activity | BW/s | 충격 부하율 |  |
| `leg_spring_stiffness` | running_dynamics | activity | kN/m | 다리 스프링 강성 |  |
| `stance_time` | running_dynamics | activity | ms | 스탠스 타임 |  |
| `avg_respiration_sleep` | **sleep** | daily | brpm | 수면 중 평균 호흡수 | garmin:`averageRespiration` |
| `avg_spo2` | sleep | daily | % | 평균 SpO2 | garmin:`averageSpO2` |
| `min_spo2` | sleep | daily | % | 최저 SpO2 | garmin:`lowestSpO2` |
| `sleep_awake_sec` | sleep | daily | sec | 깨어있던 시간 | garmin:`awakeSleepSeconds` |
| `sleep_deep_sec` | sleep | daily | sec | 깊은 수면 시간 | garmin:`deepSleepSeconds` |
| `sleep_light_sec` | sleep | daily | sec | 얕은 수면 시간 | garmin:`lightSleepSeconds` |
| `sleep_rem_sec` | sleep | daily | sec | REM 수면 시간 | garmin:`remSleepSeconds` |
| `stress_high_duration_sec` | **stress** | daily | sec | 고스트레스 시간 | garmin:`highStressDuration` |
| `stress_low_duration_sec` | stress | daily | sec | 저스트레스 시간 | garmin:`lowStressDuration` |
| `stress_medium_duration_sec` | stress | daily | sec | 중스트레스 시간 | garmin:`mediumStressDuration` |
| `stress_rest_duration_sec` | stress | daily | sec | 휴식 시간 | garmin:`restStressDuration` |
| `steps_activity` | **volume** | activity | count | 활동 중 걸음수 | garmin:`steps` |
| `weather_condition` | **weather** | activity |  | 날씨 상태 텍스트 |  |
| `weather_dew_point_c` | weather | activity | °C | 이슬점 |  |
| `weather_humidity_pct` | weather | activity | % | 습도 |  |
| `weather_pressure_hpa` | weather | activity | hPa | 기압 |  |
| `weather_temp_c` | weather | activity | °C | 기온 |  |
| `weather_wind_speed_ms` | weather | activity | m/s | 풍속 |  |

## 섹션 5: Layer 3/4 테이블 (DDL 관리)

### `activity_streams` (15 cols)

| column | dtype |
|--------|-------|
| `id` | INTEGER |
| `activity_id` | INTEGER |
| `source` | TEXT |
| `elapsed_sec` | INTEGER |
| `distance_m` | REAL |
| `heart_rate` | INTEGER |
| `cadence` | INTEGER |
| `power_watts` | REAL |
| `altitude_m` | REAL |
| `speed_ms` | REAL |
| `latitude` | REAL |
| `longitude` | REAL |
| `grade_pct` | REAL |
| `temperature_c` | REAL |
| `created_at` | TEXT |

### `activity_laps` (17 cols)

| column | dtype |
|--------|-------|
| `id` | INTEGER |
| `activity_id` | INTEGER |
| `source` | TEXT |
| `lap_index` | INTEGER |
| `start_time` | TEXT |
| `duration_sec` | REAL |
| `distance_m` | REAL |
| `avg_hr` | INTEGER |
| `max_hr` | INTEGER |
| `avg_pace_sec_km` | REAL |
| `avg_cadence` | REAL |
| `avg_power` | REAL |
| `max_power` | REAL |
| `elevation_gain` | REAL |
| `calories` | INTEGER |
| `lap_trigger` | TEXT |
| `created_at` | TEXT |

### `activity_best_efforts` (10 cols)

| column | dtype |
|--------|-------|
| `id` | INTEGER |
| `activity_id` | INTEGER |
| `source` | TEXT |
| `effort_name` | TEXT |
| `elapsed_sec` | REAL |
| `distance_m` | REAL |
| `start_index` | INTEGER |
| `end_index` | INTEGER |
| `pr_rank` | INTEGER |
| `created_at` | TEXT |

### `gear` (11 cols)

| column | dtype |
|--------|-------|
| `id` | INTEGER |
| `source` | TEXT |
| `source_gear_id` | TEXT |
| `name` | TEXT |
| `brand` | TEXT |
| `model` | TEXT |
| `gear_type` | TEXT |
| `total_distance_m` | REAL |
| `status` | TEXT |
| `created_at` | TEXT |
| `updated_at` | TEXT |

### `weather_cache` (15 cols)

| column | dtype |
|--------|-------|
| `id` | INTEGER |
| `date` | TEXT |
| `hour` | INTEGER |
| `latitude` | REAL |
| `longitude` | REAL |
| `source` | TEXT |
| `temp_c` | REAL |
| `humidity_pct` | INTEGER |
| `dew_point_c` | REAL |
| `wind_speed_ms` | REAL |
| `wind_direction_deg` | INTEGER |
| `pressure_hpa` | REAL |
| `cloud_cover_pct` | INTEGER |
| `condition_text` | TEXT |
| `fetched_at` | TEXT |

### `sync_jobs` (13 cols)

| column | dtype |
|--------|-------|
| `id` | TEXT |
| `source` | TEXT |
| `job_type` | TEXT |
| `from_date` | TEXT |
| `to_date` | TEXT |
| `status` | TEXT |
| `total_items` | INTEGER |
| `completed_items` | INTEGER |
| `error_count` | INTEGER |
| `last_error` | TEXT |
| `retry_after` | TEXT |
| `created_at` | TEXT |
| `updated_at` | TEXT |

### `chat_messages` (6 cols)

| column | dtype |
|--------|-------|
| `id` | INTEGER |
| `role` | TEXT |
| `content` | TEXT |
| `chip_id` | TEXT |
| `ai_model` | TEXT |
| `created_at` | TEXT |

### `goals` (11 cols)

| column | dtype |
|--------|-------|
| `id` | INTEGER |
| `name` | TEXT |
| `race_date` | TEXT |
| `distance_km` | REAL |
| `target_time_sec` | INTEGER |
| `target_pace_sec_km` | INTEGER |
| `status` | TEXT |
| `created_at` | TEXT |
| `distance_label` | TEXT |
| `weekly_km_target` | REAL |
| `plan_weeks` | INTEGER |

### `planned_workouts` (17 cols)

| column | dtype |
|--------|-------|
| `id` | INTEGER |
| `date` | TEXT |
| `workout_type` | TEXT |
| `distance_km` | REAL |
| `target_pace_min` | INTEGER |
| `target_pace_max` | INTEGER |
| `target_hr_zone` | INTEGER |
| `description` | TEXT |
| `rationale` | TEXT |
| `completed` | INTEGER |
| `matched_activity_id` | INTEGER |
| `source` | TEXT |
| `ai_model` | TEXT |
| `garmin_workout_id` | TEXT |
| `skip_reason` | TEXT |
| `updated_at` | TEXT |
| `interval_prescription` | TEXT |

### `user_training_prefs` (7 cols)

| column | dtype |
|--------|-------|
| `id` | INTEGER |
| `rest_weekdays_mask` | INTEGER |
| `blocked_dates` | TEXT |
| `interval_rep_m` | INTEGER |
| `max_q_days` | INTEGER |
| `long_run_weekday_mask` | INTEGER |
| `updated_at` | TEXT |

### `session_outcomes` (25 cols)

| column | dtype |
|--------|-------|
| `id` | INTEGER |
| `planned_id` | INTEGER |
| `activity_id` | INTEGER |
| `date` | TEXT |
| `planned_dist_km` | REAL |
| `actual_dist_km` | REAL |
| `dist_ratio` | REAL |
| `planned_pace` | INTEGER |
| `actual_pace` | INTEGER |
| `pace_delta_pct` | REAL |
| `hr_z1_pct` | REAL |
| `hr_z2_pct` | REAL |
| `hr_z3_pct` | REAL |
| `target_zone` | INTEGER |
| `actual_avg_hr` | INTEGER |
| `hr_delta` | INTEGER |
| `decoupling_pct` | REAL |
| `trimp` | REAL |
| `crs_at_session` | REAL |
| `tsb_at_session` | REAL |
| `hrv_at_session` | REAL |
| `bb_at_session` | INTEGER |
| `acwr_at_session` | REAL |
| `outcome_label` | TEXT |
| `computed_at` | TEXT |

## 섹션 6: 뷰

- `v_canonical_activities`

## 섹션 7: 불일치 검출

- 🟠 activity_summaries: 제거 예정 컬럼 아직 DDL에 존재 — calories, normalized_power, suffer_score, training_effect_aerobic, training_effect_anaerobic, training_load
- 🟠 daily_fitness: 삭제 예정이나 DDL에 아직 존재

## 섹션 8: scope × category 교차표

| category | activity | daily | weekly | athlete | total |
|----------|------|------|------|------|-------|
| `athlete` |  |  |  | 6 | **6** |
| `body` | 8 | 5 |  |  | **13** |
| `capacity` | 10 | 6 | 1 |  | **17** |
| `efficiency` | 8 | 1 |  |  | **9** |
| `hr` | 13 | 3 |  |  | **16** |
| `load` | 15 | 9 | 2 |  | **26** |
| `meta` | 18 |  |  |  | **18** |
| `pace` | 7 |  |  |  | **7** |
| `power` | 9 |  |  |  | **9** |
| `prediction` | 4 | 8 |  |  | **12** |
| `readiness` |  | 8 | 1 |  | **9** |
| `running_dynamics` | 13 |  |  |  | **13** |
| `sleep` |  | 10 |  |  | **10** |
| `stress` |  | 5 |  |  | **5** |
| `volume` | 7 |  |  |  | **7** |
| `weather` | 7 |  |  |  | **7** |

## 섹션 9: storage × category 교차표

| category | activity_summary | wellness | metric | total |
|----------|------|------|------|-------|
| `athlete` |  |  | 6 | **6** |
| `body` |  | 5 | 8 | **13** |
| `capacity` |  |  | 17 | **17** |
| `efficiency` |  |  | 9 | **9** |
| `hr` | 2 | 3 | 11 | **16** |
| `load` |  |  | 26 | **26** |
| `meta` | 12 |  | 6 | **18** |
| `pace` | 3 |  | 4 | **7** |
| `power` | 2 |  | 7 | **9** |
| `prediction` |  |  | 12 | **12** |
| `readiness` |  |  | 9 | **9** |
| `running_dynamics` | 6 |  | 7 | **13** |
| `sleep` |  | 3 | 7 | **10** |
| `stress` |  | 1 | 4 | **5** |
| `volume` | 6 |  | 1 | **7** |
| `weather` | 1 |  | 6 | **7** |
