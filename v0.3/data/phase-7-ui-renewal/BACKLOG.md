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
  <!-- autopilot: {"stage": "queued", "mode": "auto", "attempts": 0, "deps": ["P7-IMPL-TODAY-NEXT-SESSION"], "kind": "code", "scope": ["src/services/_narrative.py", "src/services/today_service.py", "tests/test_today_service.py", "frontend/src/lib/types/index.ts", "frontend/src/lib/evidence.ts", "frontend/src/lib/components/MetricBreakdown.svelte", "frontend/src/lib/components/MonthNarrative.svelte", "frontend/src/lib/components/EvidenceQuote.svelte", "frontend/src/routes/today/+page.svelte"], "verify": ["python3 -m pytest tests/test_today_service.py tests/test_api_today.py -q", "cd frontend && npm install && npm run check && npm run build"]} -->

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
  <!-- autopilot: {"stage": "queued", "mode": "auto", "attempts": 0, "deps": ["P7-IMPL-EVIDENCE-DRILL"], "kind": "code", "scope": ["frontend/src/lib/api/today.ts", "frontend/src/lib/components/MilestonesPanel.svelte", "frontend/src/routes/today/+page.svelte"], "verify": ["cd frontend && npm install && npm run check && npm run build"]} -->

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
