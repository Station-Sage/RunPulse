# Changelog

## [v0.2-api-strava-intervals] 2026-03-24

### 추가

**Strava + Intervals.icu 전체 API 수집 완성 — Garmin 방식 모듈 분리 + 누락 API 구현**

**Strava 모듈 분리**
- `strava_auth.py` — 토큰 관리, 연결 확인 (`refresh_token`, `check_strava_connection`)
- `strava_activity_sync.py` — 활동 list/detail/streams/laps/best_efforts (295줄)
- `strava_athlete_sync.py` — 선수 프로필/통계/기어 (`sync_athlete_profile`, `sync_athlete_stats`, `sync_gear`, `sync_athlete_and_gear`)
- `strava.py` — 하위 호환 re-export wrapper + `sync_strava()` 통합 함수

**Strava 데이터 수집 개선**
- 활동 INSERT 컬럼 15개 → 29개 (name, sport_type, moving/elapsed_time_sec, avg/max_speed_ms, kudos_count, achievement_count, pr_count, suffer_score, strava_gear_id, end_lat/lon, avg_power, normalized_power)
- 스트림: 파일 저장 → `activity_streams` DB 테이블 (stream_type별 행)
- best_efforts: JSON 블롭 → `activity_best_efforts` 테이블 (개별 행, pr_rank 포함)
- laps: 중복 코드 제거 + avg/max_speed_ms 컬럼 추가
- 신규 API: `GET /athlete`, `GET /athletes/{id}/stats`, `GET /gear/{id}`
- 미수집 기어 자동 동기화 (`sync_athlete_and_gear`)

**Intervals.icu 모듈 분리**
- `intervals_auth.py` — 인증, 연결 확인 (`base_url`, `auth`, `check_intervals_connection`)
- `intervals_activity_sync.py` — 활동 list/intervals/streams (290줄)
- `intervals_wellness_sync.py` — 웰니스/피트니스 동기화
- `intervals_athlete_sync.py` — 선수 프로필/통계 스냅샷
- `intervals.py` — 하위 호환 re-export wrapper + `sync_intervals()` 통합 함수

**Intervals.icu 데이터 수집 개선**
- INSERT 바인딩 버그 수정 (15 `?` / 16값 불일치 → 사전 3개 테스트 실패 원인 해결)
- 활동 INSERT 컬럼 15개 → 31개 (name, sport_type, moving/elapsed_time_sec, elevation_loss, normalized_power, icu_training_load, icu_trimp, icu_hrss, icu_atl, icu_ctl, icu_tsb, icu_gap, icu_decoupling, icu_efficiency_factor)
- icu_* 필드를 `activity_detail_metrics`와 `activity_summaries` 컬럼에 동시 저장
- 신규 API: `GET /activities/{id}/intervals` → activity_laps, `GET /activities/{id}/streams` → activity_streams, `GET /athlete/{id}` → athlete_profile
- DB 집계 기반 `athlete_stats` 스냅샷

### 테스트
- `test_sync_strava.py` 전면 개편: 2개 → 19개 (스트림 DB저장, best_efforts, laps, suffer_score, athlete_profile, stats, gear)
- `test_auth_strava.py` 업데이트: inspect 테스트를 서브모듈 기준으로 변경 + athlete/stats/gear 엔드포인트 검증 추가
- `test_sync_intervals.py` 전면 개편: 3개 → 19개 (icu_* 컬럼 저장, name 컬럼, 다종목, athlete_profile, stats_snapshot, intervals→laps)
- `test_auth_intervals.py` 업데이트: intervals/streams 엔드포인트 검증 추가, patch 경로 수정
- 전체 테스트: 803개 → 822개 통과 (pre-existing 2개 실패 유지)

---

## [v0.2-api-garmin] 2026-03-24

### 추가

**Garmin 전체 API 수집 완성 — DB 스키마 + 3개 신규 모듈**

**DB 스키마 (`src/db_setup.py`)**
- `activity_summaries` 18컬럼 → 80컬럼 (name, sport_type, running_dynamics, aerobic_training_effect, Strava/Intervals 전용 컬럼 포함)
- `activity_laps` 13컬럼 → 36컬럼 (split_type, GPS 좌표, running_dynamics 전체)
- 신규 테이블: `activity_streams`, `activity_best_efforts`, `activity_exercise_sets`, `athlete_profile`, `athlete_stats`, `gear`
- `daily_wellness` spo2_avg / respiration_avg / intensity_min 컬럼 추가
- `migrate_db()` 기존 DB 자동 마이그레이션 (ALTER TABLE try/except 패턴)

**`src/sync/garmin_api_extensions.py` 신설** (활동 확장 API)
- `sync_activity_streams()` — activity_details GPS/시계열 → activity_streams (metricDescriptors 파싱, executemany 배치 삽입)
- `sync_activity_gear()` — 활동 장비 → gear 테이블 upsert + activity_summaries 링크
- `sync_activity_exercise_sets()` — 운동 세트 (근력/기타 전 종목) → activity_exercise_sets

**`src/sync/garmin_daily_extensions.py` 신설** (일별 확장 API)
- `sync_daily_race_predictions()` — 레이스 예측 기록 5K/10K/하프/마라톤
- `sync_daily_training_status()` — ATL/CTL/ACWR → daily_fitness upsert
- `sync_daily_fitness_metrics()` — endurance_score, hill_score, fitnessage, lactate_threshold(FTP/LTHR)
- `sync_daily_user_summary()` — 94키 종합 요약 → daily_wellness COALESCE 보완
- `sync_daily_heart_rates()` — 일중 HR 타임라인 + max/min/avg
- `sync_daily_all_day_stress()` — 24시간 스트레스 타임라인 (get_all_day_stress)
- `sync_daily_body_battery_events()` — 충전/방전 이벤트 (get_body_battery_events)

**`src/sync/garmin_athlete_extensions.py` 신설** (선수 데이터)
- `sync_athlete_profile()` — user_profile → athlete_profile upsert
- `sync_athlete_stats()` — 누적 통계 스냅샷 → athlete_stats upsert
- `sync_athlete_personal_records()` — PR → activity_best_efforts + daily_detail_metrics

### 수정

**`src/sync/garmin_activity_sync.py`**
- 활동 저장 후 `sync_activity_streams()`, `sync_activity_gear()`, `sync_activity_exercise_sets()` 자동 호출
- 기간동기화 시 `force=True`로 streams 재수집

**`src/sync/garmin_wellness_sync.py`**
- `body_battery_summary_json`, `stress_summary_json`, `respiration_summary_json`, `spo2_summary_json`, `body_composition_summary_json` 누락 복구

**`src/sync/garmin.py`**
- `sync_garmin()` 반환값 `daily_ext` 추가
- `sync_daily_extensions()`, `sync_athlete_extensions()` 함수 추가 — 전체 동기화 시 자동 호출

### 테스트
- 기존 pre-existing 실패 3건 (test_activity_merge, test_sync_intervals, test_auth_runalyze) 외 전체 통과
- garmin 테스트 12개 전부 통과 (body_battery_timeline 테스트 데이터 포맷 수정 포함)
- 전체 797개 통과

---

## [v0.2-ui-gap-7] 2026-03-24

### 추가

**7.3 Strava Archive Import UI** (`views_import.py` 신설)
- `GET/POST /import/strava-archive` — 아카이브 경로 입력 폼 + 임포트 결과 리포트 카드
  - csv_total / inserted / file_linked / csv_only / gz_ok / skipped / errors 항목 표시
  - zip 파일 자동 압축 해제 (zipfile + tempfile), 폴더 경로도 허용
- `POST /import/strava-archive/backfill` — 기존 Strava 활동 FIT/GPX 파일 재연결
  - updated / skipped_no_file / skipped_parse_fail / skipped_not_in_db / gz_ok / errors 항목 표시
- `_render_merge_rules_card()` — 병합 규칙 안내 (7.4): source 우선순위/gzip/timestamp 매칭 규칙
- `src/web/app.py` — `import_bp` 등록
- `src/web/views_settings.py` — Strava 아카이브 임포트 링크 카드 추가

### 점검 (Section 8 — CLAUDE.md 준수)
- 8.1 파일 크기: 신규 views_import.py 311줄 (경계). 기존 app.py/views_activity.py/helpers.py/views_activities.py 300줄 초과 → B-1 리팩토링 항목으로 todo.md 등록
- 8.2 API wrapper: views_settings.py Strava OAuth 토큰 교환에 httpx 직접 사용 (OAuth 예외 케이스, 비기능적 영향 없음)
- 8.3 config 비밀: 하드코딩 없음, update_service_config() 경유 확인
- 8.4 graceful fallback: no_data_card() 29개소 사용 확인
- 8.5 문서-구현 정합성: 6.1~6.3, 7.3 완료 표시, 미구현 항목 todo.md B-1~B-3 등록

### todo.md 업데이트
- Phase UI-Gap 섹션 신설: 6.1~6.3/7.3 완료 표시, 6.4~6.8 이연 표시
- Priority B — 다음 스프린트 항목 3개 추가 (파일크기 리팩토링/graceful fallback/Settings hub)

---

## [v0.2-ui-gap-6.1~6.3] 2026-03-23

### 추가

**6.1 Dashboard 보완** (`views_dashboard_cards.py` 신설 — `views_dashboard.py` 분리)
- `_render_training_recommendation()` — UTRS grade/CIRS/TSB 기반 오늘의 훈련 권장 카드
- `_render_utrs_factors()` 강화 — 5요인 progress bar 형태로 시각화
- `_render_cirs_breakdown()` 신규 — ACWR/Monotony/Spike/Asym 상태 뱃지 + bar
- `_render_risk_pills()` — ACWR/LSI/Monotony/TSB 색상 pill 행
- `_render_darp_mini()` — 5K/10K/하프/마라톤 예측 기록 mini 카드
- `_render_fitness_mini()` — VDOT + Marathon Shape 피트니스 카드
- `templates/dashboard.html` — `recommendation_card`, `risk_pills`, `darp_card`, `fitness_card` 블록 추가
- `views_dashboard.py` — `_load_darp_data()`, `_load_risk_pills()`, `_load_fitness_data()` 신규 데이터 로더

**6.2 Activity Detail 보완** (`views_activity.py`)
- `_load_activity_metric_jsons()` / `_load_day_metric_jsons()` — metric_json 별도 조회
- `_render_activity_classification_badge()` — easy/tempo/interval/long/recovery 자동 분류 뱃지
- `_render_di_card()` — DI 내구성 지수 카드 (점수 + 상태 뱃지 + 해석 문구)
- `_render_fearp_breakdown_card()` — 기온/습도/고도/경사 요인 분해 bar
- `_render_decoupling_detail_card()` — EF + Decoupling % + aerobic stability 판단
- `_render_map_placeholder()` — Mapbox 미설정 시 graceful fallback
- `_render_secondary_metrics_card()` 확장 — DI/LSI/Monotony/ACWR/ADTI/MarathonShape 당일 지표 추가

**6.3 Report 보완** (`views_report_sections.py` 신설 — `views_report.py` 분리)
- `render_tids_section()` — 훈련 강도 분포 (z12/z3/z45 bar + 모델 비교 pill)
- `render_trimp_weekly_chart()` — 주별 TRIMP 부하 ECharts 바차트
- `render_risk_overview()` — ACWR/LSI/Monotony/CIRS 기간 평균/최고값 카드
- `render_endurance_trend()` — ADTI 유산소 분리 추세 방향 카드
- `render_darp_card()` — 레이스 거리별 DARP 예측 기록 카드
- `render_fitness_trend()` — VDOT + Marathon Shape 피트니스 현황 카드
- `render_ai_insight_placeholder()` — AI 코치 인사이트 placeholder 카드
- `render_export_buttons()` — 요약 텍스트 클립보드 복사 버튼

### 테스트
- 797개 통과 (pre-existing 3개 제외)

---

## [v0.2-sprint4C] 2026-03-23

### 추가
- `src/web/views_report.py` — `/report` 분석 레포트 블루프린트
  - 기간 탭 (week/month/3month), 요약 카드 6개, 주별 거리 ECharts 바차트, 메트릭 테이블
- `src/web/views_activity.py` — 2차 메트릭 섹션 추가
  - `_load_activity_computed_metrics`, `_load_day_computed_metrics` DB 조회 함수
  - `_render_horizontal_scroll`: 핵심 메트릭 수평 스크롤 바 (V2-4-6)
  - `_render_secondary_metrics_card`: FEARP/GAP/NGP/RE/Decoupling/EF/TRIMP (V2-4-1~4)
  - `_render_daily_scores_card`: 당일 UTRS/CIRS/ACWR 카드

### 변경
- `src/web/views_activity.py` — `html_page()` → `render_template('generic_page.html')` 전환 (5개 호출)
- `src/web/app.py` — `report_bp` 임포트 및 등록

### 미구현 (이연)
- V2-4-5: Mapbox/Leaflet 지도 → v0.3으로 이연

### 테스트
- 785개 통과 (pre-existing 3개 제외)

---

## [v0.2-sprint4B] 2026-03-23

### 추가
- `templates/base.html` — 공통 Jinja2 레이아웃 (stylesheet/nav_html/sync_js/bottom_nav 주입)
- `templates/dashboard.html` — 대시보드 전용 템플릿 (banner/utrs_card/cirs_card/rmr_card/pmc_chart/activity_list 블록)
- `templates/generic_page.html` — 범용 페이지 래퍼 (title/body/active_tab)
- `templates/macros/no_data.html` — `no_data_card` 매크로
- `templates/macros/gauge.html` — `half_gauge` SVG 매크로 stub (Sprint 4-C에서 구현)
- `templates/macros/radar.html` — `radar_chart` SVG 매크로 stub (Sprint 4-C에서 구현)

### 변경
- `src/web/app.py` — `Flask()` 생성 시 `template_folder` 설정 (프로젝트 루트 `templates/`)
  - `context_processor`: `stylesheet`(CSS), `nav_html`(드롭다운 nav), `sync_js` 전역 주입
  - `jinja_env.globals`: `bottom_nav` 함수 등록
- `src/web/views_dashboard.py` — `html_page()` → `render_template('dashboard.html', ...)` 전환; `html_page`/`bottom_nav` import 제거
- `src/web/views_settings.py` — 6개 엔드포인트 `html_page()` → `render_template('generic_page.html', ...)` 전환; `html_page`/`bottom_nav` import 제거

### 테스트
- 785개 통과 (pre-existing 3개 제외)

---

## [v0.2-sprint4A] 2026-03-23

### 추가
- `src/web/helpers.py` — `bottom_nav(active_tab, dev_mode)` 7탭 하단 네비게이션 함수
- `src/web/helpers.py` — Google Fonts CDN 로드 (Noto Sans KR + Inter)
- `src/web/helpers.py` — ECharts CDN 상수 (`_ECHARTS_CDN`)

### 변경
- `src/web/helpers.py` — 전체 CSS를 ui-spec.md 다크 테마로 교체 (Chart.js → ECharts, 고정 다크)
  - 배경: `linear-gradient(135deg, #1a1a2e→#16213e→#0f3460)`
  - 강조색 CSS 변수: `--cyan #00d4ff`, `--green #00ff88`, `--orange #ffaa00`, `--red #ff4444`
  - `.card`: border-radius 20px, backdrop-filter blur
  - `.bottom-nav`: 7탭 하단 고정 네비게이션 CSS
- `src/web/helpers.py` — `html_page()` signature 확장 (`active_tab`, `dev_mode` 파라미터 추가)
- `src/web/views_dashboard.py` — PMC 차트 Chart.js → ECharts 재작성 (TSB 위험구간 markArea)
- `src/web/views_dashboard.py` — `html_page()` 에 `active_tab='dashboard'` 적용
- `src/web/views_settings.py` — `html_page()` 에 `active_tab='settings'` 적용
- `src/web/views_activities.py` — `html_page()` 에 `active_tab='activities'` 적용

### 테스트
- 785개 통과 (pre-existing 3개 제외)

---

## [v0.2-phase2] 2026-03-23

### 추가
- `src/web/views_settings.py` — `POST /metrics/recompute` 엔드포인트 + 설정 페이지 "메트릭 재계산" 카드
  - 최근 N일(기본 90) 범위 지정 가능, 백그라운드 스레드 실행

### 변경
- `src/sync.py` — sync 완료 후 `metrics_engine.run_for_date_range()` 자동 호출
- `src/web/bg_sync.py` — 백그라운드 배치 완료 후 `metrics_engine.run_for_date_range()` 자동 호출

### 테스트
- 전체 797개 통과 (pre-existing 3개 실패 포함, Phase 2 코드 자체 신규 실패 없음)

---

## [v0.2-sprint3] 2026-03-23

### 추가
- `src/web/views_dashboard.py` — 통합 대시보드 블루프린트
  - UTRS 반원 SVG 게이지 + 하위 5요인 소형 표시
  - CIRS 반원 SVG 게이지 + CIRS≥50/75 경고 배너
  - RMR 5축 SVG 레이더 차트 (3개월 전 오버레이 지원)
  - PMC 차트 (Chart.js CDN, CTL/ATL/TSB 60일)
  - 최근 활동 목록 (FEARP/RelativeEffort 배지)
- `src/web/helpers.py` — SVG/UI 헬퍼 함수 추가
  - `svg_semicircle_gauge()` — 반원 SVG 게이지
  - `svg_radar_chart()` — 5축 SVG 레이더 차트
  - `no_data_card()` — graceful "데이터 수집 중" 카드
  - `fmt_pace()` — 초/km → M'SS" 포맷
  - `html_page()` — Chart.js CDN 자동 로드 추가

### 변경
- `src/web/app.py` — `/` → `/dashboard` 리다이렉트, `/dashboard` 블루프린트 등록
- `tests/test_web_activity.py` — 홈 대시보드 테스트 `/dashboard` 기준으로 업데이트
- `design/.ai/todo.md` — Phase 3 완료 표시

### 테스트
- 전체 803개 통과 (Sprint 2 대비 +1개)

---

## [v0.2-sprint2] 2026-03-23

### 추가
- `src/metrics/trimp.py` — TRIMPexp (Banister 1991) + HRSS 계산. 활동별/일별 저장
- `src/metrics/acwr.py` — ACWR (급성7일 합 / 만성28일 일평균) + 위험 수준 분류
- `src/metrics/monotony.py` — Monotony (평균/표준편차) + Training Strain
- `src/metrics/utrs.py` — UTRS 5요소 가중합 (sleep/hrv/tsb/rhr/sleep_consistency)
- `src/metrics/cirs.py` — CIRS 복합 부상 위험 점수 (ACWR×0.4 + Monotony×0.2 + Spike×0.3 + Asym×0.1)
- `src/metrics/decoupling.py` — Aerobic Decoupling (EF 전/후반 비율) + EF 계수
- `src/metrics/di.py` — DI 내구성 지수 (pace/HR 비율법, 90분+ 세션 3회 이상 요건)
- `src/metrics/darp.py` — DARP 레이스 예측 (Jack Daniels VDOT 역산 + DI 보정)
- `src/metrics/rmr.py` — RMR 러너 성숙도 레이더 (5축: 유산소용량/역치강도/지구력/동작효율성/회복력)
- `src/metrics/engine.py` — 메트릭 배치 오케스트레이터 (활동별 → 일별 → 주별 순서 실행)
- `tests/test_metrics_sprint2.py` — Sprint 2 단위 테스트 67개

### 변경
- `design/.ai/todo.md` — Phase 1 그룹 B 전체 완료 표시

### 테스트
- 전체 802개 통과 (Sprint 1 대비 +150개)

---

## [v0.2-sprint1] 2026-03-23

### 추가
- `src/db_setup.py` — `computed_metrics`, `weather_data`, `activity_laps` 테이블 추가, `migrate_db()` 보강
  - `activity_summaries`에 `start_lat`, `start_lon` 컬럼 추가
- `src/weather/provider.py` — Open-Meteo API 날씨 조회 (무료, 키 없음, 과거/현재 분기)
- `src/metrics/store.py` — computed_metrics UPSERT 헬퍼 (NULL activity_id 안전 처리)
- `src/metrics/gap.py` — GAP + NGP (경사 보정 페이스 / 정규화 경사 페이스)
- `src/metrics/lsi.py` — LSI 부하 스파이크 지수 (TRIMP 우선, distance 폴백)
- `src/metrics/fearp.py` — FEARP 환경 보정 페이스 (기온/습도/고도/경사)
- `src/metrics/adti.py` — ADTI 유산소 분리 추세 (8주 선형 회귀 기울기)
- `src/metrics/tids.py` — TIDS 훈련 강도 분포 (폴라리제드/피라미드/건강유지 모델 비교)
- `src/metrics/relative_effort.py` — Relative Effort (Strava 방식 zone coefficient 가중합)
- `src/metrics/marathon_shape.py` — Marathon Shape (Runalyze 방식 주간/장거리 목표 대비)
- `tests/test_db_v2.py` — DB v2 마이그레이션 테스트 23개
- `tests/test_metrics_sprint1.py` — Sprint 1 메트릭 단위 테스트 49개

### 변경
- `design/.ai/todo.md` — Phase 0, Phase 1 그룹 A 완료 표시
- `design/.ai/roadmap.md` — V3-DB-1/2/3 멀티유저 전략 추가

### 수정
- FEARP 공식: 오르막 grade_factor 분모에 적용 (분자 오류 수정)
- store.py UPSERT: SQLite NULL UNIQUE 미충돌 문제 → SELECT→UPDATE/INSERT 패턴으로 수정
