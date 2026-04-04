# RunPulse 에이전트 로드맵

> 최종 수정: 2026-04-04
> 현재 Stage: 1

## 개요

RunPulse 개발에서 반복되는 컨텍스트 폭발과 역할 혼재 문제를 해결하기 위해,
Claude Code의 subagent + skill 시스템을 도입한다.

핵심 원칙:
- 역할(기능)은 에이전트로, 도메인(지식)은 스킬로 분리
- subagent는 정보를 수집/검증하고 요약만 반환 (Write/Edit 금지)
- 모든 코드/문서 수정은 메인 에이전트가 직접 수행
- 에이전트는 전체 파일을 읽지 않는다 — grep 레시피로 필요한 수치만 확인
- architect는 `--agent` 세션 모드로 대화형 사용 (파일 1회 로드)
- 단순 작업(doc-sync 등)은 스킬로 실행 (15K 스폰 오버헤드 제거)

## Stage 1: 현재 (Phase 5 준비)

### 에이전트 6개

| 에이전트 | 계층 | 모델 | 사용 방식 | 역할 |
|---------|------|------|----------|------|
| system-architect | 설계 | inherit | `--agent` 세션 | 시스템/데이터 아키텍처 설계 |
| product-architect | 설계 | inherit | `--agent` 세션 | 제품 경험 (UI/UX/AI코칭) 설계 |
| design-verifier | 검증 | haiku | @-mention | 설계 vs 코드 불일치 검출 |
| test-analyst | 검증 | haiku | @-mention | 테스트 실행/분석 |
| code-reviewer | 리뷰 | sonnet | @-mention (필요시) | 코드 품질/보안/패턴 리뷰 |
| domain-researcher | 탐색 | sonnet | @-mention (background) | 도메인별 리서치 |

### 스킬 6개

| 스킬 | 프리로드 대상 | 용도 |
|------|-------------|------|
| system-design-conventions | system-architect | 시스템 설계 규칙 + grep 레시피 |
| product-design-conventions | product-architect | 제품 설계 규칙 + grep 레시피 |
| metric-conventions | system-architect | 메트릭 계산기 템플릿/규칙 |
| design-audit | design-verifier | 검증 체크리스트 |
| doc-sync | (수동 /doc-sync) | 문서 정합성 검증 스크립트 실행 |
| pre-commit | (수동 /pre-commit) | 커밋 전 체크리스트 |

### 토큰 최적화 전략

에이전트 시스템 프롬프트에 "반드시 읽어라" 파일 목록을 두지 않는다.
대신 스킬에 grep 레시피(bash 명령어)를 포함하여 필요한 수치만 빠르게 확인한다.
상세 맥락이 필요할 때만 해당 파일의 특정 섹션을 Read한다.

| 방식 | 토큰 비용 | 적합한 작업 |
|------|----------|------------|
| `--agent` 세션 모드 | 첫 턴 ~20K, 이후 ~2K/턴 | 반복 대화형 설계 검토 |
| @-mention 서브에이전트 | ~15K + 작업량 | 대량 출력 격리 (pytest, 대형 diff) |
| /skill 실행 | ~1K | 단순 스크립트 실행, 체크리스트 |
| 메인에서 직접 Bash | ~0.2K | 한 줄 명령 |

### 워크플로우 패턴

패턴 A — 새 Phase/Feature 설계:
  `claude --agent system-architect` + `claude --agent product-architect` (별도 세션)
  → 메인 종합 → Gate 0

패턴 B — 구현 + 검증:
  메인 구현 → @test-analyst + @design-verifier + @code-reviewer → 메인 수정 → /pre-commit

패턴 C — 문서 업데이트:
  /doc-sync 실행 → 불일치 확인 → 메인 수정 → /doc-sync 재검증

패턴 D — 리서치:
  @domain-researcher (background) → 보고서 → 메인/architect 참조

## Stage 2: Phase 5-6 진행 중 (UI/AI 코칭)

### 추가 스킬

| 스킬 | 용도 |
|------|------|
| coaching-patterns | AI 코칭 대화 패턴, 메트릭 자연어 변환 규칙 |
| training-program-design | 훈련 프로그램 설계 (주기화, 적응형 실행) |

에이전트 추가 없음. product-architect에 스킬을 추가하여 전문화.

### 추가 워크플로우

패턴 E — 훈련 프로그램 설계:
  `claude --agent product-architect` (skills: training-program-design) — UX 설계
  `claude --agent system-architect` — 데이터/로직 설계
  @domain-researcher — 경쟁 앱 적응형 계획 리서치

패턴 F — AI 코칭 설계:
  `claude --agent product-architect` (skills: coaching-patterns) — 대화 설계
  `claude --agent system-architect` — 메트릭 컨텍스트 파이프라인 설계

## Stage 3: ML 단계

### 추가 에이전트

| 에이전트 | 역할 |
|---------|------|
| ml-architect | ML 파이프라인 설계 (feature engineering, 모델 버전 관리, AB 테스트) |

### 추가 스킬

| 스킬 | 용도 |
|------|------|
| ml-pipeline | feature engineering, 모델 버전 관리, 배포 규칙 |
| ab-testing | AB 테스트 프레임워크, 실험 설계 |

### 최종 구성

에이전트 7개 + 스킬 10개

## Part 1의 5가지 문제와 에이전트 매핑

| 문제 | 담당 에이전트 |
|------|-------------|
| 1. 소스별 다른 값 | product-architect (소스 비교 UI), system-architect (대표값 선택 로직) |
| 2. 같은 개념, 다른 이름 | system-architect (SEMANTIC_GROUPS), product-architect (그룹 표시 UI) |
| 3. 같은 메트릭, 여러 출처 | system-architect (provider+is_primary), product-architect (투명성 UI) |
| 4. 메트릭 진화 | ml-architect (버전 관리), system-architect (재계산), product-architect (버전 비교 UI) |
| 5. 종합 운동 확장 | system-architect (스포츠별 메트릭 구조), product-architect (동적 UI 시스템) |

## Gate 시스템

| Gate | 시점 | 필수 조건 |
|------|------|----------|
| Gate 0 | 새 feature/phase 시작 전 | 설계 문서 완성, 사용자 리뷰 |
| Gate 1 | 구현 완료 | pytest 전체 통과, design-verifier 0 errors |
| Gate 2 | 커밋 전 | /pre-commit 전체 PASS |
| Gate 3 | Phase 전환 | 모든 DoD 항목 통과, 사용자 최종 확인 |
