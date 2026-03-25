# Changelog History (v0.2)

> 최신 3회분은 `changelog.md` 참조. 이 파일은 그 이전 이력 보관용.

---

## [v0.2-sprint5-pipeline] 2026-03-25

### 추가

**데이터 계층 아키텍처 (D-V2-16)**
- 4계층 데이터 모델 확립: 서비스 데이터 / 서비스 1차 메트릭 / RunPulse 1차 메트릭 / RunPulse 2차 메트릭
- RunPulse 2차 메트릭 계산 시 모든 소스(서비스 데이터, 외부 API 등) 입력 허용, 결과 저장은 `computed_metrics` 분리

**동기화 인프라 — 병렬 기간 동기화**
- `src/web/helpers.py`: `startBgSyncMulti()` — 선택한 서비스를 동시 병렬 시작 (기존 단독 제한 해제)
- `src/web/sync_ui.py`: `bg-jobs-container` — 서비스별 독립 progress row 렌더링

**Garmin 신규 데이터 수집**
- `garmin_api_extensions.py`: `sync_activity_weather`, `sync_activity_hr_zones`, `sync_activity_power_zones`
- `garmin_daily_extensions.py`: `sync_daily_hydration`, `sync_daily_weigh_ins`, `sync_daily_running_tolerance`

**Strava 신규 데이터 수집**
- `strava_activity_sync.py`: `_sync_activity_zones` (HR/Power 존별 시간 → `activity_detail_metrics`)

**Intervals.icu 데이터 확장**
- `intervals_activity_sync.py`: `start_lat/start_lon`, `_sync_power_curve` 추가

**DB 스키마 확장**
- `activity_summaries`: `workout_type INTEGER`, `trainer INTEGER`, `commute INTEGER` 컬럼 추가

**신규 RunPulse 2차 메트릭**
- `src/metrics/rtti.py`: RTTI (러닝 내성 훈련 지수) — Garmin running_tolerance_load / optimal_max * 100
- `src/metrics/wlei.py`: WLEI (날씨 가중 노력 지수) — TRIMP × 기온/습도 스트레스 계수
- `src/metrics/tpdi.py`: TPDI (실내/야외 퍼포먼스 격차) — trainer 컬럼 × FEARP 격차

### 개선

**메트릭 계산 정확도 향상**
- `fearp.py`: 서비스 날씨 데이터(activity_detail_metrics.weather_*) 우선 사용, 없으면 Open-Meteo fallback
- `tids.py`: zone 소스 우선순위 확장 (`hr_zone_N_sec` → `heartrate_zone_N_sec` → `hr_zone_time_N`)
- `relative_effort.py`: 동일 zone 소스 우선순위 fallback 적용
- `engine.py`: WLEI(활동별), RTTI/TPDI(일별) 등록

### 테스트

- `tests/test_metrics_sprint5.py`: RTTI/WLEI/TPDI 14개 테스트 (전체 839개 통과)
- `tests/test_sync_strava.py`: zones API 추가분 mock 업데이트
- `tests/test_sync_intervals.py`: start_latlng 저장 테스트 추가

---

## [v0.2-api-strava-intervals] 2026-03-24

### 추가

**Strava + Intervals.icu 전체 API 수집 완성 — Garmin 방식 모듈 분리 + 누락 API 구현**

**Strava 모듈 분리**
- `strava_auth.py` — 토큰 관리, 연결 확인
- `strava_activity_sync.py` — 활동 list/detail/streams/laps/best_efforts (295줄)
- `strava_athlete_sync.py` — 선수 프로필/통계/기어
- `strava.py` — 하위 호환 re-export wrapper + `sync_strava()` 통합 함수

**Intervals.icu 모듈 분리**
- `intervals_auth.py` — 인증, 연결 확인
- `intervals_activity_sync.py` — 활동 list/intervals/streams (290줄)
- `intervals_wellness_sync.py` — 웰니스/피트니스 동기화
- `intervals_athlete_sync.py` — 선수 프로필/통계 스냅샷
- `intervals.py` — 하위 호환 re-export wrapper + `sync_intervals()` 통합 함수

### 테스트
- 전체 테스트: 803개 → 822개 통과

---

## [v0.2-api-garmin] 2026-03-24

### 추가

**Garmin 전체 API 수집 완성 — DB 스키마 + 3개 신규 모듈**

- `activity_summaries` 18→80컬럼, `activity_laps` 13→36컬럼
- 신규 테이블: `activity_streams`, `activity_best_efforts`, `activity_exercise_sets`, `athlete_profile`, `athlete_stats`, `gear`
- `garmin_api_extensions.py`: streams/gear/exercise_sets
- `garmin_daily_extensions.py`: race_predictions/training_status/fitness_metrics/user_summary/heart_rates/stress/body_battery
- `garmin_athlete_extensions.py`: profile/stats/personal_records

### 테스트
- 전체 797개 통과

---

## [v0.2-ui-gap-7] 2026-03-24

- Strava Archive Import UI (`views_import.py`)
- Phase UI-Gap 6.1~6.3 완료 표시, 6.4~6.8 이연 표시

---

## [v0.2-ui-gap-6.1~6.3] 2026-03-23

- Dashboard 보완 (`views_dashboard_cards.py`): 훈련 권장/UTRS 요인/CIRS 분해/위험도 pill/DARP mini/피트니스 카드
- Activity Detail 보완: classification badge/DI/FEARP 분해/Decoupling/map placeholder
- Report 보완 (`views_report_sections.py`): TIDS/TRIMP 주별/위험도/지구력/DARP/피트니스/AI 인사이트/내보내기

---

## [v0.2-sprint4C] 2026-03-23

- `/report` 분석 레포트 블루프린트 (기간 탭, 요약 카드, ECharts 바차트, 메트릭 테이블)
- 활동 상세 2차 메트릭 섹션 (FEARP/GAP/NGP/RE/Decoupling/EF/TRIMP)

---

## [v0.2-sprint4B] 2026-03-23

- `templates/base.html` Jinja2 공통 레이아웃
- `views_dashboard.py`, `views_settings.py` → `render_template` 전환

---

## [v0.2-sprint4A] 2026-03-23

- ECharts CDN 교체 (Chart.js →), `bottom_nav()` 7탭, 다크 테마 CSS

---

## [v0.2-phase2] 2026-03-23

- `POST /metrics/recompute` + sync 후 자동 재계산

---

## [v0.2-sprint3] 2026-03-23

- 통합 대시보드 블루프린트 (UTRS/CIRS 게이지, RMR 레이더, PMC 차트)

---

## [v0.2-sprint2] 2026-03-23

- 복합 메트릭 8개 (TRIMP/ACWR/Monotony/UTRS/CIRS/Decoupling/DI/DARP/RMR) + engine

---

## [v0.2-sprint1] 2026-03-23

- DB 확장 + 단순 메트릭 8개 (GAP/NGP/LSI/FEARP/ADTI/TIDS/RelativeEffort/MarathonShape)
- Open-Meteo 날씨 API
