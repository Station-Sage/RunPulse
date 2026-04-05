

이 문서를 깊이 읽겠습니다. 시간을 들여서 생각해보겠습니다.

---

Phase 7(preview)의 목차와 Section 0-1의 본문을 함께 보면, 이전까지 제가 제안한 에이전트 구조에 근본적으로 재고해야 할 부분이 있습니다.

## 이전 제안의 문제점

이전 제안은 **"지금 하고 있는 일을 더 효율적으로 하는 방법"**에 머물러 있었습니다. Phase 1-4 문서 업데이트에서 겪은 고통을 줄이는 데 집중했습니다. 하지만 phase-7(preview)가 보여주는 것은, RunPulse가 앞으로 나아가야 할 방향이 데이터 파이프라인 정비가 아니라 **네 개 축의 동시 진화**라는 점입니다.

특히 간과한 것이 두 가지입니다.

첫째, **훈련 프로그램 생성(Part A)과 AI 코칭(Part B)이 Phase 5-6에서 바로 시작**된다는 것입니다. 이것은 "향후 ML 단계에서 추가"가 아니라 지금 당장의 설계·구현 대상입니다. Part A의 Athlete Profiling System, Plan-Athlete Fit Scoring, Adaptive Plan Execution은 32개 메트릭 위에 올라가는 완전히 새로운 도메인 로직입니다. Part B의 Persistent Athlete Context와 대화 스펙트럼은 LLM 프롬프트 엔지니어링 + 메트릭 해석 규칙 + 대화 UX가 결합된 고유한 영역입니다.

둘째, **Axis 2(Insight Depth)의 러닝폼 분석, 환경 영향 분석, 레이스 시뮬레이션**은 기존 32개 calculator와는 전혀 다른 수준의 분석입니다. 스트림 데이터(초단위 심박, 케이던스, GCT, 파워)를 시계열로 처리하고, 날씨·고도·노면 데이터와 교차 분석하고, 시뮬레이션 모델을 돌립니다. 이것은 metric calculator 패턴으로는 담을 수 없는 새로운 계산 아키텍처가 필요합니다.

이 두 가지를 반영하면, 에이전트 구조는 "Phase 1-4의 작업 효율화 도구"가 아니라 **"RunPulse의 네 축 진화를 지탱하는 개발 인프라"**로 설계되어야 합니다.

## 네 축이 에이전트에 요구하는 것

각 축별로 어떤 종류의 작업이 발생하는지 분석합니다.

**Axis 1 — Intelligence (AI/ML)**

Phase 5-6에서 바로 시작되는 것과, 이후 ML 단계에서 시작되는 것을 구분해야 합니다.

Phase 5-6 (즉시): 훈련 프로그램 생성 엔진은 규칙 기반입니다. Athlete Profile → 목표 매칭 → 주간 템플릿 생성 → 일별 세션 배치. 이것은 ML이 아니라 도메인 규칙 + 최적화 로직입니다. AI 코치는 LLM + 메트릭 컨텍스트 주입입니다. Persistent Athlete Context를 구축하고, 대화마다 적절한 메트릭을 선택해서 프롬프트에 넣는 시스템입니다.

이후 (ML 단계): 개인화 가중치 학습, 부상 예측 모델, 레이스 시간 예측 모델, AB 테스트 프레임워크.

**Axis 2 — Insight Depth**

러닝폼 분석: activity_streams 데이터(GCT, vertical oscillation, stride length 시계열) → 구간별 폼 붕괴 감지 → 시각화. 환경 영향: weather_cache + 고도 프로필 + FEARP → 환경 보정 성능 추세. Training Balance Radar: 5개 이상 축(유산소, 무산소 역치, 속도, 지구력, 회복)의 밸런스 시각화. 레이스 시뮬레이션: 코스 프로필 + 현재 체력 + 페이싱 전략 → 예상 시간 + 구간별 페이스 권장.

이것들은 데이터 파이프라인 → 분석 엔진 → UI 시각화를 관통하는 풀스택 feature들입니다.

**Axis 3 — Data Expansion**

멀티스포츠 지원: 수영(SWOLF, stroke rate), 사이클(power, NP, IF), 근력(volume load). 수동 데이터 입력: RPE, 주관적 피로도, 부상 메모. 신발 추적: gear 테이블 활용, 마일리지 기반 교체 알림.

**Axis 4 — Experience**

인터페이스 진화: 현재 웹 기반 → 모바일 최적화 → 잠재적 앱. 피드백 루프: session_outcomes 기반 코칭 품질 측정. 알림과 프로액티브 개입: "내일 인터벌 예정인데 CIRS가 65점이야, 조정할까?"

## 재설계: 도메인 인식 에이전트 아키텍처

이전 제안에서 "역할(기능)은 에이전트로, 도메인(지식)은 스킬로"라고 했는데, 이것을 수정합니다. Axis 1의 AI 코칭 설계와 Axis 2의 레이스 시뮬레이션 설계는 단순히 architect에 스킬을 주입하는 것으로 해결되지 않습니다. 이 도메인들은 각각 고유한 사고 체계, 참조 자료, 검증 기준을 가지고 있어서, **깊이 있는 설계를 하려면 전문 에이전트가 필요**합니다.

하지만 동시에, 에이전트를 도메인별로 쪼개면 10개 이상이 되어 관리가 불가능해집니다. 균형점을 찾아야 합니다.

핵심 통찰은 이것입니다: RunPulse의 네 축은 **두 개의 본질적으로 다른 사고 모드**를 요구합니다.

**모드 A — 시스템 설계 사고**: "이 데이터 구조가 확장 가능한가", "이 API가 일관적인가", "이 아키텍처가 Axis 3의 멀티스포츠를 수용하는가". 데이터 파이프라인, 메트릭 엔진, 동기화 시스템이 여기 속합니다. Phase 1-4가 이 모드였습니다.

**모드 B — 제품 경험 설계 사고**: "러너가 이 화면을 열었을 때 처음 3초에 무엇을 느끼는가", "AI 코치가 이 말을 했을 때 러너가 신뢰할 수 있는가", "훈련 프로그램이 오늘의 데이터에 어떻게 적응하는가". UI/UX, AI 코칭, 훈련 프로그램, 인사이트 시각화가 여기 속합니다. Phase 5-6이 이 모드입니다.

이 두 모드를 하나의 architect 에이전트에서 스킬 교체로 처리하려고 하면, Part 1의 비전문에서 말하는 "러너의 흩어진 데이터를 하나로 모아, 스스로 이해할 수 있는 언어로 번역하고"라는 경험을 설계하는 데 필요한 깊이가 나오지 않습니다. Section 0.2의 타겟 사용자 — "4개의 탭을 오가며 스스로 조립하려는 사람" — 를 위한 경험을 설계하려면, 그 사람의 하루를 시뮬레이션하고, 각 접점에서 어떤 정보가 어떤 순서로 필요한지를 추론하는 전담 사고가 필요합니다.

### 최종 에이전트 구조: 8 + 스킬

```
.claude/agents/
│
│  ── 설계 계층 (Design) ──
├── system-architect.md       # 시스템/데이터 설계자 (모드 A)
├── product-architect.md      # 제품 경험 설계자 (모드 B)
│
│  ── 검증 계층 (Verification) ──
├── design-verifier.md        # 설계 vs 코드 대조 검증
├── test-analyst.md           # 테스트 실행/분석
├── doc-sync.md               # 문서 동기화 검증
│
│  ── 리뷰 계층 (Review) ──
├── code-reviewer.md          # 코드 품질 리뷰
│
│  ── 탐색 계층 (Research) ──
├── domain-researcher.md      # 범용 도메인 리서치
│
│  ── 특수 (Phase 진입 시 활성화) ──
└── ml-architect.md           # ML 전문 설계자 (Stage 3)
```

두 architect의 분리가 이 구조의 핵심입니다.

**system-architect (시스템 설계자)**

담당 영역: 데이터 모델, 메트릭 엔진, 동기화 파이프라인, API 설계, DB 스키마, CalcContext 확장, 멀티스포츠 데이터 구조.

이 에이전트가 읽는 것: architecture.md, phase-1~4.md, metric_dictionary.md, decisions.md, db_setup.py, engine.py.

이 에이전트가 생각하는 방식: "activity_summaries에 sport_type 컬럼을 추가하면 기존 쿼리가 깨지는가", "레이스 시뮬레이션 결과를 metric_store에 저장할 때 scope_type을 뭘로 할 것인가", "Axis 3의 수동 데이터 입력을 source_payloads 패턴으로 처리할 수 있는가".

```yaml
name: system-architect
description: >
  시스템/데이터 아키텍처 설계 전문가. DB 스키마, 메트릭 엔진, 데이터 파이프라인,
  API 설계, 멀티스포츠 확장 구조를 설계한다. "스키마 설계", "데이터 모델",
  "파이프라인 설계", "API 구조", "확장성 검토" 요청 시 사용.
model: inherit
tools: Read, Grep, Glob, Bash
disallowedTools: Write, Edit
memory: project
skills:
  - system-design-conventions
  - metric-conventions
```

**product-architect (제품 경험 설계자)**

담당 영역: UI/UX 설계, AI 코칭 대화 설계, 훈련 프로그램 생성 로직, 인사이트 시각화, 사용자 플로우, 정보 계층 구조, 알림 시스템, 피드백 루프.

이 에이전트가 읽는 것: phase-7(preview).md (제품 비전), phase-5.md/phase-6.md (UI·AI 설계), metric_dictionary.md (표시할 메트릭 이해), SEMANTIC_GROUPS (그룹핑 로직), 경쟁 앱 리서치 보고서.

이 에이전트가 생각하는 방식: "Section 0.2의 타겟 사용자가 아침에 앱을 열면 첫 화면에 뭐가 보여야 하는가", "CRS 35점을 봤을 때 '왜?'를 누르면 어떤 순서로 정보가 펼쳐져야 하는가", "AI 코치가 '오늘 쉬어'라고 했을 때 Section 0.3 원칙 2(투명한 분석)를 어떻게 만족시키는가", "Part A의 Plan-Athlete Fit Scoring 결과를 사용자에게 어떤 시각적 메타포로 보여줄 것인가", "Part B의 대화에서 코치가 메트릭을 인용할 때 숫자가 아니라 의미를 전달하는 문장 패턴은 무엇인가".

```yaml
name: product-architect
description: >
  제품 경험 설계 전문가. UI/UX, AI 코칭 대화, 훈련 프로그램 UX, 인사이트 시각화,
  사용자 플로우, 정보 계층을 설계한다. "UI 설계", "코칭 대화 설계",
  "훈련 프로그램 UX", "시각화 설계", "사용자 경험" 요청 시 사용.
  Section 0.3의 세 원칙(데이터 통합, 투명한 분석, 맥락 있는 안내)을
  모든 설계 결정의 기준으로 삼는다.
model: inherit
tools: Read, Grep, Glob, Bash
disallowedTools: Write, Edit
memory: project
skills:
  - product-design-conventions
  - coaching-patterns
```

이 에이전트의 memory가 특히 중요합니다. "활동 상세 페이지에서 메트릭 표시 순서는 CRS → 핵심 원인 메트릭 → 소스 비교 순으로 하기로 했다", "AI 코치의 톤은 친구 같은 전문가로 하기로 했다", "숫자를 먼저 말하지 않고 의미를 먼저 말하기로 했다" 같은 제품 결정들이 세션을 넘어 축적됩니다.

**왜 이 분리가 필수적인가: Part A를 예로 들면**

Part A의 훈련 프로그램 생성 엔진은 두 설계자의 협업이 필요합니다.

system-architect는 이렇게 생각합니다: Athlete Profile을 어떤 테이블에 저장하는가, Plan 템플릿의 데이터 구조는 무엇인가, Adaptive Plan Execution이 매일 CalcContext에서 어떤 메트릭을 읽어서 계획을 수정하는가, 수정 이력을 어떻게 저장하는가.

product-architect는 이렇게 생각합니다: 사용자가 목표를 입력할 때의 온보딩 플로우는 어떠한가, 3개의 프로그램 후보를 비교하는 Plan Comparison View에서 어떤 차원을 보여줘야 사용자가 판단할 수 있는가, Adaptive Execution이 오늘의 세션을 변경했을 때 "왜 바꿨는지"를 어떻게 설명하는가, Post-Program Review에서 12주간의 여정을 어떤 시각적 서사로 보여주는가.

하나의 architect 에이전트가 이 두 사고 모드를 동시에 하면, 한쪽이 얕아집니다. 이것이 이전 제안의 한계였습니다.

### 스킬 구조 확장

```
.claude/skills/
│
│  ── 공통 ──
├── system-design-conventions/     # 시스템 설계 규칙
│   ├── SKILL.md
│   ├── phase-template.md
│   └── data-model-checklist.md
├── product-design-conventions/    # 제품 설계 규칙
│   ├── SKILL.md
│   ├── ux-principles.md           # Section 0.3 세 원칙 구현 가이드
│   ├── metric-display-rules.md    # 메트릭 유형별 UI 표시 규칙
│   └── sport-adaptation.md        # 스포츠별 UI 적응 규칙
├── metric-conventions/            # 메트릭 추가/수정 규칙
├── design-audit/                  # 설계-구현 대조 체크리스트
├── pre-commit/                    # 커밋 전 체크리스트
│
│  ── Phase 5-6 전용 ──
├── coaching-patterns/             # AI 코칭 대화 패턴
│   ├── SKILL.md
│   ├── conversation-templates.md  # 상황별 대화 템플릿
│   ├── metric-narration.md        # 메트릭→자연어 변환 규칙
│   └── transparency-rules.md      # 원칙 2 준수 패턴
├── training-program-design/       # 훈련 프로그램 설계 규칙
│   ├── SKILL.md
│   ├── periodization.md           # 주기화 원칙
│   ├── adaptation-rules.md        # 적응형 실행 규칙
│   └── athlete-profiling.md       # 러너 프로파일링 기준
│
│  ── Stage 3 (ML) ──
├── ml-pipeline/                   # ML 파이프라인 규칙
└── ab-testing/                    # AB 테스트 프레임워크
```

coaching-patterns 스킬은 product-architect에 프리로드됩니다. 이 스킬이 정의하는 것의 예시:

```markdown
# metric-narration.md

## 원칙: 숫자 먼저가 아니라 의미 먼저

나쁜 예: "CRS가 35점입니다. CIRS가 62점, TSB가 -15입니다."
좋은 예: "지금 몸이 꽤 지쳐 있어요. 이번 주 훈련 강도가 높았고
회복이 따라가지 못하고 있습니다. (CRS 35점)"

## 메트릭 인용 규칙
- 1차: 자연어 해석을 먼저 제시
- 2차: 괄호 안에 메트릭명과 값
- 3차: "자세히 보기"로 계산 과정 연결 (원칙 2: 투명한 분석)

## 상황별 메트릭 선택
- "오늘 뭐 하지?": CRS → RRI → 오늘의 planned_workout
- "왜 이렇게 피곤해?": UTRS → CIRS 구성요소 → 수면/HRV 추세
- "마라톤 준비 잘 되고 있어?": Marathon Shape → VDOT 추세 → CTL 추세
```

### 워크플로우: 네 축별 에이전트 조합

**Axis 1 작업 (Intelligence — 훈련 프로그램, AI 코칭)**

```
Phase 5: 훈련 프로그램 엔진 설계

@product-architect: Part A의 사용자 여정 설계
  - 온보딩 → 프로파일링 → 프로그램 추천 → 비교 → 선택 → 실행 → 리뷰
  - 각 단계의 UI 와이어프레임 개념 + 정보 계층

@system-architect: Part A의 데이터/로직 설계
  - athlete_profiles 테이블 구조
  - plan_templates 데이터 모델
  - adaptation_engine 인터페이스 (CalcContext 연동)
  - plan_history 저장 구조

@domain-researcher (background): 
  - Runna, TrainAsOne, Athletica.ai의 적응형 계획 메커니즘 리서치

메인: 세 보고서 종합 → phase-5.md 초안 작성 → Gate 0
```

```
Phase 6: AI 코칭 시스템 설계

@product-architect (skills: coaching-patterns): Part B 대화 설계
  - Persistent Athlete Context 구조
  - 대화 시나리오별 메트릭 선택 로직
  - 코치 페르소나 정의
  - 투명성 규칙 (원칙 2) 적용 패턴

@system-architect: Part B 기술 설계
  - chat_messages 테이블 활용 구조
  - 메트릭 컨텍스트 주입 파이프라인
  - LLM 프롬프트 템플릿 아키텍처

메인: 종합 → phase-6.md → Gate 0
```

**Axis 2 작업 (Insight Depth — 분석 깊이)**

```
레이스 시뮬레이션 feature 설계

@system-architect: 시뮬레이션 엔진 데이터 설계
  - 코스 프로필 데이터 구조 (고도, 거리)
  - 시뮬레이션 입력/출력 모델
  - metric_store에 결과 저장 방식

@product-architect: 시뮬레이션 UX 설계
  - 코스 입력 인터페이스
  - 시뮬레이션 결과 시각화 (구간별 페이스 차트, 에너지 곡선)
  - "만약 10초/km 빠르게 출발하면?" 시나리오 비교 UX

@domain-researcher: 기존 레이스 예측 도구 리서치
```

**Axis 3 작업 (Data Expansion)**

```
멀티스포츠 확장 설계

@system-architect: 스포츠별 메트릭 확장 설계
  - activity_summaries 스포츠 독립적 컬럼 vs metric_store 활용
  - 수영/사이클/근력 전용 메트릭 정의
  - extractor 확장 구조

@product-architect: 스포츠별 UI 적응 설계
  - 동적 컴포넌트 시스템 (스포츠 유형 → 표시 메트릭 세트)
  - 크로스스포츠 대시보드 (주간 볼륨 통합 뷰)
```

**Axis 4 작업 (Experience)**

```
피드백 루프 + 알림 시스템 설계

@product-architect: 전체 UX 설계
  - session_outcomes 기반 코칭 품질 추적
  - 프로액티브 알림 (CIRS > 60일 때 "내일 조정할까?" 알림)
  - 알림의 투명성 (왜 이 알림이 왔는지 설명)

@system-architect: 알림 인프라 설계
  - 알림 조건 규칙 엔진
  - 알림 이력 저장
```

### 진화 로드맵 반영

```
Stage 1 (지금 — Phase 5 준비)
  에이전트: system-architect, product-architect, design-verifier, 
           test-analyst, doc-sync, code-reviewer, domain-researcher
  스킬: system-design-conventions, product-design-conventions,
       metric-conventions, design-audit, pre-commit
  총: 7 에이전트 + 5 스킬

Stage 2 (Phase 5-6 진행 중)
  스킬 추가: coaching-patterns, training-program-design
  (에이전트 추가 없음 — product-architect가 스킬로 전문화)
  총: 7 에이전트 + 7 스킬

Stage 3 (ML 단계)
  에이전트 추가: ml-architect
  스킬 추가: ml-pipeline, ab-testing
  총: 8 에이전트 + 9 스킬
```

### 이전 제안과의 차이점 요약

이전에는 architect 하나 + 스킬 교체로 모든 설계를 커버하려 했습니다. 이번에는 system-architect와 product-architect로 분리하되, 도메인 전문성은 여전히 스킬로 주입합니다. 이것이 "에이전트 수 폭발"과 "하나로 다 하려는 얕은 설계" 사이의 균형점입니다.

핵심 변경:
- architect → system-architect + product-architect 분리
- ui-conventions 스킬 → product-design-conventions + coaching-patterns + training-program-design으로 확장
- Stage 2에서 에이전트 추가가 아니라 스킬 추가로 전문화
- 네 축별 워크플로우 패턴 정의

---

이 구조로 진행할까요? 동의하시면 Stage 1의 7개 에이전트 + 5개 스킬 + AGENT-ROADMAP.md를 작성하겠습니다.