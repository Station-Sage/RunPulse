# Phase 7 UI Renewal — 컴포넌트 카탈로그

**문서 상태**: Draft v0.2  
**작성일**: 2026-06-10  
**전제 문서**: `01-design-principles.md`, `03-screen-catalog.md`  
**후속 문서**: `05-tech-architecture.md`

---

## 이 문서의 목적

7개 핵심 컴포넌트의 props 인터페이스, 상태, 디자인 토큰, 인터랙션 패턴을 정의한다.  
SvelteKit 컴포넌트로 구현한다고 가정하고 타입 명세를 작성한다.  
시각 디자인 수치(px, rem)는 `05-tech-architecture.md`에서 디자인 토큰으로 확정한다.

**컴포넌트 목록**

| # | 이름 | 역할 | 관련 원칙 |
|---|------|------|-----------|
| C1 | `<EvidenceQuote>` | AI 결론 근거 칩 — 클릭 시 원천 데이터 패널 열기 | P1 |
| C2 | `<MetricCell>` | 단일 메트릭 + Provider 배지 + 추세 | P2, P3 |
| C3 | `<MetricBreakdown>` | 메트릭 계산 트리 분해 패널 | P2, P3 |
| C4 | `<ProviderComparison>` | 동일 메트릭 × 복수 Provider 비교 테이블 | P3 |
| C5 | `<QuickInput>` | RPE·통증·메모 빠른 입력 (≤3탭) | P6 |
| C6 | `<RecommendationCard>` | AI 권고 카드 + 근거 칩 집합 | P1, P5 |
| C7 | `<TimelineNarrative>` | 기간 내러티브 (텍스트 + 인라인 차트 + 근거) | P1, P2, P5 |

---

## C1. EvidenceQuote

### 역할

AI가 생성한 결론(브리핑·추천·내러티브) 안에 인라인으로 삽입되는 근거 칩.  
탭/클릭 시 해당 원천 데이터를 우측 패널 또는 슬라이드업 시트로 표시한다.  
근거 없는 AI 결론은 표시하지 않는다 (P1 핵심 강제).

### Props

```typescript
interface EvidenceQuoteProps {
  // 근거 유형
  type: 'metric' | 'activity' | 'wellness' | 'user_input'

  // 표시 레이블 (없으면 자동 생성)
  label?: string

  // 메트릭 근거
  metric?: {
    slug: string          // e.g. "hrv", "ctl", "tsb"
    value: number | string
    unit?: string
    date?: string         // ISO 날짜 또는 범위 "2026-06-01~06-07"
    provider?: ProviderKey
  }

  // 활동 근거
  activity?: {
    id: number
    field: string         // e.g. "avg_pace", "hr_avg"
    value: number | string
    unit?: string
  }

  // 사용자 입력 근거 (RPE, 통증 등)
  user_input?: {
    field: string         // e.g. "fatigue", "pain"
    value: number | string
    date: string
  }

  // 데이터 없음 처리
  unavailable?: boolean   // true면 "(데이터 수집 중)" 레이블로 표시
}

type ProviderKey =
  | 'garmin' | 'strava' | 'intervals' | 'runalyze'
  | 'runpulse'            // 버전 미분류 RunPulse 메트릭 (하위 호환)
  | `runpulse:${string}`  // 버전 명시 RunPulse 메트릭 (e.g. 'runpulse:formula_v1', 'runpulse:ml_v1')
// 화면 표시: 'runpulse:formula_v1' → "[RunPulse · formula_v1]" 배지
```

### 상태

| 상태 | 표시 | 동작 |
|------|------|------|
| `loaded` | `[HRV 58ms ↓]` 칩 | 탭 → 패널 열기 |
| `unavailable` | `[데이터 수집 중]` 비활성 칩 | 탭 불가 |
| `loading` | `[···]` 스켈레톤 칩 | 탭 불가 |

### 디자인 토큰

```
--eq-bg-default:   var(--surface-2)      /* 비활성 배경 */
--eq-bg-hover:     var(--surface-3)
--eq-border:       var(--border-subtle)
--eq-text:         var(--text-secondary)
--eq-icon-metric:  📊  (또는 SVG 아이콘)
--eq-icon-activity: 🏃
--eq-icon-unavail: ⋯

/* 칩 형태 */
--eq-radius:   var(--radius-pill)
--eq-px:       var(--space-2)
--eq-py:       var(--space-1)
--eq-font:     var(--font-mono-sm)    /* JetBrains Mono */
```

### 인터랙션

```
칩 탭/클릭
  → dispatch('open', { type, ...payload })
  → 부모(Today/Story/Coach)가 우측 패널 or 시트 열기 처리

키보드: Enter / Space → 동일
```

### 사용 예 (Svelte)

```svelte
<!-- Today AI 브리핑 내 인라인 사용 -->
TSB가 낮습니다.
<EvidenceQuote
  type="metric"
  metric={{ slug: "tsb", value: -4, date: "2026-06-10", provider: "runpulse" }}
/>
오늘 E2 달리기를 권장합니다.
```

---

## C2. MetricCell

### 역할

단일 메트릭을 카드 형태로 표시. Provider 배지를 항상 포함하고,  
짧은 스파크라인 추세를 선택적으로 표시한다.  
탭 시 `<MetricBreakdown>` 패널을 연다 (P2 L1 → L2 진입).

### Props

```typescript
interface MetricCellProps {
  slug: string              // 메트릭 식별자 e.g. "ctl", "hrv", "pace_avg"
  label: string             // 표시명 e.g. "CTL"
  value: number | string    // 현재값
  unit?: string             // 단위 e.g. "bpm", "ms", "/km"
  provider: ProviderKey     // 데이터 출처 (필수)

  // 시맨틱 상태 (5단계)
  status?: 'excellent' | 'good' | 'neutral' | 'caution' | 'poor'

  // 추세 (스파크라인)
  trend?: {
    direction: 'up' | 'down' | 'flat'
    data: number[]          // 최근 N개 값 (스파크라인용)
    change?: string         // e.g. "+4" "+8%" 표시 레이블
  }

  // 크기 변형
  size?: 'sm' | 'md' | 'lg'   // 기본: 'md'

  // 드릴다운 가능 여부 (기본 true)
  drillable?: boolean

  // 데이터 없음
  unavailable?: boolean
}
```

### 상태

| 상태 | 표시 |
|------|------|
| `loaded` | 값 + Provider 배지 + 추세 화살표 |
| `unavailable` | "—" + Provider 배지 (회색) |
| `loading` | 스켈레톤 박스 |
| `hover` | 배경 `--surface-2` 전환, 커서 pointer |
| `active` (드릴다운 열림) | 좌측 강조 border `--color-primary` |

### 시맨틱 색상 토큰 (P5 Quiet Data)

```
status → 색상 (텍스트 + 인디케이터 도트)
excellent → --color-semantic-green
good      → --color-semantic-teal
neutral   → --color-semantic-neutral (기본 텍스트색)
caution   → --color-semantic-amber
poor      → --color-semantic-red

provider → 배지 배경색
garmin    → --color-provider-garmin   (진한 파랑)
strava    → --color-provider-strava   (오렌지)
intervals → --color-provider-intervals (보라)
runalyze  → --color-provider-runalyze  (초록)
runpulse  → --color-provider-runpulse  (회색)
```

### 레이아웃 (md 기준)

```
┌──────────────────────┐
│  label          [Prv]│  ← label(font-sm) + provider badge
│  value  unit         │  ← 값(font-xl-bold) + 단위(font-sm)
│  ● status  ↑ +4      │  ← 상태 도트 + 추세 레이블
│  ▁▂▃▄▅▅▄▃▃▄  (7pts) │  ← 스파크라인 (trend.data 있을 때만)
└──────────────────────┘

*배지 표시 규칙*: `provider='runpulse:formula_v1'` → `[RunPulse · formula_v1]`,  
`provider='runpulse:ml_v1'` → `[RunPulse · ml_v1]`. `:` 앞은 소스명, 뒤는 버전 배지.  
신뢰도(`confidence`)가 있으면 `[RunPulse · formula_v1 · conf 0.82]` 형태로 병기.
```

### 인터랙션

```
탭/클릭 (drillable=true)
  → dispatch('drill', { slug, provider })
  → 부모가 <MetricBreakdown> 패널 마운트

키보드: Enter / Space
```

---

## C3. MetricBreakdown

### 역할

메트릭의 계산 트리를 최대 3단계로 분해해 표시하는 패널 컴포넌트.  
데스크탑: 우측 슬라이드인 패널 / 모바일: 풀스크린 슬라이드업 시트.  
P2 L2 수준. L3(원본 데이터)는 Library 링크로 연결한다.

### Props

```typescript
interface MetricBreakdownProps {
  slug: string              // 분해할 메트릭
  provider: ProviderKey     // 기준 Provider

  // 표시 모드
  mode?: 'panel' | 'sheet'  // panel=우측, sheet=모바일 슬라이드업
                            // 기본: 화면 너비에 따라 자동

  // 초기 펼침 깊이
  initialDepth?: 1 | 2 | 3  // 기본: 2
}
```

### 데이터 모델 (API 응답 기준)

```typescript
interface MetricBreakdownData {
  slug: string
  label: string
  value: number | string
  unit?: string
  provider: ProviderKey
  formula?: string          // 계산식 설명 e.g. "42일 지수이동평균(TSS)"

  // RunPulse 합성 메트릭 전용 (provider = 'runpulse:*' 형태일 때)
  computedAt?: string       // ISO 날짜시간 e.g. "2026-06-09T14:30:00"
  version?: string          // 공식 버전 e.g. "formula_v1"
  prevValue?: number        // 직전 계산값 (diff 표시용)
  confidence?: number       // 신뢰도 0~1

  children?: MetricBreakdownNode[]
}

interface MetricBreakdownNode {
  slug: string
  label: string
  value: number | string
  unit?: string
  provider: ProviderKey
  weight?: string           // 가중치 e.g. "40%"
  collapsible: boolean
  children?: MetricBreakdownNode[]
}
```

### 상태

| 상태 | 표시 |
|------|------|
| `loading` | 스켈레톤 트리 (2레벨) |
| `loaded` | 트리 렌더링 |
| `error` | "계산 데이터를 불러올 수 없습니다" + 재시도 |
| `leaf` (자식 없음) | 펼침 아이콘 없음 |

### 레이아웃

```
┌────────────────────────────────────┐
│  ← [메트릭명]              [×닫기] │
├────────────────────────────────────┤
│  현재값: 68  ● 상태      [Prv배지] │
│  formula 설명                      │
│  (RunPulse 메트릭 — provider='runpulse:*'일 때만)       │
│  재계산: 2026-06-09 14:30 · formula_v1 · conf 0.82  │
│  이전값: 66 → 68  (+2, +3%)        │  ← prevValue 있을 때
│  ──────────────────────────────    │
│  ▾ 하위 메트릭 A   0.84  [Prv]  40%│ ← L2, 탭으로 펼침
│    ▾ 하위 B        0.91  [Prv]    │  ← L3 (raw), 펼침 불가
│    ── raw 데이터: API 값 표시      │
│  ▾ 하위 메트릭 C   71    [Prv]  30%│
│  ▸ 하위 메트릭 D (접힘)            │
│  ──────────────────────────────    │
│  [Library에서 전체 추세 →]         │  ← L3 진입점
└────────────────────────────────────┘
```

### 인터랙션

```
노드 탭 (collapsible=true) → 펼침/접힘 토글
[Library 링크] → /library/metrics/:slug (Router.push)
[×닫기] → dispatch('close')
```

---

## C4. ProviderComparison

### 역할

동일 메트릭(들)을 복수의 Provider에서 가져와 가로로 비교하는 테이블.  
불일치가 허용 임계값을 초과하면 경고 배지를 표시한다.  
사용자가 메트릭별 우선 Provider를 설정할 수 있다.

### Props

```typescript
interface ProviderComparisonProps {
  // 비교할 메트릭 목록
  metrics: string[]         // slug 배열

  // 비교할 Provider (없으면 연결된 전체)
  providers?: ProviderKey[]

  // 기준 활동 (활동별 비교 시)
  activityId?: number

  // 기준 기간 (기간별 집계 비교 시)
  period?: { from: string; to: string }

  // 불일치 임계값 (기본 5%)
  discrepancyThreshold?: number

  // 우선 Provider 설정 UI 표시 여부
  showPreferenceSetter?: boolean   // 기본: false

  // is_primary 근거 배지 표시 여부 (P3 투명성 — "왜 이 Provider가 대표값인가")
  showPrimaryReason?: boolean      // 기본: false
}
```

### 데이터 모델

```typescript
interface ComparisonRow {
  slug: string
  label: string
  unit?: string
  values: Record<ProviderKey, ComparisonCell>
  discrepancy?: {
    detected: boolean
    maxDiff: number       // 절대값
    maxDiffPct: number    // 퍼센트
    severity: 'info' | 'warning'
  }
  preferredProvider?: ProviderKey

  // is_primary 근거 — dedup.py / v_canonical_activities 정적 순서에서 도출 (P3 투명성)
  // 동적 coverage 기반이 아님. 실제 DB 로직(dedup.py)과 동일 근거를 써야 한다.
  primaryReason?: {
    provider: ProviderKey
    rule: string          // e.g. "소스 우선순위 1순위 (garmin > intervals > strava > runalyze)"
                          //   or "RunPulse — 자체 산출 (always primary)"
    ruleType: 'static_priority' | 'runpulse_always'
  }
}

interface ComparisonCell {
  value: number | string | null
  available: boolean
}
```

### 상태

| 상태 | 표시 |
|------|------|
| `loaded` | 비교 테이블 |
| `loading` | 스켈레톤 테이블 |
| `single_provider` | "비교할 추가 소스가 없습니다" |
| `discrepancy` | 해당 행 배경 `--color-semantic-amber/10` + `⚠` 배지 |

### 레이아웃

```
메트릭           Garmin   Strava   Intervals  RunPulse  대표값
──────────────────────────────────────────────────────────────
HR avg           138bpm   137bpm      —          —       ★Garmin
거리             10.24km  10.19km  10.24km       —       ★Garmin  ⚠ 50m 차
TSS              —        —        52            51      ★Intervals
VO2Max           51.2     —        —            51.1     ★Garmin

★ 표시 = is_primary Provider (showPrimaryReason=true 시)
  마우스 오버 / 탭 → 툴팁: "Garmin — 소스 우선순위 1순위 (dedup.py 정적 순서)"
⚠ Garmin ↔ Strava 거리 50m 차이 (0.5%)

*컬럼(세로축) 렌더링*: 위 예시는 4-provider 고정이 아님.
`providers` prop이 없으면 해당 시맨틱 그룹에 실제 데이터가 있는 provider 집합으로 동적 렌더링.
빈 컬럼은 자동 제외. 신규 provider(Apple Health, COROS 등) 추가 시 코드 수정 불필요.
```

### 인터랙션

```
우선 Provider 드롭다운 (showPreferenceSetter=true)
  → dispatch('prefer', { slug, provider })
  → 부모가 설정 저장 처리

행 탭 → dispatch('drill', { slug }) → MetricBreakdown 열기
```

---

## C5. QuickInput

### 역할

오늘의 컨디션(피로도·통증·메모)을 최대 3탭으로 입력한다.  
Today 화면 최상단에 항상 표시. 입력 완료 시 `user_inputs` 테이블에 저장.  
키보드 단축키(R, P, N) 지원 (P6).

### Props

```typescript
interface QuickInputProps {
  // 오늘 이미 입력된 값 (있으면 수정 모드)
  existing?: {
    fatigue?: number      // 1~10
    pain?: PainLevel
    note?: string
    timestamp?: string
  }

  // 표시 모드
  compact?: boolean       // true: 한 줄 요약 + 펼침 버튼 (기본: false)

  // 저장 중 상태 외부 제어 (선택)
  saving?: boolean
}

type PainLevel = 'none' | 'mild' | 'moderate' | 'severe'
```

### 상태

| 상태 | 표시 |
|------|------|
| `empty` | 전체 입력 폼 표시 |
| `partial` | 일부 입력됨, 나머지 강조 |
| `complete` | "오늘 체크인 완료 ✓" 요약 + [수정] 버튼 |
| `saving` | [저장] 버튼 스피너 |
| `compact+empty` | "오늘 컨디션 입력 →" 한 줄 CTA |
| `compact+complete` | "피로 6 · 통증 없음 ✓" 한 줄 요약 |

### 레이아웃 (기본 모드)

```
┌─────────────────────────────────────────────────────┐
│  어떻게 느껴지나요?                        (R) (P) (N)│
│                                                      │
│  피로도  [1][2][3][4][5][ 6 ][7][8][9][10]          │
│  통증    [없음][경미][중간][심함]                     │
│  메모    [자유 입력...                    ]           │
│                                                      │
│                                        [저장]        │
└─────────────────────────────────────────────────────┘
```

### 인터랙션

```
피로도 버튼 탭 → 해당 값 선택 (단일 선택)
통증 버튼 탭   → 해당 값 선택 (단일 선택)

키보드 단축키 (포커스 독립):
  R → 피로도 필드로 포커스
  P → 통증 필드로 포커스
  N → 메모 필드로 포커스

[저장] 탭 → dispatch('save', { fatigue, pain, note })
  → 부모가 API 호출 처리
  → 완료 후 compact+complete 상태로 전환
```

### 접근성

```
피로도 버튼 그룹: role="radiogroup" aria-label="피로도 (1~10)"
통증 버튼 그룹:   role="radiogroup" aria-label="통증 수준"
각 버튼: aria-pressed, aria-label="피로도 N"
```

---

## C6. RecommendationCard

### 역할

AI가 생성한 권고를 구조화해 표시한다.  
권고 텍스트 + 근거 칩 집합 + 액션 버튼으로 구성된다.  
근거 칩이 없는 권고는 렌더링하지 않는다 (P1 강제).

### Props

```typescript
interface RecommendationCardProps {
  // 권고 내용
  recommendation: {
    title?: string          // 한 줄 요약 (선택)
    body: string            // 본문 (마크다운 지원)
    evidence: EvidenceQuoteProps[]  // 최소 1개 필수
  }

  // 액션 버튼 (최대 2개)
  actions?: {
    label: string
    href?: string           // 내부 라우트
    variant: 'primary' | 'ghost'
    onClick?: () => void
  }[]

  // 카드 변형
  variant?: 'default' | 'warning' | 'positive'

  // 로딩 상태 (AI 응답 대기)
  loading?: boolean

  // 접을 수 있는지
  collapsible?: boolean     // 기본: false
  initialCollapsed?: boolean
}
```

### 상태

| 상태 | 표시 |
|------|------|
| `loading` | 텍스트 스켈레톤 3줄 + 칩 스켈레톤 2개 |
| `loaded` | 본문 + EvidenceQuote 칩들 + 액션 버튼 |
| `warning` | 배경 `--color-semantic-amber/5` + 왼쪽 `--color-semantic-amber` border |
| `positive` | 배경 `--color-semantic-green/5` + 왼쪽 `--color-semantic-green` border |
| `error` | "AI 브리핑을 불러올 수 없습니다" + [재시도] |
| `collapsed` | 제목 한 줄 + [펼치기 ▾] |

### 레이아웃

```
┌──────────────────────────────────────────────────┐
│  [title — 선택]                                  │
│                                                  │
│  body 텍스트. 오늘은 E2 달리기 50분을 권장합니다. │
│  <EvidenceQuote/> <EvidenceQuote/> <EvidenceQuote/>│
│                                                  │
│  [Coach에게 더 묻기 →]         [실행하기 →]      │
└──────────────────────────────────────────────────┘
```

### 인터랙션

```
EvidenceQuote 칩 → C1 인터랙션 위임
액션 버튼 → href or onClick 처리
[접기/펼치기] (collapsible=true) → 높이 애니메이션 토글
```

---

## C7. TimelineNarrative

### 역할

Story 영역에서 특정 기간의 훈련 내러티브를 표시한다.  
AI 생성 텍스트 안에 `<EvidenceQuote>` 칩과 인라인 미니 차트가 포함된다.  
마크다운 서브셋 + 특수 태그(`[chart:slug]`)를 파싱해 렌더링한다.

### Props

```typescript
interface TimelineNarrativeProps {
  period: {
    year: number
    month: number           // 1~12
  }

  // 서버에서 내려주는 구조화된 내러티브
  narrative?: NarrativeContent

  loading?: boolean
}

interface NarrativeContent {
  summary: string           // 한 줄 요약
  body: NarrativeSegment[]  // 본문 세그먼트 배열
  highlights: {             // 이번 기간 수치
    totalDistance: number
    activityCount: number
    longestRun: number
    bestPace?: string
    peakCTL?: number
  }
  milestones: Milestone[]
}

type NarrativeSegment =
  | { type: 'text'; content: string }
  | { type: 'evidence'; props: EvidenceQuoteProps }
  | { type: 'chart'; slug: string; period: string; label?: string }

interface Milestone {
  date: string
  label: string
  activityId?: number
  type: 'distance_milestone' | 'pace_pb' | 'ctl_peak' | 'metric_recompute' | 'custom'
  // metric_recompute: RunPulse 공식 버전 갱신 후 재계산된 이벤트
}
```

### 상태

| 상태 | 표시 |
|------|------|
| `loading` | 텍스트 스켈레톤 5줄 + 수치 카드 스켈레톤 |
| `loaded` | 내러티브 전체 렌더링 |
| `no_data` | "이 기간에는 아직 데이터가 없습니다" |
| `partial` | 데이터 있지만 분석 미완료 → "분석 중..." 배너 + 부분 렌더 |

### 인라인 차트 (`[chart:slug]` 세그먼트)

```
┌──────────────────────────────────────┐
│  label (e.g. "CTL/ATL 추세 6월")    │
│  [스파크라인 미니 차트]               │
│  → 탭 시 우측 패널: MetricBreakdown  │
└──────────────────────────────────────┘
```

인라인 차트는 완전한 차트 라이브러리가 아니라  
SVG 스파크라인으로 구현한다 (chart.js 불필요).

### 레이아웃

```
┌──────────────────────────────────────────────────────────────┐
│  summary 한 줄                                               │
│  ────────────────────────────────────────────────────────    │
│  본문 텍스트... <EvidenceQuote/> 텍스트 계속...               │
│  <EvidenceQuote/> 또 다른 근거...                            │
│                                                              │
│  [인라인 미니 차트: CTL 추세]  → 패널                         │
│                                                              │
│  본문 텍스트 계속...                                          │
│  ────────────────────────────────────────────────────────    │
│  이번 달 수치                                                │
│  총 142km  18회  22km  5:42/km                               │
│  ────────────────────────────────────────────────────────    │
│  마일스톤                                                    │
│  🎯 6/3  누적 500km  /  🏃 6/8  하프 PB 1:52:04  →         │
└──────────────────────────────────────────────────────────────┘
```

---

## 컴포넌트 의존 관계

```
RecommendationCard
  └── EvidenceQuote (1..N)

TimelineNarrative
  ├── EvidenceQuote (인라인)
  └── InlineSparkline (내부 전용)

MetricCell
  └── (드릴다운 이벤트) → 부모가 MetricBreakdown 마운트

MetricBreakdown
  └── MetricCell (하위 노드, 재귀)

ProviderComparison
  └── (드릴다운 이벤트) → 부모가 MetricBreakdown 마운트

QuickInput (독립)
```

---

## 공유 디자인 토큰 (전체 컴포넌트)

### 색상 (P5 Quiet Data — 시맨틱만 허용)

```css
/* 시맨틱 5단계 */
--color-semantic-green:   #22c55e;
--color-semantic-teal:    #14b8a6;
--color-semantic-neutral: inherit;      /* 기본 텍스트 색 */
--color-semantic-amber:   #f59e0b;
--color-semantic-red:     #ef4444;

/* Provider 4종 */
--color-provider-garmin:    #0056b3;
--color-provider-strava:    #fc4c02;
--color-provider-intervals: #7c3aed;
--color-provider-runalyze:  #16a34a;
--color-provider-runpulse:  #6b7280;  /* RunPulse 합성 메트릭 */

/* 서피스 */
--surface-1:  색조 배경 (앱 배경)
--surface-2:  카드 배경
--surface-3:  호버·활성 배경
--border-subtle: 구분선

/* 텍스트 */
--text-primary:   주 콘텐츠
--text-secondary: 부 레이블
--text-muted:     비활성
```

### 타이포그래피

```css
/* Inter Variable */
--font-display:    Inter, sans-serif; font-weight: 700; /* 수치 강조 */
--font-body:       Inter, sans-serif; font-weight: 400; /* 본문 */
--font-label:      Inter, sans-serif; font-weight: 500; /* 레이블 */

/* JetBrains Mono */
--font-mono:       'JetBrains Mono', monospace; /* 수치, EvidenceQuote */
--font-mono-sm:    --font-mono; font-size: var(--text-sm);

/* 크기 스케일 */
--text-xs:   0.75rem
--text-sm:   0.875rem
--text-base: 1rem
--text-lg:   1.125rem
--text-xl:   1.25rem
--text-2xl:  1.5rem
```

### 간격·반경

```css
--space-1: 4px
--space-2: 8px
--space-3: 12px
--space-4: 16px
--space-6: 24px
--space-8: 32px

--radius-sm:   4px
--radius-md:   8px
--radius-lg:   12px
--radius-pill: 999px   /* EvidenceQuote 칩 */
```

---

## 접근성 공통 원칙

- 모든 인터랙티브 요소: `role`, `aria-label` 명시
- 색상만으로 상태 구별 금지 → 아이콘 또는 텍스트 병행
- 키보드 포커스: `outline: 2px solid var(--color-primary); outline-offset: 2px`
- 모바일 최소 터치 타깃: 44×44px (P6 One Finger Reach)

---

## 작성 이력

- v0.2 (2026-06-10): REVIEW-02 반영 — AO-1: ProviderKey `runpulse:${string}` 확장·MetricBreakdownData computedAt/version/prevValue/confidence·MetricCell RunPulse 버전 배지·Milestone metric_recompute 타입 추가; AO-2: ProviderComparison 컬럼 동적 렌더링 명시; AO-3: primaryReason ruleType `static_priority|runpulse_always` 정정(coverage/manual 제거)·툴팁 텍스트 dedup.py 정적 순서로 수정
- v0.1 (2026-06-10): 초안 — 7개 컴포넌트 props 인터페이스, 상태, 디자인 토큰, 인터랙션 패턴
