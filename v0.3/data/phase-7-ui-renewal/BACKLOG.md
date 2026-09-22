# Phase 7 UI Renewal — BACKLOG

## 진행 현황

**현재 상태**: **문서 재정렬 완료 + Phase 7a 구현 진행 중(D5·D3·Flask API·SvelteKit
Today/Library/Coach 화면 완료. D1도 완료 — 남은 건 D2/D4, 상단 3선 메뉴 UI뿐).**
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

P7-IMPL-D2(`activity_groups` 마스터 테이블, Phase 7b 전제조건)는 06 §D2에 설계가
이미 있어 "착수 전 설계" 없이 바로 큐 등록 가능함을 확인(2026-09-22) — NOW에 별도
요약을 남기지 않고 AUTOPILOT QUEUE의 `P7-IMPL-D2` 항목(상세 스펙)이 유일한 소스
(D1 때와 동일 패턴 — ID 중복은 `queue.update_item()`을 깨뜨린다).

- **[P7-IMPL-D1-REST]** D1 나머지 — utrs/cirs/race_readiness Calculator의 자식 메트릭
  저장(`P7-IMPL-D1`은 2026-09-22에 fitness/pmc의 ramp_rate→ctl만 완료, 07 로드맵
  §D1 참조). 배선(`parent_metric_name`/`_save_results()`)은 이미 있으니 각
  Calculator에서 부모-자식 관계를 정의하는 일만 남음 — **착수 전 확인 필요**:
  utrs/cirs/race_readiness 각각 어떤 메트릭이 부모인지(`v0.2/.ai/metrics.md` 또는
  해당 Calculator 소스에서 확인, PMC의 ctl↔ramp_rate처럼 명확한 부모-자식 쌍이
  존재하는지부터 확인).

---

## NEXT

Phase 7b(07 로드맵) 본격 착수분 — NOW의 D2/D1-REST 완료 후 순서대로 진행. 사용자
"UI Renewal 설계·개발·문서화를 할일 목록화" 지시로 2026-09-22 정리(07 로드맵
§Phase 7b 산출물 목록 기준, 세부 설계는 각 항목 착수 시점에 plan mode로 확정).

- **[P7-DESIGN-7B-API]** Phase 7b Flask API 8종의 서비스 함수 시그니처·DB 쿼리 확정 —
  `today_service.get_today_narrative()`, `metrics_service.get_metric_breakdown()`
  (parent_metric_id 트리 조립, D1-REST 선행 필요), `activity_service.
  get_provider_comparison()`(D2 선행 필요), `plan_service.get_static_plan_templates()`
  (07 §Phase 7b — 정적 플랜 템플릿 3~5개, **콘텐츠 자체가 아직 없음, 설계 필요**).
  06-data-layer-extensions.md 수준(테이블·필드명)은 있으나 함수 수준 스펙은 없음 —
  이후 항목들(API 구현·UI 구현)의 선행 설계 패스.

- **[P7-IMPL-7B-TODAY-L2]** Today L2 완성 — Flask API(`GET /api/v1/today/narrative`,
  `GET /api/v1/today/milestones`) + SvelteKit `<MetricBreakdown>`(C3)·
  `<TimelineNarrative>`(C7) 구현 + Today L2 내러티브 블록(`03a-today.md` 1-A(L2)·
  1-C)을 7a의 텍스트 스텁에서 실제 내러티브·트리 드릴다운으로 교체. `P7-DESIGN-7B-API`
  완료 후 착수.

- **[P7-IMPL-7B-LIBRARY]** Library 전면화 — Flask API(`GET /api/v1/library/metrics`,
  `/metrics/:slug`, `/wellness`, `/providers`) + SvelteKit `<ProviderComparison>`(C4)
  + Library/metrics·wellness·providers·홈 화면(`03c-library.md`). D2 완료 필요
  (providers는 activity_groups 조인).

- **[P7-IMPL-COACH-PLAN-STATIC]** Coach 정적 플랜 비교 작업 흐름(`03e-coach.md`
  5-C~5-F 골격) — `plan_service.get_static_plan_templates()`(`P7-DESIGN-7B-API`에서
  콘텐츠 설계) + `GET /api/v1/plan/templates`·`/compare`·`POST /api/v1/plan` +
  Coach 화면에 플랜 선택 UI 추가.

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
  <!-- autopilot: {"stage": "in_progress", "mode": "auto", "attempts": 1, "deps": [], "kind": "code", "scope": ["src/db_setup.py", "src/utils/dedup.py", "scripts/backfill_activity_groups.py", "tests/test_dedup.py", "tests/test_backfill_activity_groups.py", "tests/test_db_setup.py"], "verify": ["python3 -m pytest tests/test_dedup.py tests/test_db_setup.py tests/test_backfill_activity_groups.py -q", "python3 scripts/check_data_consistency.py"]} -->

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
  <!-- autopilot: {"stage": "queued", "mode": "auto", "attempts": 0, "deps": [], "kind": "code", "scope": ["src/metrics/utrs.py", "src/metrics/cirs.py", "tests/test_utrs.py", "tests/test_cirs.py", "tests/test_engine.py"], "verify": ["python3 -m pytest tests/test_utrs.py tests/test_cirs.py tests/test_engine.py -q", "python3 scripts/check_data_consistency.py"]} -->

---

## LATER

- **[P7-DATA-MENU-ENTRY]** 상단 3선 메뉴 실제 진입점(`/v2/data/settings` 등) — Phase 7d
  Data API(`GET /api/v1/data/sources` 등)가 있어야 채울 수 있음, 지금은 비활성 ☰ 버튼만
  존재(`P7-IMPL-SVELTE` 1차 참조). D1의 utrs/cirs/race_readiness 자식 메트릭 연결(Phase
  7b 몫, `06-data-layer-extensions.md` 참조)도 여기 대기 — AUTOPILOT QUEUE의
  `P7-IMPL-D1`은 fitness(ctl/ramp_rate)만 다룬다.

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
