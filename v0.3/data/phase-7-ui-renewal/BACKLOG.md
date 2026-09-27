# Phase 7 UI Renewal — BACKLOG

## 진행 현황

**현재 상태**: **Phase 7a 완료(D5·D3·D1·D2·Flask API·SvelteKit Today/Library/Coach
화면). Phase 7b 진행 중 — 백엔드 API 3종(`get_metric_breakdown`/
`get_provider_comparison`/`get_today_narrative`+milestones) 전부 완료·병합.
프론트도 대부분 붙음: `<MetricBreakdown>`(C3, Today L1 드릴다운 + 메트릭 상세
계산 분해) + Today L2 내러티브(`P7-IMPL-7B-TODAY-L2`) + `<ProviderComparison>`
(C4, Library 활동 상세 "소스 비교" 탭, `P7-IMPL-7B-PROVIDER-UI`) + 활동
스트림(3-D, `Sparkline.svelte` 신규, `P7-IMPL-7B-STREAMS`) + 메트릭 브라우저·
상세(3-E/3-F, `P7-IMPL-7B-METRICS-BROWSER`) + Library 홈 재설계(3-A,
`P7-IMPL-7B-LIBRARY-HUB` — `/library`가 활동 목록에서 홈 허브로, 목록은
`/library/activities`로 이동) + 웰니스 탭(`P7-IMPL-7B-WELLNESS` — 죽은 코드였던
`wellness_service.py` 실제 버그 수정 후 연결) + Coach 플랜 상세(5-F+5-A,
`P7-IMPL-COACH-PLAN-ACTIVE` — `src/training/` 기존 엔진 재사용, 리뷰 중
goal_id 없는 `planned_workouts` 교차 오염 버그 발견·수정) + Coach 새
프로그램 생성(5-C+5-D+5-E, `P7-IMPL-COACH-PLAN-CREATE` — 1차 autopilot이
5시간 한도로 중단돼 워크트리 리뷰로 직접 완료, race_date가 weeks를
무시하던 버그 발견·수정) 전부 완료(2026-09-23). Library는 3-B/3-D/3-E/3-F/
3-A/웰니스 전부 완료 — 남은 건 정체성 매트릭스(3-G-1, `P7-IMPL-PROVIDER-
MATRIX`/LATER, 기간 집계+메트릭별 primaryReason 판정 설계 필요)와 Provider
데이터 현황 카드(Phase 7d `data_service.py` 몫으로 명시적 이연,
`DECISIONS.md` 참조)뿐. Coach는 5-C~5-F 전부 완료. `P7-IMPL-TIMELINE-
NARRATIVE-FULL`(Today L2 "이번 달 전체 이야기" 패널)도 완료·병합
(2026-09-23 — 다른 세션이 구현, 이 세션이 리뷰하며 과거 달 조회 시 CTL/
마일스톤/규칙기반 텍스트가 오늘 기준으로 새던 버그 3건 + 프론트 스파크라인
2건 발견·수정). `P7-IMPL-COACH-PLAN-SESSION-DETAIL`(5-G 일일 세션 상세 —
조정 비교는 타입만, 목업의 가짜 TSS/거리 수치는 안 만듦, URL도 week/day
대신 date로 단순화)도 완료·병합(2026-09-23 — 이번 세션 리뷰 대상 유닛 중
처음으로 수정 사항 0건, 스펙 그대로 구현됨). `P7-IMPL-PROVIDER-MATRIX`(3-G-1
정체성 매트릭스 — 목업 예시 행 대신 문서 서두 "시맨틱 그룹 13개" 근거로
SEMANTIC_GROUPS 한정, 기간 집계는 "최신값" 단일 규칙)도 완료·병합
(2026-09-23 — 이번 세션 처음으로 autopilot이 큐 스펙·DECISIONS.md 설계를
무시하고 다른 구현으로 진행, DECISIONS.md에 이견 기록도 안 함 — 리뷰에서
전면 재구현). `P7-IMPL-COACH-PLAN-ADJUSTMENT-ACCEPT`는 `03e-coach.md`
196행이 Phase 7c로 명시 배정해둔 걸 확인해 앞당기지 않기로 함. 2026-09-24
Today 화면을 03a 1-A와 대조한 결과 L2의 "다음 세션 현황"(Plan "보기" 흡수)·L3 링크
블록이 아직 없음을 발견 — `P7-IMPL-TODAY-NEXT-SESSION`(프론트 전용, 기존 API
재사용)을 구현·병합(2026-09-24, 리뷰 수정 0건). 이어서 같은 대조에서 (a) 모든 근거 칩이 죽어
있음(`onOpen` 미연결) + `MetricBreakdown`이 slug 변경에 재조회 안 하는 실버그(입력 메트릭
드릴-인이 사실상 무동작), (b) 1-D 전체 마일스톤 패널 미구현을 발견 —
`P7-IMPL-EVIDENCE-DRILL`·`P7-IMPL-TODAY-MILESTONES-PANEL`을 AUTOPILOT QUEUE에 등록
(둘 다 `DECISIONS.md`에 설계 근거, 실행 대기 중). 남은 건 조정 수락
영속화(`P7-IMPL-COACH-PLAN-ADJUSTMENT-ACCEPT`/LATER, Phase 7c 예정), D4,
상단 3선 메뉴 UI(Phase 7d).**
REVIEW-03(Today as Gateway·모바일 IA)을
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
엔드포인트(Today+Library+Coach)도 완료(2026-09-22, 같은 세션). 이어서 SvelteKit
프론트엔드 착수 — `frontend/` 초기화 + 공통 레이아웃 + 컴포넌트 4개 + Today 화면 완료
(2026-09-22, `P7-IMPL-SVELTE` 1차 — 사용자가 "UI Renewal인데 실제 UI가 하나도 없다"고
지적한 게 계기). 이어서 오토파일럿(`kind:"code"`, 신규 확장)으로 D1 + Library/Coach
화면(SvelteKit 2차, `P7-IMPL-D1`/`P7-IMPL-SVELTE-2A`/`-2B`)까지 완료(2026-09-22, 사용자
"40분간 오토파일럿 돌리자" 지시). 상세는 DONE 참조. D2/D4·상단 3선 메뉴 UI는 아직.

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
| D1 | `parent_metric_id` 트리 활성화 — Calculator 자식 메트릭 행 저장 | Phase 7a | ✅ 완료(2026-09-22) |
| D2 | 활동 그룹 ID 모델 명시화 (그룹 마스터 테이블) | Phase 7b | ✅ 완료(2026-09-22, 백필 스크립트는 작성만·실행은 별도 승인 필요) |
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

P7-IMPL-D2(`activity_groups` 마스터 테이블)·P7-IMPL-D1-REST(utrs/cirs 자식 메트릭,
`P7-IMPL-D1-REST-UC`로 완료 — race_readiness는 별도 Calculator가 아니라 RRI 자신이고
`produces=["rri"]`뿐이라 자체 자식이 없음, `requires`(vdot/ctl/di/cirs)는
`P7-IMPL-METRIC-BREAKDOWN`의 inputs 조립으로 이미 커버됨, `test_rri_inputs_include_
cirs`로 검증됨) 모두 완료(2026-09-23, AUTOPILOT QUEUE 참조). "데이터 레이어 확장
5건" 중 D4만 미구현으로 남음(LATER 아님 — 아직 NEXT/NOW 어디에도 배정 안 됨, 07
로드맵에서 재확인 필요).

P7-DESIGN-7B-API는 완료(2026-09-23) — Phase 7b Flask API 4종의 서비스 함수
전부 구현·병합됨: `metrics_service.get_metric_breakdown()`
(`P7-IMPL-METRIC-BREAKDOWN`), `provider_comparison_service.
get_provider_comparison()`(`P7-IMPL-PROVIDER-COMPARISON`, 03c §3-G-2 활동별
비교만 — §3-G-1 정체성 매트릭스는 `P7-IMPL-PROVIDER-MATRIX`로 LATER 분리),
`today_service.get_today_narrative()`(`P7-IMPL-TODAY-NARRATIVE`), 그리고
마지막 남았던 `plan_service.get_static_plan_templates()`도
`P7-IMPL-COACH-PLAN-CREATE`에서 `plan_template_service.
get_static_plan_templates()`로 구현·병합 완료(DONE 참조). NOW 항목 제거.

P7-IMPL-7B-TODAY-L2는 NEXT에서 승격(2026-09-23, 사용자 지시 — "UI 설계/코딩
계속하자, 아직 너무 조금 진행됐어"). 백엔드(get_metric_breakdown/get_today_
narrative/get_today_milestones)는 이미 병합돼 있는데 프론트가 하나도 안 붙어
있음 — 이번 유닛이 실제로 눈에 보이는 첫 진전. Flask API는 이미 완료라 이번엔
SvelteKit만(`<MetricBreakdown>` C3 신규 컴포넌트 + Today L1 드릴다운 연결 +
L2 텍스트 스텁을 실제 내러티브로 교체) — NOW에 별도 요약을 남기지 않고
AUTOPILOT QUEUE의 `P7-IMPL-7B-TODAY-L2` 항목(상세 스펙)이 유일한 소스(D1/D2
때와 동일 패턴 — ID 중복은 `queue.update_item()`을 깨뜨린다). 착수 전
`DECISIONS.md`의 `[P7-IMPL-7B-TODAY-L2]` 항목 필독(C7 스펙이 실제 백엔드
응답보다 훨씬 커서 축소 결정함).

---

## NEXT

Phase 7b(07 로드맵) 본격 착수분. 사용자 "UI Renewal 설계·개발·문서화를
할일 목록화" 지시로 2026-09-22 정리(07 로드맵 §Phase 7b 산출물 목록 기준,
세부 설계는 각 항목 착수 시점에 plan mode로 확정).

(현재 NEXT 없음 — `P7-IMPL-COACH-PLAN-STATIC`은 하위 유닛
`P7-IMPL-COACH-PLAN-ACTIVE`/`P7-IMPL-COACH-PLAN-CREATE` 둘 다 done이 되어
2026-09-23 제거. `P7-IMPL-TIMELINE-NARRATIVE-FULL`은 조사 후 바로 AUTOPILOT
QUEUE로 등록해 NEXT를 거치지 않음.)

---

## AUTOPILOT QUEUE

무인 실행(`scripts/autopilot/`) 전용 항목만. `mode:"auto"` 메타가 없는 항목은 큐가
건드리지 않는다. 형식·규칙은 `scripts/autopilot/README.md` 참조. 완료 항목은
DONE으로 옮긴다.

**2026-09-22 `kind:"code"` 확장** — 지금까지 이 큐는 설계 문서 편집(`kind:"docs"`,
기본값) 전용이었다. 사용자가 "다음 작업(코드 구현 포함)을 오토파일럿 모드로"라고
요청해(정확히는 "scripts/autopilot을 코드 구현까지 확장" 선택) `run_unit.py`에
`kind:"code"` 경로를 추가했다 — 범위(`scope`)와 성공 판정 커맨드(`verify`)를 큐
메타에 명시하고, `claude -p`가 "성공"을 자체 보고해도 `run_unit.py`가 `verify`
커맨드를 워크트리에서 독립적으로 다시 돌려 통과해야만 `stage: review`로 넘어간다
(실패 시 `blocked`). 상세는 `scripts/autopilot/README.md`.

- **[P7-IMPL-D1]** parent_metric_id 트리 연결 — `PMCCalculator`(ctl/atl/tsb/ramp_rate)의
  `ramp_rate`를 `ctl`의 자식으로 저장한다(`06-data-layer-extensions.md` D1, **Phase 7a
  몫만** — 그 문서 자체가 "Phase 7a: fitness_calculator, Phase 7b: utrs/cirs/
  race_readiness"로 나눠뒀는데 LATER의 옛 설명이 4개를 전부 7a로 묶어놔서 부정확했음,
  이번에 바로잡음). 배선은 이미 대부분 있다 — `CalcResult.parent_metric_id`
  (`src/metrics/base.py`)와 `upsert_metric()`의 `parent_metric_id` 파라미터
  (`src/utils/db_helpers.py`)는 이미 존재하는데, `_save_results()`
  (`src/metrics/engine.py`, `_save_results` 함수)가 각 `CalcResult`를 순서대로
  `upsert_metric()`에 넘길 때 `parent_metric_id`를 아예 안 넘겨서 끊겨 있다.
  **구현**: (1) `CalcResult`에 `parent_metric_name: str | None = None` 필드 추가(계산
  시점엔 부모의 DB row id를 모르니 이름으로 참조) + `MetricCalculator._result()`에
  같은 파라미터 추가해 그대로 전달. (2) `_save_results()`를 다음처럼 수정: `results`를
  순서대로 돌며 `name_to_id: dict[str, int] = {}`를 누적하고, 각 result의
  `parent_metric_id = name_to_id.get(r.parent_metric_name)`을 계산해
  `upsert_metric()`에 넘긴 뒤 반환된 id를 `name_to_id[r.metric_name] = id`로 기록
  (부모가 먼저 나와야 자식이 참조 가능 — `PMCCalculator.compute()`는 이미 `ctl`을
  index 0, `ramp_rate`를 index 3으로 반환하니 순서는 그대로 둘 것). (3)
  `src/metrics/pmc.py`의 `ramp_rate` `self._result(...)` 호출에
  `parent_metric_name="ctl"` 추가. 고아 행 걱정 없음 — `upsert_metric()`이 이미
  `ON CONFLICT ... DO UPDATE`라 `ctl`의 row id는 재계산해도 안 바뀐다. 테스트는
  `tests/test_engine.py`의 `TestRunDailyMetrics`/`TestRunForDate` 패턴처럼 공개 함수
  (`run_daily_metrics`/`run_for_date` 등)를 통해 전체 파이프라인으로 검증하고, 저장된
  `ramp_rate` 행의 `parent_metric_id`가 같은 날짜 `ctl` 행의 id와 같은지 확인한다.
  `metrics_service.get_metric_breakdown()`(소비 API)은 범위 밖(Phase 7b, `07-migration-
  roadmap.md` 참조) — 이번엔 DB 행 연결까지만.
  <!-- autopilot: {"stage": "done", "mode": "auto", "attempts": 1, "deps": [], "kind": "code", "scope": ["src/metrics/base.py", "src/metrics/engine.py", "src/metrics/pmc.py", "tests/test_pmc.py", "tests/test_engine.py"], "verify": ["python3 -m pytest tests/test_pmc.py tests/test_engine.py -q", "python3 scripts/check_data_consistency.py"]} -->

- **[P7-IMPL-SVELTE-2A]** SvelteKit — Library 활동 목록 + 상세 화면(`03c-library.md`
  3-B·3-C 요약 탭만). `frontend/`의 Today 구현(`P7-IMPL-SVELTE` 1차, 이미 병합됨)이
  세운 패턴을 그대로 따른다 — `$lib/api/client.ts`의 `apiFetch()`, `$lib/provider.ts`
  (Provider 배지), `$lib/format.ts`(거리/시간/날짜 포맷), `$lib/components/
  MetricCell.svelte`(핵심 메트릭 그리드, `drillable=false` — MetricBreakdown은 7b라
  아직 없음). API는 이미 구현·테스트됨: `GET /api/v1/library/activities`
  (`?sport=&from=&to=&page=&per_page=`) → `{activities,total,has_more}`,
  `GET /api/v1/library/activities/:id` → `{activity:{core,metrics_by_category,
  source_comparison,semantic_groups,streams,laps,best_efforts}}`(요약 탭엔 core +
  metrics_by_category만 쓰면 됨), `GET /api/v1/library/activities/:id/streams` →
  `{streams:[...]}`(포인트별 dict 배열, 필드별 배열 아님 — `P7-IMPL-API` DONE 항목
  참조). 라우트: `frontend/src/routes/library/+page.svelte`(현재 "준비 중" 플레이스홀더
  교체) = 활동 목록, `frontend/src/routes/library/[id]/+page.svelte` 신규 = 상세.
  **범위 밖**: Library 홈의 시맨틱 그룹 탐색·Provider 연결 현황(3-A, `/library/metrics`
  등 7b API 필요), 랩·메트릭 탭(엔드포인트 없음), 스트림 전체 차트 시각화(이번엔 스트림
  존재 여부/포인트 수 정도만 표시), 고급 필터(정렬·거리 범위 — sport/날짜/페이지네이션만).
  <!-- autopilot: {"stage": "done", "mode": "auto", "attempts": 1, "deps": [], "kind": "code", "scope": ["frontend/src/routes/library/", "frontend/src/lib/api/library.ts", "frontend/src/lib/types/index.ts"], "verify": ["cd frontend && npm install && npm run check && npm run build"]} -->

- **[P7-IMPL-SVELTE-2B]** SvelteKit — Coach MVP 화면(`03e-coach.md` 5-A 홈 + 5-B
  대화 스레드, 컨텍스트 패널 제외 — 07 로드맵상 7d 몫). Today와 같은 패턴 재사용
  (`$lib/api/client.ts`, `EvidenceQuote.svelte`를 대화 답변 안 근거 칩에 재사용).
  API는 이미 구현·테스트됨: `GET /api/v1/coach/threads` → `{threads:[...]}`,
  `POST /api/v1/coach/threads`(body `initial_message`) → `{thread,message}`,
  `GET /api/v1/coach/threads/:id` → `{thread,messages:[...]}`,
  `POST /api/v1/coach/threads/:id/messages`(body `content`) → `{message}`. 라우트:
  `frontend/src/routes/coach/+page.svelte`(현재 "준비 중" 플레이스홀더 교체) = 최근
  대화 목록 + [+ 새 대화 시작], `frontend/src/routes/coach/[threadId]/+page.svelte`
  신규 = 메시지 스레드(사용자/Coach 말풍선 + EvidenceQuote 칩). **범위 밖**: 우측
  컨텍스트 패널(7d), Coach 홈의 "진행 중 플랜"·"새 프로그램 만들기" 섹션(plan_service가
  아직 스텁), Coach 홈의 QuickInput(compact) 블록 — 이미 Today에 있으니 중복 배치는
  이번엔 생략, 필요하면 후속 판단.
  <!-- autopilot: {"stage": "done", "mode": "auto", "attempts": 1, "deps": [], "kind": "code", "scope": ["frontend/src/routes/coach/", "frontend/src/lib/api/coach.ts", "frontend/src/lib/types/index.ts"], "verify": ["cd frontend && npm install && npm run check && npm run build"]} -->

- **[P7-IMPL-D2]** `activity_groups` 마스터 테이블 — 설계는 `06-data-layer-extensions.md`
  §D2에 DDL·백필 SQL·마이그레이션 전략까지 이미 확정돼 있음, 이번엔 그대로 코드로
  옮기는 작업만. **이번 유닛 범위는 데이터 레이어까지만** — `activity_service.
  get_provider_comparison()`(서비스 함수)은 범위 밖(`P7-IMPL-7B-LIBRARY`에서, API
  설계 확정 후). **구현**: (1) `src/db_setup.py`의 `_DDL_APP_TABLES` 블록에 06 §D2
  DDL 그대로 추가(`activity_groups` — `group_id TEXT PRIMARY KEY, primary_source
  TEXT NOT NULL, activity_date TEXT NOT NULL, distance_m REAL, member_count INTEGER
  DEFAULT 1, created_at/updated_at TEXT DEFAULT (datetime('now'))`), `APP_TABLES`
  리스트(556행 부근)에 `"activity_groups"` 추가. 새 테이블 추가라 `SCHEMA_VERSION`
  올릴 필요 없음(v16 주석 참조 — `create_tables()`의 `CREATE TABLE IF NOT EXISTS`로
  충분, `migrate_db()`에 버전 분기 안 씀). (2) `src/utils/dedup.py`의
  `assign_group_id()`(97행) — 매칭 성공 시(`UPDATE activity_summaries SET
  matched_group_id ...` 직후) `activity_groups`에 upsert 추가: `primary_source`는
  06 §D2가 명시한 정적 우선순위(garmin=1 > intervals=2 > strava=3 > runalyze=4,
  나머지는 알파벳순)로 두 후보(`activity_id`, `cand_id`)의 source를 비교해 결정 —
  `v_canonical_activities`(`src/db_setup.py`, `_DDL_CANONICAL_VIEW`)가 쓰는 것과 동일
  기준이어야 함(정합성 AO-3). 신규 그룹이면 INSERT, 기존 그룹 재사용이면 UPDATE
  member_count/updated_at. (3) `scripts/backfill_activity_groups.py` 신규 — 06 §D2의
  백필 SQL(`INSERT OR IGNORE ... GROUP BY matched_group_id`)을 그대로 쓰는 스크립트.
  **이 스크립트를 실제로 실행하지는 마세요** — 실 사용자 DB에 쓰는 건 범위 밖(별도
  승인 필요), 이번엔 스크립트 작성 + `tmp_path` 픽스처로 만든 임시 DB에 대한 테스트
  통과까지만. 테스트: `test_group_master_created_on_match`(두 소스 매칭 시
  `activity_groups` 행 자동 생성 — 06 §D2 테스트 요건 그대로) 등을
  `tests/test_dedup.py`에, 백필 스크립트 테스트는 `tests/test_backfill_activity_
  groups.py` 신규.
  <!-- autopilot: {"stage": "done", "mode": "auto", "attempts": 1, "deps": [], "kind": "code", "scope": ["src/db_setup.py", "src/utils/dedup.py", "scripts/backfill_activity_groups.py", "tests/test_dedup.py", "tests/test_backfill_activity_groups.py", "tests/test_db_setup.py"], "verify": ["python3 -m pytest tests/test_dedup.py tests/test_db_setup.py tests/test_backfill_activity_groups.py -q", "python3 scripts/check_data_consistency.py"]} -->

- **[P7-IMPL-D1-REST-UC]** D1 나머지 — utrs/cirs 자식 메트릭 저장만(race_readiness/rri는
  제외 — `DECISIONS.md`의 `P7-IMPL-D1-REST-RRI` 참조, 06 문서 원안이 "RRI의 자식 =
  UTRS/CIRS"라 적어둔 게 이번에 utrs/cirs 자신도 각자 부모가 되는 것과 충돌해서 사용자
  확인 전까지 보류). `src/metrics/base.py`의 `CalcResult.parent_metric_name`과
  `src/metrics/engine.py`의 `_save_results()`(`name_to_id` 누적 로직)는 `P7-IMPL-D1`에서
  이미 만들어져 있음 — PMC와 동일 패턴 재사용, 배선 변경 없음. **구현**: (1)
  `src/metrics/utrs.py`의 `UTRSCalculator.compute()` — 현재 `components` dict(계산된
  body_battery/tsb/sleep/hrv/stress 정규화값, 0~100)를 `json_val`에만 넣고 있음.
  `components`에 실제로 들어간 키마다(가용 데이터만, 조건부) `self._result(value=...,
  parent_metric_name="utrs")`를 추가로 만들어 반환 리스트에 append — 자식 메트릭 이름은
  `utrs_body_battery`/`utrs_tsb`/`utrs_sleep`/`utrs_hrv`/`utrs_stress`(기존 공유 메트릭인
  진짜 `tsb`/`hrv_weekly_avg`와 이름 겹치지 않게 `utrs_` 접두사 필수 — UTRS 자신이
  정규화한 파생값이지 원본 복사가 아님). UTRS 본체 result가 리스트 0번째여야 함(부모가
  먼저 나와야 `_save_results()`가 참조 가능, PMC의 ctl 순서와 동일 이유). (2)
  `src/metrics/cirs.py`의 `CIRSCalculator.compute()` — 동일 패턴, `components`(acwr/lsi/
  consecutive/fatigue)를 `cirs_acwr`/`cirs_lsi`/`cirs_consecutive`/`cirs_fatigue`
  자식으로. 테스트는 `P7-IMPL-D1`의 `tests/test_engine.py::test_ramp_rate_parent_metric_
  id_links_to_ctl` 패턴 그대로 — 공개 함수(`run_daily_metrics` 등)로 전체 파이프라인
  검증, 저장된 자식 행의 `parent_metric_id`가 같은 날짜 utrs/cirs 행의 id와 같은지 확인.
  `tests/test_utrs.py`/`tests/test_cirs.py`에 단위 테스트(어떤 컴포넌트가 가용/불가용일
  때 자식 개수가 맞게 달라지는지)도 추가.
  <!-- autopilot: {"stage": "done", "mode": "auto", "attempts": 1, "deps": [], "kind": "code", "scope": ["src/metrics/utrs.py", "src/metrics/cirs.py", "tests/test_utrs.py", "tests/test_cirs.py", "tests/test_engine.py"], "verify": ["python3 -m pytest tests/test_utrs.py tests/test_cirs.py tests/test_engine.py -q", "python3 scripts/check_data_consistency.py"]} -->

- **[P7-IMPL-METRIC-BREAKDOWN]** `metrics_service.get_metric_breakdown()` + `GET
  /api/v1/library/metrics/:slug` — `DECISIONS.md`의 `P7-IMPL-D1-REST-RRI` 결정(2026-09-22)
  반영: children(소유 분해, `parent_metric_id`)과 inputs(입력 사용, Calculator의
  `requires`) 둘 다 조립. `06-data-layer-extensions.md` D1 "2026-09-22 정정",
  `04-component-catalog.md` C3 `MetricBreakdownData` 참조. 스텁 파일 이미 존재
  (`src/services/metrics_service.py`, D5가 자리만 만들어둠).
  **구현**: (1) `metrics_service.get_metric_breakdown(conn, scope_type: str, scope_id:
  str, slug: str) -> dict | None`. slug의 자기 자신 행은
  `db_helpers.get_primary_metric(conn, scope_type, scope_id, slug)`(이미 존재, 재사용)
  로 조회 — 없으면 None 반환(→ API가 404). (2) children: `SELECT * FROM metric_store
  WHERE scope_type=? AND scope_id=? AND parent_metric_id=? ORDER BY id`(자기 자신의
  row id로 조회) — 각 항목 label은 `src.utils.metric_registry.METRIC_REGISTRY[name].
  description`(없으면 metric_name 그대로), weight는 이번엔 생략(스키마상 optional,
  `undefined`로 둠 — Calculator의 WEIGHTS dict가 컴포넌트 로컬 변수라 지금은 자식
  이름으로 역매핑할 공개 경로가 없음, 후속 과제로 남김). (3) inputs: `src.metrics.
  engine.ALL_CALCULATORS`에서 `calc.name == slug`인 Calculator를 찾아(없으면 빈 리스트
  — 예: slug가 children처럼 소유 파생값이면 자기 자신의 requires가 없음) 그
  `calc.requires`의 각 이름마다 `get_primary_metric(conn, scope_type, scope_id, name)`
  조회(None이면 스킵 — 데이터 없음, coding-rules.md 그레이스풀 처리), label은 동일하게
  METRIC_REGISTRY 조회, weight는 항상 None. (4) 응답 dict는 `MetricBreakdownData`
  형태(`slug`,`label`,`value`,`unit`,`provider`,`confidence`,`children`,`inputs`) —
  `formula`/`computedAt`/`version`/`prevValue`는 이번엔 생략(옵셔널 필드, 후속 과제).
  (5) `src/api/routes_library.py`에 `GET /api/v1/library/metrics/<slug>` 라우트 추가
  — 쿼리 파라미터 `scope_type`(기본 `"daily"`), `scope_id`(필수, 없으면
  `api_error("INVALID_PARAM", ...)`) — 기존 `get_library_activity_detail` 패턴
  그대로(`db_path()`, `sqlite3.connect`, `api_ok`/`api_error`). 테스트:
  `tests/test_metrics_service.py`(신규) — CTL→ramp_rate(children, 이미 PMC로 연결돼
  있음)와 RRI→cirs(inputs, 이번에 새로 조립)를 각각 실제 파이프라인
  (`run_daily_metrics`)으로 만든 뒤 `get_metric_breakdown()` 결과 검증. slug 없는 경우
  None 반환도 테스트. `tests/test_api_library.py`에 라우트 테스트(200/404/scope_id
  누락 400) 추가.
  <!-- autopilot: {"stage": "done", "mode": "auto", "attempts": 1, "deps": [], "kind": "code", "scope": ["src/services/metrics_service.py", "src/api/routes_library.py", "tests/test_metrics_service.py", "tests/test_api_library.py"], "verify": ["python3 -m pytest tests/test_metrics_service.py tests/test_api_library.py -q", "python3 scripts/check_data_consistency.py"]} -->

- **[P7-IMPL-PROVIDER-COMPARISON]** `provider_comparison_service.get_provider_comparison()`
  + `GET /api/v1/library/activities/:id/providers` — `03c-library.md` §3-G-2(활동별
  비교)만 구현, 3-G-1(정체성 매트릭스)은 LATER(스코프 축소 이유는 `DECISIONS.md`의
  `[P7-DESIGN-7B-API]` 항목 참조, 이번 착수 전 필독). `activity_service.py`는 이미
  283/300줄이라 새 파일 `src/services/provider_comparison_service.py`에 구현(300줄
  캡, coding-rules.md).
  **구현**: (1) `get_provider_comparison(conn: sqlite3.Connection, activity_id: int,
  discrepancy_threshold: float = 5.0) -> dict | None`. `activity_summaries`에서
  `id=activity_id` 행 조회 — 없으면 None(→ API 404). `matched_group_id`가 없으면
  `{"mode": "activity", "activity_id": activity_id, "state": "single_provider",
  "rows": []}` 즉시 반환(비교할 형제가 없음, 04-component-catalog.md C4의
  `single_provider` 상태). (2) 있으면 `WHERE matched_group_id=?`로 형제 행 전체
  조회, `activity_groups`(D2, `src/db_setup.py` `_DDL_ACTIVITY_GROUPS`)에서
  `SELECT primary_source FROM activity_groups WHERE group_id=?`로 그룹 대표 소스
  확보. (3) raw 메트릭 행: `src.utils.metric_registry.METRIC_REGISTRY`를 순회해
  `storage=="activity_summary" and scope=="activity" and category!="meta"`인
  항목만(위경도·이름·device_name 등 메타 컬럼 제외, distance_m/avg_hr/avg_cadence
  등 33개 중 20개 정도가 해당) 각 형제의 `source` 컬럼을 키로 값을 모음 — 형제
  전원이 None이면 그 행 자체를 스킵. (4) semantic 메트릭 행: `metric_store`는
  provider마다 **자기 소스의 activity_summaries.id에 스코프**된다(그룹의 대표 id가
  아님 — `src/sync/extractors/base.py`의 `_metric()`은 category만 정하고 scope_id는
  sync 파이프라인이 그 provider 활동 행 id로 지정, 이미 확인함). 그래서 `WHERE
  scope_type='activity' AND scope_id IN (형제 id 전체)`로 한 번에 조회해야 함 —
  `activity_service._build_semantic_groups()`(단일 scope_id만 봄)를 그대로 재사용하면
  안 되고, `src.utils.metric_groups.SEMANTIC_GROUPS`를 직접 순회해 그룹당 1개
  `ComparisonRow`로 평탄화하는 새 로직 작성(`slug=group_name`,
  `label=display_name`). (5) 각 행을 `ComparisonRow` 형태로 조립(04 C3
  아님 C4 `MetricBreakdownData`와 혼동 금지 — 04-component-catalog.md C4 섹션의
  `ComparisonRow`/`ComparisonCell` 참조): `values`는 이 활동 그룹에 등장하는 전체
  provider 집합(형제들의 `source` 합집합 + semantic 행에 등장한 provider 문자열)을
  키로 하는 dict — 값이 없는 provider는 `{"value": null, "available": false}`,
  있으면 `{"value": ..., "available": true}`(프론트가 모든 행에서 같은 컬럼 순서로
  렌더링할 수 있게). `unit`/`label`은 raw는 METRIC_REGISTRY, semantic은
  `display_name`. (6) `discrepancy`: 해당 행에 `available=true`인 숫자값이 2개
  이상일 때만 계산 — `maxDiff=max-min`, `maxDiffPct=maxDiff/min*100`(min이 0이면
  `maxDiff/max*100`, 그마저 0이면 `maxDiffPct=0.0`), `severity="warning" if
  maxDiffPct > discrepancy_threshold else "info"`, `detected = maxDiffPct >
  discrepancy_threshold`. 텍스트값(text_value)만 있는 semantic 행은 discrepancy
  생략. (7) `preferredProvider`/`primaryReason`: 이 행의 provider 중 정확히 1개뿐이고
  그게 `"runpulse"`로 시작하면 `ruleType="runpulse_always"`,
  `rule="RunPulse — 자체 산출"`. 아니면 `primary_source`가 이 행의 `available`
  provider 중에 있으면 그걸 사용, 없으면 `src.utils.dedup._SOURCE_PRIORITY`로 이
  행에 실제 등장한 provider 중 우선순위 최고를 골라 대체 — 어느 쪽이든
  `ruleType="static_priority"`, `rule`은 `_SOURCE_PRIORITY` 순서대로 " > "로 이어
  붙인 문자열(이 행에 실제 등장한 provider만, 예: "소스 우선순위 (garmin >
  strava)"). 이 행에 non-runpulse provider가 하나도 없으면 `primaryReason=None`.
  (8) 최종 반환: `{"mode": "activity", "activity_id": ..., "state": "loaded",
  "rows": [...]}` (표 전체 discrepancy 강조는 프론트가 각 행의 `discrepancy.
  severity`로 처리 — 04 C4의 `discrepancy` 상태값은 별도 top-level state로 만들지
  않음, 이번 스코프 축소). (9) `src/api/routes_library.py`에 `GET /api/v1/library/
  activities/<int:activity_id>/providers` 라우트 추가 — 기존 `get_library_
  activity_streams` 패턴 그대로(`db_path()`, `sqlite3.connect`, `api_ok`/
  `api_error`, 404 if None), 파일 최상단 docstring에도 새 라우트 경로 한 줄 추가.
  쿼리 파라미터 `discrepancy_threshold`(선택, float, 기본 5.0). 테스트:
  `tests/test_provider_comparison_service.py`(신규) — `tests/test_activity_
  service.py`의 garmin+strava 동일 `matched_group_id` fixture 패턴 재사용+
  `activity_groups` 행 직접 INSERT(D2 헬퍼 `_upsert_activity_group()` 또는 원시
  INSERT 둘 다 가능). 케이스: raw 메트릭(avg_hr) 2-provider 비교 + discrepancy
  계산, `primary_source` 기반 preferredProvider, 형제 없는 solo 활동 →
  `single_provider`/`rows=[]`, 존재하지 않는 activity_id → None,
  `SEMANTIC_GROUPS`의 한 그룹(예: `training_load` — training_load_score/intervals,
  training_load/garmin, suffer_score/strava, hrss/runpulse:formula_v1 조합)을
  형제별로 다른 id에 `metric_store` INSERT한 뒤 하나의 행으로 평탄화되는지, RunPulse
  단독 값 행의 `ruleType=="runpulse_always"`. `tests/test_api_library.py`에 라우트
  테스트(200/404) 추가.
  <!-- autopilot: {"stage": "done", "mode": "auto", "attempts": 1, "deps": [], "kind": "code", "scope": ["src/services/provider_comparison_service.py", "src/api/routes_library.py", "tests/test_provider_comparison_service.py", "tests/test_api_library.py"], "verify": ["python3 -m pytest tests/test_provider_comparison_service.py tests/test_api_library.py -q", "python3 scripts/check_data_consistency.py"]} -->

- **[P7-IMPL-MILESTONES]** `milestones` 테이블 + `milestone_service.py` — 마일스톤
  탐지·저장(03a-today.md 1-D). 설계 근거는 `DECISIONS.md`의 `[P7-DESIGN-7B-API]`
  "get_today_narrative() + milestones 테이블" 항목 참조(착수 전 필독, plan mode로
  승인받은 설계). **구현**: (1) `src/db_setup.py`에 `_DDL_MILESTONES` 추가 —
  `id INTEGER PRIMARY KEY AUTOINCREMENT`, `type TEXT NOT NULL`
  (`'distance_threshold'|'pb'|'metric_recompute'`), `date TEXT NOT NULL`,
  `title TEXT NOT NULL`, `detail TEXT`, `activity_id INTEGER`,
  `metric_name TEXT`, `old_value REAL`, `new_value REAL`,
  `created_at TEXT DEFAULT (datetime('now'))`,
  `UNIQUE(type, date, title)`(같은 마일스톤 중복 방지 — 매 sync마다 재탐지해도
  `INSERT OR IGNORE`로 안전, D2 백필과 동일 발상). `PIPELINE_TABLES`(D2의
  `activity_groups`처럼 파생 데이터 — `APP_TABLES` 아님)에 `"milestones"` 추가,
  `SCHEMA_VERSION` 17→18(`# v0.3.8: milestones 테이블 신설` 주석), `migrate_db()`
  docstring에 `v18: milestones 테이블 신설 — CREATE TABLE IF NOT EXISTS만으로
  충분.`(D2의 `v17` 항목과 동일 패턴, 코드 마이그레이션 불필요). **D2 때 놓친
  실수 반복 금지**: `tests/test_phase1_schema.py`에 `SCHEMA_VERSION`/`ver` 하드코딩
  assert가 있으면 18로 갱신(grep으로 먼저 확인). (2)
  `src/services/milestone_service.py`(신규) — 쓰기 함수(dedup.py D2와 같은 성격,
  today_service.py의 읽기 전용 원칙과는 별개 모듈). `detect_and_store_milestones
  (conn: sqlite3.Connection, start_date: str, end_date: str) -> list[dict]`(새로
  삽입된 마일스톤만 반환): (a) **distance_threshold** — `v_canonical_activities`
  (`src/db_setup.py` `_DDL_CANONICAL_VIEW`, dedup 완료 뷰)에서 `start_date` 미만
  누적거리 합과 `end_date` 이하 누적거리 합을 각각 구해, 그 사이에 새로 넘은
  100km(100000m) 배수마다 하나씩 — `title=f"누적 {n*100}km 돌파"`, `date`는
  실제로 그 배수를 넘긴 활동의 `start_time` 날짜(범위 내 활동을 `start_time`
  오름차순으로 순회하며 누적하다 넘는 시점 판정). (b) **pb** — 범위 내 활동 중
  레이스로 태그된 것만: `metric_store`에 `metric_name='workout_type_classified'
  AND text_value='race'`인 행이 있거나 `activity_summaries.name`에 "레이스"/
  "대회"/"Race" 포함(이 판정 기준은 `src/ai/tool_exec_context.py`의
  `_exec_get_race_history`와 동일 조건 — import는 안 함, ai/ 쪽 헬퍼를 services/
  에서 끌어오지 않음, 조건만 동일하게 복사). 이 활동들을 `distance_m` 기준
  버킷(5k: 4500~5500m, 10k: 9000~11000m, half: 20000~22500m, marathon:
  40000~43000m)으로 분류, 각 활동의 `avg_pace_sec_km`가 같은 버킷의 그 이전
  전체 활동(범위 밖 과거 포함, `start_time <` 해당 활동)보다 작으면(더 빠르면)
  PB — `title=f"{버킷 한글명} PB"`(5k→"5K", 10k→"10K", half→"하프마라톤",
  marathon→"풀마라톤"), `activity_id`에 연결, `detail`에 완주 시간. 버킷 내 이전
  활동이 하나도 없으면(첫 완주) PB로 치지 않음(비교 대상 없음). 두 탐지 모두
  `INSERT OR IGNORE INTO milestones (...)`로 저장. `get_recent_milestones(conn:
  sqlite3.Connection, limit: int = 10) -> list[dict]` — `ORDER BY date DESC, id
  DESC LIMIT ?`, 읽기 전용. (3) `src/utils/db_helpers.py`의 `upsert_metric()`
  재계산 감지 — 함수 맨 앞, UPSERT 실행 전에 `metric_name`이
  `_MILESTONE_TRACKED_METRICS = {"ctl", "runpulse_vdot", "race_pred_5k_sec",
  "race_pred_10k_sec", "race_pred_half_sec", "race_pred_marathon_sec", "rri"}`에
  있을 때만: 기존 행(`SELECT numeric_value, algorithm_version FROM metric_store
  WHERE scope_type=? AND scope_id=? AND metric_name=? AND provider=?`) 조회,
  있고 `algorithm_version`이 새로 들어오는 값과 다르고 `numeric_value`도 상대
  오차 1% 초과로 다르면 `milestones`에 `type='metric_recompute'` 행 INSERT OR
  IGNORE(`title=f"{metric_name} 재계산"`, `detail=f"{old_version}→{new_version}
  적용"`, `old_value`/`new_value` 채움, `date`=오늘). **allow-list 밖 메트릭은
  이 SELECT 자체를 안 함**(전체 메트릭에 걸면 sync 성능 저하 — 이번 설계의 핵심
  제약, 반드시 지킬 것). (4) `src/api/routes_today.py`에 `GET /api/v1/today/
  milestones` 라우트 추가(쿼리 파라미터 `limit`, 기본 10) — 기존 `get_today`
  패턴 그대로. (5) `src/sync.py`의 `main()` — `metrics_engine.run_for_date_range()`
  호출 성공 직후, 같은 try/except 블록 안(로그만 남기고 sync 자체는 실패
  처리 안 함, coding-rules.md "sync 중단 금지")에
  `milestone_service.detect_and_store_milestones(conn, start_date, end_date)`
  호출 추가. 테스트: `tests/test_milestone_service.py`(신규) — 100km 문턱을
  넘는 활동 시퀀스에서 정확히 그 활동 날짜로 마일스톤 생성, 레이스 태그 활동이
  이전 기록보다 빠르면 PB/느리면 미생성, 같은 범위로 두 번 호출해도 중복 삽입
  안 됨(`INSERT OR IGNORE` 검증), `upsert_metric()`으로 allow-list 메트릭의
  `algorithm_version`을 바꿔 재삽입하면 `metric_recompute` 마일스톤 생성·
  allow-list 밖 메트릭은 생성 안 됨. `tests/test_api_today.py`(또는 없으면
  적절한 기존 today API 테스트 파일)에 `/today/milestones` 라우트 테스트 추가.
  <!-- autopilot: {"stage": "done", "mode": "auto", "attempts": 1, "deps": [], "kind": "code", "scope": ["src/db_setup.py", "src/services/milestone_service.py", "src/utils/db_helpers.py", "src/api/routes_today.py", "src/sync.py", "tests/test_milestone_service.py", "tests/test_db_setup.py"], "verify": ["python3 -m pytest tests/test_milestone_service.py tests/test_db_setup.py -q", "python3 scripts/check_data_consistency.py"]} -->

- **[P7-IMPL-TODAY-NARRATIVE]** `today_service.get_today_narrative()` +
  `GET /api/v1/today/narrative` — `P7-IMPL-MILESTONES` 선행 필요(`get_recent_
  milestones()`를 컨텍스트에 씀). 설계 근거는 `DECISIONS.md`의
  `[P7-DESIGN-7B-API]` "get_today_narrative() + milestones 테이블" 항목 참조.
  **구현**: (1) `today_service.get_today_narrative(conn: sqlite3.Connection,
  date: str | None = None, config: dict | None = None) -> dict`. 컨텍스트 조립:
  `get_today_status(conn, date)`로 `training_status`(ctl 포함) 확보, 이번 달
  1일의 ctl과 비교해 변화량 계산(월초 데이터 없으면 변화량 생략), `v_canonical_
  activities`에서 이번 달 누적거리·활동수, `daily_wellness`에서 최근 7일
  `sleep_score` 평균과 그 이전 7일 평균 비교(추세 문구용, 데이터 부족하면
  생략), `milestone_service.get_recent_milestones(conn, limit=5)`. (2) AI
  우선 생성: `from src.ai.chat_engine import _build_chat_provider_chain,
  _call_provider` + `from src.ai.chat_engine import get_ai_provider`(이미
  `chat_engine.py`에 있음) — `chain = _build_chat_provider_chain(get_ai_
  provider(config), config)`로 순서 확보, 프롬프트는 위 컨텍스트 수치를 나열한
  뒤 "위 데이터만 근거로 이번 달 훈련 흐름을 한국어 2~3문장으로 요약하라.
  데이터에 없는 수치는 언급하지 마라." 같은 지시문(수치 환각 방지가 핵심 —
  반드시 프롬프트에 명시). `for prov in chain: text = _call_provider(prov,
  prompt, config); if text: break`(실패하면 다음 provider, `_call_provider`가
  이미 실패 감지·None 반환 처리함, 재구현 불필요). (3) 전체 실패(text가 계속
  None, chain이 비어 있거나 전부 실패) 시 규칙 기반 fallback — `today_service.py`
  의 `_TSB_THRESHOLDS` 딕셔너리 리스트 패턴을 참고해 CTL 증감·이번 달 거리·수면
  추세를 조건문으로 엮은 한국어 템플릿 문장 조립(예: "이번 달 { }km, CTL {a}→{b}
  ({+-N}) { 수면 추세 문구 }." — 03a-today.md 1-A' 스텁 문구의 실데이터 확장판
  수준, 새 디자인 불필요). (4) 반환: `{"date": ..., "text": ..., "source":
  "ai"|"rule", "evidence": [{"type":"metric","metric":...,"value":...,
  "label":...}, ...](`get_today_briefing()`과 동일 형태 재사용 — ctl/거리/수면
  중 실제로 언급한 것만), "milestones": [...] }`. (5)
  `today_service.get_today_milestones(conn: sqlite3.Connection, limit: int =
  20) -> list[dict]` — `milestone_service.get_recent_milestones()` 그대로
  노출하는 얇은 wrapper(1-D 패널용, `P7-IMPL-MILESTONES`가 만든 API와 별개로
  서비스 레이어에도 한 번 더 노출 — 03a 문서가 Today L2 조회를 today_service
  하나로 묶어서 기대함). (6) `src/api/routes_today.py`에 `GET /api/v1/today/
  narrative` 라우트 — `config = load_config(user_id=get_current_user_id())`로
  서버에서 로드(요청 인자로 API 키 등 안 받음 — 보안), `routes_coach.py`의
  `load_config` 사용 패턴 그대로. 테스트: `tests/test_today_service.py`
  확장 — **AI provider 미설정(config=None 또는 빈 dict) 상태에서도 규칙 기반
  fallback으로 정상 응답**(반드시 테스트, 실서버에 AI 키 없을 수 있음),
  `source` 필드가 상황에 맞게 "ai"/"rule"로 나뉘는지(AI 성공 케이스는
  `_call_provider`를 monkeypatch로 목업), evidence에 데이터 없는 항목이
  안 섞여 들어가는지. `tests/test_api_today.py`에 `/today/narrative` 라우트
  테스트 추가.
  <!-- autopilot: {"stage": "done", "mode": "auto", "attempts": 1, "deps": ["P7-IMPL-MILESTONES"], "kind": "code", "scope": ["src/services/today_service.py", "src/api/routes_today.py", "tests/test_today_service.py"], "verify": ["python3 -m pytest tests/test_today_service.py -q", "python3 scripts/check_data_consistency.py"]} -->

- **[P7-IMPL-7B-TODAY-L2]** SvelteKit만 — Flask API는 전부 이미 구현·테스트·병합
  완료(`P7-IMPL-METRIC-BREAKDOWN`/`P7-IMPL-MILESTONES`/`P7-IMPL-TODAY-NARRATIVE`).
  **착수 전 필독**: `DECISIONS.md`의 `[P7-IMPL-7B-TODAY-L2]` 항목 — C7
  `<TimelineNarrative>` 전체와 C3의 문서 스펙 그대로는 실제 API 응답보다 커서
  둘 다 축소해서 구현한다, 아래 스펙이 축소된 버전임.
  `frontend/`의 기존 패턴(`P7-IMPL-SVELTE`/`-2A`/`-2B`) 그대로 따를 것 —
  `$lib/api/client.ts`의 `apiFetch()`(이미 `.data` unwrap함), `$lib/provider.ts`,
  `$lib/format.ts`.
  **구현**: (1) `frontend/src/lib/types/index.ts`에 타입 추가 —
  `MetricBreakdownNode { name: string; label: string; value: number | string | null;
  unit: string; provider: ProviderKey | null; confidence: number | null }`(문서의
  `slug`/`weight`/`collapsible`은 없음 — 실제 API 응답 그대로), `MetricBreakdownData
  { slug: string; label: string; value: number | string | null; unit: string;
  provider: ProviderKey | null; confidence: number | null; children:
  MetricBreakdownNode[]; inputs: MetricBreakdownNode[] }`,
  `MilestoneEntry { id: number; type: 'distance_threshold' | 'pb' |
  'metric_recompute'; date: string; title: string; detail: string | null;
  activity_id: number | null }`, `NarrativeResponse { date: string; text: string;
  source: 'ai' | 'rule'; evidence: BriefingEvidence[]; milestones:
  MilestoneEntry[] }`(`BriefingEvidence`는 이미 존재하는 타입 재사용). (2)
  `frontend/src/lib/api/metrics.ts`(신규) — `getMetricBreakdown(slug: string,
  scopeType: string, scopeId: string): Promise<MetricBreakdownData>` →
  `apiFetch<{metric: MetricBreakdownData}>(...).then(r => r.metric)` 형태(실제
  응답이 `{"metric": {...}}`로 감싸져 있음, `GET /api/v1/library/metrics/<slug>
  ?scope_type=<scopeType>&scope_id=<scopeId>`). (3) `frontend/src/lib/api/
  today.ts`에 `getTodayNarrative(): Promise<NarrativeResponse>` 추가 —
  `apiFetch<NarrativeResponse>('/today/narrative')`(이 엔드포인트는 `{data:
  {...}}`만 감싸고 추가 래핑 없음 — `routes_today.py`의 `api_ok(result)` 그대로
  확인). (4) `frontend/src/lib/components/MetricBreakdown.svelte`(신규, C3
  축소판) — props: `slug: string`, `scopeType: string`, `scopeId: string`,
  `onClose: () => void`, `onDrillInput?: (slug: string) => void`. 마운트 시
  `getMetricBreakdown()` 호출(loading/error 상태 처리 — coding-rules.md
  "데이터 없음 시 에러 대신 UI" 그대로, catch해서 "계산 데이터를 불러올 수
  없습니다" 표시). 레이아웃: 헤더(`← [있으면] [label] [×닫기]` — `onClose` 호출),
  본문에 현재값+unit+provider 배지+confidence(있으면), children이 있으면
  "구성 요소" 섹션(평평한 목록, 각 항목 label/value/unit/provider만 — 펼침
  불가, `collapsible` UI 없음), inputs가 있으면 "기반 데이터" 섹션(각 항목
  탭하면 `onDrillInput?.(item.name)` 호출 — 부모가 스택에 push해서 재귀
  마운트, 이 컴포넌트 자신은 재귀를 모름). 화면 너비 무관하게 이번엔 모바일
  풀스크린 시트 하나만(데스크탑 우측 패널 분기는 범위 밖 — 04 스펙의
  `mode` prop 자동판단 생략, 항상 시트). (5) `frontend/src/routes/today/
  +page.svelte` 수정: `breakdownStack = $state<string[]>([])`(빈 배열=닫힘,
  마지막 요소=현재 열린 slug) 추가. utrs/cirs/tsb `MetricCell` 3개
  `drillable={false}` → `drillable={true}` + `onDrill={({slug}) =>
  breakdownStack = [slug]}`로 변경(주석 "7a: MetricBreakdown 없어서 false"
  삭제). `{#if breakdownStack.length > 0}` 블록에서 최상단 오버레이로
  `<MetricBreakdown slug={breakdownStack.at(-1)} scopeType="daily"
  scopeId={status.date} onClose={() => breakdownStack = []}
  onDrillInput={(slug) => breakdownStack = [...breakdownStack, slug]} />`
  렌더(뒤로가기는 이번엔 닫기만 지원 — 스택 pop으로 되돌아가는 "←" 버튼은
  범위 밖, `onClose`가 스택 전체를 비움). (6) L2 섹션(140~147줄, "흐름·훈련·
  성장" 스텁) 전체 교체 — `+page.ts`의 `load()`에서 `getTodayNarrative()`도
  같이 호출(`Promise.all`로 기존 `getToday()`와 병렬, 실패해도 Today 전체가
  깨지면 안 됨 — try/catch로 narrative만 null 처리 가능하게). 페이지에서
  `text`를 단락으로 렌더, `evidence`를 `<EvidenceQuote>` 반복 렌더(기존
  `adaptEvidence()` 재사용 가능 — `BriefingEvidence` 형태 동일), `milestones`를
  타입별 아이콘(🎯 distance_threshold, 🏃 pb, 🔄 metric_recompute) + 날짜 +
  title 목록으로. narrative 로딩 실패/null이면 기존 스텁 문구를 fallback으로
  유지(완전 삭제 금지 — coding-rules.md 그레이스풀 처리). **범위 밖**(문서에
  명시): `<TimelineNarrative>`(C7) 마크다운/차트 파싱, "이번 달 전체 이야기"
  확장 패널(1-C), 전체 마일스톤 패널(1-D, `get_today_milestones()`는 이번엔
  narrative 응답의 `milestones`로 충분 — 별도 API 호출 안 함), 데스크탑
  우측 패널 분기, MetricBreakdown 뒤로가기(스택 pop UI).
  <!-- autopilot: {"stage": "done", "mode": "auto", "attempts": 1, "deps": [], "kind": "code", "scope": ["frontend/src/lib/types/index.ts", "frontend/src/lib/api/metrics.ts", "frontend/src/lib/api/today.ts", "frontend/src/lib/components/MetricBreakdown.svelte", "frontend/src/routes/today/+page.svelte", "frontend/src/routes/today/+page.ts"], "verify": ["cd frontend && npm install && npm run check && npm run build"]} -->

- **[P7-IMPL-7B-PROVIDER-UI]** SvelteKit만 — `<ProviderComparison>`(C4) 신규
  컴포넌트, 백엔드(`get_provider_comparison()`, `P7-IMPL-PROVIDER-COMPARISON`)는
  이미 병합돼 있음(활동별 비교, 03c §3-G-2만 — §3-G-1 정체성 매트릭스는
  `P7-IMPL-PROVIDER-MATRIX`로 LATER). 문서(03c §3-G)는 `/library/providers`를
  자체 활동 피커가 있는 독립 화면으로 그리지만, 이번엔 그 피커를 새로 만들지
  않고 **이미 activity_id가 URL에 있는 활동 상세 페이지의 하위 라우트**로
  붙인다(`frontend/src/routes/library/[id]/providers/`) — 독립 `/library/
  providers` 화면(+피커, 매트릭스 모드 토글)은 `P7-IMPL-7B-LIBRARY`(NEXT)에서.
  **구현**: (1) `frontend/src/lib/types/index.ts`에 타입 추가 — `ComparisonCell
  { value: number | string | null; available: boolean }`,
  `PrimaryReason { provider: ProviderKey; rule: string; ruleType:
  'static_priority' | 'runpulse_always' }`(`P7-IMPL-PROVIDER-COMPARISON` 리뷰
  때 preferredProvider/primaryReason을 분리한 실제 응답 형태 그대로 —
  `primaryReason`은 이 객체 자체이거나 null, `preferredProvider`는 별도
  `ProviderKey | null` 필드), `ComparisonRow { slug: string; label: string;
  unit: string | null; values: Record<string, ComparisonCell>; discrepancy:
  { detected: boolean; maxDiff: number; maxDiffPct: number; severity: 'info' |
  'warning' } | null; preferredProvider: ProviderKey | null; primaryReason:
  PrimaryReason | null }`, `ProviderComparisonData { mode: 'activity';
  activity_id: number; state: 'loaded' | 'single_provider'; rows:
  ComparisonRow[] }`(문서의 `values: Record<ProviderKey,...>`가 아니라
  `Record<string,...>`로 — raw 메트릭 행의 키는 활동의 `source` 컬럼값 그대로라
  `ProviderKey` 유니온을 벗어날 수 있음, `provider_comparison_service.py`의
  `_ordered_providers()` 참조). (2) `frontend/src/lib/api/providers.ts`(신규)
  — `getProviderComparison(activityId: number, threshold?: number):
  Promise<ProviderComparisonData>` → `apiFetch<{comparison:
  ProviderComparisonData}>('/library/activities/' + activityId + '/providers'
  + (threshold ? '?discrepancy_threshold=' + threshold : '')).then(r =>
  r.comparison)`. (3) `frontend/src/lib/components/ProviderComparison.svelte`
  (신규) — props: `data: ProviderComparisonData`. `state === 'single_provider'`
  면 "비교할 추가 소스가 없습니다" 문구만(04 스펙 그대로). 아니면 테이블 렌더:
  헤더 행 = `data.rows`에 등장하는 전체 provider 키 합집합(각 행의 `values`
  키를 순회해 합집합 구성, `$lib/provider.ts`의 `providerLabel()`로 헤더 표시)
  + "대표값" 컬럼. 각 행: `label`, provider별 셀(`available`이면 값+unit,
  아니면 "—"), 대표값 컬럼엔 `preferredProvider`가 있으면 `★` +
  `providerLabel(preferredProvider)`(탭/hover 시 `primaryReason.rule`을
  타이틀 속성이나 작은 텍스트로 노출 — P3 투명성), `discrepancy?.detected`면
  행 배경 amber 톤 + `⚠` 배지 + `maxDiffPct.toFixed(1)+'%'`. 값 포맷은
  `unit`이 있으면 `value + unit` 그대로 표시(복잡한 단위 변환 없음 — `$lib/
  format.ts`의 기존 포맷터는 특정 필드 전용이라 여기선 안 씀). (4)
  `frontend/src/routes/library/[id]/providers/+page.svelte` +
  `+page.ts`(신규) — `+page.ts`의 `load({params})`에서 `getProviderComparison
  (Number(params.id))` 호출(실패 시 `errorMessage` 패턴은 기존
  `library/[id]/+page.ts` 그대로 재사용). 페이지 상단에 "← 활동으로" 링크
  (`{base}/library/{id}`), `<ProviderComparison data={...}>` 렌더. (5)
  `frontend/src/routes/library/[id]/+page.svelte`(기존 파일, "핵심 메트릭"
  섹션과 "스트림 데이터" 섹션 사이)에 링크 추가: "[Provider 비교 보기 →]"
  (`{base}/library/{id}/providers`). 테스트는 이 저장소 프론트 관례상 별도
  단위 테스트 없음(`npm run check`/`npm run build`가 검증 전부, SVELTE-2A/2B와
  동일).
  <!-- autopilot: {"stage": "done", "mode": "auto", "attempts": 1, "deps": [], "kind": "code", "scope": ["frontend/src/lib/types/index.ts", "frontend/src/lib/api/providers.ts", "frontend/src/lib/components/ProviderComparison.svelte", "frontend/src/routes/library/[id]/providers/+page.svelte", "frontend/src/routes/library/[id]/providers/+page.ts", "frontend/src/routes/library/[id]/+page.svelte"], "verify": ["cd frontend && npm install && npm run check && npm run build"]} -->

- **[P7-IMPL-7B-STREAMS]** `P7-IMPL-7B-LIBRARY`(NEXT)에서 3-D만 분리 — 백엔드는
  이미 완료(`GET /library/activities/:id/streams`,
  `activity_service.get_activity_streams()`), SvelteKit만. 조사 결과
  `activity_streams` 테이블 컬럼: `elapsed_sec, distance_m, heart_rate, cadence,
  power_watts, altitude_m, speed_ms, latitude, longitude, grade_pct,
  temperature_c, source`(`src/db_setup.py` `_DDL_ACTIVITY_STREAMS`) — `pace`
  컬럼은 없어 `speed_ms`에서 클라이언트에서 변환(`pace_sec_km = speed_ms > 0 ?
  1000/speed_ms : null`).
  **구현**: (1) `frontend/src/lib/components/Sparkline.svelte`(신규, 재사용
  컴포넌트) — props `{ data: (number | null)[]; width?: number = 600; height?:
  number = 48; color?: string = 'currentColor' }`. `<svg viewBox="0 0 {width}
  {height}" preserveAspectRatio="none">`에 `<polyline>` 하나: data를 min/max로
  정규화해 좌표 계산, `null` 지점은 선을 끊음(여러 `<polyline>` 세그먼트로 분할).
  호버/스크럽 인터랙션은 이번 스코프 밖(정적 렌더만) — 필요해지면 후속 유닛.
  데이터가 전부 null/빈 배열이면 "데이터 없음" 텍스트만. (2)
  `frontend/src/lib/types/index.ts`에 `ActivityStreamPoint { elapsed_sec:
  number; distance_m: number | null; heart_rate: number | null; cadence: number
  | null; power_watts: number | null; altitude_m: number | null; speed_ms:
  number | null; grade_pct: number | null; source: string }` 추가. (3)
  `frontend/src/lib/api/streams.ts`(신규) — `getActivityStreams(activityId:
  number): Promise<ActivityStreamPoint[]>` → `apiFetch<{streams:
  ActivityStreamPoint[]}>('/library/activities/' + activityId +
  '/streams').then(r => r.streams)`. (4)
  `frontend/src/routes/library/[id]/streams/+page.svelte` +
  `+page.ts`(신규, `P7-IMPL-7B-PROVIDER-UI`의 `providers/+page.ts`와 동일
  구조) — `load({params})`에서 `getActivityStreams(Number(params.id))` 호출
  (빈 배열이면 "스트림 데이터 없음"). 페이지 본문: 체크박스로 표시할 스트림
  토글(페이스·심박·고도·케이던스·파워 — 해당 컬럼이 전부 null인 스트림은
  체크박스 자체를 숨김), 체크된 것만 `<Sparkline>` 한 줄씩(라벨 + provider
  배지 + 최소/최대값 텍스트 + Sparkline). x축은 `elapsed_sec`(별도 렌더 없이
  포인트 순서 그대로 전달 — 스트림은 항상 균등 간격이 아닐 수 있어 정밀한 시간
  축은 후속 과제로 명시). (5)
  `frontend/src/routes/library/[id]/+page.svelte`(기존) — 탭 바의 `스트림`
  버튼을 `providers` 링크와 동일 패턴으로 `<a href="{base}/library/{core.id}
  /streams">`로 교체(disabled 제거는 스트림만, 랩·메트릭은 그대로 disabled
  유지). 테스트는 SVELTE-2A/2B·PROVIDER-UI와 동일하게 `npm run check`/`npm run
  build`만.
  <!-- autopilot: {"stage": "done", "mode": "auto", "attempts": 1, "deps": [], "kind": "code", "scope": ["frontend/src/lib/components/Sparkline.svelte", "frontend/src/lib/types/index.ts", "frontend/src/lib/api/streams.ts", "frontend/src/routes/library/[id]/streams/+page.svelte", "frontend/src/routes/library/[id]/streams/+page.ts", "frontend/src/routes/library/[id]/+page.svelte"], "verify": ["cd frontend && npm install && npm run check && npm run build"]} -->

- **[P7-IMPL-7B-METRICS-BROWSER]** `P7-IMPL-7B-LIBRARY`(NEXT)에서 3-E+3-F만
  분리 — 03c-library.md 3-E(메트릭 브라우저)·3-F(메트릭 상세). 조사 결과 시계열
  조회 함수 `db_helpers.get_metric_history(conn, metric_name, scope_type=
  'daily', provider=None, date_from=None, date_to=None, primary_only=True)`가
  이미 있어 새 쿼리 로직 불필요, 조립만 하면 됨. **스코프 축소**: 3-E/3-F는
  `scope_type='daily'` 메트릭만 대상(CTL/ATL/TSB/HRV/Body Battery/Sleep Score
  등 — 3-A/3-E/3-F 목업 예시 전부 daily-scope). `scope_type='activity'`
  메트릭(페이스/파워/케이던스 등)은 이미 3-C 활동 상세의 "핵심 메트릭"
  그리드에서 활동별로 노출되고 있어 별도 전역 브라우저가 필요 없음(하나의
  "글로벌 활동 메트릭 현재값"이 의미가 모호함 — 어느 활동 기준인지). 카테고리는
  `METRIC_REGISTRY`의 16-domain `category` 필드를 그대로 쓰되 한국어 표시 라벨은
  신규 매핑(`_CATEGORY_LABELS`, 아래 명시) — `SEMANTIC_GROUPS`(`metric_groups.
  py`)는 provider 간 동일 개념 비교용이라 이 용도에 안 맞음(재사용 안 함).
  **구현**: (1) `src/services/metrics_browser_service.py`(신규 — 기존
  `metrics_service.py`는 breakdown 트리 전용이라 관심사 분리, ADR 없이 진행
  가능한 순수 조회 함수라 별도 설계 승인 불필요) — `_CATEGORY_LABELS: dict[str,
  str] = {"load": "피트니스·피로", "pace": "페이스·속도", "hr": "심박", "sleep":
  "수면·회복", "power": "파워", "running_dynamics": "러닝 다이나믹스",
  "efficiency": "달리기 효율", "prediction": "레이스 준비도", "readiness": "컨디셔닝",
  "body": "신체 지표", "stress": "스트레스", "capacity": "능력치", "volume": "훈련량",
  "athlete": "프로필", "weather": "환경", "meta": "기타"}`(체크 #4/#10 기준 16개
  전부 매핑, `check_data_consistency.py` 카테고리 목록과 어긋나면 안 됨 — 착수
  전 `python3 scripts/check_data_consistency.py` 결과의 카테고리 집합과 대조).
  `get_metrics_browser(conn, date=None) -> dict`: `date`가 None이면
  `SELECT MAX(scope_id) FROM metric_store WHERE scope_type='daily' AND
  numeric_value IS NOT NULL`로 최신 날짜 조회(D1/marker 패턴,
  `src/ai/chat_context_builders.py`의 `scope_id<=? ORDER BY scope_id DESC`
  스타일 참조). `METRIC_REGISTRY`에서 `scope=='daily'`인 항목을 category별로
  순회, 각 metric에 대해 `db_helpers.get_primary_metric(conn, 'daily', date,
  name)` 호출 — 값 없으면(None) 스킵. 있으면 `db_helpers.get_metric_history(conn,
  name, scope_type='daily', date_to=date)`의 마지막 14개 `numeric_value`를
  `sparkline`으로 포함. 결과 없는 category는 응답에서 제외(빈 섹션 노출 금지,
  coding-rules.md "데이터 부족 시 빈 리스트"). 반환: `{"date": date, "categories":
  [{"category": "load", "label": "피트니스·피로", "metrics": [{"name", "label",
  "value", "unit", "provider", "confidence", "sparkline": [num, ...]}]}]}`.
  `get_metric_trend(conn, slug, period='3m') -> dict | None`: `period` →
  `{'4w':28,'3m':90,'6m':180,'1y':365}`(잘못된 값이면 '3m' 기본값), `date_from =
  today - days`. `db_helpers.get_metric_history(conn, slug, scope_type='daily',
  date_from=date_from)` 호출, 빈 리스트면 None 반환(404 처리는 라우트에서).
  `points = [{"date": r['scope_id'], "value": r['numeric_value']} for r in
  history]`, `current = points[-1]['value']`, `peak = max(points,
  key=lambda p: p['value'])`, `change_pct = (current - points[0]['value']) /
  points[0]['value'] * 100`(`points[0]['value']`가 0이거나 None이면 change_pct는
  None). 반환: `{"slug", "label", "unit", "current", "peak": {"value", "date"},
  "change_pct", "points": [...]}`. (2) `src/api/routes_library.py`에 라우트 2개
  추가 — `GET /library/metrics?date=`(옵션) → `get_metrics_browser`,
  `GET /library/metrics/<slug>/trend?period=`(기본 `3m`) → `get_metric_trend`
  (None이면 404). (3) `frontend/src/lib/types/index.ts`에 `MetricBrowserEntry
  { name: string; label: string; value: number | string | null; unit: string;
  provider: string | null; confidence: number | null; sparkline: number[] }`,
  `MetricBrowserCategory { category: string; label: string; metrics:
  MetricBrowserEntry[] }`, `MetricBrowserData { date: string; categories:
  MetricBrowserCategory[] }`, `MetricTrendPoint { date: string; value: number
  }`, `MetricTrendData { slug: string; label: string; unit: string; current:
  number | null; peak: { value: number; date: string } | null; change_pct:
  number | null; points: MetricTrendPoint[] }` 추가. (4)
  `frontend/src/lib/api/metrics.ts`(기존 파일에 추가) —
  `getMetricsBrowser(date?: string): Promise<MetricBrowserData>`,
  `getMetricTrend(slug: string, period?: string): Promise<MetricTrendData>`.
  (5) `frontend/src/routes/library/metrics/+page.svelte` +
  `+page.ts`(신규, 3-E) — 카테고리 칩 필터(전체 + `categories`에 실제로 있는
  카테고리만), 카테고리별 섹션에 메트릭 카드 그리드(`MetricCell`류 재사용 —
  카드 안에 값 + `<Sparkline data={m.sparkline} height={24}/>` + provider
  배지), 카드 탭 시 `{base}/library/metrics/{m.name}`로 이동. (6)
  `frontend/src/routes/library/metrics/[slug]/+page.svelte` +
  `+page.ts`(신규, 3-F) — `+page.ts`의 `load({params, url})`에서
  `getMetricTrend(params.slug, url.searchParams.get('period') ?? '3m')` 호출
  (404 시 errorMessage 패턴, 기존 `[id]/+page.ts`와 동일). 상단에 현재값·
  30일변화(`change_pct`)·피크(`peak`), 기간 선택 버튼 4개(선택 시
  `goto`로 `?period=` 쿼리 변경), `<Sparkline data={points.map(p=>p.value)}
  height={120}/>`(3-F 큰 차트용, 기존 것 그대로 재사용 — 별도 축 렌더링 없음,
  스코프 축소). 하단에 "계산 분해 보기" 버튼 — 탭 시 기존
  `<MetricBreakdown slug={slug} scopeType="daily" scopeId={points.at(-1)?.date}
  onClose={...}/>`를 바텀시트로 오픈(이미 있는 컴포넌트 그대로 재사용, 3-F
  목업의 인라인 배치 대신 기존 오버레이 패턴 유지 — Today L2 때와 동일한
  실용적 축소). "Provider 비교" 탭은 이번 스코프 밖(정체성 매트릭스,
  `P7-IMPL-PROVIDER-MATRIX`/LATER 참조) — 비활성 버튼으로만 표시.
  **의존성**: `Sparkline.svelte`를 쓰므로 `P7-IMPL-7B-STREAMS` 완료 후 착수.
  <!-- autopilot: {"stage": "done", "mode": "auto", "attempts": 1, "deps": ["P7-IMPL-7B-STREAMS"], "kind": "code", "scope": ["src/services/metrics_browser_service.py", "src/api/routes_library.py", "frontend/src/lib/types/index.ts", "frontend/src/lib/api/metrics.ts", "frontend/src/routes/library/metrics/+page.svelte", "frontend/src/routes/library/metrics/+page.ts", "frontend/src/routes/library/metrics/[slug]/+page.svelte", "frontend/src/routes/library/metrics/[slug]/+page.ts"], "verify": ["python3 -m pytest tests/test_metrics_browser_service.py tests/test_api_library.py -q", "cd frontend && npm install && npm run check && npm run build"]} -->

- **[P7-IMPL-7B-LIBRARY-HUB]** 03c-library.md 3-A — `/library` 홈 재설계
  (2026-09-23 plan mode 조사·설계, 사용자 승인). **배경**: 지금 `/library`는
  실제론 3-B(활동 목록, 필터+페이지네이션)이고 문서가 의도한 3-B 전용 경로는
  `/library/activities`다(문서 원문에 명시돼 있었음 — 이전 구현이 임시로
  `/library`에 얹어놓은 것). **IA 결정**: 목업의 `[활동][메트릭][웰니스]
  [Provider 비교]` 4-탭 중 "활동" 탭 = `/library` 자체(홈/최근 활동 요약 뷰,
  목업이 활동 탭 아래 최근 활동+빠른 메트릭 접근+Provider 현황을 그리고
  있음), 전체 필터 목록은 "활동" 탭의 하위가 아니라 "최근 활동" 섹션의
  "전체 보기" 링크로만 도달(별도 탭 아님). **Provider 데이터 현황 카드는
  이번 스코프에서 제외** — 조사 결과 연결상태 체크(`is_provider_enabled()`
  같은 공용 헬퍼 없음, `check_*_connection()` 4개 중 2개는 실제 네트워크
  호출), 마지막 동기화 시각(서로 다른 값을 가진 3개 소스: `sync_jobs`
  테이블은 비어있고 미사용, `sync_jobs.db`가 실제 최신이지만 별도 파일,
  `sync_state.json`은 stale)이 전부 정리 안 된 상태이고, 이 화면의 진짜
  주인인 `src/services/data_service.py`가 이미 "Phase 7a에서는 구현하지
  않는다"는 docstring을 가진 스텁(상단 ☰ 메뉴 "Data" 화면, `03f-data.md`,
  Phase 7d 몫)이라 여기서 얼기설기 만들면 그 작업과 충돌·중복만 됨 —
  대신 ☰ 버튼과 같은 "준비 중" 정적 placeholder만 표시.
  **구현**: (1) 기존 `frontend/src/routes/library/+page.svelte` +
  `+page.ts`(필터+페이지네이션 목록)를 `frontend/src/routes/library/
  activities/+page.svelte` + `+page.ts`로 그대로 이동(로직 변경 없음, 파일
  상단 주석의 "3-B" 경로 표기만 `/library/activities`로 정정). (2) 신규
  `frontend/src/routes/library/+page.svelte`(홈) — 탭 바(`library/[id]/
  +page.svelte`와 동일한 `border-b-2` 패턴 재사용): "활동"=현재 페이지라
  비활성 `<span>`, "메트릭"=`<a href="{base}/library/metrics">`, "웰니스"=
  아직 없으니 `disabled` 버튼(후속 `P7-IMPL-7B-WELLNESS`가 링크로 교체),
  "Provider 비교"=`disabled` 버튼(`P7-IMPL-PROVIDER-MATRIX`/LATER). 본문:
  "최근 활동" 섹션(`getActivities({page:1, per_page:5})` 호출, 활동 목록
  페이지와 동일한 행 포맷 축약판 — 날짜+이름+거리+provider 배지, "전체
  보기 →" 링크 `{base}/library/activities`), "빠른 메트릭 접근" 섹션(칩
  버튼들 — `src/services/metrics_browser_service.py`의 `_CATEGORY_LABELS`와
  정확히 같은 category slug·한국어 라벨을 그대로 옮겨써서 일치시킬 것,
  칩 탭 시 `{base}/library/metrics?category={slug}`로 이동 — 데이터 유무는
  목적지 페이지가 이미 처리하므로 홈에서 사전 체크 안 함), "Provider 데이터
  현황" 섹션(정적 텍스트 "준비 중" + 1줄 설명, 실제 fetch 없음 — ☰ 메뉴
  placeholder와 동일한 정직한 표시). (3) `frontend/src/routes/library/
  metrics/+page.ts`(기존 파일 수정) — `load({url})`로 시그니처 변경,
  `url.searchParams.get('category') ?? 'all'`를 `MetricsBrowserPageData`에
  `initialCategory` 필드로 추가 반환. `+page.svelte`도 `let selectedCategory
  = $state(data.initialCategory)`로 초기화만 변경(그 외 로직 동일). (4) 뒤로
  가기 링크 정정 — `frontend/src/routes/library/[id]/+page.svelte`의
  "← 목록으로"(활동 없음 상태) 링크는 `{base}/library/activities`로(원래
  목록으로 돌아가는 게 맞음), `frontend/src/routes/library/metrics/
  +page.svelte`의 "← Library로" 링크는 `{base}/library`로(메트릭 브라우저
  상위는 홈이 맞음) — 각각 원래 `{base}/library`였던 걸 목적지에 맞게
  분리. 백엔드 변경 없음(순수 프론트).
  <!-- autopilot: {"stage": "done", "mode": "auto", "attempts": 1, "deps": [], "kind": "code", "scope": ["frontend/src/routes/library/activities/+page.svelte", "frontend/src/routes/library/activities/+page.ts", "frontend/src/routes/library/+page.svelte", "frontend/src/routes/library/+page.ts", "frontend/src/routes/library/metrics/+page.svelte", "frontend/src/routes/library/metrics/+page.ts", "frontend/src/routes/library/[id]/+page.svelte"], "verify": ["cd frontend && npm install && npm run check && npm run build"]} -->

- **[P7-IMPL-7B-WELLNESS]** 03c-library.md 3-A "웰니스" 탭 — 화면 설계 자체가
  문서에 없어(목업엔 탭 라벨만 존재) 이번에 새로 설계(2026-09-23 plan mode).
  **핵심 발견**: `src/services/wellness_service.py`(`get_wellness_detail`/
  `get_wellness_trend`)가 이미 완성돼 있지만 어디서도 호출되지 않는 죽은
  코드이고, **실제 버그**가 있음 — `_WELLNESS_CATEGORIES`가
  `("sleep","stress","hrv","readiness","wellness","rp_readiness","rp_risk",
  "rp_recovery")`인데 실제 16-domain 카테고리엔 `hrv`/`wellness`/`rp_*`가
  존재하지 않음(진짜 이름은 `hr`) — `metrics_by_category`가 sleep detail·
  HRV·body·stress 카테고리 행을 전혀 못 잡고 있었음(`tests/
  test_wellness_service.py`가 `readiness`만 테스트해서 안 걸림). 또한
  `daily_wellness`의 핵심 12개 컬럼(sleep_score/hrv_*/resting_hr/
  body_battery_*/avg_stress/steps/active_calories/weight_kg)은 `metric_store`
  에 전혀 없어(실 데이터로 확인) 기존 `get_metrics_browser()`로는 못 보여줌
  — 반드시 `wellness_service.py`를 써야 함. **구현**: (1)
  `src/services/wellness_service.py` — `_WELLNESS_CATEGORIES = ("sleep",
  "stress", "hr", "readiness", "body")`로 수정(daily-scope `hr` 카테고리엔
  HRV detail 메트릭만 있어 안전 — 확인됨). (2) `src/api/routes_library.py`에
  라우트 2개 추가 — `GET /library/wellness?date=`(옵션) →
  `wellness_service.get_wellness_detail(conn, date=date_param)`, `GET
  /library/wellness/trend?days=`(기본 30) →
  `wellness_service.get_wellness_trend(conn, days=days_param)`. 기존 라우트
  패턴 그대로(db_path 503 체크 → `sqlite3.connect` → 서비스 호출 →
  `api_ok(result)` → `finally: conn.close()`). (3)
  `frontend/src/lib/types/index.ts`에 `WellnessCore { date: string;
  sleep_score: number | null; sleep_duration_sec: number | null;
  sleep_start_time: string | null; hrv_weekly_avg: number | null;
  hrv_last_night: number | null; resting_hr: number | null;
  body_battery_high: number | null; body_battery_low: number | null;
  avg_stress: number | null; steps: number | null; active_calories: number
  | null; weight_kg: number | null; [key: string]: unknown }`,
  `WellnessMetricEntry { metric_name: string; numeric_value: number | null;
  text_value: string | null; json_value: string | null; provider: string |
  null; confidence: number | null; unit: string; description: string }`,
  `WellnessDetailData { date: string; core: WellnessCore | Record<string,
  never>; metrics_by_category: Record<string, WellnessMetricEntry[]>;
  readiness_summary: { utrs: { value: number; confidence: number | null } |
  null; cirs: { value: number; confidence: number | null } | null } }`,
  `WellnessTrendData { dates: string[]; sleep_score: (number | null)[];
  hrv_last_night: (number | null)[]; resting_hr: (number | null)[];
  body_battery_high: (number | null)[]; avg_stress: (number | null)[];
  weight_kg: (number | null)[]; utrs: (number | null)[] }`. (4)
  `frontend/src/lib/api/wellness.ts`(신규) — `getWellnessDetail(date?:
  string): Promise<WellnessDetailData>`, `getWellnessTrend(days?: number):
  Promise<WellnessTrendData>`(`apiFetch`로 직접, 래핑 키 없음 — 백엔드가
  `api_ok(result)`로 평평하게 반환). (5)
  `frontend/src/routes/library/wellness/+page.svelte` +
  `+page.ts`(신규) — `+page.ts`의 `load()`에서 `Promise.all([
  getWellnessDetail(), getWellnessTrend()])` 호출(둘 다 실패해도 개별
  `.catch(() => null)`로 부분 렌더 허용). 탭 바는 `P7-IMPL-7B-LIBRARY-HUB`와
  동일 구조("웰니스"=활성 span, "활동"=`{base}/library` 링크, "메트릭"=
  링크, "Provider 비교"=disabled). 본문: 오늘 핵심값 카드 그리드(수면 점수·
  HRV 전날밤·안정시 심박·Body Battery·걸음수·체중·평균 스트레스 — `core`
  필드 직접, `library/metrics/+page.svelte`의 카드 스타일 재사용, 값 없는
  필드는 카드 자체를 숨김), readiness_summary가 있으면 UTRS/CIRS 카드 추가,
  트렌드 섹션(6개 시계열 각각 라벨+`<Sparkline data={trend.series} height=
  {32}/>` 한 줄씩 — `P7-IMPL-7B-STREAMS`의 스트림 목록 UI 패턴 재사용).
  (6) `frontend/src/routes/library/+page.svelte`(P7-IMPL-7B-LIBRARY-HUB가
  만든 파일) — "웰니스" 탭을 `disabled` 버튼에서 `<a href="{base}/library/
  wellness">` 링크로 교체. **테스트**: `tests/test_wellness_service.py`에
  sleep/hr/body/stress 카테고리 회귀 테스트 추가(버그 재발 방지 —
  `metrics_by_category`에 해당 카테고리 metric_store 행을 심고 실제로
  잡히는지), `tests/test_api_library.py`에 새 라우트 2개 테스트 추가(기존
  `metric_app` 픽스처가 이미 daily_wellness 시드 데이터를 갖고 있어 재사용
  가능).
  <!-- autopilot: {"stage": "done", "mode": "auto", "attempts": 1, "deps": ["P7-IMPL-7B-LIBRARY-HUB"], "kind": "code", "scope": ["src/services/wellness_service.py", "src/api/routes_library.py", "frontend/src/lib/types/index.ts", "frontend/src/lib/api/wellness.ts", "frontend/src/routes/library/wellness/+page.svelte", "frontend/src/routes/library/wellness/+page.ts", "frontend/src/routes/library/+page.svelte", "tests/test_wellness_service.py", "tests/test_api_library.py"], "verify": ["python3 -m pytest tests/test_wellness_service.py tests/test_api_library.py -q", "cd frontend && npm install && npm run check && npm run build"]} -->

- **[P7-IMPL-COACH-PLAN-ACTIVE]** 03e-coach.md 5-F(플랜 상세 — 진행 중) +
  5-A(Coach 홈 "플랜" 섹션) — `P7-IMPL-COACH-PLAN-STATIC`(NEXT)의 첫 조각으로
  분리(2026-09-23 조사). **핵심 발견**: `src/training/`에 이미 성숙한
  규칙 기반 훈련 계획 엔진이 있음(`planner.py`/`adjuster.py`/`goals.py`,
  논문 근거 기반, 테스트 존재) — 이번 유닛은 이걸 Phase 7b API/프론트에
  연결만 한다, 새 알고리즘 없음. `src.training.adjuster.adjust_todays_plan(conn,
  config=None) -> dict | None`이 이미 5-F/5-G가 요구하는 "상태 기반 조정"
  (HRV·수면·BB·TSB → 오늘 세션 강도 하향, 근거 텍스트 포함) 그대로 구현돼
  있음 — 단 **읽기 전용**(오늘 날짜만 조회, DB에 쓰지 않음, 매 로드마다
  재계산). "조정 수락" 버튼을 누르면 실제로 `planned_workouts`에 반영하는
  쓰기 경로는 코드 어디에도 없음(`src/web/views_training_crud.py` 등 grep
  확인) — **이번 유닛은 표시만 한다, "조정 수락" 버튼은 만들지 않음**
  (수락 시 영속화하는 API는 범위 밖, LATER로 별도 분리). 컴플라이언스는
  `session_outcomes.dist_ratio` 기반 계산이 어디에도 없어(레거시
  `views_training_cards.py`/`views_training_fullplan.py`가 쓰는 단순
  "완료 개수/비휴식일수" 비율 패턴을 그대로 재사용 — 새 지표 설계 안 함).
  **구현**: (1) `src/services/plan_service.py`(현재 docstring뿐인 스텁,
  함수 추가) — `get_active_plan(conn: sqlite3.Connection) -> dict | None`:
  `from src.training.goals import get_active_goal`로 활성 목표 조회(없으면
  None), `from src.training.planner import get_planned_workouts`로 이번 주
  월요일 기준 `get_planned_workouts(conn, week_start=<이번주 월요일>)` 호출.
  `week_index`는 `goal['created_at']`의 월요일부터 이번주 월요일까지 주
  차이+1로 계산(레이스데이가 아니라 시작일 기준 — `plan_weeks`와 비교해
  "N주차/전체M주" 표시용). `compliance_pct`는 이번 주 workouts 중
  `workout_type != 'rest'`인 것들의 `completed` truthy 비율(%, 정수 반올림,
  분모 0이면 None). 반환: `{"goal_id","name","distance_km","race_date",
  "plan_weeks","week_index","week_start","workouts","compliance_pct"}`.
  `get_todays_adjustment(conn) -> dict | None`: `from src.training.adjuster
  import adjust_todays_plan; return adjust_todays_plan(conn)` 그대로
  (서비스 레이어 경유 원칙 유지 — 라우트가 `src.training`을 직접 import
  하지 않도록). (2) `src/api/routes_plan.py`(신규 파일) — `GET
  /api/v1/plan/active`(`get_active_plan()` 호출, None이면 `api_ok({"plan":
  None})`), `GET /api/v1/plan/today-adjustment`(`get_todays_adjustment()`,
  None이면 `api_ok({"adjustment": None})`). 기존 라우트 파일들과 동일
  패턴(db_path 503 체크 → `sqlite3.connect` → 서비스 호출 →
  `finally: conn.close()`). `src/api/__init__.py`의 `from . import
  routes_coach, routes_library, routes_today` 줄에 `routes_plan` 추가(알파벳
  순서 유지: `routes_coach, routes_library, routes_plan, routes_today`).
  (3) `frontend/src/lib/types/index.ts`에 `PlannedWorkout { id: number; date:
  string; workout_type: string; distance_km: number | null; target_pace_min:
  number | null; target_pace_max: number | null; target_hr_zone: number |
  null; description: string | null; rationale: string | null; completed:
  number; source: string; interval_prescription: string | null }`,
  `ActivePlanData { goal_id: number; name: string; distance_km: number;
  race_date: string | null; plan_weeks: number | null; week_index: number |
  null; week_start: string; workouts: PlannedWorkout[]; compliance_pct:
  number | null }`, `TodaysAdjustment { id: number; date: string;
  workout_type: string; original_type: string; adjusted_type: string;
  adjusted: boolean; adjustment_reason: string | null; fatigue_level: 'low' |
  'moderate' | 'high'; volume_boost: boolean; distance_km: number | null;
  description: string | null }`(나머지 필드는 `[key: string]: unknown`로
  흡수). (4) `frontend/src/lib/api/plan.ts`(신규) — `getActivePlan():
  Promise<ActivePlanData | null>`(`apiFetch<{plan: ActivePlanData | null}>
  ('/plan/active').then(r => r.plan)`), `getTodaysAdjustment():
  Promise<TodaysAdjustment | null>`(동일 패턴, `/plan/today-adjustment`).
  (5) `frontend/src/routes/coach/plan/[id]/+page.svelte` +
  `+page.ts`(신규, 5-F) — `+page.ts`의 `load({params})`에서
  `Promise.all([getActivePlan(), getTodaysAdjustment()])` 호출(activePlan이
  null이거나 `goal_id`가 `params.id`와 다르면 "플랜을 찾을 수 없습니다" +
  `/coach`로 돌아가기 링크). 본문: 목표명 + "N주차/M주" + `race_date`,
  `compliance_pct` 진행 바, 이번 주 7일 스케줄 목록(월~일, `workout_type`
  한국어 라벨 매핑 — easy=이지/tempo=템포/interval=인터벌/long=롱런/
  rest=휴식/recovery=리커버리/race=레이스 — 배지 스타일은 기존
  `providerBadgeClass` 패턴처럼 간단한 색상 매핑 신규 작성, `completed`면
  "완료" 배지 아니면 "예정"), `distance_km`/페이스 범위(`target_pace_min`~
  `target_pace_max`, `formatPace` 재사용) 표시. 오늘 날짜 행 아래에
  `todaysAdjustment.adjusted`가 true면 "⚠ 상태 조정: {adjustment_reason}"
  카드(수락/거부 버튼 없음 — 표시만, 위 배경 설명 참조). (6)
  `frontend/src/routes/coach/+page.svelte`(기존 파일) — "── 플랜 ──" 섹션
  추가: `+page.ts`의 `load()`에 `getActivePlan()` 호출 추가(threads와
  병렬), 있으면 "진행 중: {name} {week_index}주차/{plan_weeks}주 [플랜
  상세→]"(`{base}/coach/plan/{goal_id}`), 없으면 "새 프로그램 만들기 →"
  (`{base}/coach/plan/new` — `P7-IMPL-COACH-PLAN-CREATE`가 아직 없으면
  일시적으로 404, 같은 세션에서 바로 이어 병합되므로 허용 — D1/D2 때와
  동일한 "탭 먼저, 내용 나중" 순서). 테스트는 이 저장소 프론트 관례상 없음
  (`npm run check`/`npm run build`), 백엔드는 `tests/test_plan_service.py`
  (신규) + `tests/test_api_plan.py`(신규, 기존 `mini_app` 픽스처 패턴
  재사용) — 최소 `get_active_plan()`이 `goals`+`planned_workouts`에 실 데이터
  심고 정상 조립하는지, 목표 없을 때 None 반환하는지, `get_todays_adjustment()`
  가 `adjust_todays_plan()`을 그대로 위임하는지.
  **리뷰 결과(2026-09-23)**: 라우트 프리픽스가 스펙(`/plan/*`)과 다르게
  `/coach/plan/*`로 구현됨(합리적 — `P7-IMPL-COACH-PLAN-CREATE` 스펙도 맞춰
  수정 완료) + `goal_id`별 조회용 `GET /coach/plan/<int:goal_id>` 라우트 추가
  구현(스펙엔 없었지만 프론트 `/coach/plan/:id` URL과 맞음, 합리적 확장).
  버그 2건 발견 후 수정: (1) `_week_index_absolute()`/`_compliance_pct()`가
  `planned_workouts`를 `source='planner'`로만 필터링해 `goal_id` 컬럼이 없는
  탓에 이전(완료/취소된) 목표의 leftover workout이 새 목표 집계에 섞일 수
  있었음 — goal의 `created_at`(주 시작)~`race_date`로 날짜 범위를 좁혀 해결,
  회귀 테스트 2건 추가. (2) Coach 홈 "새 프로그램 만들기" 링크가 존재하지
  않는 `/coach/plan/active`를 가리킴 — `/coach/plan/new`로 수정. 전체
  `pytest tests/`(1387 passed) + `check_data_consistency.py`(0 오류) +
  `check_docs.py`(0 오류) + `npm run check`/`build` 모두 통과 확인.
  <!-- autopilot: {"stage": "done", "mode": "auto", "attempts": 1, "deps": [], "kind": "code", "scope": ["src/services/plan_service.py", "src/api/routes_plan.py", "src/api/__init__.py", "frontend/src/lib/types/index.ts", "frontend/src/lib/api/plan.ts", "frontend/src/routes/coach/plan/[id]/+page.svelte", "frontend/src/routes/coach/plan/[id]/+page.ts", "frontend/src/routes/coach/+page.svelte", "frontend/src/routes/coach/+page.ts", "tests/test_plan_service.py", "tests/test_api_plan.py"], "verify": ["python3 -m pytest tests/test_plan_service.py tests/test_api_plan.py -q", "cd frontend && npm install && npm run check && npm run build"]} -->

- **[P7-IMPL-COACH-PLAN-CREATE]** 03e-coach.md 5-C(플랜 없음)+5-D(새 프로그램
  생성)+5-E(프로그램 비교) — `P7-IMPL-COACH-PLAN-STATIC`(NEXT)의 두 번째
  조각, `P7-IMPL-COACH-PLAN-ACTIVE` 완료 후 착수(5-C가 활성 플랜 여부를
  `getActivePlan()`으로 확인해야 하고, 생성 완료 후 `/coach/plan/{id}`로
  이동하므로). **핵심 발견**: "정적 템플릿 3~5개"는 새 커리큘럼을 설계할
  필요가 없다 — `src/training/readiness.py`의 `get_recommended_weeks
  (distance_km) -> {"min","optimal_min","optimal_max","taper"}`와
  `analyze_readiness(conn, goal_distance_km, goal_time_sec, target_weeks)
  -> {"achievability_pct","projected_time_end","status_summary","warnings",
  "current_vdot",...}`가 이미 기간(주)을 입력으로 받아 완전히 다른 결과를
  내는 기존 함수라, 3개의 `target_weeks` 값(= 3개 "템플릿")에 대해 그대로
  호출하면 목업이 요구하는 "기간별 달성 가능성·위험도 비교"가 그대로
  나온다(새 훈련 철학/알고리즘 발명 안 함 — 목업의 "균형형/단기집중/
  장기빌드업"이라는 스타일 차이는 실제로는 "기간 차이"로 근사). 실제
  플랜 생성도 이미 완성된 코드 재사용 —
  `src/web/views_training_wizard.py`의 `POST /training/wizard/complete`가
  하는 것(`add_goal()` → `UPDATE goals SET plan_weeks=?` → 주차 루프로
  `generate_weekly_plan()`+`save_weekly_plan()`)을 그대로 복사해 서비스
  함수로 옮긴다. **구현**: (1) `src/services/plan_template_service.py`
  (신규 파일 — `plan_service.py`가 이미 `P7-IMPL-COACH-PLAN-ACTIVE`에서
  100줄 넘게 채워져 300줄 캡 여유를 위해 분리, 관심사도 다름: 조회 vs
  생성) — `get_static_plan_templates(conn, distance_km: float,
  target_time_sec: int | None = None) -> list[dict]`: `from
  src.training.readiness import get_recommended_weeks, analyze_readiness,
  vdot_to_time` 임포트. `rec = get_recommended_weeks(distance_km)`.
  `week_presets = sorted(set([rec["min"], rec["optimal_min"],
  rec["optimal_max"]]))`(중복 제거 — 거리에 따라 min==optimal_min일 수
  있음). `target_time_sec`이 None이면("완주" 목표) `db_helpers.
  get_primary_metric(conn, 'daily', <오늘 또는 최신 날짜>, 'runpulse_vdot')`
  로 현재 VDOT 조회 → 있으면 `vdot_to_time(vdot, distance_km*1000)`을
  effective target으로 사용(달성 가능성이 자연히 ~100%에 수렴 — "완주"
  목표의 올바른 근사), 없으면(VDOT 데이터 자체가 없음) 각 템플릿에
  achievability 필드 전부 None으로 채우고 `analyze_readiness` 호출 자체를
  생략(크래시 방지 — `goal_time_sec`가 None이면 내부에서 0 비교 에러).
  각 `weeks`에 대해 `analysis = analyze_readiness(conn, distance_km,
  effective_target_sec, weeks)`(또는 생략 시 빈 값), `label`은 `weeks ==
  rec["min"] → "빠른 완성"`, `weeks == rec["optimal_max"] → "여유형"`,
  그 외(대개 optimal_min) `"권장"`. `risk_level`은
  `analysis["achievability_pct"]`가 없으면 None, 있으면 `>=70 → "낮음"`,
  `>=40 → "중간"`, 그 외 `"높음"`(단순 3단 임계값 — 이미 세션에서 쓴
  discrepancy severity 패턴과 동일한 간단한 threshold 매핑). 반환 리스트
  각 항목: `{"weeks","label","weekly_km_target": <analysis["current_vdot"]
  가 있으면 recommend_weekly_km(current_vdot, resolve 되는 distance_label,
  'peak', week_index=weeks-taper-1, total_weeks=weeks) 호출, 없으면 None>,
  "achievability_pct","projected_time_end","risk_level","status_summary"}`.
  `create_plan_from_template(conn, distance_km: float, race_date: str |
  None, weeks: int, target_time_sec: int | None = None, name: str | None =
  None) -> int`: `from src.training.goals import add_goal; from
  src.training.planner import upsert_user_training_prefs,
  generate_weekly_plan, save_weekly_plan`. `goal_id = add_goal(conn, name or
  f"{distance_km:.0f}km 목표", distance_km, race_date, target_time_sec)`,
  `conn.execute("UPDATE goals SET plan_weeks=? WHERE id=?", (weeks,
  goal_id))`, `upsert_user_training_prefs(conn)`(기본값 — 커스텀 prefs UI는
  범위 밖), 이번 주 월요일부터 `weeks`주 반복해 `generate_weekly_plan(conn,
  goal_id=goal_id, week_start=w)` → `save_weekly_plan(conn, plan)`,
  `conn.commit()`, `goal_id` 반환(`views_training_wizard.py`의 기존 로직과
  1:1 대응 — 새 로직 없음). (2) `src/api/routes_plan.py`(기존 파일에 추가
  — **주의**: `P7-IMPL-COACH-PLAN-ACTIVE`가 실제로 구현한 라우트 프리픽스는
  스펙 초안의 `/plan/*`가 아니라 `/coach/plan/*`다, 아래 경로는 그 실제
  구현에 맞춰 수정됨)
  — `GET /api/v1/coach/plan/templates?distance_km=&target_time_sec=`
  (distance_km 필수, 없으면 400) → `get_static_plan_templates`,
  `POST /api/v1/coach/plan`(JSON body: distance_km, race_date, weeks,
  target_time_sec?, name?) →
  `create_plan_from_template`, `{"goal_id": ...}` 반환. (3)
  `frontend/src/lib/types/index.ts`에 `PlanTemplate { weeks: number; label:
  string; weekly_km_target: number | null; achievability_pct: number | null;
  projected_time_end: number | null; risk_level: '낮음' | '중간' | '높음' |
  null; status_summary: string }`, `CreatePlanPayload { distance_km: number;
  race_date: string | null; weeks: number; target_time_sec?: number; name?:
  string }`. (4) `frontend/src/lib/api/plan.ts`(기존 파일에 추가) —
  `getPlanTemplates(distanceKm: number, targetTimeSec?: number):
  Promise<PlanTemplate[]>`(`/coach/plan/templates` 호출), `createPlan(payload:
  CreatePlanPayload): Promise<number>`
  (`apiFetch<{goal_id: number}>('/coach/plan', {method: 'POST',
  body: JSON.stringify(payload)}).then(r => r.goal_id)` — `apiFetch`의 POST
  옵션 시그니처는 `frontend/src/lib/api/coach.ts`의 `createThread()` 패턴
  그대로 참조). (5) `frontend/src/routes/coach/plan/+page.svelte` +
  `+page.ts`(신규, 5-C) — `load()`에서 `getActivePlan()` 호출, 있으면
  `{base}/coach/plan/{goal_id}`로 `redirect`(SvelteKit `redirect(302,...)`),
  없으면 페이지 렌더(현재 CTL 표시 + "[새 프로그램 만들기 →]"
  `{base}/coach/plan/new`). (6) `frontend/src/routes/coach/plan/new/
  +page.svelte` + `+page.ts`(신규, 5-D) — 거리 버튼(5km/10km/하프/마라톤 —
  `distance_km` 매핑: 5/10/21.097/42.195), 날짜 입력(`race_date`), 목표
  시간 입력 또는 "완주" 토글(목표 시간 입력 시 `target_time_sec` 계산,
  "완주" 선택 시 undefined로 전달), "[프로그램 생성 →]" 클릭 시
  `getPlanTemplates()` 호출 결과를 `/coach/plan/compare`로 쿼리
  스트링(distance_km/race_date/target_time_sec)과 함께 이동(`goto`).
  (7) `frontend/src/routes/coach/plan/compare/+page.svelte` +
  `+page.ts`(신규, 5-E) — `+page.ts`의 `load({url})`에서 쿼리 파라미터
  읽어 `getPlanTemplates()` 재호출(새로고침 시에도 동작하도록 서버
  재조회, 클라이언트 상태 전달에 의존 안 함). 템플릿 3개를 카드로 나열
  (기간/주간최대거리/달성가능성%/위험도/상태 요약), "선택" 버튼 클릭 시
  `createPlan({distance_km, race_date, weeks: t.weeks, target_time_sec})`
  호출 → 성공 시 `goto('/coach/plan/' + goalId)`. 테스트:
  `tests/test_plan_template_service.py`(신규) — `get_static_plan_templates`
  가 target_time_sec 있을 때/없을 때(완주)/VDOT 데이터 자체가 없을 때 3
  케이스 전부 크래시 없이 반환하는지(가장 중요 — None 처리가 핵심 리스크),
  `create_plan_from_template`이 실제로 `goals`+`planned_workouts`를 채우는지.
  `tests/test_api_plan.py`(기존 파일에 라우트 2개 테스트 추가).
  **리뷰 결과(2026-09-23)**: 1차 autopilot 실행이 5시간 사용량 한도에 걸려
  커밋 없이 중단(ledger: outcome=error) — 워크트리에 남은 미커밋 변경분을
  직접 리뷰해 완료. 버그 1건 발견 후 수정: `create_plan_from_template()`이
  `race_date`가 있으면 `weeks` 파라미터를 무시하고 `race_date+7일`로 종료일을
  계산(레거시 `views_training_wizard.py`의 단일 스텝 마법사 로직을 그대로
  복사한 결과 — 거기선 `race_date`/`plan_weeks`가 같은 입력이지만, 이 5-E
  비교 플로우에서는 `weeks`가 사용자가 3개 템플릿 중 직접 고른 값이라 항상
  존중해야 함, 안 그러면 비교 화면에 보여준 달성가능성/위험도가 실제 생성된
  플랜과 어긋남) — `weeks` 기준 루프로 수정, 회귀 테스트 추가. `/coach/plan`
  (5-C)의 `ctlCurrent`가 항상 `null`로 하드코딩돼 CTL 표시가 죽어있던 것도
  `getToday()`의 `training_status.ctl`로 연결해 수정. 전체 `pytest tests/`
  (1401 passed) + `check_data_consistency.py`(0 오류) + `check_docs.py`(0
  오류) + `npm run check`/`build` 모두 통과 확인.
  <!-- autopilot: {"stage": "done", "mode": "auto", "attempts": 1, "deps": ["P7-IMPL-COACH-PLAN-ACTIVE"], "kind": "code", "scope": ["src/services/plan_template_service.py", "src/api/routes_plan.py", "frontend/src/lib/types/index.ts", "frontend/src/lib/api/plan.ts", "frontend/src/routes/coach/plan/+page.svelte", "frontend/src/routes/coach/plan/+page.ts", "frontend/src/routes/coach/plan/new/+page.svelte", "frontend/src/routes/coach/plan/new/+page.ts", "frontend/src/routes/coach/plan/compare/+page.svelte", "frontend/src/routes/coach/plan/compare/+page.ts", "tests/test_plan_template_service.py", "tests/test_api_plan.py"], "verify": ["python3 -m pytest tests/test_plan_template_service.py tests/test_api_plan.py -q", "cd frontend && npm install && npm run check && npm run build"]} -->

- **[P7-IMPL-TIMELINE-NARRATIVE-FULL]** `<TimelineNarrative>`(C7) 완전판 —
  Today L2의 "[이번 달 전체 이야기 보기 →]" 우측/하단 시트 패널: 월 탐색 +
  `highlights` 수치 카드 + CTL(탭 시 CTL+ATL 2단) 스파크라인. AI 임베디드
  마크업(`[chart:slug]` 등 `body: NarrativeSegment[]`)과 "ATL 급상승 원인"
  근거는 제외 — 설계 근거·스코프 축소 이유는 `DECISIONS.md`의
  `[P7-IMPL-TIMELINE-NARRATIVE-FULL]` 항목 필독(착수 전 필수, 특히 기존
  `GET /library/metrics/:slug/trend` 재사용 부분).
  **구현**: (1) `src/services/today_service.py`의
  `get_today_narrative(conn, date=None, config=None, year: int | None = None,
  month: int | None = None)` — `year`/`month`가 둘 다 주어지면(하나만 오면
  무시) `month_start = f"{year}-{month:02d}-01"`, 그 달 말일을 계산해(다음 달
  1일 - 1일, `calendar.monthrange` 또는 직접 계산) `date`(조회 종료일)로 쓰되
  그 달이 오늘이 속한 달이면 말일 대신 오늘로 clamp(미래 데이터 없음). 이
  `month_start`/`date`를 기존 로직(월간 집계·AI 프롬프트·milestones 조회)에
  그대로 흘려보낸다(로직 재작성 안 함 — 이미 "이번 달"을 하드코딩 안 하고
  `date[:7]+'-01'`로 계산해뒀으므로 `date` 자체를 파라미터화하는 것만으로
  충분). AI 프롬프트(`_narrative.build_narrative_prompt`)에 "이번 달"이라는
  고정 문구가 있으면 실제 연월(`{year}년 {month}월`)로 바꿔 과거 달 조회 시
  시제 오류 방지 — 있으면 `build_narrative_prompt`에 `year`/`month` 또는
  `label` 파라미터 추가해 프롬프트 문자열에 반영. (2) 같은 함수에 `highlights`
  필드 추가: 기존 월간 집계 쿼리(`SELECT COUNT(*), SUM(distance_m) FROM
  v_canonical_activities WHERE...`)에 `MAX(distance_m)`도 같이 뽑아
  `longest_run_km`, `db_helpers.get_metric_history(conn, 'ctl',
  date_from=month_start, date_to=date)`의 `numeric_value` 최댓값을
  `peak_ctl`(데이터 없으면 None)로 반환값에 추가:
  `{"total_distance_km": month_dist_km, "activity_count": month_count,
  "longest_run_km": ..., "peak_ctl": ...}`. 응답에 `"highlights": {...}` 키
  추가. (3) `src/api/routes_today.py`의 `GET /today/narrative` —
  `request.args.get('year', type=int)`/`request.args.get('month', type=int)`
  읽어 `get_today_narrative()`에 전달(그대로 optional, 서비스 함수가 둘 다
  없으면 기존 동작). (4) `frontend/src/lib/api/today.ts`의 `getTodayNarrative`
  — `(year?: number, month?: number)` 파라미터 추가, 있으면 쿼리스트링에
  포함. (5) `frontend/src/lib/types/index.ts`의 `NarrativeResponse`에
  `highlights: {total_distance_km: number; activity_count: number;
  longest_run_km: number | null; peak_ctl: number | null}` 필드 추가. (6)
  신규 `frontend/src/lib/components/MonthNarrative.svelte` —
  `MetricBreakdown.svelte`의 오버레이/바텀시트 마크업(`fixed inset-0` 배경
  버튼 + `absolute inset-x-0 bottom-0 rounded-t-2xl` 패널) 그대로 재사용.
  Props: `{year, month, onClose}`. 내부 `$state`로 현재 `year`/`month` 보관,
  헤더에 "← YYYY년 M월 →" — 다음 달 버튼은 `{year,month}`가 이미 이번 달이면
  `disabled`. 본문: `getTodayNarrative(year, month)` 호출 결과를 Today L2와
  동일하게 텍스트 단락+`<EvidenceQuote>`+마일스톤 목록으로 렌더링(중복
  코드지만 이번 유닛 범위에서 공용 컴포넌트로 뽑지 않음 — 두 곳뿐이라
  과설계 방지), 그 아래 `highlights` 통계 행(총 거리/활동 수/최장거리/
  최고 CTL, null이면 항목 숨김 — 기존 `{#if x != null}` 관례), 그 아래
  `<Sparkline>` 1개(`getMetricTrend('ctl', '4w')` 호출, `points.map(p =>
  p.value)`를 `data`로 전달) — 탭하면 로컬 `$state`(`expanded`) 토글해 같은
  자리에 `getMetricTrend('atl', '4w')`도 추가 호출해 CTL/ATL 2개 스파크라인
  나란히 표시(새 패널 마운트 아님). 로딩/에러 상태는 `MetricBreakdown.svelte`
  패턴 그대로(loading 스피너/에러 메시지 텍스트). (7)
  `frontend/src/routes/today/+page.svelte` — L2 끝에 "[이번 달 전체 이야기
  보기 →]" 버튼 추가, 클릭 시 `showMonthNarrative = true`(로컬 상태, 초기
  `year`/`month`는 오늘 기준) + 조건부 `<MonthNarrative>` 마운트(기존
  `drillStack` MetricBreakdown 스택과는 별개 상태 — 동시에 두 패널이 뜨는
  일은 없음, 서로 트리거가 다름). 테스트: `tests/test_today_service.py`에
  `get_today_narrative(year=, month=)`가 과거 달을 올바른 범위로 조회하는지
  (이번 달 clamp 포함), `highlights`의 `longest_run_km`/`peak_ctl`이 데이터
  없으면 None인지. `tests/test_api_today.py`에 `?year=&month=` 쿼리
  파라미터 라우트 테스트 1~2개. 프론트는 이 저장소 관례상 테스트 없음
  (`npm run check`/`npm run build`).
  **리뷰 결과(2026-09-23)**: 다른 세션(같은 대화를 재개한 병렬 프로세스)이
  이 유닛을 조사·큐 등록·autopilot 실행까지 먼저 완료 — 코드는 정상
  커밋됐으나 리뷰/병합 전이라 이어서 진행. 버그 3건 발견 후 수정: (1)
  `get_today_narrative()`가 연월 확정 전(=오늘 기준) `date`로 먼저
  `get_today_status()`를 호출해, `highlights.peak_ctl`만 올바르게 그 달
  기준이고 evidence/AI 프롬프트의 "현재 CTL"은 항상 오늘 값이었음 — 연월
  확정을 `get_today_status()` 호출보다 앞으로 이동. (2) `rule_narrative()`
  (AI 실패 fallback)가 `month_label`을 안 받아 과거 달 조회에도 "이번 달
  142km..."처럼 시제가 틀린 텍스트를 냈음 — 파라미터 추가. (3)
  `get_recent_milestones()`에 날짜 범위 필터가 없어 과거 달 패널에도 항상
  오늘 기준 "최근" 마일스톤이 떴음 — `date_from`/`date_to` 옵션 추가.
  프론트 `MonthNarrative.svelte`도 2건: CTL 스파크라인이 최초 탭 전까지 빈
  채로 안 떠 있었던 것(mount 시 즉시 로드로 수정), `getMetricTrend()`가
  "오늘 기준 최근 4주"만 지원해 과거 달 조회 시 그 달과 무관한 데이터가
  뜨던 것(이번 달 조회 시에만 표시하도록 제한 — trend API의 임의 기간
  지원은 범위 밖, 후속 필요 시 별도 설계). `today_service.py`가 304줄로
  300줄 캡 초과해 evidence 조립을 `_narrative.build_evidence()`로 분리
  (286줄). 회귀 테스트 6개 추가. 전체 `pytest tests/`(1415 passed) +
  `check_data_consistency.py`(0 오류) + `check_docs.py`(0 오류, 경고
  64개=기존과 동일) + `npm run check`/`build` 모두 통과 확인.
  <!-- autopilot: {"stage": "done", "mode": "auto", "attempts": 1, "deps": [], "kind": "code", "scope": ["src/services/today_service.py", "src/api/routes_today.py", "frontend/src/lib/api/today.ts", "frontend/src/lib/types/index.ts", "frontend/src/lib/components/MonthNarrative.svelte", "frontend/src/routes/today/+page.svelte", "tests/test_today_service.py", "tests/test_api_today.py"], "verify": ["python3 -m pytest tests/test_today_service.py tests/test_api_today.py -q", "cd frontend && npm install && npm run check && npm run build"]} -->

- **[P7-IMPL-COACH-PLAN-SESSION-DETAIL]** `03e-coach.md` 5-G(일일 세션 상세)
  — 조사 후 2026-09-23 바로 큐 등록(설계 근거는 `DECISIONS.md`의
  `[P7-IMPL-COACH-PLAN-SESSION-DETAIL]` 항목 필독 — 목업의 "18km→16km"/
  "TSS 105→92" 같은 구체적 수치 변화는 실제 `adjust_todays_plan()`이
  워크아웃 타입만 바꾸고 거리/페이스/TSS는 재계산하지 않아 지어내지
  않는다는 게 핵심 결정, URL도 `:week/:day` 대신 `:date`로 단순화, "조정
  수락"/"원래 계획으로" 버튼은 문서가 Phase 7c로 명시한 대로 이번에도 안
  만듦).
  **구현 — 백엔드**: (1) `src/training/adjuster.py` — **주의**: 파일
  최상단이 `from datetime import date`(클래스)인데 새로 추가할 파라미터
  이름도 `date`(문자열)라 그대로 두면 함수 안에서 `date`가 파라미터로
  섀도잉돼 `date.today()` 호출이 깨진다. 먼저 최상단 임포트를 `from
  datetime import date as _date`로 바꾸고, 파일 안의 기존 `date.today()`
  호출부(전부 이 파일 안)를 `_date.today()`로 함께 고칠 것. 그 다음
  `adjust_todays_plan(conn, config=None, date: str | None = None)`(기본값
  None=오늘, 하위 호환) 추가 — 내부에서 `today = date.today().isoformat()`
  대신 `target = date or _date.today().isoformat()`으로 바꿔
  `planned_workouts WHERE date=?`에 사용. `_get_todays_wellness(conn, date:
  str | None = None)`도 같은 패턴으로 파라미터화(`daily_wellness WHERE
  date=?`, 인자 없으면 `_date.today()`). `_get_latest_tsb(conn, date: str
  | None = None)` — `date`가 있으면 SQL에 `AND scope_id <= ?` 조건 추가
  (과거 조회 시 그 이후 TSB가 안 섞이게), 없으면 기존과 동일(전역 최신,
  `today`용 기존 동작 유지). 세 함수 다 시그니처 변경 뿐 로직 흐름은
  그대로 — 기존 호출부(`plan_service.get_todays_adjustment()`)는 인자
  생략이라 그대로 동작. (2) `adjust_todays_plan()`의 반환에
  `adjustment_reason_parts: list[str]`도 추가(현재 `_reason_parts()`가
  만든 리스트를 `", ".join()`해서 문자열로만 반환하는데, 프론트에서
  `<EvidenceQuote>` 칩 여러 개로 각각 보여주려면 분리된 리스트가 필요 —
  `_reason_parts()` 결과를 `adjustment_reason`(합친 문자열, 기존 호환)과
  `adjustment_reason_parts`(리스트) 둘 다 반환에 포함). (3)
  `src/services/plan_service.py`(현재 ~130줄, 여유 있음, 이미 `from
  datetime import date, timedelta` 임포트돼 있음 — 섀도잉 문제 없음) —
  `_week_index_for_date(goal: dict, target_date: date) -> int`(`target_date`
  는 `date` 객체, 기존 `_week_index_absolute()`와 같은 `_plan_date_range()`
  재사용, "오늘 Monday" 대신 "target_date의 Monday" 기준으로 일반화 —
  `_week_index_absolute()`는 내부적으로 이 함수를 `target_date=오늘`로
  호출하도록 리팩터링해도 되고, 안 건드려도 무방 — 기존 동작 안 깨지면
  됨). `get_session_detail(conn, goal_id: int, session_date: str) -> dict |
  None` — `get_goal(conn, goal_id)` 없으면 None. `session_date`(문자열,
  URL에서 옴)를 `sd = date.fromisoformat(session_date)`로 파싱, `week_start
  = sd - timedelta(days=sd.weekday())`. `from src.training.planner import
  get_planned_workouts`로 `get_planned_workouts(conn,
  week_start=week_start)` 조회해 반환 리스트에서 `w["date"] ==
  session_date`인 항목 찾기(없으면 None). `week_index =
  _week_index_for_date(goal, sd)`(파싱된 `date` 객체 전달). `adjustment =
  adjust_todays_plan(conn, date=session_date)`(해당 날짜에 계획이 없으면
  None이 되니 위에서 이미 workout 존재 확인함). `note =` 아래 (4)의
  `get_session_note()` 호출. 반환:
  `{"goal": {...5-F와 동일 필드...}, "week_index", "workout": {...},
  "adjustment": {...adjust_todays_plan() 반환 그대로...} | None, "note":
  str | None}`. (4) 같은 파일에 세션 메모 — `get_session_note(conn,
  session_date: str) -> str | None`: `SELECT note FROM user_inputs WHERE
  input_date=? AND input_type='session_note'`. `save_session_note(conn,
  session_date: str, note: str) -> None`: `INSERT INTO user_inputs
  (input_date, input_type, note) VALUES (?, 'session_note', ?) ON
  CONFLICT(input_date, input_type) DO UPDATE SET note=excluded.note`
  (`today_service.save_checkin()`의 UPSERT와 동일 패턴, `src/services/
  today_service.py`의 251번째 줄 부근 참조). (5) `src/api/routes_plan.py`
  — `GET /coach/plan/<int:goal_id>/session/<session_date>` →
  `get_session_detail`(없으면 404). `POST /coach/plan/session/<session_
  date>/note`(JSON body `{"note": str}`, `note`가 빈 문자열/공백만이면
  400) → `save_session_note` 후 `{"note": note}` 반환.
  **구현 — 프론트**: (6) `frontend/src/lib/types/index.ts` —
  `SessionAdjustment`(=`adjust_todays_plan()` 반환 형태, `adjustment_reason_
  parts: string[]` 포함), `SessionDetail {goal: PlanGoal; week_index:
  number; workout: PlannedWorkout; adjustment: SessionAdjustment | null;
  note: string | null}`. (7) `frontend/src/lib/api/plan.ts`(기존 파일에
  추가) — `getSessionDetail(goalId: number, date: string):
  Promise<SessionDetail>`, `saveSessionNote(date: string, note: string):
  Promise<void>`. (8) `frontend/src/routes/coach/plan/[id]/session/
  [date]/+page.svelte` + `+page.ts`(신규) — `+page.ts`의
  `load({params})`에서 `getSessionDetail(goalId, params.date)` 호출(실패
  시 "세션을 찾을 수 없습니다" + 플랜 상세로 돌아가기 링크, 5-F 페이지의
  에러 패턴 그대로). 헤더: "Coach / {goal.name} / {week_index}주차
  {요일}"(요일 매핑은 `coach/plan/[id]/+page.svelte`의 `DAY_KO` 배열
  재사용). 본문: "원래 계획"(workout_type 라벨 + distance_km + 페이스
  범위 + description, 5-F 워크아웃 행과 동일 표시) — `adjustment`가
  null이거나 `adjusted=false`면 "조정 없음 — 계획대로 진행"만 추가로
  표시. `adjustment.adjusted`가 true면 그 아래 "상태 기반 조정" 섹션:
  "{원래 타입 라벨} → {조정 타입 라벨}"(coach/plan/[id]/+page.svelte의
  `WORKOUT_LABELS` 맵 재사용) + `adjustment_reason_parts` 각각을
  `<EvidenceQuote>` 칩으로(가짜 수치 델타 없음 — 위 DECISIONS.md 결정
  참조). 그 아래 "세션 메모" 섹션 — `<textarea>` + `[저장]` 버튼,
  `note` 초기값 표시, 저장 시 `saveSessionNote()` 호출 후 로컬 상태
  갱신(QuickInput의 저장 버튼 로딩/에러 상태 패턴 재사용). (9)
  `frontend/src/routes/coach/plan/[id]/+page.svelte`(기존 파일) — 워크아웃
  목록의 각 `<li>`를 `<a href="{base}/coach/plan/{goalId}/session/
  {w.date}">`로 감싸(현재 텍스트만 있는 행 클릭 가능하게, 완료 체크
  아이콘 등 내부 레이아웃은 그대로).
  **테스트**: `tests/test_adjuster.py`(있으면 확장, 없으면 최소 기존
  `adjust_todays_plan()` 관련 테스트 위치 확인 후 그 파일에) —
  `date=` 파라미터로 과거 날짜 조회 시 그 날짜의 `daily_wellness`/TSB를
  쓰는지(오늘 값과 다르게 시드해서 구분, 이번 세션에서 이미 쓴
  `test_today_service.py`의 `test_past_month_ctl_now_reflects_that_
  month_not_today` 패턴 참조), `adjustment_reason_parts`가 리스트로
  반환되는지. `tests/test_plan_service.py`에 `get_session_detail()` —
  존재하는 날짜/없는 날짜/goal_id 불일치 3케이스, `get_session_note`/
  `save_session_note` upsert 동작(두 번 저장 시 갱신되는지). `tests/
  test_api_plan.py`에 세션 상세 GET + 메모 POST 라우트 테스트(메모 빈
  문자열 400 포함).
  **리뷰(2026-09-23)**: 스펙대로 정확히 구현됨 — 버그 없음(이번 세션
  5번째 유닛 중 처음으로 리뷰에서 수정 사항 0건). `adjuster.py`의
  `date as _date` 섀도잉 회피가 지시한 그대로 적용, 세 함수
  (`adjust_todays_plan`/`_get_todays_wellness`/`_get_latest_tsb`) 전부
  올바르게 파라미터화. `plan_service.get_session_detail()`/
  `get_session_note()`/`save_session_note()` 스펙과 일치.
  `coach/plan/[id]/+page.svelte`의 워크아웃 행이 세션 상세로 링크됨.
  프론트 `adjustment_reason_parts`는 `<EvidenceQuote>` 대신 단순
  `<span>` 칩으로 표시 — reason이 이미 완성된 문장(예: "Body Battery
  45")이라 `<EvidenceQuote>`가 기대하는 metric/value 구조로 분해할
  근거가 없어 합리적 선택으로 판단, 수정 안 함. 문서 정합성만 1건
  수정: `test_adjuster.py` 신규 파일이 `files_index.md`에 미등록돼
  `check_docs.py`가 FAIL — `gen_files_index.py` 재생성으로 해결.
  전체 `pytest tests/`(1433 passed, 238 skipped) +
  `check_data_consistency.py`(16개 검사 0 오류) + `check_docs.py`
  (20개 검사 0 오류, 경고 64개=기존과 동일) + `npm run check`(0
  errors, 기존과 동일한 패턴의 경고 11개)/`npm run build` 모두 통과
  확인.
  <!-- autopilot: {"stage": "done", "mode": "auto", "attempts": 1, "deps": [], "kind": "code", "scope": ["src/training/adjuster.py", "src/services/plan_service.py", "src/api/routes_plan.py", "frontend/src/lib/types/index.ts", "frontend/src/lib/api/plan.ts", "frontend/src/routes/coach/plan/[id]/session/[date]/+page.svelte", "frontend/src/routes/coach/plan/[id]/session/[date]/+page.ts", "frontend/src/routes/coach/plan/[id]/+page.svelte", "tests/test_adjuster.py", "tests/test_plan_service.py", "tests/test_api_plan.py"], "verify": ["python3 -m pytest tests/test_adjuster.py tests/test_plan_service.py tests/test_api_plan.py -q", "cd frontend && npm install && npm run check && npm run build"]} -->

- **[P7-IMPL-PROVIDER-MATRIX]** `03c-library.md` §3-G-1(정체성 매트릭스) — 조사
  후 2026-09-23 큐 등록(설계 근거는 `DECISIONS.md`의
  `[P7-IMPL-PROVIDER-MATRIX]` 항목 필독 — 목업 예시 행이 아니라 문서
  서두의 "시맨틱 그룹 13개 × Provider 4개"를 근거로 `SEMANTIC_GROUPS` 13개
  한정, raw 메트릭 행은 범위 밖, 기간 집계는 "최신값" 단일 규칙).
  **구현 — 백엔드**: (1) `src/services/provider_matrix_service.py`(신규
  파일 — `provider_comparison_service.py`가 이미 279줄이라 캡 300 넘지
  않게 분리) — 상단에 `from src.services.provider_comparison_service
  import _preferred_provider, _build_values, _calc_discrepancy,
  _ordered_providers`(기존 helper 재사용, 새로 안 만듦),
  `from src.utils.dedup import _SOURCE_PRIORITY`,
  `from src.utils.metric_groups import SEMANTIC_GROUPS`,
  `from datetime import date, timedelta`.
  `get_provider_comparison_period(conn: sqlite3.Connection, days: int = 28,
  discrepancy_threshold: float = 5.0) -> dict`:
  ```
  conn.row_factory = sqlite3.Row
  end = date.today()
  start = end - timedelta(days=days - 1)
  start_s, end_excl_s = start.isoformat(), (end + timedelta(days=1)).isoformat()
  canon_rows = conn.execute(
      "SELECT id, matched_group_id FROM v_canonical_activities"
      " WHERE start_time >= ? AND start_time < ? ORDER BY start_time DESC",
      (start_s, end_excl_s),
  ).fetchall()
  if not canon_rows:
      return {"mode": "period", "days": days, "state": "no_data", "rows": []}
  group_ids = [r["matched_group_id"] for r in canon_rows if r["matched_group_id"]]
  period_primary_source = _mode_primary_source(conn, group_ids)
  sibling_map = {}
  all_scope_ids = set()
  for r in canon_rows:
      cid, gid = r["id"], r["matched_group_id"]
      if gid:
          sibs = [s["id"] for s in conn.execute(
              "SELECT id FROM activity_summaries WHERE matched_group_id = ?", (gid,)
          ).fetchall()]
      else:
          sibs = [cid]
      sibling_map[cid] = sibs
      all_scope_ids.update(sibs)
  placeholders = ",".join("?" * len(all_scope_ids))
  metric_rows = conn.execute(
      f"SELECT scope_id, metric_name, provider, numeric_value, text_value"
      f" FROM metric_store WHERE scope_type='activity' AND scope_id IN ({placeholders})",
      [str(i) for i in all_scope_ids],
  ).fetchall()
  metric_idx = {}
  for mr in metric_rows:
      d = dict(mr)
      metric_idx[(int(d["scope_id"]), d["metric_name"], d["provider"])] = d
  rows = []
  for group_name, group_def in SEMANTIC_GROUPS.items():
      cells = {}
      for canon in canon_rows:  # start_time DESC = 최신부터
          for metric_name, provider in group_def["members"]:
              if provider in cells:
                  continue
              for sib_id in sibling_map[canon["id"]]:
                  key = (sib_id, metric_name, provider)
                  if key in metric_idx:
                      d = metric_idx[key]
                      val = d["numeric_value"] if d["numeric_value"] is not None else d["text_value"]
                      cells[provider] = {"value": val, "available": val is not None}
                      break
      if not cells or not any(c["available"] for c in cells.values()):
          continue
      all_providers = _ordered_providers({p for (_, _, p) in metric_idx.keys()})
      values_dict = _build_values(all_providers, cells)
      numeric_avail = [c["value"] for c in values_dict.values()
                        if c["available"] and isinstance(c["value"], (int, float))]
      reason = _preferred_provider(
          period_primary_source,
          {k for k, v in values_dict.items() if v["available"]},
      )
      rows.append({
          "slug": group_name, "label": group_def["display_name"], "unit": None,
          "values": values_dict,
          "discrepancy": _calc_discrepancy(numeric_avail, discrepancy_threshold),
          "preferredProvider": reason["provider"] if reason else None,
          "primaryReason": reason,
      })
  return {"mode": "period", "days": days,
          "state": "loaded" if rows else "no_data", "rows": rows}
  ```
  `_mode_primary_source(conn, group_ids: list[str]) -> str | None` — `group_ids`
  비었으면 None. 아니면 `SELECT primary_source, COUNT(*) c FROM
  activity_groups WHERE group_id IN (...) GROUP BY primary_source ORDER BY c
  DESC`로 최빈값 조회, 동률(최고 count 여러 개)이면 `_SOURCE_PRIORITY`
  낮은 순으로 하나 선택. (2) `src/api/routes_library.py`(현재 204줄, 여유
  있음) — `GET /library/providers/matrix` 라우트 추가, `?days=`(기본 28,
  int 파싱 실패 시 400) `?discrepancy_threshold=`(기존 라우트와 동일 패턴)
  파싱 후 `provider_matrix_service.get_provider_comparison_period()` 호출,
  `api_ok({"comparison": result})` 반환(404 없음 — 항상 200, 데이터
  없으면 `state: "no_data"`로 표현, 기존 라우트의 404 패턴과 다름 주의).
  **구현 — 프론트**: (3) `frontend/src/lib/types/index.ts`의
  `ProviderComparisonData` 수정 — `mode: 'activity' | 'period'`,
  `activity_id?: number`, `days?: number`, `state: 'loaded' |
  'single_provider' | 'no_data'`(기존 `'activity'`/`'loaded' |
  'single_provider'` 하위 호환 유지, optional 필드 추가라 기존
  `/library/[id]/providers` 페이지는 안 건드려도 계속 동작). (4)
  `frontend/src/lib/api/providers.ts`(기존 파일)에 `getProviderMatrix(days
  = 28): Promise<ProviderComparisonApiResponse>` 추가 —
  `apiFetch('/library/providers/matrix?days=' + days)`. (5) 신규
  `frontend/src/routes/library/providers/+page.svelte` +
  `+page.ts` — `+page.ts`의 `load({url})`에서
  `getProviderMatrix(Number(url.searchParams.get('days')) || 28)` 호출,
  실패 시 `errorMessage` 패턴(기존 `[id]/providers/+page.ts`와 동일).
  페이지: 헤더("Library / Provider 정체성 매트릭스"), 기간 버튼 3개(4주/
  8주/12주 — 탭 시 `goto`로 `?days=` 쿼리 변경, `library/metrics/[slug]`
  기간 버튼과 동일한 스타일), `<ProviderComparison data={data.comparison}
  showPrimaryReason={true} discrepancyThreshold={5}/>`(기존 컴포넌트
  그대로, 수정 없음 — `state === 'no_data'`일 때 컴포넌트가 어떻게
  렌더링하는지 확인: 현재 컴포넌트는 `state === 'single_provider'`만
  특별 처리하고 나머지는 `rows` 빈 배열이면 테이블 헤더만 뜨고 바디가
  비어 보임 — `no_data` 전용 분기가 필요하면 `ProviderComparison.svelte`에
  `{:else if data.state === 'no_data'}` 케이스 추가(기존 `single_provider`
  분기와 나란히, "이 기간에 비교할 활동이 없습니다" 문구)). (6)
  `frontend/src/routes/library/+page.svelte` — 37행 근처 `<span
  class="... opacity-40" title="준비 중">Provider 비교</span>`를
  `<a href="{base}/library/providers" class="...">Provider 비교</a>`로
  교체(다른 탭 `<a>`와 동일한 클래스 패턴). (7)
  `frontend/src/routes/library/metrics/[slug]/+page.svelte` — 115~120행
  근처 `disabled` "Provider 비교" 버튼을 `<a href="{base}/library/
  providers" class="flex-1 rounded-lg border border-border-subtle
  bg-surface-2 py-2 text-center text-sm text-fg-secondary">Provider
  비교</a>`로 교체(슬러그별 필터링 없이 매트릭스 전체로 이동 —
  `DECISIONS.md` 참조).
  **테스트**: `tests/test_provider_matrix_service.py`(신규,
  `test_provider_comparison_service.py`의 `_insert_activity()` 픽스처
  패턴 재사용/복사) — 기간 내 활동 없음 → `state: "no_data"`, 같은
  그룹의 두 provider 값이 기간 내 서로 다른 날짜 활동에서 나와도 각각
  "최신값"으로 잡히는지(예: garmin 활동이 1주 전, intervals 활동이 2주
  전 — 둘 다 이번 기간엔 포함되지만 서로 다른 날짜), `matched_group_id`
  없는 단독 활동은 `_mode_primary_source`의 `group_ids`에서 자연스럽게
  빠지는지, primary_source 최빈값이 여러 활동 그룹 중 다수결로 정해지는지
  (예: 3개 그룹 중 2개가 garmin, 1개가 strava → "garmin" 선택),
  `SEMANTIC_GROUPS` 멤버 데이터가 전혀 없는 그룹은 `rows`에서 빠지는지.
  `tests/test_api_library.py`에 `GET /library/providers/matrix` 200 +
  `days` 파라미터 반영 + 잘못된 `days` 값 400 테스트.
  **리뷰(2026-09-23)**: 이번 autopilot 실행은 큐 스펙과 DECISIONS.md에
  커밋된 설계를 따르지 않고 완전히 다른 구현으로 진행함(이번 세션에서
  처음 있는 일) — `SEMANTIC_GROUPS` 13개 대신 목업 예시 행을 그대로
  옮긴 `METRIC_CATEGORIES` 16-domain 카테고리 기반 매트릭스로 구현,
  기간 집계도 "최신값" 대신 활동 평균(`AVG()`), `provider_comparison_
  service`의 기존 헬퍼(`_preferred_provider`/`_build_values`/
  `_calc_discrepancy`/`_ordered_providers`) 재사용 지시를 무시하고
  전부 새로 작성(중복 코드), `<ProviderComparison>` 컴포넌트 재사용
  지시도 무시하고 별도 타입(`ProviderMatrixData`)·커스텀 렌더링을
  전면 새로 작성, 메트릭 상세 페이지의 "Provider 비교" 버튼 연결
  항목은 아예 스킵, 파일도 318줄로 300줄 캡 초과. 설계를 바꾸려면
  `DECISIONS.md`에 이견을 기록하고 멈추라는 지시(`run_unit.py`
  프롬프트에 명시)도 따르지 않음 — 기록 없이 조용히 진행. **스펙대로
  전면 재구현**: `provider_matrix_service.py`를 `SEMANTIC_GROUPS` +
  기존 헬퍼 재사용 기반으로 다시 작성(141줄), `<ProviderComparison>`
  재사용하도록 페이지 재작성, `ProviderComparisonData` 타입 확장으로
  통일(별도 타입 제거), 스킵됐던 메트릭 상세 버튼 연결 추가, 테스트도
  스펙의 케이스(기간 필터링/최신값 채택/최빈값 투표)에 맞게 재작성.
  재구현 중 실제 버그 1건 발견·수정: `_mode_primary_source()`가 자신의
  `conn.row_factory`를 설정하지 않아 상위 함수 없이 단독 호출 시
  `TypeError` — 함수 자체에서 설정하도록 수정, 재현 테스트 추가.
  전체 `pytest tests/`(1448 passed, 238 skipped) + `check_data_
  consistency.py`(16개 검사 0 오류) + `check_docs.py`(20개 검사 0 오류,
  경고 64개=기존과 동일) + `npm run check`(0 errors)/`npm run build`
  모두 통과 확인.
  <!-- autopilot: {"stage": "done", "mode": "auto", "attempts": 1, "deps": [], "kind": "code", "scope": ["src/services/provider_matrix_service.py", "src/api/routes_library.py", "frontend/src/lib/types/index.ts", "frontend/src/lib/api/providers.ts", "frontend/src/routes/library/providers/+page.svelte", "frontend/src/routes/library/providers/+page.ts", "frontend/src/routes/library/+page.svelte", "frontend/src/routes/library/metrics/[slug]/+page.svelte", "frontend/src/lib/components/ProviderComparison.svelte", "tests/test_provider_matrix_service.py", "tests/test_api_library.py"], "verify": ["python3 -m pytest tests/test_provider_matrix_service.py tests/test_api_library.py -q", "cd frontend && npm install && npm run check && npm run build"]} -->

- **[P7-IMPL-TODAY-NEXT-SESSION]** `03a-today.md` 1-A L2 "다음 세션 현황"(구 Plan
  "보기" 흡수) + L3 링크 블록 — 프론트 전용, 백엔드/API 변경 없음(2026-09-24 조사 후
  큐 등록, 설계 근거·목업 대비 축소 5건은 `DECISIONS.md`의
  `[P7-IMPL-TODAY-NEXT-SESSION]` 항목 필독 — 목표 CTL 미저장이라 "CTL 68/80" 대신
  현재 CTL만, 조정 표시는 세션이 오늘일 때만, 주간 준수율은 `workouts`에서 프론트
  계산, "조정 수락/원래대로" 버튼은 7c라 이번에도 안 만듦).
  **구현**: (1) `frontend/src/lib/format.ts`에 추가 — `export const WORKOUT_LABELS:
  Record<string,string> = { rest:'휴식', recovery:'회복', easy:'쉬운 달리기',
  long:'장거리', tempo:'템포', interval:'인터벌', race:'레이스' };` 와 `export
  function workoutLabel(type: string): string { return WORKOUT_LABELS[type] ??
  type; }`. (2) `frontend/src/routes/coach/plan/[id]/+page.svelte`와
  `frontend/src/routes/coach/plan/[id]/session/[date]/+page.svelte` 두 파일의 로컬
  `const WORKOUT_LABELS = {...}` 정의를 삭제하고 `import { workoutLabel } from
  '$lib/format'`로 바꿔 `WORKOUT_LABELS[x] ?? x` 사용부를 `workoutLabel(x)`로 교체
  (동작 동일, 중복 제거만). (3) 신규 `frontend/src/lib/components/
  NextSessionCard.svelte` — props: `{ plan: ActivePlan | null; adjustment:
  TodaysAdjustment | { adjusted: false; adjustment_reason: null } | null; today:
  string }`(`$props()`, 타입은 `$lib/types`에서 import), `base`는 `$app/paths`.
  `nextSession = $derived(plan?.workouts.filter(w => w.date >= today &&
  w.workout_type !== 'rest').sort((a,b) => a.date.localeCompare(b.date))[0] ??
  null)`. `weekWork = $derived(plan?.workouts.filter(w => w.workout_type !==
  'rest') ?? [])`, `weekDone = $derived(weekWork.filter(w => w.completed === 1)
  .length)`. `dayText(date)`: `diff = Math.round((new Date(date+'T00:00:00')
  .getTime() - new Date(today+'T00:00:00').getTime()) / 86400000)`; diff 0이면
  '오늘', 1이면 '내일', 아니면 `${date.slice(5)}(${['일','월','화','수','목','금','토']
  [new Date(date+'T00:00:00').getDay()]})`. 렌더링 3분기: (a) `plan === null` —
  `<div class="rounded-xl bg-surface-2 p-3">` 안에 "활성 훈련 플랜이 없습니다"
  (text-sm text-fg-secondary) + `<a href="{base}/coach/plan">Coach에서 플랜 만들기
  →</a>`; (b) plan 있고 `nextSession` 없음 — 헤더 줄만 + "이번 주 남은 세션이
  없습니다"; (c) 정상 — 헤더 줄: `{plan.goal.name} · {plan.week_index}주차{plan.goal
  .plan_weeks ? ' / ' + plan.goal.plan_weeks + '주' : ''}{plan.ctl_current != null ?
  ' · CTL ' + Math.round(plan.ctl_current) : ''}`(text-xs text-fg-muted). 세션 카드
  (`rounded-xl bg-surface-2 p-3`): `{dayText(nextSession.date)}` 뱃지 + `{workoutLabel(
  nextSession.workout_type)}` + `{nextSession.distance_km}km`(있을 때만) +
  `nextSession.description`(있을 때만, text-xs). 조정 배너: `nextSession.date ===
  today && adjustment && 'original_type' in adjustment && adjustment.adjusted ===
  true`일 때만 `⚠ 상태 조정: {workoutLabel(adjustment.original_type)} →
  {workoutLabel(adjustment.adjusted_type)}` + `adjustment.adjustment_reason`(text-xs
  text-semantic-amber). 링크 2개: `<a href="{base}/coach/plan/{plan.goal.id}/session/
  {nextSession.date}">세션 상세 →</a>`, `<a href="{base}/coach/plan/{plan.goal.id}">
  계획 수립·수정은 Coach에서 →</a>`. 준수율 줄(`weekWork.length > 0`일 때):
  `이번 주 준수율 ` + `{#each weekWork as w}<span>{w.completed === 1 ? '●' : '○'}
  </span>{/each}` + ` {weekDone}/{weekWork.length} 완료`. (4)
  `frontend/src/routes/today/+page.ts` — `import { getActivePlan,
  getTodaysAdjustment } from '$lib/api/plan'`, `TodayPageData`에 `plan: ActivePlan |
  null; adjustment: TodaysAdjustment | { adjusted: false; adjustment_reason: null } |
  null` 추가(타입 import 포함), 기존 `Promise.all`에 `getActivePlan().catch(() =>
  null)`, `getTodaysAdjustment().catch(() => null)` 추가(404=플랜 없음도 null로
  수렴), 에러 분기 return에도 `plan: null, adjustment: null` 추가. (5)
  `frontend/src/routes/today/+page.svelte` — `NextSessionCard` import 후 L2
  `<section>` 안, 기존 `{#if narrative}...{:else}...{/if}` 블록 **바깥 바로 뒤**(내러티브
  로드 실패해도 플랜 카드는 나오게)에 `<div class="flex flex-col gap-2 border-t
  border-border-subtle pt-3"><p class="text-xs uppercase tracking-wide
  text-fg-muted">다음 세션</p><NextSessionCard plan={data.plan}
  adjustment={data.adjustment} today={status.date} /></div>` 추가(`status`는 이
  파일의 L1/L2가 이미 쓰는 그 변수 그대로). 내러티브 fallback 문구는 "상세
  이야기·계획 연동을 불러올 수 없습니다."에서 "상세 이야기를 불러올 수 없습니다."로
  수정(플랜은 이제 별도 카드). L2 `</section>` 뒤에 L3 블록 신설: `<section
  class="flex flex-col gap-2 border-t border-border-subtle pt-4"><p class="text-xs
  uppercase tracking-wide text-fg-muted">원본 데이터</p><p class="text-sm
  text-fg-secondary">위 지표는 탭 한 번으로 계산 분해에 닿고, 거기서 다시 원본
  데이터로 이어집니다.</p><a href="{base}/library" class="text-sm text-fg-secondary
  hover:text-fg-primary">Library에서 전체 탐색 →</a></section>`. 백엔드·테스트 파일은
  건드리지 않음(프론트 전용 유닛 — 검증은 `npm run check`/`build`, 이 저장소 프론트엔드
  엔 테스트 러너 없음).
  **리뷰(2026-09-24)**: 스펙대로 구현됨 — 버그 없음. 큐 프롬프트에 "명세 그대로 구현" 상시
  규칙을 넣은 뒤 첫 유닛이었고 scope 6개 파일을 전부 명세대로 수정(비용 $1.07, 지난 유닛의
  스펙 이탈 재발 없음). 사소한 편차 1건: 명세는 카드를 L2 `<section>` 안에 두라고 했는데
  `</section>` 바로 뒤 형제 `<div>`로 배치됨(구분선이 하나 더 생겨 별도 섹션처럼 보일 뿐
  기능 영향 없음, 수정 안 함). `WORKOUT_LABELS` 중복 제거 리팩터는 잔존 사용처 없음 확인.
  전체 `pytest tests/`(1449 passed, 238 skipped) + `check_data_consistency.py`(0 오류) +
  `check_docs.py`(0 오류, 경고 64개=기존과 동일) + `npm run check`(0 errors)/`build` 통과.
  브라우저 렌더링 육안 확인은 못함(실 DB 접근 불가·합성 데이터 서버 미기동).
  <!-- autopilot: {"stage": "done", "mode": "auto", "attempts": 1, "deps": [], "kind": "code", "scope": ["frontend/src/lib/format.ts", "frontend/src/lib/components/NextSessionCard.svelte", "frontend/src/routes/today/+page.ts", "frontend/src/routes/today/+page.svelte", "frontend/src/routes/coach/plan/[id]/+page.svelte", "frontend/src/routes/coach/plan/[id]/session/[date]/+page.svelte"], "verify": ["cd frontend && npm install && npm run check && npm run build"]} -->

- **[P7-IMPL-EVIDENCE-DRILL]** `03g-common-patterns.md` 7-3 — 근거 칩(EvidenceQuote) 탭 → 계산 분해
  패널(현재 앱의 모든 근거 칩이 비대화형 span으로 죽어 있음) + MetricBreakdown이 slug 변경 시
  재조회하지 않는 실버그 수정. 2026-09-24 코드 대조로 발견, 설계 근거는 `DECISIONS.md`의
  `[P7-IMPL-EVIDENCE-DRILL]` 항목 필독(백엔드가 근거마다 `drill` 참조를 붙여 실제로 드릴 가능한
  칩만 탭 가능하게 함 — `monthly_distance`·`sleep_score`는 `metric_store` 행이 없어 비대화형 유지).
  **구현 — 백엔드**: (1) `src/services/_narrative.py`에 추가: `def attach_drill(conn, evidence:
  list[dict], scope_date: str) -> list[dict]` — 함수 안에서 `from src.utils.db_helpers import
  get_primary_metric`, 각 `ev`에 대해 `drillable = ev.get("type") == "metric" and
  get_primary_metric(conn, "daily", scope_date, ev["metric"]) is not None`, `ev["drill"] =
  {"scope_type": "daily", "scope_id": scope_date} if drillable else None`, 마지막에 `return
  evidence`(같은 리스트를 제자리 수정 후 반환). (2) `src/services/today_service.py`(현재 286줄 —
  300줄 캡 때문에 헬퍼를 `_narrative.py`에 둔 것, 이 파일엔 아래 3줄 안팎만 추가):
  `get_today_briefing()` 안에서 `return` 직전 `from src.services._narrative import attach_drill`
  후 `attach_drill(conn, evidence, status["date"])`, `get_today_narrative()`의 기존
  `from src.services._narrative import (build_evidence, ...)` 튜플에 `attach_drill`을 추가하고
  `evidence = build_evidence(...)` 바로 다음 줄에 `attach_drill(conn, evidence, status["date"])`.
  (scope_date를 `date`가 아니라 `status["date"]`로 쓰는 이유: 근거 수치가 `get_today_status()`가 그
  날짜 행에서 읽은 값이라서.) (3) `tests/test_today_service.py`에 추가(기존 픽스처·시딩 패턴 재사용,
  특히 과거 달 CTL을 시딩하는 기존 테스트 참조): 브리핑 evidence의 `tsb` 항목이 `metric_store` daily
  `tsb` 대표 행이 있을 때 `drill == {"scope_type": "daily", "scope_id": <그 날짜>}`인지,
  내러티브 evidence의 `ctl`은 daily `ctl` 행이 있으면 drill dict / 없으면 `None`, `monthly_distance`
  는 항상 `drill is None`인지.
  **구현 — 프론트**: (4) `frontend/src/lib/types/index.ts` — `export interface EvidenceDrill {
  scope_type: string; scope_id: string }` 추가하고 `BriefingEvidence`에 `drill?: EvidenceDrill |
  null` 필드 추가. (5) 신규 `frontend/src/lib/evidence.ts`: `export interface DrillTarget { slug:
  string; scopeType: string; scopeId: string }` 와 `export function adaptEvidence(ev:
  BriefingEvidence, onDrill?: (t: DrillTarget) => void): EvidenceQuoteProps` — 기본 `{ type:
  'metric', label: ev.label, metric: { slug: ev.metric, value: ev.value } }`, `ev.drill && onDrill`
  이면 `onOpen: () => onDrill({ slug: ev.metric, scopeType: ev.drill.scope_type, scopeId:
  ev.drill.scope_id })`를 붙여 반환(drill 없으면 onOpen을 붙이지 않아 칩은 비대화형 유지).
  (6) `frontend/src/lib/components/MetricBreakdown.svelte` — `onMount` 한 번 조회를 `$effect`로
  교체: `$effect(() => { const s = slug, t = scopeType, i = scopeId; let cancelled = false;
  loading = true; error = null; data = null; getMetricBreakdown(s, t, i).then((d) => { if
  (!cancelled) data = d; }).catch((e) => { if (!cancelled) error = e instanceof Error ? e.message :
  '계산 데이터를 불러올 수 없습니다.'; }).finally(() => { if (!cancelled) loading = false; }); return
  () => { cancelled = true; }; });` — 쓰이지 않게 된 `onMount` import 제거. (7)
  `frontend/src/routes/today/+page.svelte` — 로컬 `adaptEvidence` 함수 삭제 후 `import {
  adaptEvidence, type DrillTarget } from '$lib/evidence'`; `drillStack`을 `$state<DrillTarget[]>
  ([])`로 바꾸고 `const todayDate = $derived(data.today?.status.date ?? '')`, `const drillTop =
  $derived(drillStack.length > 0 ? drillStack[drillStack.length - 1] : null)`(기존 `drillSlug`
  대체); `handleDrill(payload)`는 `drillStack = [...drillStack, { slug: payload.slug, scopeType:
  'daily', scopeId: todayDate }]`; `handleDrillInput(slug)`는 현재 top이 있으면 그 scopeType/
  scopeId를 이어받아 push(없으면 daily/todayDate); 신규 `function openEvidence(t: DrillTarget)
  { drillStack = [...drillStack, t]; }`; 호출부 2곳을 `briefing.evidence.map((ev) =>
  adaptEvidence(ev, openEvidence))`, `<EvidenceQuote {...adaptEvidence(ev, openEvidence)} />`로
  교체; 파일 하단 `{#if drillSlug}<MetricBreakdown slug={drillSlug} scopeType="daily"
  scopeId={status.date} .../>{/if}`를 `{#if drillTop}<MetricBreakdown slug={drillTop.slug}
  scopeType={drillTop.scopeType} scopeId={drillTop.scopeId} onClose={closeDrill}
  onDrillInput={handleDrillInput} />{/if}`로 교체; 쓰이지 않게 된 `BriefingEvidence`,
  `EvidenceQuoteProps` 타입 import 정리. (8) `frontend/src/lib/components/MonthNarrative.svelte` —
  로컬 `adaptEvidence` 삭제 후 `$lib/evidence`에서 import, `MetricBreakdown` import, 로컬
  `let drillStack = $state<DrillTarget[]>([])`, `drillTop` derived, `openEvidence`(push),
  `handleDrillInput`(top의 scope 이어받아 push), 칩 렌더링을 `adaptEvidence(ev, openEvidence)`로
  교체, 컴포넌트 루트 `<div>` 뒤 형제 노드로 `{#if drillTop}<MetricBreakdown slug={drillTop.slug}
  scopeType={drillTop.scopeType} scopeId={drillTop.scopeId} onClose={() => { drillStack = []; }}
  onDrillInput={handleDrillInput} />{/if}` 추가(MetricBreakdown 자체가 `fixed inset-0 z-50`라 뒤에
  오는 형제가 위에 그려짐). (9) `frontend/src/lib/components/EvidenceQuote.svelte` 상단 주석의
  "7a엔 열어줄 MetricBreakdown 패널이 없어…" 문장을 "onOpen이 없으면(드릴 대상이 없는 근거 —
  metric_store 행이 없는 지표 등) 비대화형 span으로 렌더링한다"로 현행화(동작 변경 없음).
  **리뷰(2026-09-24)**: 스펙대로 구현됨 — 이탈·버그 없음(비용 $1.65, 54턴). scope 9개 파일을 전부 명세대로
  수정. 확인한 것: `attach_drill()`이 `status["date"]`를 쓰는데 과거 달 조회 시에도 그 달 말일로
  확정된 값이라(`get_today_status(conn, date)`) 칩 값과 드릴 대상 날짜가 일치, `sleep_score`/
  `monthly_distance`는 metric_store 행이 없어 `drill=None`(비대화형 칩)이라 잘못된 패널이 뜨지 않음.
  `MetricBreakdown`의 `$effect` 재조회로 "입력 메트릭" 드릴-인 시 내용이 안 바뀌던 기존 버그 해결.
  사소한 흠 2건(수정 안 함): 테스트 이름 `test_narrative_ctl_drill_none_when_no_row`가 실제로는
  monthly_distance를 검증해 `test_monthly_distance_always_drill_none`과 중복, `get_today_briefing`의
  `attach_drill` import가 함수 내부(파일 나머지 관례와는 일치). 워크트리 `pytest tests/` 1454 passed/
  238 skipped + `check_data_consistency.py` 0 오류 + `check_docs.py` 0 오류 + `npm run check`(0 errors)/
  `build` 통과. 브라우저 육안 확인 못함(합성 데이터 서버 없음).
  <!-- autopilot: {"stage": "done", "mode": "auto", "attempts": 1, "deps": ["P7-IMPL-TODAY-NEXT-SESSION"], "kind": "code", "scope": ["src/services/_narrative.py", "src/services/today_service.py", "tests/test_today_service.py", "frontend/src/lib/types/index.ts", "frontend/src/lib/evidence.ts", "frontend/src/lib/components/MetricBreakdown.svelte", "frontend/src/lib/components/MonthNarrative.svelte", "frontend/src/lib/components/EvidenceQuote.svelte", "frontend/src/routes/today/+page.svelte"], "verify": ["python3 -m pytest tests/test_today_service.py tests/test_api_today.py -q", "cd frontend && npm install && npm run check && npm run build"]} -->

- **[P7-IMPL-TODAY-MILESTONES-PANEL]** `03a-today.md` 1-D — Today L2 "전체 마일스톤" 패널 + PB
  활동 링크. 프론트 전용(`GET /api/v1/today/milestones`는 이미 병합돼 있으나 프론트에서 미사용),
  2026-09-24 조사 후 큐 등록, 설계 근거는 `DECISIONS.md`의 `[P7-IMPL-TODAY-MILESTONES-PANEL]` 항목
  필독. **구현**: (1) `frontend/src/lib/api/today.ts`에 추가 — `import type`에 `MilestoneEntry`
  포함, `export function getTodayMilestones(limit = 50): Promise<MilestoneEntry[]> { return
  apiFetch<{ milestones: MilestoneEntry[] }>(`/today/milestones?limit=${limit}`).then((r) =>
  r.milestones); }`. (2) 신규 `frontend/src/lib/components/MilestonesPanel.svelte` — props
  `{ onClose }: { onClose: () => void }`, `onMount`에서 `getTodayMilestones()` 호출(상태
  `loading`/`error`/`items`), 오버레이 마크업은 `MonthNarrative.svelte`와 동일 패턴(루트
  `<div class="fixed inset-0 z-50 flex flex-col" role="dialog" aria-modal="true">`, 배경
  `<button class="absolute inset-0 bg-black/40" onclick={onClose} aria-label="닫기">`, 시트
  `<div class="absolute inset-x-0 bottom-0 flex max-h-[80vh] flex-col rounded-t-2xl bg-surface-1
  shadow-lg">`), 헤더는 `<h2 class="font-medium">전체 마일스톤</h2>` + `✕` 닫기 버튼(MonthNarrative의
  닫기 버튼과 같은 클래스), 본문 `overflow-y-auto p-4 flex flex-col gap-3`: 로딩 "불러오는 중…",
  에러 "마일스톤을 불러올 수 없습니다.", 빈 목록 "아직 마일스톤이 없습니다.". 각 항목은 아이콘
  (`distance_threshold`→🎯, `pb`→🏃, `metric_recompute`→🔄, 그 외 🔖) + `m.date` + `m.title`, 그
  아래 `m.detail`이 있으면 `text-xs text-fg-muted`로 표시(재계산의 "formula_v2 적용 — CTL 66→68"
  같은 문구는 백엔드가 이미 `detail`에 채움 — 프론트에서 old/new 값으로 조립하지 말 것),
  `m.activity_id`가 있으면 항목 전체를 `<a href="{base}/library/{m.activity_id}">`로 감싸고
  오른쪽에 `›`(`base`는 `$app/paths`). (3) `frontend/src/routes/today/+page.svelte` —
  `MilestonesPanel` import, `let showMilestones = $state(false)`, L2 마일스톤 목록(`narrative
  .milestones`)의 각 행을 `m.activity_id`가 있으면 `<a href="{base}/library/{m.activity_id}">`로
  감싸고(없으면 기존 `<div>` 그대로), 목록 바로 아래에 `<button class="self-start text-sm
  text-fg-secondary hover:text-fg-primary" onclick={() => { showMilestones = true; }}>전체
  마일스톤 →</button>`(목록이 비어 있지 않을 때만), 기존 `MonthNarrative` 패널 렌더링 옆에
  `{#if showMilestones}<MilestonesPanel onClose={() => { showMilestones = false; }} />{/if}`
  추가. 백엔드·테스트 파일은 건드리지 않음(프론트 전용 — 검증은 `npm run check`/`build`).
  **리뷰(2026-09-24)**: 자동 구현이 명세에서 4곳 벗어나 리뷰에서 직접 바로잡음(`541926f`) — (1) `getTodayMilestones`
  반환을 `MilestoneEntry[]`로(명세 시그니처), (2) 링크가 `pb` 한정 작은 `→`였던 것을 `activity_id`가 있는 모든 행 전체 `<a>`로,
  (3) `detail`이 재계산 한정이던 것을 있는 모든 행의 아래 줄로(PB 상세 소실 방지), (4) 빈 상태·에러 문구를 명세대로. Today L2 목록도
  같은 규칙. 비용 $0.96. `npm run check`(0 errors)/`build` 통과, 백엔드 변경 없음. 브라우저 육안 확인 못함(합성 데이터 서버 없음).
  <!-- autopilot: {"stage": "done", "mode": "auto", "attempts": 1, "deps": ["P7-IMPL-EVIDENCE-DRILL"], "kind": "code", "scope": ["frontend/src/lib/api/today.ts", "frontend/src/lib/components/MilestonesPanel.svelte", "frontend/src/routes/today/+page.svelte"], "verify": ["cd frontend && npm install && npm run check && npm run build"]} -->

- **[P7-IMPL-ACTIVITY-TABS-LAPS]** `03c-library.md` 3-C/3-D 활동 상세 탭 바 공용화 + "랩" 탭 신설 —
  프론트 전용(`GET /library/activities/:id`가 `laps`(activity_laps, lap_index 순)를 이미 내려주는데 프론트가
  안 씀, 2026-09-24 조사 후 큐 등록, 설계 근거는 `DECISIONS.md`의 `[P7-IMPL-ACTIVITY-TABS-LAPS]` 항목 필독).
  현황: 요약/스트림/소스 비교 3개 페이지가 탭 바를 각자 복붙해 구성이 제각각이다(요약: 소스 비교·스트림 링크 +
  비활성 랩/메트릭 버튼, 스트림: 요약·소스 비교·스트림, 소스 비교: 요약·소스 비교). **이 명세의 코드는 그대로
  구현할 것 — 구조를 바꾸고 싶으면 `DECISIONS.md`에 사유를 적고 중단.** **구현**:
  (1) `frontend/src/lib/types/index.ts` — `ActivityDetail` 인터페이스 바로 위에 신규 추가 후 `ActivityDetail.laps`를 `ActivityLap[] | null`로 교체(다른 필드는 그대로):
  ```ts
  // activity_laps 행 — activity_service.get_activity_detail()의 laps (lap_index 순).
  export interface ActivityLap {
  	id: number;
  	activity_id: number;
  	source: string;
  	lap_index: number;
  	start_time: string | null;
  	duration_sec: number | null;
  	distance_m: number | null;
  	avg_hr: number | null;
  	max_hr: number | null;
  	avg_pace_sec_km: number | null;
  	avg_cadence: number | null;
  	avg_power: number | null;
  	max_power: number | null;
  	elevation_gain: number | null;
  	calories: number | null;
  	lap_trigger: string | null;
  }
  ```
  (2) 신규 `frontend/src/lib/components/ActivityTabs.svelte`:
  ```svelte
  <script lang="ts">
  	// 활동 상세 공용 탭 바 — 03c-library.md 3-C/3-D. 탭마다 별도 라우트라 현재 탭만 <span>, 나머지는 <a>.
  	import { base } from '$app/paths';
  	let {
  		activityId,
  		active
  	}: { activityId: number; active: 'summary' | 'streams' | 'laps' | 'providers' } = $props();
  	const TABS = [
  		{ key: 'summary', label: '요약', path: '' },
  		{ key: 'streams', label: '스트림', path: '/streams' },
  		{ key: 'laps', label: '랩', path: '/laps' },
  		{ key: 'providers', label: '소스 비교', path: '/providers' }
  	] as const;
  </script>
  <div class="flex border-b border-border-subtle">
  	{#each TABS as tab (tab.key)}
  		{#if tab.key === active}
  			<span
  				aria-current="page"
  				class="flex-1 whitespace-nowrap border-b-2 border-fg-primary py-2.5 text-center text-sm font-medium text-fg-primary"
  			>{tab.label}</span>
  		{:else}
  			<a
  				href="{base}/library/{activityId}{tab.path}"
  				class="flex-1 whitespace-nowrap py-2.5 text-center text-sm text-fg-secondary hover:text-fg-primary"
  			>{tab.label}</a>
  		{/if}
  	{/each}
  </div>
  ```
  (3) `frontend/src/routes/library/[id]/+page.svelte` — `ActivityTabs` import 추가, 주석 `<!-- 탭 — 요약(활성), 소스 비교(링크), 나머지는 비활성 표시 (범위 밖) -->`부터 비활성 `{#each ['랩', '메트릭'] as label}…{/each}`가 든 탭 `<div class="flex border-b border-border-subtle">…</div>` 블록 전체를 `<!-- 탭 -->` 주석 + `<ActivityTabs activityId={core.id} active="summary" />` 한 줄로 교체, 파일 상단 주석 2줄(`// 03c-library.md 3-C — 활동 상세, 요약 탭만(Phase 7a).` / `// 스트림·랩·메트릭 탭은 …`)을 `// 03c-library.md 3-C — 활동 상세 요약 탭. 나머지 탭은 별도 라우트(ActivityTabs).` 한 줄로 교체. 그 외 마크업은 건드리지 않음.
  (4) `frontend/src/routes/library/[id]/streams/+page.svelte` — `ActivityTabs` import, 주석 `<!-- 탭 표시 (스트림 탭만 활성) -->` 아래 `<div class="flex border-b …">…</div>` 블록 전체를 `<!-- 탭 -->` 주석 + `<ActivityTabs activityId={data.activityId} active="streams" />`로 교체.
  (5) `frontend/src/routes/library/[id]/providers/+page.svelte` — 동일하게 주석 `<!-- 탭 표시 (소스 비교 탭만 활성) -->` 아래 탭 `<div>` 블록 전체를 `<!-- 탭 -->` 주석 + `<ActivityTabs activityId={data.activityId} active="providers" />`로 교체.
  (6) 신규 `frontend/src/routes/library/[id]/laps/+page.ts`:
  ```ts
  import { getActivity } from '$lib/api/library';
  import { ApiError } from '$lib/api/client';
  import type { ActivityLap } from '$lib/types';
  export interface LapsPageData {
  	activityId: number;
  	laps: ActivityLap[];
  	errorMessage: string | null;
  }
  export async function load({ params }: { params: { id: string } }): Promise<LapsPageData> {
  	const id = parseInt(params.id, 10);
  	if (isNaN(id)) {
  		return { activityId: NaN, laps: [], errorMessage: '잘못된 활동 ID입니다.' };
  	}
  	try {
  		const res = await getActivity(id);
  		return { activityId: id, laps: res.activity.laps ?? [], errorMessage: null };
  	} catch (e) {
  		const message = e instanceof ApiError ? e.message : '랩 데이터를 불러올 수 없습니다.';
  		return { activityId: id, laps: [], errorMessage: message };
  	}
  }
  ```
  (7) 신규 `frontend/src/routes/library/[id]/laps/+page.svelte` — 인터벌·크루즈 세트를 한눈에 비교하도록 랩별 페이스를 가장 빠른 랩 대비 막대로 보여준다(막대가 길수록 빠름). 랩 번호는 `lap_index`가 소스마다 0/1 기반이 다를 수 있어 배열 순서 `i + 1`을 쓴다:
  ```svelte
  <script lang="ts">
  	// 03c-library.md 3-C 랩 탭 — activity_laps(lap_index 순) 목록 + 랩별 페이스 막대.
  	import type { LapsPageData } from './+page';
  	import ActivityTabs from '$lib/components/ActivityTabs.svelte';
  	import { providerLabel, providerBadgeClass } from '$lib/provider';
  	import { formatDistance, formatDuration, formatPace } from '$lib/format';
  	import { base } from '$app/paths';
  	import type { ActivityLap, ProviderKey } from '$lib/types';
  	let { data }: { data: LapsPageData } = $props();
  	function lapPace(l: ActivityLap): number | null {
  		if (l.avg_pace_sec_km != null && l.avg_pace_sec_km > 0) return l.avg_pace_sec_km;
  		if (l.distance_m && l.duration_sec && l.distance_m > 0) return l.duration_sec / (l.distance_m / 1000);
  		return null;
  	}
  	const paces = $derived(data.laps.map(lapPace));
  	const fastest = $derived(Math.min(...paces.filter((p): p is number => p != null)));
  	const source = $derived(data.laps.length > 0 ? data.laps[0].source : null);
  	// 가장 빠른 랩 = 100%. 너무 짧아 안 보이지 않게 최소 8%.
  	function barPct(p: number | null): number {
  		if (p == null || !Number.isFinite(fastest)) return 0;
  		return Math.max(8, Math.round((fastest / p) * 100));
  	}
  </script>
  <div class="flex items-center gap-2 border-b border-border-subtle px-4 py-3">
  	<a href="{base}/library/{data.activityId}" class="shrink-0 text-fg-muted" aria-label="활동 상세로">←</a>
  	<h1 class="text-base font-semibold">랩</h1>
  </div>
  <ActivityTabs activityId={data.activityId} active="laps" />
  {#if data.errorMessage && data.laps.length === 0}
  	<div class="px-4 py-8 text-center">
  		<p class="text-sm text-fg-secondary">{data.errorMessage}</p>
  		<a href="{base}/library/{data.activityId}" class="mt-2 block text-xs text-fg-muted underline">← 활동으로 돌아가기</a>
  	</div>
  {:else if data.laps.length === 0}
  	<div class="px-4 py-8 text-center">
  		<p class="text-sm text-fg-muted">랩 데이터 없음</p>
  		<a href="{base}/library/{data.activityId}" class="mt-2 block text-xs text-fg-muted underline">← 활동으로 돌아가기</a>
  	</div>
  {:else}
  	<div class="flex flex-col gap-3 px-4 py-4">
  		<div class="flex items-center gap-2 text-xs text-fg-muted">
  			{#if source}
  				<span class="rounded px-1.5 py-0.5 text-[10px] text-white {providerBadgeClass(source as ProviderKey)}">{providerLabel(source as ProviderKey)}</span>
  			{/if}
  			<span>{data.laps.length}개 랩{#if Number.isFinite(fastest)} · 가장 빠른 랩 {formatPace(fastest)}{/if}</span>
  		</div>
  		<ul class="divide-y divide-border-subtle">
  			{#each data.laps as lap, i (lap.id)}
  				<li class="flex flex-col gap-1 py-2.5">
  					<div class="flex items-baseline gap-3 text-sm">
  						<span class="w-6 shrink-0 font-mono text-xs text-fg-muted">{i + 1}</span>
  						<span class="font-mono font-medium">{lap.distance_m != null ? formatDistance(lap.distance_m) : '—'}</span>
  						<span class="font-mono text-fg-secondary">{lap.duration_sec != null ? formatDuration(lap.duration_sec) : '—'}</span>
  						<span class="ml-auto font-mono font-medium">{paces[i] != null ? formatPace(paces[i] as number) : '—'}</span>
  					</div>
  					<div class="flex items-center gap-3 pl-9">
  						<div class="h-1.5 flex-1 rounded bg-surface-3">
  							<div class="h-1.5 rounded bg-fg-secondary" style="width:{barPct(paces[i])}%"></div>
  						</div>
  						<span class="flex shrink-0 gap-2 text-xs text-fg-muted">
  							{#if lap.avg_hr != null}<span>HR {lap.avg_hr}{#if lap.max_hr != null}/{lap.max_hr}{/if}</span>{/if}
  							{#if lap.avg_cadence != null}<span>{Math.round(lap.avg_cadence)}spm</span>{/if}
  							{#if lap.avg_power != null}<span>{Math.round(lap.avg_power)}W</span>{/if}
  							{#if lap.elevation_gain != null && lap.elevation_gain > 0}<span>↑{Math.round(lap.elevation_gain)}m</span>{/if}
  						</span>
  					</div>
  				</li>
  			{/each}
  		</ul>
  	</div>
  {/if}
  ```
  백엔드·테스트 파일은 건드리지 않음(프론트 전용 — 검증은 `npm run check`/`build`).
  **리뷰(2026-09-24)**: 스펙대로 구현됨 — 이탈 없음(비용 $1.40, 57턴). 7개 파일 전부 명세 코드와 일치
  (명세의 코드 블록 안 빈 줄만 큐 파싱 제약으로 제거돼 있음). `ActivityTabs`가 요약/스트림/소스 비교 3페이지의
  복붙 탭 바를 대체하고 비활성 랩/메트릭 버튼이 사라짐. `npm run check`(0 errors)/`build` 통과(워크트리),
  백엔드 변경 없음이라 pytest 생략. 랩 화면의 육안 확인은 합성 데이터 서버 스모크로 별도 수행.
  <!-- autopilot: {"stage": "done", "mode": "auto", "attempts": 1, "deps": ["P7-IMPL-TODAY-MILESTONES-PANEL"], "kind": "code", "scope": ["frontend/src/lib/types/index.ts", "frontend/src/lib/components/ActivityTabs.svelte", "frontend/src/routes/library/[id]/+page.svelte", "frontend/src/routes/library/[id]/streams/+page.svelte", "frontend/src/routes/library/[id]/providers/+page.svelte", "frontend/src/routes/library/[id]/laps/+page.ts", "frontend/src/routes/library/[id]/laps/+page.svelte"], "verify": ["cd frontend && npm install && npm run check && npm run build"]} -->
- **[P7-IMPL-ACTIVITY-METRICS-TAB]** `03c-library.md` 3-C "메트릭" 탭 신설 — 프론트 전용(`activity.metrics_by_category`가
  이미 카테고리별 전체 대표 메트릭 + 단위·설명·provider를 내려줌, 2026-09-24 조사 후 큐 등록, 설계 근거는 `DECISIONS.md`의
  `[P7-IMPL-ACTIVITY-METRICS-TAB]` 항목 필독). 각 행을 누르면 계산 분해(`MetricBreakdown`, `scopeType='activity'`)가 열려
  P2(Drillable)·P3(소스 배지)를 지킨다. **이 명세의 코드는 그대로 구현할 것 — 구조를 바꾸고 싶으면 `DECISIONS.md`에 사유를
  적고 중단.** **구현**:
  (1) 신규 `frontend/src/lib/metrics.ts`:
  ```ts
  // 활동 메트릭 표시 공용 헬퍼 — 요약/메트릭 탭이 같이 쓴다.
  import type { ActivityMetric } from '$lib/types';
  import { formatPace } from '$lib/format';
  // metric_registry.METRIC_CATEGORIES(16 도메인)의 한글 라벨 — 키 순서가 곧 메트릭 탭의 표시 순서.
  export const METRIC_CATEGORY_LABELS: Record<string, string> = {
  	hr: '심박',
  	pace: '페이스',
  	running_dynamics: '러닝 다이내믹스',
  	power: '파워',
  	load: '부하',
  	efficiency: '효율성',
  	capacity: '체력/역량',
  	prediction: '예측',
  	volume: '운동량',
  	weather: '날씨/환경',
  	body: '신체',
  	sleep: '수면',
  	stress: '스트레스',
  	readiness: '준비도',
  	meta: '메타/분류',
  	athlete: '선수 설정',
  	_unmapped: '미매핑 (개발용)'
  };
  export function categoryLabel(key: string): string {
  	return METRIC_CATEGORY_LABELS[key] ?? key;
  }
  // 알려진 카테고리는 위 순서, 모르는 카테고리는 그 뒤에 이름순.
  export function sortCategories(keys: string[]): string[] {
  	const known = Object.keys(METRIC_CATEGORY_LABELS);
  	const rank = (k: string) => {
  		const i = known.indexOf(k);
  		return i === -1 ? known.length : i;
  	};
  	return [...keys].sort((a, b) => rank(a) - rank(b) || a.localeCompare(b));
  }
  // 페이스 계열(초/km)은 m:ss/km, 그 외 수치는 소수 1자리, 수치가 없으면 텍스트 값, 그것도 없으면 '—'.
  export function formatMetricValue(m: ActivityMetric): string {
  	if (m.numeric_value == null) return m.text_value ?? '—';
  	const v = m.numeric_value;
  	if (m.metric_name.includes('pace') || m.unit === 'sec/km') return formatPace(v);
  	return Number.isInteger(v) ? String(v) : v.toFixed(1);
  }
  // formatMetricValue가 단위까지 붙이는 페이스 계열과 json 단위는 단위 표기 없음.
  export function metricUnit(m: ActivityMetric): string {
  	if (m.metric_name.includes('pace') || m.unit === 'sec/km' || m.unit === 'json') return '';
  	return m.unit;
  }
  ```
  (2) `frontend/src/lib/components/ActivityTabs.svelte` — `active` prop 유니언에 `'metrics'` 추가, `TABS`에서 `laps` 항목 바로 뒤에 `{ key: 'metrics', label: '메트릭', path: '/metrics' },` 추가(순서: 요약·스트림·랩·메트릭·소스 비교).
  (3) 신규 `frontend/src/routes/library/[id]/metrics/+page.ts`:
  ```ts
  import { getActivity } from '$lib/api/library';
  import { ApiError } from '$lib/api/client';
  import type { ActivityMetric } from '$lib/types';
  export interface MetricsTabPageData {
  	activityId: number;
  	metricsByCategory: Record<string, ActivityMetric[]>;
  	errorMessage: string | null;
  }
  export async function load({ params }: { params: { id: string } }): Promise<MetricsTabPageData> {
  	const id = parseInt(params.id, 10);
  	if (isNaN(id)) {
  		return { activityId: NaN, metricsByCategory: {}, errorMessage: '잘못된 활동 ID입니다.' };
  	}
  	try {
  		const res = await getActivity(id);
  		return { activityId: id, metricsByCategory: res.activity.metrics_by_category ?? {}, errorMessage: null };
  	} catch (e) {
  		const message = e instanceof ApiError ? e.message : '메트릭 데이터를 불러올 수 없습니다.';
  		return { activityId: id, metricsByCategory: {}, errorMessage: message };
  	}
  }
  ```
  (4) 신규 `frontend/src/routes/library/[id]/metrics/+page.svelte` — 상단 헤더(`←` 링크 + `<h1 class="text-base font-semibold">메트릭</h1>`, 랩 페이지 `laps/+page.svelte`와 같은 마크업)·`<ActivityTabs activityId={data.activityId} active="metrics" />` 다음 본문. `errorMessage`가 있고 메트릭이 하나도 없으면 에러 문구 + "← 활동으로 돌아가기" 링크, 메트릭이 하나도 없으면(에러 없이) "메트릭 데이터 수집 중". 그 외 스크립트:
  ```svelte
  <script lang="ts">
  	// 03c-library.md 3-C 메트릭 탭 — 이 활동의 대표(is_primary) 메트릭 전체를 카테고리별로.
  	// 행을 누르면 계산 분해(MetricBreakdown, scope=activity)가 열린다(P2). 소스는 배지로 항상 표기(P3).
  	import type { MetricsTabPageData } from './+page';
  	import ActivityTabs from '$lib/components/ActivityTabs.svelte';
  	import MetricBreakdown from '$lib/components/MetricBreakdown.svelte';
  	import { providerLabel, providerBadgeClass } from '$lib/provider';
  	import { categoryLabel, formatMetricValue, metricUnit, sortCategories } from '$lib/metrics';
  	import type { DrillTarget } from '$lib/evidence';
  	import { base } from '$app/paths';
  	import type { ActivityMetric, ProviderKey } from '$lib/types';
  	let { data }: { data: MetricsTabPageData } = $props();
  	let query = $state('');
  	let drillStack = $state<DrillTarget[]>([]);
  	const drillTop = $derived(drillStack.length > 0 ? drillStack[drillStack.length - 1] : null);
  	function matches(m: ActivityMetric): boolean {
  		const q = query.trim().toLowerCase();
  		if (!q) return true;
  		return m.metric_name.toLowerCase().includes(q) || m.description.toLowerCase().includes(q);
  	}
  	const sections = $derived(
  		sortCategories(Object.keys(data.metricsByCategory))
  			.map((cat) => ({ cat, items: data.metricsByCategory[cat].filter(matches) }))
  			.filter((s) => s.items.length > 0)
  	);
  	const total = $derived(
  		Object.values(data.metricsByCategory).reduce((n, items) => n + items.length, 0)
  	);
  	function openDrill(slug: string) {
  		drillStack = [...drillStack, { slug, scopeType: 'activity', scopeId: String(data.activityId) }];
  	}
  	function handleDrillInput(slug: string) {
  		const top = drillStack.length > 0 ? drillStack[drillStack.length - 1] : null;
  		drillStack = [
  			...drillStack,
  			{
  				slug,
  				scopeType: top?.scopeType ?? 'activity',
  				scopeId: top?.scopeId ?? String(data.activityId)
  			}
  		];
  	}
  </script>
  ```
  목록 마크업(메트릭이 있을 때): 바깥 `<div class="flex flex-col gap-3 px-4 py-4">` 안에 (a) 검색 입력 `<input type="search" bind:value={query} placeholder="메트릭 검색 (이름·설명)" class="w-full rounded-lg border border-border-subtle bg-surface-2 px-3 py-2 text-sm text-fg-primary placeholder:text-fg-muted focus:outline-none" />`, (b) `<p class="text-xs text-fg-muted">{total}개 메트릭</p>`, (c) `sections`가 비어 있으면 `<p class="text-sm text-fg-muted">일치하는 메트릭이 없습니다.</p>`, (d) 아니면 `{#each sections as s (s.cat)}` 마다 `<details open class="rounded-lg border border-border-subtle">` — `<summary class="cursor-pointer px-3 py-2 text-xs uppercase tracking-wide text-fg-muted">{categoryLabel(s.cat)} ({s.items.length})</summary>` + `<ul class="divide-y divide-border-subtle px-3">`, 각 `{#each s.items as m (m.metric_name)}`는 `<li>` 안에 행 버튼:
  ```svelte
  <button type="button" onclick={() => openDrill(m.metric_name)} class="flex w-full items-center gap-3 py-2.5 text-left hover:bg-surface-2">
  	<span class="min-w-0 flex-1 truncate text-sm">{m.description || m.metric_name}</span>
  	<span class="shrink-0 font-mono text-sm font-medium">{formatMetricValue(m)}{#if metricUnit(m)}<span class="ml-0.5 text-xs font-normal text-fg-secondary">{metricUnit(m)}</span>{/if}</span>
  	<span class="shrink-0 rounded px-1.5 py-0.5 text-[10px] text-white {providerBadgeClass(m.provider as ProviderKey | null)}">{providerLabel(m.provider as ProviderKey | null)}</span>
  	<span class="shrink-0 text-fg-muted">›</span>
  </button>
  ```
  파일 맨 끝(최상위 `{#if}`/`{:else}` 블록 뒤)에 계산 분해 패널: `{#if drillTop}<MetricBreakdown slug={drillTop.slug} scopeType={drillTop.scopeType} scopeId={drillTop.scopeId} onClose={() => { drillStack = []; }} onDrillInput={handleDrillInput} />{/if}`.
  요약 페이지(`[id]/+page.svelte`)는 이 유닛에서 건드리지 않음(다음 유닛이 `lib/metrics.ts`를 가져다 씀). 백엔드·테스트 파일은 건드리지 않음(프론트 전용 — 검증은 `npm run check`/`build`).
  **리뷰(2026-09-24)**: 스펙대로 구현됨 — 이탈 없음(비용 $0.89). 4개 파일 전부 명세 코드와 일치, `ActivityTabs`에 "메트릭" 탭이
  랩 뒤·소스 비교 앞에 추가됨. `npm run check`(0 errors)/`build` 통과(워크트리), 백엔드 변경 없음이라 pytest 생략.
  <!-- autopilot: {"stage": "done", "mode": "auto", "attempts": 1, "deps": ["P7-IMPL-ACTIVITY-TABS-LAPS"], "kind": "code", "scope": ["frontend/src/lib/metrics.ts", "frontend/src/lib/components/ActivityTabs.svelte", "frontend/src/routes/library/[id]/metrics/+page.ts", "frontend/src/routes/library/[id]/metrics/+page.svelte"], "verify": ["cd frontend && npm install && npm run check && npm run build"]} -->
- **[P7-IMPL-ACTIVITY-SUMMARY-ENRICH]** `03c-library.md` 3-C 활동 요약 탭 보강 — 프론트 전용, 2026-09-24 조사 후 큐 등록,
  설계 근거는 `DECISIONS.md`의 `[P7-IMPL-ACTIVITY-SUMMARY-ENRICH]` 항목 필독. 3-C 목업 대비 빠진 것: (a) 핵심 메트릭이
  `drillable={false}`라 P2 위반, (b) "핵심 메트릭"을 고르는 `CATEGORY_ORDER`가 실제 존재하지 않는 카테고리명(`performance`/
  `running`/`fitness`/`wellness`/`environment` — 실제 카테고리는 `hr`/`pace`/`load`/`efficiency`/`capacity`… 16 도메인)이라
  사실상 임의의 8개가 나옴, (c) 페이스 흐름 차트 없음(대신 "스트림 차트는 Phase 7b에서 제공됩니다" 낡은 문구), (d) HR 존
  분포 없음. **이 명세의 코드는 그대로 구현할 것 — 구조를 바꾸고 싶으면 `DECISIONS.md`에 사유를 적고 중단.** **구현**:
  (1) `frontend/src/lib/types/index.ts` — `ActivityDetail.streams`를 `unknown[] | null`에서 `ActivityStreamPoint[] | null`로 교체(`ActivityStreamPoint`는 같은 파일 아래쪽에 이미 정의됨, 다른 필드 그대로).
  (2) `frontend/src/lib/metrics.ts` 파일 끝에 추가(기존 export는 그대로):
  ```ts
  // 03c-library.md 3-C "핵심 메트릭" — 우선순위 이름 목록에서 값이 있는 것만 앞에서부터 고른다.
  // avg_pace_sec_km/avg_hr는 요약 상단 통계 바가 이미 보여주므로 여기서는 제외(03c의 Pace·HR avg 칸을 통계 바가 대신함).
  export const KEY_METRIC_NAMES = [
  	'max_hr',
  	'avg_cadence',
  	'training_stress_score',
  	'training_load',
  	'training_effect_aerobic',
  	'vo2max_activity',
  	'efficiency_factor',
  	'aerobic_decoupling',
  	'avg_ground_contact_time_ms',
  	'avg_stride_length_cm',
  	'normalized_power',
  	'relative_effort',
  	'vdot'
  ];
  export function pickKeyMetrics(
  	byCategory: Record<string, ActivityMetric[]>,
  	limit = 8
  ): ActivityMetric[] {
  	const byName = new Map<string, ActivityMetric>();
  	for (const items of Object.values(byCategory)) {
  		for (const m of items) {
  			if (m.numeric_value != null && !byName.has(m.metric_name)) byName.set(m.metric_name, m);
  		}
  	}
  	return KEY_METRIC_NAMES.map((n) => byName.get(n))
  		.filter((m): m is ActivityMetric => m != null)
  		.slice(0, limit);
  }
  export interface HrZoneShare {
  	zone: number;
  	sec: number;
  	pct: number;
  }
  // hr_zone_1..5_sec → 존별 체류 시간·비율. 존 메트릭이 없거나 합계가 0이면 null. provider는 첫 존 메트릭의 소스.
  export function hrZoneShares(
  	byCategory: Record<string, ActivityMetric[]>
  ): { zones: HrZoneShare[]; provider: string | null } | null {
  	const all = Object.values(byCategory).flat();
  	const secs = [1, 2, 3, 4, 5].map((z) => all.find((m) => m.metric_name === `hr_zone_${z}_sec`));
  	const total = secs.reduce((n, m) => n + (m?.numeric_value ?? 0), 0);
  	if (total <= 0) return null;
  	return {
  		zones: secs.map((m, i) => {
  			const sec = m?.numeric_value ?? 0;
  			return { zone: i + 1, sec, pct: Math.round((sec / total) * 100) };
  		}),
  		provider: secs.find((m) => m != null)?.provider ?? null
  	};
  }
  ```
  (3) `frontend/src/routes/library/[id]/+page.svelte` 스크립트 — `MetricCell` import 옆에 `MetricBreakdown`, `Sparkline` import, `import { formatMetricValue, hrZoneShares, metricUnit, pickKeyMetrics } from '$lib/metrics';`, `import type { DrillTarget } from '$lib/evidence';` 추가. `CATEGORY_ORDER`·`keyMetrics` 함수·`metricDisplayValue` 함수를 전부 삭제하고 아래로 교체(`core`/`metricsByCategory`/`streams` derived는 유지, `streams`는 이제 `ActivityStreamPoint[] | null`):
  ```ts
  const keyMetrics = $derived(pickKeyMetrics(metricsByCategory));
  const zoneData = $derived(hrZoneShares(metricsByCategory));
  const ZONE_COLORS = ['#38bdf8', '#10b981', '#f59e0b', '#f97316', '#ef4444'];
  // streams 행은 elapsed_sec 순 — 페이스(초/km)는 speed_ms에서 환산, null은 선을 끊는다.
  const paceSeries = $derived((streams ?? []).map((p) => (p.speed_ms != null && p.speed_ms > 0 ? 1000 / p.speed_ms : null)));
  const hrSeries = $derived((streams ?? []).map((p) => p.heart_rate));
  const streamSource = $derived(streams && streams.length > 0 ? streams[0].source : null);
  let drillStack = $state<DrillTarget[]>([]);
  const drillTop = $derived(drillStack.length > 0 ? drillStack[drillStack.length - 1] : null);
  function openMetric(slug: string) {
  	if (!core) return;
  	drillStack = [...drillStack, { slug, scopeType: 'activity', scopeId: String(core.id) }];
  }
  function handleDrillInput(slug: string) {
  	const top = drillStack.length > 0 ? drillStack[drillStack.length - 1] : null;
  	drillStack = [...drillStack, { slug, scopeType: top?.scopeType ?? 'activity', scopeId: top?.scopeId ?? String(core?.id ?? '') }];
  }
  ```
  (4) 같은 파일 마크업 — 핵심 메트릭 섹션(`{#if keyMetrics().length > 0}`)을 `{#if keyMetrics.length > 0}`로 바꾸고 `{#each keyMetrics() as m …}`도 `keyMetrics`(호출 아님)로, `MetricCell`의 `value={metricDisplayValue(m)}`를 `value={formatMetricValue(m)}`, `unit={m.unit && !m.metric_name.includes('pace') ? m.unit : undefined}`를 `unit={metricUnit(m) || undefined}`, `drillable={false}`를 `drillable={true}` + `onDrill={(p) => openMetric(p.slug)}`로 교체. 섹션 헤더 줄(`<p class="text-xs uppercase …">핵심 메트릭</p>`)을 `<div class="flex items-center justify-between"><p class="text-xs uppercase tracking-wide text-fg-muted">핵심 메트릭</p><a href="{base}/library/{core.id}/metrics" class="text-xs text-fg-secondary hover:text-fg-primary">전체 메트릭 보기 →</a></div>`로 교체.
  (5) 같은 파일 마크업 — 기존 "스트림 요약" 섹션(`<!-- 스트림 요약 (존재 여부 + 포인트 수) -->` `<section …>…</section>`, 낡은 "스트림 차트는 Phase 7b에서 제공됩니다." 문구 포함)을 통째로 삭제하고 그 자리에 아래 두 블록을 이 순서로 넣는다:
  ```svelte
  {#if paceSeries.some((v) => v != null) || hrSeries.some((v) => v != null)}
  	<section class="flex flex-col gap-2">
  		<div class="flex items-center justify-between">
  			<p class="text-xs uppercase tracking-wide text-fg-muted">페이스 · 심박 흐름</p>
  			<a href="{base}/library/{core.id}/streams" class="text-xs text-fg-secondary hover:text-fg-primary">스트림 탭에서 전체 보기 →</a>
  		</div>
  		{#if paceSeries.some((v) => v != null)}
  			<div>
  				<p class="mb-0.5 text-[10px] text-fg-muted">페이스</p>
  				<Sparkline data={paceSeries} height={40} color="#3b82f6" />
  			</div>
  		{/if}
  		{#if hrSeries.some((v) => v != null)}
  			<div>
  				<p class="mb-0.5 text-[10px] text-fg-muted">심박</p>
  				<Sparkline data={hrSeries} height={40} color="#ef4444" />
  			</div>
  		{/if}
  		<p class="text-xs text-fg-muted">{(streams ?? []).length.toLocaleString('ko-KR')}개 포인트{#if streamSource} · 소스: {providerLabel(streamSource as ProviderKey)}{/if}</p>
  	</section>
  {:else}
  	<p class="text-xs text-fg-muted">스트림 데이터 없음</p>
  {/if}
  {#if zoneData}
  	<section class="flex flex-col gap-2">
  		<div class="flex items-center justify-between">
  			<p class="text-xs uppercase tracking-wide text-fg-muted">HR 존 분포</p>
  			<span class="rounded px-1.5 py-0.5 text-[10px] text-white {providerBadgeClass(zoneData.provider as ProviderKey | null)}">{providerLabel(zoneData.provider as ProviderKey | null)}</span>
  		</div>
  		<div class="flex flex-col gap-1.5">
  			{#each zoneData.zones as z (z.zone)}
  				<div class="flex items-center gap-2 text-xs">
  					<span class="w-5 font-mono text-fg-secondary">Z{z.zone}</span>
  					<div class="h-2 flex-1 rounded bg-surface-3">
  						<div class="h-2 rounded" style="width:{z.pct}%; background:{ZONE_COLORS[z.zone - 1]}"></div>
  					</div>
  					<span class="w-20 text-right font-mono text-fg-secondary">{z.pct}% · {formatDuration(z.sec)}</span>
  				</div>
  			{/each}
  		</div>
  	</section>
  {/if}
  ```
  (6) 같은 파일 맨 끝(최상위 `{#if !core}…{:else}…{/if}` 블록 뒤)에 계산 분해 패널: `{#if drillTop}<MetricBreakdown slug={drillTop.slug} scopeType={drillTop.scopeType} scopeId={drillTop.scopeId} onClose={() => { drillStack = []; }} onDrillInput={handleDrillInput} />{/if}`. 헤더·상단 통계 바·탭(`ActivityTabs`)은 그대로 둔다. 파일이 300줄을 넘지 않게 주의. 백엔드·테스트 파일은 건드리지 않음(프론트 전용 — 검증은 `npm run check`/`build`).
  **리뷰(2026-09-24)**: 스펙대로 구현됨 — 이탈 없음(비용 $0.72). 3개 파일 전부 명세 코드와 일치: `pickKeyMetrics`(이름 우선순위)·
  `hrZoneShares`·`ActivityDetail.streams` 타입, 요약 페이지의 드릴 가능 MetricCell·"전체 메트릭 보기 →"·페이스/심박 스파크라인·HR 존 분포·
  `MetricBreakdown` 패널, 낡은 "Phase 7b에서 제공됩니다" 문구 삭제. 병합 전 합성 데이터 스모크에서 옛 로직이 실제로 "HR Zone 1~4 체류 시간"을
  핵심 메트릭으로 뽑는 것을 재현해 버그 존재를 확인했다(수정 후 재확인은 병합 후 스모크). 파일 158줄. `npm run check`(0 errors)/`build` 통과, 백엔드 변경 없음.
  <!-- autopilot: {"stage": "done", "mode": "auto", "attempts": 1, "deps": ["P7-IMPL-ACTIVITY-METRICS-TAB"], "kind": "code", "scope": ["frontend/src/lib/types/index.ts", "frontend/src/lib/metrics.ts", "frontend/src/routes/library/[id]/+page.svelte"], "verify": ["cd frontend && npm install && npm run check && npm run build"]} -->
- **[P7-IMPL-ACTIVITY-ENV-CARD]** `03c-library.md` 3-C "환경 컨텍스트" 카드 — 프론트 전용(활동 스코프 `weather` 카테고리 메트릭이
  `metrics_by_category.weather`로 이미 내려옴), 2026-09-24 조사 후 큐 등록, 설계 근거는 `DECISIONS.md`의
  `[P7-IMPL-ACTIVITY-ENV-CARD]` 항목 필독. 3-C 목업의 AQI·체감 WBGT·"훈련 가능" 판정은 저장된 데이터·계산이 없어 **표시하지
  않는다(지어내지 말 것)**. **이 명세의 코드는 그대로 구현할 것 — 구조를 바꾸고 싶으면 `DECISIONS.md`에 사유를 적고 중단.**
  **구현**: (1) 신규 `frontend/src/lib/components/EnvContextCard.svelte`:
  ```svelte
  <script lang="ts">
  	// 03c-library.md 3-C "환경 컨텍스트" — 활동 시점 날씨(metric_store weather 카테고리, 활동 스코프).
  	// AQI·체감 WBGT는 저장된 데이터가 없어 표시하지 않는다(지어내지 않음).
  	import { providerLabel, providerBadgeClass } from '$lib/provider';
  	import type { ActivityMetric, ProviderKey } from '$lib/types';
  	let { metrics }: { metrics: ActivityMetric[] } = $props();
  	const FIELDS = [
  		{ name: 'weather_temp_c', label: '기온', unit: '°C' },
  		{ name: 'avg_temperature', label: '기온(기기)', unit: '°C' },
  		{ name: 'weather_humidity_pct', label: '습도', unit: '%' },
  		{ name: 'weather_wind_speed_ms', label: '풍속', unit: 'm/s' },
  		{ name: 'weather_dew_point_c', label: '이슬점', unit: '°C' },
  		{ name: 'weather_pressure_hpa', label: '기압', unit: 'hPa' },
  		{ name: 'weather_condition', label: '날씨', unit: '' }
  	];
  	function display(m: ActivityMetric): string | null {
  		if (m.numeric_value != null) {
  			return Number.isInteger(m.numeric_value) ? String(m.numeric_value) : m.numeric_value.toFixed(1);
  		}
  		return m.text_value || null;
  	}
  	// 기기 온도는 API 날씨 기온이 없을 때만 보조로 쓴다.
  	const hasApiTemp = $derived(
  		metrics.some((m) => m.metric_name === 'weather_temp_c' && display(m) != null)
  	);
  	const cells = $derived(
  		FIELDS.filter((f) => !(f.name === 'avg_temperature' && hasApiTemp))
  			.map((f) => {
  				const m = metrics.find((x) => x.metric_name === f.name);
  				return { f, m, v: m ? display(m) : null };
  			})
  			.filter((c) => c.v != null)
  	);
  	const provider = $derived((cells[0]?.m?.provider ?? null) as ProviderKey | null);
  </script>
  {#if cells.length > 0}
  	<section class="flex flex-col gap-2 rounded-lg border border-border-subtle bg-surface-2 px-4 py-3">
  		<div class="flex items-center justify-between">
  			<p class="text-xs uppercase tracking-wide text-fg-muted">환경 컨텍스트</p>
  			<span class="rounded px-1.5 py-0.5 text-[10px] text-white {providerBadgeClass(provider)}">{providerLabel(provider)}</span>
  		</div>
  		<div class="grid grid-cols-3 gap-x-3 gap-y-2">
  			{#each cells as c (c.f.name)}
  				<div class="flex flex-col">
  					<span class="text-[10px] text-fg-muted">{c.f.label}</span>
  					<span class="font-mono text-sm font-medium">{c.v}{#if c.f.unit}<span class="ml-0.5 text-xs font-normal text-fg-secondary">{c.f.unit}</span>{/if}</span>
  				</div>
  			{/each}
  		</div>
  	</section>
  {/if}
  ```
  (2) `frontend/src/routes/library/[id]/+page.svelte` — `EnvContextCard` import 추가, HR 존 분포 섹션(`{#if zoneData}…{/if}`) 바로 뒤에 `<EnvContextCard metrics={metricsByCategory.weather ?? []} />` 한 줄 추가(카드가 스스로 빈 상태를 숨김). 그 외는 건드리지 않음. 파일이 300줄을 넘지 않게 주의. 백엔드·테스트 파일은 건드리지 않음(프론트 전용 — 검증은 `npm run check`/`build`).
  **리뷰(2026-09-24)**: 스펙대로 구현됨 — 이탈 없음(비용 $0.59). `EnvContextCard.svelte`와 요약 페이지 배치가 명세 코드와 일치(파일 160줄).
  **러너 이슈 1건**: 실행의 `git add`가 "requires approval"로 막혀 변경이 미커밋 상태로 끝났는데도 `outcome=success`/`stage=review`로 보고됨 → 리뷰어가
  워크트리에서 직접 커밋(`914a8c0`). 재발 방지로 러너에 미커밋 변경 자동 커밋 + 프롬프트에 `git -C` 금지 규칙 추가(별도 커밋). `npm run check`(0 errors)/`build` 통과.
  <!-- autopilot: {"stage": "done", "mode": "auto", "attempts": 1, "deps": ["P7-IMPL-ACTIVITY-SUMMARY-ENRICH"], "kind": "code", "scope": ["frontend/src/lib/components/EnvContextCard.svelte", "frontend/src/routes/library/[id]/+page.svelte"], "verify": ["cd frontend && npm install && npm run check && npm run build"]} -->
- **[P7-IMPL-COACH-CHECKIN-CONTEXT]** QuickInput 체크인(피로도·통증·메모)을 Coach 채팅 컨텍스트에 반영 — 백엔드,
  2026-09-24 조사 후 큐 등록, 설계 근거는 `DECISIONS.md`의 `[P7-IMPL-COACH-CHECKIN-CONTEXT]` 항목 필독. 현황: 사용자가
  Today에서 체크인을 저장해도 `chat_engine`이 `user_inputs`를 전혀 읽지 않아(`src/ai/`에 `user_inputs` 참조 0건) Coach가
  그 정보를 모른다 — `03e-coach.md` 5-A가 약속한 "(Coach 질문에 자동 컨텍스트 활용)"이 거짓인 상태. **이 명세의 코드는
  그대로 구현할 것 — 구조를 바꾸고 싶으면 `DECISIONS.md`에 사유를 적고 중단.** **구현**:
  (1) 신규 `src/ai/chat_context_checkin.py`(`chat_context_builders.py`가 이미 301줄이라 새 모듈로 분리):
  ```python
  """AI 채팅 컨텍스트 — 러너 자기 보고(QuickInput 체크인)."""
  from __future__ import annotations
  import sqlite3
  _PAIN_LABELS = {"none": "없음", "mild": "경미", "moderate": "중간", "severe": "심함"}
  _NOTE_MAX = 200
  def build_checkin_context(conn: sqlite3.Connection, today: str) -> dict | None:
      """today 기준 최근 체크인(user_inputs) — 없거나 값이 전부 비었으면 None.
      save_checkin()은 SQLite date('now')(UTC)로 날짜를 찍고 today는 서버 로컬 날짜라
      KST 새벽엔 하루 어긋난다 — 그래서 today가 아니라 [today-1일, today+1일] 범위에서
      가장 최근 1건을 쓴다.
      """
      row = conn.execute(
          "SELECT input_date, fatigue, pain, note FROM user_inputs"
          " WHERE input_type = 'checkin'"
          "   AND input_date BETWEEN date(?, '-1 day') AND date(?, '+1 day')"
          " ORDER BY input_date DESC LIMIT 1",
          (today, today),
      ).fetchone()
      if row is None:
          return None
      date_, fatigue, pain, note = row[0], row[1], row[2], row[3]
      if fatigue is None and not pain and not (note or "").strip():
          return None
      return {"date": date_, "fatigue": fatigue, "pain": pain, "note": note}
  def format_checkin_line(checkin: dict | None) -> str | None:
      """프롬프트용 한 줄 — 예: '러너 자기 보고(2026-09-24): 피로도 6/10 | 통증 경미 | 메모 "무릎 뻐근"'."""
      if not checkin:
          return None
      parts: list[str] = []
      if checkin.get("fatigue") is not None:
          parts.append(f"피로도 {checkin['fatigue']}/10")
      pain = checkin.get("pain")
      if pain:
          parts.append(f"통증 {_PAIN_LABELS.get(pain, pain)}")
      note = (checkin.get("note") or "").strip()
      if note:
          parts.append(f'메모 "{note[:_NOTE_MAX]}"')
      if not parts:
          return None
      return f"러너 자기 보고({checkin['date']}): " + " | ".join(parts)
  ```
  (2) `src/ai/chat_context.py` — 상단 docstring 모듈 목록에 `  - chat_context_checkin.py : 러너 자기 보고(QuickInput 체크인)` 한 줄 추가, `from .chat_context_checkin import build_checkin_context` import 추가, `build_chat_context()`에서 `ctx = _build_base_context(conn, today)` 바로 다음 줄들에 추가(실패해도 채팅은 계속 — 기존 빌더들과 같은 try/except 패턴):
  ```python
      try:
          ctx["checkin"] = build_checkin_context(conn, today)
      except Exception:
          log.warning("체크인 컨텍스트 빌드 실패", exc_info=True)
  ```
  (3) `src/ai/chat_context_format.py` — `from .chat_context_checkin import format_checkin_line` import 추가, `_format_chat_context()`에서 웰니스 블록(`lines.append("오늘 컨디션: " + " | ".join(parts))`이 든 `if parts:` 블록) 바로 뒤에 추가:
  ```python
      # 러너 자기 보고 (QuickInput 체크인)
      checkin_line = format_checkin_line(ctx.get("checkin"))
      if checkin_line:
          lines.append(checkin_line)
  ```
  (4) 신규 `tests/test_chat_context_checkin.py`(`db_conn` 픽스처 사용, `from src.services import today_service`로 `today_service.save_checkin(db_conn, fatigue=…, pain=…, note=…, input_date=…)` 로 시드) — 케이스: (a) 체크인 없음 → `build_checkin_context` None + `format_checkin_line(None)` None, (b) 당일 체크인(피로 6·pain 'mild'·메모) → dict 필드 일치 + 한 줄에 "피로도 6/10"·"통증 경미"·메모 포함, (c) 3일 전 체크인은 무시(None), (d) 하루 전(UTC 어긋남 대응) 체크인은 포함, (e) 피로·통증·메모가 전부 None/빈 체크인 → None, (f) 메모 200자 초과 시 잘림(`format_checkin_line` 결과의 메모 부분이 200자), (g) 통합: `save_checkin(db_conn, fatigue=7, pain='mild', input_date=date.today().isoformat())` 후 `from src.ai.chat_context import build_chat_context; build_chat_context(db_conn, "오늘 훈련 어때?", provider="rule")` 결과에 "피로도 7/10" 포함, (h) 체크인이 없을 때 위 통합 결과에 "러너 자기 보고"가 없음.
  **리뷰(2026-09-24)**: 스펙대로 구현됨 — 이탈 없음(비용 $0.55). 신규 `chat_context_checkin.py`·`chat_context.py`·`chat_context_format.py`가 명세 코드와 일치,
  테스트 9개(체크인 없음/당일/3일 전 무시/하루 전 포함(UTC 어긋남)/빈 값/공백 메모/200자 절단/통합 2건). 워크트리 `pytest tests/` 1466 passed/238 skipped +
  `check_data_consistency.py` 0 오류. `check_docs.py`는 신규 파일 2개의 `files_index.md` 미등록 오류가 나서 병합 후 `gen_files_index.py`로 재생성해 해소.
  <!-- autopilot: {"stage": "done", "mode": "auto", "attempts": 1, "deps": ["P7-IMPL-ACTIVITY-ENV-CARD"], "kind": "code", "scope": ["src/ai/chat_context_checkin.py", "src/ai/chat_context.py", "src/ai/chat_context_format.py", "tests/test_chat_context_checkin.py"], "verify": ["python3 -m pytest tests/test_chat_context_checkin.py tests/test_chat_engine_threads.py -q"]} -->
- **[P7-IMPL-COACH-HOME-QUICKINPUT]** `03e-coach.md` 5-A Coach 홈의 `<QuickInput compact=true>` 섹션 — 백엔드(체크인 전용 GET 1개) +
  프론트, 2026-09-24 조사 후 큐 등록, 설계 근거는 `DECISIONS.md`의 `[P7-IMPL-COACH-HOME-QUICKINPUT]` 항목 필독. 캡션 "입력한
  컨디션은 Coach 답변에 자동 반영됩니다"는 직전 유닛(`COACH-CHECKIN-CONTEXT`)이 배선을 끝내 사실이다. **이 명세의 코드는
  그대로 구현할 것 — 구조를 바꾸고 싶으면 `DECISIONS.md`에 사유를 적고 중단.** **구현**:
  (1) `src/api/routes_today.py` — 모듈 docstring 첫 줄에 `GET /api/v1/today/checkin`을 추가하고, `get_today()` 뒤에 추가(Coach 홈이 체크인 1건을 얻으려고 무거운 `GET /today`(상태·브리핑 계산)를 통째로 부르지 않게 함):
  ```python
  @api_bp.get("/today/checkin")
  def get_today_checkin():
      dpath = db_path()
      if not dpath.exists():
          return api_error("NOT_FOUND", "running.db 없음", 503)
      conn = sqlite3.connect(str(dpath))
      try:
          checkin = today_service.get_todays_checkin(conn)
      finally:
          conn.close()
      return api_ok({"checkin": checkin})
  ```
  (2) `tests/test_api_today.py` — 기존 `mini_app` 픽스처로 테스트 2개 추가: `test_get_today_checkin_none`(체크인 없을 때 200, `body["data"]["checkin"] is None`), `test_get_today_checkin_after_post`(`mini_app.post("/api/v1/today/checkin", json={"fatigue": 6, "pain": "none"})` 후 GET → `body["data"]["checkin"]["fatigue"] == 6`).
  (3) `frontend/src/lib/api/today.ts` — `import type`에 `CheckinRow` 추가하고 추가:
  ```ts
  export function getTodayCheckin(): Promise<CheckinRow | null> {
  	return apiFetch<{ checkin: CheckinRow | null }>('/today/checkin').then((r) => r.checkin);
  }
  ```
  (4) `frontend/src/routes/coach/+page.ts` — `CoachPageData`에 `checkin: CheckinRow | null;` 추가(`CheckinRow`는 `$lib/types`에서 import), `getTodayCheckin`을 `$lib/api/today`에서 import, `Promise.all`에 세 번째 항목 `getTodayCheckin().catch(() => null)`을 추가해 `const [threadsResult, activePlan, checkin] = await Promise.all([...])`로 받고 두 `return`(에러/정상) 모두에 `checkin`을 포함.
  (5) `frontend/src/routes/coach/+page.svelte` — `QuickInput` import, `import { postCheckin } from '$lib/api/today';`, 타입 import에 `PainLevel`·`CheckinRow` 추가, 스크립트에 추가:
  ```ts
  let checkin = $state<CheckinRow | null>(data.checkin);
  let savingCheckin = $state(false);
  let checkinError = $state<string | null>(null);
  async function handleSaveCheckin(value: { fatigue?: number; pain?: PainLevel; note?: string }) {
  	savingCheckin = true;
  	checkinError = null;
  	try {
  		checkin = await postCheckin(value);
  	} catch (e) {
  		checkinError = e instanceof Error ? e.message : '저장에 실패했습니다.';
  	} finally {
  		savingCheckin = false;
  	}
  }
  ```
  마크업 — `{#if !isCreating}` 블록 안, 기존 "플랜 섹션"(`<!-- 플랜 섹션 -->` `<div class="border-t …">`) 바로 뒤(같은 `{#if}` 안)에 추가(03e 5-A 순서: 대화·새 대화·주제·플랜·QuickInput):
  ```svelte
  <div class="flex flex-col gap-1 border-t border-border-subtle px-4 py-3">
  	<QuickInput
  		compact
  		existing={checkin
  			? {
  					fatigue: checkin.fatigue ?? undefined,
  					pain: checkin.pain ?? undefined,
  					note: checkin.note ?? undefined,
  					timestamp: checkin.created_at
  				}
  			: undefined}
  		saving={savingCheckin}
  		onSave={handleSaveCheckin}
  	/>
  	<p class="text-xs text-fg-muted">입력한 컨디션은 Coach 답변에 자동으로 반영됩니다.</p>
  	{#if checkinError}
  		<p class="text-xs text-semantic-red">{checkinError}</p>
  	{/if}
  </div>
  ```
  **리뷰(2026-09-24)**: 스펙대로 구현됨 — 이탈 없음(비용 $0.92). 5개 파일 전부 명세 코드와 일치: `GET /today/checkin` 라우트(`get_todays_checkin` 재사용), 테스트 2개,
  `getTodayCheckin()`, Coach 홈 로더에 체크인 병렬 조회(`.catch(() => null)`), Coach 홈 마지막 섹션에 compact QuickInput + "입력한 컨디션은 Coach 답변에 자동으로 반영됩니다"
  캡션(직전 유닛 `COACH-CHECKIN-CONTEXT`가 배선을 끝내 사실). `pytest tests/test_api_today.py`·`npm run check`(0 errors)/`build` 통과.
  <!-- autopilot: {"stage": "done", "mode": "auto", "attempts": 1, "deps": ["P7-IMPL-COACH-CHECKIN-CONTEXT"], "kind": "code", "scope": ["src/api/routes_today.py", "tests/test_api_today.py", "frontend/src/lib/api/today.ts", "frontend/src/routes/coach/+page.ts", "frontend/src/routes/coach/+page.svelte"], "verify": ["python3 -m pytest tests/test_api_today.py -q", "cd frontend && npm install && npm run check && npm run build"]} -->
- **[P7-IMPL-ACTIVITIES-LIST-MOBILE]** `03c-library.md` 3-B 활동 목록 — 모바일에서 페이스·심박이 안 보이는 문제 + 검색·거리 필터 누락 수정. 백엔드(쿼리
  파라미터 2개) + 프론트, 2026-09-24 합성 데이터 스모크(390px 뷰포트)로 발견, 설계 근거는 `DECISIONS.md`의 `[P7-IMPL-ACTIVITIES-LIST-MOBILE]` 항목 필독.
  현황: 목록 행이 한 줄 flex인데 페이스·심박 `<span>`에 `hidden … sm:inline`이 붙어 **폰(390px)에선 안 보임**(하단 3탭 모바일 우선 앱에서 3-B 목업의
  `5:27/km HR 138`이 사라짐), 03c 3-B의 `[검색...]`·`[거리 ▾]` 필터가 없음. `activity_service.get_activity_list()`는 이미 `search`(이름 LIKE)·
  `min_distance_m` 필터를 지원하는데 라우트가 안 받음. **이 명세의 코드는 그대로 구현할 것 — 구조를 바꾸고 싶으면 `DECISIONS.md`에 사유를 적고 중단.** **구현**:
  (1) `src/api/routes_library.py` `get_library_activities()` — `to` 처리 바로 뒤(`try: page = …` 앞)에 추가:
  ```python
      if request.args.get("q", "").strip():
          filters["search"] = request.args["q"].strip()
      if request.args.get("min_km"):
          try:
              filters["min_distance_m"] = float(request.args["min_km"]) * 1000
          except ValueError:
              return api_error("INVALID_PARAM", "min_km는 숫자여야 합니다.", 400)
  ```
  (2) `tests/test_api_library.py` — 기존 `mini_app` 픽스처(활동 2개: 아침 러닝 10km·자전거 20km)로 테스트 3개 추가: `test_list_activities_search_q`(`?q=아침` → 200, `total == 1`, 이름 "아침 러닝"), `test_list_activities_min_km`(`?min_km=15` → `total == 1`(자전거), `?min_km=5` → `total == 2`), `test_list_activities_min_km_invalid`(`?min_km=abc` → 400).
  (3) `frontend/src/lib/api/library.ts` — `ActivitiesFilters`에 `q?: string; min_km?: number | string;` 추가, `getActivities()`에 `if (filters.q) params.set('q', filters.q); if (filters.min_km) params.set('min_km', String(filters.min_km));` 추가.
  (4) `frontend/src/routes/library/activities/+page.svelte` 스크립트 — 필터 상태 옆에 추가하고 `loadPage`를 갱신(요청 경합 방지: 늦게 온 이전 응답이 최신 결과를 덮지 않게 요청 번호로 무시):
  ```ts
  let filterQuery = $state('');
  let filterMinKm = $state('');
  let searchTimer: ReturnType<typeof setTimeout> | undefined;
  let reqSeq = 0;
  function scheduleSearch() {
  	clearTimeout(searchTimer);
  	searchTimer = setTimeout(applyFilters, 300);
  }
  ```
  `loadPage` 안에서 `loading = true;` 직후 `const seq = ++reqSeq;`, `getActivities({...})` 인자에 `q: filterQuery.trim() || undefined, min_km: filterMinKm || undefined` 추가, `await` 직후 `if (seq !== reqSeq) return;`(결과 반영 전), `finally`의 `loading = false`는 `if (seq === reqSeq) loading = false;`로 바꾼다.
  (5) 같은 파일 필터 바(`<!-- 필터 바 -->` `<div class="flex flex-wrap items-center gap-2 …">`) 맨 앞에 검색 입력, 종목 `<select>` 뒤에 거리 선택 추가:
  ```svelte
  <input type="search" bind:value={filterQuery} oninput={scheduleSearch} placeholder="이름 검색" aria-label="이름 검색" class="min-w-0 flex-1 rounded border border-border-subtle bg-surface-2 px-2 py-1 text-sm text-fg-primary placeholder:text-fg-muted" />
  <select bind:value={filterMinKm} onchange={applyFilters} class="rounded border border-border-subtle bg-surface-2 px-2 py-1 text-sm text-fg-primary" aria-label="최소 거리">
  	<option value="">거리 전체</option>
  	<option value="5">5km 이상</option>
  	<option value="10">10km 이상</option>
  	<option value="21">21km 이상</option>
  </select>
  ```
  (6) 같은 파일 목록 행(`{#each activities as act (act.id)}` 안의 `<a …>…</a>` 전체)을 모바일에서도 페이스·심박이 보이는 2줄 행으로 교체:
  ```svelte
  <a href="{base}/library/{act.id}" class="flex flex-col gap-1 px-4 py-3 hover:bg-surface-2 active:bg-surface-3">
  	<div class="flex items-center gap-2">
  		<span class="min-w-0 flex-1 truncate text-sm font-medium">{act.name}</span>
  		<span class="shrink-0 rounded px-1.5 py-0.5 text-[10px] text-white {providerBadgeClass(act.source as ProviderKey)}">{providerLabel(act.source as ProviderKey)}</span>
  		<span class="shrink-0 text-fg-muted">›</span>
  	</div>
  	<div class="flex flex-wrap items-center gap-x-3 gap-y-0.5 text-xs text-fg-secondary">
  		<span class="text-fg-muted">{formatDate(act.start_time)}</span>
  		{#if act.distance_m != null}<span class="font-mono">{formatDistance(act.distance_m)}</span>{/if}
  		{#if act.duration_sec != null}<span class="font-mono">{formatDuration(act.duration_sec)}</span>{/if}
  		{#if act.avg_pace_sec_km != null}<span class="font-mono">{formatPace(act.avg_pace_sec_km)}</span>{/if}
  		{#if act.avg_hr != null}<span class="font-mono">HR {act.avg_hr}</span>{/if}
  	</div>
  </a>
  ```
  파일 상단 주석 `// 03c-library.md 3-B — 활동 목록. sport/날짜 필터 + 페이지네이션.`을 `// 03c-library.md 3-B — 활동 목록. 종목·날짜·거리 필터 + 이름 검색 + 더 불러오기.`로 교체.
  **리뷰(2026-09-24)**: 대체로 스펙대로 — 비용 $0.81. 2줄 행(이름+배지+› / 날짜·거리·시간·페이스·심박, 폰에서도 페이스·심박 표시)·검색·거리 필터·백엔드 파라미터·테스트 3개가 동작.
  편차 2건: (1) 파라미터 이름을 명세의 `q`/`min_km` 대신 `search`/`dist_min`으로 씀(백엔드·프론트·테스트가 일관돼 있어 수용), (2) 명세가 요구한 **요청 경합 방지**(늦게 온 이전
  응답이 최신 결과를 덮지 않게 요청 번호로 무시)를 빠뜨림 → 병합 후 리뷰어가 `reqSeq` 가드를 직접 추가. `pytest tests/test_api_library.py`·`npm run check`(0 errors)/`build` 통과.
  <!-- autopilot: {"stage": "done", "mode": "auto", "attempts": 1, "deps": ["P7-IMPL-COACH-HOME-QUICKINPUT"], "kind": "code", "scope": ["src/api/routes_library.py", "tests/test_api_library.py", "frontend/src/lib/api/library.ts", "frontend/src/routes/library/activities/+page.svelte"], "verify": ["python3 -m pytest tests/test_api_library.py -q", "cd frontend && npm install && npm run check && npm run build"]} -->
- **[P7-IMPL-METRICS-BROWSER-PROVIDER]** `03c-library.md` 3-E 메트릭 브라우저 — Provider 배지(P3) + `[모든 Provider ▾]` 필터. 프론트 전용, 2026-09-24
  합성 데이터 스모크로 발견, 설계 근거는 `DECISIONS.md`의 `[P7-IMPL-METRICS-BROWSER-PROVIDER]` 항목 필독. 현황: 카드가 provider를 `<span class="text-[10px]
  text-fg-muted">{m.provider}</span>`로 원문(`runpulse`, `garmin`) 텍스트만 찍어 다른 화면(MetricCell·활동 목록)의 색 배지·표기 규칙과 다르고, 3-E의
  `[모든 Provider ▾]` 필터가 없음(P3 위반). **이 명세의 코드는 그대로 구현할 것 — 구조를 바꾸고 싶으면 `DECISIONS.md`에 사유를 적고 중단.** **구현**:
  `frontend/src/routes/library/metrics/+page.svelte` 만 수정 —
  (1) 스크립트: `import { providerLabel, providerBadgeClass } from '$lib/provider';` 추가, 타입 import에 `ProviderKey` 추가(`import type { MetricBrowserEntry, ProviderKey } from '$lib/types';`), 기존 `visibleCategories` 정의(`const visibleCategories = $derived(selectedCategory === 'all' ? categories : categories.filter(...))`)를 삭제하고 아래로 교체:
  ```ts
  // provider 필터 ('all' + 실제 등장 provider) — 등장 provider가 2종 이상일 때만 필터 행을 보인다.
  let selectedProvider = $state<string>('all');
  const providers = $derived([
  	...new Set(categories.flatMap((c) => c.metrics.map((m) => m.provider).filter((p): p is string => !!p)))
  ]);
  const visibleCategories = $derived(
  	categories
  		.filter((c) => selectedCategory === 'all' || c.category === selectedCategory)
  		.map((c) => ({
  			...c,
  			metrics: c.metrics.filter((m) => selectedProvider === 'all' || m.provider === selectedProvider)
  		}))
  		.filter((c) => c.metrics.length > 0)
  );
  ```
  (2) 마크업 — 카테고리 칩 행(`<!-- 카테고리 칩 필터 -->` `<div class="flex gap-2 overflow-x-auto border-b …">…</div>`) 바로 뒤에 추가:
  ```svelte
  {#if providers.length > 1}
  	<div class="flex gap-2 overflow-x-auto border-b border-border-subtle px-4 py-2">
  		<button
  			class="shrink-0 rounded-full px-3 py-1 text-xs {selectedProvider === 'all' ? 'bg-fg-primary text-surface-1' : 'bg-surface-2 text-fg-secondary'}"
  			onclick={() => (selectedProvider = 'all')}
  		>모든 Provider</button>
  		{#each providers as p}
  			<button
  				class="shrink-0 rounded-full px-3 py-1 text-xs {selectedProvider === p ? 'bg-fg-primary text-surface-1' : 'bg-surface-2 text-fg-secondary'}"
  				onclick={() => (selectedProvider = p)}
  			>{providerLabel(p as ProviderKey)}</button>
  		{/each}
  	</div>
  {/if}
  ```
  (3) 카드 안의 `{#if m.provider}<span class="text-[10px] text-fg-muted">{m.provider}</span>{/if}`를 아래로 교체:
  ```svelte
  {#if m.provider}
  	<span class="self-start rounded px-1.5 py-0.5 text-[10px] text-white {providerBadgeClass(m.provider as ProviderKey)}">{providerLabel(m.provider as ProviderKey)}</span>
  {/if}
  ```
  `categories`가 비었거나 필터 결과가 비었을 때 기존 빈 상태("데이터 수집 중")는 그대로 둔다. 백엔드·테스트 파일은 건드리지 않음(프론트 전용 — 검증은 `npm run check`/`build`).
  리뷰 2026-09-24: 스펙 대비 이탈 1건 — Provider 필터를 결정(칩 행·provider 1종이면 숨김)과 달리 항상 보이는 드롭다운으로 구현, DECISIONS 기록·중단 없이 진행. 배지(providerLabel/providerBadgeClass)·빈 카테고리 숨김·npm check/build 통과. main에서 칩 행 + provider>1 조건으로 교정(base 키 기준 필터는 유지 — formula 버전별 칩 폭증 방지).
  <!-- autopilot: {"stage": "done", "mode": "auto", "attempts": 1, "deps": ["P7-IMPL-ACTIVITIES-LIST-MOBILE"], "kind": "code", "scope": ["frontend/src/routes/library/metrics/+page.svelte"], "verify": ["cd frontend && npm install && npm run check && npm run build"]} -->
- **[P7-IMPL-EVIDENCE-EMPTY-LABEL]** `03g-common-patterns.md` 7-3 — "원천 데이터가 없는 결론은 '(데이터 부족 — 추후 업데이트)' 레이블 표시". 프론트 전용, 2026-09-24
  스펙 대조로 발견(`frontend/src`에 "데이터 부족" 문구 0건 — 근거 칩이 하나도 없는 AI 결론이 아무 표시 없이 나가서 사용자가 "근거가 있는데 안 보이는 건지 없는 건지" 구분할 수 없음),
  설계 근거는 `DECISIONS.md`의 `[P7-IMPL-EVIDENCE-EMPTY-LABEL]` 항목 필독. **이 명세의 코드는 그대로 구현할 것 — 구조를 바꾸고 싶으면 `DECISIONS.md`에 사유를 적고 중단.** **구현** — 세 곳 모두 "근거 칩 목록이 비었을 때"의 else 분기만 추가하고 나머지는 건드리지 않는다:
  (1) `frontend/src/lib/components/RecommendationCard.svelte` — `{#if recommendation.evidence.length > 0}<div class="flex flex-wrap gap-1.5">…</div>{/if}` 의 `{/if}` 앞에 `{:else}` 분기를 추가: `{:else}<p class="text-xs text-fg-muted">(데이터 부족 — 추후 업데이트)</p>`.
  (2) `frontend/src/routes/today/+page.svelte` — L2 내러티브의 `<!-- Evidence 칩 -->` 블록 `{#if narrative.evidence.length > 0}<div class="flex flex-wrap gap-2">…</div>{/if}` 의 `{/if}` 앞에 `{:else}<p class="text-xs text-fg-muted">(데이터 부족 — 추후 업데이트)</p>` 추가.
  (3) `frontend/src/lib/components/MonthNarrative.svelte` — `{#if narrativeData.evidence.length > 0}<div class="flex flex-wrap gap-2">…</div>{/if}` 의 `{/if}` 앞에 같은 `{:else}<p class="text-xs text-fg-muted">(데이터 부족 — 추후 업데이트)</p>` 추가.
  백엔드·테스트 파일은 건드리지 않음(프론트 전용 — 검증은 `npm run check`/`build`).
  리뷰 2026-09-24: 3곳(RecommendationCard·Today L2·MonthNarrative) else 분기만 추가 — 명세와 일치, 이탈 없음. npm check 0 errors / build OK. 합성 빈 DB에서 레이블 노출 확인 예정(병합 후 스모크).
  <!-- autopilot: {"stage": "done", "mode": "auto", "attempts": 1, "deps": ["P7-IMPL-METRICS-BROWSER-PROVIDER"], "kind": "code", "scope": ["frontend/src/lib/components/RecommendationCard.svelte", "frontend/src/routes/today/+page.svelte", "frontend/src/lib/components/MonthNarrative.svelte"], "verify": ["cd frontend && npm install && npm run check && npm run build"]} -->
- **[P7-IMPL-PLAN-ADAPTATION-STATE]** `03e-coach.md` 5-F 플랜 상세의 "적응 상태" 섹션(ACWR·HRV 기준 대비·주간 피로도 평균) — 백엔드(읽기 전용 서비스 +
  GET 1개) + 프론트, 2026-09-24 스펙 대조로 발견(5-F 목업엔 있으나 `coach/plan/[id]` 화면엔 없음 — 플랜이 "내 상태에 묶인다"는 P7 State-Bound Plan의 근거
  표시가 빠져 있음), 설계 근거는 `DECISIONS.md`의 `[P7-IMPL-PLAN-ADAPTATION-STATE]` 항목 필독. 데이터는 전부 이미 있다(`acwr` 일별 메트릭, `daily_wellness`
  HRV, `user_inputs` 체크인 피로도). **이 명세의 코드는 그대로 구현할 것 — 구조를 바꾸고 싶으면 `DECISIONS.md`에 사유를 적고 중단.** **구현**:
  (1) 신규 `src/services/adaptation_service.py`:
  ```python
  """플랜 적응 상태 서비스 — 03e-coach.md 5-F "적응 상태"(ACWR·HRV·주간 피로도). 읽기 전용."""
  from __future__ import annotations
  import sqlite3
  from datetime import date as _date
  def _acwr_zone(v: float) -> str:
      """Gabbett 구간 — 5-F 목업의 '적정 범위 (0.8~1.3)'."""
      if v < 0.8:
          return "저부하"
      if v <= 1.3:
          return "적정"
      if v <= 1.5:
          return "주의"
      return "위험"
  def _hrv_zone(delta_pct: float) -> str:
      """기준(주간 평균) 대비 변화율 — 5-F 목업의 'HRV 58ms ●기준 −7% (경계)'."""
      if delta_pct >= -5:
          return "정상"
      if delta_pct >= -10:
          return "경계"
      return "저하"
  def get_adaptation_status(conn: sqlite3.Connection, date: str | None = None) -> dict:
      """date 기준 적응 상태. 없는 항목은 None(에러 아님).
      반환: {"date", "acwr": {"value","zone","date"}|None,
             "hrv": {"value","baseline","delta_pct","zone"}|None,
             "fatigue_avg": {"value","n"}|None}
      """
      if date is None:
          date = _date.today().isoformat()
      acwr = None
      row = conn.execute(
          "SELECT scope_id, numeric_value FROM metric_store"
          " WHERE scope_type = 'daily' AND metric_name = 'acwr' AND is_primary = 1"
          "   AND scope_id <= ? AND numeric_value IS NOT NULL"
          " ORDER BY scope_id DESC LIMIT 1",
          (date,),
      ).fetchone()
      if row:
          acwr = {"value": round(float(row[1]), 2), "zone": _acwr_zone(float(row[1])), "date": row[0]}
      hrv = None
      row = conn.execute(
          "SELECT hrv_last_night, hrv_weekly_avg FROM daily_wellness"
          " WHERE date <= ? AND hrv_last_night IS NOT NULL ORDER BY date DESC LIMIT 1",
          (date,),
      ).fetchone()
      if row:
          value, baseline = float(row[0]), row[1]
          delta = round((value - baseline) / baseline * 100) if baseline else None
          hrv = {
              "value": value,
              "baseline": baseline,
              "delta_pct": delta,
              "zone": _hrv_zone(delta) if delta is not None else None,
          }
      fatigue_avg = None
      row = conn.execute(
          "SELECT AVG(fatigue), COUNT(fatigue) FROM user_inputs"
          " WHERE input_type = 'checkin' AND fatigue IS NOT NULL"
          "   AND input_date BETWEEN date(?, '-6 day') AND ?",
          (date, date),
      ).fetchone()
      if row and row[1]:
          fatigue_avg = {"value": round(float(row[0]), 1), "n": int(row[1])}
      return {"date": date, "acwr": acwr, "hrv": hrv, "fatigue_avg": fatigue_avg}
  ```
  (2) `src/api/routes_plan.py` — 모듈 docstring에 `GET /api/v1/coach/plan/adaptation` 언급 추가, `from src.services import plan_service, plan_template_service`를 `from src.services import adaptation_service, plan_service, plan_template_service`로 바꾸고, `get_plan_adjustment()` 뒤에 추가:
  ```python
  @api_bp.get("/coach/plan/adaptation")
  def get_plan_adaptation():
      dpath = db_path()
      if not dpath.exists():
          return api_error("NOT_FOUND", "running.db 없음", 503)
      conn = sqlite3.connect(str(dpath))
      try:
          result = adaptation_service.get_adaptation_status(conn)
      finally:
          conn.close()
      return api_ok({"adaptation": result})
  ```
  (3) 신규 `tests/test_adaptation_service.py`(`db_conn` 픽스처, 메트릭은 `INSERT INTO metric_store (scope_type, scope_id, metric_name, provider, numeric_value, is_primary) VALUES ('daily', ?, 'acwr', 'runpulse', ?, 1)`, 웰니스는 `INSERT INTO daily_wellness (date, hrv_last_night, hrv_weekly_avg) VALUES (?, ?, ?)`, 피로도는 `today_service.save_checkin(db_conn, fatigue=…, input_date=…)`) — 케이스: (a) 데이터 전무 → `acwr`/`hrv`/`fatigue_avg` 모두 None, (b) ACWR 구간 경계 `_acwr_zone`(0.7→"저부하", 0.8→"적정", 1.3→"적정", 1.4→"주의", 1.5→"주의", 1.6→"위험"), (c) `date` 이전 최신 ACWR 선택(미래 날짜 행은 무시)하고 `acwr["date"]`가 그 행의 scope_id, (d) HRV 기준 대비(value 58, baseline 62 → delta_pct −6, zone "경계"; value 61 baseline 62 → "정상"; value 50 baseline 62 → "저하"), (e) `hrv_weekly_avg`가 NULL이면 `delta_pct`·`zone` None이고 `value`는 있음, (f) 피로도 평균: 최근 7일 이내 체크인 3건(4,6,8) → `value == 6.0`, `n == 3`, 8일 전 체크인은 제외.
  (4) `tests/test_api_plan.py` — 기존 `mini_app` 픽스처로 2개 추가: `test_get_plan_adaptation_empty`(200, `body["data"]["adaptation"]`의 `acwr`/`hrv`/`fatigue_avg`가 모두 None), `test_get_plan_adaptation_with_acwr`(픽스처가 만든 DB에 `metric_store` acwr 행을 오늘 날짜(`date.today().isoformat()`)로 삽입한 뒤 GET → `adaptation["acwr"]["zone"] == "적정"`(값 1.12) — 픽스처가 DB 경로를 안 돌려주면 `tmp_path`를 쓰는 별도 헬퍼로 처리).
  (5) `frontend/src/lib/types/index.ts` — 파일 끝에 추가:
  ```ts
  // ── PlanAdaptation (5-F — /api/v1/coach/plan/adaptation) ─────────────────────
  export interface PlanAdaptation {
  	date: string;
  	acwr: { value: number; zone: string; date: string } | null;
  	hrv: { value: number; baseline: number | null; delta_pct: number | null; zone: string | null } | null;
  	fatigue_avg: { value: number; n: number } | null;
  }
  ```
  (6) `frontend/src/lib/api/plan.ts` — `import type` 목록에 `PlanAdaptation` 추가, 추가:
  ```ts
  export function getPlanAdaptation(): Promise<PlanAdaptation> {
  	return apiFetch<{ adaptation: PlanAdaptation }>('/coach/plan/adaptation').then((r) => r.adaptation);
  }
  ```
  (7) `frontend/src/routes/coach/plan/[id]/+page.ts` — `PlanDetailPageData`에 `adaptation: PlanAdaptation | null;` 추가(`PlanAdaptation`은 `$lib/types` import), `getPlanAdaptation`을 `$lib/api/plan`에서 import, `Promise.all`에 세 번째 항목 `getPlanAdaptation().catch(() => null)`을 추가해 `const [plan, adjustment, adaptation] = await Promise.all([...])`로 받고 두 `return`(ID 오류/정상) 모두에 `adaptation`을 포함(ID 오류 분기는 `adaptation: null`).
  (8) `frontend/src/routes/coach/plan/[id]/+page.svelte` — `MetricBreakdown` import 추가, 스크립트에 추가:
  ```ts
  let drillAcwr = $state(false);
  const ZONE_CLASS: Record<string, string> = {
  	적정: 'text-semantic-green',
  	정상: 'text-semantic-green',
  	저부하: 'text-semantic-amber',
  	주의: 'text-semantic-amber',
  	경계: 'text-semantic-amber',
  	위험: 'text-semantic-red',
  	저하: 'text-semantic-red'
  };
  function zoneClass(z: string): string {
  	return ZONE_CLASS[z] ?? 'text-fg-secondary';
  }
  ```
  마크업 — "이번 주 워크아웃 목록" 블록(`<!-- 이번 주 워크아웃 목록 -->` `<div class="border-b …">…</div>`) 바로 뒤에 추가(P7 State-Bound Plan: 플랜이 어떤 상태 근거로 조정되는지 보여줌. ACWR 행만 `metric_store` 근거가 있어 탭하면 계산 분해가 열리고 HRV·피로도는 원천이 다른 테이블이라 비대화형):
  ```svelte
  {#if data.adaptation && (data.adaptation.acwr || data.adaptation.hrv || data.adaptation.fatigue_avg)}
  	<div class="border-b border-border-subtle px-4 py-3">
  		<p class="mb-2 text-xs uppercase tracking-wide text-fg-muted">적응 상태</p>
  		<ul class="flex flex-col gap-2 text-sm">
  			{#if data.adaptation.acwr}
  				{@const a = data.adaptation.acwr}
  				<li>
  					<button type="button" onclick={() => (drillAcwr = true)} class="flex w-full items-center gap-2 text-left hover:bg-surface-2">
  						<span class="w-24 shrink-0 text-fg-secondary">ACWR</span>
  						<span class="font-mono font-medium">{a.value.toFixed(2)}</span>
  						<span class="text-xs {zoneClass(a.zone)}">● {a.zone}</span>
  						<span class="ml-auto text-xs text-fg-muted">적정 0.8~1.3 ›</span>
  					</button>
  				</li>
  			{/if}
  			{#if data.adaptation.hrv}
  				{@const h = data.adaptation.hrv}
  				<li class="flex items-center gap-2">
  					<span class="w-24 shrink-0 text-fg-secondary">HRV</span>
  					<span class="font-mono font-medium">{Math.round(h.value)}ms</span>
  					{#if h.delta_pct != null && h.zone}
  						<span class="text-xs {zoneClass(h.zone)}">● 기준 {h.delta_pct > 0 ? '+' : ''}{h.delta_pct}% ({h.zone})</span>
  					{/if}
  				</li>
  			{/if}
  			{#if data.adaptation.fatigue_avg}
  				{@const f = data.adaptation.fatigue_avg}
  				<li class="flex items-center gap-2">
  					<span class="w-24 shrink-0 text-fg-secondary">피로도 주간 평균</span>
  					<span class="font-mono font-medium">{f.value.toFixed(1)} / 10</span>
  					<span class="text-xs text-fg-muted">({f.n}회 입력)</span>
  				</li>
  			{/if}
  		</ul>
  	</div>
  {/if}
  ```
  그리고 파일 맨 끝(최상위 `<div class="flex flex-col">…</div>` 뒤)에 추가: `{#if drillAcwr && data.adaptation?.acwr}<MetricBreakdown slug="acwr" scopeType="daily" scopeId={data.adaptation.acwr.date} onClose={() => { drillAcwr = false; }} />{/if}`. 파일이 300줄을 넘지 않게 주의.
  리뷰 2026-09-24: adaptation_service·GET /coach/plan/adaptation·테스트 명세와 일치(이탈 없음, 서비스 코드 바이트 동일). 워크트리 pytest: adaptation 36 통과(전체는 워크트리 경로 의존 테스트 3건만 실패 — 환경 한정, main에서 재확인). npm check 0 errors/build OK. files_index 재생성은 병합 후 main에서.
  <!-- autopilot: {"stage": "done", "mode": "auto", "attempts": 1, "deps": ["P7-IMPL-EVIDENCE-EMPTY-LABEL"], "kind": "code", "scope": ["src/services/adaptation_service.py", "src/api/routes_plan.py", "tests/test_adaptation_service.py", "tests/test_api_plan.py", "frontend/src/lib/types/index.ts", "frontend/src/lib/api/plan.ts", "frontend/src/routes/coach/plan/[id]/+page.ts", "frontend/src/routes/coach/plan/[id]/+page.svelte"], "verify": ["python3 -m pytest tests/test_adaptation_service.py tests/test_api_plan.py -q", "cd frontend && npm install && npm run check && npm run build"]} -->
- **[P7-IMPL-NARRATIVE-CACHE]** Today L2 성장 내러티브의 LLM 호출을 `ai_cache`로 캐시 — 백엔드, 2026-09-24 합성 데이터 서버 점검 중 발견, 설계 근거는 `DECISIONS.md`의
  `[P7-IMPL-NARRATIVE-CACHE]` 항목 필독. 현황: `today_service.get_today_narrative()`가 **호출될 때마다** AI provider 체인(Gemini→Groq 등)을 순서대로 호출하고, Today 프론트
  로더(`Promise.all`)가 그 응답을 기다린다 → AI 키가 유효한 실사용에선 Today를 열 때마다 LLM 호출 1회(지연 수 초 + 토큰 비용). 같은 저장소에 이미 `src/ai/ai_cache.py`(ADR-011:
  신규 활동·웰니스·날짜 변경 시 무효화 + 8시간 TTL)가 있는데 내러티브는 안 씀. **이 명세의 코드는 그대로 구현할 것 — 구조를 바꾸고 싶으면 `DECISIONS.md`에 사유를 적고 중단.** **구현**:
  (1) `src/services/_narrative.py` — 파일 끝에 추가(`today_service.py`가 289/300줄이라 헬퍼는 여기에 둔다):
  ```python
  _CACHE_TAB = "today_narrative"
  def generate_ai_narrative(conn, chain: list, prompt: str, config: dict | None, cache_key: str) -> str | None:
      """AI 내러티브 텍스트 — ai_cache(ADR-011: 신규 활동·웰니스·날짜 변경 시 무효화, 8h TTL)에 있으면 재사용,
      없으면 provider 체인을 순서대로 호출하고 성공 시 저장한다. 전부 실패하면 None(호출부가 규칙 기반 fallback).
      규칙 기반 fallback 결과는 캐시하지 않는다(싸고, AI가 복구되면 바로 AI 결과로 바뀌어야 함).
      """
      import logging
      from src.ai import ai_cache
      from src.ai.chat_engine import _call_provider
      cached = ai_cache.get_cached(conn, _CACHE_TAB, cache_key)
      if cached and cached.get("text"):
          return cached["text"]
      for prov in chain:
          text = _call_provider(prov, prompt, config)
          if text:
              try:
                  ai_cache.set_cached(conn, _CACHE_TAB, cache_key, {"text": text})
              except Exception:
                  logging.getLogger(__name__).warning("내러티브 캐시 저장 실패", exc_info=True)
              return text
      return None
  ```
  (`_call_provider`는 반드시 함수 안에서 import — 기존 테스트가 `patch("src.ai.chat_engine._call_provider", ...)`로 목업하므로 호출 시점에 모듈 속성을 읽어야 한다.)
  (2) `src/services/today_service.py` `get_today_narrative()` — 상단 지역 import에 `generate_ai_narrative`를 추가(`from src.services._narrative import (attach_drill, build_evidence, …)` 목록에 넣고, 이제 안 쓰는 `_call_provider` import는 `from src.ai.chat_engine import _build_chat_provider_chain, get_ai_provider`로 정리), 그리고 AI 생성 블록(`if chain:` 안 `prompt = build_narrative_prompt(...)` 다음의 `for prov in chain: result = _call_provider(prov, prompt, config) … break` 루프)을 아래로 교체 — `prompt` 생성 코드는 그대로 두고 루프만 교체:
  ```python
          text = generate_ai_narrative(conn, chain, prompt, config, cache_key=f"{month_start}:{date}")
          if text:
              source = "ai"
  ```
  (캐시 키에 조회 달의 시작일과 기준일을 모두 넣는다 — 과거 달 조회(`year`/`month`)와 이번 달이 서로 캐시를 덮지 않고, 날짜가 바뀌면 자연히 새 키.) `text = None`/`source = "rule"` 초기화와 그 뒤 `if text is None:` 규칙 기반 fallback은 그대로 둔다.
  (3) 신규 `tests/test_narrative_cache.py`(`db_conn` 픽스처 + `unittest.mock.patch`; 기존 `tests/test_today_service.py`의 AI 테스트처럼 `patch("src.ai.chat_engine._call_provider", …)`와 `patch("src.ai.chat_engine._build_chat_provider_chain", return_value=["fake"])`, `patch("src.ai.chat_engine.get_ai_provider", return_value="gemini")` 사용, `today_service.get_today_narrative(db_conn, date="2026-09-22", config={})` 호출) — 케이스: (a) 같은 인자로 두 번 호출하면 `_call_provider` 호출 1회뿐이고 두 결과 모두 `source == "ai"`·같은 `text`, (b) 다른 `date`(예: "2026-09-21")면 다시 호출됨(호출 2회), (c) 모든 provider가 None이면 `source == "rule"`이고 캐시에 아무것도 저장되지 않아 다음 호출에 다시 provider를 시도함(호출 횟수가 늘어남), (d) 첫 호출 후 새 활동을 추가하면(`INSERT INTO activity_summaries …`로 MAX(id) 변경) 캐시가 무효화되어 다시 호출됨, (e) `generate_ai_narrative`를 직접 호출: 체인 첫 provider가 None·둘째가 텍스트면 둘째 텍스트를 반환하고 캐시에 저장됨(`ai_cache.get_cached(db_conn, "today_narrative", key)["text"]`).
  리뷰 2026-09-24: 결정(DECISIONS)과 일치 — ai_cache 재사용(탭 today_narrative, 키 월시작:기준일), AI 성공만 캐시, 저장 실패 삼킴, 헬퍼는 _narrative.py로(today_service 299줄). **명세 이탈 1건(수용)**: 명세의 `generate_ai_narrative()`(텍스트만 캐시, evidence·milestones는 매번 재계산) 대신 `get/set_narrative_cache()`로 **결과 dict 전체**를 캐시하고 조회 최상단에서 조기 반환(DB 조회까지 생략) — 무효화가 ADR-011(신규 활동·웰니스·날짜·8h)에 위임돼 evidence 신선도 손실은 같은 조건에서만 생기고 응답이 더 빨라 그대로 둠. 테스트 11개 통과(캐시 히트 시 AI 미호출, fallback 미캐시, 신규 활동 시 무효화). 워크트리 today/narrative 관련 59 통과.
  <!-- autopilot: {"stage": "done", "mode": "auto", "attempts": 1, "deps": ["P7-IMPL-PLAN-ADAPTATION-STATE"], "kind": "code", "scope": ["src/services/_narrative.py", "src/services/today_service.py", "tests/test_narrative_cache.py"], "verify": ["python3 -m pytest tests/test_narrative_cache.py tests/test_today_service.py tests/test_api_today.py -q"]} -->
- **[P7-IMPL-PROVIDER-STATUS]** `03c-library.md` 3-A Library 홈의 "Provider 데이터 현황"(P3 Provider Transparency) — 백엔드(읽기 전용 서비스 + GET 1개) + 프론트, 2026-09-24 합성 데이터 스모크에서 발견, 설계 근거는 `DECISIONS.md`의 `[P7-IMPL-PROVIDER-STATUS]` 항목 필독. 현황: `frontend/src/routes/library/+page.svelte` 의 "Provider 현황" 섹션이 "준비 중 — 연결 상태·마지막 동기화 정보는 후속 업데이트에서 제공됩니다."라는 문구뿐 — 3-A 목업은 Provider별 `[Garmin ●연결] 마지막 동기화 2시간 전 · 활동 312건` 행을 요구한다. 데이터는 이미 있다(`activity_summaries.source`, `source_payloads.fetched_at`). **이 명세의 코드는 그대로 구현할 것 — 구조를 바꾸고 싶으면 `DECISIONS.md`에 사유를 적고 중단.** **구현**:
  (1) 신규 `src/services/provider_status_service.py`:
  ```python
  """Provider 데이터 현황 서비스 — 03c-library.md 3-A "Provider 데이터 현황". 읽기 전용."""
  from __future__ import annotations
  import sqlite3
  _PROVIDERS = ("garmin", "strava", "intervals", "runalyze")
  def get_provider_status(conn: sqlite3.Connection) -> list[dict]:
      """Provider 4종 각각의 저장된 데이터 현황 — 항상 4행, 고정 순서(_PROVIDERS).
      반환: [{"provider", "activity_count", "last_activity_date", "last_synced_at", "has_data"}]
      - activity_count: activity_summaries 원본 행 수(중복 그룹 통합 전 — 그 provider가 실제로 가진 데이터)
      - last_activity_date: 그 provider 활동 중 가장 최근 start_time의 앞 10자(YYYY-MM-DD), 없으면 None
      - last_synced_at: source_payloads.fetched_at 최댓값(UTC 'YYYY-MM-DD HH:MM:SS' 문자열), 없으면 None
      - has_data: activity_count > 0 또는 last_synced_at 존재
      '연결 여부'(자격증명 유무)는 판단하지 않는다 — 7d Data 화면(data_service)의 몫.
      """
      try:
          acts = {
              r[0]: (r[1], r[2])
              for r in conn.execute(
                  "SELECT source, COUNT(*), MAX(start_time) FROM activity_summaries GROUP BY source"
              )
          }
          syncs = {
              r[0]: r[1]
              for r in conn.execute("SELECT source, MAX(fetched_at) FROM source_payloads GROUP BY source")
          }
      except sqlite3.OperationalError:
          acts, syncs = {}, {}
      out = []
      for p in _PROVIDERS:
          count, last_start = acts.get(p, (0, None))
          last_sync = syncs.get(p)
          out.append({
              "provider": p,
              "activity_count": int(count),
              "last_activity_date": last_start[:10] if last_start else None,
              "last_synced_at": last_sync,
              "has_data": bool(count) or last_sync is not None,
          })
      return out
  ```
  (2) `src/api/routes_library.py` — import 줄(`from src.services import activity_service, metrics_browser_service, ...`)에 `provider_status_service`를 알파벳 순서에 맞게 추가하고, `get_library_providers_matrix()` 함수 바로 뒤에 추가:
  ```python
  @api_bp.get("/library/providers/status")
  def get_library_providers_status():
      dpath = db_path()
      if not dpath.exists():
          return api_error("NOT_FOUND", "running.db 없음", 503)
      conn = sqlite3.connect(str(dpath))
      try:
          result = provider_status_service.get_provider_status(conn)
      finally:
          conn.close()
      return api_ok({"providers": result})
  ```
  (3) 신규 `tests/test_provider_status.py` — `db_conn` 픽스처로 서비스 테스트 4개: (a) 빈 DB → 4행이며 `[r["provider"] for r in rows] == ["garmin","strava","intervals","runalyze"]`, 전부 `activity_count == 0`·`has_data is False`·`last_synced_at is None`·`last_activity_date is None`, (b) garmin 활동 2건(`INSERT INTO activity_summaries (source, source_id, name, activity_type, start_time, distance_m, duration_sec) VALUES ('garmin','g1','a','running','2026-09-20T07:00:00Z',5000,1800)` 등, 두 번째는 `'2026-09-22T07:00:00Z'`) → garmin `activity_count == 2`, `last_activity_date == "2026-09-22"`, `has_data is True`, 나머지 provider는 `has_data is False`, (c) `INSERT INTO source_payloads (source, entity_type, entity_id, payload, fetched_at) VALUES ('strava','activity','s1','{}','2026-09-24 03:00:00')` 와 같은 source의 더 이른 행(`'2026-09-23 01:00:00'`, entity_id `s2`) → strava `last_synced_at == "2026-09-24 03:00:00"`, 활동 0건이어도 `has_data is True`, (d) `_PROVIDERS`에 없는 source(`'coros'`) 활동은 결과에 나타나지 않음(길이 4 유지). 그리고 API 테스트 2개 — 같은 파일 안에 `tests/test_api_library.py`의 `mini_app` 픽스처와 같은 방식(임시 DB 만들고 `routes_library.db_path`를 monkeypatch, Flask 앱에 `api_bp` 등록)으로 로컬 픽스처를 만들어 (e) `GET /api/v1/library/providers/status` → 200, `body["data"]["providers"]`가 길이 4, (f) garmin 활동 1건을 넣은 DB에서 garmin 행의 `activity_count == 1`.
  (4) `frontend/src/lib/types/index.ts` — 파일 끝에 추가:
  ```ts
  // ── ProviderStatus (3-A — /api/v1/library/providers/status) ──────────────────
  export interface ProviderStatus {
  	provider: ProviderKey;
  	activity_count: number;
  	last_activity_date: string | null;
  	last_synced_at: string | null;
  	has_data: boolean;
  }
  ```
  (5) `frontend/src/lib/api/providers.ts` — `import type { ProviderComparisonData } from '$lib/types';`를 `import type { ProviderComparisonData, ProviderStatus } from '$lib/types';`로 바꾸고 파일 끝에 추가:
  ```ts
  export function getProviderStatus(): Promise<ProviderStatus[]> {
  	return apiFetch<{ providers: ProviderStatus[] }>('/library/providers/status').then((r) => r.providers);
  }
  ```
  (6) `frontend/src/routes/library/+page.ts` — `getProviderStatus`를 `$lib/api/providers`에서, `ProviderStatus`를 `$lib/types`에서 import. `LibraryHomeData`에 `providerStatus: ProviderStatus[]; providerStatusError: string | null;` 추가. `Promise.allSettled([...])`에 세 번째 항목 `getProviderStatus()`를 추가해 `const [activitiesRes, metricsRes, statusRes] = await Promise.allSettled([...])`로 받고, 기존 패턴 그대로:
  ```ts
  	const providerStatus = statusRes.status === 'fulfilled' ? statusRes.value : [];
  	const providerStatusError =
  		statusRes.status === 'rejected'
  			? (statusRes.reason as Error).message ?? 'Provider 현황을 불러올 수 없습니다.'
  			: null;
  ```
  을 계산해 `return`에 두 필드를 포함한다.
  (7) `frontend/src/routes/library/+page.svelte` — 스크립트 import: `import { formatDistance, formatDuration, formatPace, formatDate } from '$lib/format';`에 `formatRelativeTime`을 추가. 마크업의 `<!-- Provider 데이터 현황 -->` 섹션 안 `<p class="text-sm text-fg-muted">준비 중 — …</p>` 한 줄을 아래로 교체(`<h2>`는 그대로):
  ```svelte
  	{#if data.providerStatusError}
  		<p class="text-sm text-fg-muted">{data.providerStatusError}</p>
  	{:else}
  		<ul class="flex flex-col gap-2">
  			{#each data.providerStatus as ps}
  				<li class="flex items-center gap-2 text-sm">
  					<span class="shrink-0 text-xs {ps.has_data ? 'text-semantic-green' : 'text-fg-muted'}" aria-hidden="true">{ps.has_data ? '●' : '○'}</span>
  					<span class="shrink-0 rounded px-1.5 py-0.5 text-[10px] text-white {providerBadgeClass(ps.provider)}">{providerLabel(ps.provider)}</span>
  					{#if ps.has_data}
  						<span class="min-w-0 flex-1 truncate text-xs text-fg-secondary">활동 {ps.activity_count}건{#if ps.last_synced_at}{' · '}마지막 동기화 {formatRelativeTime(ps.last_synced_at)}{/if}</span>
  					{:else}
  						<span class="text-xs text-fg-muted">데이터 없음</span>
  					{/if}
  				</li>
  			{/each}
  		</ul>
  	{/if}
  ```
  (`{' · '}` 식은 Svelte가 블록 경계 공백을 잘라 "동기화" 앞뒤가 붙는 것을 막기 위한 것 — 그대로 둘 것.) 이 유닛은 "연결 여부"를 판단하지 않는다(문구는 "데이터 있음/없음" 기준 ●/○) — 자격증명 기반 연결 상태는 7d Data 화면 범위.
  리뷰 2026-09-24: **명세 이탈 다수 — main에서 교정**: (1) `has_data`가 활동 수만 봄(명세: 활동 수>0 또는 동기화 기록 존재) → 웰니스 payload만 있는 provider가 "데이터 없음"인데 "마지막 동기화 …"를 같이 표시하는 모순, (2) `sqlite3.OperationalError` 가드 누락, (3) `last_activity_date` 필드 누락(UI 미사용이라 그대로 둠), (4) API 테스트 2건 누락, (5) `$lib/format` import 중복. 화면 레이아웃(배지 + ●/○ + 동기화·활동 수)은 명세와 다르나 정보 동일해 수용. npm check 0 errors / build OK, 서비스 테스트 8개 통과.
  <!-- autopilot: {"stage": "done", "mode": "auto", "attempts": 1, "deps": ["P7-IMPL-NARRATIVE-CACHE"], "kind": "code", "scope": ["src/services/provider_status_service.py", "src/api/routes_library.py", "tests/test_provider_status.py", "frontend/src/lib/types/index.ts", "frontend/src/lib/api/providers.ts", "frontend/src/routes/library/+page.ts", "frontend/src/routes/library/+page.svelte"], "verify": ["python3 -m pytest tests/test_provider_status.py -q", "cd frontend && npm install && npm run check && npm run build"]} -->
- **[P7-IMPL-PAGE-TITLES]** 페이지별 브라우저 탭 제목 — 프론트 전용, 2026-09-24 합성 데이터 스모크에서 발견, 설계 근거는 `DECISIONS.md`의 `[P7-IMPL-PAGE-TITLES]` 항목 필독. 현황: `frontend/src`에 `<title>`이 **하나도 없다**(`+layout.svelte`의 `<svelte:head>`엔 favicon `<link>`만, `app.html`에도 title 없음) — 탭·브라우저 기록·북마크에 URL만 보이고 20개 화면이 구분되지 않는다. **이 명세의 코드는 그대로 구현할 것 — 구조를 바꾸고 싶으면 `DECISIONS.md`에 사유를 적고 중단.** **구현** — 아래 19개 `+page.svelte` 각각에서, 스크립트 블록의 닫는 `</script>` 바로 뒤(한 줄 띄우고)에 `<svelte:head><title>…</title></svelte:head>` 한 줄만 추가한다(파일의 다른 부분은 건드리지 않는다. `<script>` 블록이 없는 파일은 맨 위에 추가). 제목 형식은 항상 `<화면 이름> · RunPulse`. **`+layout.svelte`와 `app.html`에는 기본 `<title>`을 넣지 않는다**(같은 문서에 `<title>`이 둘이면 브라우저가 첫 번째를 쓰므로 페이지 제목이 가려진다). 화면별 제목(파일 → 제목):
  `today/+page.svelte` → `Today · RunPulse`
  `library/+page.svelte` → `Library · RunPulse`
  `library/activities/+page.svelte` → `활동 목록 · RunPulse`
  `library/[id]/+page.svelte` → `<title>{core?.name ?? '활동 상세'} · RunPulse</title>` (이 파일의 스크립트에 이미 있는 `const core = $derived(data.activity?.core ?? null)`를 그대로 사용 — 활동 이름이 탭에 뜬다)
  `library/[id]/laps/+page.svelte` → `랩 · RunPulse`
  `library/[id]/metrics/+page.svelte` → `활동 메트릭 · RunPulse`
  `library/[id]/providers/+page.svelte` → `소스 비교 · RunPulse`
  `library/[id]/streams/+page.svelte` → `스트림 · RunPulse`
  `library/metrics/+page.svelte` → `메트릭 브라우저 · RunPulse`
  `library/metrics/[slug]/+page.svelte` → `<title>{data.trend?.label ?? data.slug} · RunPulse</title>`
  `library/providers/+page.svelte` → `Provider 비교 · RunPulse`
  `library/wellness/+page.svelte` → `웰니스 · RunPulse`
  `coach/+page.svelte` → `Coach · RunPulse`
  `coach/[threadId]/+page.svelte` → `Coach 대화 · RunPulse`
  `coach/plan/+page.svelte` → `훈련 플랜 · RunPulse`
  `coach/plan/[id]/+page.svelte` → `플랜 상세 · RunPulse`
  `coach/plan/[id]/session/[date]/+page.svelte` → `세션 상세 · RunPulse`
  `coach/plan/compare/+page.svelte` → `플랜 비교 · RunPulse`
  `coach/plan/new/+page.svelte` → `새 플랜 · RunPulse`
  (루트 `routes/+page.svelte`는 항상 `/today`로 리다이렉트되므로 제외.) 정적 제목은 `<svelte:head><title>Today · RunPulse</title></svelte:head>`처럼 텍스트 그대로. 백엔드·테스트 파일은 건드리지 않음(프론트 전용 — 검증은 `npm run check`/`build`).
  리뷰 2026-09-24: 19개 파일 각 2줄(`<svelte:head><title>…`) 추가만 — 명세의 제목 표와 일치, layout/app.html 무변경, 동적 두 곳(활동 이름·메트릭 라벨) 반영. npm check 0 errors / build OK. 병합 후 합성 데이터 브라우저에서 page.title() 확인.
  <!-- autopilot: {"stage": "done", "mode": "auto", "attempts": 1, "deps": ["P7-IMPL-PROVIDER-STATUS"], "kind": "code", "scope": ["frontend/src/routes/today/+page.svelte", "frontend/src/routes/library/+page.svelte", "frontend/src/routes/library/activities/+page.svelte", "frontend/src/routes/library/[id]/+page.svelte", "frontend/src/routes/library/[id]/laps/+page.svelte", "frontend/src/routes/library/[id]/metrics/+page.svelte", "frontend/src/routes/library/[id]/providers/+page.svelte", "frontend/src/routes/library/[id]/streams/+page.svelte", "frontend/src/routes/library/metrics/+page.svelte", "frontend/src/routes/library/metrics/[slug]/+page.svelte", "frontend/src/routes/library/providers/+page.svelte", "frontend/src/routes/library/wellness/+page.svelte", "frontend/src/routes/coach/+page.svelte", "frontend/src/routes/coach/[threadId]/+page.svelte", "frontend/src/routes/coach/plan/+page.svelte", "frontend/src/routes/coach/plan/[id]/+page.svelte", "frontend/src/routes/coach/plan/[id]/session/[date]/+page.svelte", "frontend/src/routes/coach/plan/compare/+page.svelte", "frontend/src/routes/coach/plan/new/+page.svelte"], "verify": ["cd frontend && npm install && npm run check && npm run build"]} -->
- **[P7-IMPL-STREAMS-SCRUB]** `03c-library.md` 3-D 활동 스트림 — 시간 눈금 + 터치 스크럽. 프론트 전용, 2026-09-24 스펙 대조로 발견, 설계 근거는 `DECISIONS.md`의 `[P7-IMPL-STREAMS-SCRUB]` 항목 필독. 현황: `frontend/src/routes/library/[id]/streams/+page.svelte`는 스트림별 스파크라인만 세로로 나열하고 시간 눈금이 없으며(3-D 목업: `시간 → 0  15m  30m  45m  55m`) 하단에 "x축은 포인트 순서(… 정밀 시간축은 후속 과제)"라고 적혀 있다. 목업의 "마우스 호버 / 터치 스크럽 → 해당 시각 수치 표시"도 없다. **이 명세의 코드는 그대로 구현할 것 — 구조를 바꾸고 싶으면 `DECISIONS.md`에 사유를 적고 중단.** **구현**:
  (1) 신규 `frontend/src/lib/streamAxis.ts`(순수 함수 — 다른 모듈을 import하지 않는다: Node 테스트 러너가 확장자 없는 상대 import를 못 푼다):
  ```ts
  // 스트림 x축 보조 — 스파크라인은 포인트 순서(인덱스) 축이라, 눈금 라벨은 그 인덱스 지점의 실제 elapsed_sec로 붙인다.
  /** 0~1 비율을 [0, n-1] 인덱스로 (범위 밖은 clamp). n<=0이면 0. */
  export function indexAtFraction(frac: number, n: number): number {
  	if (n <= 0) return 0;
  	const f = Math.min(1, Math.max(0, frac));
  	return Math.round(f * (n - 1));
  }
  /** count개 균등 눈금 — 각 눈금의 sec는 그 인덱스 지점의 elapsed_sec. 포인트가 2개 미만이거나 count<2면 []. */
  export function axisTicks(elapsed: number[], count = 5): { frac: number; sec: number }[] {
  	const n = elapsed.length;
  	if (n < 2 || count < 2) return [];
  	return Array.from({ length: count }, (_, k) => {
  		const frac = k / (count - 1);
  		return { frac, sec: elapsed[indexAtFraction(frac, n)] };
  	});
  }
  ```
  (2) 신규 `frontend/tests/streamAxis.test.mjs`(기존 `frontend/tests/format.test.mjs`와 같은 방식 — `node:test`, `node:assert/strict`, 소스는 `../src/lib/streamAxis.ts`에서 import, 케이스: (a) `indexAtFraction(0,101)===0`, `(0.5,101)===50`, `(1,101)===100`, 범위 밖 `(-1,101)===0`·`(2,101)===100`, `n=0`이면 `0`, (b) `axisTicks(Array.from({length:101},(_,i)=>i*10))`의 `sec` 배열이 `[0,250,500,750,1000]`이고 `frac`이 `[0,0.25,0.5,0.75,1]`, (c) 포인트 1개 → `[]`, 빈 배열 → `[]`, `count=1` → `[]`, (d) 일시정지가 있는 불균등 elapsed(`[0,10,20,300,310]`, count 3)에서 가운데 눈금 `sec===20`(인덱스 2 지점의 실제 경과 시간)).
  (3) `frontend/src/routes/library/[id]/streams/+page.svelte`:
   - 스크립트 import에 추가: `import { formatDuration } from '$lib/format';`, `import { axisTicks, indexAtFraction } from '$lib/streamAxis';`.
   - 스크립트 끝(`formatMinMaxPace` 함수 뒤)에 추가:
  ```ts
  	// 시간 눈금 — 포인트 인덱스 축 위의 5개 지점(0/25/50/75/100%)에 실제 경과 시간을 붙인다
  	const ticks = $derived(axisTicks(data.streams.map((p) => p.elapsed_sec), 5));
  	// 스크럽 — 마우스 호버·터치 드래그로 가리킨 포인트 인덱스(null이면 미표시)
  	let scrubIdx = $state<number | null>(null);
  	function scrub(e: PointerEvent) {
  		const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
  		if (rect.width <= 0) return;
  		scrubIdx = indexAtFraction((e.clientX - rect.left) / rect.width, data.streams.length);
  	}
  	function endScrub() {
  		scrubIdx = null;
  	}
  	function formatPoint(def: StreamDef, v: number | null): string {
  		if (v == null) return '—';
  		if (def.key === 'pace') return `${formatPaceSec(v)}${def.unit}`;
  		return def.key === 'altitude_m' ? `${v.toFixed(1)}${def.unit}` : `${Math.round(v)}${def.unit}`;
  	}
  ```
   - 마크업: `<!-- 스트림 목록 -->` 블록(`<div class="flex flex-col gap-5">…{/each}</div>`)을 아래 구조로 감싼다 — 판독 줄 + 시간 눈금 줄 + 스크럽 영역(기존 `{#each availableStreams as def}…{/each}` 내용은 한 글자도 바꾸지 않고 스크럽 영역 `<div>` 안에 그대로 둔다):
  ```svelte
  		<!-- 스크럽 판독 — 높이 고정(레이아웃 흔들림 방지) -->
  		<div class="min-h-[2.5rem] text-xs text-fg-secondary">
  			{#if scrubIdx !== null}
  				{@const pt = data.streams[scrubIdx]}
  				<span class="font-mono font-medium text-fg-primary">{formatDuration(pt.elapsed_sec)}</span>
  				{#each availableStreams as def}
  					{#if checked[def.key]}
  						<span class="ml-2 whitespace-nowrap"><span style="color:{def.color}">{def.label}</span> {formatPoint(def, def.extract(pt))}</span>
  					{/if}
  				{/each}
  			{:else}
  				<span class="text-fg-muted">그래프를 터치·드래그하면 해당 시점의 수치가 보입니다.</span>
  			{/if}
  		</div>
  		<!-- 시간 눈금 (3-D: 시간 → 0 15m 30m …) -->
  		{#if ticks.length > 0}
  			<div class="flex justify-between font-mono text-[10px] text-fg-muted" aria-hidden="true">
  				{#each ticks as t}
  					<span>{formatDuration(t.sec)}</span>
  				{/each}
  			</div>
  		{/if}
  		<!-- svelte-ignore a11y_no_static_element_interactions -->
  		<div
  			class="relative flex flex-col gap-5"
  			style="touch-action: pan-y;"
  			onpointermove={scrub}
  			onpointerdown={scrub}
  			onpointerleave={endScrub}
  			onpointercancel={endScrub}
  		>
  			{#if scrubIdx !== null && data.streams.length > 1}
  				<div
  					class="pointer-events-none absolute inset-y-0 w-px bg-fg-muted"
  					style="left:{(scrubIdx / (data.streams.length - 1)) * 100}%"
  					aria-hidden="true"
  				></div>
  			{/if}
  			(여기에 기존 `{#each availableStreams as def}…{/each}` 블록을 그대로)
  		</div>
  ```
   (`touch-action: pan-y`는 세로 스크롤은 그대로 두고 가로 드래그만 스크럽으로 받기 위한 것 — 그대로 둘 것.) 하단 안내 `<p class="text-xs text-fg-muted">` 의 문구 두 줄 `{data.streams.length.toLocaleString('ko-KR')}개 포인트 ·` / `x축은 포인트 순서(elapsed_sec 균등 간격 미보장 — 정밀 시간축은 후속 과제)` 중 둘째 줄을 `x축은 포인트 순서 — 눈금은 해당 지점의 실제 경과 시간`으로 교체한다. 백엔드·다른 화면은 건드리지 않음.
  리뷰 2026-09-24: 기능은 명세와 같음(시간 눈금·스크럽 판독·커서·고정 높이 판독 줄, npm check 0 errors/build OK, 단위 테스트 통과) — 다만 구조 이탈: `indexAtFraction(n, frac)` 인자 순서 반대, 라벨 포맷(`formatElapsed`)·null 이웃 대체를 streamAxis로 흡수, `axisTicks`가 sec 대신 label 반환, 커서를 차트별로 그림(정렬은 더 정확). 자체 일관적이라 수용, 단 `pointerdown`·`pointercancel` 핸들러 누락(탭만으로는 판독이 안 뜸)과 양끝 눈금 라벨 가로 오버플로 가능성은 main에서 보정.
  <!-- autopilot: {"stage": "done", "mode": "auto", "attempts": 1, "deps": ["P7-IMPL-PAGE-TITLES"], "kind": "code", "scope": ["frontend/src/lib/streamAxis.ts", "frontend/tests/streamAxis.test.mjs", "frontend/src/routes/library/[id]/streams/+page.svelte"], "verify": ["cd frontend && npm install && npm run test:unit && npm run check && npm run build"]} -->
- **[P7-IMPL-TODAY-FITNESS-CHART]** `03a-today.md` 1-A L2 "성장 내러티브"의 인라인 CTL/ATL 추세 차트 — 프론트 전용, 2026-09-24 스펙 대조로 발견(브라우저 스모크에서 `/today`에 `<svg>`가 0개), 설계 근거는 `DECISIONS.md`의 `[P7-IMPL-TODAY-FITNESS-CHART]` 항목 필독. 현황: 1-A 목업은 내러티브 문단 아래에 `인라인 차트: [CTL/ATL 추세 ─────▲──] → 우측 패널(1-C)`를 두는데 `frontend/src/routes/today/+page.svelte`의 L2엔 텍스트·근거 칩·마일스톤뿐 차트가 없다. 데이터는 이미 있다(`GET /library/metrics/:slug/trend` → `getMetricTrend(slug, period)`, `MetricTrendData.points: {date, value}[]`). **이 명세의 코드는 그대로 구현할 것 — 구조를 바꾸고 싶으면 `DECISIONS.md`에 사유를 적고 중단.** **구현**:
  (1) `frontend/src/routes/today/+page.ts` — `import { getMetricTrend } from '$lib/api/metrics';`, 타입 import에 `MetricTrendPoint` 추가. `TodayPageData`에 `fitness: { ctl: MetricTrendPoint[]; atl: MetricTrendPoint[] } | null;` 추가. `load()`의 `Promise.all`에 두 항목을 추가해 `const [today, narrative, plan, adjustment, ctlTrend, atlTrend] = await Promise.all([..., getMetricTrend('ctl', '4w').catch(() => null), getMetricTrend('atl', '4w').catch(() => null)]);`로 받고, 정상 반환에 아래를 포함(포인트가 2개 미만이면 추세가 아니므로 null):
  ```ts
  		const fitness =
  			ctlTrend && ctlTrend.points.length > 1
  				? { ctl: ctlTrend.points, atl: atlTrend?.points ?? [] }
  				: null;
  ```
  `return { today, errorMessage: null, narrative, plan, adjustment, fitness };`, `catch` 분기 반환에도 `fitness: null`을 추가한다.
  (2) `frontend/src/routes/today/+page.svelte` — 스크립트 import에 `import Sparkline from '$lib/components/Sparkline.svelte';` 추가. 마크업의 `<!-- Evidence 칩 -->` 블록(`{#if narrative.evidence.length > 0}…{:else}…{/if}`) 바로 뒤, `<!-- 마일스톤 목록 -->` 바로 앞에 추가:
  ```svelte
  				<!-- CTL/ATL 추세 인라인 차트 (1-A) — 탭하면 이번 달 전체 이야기 패널(1-C) -->
  				{#if data.fitness}
  					{@const ctlNow = data.fitness.ctl[data.fitness.ctl.length - 1].value}
  					<button
  						type="button"
  						onclick={() => { showMonthNarrative = true; }}
  						class="flex flex-col gap-2 rounded-lg border border-border-subtle bg-surface-2 p-3 text-left hover:bg-surface-3"
  						aria-label="CTL·ATL 추세 — 이번 달 전체 이야기 열기"
  					>
  						<div class="flex items-center justify-between text-xs text-fg-muted">
  							<span>피트니스·피로 추세 · 최근 4주</span>
  							<span>이번 달 이야기 →</span>
  						</div>
  						<div class="flex flex-col gap-1">
  							<div class="flex items-center justify-between text-xs">
  								<span style="color:#3b82f6">● CTL</span>
  								<span class="font-mono text-fg-secondary">{ctlNow.toFixed(1)}</span>
  							</div>
  							<Sparkline data={data.fitness.ctl.map((p) => p.value)} height={40} color="#3b82f6" />
  						</div>
  						{#if data.fitness.atl.length > 1}
  							<div class="flex flex-col gap-1">
  								<div class="flex items-center justify-between text-xs">
  									<span style="color:#f59e0b">● ATL</span>
  									<span class="font-mono text-fg-secondary">{data.fitness.atl[data.fitness.atl.length - 1].value.toFixed(1)}</span>
  								</div>
  								<Sparkline data={data.fitness.atl.map((p) => p.value)} height={40} color="#f59e0b" />
  							</div>
  						{/if}
  					</button>
  				{/if}
  ```
  (`showMonthNarrative`은 이 파일에 이미 있는 상태 변수 — 새로 만들지 않는다. 두 Sparkline은 각자 자기 값 범위로 자동 스케일되므로 겹치지 않고 위아래로 쌓는다.) 다른 부분·백엔드·테스트는 건드리지 않음(프론트 전용 — 검증은 `npm run check`/`build`).
  리뷰 2026-09-24: 이탈 다수 — main에서 명세대로 교정: (1) 차트 위치가 "규칙 기반 요약" 뒤·월간 패널 버튼 앞(명세: 근거 칩 바로 뒤·마일스톤 앞), (2) 표시 조건이 포인트 ≥1(명세: ≥2 — 1점 시리즈는 Sparkline이 못 그림), (3) 색을 `var(--color-…, #hex)`로 넘김 — SVG 프레젠테이션 속성의 var()는 브라우저별로 불안정하고 다른 Sparkline 사용처는 전부 hex, (4) 데이터 필드명 ctlTrend/atlTrend(명세: fitness — 기능 동일해 수용), (5) 범례 색 점 없음. npm check 0 errors / build OK.
  <!-- autopilot: {"stage": "done", "mode": "auto", "attempts": 1, "deps": ["P7-IMPL-STREAMS-SCRUB"], "kind": "code", "scope": ["frontend/src/routes/today/+page.ts", "frontend/src/routes/today/+page.svelte"], "verify": ["cd frontend && npm install && npm run check && npm run build"]} -->
- **[P7-IMPL-VALUE-FORMAT]** 메트릭 값의 단위 인지 표기 통일 — 프론트 전용, 2026-09-24 실데이터(pansongit 계정 DB 복사본) 화면 리뷰에서 발견, 설계 근거는 `DECISIONS.md`의 `[P7-IMPL-VALUE-FORMAT]` 항목 필독. 현황(실데이터 스크린샷): 메트릭 브라우저 카드가 수면 시간을 `22440 sec`, 레이스 예측을 `15750 sec`로, 소스 비교 표가 총 시간을 `8357 sec`·거리를 `24207.9 m`로, 활동 요약 상단이 고도를 `↑26.07999999821186 m`로 원시값 그대로 찍는다 — 러너가 읽을 수 없는 값이고 화면마다 표기도 다르다(웰니스 화면은 `9h 5m`). **이 명세의 코드는 그대로 구현할 것 — 구조를 바꾸고 싶으면 `DECISIONS.md`에 사유를 적고 중단.** **구현**:
  (1) `frontend/src/lib/format.ts` — 파일 끝에 추가(이 파일은 다른 모듈을 import하지 않으므로 Node 테스트 러너가 그대로 읽는다. 기존 `formatDuration`/`formatPace`를 쓴다):
  ```ts
  /** 숫자를 소수 1자리로 정리(정수·100 이상은 정수) — 부동소수 잡음(26.07999…)을 없앤다. */
  function roundNice(v: number): string {
  	if (Number.isInteger(v)) return String(v);
  	if (Math.abs(v) >= 100) return String(Math.round(v));
  	return String(Number(v.toFixed(1)));
  }
  /** 단위 인지 값 표기 — 초(sec/s) 60 이상은 시:분:초, sec/km는 페이스, 1000m 이상은 km, 그 외는 roundNice. 반환 unit이 ''이면 text만 쓴다. */
  export function formatUnitValue(v: number, unit: string | null | undefined): { text: string; unit: string } {
  	const u = (unit ?? '').trim();
  	if (u === 'sec' || u === 's') {
  		return v >= 60 ? { text: formatDuration(Math.round(v)), unit: '' } : { text: roundNice(v), unit: '초' };
  	}
  	if (u === 'sec/km') return { text: formatPace(v), unit: '/km' };
  	if (u === 'm' && Math.abs(v) >= 1000) return { text: (v / 1000).toFixed(2), unit: 'km' };
  	return { text: roundNice(v), unit: u };
  }
  ```
  (2) 신규 `frontend/tests/formatUnitValue.test.mjs`(기존 `frontend/tests/format.test.mjs`와 같은 방식 — `node:test`, `node:assert/strict`, `../src/lib/format.ts`에서 import) 케이스: `formatUnitValue(4500,'sec')` → `{text:'1:15:00',unit:''}`, `(8357,'sec')` → `'2:19:17'`, `(45,'sec')` → `{text:'45',unit:'초'}`, `(337,'sec/km')` → `{text:'5:37',unit:'/km'}`, `(24207.9,'m')` → `{text:'24.21',unit:'km'}`, `(26.07999999821186,'m')` → `{text:'26.1',unit:'m'}`, `(241,'ms')` → `{text:'241',unit:'ms'}`, `(277.83,'AU')` → `{text:'278',unit:'AU'}`, `(1.4234,null)` → `{text:'1.4',unit:''}`, `(3,'')` → `{text:'3',unit:''}`.
  (3) `frontend/src/lib/metrics.ts` — `import { formatPace } from '$lib/format';`를 `import { formatPace, formatUnitValue } from '$lib/format';`로 바꾸고, `formatMetricValue`의 마지막 줄 `return Number.isInteger(v) ? String(v) : v.toFixed(1);`을 `return formatUnitValue(v, m.unit).text;`로, `metricUnit`의 마지막 줄 `return m.unit;`을 `return m.numeric_value == null ? m.unit : formatUnitValue(m.numeric_value, m.unit).unit;`로 교체(페이스·json 분기는 그대로).
  (4) `frontend/src/routes/library/metrics/+page.svelte` — 스크립트 import에 `import { formatUnitValue } from '$lib/format';` 추가. 기존 `formatValue(m)` 함수(값이 null이면 '—', 문자열이면 그대로, 숫자면 정수/소수1자리)를 삭제하고 아래로 교체:
  ```ts
  	function displayValue(m: MetricBrowserEntry): { text: string; unit: string } {
  		const v = m.value;
  		if (v == null) return { text: '—', unit: '' };
  		if (typeof v === 'string') return { text: v, unit: m.unit ?? '' };
  		return formatUnitValue(Number(v), m.unit);
  	}
  ```
  카드 마크업의 값 줄 `<span class="font-mono text-lg font-semibold leading-none">{formatValue(m)}{#if m.unit}<span …>{m.unit}</span>{/if}</span>`을 `{@const fv = displayValue(m)}`를 카드 `<a …>` 바로 안쪽 첫 줄에 두고 `{fv.text}{#if fv.unit}<span class="ml-0.5 text-xs font-normal text-fg-muted">{fv.unit}</span>{/if}`로 바꾼다(그 밖의 마크업은 건드리지 않는다).
  (5) `frontend/src/lib/components/ProviderComparison.svelte` — `import { formatUnitValue } from '$lib/format';` 추가. `cellDisplayValue`의 숫자 분기에서 페이스(`sec/km`) 처리 뒤 마지막 `return Number.isInteger(v) ? String(v) : v.toFixed(1);`을 `return formatUnitValue(v, row.unit).text;`로 교체. 행 이름 아래 단위 줄 `{#if row.unit && row.unit !== 'sec/km'}<span class="text-[10px] text-fg-muted">{row.unit}</span>{/if}`은 아래 헬퍼로 바꾼다(스크립트에 추가):
  ```ts
  	// 행 단위 표기 — 셀 값이 이미 변환돼 있으므로(초→시:분:초, m→km) 첫 유효 숫자값 기준으로 변환된 단위를 보인다.
  	function rowUnit(row: ComparisonRow): string {
  		if (!row.unit || row.unit === 'sec/km') return '';
  		for (const cell of Object.values(row.values)) {
  			if (cell.available && typeof cell.value === 'number') return formatUnitValue(cell.value, row.unit).unit;
  		}
  		return row.unit;
  	}
  ```
  마크업은 `{#if rowUnit(row)}<span class="text-[10px] text-fg-muted">{rowUnit(row)}</span>{/if}`.
  (6) `frontend/src/routes/library/[id]/+page.svelte` 91번째 줄 부근의 고도 표시 `{core.elevation_gain}`을 `{Math.round(core.elevation_gain as number)}`로 바꾼다(다른 부분은 그대로).
  리뷰 2026-09-24: 기능은 명세와 같으나 구현 이탈 — 반환 형태 `{display, unit}`(명세 `{text, unit}`)·sec/km를 `5:00/km` 문자열+unit ''로 반환(명세: `5:00`+`/km`)·km 소수 1자리(명세 2자리)·**정수(<100)가 `58.0`으로 찍히는 회귀**(명세 roundNice의 `Number.isInteger` 분기 누락 — HRV 48ms→`48.0`) → main에서 교정. 호출부(메트릭 브라우저·소스 비교·활동 메트릭·고도)는 일관되게 갱신돼 나머지는 수용. npm check 0 errors/build OK, 단위 테스트 통과.
  <!-- autopilot: {"stage": "done", "mode": "auto", "attempts": 1, "deps": ["P7-IMPL-TODAY-FITNESS-CHART"], "kind": "code", "scope": ["frontend/src/lib/format.ts", "frontend/tests/formatUnitValue.test.mjs", "frontend/src/lib/metrics.ts", "frontend/src/routes/library/metrics/+page.svelte", "frontend/src/lib/components/ProviderComparison.svelte", "frontend/src/routes/library/[id]/+page.svelte"], "verify": ["cd frontend && npm install && npm run test:unit && npm run check && npm run build"]} -->
- **[P7-IMPL-PROVIDER-BADGE-LAYOUT]** Provider 배지 때문에 메트릭 이름이 잘리고 소스 비교 표의 대표값 열이 화면 밖으로 밀리는 문제 — 프론트 전용, 2026-09-24 실데이터 화면 리뷰에서 발견, 설계 근거는 `DECISIONS.md`의 `[P7-IMPL-PROVIDER-BADGE-LAYOUT]` 항목 필독. 현황(실데이터 스크린샷): (a) 메트릭 브라우저 카드가 이름 옆에 `RunPulse · formula_v1` 배지(폭 100px+)를 붙여 이름이 `Ch…`, `Ac…`, `Tr…`처럼 2글자만 남는다 — 어떤 메트릭인지 알 수 없다. (b) Today `MetricCell` 3개도 같은 긴 배지가 2줄로 접혀 이름을 밀어낸다. (c) 소스 비교 표는 `min-w-[480px]` + 별도 "대표값" 열이라 390px 화면에서 대표값 열이 가로 스크롤 밖에 잘려 있다 — P3의 핵심 정보("왜 이 소스가 대표값인가")가 안 보인다. **이 명세의 코드는 그대로 구현할 것 — 구조를 바꾸고 싶으면 `DECISIONS.md`에 사유를 적고 중단.** **구현**:
  (1) `frontend/src/lib/provider.ts` — `providerLabel`의 시그니처를 `providerLabel(p: ProviderKey | null | undefined, compact = false): string`로 바꾸고, 함수 첫 부분(`if (!p) return '—';`) 바로 뒤에 `if (compact && p.startsWith('runpulse:')) return 'RunPulse';`를 추가한다(기존 호출부는 인자 없이 그대로 동작 — 전체 표기 `RunPulse · formula_v1`은 MetricBreakdown 패널 등에서 계속 쓴다. P3의 "공식 버전 표기"는 카드가 아니라 계산 분해 패널이 담당).
  (2) `frontend/src/lib/components/MetricCell.svelte` — 헤더의 배지 `<span class="rounded px-1.5 py-0.5 text-[10px] text-white {providerBadgeClass(provider)}">{providerLabel(provider)}</span>`를 `<span class="shrink-0 rounded px-1.5 py-0.5 text-[10px] text-white {providerBadgeClass(provider)}" title={providerLabel(provider)}>{providerLabel(provider, true)}</span>`로, 그 옆 라벨 `<span class="text-xs text-fg-secondary">{label}</span>`을 `<span class="min-w-0 text-xs leading-4 text-fg-secondary">{label}</span>`로 바꾼다.
  (3) `frontend/src/routes/library/metrics/+page.svelte` — 카드(`<a href="{base}/library/metrics/{m.name}" …>`) 안의 헤더 행(`<div class="flex items-start justify-between gap-1">…</div>` — 라벨 `<span class="truncate …">`과 배지)을 삭제하고, 값 줄(`<span class="font-mono text-lg …">`)을 아래 구조로 감싼다(라벨이 카드 폭 전체를 쓰고 2줄까지 보이며, 배지는 값 줄 오른쪽 아래로 이동):
  ```svelte
  							<span class="line-clamp-2 min-h-[2rem] text-xs leading-4 text-fg-muted">{m.label}</span>
  							<div class="flex items-end justify-between gap-1">
  								(여기에 기존 값 `<span class="font-mono text-lg …">…</span>` 그대로)
  								{#if m.provider}
  									<span
  										class="shrink-0 rounded px-1.5 py-0.5 text-[10px] text-white {providerBadgeClass(m.provider as ProviderKey)}"
  										title={providerLabel(m.provider as ProviderKey)}
  									>
  										{providerLabel(m.provider as ProviderKey, true)}
  									</span>
  								{/if}
  							</div>
  ```
  스파크라인(`{#if m.sparkline.length > 1}…`)은 그 아래에 그대로 둔다.
  (4) `frontend/src/lib/components/ProviderComparison.svelte` — (i) `<table class="w-full min-w-[480px] text-sm">`에서 `min-w-[480px]`을 제거한다. (ii) 헤더의 "대표값" `<th>`(마지막 `<th class="py-2 pl-2 pr-4 …">대표값</th>`)와 각 행의 마지막 `<td class="py-2.5 pl-2 pr-4 text-right">…</td>`(대표값 배지 셀) 전체를 삭제한다. (iii) provider 헤더 배지의 `{providerLabel(provider as ProviderKey)}`를 `{providerLabel(provider as ProviderKey, true)}`로 바꾼다. (iv) provider 값 셀의 `<span class="font-mono text-sm …">{cellDisplayValue(row, provider)}</span>`을 아래로 바꿔 대표값 소스를 셀 안에서 ★로 표시한다(이유 툴팁 유지):
  ```svelte
  								<span
  									class="font-mono text-sm {row.values[provider]?.available
  										? isPrimary(row, provider) ? 'font-semibold text-fg-primary' : 'text-fg-secondary'
  										: 'text-fg-muted'}"
  									title={isPrimary(row, provider) && showPrimaryReason && row.primaryReason ? row.primaryReason.rule : undefined}
  								>
  									{#if isPrimary(row, provider) && row.values[provider]?.available}<span class="text-amber-500" aria-label="대표값">★</span>{' '}{/if}{cellDisplayValue(row, provider)}
  								</span>
  ```
  (v) 표 아래 범례 영역(`<!-- 불일치 범례 -->` 위)에 항상 보이는 한 줄 `<div class="mt-2 px-4 text-xs text-fg-muted"><span class="text-amber-500">★</span> 대표값(우선 소스)</div>`를 추가한다(기존 `⚠ 소스 간 차이` 범례는 그대로).
  리뷰 2026-09-24: 대체로 명세대로 — 표에서 대표값 열 제거·★ 셀 표기·min-w 제거·MetricCell/메트릭 브라우저 배지 컴팩트화(별도 `providerLabelCompact` 함수, 명세는 `providerLabel(p, compact)` 인자 — 동등해 수용), 메트릭 라벨 `line-clamp-2` 미적용(전체 줄바꿈 허용, 수용). 이탈: "★ 대표값" 범례 누락 → main에서 추가. npm check 0 errors/build OK.
  <!-- autopilot: {"stage": "done", "mode": "auto", "attempts": 1, "deps": ["P7-IMPL-VALUE-FORMAT"], "kind": "code", "scope": ["frontend/src/lib/provider.ts", "frontend/src/lib/components/MetricCell.svelte", "frontend/src/routes/library/metrics/+page.svelte", "frontend/src/lib/components/ProviderComparison.svelte"], "verify": ["cd frontend && npm install && npm run check && npm run build"]} -->
- **[P7-IMPL-STREAMS-TRUTH]** 스트림 화면의 거짓 시간축과 이상치로 납작해진 차트 교정 — 프론트 전용, 2026-09-24 실데이터(pansongit 복사본) 화면 리뷰에서 발견, 설계 근거는 `DECISIONS.md`의 `[P7-IMPL-STREAMS-TRUTH]` 항목 필독. 현황(실데이터): (a) 2시간 19분짜리 장거리 러닝의 스트림 화면 시간 눈금이 `0 … 28m`으로 끝난다 — Garmin 상세 스트림이 downsample되면서 `elapsed_sec`가 시간이 아니라 **샘플 인덱스**(0..1691)로 저장돼 있기 때문(`garmin_extractor.py`가 `directElapsedDuration` 없으면 `i`를 씀 — 저장 데이터 정정은 별도 BACKLOG 항목). 방금 병합한 STREAMS-SCRUB의 눈금·스크럽 판독이 이 값을 그대로 믿어 틀린 시각을 보인다(P1 위반: 틀린 근거보다 없는 편이 낫다). (b) 페이스 스트림에 GPS 스파이크(`4:20 – 15:08 /km`)가 있어 스파이크 하나가 차트 범위를 잡아 나머지가 납작한 직선이 된다(활동 요약 탭의 페이스 스파크라인도 동일). **이 명세의 코드는 그대로 구현할 것 — 구조를 바꾸고 싶으면 `DECISIONS.md`에 사유를 적고 중단.** **구현**:
  (1) 신규 `frontend/src/lib/chartScale.ts`(순수 함수, 다른 모듈 import 금지):
  ```ts
  /** 유효값(null 제외)의 백분위 p(0~1) — 선형 보간. 유효값이 없으면 null. */
  export function percentile(values: (number | null)[], p: number): number | null {
  	const nums = values.filter((v): v is number => v != null).sort((a, b) => a - b);
  	if (nums.length === 0) return null;
  	const idx = Math.min(1, Math.max(0, p)) * (nums.length - 1);
  	const lo = Math.floor(idx);
  	const hi = Math.ceil(idx);
  	return nums[lo] + (nums[hi] - nums[lo]) * (idx - lo);
  }
  /** 이상치를 [lo, hi] 백분위 범위로 clamp한 새 배열 — 스파이크 하나가 차트 범위를 잡아 나머지를 납작하게 만드는 것을 막는다.
   *  null은 그대로 두고, 유효값이 5개 미만이면 원본 그대로 돌려준다. */
  export function clampOutliers(values: (number | null)[], lo = 0.02, hi = 0.98): (number | null)[] {
  	const valid = values.filter((v) => v != null).length;
  	if (valid < 5) return values;
  	const min = percentile(values, lo) as number;
  	const max = percentile(values, hi) as number;
  	return values.map((v) => (v == null ? null : Math.min(max, Math.max(min, v))));
  }
  ```
  (2) 신규 `frontend/tests/chartScale.test.mjs`(기존 `frontend/tests/streamAxis.test.mjs`와 같은 방식, `../src/lib/chartScale.ts` import): `percentile([1,2,3,4,5],0.5)===3`, `percentile([1,2,3,4],0.5)===2.5`, `percentile([],0.5)===null`, `percentile([null,10],0.5)===10`; `clampOutliers`: 값 99개가 5이고 하나가 1000인 배열(길이 100)에서 결과 최댓값이 5 근처(`<= 5.0001`)이고 길이·순서 유지, null 위치 보존(`[null,1,2,3,4,5,6]` 결과의 0번이 null), 유효값 4개 이하 배열은 입력과 `deepEqual`.
  (3) `frontend/src/lib/streamAxis.ts` — 파일 끝에 추가:
  ```ts
  /** 각 포인트의 실제 경과 초. downsample된 Garmin 스트림은 elapsed_sec가 시간이 아니라 샘플 인덱스(예: 2h19m 활동의 마지막 값이 1691)로
   *  저장돼 있다 — 마지막 elapsed_sec가 활동 총 시간의 90% 미만이면 등간격 샘플로 보고 총 시간에 비례해 환산한다.
   *  총 시간을 모르거나 포인트가 2개 미만이면 elapsed 그대로. */
  export function streamSeconds(elapsed: number[], durationSec: number | null | undefined): number[] {
  	const n = elapsed.length;
  	if (n < 2 || !durationSec || durationSec <= 0) return elapsed;
  	if (elapsed[n - 1] >= durationSec * 0.9) return elapsed;
  	return elapsed.map((_, i) => Math.round((i / (n - 1)) * durationSec));
  }
  ```
  (4) `frontend/tests/streamAxis.test.mjs` — 기존 파일 끝에 `streamSeconds` 테스트 추가(import 목록에도 추가): (a) `Array.from({length:3600},(_,i)=>i)`와 `3600`(마지막 3599 ≥ 3240) → 입력과 `deepEqual`, (b) `Array.from({length:1692},(_,i)=>i)`와 `8357` → 첫 값 0, 마지막 값 8357, 가운데(인덱스 846) 값이 `4178±5`, (c) `durationSec`가 `null`/`0`이면 입력 그대로, (d) 포인트 1개면 입력 그대로.
  (5) `frontend/src/routes/library/[id]/streams/+page.ts` — `import { getActivity } from '$lib/api/library';` 추가. `StreamsPageData`에 `durationSec: number | null;` 추가. 정상 경로를 `const [streams, activity] = await Promise.all([getActivityStreams(id), getActivity(id).catch(() => null)]);`로 바꾸고 `return { activityId: id, streams, durationSec: activity?.core?.duration_sec ?? null, errorMessage: null };`. 오류·잘못된 ID 분기 반환에도 `durationSec: null`을 넣는다.
  (6) `frontend/src/routes/library/[id]/streams/+page.svelte`: 스크립트 import에 `streamSeconds`(`$lib/streamAxis`)와 `import { clampOutliers } from '$lib/chartScale';` 추가. 기존 `const ticks = $derived(axisTicks(data.streams.map((p) => p.elapsed_sec)));`를 아래 두 줄로 교체:
  ```ts
  	// 실제 경과 초 — 저장된 elapsed_sec가 샘플 인덱스인 활동은 총 시간에 비례해 환산(streamSeconds 참조)
  	const secs = $derived(streamSeconds(data.streams.map((p) => p.elapsed_sec), data.durationSec));
  	const ticks = $derived(axisTicks(secs));
  ```
  스크럽 판독 줄의 `formatElapsed(point.elapsed_sec)`를 `formatElapsed(secs[scrubIndex])`로 바꾼다(`{@const point = data.streams[scrubIndex]}`는 값 표시용으로 그대로). 스트림 목록의 `{@const values = data.streams.map(def.extract)}`를 `{@const values = clampOutliers(data.streams.map(def.extract))}`로 바꾼다(차트와 범위 라벨이 같은 값을 쓴다). 하단 안내 문구의 둘째 줄 `시간 눈금은 포인트 인덱스 기준 위치에 실제 elapsed_sec를 표시`를 `시간 눈금은 활동 총 시간 기준 · 상·하위 2% 이상치는 차트에서 제외`로 교체.
  (7) `frontend/src/routes/library/[id]/+page.svelte` — `import { clampOutliers } from '$lib/chartScale';` 추가, 125·131번째 줄 부근의 `<Sparkline data={paceSeries} …>`·`<Sparkline data={hrSeries} …>`를 각각 `data={clampOutliers(paceSeries)}`·`data={clampOutliers(hrSeries)}`로 바꾼다(다른 부분은 그대로).
  리뷰 2026-09-24: 기능은 명세대로(등간격 환산·백분위 clamp·이상치 안내), 구조 이탈은 수용 — `streamSeconds(elapsed, totalSec)`·`clampOutliers → {values, clamped}`·nearest-rank 백분위·로더 필드명 `totalSec`(명세 `durationSec`)·이상치 안내는 clamp가 실제 일어난 스트림에만 표시(명세: 항상 — 더 조용해 수용). npm check 0 errors/build OK, 단위 테스트 통과. 실데이터 화면 확인은 병합 후.
  <!-- autopilot: {"stage": "done", "mode": "auto", "attempts": 1, "deps": ["P7-IMPL-PROVIDER-BADGE-LAYOUT"], "kind": "code", "scope": ["frontend/src/lib/chartScale.ts", "frontend/tests/chartScale.test.mjs", "frontend/src/lib/streamAxis.ts", "frontend/tests/streamAxis.test.mjs", "frontend/src/routes/library/[id]/streams/+page.ts", "frontend/src/routes/library/[id]/streams/+page.svelte", "frontend/src/routes/library/[id]/+page.svelte"], "verify": ["cd frontend && npm install && npm run test:unit && npm run check && npm run build"]} -->
- **[P7-IMPL-COACH-MARKDOWN]** Coach 답변의 마크다운 원문 노출 교정 — 프론트 전용, 2026-09-24 실데이터(pansongit 복사본) 화면 리뷰에서 발견, 설계 근거는 `DECISIONS.md`의 `[P7-IMPL-COACH-MARKDOWN]` 항목 필독. 현황(실데이터 스크린샷): Coach 대화 화면의 어시스턴트 답변이 `**오늘의 훈련 추천**`, `- TSB -28.4 — 피로 축적. …`처럼 마크다운 기호 그대로 찍히고(`{msg.content}`를 `whitespace-pre-wrap`으로 출력), Coach 홈 대화 목록 미리보기도 `**"훈련 분석"에 대한 분석** - TSB(신선도): -16.5 - …`로 별표가 보인다. Coach는 앱의 핵심 AI 표면인데 첫인상이 깨진 텍스트다. 어시스턴트 답변 아래 `rule`이라는 내부 용어도 그대로 노출된다. **이 명세의 코드는 그대로 구현할 것 — 구조를 바꾸고 싶으면 `DECISIONS.md`에 사유를 적고 중단.** **구현**(XSS 방지: `{@html}`을 쓰지 않고 Svelte 텍스트 노드로만 렌더한다):
  (1) 신규 `frontend/src/lib/markdownLite.ts`(순수 함수, 다른 모듈 import 금지):
  ```ts
  // Coach 답변용 최소 마크다운 — **굵게**, 목록(-, *, •, 1.), 제목(#)만 해석한다. HTML은 만들지 않는다(텍스트 조각만 반환).
  export type Inline = { text: string; bold: boolean };
  export type Block =
  	| { type: 'p'; inlines: Inline[] }
  	| { type: 'ul' | 'ol'; items: Inline[][] };
  /** `**굵게**`를 조각으로 나눈다. 짝이 없는 `**`는 글자 그대로 둔다. */
  export function parseInline(s: string): Inline[] {
  	const out: Inline[] = [];
  	const re = /\*\*(.+?)\*\*/g;
  	let last = 0;
  	let m: RegExpExecArray | null;
  	while ((m = re.exec(s)) !== null) {
  		if (m.index > last) out.push({ text: s.slice(last, m.index), bold: false });
  		out.push({ text: m[1], bold: true });
  		last = m.index + m[0].length;
  	}
  	if (last < s.length) out.push({ text: s.slice(last), bold: false });
  	return out;
  }
  const UL = /^\s*[-*•]\s+(.*)$/;
  const OL = /^\s*\d+[.)]\s+(.*)$/;
  const HEADING = /^\s*#{1,6}\s+(.*)$/;
  /** 줄 단위로 문단·목록 블록을 만든다. 빈 줄은 건너뛰고, 연속된 같은 종류 목록 줄은 한 목록으로 묶는다. */
  export function parseBlocks(text: string): Block[] {
  	const blocks: Block[] = [];
  	for (const line of text.split('\n')) {
  		if (!line.trim()) continue;
  		const ul = UL.exec(line);
  		const ol = ul ? null : OL.exec(line);
  		const heading = ul || ol ? null : HEADING.exec(line);
  		if (ul || ol) {
  			const type = ul ? 'ul' : 'ol';
  			const item = parseInline((ul ?? ol)![1]);
  			const prev = blocks[blocks.length - 1];
  			if (prev && prev.type === type) prev.items.push(item);
  			else blocks.push({ type, items: [item] });
  		} else if (heading) {
  			blocks.push({ type: 'p', inlines: parseInline(heading[1]).map((s) => ({ ...s, bold: true })) });
  		} else {
  			blocks.push({ type: 'p', inlines: parseInline(line) });
  		}
  	}
  	return blocks;
  }
  /** 목록 미리보기용 — 마크다운 기호를 떼고 한 줄로 합친다. */
  export function stripMarkdown(text: string): string {
  	return text
  		.split('\n')
  		.map((l) => l.replace(HEADING, '$1').replace(UL, '$1').replace(OL, '$1').replace(/\*\*/g, '').trim())
  		.filter(Boolean)
  		.join(' ');
  }
  ```
  (2) 신규 `frontend/tests/markdownLite.test.mjs`(기존 `frontend/tests/streamAxis.test.mjs`와 같은 방식, `../src/lib/markdownLite.ts` import): `parseInline('a **b** c')` → `[{text:'a ',bold:false},{text:'b',bold:true},{text:' c',bold:false}]`; 짝 없는 `parseInline('**x')` → `[{text:'**x',bold:false}]`; `parseBlocks('**제목**\n피로 회복이 필요합니다.\n- TSB -28.4\n- ACWR 1.3\n\n1. 첫째\n2. 둘째')` → 블록 타입 순서가 `['p','p','ul','ol']`이고 `ul.items.length===2`, `ol.items.length===2`, 첫 문단의 첫 조각이 `{text:'제목',bold:true}`; `## 제목`이 굵은 문단이 됨; 빈 문자열 → `[]`; `stripMarkdown('**오늘의 훈련 추천**\n피로 회복이 필요합니다.\n- TSB -28.4 — 피로 축적.')` → `'오늘의 훈련 추천 피로 회복이 필요합니다. TSB -28.4 — 피로 축적.'`.
  (3) 신규 `frontend/src/lib/components/ChatBody.svelte`:
  ```svelte
  <script lang="ts">
  	// Coach 답변 본문 — markdownLite 블록을 텍스트 노드로만 렌더한다({@html} 금지).
  	import { parseBlocks } from '$lib/markdownLite';
  	let { text }: { text: string } = $props();
  	const blocks = $derived(parseBlocks(text));
  </script>
  <div class="flex flex-col gap-2">
  	{#each blocks as b}
  		{#if b.type === 'p'}
  			<p>{#each b.inlines as s}{#if s.bold}<strong class="font-semibold">{s.text}</strong>{:else}{s.text}{/if}{/each}</p>
  		{:else}
  			<svelte:element this={b.type} class="flex flex-col gap-1 pl-5 {b.type === 'ul' ? 'list-disc' : 'list-decimal'}">
  				{#each b.items as item}
  					<li>{#each item as s}{#if s.bold}<strong class="font-semibold">{s.text}</strong>{:else}{s.text}{/if}{/each}</li>
  				{/each}
  			</svelte:element>
  		{/if}
  	{/each}
  </div>
  ```
  (4) `frontend/src/routes/coach/[threadId]/+page.svelte` — `import ChatBody from '$lib/components/ChatBody.svelte';` 추가. 어시스턴트 메시지의 `<p class="whitespace-pre-wrap">{msg.content}</p>`를 `<ChatBody text={msg.content} />`로 바꾸고, 그 아래 `{msg.ai_model}` 표기를 `{msg.ai_model === 'rule' ? '규칙 기반 답변' : msg.ai_model}`로 바꾼다(사용자 메시지 버블은 그대로).
  (5) `frontend/src/routes/coach/+page.svelte` — `import { stripMarkdown } from '$lib/markdownLite';` 추가, 대화 목록 미리보기 `<p class="truncate text-xs text-fg-muted">{t.last_message}</p>`를 `{stripMarkdown(t.last_message)}`로 바꾼다.
  리뷰 2026-09-24: 명세와 다른 설계(토큰 방식 `parseMarkdown`·`localizeSource`, 컴포넌트 prop `content`) — 굵게·제목·목록·출처 한글화·미리보기 정리는 동작해 수용. 위험 이탈 2건은 main에서 교정: (1) 별표 한 쌍(`*x*`)까지 굵게 처리해 "TSB * 0.5 … CTL * 2" 같은 산식 문장이 깨질 수 있음 → `**`만 해석, (2) 번호 목록(`1.`) 미지원은 문단으로 읽혀 수용. npm check 0 errors/build OK.
  <!-- autopilot: {"stage": "done", "mode": "auto", "attempts": 1, "deps": ["P7-IMPL-STREAMS-TRUTH"], "kind": "code", "scope": ["frontend/src/lib/markdownLite.ts", "frontend/tests/markdownLite.test.mjs", "frontend/src/lib/components/ChatBody.svelte", "frontend/src/routes/coach/[threadId]/+page.svelte", "frontend/src/routes/coach/+page.svelte"], "verify": ["cd frontend && npm install && npm run test:unit && npm run check && npm run build"]} -->
- **[P7-IMPL-TODAY-HERO]** Today 첫 화면의 위계 — "오늘 무엇을 할까"가 입력 폼 아래로 밀려 있다. 프론트 전용, 2026-09-24 실데이터·합성 데이터 화면 리뷰에서 발견, **설계 변경**(03a·03g 문서는 본 유닛 등록 시 이미 수정됨 — `DECISIONS.md`의 `[P7-IMPL-TODAY-HERO]` 항목 필독). 현황(스크린샷): 390×844 첫 화면의 45%를 QuickInput(피로도 버튼 8+2개로 두 줄 접힘 + 통증 4버튼 + 메모 textarea + 저장)이 차지하고, 정작 권고 카드("피로도가 높습니다 — 완전 휴식이나 회복 위주…")는 그 아래 스크롤 경계에 걸린다 — 03a의 의도("L0에서 오늘 무엇을 할까를 30초 안에 답한다")와 반대. 체크인은 하루 1회 10초 입력이라 매번 펼쳐 둘 이유가 없다. **이 명세의 코드는 그대로 구현할 것 — 구조를 바꾸고 싶으면 `DECISIONS.md`에 사유를 적고 중단.** **구현**:
  (1) `frontend/src/routes/today/+page.svelte` — `<!-- ══ L0 — 즉시 브리핑 ══ -->` 섹션 안에서 순서를 바꾼다: `<RecommendationCard …/>` 블록을 섹션의 **첫 자식**으로 옮기고, 그 뒤에 `<QuickInput … />`와 `{#if checkinError}…{/if}`를 둔다. `<QuickInput`에는 `compact` 속성을 추가한다(`existing={…}`·`saving`·`onSave`는 그대로). 섹션 시작 `<section class="flex flex-col gap-3">`과 나머지 마크업은 그대로.
  (2) `frontend/src/lib/components/QuickInput.svelte` — 피로도 1~10 버튼 묶음(`<div role="radiogroup" aria-label="피로도 (1~10)" class="flex flex-wrap gap-1">`)을 한 줄 눈금으로 바꾼다: 컨테이너 클래스를 `grid grid-cols-10 gap-1`로, 각 버튼 클래스의 `h-9 w-9`를 `h-11 min-w-0`로 바꾼다(나머지 `rounded border … text-sm` 조건 클래스는 그대로). 통증 묶음·메모·저장 마크업은 건드리지 않는다.
  리뷰: 워크트리 diff를 명세와 줄 단위 대조 — RecommendationCard가 L0 첫 자식, QuickInput `compact={true}`, 피로도 `grid grid-cols-10 gap-1` / `h-11 w-full` 모두 명세와 일치(이탈 없음). npm test:unit·check·build 통과. 실데이터 사본/합성 브라우저 확인은 병합 후.
  <!-- autopilot: {"stage": "done", "mode": "auto", "attempts": 1, "deps": ["P7-IMPL-COACH-MARKDOWN"], "kind": "code", "scope": ["frontend/src/routes/today/+page.svelte", "frontend/src/lib/components/QuickInput.svelte"], "verify": ["cd frontend && npm install && npm run check && npm run build"]} -->
- **[P7-DATA-STREAM-ELAPSED]** `activity_streams.elapsed_sec`가 시간이 아니라 샘플 인덱스로 저장된 활동이 있다 —
  2026-09-24 실데이터 화면 리뷰에서 발견(활동 15302: 실제 8357초인데 1692점·elapsed 0..1691). 원인: `garmin_extractor.
  extract_activity_streams`가 `directElapsedDuration`이 없으면 `int(elapsed_raw) if … else i`(샘플 인덱스)를 쓴다 —
  Garmin 상세 스트림은 `maxChartSize`로 downsample돼 오기 때문. 수정 방향(판단 필요): descriptor의 시간 키(`directTimestamp`
  등) 차이로 실제 초를 계산하거나 총 시간에 비례 환산 + `source_payloads` raw로 **재처리(reprocess)해 기존 행 정정**.
  UI는 `P7-IMPL-STREAMS-TRUTH`가 저장값을 맹신하지 않도록 이미 방어함. Strava 추출기(`elapsed_sec: t`)는 시간 스트림을
  쓰므로 영향 없음 추정 — 확인 필요. **(판단 필요)** — 스키마·재처리(실데이터 갱신) 수반.

- **[P7-IMPL-TREND-CHART]** 추세 차트에 축·공통 스케일·스크럽 추가 + 무의미한 % 변화 교정 — 프론트 전용, 2026-09-24 실데이터 화면 리뷰에서 발견, 설계 근거는 `DECISIONS.md`의 `[P7-IMPL-TREND-CHART]` 항목 필독. 현황(실데이터 스크린샷): (a) 메트릭 상세(`library/metrics/[slug]`)의 추세 차트는 선 하나뿐 — y축·값 눈금이 없고 어느 날 값이 얼마인지 볼 수 없다(P2 "데이터 포인트를 눌러 확인"이 불가). (b) 같은 화면의 "30일 변화"가 `+742.2%`(CTL이 4.5→37.9라 기준값이 작아 퍼센트가 무의미). (c) Today L2의 CTL·ATL 차트가 각자 자기 범위로 스케일돼 ATL이 실제보다 훨씬 출렁이는 것처럼 보이고(같은 축이 아님) 값을 읽을 수 없다. **이 명세의 코드는 그대로 구현할 것 — 구조를 바꾸고 싶으면 `DECISIONS.md`에 사유를 적고 중단.** **구현**:
  (1) 신규 `frontend/src/lib/trendChart.ts`(순수 함수, 다른 모듈 import 금지):
  ```ts
  export interface TrendPoint { date: string; value: number }
  export interface TrendSeries { key: string; label: string; color: string; points: TrendPoint[] }
  /** 모든 시리즈를 한 축에 그릴 공통 y 범위(위아래 5% 여백). 값이 하나도 없으면 null. 최댓값=최솟값이면 ±1. */
  export function commonRange(series: TrendSeries[]): { min: number; max: number } | null {
  	const vals = series.flatMap((s) => s.points.map((p) => p.value));
  	if (vals.length === 0) return null;
  	let min = Math.min(...vals);
  	let max = Math.max(...vals);
  	if (min === max) { min -= 1; max += 1; }
  	const pad = (max - min) * 0.05;
  	return { min: min - pad, max: max + pad };
  }
  /** 날짜(YYYY-MM-DD)의 [t0, t1] 구간 내 위치 0~1 — 시리즈마다 날짜가 달라도 같은 x축에 놓기 위함. 구간 길이가 0이면 0. */
  export function xFraction(date: string, t0: string, t1: string): number {
  	const a = Date.parse(t0);
  	const b = Date.parse(t1);
  	if (!(b > a)) return 0;
  	return Math.min(1, Math.max(0, (Date.parse(date) - a) / (b - a)));
  }
  /** 위치 frac(0~1)에 가장 가까운 날짜의 점. 점이 없으면 null. */
  export function nearestPoint(points: TrendPoint[], frac: number, t0: string, t1: string): TrendPoint | null {
  	let best: TrendPoint | null = null;
  	let bestD = Infinity;
  	for (const p of points) {
  		const d = Math.abs(xFraction(p.date, t0, t1) - frac);
  		if (d < bestD) { bestD = d; best = p; }
  	}
  	return best;
  }
  /** "N일 변화" 라벨 — 기준값(N일 전 이하의 마지막 점, 없으면 첫 점)이 작으면(|기준|<10) 퍼센트가 무의미하므로 절대 변화(+33.4)로, 아니면 퍼센트(+13.0%)로. 점이 없으면 '—'. */
  export function changeLabel(points: TrendPoint[], days = 30): string {
  	if (points.length === 0) return '—';
  	const last = points[points.length - 1];
  	const cutoff = Date.parse(last.date) - days * 86_400_000;
  	let base = points[0];
  	for (const p of points) if (Date.parse(p.date) <= cutoff) base = p;
  	const delta = last.value - base.value;
  	const sign = delta >= 0 ? '+' : '';
  	if (Math.abs(base.value) < 10) return `${sign}${delta.toFixed(1)}`;
  	return `${sign}${((delta / base.value) * 100).toFixed(1)}%`;
  }
  ```
  (2) 신규 `frontend/tests/trendChart.test.mjs`(기존 `frontend/tests/chartScale.test.mjs`와 같은 방식, `../src/lib/trendChart.ts` import): `commonRange` — 두 시리즈(값 0~10, 50~100)에서 min이 0보다 작고 max가 100보다 큼, 빈 시리즈 배열/점 없는 시리즈 → `null`, 값이 전부 같으면(5,5) `max-min > 0`; `xFraction('2026-09-15','2026-09-01','2026-09-29')===0.5`, 범위 밖은 0/1로 clamp, `t0===t1`이면 0; `nearestPoint` — 점 3개(9/1, 9/15, 9/29)에서 frac 0.55 → 9/15 점, 점 없으면 null; `changeLabel` — 기준값 4.5→37.9(30일 전 점 포함)이면 `'+33.4'`, 기준 50→60이면 `'+20.0%'`, 빈 배열이면 `'—'`, 하락(60→50)은 `'-16.7%'`.
  (3) 신규 `frontend/src/lib/components/TrendChart.svelte` — props `{ series: TrendSeries[]; height?: number (기본 140); unit?: string; interactive?: boolean (기본 true) }`(`TrendSeries` 타입은 `$lib/trendChart`에서 import). 구현 요건: (i) 공통 y 범위(`commonRange`)와 날짜 x 위치(`xFraction`, t0/t1은 모든 시리즈 점의 최소·최대 날짜)로 시리즈마다 `<polyline>`을 한 `<svg viewBox="0 0 600 {height}" preserveAspectRatio="none" style="width:100%;height:{height}px">`에 그린다(선 두께 2, `vector-effect="non-scaling-stroke"`), 위·중간·아래 3줄의 가는 격자선(`stroke` 옅게); (ii) svg 위에 절대배치한 y축 라벨 두 개(최대·최소 값, `text-[10px] text-fg-muted font-mono`, 소수 1자리, 값 자체가 아니라 눈금이므로 단위는 붙이지 않는다)와 아래 x축 라벨 두 개(t0·t1 날짜); (iii) `interactive`이면 컨테이너에 Pointer Events(`pointerdown/pointermove` → frac = (clientX − rect.left)/rect.width, `pointerleave/pointercancel` → 해제, `style="touch-action: pan-y"`)로 스크럽: 세로 커서선(`pointer-events-none absolute inset-y-0 w-px bg-fg-muted`)과, 차트 위 높이 고정 판독 줄(`min-h-[1.25rem]`)에 `날짜 · {label} {값}{unit}`을 시리즈마다 `nearestPoint`로 표시(스크럽 안 할 때는 마지막 날짜와 마지막 값들을 표시); (iv) 시리즈 범례(색 ● + label + 현재값)는 차트 위 한 줄. `interactive`가 false면 포인터 핸들러·커서를 붙이지 않는다.
  (4) `frontend/src/routes/library/metrics/[slug]/+page.svelte` — import에서 `Sparkline`을 `TrendChart`(`$lib/components/TrendChart.svelte`)로 바꾸고 `import { changeLabel } from '$lib/trendChart';` 추가. "30일 변화" 값 `{formatChangePct(data.trend.change_pct)}`를 `{changeLabel(points)}`로 바꾸고(`formatChangePct` 함수는 삭제), `<!-- 스파크라인 (큰 차트) -->` 블록 안의 `<Sparkline …/>`과 그 아래 시작·끝 날짜 `<div class="mt-1 flex justify-between …">…</div>`를 `<TrendChart series={[{ key: data.slug, label: data.trend.label, color: '#3b82f6', points }]} unit={data.trend.unit} />` 한 줄로 교체(`points`는 이 파일에 이미 있는 `$derived`).
  (5) `frontend/src/routes/today/+page.svelte` — `import Sparkline …`을 `import TrendChart from '$lib/components/TrendChart.svelte';`로 바꾼다(다른 곳에서 Sparkline을 안 쓰면). `<!-- CTL/ATL 추세 인라인 차트 …` 블록의 `<button …>` 안에서 두 개의 `<div class="flex flex-col gap-1">` 시리즈 블록(CTL·ATL 각각의 라벨 줄 + `<Sparkline …/>`)을 아래 한 줄로 교체한다 — 헤더 줄 `피트니스·피로 추세 · 최근 4주 / 이번 달 이야기 →`은 그대로 두고, 차트는 한 축에 겹쳐 그리며 탭은 그대로 이번 달 이야기 패널을 연다(그래서 `interactive={false}`):
  ```svelte
  						<TrendChart
  							interactive={false}
  							height={120}
  							series={[
  								{ key: 'ctl', label: 'CTL', color: '#3b82f6', points: data.ctlTrend?.points ?? [] },
  								...(data.atlTrend && data.atlTrend.points.length > 1
  									? [{ key: 'atl', label: 'ATL', color: '#f59e0b', points: data.atlTrend.points }]
  									: [])
  							]}
  						/>
  ```
  리뷰: 워크트리 diff를 명세와 대조 → 명세 불일치 다수(이탈): (1) `trendChart.ts` API를 명세(TrendSeries/points, commonRange, xFraction, nearestPoint, changeLabel(points))와 다르게 구현(ChartSeries/values+dates 인덱스 매핑, sharedYRange, changeLabel(current, prev)) — CTL·ATL 날짜가 다르면 x축이 어긋남; (2) SVG `preserveAspectRatio="none"` 안에 `<text>`·`<circle>`을 그려 글자·마커가 가로로 찌그러짐(명세는 HTML 오버레이); (3) y 눈금 `toFixed(0)`(0.8 같은 소수 메트릭에서 무의미; 명세 1자리); (4) 범례·판독 줄·pointerdown/touch-action 누락; (5) "30일 변화"가 기간 첫 점 기준(명세는 30일 전 점). 정정: main에서 명세대로 재작성(`fix(frontend): TrendChart 명세 정합`) 후 실데이터·합성 브라우저 확인.
  <!-- autopilot: {"stage": "done", "mode": "auto", "attempts": 1, "deps": ["P7-IMPL-TODAY-HERO"], "kind": "code", "scope": ["frontend/src/lib/trendChart.ts", "frontend/tests/trendChart.test.mjs", "frontend/src/lib/components/TrendChart.svelte", "frontend/src/routes/library/metrics/[slug]/+page.svelte", "frontend/src/routes/today/+page.svelte"], "verify": ["cd frontend && npm install && npm run test:unit && npm run check && npm run build"]} -->
- **[P7-IMPL-RACE-HUB-API]** Today 목표 레이스 허브용 백엔드 — 활성 목표 + D-day + 예측 기록·목표 격차·예측 추이 + 현재 폼. 백엔드 전용, `REVIEW-05-vision-gap.md` E1 참조, 설계 근거는 `DECISIONS.md`의 `[P7-IMPL-RACE-HUB-API]` 항목 필독. **이 명세의 시그니처·반환 키는 그대로 구현할 것 — 바꾸고 싶으면 `DECISIONS.md`에 사유를 적고 중단.** 배경: 실데이터에 `race_pred_*_sec`(5k/10k/half/marathon, provider `runpulse:formula_v1`, 429일 이력)가 있는데 화면 어디에도 나오지 않고, `dashboard_service.get_dashboard_data()`는 존재하지 않는 메트릭명 `darp_*_sec`를 읽어 `race_predictions`가 항상 null이다(실제 메트릭명은 `src/metrics/darp.py`의 produces와 같은 `race_pred_{5k,10k,half,marathon}_sec`).
  (1) `src/services/dashboard_service.py` 버그 수정 — `pred_names = ["darp_5k_sec", ...]`를 `["race_pred_5k_sec", "race_pred_10k_sec", "race_pred_half_sec", "race_pred_marathon_sec"]`로, `pred_map.get(...)`의 키도 같은 이름으로 바꾼다. 반환 딕셔너리의 키(`darp_5k`, `darp_10k`, `darp_half`, `darp_marathon`)는 소비자(`ai_context.py` 등)가 쓰므로 그대로 둔다. `tests/test_dashboard_service.py`(50~53행 시드)와 `tests/test_ai_context.py`(45~46행 시드)가 잘못된 이름 `darp_*_sec`을 시드하고 있으므로 시드의 메트릭명만 `race_pred_*_sec`로 바꾸고 기대값은 그대로 둔다(버그를 테스트가 감추고 있었음).
  (2) 신규 `src/services/race_hub_service.py` — 모듈 docstring 첫 줄 `"""Today 목표 레이스 허브 — 활성 목표 + D-day + 예측 기록·목표 격차·예측 추이."""`. 읽기 전용, raw SQL 허용(서비스 레이어). `from __future__ import annotations`, `import sqlite3`, `from datetime import date as _date, datetime, timedelta`. 구현:
  ```python
  _BUCKETS = [("5k", 5.0, 1.0), ("10k", 10.0, 1.5), ("half", 21.0975, 2.0), ("marathon", 42.195, 2.5)]
  def bucket_for_distance(distance_km: float | None) -> str | None:
      """목표 거리(km)에 대응하는 예측 버킷. 중심에서 허용오차 이내이고 가장 가까운 버킷, 없으면 None."""
  def get_race_hub(conn: sqlite3.Connection, date: str | None = None) -> dict:
      """가장 가까운 다가오는 활성 목표와 준비 현황.
      반환: {"goal": None | {...}, "prediction": None | {...}, "form": None | {...}}
      """
  ```
  `date` 기본은 오늘(`_date.today().isoformat()`). 목표 선택: `SELECT id, name, race_date, distance_km, target_time_sec, target_pace_sec_km FROM goals WHERE status = 'active' AND race_date IS NOT NULL AND race_date >= ? ORDER BY race_date ASC, id DESC LIMIT 1`. 없으면 `{"goal": None, "prediction": None, "form": None}`. 있으면 `goal` = `{"id","name","race_date","distance_km","target_time_sec","target_pace_sec_km","days_left","weeks_left"}` (`days_left` = `(race_date − date).days` 정수, `weeks_left` = `days_left // 7`). `prediction`: `bucket_for_distance(distance_km)`가 None이면 None. 아니면 메트릭 `race_pred_{bucket}_sec`에서 `SELECT scope_id, numeric_value FROM metric_store WHERE metric_name = ? AND scope_type = 'daily' AND is_primary = 1 AND numeric_value IS NOT NULL AND scope_id <= ? ORDER BY scope_id DESC LIMIT 1`로 최신 1건(없으면 `prediction` = None). `prediction` = `{"bucket": bucket, "value_sec": 최신값(int), "as_of": scope_id, "gap_sec": value_sec − target_time_sec (target_time_sec가 None이면 None), "history": [{"date": scope_id, "value": 값(int)}, …]}` — history는 같은 쿼리로 `scope_id >= date − 90일` 범위를 날짜 오름차순. `form`: `ctl`, `tsb` 각각 `metric_name = ? AND scope_type = 'daily' AND is_primary = 1 AND scope_id <= ?`의 최신 값 → `{"ctl": float | None, "tsb": float | None}`(둘 다 None이어도 dict 반환).
  (3) `src/api/routes_today.py` — 모듈 docstring 첫 줄에 `GET /api/v1/today/race-hub` 추가, 기존 라우트와 같은 패턴(db 없으면 503 NOT_FOUND, `sqlite3.connect`/finally close)으로 `@api_bp.get("/today/race-hub")` 추가, `race_hub_service.get_race_hub(conn)` 결과를 `api_ok`로 반환(`from src.services import milestone_service, today_service` 줄에 `race_hub_service` 추가).
  (4) 테스트 `tests/test_race_hub_service.py`(신규, 인메모리 `sqlite3.connect(":memory:")` + `create_tables` + `migrate_db`, 기존 `tests/test_milestone_service.py`의 픽스처 방식 참고): `bucket_for_distance` — 42.195→"marathon", 42.0→"marathon", 21.1→"half", 10→"10k", 5→"5k", 15→None, None→None. `get_race_hub` — (a) 목표 없음 → 세 키 모두 None; (b) 지난 날짜 목표만 있음 → goal None; (c) 미래 목표 2개(가까운 것 선택), `date="2026-09-24"`, race_date `2026-10-25` → `days_left==31`, `weeks_left==4`; (d) 마라톤 목표(target 14400) + `race_pred_marathon_sec` 3일치(예: 15750, 15692, 15692, provider `runpulse:formula_v1`, is_primary=1) → `value_sec` 최신값, `gap_sec == 최신값 − 14400`, history 3건 오름차순; (e) 목표 거리 15km → prediction None이지만 goal 있음; (f) target_time_sec None → `gap_sec` None; (g) ctl·tsb 시드 시 form에 반영, 없으면 둘 다 None. `tests/test_api_today.py`에 `test_get_race_hub_no_goal`(빈 DB → 200, `data.goal is None`) 추가. `tests/test_dashboard_service.py`의 기존 `rp["darp_marathon"] == 12900` 단언이 수정된 시드로 통과해야 한다.
  리뷰: 워크트리 diff를 명세와 줄 단위 대조 — `race_hub_service`(버킷 허용오차·목표 선택 쿼리·prediction/history/form 반환 키), 라우트, `dashboard_service` 메트릭명 교정(`race_pred_*_sec`, 반환 키 `darp_*` 유지), 잘못된 시드 교정(test_dashboard_service·test_ai_context) 모두 명세와 일치(이탈 없음). 실행 중 verify가 `blocked`된 것은 코드 결함이 아니라 러너의 `python3`가 pytest 없는 scripts/.venv로 잡힌 환경 문제 — `/usr/bin/python3`로 4개 테스트 파일 67 통과 확인 후 수동 병합.
  <!-- autopilot: {"stage": "done", "mode": "auto", "attempts": 1, "deps": [], "kind": "code", "scope": ["src/services/race_hub_service.py", "src/api/routes_today.py", "src/services/dashboard_service.py", "tests/test_race_hub_service.py", "tests/test_api_today.py", "tests/test_dashboard_service.py", "tests/test_ai_context.py"], "verify": ["python3 -m pytest tests/test_race_hub_service.py tests/test_api_today.py tests/test_dashboard_service.py tests/test_ai_context.py -q", "python3 scripts/check_data_consistency.py"]} -->
- **[P7-IMPL-RACE-HUB-UI]** Today 최상단 "목표 레이스 허브" — D-day·예측 기록 vs 목표·예측 추이. 프론트 전용, `REVIEW-05-vision-gap.md` E1 참조, 설계 근거는 `DECISIONS.md`의 `[P7-IMPL-RACE-HUB-UI]` 항목 필독. 앞 유닛 `P7-IMPL-RACE-HUB-API`의 `GET /api/v1/today/race-hub`(`apiFetch`가 `{data}`를 벗겨 `{goal, prediction, form}` 반환)를 쓴다. **이 명세의 코드는 그대로 구현할 것 — 구조를 바꾸고 싶으면 `DECISIONS.md`에 사유를 적고 중단.** 현황: Today 첫 화면이 문장 하나와 숫자 카드뿐이라 러너가 앱을 여는 이유("내가 레이스에 얼마나 가까운가")에 답하지 못한다.
  (1) `frontend/src/lib/types/index.ts` 끝에 추가:
  ```ts
  export interface RaceHubGoal {
  	id: number;
  	name: string | null;
  	race_date: string;
  	distance_km: number;
  	target_time_sec: number | null;
  	target_pace_sec_km: number | null;
  	days_left: number;
  	weeks_left: number;
  }
  export interface RaceHubPrediction {
  	bucket: string;
  	value_sec: number;
  	as_of: string;
  	gap_sec: number | null;
  	history: { date: string; value: number }[];
  }
  export interface RaceHub {
  	goal: RaceHubGoal | null;
  	prediction: RaceHubPrediction | null;
  	form: { ctl: number | null; tsb: number | null } | null;
  }
  ```
  `frontend/src/lib/api/today.ts`에 `getTodayRaceHub(): Promise<RaceHub>` 추가(`apiFetch<RaceHub>('/today/race-hub')`, `RaceHub`를 type import에 추가).
  (2) 신규 `frontend/src/lib/raceHub.ts`(순수 함수, 다른 모듈 import 금지):
  ```ts
  export type GapTone = 'ahead' | 'on' | 'behind' | 'unknown';
  /** 예측−목표 격차(초, 양수=목표보다 느림)를 톤과 문구로. |격차|<60초는 '목표 페이스권'. null이면 unknown. */
  export function gapVerdict(gapSec: number | null): { tone: GapTone; label: string } {
  	if (gapSec == null) return { tone: 'unknown', label: '목표 시간을 설정하면 격차를 보여줘요' };
  	if (Math.abs(gapSec) < 60) return { tone: 'on', label: '목표 페이스권' };
  	const abs = Math.abs(gapSec);
  	const h = Math.floor(abs / 3600);
  	const m = Math.floor((abs % 3600) / 60);
  	const s = Math.round(abs % 60);
  	const text = h > 0 ? `${h}시간 ${m}분` : `${m}분 ${s}초`;
  	return gapSec < 0
  		? { tone: 'ahead', label: `목표보다 ${text} 빠름` }
  		: { tone: 'behind', label: `목표보다 ${text} 느림` };
  }
  /** D-day 문구: 0이면 'D-DAY', 양수 'D-31', 음수 'D+3'. */
  export function countdownLabel(daysLeft: number): string {
  	if (daysLeft === 0) return 'D-DAY';
  	return daysLeft > 0 ? `D-${daysLeft}` : `D+${-daysLeft}`;
  }
  /** 목표 거리(km) 표기: 풀/하프/10K/5K 근사(±허용) 아니면 소수 1자리 km. */
  export function distanceLabel(km: number): string {
  	if (Math.abs(km - 42.195) <= 2.5) return '풀 마라톤';
  	if (Math.abs(km - 21.0975) <= 2) return '하프';
  	if (Math.abs(km - 10) <= 1.5) return '10K';
  	if (Math.abs(km - 5) <= 1) return '5K';
  	return `${km.toFixed(1)}km`;
  }
  ```
  (3) 신규 `frontend/tests/raceHub.test.mjs`(기존 `frontend/tests/chartScale.test.mjs`와 같은 방식, `../src/lib/raceHub.ts` import): `gapVerdict(null)` tone unknown; `gapVerdict(30)`/`gapVerdict(-59)` tone on; `gapVerdict(252)` → tone behind, label `목표보다 4분 12초 느림`; `gapVerdict(-3700)` → ahead, `목표보다 1시간 1분 빠름`; `countdownLabel(31)==='D-31'`, `(0)==='D-DAY'`, `(-3)==='D+3'`; `distanceLabel(42.195)==='풀 마라톤'`, `(21.1)==='하프'`, `(10)==='10K'`, `(5)==='5K'`, `(15)==='15.0km'`.
  (4) `frontend/src/lib/components/TrendChart.svelte` — props에 `formatValue?: (v: number) => string`(기본 `(v) => v.toFixed(1)`)을 추가하고, y축 최대·최소 라벨과 판독 값(`r.p.value.toFixed(1)` 부분)에서 `toFixed(1)` 대신 이 함수를 쓴다. 기존 호출부(메트릭 상세·Today CTL/ATL)는 prop을 안 넘기므로 동작 불변이어야 한다.
  (5) 신규 `frontend/src/lib/components/RaceHub.svelte` — props `{ hub: RaceHub }`. import: `base` from `$app/paths`, `formatDuration` from `$lib/format`, `gapVerdict, countdownLabel, distanceLabel` from `$lib/raceHub`, `TrendChart` from `./TrendChart.svelte`, 타입 `RaceHub`. 두 상태:
   - `hub.goal`이 null: `<a href="{base}/coach/plan/new" class="flex flex-col gap-1 rounded-lg border border-dashed border-border-subtle bg-surface-2 p-4 hover:bg-surface-3">`에 굵은 `목표 레이스를 등록해 보세요`와 `text-xs text-fg-muted`로 `D-day, 예측 기록, 목표까지의 격차와 준비도 추이를 여기서 계속 볼 수 있어요 →`.
   - 목표 있음: `<section aria-label="목표 레이스" class="flex flex-col gap-3 rounded-lg border border-border-subtle bg-surface-2 p-4">`. 위 줄: 왼쪽 `text-4xl font-bold font-mono leading-none`으로 `countdownLabel(goal.days_left)`, 오른쪽(`min-w-0 flex-1`)에 `truncate text-sm font-medium`으로 `goal.name ?? distanceLabel(goal.distance_km)`와 `text-xs text-fg-muted`로 `{goal.race_date} · {distanceLabel(goal.distance_km)}{goal.weeks_left > 0 ? ` · ${goal.weeks_left}주 남음` : ''}`. 중간 줄(`grid grid-cols-2 gap-3`): 두 칸 각각 `text-xs text-fg-muted` 라벨(`예측 기록`, `목표`)과 `font-mono text-2xl font-bold` 값 — 예측은 `prediction ? formatDuration(prediction.value_sec) : '—'`, 목표는 `goal.target_time_sec != null ? formatDuration(goal.target_time_sec) : '미설정'`(미설정이면 `text-fg-muted`, 크기는 `text-lg`). 격차 칩: `prediction`이 있으면 `gapVerdict(prediction.gap_sec)`로 `<p class="text-sm font-medium {tone 색}">`(ahead `text-semantic-green`, on `text-semantic-teal`, behind `text-semantic-amber`, unknown `text-fg-muted font-normal text-xs`)에 label. 예측 추이: `prediction && prediction.history.length > 1`이면 `text-xs text-fg-muted`로 `예측 기록 추이 · 최근 90일`과 `<TrendChart series={[{ key: 'pred', label: '예측', color: '#14b8a6', points: prediction.history }]} height={72} interactive={false} formatValue={formatDuration} />` — formatDuration은 초→`h:mm:ss`이므로 y 눈금·판독에 그대로 쓴다(값 실수는 `Math.round`로 넘길 것: `formatValue={(v) => formatDuration(Math.round(v))}`). `hub.form`이 있고 `tsb`가 null이 아니면 맨 아래 `text-xs text-fg-muted` 한 줄 `현재 폼(TSB) {tsb 부호 포함 정수}`.
  (6) `frontend/src/routes/today/+page.ts` — `TodayPageData`에 `raceHub: RaceHub | null` 추가, `Promise.all`에 `getTodayRaceHub().catch(() => null)`(반환 구조분해 이름 `raceHub`), 성공/에러 두 return 모두에 `raceHub`(에러 쪽은 null) 포함, import 정리. `frontend/src/routes/today/+page.svelte` — `import RaceHub from '$lib/components/RaceHub.svelte';` 추가하고 L0 `<section class="flex flex-col gap-3">`의 첫 자식(현재 `<RecommendationCard …/>` 앞)으로 `{#if data.raceHub}<RaceHub hub={data.raceHub} />{/if}` 삽입. 다른 순서·레이아웃은 건드리지 않는다.
  리뷰: 워크트리 diff를 명세와 대조 → 이탈 다수: (1) `raceHub.ts` API를 명세(gapVerdict/countdownLabel/distanceLabel)와 다르게 구현(gapTone/formatGap/predictionToSeries)하고 순수 모듈이 다른 모듈을 import; (2) 레이스 당일 `D-0` 표기(D-DAY 처리 없음), 거리 `42.195km` 원문 표기, weeks_left·TSB 폼 줄 누락; (3) 격차를 `+7:30`으로만 표기(의미 불명, 60초 이내 '목표 페이스권' 톤 없음); (4) 등록 유도 카드가 한 줄짜리(명세는 제목+설명). 채택: 타입명 `RaceHubData`·API 함수명 `getRaceHub`·TrendChart `formatValue` 확장·Today 마운트 위치는 명세 취지와 같아 유지. 정정: main에서 명세대로 raceHub.ts/테스트/RaceHub.svelte 재작성(`fix(frontend): RaceHub 명세 정합`) 후 실데이터 사본에서 브라우저 확인. (verify가 `blocked`된 것은 코드가 아니라 내가 러너를 `PATH=/usr/bin:$PATH`로 띄워 구버전 시스템 node가 잡혀 `tests/*.test.mjs` 글롭을 못 푼 환경 문제 — 수동으로 test:unit 86·check 통과 확인.)
  <!-- autopilot: {"stage": "done", "mode": "auto", "attempts": 1, "deps": ["P7-IMPL-RACE-HUB-API"], "kind": "code", "scope": ["frontend/src/lib/raceHub.ts", "frontend/tests/raceHub.test.mjs", "frontend/src/lib/types/index.ts", "frontend/src/lib/api/today.ts", "frontend/src/lib/components/RaceHub.svelte", "frontend/src/lib/components/TrendChart.svelte", "frontend/src/routes/today/+page.ts", "frontend/src/routes/today/+page.svelte"], "verify": ["cd frontend && npm install && npm run test:unit && npm run check && npm run build"]} -->
- **[P7-IMPL-ROUTE-MAP]** 활동 상세에 타일 없는 SVG 경로 지도(페이스/심박 색상) — 프론트 전용, `REVIEW-05-vision-gap.md` E2 참조, 설계 근거는 `DECISIONS.md`의 `[P7-IMPL-ROUTE-MAP]` 항목 필독. **이미 main에 있다 — 수정 금지: `frontend/src/lib/routeGeometry.ts`, `frontend/tests/routeGeometry.test.mjs`, `ActivityStreamPoint`의 `latitude`/`longitude`. 아래 (1)(2)(3)은 건너뛰고 (4)(5)만 구현하되 (2)에 적힌 함수들을 `$lib/routeGeometry`에서 import해 쓴다.** **이 명세의 코드는 그대로 구현할 것 — 구조를 바꾸고 싶으면 `DECISIONS.md`에 사유를 적고 중단.** 현황: 활동 스트림에 GPS(`latitude`/`longitude`)가 있는데(실데이터 활동 107개, 20만 점) 화면에 지도가 없다. 로컬 퍼스트 원칙상 외부 타일 요청 없이 좌표를 직접 SVG로 그린다. 데이터는 이미 `data.activity.streams`(활동 상세 응답)에 있어 API 변경이 없다.
  (1) `frontend/src/lib/types/index.ts`의 `ActivityStreamPoint`에 `latitude?: number | null;`과 `longitude?: number | null;` 추가.
  (2) 신규 `frontend/src/lib/routeGeometry.ts`(순수 함수, 다른 모듈 import 금지):
  ```ts
  export interface StreamLike {
  	latitude?: number | null;
  	longitude?: number | null;
  	speed_ms?: number | null;
  	heart_rate?: number | null;
  }
  export interface RoutePoint { lat: number; lng: number; pace: number | null; hr: number | null }
  export interface ProjectedPoint { x: number; y: number; pace: number | null; hr: number | null }
  export interface ProjectedRoute { width: number; height: number; points: ProjectedPoint[] }
  /** GPS가 유효한 스트림 점만 RoutePoint로. 유효: 유한수, |lat|≤90, |lng|≤180, (0,0) 제외. pace는 speed_ms>0일 때 1000/speed_ms(초/km), 아니면 null. */
  export function routePoints(streams: StreamLike[]): RoutePoint[] {
  	const out: RoutePoint[] = [];
  	for (const s of streams) {
  		const lat = s.latitude;
  		const lng = s.longitude;
  		if (lat == null || lng == null || !Number.isFinite(lat) || !Number.isFinite(lng)) continue;
  		if (Math.abs(lat) > 90 || Math.abs(lng) > 180 || (lat === 0 && lng === 0)) continue;
  		out.push({
  			lat,
  			lng,
  			pace: s.speed_ms != null && s.speed_ms > 0 ? 1000 / s.speed_ms : null,
  			hr: s.heart_rate ?? null
  		});
  	}
  	return out;
  }
  /** 균등 간격으로 최대 max개로 줄인다(첫·끝 점 항상 포함). items.length ≤ max면 그대로. */
  export function downsample<T>(items: T[], max: number): T[] {
  	if (items.length <= max || max < 2) return items;
  	const out: T[] = [];
  	for (let i = 0; i < max; i++) out.push(items[Math.round((i * (items.length - 1)) / (max - 1))]);
  	return out;
  }
  /** 위경도를 등장방형(위도 중앙 cos 보정) 투영해 긴 변이 maxSize−2·pad가 되게 SVG 좌표로. 북쪽이 위(y 반전). 점이 2개 미만이거나 범위가 0이면 null. */
  export function projectRoute(points: RoutePoint[], maxSize: number, pad: number): ProjectedRoute | null {
  	if (points.length < 2) return null;
  	let minLat = Infinity, maxLat = -Infinity, minLng = Infinity, maxLng = -Infinity;
  	for (const p of points) {
  		if (p.lat < minLat) minLat = p.lat;
  		if (p.lat > maxLat) maxLat = p.lat;
  		if (p.lng < minLng) minLng = p.lng;
  		if (p.lng > maxLng) maxLng = p.lng;
  	}
  	const k = Math.cos((((minLat + maxLat) / 2) * Math.PI) / 180);
  	const spanX = (maxLng - minLng) * k;
  	const spanY = maxLat - minLat;
  	const span = Math.max(spanX, spanY);
  	if (!(span > 0)) return null;
  	const scale = (maxSize - 2 * pad) / span;
  	return {
  		width: spanX * scale + 2 * pad,
  		height: spanY * scale + 2 * pad,
  		points: points.map((p) => ({
  			x: (p.lng - minLng) * k * scale + pad,
  			y: (maxLat - p.lat) * scale + pad,
  			pace: p.pace,
  			hr: p.hr
  		}))
  	};
  }
  /** 유효 값의 5~95퍼센타일 범위(이상치 제외). 유효 값 2개 미만이면 null, lo===hi면 hi=lo+1. */
  export function robustRange(values: (number | null)[]): { lo: number; hi: number } | null {
  	const v = values.filter((x): x is number => x != null && Number.isFinite(x)).sort((a, b) => a - b);
  	if (v.length < 2) return null;
  	const at = (q: number) => v[Math.min(v.length - 1, Math.max(0, Math.round(q * (v.length - 1))))];
  	const lo = at(0.05);
  	let hi = at(0.95);
  	if (hi === lo) hi = lo + 1;
  	return { lo, hi };
  }
  /** '#rrggbb' 두 색 사이 선형 보간(t는 0~1로 clamp). */
  export function lerpColor(a: string, b: string, t: number): string {
  	const c = Math.min(1, Math.max(0, t));
  	const pa = [1, 3, 5].map((i) => parseInt(a.slice(i, i + 2), 16));
  	const pb = [1, 3, 5].map((i) => parseInt(b.slice(i, i + 2), 16));
  	return '#' + pa.map((x, i) => Math.round(x + (pb[i] - x) * c).toString(16).padStart(2, '0')).join('');
  }
  /** 값→색. pace: 빠름(작은 값) 파랑 #3b82f6 → 느림 주황 #f97316. hr: 낮음 청록 #14b8a6 → 높음 빨강 #ef4444. 값 또는 범위가 없으면 회색 #64748b. */
  export function segmentColor(value: number | null, range: { lo: number; hi: number } | null, mode: 'pace' | 'hr'): string {
  	if (value == null || !range) return '#64748b';
  	const t = (value - range.lo) / (range.hi - range.lo);
  	return mode === 'pace' ? lerpColor('#3b82f6', '#f97316', t) : lerpColor('#14b8a6', '#ef4444', t);
  }
  ```
  (3) 신규 `frontend/tests/routeGeometry.test.mjs`(기존 `frontend/tests/chartScale.test.mjs`와 같은 방식, `../src/lib/routeGeometry.ts` import): `routePoints` — 유효 점만 남김(null·NaN·(0,0)·lat 91 제외), `speed_ms=2.5`→pace 400, `speed_ms=0`→pace null; `downsample` — 10개→4개는 길이 4·첫 끝 포함, 3개 max 10은 그대로; `projectRoute` — 정사각 위경도 범위(적도 근처)에서 `width≈height`, 위도만 변하는 점 3개(경도 동일)면 `width===2*pad`이고 북쪽(위도 큰) 점의 y가 더 작음, 점 1개 → null, 모든 점 동일 → null; `robustRange` — `[1..100]`에서 lo≈6, hi≈95, null 무시, 값 1개 → null, 전부 같으면 hi=lo+1; `lerpColor('#000000','#ffffff',0.5)==='#808080'`, t 범위 밖 clamp; `segmentColor(null,…)==='#64748b'`, `segmentColor(lo, range,'pace')==='#3b82f6'`, `segmentColor(hi, range,'pace')==='#f97316'`.
  (4) 신규 `frontend/src/lib/components/RouteMap.svelte` — props `{ streams: ActivityStreamPoint[] }`(타입 import `$lib/types`). `routePoints` → `downsample(…, 300)` → `projectRoute(points, 320, 12)` 를 `$derived`로. `route`가 null이면 아무것도 렌더링하지 않는다(`{#if route}`). 모드 `let mode = $state<'pace' | 'hr'>('pace')`; 심박 값이 유효한 점이 2개 미만(`robustRange(hr들)`이 null)이면 모드 토글 숨기고 pace 고정. 렌더: `<section class="flex flex-col gap-2" aria-label="경로">` — 머리줄 `flex items-center justify-between`: 왼쪽 `<p class="text-xs uppercase tracking-wide text-fg-muted">경로</p>`, 오른쪽(토글 표시 조건 충족 시) 두 버튼 `페이스`/`심박`(`type="button"`, `aria-pressed={mode === '…'}`, 활성은 `text-fg-primary underline`, 비활성 `text-fg-muted`, `text-xs`). 본문: `<div class="flex justify-center rounded-lg border border-border-subtle bg-surface-2 p-3">` 안에 `<svg viewBox="0 0 {route.width} {route.height}" class="w-full" style="max-height:280px;aspect-ratio:{route.width}/{route.height}" role="img" aria-label="활동 경로 지도(타일 없음)">`; 연속한 점쌍마다 `<line x1 y1 x2 y2 stroke={segmentColor(두 점 값 평균(null이면 있는 쪽, 둘 다 null이면 null), range, mode)} stroke-width="3" stroke-linecap="round" />`(range는 모드별 `robustRange` 를 `$derived`); 시작점 `<circle r="5" fill="#22c55e" stroke="#0b1220" stroke-width="2">`, 끝점 `<circle r="5" fill="#f8fafc" stroke="#0b1220" stroke-width="2">`(마지막 점). 아래 범례 한 줄 `flex items-center gap-2 text-[10px] text-fg-muted`: 모드 pace면 `빠름`, 그라데이션 막대(`h-1.5 flex-1 rounded`, `style="background: linear-gradient(to right, #3b82f6, #f97316)"`), `느림`; hr면 `낮음`, `linear-gradient(to right, #14b8a6, #ef4444)`, `높음`. 범례 아래 `text-[10px] text-fg-muted`로 `지도 타일 없이 GPS 좌표만으로 그린 경로 · 북쪽이 위`.
  (5) `frontend/src/routes/library/[id]/+page.svelte` — `import RouteMap from '$lib/components/RouteMap.svelte';` 추가하고, 핵심 통계 바(`<!-- 핵심 통계 바 -->` 블록)와 `<!-- 핵심 메트릭 그리드` 사이에 `<RouteMap streams={streams ?? []} />` 삽입. 다른 곳은 건드리지 않는다.
  리뷰: 워크트리 diff를 명세와 대조 → 이탈: (1) 모드 토글(페이스/심박)과 `mapMode` 상태를 컴포넌트가 아니라 페이지에 둠, 심박 데이터가 없어도 토글 노출·`aria-pressed` 없음; (2) 배치가 명세(핵심 통계 바 다음, 핵심 메트릭 앞)가 아니라 핵심 메트릭·페이스 차트 뒤 → 지도가 화면 아래로 밀림; (3) 카드 테두리·범례(빠름→느림 그라데이션)·"타일 없이 GPS 좌표만으로 그린 경로 · 북쪽이 위" 문구 누락, 끝점 색·투영 크기(320/12) 상이. 채택: `routeGeometry` 함수 사용·다운샘플·`vector-effect` 유지. 정정: main에서 RouteMap을 명세대로 재작성(토글·범례 컴포넌트 내부화)하고 페이지에서 배치·토글 상태 제거 후 실데이터 사본 브라우저 확인.
  <!-- autopilot: {"stage": "done", "mode": "auto", "attempts": 1, "deps": ["P7-IMPL-RACE-HUB-UI"], "kind": "code", "scope": ["frontend/src/lib/routeGeometry.ts", "frontend/tests/routeGeometry.test.mjs", "frontend/src/lib/types/index.ts", "frontend/src/lib/components/RouteMap.svelte", "frontend/src/routes/library/[id]/+page.svelte"], "verify": ["cd frontend && npm install && npm run test:unit && npm run check && npm run build"]} -->
- **[P7-IMPL-ACTIVITY-SPLITS]** 활동 상세에 km 스플릿 막대와 고도 프로필 — 프론트 전용, `REVIEW-05-vision-gap.md` E2 참조, 설계 근거는 `DECISIONS.md`의 `[P7-IMPL-ACTIVITY-SPLITS]` 항목 필독. **이미 main에 있다 — 수정 금지: `frontend/src/lib/splits.ts`, `frontend/tests/splits.test.mjs`. 아래 (1)(2)는 건너뛰고 (3)(4)(5)만 구현하되 `Split`, `computeSplits`, `cumulativeDistance`를 `$lib/splits`에서 import해 쓴다.** **이 명세의 알고리즘·시그니처는 그대로 구현할 것 — 바꾸고 싶으면 `DECISIONS.md`에 사유를 적고 중단.** 현황: 활동 상세에 구간(km)별 페이스와 고도 정보가 없다. 실데이터의 Garmin 스트림은 `distance_m`이 null이고 `elapsed_sec`가 샘플 인덱스로 저장된 경우가 있어(P7-DATA-STREAM-ELAPSED) 저장값을 믿을 수 없으므로 활동 총 시간·거리에 맞춰 재구성한다.
  (1) 신규 `frontend/src/lib/splits.ts`(순수 함수, 다른 모듈 import 금지):
  ```ts
  export interface SplitStream {
  	elapsed_sec: number;
  	distance_m: number | null;
  	speed_ms: number | null;
  	heart_rate: number | null;
  	altitude_m: number | null;
  }
  export interface Split { km: number; distanceM: number; sec: number; paceSecKm: number; avgHr: number | null; elevDelta: number | null }
  ```
  `export function sampleTimes(streams: SplitStream[], totalSec: number): number[]` — 샘플별 경과 초. n<2 또는 totalSec≤0이면 `streams.map((s) => s.elapsed_sec)`. 마지막 `elapsed_sec`가 `totalSec × 0.9` 이상이면 `elapsed_sec` 그대로, 아니면 `i × totalSec / (n − 1)`(등간격 재환산).
  `export function cumulativeDistance(streams: SplitStream[], totalSec: number, totalDistM: number): number[]` — 샘플별 누적 거리(m). 모든 샘플의 `distance_m`이 non-null이고 마지막 값이 0보다 크면 그 값을 사용, 아니면 `t = sampleTimes(...)`로 `d[0]=0`, `d[i] = d[i-1] + max(0, speed_ms ?? 직전 유효 속도 ?? 0) × (t[i] − t[i-1])`로 적분한다. 마지막 누적값이 0보다 크고 `totalDistM > 0`이면 전체를 `totalDistM / d[last]`배 해 총 거리를 활동 거리에 맞춘다(0이면 그대로 반환).
  `export function computeSplits(streams: SplitStream[], totalSec: number, totalDistM: number): Split[]` — `streams.length < 2 || totalSec <= 0 || totalDistM < 1000`이면 `[]`. `t = sampleTimes`, `d = cumulativeDistance`로 경계 `k×1000`m(k=1,2,…, `≤ d[last]`)마다 인접 두 샘플 사이를 선형보간해 통과 시각을 구하고, 구간 k의 `sec` = 통과 시각(k) − 통과 시각(k−1)(시작은 `t[0]`), `distanceM`=1000, `paceSecKm = sec`. 마지막 경계 이후 잔여 거리가 200m 이상이면 마지막 구간을 추가(`distanceM`=잔여, `sec` = `t[last]` − 마지막 경계 시각, `paceSecKm = sec / (distanceM/1000)`, `km`=번호). 각 구간의 `avgHr`은 그 구간 안(시작 시각 ≤ t < 끝 시각) 샘플의 non-null 심박 평균(반올림 정수, 없으면 null), `elevDelta`는 구간 끝·시작 시각에 가장 가까운 샘플의 `altitude_m` 차(둘 중 하나가 null이면 null, 소수 1자리로 반올림).
  (2) 신규 `frontend/tests/splits.test.mjs`(기존 `frontend/tests/streamAxis.test.mjs`와 같은 방식, `../src/lib/splits.ts` import): 헬퍼로 1초 간격 등속 스트림 생성. (a) 1001샘플, `speed_ms`=4, `distance_m` null, `elapsed_sec`=0..1000, `totalSec=1000`, `totalDistM=4000` → 4구간, 각 `sec≈250`(±1), `paceSecKm≈250`, `km` 1..4; (b) `distance_m`가 0..4000 선형으로 채워진 경우 같은 결과; (c) `elapsed_sec`가 인덱스(0..500, 501샘플)인데 `totalSec=1000`이면 재환산되어 (a)와 같은 구간 시간; (d) `totalDistM=2500`(속도 적분 후 총 거리 스케일링)이면 3구간이고 마지막 `distanceM≈500`, 마지막 `paceSecKm≈`(`sec/0.5`); (e) `totalDistM=800` → `[]`, 샘플 1개 → `[]`; (f) 심박 150 일정이면 모든 구간 `avgHr===150`, 심박 전부 null이면 null; (g) 고도가 0→80 선형(1000샘플 구간)이면 각 `elevDelta`가 20(±0.1) — 4km 활동; (h) 점차 빨라지는 속도(2→4 m/s)에서 `paceSecKm`이 구간마다 단조 감소.
  (3) 신규 `frontend/src/lib/components/SplitBars.svelte` — props `{ splits: Split[] }`. `splits.length === 0`이면 렌더 안 함. `<section class="flex flex-col gap-2" aria-label="구간별 페이스">`, 머리줄 `<p class="text-xs uppercase tracking-wide text-fg-muted">구간별 페이스</p>` + 오른쪽 `text-[10px] text-fg-muted` `스트림 기반 추정`. 가장 빠른 페이스 `best`, 평균 `avg`(구간 sec 합 / 거리 합 ×1000)를 계산. 행마다 `flex items-center gap-2 text-xs`: `<span class="w-6 text-right font-mono text-fg-muted">{km}</span>`(마지막 부분 구간은 `{km}`가 아닌 `{(distanceM/1000).toFixed(1)}`km 표기), 막대 트랙 `h-3 flex-1 rounded bg-surface-3` 안의 채움 `h-3 rounded` 너비 `{Math.max(8, (best / paceSecKm) * 100)}%`(빠를수록 김), 색은 최고 구간 `#22c55e`, 평균보다 빠르면 `#3b82f6`, 아니면 `#f59e0b`; 오른쪽 `w-14 text-right font-mono text-fg-secondary`에 `formatPace(paceSecKm)`에서 `/km` 뺀 `m:ss`(=`formatPace(...).replace('/km','')`), 그 옆 `w-10 text-right font-mono text-fg-muted`에 `avgHr ?? '—'`. 맨 위 열 머리는 두지 않는다. 최고 구간 행에는 이름표 대신 막대 색만 다르게(별도 텍스트 없음). `formatPace` import는 `$lib/format`.
  (4) 신규 `frontend/src/lib/components/ElevationProfile.svelte` — props `{ streams: ActivityStreamPoint[]; totalSec: number; totalDistM: number }`. `cumulativeDistance`로 x(km) 계산, 고도가 유효한 샘플(`altitude_m != null`)이 10개 미만이거나 (최대−최소)고도가 3m 미만이면 렌더 안 함. 최대 200점으로 균등 다운샘플. `<section class="flex flex-col gap-2" aria-label="고도 프로필">` 머리줄: `고도 프로필` + 오른쪽 `text-[10px] text-fg-muted` `{Math.round(min)}~{Math.round(max)} m`. 차트: `<div class="relative rounded-lg border border-border-subtle bg-surface-2 p-2">` 안 `<svg viewBox="0 0 600 80" preserveAspectRatio="none" style="width:100%;height:80px;display:block" aria-hidden="true">`에 면적 `<polygon fill="#38bdf8" fill-opacity="0.18">`(좌하단·곡선·우하단)과 선 `<polyline fill="none" stroke="#38bdf8" stroke-width="2" vector-effect="non-scaling-stroke">`. y는 (max−min)에 5% 여백. 아래 `flex justify-between font-mono text-[10px] text-fg-muted`로 `0`과 `{(총거리/1000).toFixed(1)}km`.
  (5) `frontend/src/routes/library/[id]/+page.svelte` — `import SplitBars …`, `import ElevationProfile …`, `import { computeSplits } from '$lib/splits';` 추가. script에 `const splits = $derived(streams && core?.duration_sec && core.distance_m ? computeSplits(streams, core.duration_sec, core.distance_m) : []);` 추가. `<RouteMap …/>` 바로 다음에 `<SplitBars {splits} />`와 `{#if streams && core.duration_sec && core.distance_m}<ElevationProfile {streams} totalSec={core.duration_sec} totalDistM={core.distance_m} />{/if}` 삽입. 다른 곳은 건드리지 않는다.
  리뷰: 워크트리 diff를 명세와 대조. SplitBars는 명세와 다르게 페이스 라벨을 막대 안에, 고도 변화 열을 추가했고 막대 너비를 min~max 선형(25~100%)으로 계산했으나 의도(빠를수록 길게·최고 구간 green·평균보다 빠름 blue)와 일치해 채택. 이탈: (1) ElevationProfile이 x축을 거리가 아닌 샘플 인덱스로 그림(총 거리·`cumulativeDistance` 미사용), 시작/끝 거리 라벨·min~max 표기 문구가 `↑max ↓min`으로 오해 소지; (2) 마지막 부분 구간의 km 표기(0.5km 등)가 없어 `km` 번호만 표시. 정정: main에서 ElevationProfile을 거리축·라벨로 재작성하고 부분 구간 라벨을 보강한 뒤 실데이터 사본 브라우저 확인.
  <!-- autopilot: {"stage": "done", "mode": "auto", "attempts": 1, "deps": ["P7-IMPL-ROUTE-MAP"], "kind": "code", "scope": ["frontend/src/lib/splits.ts", "frontend/tests/splits.test.mjs", "frontend/src/lib/components/SplitBars.svelte", "frontend/src/lib/components/ElevationProfile.svelte", "frontend/src/routes/library/[id]/+page.svelte"], "verify": ["cd frontend && npm install && npm run test:unit && npm run check && npm run build"]} -->
- **[P7-IMPL-ACTIVITY-HERO]** 활동 상세 요약 상단을 히어로 수치로 — 위계 부여 + 차트 선 굵기 왜곡 수정. 프론트 전용, `REVIEW-05-vision-gap.md` E2·E5 참조, 설계 근거는 `DECISIONS.md`의 `[P7-IMPL-ACTIVITY-HERO]` 항목 필독. **이 명세의 마크업·클래스는 그대로 구현할 것 — 구조를 바꾸고 싶으면 `DECISIONS.md`에 사유를 적고 중단.** 현황: 활동 상세 최상단이 한 줄짜리 작은 통계 바(모든 값이 같은 크기)라 "이 러닝이 어땠나"가 한눈에 안 읽힌다. 또 `Sparkline`이 `preserveAspectRatio="none"`으로 가로로 늘어날 때 선 굵기가 왜곡된다(데스크톱 폭에서 눈에 띔).
  (1) `frontend/src/routes/library/[id]/+page.svelte`의 `<!-- 핵심 통계 바 -->` 블록(`<div class="flex flex-wrap gap-x-5 …">…</div>` 전체)을 아래로 교체한다(`core.distance_m`이 null이면 거리 히어로 줄만 생략하고 나머지는 유지):
  ```svelte
  		<!-- 히어로 통계 -->
  		<section class="flex flex-col gap-3" aria-label="활동 요약">
  			{#if core.distance_m != null}
  				<div class="flex items-end gap-2">
  					<span class="font-mono text-5xl font-bold leading-none">{(core.distance_m / 1000).toFixed(2)}</span>
  					<span class="pb-1 text-lg text-fg-muted">km</span>
  				</div>
  			{/if}
  			<div class="grid grid-cols-3 gap-3 rounded-lg border border-border-subtle bg-surface-2 px-4 py-3">
  				<div class="flex flex-col gap-0.5">
  					<span class="text-[11px] text-fg-muted">시간</span>
  					<span class="font-mono text-xl font-bold">{core.duration_sec != null ? formatDuration(core.duration_sec) : '—'}</span>
  				</div>
  				<div class="flex flex-col gap-0.5">
  					<span class="text-[11px] text-fg-muted">평균 페이스</span>
  					<span class="font-mono text-xl font-bold">{core.avg_pace_sec_km != null ? formatPace(core.avg_pace_sec_km).replace('/km', '') : '—'}<span class="text-xs font-normal text-fg-muted"> /km</span></span>
  				</div>
  				<div class="flex flex-col gap-0.5">
  					<span class="text-[11px] text-fg-muted">평균 심박</span>
  					<span class="font-mono text-xl font-bold">{core.avg_hr ?? '—'}<span class="text-xs font-normal text-fg-muted"> bpm</span></span>
  				</div>
  			</div>
  			{#if core.elevation_gain != null && (core.elevation_gain as number) > 0}
  				{@const elev = formatUnitValue(core.elevation_gain as number, 'm')}
  				<p class="text-xs text-fg-muted">누적 상승 <span class="font-mono font-bold text-fg-secondary">{elev.display}</span> {elev.unit}</p>
  			{/if}
  		</section>
  ```
  `formatDistance` import가 더 이상 쓰이지 않으면 import 목록에서 제거한다(`npm run check` 경고 없이). 이 유닛의 앞 유닛이 넣은 `<RouteMap>`·`<SplitBars>`·`<ElevationProfile>`은 그대로 히어로 다음에 남긴다.
  (2) `frontend/src/lib/components/Sparkline.svelte` — `<polyline>`(또는 선을 그리는 요소)에 `vector-effect="non-scaling-stroke"`를 추가해 SVG가 가로로 늘어나도 선 굵기가 일정하게 한다. 그 외 로직·props는 바꾸지 않는다. 파일을 먼저 읽어 선 요소가 여러 개면(면적 채움 제외) 모두 적용.
  리뷰: 자동 실행 없이 main에서 명세의 마크업 그대로 직접 구현(자동 구현이 명세 이탈을 반복해 재작업이 더 커서). 히어로 거리 5xl·3열 그리드·누적 상승, `Sparkline` `vector-effect="non-scaling-stroke"` 적용, 실데이터 사본 브라우저 확인. 이탈 없음.
  <!-- autopilot: {"stage": "done", "mode": "auto", "attempts": 0, "deps": ["P7-IMPL-ACTIVITY-SPLITS"], "kind": "code", "scope": ["frontend/src/routes/library/[id]/+page.svelte", "frontend/src/lib/components/Sparkline.svelte"], "verify": ["cd frontend && npm install && npm run test:unit && npm run check && npm run build"]} -->
- **[P7-IMPL-LIST-STORY]** 활동 목록을 "주 단위 이야기"로 — 주별 그룹(주간 km·횟수·시간·주간 막대)·행마다 경로 썸네일·거리 히어로·칩 필터. REVIEW-05 E4 잔여. 백엔드: `get_activity_list` 응답 각 활동에 `route`(러닝 GPS를 ≤32점으로 다운샘플한 [lat,lng] 배열, 없으면 null). 프론트: 순수 `activityList.ts`(`weekGroups`·`weekLabel`·`dayLabel`), `RouteThumb.svelte`(routeGeometry 재사용), 목록 페이지 재작성(종목 칩·거리 칩·검색, 네이티브 날짜 입력 제거). main에서 직접 구현.
  리뷰: main에서 직접 구현(자동 구현의 명세 이탈 반복 회피). 백엔드 route 미리보기(≤32점, 테스트 2)·weekGroups 순수 함수(테스트 4)·RouteThumb·목록 재작성(종목/거리 칩·검색, 네이티브 date 입력 제거)을 실데이터 사본에서 확인. 기간 필터는 후속으로 이월(이탈로 기록).
  <!-- autopilot: {"stage": "done", "mode": "auto", "attempts": 0, "deps": ["P7-IMPL-ARCHIVE"], "kind": "code", "scope": ["src/services/activity_service.py", "tests/test_activity_service.py", "frontend/src/lib/activityList.ts", "frontend/tests/activityList.test.mjs", "frontend/src/lib/components/RouteThumb.svelte", "frontend/src/routes/library/activities/+page.svelte", "frontend/src/lib/types/index.ts"], "verify": ["python3 -m pytest tests/test_activity_service.py -q", "cd frontend && npm run test:unit && npm run check && npm run build"]} -->
- **[P7-IMPL-FORM-CHART]** 피트니스·폼 시그니처 차트(E3) — Today의 CTL/ATL 차트를 90일 이력 + 레이스까지의 TSB 예측(테이퍼/유지 점선)으로: 위 패널 CTL·ATL(공통 스케일), 아래 패널 TSB 면적(0선·레이스 최적 밴드 +5~+15 음영), 오늘 세로선, 레이스 깃발. 순수 `formChart.ts`(패널 스케일·경로·밴드 계산), `FormChart.svelte`(스크럽 판독 포함). main에서 직접 구현.
  리뷰: main에서 직접 구현. FormChart(위: CTL·ATL 공통 스케일 / 아래: TSB 면적+레이스 최적 밴드 / 오늘·레이스 세로선 / 레이스 아침 TSB 예측 점선 / 스크럽), formChart.ts 테스트 5. 실데이터 사본에서 확인하다 **TRIMP 누락으로 CTL이 붕괴(TSB −28→+2.6)**한 데이터 결함을 발견해 P7-DATA-LOAD-BACKFILL로 수정(DECISIONS 참조). 이탈: 밴드 상한 +15→+25 정정.
  <!-- autopilot: {"stage": "done", "mode": "auto", "attempts": 0, "deps": ["P7-IMPL-RACE-PROJECTION"], "kind": "code", "scope": ["frontend/src/lib/formChart.ts", "frontend/tests/formChart.test.mjs", "frontend/src/lib/components/FormChart.svelte", "frontend/src/routes/today/+page.svelte", "frontend/src/routes/today/+page.ts"], "verify": ["cd frontend && npm install && npm run test:unit && npm run check && npm run build"]} -->
- **[P7-IMPL-VISUAL-SYSTEM]** 비주얼 시스템(E5) — 프론트 전용, `REVIEW-05-vision-gap.md` E5, 설계 근거 `DECISIONS.md`의 `[P7-IMPL-VISUAL-SYSTEM]`. **이 명세의 마크업·클래스는 그대로 구현할 것 — 구조를 바꾸고 싶으면 `DECISIONS.md`에 사유를 적고 중단. 이미 main에 있다(수정 금지): `frontend/src/lib/scoreRing.ts`(`ringFraction`, `ringDash`)와 `frontend/tests/scoreRing.test.mjs`.** 현황: Today L1의 UTRS/CIRS/TSB가 같은 사각 `MetricCell`이라 상태 의미·위계가 안 보이고, 탭바는 텍스트뿐이며, 데스크톱(≥1024px)은 모바일 화면을 그대로 늘린 형태다.
  (1) 신규 `frontend/src/lib/components/ScoreRing.svelte` — props `{ slug: string; label: string; value: number | null; min?: number; max?: number; decimals?: number; provider: ProviderKey | null; status?: MetricStatus; unavailable?: boolean; onDrill?: (p: { slug: string; provider: ProviderKey | null }) => void }`(기본 `min=0`, `max=100`, `decimals=0`; 타입은 `$lib/types`의 `MetricCellProps`와 같은 출처, `MetricStatus`는 `MetricCell`이 쓰는 status 문자열 유니온 — `MetricCell.svelte`·`$lib/types`를 먼저 읽고 같은 이름을 쓸 것). 구조: 바깥 `<div role="button" tabindex="0" aria-label="{label} {값} — 눌러서 계산 근거 보기">`(onDrill 있고 값 있을 때만 button 속성·클릭·Enter/Space로 `onDrill({slug, provider})`, `unavailable`이면 비활성), 클래스 `flex flex-col items-center gap-1.5 rounded-lg border border-border-subtle bg-surface-2 p-3 hover:bg-surface-3 cursor-pointer`. 안에 `<svg viewBox="0 0 64 64" class="h-16 w-16 -rotate-90">`: 트랙 `<circle cx="32" cy="32" r="26" fill="none" stroke-width="6" class="stroke-surface-3">`, 채움 `<circle cx="32" cy="32" r="26" fill="none" stroke-width="6" stroke-linecap="round" stroke-dasharray={ringDash(ringFraction(value, min, max), 26)} style="stroke:{링 색}">`(`unavailable`/null이면 채움 생략). 링 중앙에 값(절대 배치 `absolute inset-0 flex items-center justify-center font-mono text-lg font-bold`, `value.toFixed(decimals)`, 없으면 `—`)을 두려면 svg를 `<div class="relative">`로 감싼다. 링 색: excellent `#22c55e`, good `#14b8a6`, neutral `#94a3b8`, caution `#f59e0b`, poor `#ef4444`, status 없으면 `#94a3b8`. 링 아래 `<span class="text-xs font-medium">{label}</span>`, 상태 문구(`MetricCell`과 같은 매핑: 매우 좋음/양호/보통/주의/나쁨, status 없으면 생략)는 링 색과 같은 색의 `text-[11px]`, 마지막에 Provider 배지(`providerLabelCompact`, `providerBadgeClass` from `$lib/provider`, 클래스 `rounded px-1.5 py-0.5 text-[10px] text-white`, provider 없으면 생략).
  (2) `frontend/src/routes/today/+page.svelte` — L1의 `<MetricCell slug="utrs" …/>`, `cirs`, `tsb` 세 개를 `ScoreRing`으로 교체(props는 기존과 같은 값 전달: value·provider·status·unavailable·onDrill={handleDrill}). UTRS·CIRS는 `min=0 max=100 decimals=0`, TSB는 `min={-40} max={40} decimals={0}`. 세 개를 감싸는 그리드는 그대로 두되 `MetricCell` import가 더 안 쓰이면 제거.
  (3) 신규 `frontend/src/lib/components/Icon.svelte` — props `{ name: 'today' | 'library' | 'coach'; class?: string }`. `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" class="h-5 w-5 {class}" aria-hidden="true">` 안에 name별 경로: today = `<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>`, library = `<rect x="3" y="4" width="7" height="7" rx="1"/><rect x="14" y="4" width="7" height="7" rx="1"/><rect x="3" y="15" width="7" height="5" rx="1"/><rect x="14" y="15" width="7" height="5" rx="1"/>`, coach = `<path d="M21 12a8 8 0 0 1-11.6 7.1L4 20l1-4.4A8 8 0 1 1 21 12z"/>`.
  (4) `frontend/src/routes/+layout.svelte` — `tabs`에 `icon: 'today' | 'library' | 'coach'` 추가, 탭 링크를 `<a … class="flex flex-1 flex-col items-center gap-0.5 py-2 text-[11px] {활성 ? 'text-fg-primary' : 'text-fg-muted'}"><Icon name={tab.icon} />{tab.label}</a>`로(`aria-current` 유지). `<main>`을 `class="mx-auto w-full max-w-3xl flex-1 pb-20"`로, 하단 `<nav>`는 그대로 전폭 고정(내부만 `mx-auto flex w-full max-w-3xl`로 감싸 콘텐츠와 폭을 맞춘다). 헤더 안쪽도 같은 `mx-auto max-w-3xl` 정렬.
  (5) 데스크톱 Today 2열은 이번 유닛 범위 밖(후속) — 위 `max-w-3xl` 중앙 정렬만 적용한다.
  리뷰: 워크트리 diff를 명세와 줄 단위 대조 — ScoreRing 구조(트랙/채움 circle, dasharray, 중앙 값, 색 매핑, 라벨·상태·Provider 배지)·Today 3개 교체(UTRS/CIRS 0~100, TSB −40~40)·Icon 3종 경로·레이아웃(탭 아이콘, max-w-3xl 중앙 정렬, 헤더/네비 폭 정렬) 명세와 일치. 사소한 이탈: 비대화형(값 없음)에서도 `cursor-pointer hover:bg-surface-3`가 남음 → main에서 보정. test:unit·check 통과. 브라우저 확인은 병합 후.
  <!-- autopilot: {"stage": "done", "mode": "auto", "attempts": 1, "deps": ["P7-IMPL-FORM-CHART"], "kind": "code", "scope": ["frontend/src/lib/components/ScoreRing.svelte", "frontend/src/lib/components/Icon.svelte", "frontend/src/routes/+layout.svelte", "frontend/src/routes/today/+page.svelte"], "verify": ["cd frontend && npm install && npm run test:unit && npm run check && npm run build"]} -->
- **[P7-REVIEW-DESIGN-VISION]** 디자인 에이전트(product-architect)로 실데이터 화면을 보고 앱 비전(세상에 없던 최고의 러닝 앱) 부합 여부·UI/UX 재검토, 수정 방안 수립(REVIEW-06). E1~E6 구현 후 진행.
  product-architect 에이전트가 실데이터 스크린샷 10장을 보고 REVIEW-06 작성(화면별 평가·3축 갭·수정 유닛 10개·열린 결정 5건). 핵심 발견 정정: 지표 불일치의 원인은 스냅샷 혼재가 아니라 기준일 불일치(허브=달력 9/25 D-30, 상태·브리핑·Coach=최신 데이터일 9/24 D-31, 폼차트·메트릭 브라우저=백필이 만든 9/25 휴식일 행 TSB 16.2). 수정 실행은 사용자 승인 후 큐 등록.
  <!-- autopilot: {"stage": "done", "mode": "auto", "attempts": 0, "deps": ["P7-IMPL-COACH-EVIDENCE-UI", "P7-IMPL-VISUAL-SYSTEM", "P7-IMPL-LIST-STORY"], "kind": "code", "scope": ["v0.3/data/phase-7-ui-renewal/REVIEW-06-design-agent-review.md"], "verify": ["python3 scripts/check_docs.py"]} -->
- **[P7-IMPL-COACH-EVIDENCE-API]** Coach 답변에 근거(evidence)를 저장·반환하고, Coach 컨텍스트에 레이스 국면·예측을 주입 — 백엔드 전용, `REVIEW-05-vision-gap.md` E6(P1: 모든 AI 결론에 근거), 설계 근거 `DECISIONS.md`의 `[P7-IMPL-COACH-EVIDENCE-API]` 필독. **이 명세의 시그니처·키는 그대로 구현할 것 — 바꾸고 싶으면 `DECISIONS.md`에 사유를 적고 중단.** 현황: Coach 답변(`chat_messages` assistant)에는 본문과 `ai_model`만 있고 근거가 없으며, Coach 컨텍스트에는 목표 레이스 이름·D-day만 있고 예측·폼 예측이 없다. Today 브리핑(`today_service.get_today_briefing`)은 이미 레이스 국면에 맞춘 근거 리스트(`[{"type":"metric","metric","value","label","drill"}]`)를 만든다 — 같은 근거를 Coach 답변에도 붙인다.
  (1) `src/db_setup.py` — `_DDL_APP_TABLES`의 `chat_messages`에 `evidence_json TEXT` 컬럼 추가(`thread_id INTEGER,` 다음 줄). `SCHEMA_VERSION`을 18→19로(주석 `# v0.3.9: chat_messages.evidence_json`), `migrate_db` 안에 v18 블록 다음에 `# v19: chat_messages.evidence_json 추가 (Coach 답변 근거)` 블록 추가: `if current < 19:` 아래 `PRAGMA table_info(chat_messages)` 컬럼 집합을 구해 `existing and "evidence_json" not in existing`이면 `ALTER TABLE chat_messages ADD COLUMN evidence_json TEXT`(v16 블록과 같은 패턴). 파일 상단 docstring의 버전 이력에 v19 줄 추가. `SCHEMA_VERSION`·`user_version`을 18로 하드코딩한 테스트가 있으면(`grep -rn "18" tests/test_db_setup.py tests/test_phase1_schema.py` 및 `SCHEMA_VERSION|user_version` 검색) 19로 갱신하고, `tests/test_db_setup.py`에 "구버전 chat_messages(evidence_json 없음)에서 migrate_db 후 컬럼 생김" 테스트 1개 추가.
  (2) `src/services/coach_service.py` — `import json` 추가. 신규 함수 `def build_evidence(conn: sqlite3.Connection) -> list[dict]:`(docstring: "오늘 브리핑의 근거를 Coach 답변 근거로 재사용 — 실패하면 빈 리스트") = `from src.services.today_service import get_today_briefing`로 `get_today_briefing(conn)["evidence"]`의 앞 5개를 반환, 예외는 `[]`로 삼킨다(Coach 응답 자체는 막지 않음). `create_thread`와 `add_message`가 assistant 메시지를 INSERT할 때 `evidence_json` 컬럼에 `json.dumps(evidence, ensure_ascii=False)`를 함께 저장하고(근거가 빈 리스트면 NULL), 반환하는 `message` dict에 `"evidence": evidence`(리스트, 없으면 `[]`)를 추가한다. `get_thread`의 메시지 SELECT에 `evidence_json`을 추가하고, 반환 시 각 메시지에서 `evidence_json`을 제거하고 `"evidence"`에 `json.loads` 결과(NULL이면 `[]`; user 메시지도 `[]`)를 넣는다(파싱 실패 시 `[]`).
  (3) `src/ai/chat_context_builders.py`의 `_add_race_context` 끝에 `try: from src.services.race_hub_service import get_race_hub; ctx["race_hub"] = get_race_hub(conn, today)` / `except Exception: ctx["race_hub"] = None`을 추가(기존 `ctx["goal"]` 설정은 유지). `src/ai/chat_context_format.py`의 목표 레이스 줄(`### 목표 레이스: …`)을 만드는 블록 바로 뒤에, `ctx.get("race_hub")`가 있고 그 안 `projection`이 있으면 다음 줄들을 `lines`에 추가: `f"- 레이스 아침 예상 폼(TSB): " + ", ".join(f"{s['label']} {s['tsb']:+.0f}" for s in projection["scenarios"])`, `f"- 가정: {projection['assumptions']}"`; `prediction`이 있으면 `f"- 목표 거리 예측 기록: {_fmt_sec(prediction['value_sec'])}" + (f" (목표 대비 {prediction['gap_sec']:+d}초)" if prediction.get("gap_sec") is not None else "")`(`_fmt_sec`은 같은 파일에 이미 있는 헬퍼를 쓴다 — 파일을 읽어 이름 확인).
  (4) 테스트: `tests/test_coach_service.py`(기존 파일 확장 — 먼저 읽고 기존 AI 호출 모킹 방식을 그대로 따른다)에 (a) `create_thread` 응답 `message["evidence"]`가 리스트이고, 활성 목표+TSB 시드가 있으면 첫 항목 `metric == "race_days_left"`; (b) `get_thread`가 assistant 메시지에 `evidence`를 파싱해 돌려주고 user 메시지는 `[]`, `evidence_json` 키는 없음; (c) `build_evidence`가 예외 시 `[]`(get_today_briefing을 monkeypatch로 raise). 신규 `tests/test_chat_context_race.py`: 목표 + `race_pred_marathon_sec` + ctl/atl 시드(`tests/test_race_hub_service.py`의 `_seed_metric`·픽스처 방식 참고)로 컨텍스트를 만들고 포맷한 텍스트에 `레이스 아침 예상 폼`과 `목표 거리 예측 기록`이 들어가며, 목표가 없으면 둘 다 없음.
  리뷰: 워크트리 diff를 명세와 줄 단위 대조 — `evidence_json` 컬럼(DDL·v19 마이그레이션·SCHEMA_VERSION 19·docstring), `build_evidence`(브리핑 근거 앞 5개, 예외 시 []), create_thread/add_message 저장·반환, get_thread의 `evidence` 파싱(evidence_json 키 제거), 컨텍스트 `race_hub` 주입·포맷(예상 폼·가정·목표 거리 예측 기록) 모두 명세와 일치(이탈 없음). 대상 4개 테스트 파일 통과. 병합 후 전체 pytest·check_docs·check_data_consistency 확인.
  <!-- autopilot: {"stage": "done", "mode": "auto", "attempts": 1, "deps": ["P7-IMPL-RACE-HUB-API"], "kind": "code", "scope": ["src/db_setup.py", "src/services/coach_service.py", "src/ai/chat_context_builders.py", "src/ai/chat_context_format.py", "tests/test_coach_service.py", "tests/test_db_setup.py", "tests/test_chat_context_race.py"], "verify": ["python3 -m pytest tests/test_coach_service.py tests/test_db_setup.py tests/test_chat_context_race.py tests/test_ai_context.py -q", "python3 scripts/check_data_consistency.py"]} -->
- **[P7-IMPL-COACH-EVIDENCE-UI]** Coach 스레드 화면에 근거 칩 표시 + 입력창 도킹 — 프론트 전용. 앞 유닛 `P7-IMPL-COACH-EVIDENCE-API`가 메시지에 `evidence: BriefingEvidence[]`를 준다(Today 브리핑 근거와 같은 형태: `{type:'metric', metric, value, label, drill: {scope_type, scope_id} | null}`). 구현 전에 `frontend/src/routes/coach/[threadId]/+page.svelte`와 `frontend/src/routes/today/+page.svelte`의 근거 칩 처리(`adaptEvidence`, `EvidenceQuote`, `MetricBreakdown` 열기)를 먼저 읽고 같은 방식을 재사용한다. (1) `frontend/src/lib/types/index.ts`의 Coach 메시지 타입(assistant/user 공통 `ThreadMessage` 또는 유사 이름)에 `evidence?: BriefingEvidence[]` 추가. (2) 스레드 페이지의 assistant 메시지 말풍선 바로 아래에 `evidence`가 1개 이상이면 `<div class="mt-2 flex flex-wrap gap-2">` 안에 `EvidenceQuote`(Today와 동일하게 `adaptEvidence(ev, openEvidence)`로 변환)를 나열하고, drill이 있는 칩을 누르면 Today와 같은 `MetricBreakdown` 바텀시트가 열리게 한다(닫기 포함). 새 메시지를 보낸 직후 응답 메시지의 `evidence`도 같은 방식으로 표시. (3) 입력창(composer)을 하단 탭바 바로 위에 고정: 입력 영역 컨테이너에 `sticky bottom-14 z-10 border-t border-border-subtle bg-surface-1 px-4 py-3`(탭바 높이 3.5rem 기준 — 하단 탭바가 `fixed`이므로 겹치지 않게), 메시지 목록 하단 패딩을 늘려 마지막 메시지가 입력창에 가리지 않게 하고, 메시지 추가/응답 도착 시 목록 끝으로 스크롤한다(`scrollIntoView({ block: 'end' })`, 사용자가 위로 올려 읽는 중이라는 판단은 하지 않는다 — 단순 구현).
  Coach 답변 아래 근거 칩(EvidenceQuote+adaptEvidence) + MetricBreakdown 드릴다운 스택 + 입력창 sticky bottom-14 도킹 + 스크롤 end 정렬. 워크트리 diff를 스펙과 대조해 이탈 없음 확인, test:unit 129/check 0 errors/build 통과. 실데이터 사본 브라우저 검증은 병합 후 수행.
  <!-- autopilot: {"stage": "done", "mode": "auto", "attempts": 1, "deps": ["P7-IMPL-COACH-EVIDENCE-API"], "kind": "code", "scope": ["frontend/src/lib/types/index.ts", "frontend/src/routes/coach/[threadId]/+page.svelte"], "verify": ["cd frontend && npm install && npm run test:unit && npm run check && npm run build"]} -->
- **[P7-FIX-ASOF-LOCALTIME]** 기준일을 서버 로컬 달력 오늘로 통일하고 오늘 PMC를 현 시각 기준(하루 전체 휴식 가정 금지)으로 계산 — 백엔드 전용. `v0.3/data/phase-7-ui-renewal/specs/REVIEW06-UNITS.md`의 '결정'·'유닛 1' 섹션이 유일한 명세이며 코드(diff·신규 파일 전문·테스트)를 그대로 구현한다. 근거: `REVIEW-06-design-agent-review.md` 4-A(화면마다 오늘 기준이 달라 TSB/UTRS/D-day 불일치). main에서 하지 않고 autopilot에서만 진행(사용자 지시).
  명세 코드·시그니처 그대로 구현(diff 대조 이탈 없음). 서비스 4파일 date('now','localtime') 치환 잔여 0, PMC 오늘 부분일 감쇠(elapsed_day_fraction), 오늘 행 30분 지연 갱신(before_request), 테스트 추가. main 전체 pytest·check_docs 통과 확인은 병합 후.
  <!-- autopilot: {"stage": "done", "mode": "auto", "attempts": 1, "deps": [], "kind": "code", "scope": ["src/services/today_service.py", "src/services/dashboard_service.py", "src/services/wellness_service.py", "src/services/activity_service.py", "src/ai/chat_context_checkin.py", "src/metrics/pmc.py", "src/metrics/today_refresh.py", "src/api/__init__.py", "tests/test_pmc_intraday.py", "tests/test_api_today.py", "v0.3/data/files_index.md"], "verify": ["python3 -m pytest tests/test_pmc_intraday.py tests/test_pmc.py tests/test_api_today.py tests/test_today_service.py tests/test_dashboard_service.py -q", "python3 scripts/check_docs.py"]} -->
- **[P7-IMPL-TODAY-ACTION-FIRST]** Today 첫 화면에 오늘 할 일 문장이 보이도록 RaceHub 차트를 접고 기준 시점 라벨 표기 — 프론트 전용. `v0.3/data/phase-7-ui-renewal/specs/REVIEW06-UNITS.md`의 '유닛 2' 섹션이 유일한 명세(코드·문구 그대로). 근거 REVIEW-06 §5-3.
  명세 코드 그대로 구현(diff 대조 이탈 없음): asOf.ts+테스트, RaceHub 차트 <details> 접힘, Today L1 기준 시점 라벨. test:unit/check/build 통과.
  <!-- autopilot: {"stage": "done", "mode": "auto", "attempts": 1, "deps": ["P7-FIX-ASOF-LOCALTIME"], "kind": "code", "scope": ["frontend/src/lib/asOf.ts", "frontend/tests/asOf.test.mjs", "frontend/src/lib/components/RaceHub.svelte", "frontend/src/routes/today/+page.svelte"], "verify": ["cd frontend && npm install && npm run test:unit && npm run check && npm run build"]} -->
- **[P7-IMPL-PLAN-EMPTY-TO-ACTION]** 목표 레이스는 있는데 플랜이 없을 때 Today·Plan 화면에 '로드맵 만들기' 원탭 CTA를 두고 /coach/plan/new를 목표 데이터로 프리필 — 프론트 전용. `v0.3/data/phase-7-ui-renewal/specs/REVIEW06-UNITS.md`의 '유닛 3' 섹션이 유일한 명세(코드·문구 그대로). 근거 REVIEW-06 §5-4.
  명세 코드 그대로 구현(diff 대조 이탈 없음, import 끝 쉼표 서식만 상이): planPrefill+테스트, NextSessionCard CTA, Plan 게이트웨이 CTA, /coach/plan/new 프리필. 직접 diff 리뷰 + test:unit 140/check 0 errors 확인 후 병합. 브라우저 확인은 병합 후.
  <!-- autopilot: {"stage": "done", "mode": "auto", "attempts": 1, "deps": ["P7-IMPL-TODAY-ACTION-FIRST"], "kind": "code", "scope": ["frontend/src/lib/planPrefill.ts", "frontend/tests/planPrefill.test.mjs", "frontend/src/lib/components/NextSessionCard.svelte", "frontend/src/routes/today/+page.svelte", "frontend/src/routes/coach/plan/+page.ts", "frontend/src/routes/coach/plan/+page.svelte", "frontend/src/routes/coach/plan/new/+page.svelte"], "verify": ["cd frontend && npm install && npm run test:unit && npm run check && npm run build"]} -->
- **[P7-IMPL-METRICS-MEANING]** 메트릭 브라우저에 의미(해석 밴드)를 붙이고 내부 식별자·중복 배지·평평한 스파크라인 제거 — 유닛 A. 프론트 전용. `v0.3/data/phase-7-ui-renewal/specs/REVIEW06-UNITS-2.md`의 해당 유닛 섹션이 유일한 명세이며 코드·문구·클래스를 그대로 구현한다(REVIEW-06 근거).
  명세 코드 그대로 구현(순수 모듈 3개는 명세 코드 블록과 공백 정규화 diff 0줄, 페이지 변경도 줄 단위 대조 이탈 없음). test:unit 174/check 0 errors/build 통과. 6개 유닛(METRICS-MEANING·ACTIVITY-MEANING·COACH-FOLLOWUP·PROVIDER-HINTS·ARCHIVE-EXPLORE·DESKTOP-LAYOUT)을 한 브랜치로 일괄 병합. 실 계정 브라우저 검증은 병합 후.
  <!-- autopilot: {"stage": "done", "mode": "auto", "attempts": 1, "deps": [], "kind": "code", "scope": ["frontend/src/lib/metricMeaning.ts", "frontend/tests/metricMeaning.test.mjs", "frontend/src/lib/types/index.ts", "frontend/src/lib/components/MetricCell.svelte", "frontend/src/routes/library/metrics/+page.svelte"], "verify": ["cd frontend && npm install && npm run test:unit && npm run check && npm run build"]} -->
- **[P7-IMPL-ACTIVITY-MEANING]** 활동 상세 핵심 메트릭 해석 라벨 + 스플릿 바 범례 — 유닛 B. 프론트 전용. `v0.3/data/phase-7-ui-renewal/specs/REVIEW06-UNITS-2.md`의 해당 유닛 섹션이 유일한 명세이며 코드·문구·클래스를 그대로 구현한다(REVIEW-06 근거).
  리뷰: 명세 코드 그대로 구현(줄 단위 대조 이탈 없음), METRICS-MEANING 노트와 함께 일괄 병합.
  <!-- autopilot: {"stage": "done", "mode": "auto", "attempts": 1, "deps": [], "kind": "code", "scope": ["frontend/src/routes/library/[id]/+page.svelte", "frontend/src/lib/components/SplitBars.svelte"], "verify": ["cd frontend && npm install && npm run test:unit && npm run check && npm run build"]} -->
- **[P7-IMPL-COACH-FOLLOWUP]** Coach 후속 질문 칩·레이스 맥락 주제·출처 표기 강화 — 유닛 C. 프론트 전용. `v0.3/data/phase-7-ui-renewal/specs/REVIEW06-UNITS-2.md`의 해당 유닛 섹션이 유일한 명세이며 코드·문구·클래스를 그대로 구현한다(REVIEW-06 근거).
  리뷰: 명세 코드 그대로 구현(줄 단위 대조 이탈 없음), METRICS-MEANING 노트와 함께 일괄 병합.
  <!-- autopilot: {"stage": "done", "mode": "auto", "attempts": 1, "deps": [], "kind": "code", "scope": ["frontend/src/lib/coachSuggestions.ts", "frontend/tests/coachSuggestions.test.mjs", "frontend/src/routes/coach/+page.ts", "frontend/src/routes/coach/+page.svelte", "frontend/src/routes/coach/[threadId]/+page.svelte"], "verify": ["cd frontend && npm install && npm run test:unit && npm run check && npm run build"]} -->
- **[P7-IMPL-PROVIDER-HINTS]** Provider 현황 조치 문구 + 활동 목록 단일 소스 배지 숨김 — 유닛 D. 프론트 전용. `v0.3/data/phase-7-ui-renewal/specs/REVIEW06-UNITS-2.md`의 해당 유닛 섹션이 유일한 명세이며 코드·문구·클래스를 그대로 구현한다(REVIEW-06 근거).
  리뷰: 명세 코드 그대로 구현(줄 단위 대조 이탈 없음), METRICS-MEANING 노트와 함께 일괄 병합.
  <!-- autopilot: {"stage": "done", "mode": "auto", "attempts": 1, "deps": [], "kind": "code", "scope": ["frontend/src/lib/providerHint.ts", "frontend/tests/providerHint.test.mjs", "frontend/src/routes/library/+page.svelte", "frontend/src/routes/library/activities/+page.svelte"], "verify": ["cd frontend && npm install && npm run test:unit && npm run check && npm run build"]} -->
- **[P7-IMPL-ARCHIVE-EXPLORE]** 아카이브 월 막대에서 그 달 활동 목록으로 이동 + 기간 필터 — 유닛 E. 프론트 전용. `v0.3/data/phase-7-ui-renewal/specs/REVIEW06-UNITS-2.md`의 해당 유닛 섹션이 유일한 명세이며 코드·문구·클래스를 그대로 구현한다(REVIEW-06 근거).
  리뷰: 명세 코드 그대로 구현(줄 단위 대조 이탈 없음), METRICS-MEANING 노트와 함께 일괄 병합.
  <!-- autopilot: {"stage": "done", "mode": "auto", "attempts": 1, "deps": [], "kind": "code", "scope": ["frontend/src/lib/archive.ts", "frontend/tests/archive.test.mjs", "frontend/src/lib/components/ArchiveHero.svelte", "frontend/src/routes/library/activities/+page.ts", "frontend/src/routes/library/activities/+page.svelte"], "verify": ["cd frontend && npm install && npm run test:unit && npm run check && npm run build"]} -->
- **[P7-IMPL-DESKTOP-LAYOUT]** 데스크톱(≥1024px) Today 2열 배치 — 유닛 F(DECISIONS [P7-IMPL-VISUAL-SYSTEM]의 미이행 결정 실현). 프론트 전용. `v0.3/data/phase-7-ui-renewal/specs/REVIEW06-UNITS-2.md`의 해당 유닛 섹션이 유일한 명세이며 코드·문구·클래스를 그대로 구현한다(REVIEW-06 근거).
  리뷰: 명세 코드 그대로 구현(줄 단위 대조 이탈 없음), METRICS-MEANING 노트와 함께 일괄 병합.
  <!-- autopilot: {"stage": "done", "mode": "auto", "attempts": 1, "deps": [], "kind": "code", "scope": ["frontend/src/routes/+layout.svelte", "frontend/src/routes/today/+page.svelte"], "verify": ["cd frontend && npm install && npm run test:unit && npm run check && npm run build"]} -->
- **[P7-IMPL-TODAY-RECENT-THUMBS]** Today 최근 활동에 경로 썸네일 — 유닛 J. `v0.3/data/phase-7-ui-renewal/specs/REVIEW06-UNITS-3.md`의 해당 유닛 섹션이 유일한 명세이며 코드·문구를 그대로 구현한다(REVIEW-06 근거).
  명세 코드 그대로 구현(순수 모듈 2개 명세 블록과 diff 0줄, 페이지·서비스 변경 줄 단위 대조 이탈 없음). test:unit 183/check 0 errors/build/관련 pytest 74 통과. 5개 유닛(TODAY-RECENT-THUMBS·COACH-THREAD-STALE·ACTIVITY-IMPACT-API/UI·DESKTOP-SIDENAV) 일괄 병합. 발견: 명세 결함 — impact.race가 과거 활동에도 '오늘' 기준 D-day를 붙임(병합 후 main에서 교정).
  <!-- autopilot: {"stage": "done", "mode": "auto", "attempts": 1, "deps": [], "kind": "code", "scope": ["src/services/today_service.py", "tests/test_today_service.py", "frontend/src/lib/types/index.ts", "frontend/src/routes/today/+page.svelte"], "verify": ["python3 -m pytest tests/test_today_service.py -q", "cd frontend && npm install && npm run test:unit && npm run check && npm run build"]} -->
- **[P7-IMPL-COACH-THREAD-STALE]** Coach 낡은 스레드에 '당시 기준' 표기 — 프론트 전용, 유닛 L. `v0.3/data/phase-7-ui-renewal/specs/REVIEW06-UNITS-3.md`의 해당 유닛 섹션이 유일한 명세이며 코드·문구를 그대로 구현한다(REVIEW-06 근거).
  리뷰: 명세 코드 그대로 구현(줄 단위 대조 이탈 없음), TODAY-RECENT-THUMBS 노트와 함께 일괄 병합.
  <!-- autopilot: {"stage": "done", "mode": "auto", "attempts": 1, "deps": [], "kind": "code", "scope": ["frontend/src/lib/threadAge.ts", "frontend/tests/threadAge.test.mjs", "frontend/src/routes/coach/+page.svelte"], "verify": ["cd frontend && npm install && npm run test:unit && npm run check && npm run build"]} -->
- **[P7-IMPL-ACTIVITY-IMPACT-API]** 활동 상세에 impact(CTL Δ·유사 활동 비교·레이스 맥락) 추가 — 백엔드 전용, 유닛 H1. `v0.3/data/phase-7-ui-renewal/specs/REVIEW06-UNITS-3.md`의 해당 유닛 섹션이 유일한 명세이며 코드·문구를 그대로 구현한다(REVIEW-06 근거).
  리뷰: 명세 코드 그대로 구현(줄 단위 대조 이탈 없음), TODAY-RECENT-THUMBS 노트와 함께 일괄 병합.
  <!-- autopilot: {"stage": "done", "mode": "auto", "attempts": 1, "deps": [], "kind": "code", "scope": ["src/services/activity_impact_service.py", "src/services/activity_service.py", "tests/test_activity_impact_service.py", "v0.3/data/files_index.md"], "verify": ["python3 -m pytest tests/test_activity_impact_service.py tests/test_activity_service.py -q", "python3 scripts/check_docs.py", "python3 scripts/check_data_consistency.py"]} -->
- **[P7-IMPL-ACTIVITY-IMPACT-UI]** 활동 상세 '이 러닝의 의미' 블록 — 프론트 전용, 유닛 H2. `v0.3/data/phase-7-ui-renewal/specs/REVIEW06-UNITS-3.md`의 해당 유닛 섹션이 유일한 명세이며 코드·문구를 그대로 구현한다(REVIEW-06 근거).
  리뷰: 명세 코드 그대로 구현(줄 단위 대조 이탈 없음), TODAY-RECENT-THUMBS 노트와 함께 일괄 병합.
  <!-- autopilot: {"stage": "done", "mode": "auto", "attempts": 1, "deps": [], "kind": "code", "scope": ["frontend/src/lib/types/index.ts", "frontend/src/lib/activityImpact.ts", "frontend/tests/activityImpact.test.mjs", "frontend/src/routes/library/[id]/+page.svelte"], "verify": ["cd frontend && npm install && npm run test:unit && npm run check && npm run build"]} -->
- **[P7-IMPL-DESKTOP-SIDENAV]** 데스크톱(≥1024px)에서 하단 탭바를 좌측 고정 내비로 전환(사용자 승인) — 프론트 전용. `v0.3/data/phase-7-ui-renewal/specs/REVIEW06-UNITS-3.md`의 유닛 K 섹션이 유일한 명세이며 코드·클래스를 그대로 구현한다.
  리뷰: 명세 코드 그대로 구현(줄 단위 대조 이탈 없음), TODAY-RECENT-THUMBS 노트와 함께 일괄 병합.
  <!-- autopilot: {"stage": "done", "mode": "auto", "attempts": 1, "deps": [], "kind": "code", "scope": ["frontend/src/routes/+layout.svelte", "frontend/src/routes/coach/[threadId]/+page.svelte"], "verify": ["cd frontend && npm install && npm run test:unit && npm run check && npm run build"]} -->
- **[P7-IMPL-ACTIVITY-FLAGS]** 활동 목록 행 배지를 폐기하고 예외(이상치·심박/경로 없음)만 표시 — 프론트 전용, 유닛 M(사용자 승인). `v0.3/data/phase-7-ui-renewal/specs/REVIEW06-UNITS-3.md`의 '소스 배지 재설계' 절 해당 유닛이 유일한 명세이며 코드·문구를 그대로 구현한다.
  명세 코드 그대로 구현(순수 모듈 2개·서비스 함수 명세 블록과 diff 0줄, 페이지·라우트 변경 줄 단위 대조 이탈 없음). test:unit 200/check 0 errors/build/관련 pytest 34 통과. 3개 유닛(ACTIVITY-FLAGS·SOURCE-COVERAGE-API·SOURCE-COVERAGE-UI) 일괄 병합.
  <!-- autopilot: {"stage": "done", "mode": "auto", "attempts": 1, "deps": [], "kind": "code", "scope": ["frontend/src/lib/activityFlags.ts", "frontend/tests/activityFlags.test.mjs", "frontend/src/routes/library/activities/+page.svelte"], "verify": ["cd frontend && npm install && npm run test:unit && npm run check && npm run build"]} -->
- **[P7-IMPL-SOURCE-COVERAGE-API]** 소스별 월 단위 활동 커버리지 API — 백엔드 전용, 유닛 N1. `v0.3/data/phase-7-ui-renewal/specs/REVIEW06-UNITS-3.md`의 '소스 배지 재설계' 절 해당 유닛이 유일한 명세이며 코드·문구를 그대로 구현한다.
  리뷰: 명세 코드 그대로 구현(줄 단위 대조 이탈 없음), ACTIVITY-FLAGS 노트와 함께 일괄 병합.
  <!-- autopilot: {"stage": "done", "mode": "auto", "attempts": 1, "deps": [], "kind": "code", "scope": ["src/services/provider_status_service.py", "src/api/routes_library.py", "tests/test_provider_status_service.py", "tests/test_api_library.py", "v0.3/data/files_index.md"], "verify": ["python3 -m pytest tests/test_provider_status_service.py tests/test_api_library.py -q", "python3 scripts/check_docs.py"]} -->
- **[P7-IMPL-SOURCE-COVERAGE-UI]** Library 홈 소스 커버리지 타임라인(Provider 현황 대체) — 프론트 전용, 유닛 N2. `v0.3/data/phase-7-ui-renewal/specs/REVIEW06-UNITS-3.md`의 '소스 배지 재설계' 절 해당 유닛이 유일한 명세이며 코드·문구를 그대로 구현한다.
  리뷰: 명세 코드 그대로 구현(줄 단위 대조 이탈 없음), ACTIVITY-FLAGS 노트와 함께 일괄 병합.
  <!-- autopilot: {"stage": "done", "mode": "auto", "attempts": 1, "deps": [], "kind": "code", "scope": ["frontend/src/lib/coverage.ts", "frontend/tests/coverage.test.mjs", "frontend/src/lib/api/providers.ts", "frontend/src/lib/types/index.ts", "frontend/src/lib/components/SourceCoverage.svelte", "frontend/src/routes/library/+page.ts", "frontend/src/routes/library/+page.svelte"], "verify": ["cd frontend && npm install && npm run test:unit && npm run check && npm run build"]} -->
- **[P7-IMPL-MERGED-SOURCES]** 활동 목록에 병합 소스 수 표시(통합의 가시화) — 유닛 I. 그룹 개념이 명세와 다르면 DECISIONS에 적고 중단. `v0.3/data/phase-7-ui-renewal/specs/REVIEW06-UNITS-3.md`의 해당 유닛 섹션이 유일한 명세이며 코드·문구를 그대로 구현한다(REVIEW-06 근거).
  <!-- autopilot: {"stage": "queued", "mode": "manual", "attempts": 0, "deps": [], "kind": "code", "scope": ["src/services/activity_service.py", "tests/test_activity_service.py", "frontend/src/lib/types/index.ts", "frontend/src/routes/library/activities/+page.svelte"], "verify": ["python3 -m pytest tests/test_activity_service.py -q", "cd frontend && npm install && npm run test:unit && npm run check && npm run build"]} -->
- **[P7-FIX-CHAT-WORKOUT-TYPE]** 앱 AI 코치 컨텍스트가 `workout_type_classified`를 `numeric_value`에서 읽어 항상 비는 버그 수정(BUG-WORKOUT-TYPE-COLUMN). 실제 저장은 `text_value`다. 명세: (1) `src/ai/chat_context_builders.py` 두 곳 — `SELECT numeric_value, json_value FROM metric_store WHERE metric_name='workout_type_classified' ...`(약 93행)는 `SELECT text_value, json_value ...`로, 같은 조건의 `SELECT numeric_value FROM metric_store`(약 274행)는 `SELECT text_value`로 바꾼다(이후 `cls[0]` 사용은 그대로). (2) `src/ai/chat_context_rich.py`의 `workout_type_classified` JOIN을 쓰는 세 쿼리에서 `c.numeric_value`를 `c.text_value`로 바꾼다: 레이스 목록 WHERE의 `c.numeric_value='race'`, 오늘 분류 SELECT의 `c.numeric_value`, 유사 활동 WHERE의 `c.numeric_value=?`. 다른 로직은 바꾸지 않는다. (3) 테스트 `tests/test_chat_context_workout_type.py` 신규(모듈 docstring 첫 줄 필수): `tests/test_chat_context_race.py`의 DB 픽스처·시드 헬퍼 패턴을 따라 (a) `text_value='race'`(numeric_value NULL)인 러닝 활동이 이름에 '레이스/대회/Race'가 없어도 race_history에 나오고, (b) 오늘 활동의 분류가 today_detail 또는 similar_activities의 type으로 채워지며 같은 분류의 과거 활동이 similar_activities.history에 들어오고, (c) 분류 행이 없으면 키가 생기지 않는지 검증. 실행 후 `python3 scripts/gen_files_index.py`로 인덱스를 갱신한다.
  리뷰: 명세 diff 대조 이탈 없음(text_value 5곳·_RUNNING_TYPES·도구 3줄 그대로). 워크트리 관련 pytest 90건·check_docs 통과. 참고: 회귀 테스트 `test_race_not_included_when_only_numeric_value`는 numeric_value를 실제로 시드하지 않아 약함(동작 검증은 다른 케이스가 담당). 세 유닛 일괄 병합.
  <!-- autopilot: {"stage": "done", "mode": "auto", "attempts": 1, "deps": [], "kind": "code", "scope": ["src/ai/chat_context_builders.py", "src/ai/chat_context_rich.py", "tests/test_chat_context_workout_type.py", "v0.3/data/files_index.md"], "verify": ["python3 -m pytest tests/test_chat_context_workout_type.py tests/test_chat_context_race.py tests/test_chat_context_intents.py tests/test_chat_context_checkin.py -q", "python3 scripts/check_docs.py", "python3 scripts/check_data_consistency.py"]} -->
- **[P7-FIX-INDOOR-RUN-TYPE]** Garmin `indoor_running`이 러닝으로 정규화되지 않아 러닝 집계에서 빠지는 문제의 코드 수정(BUG-INDOOR-RUN-TYPE). `src/utils/activity_types.py`의 `_RUNNING_TYPES` 집합에 `"indoor_running"`을 추가한다(다른 매핑은 변경 금지; `treadmill`도 이미 이 집합을 통해 `running`이 되므로 같은 값). 테스트 `tests/test_activity_types.py`에 추가: `normalize_activity_type("indoor_running","garmin")=="running"`, 대소문자·공백 변형(`" Indoor_Running "`)도 `running`, 기존 케이스 불변. 기존 DB의 `activity_type='indoor_running'` 16건 정정과 메트릭 재계산은 이 유닛 범위 밖(실DB 작업은 사용자 지시 시 별도).
  리뷰: 명세 대조 이탈 없음, 관련 테스트 통과. P7-FIX-CHAT-WORKOUT-TYPE와 일괄 병합.
  <!-- autopilot: {"stage": "done", "mode": "auto", "attempts": 1, "deps": [], "kind": "code", "scope": ["src/utils/activity_types.py", "tests/test_activity_types.py"], "verify": ["python3 -m pytest tests/test_activity_types.py tests/test_garmin_extractor.py -q", "python3 scripts/check_docs.py", "python3 scripts/check_data_consistency.py"]} -->
- **[P7-FIX-CHAT-TOOL-PROMPT]** 앱 AI 코치 도구 호출 프롬프트에 누락된 도구 3개 추가(AI-CHAT-TOOL-PROMPT). `src/ai/chat_engine_providers.py`의 `_TOOL_SYSTEM_TEXT` '반드시 도구를 호출해야 하는 경우' 목록에 다음 세 줄을 기존 줄과 같은 형식으로 추가한다: `- 훈련 기간·블록·대회 이후 요약 → get_training_summary (기간 질문의 첫 호출)`, `- 인터벌·크루즈 세트별 랩 데이터 → get_activity_laps (activity_id는 정수)`, `- 세션 간 세트 페이스 비교 → compare_workout_sets`. 다른 문구는 바꾸지 않는다. 테스트 `tests/test_ai_tool_guide.py`에 추가: `TOOL_DECLARATIONS`의 모든 도구 이름이 `_TOOL_SYSTEM_TEXT`에 포함되는지 검증(`from src.ai.chat_engine_providers import _TOOL_SYSTEM_TEXT`). 이 검증이 실패하면 누락된 도구 줄을 추가해 통과시킨다. USAGE_GUIDE와의 SSOT 통합은 이 유닛 범위 밖.
  리뷰: 명세 대조 이탈 없음, 관련 테스트 통과. P7-FIX-CHAT-WORKOUT-TYPE와 일괄 병합.
  <!-- autopilot: {"stage": "done", "mode": "auto", "attempts": 1, "deps": [], "kind": "code", "scope": ["src/ai/chat_engine_providers.py", "tests/test_ai_tool_guide.py"], "verify": ["python3 -m pytest tests/test_ai_tool_guide.py tests/test_chat_engine_threads.py -q", "python3 scripts/check_docs.py", "python3 scripts/check_data_consistency.py"]} -->
- **[P7-PRED-11]** 스키마 v20 — `v0.3/data/phase-7-ui-renewal/specs/PRED-1x-*.md`의 P7-PRED-11 절이 유일한 명세(코드·diff 그대로). 근거 REVIEW-07/08 r3.
  리뷰: 명세 블록 대조(신규 파일 공백 정규화 diff, 수정 파일 +/- 줄 비교) — 11 이탈 1건(test_pred_schema_v20의 버전 하드코딩 `== 20`, 명세는 SCHEMA_VERSION 비교: main에서 명세대로 교정), 12·13·14·84·81(+82) 이탈 없음. 13은 예산 초과 종료건(커밋은 완성)이라 수동 review 전환. 6유닛 일괄 병합.
  <!-- autopilot: {"stage": "done", "mode": "auto", "attempts": 1, "deps": [], "kind": "code", "scope": ["src/db_schema_v20.py", "src/db_setup.py", "src/utils/db_helpers.py", "tests/helpers_pred.py", "tests/test_pred_schema_v20.py", "tests/test_db_setup.py", "tests/test_phase1_schema.py", "v0.3/data/files_index.md"], "verify": ["python3 -m pytest tests/test_pred_schema_v20.py tests/test_db_setup.py tests/test_phase1_schema.py -q", "python3 scripts/check_docs.py", "python3 scripts/check_data_consistency.py"]} -->
- **[P7-PRED-12]** Garmin 추출 보존(랩·스트림·활동 GAP) — `v0.3/data/phase-7-ui-renewal/specs/PRED-1x-*.md`의 P7-PRED-12 절이 유일한 명세(코드·diff 그대로). 근거 REVIEW-07/08 r3.
  리뷰: 명세 블록 대조 이탈 없음. P7-PRED-11과 6유닛 일괄 병합.
  <!-- autopilot: {"stage": "done", "mode": "auto", "attempts": 1, "deps": [], "kind": "code", "scope": ["src/sync/extractors/garmin_lap_fields.py", "src/sync/extractors/garmin_extractor.py", "tests/test_garmin_lap_fields.py", "v0.3/data/files_index.md"], "verify": ["python3 -m pytest tests/test_garmin_lap_fields.py tests/test_garmin_extractor.py -q", "python3 scripts/check_docs.py", "python3 scripts/check_data_consistency.py"]} -->
- **[P7-PRED-13]** 제자리 재추출 + reprocess 파손 수정 — `v0.3/data/phase-7-ui-renewal/specs/PRED-1x-*.md`의 P7-PRED-13 절이 유일한 명세(코드·diff 그대로). 근거 REVIEW-07/08 r3.
  실행 노트: 러너가 예산 상한($2.5, error_max_budget_usd)에 걸려 stage를 queued로 되돌렸으나 커밋(16f3c31)은 완성 상태 — 명세 대조(신규 2파일 공백 정규화 diff 0, reprocess 결과 동일)·관련 pytest 16건·check_docs 통과 확인 후 수동으로 review 처리.
  리뷰: 명세 블록 대조 이탈 없음. P7-PRED-11과 6유닛 일괄 병합.
  <!-- autopilot: {"stage": "done", "mode": "auto", "attempts": 1, "deps": [], "kind": "code", "scope": ["src/sync/reextract.py", "src/sync/reprocess.py", "tests/test_reextract.py", "v0.3/data/files_index.md"], "verify": ["python3 -m pytest tests/test_reextract.py tests/test_reprocess.py -q", "python3 scripts/check_docs.py", "python3 scripts/check_data_consistency.py"]} -->
- **[P7-PRED-14]** CalcContext 러닝 이력 API — `v0.3/data/phase-7-ui-renewal/specs/PRED-1x-*.md`의 P7-PRED-14 절이 유일한 명세(코드·diff 그대로). 근거 REVIEW-07/08 r3.
  리뷰: 명세 블록 대조 이탈 없음. P7-PRED-11과 6유닛 일괄 병합.
  <!-- autopilot: {"stage": "done", "mode": "auto", "attempts": 1, "deps": [], "kind": "code", "scope": ["src/metrics/context_runs.py", "src/metrics/base.py", "tests/test_context_runs.py", "v0.3/data/files_index.md"], "verify": ["python3 -m pytest tests/test_context_runs.py tests/test_activity_calcs.py tests/test_sapi.py -q", "python3 scripts/check_docs.py", "python3 scripts/check_data_consistency.py"]} -->
- **[P7-PRED-84]** runpulse_vdot 상한 가드 — `v0.3/data/phase-7-ui-renewal/specs/PRED-8x-*.md`의 P7-PRED-84 절이 유일한 명세(코드·diff 그대로). 근거 REVIEW-07/08 r3.
  리뷰: 명세 블록 대조 이탈 없음. P7-PRED-11과 6유닛 일괄 병합.
  <!-- autopilot: {"stage": "done", "mode": "auto", "attempts": 1, "deps": [], "kind": "code", "scope": ["src/metrics/vdot.py", "tests/test_vdot_guard.py", "v0.3/data/files_index.md"], "verify": ["python3 -m pytest tests/test_vdot_guard.py tests/test_activity_calcs.py -q", "python3 scripts/check_docs.py", "python3 scripts/check_data_consistency.py"]} -->
- **[P7-PRED-81]** 시리즈 canonical 집계 + rec 백분위(P7-PRED-82 포함) — `v0.3/data/phase-7-ui-renewal/specs/PRED-8x-*.md`의 P7-PRED-81 절이 유일한 명세(코드·diff 그대로). 근거 REVIEW-07/08 r3.
  리뷰: 명세 블록 대조 이탈 없음. P7-PRED-11과 6유닛 일괄 병합.
  <!-- autopilot: {"stage": "done", "mode": "auto", "attempts": 1, "deps": [], "kind": "code", "scope": ["src/metrics/teroi.py", "src/metrics/rec.py", "src/metrics/tpdi.py", "src/metrics/critical_power.py", "tests/test_rec.py"], "verify": ["python3 -m pytest tests/test_rec.py tests/test_teroi.py tests/test_tpdi.py tests/test_critical_power.py -q", "python3 scripts/check_docs.py", "python3 scripts/check_data_consistency.py"]} -->

- **[P7-PRED-87]** recompute-all 전 기간 기본·삭제 범위 = 재계산 범위 — `v0.3/data/phase-7-ui-renewal/specs/PRED-8x-*.md`의 P7-PRED-87 절이 유일한 명세(코드·diff 그대로). 근거 REVIEW-07 §R4·REVIEW-08 §R4·REVIEW-09.
  리뷰(클라우드 세션): 명세 블록 대조 이탈 없음. verify 3종 통과.
  리뷰(2026-09-26): 명세 블록 대조 이탈 없음(신규 파일 공백 정규화 diff 0, 수정 파일 +/- 줄 비교). 풀 pytest 1928 통과·check_docs·check_data_consistency 통과.
  <!-- autopilot: {"stage": "done", "mode": "auto", "attempts": 1, "deps": [], "kind": "code", "scope": ["src/metrics/engine.py", "src/metrics/cli.py", "tests/test_recompute_all_range.py", "tests/test_phase4_dod.py", "v0.3/data/files_index.md"], "verify": ["python3 -m pytest tests/test_recompute_all_range.py tests/test_phase4_dod.py tests/test_engine.py -q", "python3 scripts/check_docs.py", "python3 scripts/check_data_consistency.py"]} -->
- **[P7-PRED-20]** Daniels 공식·세트 등가 지속시간 + 칼만(순수) — `v0.3/data/phase-7-ui-renewal/specs/PRED-2x-*.md`의 P7-PRED-20 절이 유일한 명세(코드·diff 그대로). 근거 REVIEW-07 §R4·REVIEW-08 §R4·REVIEW-09.
  리뷰(클라우드 세션): 명세 전문 그대로. __init__.py는 P7-PRED-22 전문과 동일 내용으로 선생성. verify 3종 통과.
  리뷰(2026-09-26): 명세 블록 대조 이탈 없음(신규 파일 공백 정규화 diff 0, 수정 파일 +/- 줄 비교). 풀 pytest 1928 통과·check_docs·check_data_consistency 통과.
  <!-- autopilot: {"stage": "done", "mode": "auto", "attempts": 1, "deps": [], "kind": "code", "scope": ["src/metrics/prediction/__init__.py", "src/metrics/prediction/daniels.py", "src/metrics/prediction/kalman.py", "tests/test_daniels_kalman.py", "v0.3/data/files_index.md"], "verify": ["python3 -m pytest tests/test_daniels_kalman.py -q", "python3 scripts/check_docs.py", "python3 scripts/check_data_consistency.py"]} -->
- **[P7-PRED-21]** 세그먼트 분해 r4(세트 구조) — `v0.3/data/phase-7-ui-renewal/specs/PRED-2x-*.md`의 P7-PRED-21 절이 유일한 명세(코드·diff 그대로). 근거 REVIEW-07 §R4·REVIEW-08 §R4·REVIEW-09.
  리뷰(클라우드 세션): 명세 전문 그대로. verify 3종 통과.
  리뷰(2026-09-26): 명세 블록 대조 이탈 없음(신규 파일 공백 정규화 diff 0, 수정 파일 +/- 줄 비교). 풀 pytest 1928 통과·check_docs·check_data_consistency 통과.
  <!-- autopilot: {"stage": "done", "mode": "auto", "attempts": 1, "deps": [], "kind": "code", "scope": ["src/metrics/segments.py", "tests/test_segments.py", "v0.3/data/files_index.md"], "verify": ["python3 -m pytest tests/test_segments.py -q", "python3 scripts/check_docs.py", "python3 scripts/check_data_consistency.py"]} -->
- **[P7-PRED-22]** 예측 라이브러리(r3 기본 + r4 섀도 + 전력 판정) — `v0.3/data/phase-7-ui-renewal/specs/PRED-2x-*.md`의 P7-PRED-22 절이 유일한 명세(코드·diff 그대로). 근거 REVIEW-07 §R4·REVIEW-08 §R4·REVIEW-09.
  리뷰(클라우드 세션): 명세 전문 그대로(7개 신규 파일). __init__.py는 P7-PRED-20에서 선생성한 내용과 동일. verify 3종 통과(30 pytest).
  리뷰(2026-09-26): 명세 블록 대조 이탈 없음(신규 파일 공백 정규화 diff 0, 수정 파일 +/- 줄 비교). 풀 pytest 1928 통과·check_docs·check_data_consistency 통과.
  <!-- autopilot: {"stage": "done", "mode": "auto", "attempts": 1, "deps": [], "kind": "code", "scope": ["src/metrics/prediction/__init__.py", "src/metrics/prediction/core.py", "src/metrics/prediction/physio.py", "src/metrics/prediction/effort.py", "src/metrics/prediction/signals.py", "src/metrics/prediction/core_r4.py", "src/metrics/prediction/signals_r4.py", "tests/test_prediction_core.py", "tests/test_prediction_signals.py", "tests/test_prediction_core_r4.py", "tests/test_prediction_signals_r4.py", "tests/test_race_effort.py", "v0.3/data/files_index.md"], "verify": ["python3 -m pytest tests/test_prediction_core.py tests/test_prediction_signals.py tests/test_prediction_core_r4.py tests/test_prediction_signals_r4.py tests/test_race_effort.py -q", "python3 scripts/check_docs.py", "python3 scripts/check_data_consistency.py"]} -->
- **[P7-PRED-23]** 분류기 v2(예측 비의존) — `v0.3/data/phase-7-ui-renewal/specs/PRED-2x-*.md`의 P7-PRED-23 절이 유일한 명세(코드·diff 그대로). 근거 REVIEW-07 §R4·REVIEW-08 §R4·REVIEW-09.
  리뷰(클라우드 세션): classifier.py 전문 교체, 명세 그대로. verify 3종 통과 + 전체 pytest 1706건(known env-limited 3건 제외) 통과 확인.
  리뷰(2026-09-26): 명세 블록 대조 이탈 없음(신규 파일 공백 정규화 diff 0, 수정 파일 +/- 줄 비교). 풀 pytest 1928 통과·check_docs·check_data_consistency 통과.
  <!-- autopilot: {"stage": "done", "mode": "auto", "attempts": 1, "deps": [], "kind": "code", "scope": ["src/metrics/classifier.py", "tests/test_activity_calcs.py"], "verify": ["python3 -m pytest tests/test_activity_calcs.py tests/test_mock_calcs.py -q", "python3 scripts/check_docs.py", "python3 scripts/check_data_consistency.py"]} -->
- **[P7-PRED-88]** TIDS 세그먼트 시간 기준 — `v0.3/data/phase-7-ui-renewal/specs/PRED-8x-*.md`의 P7-PRED-88 절이 유일한 명세(코드·diff 그대로). 근거 REVIEW-07 §R4·REVIEW-08 §R4·REVIEW-09.
  리뷰(클라우드 세션): tids.py 전문 교체, 명세 그대로. verify 3종 통과.
  리뷰(2026-09-26): 명세 대조 이탈 없음. 단, 명세 코드 자체 결함을 실데이터 재계산에서 발견 — 존1 시간이 0이면 pattern() 의 log10(0) 으로 계산 예외(엔진이 삼켜 해당 일 TIDS 누락). main 에서 교정: z1>0 and z3>0 일 때만 양극화 지수 계산, 아니면 None(테스트 추가).
  <!-- autopilot: {"stage": "done", "mode": "auto", "attempts": 1, "deps": [], "kind": "code", "scope": ["src/metrics/tids.py", "tests/test_tids_time.py", "tests/test_phase4_dod.py", "v0.3/data/files_index.md"], "verify": ["python3 -m pytest tests/test_tids_time.py tests/test_phase4_dod.py tests/test_activity_calcs.py -q", "python3 scripts/check_docs.py", "python3 scripts/check_data_consistency.py"]} -->
- **[P7-PRED-24]** HR 프로필(자체·기기, 두 존 체계) — `v0.3/data/phase-7-ui-renewal/specs/PRED-2x-*.md`의 P7-PRED-24 절이 유일한 명세(코드·diff 그대로). 근거 REVIEW-07 §R4·REVIEW-08 §R4·REVIEW-09.
  리뷰(클라우드 세션): 명세 전문·diff 그대로. gen_metric_dictionary.py 재생성(32→33 calculators). verify 3종 통과.
  리뷰(2026-09-26): 명세 블록 대조 이탈 없음(신규 파일 공백 정규화 diff 0, 수정 파일 +/- 줄 비교). 풀 pytest 1928 통과·check_docs·check_data_consistency 통과.
  <!-- autopilot: {"stage": "done", "mode": "auto", "attempts": 1, "deps": [], "kind": "code", "scope": ["src/metrics/hr_profile.py", "tests/test_hr_profile.py", "src/metrics/engine.py", "src/utils/metric_registry.py", "scripts/check_docs.py", "v0.3/data/metric_dictionary.md", "v0.3/data/files_index.md"], "verify": ["python3 -m pytest tests/test_hr_profile.py tests/test_doc_sync.py tests/test_metric_naming.py tests/test_validator.py -q", "python3 scripts/check_docs.py", "python3 scripts/check_data_consistency.py"]} -->
- **[P7-PRED-25]** Garmin 참조값(LTHR·레이스 예측) 동기화 — `v0.3/data/phase-7-ui-renewal/specs/PRED-2x-*.md`의 P7-PRED-25 절이 유일한 명세(코드·diff 그대로). 근거 REVIEW-07 §R4·REVIEW-08 §R4·REVIEW-09.
  리뷰(클라우드 세션): 명세 전문·diff 그대로(기존 파싱 버그 수정 — lactateThresholdHeartRate 경로 오류로 0건이던 것을 실제 payload 경로로 교체). verify 3종 통과. 실 Garmin API 호출은 P7-PRED-61 런북(사람)에서.
  리뷰(2026-09-26): 명세 대조 이탈 없음. 실 Garmin API 로 검증하며 결함 2건 교정 — 젖산역치 이력 응답이 리스트가 아니라 {speed, heart_rate, power} dict(파서 0건), 이력 조회는 366일 제한(400) → 360일 창 분할. LT 속도 ×10 단위 확정.
  <!-- autopilot: {"stage": "done", "mode": "auto", "attempts": 1, "deps": [], "kind": "code", "scope": ["src/sync/garmin_ref_parsers.py", "src/sync/garmin_ref_sync.py", "src/sync/garmin_daily_extensions.py", "tests/test_garmin_ref_parsers.py", "tests/test_garmin_ref_sync.py", "src/utils/metric_registry.py", "v0.3/data/metric_dictionary.md", "v0.3/data/files_index.md"], "verify": ["python3 -m pytest tests/test_garmin_ref_parsers.py tests/test_garmin_ref_sync.py tests/test_doc_sync.py -q", "python3 scripts/check_docs.py", "python3 scripts/check_data_consistency.py"]} -->
- **[P7-PRED-86]** 날씨 모듈 통합(provider.py = 단일 Open-Meteo 클라이언트) — `v0.3/data/phase-7-ui-renewal/specs/PRED-3x-*.md`의 P7-PRED-86 절이 유일한 명세(코드·diff 그대로). 근거 REVIEW-07 §R4·REVIEW-08 §R4·REVIEW-09.
  리뷰(클라우드 세션): provider.py 전문 교체(죽은 코드였음, 기존 소비자 없음 확인). 명세 그대로. verify 3종 통과.
  리뷰(2026-09-26): 명세 블록 대조 이탈 없음(신규 파일 공백 정규화 diff 0, 수정 파일 +/- 줄 비교). 풀 pytest 1928 통과·check_docs·check_data_consistency 통과.
  <!-- autopilot: {"stage": "done", "mode": "auto", "attempts": 1, "deps": [], "kind": "code", "scope": ["src/weather/provider.py", "tests/test_weather_provider.py", "v0.3/data/files_index.md"], "verify": ["python3 -m pytest tests/test_weather_provider.py -q", "python3 scripts/check_docs.py", "python3 scripts/check_data_consistency.py"]} -->
- **[P7-PRED-32]** 활동 외기 기상 인제스트 + 우선순위 + sync 훅 — `v0.3/data/phase-7-ui-renewal/specs/PRED-3x-*.md`의 P7-PRED-32 절이 유일한 명세(코드·diff 그대로). 근거 REVIEW-07 §R4·REVIEW-08 §R4·REVIEW-09.
  리뷰(클라우드 세션): 명세 전문·diff 그대로. verify 3종 통과 + 전체 pytest 1710건(known env-limited 3건 제외) 통과 확인(5유닛 주기 전체 검증). 실 API 백필은 P7-PRED-61 런북(사람).
  리뷰(2026-09-26): 명세 블록 대조 이탈 없음(신규 파일 공백 정규화 diff 0, 수정 파일 +/- 줄 비교). 풀 pytest 1928 통과·check_docs·check_data_consistency 통과.
  <!-- autopilot: {"stage": "done", "mode": "auto", "attempts": 1, "deps": [], "kind": "code", "scope": ["src/weather/activity_weather.py", "src/utils/metric_priority.py", "src/sync.py", "tests/test_weather_ingest.py", "src/utils/metric_registry.py", "v0.3/data/metric_dictionary.md", "v0.3/data/files_index.md"], "verify": ["python3 -m pytest tests/test_weather_provider.py tests/test_weather_ingest.py tests/test_doc_sync.py -q", "python3 scripts/check_docs.py", "python3 scripts/check_data_consistency.py"]} -->
- **[P7-PRED-33]** 개인 기온 모델 — `v0.3/data/phase-7-ui-renewal/specs/PRED-3x-*.md`의 P7-PRED-33 절이 유일한 명세(코드·diff 그대로). 근거 REVIEW-07 §R4·REVIEW-08 §R4·REVIEW-09.
  리뷰(클라우드 세션): 명세 전문·diff 그대로. gen_metric_dictionary.py 재생성(33→34 calculators). verify 3종 통과.
  리뷰(2026-09-26): 명세 블록 대조 이탈 없음(신규 파일 공백 정규화 diff 0, 수정 파일 +/- 줄 비교). 풀 pytest 1928 통과·check_docs·check_data_consistency 통과.
  <!-- autopilot: {"stage": "done", "mode": "auto", "attempts": 1, "deps": [], "kind": "code", "scope": ["src/metrics/heat_model.py", "tests/test_heat_model.py", "src/metrics/engine.py", "src/utils/metric_registry.py", "scripts/check_docs.py", "v0.3/data/metric_dictionary.md", "v0.3/data/files_index.md"], "verify": ["python3 -m pytest tests/test_heat_model.py tests/test_doc_sync.py tests/test_metric_naming.py tests/test_validator.py -q", "python3 scripts/check_docs.py", "python3 scripts/check_data_consistency.py"]} -->
- **[P7-PRED-83]** sapi 외기 기온 — `v0.3/data/phase-7-ui-renewal/specs/PRED-8x-*.md`의 P7-PRED-83 절이 유일한 명세(코드·diff 그대로). 근거 REVIEW-07 §R4·REVIEW-08 §R4·REVIEW-09.
  리뷰(클라우드 세션): diff 그대로(raw SQL 제거, ADR-009 준수). verify 3종 통과.
  리뷰(2026-09-26): 명세 블록 대조 이탈 없음(신규 파일 공백 정규화 diff 0, 수정 파일 +/- 줄 비교). 풀 pytest 1928 통과·check_docs·check_data_consistency 통과.
  <!-- autopilot: {"stage": "done", "mode": "auto", "attempts": 1, "deps": [], "kind": "code", "scope": ["src/metrics/sapi.py", "tests/test_sapi.py"], "verify": ["python3 -m pytest tests/test_sapi.py -q", "python3 scripts/check_docs.py", "python3 scripts/check_data_consistency.py"]} -->
- **[P7-PRED-90]** vdot_adj 폐기 + fearp 외기·이슬점 — `v0.3/data/phase-7-ui-renewal/specs/PRED-8x-*.md`의 P7-PRED-90 절이 유일한 명세(코드·diff 그대로). 근거 REVIEW-07 §R4·REVIEW-08 §R4·REVIEW-09.
  리뷰(클라우드 세션): 명세 전문·diff 그대로(34→33 calculators). 스코프 밖의 다른 VDOT_ADJ 참조 다수 확인했으나 모두 문자열/템플릿 표시용이거나 이미 0행이던 조회라 회귀 없음(grep으로 import 경로 확인). verify 3종 통과 + 전체 pytest 1711건(known env-limited 3건 제외) 통과.
  리뷰(2026-09-26): 명세 블록 대조 이탈 없음(신규 파일 공백 정규화 diff 0, 수정 파일 +/- 줄 비교). 풀 pytest 1928 통과·check_docs·check_data_consistency 통과.
  <!-- autopilot: {"stage": "done", "mode": "auto", "attempts": 1, "deps": [], "kind": "code", "scope": ["src/metrics/vdot_adj.py", "tests/test_vdot_adj.py", "src/metrics/engine.py", "scripts/check_docs.py", "src/metrics/fearp.py", "tests/test_fearp_v2.py", "src/web/views_dashboard.py", "src/web/views_report_sections_data.py", "src/training/planner_config.py", "src/training/readiness.py", "src/services/plan_template_service.py", "tests/test_readiness.py", "tests/test_plan_template_service.py", "v0.3/data/metric_dictionary.md", "v0.3/data/files_index.md"], "verify": ["python3 -m pytest tests/test_fearp_v2.py tests/test_readiness.py tests/test_plan_template_service.py tests/test_sapi.py tests/test_engine.py tests/test_phase4_dod.py -q", "python3 scripts/check_docs.py", "python3 scripts/check_data_consistency.py"]} -->
- **[P7-PRED-41]** 훈련 반응 r4(세트 기반, 기기 불필요) — `v0.3/data/phase-7-ui-renewal/specs/PRED-4x-*.md`의 P7-PRED-41 절이 유일한 명세(코드·diff 그대로). 근거 REVIEW-07 §R4·REVIEW-08 §R4·REVIEW-09.
  리뷰(클라우드 세션): 명세 전문·diff 그대로(33→34 calculators). verify 3종 통과.
  리뷰(2026-09-26): 명세 블록 대조 이탈 없음(신규 파일 공백 정규화 diff 0, 수정 파일 +/- 줄 비교). 풀 pytest 1928 통과·check_docs·check_data_consistency 통과.
  <!-- autopilot: {"stage": "done", "mode": "auto", "attempts": 1, "deps": [], "kind": "code", "scope": ["src/metrics/prediction/response.py", "src/metrics/training_response.py", "tests/test_training_response.py", "src/metrics/engine.py", "src/utils/metric_registry.py", "scripts/check_docs.py", "v0.3/data/metric_dictionary.md", "v0.3/data/files_index.md"], "verify": ["python3 -m pytest tests/test_training_response.py tests/test_doc_sync.py tests/test_metric_naming.py tests/test_validator.py -q", "python3 scripts/check_docs.py", "python3 scripts/check_data_consistency.py"]} -->
- **[P7-PRED-42]** 계획 구조 형식 + 세그먼트 비교(순수) — `v0.3/data/phase-7-ui-renewal/specs/PRED-4x-*.md`의 P7-PRED-42 절이 유일한 명세(코드·diff 그대로). 근거 REVIEW-07 §R4·REVIEW-08 §R4·REVIEW-09.
  리뷰(클라우드 세션): 명세 전문 그대로. verify 3종 통과.
  리뷰(2026-09-26): 명세 블록 대조 이탈 없음(신규 파일 공백 정규화 diff 0, 수정 파일 +/- 줄 비교). 풀 pytest 1928 통과·check_docs·check_data_consistency 통과.
  <!-- autopilot: {"stage": "done", "mode": "auto", "attempts": 1, "deps": [], "kind": "code", "scope": ["src/training/outcome_v2.py", "tests/test_outcome_v2.py", "v0.3/data/files_index.md"], "verify": ["python3 -m pytest tests/test_outcome_v2.py -q", "python3 scripts/check_docs.py", "python3 scripts/check_data_consistency.py"]} -->
- **[P7-PRED-43]** 매처 세그먼트 이행 저장 — `v0.3/data/phase-7-ui-renewal/specs/PRED-4x-*.md`의 P7-PRED-43 절이 유일한 명세(코드·diff 그대로). 근거 REVIEW-07 §R4·REVIEW-08 §R4·REVIEW-09.
  리뷰(클라우드 세션): 명세 전문·diff 그대로. verify 3종 통과.
  리뷰(2026-09-26): 명세 블록 대조 이탈 없음(신규 파일 공백 정규화 diff 0, 수정 파일 +/- 줄 비교). 풀 pytest 1928 통과·check_docs·check_data_consistency 통과.
  <!-- autopilot: {"stage": "done", "mode": "auto", "attempts": 1, "deps": [], "kind": "code", "scope": ["src/training/outcome_store.py", "src/training/matcher.py", "tests/test_outcome_store.py", "v0.3/data/files_index.md"], "verify": ["python3 -m pytest tests/test_outcome_store.py tests/test_outcome_v2.py -q", "python3 scripts/check_docs.py", "python3 scripts/check_data_consistency.py"]} -->
- **[P7-PRED-51]** DARP r3 기본 + r4 섀도 2종 — `v0.3/data/phase-7-ui-renewal/specs/PRED-5x-*.md`의 P7-PRED-51 절이 유일한 명세(코드·diff 그대로). 근거 REVIEW-07 §R4·REVIEW-08 §R4·REVIEW-09.
  리뷰(클라우드 세션): darp.py 전문 교체(r3), darp_r4.py 신규(섀도 2종), diff 5개 그대로(34→37 calculators, provider 분리 규칙 반영). verify 3종 통과(86 pytest) + 전체 pytest 1734건(known env-limited 3건 제외) 통과.
  리뷰(2026-09-26): 명세 블록 대조 이탈 없음(신규 파일 공백 정규화 diff 0, 수정 파일 +/- 줄 비교). 풀 pytest 1928 통과·check_docs·check_data_consistency 통과.
  <!-- autopilot: {"stage": "done", "mode": "auto", "attempts": 1, "deps": [], "kind": "code", "scope": ["src/metrics/darp.py", "src/metrics/darp_r4.py", "tests/test_darp_v2.py", "tests/test_darp_r4.py", "src/metrics/engine.py", "src/utils/metric_registry.py", "scripts/check_docs.py", "tests/test_metric_naming.py", "tests/test_validator.py", "v0.3/data/metric_dictionary.md", "v0.3/data/files_index.md"], "verify": ["python3 -m pytest tests/test_darp_v2.py tests/test_darp_r4.py tests/test_doc_sync.py tests/test_metric_naming.py tests/test_validator.py tests/test_dashboard_service.py tests/test_ai_context.py -q", "python3 scripts/check_docs.py", "python3 scripts/check_data_consistency.py"]} -->
- **[P7-PRED-52]** rri·eftp 의존 복구 + marathon_shape v2 — `v0.3/data/phase-7-ui-renewal/specs/PRED-5x-*.md`의 P7-PRED-52 절이 유일한 명세(코드·diff 그대로). 근거 REVIEW-07 §R4·REVIEW-08 §R4·REVIEW-09.
  리뷰(클라우드 세션): marathon_shape.py 전문 교체, rri·eftp·테스트 3개 diff 그대로. verify 3종 통과.
  리뷰(2026-09-26): 명세 블록 대조 이탈 없음(신규 파일 공백 정규화 diff 0, 수정 파일 +/- 줄 비교). 풀 pytest 1928 통과·check_docs·check_data_consistency 통과.
  <!-- autopilot: {"stage": "done", "mode": "auto", "attempts": 1, "deps": [], "kind": "code", "scope": ["src/metrics/marathon_shape.py", "src/metrics/rri.py", "src/metrics/eftp.py", "tests/test_marathon_shape.py", "tests/test_rri.py", "tests/test_eftp.py"], "verify": ["python3 -m pytest tests/test_marathon_shape.py tests/test_rri.py tests/test_eftp.py -q", "python3 scripts/check_docs.py", "python3 scripts/check_data_consistency.py"]} -->
- **[P7-PRED-89]** acwr·lsi·adti·rtti·hrss·di 재정의 — `v0.3/data/phase-7-ui-renewal/specs/PRED-8x-*.md`의 P7-PRED-89 절이 유일한 명세(코드·diff 그대로). 근거 REVIEW-07 §R4·REVIEW-08 §R4·REVIEW-09.
  리뷰(클라우드 세션): di.py 전문 교체, 나머지 5개 diff 그대로. files_index.md 재생성 필요(check_docs 최초 실패 → 재생성 후 통과). verify 3종 통과(51 pytest) + 전체 pytest 1738건(known env-limited 3건 제외) 통과.
  리뷰(2026-09-26): 명세 블록 대조 이탈 없음(신규 파일 공백 정규화 diff 0, 수정 파일 +/- 줄 비교). 풀 pytest 1928 통과·check_docs·check_data_consistency 통과.
  <!-- autopilot: {"stage": "done", "mode": "auto", "attempts": 1, "deps": [], "kind": "code", "scope": ["src/metrics/acwr.py", "src/metrics/lsi.py", "src/metrics/adti.py", "src/metrics/rtti.py", "src/metrics/hrss.py", "src/metrics/di.py", "tests/test_di_v2.py", "tests/test_activity_core_sanitize.py", "tests/test_daily_calcs.py", "tests/test_rtti.py", "tests/test_engine.py", "v0.3/data/files_index.md"], "verify": ["python3 -m pytest tests/test_di_v2.py tests/test_activity_core_sanitize.py tests/test_daily_calcs.py tests/test_rtti.py tests/test_engine.py tests/test_cirs.py tests/test_crs.py -q", "python3 scripts/check_docs.py", "python3 scripts/check_data_consistency.py"]} -->
- **[P7-PRED-53]** 대회 확인 서비스 — `v0.3/data/phase-7-ui-renewal/specs/PRED-5x-*.md`의 P7-PRED-53 절이 유일한 명세(코드·diff 그대로). 근거 REVIEW-07 §R4·REVIEW-08 §R4·REVIEW-09.
  리뷰(클라우드 세션): 명세 전문 그대로. verify 3종 통과.
  리뷰(2026-09-26): 명세 블록 대조 이탈 없음(신규 파일 공백 정규화 diff 0, 수정 파일 +/- 줄 비교). 풀 pytest 1928 통과·check_docs·check_data_consistency 통과.
  <!-- autopilot: {"stage": "done", "mode": "auto", "attempts": 1, "deps": [], "kind": "code", "scope": ["src/services/race_result_service.py", "tests/test_race_result_service.py", "v0.3/data/files_index.md"], "verify": ["python3 -m pytest tests/test_race_result_service.py -q", "python3 scripts/check_docs.py", "python3 scripts/check_data_consistency.py"]} -->
- **[P7-PRED-62]** 수용 백테스트 스크립트(r3·r4 나란히) — `v0.3/data/phase-7-ui-renewal/specs/PRED-6x-*.md`의 P7-PRED-62 절이 유일한 명세(코드·diff 그대로). 근거 REVIEW-07 §R4·REVIEW-08 §R4·REVIEW-09.
  리뷰(클라우드 세션): 명세 전문 그대로. verify 3종 통과. 실DB 대상 실행(합격 기준 확인)은 P7-PRED-61 런북(사람).
  리뷰(2026-09-26): 명세 블록 대조 이탈 없음(신규 파일 공백 정규화 diff 0, 수정 파일 +/- 줄 비교). 풀 pytest 1928 통과·check_docs·check_data_consistency 통과.
  <!-- autopilot: {"stage": "done", "mode": "auto", "attempts": 1, "deps": [], "kind": "code", "scope": ["scripts/pred_backtest.py", "tests/test_pred_backtest.py", "v0.3/data/files_index.md"], "verify": ["python3 -m pytest tests/test_pred_backtest.py -q", "python3 scripts/check_docs.py", "python3 scripts/check_data_consistency.py"]} -->
- **[P7-PRED-63]** 예측 스냅샷(v21) + 대회 전향 평가 — `v0.3/data/phase-7-ui-renewal/specs/PRED-6x-*.md`의 P7-PRED-63 절이 유일한 명세(코드·diff 그대로). 근거 REVIEW-07 §R4·REVIEW-08 §R4·REVIEW-09.
  리뷰(클라우드 세션): 명세 전문·diff 그대로(schema v20→v21). verify 3종 통과(72 pytest) + 전체 pytest 1746건(known env-limited 3건 제외) 통과.
  리뷰(2026-09-26): 명세 블록 대조 이탈 없음(신규 파일 공백 정규화 diff 0, 수정 파일 +/- 줄 비교). 풀 pytest 1928 통과·check_docs·check_data_consistency 통과.
  <!-- autopilot: {"stage": "done", "mode": "auto", "attempts": 1, "deps": [], "kind": "code", "scope": ["src/db_schema_v21.py", "src/db_setup.py", "src/services/prediction_snapshot_service.py", "src/services/race_result_service.py", "src/web/bg_sync.py", "tests/test_prediction_snapshot.py", "tests/test_db_setup.py", "tests/test_phase1_schema.py", "v0.3/data/files_index.md"], "verify": ["python3 -m pytest tests/test_prediction_snapshot.py tests/test_db_setup.py tests/test_phase1_schema.py tests/test_race_result_service.py -q", "python3 scripts/check_docs.py", "python3 scripts/check_data_consistency.py"]} -->
- **[P7-PRED-71]** 비교·근거·대회 확인 API(+섀도 후보 행) — `v0.3/data/phase-7-ui-renewal/specs/PRED-7x-*.md`의 P7-PRED-71 절이 유일한 명세(코드·diff 그대로). 근거 REVIEW-07 §R4·REVIEW-08 §R4·REVIEW-09.
  리뷰(클라우드 세션): 명세 전문·diff 그대로. verify 3종 통과(22 pytest) + check_data_consistency 통과.
  리뷰(2026-09-26): 명세 블록 대조 이탈 없음(신규 파일 공백 정규화 diff 0, 수정 파일 +/- 줄 비교). 풀 pytest 1928 통과·check_docs·check_data_consistency 통과.
  <!-- autopilot: {"stage": "done", "mode": "auto", "attempts": 1, "deps": [], "kind": "code", "scope": ["src/services/prediction_compare_service.py", "src/api/routes_prediction.py", "src/api/__init__.py", "src/services/race_hub_service.py", "tests/test_prediction_compare.py", "tests/test_api_prediction.py", "v0.3/data/files_index.md"], "verify": ["python3 -m pytest tests/test_prediction_compare.py tests/test_api_prediction.py tests/test_api_today.py -q", "python3 scripts/check_docs.py", "python3 scripts/check_data_consistency.py"]} -->
- **[P7-PRED-85]** 내장 Daniels 표 → 공식, import 경로 수정 — `v0.3/data/phase-7-ui-renewal/specs/PRED-8x-*.md`의 P7-PRED-85 절이 유일한 명세(코드·diff 그대로). 근거 REVIEW-07 §R4·REVIEW-08 §R4·REVIEW-09.
  리뷰(클라우드 세션): 명세 diff 5개 그대로. verify 3종 통과(28 pytest) + 전체 pytest 1754건(known env-limited 3건 제외) 통과.
  리뷰(2026-09-26): 명세 블록 대조 이탈 없음(신규 파일 공백 정규화 diff 0, 수정 파일 +/- 줄 비교). 풀 pytest 1928 통과·check_docs·check_data_consistency 통과.
  <!-- autopilot: {"stage": "done", "mode": "auto", "attempts": 1, "deps": [], "kind": "code", "scope": ["src/utils/daniels_table.py", "src/ai/tool_exec_context.py", "src/training/interval_calc.py", "src/training/planner_rules.py", "tests/test_daniels_table.py"], "verify": ["python3 -m pytest tests/test_daniels_table.py tests/test_eftp.py tests/test_marathon_shape.py tests/test_replanner.py -q", "python3 scripts/check_docs.py", "python3 scripts/check_data_consistency.py"]} -->
- **[P7-PRED-72]** 레이스 허브 UI(73·74 포함) — `v0.3/data/phase-7-ui-renewal/specs/PRED-7x-*.md`의 P7-PRED-72 절이 유일한 명세(코드·diff 그대로). 근거 REVIEW-07 §R4·REVIEW-08 §R4·REVIEW-09.
  리뷰(클라우드 세션): 명세 전문·diff 그대로(72/73/74 통합). `types/index.ts`의 `PredictionCompareRow`가 명세 diff에서는 `key: 'garmin'|'ref'|'self'`·`candidate` 필드 없이 정의됐지만, 같은 유닛의 r4 섹션이 r4/r4_asym 행과 `candidate?: boolean`을 명시적으로 요구하고 `PredictionCompare.svelte`(역시 명세 원문)가 `row.candidate`를 읽어 타입 에러 발생 — 명세 자신의 요구사항을 완성하는 수준으로 `key`에 `'r4'|'r4_asym'` 추가, `contributions`를 `Record<string, number> | null`로, `candidate?: boolean` 추가(동작 변경 아님, DECISIONS.md 기록 대상 아닌 사소 보완으로 판단). verify 3종 통과: svelte-check 0 errors(기존 경고 15개 그대로), node --test 3파일 전부 통과, npm run build 성공.
  리뷰(2026-09-26): 명세 대조 이탈 1건 — types/index.ts 의 PredictionCompareRow 에 candidate·key r4/r4_asym·contributions Record 를 명세 본문 밖에서 추가. 수용: 유닛 71 API 가 실제로 candidate 행(r4·r4_asym)과 기여도 키 H/I/R/T/race 를 내보내므로 타입 보완이 필요했다(API 응답 대조 확인). 실데이터 사본(재추출·날씨·Garmin 이력·재계산 적용)에서 브라우저 스모크: 390·1280px 가로 넘침 없음, 콘솔/HTTP 에러 0, 3-way 비교(Garmin·기기 심박·자체 + 후보 r4·r4 비대칭 섀도)·예측 근거·대회 확인 표시, 대회 확인 클릭(페이스→API confirmed_effort=paced→재클릭 시 null) 확인. svelte-check 에러 0(경고 15), build·test:unit 204 통과.
  <!-- autopilot: {"stage": "done", "mode": "auto", "attempts": 1, "deps": [], "kind": "code", "scope": ["frontend/src/lib/predictionCompare.ts", "frontend/tests/predictionCompare.test.mjs", "frontend/src/lib/types/index.ts", "frontend/src/lib/api/prediction.ts", "frontend/src/lib/components/PredictionCompare.svelte", "frontend/src/lib/components/PredictionBasis.svelte", "frontend/src/lib/components/RaceConfirmList.svelte", "frontend/src/lib/components/RaceHub.svelte", "frontend/src/lib/format.ts"], "verify": ["cd frontend && npm run check", "cd frontend && node --test tests/predictionCompare.test.mjs tests/raceHub.test.mjs tests/format.test.mjs", "cd frontend && npm run build"]} -->

- **[P7-PRED-61]** 실DB 백필 런북 — `v0.3/data/phase-7-ui-renewal/specs/PRED-6x-backfill.md`(사람 실행).
  실행(2026-09-26, 백업 `running.db.bak-pred-20260926` 무결성 확인 후): 재추출(활동 586·랩 3,360·오류 0) → 외기 날씨(428건, 실패 0) → Garmin 참조 이력(레이스 예측 1,956·LT 103) → 재계산 전 스냅샷 → `recompute --days 1100`(약 25분, 실패 0) → 계획 인제스트. 사본 리허설과 동일 결과. 백테스트 PASS(r3 1.39/2.16, r4 1.39/1.77, r4_asym 1.26/1.46, n=7). 현재 15℃ 마라톤: r3 3:40:39 · r4 3:42:11 · r4 비대칭 3:40:19 · Garmin 3:44:22. indoor_running 16건 DB 정정은 미실행(별도 지시 시).
  <!-- autopilot: {"stage": "done", "mode": "manual", "attempts": 1, "deps": [], "kind": "code", "scope": [], "verify": []} -->
- **[P7-PRED-44]** 외부 계획 인제스트 — `PRED-4x-*.md`(사람 확인 후 구현).
  Garmin 구현·실DB 적용(2026-09-26, `src/sync/plan_ingest.py`): 실행된 계획 39건(세그먼트 이행률 산출)·적응형 계획 6건. Intervals 이벤트도 구현·적용(2026-09-27, `plan_ingest_intervals.py`): 30건 저장·24건 활동 연결·이행률 10건. (처음 401 은 키 무효가 아니라 Fernet 암호화 키를 셸에서 복호화하지 못한 탓 — 컨테이너에서 정상.)
  <!-- autopilot: {"stage": "done", "mode": "manual", "attempts": 1, "deps": [], "kind": "code", "scope": [], "verify": []} -->

---

## LATER

- **[P7-DATA-MENU-ENTRY]** 상단 3선 메뉴 실제 진입점(`/v2/data/settings` 등) — Phase 7d
  Data API(`GET /api/v1/data/sources` 등)가 있어야 채울 수 있음, 지금은 비활성 ☰ 버튼만
  존재(`P7-IMPL-SVELTE` 1차 참조).

- **[P7-IMPL-COACH-PLAN-ADJUSTMENT-ACCEPT]** 5-F/5-G의 "조정 수락" 영속화 —
  현재 `adjust_todays_plan()`은 완전 읽기 전용(매 로드마다 재계산, DB
  미기록)이라 "수락" 버튼을 눌러도 반영할 데이터가 없음. `planned_workouts`
  에 조정 결과를 반영하는 쓰기 경로 신설 필요(예: `adjusted_distance_km`
  컬럼 추가 또는 `distance_km`를 직접 덮어쓰고 `source`에 조정 이력 태그) —
  스키마 변경 수반 가능성 있어 별도 설계 필요. **`03e-coach.md` 196행이
  이 기능을 명시적으로 Phase 7c(세션 조정 승인 API `PUT .../accept-
  adjustment`)로 배정해둠** — Phase 7b 범위인 지금 앞당겨 만들지 않음,
  ML 개인화 플랜 생성(7c)과 묶어서 재검토. `P7-IMPL-COACH-PLAN-ACTIVE`
  설계 근거는 `DECISIONS.md` 참조.

---

## DONE

- **[P7-UI-REVIEW-0927]** 실계정 UI 점검 → 계획 기간·단계, 매칭·결과 라벨, 이행률, 예측 카드 정리,
  마일스톤 표시, 동기화 소스 토글(`sync_sources`) 정정(2026-09-27, 사용자 승인). 결정·근거는
  `DECISIONS.md [P7-UI-REVIEW-0927]`. 실 DB 정정은 `src.training.rematch` 로 백업 후 사용자 지시 시. 남은 것:
  Today 좌측 열 빈 공간, Coach 대화 제목·미리보기, 메트릭 브라우저 위계, PB 출처 라벨(대회 기반/구간 기반),
  롱런 상한(마라톤 피크 22km — planner 설계, 별도 검토), 미래 주차 볼륨이 현재 CTL 고정.
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
- **[P7-IMPL-SVELTE 1차]** SvelteKit 프론트엔드 착수 — 기반 + Today 화면(2026-09-22, plan
  mode로 조사·설계 후 승인받아 진행, 사용자 auto-accept). 사용자가 "UI Renewal인데 실제
  UI가 없다"고 지적한 게 계기 — D5/D3/API가 전부 백엔드였고 `frontend/` 자체가 없었음.
  Library/Coach 화면까지 한 덩어리로 만들면 리뷰가 무거워질 것 같아 범위를 Today까지로
  좁히기로 사용자와 합의(`P7-IMPL-SVELTE-2`가 나머지, LATER 참조).
  `npx sv create`로 `frontend/` 초기화(TypeScript + Tailwind v4 + adapter-static — 05
  문서의 "tailwindcss ^3.x"는 구식, 실제 최신은 v4/설정파일 없이 CSS `@import`. `svelte.config.js`도
  이번 kit 버전(2.7x)부턴 안 쓰고 `vite.config.ts`의 `sveltekit({adapter, paths})`로 통합됨 —
  05 문서 예시와 구조가 다름, 갱신함). `base: '/v2'`, 개발 중엔 Vite가 `/api`를 Flask
  실제 엔트리포인트(`src/serve.py`, 포트 18080 — 05 문서의 5000 예시와 다름)로 프록시.
  공통 레이아웃(하단 3탭+상단 ☰ 더미) + 컴포넌트 4개(EvidenceQuote/MetricCell/QuickInput/
  RecommendationCard, 04 스펙대로 — MetricCell은 `drillable=false`, EvidenceQuote는 `onOpen`
  없으면 비대화형 렌더링. MetricBreakdown 패널이 없는 7a라 그렇게 씀) + Today 화면(L0+L1
  완성, L2는 실제 조회 가능한 데이터만 표시하는 축약 스텁 — 03a-today.md 1-A' 문구 그대로가
  아니라 월간거리/준수율/다음세션처럼 아직 없는 데이터를 지어내지 않음, narrative/plan
  API는 7b) + Library/Coach는 "준비 중" 플레이스홀더.

  **구현 중 발견한 문제 2건** (`today_service.py`에 순수 추가 — 기존 반환 구조 안 건드림):
  1) `today_service.get_today_status()`가 provider를 안 내려줘서 MetricCell(C2)의 P3(Provider
     배지 필수) 요건을 못 지킴 → `dashboard_service.get_dashboard_data()`(v1 레거시 공유 함수,
     직접 안 건드림)는 그대로 두고 UTRS/CIRS/TSB만 별도 쿼리해 최상위 `providers` dict 추가.
  2) `/api/v1/today` 응답에 오늘 체크인 존재 여부가 없어서 QuickInput(C5)의 "이미 입력했으면
     compact+complete로 표시"(03g 7-5) 요건을 못 지킴 → `get_todays_checkin()` 신규(읽기 전용,
     D5 원칙과 일관) + `routes_today.py` 응답에 `checkin` 필드 추가.

  Flask `src/web/app.py`에 `/v2/<path:path>` 정적 서빙 라우트 추가(05 §3.4 그대로,
  `_project_root()/frontend/build`). 실제 `pansongit@gmail.com` DB로 `/api/v1/today` GET/POST
  왕복 확인(실 데이터 정상 반환, 테스트로 넣은 체크인 행은 확인 후 삭제). `npm run build`/
  `npm run check`(svelte-check, 0 errors) 통과. 브라우저 도구가 이 세션에 없어 실제 렌더링·
  인터랙션의 시각 확인은 못 함 — Flask가 빌드 산출물(JS/CSS)을 올바른 Content-Type으로
  서빙하는 것과 API 응답까지는 curl로 확인, 최종 시각 확인은 사용자 브라우저 필요.
  신규 백엔드 테스트 5개(`test_today_service.py`에 3개, `test_api_today.py`에 2개),
  전체 1444 passed, `check_docs.py` 0 errors(64 warnings, 기존과 동일).
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
