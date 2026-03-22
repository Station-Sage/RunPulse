# Changelog

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
