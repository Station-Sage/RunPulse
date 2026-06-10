# Phase 7 UI Renewal — 마이그레이션 로드맵

**문서 상태**: Draft v0.1  
**작성일**: 2026-06-10  
**전제 문서**: `05-tech-architecture.md`, `06-data-layer-extensions.md`  
**이 문서가 마지막 설계 문서**

---

## 이 문서의 목적

Phase 7a→7d 4단계의 범위, 산출물, 검증 기준, 단계 전환 조건을 정의한다.  
날짜(일정)는 명시하지 않는다 — 각 단계의 완료 조건을 기준으로 진행한다.

---

## 전체 흐름

```
Phase 7a            Phase 7b              Phase 7c          Phase 7d
──────────────      ──────────────        ──────────────    ──────────────
기반·Coach MVP      탐색·Plan 기반         계획·ML            확장·전환

D5 서비스레이어      D2 그룹 마스터         D4 프로필 스냅샷   신규 데이터 소스
D3 user_inputs      Story UI              Plan ML 개인화    COROS/Polar/etc
D1 트리 계층         Library 전체           PlanFitReport     Training Balance
Flask API 골격      ProviderComparison     PWA               Radar 완성
Today UI            Plan 정적 비교 기반    state-bound 조정   /v2/ → 기본
Coach MVP UI        (3~5 옵션 골격)                          v1 제거
Library/activities  
```

---

## Phase 7a — 기반 구축 + Coach MVP

**목표**: API 골격, Today, Library/activities, 그리고 Coach MVP를 동작시킨다.  
00-diagnostic-and-direction.md 4.1에서 결정: Coach MVP는 Today + 입력과 함께 1단계에 묶여야 가치 발현이 즉시 보인다.  
베타 토글 ON 시 `/v2/today`, `/v2/library/activities`, `/v2/coach`(MVP)가 실제 데이터를 표시한다.

### 전제조건 (시작 전 충족)

- [ ] BACKLOG의 `AUDIT-SERVICE-LAYER` 결정 — D5 진행 승인 확인
- [ ] `frontend/` SvelteKit 프로젝트 초기화 완료
- [ ] `src/api/` 블루프린트 등록 완료 (`serve.py`)

### 산출물

**데이터 레이어**
- [ ] D5: `src/services/` 8개 파일 — stub + Today/Library/Coach 구현 완료
  - `today_service.get_today_status()`, `get_today_briefing()`, `get_recent_activities()`
  - `activity_service.list_activities()`, `get_activity_detail()`, `get_activity_streams()`
  - `coach_service.list_threads()`, `create_thread()`, `add_message()` (스레드 CRUD + AI 호출 래핑)
  - `save_checkin()` (D3 연동)
- [ ] D3: `user_inputs`, `ai_feedback` DDL + `db_setup.migrate()` 등록
- [ ] D1: `upsert_metric()` `parent_metric_id` 파라미터 추가 + fitness Calculator 자식 저장

**Flask API**
- [ ] `GET /api/v1/today` — TodayStatus + Briefing + RecentActivities
- [ ] `POST /api/v1/today/checkin` — QuickInput 저장
- [ ] `GET /api/v1/library/activities` — 목록 (필터/페이지)
- [ ] `GET /api/v1/library/activities/:id` — 상세
- [ ] `GET /api/v1/library/activities/:id/streams` — 스트림

**Flask API (Coach MVP 추가)**
- [ ] `GET /api/v1/coach/threads`
- [ ] `POST /api/v1/coach/threads`
- [ ] `GET /api/v1/coach/threads/:id`
- [ ] `POST /api/v1/coach/threads/:id/messages` — AI 응답 포함

**SvelteKit UI**
- [ ] 공통 레이아웃: 탭 바 (데스크탑/모바일), 우측 패널 슬롯, 슬라이드업 시트
- [ ] `<EvidenceQuote>` (C1) — 기본 칩 + 패널 열기
- [ ] `<MetricCell>` (C2) — 값 + Provider 배지 + 상태 도트
- [ ] `<QuickInput>` (C5) — 저장 기능 포함
- [ ] `<RecommendationCard>` (C6) — EvidenceQuote 연동
- [ ] Today 화면 — 03-screen-catalog.md 1-A 구현
- [ ] Library/activities 화면 — 3-B, 3-C, 3-D 구현
- [ ] **Coach MVP 화면** — 스레드 목록 + 대화창 (5-A 기본 구현, 컨텍스트 패널 제외)
- [ ] `/v2/` 베타 토글 UI (`/data/settings`)

### 검증 기준

```
✓ GET /api/v1/today → 실제 DB 데이터 반환 (200ms 이내)
✓ QuickInput 저장 → user_inputs 행 생성 확인
✓ Library/activities 목록 → v_canonical_activities 기반 (중복 없음)
✓ Activity 상세 → 메트릭 8개 이상 표시
✓ EvidenceQuote 칩 탭 → 패널 열림
✓ MetricCell → Provider 배지 항상 표시 (빈 배지 없음)
✓ 오프라인 상태 → Today 화면 캐시에서 정상 렌더
✓ 모바일 375px → 레이아웃 깨짐 없음
✓ pytest tests/ → 전체 통과 (기존 1188개 + 신규 테스트)
```

### 7a → 7b 전환 조건

- 검증 기준 전체 충족
- Today + Library/activities 베타 사용 1주 이상 (실제 데이터)
- D1 트리 계층: CTL/UTRS 자식 메트릭 DB에 실제 저장 확인

---

## Phase 7b — 핵심 탐색 + Plan 기반

**목표**: Story와 Library 전체를 완성하고, Plan 정적 비교 골격을 구축한다.  
메트릭 브라우저, Provider 비교, 웰니스, 고정 훈련 플랜 선택이 동작한다.

### 전제조건

- Phase 7a 완료
- D2 activity_groups 백필 완료 (기존 활동 그룹 마스터 생성)

### 산출물

**데이터 레이어**
- [ ] D2: `activity_groups` DDL + `assign_group_id()` 수정 + 백필 스크립트 실행
- [ ] D1: utrs/cirs/race_readiness Calculator 자식 메트릭 저장 수정
- [ ] `metrics_service.get_metric_breakdown()` — parent_metric_id 트리 조립
- [ ] `activity_service.get_provider_comparison()` — D2 연동
- [ ] `plan_service.get_static_plan_templates()` — 고정 훈련 프로그램 3~5개 반환 (ML 없음)

**Flask API**
- [ ] `GET /api/v1/story` — 내러티브 + 하이라이트 + 마일스톤
- [ ] `GET /api/v1/story/milestones`
- [ ] `GET /api/v1/library/metrics` — 그룹 목록 + 현재값
- [ ] `GET /api/v1/library/metrics/:slug` — 상세 + 추세 + 분해 트리
- [ ] `GET /api/v1/library/wellness`
- [ ] `GET /api/v1/library/providers` — Provider 비교
- [ ] `GET /api/v1/plan/templates` — 정적 플랜 템플릿 목록
- [ ] `GET /api/v1/plan/compare` — 템플릿 비교 (CTL·주간 거리 기반)
- [ ] `POST /api/v1/plan` — 템플릿 선택 확정

**SvelteKit UI**
- [ ] `<MetricBreakdown>` (C3) — parent_metric_id 트리 렌더링
- [ ] `<ProviderComparison>` (C4) — 불일치 경고 포함
- [ ] `<TimelineNarrative>` (C7) — 내러티브 + 인라인 스파크라인
- [ ] Story 화면 — 2-A, 2-B 구현
- [ ] Library/metrics 화면 — 3-E, 3-F 구현
- [ ] Library/wellness 화면
- [ ] Library/providers 화면 — 3-G 구현
- [ ] Library 홈 — 3-A 구현
- [ ] Plan 새 프로그램 화면 (정적 비교 골격) — 4-C, 4-D 구현

### 검증 기준

```
✓ MetricBreakdown: CTL → TSS 자식, UTRS → 4개 자식 트리 표시
✓ ProviderComparison: Garmin↔Strava 거리 차이 경고 표시
✓ Story 내러티브: EvidenceQuote 칩 최소 3개 포함
✓ Library/metrics: 전체 시맨틱 그룹 13개 탐색 가능
✓ Provider 배지: Library 전체에서 출처 없는 수치 없음 (P3)
✓ 드릴다운 3레벨: Summary → Breakdown → Library 이동 동작
✓ Plan 정적 비교: 3개 이상 고정 플랜 템플릿 표시 + 비교 가능
✓ Plan 선택 확정 → active plan 생성 확인
```

### 7b → 7c 전환 조건

- 검증 기준 전체 충족
- Story + Library + Plan 정적 비교 베타 사용 1주 이상
- D2 활동 그룹 마스터: 기존 그룹 100% 마이그레이션 확인

---

## Phase 7c — 계획 ML 개인화 + PWA

**목표**: Plan ML 개인화와 PlanFitReport를 완성하고 PWA를 적용한다.  
정적 템플릿에서 개인 프로필 기반 ML 플랜 생성으로 업그레이드된다.

### 전제조건

- Phase 7b 완료 (Plan 정적 비교 동작 중)
- D4 athlete_profile_snapshots 초기 스냅샷 생성

### 산출물

**데이터 레이어**
- [ ] D4: `athlete_profile_snapshots` DDL + 초기화 스크립트 실행
- [ ] `plan_service.generate_plan_options()` — D4 VDOT + CTL 기반 ML 개인화 옵션 생성
- [ ] `plan_service.get_plan_fit_report()` — 현재 상태 vs 플랜 적합도 평가
- [ ] `plan_service.get_session_adjustments()` — HRV/TSB 기반 세션 조정
- [ ] `wellness_service.get_wellness_for_date()` — user_inputs 병합

**Flask API**
- [ ] `GET /api/v1/plan/active`
- [ ] `POST /api/v1/plan/generate` — ML 개인화 옵션 3~5개 생성 (D4 기반)
- [ ] `GET /api/v1/plan/:id`
- [ ] `GET /api/v1/plan/:id/fit-report` — PlanFitReport
- [ ] `GET /api/v1/plan/:id/session/:week/:day` — 상태 조정 포함
- [ ] `PUT /api/v1/plan/:id/session/:week/:day/accept-adjustment`

**SvelteKit UI**
- [ ] Plan 홈 (진행 중 / 없음 분기) — 4-A, 4-B 구현 (ML 개인화 옵션으로 업그레이드)
- [ ] Plan 새 프로그램 생성 3단계 플로 — 4-C 구현 (ML 옵션 표시)
- [ ] Plan 일일 세션 상세 (상태 조정 UI) — 4-E 구현
- [ ] PlanFitReport 화면
- [ ] Today 화면 "오늘 예정 세션" — Plan 연동 활성화
- [ ] PWA Service Worker — Cache-First 전략 적용

### 검증 기준

```
✓ ML 플랜 생성: 목표 + athlete_profile → 3개 개인화 옵션 반환
✓ PlanFitReport: 현재 CTL·VDOT 대비 플랜 난이도 평가 표시
✓ 세션 조정: HRV −12% 시 거리 −10~15% 조정 제안 표시
✓ Plan → Today 연동: 세션 수정이 Today에 반영
✓ state-bound 배지: 모든 세션 카드에 ACWR/HRV 상태 표시
✓ PWA: 오프라인 Today + Library + Plan 정상 렌더 (새 동기화 없음)
✓ athlete_profile_snapshots: Plan 생성 시 스냅샷 행 자동 생성
```

### 7c → 7d 전환 조건

- 검증 기준 전체 충족
- Plan ML + PWA 베타 사용 2주 이상
- 기존 v1 `/training` 화면과 기능 동등성 확인 (누락 기능 없음)

---

## Phase 7d — 신규 데이터 소스 확장 + v2 전환

**목표**: 신규 데이터 소스를 통합하고 Training Balance Radar를 완성한 후 v2를 기본값으로 전환한다.  
v1 HTML 뷰는 리다이렉트 전용으로 유지하다 제거한다.

### 전제조건

- Phase 7c 완료
- 신규 데이터 소스 API 접근 가능 여부 확인 (COROS / Polar / Apple Health / Whoop)

### 산출물

**데이터 레이어**
- [ ] 신규 소스 커넥터 — COROS 또는 Polar 중 1개 우선 (기존 `src/connectors/` 패턴 동일)
- [ ] Training Balance Radar 메트릭 계산 — 다차원 레이더 데이터 (stress/load/recovery/form/sleep/hrv)
- [ ] `sync.py` 신규 소스 등록

**Flask API**
- [ ] `GET /api/v1/data/sources` — 소스 연결 상태 (신규 소스 포함)
- [ ] `GET /api/v1/data/sync`
- [ ] `POST /api/v1/data/sync` — 동기화 실행
- [ ] `GET /api/v1/data/settings`
- [ ] `GET /api/v1/library/metrics/training-balance` — Training Balance Radar 데이터

**SvelteKit UI**
- [ ] Data 화면 — 6-A, 6-B 구현 (신규 소스 연결 카드 포함)
- [ ] Coach 스레드 완성 — 5-B 컨텍스트 패널 구현 (7a MVP에서 제외된 부분)
- [ ] Training Balance Radar 차트 — Library 또는 Today 내 표시
- [ ] 베타 토글 → 전체 영역 커버 확인

**v2 기본 전환**
- [ ] Flask 쿠키 기반 베타 토글 → **기본값 ON**으로 변경
- [ ] 구 URL 301 리다이렉트 활성화:
  ```
  /dashboard  → /v2/today
  /report     → /v2/story
  /activities → /v2/library/activities
  /training   → /v2/plan
  /ai-coach   → /v2/coach
  /sync       → /v2/data/sync
  /settings   → /v2/data/settings
  ```
- [ ] v1 HTML 뷰 코드 제거 계획 작성 (별도 PR)

### 검증 기준

```
✓ 신규 소스 동기화: COROS or Polar 활동 DB 저장 확인
✓ Training Balance Radar: 6개 축 데이터 정상 렌더링
✓ Coach 컨텍스트 패널: 대화 중 메트릭 차트 패널 표시
✓ Data 화면: 소스 연결 상태 + 동기화 실행 가능
✓ 구 URL 접근 시 v2로 301 리다이렉트
✓ 전체 영역 베타 토글 없이 기본 진입
✓ v1 기능 완전 대체 확인 (기능 체크리스트 전체 통과)
✓ Lighthouse PWA 점수 ≥ 80
✓ Core Web Vitals: LCP ≤ 2.5s, CLS ≤ 0.1
```

### 전환 완료 기준

- 검증 기준 전체 충족
- 2주 기본 운용 중 크리티컬 버그 없음
- v1 HTML 뷰 제거 PR 생성 (즉시 머지 아님 — 안정화 후)

---

## 롤백 전략

### Phase 7a~7c (베타 토글 ON 상태)

```
롤백 조건: 베타 화면에서 데이터 표시 오류 또는 API 500 연속 발생
롤백 방법: 쿠키 'use_v2' 삭제 → v1 복귀 (서버 재시작 불필요)
영향 범위: v2 UI만 — 데이터 파이프라인·v1 화면 무영향
```

### Phase 7d (v2 기본 전환 후)

```
롤백 조건: 기본 전환 후 주요 기능 불가 버그
롤백 방법: 
  1. Flask 기본값 OFF 복구 (use_v2 쿠키 기본 '0')
  2. 301 리다이렉트 비활성화
  3. v1 화면 복원 (git revert 또는 브랜치 전환)
소요 시간: ~10분 (재배포 불필요)
```

---

## 기능 동등성 체크리스트 (v1 → v2)

v2가 v1을 대체하기 전 확인해야 할 v1 기능 목록.

| v1 기능 | v2 대응 | 단계 |
|---------|--------|------|
| Dashboard — 오늘 상태 | Today 화면 | 7a |
| Dashboard — 최근 활동 목록 | Today + Library/activities | 7a |
| Activity 상세 + 스트림 | Library/activities/:id/streams | 7a |
| Report — 주간/월간 요약 | Story 화면 | 7b |
| Metrics 브라우저 | Library/metrics | 7b |
| HR 존 분포 | Activity 상세 내 표시 | 7a |
| Provider 비교 | Library/providers | 7b |
| Training 계획 보기 | Plan 홈 | 7c |
| AI Coach 대화 (MVP) | Coach 화면 | 7a |
| AI Coach 컨텍스트 패널 | Coach 화면 | 7d |
| 동기화 실행 | Data/sync | 7d |
| 소스 연결 관리 | Data/sources | 7d |
| 설정 | Data/settings | 7d |

---

## 브랜치 전략

```
main                  (안정)
 └── renew/data-architecture   (현재 브랜치 — Phase 7 기반)
       ├── feat/phase-7a-foundation-coach-mvp
       ├── feat/phase-7b-explore-plan-static
       ├── feat/phase-7c-plan-ml-pwa
       └── feat/phase-7d-expansion-switch
```

각 Phase는 feature 브랜치에서 개발 → `renew/data-architecture`로 PR.  
`renew/data-architecture` → `main` 머지는 Phase 7d 완료 후.

---

## 위험 요소

| 위험 | 확률 | 영향 | 대응 |
|------|------|------|------|
| D5 서비스 레이어 범위 예상 초과 | 중 | 7a 지연 | stub 우선 → 점진 충실화 |
| AI 브리핑 응답 지연 (>3s) | 중 | Today UX 저하 | 스켈레톤 + 캐시 우선 전략 |
| SvelteKit adapter-static SPA fallback 미동작 | 낮 | 직접 URL 접근 404 | Flask fallback 핸들러 사전 검증 |
| metric_store 트리 데이터 누락 (D1 백필 전) | 중 | MetricBreakdown 빈 패널 | "계산 데이터 수집 중" graceful fallback |
| v1 → v2 기능 누락 발견 (7d 전환 후) | 중 | 롤백 필요 | 기능 동등성 체크리스트 사전 완료 |

---

## 설계 완료 확인

이 문서를 마지막으로 Phase 7 설계 문서 7개가 완성되었다.

| 문서 | 완료 |
|------|------|
| `00-diagnostic-and-direction.md` | ✓ v0.2 |
| `01-design-principles.md` | ✓ v0.1 |
| `02-information-architecture.md` | ✓ v0.1 |
| `03-screen-catalog.md` | ✓ v0.1 |
| `04-component-catalog.md` | ✓ v0.1 |
| `05-tech-architecture.md` | ✓ v0.1 |
| `06-data-layer-extensions.md` | ✓ v0.1 |
| `07-migration-roadmap.md` | ✓ v0.1 |

**다음 단계**: Phase 7a 구현 시작 — D5 서비스 레이어 → D3 테이블 → Flask API → Today UI 순서.

---

## 작성 이력

- v0.1 (2026-06-10): 초안 — 4단계 로드맵, 단계별 산출물·검증 기준·전환 조건, 롤백 전략, 기능 동등성 체크리스트, 위험 요소
