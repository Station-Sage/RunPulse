# Changelog

> 이전 이력은 `changelog_history.md` 참조

## [fix/metrics-everythings] 2026-03-28 (훈련탭 UX 재설계 Phase C — Wizard)

### Phase C: 4단계 AJAX Wizard (`/training/wizard`)
- `src/web/views_training_wizard.py` 신규: `wizard_bp` Blueprint
  - `GET /training/wizard` — Step 1 전체 페이지
  - `POST /training/wizard/step` — AJAX step별 처리 (JSON: `{step, html}`)
  - `POST /training/wizard/complete` — goals + prefs 저장 + 플랜 생성 후 redirect
- `src/web/views_training_wizard_render.py` 신규: HTML 렌더러 + JS
  - `render_step1()` ~ `render_step4()`: 각 단계 HTML
  - `wizard_js()`: `_wizHistory` 배열 기반 JS 뒤로가기 + AJAX step 전환
- `src/web/app.py`: `wizard_bp` 등록
- `src/web/views_training_cards.py`: 목표 없을 때 "🗓️ 훈련 계획 시작하기" 버튼 추가
- `tests/test_training_wizard.py` 신규: 18개 테스트 통과 (단위 + 통합)
- 테스트: **1097개 통과** (기존 1047 + readiness 32 + wizard 18)

---

## [fix/metrics-everythings] 2026-03-28 (훈련탭 UX 재설계 Phase A+B)

### SCHEMA_VERSION 3.1 — 마이그레이션 v4
- `db_setup.py`: `SCHEMA_VERSION = 4` (display: '3.1')
- `_migrate_to_v4()`: `schema_meta.display_version`, `goals.weekly_km_target`, `goals.plan_weeks`, `user_training_prefs.long_run_weekday_mask` 추가

### Phase A: readiness.py 신규
- `src/training/readiness.py`: 훈련 준비도 분석 + 목표 달성 가능성 예측
  - VDOT 성장 모델: VO2max + 러닝 경제성(RE) + 젖산역치(LT) 합산 (Saunders 2004, Coyle 1988)
  - VDOT 구간별 `base_gain`: < 30(0.65) / 30~40(0.40) / 40~50(0.27) / 50~60(0.14) / 60+(0.07)
  - 최솟값 미만 기간 선택 시 달성률 70% 상한 페널티
  - 거리별 논문 기반 훈련 기간 (5K:6~10주/테이퍼1주, Full:16~20주/테이퍼3주 등)
  - `vdot_to_time()`, `get_taper_weeks()`, `recommend_weekly_km()`, `analyze_readiness()`
- `tests/test_readiness.py`: 32개 테스트 통과
- `planner.py`: `upsert_user_training_prefs()`에 `long_run_weekday_mask` 파라미터 추가

### Phase B: 훈련 환경 설정 → 훈련탭 이전
- `src/web/views_training_prefs.py` **신규**: `render_training_prefs_collapsed()` — `<details>` Collapsible 카드 (휴식 요일, 롱런 요일, 일회성 쉬는 날, 인터벌 거리, Q-day)
- `views_training_crud.py`: `POST /training/prefs` 라우트 추가
- `views_training.py`: 훈련탭 하단에 prefs 섹션 연결
- `views_settings.py`: 훈련환경설정 → "훈련탭 바로가기" 링크로 교체, 구 라우트 redirect
- 1047 테스트 통과 유지

---

## [fix/metrics-everythings] 2026-03-28 (테스트 추가 — matcher/replanner/crs)

### 신규 테스트 55개 (55 passed)
- `tests/test_matcher.py` (12개): 매칭 기본 동작, completed 플래그, rest 제외, 멱등성, session_outcomes 저장/레이블
- `tests/test_replanner.py` (10개): Rule1 고강도 이동, Rule2 연속건너뜀 볼륨축소, Rule3 달성률 경고, Rule4 테이퍼 보호
- `tests/test_crs.py` (33개): Gate 1~5 단위 + CRS 점수 범위/보정 + evaluate() 통합

---

## [fix/metrics-everythings] 2026-03-28 (동기화 후 자동 매칭)

### 동기화 완료 시 계획↔활동 자동 매칭
- `app.py`: `_auto_match_after_sync()` 헬퍼 추가
  - `trigger_sync()` 성공 후 이번 주 + 지난 주 `match_week_activities()` 자동 호출
- `bg_sync.py`: 백그라운드 sync 완료 블록에 최근 4주 자동 매칭 추가
  - 메트릭 재계산 블록 이후 실행, 실패 시 조용히 무시 (pass)
- 61 테스트 통과 (test_planner + test_web_training)

---

## [fix/metrics-everythings] 2026-03-28 (훈련탭 체크인 UX 개선)

### 훈련탭 체크인 AJAX 처리 + 재조정 diff 카드
- `views_training_crud.py`: `/confirm`, `/skip` 라우트에 `Accept: application/json` 헤더 시 JSON 응답 추가
  - confirm → `{"ok": true}`
  - skip → `{"ok": true, "message", "changes": [...], "warnings": [...], "moved", "target_date"}`
  - `result` 변수 초기화를 try 블록 앞으로 이동 (예외 발생 시 변수 미정의 버그 수정)
- `views_training_cards.py`: 체크인 카드 form POST → fetch AJAX 전환
  - 완료 버튼: 카드 fade-out 후 DOM 제거 (페이지 새로고침 없음)
  - 건너뜀 버튼: 재조정 결과를 인라인 diff 테이블로 표시 (날짜·변경 전→후·경고 메시지)
  - fallback: fetch 실패 시 `location.reload()` (기존 동작 유지)
- 테스트: 990 통과 (2개 기존 실패 `test_web_settings.py` — `get_db_path` import 버그, 무관)

---

## [fix/metrics-everythings] 2026-03-28 (훈련 엔진 v2)

### 훈련 엔진 v2 전면 재설계 (논문 기반)

**DB 스키마 v3 마이그레이션:**
- `user_training_prefs` 신규: 휴식요일 bitmask, 차단날짜 JSON, 인터벌 rep 거리, max Q-day
- `session_outcomes` 신규: ML 훈련 데이터 (달성률/페이스편차/HR분포/컨디션 스냅샷/outcome_label)
- `planned_workouts.interval_prescription TEXT` 컬럼 추가
- `goals.distance_label TEXT` 컬럼 추가 ('1.5k'|'3k'|'5k'|'10k'|'half'|'full'|'custom')
- UNIQUE INDEX on `session_outcomes(planned_id)`

**`src/metrics/crs.py` 신규 (게이트 기반 훈련 준비도):**
- Gate 1: ACWR (Gabbett 2016, BJSM) — >1.5 Z1 강제, >1.3 Z3 금지
- Gate 2: HRV (Plews 2013, IJSPP) — 7일 rolling avg 대비 -10% 임계
- Gate 3: Body Battery / Sleep Score — <25 휴식, <50 Z3 금지
- Gate 4: TSB (Coggan 2003) — <-30 즉시 회복주
- Gate 5: CIRS (내부) — >80 위험
- CRS 참고 점수 0~100 (UTRS 기반 + ACWR/CIRS 보정)
- 훈련 레벨: 0=REST, 1=Z1_ONLY, 2=Z1_Z2, 3=FULL, 4=BOOST

**`src/training/interval_calc.py` 신규 (Billat/Buchheit 공식):**
- `prescribe_interval(rep_m, interval_pace_sec_km)` — Billat 2001 휴식 비율 (60~240초 선형 보간)
- `prescribe_from_vdot(rep_m, vdot)` — VDOT_ADJ → Daniels I-pace → 처방
- Buchheit & Laursen 2013 rep 거리별 총 볼륨 상한
- VO2max 자극 60초 미달 경고

**`src/training/planner.py` 전면 개편 (v2):**
- `DISTANCE_LABEL_KM` — 6 표준 레이스 거리 + custom
- `_training_phase(weeks_left, week_idx)` — Foster 1998 3:1 사이클 (week_idx%4==3 → recovery_week)
- `_weekly_volume_km(ctl, phase, tsb, shape_pct)` — CTL 기반 + Mujika 2003 테이퍼 55% 감소
- `_get_available_days(week_start, prefs)` — bitmask + blocked_dates
- `_assign_qdayslots()` — Seiler 2009 Hard-Easy 48h 간격
- `generate_weekly_plan()` — CRS 게이트 다운그레이드, Seiler 80/20, Daniels 페이스
- `upsert_user_training_prefs()` — INSERT OR REPLACE

**`src/training/matcher.py` 확장:**
- `match_week_activities()` — session_outcomes 자동 저장
- `_save_session_outcome()` — dist_ratio, pace_delta_pct, HR zone 분포, 컨디션 스냅샷
- `save_skipped_outcome()` — 건너뜀 outcome_label='skipped' 기록

**`src/training/replanner.py` 재작성 (v2):**
- Rule 1: 고강도/long → Hard-Easy 2일 간격 보장하며 이동 (Lydiard/Bowerman)
- Rule 2: 연속 건너뜀 → 볼륨 10% 축소 (Gabbett 2016 ACWR)
- Rule 3: session_outcomes 피드백 — dist_ratio/pace/CRS 기반 경고
- Rule 4: 테이퍼 보호 — 이동 없이 볼륨 5% 축소만 (Mujika 2003)

**`src/web/views_settings.py` 훈련 설정 UI:**
- 요일별 휴식 체크박스 (bitmask)
- 일회성 차단 날짜 입력
- 인터벌 rep 거리 드롭다운 + 커스텀 입력 (320m 등 비표준 포함)
- `POST /settings/training-prefs` 라우트

**`src/web/views_training_cards.py` 인터벌 처방 카드:**
- `render_interval_prescription_card(workout)` — rep×sets, 페이스, 휴식, 총볼륨, 세션시간
- 논문 인용 표시 (Billat 2001, Buchheit 2013)

**설계 문서:**
- `v0.2/.ai/training_engine_v2_design.md` — 논문 참조표 + 모듈 구조 + ML 로드맵

**테스트:** 992 통과 (test_planner.py v2 API 반영)

---

## [feat/training-compliance] 2026-03-28

### 훈련 이행 추적 + 재조정 + 브리핑 연동

**DB 스키마 v2 마이그레이션:**
- `planned_workouts` 테이블에 `skip_reason TEXT`, `updated_at TEXT` 컬럼 추가
- `completed`: 0=대기, 1=완료, -1=건너뜀 (3-state)
- `SCHEMA_VERSION` 1→2, `_migrate_to_v2` 함수 추가

**어제 훈련 체크인 카드 (Phase A):**
- 훈련 탭 상단에 어제 미확인 계획이 있으면 체크인 카드 표시
- "완료했어요" → `POST /training/workout/{id}/confirm` → `completed=1` + 자동 매칭
- "건너뜀" → `POST /training/workout/{id}/skip` → `completed=-1` + 자동 재조정 실행
- `views_training_cards.py`: `render_checkin_card()` 신규
- `views_training_loaders.py`: `load_yesterday_pending()` 신규
- `views_training_crud.py`: confirm/skip/replan 라우트 신규

**계획 vs 실제 캘린더 비교 (Phase B):**
- `src/training/matcher.py` 신규 — 날짜 기반 계획↔활동 자동 매칭, 거리 근사치 선택
- `views_training_loaders.py`: `load_actual_activities()` 신규
- `render_week_calendar()`: `actual_activities` 파라미터 추가
  - 과거 날짜 각 칸에 "실제 Xkm · P:SS/km" 표시
  - 달성률 ≥90% 초록, 70~89% 주황, <70% 빨강

**계획 재조정 (Phase C):**
- `src/training/replanner.py` 신규
  - 건너뛴 고강도(interval/tempo)/long → 이번 주 남은 rest/easy 날로 이동
  - 연속 2일 건너뜀 → 남은 고강도 볼륨 10% 축소
- `POST /training/replan` 라우트 (수동 재조정)

**AI 브리핑 이행 현황 연동:**
- `ai_context.py`: `build_context()`에 `yesterday_plan`, `plan_compliance` 추가
- `ai_context.py`: `format_context_text()`에 "훈련 계획 이행 현황" 섹션 추가
- `context_builders.py`: `build_dashboard_context()`, `build_training_context()`에 어제 이행 + 이행률 추가
- `briefing.txt`: 항목 4(오늘 권장 훈련) — 어제 이행 여부 반영 지시; 항목 5(이번 주 나머지) — 건너뜀 이력 반영 지시

**재계산 개선 (sync 탭):**
- `views_settings.py`: `GET /recompute-metrics` 라우트 신규 (sync 탭 JS 호환)
- `days=0` = 전체 기간 (DB 최초 활동부터)
- 365일 상한 제거

---

## [fix/metrics-everythings] 2026-03-28

### 메트릭 버그 수정 + 대시보드 브리핑 개선 + Shape 라벨 통일

**레이스 감지 소스 기반으로 전면 교체:**
- 기존: HR 임계값(90% maxHR) 또는 레이블 텍스트 기반 → 템포런이 레이스로 오분류
- 수정: Garmin `event_type='race'`, Strava `workout_type=1`, Intervals `sub_type='RACE'`/`race=True` 소스 태그 기준
- 영향 파일: `vdot_adj.py`, `workout_classifier.py`, `intervals_activity_sync.py`

**VDOT_ADJ 버그 수정 2건:**
- `vdot.py`: `"source": "race_estimate"` 키 누락 → race_estimate 소스 인식 불가 수정
- `vdot_adj.py` 보정 범위: 4주 이내 ±1%, 4~8주 ±3%, 8주+ ±7% (이전: 8주+ ±7% 적용 조건 버그)
- `vdot_adj.py` T-pace 블렌딩: 레이스 직후 easy run HR 오염 방지 (레이스 implied T-pace × race_weight + stream 측정값 × (1-weight))

**대시보드 DARP 갱신 일관성:**
- `views_dashboard.py`: `_ensure_today_metrics` 조건에 `DARP_half` 포함 (UTRS만 있어도 스킵하던 버그)
- `views_race.py`: 레이스 탭 접근 시 오늘 `DARP_half` 없으면 자동 재계산

**대시보드 훈련 권장 카드 개선 (`views_dashboard_cards.py`):**
- UTRS 단독 판단 → ACWR/CIRS/DI 종합 보정
  - ACWR 1.0~1.3 + CIRS < 30 + DI > 80 → effective_level +1 상향
  - ACWR > 1.5 → effective_level -1 하향
- ACWR 과부하 경고 notes 추가 (> 1.5 빨간, 1.3~1.5 주황)
- 오늘 계획된 훈련 비교 블록 추가
  - `planned_workouts` 테이블에서 오늘 계획 조회
  - effective_level vs 계획 강도 비교 → "계획대로 진행 / 강도 낮춰 진행 / 건너뛰기 권장" 색상 표시
- `context_builders.py`: 대시보드 AI 컨텍스트에 `planned_workout` 포함
- `prompt_config.py`: `dashboard_recommendation` 프롬프트에 계획 대비 조언 지시 추가

**Shape 라벨 소스 불일치 수정 (`views_dashboard_cards.py`):**
- 기존: 값은 `darp_data["half"]["race_shape"]`(84%), 라벨은 `MarathonShape` metric의 `race_distance_km`(10km) → "10K Shape" 오표시
- 수정: `shape_dist_key` 파라미터 추가, DARP 소스 거리와 라벨 일치
- `_render_darp_mini` Shape 배지도 "Shape" → "Half Shape"/"10K Shape" 등 명시

**목표 거리 기반 Shape/DARP 우선 표시 (`views_dashboard.py`):**
- `get_active_goal()` 조회 → `_goal_dist_key` 결정
- 대시보드 피트니스 카드 + DARP 카드 모두 목표 거리 shape 우선 표시
- 목표 없으면 half → full → 10k → 5k 순서 fallback

---

## [v0.4-stream-fix] 2026-03-27

### Stream 데이터 접근 버그 수정 + CTL/ATL 자체 계산

**Stream 접근 경로 수정 (핵심 버그):**
- 동기화: activity_streams 테이블에 저장
- 분석: activity_detail_metrics.stream_file 파일 경로 탐색 → 항상 None!
- 수정: activity_streams DB 테이블 우선 조회 (5곳 전부)
- 영향: EF, Decoupling, VDOT_ADJ(Stream 역치), maxHR(30초 peak), HR존 분석

**CTL/ATL/TSB 자체 계산 (ctl_atl.py 신규):**
- Intervals.icu API가 과거 CTL/ATL 미제공 (최근 ~30일만)
- DailyTRIMP 기반 EMA: CTL(42일), ATL(7일), TSB=CTL-ATL
- Intervals 값 있는 날짜는 스킵, 없는 날짜만 source='runpulse'로 채움

**레이스 분류기 수정:**
- 원본 event_type 태그 최우선 (Garmin "race" → 무조건 레이스)
- 풀마라톤 HR 75%+ 대응 (기존 90% → 거리별 차등)

**MarathonShape VDOT_ADJ 통일:**
- DARP/eFTP/MarathonShape 모두 VDOT_ADJ 사용 → Shape 카드 간 일관성

**DARP Shape 배지:**
- half → full → 10k → 5k 우선순위로 목표 거리 Shape 표시


