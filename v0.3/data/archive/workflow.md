# RunPulse 개발 프로세스 개선 계획

> 작성일: 2026-03-29
> 목적: Claude Code 단독 개발 환경에서 반복되는 누락/검증 문제 해결을 위한 문서 재편, 폴더 관리, 에이전트 활용 전략

---

## 1. 현재 문제 진단

### 1.1 핵심 문제: AI 에이전트 관리의 악순환

사용자 테스트 후 수정사항 다수 발생
→ 그때그때 Claude Code에 비구조적으로 던짐
→ Claude Code가 일부만 수정하고 "완료" 선언
→ 기획 명세서에는 반영 안 됨
→ 다음 세션에서 뭐가 됐고 안 됐는지 파악 불가
→ 검수도 불가능 (기준이 없으니)
→ md 파일 동기화 시도 → md가 너무 많아 오히려 부담

### 1.2 구체적 증상

- **기능 누락**: Claude Code가 요청된 기능 중 일부만 구현하고 완료 선언
- **문서 미갱신**: 코드는 수정했지만 관련 md 파일 업데이트 누락
- **거짓 완료**: "완료했다"고 하지만 실제 수정 안 된 케이스
- **명세서 드리프트**: 그때그때 추가 요구사항이 기획 문서에 반영 안 됨
- **문서 과다**: v0.2/.ai/ 12개 파일 73KB — 세션마다 읽기엔 과도
- **정합성 붕괴**: 문서 간 숫자/상태 불일치 (테스트 수, 탭 수 등)
- **토큰 낭비**: 불필요한 문서까지 읽어 토큰 오버헤드 발생

### 1.3 근본 원인

md 파일들이 "기획서 + 작업지시서 + 상태추적기 + 검수기준"을 동시에 담당.
하나가 업데이트 안 되면 전체가 틀어진다.
Claude Code는 "코드 작성"이 주 임무라서 md 동기화 같은 메타 작업은 체크리스트를 넣어도 우선순위에서 밀린다.
문서를 더 잘 쓴다고 해결되는 문제가 아니라, **문서 기반 관리 방식 자체의 한계**에 도달한 상황.

---

## 2. 문서 구조 재편

### 2.1 현재 문서 구조 (문제)

| 위치 | 파일 수 | 총 크기 | 문제 |
|------|---------|---------|------|
| CLAUDE.md | 1 | 6KB | 양호, 유지 |
| AGENTS.md | 1 | 3KB | v0.1 수준, CLAUDE.md와 불일치 |
| .claude/rules/ | 2 | 2KB | 양호, 유지 |
| v0.2/.ai/ | 12 | 73KB | 과다, 역할 중복, 정합성 붕괴 |
| docs/ | 10 | 75KB | 인간용 문서, 에이전트와 무관 |

**세션당 에이전트가 읽는 양: 약 40KB+**

### 2.2 목표 문서 구조

| 위치 | 크기 | 역할 | 읽는 시점 |
|------|------|------|-----------|
| CLAUDE.md | 6KB | 프로젝트 헌법 (거의 안 바뀜) | 매 세션 |
| BACKLOG.md | 2KB | 유일한 작업 추적 (자주 바뀜) | 매 세션 |
| AGENTS.md | 1KB | CLAUDE.md 요약 + 에이전트별 차이점 | Codex 검수 시 |
| .claude/rules/ | 2KB | 자동 적용 규칙 | 자동 |
| src/web/GUIDE.md | 2KB | 웹 폴더 가이드 | 웹 작업 시 |
| src/metrics/GUIDE.md | 2KB | 메트릭 폴더 가이드 | 메트릭 작업 시 |
| src/sync/GUIDE.md | 1KB | 동기화 폴더 가이드 | 동기화 작업 시 |
| src/ai/GUIDE.md | 1KB | AI 폴더 가이드 | AI 작업 시 |
| v0.2/.ai/metrics.md | 12KB | 계산식 원본 | 새 메트릭 구현 시만 |
| v0.2/.ai/decisions.md | 10KB | 설계 결정 기록 | 설계 판단 시만 |

**세션당 에이전트가 읽는 양: 약 10KB (70% 절감)**

### 2.3 v0.2/.ai/ 파일 처리 계획

| 파일 | 크기 | 처리 | 이유 |
|------|------|------|------|
| todo.md | 8KB | → BACKLOG.md로 대체 (미완료만 이동) | 완료/미완료 혼재로 포커스 상실 |
| architecture.md | 15KB | → 폐기, 폴더별 GUIDE.md로 분배 | 전체를 매번 읽을 필요 없음 |
| files_index.md | 12KB | → 폐기, 폴더별 GUIDE.md 파일 맵으로 대체 | 중복 |
| index.md | 8KB | → 폐기, CLAUDE.md + BACKLOG.md로 대체 | 역할 중복 |
| roadmap.md | 3KB | → BACKLOG.md에 흡수 | 소량, 별도 파일 불필요 |
| changelog.md | 17KB | → 폐기, git log로 대체 | 수동 동기화 실패 반복 |
| changelog_history.md | 5KB | → 폐기, git log로 대체 | 동일 |
| metrics.md | 12KB | ✅ 유지, 필요 시만 참조 | 계산식 원본, 대체 불가 |
| metrics_by_claude.md | 9KB | ✅ 유지, 비교용 보존 | 대안 버전 |
| decisions.md | 10KB | ✅ 유지, 필요 시만 참조 | 설계 결정 기록 |
| v0.2_audit_report.md | 10KB | → archive/ 이동 | 일회성 감사 보고서 |
| v0.2_ui_gap_analysis.md | 22KB | → archive/ 이동 | 완료된 갭 분석 |

폐기 대상 파일은 삭제하지 않고 `v0.2/.ai/archive/` 폴더로 이동하여 필요 시 참조 가능하게 보존.

---

## 3. 폴더별 GUIDE.md 설계

### 3.1 원칙: 3계층 점진적 로딩

- **Level 1 (항상)**: CLAUDE.md + .claude/rules/ + BACKLOG.md — 약 10KB
- **Level 2 (해당 폴더)**: src/xxx/GUIDE.md — 약 1~2KB
- **Level 3 (필요 시)**: v0.2/.ai/metrics.md, decisions.md — 10~12KB

CLAUDE.md에 규정: "Level 1은 항상, Level 2는 작업 대상 폴더만, Level 3은 명시적 지시 시만"

### 3.2 GUIDE.md 표준 구조

각 GUIDE.md는 아래 섹션을 포함. 해당 폴더에 관련된 내용만 최소한으로.

- **구조**: 파일 조직 패턴 (예: 3-tier loaders/cards/views)
- **파일 맵**: 파일명과 한줄 역할 설명
- **규칙**: 해당 폴더 작업 시 지켜야 할 규칙
- **주의사항**: 300줄 초과 파일, 알려진 기술부채
- **의존성**: 다른 폴더와의 연결 관계

### 3.3 생성할 GUIDE.md

**src/web/GUIDE.md (~2KB)**
- 3-tier 패턴 (loaders → cards → views)
- 뷰별 파일 맵 (대시보드, 활동, 레포트, 훈련, AI코치, 웰니스, 설정)
- 다크테마 색상 코드, card 스타일, 하단 네비 규칙
- 차트 컴포넌트 (ECharts CDN vs SVG)
- 300줄 초과 파일 목록

**src/metrics/GUIDE.md (~2KB)**
- 함수 시그니처 패턴 (일별/활동별)
- 계산 순서 (engine.py 의존 그래프)
- store.py 사용법
- "데이터 없으면 None" 규칙
- 새 메트릭 추가 시 체크리스트

**src/sync/GUIDE.md (~1KB)**
- 4소스별 파일 맵 (Garmin/Strava/Intervals/Runalyze)
- 병렬 동기화 구조
- sync 완료 후 engine 호출 훅
- API 래퍼 (src/utils/api.py) 사용 규칙

**src/ai/GUIDE.md (~1KB)**
- AI 프로바이더 구조 (Gemini/Groq/Rule-based)
- 프롬프트 템플릿 위치
- Function Calling 도구 목록
- fallback 체인

---

## 4. BACKLOG.md 설계

### 4.1 구조

BACKLOG.md는 유일한 작업 추적 파일. 4개 섹션만.

- **NOW**: 진행 중 — 최대 3개
- **NEXT**: 다음 착수 — 최대 5개
- **BUGS**: 사용자 테스트에서 발견, 즉시 수정
- **DONE**: 최근 10건만 유지, 나머지는 git log

### 4.2 항목 형식

각 항목에 인라인 완료 조건 포함. 별도 문서 참조 없이 한 항목으로 "뭘 해야 하고, 언제 끝인지" 명확.

예시:
- AUTH-1: 인증/로그인 시스템
-- scope: bcrypt, Flask 세션, 미인증 리다이렉트
-- files: src/web/auth.py(신규), views_settings.py(수정)
-- done: 테스트 5개 + /login 동작 + 기존 테스트 전체 통과

### 4.3 운영 규칙

- Claude Code는 BACKLOG.md에 없는 작업을 임의 진행하지 않음
- 사용자 테스트 후 수정사항은 **먼저 BACKLOG.md BUGS에 기록** 후 Claude Code에 지시
- DONE 섹션 10건 초과 시 오래된 것부터 삭제 (git log에 이력 보존)
- NOW 항목 모두 완료 시 NEXT에서 승격

### 4.4 todo.md에서 이관할 미완료 항목

**NOW/NEXT 이관:**
- 인증/로그인 시스템 (bcrypt, 세션, 리다이렉트)
- REST API (/api/v1/*)
- DB 정규화, 멀티유저 강화
- 캘린더 API 연동 (Google/Naver/Garmin)

**v0.4 NEXT 이관:**
- React Native 모바일 앱
- TQI (ML 기반 훈련 품질 지수)
- PLTD (ML 기반 개인화 역치 탐지)
- GPX/FIT/TCX Import, CSV/JSON Export

---

## 5. CLAUDE.md 개선

### 5.1 "필수 읽기" 섹션 변경

**변경 전:**
1. v0.2/.ai/todo.md — 상단 "현재 미완료 작업" 섹션만 읽을 것
2. v0.2/.ai/architecture.md — 코드 구조 + 모듈 맵

**변경 후:**
1. BACKLOG.md — 현재 작업 확인 (NOW/BUGS만)
2. 작업 대상 폴더의 GUIDE.md (해당 시만):
   - src/web/GUIDE.md (웹 UI 작업 시)
   - src/metrics/GUIDE.md (메트릭 작업 시)
   - src/sync/GUIDE.md (동기화 작업 시)
   - src/ai/GUIDE.md (AI 작업 시)
3. 필요 시 참조 (매번 읽지 않음):
   - v0.2/.ai/metrics.md — 새 메트릭 구현 시 계산식
   - v0.2/.ai/decisions.md — 설계 판단 필요 시

### 5.2 "완료 규칙" 추가

CLAUDE.md "핵심 규칙" 섹션에 추가:

1. BACKLOG.md 해당 항목의 done 조건 모두 충족 확인
2. 수정한 파일이 속한 폴더의 GUIDE.md 파일 맵이 여전히 정확한지 확인
3. `python -m pytest tests/` 전체 통과 (test_doc_sync.py 포함)
4. 300줄 초과 파일이 새로 생기면 즉시 분리 계획 제시
5. Calculator 추가/변경 시 `python scripts/gen_metric_dictionary.py` 실행
6. BACKLOG.md 해당 항목 [x] 체크 및 DONE으로 이동

### 5.3 "세션 종료 체크리스트" 추가

.claude/rules/workflow-rules.md의 세션 종료 프로토콜을 아래로 교체:

1. BACKLOG.md 해당 항목 상태 업데이트 ([x] 또는 진행률 메모)
2. 변경/생성된 파일이 해당 GUIDE.md에 반영되었는지 확인
3. `python -m pytest tests/` 전체 통과 확인 (test_doc_sync.py 포함)
4. 신규 설계 결정이 있었으면 decisions.md에 기록
5. Calculator 추가/변경 시 `python scripts/gen_metric_dictionary.py` 실행
6. `python scripts/check_docs.py` 실행 및 불일치 수정 (9개 검사 항목 전체 PASS)

---

## 6. AGENTS.md 재정의

### 6.1 현재 문제

AGENTS.md가 v0.1 수준의 코드 구조를 기술. CLAUDE.md와 심각한 불일치.
Codex 검수자 투입 시 잘못된 기준으로 검수하게 됨.

### 6.2 변경 방향

"프로젝트 요약 + 에이전트별 역할 차이"만 담는 경량 파일로 재작성.

포함할 내용:
- 프로젝트 한줄 요약
- 기술 스택 요약
- 브랜치 전략
- 실행 명령어
- "상세 규칙과 아키텍처는 CLAUDE.md 및 해당 폴더 GUIDE.md 참조"
- Codex 전용 규칙: "코드 수정 금지, 검수/리포트만 생성"

---

## 7. 에이전트 활용 전략

### 7.1 현재: Claude Code 단독

모든 역할(기획 해석, 개발, 테스트, 문서, 검수)을 하나의 에이전트가 담당.
코드 작성에 집중하면 나머지가 밀림.

### 7.2 목표: 2 에이전트 + 자동화

| 역할 | 담당 | 방식 | 비용 |
|------|------|------|------|
| 기획 | 사용자 직접 | BACKLOG.md에 항목 기록 (30초) | 없음 |
| 개발 | Claude Code | BACKLOG.md 기반 개발 | 기존 |
| 일상 검증 | 자동화 스크립트 | pytest + 문서 정합성 체크 | 없음 |
| 마일스톤 검수 | Codex Cloud | chatgpt.com에서 GitHub repo 연결 | ChatGPT Plus |

### 7.3 Genspark 기획자 — 현재 불필요

이미 PDF 원본 → metrics.md → architecture.md로 이어지는 기획 체계가 있음.
기획 품질이 아니라 기획→코드 전환 시 누락이 문제.
기획 단계에 AI 추가는 ROI 낮음.
v0.4 React Native 같은 큰 설계가 필요할 때 재검토.

### 7.4 Codex Cloud 검수자 — 마일스톤 단위 투입

매 작업마다 검수하면 비용과 시간 과도. 마일스톤 단위로 투입.

**투입 시점 예시:**
- v0.3 인증 시스템 완료 시
- REST API 완료 시
- DB 정규화 완료 시

**검수 지시 형식:**
"dev 브랜치의 최근 커밋 N개가 BACKLOG.md의 AUTH-1 명세를 충족하는지 검토.
확인 항목: 기능 누락, 보안 취약점, 테스트 커버리지, GUIDE.md 정합성"

Codex Cloud (chatgpt.com)를 사용하면 VPS에 별도 설치 없이 브라우저에서 GitHub repo 연결 검수 가능.

### 7.5 일상 검증 — 자동화 스크립트 (2026-04-04 구현 완료)

`scripts/check_docs.py` (302줄). Claude Code가 작업 완료 후 실행.

**검사 항목 (9개):**
- [1] BACKLOG.md의 NOW 항목 수 (3개 이하인지)
- [2] 각 GUIDE.md에 등록된 파일 vs 실제 존재 파일 불일치
- [3] 300줄 초과 파일 목록 출력
- [4] pytest 수집 수 출력
- [5] metric_dictionary.md 동기화 검증 (calculator 수/이름, group 수)
- [6] 문서 간 calculator 수 일치 (GUIDE.md, files_index.md, phase_summary.md)
- [7] semantic groups 수 일치
- [8] 테스트 파일 수 vs files_index.md 비교
- [9] outdated 표현 스캔 (13개 테이블, computed_metrics 등)

**추가 자동화 도구:**
- `scripts/gen_metric_dictionary.py` (252줄) — 메트릭 사전 자동 생성
- `tests/test_doc_sync.py` (97줄, 6 tests) — CI에서 문서 동기화 자동 감지

**메트릭 사전 워크플로우:**
calculator 추가/변경 → pytest 실행 → test_doc_sync.py 실패 감지 →
`python scripts/gen_metric_dictionary.py` 실행 → 재생성된 문서 커밋 → 통과

---

## 8. 수정사항 투입 프로세스 개선

### 8.1 현재 프로세스 (문제)

사용자 테스트 → 문제 발견 → Claude Code에 즉시 "이것 고쳐"
→ Claude Code가 일부만 수정 → 명세서 미반영 → 누락 반복

### 8.2 개선 프로세스

1. 사용자 테스트 → BACKLOG.md BUGS 섹션에 기록 (30초)
2. Claude Code에 "BACKLOG.md BUGS 처리해" 지시
3. Claude Code가 각 항목의 done 조건 기준으로 작업
4. 완료 시 DONE으로 이동
5. 마일스톤 시점에 Codex Cloud 검수

**핵심 변화:** "구두 지시" → "BACKLOG.md에 먼저 기록". 이것만으로 누락 추적 가능.

### 8.3 긴급 수정 (hotfix)

BACKLOG.md 기록이 어려운 긴급 1건은 직접 Claude Code에 지시 가능.
단, "완료 후 BACKLOG.md DONE에 기록할 것"을 함께 지시.

---

## 9. 실행 계획

### Phase 1: 문서 재편

1. BACKLOG.md 생성 — todo.md에서 미완료 항목만 추출, 형식 변환
2. v0.2/.ai/archive/ 폴더 생성, 폐기 대상 이동
3. CLAUDE.md 업데이트 — 필수 읽기, 완료 규칙, 세션 종료 체크리스트
4. .claude/rules/workflow-rules.md 업데이트 — BACKLOG.md 기반으로 변경
5. AGENTS.md 재작성 — 경량 요약본

### Phase 2: 폴더별 GUIDE.md 생성

1. src/web/GUIDE.md — architecture.md + files_index.md에서 웹 관련 추출
2. src/metrics/GUIDE.md — 메트릭 관련 추출
3. src/sync/GUIDE.md — 동기화 관련 추출
4. src/ai/GUIDE.md — AI 관련 추출
5. 생성 후 architecture.md, files_index.md, index.md를 archive/로 이동

### Phase 3: 자동화 — ✅ 완료 (2026-04-04)

1. ~~scripts/check_docs.py 생성~~ → 구현 완료 (9개 검사 항목, 302줄)
2. ~~CLAUDE.md 완료 규칙에 스크립트 실행 추가~~ → 완료 규칙 6항목으로 확장
3. scripts/gen_metric_dictionary.py 추가 (252줄, 메트릭 사전 자동 생성)
4. tests/test_doc_sync.py 추가 (6 tests, CI 자동 감지)
5. v0.3/data/metric_dictionary.md 생성 (859줄, single source of truth)

### Phase 4: Codex 검수자 도입 (Phase 1~3 안정화 후)

1. Codex Cloud에 GitHub repo 연결
2. AGENTS.md 기반 검수 테스트
3. 첫 마일스톤 (인증 시스템 등) 완료 시 검수 실행
4. 검수 리포트 기반으로 Claude Code에 수정 지시

---

## 10. 예상 효과

| 항목 | 현재 | 개선 후 |
|------|------|---------|
| 세션당 토큰 사용 | ~40KB 문서 로딩 | ~10KB (70% 절감) |
| 작업 추적 파일 | 12개 (v0.2/.ai/) | 1개 (BACKLOG.md) |
| 완료 기준 | 암묵적 | 인라인 done 조건 |
| 문서 동기화 부담 | 12개 파일 수동 | BACKLOG.md + GUIDE.md만 |
| 누락 검출 | 사용자가 직접 확인 | 자동화 + Codex 마일스톤 검수 |
| 수정사항 투입 | 구두 → 즉시 → 누락 | BACKLOG.md 기록 → 추적 가능 |
