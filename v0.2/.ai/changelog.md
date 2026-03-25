# Changelog

> 이전 이력은 `changelog_history.md` 참조

## [v0.2-sprint6-final] 2026-03-25

### 추가

**V2-9-6: 웹 뷰 통합 테스트 37개**
- `tests/test_web_dashboard.py` (12개): 기본 렌더링, DB 미존재, 활동/메트릭 시드, PMC/RMR 카드, resync 배너, /analyze/* 리다이렉트
- `tests/test_web_report.py` (11개): 기간 파라미터(week/month/3month), 폴백, 요약 카드, 주별 차트, 메트릭 테이블, 탭
- `tests/test_web_race.py` (14개): 거리 선택기(5K/10K/하프/풀), DARP/DI/페이스전략/HTW 카드, no-data 처리

**V2-9-7: /analyze/* 레거시 경로 리다이렉트**
- `src/web/app.py`: `/analyze/today` → `/dashboard`, `/analyze/full` → `/report`, `/analyze/race` → `/race`
- `src/web/helpers.py`: 네비게이션 메뉴 링크 신규 경로로 업데이트

**V2-9-9: Mapbox 토큰 설정**
- `src/web/views_settings.py`: 설정 페이지에 Mapbox 토큰 입력/저장 섹션 추가
- `config.json.example`: `mapbox.token` 키 추가
- `src/web/views_activity_cards.py`: 토큰 존재 시 Mapbox GL JS 지도 렌더링

### 테스트
- 전체 829개 통과 (기존 792 + 신규 37)

---

## [v0.2-sprint5-audit] 2026-03-25

### API 데이터 감사 후 수정

**Bug #1: Garmin athlete_profile 컬럼명 오류**
- `garmin_athlete_extensions.py`: `first_name`→`firstname`, `last_name`→`lastname`, `username`/`profile_medium` 제거, `source_athlete_id` 추가
- `activity_best_efforts` INSERT: `effort_name` → `name` (실제 컬럼명 일치)

**Bug #2: Garmin ZIP zone time 루프 데드코드**
- `garmin_v2_mappings.py`: `extract_summary_fields_from_zip`에서 `hrTimeInZone_N`/`powerTimeInZone_N` 루프가 key 변수만 만들고 버림 → 실제 리스트 빌드 후 `_hr_zone_times`/`_power_zone_times`로 반환
- `garmin_backfill.py`: 특수 키 pop 후 `activity_detail_metrics`에 zone time 저장

**Bug #3: Strava elevation_loss 미저장**
- `strava_activity_sync.py`: `total_elevation_loss` → `elevation_loss` 컬럼에 INSERT/UPDATE 추가

**Bug #4: Intervals avg_power = normalized_power 동일값**
- `intervals_activity_sync.py`: `avg_power` = `icu_average_watts`(평균), `normalized_power` = `icu_weighted_avg_watts`(가중평균 NP)로 분리

**Bug #5: Intervals wellness stress_avg/body_battery 미저장**
- `intervals_wellness_sync.py`: `avgStress`→`stress_avg`, `bodyBattery`→`body_battery` INSERT 추가

**Check #6: Garmin extract_detail_fields 인자 순서 역전**
- `garmin_activity_sync.py`: `extract_detail_fields(act, detail)` → `extract_detail_fields(detail, act)` 수정
- Running Dynamics 필드들이 실제로 저장되지 않던 근본 원인 수정

**Check #7: Garmin ZIP avgVerticalOscillation 단위 mm→cm**
- `garmin_v2_mappings.py`: ZIP export는 mm 단위 → `/10`으로 cm 변환

**신규 필드 추가**
- `db_setup.py`: `activity_summaries`에 `session_rpe`, `strain_score`, `polarization_index`, `perceived_exertion` 컬럼 추가 + 마이그레이션
- `intervals_activity_sync.py`: `lap_count(icu_lap_count)`, `session_rpe`, `strain_score`, `polarization_index` → `activity_summaries` INSERT/UPDATE
- `strava_activity_sync.py`: `perceived_exertion` → detail UPDATE

---

## [v0.2-sprint5-bugfix] 2026-03-25

### 버그 수정

**활동 목록 — matched_group_id hex 오분류**
- `unified_activities.py` Step2 쿼리에 `is_group` 플래그 추가
- `'66588299'` 같이 숫자처럼 보이는 8자리 hex group ID가 `solo_id`로 오분류되어 활동 미표시되는 버그 수정

**활동 상세 — 서비스별 1차 메트릭 누락**
- `_load_service_metrics`: 대표(Garmin) row 1개만 조회 → 그룹 전체 소스별 row 각각 조회
- Strava `suffer_score`, Intervals `icu_atl/ctl/tsb/intensity` 전부 "—"으로 표시되던 버그 수정
- `activity_summaries`에 `icu_intensity` 컬럼 추가 + intervals sync에서 저장

**활동 상세 — no such column 오류**
- `training_load_acute/chronic` (Garmin API에서 제공 안 함) → `training_load` 단일 컬럼으로 교체
- `icu_intensity` 컬럼 DB 추가 및 마이그레이션

**대시보드 활동 링크 → Not Found**
- `views_dashboard_cards.py`: `/activity?id=` → `/activity/deep?id=` 수정

**API 로그 정리**
- `api.py`: 4xx 응답은 `[API]` 로그 출력 안 함 (caller가 처리)
- `intervals_activity_sync.py`: intervals/streams/power_curve 404 로그 억제
- `strava_activity_sync.py`: zones 402/404, streams 404 로그 억제

**병렬 동기화 req_count 추정치 수정**
- strava: `count * 3 + 1` → `count * 4 + 1` (zones 추가 반영)
- intervals: `count + 1` → `count * 3 + 1` (intervals + streams + power_curve 반영)
- runalyze: `count + 1` → `count * 2 + 1` (detail 반영)
