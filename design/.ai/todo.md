# v0.2 작업 목록
최종 업데이트: 2026-03-25 (문서 정합성 업데이트)

## Sprint 5-F: API 데이터 감사 수정 ✅ 완료 (2026-03-25)

- [x] Bug #1: `garmin_athlete_extensions.py` — `athlete_profile` 컬럼명 수정 (`firstname`/`lastname`/`source_athlete_id`), `activity_best_efforts` `effort_name`→`name`
- [x] Bug #2: `garmin_v2_mappings.py` + `garmin_backfill.py` — ZIP zone time 데드코드 수정, `activity_detail_metrics` 저장
- [x] Bug #3: `strava_activity_sync.py` — `elevation_loss` INSERT/UPDATE 추가
- [x] Bug #4: `intervals_activity_sync.py` — `avg_power` = `icu_average_watts`(평균), `normalized_power` = `icu_weighted_avg_watts`(NP) 분리
- [x] Bug #5: `intervals_wellness_sync.py` — `stress_avg`/`body_battery` INSERT 추가
- [x] Check #6: `garmin_activity_sync.py` — `extract_detail_fields(act, detail)` → `extract_detail_fields(detail, act)` 인자 순서 수정 (Running Dynamics 저장 불량 근본 원인)
- [x] Check #7: `garmin_v2_mappings.py` — ZIP `avgVerticalOscillation` mm→cm (`/10`) 변환
- [x] Intervals cadence ×2: 확인 완료 (half-step 방식으로 ×2 맞음, 변경 없음)
- [x] 신규: `db_setup.py` — `session_rpe`/`strain_score`/`polarization_index`/`perceived_exertion` 컬럼 추가
- [x] 신규: `intervals_activity_sync.py` — `lap_count`/`session_rpe`/`strain_score`/`polarization_index` 저장
- [x] 신규: `strava_activity_sync.py` — `perceived_exertion` detail UPDATE
- [x] Garmin best_efforts: `effort_name`→`name` 수정으로 `sync_athlete_personal_records` 정상 저장
- [x] Strava best_efforts: `_sync_activity_best_efforts` 이미 구현됨 (확인 완료)
- [x] Running Dynamics: Check #6 수정으로 `extract_detail_fields` 올바르게 호출됨 (GCT/VO/VR 정상 저장)

---

최종 업데이트: 2026-03-23 (메트릭 전체 리뷰 반영 — 공식 있는 것 우선순위 반영)

## Phase PERF: 성능 개선 (v0.2 선행 작업) ✅ 완료

- [x] PERF-1: `src/db_setup.py` — 누락 복합 인덱스 + `v_canonical_activities` 뷰 최적화
- [x] PERF-2: `src/services/unified_activities.py` — DB 레벨 2단계 페이지네이션
- [x] PERF-3: `src/web/app.py` — 홈 화면 TTL 캐시 (60초)
- [x] PERF-4: `src/sync.py` + `src/sync/__init__.py` — 4소스 ThreadPoolExecutor 병렬화
- [x] PERF-5: `tests/test_perf.py` — 성능 테스트 15개 (모두 통과)
- [x] PERF-6: `design/.ai/` 문서 업데이트
- [x] PERF-7: git 커밋

---

## 메트릭 전체 현황 (2026-03-23 리뷰)

> **원칙**: 장비 의존 메트릭 제외하고는 모두 todo 또는 로드맵에 포함.
> 공식이 확정된 메트릭은 ML 기반보다 우선순위 높게 배치.

### 1차 메트릭 커버리지

| 메트릭 | 출처 | 상태 | 공식 |
|--------|------|------|------|
| ATL/CTL/TSB (PMC) | 전 서비스 | ✅ v0.2 계획 | 있음 |
| TRIMP / HRSS | 전 서비스 | ✅ v0.2 (V2-1-6) | 있음 |
| rTSS | TrainingPeaks | ✅ v0.2 (TSS 엔진) | 있음 |
| VDOT | Runalyze/TP | ✅ v0.2 (DARP 선행) | 있음 |
| Aerobic Decoupling | Intervals/TP | ✅ v0.2 (V2-1-9) | 있음 |
| GAP (경사 보정 페이스) | Strava/전 서비스 | ✅ v0.2 (V2-1-15) | 있음 |
| NGP (정규화 경사 페이스) | TrainingPeaks | ✅ v0.2 (V2-1-16) | 있음 |
| EF (효율 계수) | Intervals/TP | ✅ v0.2 (V2-1-9 파생, V2-4-4 표시) | 있음 |
| Monotony & Training Strain | 공통 | ✅ v0.2 (V2-1-17, CIRS 파생) | 있음 |
| Relative Effort | Strava | ✅ v0.2 **(V2-1-18 추가)** | 있음 |
| Marathon Shape | Runalyze | ✅ v0.2 **(V2-1-19 추가)** | 있음 |
| Aerobic Training Effect (TE) | Garmin | ✅ v0.2 (V2-4-2, Garmin 수집값) | Garmin 제공 |
| Anaerobic Training Effect | Garmin | ✅ v0.2 (V2-4-4, Garmin 수집값) | Garmin 제공 |
| Training Status (Garmin 원본) | Garmin | ✅ v0.2 (V2-4-4, Garmin 수집값) | Garmin 제공 |
| Body Battery | Garmin | ✅ v0.1 웰니스 | Garmin 제공 |
| Training Readiness | Garmin | ✅ v0.1 웰니스 | Garmin 제공 |
| Running Dynamics (GCT/VO/VR) | Garmin | ✅ v0.2 (V2-4-2) | 있음 |
| eFTP | Intervals.icu | ⏳ v0.3 (V3-1-3) | 있음 |
| Critical Power / W' | 공통 (파워 데이터) | ⏳ v0.3 (V3-1-4) | 있음 |
| PEI (파워 이코노미) | Stryd | ❌ Optional | 있음 (장비 의존) |
| RSS (Stryd) | Stryd | ❌ Optional | 있음 (장비 의존) |

### 2차 메트릭 (RunPulse 고유) 커버리지

| 코드 | 명칭 | 상태 | 공식 |
|------|------|------|------|
| UTRS | 통합 훈련 준비도 | ✅ v0.2 (V2-1-7) | 있음 |
| DI | 내구성 지수 | ✅ v0.2 (V2-1-10) | 있음 |
| CIRS | 복합 부상 위험 | ✅ v0.2 (V2-1-8) | 있음 |
| LSI | 부하 스파이크 | ✅ v0.2 (V2-1-1) | 있음 |
| ACWR | 급성/만성 부하 비율 | ✅ v0.2 (V2-1-5) | 있음 |
| FEARP | 환경 보정 페이스 | ✅ v0.2 (V2-1-2) | 있음 |
| ADTI | 유산소 분리 추세 | ✅ v0.2 (V2-1-3) | 있음 |
| TIDS | 훈련 강도 분배 | ✅ v0.2 (V2-1-4) | 있음 |
| DARP | 내구성 보정 레이스 예측 | ✅ v0.2 (V2-1-11) | 있음 |
| RMR | 러너 성숙도 레이더 | ✅ v0.2 (V2-1-12) | 있음 |
| RTTI | 러닝 내성 훈련 지수 | ✅ v0.2 (Sprint 5-C) | 있음 |
| WLEI | 날씨 가중 노력 지수 | ✅ v0.2 (Sprint 5-C) | 있음 |
| TPDI | 실내/야외 퍼포먼스 격차 | ✅ v0.2 (Sprint 5-C) | 있음 |
| REC | 통합 러닝 효율성 | ⏳ v0.3 (V3-2-1) | 있음 |
| RRI | 레이스 준비도 지수 | ⏳ v0.3 (V3-2-2) | 있음 |
| SAPI | 계절·날씨 성과 비교 | ⏳ v0.3 (V3-2-3) | 있음 |
| TEROI | 훈련 효과 투자 수익률 | ⏳ v0.3 (V3-2-4) | 있음 |
| TQI | 훈련 품질 지수 | ⏳ v0.4+ (V4-1-1) | ML 기반 |
| PLTD | 개인화 역치 자동 탐지 | ⏳ v0.4+ (V4-1-2) | ML 기반 |

---

## 구현 우선순위

- **v0.2 (0-3개월, 공식 확정)**: LSI, GAP, NGP, FEARP, ADTI, TIDS, Relative_Effort, Marathon_Shape + ACWR, TRIMP, UTRS, CIRS, Decoupling, DI, DARP, RMR, Monotony
- **v0.3 (3-6개월, 공식 확정)**: REC, RRI, SAPI, TEROI, eFTP, Critical_Power
- **v0.4+ (6개월+, ML 기반)**: TQI, PLTD
- **Optional (장비 의존)**: PEI, RSS

---

## Phase 0: 기반 준비

- [x] V2-0-1: `src/db_setup.py` — `computed_metrics`, `weather_data`, `activity_laps` 테이블 추가 + migrate_db()
  - `activity_summaries`에 `start_lat`, `start_lon` 컬럼 추가 (FEARP 위치 기반 날씨 조회)
  - `planned_workouts.workout_type` CHECK에 'recovery', 'race' 추가
- [x] V2-0-2: `src/weather/provider.py` — Open-Meteo API 날씨 조회 (무료, 키 없음)
- [x] V2-0-3: `tests/test_db_v2.py` — 새 테이블 마이그레이션 테스트 (23개 통과)

---

## Phase 1: 2차 메트릭 계산 엔진

작업 순서: GAP/NGP → LSI → FEARP → ADTI → TIDS → Relative_Effort → Marathon_Shape → ACWR → TRIMP → Monotony → UTRS → CIRS → Decoupling → DI → DARP → RMR → engine

### 그룹 A: 단순 공식 (0-3개월, 즉시 구현)

- [x] V2-1-15: `src/metrics/gap.py` — GAP + NGP (경사 보정 페이스): Strava 공식
  - `effort_factor = 1 + 0.0333*grade + 0.0001*grade²`; NGP = 4차 멱승 가중 평균
- [x] V2-1-1: `src/metrics/lsi.py` — LSI (부하 스파이크): today_load / rolling_21day_avg
- [x] V2-1-2: `src/metrics/fearp.py` — FEARP (환경 보정 페이스): GAP×기온×습도×고도
- [x] V2-1-3: `src/metrics/adti.py` — ADTI (유산소 분리 추세): 8주 선형 회귀 기울기
- [x] V2-1-4: `src/metrics/tids.py` — TIDS (훈련 강도 분포): 폴라리제드/피라미드/건강유지
- [x] V2-1-18: `src/metrics/relative_effort.py` — Relative Effort (Strava 방식): Σ(zone_coeff × time_in_zone)
  - zone_coefficients = [0.5, 1.0, 2.0, 3.5, 5.5]
- [x] V2-1-19: `src/metrics/marathon_shape.py` — Marathon Shape (Runalyze 방식)
  - `weekly_shape = min(1.0, weekly_km_avg / (vdot * 0.8))`
  - `long_run_shape = min(1.0, longest_run_km / (vdot * 0.35))`
  - `shape_pct = (weekly_shape*2/3 + long_run_shape*1/3) * 100`
- [x] `src/metrics/store.py` — computed_metrics DB 저장/조회 헬퍼 (UPSERT, NULL 처리 포함)
- [x] `tests/test_metrics_sprint1.py` — Sprint 1 메트릭 단위 테스트 49개 (모두 통과)

### 그룹 B: 복합 공식 (0-3개월 후반 ~ 3-6개월)

- [x] V2-1-5: `src/metrics/acwr.py` — ACWR (급성/만성 부하 비율)
- [x] V2-1-6: `src/metrics/trimp.py` — TRIMP 자체 계산 (TRIMPexp + HRSS)
- [x] V2-1-17: `src/metrics/monotony.py` — Monotony & Training Strain (CIRS 파생, 레포트 별도 저장)
  - `monotony = mean(trimp_7d) / std(trimp_7d)`
  - `strain = monotony * sum(trimp_7d)`
- [x] V2-1-7: `src/metrics/utrs.py` — UTRS (통합 훈련 준비도): 5가지 요소 가중합
- [x] V2-1-8: `src/metrics/cirs.py` — CIRS: ACWR×0.4 + Monotony×0.2 + Spike×0.3 + Asym×0.1
- [x] V2-1-9: `src/metrics/decoupling.py` — Aerobic Decoupling + EF 계수 계산 및 저장
- [x] V2-1-10: `src/metrics/di.py` — DI (내구성 지수): pace/HR 비율법, 90분+ 세션 필요
- [x] V2-1-11: `src/metrics/darp.py` — DARP: VDOT 기반 + DI 보정
- [x] V2-1-12: `src/metrics/rmr.py` — RMR: 5개 축 (유산소용량/역치강도/지구력/동작효율성/회복력)
- [x] V2-1-13: `src/metrics/engine.py` — 전체 메트릭 배치 오케스트레이터
- [x] V2-1-14: `tests/test_metrics_sprint2.py` — Sprint 2 메트릭 단위 테스트 67개 (모두 통과)

---

## Phase 2: 동기화 후 메트릭 자동 계산 ✅ 완료 (2026-03-23)

- [x] V2-2-1: `src/sync.py` — sync 완료 후 `engine.run_for_date_range()` 호출
- [x] V2-2-2: `src/web/bg_sync.py` — 백그라운드 sync 완료 후 동일 훅 추가
- [x] V2-2-3: `src/web/views_settings.py` — `POST /metrics/recompute` 엔드포인트 + 설정 페이지 재계산 버튼

---

## Phase 3: 통합 대시보드 UI

- [x] V2-3-1: `src/web/views_dashboard.py` — 대시보드 뷰 블루프린트
  - UTRS/CIRS 반원 게이지 (SVG) + UTRS 하위 요인 5개 소형 표시
  - CIRS > 50/75 경고 배너 (상단 조건부)
  - RMR 레이더 차트 (SVG, 5개 축 + 3개월 전 오버레이)
  - PMC 차트 (Chart.js CDN, CTL/ATL/TSB, 60일)
  - 최근 활동 목록 (FEARP/RelativeEffort 배지)
- [x] V2-3-2: `src/web/app.py` — `/dashboard` 블루프린트 등록 + `/` → `/dashboard` 리다이렉트
- [x] V2-3-3: 공통 SVG/UI 헬퍼 (`helpers.py`에 svg_semicircle_gauge, svg_radar_chart, no_data_card, fmt_pace 추가)

---

## Sprint 4-A: 공통 UI 기반

- [x] V2-4A-1: `src/web/helpers.py` — ECharts CDN으로 교체 (`_CHARTJS_CDN` → `_ECHARTS_CDN`, `html_page()` 수정)
- [x] V2-4A-2: `src/web/views_dashboard.py` — PMC 차트를 ECharts Line 차트로 재작성
  - TSB 위험구간 배경: TSB < -20 이면 주황 음영, < -30 이면 빨강 음영 (ECharts markArea)
- [x] V2-4A-3: `src/web/helpers.py` — `bottom_nav(active_tab)` 함수 추가 (7탭, dev_mode 조건부)
- [x] V2-4A-4: 기존 `/dashboard`, `/settings`, `/activities` 에 `bottom_nav` 삽입
- [x] V2-4A-5: `html_page()` 에 ui-spec.md 다크 테마 CSS 색상 토큰 반영
  - 배경: `linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%)`
  - 강조: `--cyan: #00d4ff`, `--green: #00ff88`, `--orange: #ffaa00`, `--red: #ff4444`
  - 폰트: Noto Sans KR + Inter (Google Fonts CDN)
- [x] V2-4A-6: `tests/` — ECharts 전환 후 기존 테스트 통과 확인

---

## Sprint 4-B: Jinja2 render_template 전환 ✅ 완료 (2026-03-23)

- [x] V2-4B-1: `templates/base.html` — 공통 레이아웃 (stylesheet/nav_html/sync_js context_processor 주입)
- [x] V2-4B-2: `src/web/app.py` — `template_folder` 설정, `context_processor`(`stylesheet`, `nav_html`, `sync_js`), Jinja2 globals(`bottom_nav`)
- [x] V2-4B-3: `templates/macros/gauge.html` — `half_gauge` SVG 매크로 stub
- [x] V2-4B-4: `templates/macros/radar.html` — `radar_chart` SVG 매크로 stub
- [x] V2-4B-5: `templates/macros/no_data.html` — `no_data_card` 매크로
- [x] V2-4B-6: `templates/dashboard.html` + `views_dashboard.py` → `render_template('dashboard.html')` 전환
- [x] V2-4B-7: `templates/generic_page.html` + `views_settings.py` 6개 엔드포인트 → `render_template` 전환

---

## Phase 4: 활동 상세 UI 고도화 (Sprint 4-C) ✅ 완료 (2026-03-23, V2-4-5 제외)

- [x] V2-4-1~4: `src/web/views_activity.py` — 2차 메트릭 카드 추가
  - `_render_secondary_metrics_card`: FEARP/GAP/NGP/RelativeEffort/Decoupling/EF/TRIMP
  - `_render_daily_scores_card`: 당일 UTRS/CIRS/ACWR 지수
  - `_load_activity_computed_metrics`, `_load_day_computed_metrics`: DB 조회
  - `html_page()` → `render_template('generic_page.html')` 전환 (5개 엔드포인트)
- [x] V2-4-6: `_render_horizontal_scroll` — 핵심 메트릭 수평 스크롤 바 (거리/시간/페이스/심박/고도/FEARP/GAP)
- [ ] V2-4-5: activity_deep — 지도 (Mapbox/Leaflet) — v0.3으로 이연

---

## Phase 5: 분석 레포트 UI (Sprint 4-C) ✅ 완료 (2026-03-23)

- [x] V2-5-1: `src/web/views_report.py` — 분석 레포트 뷰 블루프린트
  - 기간 선택 탭 (week/month/3month) — GET /report?period=week
  - 요약 카드 (활동 수/총 거리/총 시간/평균 거리/평균 UTRS/CIRS)
  - 주별 거리 ECharts 바차트 (markLine 평균선 포함)
  - 활동별 메트릭 테이블 (FEARP/GAP/Relative Effort/Decoupling, 최근 15개)
- [x] V2-5-2: `src/web/app.py` — `/report` 블루프린트 등록

---

## Phase UI-Gap: v0.2 UI 보완 (v0.2_ui_gap_analysis.md 기준) ✅ 완료 (2026-03-24)

### Priority A — 즉시 구현 완료

- [x] **6.1** `src/web/views_dashboard_cards.py` 신설 — Dashboard 보완
  - `_render_training_recommendation()`: UTRS grade/CIRS/TSB 기반 오늘의 훈련 권장 카드
  - `_render_utrs_factors()` 강화: 5요인 progress bar 시각화
  - `_render_cirs_breakdown()`: ACWR/Monotony/Spike/Asym 상태 배지 + bar
  - `_render_risk_pills()`: ACWR/LSI/Monotony/TSB 색상 pill 행
  - `_render_darp_mini()`: 5K/10K/하프/마라톤 예측 기록 mini 카드
  - `_render_fitness_mini()`: VDOT + Marathon Shape 피트니스 카드
  - `templates/dashboard.html` 블록 추가 (recommendation_card/risk_pills/darp_card/fitness_card)
- [x] **6.2** `src/web/views_activity.py` — Activity Detail 보완
  - `_load_activity_metric_jsons()` / `_load_day_metric_jsons()` — metric_json 별도 조회
  - `_render_activity_classification_badge()` — easy/tempo/interval/long/recovery 자동 분류
  - `_render_di_card()` — DI 내구성 지수 카드
  - `_render_fearp_breakdown_card()` — 기온/습도/고도/경사 요인 분해 bar
  - `_render_decoupling_detail_card()` — EF + Decoupling % + aerobic stability
  - `_render_map_placeholder()` — Mapbox 미설정 시 graceful fallback
  - `_render_secondary_metrics_card()` 확장 — 당일 종합 지표 DI/LSI/Monotony/ACWR/ADTI/MarathonShape 추가
- [x] **6.3** `src/web/views_report_sections.py` 신설 — Report 보완
  - `render_tids_section()`, `render_trimp_weekly_chart()`, `render_risk_overview()`
  - `render_endurance_trend()`, `render_darp_card()`, `render_fitness_trend()`
  - `render_ai_insight_placeholder()`, `render_export_buttons()`
- [x] **7.3** `src/web/views_import.py` 신설 — Strava Archive Import UI
  - GET/POST `/import/strava-archive` — 임포트 폼 + 결과 리포트 카드
  - POST `/import/strava-archive/backfill` — 기존 활동 파일 재연결
  - `_render_merge_rules_card()` — 병합 규칙 설명 (7.4 포함)
  - zip 자동 압축 해제 + sqlite3 conn 핸들링

### 이연됨

- [ ] **6.4~6.8**: 추후 구현 (다음 스프린트에서 확인 후 반영)
- [ ] **V2-4-5**: activity_deep 지도 (Mapbox/Leaflet) — v0.3으로 이연

---

## Phase API-Garmin: Garmin 전체 API 수집 완성 ✅ 완료 (2026-03-24)

### DB 스키마 확장
- [x] `activity_summaries` 80컬럼으로 확장 (name, sport_type, moving_time_sec, aerobic_training_effect 등 50+개 추가)
- [x] `activity_laps` 36컬럼 (split_type, GPS 좌표, running_dynamics 전체 포함)
- [x] `activity_streams` 신규 (GPS/시계열 데이터, SQL 기반 메트릭 계산용)
- [x] `activity_best_efforts` 신규 (PR 세그먼트)
- [x] `activity_exercise_sets` 신규 (근력/인터벌 운동 세트, 전 종목)
- [x] `athlete_profile` 신규 (선수 프로필)
- [x] `athlete_stats` 신규 (누적 통계 스냅샷)
- [x] `gear` 신규 (신발/장비)
- [x] `daily_wellness` spo2_avg/respiration_avg/intensity_min 컬럼 추가
- [x] `migrate_db()` 기존 DB 자동 마이그레이션

### 활동 확장 API (garmin_api_extensions.py)
- [x] `sync_activity_streams()` — activity_details GPS + 시계열 (1500+ 포인트/활동)
- [x] `sync_activity_gear()` — 활동별 장비 → gear 테이블
- [x] `sync_activity_exercise_sets()` — 운동 세트 (근력/기타 전 종목)

### 일별 확장 API (garmin_daily_extensions.py)
- [x] `sync_daily_race_predictions()` — 5K/10K/하프/마라톤 예측 기록
- [x] `sync_daily_training_status()` — ATL/CTL/ACWR/training_status → daily_fitness
- [x] `sync_daily_fitness_metrics()` — endurance_score, hill_score, fitnessage, lactate_threshold
- [x] `sync_daily_user_summary()` — 94키 종합 요약 (BB, 강도분, SPO2 등 daily_wellness 보완)
- [x] `sync_daily_heart_rates()` — 일중 HR 타임라인
- [x] `sync_daily_all_day_stress()` — 24시간 스트레스 타임라인
- [x] `sync_daily_body_battery_events()` — 충전/방전 이벤트

### 선수 데이터 (garmin_athlete_extensions.py)
- [x] `sync_athlete_profile()` — user_profile → athlete_profile
- [x] `sync_athlete_stats()` — 누적 통계 스냅샷 → athlete_stats
- [x] `sync_athlete_personal_records()` — PR → activity_best_efforts + daily_detail_metrics

### 웰니스 버그 수정 (garmin_wellness_sync.py)
- [x] `body_battery_summary_json`, `stress_summary_json`, `respiration_summary_json`, `spo2_summary_json`, `body_composition_summary_json` 누락 → 복구

### garmin.py 동기화 흐름 업데이트
- [x] `sync_garmin()` — 활동 + 웰니스 + 일별확장 + 선수데이터 전체 통합
- [x] 기간동기화 시 streams force 재수집, 일반동기화 시 기존 스킵

---

## Phase API-Strava: Strava 전체 API 수집 완성 ✅ 완료 (2026-03-24)

### 모듈 분리 (Garmin 방식)
- [x] `strava_auth.py` — 토큰 관리, 연결 확인
- [x] `strava_activity_sync.py` — 활동 동기화 (list/detail/streams/laps/best_efforts)
- [x] `strava_athlete_sync.py` — 선수 프로필, 통계, 기어
- [x] `strava.py` — 하위 호환 re-export wrapper + `sync_strava()`

### 활동 데이터 개선
- [x] INSERT 컬럼 확장: name, sport_type, moving_time_sec, elapsed_time_sec, avg_speed_ms, max_speed_ms, kudos_count, achievement_count, pr_count, suffer_score, strava_gear_id, end_lat/end_lon, avg_power, normalized_power
- [x] 중복 laps/splits 코드 제거
- [x] 스트림 → 파일 저장 제거, activity_streams DB 테이블로 이전
- [x] best_efforts → activity_best_efforts 테이블 (개별 행)
- [x] laps → activity_laps 테이블 (avg_speed_ms, max_speed_ms 포함)

### 신규 API 구현
- [x] `GET /athlete` → athlete_profile
- [x] `GET /athletes/{id}/stats` → athlete_stats 스냅샷
- [x] `GET /gear/{id}` → gear 테이블
- [x] `sync_athlete_and_gear()` — 활동의 미수집 기어 자동 동기화

### 테스트
- [x] `test_sync_strava.py` 전면 개편 (19개 테스트: 기존 2개 → 신규 17개 추가)
- [x] `test_auth_strava.py` 업데이트 (inspect 테스트를 서브모듈 기준으로)

---

## Phase API-Intervals: Intervals.icu 전체 API 수집 완성 ✅ 완료 (2026-03-24)

### 모듈 분리 (Garmin 방식)
- [x] `intervals_auth.py` — 인증, 연결 확인
- [x] `intervals_activity_sync.py` — 활동 동기화 (list/intervals/streams)
- [x] `intervals_wellness_sync.py` — 웰니스/피트니스 동기화
- [x] `intervals_athlete_sync.py` — 선수 프로필, 통계 스냅샷
- [x] `intervals.py` — 하위 호환 re-export wrapper + `sync_intervals()`

### 버그 수정
- [x] INSERT 바인딩 수 불일치 버그 수정 (15 `?` but 16 values → 사전 테스트 3개 실패 원인)

### 활동 데이터 개선
- [x] INSERT 컬럼 확장: name, sport_type, moving_time_sec, elapsed_time_sec, avg_speed_ms, max_speed_ms, elevation_loss, normalized_power
- [x] icu_* 필드 activity_summaries에 직접 저장 (icu_training_load, icu_trimp, icu_hrss, icu_atl, icu_ctl, icu_tsb, icu_gap, icu_decoupling, icu_efficiency_factor)

### 신규 API 구현
- [x] `GET /activities/{id}/intervals` → activity_laps (인터벌 랩)
- [x] `GET /activities/{id}/streams` → activity_streams
- [x] `GET /athlete/{id}` → athlete_profile (ftp, lthr, vo2max 포함)
- [x] DB 집계 기반 athlete_stats 스냅샷

### 테스트
- [x] `test_sync_intervals.py` 전면 개편 (19개 테스트: 기존 3개 → 신규 16개 추가)
- [x] `test_auth_intervals.py` 업데이트 (intervals/streams 엔드포인트 검증 추가)

---

### Priority B — 다음 스프린트

- [x] **B-1**: 파일 크기 리팩토링 (기능 기준 분리) ✅ 부분 완료 (2026-03-25)
  - [x] helpers.py → helpers_svg.py 분리 (1042→854줄)
  - [x] views_activity_cards.py → views_activity_source_cards.py 분리 (1102→731줄)
  - [x] views_activity.py → views_activity_cards.py + views_activity_loaders.py 분리 (1529→185줄)
  - [x] app.py → views_dev.py 분리 (1351→839줄)
- [x] **B-2**: `V2-9-3` graceful fallback 전면 보강 ✅ 완료 (2026-03-25)
  - DB exists() 체크, "데이터 수집 중" 통일, try/except Exception 전면 적용
- [x] **B-3**: `V2-9-4` Settings hub 고도화 ✅ 완료 (2026-03-25)
  - last_sync 시각 표시, 사용자 프로필 설정 폼(max_hr/threshold_pace/weekly_km), POST /settings/profile

---

## Sprint 5: 데이터 파이프라인 확장 + 병렬 동기화 (2026-03-25)

### Sprint 5-A: 데이터 레이어 아키텍처 확립 ✅ 완료

- [x] D-V2-16: 데이터 계층 아키텍처 결정 문서화 (저장 분리 + 입력 유연성)
  - 서비스 데이터 / 서비스 1차 / RunPulse 1차 / RunPulse 2차
  - RunPulse 2차 메트릭은 모든 소스(서비스 데이터, 서비스 1차, RunPulse 1차, 외부 API) 입력 허용
  - 결과 저장은 반드시 `computed_metrics` (서비스 테이블과 분리)
- [x] FEARP: 서비스 날씨 데이터(activity_detail_metrics.weather_*) 우선 사용, 없으면 Open-Meteo fallback

### Sprint 5-B: 동기화 인프라 개선 ✅ 완료

- [x] 기간 동기화 4개 서비스 동시 병렬 실행 (`helpers.py` `startBgSyncMulti`)
  - 서비스별 단독 실행 제한 해제 (서비스별 rate limit 독립 적용)
  - 진행 상황 서비스별 개별 행 표시 (`bg-jobs-container`)
  - 일시중지/중지/재개는 모든 활성 서비스 동시 적용
- [x] Garmin 신규 데이터: `sync_activity_weather`, `sync_activity_hr_zones`, `sync_activity_power_zones`
- [x] Garmin 신규 일별: `sync_daily_hydration`, `sync_daily_weigh_ins`, `sync_daily_running_tolerance`
- [x] Strava 신규: `_sync_activity_zones` (HR/Power 존별 시간)
- [x] Intervals.icu: `start_lat/start_lon`, `_sync_power_curve`
- [x] DB 스키마: `activity_summaries.workout_type / trainer / commute` 컬럼 추가

### Sprint 5-C: 메트릭 계산 개선 ✅ 완료

- [x] TIDS: zone 데이터 소스 우선순위 확장 (`hr_zone_N_sec` → `heartrate_zone_N_sec` → `hr_zone_time_N`)
- [x] RelativeEffort: 동일 우선순위 zone 소스 fallback 적용
- [x] RTTI (러닝 내성 훈련 지수): Garmin running_tolerance 기반, `src/metrics/rtti.py`
- [x] WLEI (날씨 가중 노력 지수): TRIMP × 기온/습도 스트레스, `src/metrics/wlei.py`
- [x] TPDI (실내/야외 퍼포먼스 격차): trainer 컬럼 × FEARP, `src/metrics/tpdi.py`
- [x] engine.py: WLEI (활동별), RTTI/TPDI (일별) 등록
- [x] `tests/test_metrics_sprint5.py`: RTTI/WLEI/TPDI 14개 테스트 통과

### Sprint 5-E: 버그 수정 ✅ 완료 (2026-03-25)

- [x] `unified_activities.py`: matched_group_id hex 오분류 수정 (`is_group` 플래그)
- [x] `views_activity.py/_load_service_metrics`: 소스별 row 각각 조회 (Strava/Intervals 지표 누락 수정)
- [x] `db_setup.py`: `icu_intensity` 컬럼 추가, `training_load_acute/chronic` 제거
- [x] `intervals_activity_sync.py`: `icu_intensity` activity_summaries 저장 추가
- [x] `views_dashboard_cards.py`: 활동 링크 `/activity?id=` → `/activity/deep?id=` 수정
- [x] `api.py`: 4xx 응답 [API] 로그 억제
- [x] `intervals/strava_activity_sync.py`: 404/402 예상 응답 실패 로그 억제
- [x] `bg_sync.py`: req_added 추정치 수정 (strava×4+1, intervals×3+1, runalyze×2+1)

### Sprint 5-Wellness: Wellness UI ✅ 완료

- [x] `src/web/views_wellness.py` (250줄) — `/wellness` 라우트
  - 수면/HRV/Body Battery/스트레스/안정시심박 트렌드
  - 7일/30일 기간 선택
  - app.py에 wellness_bp 등록

### Sprint 5-D: 미완료 — 다음 스프린트 (Phase B+C)

- [ ] **S5-B1**: 메트릭 재계산 Progress bar (SSE 스트리밍)
  - `src/metrics/engine.py` `recompute_all()` 에 `progress_callback` 파라미터 추가
  - `src/web/views_settings.py` SSE 엔드포인트 `/metrics/recompute-stream` 추가
  - 설정 화면 진행률 바 (날짜별 %, 예상 남은 시간)
- [ ] **S5-C1**: 활동 상세 UI — RunPulse/서비스 데이터 분리 표시 (D-V2-16 반영)
  - Primary 탭: RunPulse 1차/2차 메트릭 (`computed_metrics`)
  - Secondary 서브탭: 서비스 1차 메트릭 (Garmin training_effect, Strava suffer_score, Intervals icu_training_load 등)
  - 지표 hover 툴팁 (의미 + 공식 설명)
  - 현재 수치 해설 텍스트 (예: "CIRS 78 — 부상 위험 높음, 강도 낮추기 권장")
- [ ] **S5-C2**: 대폭 확장된 데이터 반영 UI 전면 재설계 (로드맵으로 이연 — 별도 스프린트)
  - Sprint 5-A~C로 추가된 데이터(날씨/존/running dynamics/running tolerance 등)를 UI에 노출하는 구조 재설계 필요
  - 현재 activity 상세 UI는 v0.1 기준 설계 → 새로운 데이터 계층 구조에 맞게 전면 재검토

---

## Phase 6: 레이스 예측 UI (Sprint 5) ✅ 완료 (2026-03-25)

- [x] V2-6-1: `src/web/views_race.py` (225줄) — 레이스 예측 뷰 블루프린트
  - 레이스 거리 선택 탭 (5K/10K/하프마라톤/마라톤/커스텀) — GET ?distance=half
  - 예측 결과 카드 (완주 시간, 평균 페이스, 스플릿)
  - DI 가로 게이지 + 설명
  - 페이스 전략 + Hitting the Wall 확률
  - `templates/race.html` Jinja2 템플릿
- [x] V2-6-2: `src/web/app.py` — `/race` 블루프린트 등록 (race_bp)

---

## Phase 7: AI 코칭 UI (Sprint 5) ✅ 기본 구현 완료 (2026-03-25)

- [x] V2-7-1: `src/web/views_ai_coach.py` (204줄) — `/ai-coaching` 라우트
  - 코치 프로필 카드 + 오늘의 브리핑 카드
  - UTRS/CIRS/DARP 수치를 브리핑 컨텍스트에 포함
  - 추천 칩 (FEARP, CIRS, Marathon Shape 기반)
  - `templates/ai_coaching.html` Jinja2 템플릿
  - bottom_nav('ai-coach')
  - 채팅 인터페이스는 v0.3으로 이연

---

## Phase 8: 훈련 계획 캘린더 UI (Sprint 6)

- [x] V2-8-1a: `src/web/views_training.py` 스캐폴딩 ✅ 완료 (2026-03-25)
  - Blueprint training_bp, /training GET
  - placeholder 페이지: "훈련 계획 기능이 곧 추가됩니다"
  - bottom_nav('training') 연결
- [→] V2-8-1 풀 구현 → v0.3으로 이연 (캘린더 UI, 운동 CRUD, 캘린더 연동)
- [→] V2-8-2: 기존 `src/training/` 모듈과 연동 → v0.3

---

## Phase 9: 설정 통합·개발자 탭·마무리 (Sprint 6 후반)

- [→] V2-9-1: 전체 뷰 하단 nav 통일 → **Sprint 4-A로 이동 (V2-4A-3/4)**
- [→] V2-9-2: ECharts CDN 로드 실패 시 fallback → **Sprint 4-A 이후 처리**
- [x] V2-9-3: 메트릭 데이터 부재 시 graceful UI ("데이터 수집 중" 카드) ✅ 완료 (2026-03-25)
- [x] V2-9-4: `views_settings.py` 설정 고도화 ✅ 완료 (2026-03-25)
  - A. 소스 연동 (기존, 마지막 동기화 시간 last_sync 추가)
  - B. 사용자 프로필 설정 (max_hr, threshold_pace, weekly_km, POST /settings/profile)
  - [→] C. 데이터 관리 / D. 앱 설정 → v0.3으로 이연
- [ ] V2-9-5: `src/web/views_dev.py` + `/dev` 라우트 (개발자 탭, dev_mode 조건부)
  - DB 테이블 뷰어, Payload 뷰어, DB 경로 설정, 레거시 분석 링크
  - `bottom_nav` 에서 `config.get('dev_mode', False)` 플래그로 조건부 노출
- [ ] V2-9-6: 통합 테스트 (`test_web_dashboard.py`, `test_web_report.py`, `test_web_race.py`)
- [ ] V2-9-7: `/analyze/*` → 신규 화면 리다이렉트
  - `/analyze/today` → `/dashboard`
  - `/analyze/full` → `/report`
  - `/analyze/race` → `/race`
- [ ] V2-9-8: `.ai/changelog.md` 업데이트
- [ ] V2-9-9: Mapbox 토큰 설정 추가 (`config.json` `mapbox.token` 키, 활동 상세 지도용)

---

## Phase Multi-User: 멀티유저 지원 ✅ 기본 완료 (2026-03-25)

- [x] `get_db_path(user_id)` → `data/users/{user_id}/running.db`
- [x] `load_config(user_id=)` → 사용자별 config.json
- [x] Flask 세션 기반 user_id 자동 추출 (helpers.get_current_user_id)
- [x] `/switch-user` 사용자 전환 UI
- [x] CLI `--user` 파라미터 (sync.py, plan.py, analyze.py)
- [x] sync_jobs.db 사용자별 분리
- [ ] 인증/로그인 시스템 (v0.3 이연)
  - 로그인 폼 + 세션 기반 인증
  - 비밀번호 해시 저장 (bcrypt)
  - 미인증 시 로그인 페이지 리다이렉트
  - 사용자 등록/관리 UI

---

## v0.3 로드맵 (공식 확정, 3-6개월)

> 모두 수식 기반. 데이터 누적 또는 추가 연동 필요.

### 1차 메트릭 추가

- [ ] V3-1-3: `src/metrics/eftp.py` — eFTP 추정 (Intervals.icu 방식)
  - 최고 기록 vs 데이터베이스 평균 파워 커브 비교
  - 2파라미터 CP 모델: P(t) = W'/t + CP
- [ ] V3-1-4: `src/metrics/critical_power.py` — Critical Power 추정 (Stryd 없이)
  - 3개 이상 올아웃 기록으로 CP·W' 추정 (polyfit 선형 회귀)
  - 데이터 요건: 파워 데이터 또는 속도 기반 대체 추정

### 2차 메트릭 추가 (모두 공식 확정)

- [ ] V3-2-1: `src/metrics/rec.py` — REC (통합 러닝 효율성 지수)
  - `REC = MetabolicEff×0.4 + VerticalEff×0.2 + ContactEff×0.2 + CadenceOpt×0.1 + StrideConsistency×0.1`
  - 데이터 요건: Garmin Running Dynamics (GCT, VO, VR, 케이던스)
- [ ] V3-2-2: `src/metrics/rri.py` — RRI (레이스 준비도 지수)
  - `RRI = TSB_score×0.30 + CTL_peak_score×0.25 + Marathon_Shape_score×0.25 + quality_workouts×0.20`
- [ ] V3-2-3: `src/metrics/sapi.py` — SAPI (계절·날씨 성과 비교)
  - `SAPI = (FEARP_current - FEARP_baseline) / FEARP_baseline × 100 (%)`
  - 동일 코스 과거 세션과 비교 (baseline: 동코스 최근 5회 평균)
- [ ] V3-2-4: `src/metrics/teroi.py` — TEROI (훈련 효과 투자 수익률)
  - `TEROI = ΔPerformance / ΔTRIMP_3months`
  - ΔPerformance: VDOT 또는 race_time 개선율
- [ ] V3-3-1: UI — 레포트/활동 상세에 REC, SAPI 표시
- [ ] V3-3-2: UI — 레이스 예측에 RRI 게이지 추가 (DARP 옆에 배치)
- [ ] V3-3-3: UI — 레포트에 TEROI 트렌드 차트 추가
- [ ] V3-9-1: PWA (Service Worker + manifest.json + 홈 화면 추가 배너)
- [ ] V3-9-2: REST API 기반 (`GET /api/v1/*`) — 모바일 앱 준비

### DB 고도화 (v0.3)

- [ ] V3-DB-1: `best_efforts` 테이블 — 거리별 베스트 기록 전용 저장 (400m~마라톤)
  - 현재 `activity_detail_metrics`에 분산 → 전용 테이블로 PR 조회 최적화
  - DARP/Marathon Shape 계산 속도 향상
- [ ] V3-DB-2: `daily_fitness` 정규화 — `runalyze_evo2max`, `runalyze_vdot`, `runalyze_marathon_shape` 컬럼을 `daily_detail_metrics`로 이관
  - 신규 소스 추가 시 스키마 변경 불필요
- [ ] V3-DB-3: 멀티유저 지원 — **사용자별 별도 DB 파일 패턴** 채택
  - `data/users/{user_id}/running.db` 디렉토리 구조
  - 스키마 변경 없음, `get_db_path(user_id)` 함수 추가만 필요
  - 웹 세션 기반 사용자 판별, config.json도 사용자별 분리
  - 이 방식으로 스키마 전체에 `user_id` 컬럼 추가 불필요

---

## v0.4+ 로드맵 (ML 기반, 6개월+)

- [ ] V4-1-1: `src/metrics/tqi.py` — TQI (훈련 품질 지수)
  - ML로 세션 유형 자동 분류 (interval/tempo/easy/long) 후 실행 품질 평가
  - 데이터 요건: 최소 50회 이상 활동 (학습용)
- [ ] V4-1-2: `src/metrics/pltd.py` — PLTD (개인화 역치 자동 탐지)
  - 개인 역대 HR×pace 데이터에서 젖산 역치 자동 추정
  - 단순 공식(LTHR = HR_max × 0.85)에서 시작, ML로 점진적 고도화
- [ ] V4-9-1: React Native 모바일 앱 (iOS/Android): `/api/v1/*` REST API 소비
- [ ] V4-9-2: Mapbox GL JS → React Native Mapbox SDK 전환

---

## 미계획 (장비 의존 — Optional)

| 메트릭 | 필요 장비 | 공식 | 비고 |
|--------|----------|------|------|
| PEI (파워 이코노미 지수) | Stryd 파워 풋팟 | `PEI = velocity / (power/weight)` | Stryd 없으면 불가 |
| RSS (Running Stress Score) | Stryd | `RSS = a × (power/CP)^b × sec` | 상동 |
| W' (무산소 작업 용량) | 파워 미터 (Stryd/기타) | CP 2파라미터 모델 파생 | 상동 |
