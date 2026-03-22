# v0.2 작업 목록
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

## Sprint 4-B: Jinja2 render_template 전환

- [ ] V2-4B-1: `templates/macros/base.html` — `page_shell(title)` 매크로
- [ ] V2-4B-2: `templates/macros/nav.html` — `bottom_nav(active_tab)` Jinja2 매크로
- [ ] V2-4B-3: `templates/macros/gauge.html` — `half_gauge(value, max, color)` SVG 매크로
- [ ] V2-4B-4: `templates/macros/radar.html` — `radar_chart(axes, values)` SVG 매크로
- [ ] V2-4B-5: `templates/macros/no_data.html` — `no_data_card(title, message)` 매크로
- [ ] V2-4B-6: `views_dashboard.py` → `render_template('dashboard.html')` 전환
- [ ] V2-4B-7: `views_settings.py`, `views_activity.py` 순차 전환

---

## Phase 4: 활동 상세 UI 고도화 (Sprint 4-C)

- [ ] V2-4-1: `src/web/views_activity.py` — activity_deep에 FEARP 섹션 추가
  - 실제 페이스 vs 보정 페이스 비교 표시
  - 환경 영향 분해 배지: 기온/습도/경사 각 delta(초)
- [ ] V2-4-2: activity_deep에 2차 메트릭 카드
  - Aerobic Decoupling, EF (효율 계수)
  - Aerobic Training Effect (Garmin 수집값)
  - Running Dynamics (GCT, GCT Balance, VO, VR)
- [ ] V2-4-3: activity_deep에 UTRS/CIRS 기여도 표시
- [ ] V2-4-4: activity_deep에 추가 1차 메트릭 표시
  - GAP (경사 보정 페이스)
  - NGP (정규화 경사 페이스)
  - Relative Effort (구역 기반 노력도)
  - Anaerobic Training Effect (Garmin 수집값)
  - Training Status 라벨 (Garmin 원본: Peaking/Productive/Maintaining 등)
- [ ] V2-4-5: activity_deep — 지도 전체 화면 상단 60%
  - Mapbox GL JS 궤적 + FEARP 히트맵 오버레이 (토큰 없으면 Leaflet.js 폴백)
  - Mapbox 토큰: `config.json`에 저장 (`config.mapbox.token`)
- [ ] V2-4-6: activity_deep — 핵심 메트릭 수평 스크롤 카드 (모바일)
  - 거리 / 페이스 / 시간 / 심박수 / 고도 / 케이던스 가로 스와이프

---

## Phase 5: 분석 레포트 UI (Sprint 4-C)

- [ ] V2-5-1: `src/web/views_report.py` — 분석 레포트 뷰 블루프린트
  - 기간 선택 탭 (오늘/주/월/분기/연/사용자정의) — GET ?period=week
  - 레포트 헤더 카드 (기간 라벨, 활동 수, 총 거리, 총 시간)
  - 요약 카드 2×2 grid (총 거리/시간/UTRS/CIRS + 전기간 대비 변화율)
  - 활동 추세 차트 (ECharts Line, 주별 거리)
  - TIDS 분포 가로 분할 바 (Easy/Tempo/Threshold %)
  - TRIMP 주간 부하 바차트 (ECharts Bar)
  - 세부 메트릭 테이블 (GAP, NGP, EF, Relative Effort, Decoupling)
  - AI 인사이트 카드 3개
  - 액션 버튼: 훈련 플랜 조정 → /training
- [ ] V2-5-2: `src/web/app.py` — `/report` 블루프린트 등록

---

## Phase 6: 레이스 예측 UI (Sprint 5)

- [ ] V2-6-1: `src/web/views_race.py` — 레이스 예측 뷰 블루프린트
  - 레이스 거리 선택 탭 (5K/10K/하프마라톤/마라톤/커스텀) — GET ?distance=half
  - 예측 결과 카드 (완주 시간, 평균 페이스, 스플릿: 5K/10K/중간/순위%)
  - DI 가로 게이지 + 설명
  - 페이스 전략 타임라인 (구간별 color: green/yellow/red)
  - 히팅 더 월 확률 % (red gradient 배경)
  - 훈련 플랜 조정 카드 → POST /training/apply-darp
  - bottom_nav('report')  ← 레이스 예측은 레포트 탭 하위
- [ ] V2-6-2: `src/web/app.py` — `/race` 블루프린트 등록

---

## Phase 7: AI 코칭 UI (Sprint 5)

- [ ] V2-7-1: `src/web/views_ai_coach.py` — `/ai-coach` URL 라우트 신규 또는 리다이렉트 추가
  - 기존 AI 뷰 URL 확인 후 `/ai-coach` 로 통일
  - UTRS/CIRS/DARP 수치를 브리핑 컨텍스트에 포함
  - 추천 칩에 FEARP, CIRS, Marathon Shape 기반 항목 추가
  - 채팅 버블 UI (role=ai: cyan 배경 / role=user: 오른쪽 정렬)
  - 고정 채팅 입력창 (position: fixed, bottom: 80px)
  - POST /ai-coach/briefing (재생성), POST /ai-coach/chat (대화)
  - bottom_nav('ai-coach')

---

## Phase 8: 훈련 계획 캘린더 UI (Sprint 6)

- [ ] V2-8-1: `src/web/views_training_plan.py` — `/training` 라우트
  - 이번 주 요약 4-stat grid (완료/목표/시간/UTRS)
  - 캘린더 뷰 전환 (GET ?view=week|month|day)
  - 주간 뷰 7열 grid — .workout-item.{easy|tempo|interval|long|rest}
  - AI 훈련 요약 카드 (최근 브리핑 발췌 1~2줄 + "/ai-coach로 더 묻기 →" 링크)
  - 캘린더 연동 상태 (Google/Naver/Garmin/TrainingPeaks)
  - bottom_nav('training')
  - GET/POST `/training/new` — 새 훈련 항목 추가
  - POST `/training/apply-darp` — DARP 레이스 예측 결과 플랜 반영
- [ ] V2-8-2: 기존 `src/training/` 모듈과 연동

---

## Phase 9: 설정 통합·개발자 탭·마무리 (Sprint 6 후반)

- [→] V2-9-1: 전체 뷰 하단 nav 통일 → **Sprint 4-A로 이동 (V2-4A-3/4)**
- [→] V2-9-2: ECharts CDN 로드 실패 시 fallback → **Sprint 4-A 이후 처리**
- [ ] V2-9-3: 메트릭 데이터 부재 시 graceful UI ("데이터 수집 중" 카드)
- [ ] V2-9-4: `views_settings.py` 설정 4섹션 통합 (ui-spec 3-7 기준)
  - A. 소스 연동 (기존, 마지막 동기화 시간 `last_sync_at` 추가)
  - B. 동기화 — `/sync-status` 인라인 흡수 (배치 제어 + 진행률 폴링)
  - C. 데이터 관리 — `/import`(GPX/FIT/TCX/ZIP) + `/import-export`(CSV) 흡수
  - D. 앱 설정 — AI 모델 select, 기본 레이스 거리 select
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
