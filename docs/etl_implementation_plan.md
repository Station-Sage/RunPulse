# RunPulse ETL 구현 설계서
생성일: 2026-03-24

## 1. 현황 요약

| 항목 | 현재 | 목표 | 갭 |
|------|------|------|-----|
| 테이블 수 | 35 | 35 | INSERT 미구현 19개 |
| activity_summaries 컬럼 | 166 | 166 | 150개 미구현 |
| activity_laps 컬럼 | 70 | 70 | 58개 미구현 |
| daily_wellness 컬럼 | 56 | 56 | 47개 미구현 |
| daily_fitness 컬럼 | 22 | 22 | 13개 미구현 |

---
## 2. garmin.py — sync_activities() 확장

### 2.1 activity_summaries INSERT 확장

현재 INSERT 컬럼 (16개):
```
activity_type, avg_cadence, avg_hr, avg_pace_sec_km, calories, description, distance_km, duration_sec, elevation_gain, max_hr, source, source_id, start_lat, start_lon, start_time
```

추가 필요 — Garmin API `act` 객체 (활동 목록) → activity_summaries:

| API 필드 | DB 컬럼 | 타입 | 변환 |
|----------|---------|------|------|
| `activityId` | `garmin_activity_id` | TEXT | `str(act.get('activityId'))` |
| `activityName` | `name` | TEXT | `act.get('activityName')` |
| `activityType.typeKey` | `activity_type` | TEXT | `act.get('activityType',{}).get('typeKey')` |
| `sportTypeId` | `sport_type` | TEXT | `act.get('sportTypeId')` |
| `movingDuration` | `moving_time_sec` | INTEGER | `int(act.get('movingDuration') or 0)` |
| `duration` | `elapsed_time_sec` | INTEGER | `int(act.get('duration') or 0)` |
| `averageSpeed` | `avg_speed_ms` | REAL | `act.get('averageSpeed')` |
| `maxSpeed` | `max_speed_ms` | REAL | `act.get('maxSpeed')` |
| `averageRunningCadenceInStepsPerMinute` | `avg_cadence` | INTEGER | `이미 구현` |
| `maxRunningCadenceInStepsPerMinute` | `max_cadence` | INTEGER | `act.get('maxRunningCadenceInStepsPerMinute')` |
| `averageHR` | `avg_hr` | INTEGER | `이미 구현` |
| `maxHR` | `max_hr` | INTEGER | `이미 구현` |
| `elevationGain` | `elevation_gain` | REAL | `이미 구현` |
| `elevationLoss` | `elevation_loss` | REAL | `act.get('elevationLoss')` |
| `calories` | `calories` | INTEGER | `이미 구현` |
| `bmrCalories` | `bmr_calories` | INTEGER | `act.get('bmrCalories')` |
| `steps` | `steps` | INTEGER | `act.get('steps')` |
| `averagePower` | `avg_power` | REAL | `act.get('averagePower') — 현재 detail에서만` |
| `maxPower` | `max_power` | INTEGER | `act.get('maxPower')` |
| `normPower` | `norm_power` | REAL | `act.get('normPower')` |
| `aerobicTrainingEffect` | `aerobic_training_effect` | REAL | `act.get('aerobicTrainingEffect')` |
| `anaerobicTrainingEffect` | `anaerobic_training_effect` | REAL | `act.get('anaerobicTrainingEffect')` |
| `activityTrainingLoad` | `training_load` | REAL | `act.get('activityTrainingLoad')` |
| `vO2MaxValue` | `vo2max_activity` | REAL | `act.get('vO2MaxValue')` |
| `avgGroundContactTime` | `avg_ground_contact_time` | REAL | `현재 detail에서만` |
| `avgStrideLength` | `avg_stride_length` | REAL | `현재 detail에서만` |
| `avgVerticalOscillation` | `avg_vertical_oscillation` | REAL | `현재 detail에서만` |
| `avgVerticalRatio` | `avg_vertical_ratio` | REAL | `현재 detail에서만` |
| `avgGroundContactBalance` | `avg_ground_contact_balance` | REAL | `act.get('avgGroundContactBalance')` |
| `avgStrideLengthCM` | `avg_stride_length_cm` | REAL | `act.get('avgStrideLengthCM')` |
| `avgVerticalOscillationCM` | `avg_vertical_oscillation_cm` | REAL | `act.get('avgVerticalOscillationCM')` |
| `avgVerticalRatioPct` | `avg_vertical_ratio_pct` | REAL | `act.get('avgVerticalRatioPct')` |
| `avgGroundContactTimeMilli` | `avg_ground_contact_time_ms` | REAL | `act.get('avgGroundContactTimeMilli')` |
| `avgDoubleCadence` | `avg_double_cadence` | REAL | `act.get('avgDoubleCadence')` |
| `lapCount` | `lap_count` | INTEGER | `act.get('lapCount')` |
| `startLatitude` | `start_lat` | REAL | `이미 구현` |
| `startLongitude` | `start_lon` | REAL | `이미 구현` |
| `endLatitude` | `end_lat` | REAL | `act.get('endLatitude')` |
| `endLongitude` | `end_lon` | REAL | `act.get('endLongitude')` |
| `minElevation` | `min_elevation` | REAL | `act.get('minElevation')` |
| `maxElevation` | `max_elevation` | REAL | `act.get('maxElevation')` |
| `maxVerticalSpeed` | `max_vertical_speed` | REAL | `act.get('maxVerticalSpeed')` |
| `minTemperature` | `min_temperature` | REAL | `act.get('minTemperature')` |
| `maxTemperature` | `max_temperature` | REAL | `act.get('maxTemperature')` |
| `avgTemperature` | `avg_temperature` | REAL | `act.get('avgTemperature')` |
| `differenceBodyBattery` | `body_battery_diff` | INTEGER | `act.get('differenceBodyBattery')` |
| `waterEstimated` | `water_estimated_ml` | REAL | `act.get('waterEstimated')` |
| `moderateIntensityMinutes` | `intensity_mins_moderate` | INTEGER | `act.get('moderateIntensityMinutes')` |
| `vigorousIntensityMinutes` | `intensity_mins_vigorous` | INTEGER | `act.get('vigorousIntensityMinutes')` |
| `deviceId` | `device_id` | TEXT | `str(act.get('deviceId'))` |

### 2.2 Garmin detail API → activity_summaries UPDATE

sync_activities() 내부에서 detail API 호출 후 추가 필드:

| detail/summaryDTO 필드 | DB 컬럼 | 현재 상태 |
|----------------------|---------|----------|
| `hrTimeInZone[0~6]` | `hr_zone0_sec ~ hr_zone6_sec` | detail_metrics에 JSON으로 저장 → 컬럼으로 이동 |
| `powerTimeInZone[0~5]` | `power_zone0_sec ~ power_zone5_sec` | detail_metrics에 JSON으로 저장 → 컬럼으로 이동 |
| `avgHrGap` | `avg_hr_gap` | 미구현 |
| `avgGradeAdjustedSpeed` | `avg_grade_adjusted_speed` | 미구현 |
| `maxDoubleCadence` | `max_double_cadence` | 미구현 |
| `minActivityLapDuration` | `min_activity_lap_duration` | 미구현 |

### 2.3 sync_wellness() → daily_wellness 확장

현재 INSERT 컬럼 (14개):
```
avg_sleeping_hr, body_battery, date, hrv_sdnn, hrv_value, readiness_score, resting_hr, sleep_hours, sleep_score, source, steps, stress_avg, weight_kg
```

추가 필요 (29개) — Garmin API 소스별:

| API 소스 | API 필드 | DB 컬럼 | 타입 |
|----------|----------|---------|------|
| user_summary | `totalKilocalories` | `total_calories` | INTEGER |
| user_summary | `activeKilocalories` | `active_calories` | INTEGER |
| user_summary | `totalDistanceMeters` | `total_distance_m` | REAL |
| user_summary | `highlyActiveSeconds` | `highly_active_secs` | INTEGER |
| user_summary | `activeSeconds` | `active_secs` | INTEGER |
| user_summary | `sedentarySeconds` | `sedentary_secs` | INTEGER |
| user_summary | `sleepingSeconds` | `sleeping_secs` | INTEGER |
| user_summary | `bodyBatteryHighestValue` | `body_battery_high` | INTEGER |
| user_summary | `bodyBatteryLowestValue` | `body_battery_low` | INTEGER |
| user_summary | `bodyBatteryMostRecentValue` | `body_battery_latest` | INTEGER |
| user_summary | `floorsAscended` | `floors_ascended` | INTEGER |
| user_summary | `floorsDescended` | `floors_descended` | INTEGER |
| user_summary | `minHeartRate` | `min_hr` | INTEGER |
| user_summary | `maxHeartRate` | `max_hr` | INTEGER |
| user_summary | `averageSpo2` | `avg_spo2` | REAL |
| user_summary | `lowestSpo2` | `lowest_spo2` | INTEGER |
| all_day_stress | `overallStressLevel` | `stress_level` | INTEGER |
| all_day_stress | `restStressDuration` | `rest_stress_duration` | INTEGER |
| all_day_stress | `activityStressDuration` | `activity_stress_duration` | INTEGER |
| all_day_stress | `highStressDuration` | `high_stress_duration` | INTEGER |
| all_day_stress | `lowStressDuration` | `low_stress_duration` | INTEGER |
| all_day_stress | `mediumStressDuration` | `medium_stress_duration` | INTEGER |
| intensity_minutes | `moderateIntensityMinutes` | `moderate_intensity_mins` | INTEGER |
| intensity_minutes | `vigorousIntensityMinutes` | `vigorous_intensity_mins` | INTEGER |
| body_battery | `bodyBatteryChange` | `body_battery_change` | INTEGER |
| steps_data | `primaryActivityLevel` | `activity_level` | TEXT |
| sleep | `sleepTimeSeconds` | `sleep_duration_sec` | INTEGER |
| wellness | `sleepQuality` | `sleep_quality` | TEXT |
| wellness | `hrvStatus` | `hrv_status` | REAL |

### 2.4 sync_wellness() → 신규 테이블

#### sleep_data (37컬럼) ← Garmin sleep API

| API 필드 | DB 컬럼 | 타입 |
|----------|---------|------|
| `calendarDate` | `date` | TEXT |
| `sleepStartTimestampGMT` | `sleep_start` | TEXT |
| `sleepEndTimestampGMT` | `sleep_end` | TEXT |
| `deepSleepSeconds` | `deep_sleep_sec` | INTEGER |
| `lightSleepSeconds` | `light_sleep_sec` | INTEGER |
| `remSleepSeconds` | `rem_sleep_sec` | INTEGER |
| `awakeSleepSeconds` | `awake_sec` | INTEGER |
| `averageRespiration` | `avg_respiration` | REAL |
| `lowestRespiration` | `lowest_respiration` | REAL |
| `highestRespiration` | `highest_respiration` | REAL |
| `avgSleepStress` | `avg_sleep_stress` | REAL |
| `sleepScores.overall` | `overall_score` | INTEGER |
| `sleepScores.deep` | `deep_score` | INTEGER |
| `sleepScores.rem` | `rem_score` | INTEGER |
| `sleepScores.light` | `light_score` | INTEGER |
| `sleepScores.recovery` | `recovery_score` | INTEGER |
| `spo2SleepSummary.averageSPO2` | `avg_spo2` | REAL |
| `spo2SleepSummary.lowestSPO2` | `lowest_spo2` | INTEGER |

#### health_status (9컬럼) ← Garmin healthStatusData

| API 필드 | DB 컬럼 | 타입 |
|----------|---------|------|
| `calendarDate` | `date` | TEXT |
| `hrv7DayAvg` | `hrv_7d_avg` | REAL |
| `currentDayRestingHeartRate` | `resting_hr` | INTEGER |
| `averageSpO2` | `avg_spo2` | REAL |
| `skinTemp` | `skin_temp` | REAL |
| `averageRespiration` | `avg_respiration` | REAL |

#### training_readiness (18컬럼) ← Garmin TrainingReadinessDTO

| API 필드 | DB 컬럼 | 타입 |
|----------|---------|------|
| `calendarDate` | `calendar_date` | TEXT |
| `level` | `level` | TEXT |
| `score` | `score` | REAL |
| `sleepScoreFactorPercent` | `sleep_factor_pct` | REAL |
| `recoveryTime` | `recovery_time` | INTEGER |
| `recoveryTimeFactorPercent` | `recovery_factor_pct` | REAL |
| `hrvFactorPercent` | `hrv_factor_pct` | REAL |
| `acuteLoadFactorPercent` | `acute_load_factor_pct` | REAL |

#### race_predictions (8컬럼) ← Garmin RunRacePredictions

| API 필드 | DB 컬럼 | 타입 |
|----------|---------|------|
| `calendarDate` | `date` | TEXT |
| `raceTime5K` | `time_5k_sec` | REAL |
| `raceTime10K` | `time_10k_sec` | REAL |
| `raceTimeHalf` | `time_half_sec` | REAL |
| `raceTimeMarathon` | `time_marathon_sec` | REAL |

#### training_load_daily (8컬럼) ← Garmin MetricsAcuteTrainingLoad

| API 필드 | DB 컬럼 | 타입 |
|----------|---------|------|
| `calendarDate` | `date` | TEXT |
| `dailyTrainingLoadAcute` | `acute_load` | REAL |
| `dailyTrainingLoadChronic` | `chronic_load` | REAL |
| `acwrStatus` | `acwr_status` | TEXT |

#### endurance_hill_score (15컬럼) ← Garmin EnduranceScore + HillScore

| API 필드 | DB 컬럼 | 타입 |
|----------|---------|------|
| `calendarDate` | `calendar_date` | TEXT |
| `overallScore (endurance)` | `endurance_overall` | REAL |
| `classification (endurance)` | `endurance_classification` | TEXT |
| `overallScore (hill)` | `hill_overall_score` | REAL |
| `strengthScore (hill)` | `hill_strength_score` | REAL |
| `enduranceScore (hill)` | `hill_endurance_score` | REAL |

#### fitness_age (12컬럼) ← Garmin fitnessAgeData

| API 필드 | DB 컬럼 | 타입 |
|----------|---------|------|
| `chronologicalAge` | `chronological_age` | REAL |
| `fitnessAge` | `fitness_age` | REAL |
| `achievableFitnessAge` | `achievable_fitness_age` | REAL |
| `bmi` | `bmi` | REAL |
| `rhr` | `rhr` | INTEGER |

#### bio_metrics_history (12컬럼) ← Garmin userBioMetrics

| API 필드 | DB 컬럼 | 타입 |
|----------|---------|------|
| `date` | `date` | TEXT |
| `vo2MaxRunning` | `vo2max_running` | REAL |
| `functionalThresholdPower` | `ftp` | REAL |
| `lactateThresholdHeartRate` | `lt_hr` | INTEGER |
| `weight` | `weight_kg` | REAL |

#### personal_records (10컬럼) ← Garmin personalRecords

| API 필드 | DB 컬럼 | 타입 |
|----------|---------|------|
| `typeId` | `record_type` | TEXT |
| `value` | `value` | REAL |
| `activityId` | `activity_id` | TEXT |
| `prStartTimeGMT` | `achieved_at` | TEXT |

#### gear + gear_activities (22컬럼) ← Garmin gear

| API 필드 | DB 컬럼 | 타입 |
|----------|---------|------|
| `gearPk` | `garmin_gear_id` | TEXT |
| `gearModelName` | `gear_name` | TEXT |
| `gearTypeName` | `gear_type` | TEXT |
| `maximumMeters` | `max_distance_m` | REAL |
| `gearStatusName` | `gear_status` | TEXT |

#### devices (10컬럼) ← Garmin devices + device_last_used

| API 필드 | DB 컬럼 | 타입 |
|----------|---------|------|
| `displayName` | `device_name` | TEXT |
| `applicationKey` | `device_key` | TEXT |
| `deviceTypePk` | `device_type_id` | INTEGER |
| `lastUsedDeviceUploadTime` | `last_sync` | TEXT |

#### heat_altitude_acclimation (8컬럼) ← Garmin MetricsHeatAltitude

| API 필드 | DB 컬럼 | 타입 |
|----------|---------|------|
| `calendarDate` | `date` | TEXT |
| `heatAcclimationPercentage` | `heat_pct` | REAL |
| `altitudeAcclimation` | `altitude_score` | REAL |

#### training_history (6컬럼) ← Garmin TrainingHistory

| API 필드 | DB 컬럼 | 타입 |
|----------|---------|------|
| `calendarDate` | `date` | TEXT |
| `trainingStatus` | `status` | TEXT |
| `trainingStatus2FeedbackPhrase` | `feedback` | TEXT |

#### weather_data (28컬럼) ← Strava CSV + Intervals weather

| API 필드 | DB 컬럼 | 타입 |
|----------|---------|------|
| `activity_id` | `activity_id` | INTEGER |
| `temperature_c` | `temperature_c` | REAL |
| `humidity_pct` | `humidity_pct` | INTEGER |
| `wind_speed_ms` | `wind_speed_ms` | REAL |
| `weather_condition` | `weather_condition` | TEXT |

---
## 3. strava.py — sync_activities() 확장

### 3.1 activity_summaries INSERT 확장

현재 INSERT 컬럼 (16개). 추가 매핑:

| API 필드 | DB 컬럼 | 변환 |
|----------|---------|------|
| `id` | `strava_activity_id` | `str(act.get('id'))` |
| `moving_time` | `moving_time_sec` | `int(act.get('moving_time'))` |
| `elapsed_time` | `elapsed_time_sec` | `int(act.get('elapsed_time'))` |
| `average_speed` | `avg_speed_ms` | `act.get('average_speed')` |
| `max_speed` | `max_speed_ms` | `act.get('max_speed')` |
| `average_watts` | `avg_power` | `act.get('average_watts')` |
| `weighted_average_watts` | `weighted_avg_watts` | `act.get('weighted_average_watts')` |
| `max_watts` | `max_watts` | `act.get('max_watts')` |
| `kilojoules` | `icu_joules` | `act.get('kilojoules') * 1000` |
| `average_temp` | `avg_temperature` | `act.get('average_temp')` |
| `elev_high` | `max_elevation` | `act.get('elev_high')` |
| `elev_low` | `min_elevation` | `act.get('elev_low')` |
| `suffer_score` | `suffer_score` | `detail.get('suffer_score')` |
| `gear_id` | `gear_id` | `act.get('gear_id')` |
| `device_name` | `device_name` | `act.get('device_name')` |
| `commute` | `commute` | `act.get('commute')` |
| `flagged` | `favorite` | `act.get('flagged')` |
| `external_id` | `external_id` | `act.get('external_id')` |
| `end_latlng[0]` | `end_lat` | `act.get('end_latlng', [None,None])[0]` |
| `end_latlng[1]` | `end_lon` | `act.get('end_latlng', [None,None])[1]` |
| `perceived_exertion` | `perceived_exertion` | `detail.get('perceived_exertion')` |

### 3.2 Strava streams → activity_streams (신규)

현재: streams를 `activity_detail_metrics`에 JSON blob으로 저장
목표: `activity_streams` 테이블에 시계열 row로 저장

| Stream key | DB 컬럼 | 비고 |
|------------|---------|------|
| `time` | `elapsed_sec` | 초 단위 타임스탬프 |
| `distance` | `distance_m` | 누적 거리(m) |
| `heartrate` | `heart_rate` | BPM |
| `cadence` | `cadence` | SPM |
| `watts` | `power_watts` | W |
| `altitude` | `altitude_m` | 고도(m) |
| `latlng[0]` | `latitude` | 위도 |
| `latlng[1]` | `longitude` | 경도 |
| `velocity_smooth` | `speed_ms` | 속도(m/s) |
| `grade_smooth` | `grade` | 경사도(%) |
| `temp` | `temperature_c` | 온도(°C) |

### 3.3 Strava laps → activity_laps 확장

현재 14개 컬럼. 추가:

| API 필드 | DB 컬럼 | 타입 |
|----------|---------|------|
| `max_speed` | `max_speed` | REAL |
| `average_speed` | `avg_speed` | REAL |
| `total_elevation_gain` | `elevation_gain` | REAL |
| `average_watts` | `avg_power` | REAL |
| `max_watts` | `max_power` | INTEGER |
| `average_cadence` | `avg_cadence` | REAL |

---
## 4. intervals.py — sync_activities() 확장

### 4.1 activity_summaries INSERT 확장

현재 INSERT 컬럼 (16개). 추가 매핑 (activity_detail 173필드에서):

| API 필드 | DB 컬럼 | 타입 |
|----------|---------|------|
| `id` | `intervals_activity_id` | TEXT |
| `icu_training_load` | `icu_training_load` | REAL |
| `icu_intensity` | `icu_intensity` | REAL |
| `icu_variability_index` | `icu_variability_index` | REAL |
| `icu_efficiency_factor` | `icu_efficiency_factor` | REAL |
| `icu_ftp` | `icu_ftp` | INTEGER |
| `icu_eftp` | `icu_eftp` | INTEGER |
| `icu_pm_ftp` | `icu_pm_ftp` | INTEGER |
| `icu_pm_cp` | `icu_pm_cp` | INTEGER |
| `icu_pm_w_prime` | `icu_pm_w_prime` | REAL |
| `icu_pm_p_max` | `icu_pm_p_max` | INTEGER |
| `icu_hrrc` | `icu_hrrc` | REAL |
| `icu_hrrc_start_bpm` | `icu_hrrc_start_bpm` | INTEGER |
| `icu_recording_time` | `icu_recording_time` | INTEGER |
| `icu_warmup_time` | `icu_warmup_time` | INTEGER |
| `icu_cooldown_time` | `icu_cooldown_time` | INTEGER |
| `icu_joules` | `icu_joules` | REAL |
| `pace_load` | `pace_load` | REAL |
| `hr_load` | `hr_load` | REAL |
| `power_load` | `power_load` | REAL |
| `gap` | `gap` | REAL |
| `trimp` | `trimp` | REAL |
| `strain_score` | `strain_score` | REAL |
| `decoupling` | `decoupling` | REAL |
| `threshold_pace` | `threshold_pace` | REAL |
| `coasting_time` | `coasting_time` | INTEGER |
| `total_elevation_loss` | `total_elevation_loss` | REAL |
| `icu_joules_above_ftp` | `icu_joules_above_ftp` | INTEGER |
| `icu_max_wbal_depletion` | `icu_max_wbal_depletion` | INTEGER |
| `icu_power_hr_z2` | `icu_power_hr_z2` | REAL |
| `icu_power_hr_z2_mins` | `icu_power_hr_z2_mins` | INTEGER |
| `icu_cadence_z2` | `icu_cadence_z2` | INTEGER |
| `icu_median_time_delta` | `icu_median_time_delta` | INTEGER |
| `icu_power_hr` | `icu_power_hr` | REAL |
| `average_speed` | `avg_speed_ms` | REAL |
| `max_speed` | `max_speed_ms` | REAL |
| `max_heartrate` | `max_hr` | INTEGER |

### 4.2 Intervals streams → activity_streams

Intervals `/activity/{id}/streams` → activity_streams 테이블
현재: activity_detail_metrics에 JSON blob 저장
목표: activity_streams 행 단위 저장 (Strava streams와 동일 구조)

### 4.3 Intervals wellness → daily_wellness/daily_fitness 확장

현재: ctl, atl, tsb, ramp_rate, sleepQuality, hrv 등 기본 필드만
추가 필요:

| API 필드 | DB 컬럼 | 테이블 |
|----------|---------|--------|
| `hrvSDNN` | `hrv_status` | daily_wellness |
| `sleepTime` | `sleep_duration_sec` | daily_wellness |
| `sleepQuality` | `sleep_quality` | daily_wellness |
| `weight` | `weight_kg` | daily_wellness |
| `ctl` | `ctl` | daily_fitness — 이미 구현 |
| `atl` | `atl` | daily_fitness — 이미 구현 |

---
## 5. 구현 우선순위

### Phase 1 — 핵심 (activity_summaries 확장)
1. garmin.py sync_activities() — act 목록 필드 확장 (~30컬럼)
2. garmin.py sync_activities() — detail API 필드 확장 (~20컬럼)
3. strava.py sync_activities() — 요약 필드 확장 (~20컬럼)
4. intervals.py sync_activities() — 리스트+디테일 필드 확장 (~35컬럼)

### Phase 2 — 스트림 데이터
5. strava.py — streams → activity_streams 테이블
6. intervals.py — streams → activity_streams 테이블
7. garmin.py — activity_details metrics → activity_streams

### Phase 3 — 웰니스/데일리
8. garmin.py sync_wellness() — daily_wellness 29컬럼 확장
9. garmin.py sync_wellness() — daily_fitness 13컬럼 확장
10. intervals.py sync_wellness() — daily_wellness 추가 필드

### Phase 4 — 신규 테이블
11. garmin.py — sleep_data (37컬럼)
12. garmin.py — health_status (9컬럼)
13. garmin.py — training_readiness (18컬럼)
14. garmin.py — race_predictions (8컬럼)
15. garmin.py — training_load_daily (8컬럼)
16. garmin.py — endurance_hill_score (15컬럼)
17. garmin.py — fitness_age (12컬럼)
18. garmin.py — bio_metrics_history (12컬럼)
19. garmin.py — personal_records (10컬럼)
20. garmin.py — gear + gear_activities (25컬럼)
21. garmin.py — devices (10컬럼)
22. garmin.py — heat_altitude_acclimation (8컬럼)
23. garmin.py — training_history (6컬럼)

### Phase 5 — 보조
24. weather_data — Strava CSV import + Intervals weather API
25. nutrition_logs, hydration_logs — Garmin export
26. activity_laps 확장 — Strava/Garmin
27. activity_zones — Garmin/Intervals zones

---
## 6. 중복 컬럼 검증 (ETL 후)

데이터 입력 후 확인할 9건:

| # | 의미 | 후보 컬럼 | 검증 방법 |
|---|------|----------|----------|
| 1 | 이동시간 | moving_time_sec, duration_sec, elapsed_time_sec | 값 비교 후 duration_sec 제거 검토 |
| 2 | 고도하강 | elevation_loss, total_elevation_loss | 값 동일 시 total 제거 |
| 3 | 효율 | icu_efficiency_factor, icu_power_hr, icu_efficiency | 값 동일 시 2개 제거 |
| 4 | 변동성 | icu_variability_index, icu_variability | 값 동일 시 1개 제거 |
| 5 | 걸음수 | steps, total_cycles | 값 동일 시 total_cycles 제거 |
| 6 | 랩수 | lap_count, num_laps_fit | 값 동일 시 num_laps_fit 제거 |
| 7 | 최대파워 | max_power, max_watts | 값 동일 시 max_watts 제거 |
| 8 | 수면시간 | sleep_duration_sec, sleeping_secs | 값 비교 |
| 9 | 수면점수 | sleep_score, sleep_quality | 수치 vs 텍스트 → 둘 다 유지 |
---
## 7. Backfill 전략 (추가)

### 문제
- 기존 496개 garmin 활동: v1 INSERT로 16컬럼만 채워짐
- raw_source_payloads: 14건(3%)만 존재, v2.5 필드 0개
- API 재호출: rate limit (분당 ~25건) → 496건 처리에 ~20분

### 해결
1. **Garmin ZIP export backfill** (최우선)
   - `summarizedActivities.json` (485개, 95필드)
   - API 호출 없이 즉시 ~50컬럼 채우기
   - `python -m src.sync.garmin_backfill --export-dir PATH`
   
2. **API backfill** (보조)
   - ZIP에 없는 detail API 전용 필드 (avgHrGap 등)
   - 배치 처리: 50건씩, 중간 commit
   - `force_update=True` 옵션으로 기존 활동도 detail 재호출

3. **단위 변환 주의사항** (ZIP export)
   - distance: cm → ÷100,000 = km
   - duration/movingDuration: ms → ÷1,000 = sec
   - avgSpeed/maxSpeed: ×10 = m/s
   - elevation: cm → ÷100 = m
   - hrTimeInZone/powerTimeInZone: ms → ÷1,000 = sec
   - startTimeLocal: epoch ms → ÷1,000 → ISO 8601

### 코드 구조
- `src/sync/garmin_v2_mappings.py` — 공통 매핑 함수
  - `extract_summary_fields_from_api()` — API 응답 → DB 컬럼
  - `extract_summary_fields_from_zip()` — ZIP export → DB 컬럼 (단위 변환 포함)
  - `extract_detail_fields()` — detail API → UPDATE 컬럼
- `src/sync/garmin_backfill.py` — ZIP backfill 실행
  - `backfill_from_zip()` — 기존 활동 UPDATE
  - `backfill_new_activities_from_zip()` — 누락 활동 INSERT
