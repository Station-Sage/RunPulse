# Phase 2 상세 설계 — Extractor 모듈

> 소스: [src/sync/extractors/](src/sync/extractors/) | 의존: architecture.md Part 4, phase-1.md
> Extractor는 **DB를 모르는 순수 함수**입니다. JSON을 받아 dict/list를 반환할 뿐이며, DB 저장은 Phase 3 Sync Orchestrator의 책임입니다.

---

## 2-1. 공통 인터페이스

**소스**: [src/sync/extractors/base.py](src/sync/extractors/base.py)

### BaseExtractor 메서드

| 메서드 | 반환 | 저장 대상 | 구현 |
|--------|------|-----------|------|
| `extract_activity_core(raw)` | dict | activity_summaries | abstract |
| `extract_activity_metrics(summary_raw, detail_raw)` | list[MetricRecord] | metric_store (scope=activity) | abstract |
| `extract_activity_laps(detail_raw)` | list[dict] | activity_laps | 기본: [] |
| `extract_activity_streams(streams_raw)` | list[dict] | activity_streams | 기본: [] |
| `extract_best_efforts(raw)` | list[dict] | activity_best_efforts | 기본: [] |
| `extract_wellness_core(date, **raw_payloads)` | dict | daily_wellness | 기본: {} |
| `extract_wellness_metrics(date, **raw_payloads)` | list[MetricRecord] | metric_store (scope=daily) | 기본: [] |
| `extract_fitness(date, raw)` | dict | daily_fitness | 기본: {} — **Phase 5에서 제거 예정** |

### MetricRecord 필드

| 필드 | 타입 | 설명 |
|------|------|------|
| metric_name | str | canonical name (metric_registry.py 기준) |
| category | str | 16개 도메인 카테고리 (architecture.md Part 3) |
| numeric_value | float? | 수치 값 |
| text_value | str? | 텍스트 값 |
| json_value | str? | JSON 직렬화 문자열 |
| raw_name | str? | 소스 원본 필드명 (디버깅용) |
| algorithm_version | str | 기본 "1.0" |
| confidence | float? | 신뢰도 (선택) |

### 설계 결정

**`_metric()` 헬퍼**: `category=` 미전달 시 metric_registry에서 자동 조회. 미등록 메트릭은 `_unmapped` 저장. 값이 모두 None이면 None 반환 → `_collect()`에서 필터링.

**이중 저장 금지**: `extract_activity_core()`에 들어간 컬럼은 `extract_activity_metrics()`에 다시 넣지 않음.

---

## 2-2. Garmin Extractor

**소스**: [src/sync/extractors/garmin_extractor.py](src/sync/extractors/garmin_extractor.py)

### extract_activity_core — activity_summaries 매핑

| activity_summaries 컬럼 | Garmin API 필드 | 비고 |
|-------------------------|----------------|------|
| source | — | "garmin" 고정 |
| source_id | activityId | str 변환 |
| name | activityName | |
| activity_type | activityType.typeKey | normalize_activity_type() |
| start_time | startTimeGMT / startTimeLocal | |
| distance_m | distance | |
| duration_sec | duration | _seconds(): ms/s 자동 판별 |
| moving_time_sec | movingDuration | _seconds() |
| elapsed_time_sec | elapsedDuration | _seconds() |
| avg_speed_ms | averageSpeed | |
| max_speed_ms | maxSpeed | |
| avg_pace_sec_km | averageSpeed | 1000/speed 계산 |
| avg_hr | averageHR | |
| max_hr | maxHR | |
| avg_cadence | averageRunningCadenceInStepsPerMinute | |
| max_cadence | maxRunningCadenceInStepsPerMinute | |
| avg_power | avgPower / averagePower | |
| max_power | maxPower | |
| normalized_power | normPower | **Phase 5에서 metric_store 이동** |
| elevation_gain | elevationGain | |
| elevation_loss | elevationLoss | |
| calories | calories | **Phase 5에서 metric_store 이동** |
| training_effect_aerobic | aerobicTrainingEffect | **Phase 5에서 metric_store 이동** |
| training_effect_anaerobic | anaerobicTrainingEffect | **Phase 5에서 metric_store 이동** |
| training_load | activityTrainingLoad | **Phase 5에서 metric_store 이동** |
| avg_ground_contact_time_ms | avgGroundContactTime / avgGroundContactTimeMilli | |
| avg_stride_length_cm | avgStrideLength / avgStrideLengthCM | _stride_to_cm(): m/cm 자동 변환 |
| avg_vertical_oscillation_cm | avgVerticalOscillation / avgVerticalOscillationCM | |
| avg_vertical_ratio_pct | avgVerticalRatio / avgVerticalRatioPct | |
| start_lat / start_lon | startLatitude / startLongitude | |
| end_lat / end_lon | endLatitude / endLongitude | |
| avg_temperature | avgTemperature / averageTemperature | _celsius_if_available() |
| description | description | |
| event_type | eventType.typeKey | |
| device_name | deviceName / metadataDTO.productDisplayName | _extract_device_name() |
| source_url | activityId | URL 조립 |

### extract_activity_metrics — metric_store 매핑

summary_raw 기반:

| metric_name | category | Garmin API 필드 |
|-------------|----------|----------------|
| vo2max_activity | capacity | vO2MaxValue |
| steps_activity | volume | steps |
| perceived_exertion | (미정의) | averageRPE |
| body_battery_diff | body | differenceBodyBattery |
| intensity_mins_moderate | load | moderateIntensityMinutes |
| intensity_mins_vigorous | load | vigorousIntensityMinutes |
| training_stress_score | load | trainingStressScore |
| intensity_factor | load | intensityFactor |
| ground_contact_balance | running_dynamics | avgGroundContactBalance |
| lactate_threshold_hr | capacity | lactateThresholdBpm |
| lactate_threshold_speed | capacity | lactateThresholdSpeed |
| performance_condition | load | performanceCondition |
| avg_respiration_rate | running_dynamics | averageRespirationRate |
| avg_spo2 | sleep | avgSpo2 |
| min_spo2 | sleep | minSpo2 |
| timezone_offset | meta | timeZoneUnitDTO.offset |

detail_raw 기반 (`_extract_detail_metrics`):

| metric_name | category | Garmin API 필드 |
|-------------|----------|----------------|
| hr_zone_{1-5}_sec | hr | hrTimeInZone[i].secsInZone |
| hr_zones_detail | hr | hrTimeInZone (JSON) |
| power_zone_{1-7}_sec | power | powerTimeInZone[i].secsInZone |
| power_zones_detail | power | powerTimeInZone (JSON) |
| weather_temp_c | weather | weatherDTO.temp |
| weather_humidity_pct | weather | weatherDTO.relativeHumidity |
| weather_wind_speed_ms | weather | weatherDTO.windSpeed |
| weather_wind_direction_deg | weather | weatherDTO.windDirection |
| weather_dew_point_c | weather | weatherDTO.dewPoint |
| splits_metric | meta | splitSummaries (JSON) |

### extract_wellness_core — daily_wellness 매핑

| daily_wellness 컬럼 | Garmin API 소스 | 필드 |
|--------------------|----------------|------|
| sleep_score | sleep_day | overallScore / sleepScores.overall |
| sleep_duration_sec | sleep_day | sleepTimeSeconds |
| sleep_start_time | sleep_day | sleepStartTimestampGMT |
| hrv_weekly_avg | hrv_day | hrvSummary.weeklyAvg |
| hrv_last_night | hrv_day | hrvSummary.lastNightAvg / lastNight5MinHigh |
| resting_hr | hrv_day / user_summary_day | restingHeartRate (hrv 우선) |
| body_battery_high | body_battery_day | max(bodyBatteryLevel) / bodyBatteryHigh |
| body_battery_low | body_battery_day | min(bodyBatteryLevel) / bodyBatteryLow |
| avg_stress | stress_day | overallStressLevel / avgStressLevel |
| steps | user_summary_day | totalSteps |
| active_calories | user_summary_day | activeKilocalories |

### extract_wellness_metrics — metric_store 매핑 (scope=daily)

| metric_name | category | API 소스 | API 필드 |
|-------------|----------|---------|---------|
| sleep_deep_sec | sleep | sleep_day | deepSleepSeconds |
| sleep_light_sec | sleep | sleep_day | lightSleepSeconds |
| sleep_rem_sec | sleep | sleep_day | remSleepSeconds |
| sleep_awake_sec | sleep | sleep_day | awakeSleepSeconds |
| avg_respiration_sleep | sleep | sleep_day | averageRespiration |
| avg_spo2 | sleep | sleep_day | averageSpO2Value |
| sleep_deep_score | sleep | sleep_day | sleepScores.deep |
| sleep_rem_score | sleep | sleep_day | sleepScores.rem |
| sleep_recovery_score | sleep | sleep_day | sleepScores.recovery |
| stress_high_duration_sec | stress | stress_day | highStressDuration |
| stress_medium_duration_sec | stress | stress_day | mediumStressDuration |
| stress_low_duration_sec | stress | stress_day | lowStressDuration |
| stress_rest_duration_sec | stress | stress_day | restStressDuration |
| training_readiness_score | readiness | training_readiness | score |
| training_readiness_level | readiness | training_readiness | level (text) |
| training_readiness_sleep_factor | readiness | training_readiness | sleepScoreFactorPercent |
| training_readiness_hrv_factor | readiness | training_readiness | hrvFactorPercent |
| training_readiness_recovery_factor | readiness | training_readiness | recoveryFactorPercent |
| race_pred_5k_sec | prediction | race_predictions | raceTime5K |
| race_pred_10k_sec | prediction | race_predictions | raceTime10K |
| race_pred_half_sec | prediction | race_predictions | raceTimeHalf |
| race_pred_marathon_sec | prediction | race_predictions | raceTimeMarathon |
| hrv_status | (미정의) | hrv_day | status (text) |
| hrv_baseline_low | hr | hrv_day | baselineLowUpper |
| hrv_baseline_balanced_low | hr | hrv_day | baselineBalancedLow |
| hrv_baseline_balanced_upper | hr | hrv_day | baselineBalancedUpper |
| floors_climbed | body | user_summary_day | floorsAscended |
| total_calories | body | user_summary_day | totalKilocalories |

### extract_fitness (daily_fitness — Phase 5에서 metric_store 이동)

| daily_fitness 컬럼 | Garmin API 필드 |
|-------------------|----------------|
| vo2max | vo2MaxValue / vo2max |

---

## 2-3. Strava Extractor

**소스**: [src/sync/extractors/strava_extractor.py](src/sync/extractors/strava_extractor.py)

### extract_activity_core — activity_summaries 매핑

| activity_summaries 컬럼 | Strava API 필드 | 비고 |
|------------------------|----------------|------|
| source | — | "strava" 고정 |
| source_id | id | str 변환 |
| name | name | |
| activity_type | type | normalize_activity_type() |
| start_time | start_date_local / start_date | |
| distance_m | distance | |
| duration_sec | elapsed_time | |
| moving_time_sec | moving_time | |
| elapsed_time_sec | elapsed_time | |
| avg_speed_ms | average_speed | |
| max_speed_ms | max_speed | |
| avg_pace_sec_km | average_speed | 계산 |
| avg_hr | average_heartrate | |
| max_hr | max_heartrate | |
| avg_cadence | average_cadence | |
| avg_power | average_watts / weighted_average_watts | |
| max_power | max_watts | |
| normalized_power | weighted_average_watts | **Phase 5에서 metric_store 이동** |
| elevation_gain | total_elevation_gain | |
| calories | calories | **Phase 5에서 metric_store 이동** |
| suffer_score | suffer_score | **Phase 5에서 metric_store 이동** |
| start_lat / start_lon | start_latlng[0] / [1] | |
| end_lat / end_lon | end_latlng[0] / [1] | |
| avg_temperature | average_temp | |
| description | description | |
| event_type | workout_type | |
| device_name | device_name | |
| gear_id | gear_id | |
| source_url | id | URL 조립 |

### extract_activity_metrics — metric_store 매핑

| metric_name | category | Strava API 필드 |
|-------------|----------|----------------|
| kilojoules | (미정의) | kilojoules |
| perceived_exertion | (미정의) | perceived_exertion |
| achievement_count | meta | achievement_count |
| pr_count | meta | pr_count |
| kudos_count | meta | kudos_count |
| timezone_offset | meta | timezone (text) |
| segment_efforts | meta | segment_efforts (JSON, 최대 20개) |
| splits_metric | meta | splits_metric (JSON) |

### extract_activity_streams / extract_best_efforts

`extract_activity_streams`: Strava Streams API (`time`, `latlng`, `heartrate`, `cadence`, `watts`, `altitude`, `velocity_smooth`, `grade_smooth`, `temp`) → activity_streams 행 리스트.

`extract_best_efforts`: `best_efforts[]` → activity_best_efforts 행 리스트. 필드: effort_name, elapsed_sec, distance_m, start_index, end_index, pr_rank.

---

## 2-4. Intervals Extractor

**소스**: [src/sync/extractors/intervals_extractor.py](src/sync/extractors/intervals_extractor.py)

### extract_activity_core — activity_summaries 매핑

| activity_summaries 컬럼 | Intervals API 필드 | 비고 |
|------------------------|-------------------|------|
| source | — | "intervals" 고정 |
| source_id | id | str 변환 |
| name | name | |
| activity_type | type | normalize_activity_type() |
| start_time | start_date_local / start_date | |
| distance_m | distance | |
| duration_sec | elapsed_time / icu_total_time | |
| moving_time_sec | moving_time / icu_moving_time | |
| elapsed_time_sec | elapsed_time | |
| avg_speed_ms | average_speed / 계산 | 없으면 distance/moving_time |
| max_speed_ms | max_speed | |
| avg_pace_sec_km | avg_speed | 계산 |
| avg_hr | average_heartrate / icu_average_hr | |
| max_hr | max_heartrate / icu_max_hr | |
| avg_cadence | avg_run_cadence / average_cadence | |
| avg_power | icu_weighted_avg_watts / average_watts | |
| max_power | max_watts / icu_max_watts | |
| normalized_power | icu_weighted_avg_watts | **Phase 5에서 metric_store 이동** |
| elevation_gain | total_elevation_gain | |
| elevation_loss | total_elevation_loss | |
| calories | calories / icu_calories | **Phase 5에서 metric_store 이동** |
| training_load | icu_training_load | **Phase 5에서 metric_store 이동** |
| avg_stride_length_cm | average_stride | _stride_cm(): m→cm |
| start_lat / start_lon | start_latlng[0] / [1] | |
| avg_temperature | icu_average_temp / average_temp | |
| description | description | |
| event_type | workout_type | |
| device_name | device_name | |
| gear_id | gear_id | |
| source_url | id | URL 조립 |

### extract_activity_metrics — metric_store 매핑

| metric_name | category | Intervals API 필드 |
|-------------|----------|-------------------|
| trimp | load | icu_trimp |
| hrss | load | icu_hrss |
| efficiency_factor | efficiency | icu_efficiency_factor |
| aerobic_decoupling | efficiency | icu_decoupling |
| variability_index | efficiency | icu_variability_index |
| icu_ftp | power | icu_ftp |
| gap | capacity | icu_gap |
| icu_rpe | load | icu_rpe |
| icu_feel | load | icu_feel |
| hr_zone_{1-5}_sec | hr | icu_hr_zone_times[i] |
| hr_zones_detail | hr | icu_hr_zone_times (JSON) |
| power_curve | power | icu_power_curve (JSON) |
| weather_temp_c | weather | icu_weather_temp |
| weather_humidity_pct | weather | icu_weather_humidity |
| weather_wind_speed_ms | weather | icu_weather_wind_speed |

### extract_wellness_core — daily_wellness 매핑

| daily_wellness 컬럼 | Intervals API 필드 |
|--------------------|-------------------|
| sleep_score | sleepQuality |
| sleep_duration_sec | sleepSecs |
| hrv_last_night | hrv |
| resting_hr | restingHR |
| weight_kg | weight |
| steps | steps |

### extract_fitness (daily_fitness — Phase 5에서 metric_store 이동)

| daily_fitness 컬럼 | Intervals API 필드 |
|-------------------|-------------------|
| ctl | ctl |
| atl | atl |
| tsb | tsb |
| ramp_rate | rampRate |

---

## 2-5. Runalyze Extractor

**소스**: [src/sync/extractors/runalyze_extractor.py](src/sync/extractors/runalyze_extractor.py)

### extract_activity_core — activity_summaries 매핑

| activity_summaries 컬럼 | Runalyze API 필드 | 비고 |
|------------------------|-----------------|------|
| source | — | "runalyze" 고정 |
| source_id | id | str 변환 |
| name | title / name | |
| activity_type | sport.name | normalize_activity_type() |
| start_time | datetime / start_time | |
| distance_m | distance / distance_km×1000 | |
| duration_sec | s / duration | |
| moving_time_sec | elapsed_time | |
| avg_speed_ms | 계산 | distance/duration |
| avg_pace_sec_km | 계산 | |
| avg_hr | pulse_avg / avg_hr | |
| max_hr | pulse_max / max_hr | |
| avg_cadence | cadence | |
| avg_power | power | |
| elevation_gain | elevation / elevation_gain | |
| calories | kcal / calories | **Phase 5에서 metric_store 이동** |
| training_load | trimp | **Phase 5에서 metric_store 이동. trimp값을 training_load에 매핑** |
| avg_temperature | temperature | |
| description | notes | |
| source_url | id | URL 조립 |

### extract_activity_metrics — metric_store 매핑

| metric_name | category | Runalyze API 필드 |
|-------------|----------|-----------------|
| effective_vo2max | capacity | vo2max |
| vdot | capacity | vdot |
| marathon_shape | capacity | marathonShape |
| trimp | load | trimp |
| race_pred_5k_sec | prediction | racePredictions.5k / predictions.5k |
| race_pred_10k_sec | prediction | racePredictions.10k / predictions.10k |
| race_pred_half_sec | prediction | racePredictions.half / predictions.half |
| race_pred_marathon_sec | prediction | racePredictions.marathon / predictions.marathon |

---

## 2-6. 팩토리 & 파일 구조

**소스**: [src/sync/extractors/__init__.py](src/sync/extractors/__init__.py)

`get_extractor(source: str) → BaseExtractor` — 소스 이름(case-insensitive)으로 Extractor 인스턴스 반환. 미지원 소스 시 KeyError.

    src/sync/extractors/
    ├── __init__.py            # EXTRACTORS dict + get_extractor()
    ├── base.py                # MetricRecord + BaseExtractor
    ├── garmin_extractor.py    # GarminExtractor (activity + wellness + fitness)
    ├── strava_extractor.py    # StravaExtractor (activity + streams + best_efforts)
    ├── intervals_extractor.py # IntervalsExtractor (activity + wellness + fitness)
    └── runalyze_extractor.py  # RunalyzeExtractor (activity)

    src/utils/activity_types.py  # normalize_activity_type() — 5개 운동 유형 통일

---

## 2-7. 테스트 전략

**소스**: `tests/test_*_extractor.py`, `tests/test_extractors_cross.py`

| 테스트 파일 | 검증 대상 |
|------------|---------|
| test_extractor_base.py | MetricRecord, _metric(), _collect() |
| test_garmin_extractor.py | activity_core 필수 필드, metrics category, wellness |
| test_strava_extractor.py | activity_core, metrics, streams, best_efforts |
| test_intervals_extractor.py | activity_core, metrics, wellness |
| test_runalyze_extractor.py | activity_core, metrics |
| test_activity_types.py | normalize_activity_type() |
| test_extractors_cross.py | 소스 간 일관성 (동일 컬럼명, 단위 통일) |

Fixture: `tests/fixtures/api/{garmin,strava,intervals,runalyze}/` — 익명화된 실제 API 응답 JSON.

---

## 2-8. 완료 기준 (DoD)

| # | 완료 기준 | 상태 |
|---|----------|------|
| 1 | 4개 extractor가 BaseExtractor 상속 | ✅ |
| 2 | `get_extractor("garmin")` 팩토리 정상 동작 | ✅ |
| 3 | extract_activity_core() 반환 key가 activity_summaries 컬럼명과 일치 | ✅ |
| 4 | extract_activity_core()에 source, source_id, activity_type, start_time 포함 | ✅ |
| 5 | extract_activity_metrics() MetricRecord.metric_name이 activity_summaries 컬럼명과 겹치지 않음 | ✅ |
| 6 | 모든 MetricRecord에 category 설정됨 | ✅ |
| 7 | distance_m 미터 단위 통일 | ✅ |
| 8 | _seconds() ms/s 자동 판별 | ✅ |
| 9 | fixture 기반 단위 테스트 전체 통과 | ✅ |
| 10 | Cross-extractor 일관성 테스트 통과 | ✅ |

**Phase 2 완료일: 2026-04-03** — 테스트 83개 전체 통과. 누적 147 tests (Phase 1: 64 + Phase 2: 83)  
**Phase 2 후속 정리: 2026-04-07** — M-1~M-5 수정 완료. 795 tests 전체 통과.

---

## 2-9. 구현 결과 & 설계 대비 변경 로그

**변경 1 — Strava normalized_power 위치**: 설계에서 extract_activity_metrics로 계획했으나, activity_summaries 컬럼 중복 저장 금지 원칙에 따라 extract_activity_core로 이동. Strava `weighted_average_watts` → `normalized_power` 컬럼.

**변경 2 — get_extractor() 추가**: `__init__.py`에 팩토리 함수 추가. case-insensitive 처리.

**변경 3 — test_extractors_cross.py 신규**: 설계 산출물 목록에 없던 cross-extractor 일관성 테스트 파일 추가.

**변경 4 — activity_types.py 분리**: `normalize_activity_type()`를 4개 extractor가 공통 사용하므로 `src/utils/activity_types.py`로 분리. 5개 운동 유형(running, cycling, swimming, walking, strength).

