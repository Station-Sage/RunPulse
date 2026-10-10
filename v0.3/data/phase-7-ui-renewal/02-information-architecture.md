# Phase 7 UI Renewal — 정보 구조 (IA)

**문서 상태**: Draft v0.2
**작성일**: 2026-06-09 (v0.1) / 2026-06-10 (v0.2)
**전제 문서**: `00-diagnostic-and-direction.md` (A2 결정), `01-design-principles.md` (P4·P8'), `REVIEW-03-today-as-gateway-and-mobile-ia.md` (v0.3)
**후속 문서**: `03-screen-catalog.md`

---

## 이 문서의 목적

3탭+관리 서랍 IA의 전체 라우트 트리, URL 스키마, 네비게이션 패턴, 인증 상태별 분기, 영역 간 이동 흐름을 정의한다. 화면의 내용(와이어프레임)은 `03-screen-catalog.md`에서 다룬다.

> **v0.2 개정 요지 (REVIEW-03)**: 기존 5+1 의도 기반 IA를 폐기하고 **관여 기반 관문 IA**로 전환한다. Today는 사용자를 깊이별로 끌어당기는 관문이 되며, Story·Plan의 독립 탭은 제거된다. 하단 탭은 3개(Today/Library/Coach), 관리 항목은 상단 3선 메뉴로 분리한다. 자세한 배경은 REVIEW-03 참조.

---

## 1. 영역 개요 — 3탭 + 관리 서랍

| 영역 | URL prefix | 핵심 의도 | 네비게이션 위치 |
|------|-----------|-----------|----------------|
| **Today** | `/today` | 관문 — 어느 깊이에 있든 받아주고 한 단계 더 끌어당김 | 하단 탭 (첫 번째) |
| **Library** | `/library` | 왜 이 숫자가 이런가 — 781 지표 전체 탐색 | 하단 탭 (두 번째) |
| **Coach** | `/coach` | 목표·계획 수립/수정·조정·대화 (작업 목적지) | 하단 탭 (세 번째) |
| **Data/설정** | `/data` | 소스 연결·동기화·export·계정·설정 | 상단 3선(햄버거) 메뉴 |

**흡수된 영역**:
- **Story**(`/story`)는 독립 탭에서 제거 → Today L2(성장 내러티브)로 흡수, 전체 보기는 Library 연속.
- **Plan**(`/plan`)은 둘로 분리 → 계획 **현황**(준수율·다음 세션)은 Today L2로 흡수, 계획 **수립·수정 작업**은 Coach가 담당.
**확장 시 분리 원칙**: Story·Plan은 현재 Today·Coach에 흡수되지만, 각 영역이 독립 작업량·진입 빈도가 충분히 커지면 별도 하단 탭으로 재분리할 수 있다. 흡수는 모바일 단순성을 위한 현 단계 결정이며 영구 고정이 아니다. 재분리 시 IA 라우트는 이미 /library/story·/coach/plan/*로 분리돼 있으므로 탭만 승격하면 된다.

---

## 2. 전체 라우트 트리

```
/                                   # 인증 분기점 (§2.1)
│
├── [공개 — 비로그인]
│   ├── /                           # S0 공개 랜딩 (가치 증명 + 정직한 데모)
│   ├── /demo                       # 샘플 러너 데이터로 Today 관문 체험
│   └── /auth                       # 가입/로그인 (현 CF+GitHub, 향후 OAuth)
│
└── [보호 — 로그인]
    ├── /today                      # 관문 (랜딩). 상태 변형: S2 콜드스타트 / S3 충만
    │
    ├── /library
    │   ├── /library                # Library 홈 (시맨틱 그룹 매트릭스)
    │   ├── /library/activities
    │   │   ├── /library/activities/:id
    │   │   └── /library/activities/:id/streams
    │   ├── /library/metrics
    │   │   └── /library/metrics/:slug
    │   ├── /library/wellness
    │   │   └── /library/wellness/:date
    │   ├── /library/providers      # Provider 비교 (동적 매트릭스, AO-2)
    │   └── /library/story          # (구 /story 흡수) 성장 내러티브 전체 보기
    │       ├── /library/story/:year/:month
    │       └── /library/story/milestones
    │
    ├── /coach
    │   ├── /coach                  # Coach 홈 (대화 목록 / 새 대화 / 작업 진입)
    │   ├── /coach/:threadId         # 대화 스레드
    │   └── /coach/plan             # 계획 수립·수정 작업 영역 (구 /plan/new·compare·session 흡수)
    │       ├── /coach/plan/new      # 새 프로그램 생성 (목표 입력 → 옵션 비교)
    │       ├── /coach/plan/compare  # 프로그램 비교 (3~5개 병렬)
    │       ├── /coach/plan/:id      # 프로그램 상세 (주간 캘린더 + 적응 상태)
    │       ├── /coach/plan/:id/session/:week/:day
    │       └── /coach/plan/:id/review
    │
    └── /data                       # 상단 3선 메뉴로 진입 (하단 탭 아님)
        ├── /data                   # 내 데이터 개요
        ├── /data/sources           # 소스 연결 관리
        ├── /data/sync              # 동기화 상태 및 실행
        ├── /data/export            # 데이터 내보내기 (P8')
        └── /data/settings          # 앱 설정·계정
```

> **설계 노트 — Plan 라우트 귀속**: 계획의 *현황 보기*는 Today에 흡수되므로 별도 라우트가 없다(Today 블록). 계획의 *작업*(생성·비교·수정)은 Coach의 하위(`/coach/plan/*`)로 귀속해, "만드는 것은 Coach"라는 §1 원칙을 URL로 표현한다.

### 2.1 인증 상태별 라우팅 분기 (신규)

RunPulse는 SaaS이므로 비로그인/로그인 라우트를 분리한다(REVIEW-03 §8·§10).

```
요청 /
  ├── 비로그인 → / (S0 공개 랜딩)
  │     └── /demo (체험), /auth (가입/로그인)
  └── 로그인 → /today 로 리다이렉트
        └── 보호 라우트 미인증 접근 시 → /auth?next=<원경로>
```

- **공개 라우트**: `/`, `/demo`, `/auth`. 인증 없이 접근 가능.
- **보호 라우트**: 그 외 전부. 미인증 시 `/auth`로 리다이렉트하고 `next`로 원경로 보존.
- **G0 스위치와의 공존**: 미인증 분기(S0)는 `ui_default`(v1/v2) 판정보다 **앞단**, 인증 후 생애주기 판정(S1/S2/S3)은 **뒷단**이다. 신규 가입자는 `ui_default`가 비어 있으면 v2로 시작한다(REVIEW03 §2.4, D-L6).
- **데모**: `/demo`는 명시적 샘플 데이터(P8' 투명성)로 Today 관문 흐름을 그대로 체험시키되, 저장·체크인 등 쓰기 동작은 가입 유도로 전환.

---

## 3. URL 스키마 규칙

### 3.1 원칙

소문자 kebab-case, 명사 중심, ID는 path parameter(`:id`, `:slug`), 영역 prefix 항상 포함. (v0.1과 동일)

### 3.2 Query string 허용 범위

```
/library/activities?sport=running&from=2026-01-01&to=2026-03-31
/library/metrics?group=fitness&provider=garmin
/library/story?month=2026-05
```

필터·정렬·페이지네이션에만 사용.

### 3.3 구 URL → 신 URL 리다이렉트

```
/dashboard         → /today
/report            → /library/story        # (변경) Story 흡수
/story             → /library/story        # (신규) 구 v2 Story 라우트 흡수
/activities        → /library/activities
/activity/:id      → /library/activities/:id
/training          → /coach/plan           # (변경) Plan 작업 → Coach 귀속
/plan              → /today                # (신규) Plan 현황은 Today로
/plan/:id          → /coach/plan/:id       # (신규) Plan 작업 라우트 이전
/ai-coach          → /coach
/sync              → /data/sync
/settings          → /data/settings
```

v1 URL은 v2 전환 시점까지 301 리다이렉트로 유지.

---

## 4. 네비게이션 구조

### 4.1 데스크탑 (≥ 1024px)

```
┌─────────────────────────────────────────────────┐
│ RunPulse        [Today | Library | Coach]    [☰] │  ← 상단: 3탭 + 3선
│ ─────────────────────────────────────────────────│
│  [메인 콘텐츠 영역]          [우측 패널]           │
│                              (드릴다운/컨텍스트)   │
└─────────────────────────────────────────────────┘
```

- 상단 탭: Today / Library / Coach
- 상단 우측 3선(☰): Data·소스·동기화·내보내기·설정·계정·로그아웃
- 우측 패널: 드릴다운, EvidenceQuote 점프, Coach 컨텍스트 차트
- **반응형 IA**: 모바일에서 Today에 흡수된 Story·Plan 현황은 데스크탑에서 우측 패널/사이드 영역으로 더 넓게 펼칠 수 있다. IA는 하나, 표현만 뷰포트별로 다르게.

### 4.2 모바일 (< 1024px)

```
┌──────────────────────────┐
│  [☰]            RunPulse  │  ← 상단: 3선 메뉴 (관리 서랍)
│  [콘텐츠]                 │
│                          │
├──────────────────────────┤
│   Today  Library  Coach  │  ← 하단 탭 바 (3개)
└──────────────────────────┘
```

- 하단 탭 바: Today / Library / Coach (3개)
- 상단 좌측 3선(☰): Data·소스·동기화·내보내기·설정·계정·로그아웃 (자주 안 쓰는 관리 항목만)
- 드릴다운: 풀스크린 슬라이드업 시트

> **3선 메뉴 원칙**: 3선은 "관리·설정 서랍"이지 "기능 탭 대체물"이 아니다. 일상적으로 도는 핵심 기능(상태·데이터·계획)은 절대 3선에 숨기지 않고 3탭 안에서 닿게 한다.

### 4.3 탭 선택 상태 유지

각 탭은 마지막 방문 상태를 기억한다(History stack per tab). 탭 전환 시 스크롤 위치·열린 패널·필터를 복원한다. (v0.1과 동일)

---

## 5. 영역 진입 흐름

### 5.1 Today — 관문 (Progressive Engagement)

REVIEW-03 §3의 4층 관여 구조를 그대로 따른다. 세로 스크롤 = 관여 깊이.

```
진입: 앱 실행 또는 Today 탭
↓
Today 화면 (단일 스크롤, 상태 변형 S2/S3)
  ├── L0 즉시 브리핑: 오늘 한 줄 판단, Readiness, 동기화 상태
  │     └── "왜?" 탭 → L1 근거 펼침
  ├── L1 내 상태 요약: 회복(HRV·수면·BB), 최근 활동, 주간 누적
  │     └── 지표 탭 → 우측 패널 계산 분해 (P2), 활동 탭 → /library/activities/:id
  ├── L2 흐름·훈련·성장:
  │     ├── 성장 내러티브 (Story 흡수) → "전체 보기" → /library/story
  │     ├── 계획 현황·다음 세션 (Plan 현황 흡수) → "계획 세우기/수정" → /coach/plan
  │     └── AI 제안 (RecommendationCard, P1)
  └── L3 데이터 드릴다운: 781 지표 트리 → Library 영역으로 연속
```

### 5.2 Library — 데이터 탐색

기존 v0.1 §5.3 구조 유지에 **Story 흡수 라우트** 추가.

```
진입: Library 탭
↓
Library 홈 (시맨틱 그룹 × Provider 동적 매트릭스, AO-2)
  ├── [활동] → /library/activities → :id → streams
  ├── [메트릭] → /library/metrics → :slug (분해 P2 + 동적 Provider 비교 P3)
  ├── [웰니스] → /library/wellness → :date
  ├── [Provider 비교] → /library/providers (동적 매트릭스)
  └── [성장 스토리] → /library/story (구 Story 흡수, 월별 내러티브 + 마일스톤)
```

### 5.3 Coach — 작업 목적지 (대화 + 계획 수립)

Coach는 단순 대화가 아니라 목표·계획 수립/수정/조정을 수행하는 작업 영역이다.

```
진입: Coach 탭
↓
Coach 홈
  ├── [대화] 이전 대화 목록 / 새 대화 → /coach/:threadId
  │     ├── 대화창 (RecommendationCard + EvidenceQuote, P1)
  │     └── 근거 칩 탭 → 우측 패널 원천 데이터
  └── [계획 작업] → /coach/plan
        ├── [진행 중 프로그램] → /coach/plan/:id (주간 캘린더 + 적응 상태 P7)
        │     └── 세션 → /coach/plan/:id/session/:week/:day (상태 기반 조정)
        └── [프로그램 없음] → /coach/plan/new
              ├── 목표 입력 (레이스·날짜·목표 시간)
              ├── 러너 프로필 자동 요약 (athlete_profile_snapshots, D4)
              └── 3~5개 생성 → /coach/plan/compare → 선택 → /coach/plan/:id
```

> Plan의 *현황*(이번 주 세션·CTL 진행률)은 Today L2에서 읽고, *작업*(생성·수정·조정)은 여기서 한다. 보는 것과 만드는 것의 분리.

---

## 6. 영역 간 이동 — 컨텍스트 유지 패턴

### 6.1 드릴다운 이동 (P2)

```
Today의 CTL 클릭 → 우측 패널 계산 분해 (영역 이동 없음)
  → [더 보기] → /library/metrics/ctl (브레드크럼 "← Today")
```
```
Today L2 성장 내러티브 인라인 차트 클릭 → 우측 패널 추세
  → [전체 보기] → /library/story 또는 /library/metrics/:slug?from=today
```

### 6.2 Coach에서 데이터 참조

Coach 대화 중 데이터 참조는 Library 이동 없이 인라인 패널에서 처리. (v0.1과 동일)

### 6.3 Today ↔ Coach(Plan) 연동

계획 현황과 작업의 분리에 따른 양방향 연결.

```
Coach /coach/plan/:id/session/3/2 에서 세션 수정
  → Today L2 "계획 현황·다음 세션" 자동 반영
Today L2 "다음 세션" → [수정] → /coach/plan/:id/session/3/2 이동
```

### 6.4 활동 → 다중 영역 접근

단일 활동 URL은 `/library/activities/:id` 하나. Today·Library·Coach 어디서 인용해도 이 정규 URL로 수렴. (v0.1과 동일)

---

## 7. 딥링크 / 외부 진입

### 7.1 알림에서 진입

| 알림 유형 | 딥링크 |
|----------|--------|
| 부상 위험 경보 | `/today#injury-alert` |
| 동기화 완료 | `/today` |
| 레이스 D-3 알림 | `/coach/plan/:id` |
| 마일스톤 달성 | `/library/story?month=YYYY-MM#milestone` |

### 7.2 공유 링크 (P8' Data Ownership & Transparency)

외부 소셜 공유는 지원하지 않는다(비전에서 배제). 단, **S0 공개 랜딩/데모**는 비로그인 진입점이므로 마케팅 외부 링크(`/`, `/demo`)는 허용한다. 개인 데이터 공유는 export(`/data/export`)를 통한 본인 소유 형태로만.

---

## 8. 네비게이션 엣지 케이스

### 8.1 데이터 없음 / 콜드 스타트 상태 (REVIEW-03 §9)

모든 화면은 "데이터 충만(S3)"과 "데이터 0/소량(S2)" 변형을 쌍으로 가진다. 빈 상태는 죽은 화면이 아니라 다음 행동 유도 화면이다.

| 상황 | Today | Library | Coach |
|------|-------|---------|-------|
| 비로그인 (S0) | `/`로 (공개 랜딩·데모) | 〃 | 〃 |
| 연결 0·백필 중 (S2) | 백필 진행 가시화 + 소량 데이터 의미화 | "채워지는 중" 표시 | 사용 가능 (목표 셋업부터) |
| 활동 0건 | "첫 기록을 남겨보세요" + QuickInput | 빈 목록 + 연결 유도 | 목표·계획 수립 유도 |
| 계획 현황 없음 | L2 계획 블록을 "계획 시작" 후크로 | 정상 | `/coach/plan/new` 유도 |

### 8.2 오프라인 상태 (P8' 재해석)

RunPulse는 SaaS·서버 가공이므로 완전 오프라인 가용성은 보장 대상이 아니다(REVIEW-03 §8). 네트워크 단절 시 캐시된 마지막 상태를 읽기 전용으로 표시하고, 쓰기/동기화/AI 응답은 재연결 시 처리한다. (향후 PWA 도입 시 재검토)

| 영역 | 오프라인 동작 |
|------|-------------|
| Today / Library | 캐시된 마지막 데이터 읽기 전용 표시 |
| Coach | 제한 — 새 AI 응답·계획 생성 불가, 이전 대화 열람 가능 |
| Data/sync | 제한 — 동기화 실행 불가 |

### 8.3 모바일 하단 탭 3개 고정

탭 바는 3개 고정(Today / Library / Coach). Data·설정 등은 상단 3선(☰)으로 진입. 하단 탭 추가는 모바일 단순성 원칙에 따라 금지.

---

## 9. URL 마이그레이션 전략 (v1 → v2)

(v0.1 §9 유지) `/v2/*` prefix 독립 구동 → v1 병행 → 301 리다이렉트 → v1 제거. `/data/settings`의 "새 UI(v2) 사용" 토글로 전환. 단 §3.3 리다이렉트 표가 Story/Plan 흡수에 맞춰 갱신됨에 유의.

---

## 작성 이력

- v0.1 (2026-06-09): 초안 — 5+1 영역 라우트 트리, URL 스키마, 네비게이션 구조, 영역 간 이동 패턴, 마이그레이션 전략
- v0.2 (2026-06-10): REVIEW-03 반영 전면 개정 — 5+1 → 3탭(Today/Library/Coach)+상단 3선. Story 독립 탭 제거(→ Today L2 흡수 + /library/story). Plan 분리(현황→Today L2, 작업→/coach/plan/*). 인증 상태별 라우팅 분기(§2.1, 공개/보호 라우트) 신규. 리다이렉트 표·엣지케이스·오프라인(P8') 갱신.

---

주요 판단 두 가지를 짚어드립니다. 첫째, **Plan 작업을 `/coach/plan/*` 하위로 귀속**시켰습니다. "만드는 것은 Coach"라는 합의를 URL 구조로 명시하기 위함인데, 만약 Plan 작업이 Coach 대화와 독립적으로 충분히 큰 영역이라면 `/plan/*`을 유지하되 진입만 Coach 탭에서 하는 방식도 가능합니다. 둘째, **Story를 `/library/story`로 흡수**했습니다. 성장 내러티브 전체 보기가 데이터 탐색 성격이라 Library가 자연스럽다고 봤습니다.

이 두 귀속 방식이 의도에 맞나요? 맞다면 v0.2로 확정하고 다음 순서(§6 진행순서의 3번 — `03-screen-catalog.md` 반영)로 넘어가겠습니다.