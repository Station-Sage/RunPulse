# race_calendar 관리 화면·계획 연동·목표 원천 재설계 (ADJ-11·12, NEW-1·4·5, RC-1~17)

> 작성 2026-10-11 · product-architect · 상태: RC-1~10 결정 반영, RC-11~17 결정 대기 · 상위: `decisions-table.md` ADJ-11·12·NEW-1·4·5·RC-1~10, `adjustment-signals.md` §3.4, `adjustment-new-signals.md`
> DB·API 형태는 system-architect 확인 대상이다. 정책·기본값·문구 중 미결은 §5에 결정 항목으로만 올린다.

**변경 이력**
- 2026-10-11 초안(결정 전).
- 2026-10-11 RC-1~10 결정 반영: RC-1 (c) race_calendar 원천 + goals 참조 재설계(§2.1·§2.2·§2.6), 상태 머신(§2.4), 신규 결정 RC-11~17 추가.

## 1. 근본 원인 (grep 2026-10-11)
- **대회의 원천이 셋으로 흩어져 있고, B/C 대회를 관리하는 곳이 없다.** ① `goals.race_date·distance_km`(활성 목표 1건 유니크 `ux_goals_one_active`, v32) ② `planned_workouts.workout_type='race'` 행(재계획 때 다시 만들어져 메타데이터가 사라짐) ③ `race_results`(v20, `activity_id` 기준 실적, 예정 대회 아님).
- **대회 사실을 쓰는 경로가 목표 쪽에 흩어져 있다.** `training/goals.add_goal`(188줄) 호출자: `plan_template_service.py:181`(신규 화면 `/coach/plan/new`), `web/views_training_wizard.py:366`(온보딩 마법사, v1), `web/views_training_goal_crud.py:52`(v1 목표 CRUD), `src/plan.py:79`(CLI). `update_goal`이 race_date·distance_km를 직접 고친다. `goals.race_date`를 읽는 곳은 `src/` 40여 파일(planner·replanner·race_hub·today_hero·ai 컨텍스트 등)이다.
- **화면이 없다.** 대회 화면은 `/today/race`(예측 위주)와 `/today/race/races`(실적 확정 목록, 39줄)뿐이다. 등록 경로는 목표 생성의 race_date 하나뿐이고 B/C 등록·수정·삭제·조회는 없다.
- **대회에서 계획으로 이어지는 길이 끊겨 있다.** `training/constraints.b_race_week()`는 테스트만 부른다. `plan_replan_service.preview/apply/undo`는 활성 goal 기준이고 다음 월요일 시작·대회 주 거부(409 `RACE_WEEK`)라 가까운 B/C 대회를 반영할 수 없다. `plan_adjustments`(v31)의 `source` CHECK는 `crs|user|coach`뿐이다(v37 재생성에서 확장 예정).
- 그 결과 B/C 대회를 알릴 방법이 없고, `race_plan` 신호 priority는 `unknown`이며, 목표와 대회가 같은 사실을 두 곳에 들고 있게 된다.

## 2. 설계안 (확정 = 대안 A 하이브리드 + RC-1 (c))

### 2.1 데이터 모델
**원칙(RC-1 c):** 대회 사실(이름·날짜·거리·우선순위·대회 목표)의 원천은 `race_calendar` 한 곳이다. `goals`는 "그 대회를 위한 훈련 계획의 목표"(plan_weeks, 규칙 버전, 시작 부하, 상태)를 갖고 `goals.race_id`로 대회를 참조한다. `goals.race_date·distance_km·target_time_sec`는 **읽기 호환 캐시**로 남긴다(40여 개 읽기 경로와 v1을 바꾸지 않기 위함). 캐시는 `race_goal_sync` 한 곳만 쓴다. `goals.name`은 목표 자체 이름이라 동기화하지 않는다.

`race_calendar` (v38 생성, 가산)
| 필드 | 필수 | 의미 |
|---|---|---|
| `id, created_at, updated_at` | 자동 | |
| `name`, `race_date`, `distance_km` | 필수 | 이름, YYYY-MM-DD, 프리셋 5/10/21.0975/42.195 또는 직접 입력 |
| `priority` | 필수 | `A|B|C` CHECK, 미선택 불가(RC-2) |
| `goal_type`, `goal_value` | 선택 | `finish|time|pb` CHECK(RC-3). `time`이면 `goal_value`=초, `pb`는 기존 PB를 표시하고 값은 비움 |
| `adapt_choice` | 자동 | `unasked|later|adapt|no_adapt`, 기본 `unasked`. 기본 선택값은 없고 항상 묻는다(RC-4 b) |
| `plan_state` | 자동 | `none|applied|stale`: 계획에 실제 반영된 상태 |
| `taper_days`, `recovery_days` | 선택 | NULL이면 거리별 기본값(§2.5), 값이 있으면 대회별 덮어쓰기(RC-5 a) |
| `status` | 자동 | `planned|done|cancelled` |
| `origin` | 자동 | `manual|goal|import`(goal=v39 백필 또는 목표 생성 경로, import는 범위 밖) |
| `planned_workout_id`, `race_result_id` | 선택 | 계획의 race 행, 확정 실적 |
| `note` | 선택 | 메모 |
- 앞선 초안의 `goal_id`(역방향 참조)·`allow_recovery_downgrade`(RC-6으로 규칙화)·`adapt_plan` 0/1은 없앤다. 참조 방향은 `goals.race_id → race_calendar.id` 하나다.
- 인덱스: `ux_race_planned_same`(`race_date, distance_km` WHERE status='planned'), `ux_race_one_a`(`priority` WHERE priority='A' AND status='planned').

`goals` 변경 (v39)
- `race_id INTEGER REFERENCES race_calendar(id)` NULL 허용(race_date 없는 목표는 RC-11).
- `ux_goals_race`(`race_id` WHERE race_id IS NOT NULL AND status='active'): 한 대회에 활성 목표 1건.
- `ux_goals_one_active`(v32)는 **그대로 둔다.** 회귀 위험 없이 "활성 목표 1개"를 계속 보장한다.

### 2.2 불변식 ('A 대회 하나'의 새 표현)
1. 활성 목표 ≤ 1 (`ux_goals_one_active`, v32 유지).
2. planned A 대회 ≤ 1 (`ux_race_one_a`).
3. 활성 목표에 race_id가 있으면 그 대회는 `priority='A' AND status='planned'`이다. 반대로 planned A 대회가 있으면 그것을 참조하는 활성 목표가 있다. 즉 **A 지정 = 목표 대회 지정**이다. A는 목표 생성·교체 흐름으로만 만들어지고, 캘린더 시트에서 A를 고르면 목표 생성 화면으로 넘어간다(이전 A 처리는 RC-15).
4. 캐시 일치: 활성·비활성 목표 모두 `goals.race_date/distance_km/target_time_sec` = 참조 대회 값.
- 1·2는 DB 인덱스, 3·4는 서비스(`race_goal_sync`)와 `check_data_consistency.py` 신규 검사 2건으로 지킨다(SQLite 트리거는 마이그레이션·테스트 부담 대비 이득이 작아 쓰지 않는다).

### 2.3 쓰기 경로와 화면 역할 (어느 쪽에서 고쳐도 한 곳이 갱신)
| 진입 | 고치는 것 | 실제 쓰기 |
|---|---|---|
| 대회 캘린더 시트 `RaceEntrySheet` | B/C 대회 전부, A 대회의 이름·날짜·거리·대회 목표 | `race_calendar_service.update` → A이면 같은 트랜잭션에서 `race_goal_sync.push_cache` |
| 목표 생성 `/coach/plan/new` | 대회 고르기(등록된 B/C 또는 새 대회) + 계획 조건 | `goal_service.create_goal_with_race`: 대회 행 생성·승격(A) → `add_goal(race_id=…)` |
| 목표 수정(계획 상세 `/coach/plan/[id]`) | 계획 조건, "대회 바꾸기" | 대회 사실 변경은 캘린더 시트를 같은 컴포넌트로 연다(별도 폼 없음) |
| v1·CLI(`views_training_wizard`, `views_training_goal_crud`, `plan.py`) | 기존과 같음 | `add_goal(race_date=…)` 호환 래퍼가 대회 행을 만들고 연결. `update_goal(race_date|distance_km)`은 `race_calendar_service.update`로 위임 |
- 대회 사실을 고치는 UI는 `RaceEntrySheet` 하나다. 목표 화면은 그 시트를 재사용하고, 날짜·거리 변경 뒤 확인 단계는 RC-13.
- A 대회 날짜·거리 변경은 §2.6-3의 재계획 경로, B/C는 행 단위 경로로 간다.

### 2.4 상태 머신 (대회 status × adapt_choice × plan_state → 신호 사용)
| status | adapt_choice | plan_state | 보호 기간 상향 차단 | 회복 하향 트리거 | race_plan 신호·AI 맥락 | 목록 칩 |
|---|---|---|---|---|---|---|
| planned | unasked | none | 테이퍼 O | (대회 전) | O | 질문 대기 |
| planned | later | none | 테이퍼 O | (대회 전) | O | 나중에 |
| planned | adapt | applied | 테이퍼 O | (대회 전) | O | 반영됨 |
| planned | adapt | stale | 테이퍼 O(새 값) | (대회 전) | O | 변경 후 미반영 |
| planned | no_adapt | none | **X** | **X** | **X**(RC-4b) | 조정 안 함 |
| done | unasked·later | none | 회복 O | **O**(RC-6, Q-day 있을 때) | O | 결과 연결 |
| done | adapt | applied·stale | 회복 O | X(이중 감량 방지) | O | 결과 연결 |
| done | no_adapt | none | X | X | X | 결과 연결 |
| cancelled | 무관 | none | X | X | X | 취소됨 |
| planned/done, A | adapt 고정 | applied | O | X | O | 목표 대회 |
- 테이퍼 기간 하향은 어떤 상태에서도 보조 근거로만 쓴다(§3.4). `no_adapt`는 캘린더 표시만 남고 조정 신호에는 전혀 들어가지 않는다.
- **전이:** 등록 → unasked. 질문 응답 → adapt(일괄 적용 성공 시 applied) / later / no_adapt. 시트를 닫으면 unasked 유지. later·no_adapt는 목록 칩에서 다시 고를 수 있다. applied 대회의 날짜·거리·우선순위·보호 기간 수정 → stale(no_adapt·unasked·later는 질문 없이 값만 바뀜). 일괄 되돌리기 → plan_state none, adapt_choice later. 날짜 경과 → done(RC-8). 삭제 → cancelled, applied였으면 같은 트랜잭션에서 반영분 일괄 되돌리기(RC-9). A는 질문 없이 adapt·applied(계획이 목표에서 생성).
- 적용 실패(409 등)면 adapt_choice·plan_state를 바꾸지 않는다.

### 2.5 보호 기간 (RC-5 a)
- 기본: 테이퍼 5·10K 3일 / 하프 7일 / 풀 14일, 회복 2 / 4 / 7일. B/C는 절반(반올림 규칙 RC-16). `taper_days·recovery_days`가 있으면 그 값을 그대로 쓴다(절반 미적용).
- 상세 시트 Level 2 "왜?"에 거리 → 기본 일수 → B/C 보정 → 덮어쓰기 여부를 보여 준다.

### 2.6 계획 연동 흐름
1. **저장 → 영향 계산(쓰기 없음):** 순수 함수 `race_impact(rows, race, windows)`. `b_race_week()`를 일반화(테이퍼·회복 일수 인자)해 재사용한다. race·rest·완료·매칭된 행은 건드리지 않는다.
2. **B/C 대회 일괄 적용(RC-7 a):** `RacePlanPrompt` 미리보기(날짜별 전→후, 근거 칩) 한 번에 수락 → 행 단위 `plan_adjustments`를 한 묶음(`batch_id`)으로 적용, 묶음 단위로 되돌린다. `source='race'`는 v37 재생성에 포함하도록 system-architect와 협의한다.
3. **A 대회:** 날짜·거리 변경 시 `race_calendar` 갱신 + 캐시 → `plan_replan_service.preview → apply → undo`(다음 월요일 시작, 마지막 1건 되돌리기 규칙 유지). 대회 주 안의 변경은 2번 경로로 대체한다.
4. **보호 기간 신호:** §2.4 표대로. applied 대회는 `race_plan` 단독 하향 트리거를 만들지 않는다.
5. **완료(RC-8 b):** `race_date < 오늘`인 planned 행은 조회·동기화 시점에 `done`으로 바꾸고(지연 전이, 별도 스케줄러 없음) 레이스 허브 "결과 기록" 카드에 `race_result_service.candidates`(같은 날짜, 거리 ±10%)를 띄운다. 확정하면 `race_result_id` 연결. A 대회 done 시 목표 처리는 RC-17.
6. **AI 코칭 예시:** "다음 주 일요일 10K(B)가 있어서 목요일 템포는 가볍게 바꿔 뒀어요. (race_plan D-10, 테이퍼 기간)" → "왜?"는 상세 Level 2.

### 2.7 화면 (모바일 375px, h1(PageHead) 1개, 44px 탭 영역, 오버레이 `use:modal`)
- **진입:** 레이스 허브 "대회 캘린더" 카드(예: "다음 대회 · 춘천 10K(B) · D-15 · 반영됨"), 계획 상세 주간 목록의 A/B/C 배지, 목표 생성의 "등록된 대회에서 고르기".
- **목록 `/today/race/calendar`(h1 "대회 캘린더"):** 다가오는/지난 두 구역, 행 = 배지·이름·D-day·거리·목표 한 줄·§2.4 칩. 우상단 "대회 추가".
- **등록·수정 시트:** 필수 4개(날짜·이름·거리 칩·우선순위 세그먼트) 위, 나머지(목표 유형·값, 보호 기간 덮어쓰기, 메모)는 "더 설정"에 접는다. A를 고르면 "목표 대회로 지정하면 훈련 계획을 이 대회에 맞춰 새로 만들어요" 안내 후 목표 생성으로 이동. 저장 실패는 시트 안 문구 + 입력 유지.
- **계획 반영 질문:** 제목 "이 대회에 맞춰 계획을 조정할까요?", 버튼 "조정할게요 / 나중에 / 조정 안 함"(RC-10, 최종 문구는 구현 중 확인). 수정 시 "변경 영향" 모드(기존 반영분 되돌리기 + 새 제안 diff).
- **삭제:** 확인 다이얼로그에 되돌릴 조정 N건·연결 실적 유지 안내 → cancelled(RC-9). A 삭제는 목표 취소를 함께 묻는다(목표 화면과 같은 확인).
- **빈 상태:** "등록된 대회가 없어요. 목표 외에 나갈 대회를 추가하면 그 앞뒤 훈련을 맞춰 드려요" + 추가 버튼. **오류:** 공통 `ErrorState`, 409(A 중복·같은 날 같은 거리·`REPLAN_LOCKED`·`RACE_WEEK`)는 코드별 문구.

### 2.8 대안 (기록용)
- B: 모든 대회를 재계획 엔진 제약으로 처리 — 2주 안 대회 반영 불가, 엔진 변경 큼. 채택 안 함.
- RC-1 (a) 미러·(b) B/C만 저장 — 사용자가 (c)를 골라 채택 안 함.

## 3. 변경 파일 표 (RC-1 c 반영 재산정, 모두 300줄 이하)
| 파일 | 구분 | 내용 | 줄 |
|---|---|---|---|
| `src/db_schema_v38.py` | 신규(설계 중) | race_calendar 생성 + 인덱스 2개(context_episodes와 같은 파일) | +40 |
| `src/db_schema_v39.py` | 신규 | goals.race_id 추가, 백필, `ux_goals_race`, 캐시 재동기화(멱등) | ~110 |
| `src/db_setup.py` | 수정 | SCHEMA_VERSION 39, ensure_v38·v39 호출 | +6 |
| `src/training/goals.py` | 수정 | `_COLS`에 race_id, `add_goal(race_id=…)` + race_date 호환 래퍼, `update_goal` 대회 필드 위임 | 188→~225 |
| `src/services/race_calendar_service.py` | 신규 | add/list/get/update/cancel, 지연 done 전이, 중복·A 검사 | ~190 |
| `src/services/race_goal_sync.py` | 신규 | 캐시 쓰기, A 승격·교체, 불변식 검사 함수 | ~120 |
| `src/services/goal_service.py` | 신규 | `create_goal_with_race`(목표+대회 한 트랜잭션) | ~80 |
| `src/services/plan_template_service.py` | 수정 | add_goal 호출에 race_id 전달(선택한 대회) | 202→~215 |
| `src/services/race_plan_link.py` | 신규 | race_impact 호출, 묶음 적용·되돌리기, 상태 전이 | ~160 |
| `src/training/constraints.py` | 수정 | `b_race_week` 일수 인자 일반화(시그니처 호환) | +20 |
| `src/services/adjustment_signals_race.py` | 수정 | race_calendar·§2.4 표 기반 신호 | +40 |
| `src/api/routes_race_calendar.py` | 신규 | CRUD, `/<id>/impact`, `/<id>/plan`(adapt/later/no_adapt/undo). v1 밖 | ~150 |
| 목표 생성 API 핸들러(`src/api/routes_plan*.py`, 구현 시 grep 확정) | 수정 | race_id 입력 수용 | +20 |
| `scripts/check_data_consistency.py` | 수정 | 불변식 3·4 검사 2건 | +30 |
| `scripts/race_backfill_dry_run.py` | 신규 | DB 사본에 v39 실행 후 리포트(쓰기는 사본만) | ~90 |
| `frontend/src/routes/today/race/calendar/+page.svelte`·`+page.ts` | 신규 | 목록·빈·오류 상태 | ~150 |
| `frontend/src/lib/components/RaceEntrySheet.svelte`·`RacePlanPrompt.svelte`·`RaceDetailSheet.svelte` | 신규 | 시트 3종 | ~180/~130/~140 |
| `frontend/src/routes/coach/plan/new/+page.svelte`, `lib/planPrefill.ts`, `lib/api/plan.ts`, `lib/types/index.ts` | 수정 | 대회 고르기, race_id 전달 | +40/+15/+10/+10 |
| `frontend/src/routes/today/race/+page.svelte`, `coach/plan/[id]/+page.svelte` | 수정 | 캘린더 카드, 배지, "대회 바꾸기" | +20/+25 |
| tests: `test_db_schema_v39.py`, `test_race_calendar_service.py`, `test_race_goal_sync.py`, `test_goal_service.py`, `test_race_plan_link.py`, `test_routes_race_calendar.py`, `test_goals.py`(+), `test_plan_template_service.py`(+), `test_constraints.py`(+), `test_db_schema_v32.py`(회귀 유지); 프론트 시트 3종 | 신규·수정 | 함수마다 1개 이상 | ~75개 |
- 바꾸지 않음: `goals.race_date`를 읽는 40여 파일(캐시 유지), `race_results`, `/today/race/races`, v1 라우트.

## 4. 스키마 순서·마이그레이션·단계·검증
**버전 순서(확정 제안):** v37 `plan_adjustments` 재생성(`source`에 `race` 포함) → v38 `context_episodes`·`race_calendar` 생성(가산만) → **v39 goals.race_id + 백필**. goals 참조를 v38에 넣지 않는 이유: v38은 다른 번들과 공유하는 가산 단계라 실패·롤백이 쉬워야 하고, 백필은 race_calendar 최종 컬럼에 의존하며 실패 시 v38까지 묶여 막히면 안 된다.

**v39 백필 절차(한 트랜잭션, 멱등):**
1. `goals.race_id` 컬럼이 없으면 추가.
2. `race_date IS NOT NULL AND race_id IS NULL`인 목표를 id 순으로: 같은 날짜·거리(±0.01km)의 cancelled 아닌 대회가 있으면 연결, 없으면 생성(`origin='goal'`, name=goal.name, goal_type=target_time_sec 유무로 time/finish, goal_value=target_time_sec). 활성 목표 → `priority='A'`, adapt_choice `adapt`, plan_state(그 목표의 planned_workouts가 있으면 `applied`, 없으면 `none`), status planned. 비활성 목표 범위·우선순위는 RC-12.
3. race_date 없는 목표는 RC-11 결정대로 처리(결정 전 기본 구현은 race_id NULL 유지).
4. 이미 연결된 목표의 캐시가 대회 값과 다르면 **goals 값을 대회에 반영**하고 로그(롤백 후 구 코드가 goals만 고친 경우의 재동기화).
5. `ux_goals_race` 생성. 불변식 3 위반이 있으면 예외 → 트랜잭션 롤백, user_version 미갱신.

**롤백·호환:**
- 코드 롤백(v36~38 코드로 되돌림): 스키마는 앞으로만 간다. 구 코드는 user_version ≥ 자기 버전이면 마이그레이션을 건너뛰고, race_id·race_calendar를 모른 채 캐시 컬럼(race_date 등)을 그대로 읽고 쓴다 → 동작한다. 재업그레이드 시 v39 4단계가 차이를 흡수한다(ensure_v39는 user_version과 무관하게 재동기화 함수를 한 번 더 부를 수 있게 분리).
- 데이터 롤백: 마이그레이션 전 백업 방식·중단 복구는 RC-14.
- v1: 의존 경로는 `add_goal`/`update_goal` 래퍼로 계속 동작한다. v1 제거 후 캐시 컬럼 제거 여부는 범위 밖(§6).

**단계:**
1. **S0** RC-11~17 결정, system-architect와 `source='race'`·API 형태·v37~39 순서 확정.
2. **S1 스키마** v38·v39, 검증: 빈 DB/DB **사본** 마이그레이션, 재실행 멱등, `race_backfill_dry_run.py` 리포트(목표 수/연결/재사용/생성/race_date 없음/캐시 차이), 불변식 1~4 위반 0, `test_db_schema_v32.py` 그대로 통과.
3. **S2 서비스·목표 경로** `race_calendar_service`·`race_goal_sync`·`goal_service`·goals.py 래퍼. 검증: **활성 목표 유니크 회귀**(add_goal 2회 → 활성 1건, 새 목표 대회만 A, 이전 A는 RC-15대로), 캘린더에서 A 날짜 수정 → goals 캐시 갱신, `update_goal(race_date)` → race_calendar 갱신(양방향 왕복), v1 마법사·CLI 경로 회귀, plan_template_service 생성 경로.
4. **S3 영향·연동** `race_impact`·`race_plan_link`. 검증: 보호 행 불변, 묶음 적용 → 되돌리기 왕복, stale → 재반영, 삭제 시 되돌리기, §2.4 표 행별 신호 테스트(no_adapt 무신호, later·unasked done 하향 허용, applied 하향 없음).
5. **S4 API** 400/404/409 매핑. **S5 화면** 375px 브라우저: 등록 → 질문 → 일괄 적용 → 되돌리기, 목표 생성에서 B 대회 고르기 → A 승격, 계획 상세 "대회 바꾸기", 삭제 미리보기, 데모 모드, h1·44px·Esc 포커스 복귀.
6. `pytest tests/` 전체, `check_docs.py`, `check_data_consistency.py`, BACKLOG·decisions 기록.

## 5. 결정
### 결정됨(2026-10-11)
- **RC-1** (c) race_calendar 원천, goals가 `race_id`로 참조(§2.1~2.3, §4).
- **RC-2** (a) 우선순위 A/B/C 필수. **RC-3** (a) 완주/목표 기록/PB.
- **RC-4** (b) 항상 질문, 기본값 없음. **RC-4b** '조정 안 함' 대회는 보호 기간 상향 차단 포함 대회 신호를 전혀 쓰지 않음.
- **RC-5** (a) 제안값 기본 + 대회별 덮어쓰기(절반 반올림 규칙은 RC-16). **RC-6** (a) 회복 하향 트리거는 미반영 대회 중 '미응답/나중에'에만(§2.4).
- **RC-7** (a) 미리보기 일괄 적용 + 일괄 되돌리기. **RC-8** (b) 날짜 경과 시 자동 done + 결과 연결 안내.
- **RC-9** (a) 소프트 삭제(cancelled), 이력·실적 유지, 반영분은 삭제 시 되돌리기. **RC-10** 설계서 문구로 진행, 최종 문구는 구현 중 확인.

### 결정 필요(신규)
- **RC-11 race_date 없는 목표(백필·이후 생성):** (a) race_id NULL 허용 — "대회 없는 목표" 유지(단순, 불변식 3이 조건부가 됨) / (b) 활성 목표면 날짜 입력 배너로 유도, 입력 시 대회 생성(데이터 깔끔, 사용자 행동 필요) / (c) 계획 마지막 주 일요일로 가상 대회 생성(자동, 가짜 대회가 목록에 보임).
- **RC-12 비활성 목표 백필 범위:** (a) 활성만(최소 변경, 과거 목표는 캐시만) / (b) 전부 — completed→done, cancelled→cancelled, 우선순위 A로 기록(이력 일관, 지난 대회 구역이 채워짐) / (c) completed만 done으로(취소 목표 소음 제거).
- **RC-13 목표 화면에서 대회 날짜·거리 변경 시 확인:** (a) 저장 전 재계획 미리보기 필수(안전, 단계 1개 추가) / (b) 저장 후 캘린더와 같은 질문 시트(일관, 잘못 저장 후 되돌리기 필요) / (c) 날짜만 바뀌고 같은 주면 질문 생략.
- **RC-14 마이그레이션 중단 복구:** (a) v39 직전 DB 파일 자동 백업 + 단일 트랜잭션(복구 확실, 디스크 사용) / (b) 단일 트랜잭션만(SQLite 원자성 의존, 단순) / (c) 단계별 체크포인트 + 재실행 멱등(긴 DB에 유리, 구현 복잡).
- **RC-15 A 교체(새 목표 생성·다른 대회 A 지정) 시 이전 A 대회:** (a) cancelled(현재 add_goal의 목표 취소와 같은 의미) / (b) B로 강등 + adapt_choice unasked(대회는 남고 질문 대기) / (c) 교체 시트에서 매번 묻기.
- **RC-16 B/C 절반 반올림:** (a) 올림(테이퍼 2/4/7, 회복 1/2/4) / (b) 내림(1/3/7, 1/2/3) / (c) B는 올림, C는 내림(B와 C 차이가 생김, 규칙이 둘). 참고: 이 기본값에서는 반올림 결과가 (a)와 같다.
- **RC-17 A 대회 자동 done 시 목표:** (a) 목표도 자동 completed(활성 목표 없음 상태가 됨) / (b) 목표는 활성 유지, "결과 기록·다음 목표" 카드로 사용자가 완료(현재 동작과 같음) / (c) N일 뒤 자동 completed.

## 6. 범위 밖 메모
- 외부 캘린더 가져오기(`origin='import'`), CalDAV·Garmin에 푸시된 race 행 정리(A6 D5와 같은 문제).
- 생성기가 race_calendar를 직접 제약으로 받는 방식, 다중 A 시즌 계획(계획 엔진 영역).
- v1 제거 후 goals 캐시 컬럼(race_date·distance_km·target_time_sec) 제거와 읽기 경로 40여 곳 전환.
- `/today/race/races`와 캘린더 지난 대회 구역 통합(IA 정리 때). 대회 데이터 AI 전송 동의는 NEW-12와 함께.
