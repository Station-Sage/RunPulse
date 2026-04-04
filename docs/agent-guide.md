# RunPulse 에이전트/스킬 실전 운영 매뉴얼

> 예산: Pro $20/월 + API $11/월 한도
> 최종 수정: 2026-04-04

---

## 핵심 원칙

**평소 코딩할 때는 에이전트를 쓰지 않는다.**
메인 Claude Code 세션에서 직접 작업하는 것이 가장 효율적이다.
에이전트는 특정 상황에서만 꺼내 쓰는 도구다.
**의심되면 메인에서 직접 하라.**

---

## 도구 4가지

| 도구 | 비용 풀 | 토큰 비용 | 용도 |
|------|--------|----------|------|
| 메인 세션 (직접 작업) | Pro 5시간 | ~1K/프롬프트 | 일상 코딩 전부 |
| 스킬 (/명령어) | Pro 5시간 | ~1K | 문서 확인, 커밋 전 검증 |
| --agent 세션 모드 | Pro (넘치면 API) | 첫 턴 ~20K, 이후 ~2K | 설계 논의 (대화형) |
| @-mention 서브에이전트 | API $11 | 15K + 작업량 | 대량 출력 격리 (일회성) |

---

## 스킬: /doc-sync vs /pre-commit

| | /doc-sync | /pre-commit |
|---|---|---|
| **언제** | 코딩 중 수시로 | 커밋 직전 1회 |
| **목적** | 문서가 코드와 맞는지 빠른 확인 | 커밋해도 되는지 전체 판정 |
| **실행 시간** | ~5초 | ~35초 |
| **검사 항목** | check_docs.py, dictionary 동기화, test_doc_sync (3개) | pytest 전체 + check_docs + dictionary + 300줄 초과 + BACKLOG NOW (5개) |
| **관계** | pre-commit의 **부분집합** | doc-sync를 **포함** + 추가 검사 |
| **결과** | 문서 상태 보고 | "커밋 가능" / "커밋 불가" 판정 |

사용 흐름:

    코딩 중 → /doc-sync (문서 깨졌나 빠르게 확인, 5초)
    커밋 직전 → /pre-commit (전체 게이트, pytest 포함, 35초)

나머지 스킬 4개 (에이전트에 자동 프리로드):

| 스킬 | 프리로드 대상 | 용도 |
|------|-------------|------|
| system-design-conventions | system-architect | 시스템 설계 규칙 + grep 레시피 |
| product-design-conventions | product-architect | 제품 설계 규칙 + grep 레시피 |
| metric-conventions | system-architect | 메트릭 계산기 템플릿/규칙 |
| design-audit | design-verifier | 검증 체크리스트 |

---

## 에이전트 6개

| 에이전트 | 모델 | 사용 방식 | 호출당 비용 | 역할 |
|---------|------|----------|-----------|------|
| system-architect | inherit (Sonnet) | --agent 세션 | 첫 턴 ~20K | DB 스키마, API, 파이프라인 설계 |
| product-architect | inherit (Sonnet) | --agent 세션 | 첫 턴 ~20K | UI/UX, AI 코칭, 화면 설계 |
| design-verifier | **haiku** | @-mention | ~$0.10 | 설계문서 vs 코드 대조 |
| test-analyst | **haiku** | @-mention | ~$0.10 | pytest 실행 + 실패 분석 |
| code-reviewer | **sonnet** | @-mention (필요시) | ~$0.30 | 대형 코드 변경 리뷰 |
| domain-researcher | **sonnet** | @-mention (background) | ~$0.50 | 기술 조사, 패턴 리서치 |

---

## 실전 활용 패턴

### 패턴 1: 코딩 중 문서 확인 — /doc-sync

코드를 수정하다가 문서가 맞는지 궁금할 때:

    /doc-sync

5초면 끝난다. check_docs 결과 + dictionary 동기화 상태 + doc_sync 테스트를 요약해준다.

### 패턴 2: 커밋 직전 — /pre-commit

커밋하기 전에:

    /pre-commit

pytest 전체 + 문서 검증 + 300줄 초과 + BACKLOG 확인까지 전부 돌린다.
"커밋 가능" 판정이 나와야 커밋한다.

### 패턴 3: Phase 설계 논의 — --agent 세션 모드

Phase-5 UI 설계를 논의하고 싶을 때, VS Code 터미널에서:

    claude --agent system-architect --name "phase5-설계"

세션 안에서 여러 번 질문한다:

    > metric_store에 새 scope_type 'weekly' 추가하면 기존 Calculator에 영향이 뭐야?
    > phase-5에서 대시보드 카드 구조를 바꾸려면 어떤 테이블이 관련돼?
    > 현재 CalcContext API로 주간 트렌드 데이터를 뽑을 수 있어?

파일을 첫 질문 때 한 번 읽고 이후 대화에서 재활용한다.
나중에 이어가려면:

    claude --resume "phase5-설계"

UX/제품 관련이면 claude --agent product-architect를 사용한다.

architect 세션 결과를 메인에서 활용하는 방법:

    # architect 세션에서
    > 지금까지 논의한 phase-5 DB 설계를 마크다운으로 정리해줘
    # 출력된 내용을 복사

    # 메인 세션에서
    > 아래 설계안을 v0.3/data/phase-5-db-draft.md로 저장해줘
    (붙여넣기)

### 패턴 4: 대량 출력 격리 — @-mention 서브에이전트

pytest가 실패하고 원인을 분석하고 싶을 때:

    @"test-analyst (agent)" tests/test_metrics/ 분석해줘

대상 경로만 지정하면 에이전트가 자동으로:
1. pytest 실행
2. 실패 테스트 상세 수집
3. 실패 원인 분류 (mock/로직/의존성/환경)
4. 수정 제안 + 우선순위 생성

pytest 출력이 수만 토큰이어도 서브에이전트 안에서 소화되고,
메인에는 요약만 돌아온다.

설계 문서와 코드 비교:

    @"design-verifier (agent)" v0.3/data/phase-4.md와 src/metrics/ 비교해줘

### 패턴 5: 코드 리뷰 — 필요시만

큰 변경을 했을 때:

    @"code-reviewer (agent)" 오늘 변경한 src/web/views_dashboard*.py 리뷰해줘

에이전트가 자동으로 git diff 분석 + raw SQL 검사 + 커밋 가능 판정을 수행한다.
5줄짜리 수정에는 쓰지 마라. 15K 오버헤드가 아깝다.

### 패턴 6: 리서치 — 백그라운드

새로운 기능 구현 전 조사가 필요할 때:

    @"domain-researcher (agent)" Flask에서 SSE로 실시간 동기화 진행률 표시하는 패턴 조사해줘

background: true이므로 조사하는 동안 메인에서 다른 작업을 계속할 수 있다.
에이전트가 자동으로 기존 코드 파악 -> 외부 조사 -> RunPulse 적용 방안을 정리한다.

---

## 서브에이전트 활용 팁

서브에이전트는 "한 번 호출로 충분한 결과를 얻는" 도구다.
반복적 추적이 필요하면 메인에서 직접 하거나 --agent 세션을 열어라.

서브에이전트 결과를 받은 후 수정 -> 재확인 흐름:

    # 서브에이전트가 "CalcContext mock 누락" 보고
    # -> 메인에서 수정 후, Bash로 직접 재확인 (0.2K)
    > python3 -m pytest tests/test_metrics/test_cirs.py -v --tb=short

서브에이전트를 다시 스폰하는 것(15K)보다 메인에서 직접 확인하는 것이 훨씬 저렴하다.

호출 시 구체적으로 지시할수록 한 번에 끝난다:

    # 나쁜 예 (결과 부족할 수 있음)
    @"test-analyst (agent)" 테스트 실패 원인 분석해줘

    # 좋은 예 (한 번에 충분한 결과)
    @"test-analyst (agent)" tests/test_metrics/ 분석해줘

좋은 예에서는 에이전트의 기본 작업 절차가 자동으로 실행되어
실패 분류 + 수정 제안 + 우선순위까지 한 번에 나온다.

---

## 쓰지 않는 것이 더 나은 경우

| 작업 | 에이전트 가치 | 이유 |
|------|-------------|------|
| pytest 1000개 실행 + 요약 | **높음** | 출력이 수만 토큰, 메인 오염 방지 |
| phase-3.md(80KB) vs 코드 대조 | **높음** | 80KB를 메인에 넣지 않고 격리 |
| 반복적 설계 질의응답 | **높음** | --agent 세션으로 파일 1회 로드 |
| git diff 5줄 코드 리뷰 | **낮음** | 15K 오버헤드 >> 실제 작업량 |
| check_docs.py 결과 확인 | **낮음** | /doc-sync나 Bash 직접 실행 |
| 변수명 수정, 한 줄 버그 픽스 | **낮음** | 메인에서 직접이 50배 저렴 |

---

## 하루 워크플로우

**오전: 코딩 (메인 세션, Pro 풀)**

    > BACKLOG.md 읽어줘
    > src/web/views_dashboard.py에서 카드 정렬 로직 수정해줘

**코딩 중: 문서 확인 (메인 세션, ~5초)**

    /doc-sync

**커밋 직전: 전체 게이트 (메인 세션, ~35초)**

    /pre-commit

**필요시: 서브에이전트 (API $11 풀, 하루 1~2회)**

    @"design-verifier (agent)" phase-4.md와 src/metrics/ 비교해줘

**Phase 전환기: architect 세션 (Pro 풀)**

    claude --agent system-architect --name "phase5-설계"
    # 질문 5~6개를 몰아서 -> 세션 종료
    claude --resume "phase5-설계"  # 나중에 이어가기

---

## 월간 예산 배분

| 항목 | 모델 | 빈도 | 월 비용 | 풀 |
|------|------|------|--------|-----|
| 일상 코딩 | Sonnet | 매일 | 포함 | Pro 5시간 |
| /doc-sync, /pre-commit | — | 매일 | 포함 | Pro 5시간 |
| --agent architect 세션 | Sonnet | 월 3~4회 | 포함 (넘치면 ~$3) | Pro -> API |
| @design-verifier | **haiku** | 주 2회 | ~$1 | API $11 |
| @test-analyst | **haiku** | 주 2회 | ~$1 | API $11 |
| @code-reviewer | **sonnet** | 주 1회 | ~$2 | API $11 |
| @domain-researcher | **sonnet** | 월 2~3회 | ~$1.5 | API $11 |
| 여유분 | — | — | ~$2.5 | API $11 |
| **API 합계** | | | **~$8.5 / $11** | |

---

## 비용 절약 핵심 규칙

1. **의심되면 메인에서 직접 하라.** 서브에이전트는 출력이 거대하거나 격리가 필요할 때만 쓴다.
2. **haiku 에이전트를 먼저 써라.** design-verifier와 test-analyst는 sonnet의 1/3 비용이다.
3. **architect는 세션 모드로 몰아서 질문하라.** 5~6개 질문을 한 세션에서 처리하면 70~80% 절감.
4. **서브에이전트 후속 확인은 메인에서 Bash로.** 재스폰(15K)보다 직접 실행(0.2K)이 저렴.
5. **/cost로 수시 확인하라.** 현재 세션 토큰 사용량과 비용을 볼 수 있다.

---

## 치트시트

| 상황 | 명령어 | 비용 |
|------|--------|------|
| 문서 확인 (수시) | /doc-sync | ~1K |
| 커밋 전 게이트 | /pre-commit | ~1K |
| 설계 논의 | claude --agent system-architect | 첫 턴 ~20K, 이후 ~2K |
| 테스트 분석 | @"test-analyst (agent)" ... | ~15K + 출력량 |
| 설계 vs 코드 대조 | @"design-verifier (agent)" ... | ~15K + 문서 크기 |
| 코드 리뷰 (대형) | @"code-reviewer (agent)" ... | ~15K + diff 크기 |
| 기술 조사 | @"domain-researcher (agent)" ... | ~15K + 조사량 |
| 단순 작업 | 메인에서 직접 | ~0.2K |
