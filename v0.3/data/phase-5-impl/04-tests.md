# Phase 5 테스트 계획 + 전체 DoD

## 테스트 전략

모든 서비스 테스트는 인메모리 SQLite + fixture 데이터로 실행.
fixture는 db_setup.py로 스키마 생성 후, 테스트 데이터를 INSERT.

## fixture 데이터 구조

tests/conftest.py 또는 tests/fixtures/phase5_fixtures.py에 정의.

create_test_db() 함수:

    1. conn = sqlite3.connect(":memory:")
    2. db_setup.create_tables(conn) 호출하여 스키마 생성
    3. 아래 테스트 데이터 INSERT

활동 2개 (garmin + strava, 같은 활동 = matched_group):

    INSERT INTO activity_summaries
    (source, source_id, matched_group_id, name, activity_type,
     start_time, distance_m, duration_sec, avg_pace_sec_km,
     avg_hr, max_hr, elevation_gain, training_load, suffer_score)
    VALUES
    ('garmin', 'g123', 'group1', '오후 달리기', 'running',
     '2026-04-03T18:00:00Z', 10020, 3135, 312.8,
     155, 178, 120.5, 52.0, NULL),
    ('strava', 's456', 'group1', 'Evening Run', 'running',
     '2026-04-03T18:00:00Z', 10050, 3140, 312.3,
     154, 177, 118.0, NULL, 78)

metric_store — activity scope (RunPulse + 소스):

    scope  scope_id  metric_name              category           provider                 num    text  json                           conf  primary
    act    1         trimp                    rp_load            runpulse:formula_v1      91.2   -     -                              0.9   1
    act    1         hrss                     rp_load            runpulse:formula_v1      95.1   -     -                              0.9   1
    act    1         aerobic_decoupling_rp    rp_efficiency      runpulse:formula_v1      3.2    -     -                              -     1
    act    1         gap_rp                   rp_performance     runpulse:formula_v1      308.5  -     -                              -     1
    act    1         runpulse_vdot            rp_performance     runpulse:formula_v1      48.2   -     -                              0.9   1
    act    1         workout_type             rp_classification  runpulse:rule_v1         -      tempo {"type":"tempo","conf":0.78}   0.78  1
    act    1         trimp                    rp_load            intervals                85.0   -     -                              -     0

metric_store — daily scope:

    scope  scope_id    metric_name  category       provider                 num    json                              conf  primary
    daily  2026-04-03  utrs         rp_readiness   runpulse:formula_v1      72.3   {"components":{"sleep":85,...}}    0.8   1
    daily  2026-04-03  cirs         rp_risk        runpulse:formula_v1      28.1   -                                 -     1
    daily  2026-04-03  crs          rp_readiness   runpulse:formula_v1      65.0   -                                 -     1
    daily  2026-04-03  ctl          rp_load        runpulse:formula_v1      45.2   -                                 -     1
    daily  2026-04-03  atl          rp_load        runpulse:formula_v1      52.1   -                                 -     1
    daily  2026-04-03  tsb          rp_load        runpulse:formula_v1      -6.9   -                                 -     1
    daily  2026-04-03  ramp_rate    rp_load        runpulse:formula_v1      2.3    -                                 -     1
    daily  2026-04-03  acwr         rp_load        runpulse:formula_v1      1.05   -                                 -     1
    daily  2026-04-03  darp_5k      rp_prediction  runpulse:formula_v1      1335   -                                 -     1
    daily  2026-04-03  darp_10k     rp_prediction  runpulse:formula_v1      2790   -                                 -     1
    daily  2026-04-03  darp_half    rp_prediction  runpulse:formula_v1      6130   -                                 -     1
    daily  2026-04-03  darp_marathon rp_prediction runpulse:formula_v1      12900  -                                 -     1

daily_wellness:

    date        sleep_score  sleep_duration_sec  hrv_weekly_avg  hrv_last_night
    2026-04-03  82           25920               39.0            42.0

    resting_hr  body_battery_high  body_battery_low  avg_stress  steps
    52          78                 25                32          8500

## 테스트 파일별 케이스

### tests/test_activity_service.py (~15 tests)

    test_get_activity_list_basic
    test_get_activity_list_filter_type
    test_get_activity_list_filter_date_range
    test_get_activity_list_pagination
    test_get_activity_list_sort
    test_get_activity_list_empty

    test_get_activity_detail_core
    test_get_activity_detail_metrics_by_category
    test_get_activity_detail_source_comparison
    test_get_activity_detail_semantic_groups
    test_get_activity_detail_not_found

    test_get_activity_streams
    test_get_activity_streams_empty

    test_get_activity_trend
    test_get_activity_trend_empty

### tests/test_dashboard_service.py (~10 tests)

    test_get_dashboard_data_full
    test_get_dashboard_data_no_wellness
    test_get_dashboard_data_no_metrics
    test_get_dashboard_readiness_levels
    test_get_dashboard_training_phase

    test_get_pmc_chart_data
    test_get_pmc_chart_data_empty

    test_get_daily_metric_chart
    test_get_daily_metric_chart_empty
    test_get_daily_metric_chart_nonexistent_metric

### tests/test_wellness_service.py (~8 tests)

    test_get_wellness_detail_full
    test_get_wellness_detail_no_date
    test_get_wellness_detail_metrics_by_category
    test_get_wellness_detail_no_data

    test_get_wellness_trend_full
    test_get_wellness_trend_with_gaps
    test_get_wellness_trend_includes_utrs
    test_get_wellness_trend_empty

### tests/test_ai_context.py (~6 tests)

    test_build_daily_briefing_full
    test_build_daily_briefing_no_wellness
    test_build_daily_briefing_no_metrics
    test_build_daily_briefing_format

    test_build_activity_analysis_full
    test_build_activity_analysis_no_rp_metrics

### tests/test_template_helpers.py (~20 tests)

    test_format_distance_km
    test_format_distance_zero
    test_format_distance_none
    test_format_pace_normal
    test_format_pace_zero
    test_format_pace_none
    test_format_duration_under_hour
    test_format_duration_over_hour
    test_format_duration_zero
    test_format_time_prediction
    test_format_speed

    test_interpret_metric_level_utrs
    test_interpret_metric_level_cirs
    test_interpret_metric_level_acwr
    test_interpret_metric_level_all_metrics

    test_metric_level_color_higher_is_better
    test_metric_level_color_lower_is_better
    test_confidence_badge
    test_provider_badge
    test_metric_display_name_found
    test_metric_display_name_not_found

### 예상 테스트 수: ~59 tests

---

## 전체 Phase 5 DoD

### 선행 작업
- [ ] metric_registry.py: 9개 category 수정 완료
- [ ] metric_registry.py: 6개 신규 등록 완료
- [ ] gen_metric_dictionary.py 재실행, 에러 없음
- [ ] 기존 테스트 전체 통과

### 서비스 레이어
- [ ] activity_service.py: 01-service-layer.md의 DoD 전체 통과
- [ ] dashboard_service.py: 01-service-layer.md의 DoD 전체 통과
- [ ] wellness_service.py: 01-service-layer.md의 DoD 전체 통과
- [ ] 모든 서비스가 db_helpers 읽기 함수 또는 직접 SQL만 사용 (쓰기 없음)
- [ ] 모든 metric_store 조회에 is_primary=1 포함 (비교 뷰 제외)
- [ ] scope_id는 항상 TEXT

### AI Context
- [ ] ai_context.py: 02-ai-context.md의 DoD 전체 통과
- [ ] 직접 SQL 없음 (서비스 레이어만 호출)
- [ ] 메트릭 값에 해석 포함

### Template Helpers
- [ ] template_helpers.py: 03-template-helpers.md의 DoD 전체 통과
- [ ] metric_dictionary의 모든 범위 해석 테이블 커버

### 테스트
- [ ] 신규 테스트 ~59개 전체 통과
- [ ] 기존 테스트 ~791개 regression 없음
- [ ] 총 테스트 ~850개

### 코드 품질
- [ ] 기존 뷰 파일 변경 0개
- [ ] computed_metrics 참조 추가 0개
- [ ] distance_km 참조 0개 (서비스 + 헬퍼에서)
