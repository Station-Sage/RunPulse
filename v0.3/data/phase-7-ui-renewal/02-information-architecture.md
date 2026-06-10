# Phase 7 UI Renewal — 정보 구조 (IA)

**문서 상태**: Draft v0.1  
**작성일**: 2026-06-09  
**전제 문서**: `00-diagnostic-and-direction.md` (A2 결정), `01-design-principles.md` (P4)  
**후속 문서**: `03-screen-catalog.md`

---

## 이 문서의 목적

5+1 영역의 전체 라우트 트리, URL 스키마, 네비게이션 패턴, 영역 간 이동 흐름을 정의한다.  
화면의 내용(와이어프레임)은 `03-screen-catalog.md`에서 다룬다.

---

## 1. 5+1 영역 개요

| 영역 | URL prefix | 핵심 의도 | 네비게이션 위치 |
|------|-----------|-----------|----------------|
| **Today** | `/today` | 오늘 무엇을 할까 | 기본 탭 (첫 번째) |
| **Story** | `/story` | 내 상태는 어떻게 변하고 있나 | 탭 (두 번째) |
| **Library** | `/library` | 왜 이 숫자가 이런가 | 탭 (세 번째) |
| **Plan** | `/plan` | 다음 레이스를 어떻게 준비할까 | 탭 (네 번째) |
| **Coach** | `/coach` | 내 코치와 대화 | 탭 (다섯 번째) |
| **Data** | `/data` | 소스 연결·동기화·설정·export | 더보기 또는 설정 아이콘 |

---

## 2. 전체 라우트 트리

```
/
├── /today                          # 오늘 결정 지원 화면 (랜딩)
│
├── /story
│   ├── /story                      # 이번 달 내러티브 (기본)
│   ├── /story/:year/:month         # 특정 월 내러티브
│   └── /story/milestones           # 마일스톤 타임라인
│
├── /library
│   ├── /library                    # Library 홈 (시맨틱 그룹 매트릭스)
│   │
│   ├── /library/activities         # 활동 목록
│   │   ├── /library/activities/:id # 활동 상세
│   │   └── /library/activities/:id/streams  # 스트림 뷰어
│   │
│   ├── /library/metrics            # 메트릭 브라우저
│   │   └── /library/metrics/:slug  # 메트릭 상세 (계산 분해 + 추세)
│   │
│   ├── /library/wellness           # 웰니스 캘린더
│   │   └── /library/wellness/:date # 특정일 웰니스 상세
│   │
│   └── /library/providers          # Provider 비교 (시맨틱 그룹 × provider 매트릭스)
│
├── /plan
│   ├── /plan                       # Plan 홈 (진행 중 프로그램 또는 시작 유도)
│   ├── /plan/new                   # 새 프로그램 생성 (목표 입력 → 옵션 비교)
│   ├── /plan/compare               # 프로그램 비교 뷰 (3~5개 병렬)
│   ├── /plan/:id                   # 프로그램 상세 (주간 캘린더 + 적응 상태)
│   ├── /plan/:id/session/:week/:day # 일일 세션 상세 (상태 기반 조정 포함)
│   └── /plan/:id/review            # 프로그램 사후 분석
│
├── /coach
│   ├── /coach                      # Coach 홈 (대화 목록 또는 새 대화 시작)
│   └── /coach/:threadId            # 대화 스레드
│
└── /data
    ├── /data                       # Data 홈 (내 데이터 개요)
    ├── /data/sources               # 소스 연결 관리 (Garmin/Strava/Intervals/Runalyze)
    ├── /data/sync                  # 동기화 상태 및 실행
    ├── /data/export                # 데이터 내보내기
    └── /data/settings              # 앱 설정
```

---

## 3. URL 스키마 규칙

### 3.1 원칙

- 소문자 kebab-case
- 명사 중심 (행위 동사 금지 — `/activities/new` 아닌 `/plan/new` 예외는 생성 흐름)
- ID는 path parameter (`:id`, `:slug`) — query string은 필터/페이지에만
- 영역 prefix 항상 포함 (`/library/activities/:id`, not `/activities/:id`)

### 3.2 Query string 허용 범위

```
/library/activities?sport=running&from=2026-01-01&to=2026-03-31
/library/metrics?group=fitness&provider=garmin
/story?month=2026-05
```

필터·정렬·페이지네이션에만 사용. 상태를 URL에 저장해 북마크·공유 가능하게 한다.

### 3.3 구 URL → 신 URL 리다이렉트

```
/dashboard         → /today
/report            → /story
/activities        → /library/activities
/activity/:id      → /library/activities/:id
/training          → /plan
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
│ RunPulse          [Today|Story|Library|Plan|Coach] │  ← 상단 수평 탭
│ ─────────────────────────────────────────────────│
│                                                   │
│  [메인 콘텐츠 영역]          [우측 패널]           │
│                              (드릴다운/컨텍스트)   │
│                                                   │
│                                         [⚙ Data] │  ← 우측 하단 고정
└─────────────────────────────────────────────────┘
```

- 상단 탭: Today / Story / Library / Plan / Coach
- 우측 패널: 드릴다운, EvidenceQuote 점프, Coach 컨텍스트 차트
- Data: 헤더 우측 설정 아이콘 또는 하단 우측 고정 버튼

### 4.2 모바일 (< 1024px)

```
┌──────────────────────────┐
│  [콘텐츠]                 │
│                          │
│                          │
│                          │
├──────────────────────────┤
│ Today Story Lib Plan Coach│  ← 하단 탭 바 (5개)
└──────────────────────────┘
```

- 하단 탭 바: Today / Story / Library / Plan / Coach
- Data: 탭 바에 없음 → Today 또는 Library 헤더의 설정 아이콘
- 드릴다운: 풀스크린 슬라이드업 시트

### 4.3 탭 선택 상태 유지

각 탭은 마지막 방문 상태를 기억한다 (History stack per tab).  
탭 전환 시 스크롤 위치·열린 패널·적용 필터를 복원한다.

---

## 5. 영역 진입 흐름

### 5.1 Today — 오늘 결정 지원

```
진입: 앱 실행 또는 Today 탭 탭
↓
Today 화면 (단일 화면, 스크롤)
  ├── 상단: 오늘 컨디션 체크인 (QuickInput — 10초)
  ├── 섹션1: 오늘 상태 요약 (UTRS·CIRS·TSB)
  │     └── 각 지표 탭 → 우측 패널: 계산 분해 (P2)
  ├── 섹션2: 오늘 AI 브리핑 (RecommendationCard)
  │     └── 근거 칩 탭 → 우측 패널: 원천 데이터 (P1)
  ├── 섹션3: 오늘 예정 세션 (Plan 연동 시)
  │     └── 상태 기반 조정 제안 표시 (P7)
  └── 섹션4: 최근 활동 요약 (최근 3건)
        └── 활동 탭 → /library/activities/:id
```

### 5.2 Story — 내러티브 인사이트

```
진입: Story 탭
↓
Story 화면 (이번 달 기본)
  ├── 헤더: 월 선택기 (← 이전달 / 이번달 →)
  ├── 내러티브 텍스트 (AI 생성)
  │     └── 인라인 차트: 클릭 → Library/metrics/:slug (P2)
  │     └── EvidenceQuote 칩: 클릭 → 해당 활동 또는 메트릭 (P1)
  └── 마일스톤 섹션 (이번 달 주요 기록)
        └── → /story/milestones 전체 보기
```

### 5.3 Library — 데이터 탐색

```
진입: Library 탭
↓
Library 홈 (시맨틱 그룹 × Provider 매트릭스 개요)
  ├── [활동] → /library/activities
  │     ├── 필터 (sport, 날짜, 거리)
  │     └── 활동 카드 탭 → /library/activities/:id
  │           ├── 스트림 탭 → /library/activities/:id/streams
  │           └── 메트릭 탭 → 각 메트릭 탭 시 우측 패널 분해 (P2)
  │
  ├── [메트릭] → /library/metrics
  │     ├── 시맨틱 그룹 13개 필터
  │     └── 메트릭 카드 탭 → /library/metrics/:slug
  │           ├── 추세 차트 (기간 선택)
  │           ├── 계산 분해 (MetricBreakdown) (P2)
  │           └── Provider 비교 (ProviderComparison) (P3)
  │
  ├── [웰니스] → /library/wellness
  │     └── 날짜 탭 → /library/wellness/:date
  │
  └── [Provider 비교] → /library/providers
        (시맨틱 그룹 13개 × provider 4개 전체 매트릭스)
```

### 5.4 Plan — 훈련 계획

```
진입: Plan 탭
↓
Plan 홈
  ├── [진행 중 프로그램 있음] → 프로그램 대시보드
  │     ├── 이번 주 세션 목록 (상태 기반 조정 배지) (P7)
  │     ├── CTL 진행률 바
  │     └── 세션 탭 → /plan/:id/session/:week/:day
  │
  └── [프로그램 없음] → 시작 유도 화면
        └── [새 프로그램 만들기] → /plan/new
              ├── 목표 입력 (레이스, 날짜, 목표 시간)
              ├── 러너 프로필 요약 (데이터 기반 자동)
              ├── 3~5개 프로그램 생성
              └── → /plan/compare (병렬 비교)
                    └── 선택 → /plan/:id (프로그램 시작)
```

### 5.5 Coach — AI 대화

```
진입: Coach 탭
↓
Coach 홈
  ├── [이전 대화 있음] → 대화 목록 + 새 대화 버튼
  └── [처음] → 바로 새 대화 입력창
↓
/coach/:threadId (대화 스레드)
  ├── 좌: 대화 히스토리
  ├── 중: 대화창 (RecommendationCard + EvidenceQuote) (P1)
  │     └── 근거 칩 탭 → 우측 패널: 원천 데이터
  └── 우: 컨텍스트 패널 (코치가 참조 중인 차트/메트릭)
        (데스크탑만, 모바일은 인라인 펼침)
```

---

## 6. 영역 간 이동 — 컨텍스트 유지 패턴

### 6.1 드릴다운 이동 (P2 Drillable Everything)

메트릭·차트 클릭으로 이동할 때 "어디서 왔는지" 맥락이 유지된다.

```
Today의 CTL 64 클릭
  → 우측 패널: CTL 계산 분해 (영역 이동 없음)
  → [더 보기] 클릭
  → /library/metrics/ctl (Library로 이동, 브레드크럼에 "← Today")
```

```
Story의 인라인 차트 클릭
  → 우측 패널: 해당 메트릭 추세 (영역 이동 없음)
  → [Library에서 전체 보기]
  → /library/metrics/:slug?from=story (Library로 이동)
```

### 6.2 Coach에서 데이터 참조

Coach 대화 중 데이터 참조는 Library 이동 없이 인라인 패널에서 처리한다.

```
Coach 대화: "최근 2주 ACWR 보여줘"
  → 우측 패널에 ACWR 차트 표시 (Coach 이탈 없음)
  → [Library에서 보기] 링크 제공 (선택)
```

### 6.3 Plan → Today 연동

오늘의 세션이 Plan에서 왔으면 Today에서도 보인다. 단방향 참조.

```
Plan /plan/:id/session/3/2 에서 세션 수정
  → Today의 "오늘 예정 세션" 자동 반영
  → Today에서 "세션 수정" 버튼 → /plan/:id/session/3/2 이동
```

### 6.4 활동 → 다중 영역 접근

단일 활동은 여러 영역에서 접근되지만 URL은 하나다.

```
/library/activities/:id  (정규 URL)

접근 경로:
  Today 최근 활동 카드 → /library/activities/:id
  Story 인라인 활동 인용 → /library/activities/:id
  Plan 세션 완료 후 연결 → /library/activities/:id
  Coach 대화 중 활동 인용 → 패널에서 미리보기, [전체보기] → /library/activities/:id
```

---

## 7. 딥링크 / 외부 진입

### 7.1 알림에서 진입

| 알림 유형 | 딥링크 |
|----------|--------|
| 부상 위험 경보 | `/today#injury-alert` |
| 동기화 완료 | `/today` |
| 레이스 D-3 알림 | `/plan/:id` |
| 마일스톤 달성 | `/story?month=YYYY-MM#milestone` |

### 7.2 공유 링크 (로컬 퍼스트 원칙 P8)

외부 공유는 지원하지 않는다. 딥링크는 로컬 앱 내부 이동에만 사용.  
(소셜 공유는 비전에서 명시적으로 배제)

---

## 8. 네비게이션 엣지 케이스

### 8.1 데이터 없음 상태

| 상황 | Today | Library | Plan | Coach |
|------|-------|---------|------|-------|
| 동기화 안 됨 | 빈 상태 화면 + 동기화 유도 | 빈 상태 | 빈 상태 | 사용 가능 (제한적) |
| 활동 0건 | "아직 활동이 없습니다" | 빈 목록 | 프로그램 생성 유도 | 사용 가능 |
| Plan 없음 | 세션 섹션 숨김 | 정상 | 생성 유도 화면 | 정상 |

### 8.2 오프라인 상태 (P8 Local-First)

| 영역 | 오프라인 동작 |
|------|-------------|
| Today | 정상 (로컬 DB) |
| Story | 정상 (캐시된 내러티브) |
| Library | 정상 (로컬 DB) |
| Plan | 정상 (로컬 DB) |
| Coach | 제한 — 새 AI 응답 불가, 이전 대화 열람 가능 |
| Data/sync | 제한 — 동기화 실행 불가, 설정 변경 가능 |

### 8.3 모바일 하단 탭 5개 초과 방지

탭 바는 5개 고정 (Today / Story / Library / Plan / Coach).  
Data는 진입하는 방법:
- 모바일: Today 또는 Library 헤더의 ⚙ 아이콘
- 데스크탑: 헤더 우측 설정 아이콘

---

## 9. URL 마이그레이션 전략 (v1 → v2)

### 9.1 단계

1. **v2 독립 구동**: `/v2/*` prefix로 신 IA 전체 구동 (베타 토글)
2. **v1 병행 유지**: `/v1/*` 또는 prefix 없이 구 URL 유지
3. **리다이렉트 활성화**: 충분한 v2 안정화 후 구 URL 301 리다이렉트
4. **v1 제거**: 전 영역 완성 후 v1 라우트 제거

### 9.2 베타 토글

`/data/settings`에서 "새 UI (v2) 사용" 토글.  
토글 ON → 모든 내부 링크가 `/v2/*` 경로로 전환.  
토글 OFF → v1 경로 복귀 (구 Flask 서버사이드 렌더링).

---

## 작성 이력

- v0.1 (2026-06-09): 초안 — 5+1 영역 라우트 트리, URL 스키마, 네비게이션 구조, 영역 간 이동 패턴, 마이그레이션 전략
