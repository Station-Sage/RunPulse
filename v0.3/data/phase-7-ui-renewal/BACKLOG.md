# Phase 7 UI Renewal — BACKLOG

## 진행 현황

**현재 상태**: **문서 재정렬 완료 + Phase 7a 구현 진행 중(D5·D3·Flask API 완료, SvelteKit
프론트엔드 남음).** REVIEW-03(Today as Gateway·모바일 IA)을
최종안으로 채택 확정(2026-09-22, 사용자 확인, `DECISIONS.md`). REVIEW-02는 이미 2026-06-10에
01·03·04·06에 전부 반영되어 있었음(재확인 완료). REVIEW-03 반영: 무인 실행
(`scripts/autopilot/`) 5유닛(00 §10 결정 요약, 00 §5.1/5.3/6/7 IA 영역 서술, 01 P8→P8',
03을 8개 파일로 구조 분리) + 이번 세션 직접 작업으로 00·03·04·05·07 전체 완료:
- 00 §1.3/§4/§5.4 — Phase 순서 논거·산출물 표를 REVIEW-03 라벨로. 핵심 판단은 Today L2
  완성 시점을 7a→7b로 이연(근거: 비전 6장 그룹1/그룹2 우선순위 분리, §4.1 참조).
- 03a~03g — Today를 L0~L3 관여 구조로 전면 재작성, Story는 L2로, Plan은 Today(보기)·
  Coach(작업)로 분할 흡수. 03b-story.md·03d-plan.md는 흡수 후 안내 스텁으로 대체.
  드릴다운 표기 L1~L3→D1~D3(Today 관여 계층과 명칭 충돌 회피).
- 04 — Story/드릴다운 표기 정정 + REVIEW-03 §5가 요구한 "층별 전환 컴포넌트 필요성"
  검토 완료(결론: 신규 컴포넌트 불필요).
- 05 — Story API 흡수, PWA/라우트 표 갱신, REVIEW-03 §10이 요구한 인증·멀티테넌시
  섹션(§11) 신설(CF Access 현황·OAuth 로드맵·email@db — 단 실제 DB 라우팅 구현은
  범위 밖으로 명시).
- 07 — Phase 7a~7d 전체를 신 IA로 재정렬.

문서 재정렬 단계에선 데이터 레이어(D1~D5) 변경 없음(REVIEW-03 §7, 순수 UI/IA 재검토).
이후 실제 구현 단계에서 D5(`today_service.py`/`coach_service.py` 전체, 나머지 3개 스텁)와
D3(`user_inputs`/`ai_feedback` + 구현 중 발견한 `chat_threads`)를 완료(2026-09-22, plan
mode로 조사·설계 후 승인받아 진행). 이어서 `src/api/` Flask `/api/v1/` 블루프린트 9개
엔드포인트(Today+Library+Coach)도 완료(2026-09-22, 같은 세션). 상세는 DONE 참조.
D1/D2/D4는 아직 미착수, SvelteKit 프론트엔드(`P7-IMPL-SVELTE`)도 아직.

**보류(사용자 지시, 2026-09-22, "러닝이 우선")**:
1. PWA 타이밍 — 비전 그룹1 vs 00/07의 7c 배치 불일치.
2. 멀티스포츠 범위 — 비전 그룹1 항목이 00/07 어디에도 없음.
3. S0/S1/S2 화면 설계(위 NOW `P7-REVIEW03-LIFECYCLE` 참조) — REVIEW-03 §9-4가 정한
   구현순서(S3→S2→S0)상 급하지 않음.
4. export 엔드포인트(`GET /api/v1/data/export`, P8' 요건) 07 어느 단계에도 미배정 —
   05 §11.4에서 발견, 판단 보류.
5. email@db 멀티테넌시 DB 라우팅 실제 구현 — 05 §11.3에서 범위 밖으로 명시, 별도
   시스템 설계 필요.

---

## 결정 완료 사항 (`00` 문서)

| 분기점 | 결정 내용 | 상태 |
|--------|-----------|------|
| **A. IA** | ~~사용자 의도 중심 5+1 영역~~ → **하단 3탭(Today/Library/Coach) + 상단 3선 메뉴** (REVIEW-03 v0.3). Story는 Today L2로 흡수, Plan은 현황(Today L2)·작업(Coach)으로 분할 | ✅ 00 전체(§1~10)·02·07 반영 |
| **B. 기술 스택** | SvelteKit + Tailwind CSS + Flask API (JSON only) + 단일 프로세스 배포 | 유효 |
| **C. 디자인** | Quiet Data 미니멀리즘 + Story 영역 에디토리얼 / 글래스모피즘 폐기 | ✅ "Today L2 예외"로 00 §5.3 반영 |
| **D. 마이그레이션** | `/v2/` 단계별 구축 → 완성 후 디폴트 스위치 (Phase 7a→7d 4단계) | ✅ 00 §5.4·07 화면 분배 재정렬 완료 (2026-09-22) |

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

### 데이터 레이어 확장 5건
| ID | 내용 | 단계 | 상태 |
|----|------|------|------|
| D1 | `parent_metric_id` 트리 활성화 — Calculator 자식 메트릭 행 저장 | Phase 7a | 미구현 |
| D2 | 활동 그룹 ID 모델 명시화 (그룹 마스터 테이블) | Phase 7b | 미구현 |
| D3 | `user_inputs` / `ai_feedback` 테이블 신설 (+ 구현 중 발견: `chat_threads` 신설) | Phase 7a | ✅ 완료(2026-09-22) |
| D4 | `athlete_profile_snapshots` 테이블 신설 | Phase 7c | 미구현 |
| D5 | `src/services/` — today_service·coach_service 구현, 나머지 3개 스텁 | Phase 7a (전제조건) | ✅ 완료(2026-09-22) |

---

## NOW

- **[P7-REVIEW03-LIFECYCLE]** REVIEW-03 §9·§10이 요구한 S0(비로그인 랜딩)·S1(가입/연결)·
  S2(콜드스타트) 화면 설계가 아직 없다 — 지금까지 한 재정렬은 전부 S3(데이터 충만) 기준.
  §9-4가 정한 구현 순서(S3→S2→S0)상 Phase 7a~7d 착수를 막지는 않지만, 03 화면 카탈로그에
  언젠가 반영해야 하는 남은 설계 작업. **(판단 필요)** — 새 화면 설계라 지금까지의
  "재정렬"보다 범위가 큼, 착수 시점은 사용자 판단. 2026-09-22 D5/D3 착수 확정 시
  사용자가 이 항목은 보류.

---

## NEXT

(비어있음 — 다음 후보는 LATER의 `P7-IMPL-D1`/`P7-IMPL-SVELTE` 중 사용자 판단 후 승격)

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

- **[P7-IMPL-D5, P7-IMPL-D3]** Phase 7a 서비스 레이어 + 신규 테이블 구현(2026-09-22, plan
  mode로 조사 후 승인받아 진행). D5: `today_service.py`(get_today_status/briefing,
  get_recent_activities, save_checkin)·`coach_service.py`(list_threads/create_thread/
  add_message) 전체 구현, `metrics_service.py`/`plan_service.py`/`data_service.py`는
  스텁(7b~7d). `story_service.py`는 만들지 않음(Story→Today L2 흡수, 이미 반영된 IA
  결정과 일관). `activity_service.list_activities()`도 안 만듦 — 기존
  `get_activity_list()`가 이미 필터/정렬/페이지네이션 지원. D3:
  `user_inputs`/`ai_feedback` DDL(원안 대비 조정 2건 — activity_id FK 제거,
  ai_feedback 타입 TEXT→INTEGER 정정). **구현 중 ADR에 없던 스키마 필요성 발견**:
  Coach 스레드 기능에 `chat_threads` 테이블 + `chat_messages.thread_id` 컬럼 필요
  (SCHEMA_VERSION 15→16) — `chat_engine.chat()`에 하위호환 `thread_id` 옵션 추가로
  대응. 신규 테스트 28개(`test_user_inputs.py`/`test_today_service.py`/
  `test_coach_service.py`/`test_chat_engine_threads.py`), 전체 1404 passed. 과정에서
  D3/D5와 무관한 기존 버그(rule fallback ImportError) 1건 발견 → 최상위
  `BACKLOG.md`의 `BUG-CHAT-RULE-FALLBACK`로 기록, 이 시점엔 범위 밖이라 수정 안 함.
  상세 판단 근거는 `06-data-layer-extensions.md` "구현 후기" 절. **(2026-09-22 후속 수정
  완료 — 최상위 `BACKLOG.md` DONE 참조, 아래 "진행 현황"도 갱신됨)**
- **[P7-IMPL-API]** Flask `/api/v1/` 블루프린트 9개 엔드포인트(2026-09-22, plan mode로 조사 후
  승인받아 진행). 범위는 사용자 확인으로 BACKLOG 한 줄 설명(Today/Library)보다 넓게
  확정 — 07 로드맵의 Phase 7a 산출물 체크리스트대로 Coach MVP 4개 포함. `src/api/`
  신설(`__init__.py`의 `api_bp` + `routes_today.py`/`routes_library.py`/`routes_coach.py`),
  `src/web/app.py`에 등록. 새 비즈니스 로직 없이 D5 서비스 함수를 그대로 노출하는
  배선 작업 — 유일한 서비스 레이어 추가는 `coach_service.get_thread()`(스레드 상세+메시지,
  `GET /coach/threads/:id`에 필요, 읽기 전용이라 D5 원칙과 일관). 응답 포맷은
  `05-tech-architecture.md` §3.3의 `{data, meta}`/`{error:{code,message}}`를 채택(기존
  v1 뷰의 `{ok,error}`와는 다른 신규 네임스페이스 계약). Library/activities 쿼리 파라미터는
  공개 계약(`sport`/`from`/`to`)과 서비스 내부 필터 키(`activity_type`/`date_from`/
  `date_to`)가 달라 라우트에서 매핑. Streams 응답은 05 문서의 필드별 배열 피벗 대신
  `get_activity_streams()`의 포인트별 dict 리스트를 그대로 반환(변환 로직 없음, 범위
  판단 — 06/07 어디에도 피벗 요구 없음). SvelteKit 프론트엔드는 범위 밖(`P7-IMPL-SVELTE`,
  LATER). 신규 테스트 25개(`test_api_today.py`/`test_api_library.py`/`test_api_coach.py`
  + `test_coach_service.py`에 `get_thread()` 테스트 2개), 전체 1439 passed,
  `check_docs.py` 0 errors.
- **[P7-REALIGN-CONTENT]** 03a~03g·04·05를 REVIEW-03 3탭 IA로 재정렬(2026-09-22, 이 세션에서
  직접 작업, 무인 실행 아님). 03a(Today)를 L0~L3 전면 재작성, 03e(Coach)에 구 Plan "작업"
  흡수, 03b/03d는 안내 스텁化. 04는 REVIEW-03 §5의 "신규 컴포넌트 필요성" 질문에 답함(불필요).
  05는 REVIEW-03 §10의 "인증·멀티테넌시 섹션" 요구를 충족(§11 신설). `check_docs.py` 0
  errors. 새로 발견한 미결 항목 5건은 "진행 현황" 보류 목록 참조.
- **[P7-REALIGN-SCOPE]** Phase 7a~7d 재정렬 — 00 §1.3/§4/§5.4, `07-migration-roadmap.md`
  전체를 REVIEW-03(하단 3탭) IA로 재정렬(2026-09-22, 이 세션에서 직접 판단·작성, 무인 실행
  아님 — 사용자가 "오토파일럿의 목적은 에이전트가 트레이드오프를 판단하는 것"이라며 사람이
  관여 가능한 이 세션에서 직접 하도록 요청). 핵심 판단: Today L2(내러티브)를 7a 완성형이
  아니라 7b로 이연 — 근거는 비전 문서(`phase-7(preview).md`) §6의 그룹1(데일리 브리핑)/
  그룹2(내러티브 보고서) 우선순위 분리. Story→Today L2, Plan→Today L2(보기)+Coach(작업)
  흡수를 07의 API/화면/체크리스트 전체에 반영. API 네임스페이스 원칙 확정(REST는 도메인
  기준 유지, IA 탭이 경계를 결정하지 않음). `check_docs.py` 0 errors 확인. 부차 발견 2건
  (PWA 타이밍 vs 비전 그룹1, 멀티스포츠 범위 누락)은 사용자 지시로 보류 — "진행 현황" 참조.
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
