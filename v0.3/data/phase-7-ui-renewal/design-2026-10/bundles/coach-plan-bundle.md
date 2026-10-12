# 설계: 훈련 계획 묶음 (P-01~P-25)

- 대상: `ux-review-2026-10/05-coach-plan.md` P-01~P-25 · 작성일 2026-10-11 · 상태: 결정 확정(2026-10-11, PLN-1~42·V1-13), 구현 전 — 실데이터 확인·열린 질문 남음(§5, §8)
- 변경 이력: 2026-10-11 원인 검증 반영 — P-06(매칭 비율 상한·판정 순서·_effective 순위), P-08(v1 폴백·운영 경로 휴식 보장 부재) 원인 확정 및 실데이터 확인 항목 추가
- 변경 이력: 2026-10-11 1~3차 동기화 — PLN-1~17 반영(지정 요일 `user_training_prefs.workout_weekdays_mask`, workout mask 우선, mask NULL 시 생성 전 요일 입력 요구, 최소 휴식일 하한 없음, 휴식 0~1일 저장 전 1회 안내). v1 화면·경로 범위 제외
- 변경 이력: 2026-10-11 4~5차 동기화 — V1-1·V1-2(v1 일몰 = UI·라우트 일몰, 공유 파일·함수 유지). 'v1 템플릿/v1 폴백/v1 목표'(plan_weeks NULL·rules_version<2 데이터·알고리즘 용어)는 유지
- 변경 이력: 2026-10-11 6~8차 동기화 — PLN-18(백테스트 입력 mask), PLN-19·20(planner 행 한정 goal_id CHECK), PLN-22·25(이력 시나리오 mask 직접 명시), PLN-23·24(기존 플랜 삭제, 이행 코드 미작성), PLN-26(v40 단일 마이그레이션), PLN-27 반영
- 변경 이력: 2026-10-12 9차 동기화 — PLN-31 최종 E안(D안 철회) 기준으로 전면 정합. PLN-19·20·26 복원(planner 행 한정 CHECK, v40 단일 = ADD COLUMN+CHECK), PLN-21 소멸, PLN-23·24·28·29·30·42(레거시 6종을 사용자가 v40 이전에 DB 에서 직접 삭제 — goals 는 active·cancelled 만, §2.4), PLN-32(부분 첫 주 볼륨 일수 비례 축소 + 그 주 러닝 기록 참고), PLN-33(겹칠 수 있는 경로만 goal_id 필터), PLN-34(수락 조정 표시 컬럼·동기화 규칙), PLN-35(옛 목표 복구 고려 안 함), PLN-36(생성 시작 = 오늘), PLN-37(undo 활성 목표 한정 + goal_id 기입), PLN-38(goal_id 누락 방지 가드), PLN-39(replan 사용자 경로 400), PLN-40(배너·재생성 제안 없음), PLN-41(고아 outcomes 점유 현행). §8 재작성
- 범위: 플랜 생성 파이프라인(`src/training/planner*`), 플랜 소유·교체(`goals`, `plan_replace`), 읽기 모델(`plan_service`, `week_compliance`, `routes_plan`), v2 `frontend/src/routes/coach/plan/*`. v1 화면·라우트는 일몰 예정(V1-1·V1-2, UI·라우트 일몰)이라 범위 밖. 공유 함수(`generate_weekly_plan`, `match_week_activities` 등)는 유지 대상
- 참조만: 입력·Origin 검증 → `server-input-origin-validation.md`, 오류·재시도 → `error-retry-common.md`, 접근성 → 별도 접근성 설계

## 1. 근본 원인

### R1. 주간 플랜이 여러 단계에서 바뀌는데 파생 필드는 첫 단계에서 한 번만 만든다 (P-01, P-02, P-08)
- `planner.generate_weekly_plan` 이 `description(wtype, dist, day)`·`structure` 를 v1 거리로 먼저 채운다. 이후 `planner_v2.apply_v2`(`_shakeout` L72·74, 휴식 전환 L91·111, 최소거리 L116), `planner_v2_long._shrink`/`rebalance`/`plan_long_week`, `apply_ladder` 가 `distance_km`·`workout_type` 을 바꾸지만 description 은 일부 경로(`trim_run_days`, `plan_long_week` 강등)에서만 다시 만든다.
- 결과: 거리 컬럼과 설명이 어긋나고(P-01 10.0 vs "16.1km"), rest 로 바뀐 행에 "3.7km 이지런" 이 남는다(P-02). `_finalize_rows` 는 rest 행의 페이스·구조만 비우고 설명은 건드리지 않는다.
- 주간 불변식(러닝 일수 상한, rest ↔ 거리 0, 설명 거리 = 컬럼 거리)을 검사하는 곳이 없다. P-08 재현 확정: v1 템플릿(`planner.py:124-128,162-173`)은 `rest_weekdays_mask`(기본 0, `planner_config.py:84`) 외 모든 요일을 러닝으로 채워 7주 내내 주 7회가 된다. v2 분기(`planner.py:210-213`)는 `goal and target and effective_rules_version>=2`일 때만 적용되는데, `plan_weeks`가 NULL이면 target이 None(`planner_rules.py:48-49`)이라 rules_version=2여도 v1으로 폴백한다(재현: rv2+plan_weeks NULL → 7회, rv2+plan_weeks=7 → 주 2~3회). 휴식 최소를 보장하는 G1 게이트(`plan_gates.py:71`)는 `plan_backtest` 전용이라 운영 생성 경로에는 휴식 보장이 없다. goal 1이 어느 경로로 생성됐는지는 실데이터 확인 필요(§5).

### R2. planned_workouts 에 플랜 소유자가 없다 (P-03, P-11, P-15, P-23, P-09 일부)
- `planned_workouts` 는 날짜 키로만 존재하고 `goal_id` 가 없다. 플랜 = "활성 목표 + 그 날짜 범위의 행" 이라는 암묵 규칙이다.
- 그래서 새 플랜 생성은 `add_goal` 이 기존 active 를 무조건 `cancelled` 로 바꾸고(`goals.py` L102), `replace_range(today~9999)` 가 이력 없는 미래 행을 지운다(P-03, `plan_template_service.py:183`). 확인 단계·복구 스냅샷이 없다. `replace_range` 는 snapshot 을 반환하지만 `create_plan_from_template` 이 버린다.
- 같은 이유로 `get_active_plan(goal_id)` 는 goal_id 와 무관하게 "오늘 주의 행" 을 돌려주고, 취소된 플랜 세션도 현재 행으로 보인다(P-23). 메모는 `user_inputs(input_date, 'session_note')` 날짜 키라 플랜 간 공유된다(P-15).
- 시작 주는 `today - weekday()`(`plan_template_service.py:191`) 또는 `plan_start_monday`(이번 주 월요일이 될 수 있음)로 정해져 일요일 생성 시 지난 6일이 1주차에 들어간다(P-11). 이 지난 날짜에 `save_weekly_plan`(`planner.py:231`)이 같은 날짜 planner 행을 보호 여부와 무관하게 지우고 다시 넣는다(PLN-36 문제 제기).

### R3. 읽기 모델이 "이번 주" 하나뿐이고 매칭은 동기화 시점에만 돈다 (P-06, P-07, P-08 검증 불가, P-09)
- `plan_service.get_active_plan` 은 `_current_week_start()` 한 주만 조회한다. 전체 주차 볼륨·단계·테이퍼를 돌려주는 API 가 없다(P-07). 사용자가 P-08 을 검증할 화면도 없다.
- `match_week_activities`는 `bg_sync` 완료 후(v2 동기화 포함, 최근 4주)·앱 시작에서 호출된다. v2 `POST /coach/plan`은 생성 후 재매칭하지 않는다. P-06 10/8·10/9는 거리 비율 상한(`match_select.py:10,40-41`, 2.5배·1.83배 > 1.6)으로 탈락했다(합성 재현으로 확정). 외부 계획 행이 먼저 정렬·매칭(`matcher.py:51`)되어도 결과는 같았다.
- `outcome_label`은 이지 페이스 판정을 볼륨보다 먼저 한다(`week_compliance.py:69-72`). 10/6·10/7의 10km·6km가 "강도 어긋남"이 되고(확정), 사유·실제 거리/페이스는 응답에 없다. `_effective` 순위(48-52)는 미매칭 외부 행을 매칭된 planner 행보다 우선해 missed를 만든다(결함 재현됨, 이번 데이터 해당 여부 불명, §5). 헤더는 누적(`_plan_compliance`), 목록은 주간(`week_compliance.compute`)이라 기준이 다르다(P-09).

## 2. 설계안 (확정: A안 PLN-9, 소유권 방식 E안 PLN-31)

### 2.1 R1 — 마지막 단계에서 한 번 파생 + 불변식 자동 교정
- 신규 `src/training/plan_finalize.py`: `finalize_week(rows, *, run_weekdays) -> list[dict]` 가 모든 변형이 끝난 뒤 `description`·`structure` 를 (type, distance, date) 에서 다시 만든다. race·cold-start 노트처럼 의도된 설명은 `_desc_locked` 플래그로 보존.
- 같은 모듈 `week_violations(rows, run_weekdays) -> list[str]`: rest↔거리, 설명 km = 컬럼 km(±0.1), 러닝 요일 ⊆ 지정 요일, 롱런 ≤ 주간의 일정 비율. 위반은 **자동 교정 + 로그**(PLN-4): rest 행 거리 0·설명 재생성, 지정 요일 밖 러닝 행 → rest, 설명 불일치 → 재생성. 생성·저장은 막지 않으며 테스트에서는 교정 전 위반 0 을 assert.
- `generate_weekly_plan` 마지막 줄을 `finalize_week(apply_race_week(...))` 로 바꾼다. `planner.py` 가 300줄이라 `save_weekly_plan`·prefs 함수(L218~)를 `planner_store.py` 로 옮긴다(재수출 유지).
- P-08(PLN-3): 원칙은 **사용자가 지정한 운동 요일 준수**. 지정 요일은 **`user_training_prefs.workout_weekdays_mask INTEGER NULL` 신규 컬럼**(NULL=미지정, 기존 `rest_weekdays_mask` 와 별개)에 저장해 v2·`finalize_week` 가 공통으로 읽는다. mask 가 NULL 이면 계획 생성 시 요일 선택을 요구한다(`POST /coach/plan` 에 `run_weekdays` 없으면 400, 받은 값은 mask 에 저장; 프런트 생성 폼에 요일 선택 단계). 구현은 (c) **신규 목표는 v2 규칙으로 일괄 전환** — `add_goal` 이 rules_version=2 와 v2 진입 조건(target 산출에 필요한 `plan_weeks`)을 항상 채워 v1 폴백 경로에 들어가지 않게 한다.
- 두 mask 우선순위(PLN-11): `workout_weekdays_mask` 와 `rest_weekdays_mask` 가 같은 요일에서 모순되면 **workout 우선** — 지정 운동 요일은 rest mask 와 무관하게 러닝 요일로 쓴다. 저장 시 모순을 거부하지 않는다(입력 검증 없음). `run_weekdays` 산출을 `planner_store.resolve_run_weekdays(prefs)` 한 곳에 두어 v2·`finalize_week`·`week_violations` 가 같은 값을 쓴다.
- 최소 휴식일(PLN-13): **하한 없이 사용자 지정 존중**. 7요일 모두 지정해도 생성·`week_violations` 가 막거나 교정하지 않으며, G1 게이트(`plan_gates.py:71`)는 운영 경로에 재사용하지 않는다(`plan_backtest` 전용 유지). 휴식 0~1일 지정 시(PLN-14) **저장 전 1회 안내** — 요일 선택 단계에서 지정 요일이 6~7개면 저장(생성 요청) 전에 부상 위험 안내를 한 번 보여 주고, 확인 시 그대로 저장한다(차단 아님). 판정은 프런트 순수 함수(지정 요일 수 ≥ 6)로 두고 서버 계약은 바꾸지 않는다. 문구는 구현 단계에서 후보 제시.
- mask NULL 인 생성 경로(PLN-12): **생성 전 요일 입력 요구**를 v2 `POST /coach/plan` 뿐 아니라 `generate_weekly_plan` 을 부르는 모든 경로에 적용한다. 확인 지점은 `planner_store.resolve_run_weekdays` 한 곳 — mask NULL 이면 `WeekdaysRequired` 를 올린다(요일 무시 폴백·과거 요일 재사용 없음). 호출 경로별 처리 수준:
  - 사용자 요청 경로: v2 `POST /coach/plan`, **사용자가 누른 재계획 `plan_replan_service.py:128`(PLN-39 a)**, CLI `src/plan.py:162`. 생성하지 않고 요일 입력을 요구한다 — v2 생성·재계획 API 는 `WeekdaysRequired` → 400(조용한 skip 없음), CLI 는 안내 메시지.
  - v1 라우트(`/training/wizard/complete`·`/training/generate`): 요일 없이 `generate_weekly_plan` 을 불러 mask NULL 이면 생성이 막힌다. 대응하지 않는다(V1-13, v1 손상 허용).
  - 자동 경로(`weekly_adapt_job.run`·`rematch.py:82`): `WeekdaysRequired` 를 잡아 해당 실행에서 생성·저장하지 않고 사유를 로그에 남긴다(`weekly_adapt_job` 은 기존 rules_version<2 분기처럼 0 반환). 신규 생성은 mask 를 먼저 저장하므로 정상 흐름에서는 도달하지 않는 방어 분기다.
  - 요일 입력 요구는 **신규 생성(및 사용자 재계획) 때만**이다(PLN-40 결정 문구 — 선택지 표기는 (a)이나 내용은 '신규 생성 때만 요구, 배너·재생성 제안 없음'). 코치 화면 배너·기존 목표 재생성 제안·'요일 입력 전까지 갱신 안 됨' 표시·주간 적응 정지 안내는 두지 않는다 — 옛 active 목표는 §2.4 로 삭제되어 'active goal + mask NULL' 상태가 생기지 않는다(PLN-40·PLN-27).
  - 백테스트 경로(PLN-18 b): `plan_backtest.py:70-74`·`plan_backtest_replan.py:22-30` 은 현재 `rest_weekdays_mask=rest_mask(scn.days)` 만 쓰고 `generate_weekly_plan` 을 부르므로 mask NULL 이면 `WeekdaysRequired` 로 깨진다. **백테스트 입력(`Scenario`)에 요일 mask 를 지정**한다 — `Scenario.workout_weekdays_mask: int` 필드를 추가하고, 시나리오 실행 시 `upsert_user_training_prefs(conn, workout_weekdays_mask=scn.workout_weekdays_mask, rest_weekdays_mask=…)` 로 메모리 DB prefs 에 넣은 뒤 생성한다(운영 `resolve_run_weekdays` 경로를 그대로 탄다, 백테스트 전용 우회 없음). 격자 시나리오는 격자 정의의 `days` 와 `DAY_ORDER`(`plan_backtest.py:28`)로 만든 mask 를 **입력값으로 명시**해 넣고, `plan_backtest_replan` 의 `Scenario(**scn.__dict__)` 복제(`:53·81`)는 필드를 그대로 이어받는다. mask 미지정 시나리오는 생성 전에 구성 오류로 거부한다(`WeekdaysRequired` 를 결과 '실패'로 세지 않음). **이력 시나리오(PLN-22 b·PLN-25 b)**: `history_scenarios`(`plan_backtest.py:131-150`, `days=0`)도 같은 `Scenario.workout_weekdays_mask` 필드로 mask 를 필수 입력받고, 없으면 같은 구성 오류로 거부(전체 요일·mask 무시 폴백 없음). mask 는 **시나리오 입력에 직접 명시(호출자 책임, PLN-25)** — `user_training_prefs`(단일 행, 시점별 이력 없음)의 현재 값 재사용이나 활동 요일 분포 추정은 하지 않으며, `history_scenarios` 는 호출자가 넘긴 값을 시나리오에 싣기만 한다(인자 형태는 구현 시 확정). G1 게이트(`plan_gates.py:71`)는 백테스트 전용으로 유지(PLN-13).
- 테이퍼 볼륨·마지막 롱런 시점, 컨디션 기반 변경(adjuster·weekly_adapt, ADR-035 확인 후)은 이 설계 범위 밖.

### 2.2 R2 — 플랜 소유권(E안) + 교체 확인 + 복구
- **E안(PLN-31 재결정, PLN-19·20·26 복원):** `planned_workouts.goal_id INTEGER` 추가 + **planner 행 한정 CHECK `(source <> 'planner' OR goal_id IS NOT NULL)`**. 외부 계획 행(`source`=`'garmin'`·`'intervals'`, `plan_ingest.store_planned` 이 `source=source_system` 으로 기입)과 v1 `manual`·`imported` 행은 goal_id NULL 유지. D안(NULL 허용 컬럼만 추가·기존 데이터 보존)은 철회됐다.
- **전제 — 레거시 삭제 선행(PLN-23·24·28·42):** v40 은 '`source='planner'` 행이 0 인 DB' 를 전제한다. 레거시 6종은 **사용자가 v40 적용 전에 DB 에서 직접 삭제**한다(§2.4). goal_id 백필·고아/외부/v1 행 귀속·옛 스냅샷 보충 등 마이그레이션·미티게이션 코드는 작성하지 않는다(PLN-23). 옛 목표의 취소 플랜 복구는 설계에서 고려하지 않는다(PLN-35 c — PLN-1 복구는 신규 목표부터).
- **마이그레이션 버전(PLN-26 a 복원):** 현재 `SCHEMA_VERSION = 36`(`db_setup.py:32`), v37(`plan_adjustments` 재생성, `adjustment-signals.md`)·v38(가산 테이블, `adjustment-new-signals.md`·`race-calendar.md`)·v39(`goals.race_id` 백필, `race-calendar.md`)이 다른 번들에 배정돼 있으므로 이 번들은 그 뒤 **v40 하나**를 쓴다(2026-10-12 grep: 설계 폴더에서 v40 을 쓰는 다른 문서 없음). v39 와 데이터 의존은 없다(`race_id` 를 읽지 않음). 순서는 번호 순차성 때문이며, v39 가 전진 전용(`race-calendar.md` §4)이므로 롤백은 v39 이후 상태로만 돌아간다.
- **v40 내용(단일 트랜잭션, 테이블 재생성·백필 없음):**
  1. `ALTER TABLE planned_workouts ADD COLUMN goal_id INTEGER CHECK (source <> 'planner' OR goal_id IS NOT NULL)` — SQLite 는 CHECK 가 붙은 ADD COLUMN 시 기존 행을 검사하므로 planner 행이 남아 있으면 `CHECK constraint failed` 로 실패 → 롤백(로컬 SQLite 3.45.1 로 확인: planner 행 없으면 추가 성공·이후 goal_id NULL planner INSERT 거부, planner 행 있으면 추가 실패). 이것이 §2.4 삭제 누락의 검출 지점이다(planner 행 외 나머지 5종 삭제 여부는 v40 이 검사하지 않음).
  2. `ALTER TABLE planned_workouts ADD COLUMN` 수락 조정 표시 컬럼(PLN-34 b, 이름 가칭 `adj_accepted INTEGER NOT NULL DEFAULT 0 CHECK (adj_accepted IN (0,1))`) — 동기화 규칙은 아래 별도 항목.
  3. `ALTER TABLE user_training_prefs ADD COLUMN workout_weekdays_mask INTEGER`(NULL 기본).
  4. goal_id 워터마크(PLN-38): 적용 시점 `planned_workouts` max(id) 기록. 저장 위치는 구현 시 확정(현 DB 에 메타 키-값 테이블 없음, grep 2026-10-12).
  5. (조건부) BEFORE INSERT 트리거(PLN-38) — CHECK 와 중복 여부 확인 전까지 보류, §8-13.
  - 공통: `PRAGMA integrity_check` 선행, 멱등(컬럼이 있으면 skip), 역마이그레이션 = 백업 복원. **운영 SQLite 버전은 구현 첫 단계에서 확인**(PLN-26).
- **PLN-21 소멸:** v41 은 없고(PLN-26), v1 `manual`·`imported` 행은 CHECK 대상이 아니어서 v1 라우트 일몰과 마이그레이션의 선후 제약은 없다.
- **planner 행 INSERT 경로(grep 2026-10-12, `INTO planned_workouts`):** CHECK 이후 planner 행은 goal_id 를 채워야 한다. planner INSERT 는 모두 **서비스 헬퍼 단일 진입점 `planner_store.write_planner_rows(conn, rows, *, goal_id)`**(PLN-38)를 거친다.

  | 경로 | 위치 | 호출자 | 처리 |
  |---|---|---|---|
  | `planner.save_weekly_plan` | `planner.py:238`(→ `planner_store.py` 이동) | `plan_template_service.py:194`, `weekly_adapt_job.py:53`, `rematch.py:87`, CLI `plan.py:165` (v1 `views_training_wizard.py:352·411`·`views_training.py:240` 은 수정하지 않음, V1-13) | goal_id 인자 추가 → `write_planner_rows` |
  | `plan_replace.replace_range` | `plan_replace.py:53` | `plan_replan_service.py:130`, `plan_template_service.py:183`(빈 plan) | goal_id 인자 → `write_planner_rows` |
  | replan 되돌리기 복원 | `plan_replan_service.py:237` | `plan_replans.replaced_json` 의 `deleted` 행 재INSERT | **활성 목표의 replan 만 허용, 재INSERT 에 goal_id 기입**(PLN-37 a, 아래). 스냅샷은 `SELECT *`(`plan_replace._row_dicts`)라 v40 이후 goal_id 를 포함. v40 이전 `plan_replans` 는 §2.4 에서 삭제 |
  | PLN-1 복구(`restore`) | 신규(`goals.plan_snapshot_json`) | `POST /coach/plan/<id>/restore` | 스냅샷 행에 goal_id 포함 → `write_planner_rows` |
  | 외부 계획 수집 | `sync/plan_ingest.py:121`(`plan_ingest_intervals.py:73` 경유 포함) | Garmin·intervals 계획 수집 — 일반 sync 에 연결돼 있지 않고 CLI 수동 실행으로만 호출 | 변경 없음(goal_id NULL, CHECK 대상 아님) |
  | v1 수동 추가·범위 복사 | `web/views_training_crud.py:39`(`manual`), `web/views_training_goal_crud.py:374`(`imported`) | v1 라우트 | 변경 없음(CHECK 대상 아님) |
  | v27 재생성 복사 | `db_schema_v27.py:22` | 과거 마이그레이션 | 영향 없음 |

  테스트 픽스처: `tests/` 에서 `INTO planned_workouts` 를 직접 쓰는 파일 32개 중 `'planner'` 를 포함하는 18개(문자열 기준, 구현 시 재확인)는 CHECK 때문에 goal_id 필요(공용 헬퍼로 처리).
- **goal_id 누락 방지 가드(PLN-38 b):** ① 단일 진입점 `write_planner_rows`(위 표) ② v40 워터마크 ③ `scripts/check_data_consistency.py` 검사 — 워터마크 이후 planner 행 중 goal_id NULL 0건, 수락 조정 표시 컬럼 불일치 0건(PLN-34) ④ pytest 정적 검사 — `src/` 에서 `INTO planned_workouts` 가 허용 파일(`planner_store.py`, `sync/plan_ingest.py`, v1 `web/views_training_crud.py`·`views_training_goal_crud.py`, `db_schema_v27.py`) 밖에 나오면 실패 ⑤ BEFORE INSERT 트리거. 단 E안 CHECK 가 신규 planner 행의 goal_id 누락을 이미 DB 수준에서 막으므로 ⑤는 CHECK 와 중복이고, `race-calendar.md` §2.2 의 'SQLite 트리거 미사용' 원칙과 충돌한다 — 예외 처리 또는 생략은 §8-13 열린 질문. 워터마크(②)도 레거시 planner 행이 모두 삭제된 상태에서 시작하므로 역할이 '검사 경계 기록'으로 줄어든다(§8-13).
- **수락 조정 표시 컬럼(PLN-34 b) — 동기화 규칙:** 원천(SSOT)은 `plan_adjustments`(`decision='accepted'`)이고 표시 컬럼은 파생값이다(ADR-035: 조정은 원본 행 값을 수정하지 않음 — 이 컬럼은 값이 아니라 표시만). 불변식: `adj_accepted = 1 ⇔ EXISTS(plan_adjustments a WHERE a.workout_id = w.id AND a.decision = 'accepted')`.
  - 갱신 지점: `plan_adjustments` 의 decision 이 바뀌거나 행이 생기거나 지워지는 모든 쓰기(grep 2026-10-12: `plan_adjustment_service.py:106·114·118·154·194·277·281`, `plan_move.py:116·142`, `plan_replace.py:41`, `plan_replan_service.py:233`, v37 재생성 경로) 직후 **같은 트랜잭션**에서 헬퍼 `sync_adj_flag(conn, workout_ids)` 가 위 EXISTS 로 다시 계산해 기록한다(토글이 아닌 재계산 — 여러 출처의 accepted 가 공존해도 맞음).
  - 초기값: v40 시점 0. §2.4 로 `plan_adjustments` 가 비어 있으므로 백필 없이 불변식이 성립한다.
  - 읽기: `_effective` 순위(PLN-10, §2.3)가 이 컬럼을 쓴다. 보호 행 판정(`plan_replace._PROTECT_SQL`, `_undo_blocker`)의 EXISTS 조인은 그대로 둔다(원천 기준 판정 유지).
  - 검증: consistency 검사(위 ③)와 테스트(accept → 1, revert → 0, 같은 workout 에 다른 accepted 가 남으면 1 유지).
- **쓰기·삭제 범위:** `save_weekly_plan` 의 같은 날짜 planner 행 삭제(`planner.py:231`)와 `replace_range` 의 범위 삭제는 대상 goal_id 행으로 한정한다 — PLN-1 의 '취소 플랜 행 보존'과 맞추기 위함(다른 목표 행을 지우지 않음). `create_plan_from_template` 의 `replace_range(today~9999)`(이전 활성 목표의 미래 무이력 행 삭제)와 PLN-1 행 보존의 관계는 §8-14.
- `create_plan_from_template(..., expect_active_goal_id)`: 활성 플랜이 있는데 기대값이 다르면 `PlanConflict` → API 409 `ACTIVE_PLAN_EXISTS`(현재 플랜 요약 포함). 클라이언트는 확인 후 다시 보낸다(compare 의 `expect_anchor` 패턴 재사용).
- 교체(PLN-1): 이전 goal 은 `cancelled` 로 두고 그 goal_id 행·스냅샷(`goals.plan_snapshot_json`)을 보존. 취소 플랜 화면에 **복구 버튼** — `POST /coach/plan/<id>/restore` 가 대상 goal 을 active 로, 현재 active 를 cancelled 로 바꾼다(같은 409 확인 흐름). 복구 대상은 v40 이후 생성된 목표뿐이다(PLN-35 c — 옛 목표는 §2.4 로 삭제됨, completed 옛 목표는 `plan_snapshot_json` 이 없고 복구 대상 아님).
- replan 되돌리기(PLN-37 a): `_undo_blocker` 에 '해당 replan 의 goal 이 active 가 아니면 차단' 사유를 추가하고(응답은 기존 `REPLAN_LOCKED` 경로), 복원 재INSERT 는 `plan_replans.goal_id` 를 goal_id 로 기입해 `write_planner_rows` 로 넣는다. `last_undoable` 은 이미 활성 목표 기준이라 노출 규칙은 같다.
- 조회(`get_active_plan(goal_id)`, 세션 상세)는 `goal_id` 로 필터하고 `goal.status` 를 응답에 실어 취소 플랜을 읽기 전용 표시(P-23).
- 날짜 기준 읽기 경로의 goal_id 필터(PLN-33 a): **planner 행이 여러 목표에 겹칠 수 있는 경로에만** `(goal_id = :goal_id OR source <> 'planner')` 를 적용하고, 나머지 날짜 기반 읽기는 현행 유지. 겹침은 PLN-1 로 취소 플랜 행이 남은 날짜(교체·복구일 이후)에서만 생긴다. 필터 절은 `planned_query` 한 곳의 헬퍼로 둔다. 판정 기준과 후보 경로 목록은 §8-5.
- 메모(PLN-2): **날짜 기준 유지**(`user_inputs` 스키마·API 변경 없음). 플랜 교체와 무관한 훈련 기록으로 취급하며 화면에 "날짜별 메모" 로 표기.
- 시작일(PLN-5·PLN-36 c): **플랜 생성 시작을 오늘로** 한다. 현 코드(`plan_template_service.py:190-191`)는 이번 주 월요일(`today - weekday()`) 또는 `plan_start_monday`(이번 주 월요일이 될 수 있음)부터 생성해 PLN-5 와 어긋나므로 수정 항목이다 — 시작 월요일이 오늘 이전이면 첫 주에서 오늘 이전 날짜 행을 만들지·저장하지 않는다(지난 날짜는 계획에 넣지 않음). 그 결과 `save_weekly_plan` 이 지난 날짜의 보호 행을 지우는 경로도 생기지 않는다. 시작 월요일이 미래이면 현행대로 그 월요일부터.
- 부분 첫 주(PLN-32 a): 주차 경계는 월요일 유지, 첫 주는 부분 주(오늘~일요일)로 1주차에 포함한다(`plan_replans.anchor_monday`·`schedule_for_goal` 주차·phase 는 그 주 월요일 기준 그대로). 그 주의 **주간 볼륨 목표는 남은 일수 비례로 축소**(목표 × 남은 일수/7)하고, **그 주 이미 기록된 사용자 러닝(거리·세션 종류·대회)을 참고해 조정**한다. 참고 방식(차감·중복 품질 세션 회피 등 구체 규칙)은 §8-2.
- 고아 `session_outcomes`(PLN-41 b): `matcher.py:91-93` 의 claimed 조건(다른 `planned_id` 의 outcomes 가 활동 점유)은 현행 유지. 레거시 outcomes 는 §2.4 로 삭제되고, 이후 삭제되는 planner 행은 보호 행 규칙상 outcomes 참조가 없는 행이라 새 고아는 정상 경로에서 생기지 않는다.

### 2.3 R3 — 전체 주차 읽기 모델 + 생성 직후 재매칭 + 판정 사유
- 신규 `src/services/plan_overview_service.py`: `get_plan_overview(conn, goal_id) -> {weeks:[{week_start, phase, planned_km, actual_km, run_days, rest_days, long_km, quality_n, compliance_pct}], basis}`. phase 는 `schedule_for_goal` 값 사용. 부분 첫 주는 `week_start`(월요일)와 함께 시작일을 실어 축소 목표임을 표시. API `GET /coach/plan/<id>/weeks`.
- `create_plan_from_template`·replan 적용·복구 후 `rematch.rematch(conn, start, min(end, today))` 호출(같은 트랜잭션 밖, 실패 시 로그만).
- `week_compliance` entry 에 `reason`(코드: `no_activity`, `pace_fast`, `volume_over`, `volume_under`, `cross`) 과 `actual_km`, `actual_pace` 추가. 판정(PLN-6): **둘 다 표시** — 대표 라벨은 볼륨 초과, 보조 라벨은 페이스 빠름(`reasons` 배열, 첫 원소가 대표).
- 헤더(PLN-7): 누적 지표에 서버 `basis: "cumulative"` 를 실어 **'누적(플랜 시작~어제)'** 라벨 + 기준 툴팁, 주간 목록은 `basis: "week"` 로 '이번 주' 표기.
- `_effective` 순위(PLN-10): **매칭된 행 최우선(출처 무관)** > 수락된 조정 행(표시 컬럼 `adj_accepted=1`, PLN-34) > 미매칭 외부 행 > 미매칭 planner 행. 조정 행의 의미(대체인지 추가인지)는 구현 시 검토.
- 거리 비율 상한은 `high-severity-remaining.md` HSR-1 과 단일 결정: 같은 날 후보가 1개면 비율 무시, 여럿이면 1.6 유지(구현은 HSR 설계서 T-01 소관, 여기서는 reason 에 반영만).
- replan 되돌리기(PLN-8): 프런트에 확인 단계(확인 대화상자) 추가(P-20). 활성 목표 한정(PLN-37)은 서버 규칙.
- 프런트: `PlanWeeksTable.svelte`(신규)로 주차 표, 주간 목록 행에 실제값·사유 표시.

### 2.4 레거시 플랜 삭제 — 사용자가 v40 이전에 직접 실행하는 일회성 운영 절차 (PLN-23·24·28·29·30·42)
- **성격:** 사용자가 운영 DB 에서 **v40 적용 전에 직접 실행**하는 일회성 수동 절차다(PLN-31 E·PLN-42). **마이그레이션·미티게이션 코드가 아니다**(PLN-23) — `db_schema_v40`·`ensure_*`·앱 시작 경로·테스트에 삭제 로직을 넣지 않으며, 새 DB·다른 환경에서 자동으로 재실행되지 않는다. 삭제 선행은 v40 CHECK 추가의 전제다(§2.2).
- **삭제 대상(PLN-24·PLN-42 b, 6종):**

  | # | 대상 | 조건 | 비고 |
  |---|---|---|---|
  | ① | `session_outcomes` | 전체 행 | 훈련 결과 이력·ML 자산 — 사용자가 알고 선택(PLN-42). **실행 시점 건수 표시 후 재확인** |
  | ② | `plan_adjustments` | 전체 행(source 무관) | `workout_id` FK 선언 없음(`db_schema_v31.py:10`) — 고아 방지. source 별 건수 분포 표시 후 재확인(PLN-30 c) |
  | ③ | `plan_replans` | 전체 행 | 남기면 되돌리기(`plan_replan_service.py:237`)가 goal_id 없는 planner 행을 재INSERT 해 CHECK 에 걸림 |
  | ④ | `planned_workouts` planner 행 | `source='planner'` | v40 CHECK 전제(남으면 v40 실패) |
  | ⑤ | `planned_workouts` 외부 계획 행 | `source IN ('garmin','intervals')` | 일반 sync 에 연결돼 있지 않고 CLI 수동 실행으로만 유입 — 삭제 후 CLI 를 다시 돌리지 않으면 재유입 없음(재유입돼도 goal_id NULL 허용) |
  | ⑥ | `goals` | `status IN ('active','cancelled')` | **completed 는 유지**(대회 기록 RC-12 근거, PLN-28 c). **실행 시점 건수 표시 후 재확인** |

  대상 아님: v1 `manual`·`imported` 행(CHECK 대상 아님), 날짜별 메모 `user_inputs`(PLN-2), completed 목표. 6종 밖 목표 참조 테이블 `plan_progression(goal_id)`(`db_schema_v29.py`)은 결정 범위에 없음 — §8-15.
- **순서:** 참조하는 쪽 먼저 — ① `session_outcomes`(`planned_id` 참조) → ② `plan_adjustments`(`workout_id`·`goal_id`) → ③ `plan_replans`(`goal_id`) → ④·⑤ `planned_workouts` → ⑥ `goals`. FK 선언이 없어 순서가 결과를 바꾸지는 않지만, 단계별로 건수를 확인할 때 고아 참조가 생기지 않는 순서다.
- **권장 절차(사용자 실행용 체크리스트):**
  0. 사전: 앱·백그라운드 작업(자동 동기화·`weekly_adapt_job`) 정지로 동시 쓰기 차단, 대상 DB 파일 경로 확정(사용자별 DB 각각). §5 실데이터 확인 쿼리는 이 절차 **전에** 사본에서 실행.
  1. 백업: SQLite backup API(`sqlite3 … ".backup"`)로 같은 폴더에 `running.db.pre-plan-reset-<타임스탬프>` 생성(커밋 대상 아님), `PRAGMA integrity_check` = ok. 백업 실패 시 중단.
  2. 건수 표시: 6종 각각 위 조건 그대로 `SELECT COUNT(*)`, ②는 `GROUP BY source` 분포도 함께.
  3. 재확인: ①`session_outcomes`·⑥`goals`(·②분포) 건수를 보고 진행 여부를 다시 확인한다(PLN-24·30). 확인하지 않으면 중단(삭제 0건).
  4. 실행: 단일 트랜잭션(`BEGIN IMMEDIATE` … `COMMIT`)에서 위 순서로 `DELETE`. 트랜잭션 안 재집계가 0 이 아니면 `ROLLBACK`.
  5. 사후 검증: 6종 대상 건수 0(⑥은 active·cancelled 0, completed 건수 불변), `source='planner'` 행 0, `PRAGMA integrity_check` = ok. 그 뒤 마이그레이션 적용.
- **롤백:** 단계 4 실패는 트랜잭션 롤백(원 상태 유지), 완료 후 되돌림은 단계 1 백업 파일 복원.
- **다른 마이그레이션과의 위치:** v40 이전은 필수(CHECK 전제). PLN-29 원결정은 'v37 이전에 삭제 후 v37~v40 순차 적용'이며, 조정 문구(PLN-31 E)는 'v40 전'으로 적혀 있다 — 어느 쪽이 최종 기준인지는 §8-12. v37 이전이면 v37 은 빈 `plan_adjustments` 를 재생성하고, v39 는 남은 completed 목표만 `race_calendar` 로 백필한다.

### 기각된 대안
- B안(스키마 무변경, 스냅샷만)·C안(R1만 우선)은 PLN-9 로 기각. D안(goal_id NULL 허용 컬럼만, 기존 데이터 보존)은 PLN-31 재결정으로 철회. 단계 1(R1)·단계 2(R3)는 스키마 무관이라 먼저 진행 가능.

## 3. ID 처리 매핑

| ID | 처리 | 근거 |
|----|------|------|
| P-01, P-02 | 설계 R1 | 파생 필드 재생성 + 자동 교정(PLN-4) |
| P-03 | 설계 R2 | 409 확인 + 행·스냅샷 보존 + 복구(PLN-1, 신규 목표부터 PLN-35) |
| P-04, P-05 | 참조 | server-input-origin-validation.md 2.4 |
| P-06 | 설계 R3 | 원인 확정. reason·두 라벨(PLN-6), `_effective`(PLN-10·34), 상한은 HSR-1 |
| P-07 | 설계 R3 | plan overview API·표 |
| P-08 | 설계 R1 | 지정 요일(`workout_weekdays_mask`) 준수·workout mask 우선(PLN-11)·미지정 시 생성·사용자 재계획에서 입력 요구(PLN-12·39)·자동 경로 보류·휴식 하한 없음(PLN-13)·휴식 0~1일 저장 전 안내(PLN-14)·신규 목표 v2 전환(PLN-3). 기존 목표는 삭제되어 배너·재생성 제안 없음(PLN-40) |
| P-09 | 설계 R3 | basis 필드 + '누적(플랜 시작~어제)' 라벨(PLN-7) |
| P-10 | BACKLOG 개별 | ACWR 범위를 메트릭 정의에서 받기, CTL 스케일 |
| P-11 | 설계 R2 | 생성 시작 = 오늘(PLN-5·36) + 부분 첫 주 볼륨 축소(PLN-32) + 생성 후 재매칭 |
| P-12 | BACKLOG 개별 (+참조) | 목표 없음 문구 모순은 개별, 1초 입력은 입력 검증 참조 |
| P-13 | 참조 | error-retry-common.md(경로·재시도), 잘못된 파라미터 400 은 입력 검증 |
| P-14 | BACKLOG 개별 (+R2) | 단계 표시·입력 항목은 개별, 활성 시 진입점은 R2 409 흐름에 포함 |
| P-15 | 현행 유지 (+참조) | 메모 날짜 기준 유지(PLN-2), 길이·날짜 검증은 입력 검증 |
| P-16 | BACKLOG 개별 | 빈 메모 저장=삭제 허용 |
| P-17 | 참조 | Origin 관문(D-22 동일 원인) |
| P-18, P-19, P-21 | 참조 | 접근성 설계 |
| P-20 | 설계 R3 + BACKLOG 개별 | 되돌리기 확인 단계(PLN-8)·활성 목표 한정(PLN-37), title·문구는 개별 |
| P-22 | 참조 | 입력 검증 2.3 엔벨로프(라우팅 404 포함 여부 확인 요청) |
| P-23 | 설계 R2 | status 노출·읽기 전용·복구 버튼·겹침 경로 goal_id 필터(PLN-33) |
| P-24 | BACKLOG 개별 | R1 후 rest 설명 해소, 버튼 허용 범위는 정책 |
| P-25 | BACKLOG 개별 | 로딩 스켈레톤 |

## 4. 변경 파일 표

| 파일 | 구분 | 내용 | 줄 수(예상) |
|------|------|------|------------|
| `src/training/plan_finalize.py` | 신규 | finalize_week, week_violations, 자동 교정·로그 | ~110 |
| `src/training/planner_store.py` | 신규 | planner.py 에서 저장·prefs 함수 이동, `workout_weekdays_mask` 읽기·쓰기, `resolve_run_weekdays`(workout 우선, NULL 이면 `WeekdaysRequired`), **`write_planner_rows`(planner INSERT 단일 진입점, goal_id 필수, PLN-38)**, `save_weekly_plan` 삭제 범위 goal_id 한정 | ~130 |
| `src/training/planner.py` | 수정 | finalize 호출, 이동분 재수출, 부분 첫 주(오늘 이전 날짜 제외·볼륨 일수 비례 축소 + 그 주 러닝 기록 참고, PLN-32) | 300 → ~235 |
| `src/training/planner_v2.py` | 수정 | `_desc_locked` 표시(race·cold-start), 지정 요일 입력, 부분 주 볼륨 목표 입력 | +15 |
| `src/db_schema_v40.py` | 신규 | `planned_workouts.goal_id INTEGER CHECK(source<>'planner' OR goal_id IS NOT NULL)` + 수락 조정 표시 컬럼(PLN-34) + `user_training_prefs.workout_weekdays_mask` ADD COLUMN, 워터마크 기록, integrity_check·멱등. 트리거는 §8-13 결과에 따름. 레거시 삭제 로직 없음(§2.4) | ~50 |
| `src/db_setup.py` | 수정 | DDL(goal_id CHECK·표시 컬럼)·`SCHEMA_VERSION` 40·ensure 호출 | +10 |
| `src/training/planned_query.py` | 수정 | 겹침 경로용 goal_id 필터 절 헬퍼(PLN-33) | +10 |
| `src/training/plan_replace.py` | 수정 | goal_id 인자, 삭제 범위 goal_id 한정, `write_planner_rows` 경유, 조정 삭제 후 `sync_adj_flag` | +8 |
| `src/services/plan_adjustment_service.py`, `src/services/plan_move.py` | 수정 | decision 변경·INSERT 직후 `sync_adj_flag`(PLN-34 동기화 규칙) | +6 each |
| `src/training/plan_backtest.py`, `plan_backtest_replan.py`, `scripts/plan_backtest.py` | 수정 | PLN-18·22·25: `Scenario.workout_weekdays_mask`(격자·이력 시나리오 모두 필수, 이력은 호출자가 직접 명시), prefs 에 mask 기입 후 생성, mask 미지정 시나리오 거부 | +15 / +3 / +3 |
| `src/training/goals.py`, `src/services/plan_template_service.py` | 수정 | v2 일괄 전환, expect_active_goal_id, PlanConflict, 행 보존·snapshot 저장, restore, goal_id 기입, **생성 시작 = 오늘(PLN-36)**, 재매칭 | +75 |
| `src/services/plan_service.py` | 수정 | goal_id 필터, status, basis | +20 |
| `src/services/plan_overview_service.py` | 신규 | 주차 요약(부분 첫 주 표시 포함) | ~110 |
| `src/training/week_compliance.py` | 수정 | reason(s)·actual 필드, 두 라벨, `_effective` 순위(표시 컬럼 사용), 겹침 경로면 goal_id 필터 | +25 (≤256) |
| `src/api/routes_plan.py`, `src/api/routes_plan_replan.py` | 수정 | 409, mask NULL 시 run_weekdays 필수(`WeekdaysRequired` → 400), 재계획도 `WeekdaysRequired` → 400(PLN-39), `/weeks`·`/restore` 라우트 | +45 |
| `src/services/plan_replan_service.py` | 수정 | `:128` 사용자 경로 분류(`WeekdaysRequired` 전파, PLN-39), `replace_range` goal_id 전달, undo 활성 목표 한정·재INSERT goal_id(PLN-37) | +12 |
| `src/services/weekly_adapt_job.py`, `src/training/rematch.py` | 수정 | `WeekdaysRequired` 시 생성·저장 보류·사유 로그(PLN-12 자동 경로), `save_weekly_plan` 에 goal_id 전달 | +6 each |
| `src/plan.py` | 수정 | `WeekdaysRequired` 시 생성하지 않고 요일 입력 안내(CLI), `save_weekly_plan` 에 goal_id 전달 | +6 |
| 겹침 가능 읽기 경로(§8-5 분류 결과) | 수정 | `planned_query` 필터 절 적용 | 경로당 +2 |
| `scripts/check_data_consistency.py` | 수정 | 워터마크 이후 planner 행 goal_id NULL 0건, 수락 조정 표시 컬럼 불일치 0건(PLN-38·34) | +25 |
| `frontend/src/lib/api/plan.ts` | 수정 | 타입·getPlanWeeks·restore·409 처리 | +30 |
| `frontend/src/lib/planWeekdays.ts` | 신규 | 휴식 0~1일 판정(지정 요일 수 ≥ 6, PLN-14) 순수 함수 | ~20 |
| `frontend/src/lib/components/plan/PlanWeeksTable.svelte` | 신규 | 주차 표 | ~100 |
| `frontend/src/routes/coach/plan/[id]/+page.svelte`·`+page.ts`, `compare/+page.svelte`, 생성 폼 | 수정 | 표·사유·상태·복구, 교체·되돌리기 확인, 요일 선택·휴식 0~1일 저장 전 안내(PLN-14), 재계획 400 시 요일 입력 유도 | +95 |
| `tests/test_plan_finalize.py`, `test_plan_ownership.py`, `test_plan_overview.py`, `test_week_compliance_reason.py`, `test_plan_weekdays.py`, `test_db_schema_v40.py`, `test_plan_backtest_weekdays.py`, `test_planner_insert_guard.py`(정적 검사), `test_adj_flag_sync.py`, 프런트 `planWeekdays.test.ts` | 신규 | 아래 검증 | ~520 |
| 기존 테스트 픽스처(`INTO planned_workouts` 32개 중 planner 행을 넣는 약 18개 파일) | 수정 | goal_id 기입(공용 헬퍼) | — |

## 5. 단계·검증
1. R1: 7주 템플릿을 rv1 / rv2+plan_weeks NULL / rv2+plan_weeks=7 세 픽스처로 생성 → 교정 후 `week_violations == []`, 러닝 요일 ⊆ 지정 요일. 신규 목표는 plan_weeks 누락 입력에서도 v2 경로 진입. mask NULL + `run_weekdays` 없음 → 400, `run_weekdays` 전달 시 mask 저장, mask 설정 후 재생성 시 생략 가능. PLN-11: workout mask 와 rest mask 가 같은 요일을 지정하면 그 요일은 러닝(모순 저장도 허용). PLN-13: 7요일 지정 시 휴식 0일로 생성되고 `week_violations` 위반 없음. PLN-14: `planWeekdays` 가 지정 5개 → 안내 없음, 6·7개 → 안내 필요. PLN-12·39: mask NULL 에서 사용자 재계획 API → 400(저장 0건), `weekly_adapt_job.run`·`rematch` 는 저장 0건·사유 로그·예외 전파 없음, CLI 는 생성 없이 안내. 기존 planner 골든 테스트는 description 기대값만 갱신. PLN-18·22: 격자·이력 시나리오가 mask 를 입력으로 받아 `WeekdaysRequired` 없이 생성, 러닝 요일 ⊆ 시나리오 mask, mask 미지정 시나리오(이력 포함)는 구성 오류로 거부(결과 '실패' 집계에 안 들어감), `plan_backtest_replan` 복제 시 mask 유지, 기존 격자 통과 수 회귀 비교(`scripts/plan_backtest.py --engine v2|replan`).
2. R3 읽기: overview 합계 = planned_workouts 집계, 생성 직후 과거 날짜 매칭, 10/6~10/9 합성 주로 reasons(대표 volume_over·보조 pace_fast / 상한 탈락), ext2 픽스처(미매칭 외부 + 매칭 planner)에서 매칭 행이 effective, 수락 조정 행(`adj_accepted=1`) > 미매칭 외부 행.
   **실데이터 확인 필요**(real_ui.db 사본, 읽기 전용 — 원인 확인용이므로 §2.4 레거시 삭제 전 사본에서 실행):
   | 확인 | 쿼리 | 판정 |
   |---|---|---|
   | goal 생성 경로 | `SELECT id,status,created_at,plan_rules_version,plan_weeks,race_date,distance_km FROM goals ORDER BY id;` | rv=1 또는 plan_weeks NULL이면 v1 경로 |
   | anchor별 규칙 버전 | `SELECT id,goal_id,anchor_monday,rules_version,status,created_at FROM plan_replans WHERE goal_id=1 ORDER BY anchor_monday;` | 주별 effective_rules_version 차이 |
   | 휴식 설정 | `SELECT rest_weekdays_mask,long_run_weekday_mask,max_q_days FROM user_training_prefs;` | mask=0이면 v1에서 휴식 0 |
   | 주간 러닝 일수 | `SELECT date(date,'weekday 0','-6 days') wk, SUM(workout_type<>'rest') runs, ROUND(SUM(distance_km),1) km FROM planned_workouts WHERE source='planner' GROUP BY wk ORDER BY wk;` | 7회가 이어지면 P-08 재현 |
   | P-06 주 매칭·외부 행 | `SELECT id,date,source,workout_type,distance_km,matched_activity_id FROM planned_workouts WHERE date BETWEEN '2026-10-05' AND '2026-10-11' ORDER BY date,id;` | 같은 날 외부 미매칭 + planner 매칭이면 PLN-10 해당 |
3. R2: 레거시 삭제(§2.4, 사용자 실행 — 코드·테스트 없음) 후 확인 — 백업 파일 존재·`integrity_check` ok, session_outcomes·goals 재확인 기록, 사후 대상 건수 0·completed 목표 불변. 그 뒤 마이그레이션 — 운영 SQLite 버전 확인(PLN-26), `workout_weekdays_mask` 기본 NULL, 표시 컬럼 기본 0, planner 행 없는 DB 에서 적용 후 planner 행 goal_id NULL INSERT 거부·`garmin`/`intervals`/`manual` 행 goal_id NULL INSERT 허용·`integrity_check` ok·재실행 멱등, planner 행이 남은 DB 에서는 적용 실패·롤백·원 테이블 불변(전제 위반 검출). INSERT 경로 표의 planner 경로마다 goal_id 기입 테스트, 정적 검사(허용 파일 밖 `INTO planned_workouts` → 실패), consistency 검사 2건 통과. PLN-34: accept → 표시 1, revert → 0, 다른 accepted 공존 시 1 유지, 조정 삭제 경로 후 불변식 유지. PLN-37: 취소 목표의 replan undo → `REPLAN_LOCKED`, 활성 목표 undo 재INSERT 행 goal_id = `plan_replans.goal_id`. 409 → 확인 재전송 → 이전 플랜 cancelled·행 보존(다른 목표 행 삭제 없음), restore 후 active 교대, 취소 플랜 세션 응답 status=cancelled, 겹침 경로에서 취소 플랜 행이 활성 플랜 조회에 섞이지 않음(PLN-33). PLN-36·32: 수요일 생성 시 첫 주 행은 수~일만 존재·월~화 행 없음·보호 행 삭제 없음, 첫 주 볼륨 목표 ≈ 주간 목표 × 5/7(그 주 기록 반영 규칙은 §8-2 확정 후), 일요일 생성 시 첫 주 = 그 일요일 하루. 메모는 교체 전후 같은 날짜에서 동일.
4. 브라우저(DB 사본): 375/1280px 에서 /coach/plan/{id} 주차 표(부분 첫 주 표시)·사유·두 라벨, 헤더 '누적(플랜 시작~어제)' 툴팁, compare 교체 확인, 복구 버튼, replan 되돌리기 확인, 생성 폼 요일 선택·6~7요일 지정 시 저장 전 1회 안내(취소 시 요청 없음). `pytest`·`check_docs.py`·`check_data_consistency.py`·프런트 테스트 통과.
- 호환성: 레거시 플랜(6종)은 사용자가 v40 전에 삭제하고 시작한다(§2.4, PLN-23·42) — 기존 플랜·목표를 위한 이행·완충 코드는 없고, completed 목표만 남는다(PLN-28). goal_id 는 planner 행만 CHECK 로 필수, 외부(garmin·intervals)·v1 행은 NULL(PLN-31 E). `workout_weekdays_mask` NULL 기본, 신규 생성 시 요일 입력으로 채워진다(PLN-12·40). 보존된 취소 플랜 행은 겹칠 수 있는 경로에서만 goal_id 필터로 분리(PLN-33). v1 화면·경로는 깨져도 허용하며 보호·호환 코드를 두지 않는다(V1-1·V1-13). 알고리즘 출력(설명·요일·부분 첫 주 볼륨)이 바뀌므로 ADR-042 에 따라 버전/algo_changelog 항목 필요 여부 확인.

## 6. 결정
- PLN-1~42, 연관 HSR-1·V1-2·V1-13: 결정 완료(표 참조, `decisions-table.md` 2026-10-11). 최종 소유권 방식은 PLN-31 재결정 E안(D안 철회) — PLN-19·20·26 은 E안으로 복원, PLN-21 은 v41 이 없어져 소멸, PLN-23·24·28·29·30·42 는 '사용자가 v40 전에 직접 삭제'(6종, goals 는 active·cancelled 만), PLN-35 는 옛 목표 복구 미고려. 본문 §2 각 항목에 반영.

## 7. 범위 밖 메모
- `planned_workouts` INSERT 경로의 goal_id 기입은 §2.2 표. garmin_push(`garmin_workout_id` UPDATE 만)·calendar_feed(조회)는 INSERT 하지 않아 §8-5 goal_id 필터 분류 대상으로만 남는다.
- `plan_adjustments.goal_id`(`db_schema_v31.py:9`, '생성 시점 활성 목표') 채움 방식은 바꾸지 않는다. v37 재생성(`adjustment-signals.md`)과의 정합은 그 번들 소관.
- compare 의 "달성 가능성" 계산(P-12)은 예측 묶음(T-08..T-13) 공식과 일치 여부 확인 필요.
- 외부 계획 행의 활동 선점은 합성 재현에서 결과 불변으로 확인. 남은 것은 §5 쿼리로 확인하는 `_effective` 해당 여부(PLN-10).
- `src/training/planner_rules.py` 가 이미 325줄(300줄 규칙 초과). 이번 설계는 이 파일을 건드리지 않으며 분리는 별도 작업.

## 8. 동기화 중 발견한 모호점
번호는 다른 절의 '§8-n' 참조를 위해 유지한다. 해소된 항목: 8-1·3·7·8·9(PLN-25)·10(PLN-26)·11(PLN-24) 삭제, 8-6 해소(PLN-34) 삭제. 아래에 남은 항목과 이번 동기화의 해소 표시만 둔다.
- **8-2. 해소(PLN-32) — 세부 1건 남음:** 부분 첫 주는 1주차·월요일 경계·일수 비례 축소로 확정. **남은 것:** '그 주 사용자 러닝 기록(거리·세션 종류·대회) 참고' 의 구체 규칙(이미 달린 거리 차감 여부, 이미 수행한 품질·롱런 세션의 중복 회피, 그 주 대회가 있을 때 처리)은 결정 문구에 없음 — 구현 단계에서 후보 제시 후 사용자 확정.
- **8-4.** PLN-14 안내 문구는 구현 단계에서 후보 제시 후 사용자 확정.
- **8-5. 판정 기준 해소(PLN-33) — 경로 분류 남음:** 기준은 '교체·복구 이후 날짜의 planner 행을 날짜만으로 고르는 경로 = 겹침 가능 → 필터, 그 외 현행'. 후보(grep 2026-10-12, `planned_workouts` 를 읽는 `src/` 비-v1 파일): `matcher`·`rematch`, `week_compliance`, `planned_query`·`plan_overlay`, `adjuster`·`plan_adjustment_service`·`plan_pain`·`plan_move`·`plan_advisory`, `calendar_feed_service`, `garmin_push`, `week_digest`, `plan_load`, `progression_service`, `weekly_adapt_job`, `replanner`·`plan_replan_service`·`plan_replan_diff`, `ai/*` 컨텍스트 빌더. 경로별 해당 여부는 구현 첫 단계에서 목록으로 확정(사실 확인, 정책 아님).
- **8-12. 열린 질문(삭제 실행 시점):** PLN-29 원결정은 'v37 이전 삭제 → v37~v40 순차', 조정 문구(PLN-31 E·PLN-42)는 'v40 이전' 만 명시한다. 'v37 이전'이 여전히 유효한지 불명확하다. v39 이후에 삭제하면 삭제된 active·cancelled 목표를 가리키던 `race_calendar` 행(`origin='goal'`)·`goals.race_id` 정리 문제가 생기고(v39 는 비활성 목표도 백필), v37 이후면 v37 재분류 백필이 곧바로 지워질 데이터에 수행된다.
- **8-13. 열린 질문(PLN-38 트리거·워터마크):** E안 CHECK 가 신규 planner 행 goal_id 누락을 INSERT·UPDATE 모두에서 이미 막으므로 BEFORE INSERT 트리거는 중복이다. (a) `race-calendar.md` §2.2 'SQLite 트리거는 쓰지 않는다' 원칙의 예외로 트리거를 둘지 (b) 트리거를 생략할지 미정. 워터마크도 레거시 planner 행이 모두 삭제된 뒤 v40 이 적용되므로 consistency 검사 경계로서의 실익이 작다 — 유지(결정대로) 시 저장 위치(메타 테이블 없음)는 구현 시 확정.
- **8-14. 열린 질문(교체 시 이전 목표 미래 행):** PLN-1 은 이전 goal 행을 '삭제하지 않고 보존'하는데, 현 `create_plan_from_template` 은 `replace_range(today~9999)` 로 이전 활성 목표의 미래 무이력 행을 지우고 그 snapshot 을 `plan_snapshot_json` 보존 근거로 쓴다(§1 R2). 교체 시 이전 목표의 미래 행을 (가) 모두 남기고 goal_id 필터로만 분리할지 (나) 지우고 스냅샷으로 복구할지가 본문(행 보존 + 스냅샷 보존)에서 하나로 정해져 있지 않다. 복구 동작·PLN-33 겹침 범위가 이 답에 달려 있다.
- **8-15. 열린 질문(삭제 범위 밖 목표 참조):** `plan_progression(goal_id, qtype)`(`db_schema_v29.py`, 목표별 품질 사다리 단계)은 6종에 없어 active·cancelled 목표 삭제 후 고아 행이 남는다. 함께 지울지 남길지는 결정 기록이 없다(`goals.id` 는 AUTOINCREMENT(`db_setup.py:449`)라 삭제된 id 가 재사용되지 않아 고아 행이 새 목표에 섞이지는 않음 — 잔존 데이터 정리 여부만 남음).
