# Phase 7 UI Renewal — BACKLOG

## 진행 현황

**현재 상태**: **재정렬 진행 중.** REVIEW-03(Today as Gateway·모바일 IA)을 최종안으로
채택 확정(2026-09-22, 사용자 확인, `DECISIONS.md`). REVIEW-02는 이미 2026-06-10에
01·03·04·06에 전부 반영되어 있었음(재확인 완료, 별도 작업 불필요 — 착오였던
이전 기록 정정). REVIEW-03 반영은 무인 실행(`scripts/autopilot/`)으로 5유닛 완료·병합됨:
00 §10 결정 요약, 00 §5.1/5.3/6/7의 IA 영역 서술(3탭+3선, L0~L3 관여 모델), 01 P8→P8',
03을 영역별 8개 파일로 분리(내용은 아직 구 IA 그대로).

**남은 재정렬**: 00 §1~4(진단·재독 근거 서술, 특히 §4의 Phase 순서 논거가 구 5개 영역
전제)·§5.4(Phase 단계별 산출물 표), 03a~03g 각 파일의 내용 자체(구조만 나눴을 뿐 Story
흡수·Today 4층 구조는 미반영), 04(층별 컴포넌트 검토), 05(인증/멀티테넌시 섹션 —
Cloudflare Access/OAuth 로드맵/email@db 명문화), 07(Phase 7a~7d 화면 분배 — 00 §4·§5.4와
함께 다뤄야 함, Story/Plan이 여러 단계에 얽혀있어 재정렬 난이도 높음). 데이터 레이어
(D1~D5)는 변경 없음 — 이건 순수 UI/IA 재검토(REVIEW-03 §7).

---

## 결정 완료 사항 (`00` 문서)

| 분기점 | 결정 내용 | 상태 |
|--------|-----------|------|
| **A. IA** | ~~사용자 의도 중심 5+1 영역~~ → **하단 3탭(Today/Library/Coach) + 상단 3선 메뉴** (REVIEW-03 v0.3). Story는 Today L2로 흡수, Plan은 현황(Today L2)·작업(Coach)으로 분할 | ✅ 00 §5.1·§5.3·§6·§7·§10·02 반영. §1~4·§5.4 미반영 |
| **B. 기술 스택** | SvelteKit + Tailwind CSS + Flask API (JSON only) + 단일 프로세스 배포 | 유효 |
| **C. 디자인** | Quiet Data 미니멀리즘 + Story 영역 에디토리얼 / 글래스모피즘 폐기 | ✅ "Today L2 예외"로 00 §5.3 반영 |
| **D. 마이그레이션** | `/v2/` 단계별 구축 → 완성 후 디폴트 스위치 (Phase 7a→7d 4단계) | 00 §5.4·07 화면 분배 재정렬 아직 미반영 |

### 설계 원칙 8개
1. Evidence-First
2. Drillable Everything
3. Provider Transparency
4. Intent-Centered IA — REVIEW-03로 강화됨(관여축=의도 흐름)
5. Quiet Data
6. One Finger Reach for Input
7. State-Bound Plan
8. ~~Local-First Identity~~ → **P8' Data Ownership & Transparency** — SaaS 확정(서버 가공,
   `email@db` 격리 저장, export 가능, AI 전송 범위 고지, source_payloads 보존). ✅ 00·01 반영
   완료(2026-09-22).

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

- **[P7-REALIGN-SCOPE]** 남은 재정렬(00 §1~4·§5.4, 03a~03g 내용, 04, 05, 07)을 무인 실행
  유닛으로 쪼갠다. 지금까지 쓴 패턴(정확한 행 범위·교체할 문구를 미리 지정해 탐색 비용을
  줄임)을 그대로 적용. 00 §4(Phase 순서 논거)·§5.4(단계별 산출물 표)와 07(Phase 7a~7d 화면
  분배)은 사실상 같은 내용이라 함께 재설계해야 함 — 이건 REVIEW-03 §5·§6가 제안한 것보다
  범위가 커서(Phase 순서 자체를 다시 정해야 함) 무인 실행 전에 사람이 방향을 먼저 정하는
  게 나을 수 있음. **(판단 필요)** 03a~03g 내용 재작성은 그 이후.

---

## NEXT

- **[P7-IMPL-D5]** `src/services/` 서비스 레이어 구현 (Phase 7a 전제조건 — D5)
- **[P7-IMPL-D3]** `user_inputs` / `ai_feedback` DDL + `db_setup.migrate()` 등록 (Phase 7a)
- **[P7-IMPL-API]** Flask `/api/v1/` 블루프린트 + Today/Library/activities 엔드포인트 (Phase 7a)

---

## AUTOPILOT QUEUE

무인 실행(`scripts/autopilot/`) 전용 항목만. `mode:"auto"` 메타가 없는 항목은 큐가
건드리지 않는다. 형식·규칙은 `scripts/autopilot/README.md` 참조. 완료 항목은
DONE으로 옮긴다.

(비어있음 — 다음 유닛은 P7-REALIGN-SCOPE의 판단 이후 추가)

---

## LATER

- **[P7-IMPL-D1]** parent_metric_id 활성화 — fitness/utrs/cirs/race_readiness Calculator 수정 4개 (Phase 7a)
- **[P7-IMPL-SVELTE]** SvelteKit 프로젝트 초기화 + 공통 컴포넌트 7개 구현 (Phase 7a)

---

## DONE

- **[P7-AUTO-*]** REVIEW-03 재정렬 1차 5유닛, 무인 실행(`scripts/autopilot/`)으로 완료·검증·병합
  (`renew/data-architecture`, 2026-09-22, 총 비용 ≈$1.6). `P7-AUTO-SELFTEST`(러너 검증),
  `P7-AUTO-SPLIT-03`(03을 영역별 8개 파일로 분리, 원본과 바이트 단위 diff 대조 완료),
  `P7-AUTO-ALIGN-01-P8`(P8→P8' 재작성), `P7-AUTO-ALIGN-00-SUMMARY`(00 §10 결정 요약 갱신),
  `P7-AUTO-ALIGN-00-IA-AREAS`(00 §5.1/5.3/6/7 IA 영역 서술을 3탭+L0~L3 관여 모델로 갱신).
  1차 시도에서 worktree가 base 브랜치 갱신 없이 고정돼 있던 버그로 예산 초과 실패 1건 →
  `worktree.sync()` 추가로 수정 후 재시도 성공. 상세 커밋 이력은 `scripts/autopilot/` git log 참조.
- **[P7-07]** `07-migration-roadmap.md` v0.1 완료 — Phase 7a~7d 4단계 로드맵, 단계별 산출물·검증 기준·전환 조건, 롤백 전략, 기능 동등성 체크리스트, 위험 요소 5건
- **[P7-06]** `06-data-layer-extensions.md` v0.1 완료 — D1~D5 ADR 5건, DDL (user_inputs/ai_feedback/activity_groups/athlete_profile_snapshots), Calculator 수정 범위(4개), 마이그레이션 실행 순서, 영향 파일 목록, 테스트 요건
- **[P7-05]** `05-tech-architecture.md` v0.1 완료 — SvelteKit adapter-static + Flask 단일 프로세스, `/api/v1/` 엔드포인트 전체 목록, 빌드·배포 전략, PWA Cache-First 전략, 베타 토글 구현, ADR 6개, 구현 전제조건 체크리스트
- **[P7-04]** `04-component-catalog.md` v0.1 완료 — 7개 컴포넌트 props 인터페이스(TypeScript), 상태 테이블, 레이아웃 와이어프레임, 인터랙션 패턴, 공유 디자인 토큰(색상·타이포·간격), 접근성 원칙
- **[P7-03]** `03-screen-catalog.md` v0.1 완료 — 6개 영역 22개 화면 텍스트 와이어프레임, 공통 패턴 4개 (드릴다운 레벨, Provider 배지, EvidenceQuote 칩, 상태 기반 배지)
- **[P7-02]** `02-information-architecture.md` v0.1 완료 — 전체 라우트 트리, URL 스키마 규칙, 구↔신 URL 리다이렉트 매핑, 네비게이션 구조(데스크탑/모바일), 영역별 진입 흐름 5개, 영역 간 컨텍스트 유지 패턴, 딥링크, 마이그레이션 단계
- **[P7-01]** `01-design-principles.md` v0.1 완료 — 원칙 8개 상세 정의(적용/위반/준수 예시 포함), 우선순위, 충돌 해결 예시, 설계 완료 체크리스트
- **[P7-00]** `00-diagnostic-and-direction.md` v0.2 완료 — 현 UI 진단(3/10), 데이터 레이어 적합도(8.5/10), 분기점 A/B/C/D 확정, KPI 매핑 8개
