# Phase 7 UI Renewal — BACKLOG

## 진행 현황

**현재 상태**: **재검토 대기 — 구현 착수 아님.** REVIEW-02(아키텍처 최적성)·REVIEW-03
(Today as Gateway·모바일 IA)가 00~07 확정 결정 중 일부를 뒤집었으나, 그 변경이
`02-information-architecture.md`에만(그것도 미커밋 상태로) 반영되고 00·01·03·04·05·07에는
아직 반영되지 않았다. 2026-09-22 확인: "5+1 영역"·"Story 독립 라우트" 등 REVIEW-03 이전
표현이 00/01/03/04/05/07/이 BACKLOG에 잔존. 이 상태로 구현(Phase 7a)에 들어가면 문서마다
다른 IA를 가리키게 된다. **다음 작업은 새 기능 구현이 아니라 00~07을 REVIEW-02·REVIEW-03의
최종 결정에 맞춰 재정렬하는 것.**

- REVIEW-03 §5 "연쇄 영향"이 재정렬 대상을 문서별로 명시함(아래 표는 그 요약).
- REVIEW-02 F1~F4(메트릭 재처리 미반영, Library 매트릭스 세로축, is_primary 근거,
  Fat Summary 경로)는 별도로 반영 필요.
- 데이터 레이어(D1~D5)는 변경 없음 — 이건 순수 UI/IA 재검토(REVIEW-03 §7).

무인 실행 인프라(`scripts/autopilot/`)를 이 재검토 루프에 쓴다 — 아래 "AUTOPILOT QUEUE" 참조.

---

## 결정 완료 사항 (`00` 문서) — ⚠️ A·P8은 REVIEW-03로 갱신됨, 00 문서 자체는 미반영

| 분기점 | 결정 내용 | 상태 |
|--------|-----------|------|
| **A. IA** | ~~사용자 의도 중심 5+1 영역~~ → **하단 3탭(Today/Library/Coach) + 상단 3선 메뉴** (REVIEW-03 v0.3). Story 독립 라우트 제거, Plan은 현황(Today 흡수)·작업(Coach)으로 분할 | 00 문서 미반영 |
| **B. 기술 스택** | SvelteKit + Tailwind CSS + Flask API (JSON only) + 단일 프로세스 배포 | 유효 |
| **C. 디자인** | Quiet Data 미니멀리즘 + Story 영역 에디토리얼 / 글래스모피즘 폐기 | Story 영역 자체가 흡수됨 — "에디토리얼" 표현 재검토 필요 |
| **D. 마이그레이션** | `/v2/` 단계별 구축 → 완성 후 디폴트 스위치 (Phase 7a→7d 4단계) | IA 변경에 맞춰 화면 분배 재정렬 필요(REVIEW-03 §5) |

### 설계 원칙 8개 — P8은 P8'로 갱신됨 (REVIEW-03 §8)
1. Evidence-First
2. Drillable Everything
3. Provider Transparency
4. Intent-Centered IA — REVIEW-03로 강화됨(관여축=의도 흐름)
5. Quiet Data
6. One Finger Reach for Input
7. State-Bound Plan
8. ~~Local-First Identity~~ → **P8' Data Ownership & Transparency** — SaaS 확정(서버 가공,
   `email@db` 격리 저장, export 가능, AI 전송 범위 고지, source_payloads 보존). "로컬 DB" 문구
   금지, "내 데이터·격리 저장·언제든 내보내기"로 표현. `01-design-principles.md` 미반영.

### 핵심 컴포넌트 1차 목록 (확정)
`<EvidenceQuote>` / `<MetricCell>` / `<MetricBreakdown>` / `<ProviderComparison>` / `<QuickInput>` / `<RecommendationCard>` / `<TimelineNarrative>`

### 데이터 레이어 확장 5건 (미구현)
| ID | 내용 | 단계 |
|----|------|------|
| D1 | `parent_metric_id` 트리 활성화 — Calculator 자식 메트릭 행 저장 | Phase 7a |
| D2 | 활동 그룹 ID 모델 명시화 (그룹 마스터 테이블) | Phase 7b |
| D3 | `user_inputs` / `ai_feedback` 테이블 신설 | Phase 7a |
| D4 | `athlete_profile_snapshots` 테이블 신설 | Phase 7c |
| D5 | `src/services/` — phase-5 서비스 레이어 설계 구현 | Phase 7a (전제조건) |

---

## NOW

- **[P7-REALIGN-SCOPE]** 00·01·03·04·05·07을 REVIEW-02·REVIEW-03에 맞춰 재정렬하는 작업을
  문서별 유닛으로 쪼갠다(각 유닛이 무인 실행 큐 1건이 되도록 — 범위가 커서 아직
  AUTOPILOT QUEUE에 넣지 않음). **(판단 필요)** 완료 후에야 실제 재정렬 유닛을 큐에 올린다.

---

## NEXT

- **[P7-IMPL-D5]** `src/services/` 서비스 레이어 구현 (Phase 7a 전제조건 — D5)
- **[P7-IMPL-D3]** `user_inputs` / `ai_feedback` DDL + `db_setup.migrate()` 등록 (Phase 7a)
- **[P7-IMPL-API]** Flask `/api/v1/` 블루프린트 + Today/Library/activities 엔드포인트 (Phase 7a)

---

## AUTOPILOT QUEUE

무인 실행(`scripts/autopilot/`) 전용 항목만. `mode:"auto"` 메타가 없는 항목은 큐가
건드리지 않는다. 형식·규칙은 `scripts/autopilot/README.md` 참조.

- **[P7-AUTO-SELFTEST]** 러너 동작 검증용(실제 설계 작업 아님). `v0.3/data/phase-7-ui-renewal/AUTOPILOT-SELFTEST.md` 끝에 현재 날짜와 "ok" 한 줄 추가(없으면 한 줄짜리 제목과 함께 새로 생성) 후 `docs: autopilot selftest`로 커밋. 그 외 파일은 건드리지 않는다.
  <!-- autopilot: {"stage": "review", "mode": "auto", "attempts": 1, "deps": []} -->
- **[P7-AUTO-SPLIT-03]** `03-screen-catalog.md`(809줄)를 영역별 파일로 분리. **Read/Write로 전체를 왕복하지 말고 `sed -n 'START,ENDp' 03-screen-catalog.md > 새파일` 로 바이트 그대로 발췌한다** (내용을 한 글자도 바꾸지 않는다 — IA 재검토는 아직 사람 확인 전이라 지금은 순수 재구성만 한다). 경계는 이미 확인됨, 다시 찾지 말 것: 1-25→(인덱스로), 26-133→`03a-today.md`, 134-200→`03b-story.md`, 201-501→`03c-library.md`, 502-633→`03d-plan.md`, 634-699→`03e-coach.md`, 700-763→`03f-data.md`, 764-804→`03g-common-patterns.md`, 805-809→(인덱스로). 각 발췌 파일 맨 앞에 `# Phase 7 UI Renewal — 화면 카탈로그 · <영역명>` 한 줄과 `[← 목차](03-screen-catalog.md)` 링크만 추가(본문 내용 자체는 불변). `03-screen-catalog.md`는 1-25행 + 각 파일 1줄 요약 링크 목록 + 805-809행(작성 이력)만 남긴 인덱스로 교체. 완료 후 8개 파일 총 줄 수 자릿수가 크게 어긋나지 않는지 `wc -l`로만 가볍게 확인(정확한 절대치 비교는 안 해도 됨 — 헤더 줄 추가로 약간 늘어나는 게 정상). 오타·불일치를 발견해도 고치지 말고 DECISIONS.md에 메모만. `docs: split 03-screen-catalog into per-area files`로 커밋.
  <!-- autopilot: {"stage": "review", "mode": "auto", "attempts": 1, "deps": []} -->
- **[P7-AUTO-ALIGN-01-P8]** `01-design-principles.md`에서 P8을 REVIEW-03 §8이 확정한 P8'로 교체. 건드릴 곳 3군데뿐, 그 외는 손대지 말 것: (1) 24-37행 "원칙 우선순위" 목록의 "8. Local-First Identity"를 "8. Data Ownership & Transparency"로, (2) 360-407행 "## P8 — Local-First Identity" 섹션 전체(정의/근거/적용/위반 예시/준수 예시 5개 하위 섹션 구조는 유지)를 아래 내용으로 다시 쓴다, (3) 442행 체크리스트의 "P8 ☐ 오프라인에서도..." 줄을 데이터 소유권·투명성 확인 문항으로 교체. **P8' 정의(그대로 쓸 것, REVIEW-03 §8 원문)**: "데이터는 서버에서 가공되더라도, (1) 사용자별로 격리 저장되고(`email@db`), (2) 언제든 전체 export/백업 가능하며, (3) 외부 LLM/ML에 전송되는 데이터 범위가 투명하게 고지되고, (4) 원본(source_payloads)이 보존되어 재가공·이식이 가능하다 = '클라우드에 있되 내 것이다'." 근거는 REVIEW-03 §8(SaaS 확정 — 데이터는 VPC 내 API로 수집·가공, 통합·ML·계획 가치 자체가 서버 가공을 전제, 인증 현황은 Cloudflare Access, 로드맵은 Google/Apple OAuth)로 다시 쓰고, "로컬에 있다"는 취지의 문장은 전부 제거한다. 위반/준수 예시는 "클라우드 강조를 숨긴다"가 아니라 "전송 범위를 투명히 밝히지 않는다/밝힌다"로 바꾼다. 마지막에 "## 작성 이력" 최상단(기존 v0.3 줄 바로 위)에 새 v0.4 항목 한 줄 추가: "REVIEW-03 반영 — P8 → P8'(Data Ownership & Transparency)로 재해석". `docs: 01 P8 → P8' 재해석 (REVIEW-03)`로 커밋.
  <!-- autopilot: {"stage": "review", "mode": "auto", "attempts": 1, "deps": []} -->
- **[P7-AUTO-ALIGN-00-SUMMARY]** `00-diagnostic-and-direction.md`의 §10 "결정 요약 — 한 페이지"(306행부터 문서 끝 전까지, `>` 인용 블록)만 REVIEW-03 최종안으로 교체한다. 그 외 섹션(§1~§9)은 이번 유닛에서 건드리지 않는다(별도 후속 작업). 결정 A를 "사용자 의도 중심 5+1 영역(Today/Story/Library/Plan/Coach+Data)"에서 "하단 3탭(Today/Library/Coach) + 상단 3선 메뉴, Story는 Today 흡수·독립 라우트 없음, Plan은 현황(Today)·작업(Coach)으로 분할"로 바꾸고, 원칙 8 줄을 "Local-First Identity"에서 "Data Ownership & Transparency(P8') — SaaS, 서버 가공, `email@db` 격리 저장, export 가능"으로 바꾼다. 근거는 `REVIEW-03-today-as-gateway-and-mobile-ia.md`를 참조(전체를 다 읽지 말고 §2 "핵심 재정의", §4 "모바일 IA 재설계안 확정", §8 "배포 모델 확정"만 읽으면 충분). "이 결정은 REVIEW-03(2026-09-22 확정)으로 갱신됨" 한 줄을 요약 블록 맨 위에 추가. `docs: 00 결정 요약을 REVIEW-03 최종안으로 갱신`으로 커밋.
  <!-- autopilot: {"stage": "review", "mode": "auto", "attempts": 1, "deps": []} -->

---

## LATER

- **[P7-IMPL-D1]** parent_metric_id 활성화 — fitness/utrs/cirs/race_readiness Calculator 수정 4개 (Phase 7a)
- **[P7-IMPL-SVELTE]** SvelteKit 프로젝트 초기화 + 공통 컴포넌트 7개 구현 (Phase 7a)

---

## DONE

- **[P7-07]** `07-migration-roadmap.md` v0.1 완료 — Phase 7a~7d 4단계 로드맵, 단계별 산출물·검증 기준·전환 조건, 롤백 전략, 기능 동등성 체크리스트, 위험 요소 5건
- **[P7-06]** `06-data-layer-extensions.md` v0.1 완료 — D1~D5 ADR 5건, DDL (user_inputs/ai_feedback/activity_groups/athlete_profile_snapshots), Calculator 수정 범위(4개), 마이그레이션 실행 순서, 영향 파일 목록, 테스트 요건
- **[P7-05]** `05-tech-architecture.md` v0.1 완료 — SvelteKit adapter-static + Flask 단일 프로세스, `/api/v1/` 엔드포인트 전체 목록, 빌드·배포 전략, PWA Cache-First 전략, 베타 토글 구현, ADR 6개, 구현 전제조건 체크리스트
- **[P7-04]** `04-component-catalog.md` v0.1 완료 — 7개 컴포넌트 props 인터페이스(TypeScript), 상태 테이블, 레이아웃 와이어프레임, 인터랙션 패턴, 공유 디자인 토큰(색상·타이포·간격), 접근성 원칙
- **[P7-03]** `03-screen-catalog.md` v0.1 완료 — 6개 영역 22개 화면 텍스트 와이어프레임, 공통 패턴 4개 (드릴다운 레벨, Provider 배지, EvidenceQuote 칩, 상태 기반 배지)
- **[P7-02]** `02-information-architecture.md` v0.1 완료 — 전체 라우트 트리, URL 스키마 규칙, 구↔신 URL 리다이렉트 매핑, 네비게이션 구조(데스크탑/모바일), 영역별 진입 흐름 5개, 영역 간 컨텍스트 유지 패턴, 딥링크, 마이그레이션 단계
- **[P7-01]** `01-design-principles.md` v0.1 완료 — 원칙 8개 상세 정의(적용/위반/준수 예시 포함), 우선순위, 충돌 해결 예시, 설계 완료 체크리스트
- **[P7-00]** `00-diagnostic-and-direction.md` v0.2 완료 — 현 UI 진단(3/10), 데이터 레이어 적합도(8.5/10), 분기점 A/B/C/D 확정, KPI 매핑 8개
