# 설계: 훈련 계획 묶음 (P-01~P-25)

- 대상: `ux-review-2026-10/05-coach-plan.md` P-01~P-25 · 작성일 2026-10-11 · 상태: 결정 확정(2026-10-11, PLN-1~27·V1-13), 구현 전 — 실데이터 확인·후속 확인 항목 남음(§5, §8)
- 변경 이력: 2026-10-11 원인 검증 반영 — P-06(매칭 비율 상한·판정 순서·_effective 순위), P-08(v1 폴백·운영 경로 휴식 보장 부재) 원인 확정 및 실데이터 확인 항목 추가
- 변경 이력: 2026-10-11 설계서 동기화 — `decisions-table.md` PLN-1~10 결정을 본문(설계안·변경 파일·단계·검증·호환성)에 반영, HSR-1 과의 단일 결정 관계 반영
- 변경 이력: 2026-10-11 PLN-3 보강 반영 — 지정 요일 저장 `user_training_prefs.workout_weekdays_mask`(NULL=미지정), 기존 v1 목표 즉시 재생성 제안(미리보기·확인, 자동 재생성 아님). 결정 섹션 축약
- 변경 이력: 2026-10-11 2차 동기화 — PLN-11(workout mask 우선)·PLN-12(mask NULL 이면 모든 생성 경로에서 요일 입력 전 생성 보류)·PLN-13(최소 휴식일 하한 없음) 반영, §8 해소 항목 축약
- 변경 이력: 2026-10-11 3차 동기화 — PLN-14(휴식 0~1일 저장 전 1회 안내)·PLN-15(보류 중 기존 행 유지 + '요일 입력 전까지 갱신 안 됨' 표시)·PLN-16(코치 화면 배너, v1 범위 제외)·PLN-17(요일 입력 전까지 주간 적응 정지 + 안내) 반영. v1 변경 파일·단계 제거
- 변경 이력: 2026-10-11 4차 동기화 — V1-1(v1 화면·경로는 v2 완료 시 일몰, 설계·검증·호환성에서 고려하지 않음): 레거시 v1 UI 호출·호환 서술 제거. 'v1 템플릿/v1 폴백/v1 목표'(plan_weeks NULL·rules_version<2 데이터·알고리즘 용어)는 유지
- 변경 이력: 2026-10-11 5차 동기화 — V1-1 정정·V1-2(v1 일몰 = UI·라우트 일몰, 공유 파일·함수 유지): §2 PLN-12 에 v1 위저드 mask NULL 위험을 '라우트 일몰 시 소멸하는 위험'으로 한 줄 복원(grep 재확인)
- 변경 이력: 2026-10-11 6차 동기화 — PLN-18(백테스트 `plan_backtest*` 입력에 요일 mask 지정: §2.1·§4·§5), PLN-19(`planned_workouts.goal_id` 이번 작업에서 NOT NULL 승격, 백필 완료 후: §2.2 마이그레이션 순서·NULL 잔존 처리·INSERT 경로 grep, §4·§5·호환성), V1-2 정합 재확인(v1 라우트의 INSERT 경로는 라우트 일몰 시 소멸, 공유 함수 `save_weekly_plan`·`replace_range` 는 유지)
- 변경 이력: 2026-10-11 7차 동기화 — PLN-23(기존 훈련 플랜 삭제 허용, 기존 플랜용 마이그레이션·미티게이션 코드 미작성): goal_id 백필·dry-run 분포·고아/외부/v1 행 귀속·NULL 잔존 중단·옛 스냅샷 goal_id 보충·기존 v1 목표 재생성 제안(`regen-preview`)·보류 중 기존 행 유지 표시(`weekdays_required`)·코치 배너·기존 사용자 주간 적응 정지 안내 삭제. PLN-19 재결정·PLN-20(goal_id NOT NULL 을 planner 행 한정 CHECK 로, 외부·v1 행 NULL 유지)·PLN-21 해소·PLN-22(이력 시나리오도 실제 mask 필수)·V1-13(v1 보호·호환 서술 제거) 반영. v40·v41 병합 제안(§8-10), 삭제 범위 사실 정리(§8-11)
- 변경 이력: 2026-10-11 8차 동기화 — PLN-24(삭제 대상 6종 확정, 외부 계획 행은 CLI 수동 실행으로만 유입)·PLN-23 을 §2.4 '일회성 운영 절차'(마이그레이션 코드 아님: 순서·백업·건수 표시·재확인·단일 트랜잭션)로 서술, PLN-25(이력 시나리오 mask 는 시나리오 입력에 직접 명시, 호출자 책임), PLN-26(v40·v41 병합 채택 — 단일 v40, 분리안·v41 삭제; v38·v39 와 번호 충돌 없음 grep 확인), PLN-27(코치 배너 삭제 유지). 해소된 §8 항목(1·3·7·8·9·10·11) 삭제, 남은 항목 번호 유지
- 범위: 플랜 생성 파이프라인(`src/training/planner*`), 플랜 소유·교체(`goals`, `plan_replace`), 읽기 모델(`plan_service`, `week_compliance`, `routes_plan`), v2 `frontend/src/routes/coach/plan/*`. v1 화면·라우트는 일몰 예정(V1-1·V1-2, UI·라우트 일몰)이라 범위 밖. 공유 함수(`generate_weekly_plan`, `match_week_activities` 등)는 유지 대상
- 참조만: 입력·Origin 검증 → `server-input-origin-validation.md`, 오류·재시도 → `error-retry-common.md`, 접근성 → 별도 접근성 설계

## 1. 근본 원인

### R1. 주간 플랜이 여러 단계에서 바뀌는데 파생 필드는 첫 단계에서 한 번만 만든다 (P-01, P-02, P-08)
- `planner.generate_weekly_plan` 이 `description(wtype, dist, day)`·`structure` 를 v1 거리로 먼저 채운다. 이후 `planner_v2.apply_v2`(`_shakeout` L72·74, 휴식 전환 L91·111, 최소거리 L116), `planner_v2_long._shrink`/`rebalance`/`plan_long_week`, `apply_ladder` 가 `distance_km`·`workout_type` 을 바꾸지만 description 은 일부 경로(`trim_run_days`, `plan_long_week` 강등)에서만 다시 만든다.
- 결과: 거리 컬럼과 설명이 어긋나고(P-01 10.0 vs "16.1km"), rest 로 바뀐 행에 "3.7km 이지런" 이 남는다(P-02). `_finalize_rows` 는 rest 행의 페이스·구조만 비우고 설명은 건드리지 않는다.
- 주간 불변식(러닝 일수 상한, rest ↔ 거리 0, 설명 거리 = 컬럼 거리)을 검사하는 곳이 없다. P-08 재현 확정: v1 템플릿(`planner.py:124-128,162-173`)은 `rest_weekdays_mask`(기본 0, `planner_config.py:84`) 외 모든 요일을 러닝으로 채워 7주 내내 주 7회가 된다. v2 분기(`planner.py:210-213`)는 `goal and target and effective_rules_version>=2`일 때만 적용되는데, `plan_weeks`가 NULL이면 target이 None(`planner_rules.py:48-49`)이라 rules_version=2여도 v1으로 폴백한다(재현: rv2+plan_weeks NULL → 7회, rv2+plan_weeks=7 → 주 2~3회). 휴식 최소를 보장하는 G1 게이트(`plan_gates.py:71`)는 `plan_backtest` 전용이라 운영 생성 경로에는 휴식 보장이 없다. goal 1이 어느 경로로 생성됐는지는 실데이터 확인 필요(§5).

### R2. planned_workouts 에 플랜 소유자가 없다 (P-03, P-11, P-15, P-23, P-09 일부)
- `planned_workouts` 는 날짜 키로만 존재하고 `goal_id` 가 없다. 플랜 = "활성 목표 + 그 날짜 범위의 행" 이라는 암묵 규칙이다.
- 그래서 새 플랜 생성은 `add_goal` 이 기존 active 를 무조건 `cancelled` 로 바꾸고(`goals.py` L102), `replace_range(today~9999)` 가 이력 없는 미래 행을 지운다(P-03). 확인 단계·복구 스냅샷이 없다. `replace_range` 는 snapshot 을 반환하지만 `create_plan_from_template` 이 버린다.
- 같은 이유로 `get_active_plan(goal_id)` 는 goal_id 와 무관하게 "오늘 주의 행" 을 돌려주고, 취소된 플랜 세션도 현재 행으로 보인다(P-23). 메모는 `user_inputs(input_date, 'session_note')` 날짜 키라 플랜 간 공유된다(P-15).
- 시작 주는 `today - weekday()` 로 고정이라 일요일 생성 시 지난 6일이 1주차에 들어간다(P-11).

### R3. 읽기 모델이 "이번 주" 하나뿐이고 매칭은 동기화 시점에만 돈다 (P-06, P-07, P-08 검증 불가, P-09)
- `plan_service.get_active_plan` 은 `_current_week_start()` 한 주만 조회한다. 전체 주차 볼륨·단계·테이퍼를 돌려주는 API 가 없다(P-07). 사용자가 P-08 을 검증할 화면도 없다.
- `match_week_activities`는 `bg_sync` 완료 후(v2 동기화 포함, 최근 4주)·앱 시작에서 호출된다. v2 `POST /coach/plan`은 생성 후 재매칭하지 않는다. P-06 10/8·10/9는 거리 비율 상한(`match_select.py:10,40-41`, 2.5배·1.83배 > 1.6)으로 탈락했다(합성 재현으로 확정). 외부 계획 행이 먼저 정렬·매칭(`matcher.py:51`)되어도 결과는 같았다.
- `outcome_label`은 이지 페이스 판정을 볼륨보다 먼저 한다(`week_compliance.py:69-72`). 10/6·10/7의 10km·6km가 "강도 어긋남"이 되고(확정), 사유·실제 거리/페이스는 응답에 없다. `_effective` 순위(48-52)는 미매칭 외부 행을 매칭된 planner 행보다 우선해 missed를 만든다(결함 재현됨, 이번 데이터 해당 여부 불명, §5). 헤더는 누적(`_plan_compliance`), 목록은 주간(`week_compliance.compute`)이라 기준이 다르다(P-09).

## 2. 설계안 (확정: A안, PLN-9)

### 2.1 R1 — 마지막 단계에서 한 번 파생 + 불변식 자동 교정
- 신규 `src/training/plan_finalize.py`: `finalize_week(rows, *, run_weekdays) -> list[dict]` 가 모든 변형이 끝난 뒤 `description`·`structure` 를 (type, distance, date) 에서 다시 만든다. race·cold-start 노트처럼 의도된 설명은 `_desc_locked` 플래그로 보존.
- 같은 모듈 `week_violations(rows, run_weekdays) -> list[str]`: rest↔거리, 설명 km = 컬럼 km(±0.1), 러닝 요일 ⊆ 지정 요일, 롱런 ≤ 주간의 일정 비율. 위반은 **자동 교정 + 로그**(PLN-4): rest 행 거리 0·설명 재생성, 지정 요일 밖 러닝 행 → rest, 설명 불일치 → 재생성. 생성·저장은 막지 않으며 테스트에서는 교정 전 위반 0 을 assert.
- `generate_weekly_plan` 마지막 줄을 `finalize_week(apply_race_week(...))` 로 바꾼다. `planner.py` 가 300줄이라 `save_weekly_plan`·prefs 함수(L218~)를 `planner_store.py` 로 옮긴다(재수출 유지).
- P-08(PLN-3): 원칙은 **사용자가 지정한 운동 요일 준수**. 지정 요일은 **`user_training_prefs.workout_weekdays_mask INTEGER NULL` 신규 컬럼**(NULL=미지정, 기존 `rest_weekdays_mask` 와 별개)에 저장해 v2·`finalize_week` 가 공통으로 읽는다. mask 가 NULL 이면 계획 생성 시 요일 선택을 요구한다(`POST /coach/plan` 에 `run_weekdays` 없으면 400, 받은 값은 mask 에 저장; 프런트 생성 폼에 요일 선택 단계). 구현은 (c) **신규 목표는 v2 규칙으로 일괄 전환** — `add_goal` 이 rules_version=2 와 v2 진입 조건(target 산출에 필요한 `plan_weeks`)을 항상 채워 v1 폴백 경로에 들어가지 않게 한다.
- 두 mask 우선순위(PLN-11): `workout_weekdays_mask` 와 `rest_weekdays_mask` 가 같은 요일에서 모순되면 **workout 우선** — 지정 운동 요일은 rest mask 와 무관하게 러닝 요일로 쓴다. 저장 시 모순을 거부하지 않는다(입력 검증 없음). `run_weekdays` 산출을 `planner_store.resolve_run_weekdays(prefs)` 한 곳에 두어 v2·`finalize_week`·`week_violations` 가 같은 값을 쓴다.
- 최소 휴식일(PLN-13): **하한 없이 사용자 지정 존중**. 7요일 모두 지정해도 생성·`week_violations` 가 막거나 교정하지 않으며, G1 게이트(`plan_gates.py:71`)는 운영 경로에 재사용하지 않는다(`plan_backtest` 전용 유지). 휴식 0~1일 지정 시(PLN-14) **저장 전 1회 안내** — 요일 선택 단계에서 지정 요일이 6~7개면 저장(생성 요청) 전에 부상 위험 안내를 한 번 보여 주고, 확인 시 그대로 저장한다(차단 아님). 판정은 프런트 순수 함수(지정 요일 수 ≥ 6)로 두고 서버 계약은 바꾸지 않는다. 문구는 구현 단계에서 후보 제시.
- mask NULL 인 생성 경로(PLN-12): **생성 전 요일 입력 요구**를 v2 `POST /coach/plan` 뿐 아니라 `generate_weekly_plan` 을 부르는 모든 경로에 적용한다. 확인 지점은 `planner_store.resolve_run_weekdays` 한 곳 — mask NULL 이면 `WeekdaysRequired` 를 올린다(요일 무시 폴백·과거 요일 재사용 없음). 호출 경로별 처리 수준:
  - 사용자 요청 경로(v2 `POST /coach/plan`, CLI `src/plan.py:162`): 생성하지 않고 요일 입력을 요구한다(v2 는 400 + 요일 선택 단계, CLI 는 안내 메시지).
  - v1 라우트(`/training/wizard/complete`·`/training/generate`): 요일 없이 `generate_weekly_plan` 을 불러 mask NULL 이면 생성이 막힌다. 대응하지 않는다(V1-13, v1 손상 허용).
  - 자동 경로(`weekly_adapt_job.run`·`rematch.py:82`·`plan_replan_service.py:128`): `WeekdaysRequired` 를 잡아 해당 실행에서 생성·저장하지 않고 사유를 로그에 남긴다(`weekly_adapt_job` 은 기존 rules_version<2 분기처럼 0 반환). 신규 생성은 mask 를 먼저 저장하므로 정상 흐름에서는 도달하지 않는 방어 분기다.
  - 삭제(PLN-23): 보류 중 기존 행 유지·'요일 입력 전까지 갱신 안 됨' 표시(PLN-15)와 기존 사용자 주간 적응 정지 안내(PLN-17)는 기존 플랜을 삭제하므로 작성하지 않는다.
  - 백테스트 경로(PLN-18 b): `plan_backtest.py:70-74`·`plan_backtest_replan.py:22-30` 은 현재 `rest_weekdays_mask=rest_mask(scn.days)` 만 쓰고 `generate_weekly_plan` 을 부르므로 mask NULL 이면 `WeekdaysRequired` 로 깨진다. **백테스트 입력(`Scenario`)에 요일 mask 를 지정**한다 — `Scenario.workout_weekdays_mask: int` 필드를 추가하고, 시나리오 실행 시 `upsert_user_training_prefs(conn, workout_weekdays_mask=scn.workout_weekdays_mask, rest_weekdays_mask=…)` 로 메모리 DB prefs 에 넣은 뒤 생성한다(운영 `resolve_run_weekdays` 경로를 그대로 탄다, 백테스트 전용 우회 없음). 격자 시나리오는 격자 정의의 `days` 와 `DAY_ORDER`(`plan_backtest.py:28`)로 만든 mask 를 **입력값으로 명시**해 넣고, `plan_backtest_replan` 의 `Scenario(**scn.__dict__)` 복제(`:53·81`)는 필드를 그대로 이어받는다. mask 미지정 시나리오는 생성 전에 구성 오류로 거부한다(`WeekdaysRequired` 를 결과 '실패'로 세지 않음). **이력 시나리오(PLN-22 b·PLN-25 b)**: `history_scenarios`(`plan_backtest.py:131-150`, `days=0`)도 mask 를 필수 입력으로 받는다 — 격자와 같은 `Scenario.workout_weekdays_mask` 필드를 쓰고, 없으면 같은 구성 오류로 거부(전체 요일·mask 무시 폴백 없음). mask 출처는 **시나리오 입력에 직접 명시(호출자 책임, PLN-25)** — `user_training_prefs`(단일 행, 시점별 이력 없음)의 현재 값 재사용이나 활동 요일 분포 추정은 하지 않는다. `history_scenarios` 는 mask 를 만들지 않고 호출자가 넘긴 값을 시나리오에 싣는다(인자 형태는 구현 시 확정). G1 게이트(`plan_gates.py:71`)는 백테스트 전용으로 유지(PLN-13).
- 삭제(PLN-23·PLN-27): 기존 v1 목표 즉시 재생성 제안(PLN-3 보강의 제안 배너·`regen-preview`)과 코치 화면 보류 배너(PLN-16, 트리거 상태 'active goal + mask NULL' 은 기존 플랜에서만 생김)는 기존 플랜 삭제로 대체되어 작성하지 않는다. 배너 삭제는 PLN-27 (a)로 유지 — 신규 생성의 요일 입력 요구(PLN-12)로 충분하다.
- 테이퍼 볼륨·마지막 롱런 시점, 컨디션 기반 변경(adjuster·weekly_adapt, ADR-035 확인 후)은 이 설계 범위 밖.

### 2.2 R2 — 플랜 소유권 + 교체 확인 + 복구
- `planned_workouts.goal_id INTEGER` 추가 + **planner 행 한정 CHECK `(source <> 'planner' OR goal_id IS NOT NULL)`**(PLN-19 재결정·PLN-20 e). 외부 계획 행(`source`=`'garmin'`·`'intervals'`, `plan_ingest.store_planned` 이 `source=source_system` 으로 기입)과 v1 `manual`·`imported` 행은 goal_id NULL 유지.
- **기존 플랜 전제(PLN-23):** 기존 훈련 플랜은 삭제하고 시작한다. goal_id 백필·dry-run 분포·범위 밖 고아 행 처리·외부/v1 행 귀속 코드는 작성하지 않는다(PLN-20 의 '고아 행 dry-run 후 삭제/귀속' 은 PLN-23 으로 대체). 삭제는 §2.4 일회성 운영 절차(PLN-24 대상 6종)로 v40 적용 전에 실행한다. 마이그레이션은 '`source='planner'` 행이 0 인 상태'를 전제로 한다.
- **마이그레이션 버전·순서(PLN-26 확정):** 현재 `SCHEMA_VERSION = 36`(`db_setup.py:32`), v37(`plan_adjustments` 재생성, `adjustment-signals.md`)·v38(가산 테이블, `adjustment-new-signals.md`·`race-calendar.md`)·v39(`goals.race_id` 백필, `race-calendar.md`)이 다른 번들에 배정돼 있으므로 이 번들은 그 뒤 **v40 하나**를 쓴다(2026-10-11 grep: 설계 폴더에서 v40 을 쓰는 다른 문서 없음, 다른 번들은 `SCHEMA_VERSION` 39 까지).
  - **v40 단일(PLN-26 (a) 병합 채택):** `ALTER TABLE planned_workouts ADD COLUMN goal_id INTEGER CHECK (source <> 'planner' OR goal_id IS NOT NULL)` + `ALTER TABLE user_training_prefs ADD COLUMN workout_weekdays_mask INTEGER`. 테이블 재생성·백필 없음. SQLite 는 CHECK 가 붙은 ADD COLUMN 시 기존 행을 검사하므로 planner 행이 남아 있으면 ALTER 가 `CHECK constraint failed` 로 실패 → 트랜잭션 롤백(로컬 SQLite 3.45.1 로 확인: planner 행 없으면 추가 성공·이후 goal_id NULL planner INSERT 거부, planner 행 있으면 추가 실패). **운영 SQLite 버전은 구현 첫 단계에서 확인**(PLN-26). 멱등: 컬럼이 있으면 skip. `PRAGMA integrity_check` 선행, 역마이그레이션 = 백업 복원. 분리안(v41 재생성)은 채택하지 않는다(PLN-26).
  - v39 와의 선후: 데이터 의존은 없다(`race_id` 를 읽지 않음). 순서는 번호 순차성 때문이며, v39 가 전진 전용(`race-calendar.md` §4)이므로 롤백은 v39 이후 상태로만 돌아간다.
- **PLN-21 해소:** v1 `manual`·`imported` 행이 CHECK 대상이 아니어서 v1 라우트 일몰과 마이그레이션의 선후 제약은 없다.
- **planner 행 INSERT 경로(grep 2026-10-11, `INTO planned_workouts`):** CHECK 이후 planner 행은 goal_id 를 채워야 한다.

  | 경로 | 위치 | 호출자 | 처리 |
  |---|---|---|---|
  | `planner.save_weekly_plan` | `planner.py:238`(→ `planner_store.py` 이동) | `plan_template_service.py:194`, `weekly_adapt_job.py:53`, `rematch.py:87`, CLI `plan.py:165` (v1 `views_training_wizard.py:352·411`·`views_training.py:240` 은 수정하지 않음, V1-13) | goal_id 인자 추가 |
  | `plan_replace.replace_range` | `plan_replace.py:53` | `plan_replan_service.py:130`, `plan_template_service.py:183`(빈 plan) | 행 dict 또는 인자로 goal_id 기입 |
  | replan 되돌리기 복원 | `plan_replan_service.py:237` | `plan_replans.replaced_json` 의 `deleted` 행을 컬럼 그대로 재INSERT | 신규 스냅샷은 goal_id 포함. 마이그레이션 이전 스냅샷 보충 코드는 작성하지 않음(PLN-23) — 이전 `plan_replans` 행은 §2.4 에서 삭제(PLN-24) |
  | PLN-1 복구(`restore`) | 신규(`goals.plan_snapshot_json`) | `POST /coach/plan/<id>/restore` | 스냅샷 행에 goal_id 포함 |
  | 외부 계획 수집 | `sync/plan_ingest.py:121`(`plan_ingest_intervals.py:73` 경유 포함) | Garmin·intervals 계획 수집 — 일반 sync 에 연결돼 있지 않고 CLI 수동 실행으로만 호출(PLN-24 결정 문구의 코드 확인) | 변경 없음(goal_id NULL, CHECK 대상 아님, PLN-20) |
  | v1 수동 추가·범위 복사 | `web/views_training_crud.py:39`(`manual`), `web/views_training_goal_crud.py:374`(`imported`) | v1 라우트 | 변경 없음(CHECK 대상 아님) |
  | v27 재생성 복사 | `db_schema_v27.py:22` | 과거 마이그레이션 | 영향 없음 |

  테스트 픽스처: `tests/` 에서 `INTO planned_workouts` 를 직접 쓰는 파일 32개 중 `'planner'` 를 포함하는 18개(문자열 기준, 구현 시 재확인)만 goal_id 필요(공용 헬퍼로 처리).
- `create_plan_from_template(..., expect_active_goal_id)`: 활성 플랜이 있는데 기대값이 다르면 `PlanConflict` → API 409 `ACTIVE_PLAN_EXISTS`(현재 플랜 요약 포함). 클라이언트는 확인 후 다시 보낸다(compare 의 `expect_anchor` 패턴 재사용).
- 교체(PLN-1): 이전 goal 은 `cancelled` 로 두고 그 goal_id 행은 삭제하지 않으며, `replace_range` snapshot 은 `goals.plan_snapshot_json` 에 보존. 취소 플랜 화면에 **복구 버튼** — `POST /coach/plan/<id>/restore` 가 대상 goal 을 active 로, 현재 active 를 cancelled 로 바꾼다(같은 409 확인 흐름).
- 조회(`get_active_plan(goal_id)`, 세션 상세)는 `goal_id` 로 필터하고 `goal.status` 를 응답에 실어 취소 플랜을 읽기 전용 표시(P-23).
- 메모(PLN-2): **날짜 기준 유지**(`user_inputs` 스키마·API 변경 없음). 플랜 교체와 무관한 훈련 기록으로 취급하며 화면에 "날짜별 메모" 로 표기.
- 시작 주(PLN-5): **생성일부터 시작**. 첫 주는 부분 주(생성일~일요일)이고 지난 날짜는 계획에 넣지 않는다. 주차 경계는 월요일 유지.

### 2.3 R3 — 전체 주차 읽기 모델 + 생성 직후 재매칭 + 판정 사유
- 신규 `src/services/plan_overview_service.py`: `get_plan_overview(conn, goal_id) -> {weeks:[{week_start, phase, planned_km, actual_km, run_days, rest_days, long_km, quality_n, compliance_pct}], basis}`. phase 는 `schedule_for_goal` 값 사용. API `GET /coach/plan/<id>/weeks`.
- `create_plan_from_template`·replan 적용·복구 후 `rematch.rematch(conn, start, min(end, today))` 호출(같은 트랜잭션 밖, 실패 시 로그만).
- `week_compliance` entry 에 `reason`(코드: `no_activity`, `pace_fast`, `volume_over`, `volume_under`, `cross`) 과 `actual_km`, `actual_pace` 추가. 판정(PLN-6): **둘 다 표시** — 대표 라벨은 볼륨 초과, 보조 라벨은 페이스 빠름(`reasons` 배열, 첫 원소가 대표).
- 헤더(PLN-7): 누적 지표에 서버 `basis: "cumulative"` 를 실어 **'누적(플랜 시작~어제)'** 라벨 + 기준 툴팁, 주간 목록은 `basis: "week"` 로 '이번 주' 표기.
- `_effective` 순위(PLN-10): **매칭된 행 최우선(출처 무관)** > 수락된 조정 행 > 미매칭 외부 행 > 미매칭 planner 행. 조정 행의 의미(대체인지 추가인지)는 구현 시 검토.
- 거리 비율 상한은 `high-severity-remaining.md` HSR-1 과 단일 결정: 같은 날 후보가 1개면 비율 무시, 여럿이면 1.6 유지(구현은 HSR 설계서 T-01 소관, 여기서는 reason 에 반영만).
- replan 되돌리기(PLN-8): 프런트에 확인 단계(확인 대화상자) 추가(P-20).
- 프런트: `PlanWeeksTable.svelte`(신규)로 주차 표, 주간 목록 행에 실제값·사유 표시.

### 2.4 기존 플랜 삭제 — 일회성 운영 절차 (PLN-23·PLN-24)
- **성격:** 운영 DB 에 대해 구현 단계에서 한 번 수행하는 **수동 운영 절차**다. **마이그레이션 코드가 아니다**(PLN-23) — `db_schema_v40`·`ensure_*`·앱 시작 경로·테스트에 삭제 로직을 넣지 않으며, 새 DB·다른 환경에서 자동으로 재실행되지 않는다. 실행 권한(bash·운영 DB 삭제)은 사용자가 승인했다(PLN-23, 실행은 대상·백업 확인 후).
- **삭제 대상(PLN-24, 6종):**

  | # | 대상 | 조건 | 비고 |
  |---|---|---|---|
  | ① | `session_outcomes` | 전체 행 | 훈련 결과 이력 — **건수 표시 후 재확인** |
  | ② | `plan_adjustments` | 전체 행 | `workout_id` FK 선언 없음(`db_schema_v31.py:10`) — 고아 방지 |
  | ③ | `plan_replans` | 전체 행 | 남기면 되돌리기(`plan_replan_service.py:237`)가 goal_id 없는 planner 행을 재INSERT 해 CHECK 에 걸림 |
  | ④ | `planned_workouts` planner 행 | `source='planner'` | v40 CHECK 전제 |
  | ⑤ | `planned_workouts` 외부 계획 행 | `source IN ('garmin','intervals')` | 일반 sync 에 연결돼 있지 않고 CLI 수동 실행으로만 유입 — 삭제 후 CLI 를 다시 돌리지 않으면 재유입 없음(재유입돼도 goal_id NULL 허용, PLN-20) |
  | ⑥ | `goals` | 결정 문구 'goals(active goal)' | 목표 이력 — **건수 표시 후 재확인**. cancelled·completed 목표 포함 여부는 §8-12 |

  대상 아님: v1 `manual`·`imported` 행(PLN-20, CHECK 대상 아님), 날짜별 메모 `user_inputs`(PLN-2).
- **순서:** 참조하는 쪽 먼저 — ① `session_outcomes`(`planned_id` 참조) → ② `plan_adjustments`(`workout_id`·`goal_id`) → ③ `plan_replans`(`goal_id`) → ④·⑤ `planned_workouts` → ⑥ `goals`. FK 선언이 없고 단일 트랜잭션이라 순서가 결과를 바꾸지는 않지만, 문장 단위로 건수를 확인하며 진행할 때 고아 참조가 생기지 않는 순서로 둔다.
- **절차:**
  0. 사전: 앱·백그라운드 작업(자동 동기화·`weekly_adapt_job`) 정지로 동시 쓰기 차단, 대상 DB 파일 경로 확정(사용자별 DB 각각). 원인 확인용 §5 실데이터 쿼리는 이 절차 **전에** 사본에서 실행.
  1. 백업: SQLite backup API(`sqlite3 … ".backup"`)로 같은 폴더에 `running.db.pre-plan-reset-<타임스탬프>` 생성(커밋 대상 아님), `PRAGMA integrity_check` = ok. 백업 실패 시 중단.
  2. 건수 표시: 6종 각각 `SELECT COUNT(*)`(위 조건 그대로)를 출력.
  3. 재확인: ①`session_outcomes`·⑥`goals` 건수를 사용자에게 보여 주고 재확인을 받는다(PLN-24). 확인이 없으면 절차를 중단한다(삭제 0건).
  4. 실행: 단일 트랜잭션(`BEGIN IMMEDIATE` … `COMMIT`)에서 위 순서로 `DELETE`. 트랜잭션 안에서 6종 재집계가 0 이 아니면 `ROLLBACK`.
  5. 사후 검증: 6종 건수 0, `source='planner'` 행 0(v40 전제), `PRAGMA integrity_check` = ok. 그 뒤 v40 적용.
- **롤백:** 단계 4 실패는 트랜잭션 롤백(원 상태 유지), 완료 후 되돌림은 단계 1 백업 파일 복원.
- **다른 마이그레이션과의 위치:** v40 은 '`source='planner'` 행 0' 을 전제하므로 이 절차가 v40 보다 먼저다. v37(`plan_adjustments` 재생성·재분류 백필)·v39(`goals.race_id` 백필, `race-calendar.md` §4)와의 선후는 §8-12.

### 기각된 대안
- B안(스키마 무변경, 스냅샷만)·C안(R1만 우선)은 PLN-9 로 기각. 단계 1(R1)·단계 2(R3)는 스키마 무관이라 먼저 진행 가능.

## 3. ID 처리 매핑

| ID | 처리 | 근거 |
|----|------|------|
| P-01, P-02 | 설계 R1 | 파생 필드 재생성 + 자동 교정(PLN-4) |
| P-03 | 설계 R2 | 409 확인 + 행·스냅샷 보존 + 복구(PLN-1) |
| P-04, P-05 | 참조 | server-input-origin-validation.md 2.4 |
| P-06 | 설계 R3 | 원인 확정. reason·두 라벨(PLN-6), `_effective`(PLN-10), 상한은 HSR-1 |
| P-07 | 설계 R3 | plan overview API·표 |
| P-08 | 설계 R1 | 지정 요일(`workout_weekdays_mask`) 준수·workout mask 우선(PLN-11)·미지정 시 생성 경로에서 입력 요구·자동 경로 보류(PLN-12)·휴식 하한 없음(PLN-13)·휴식 0~1일 저장 전 안내(PLN-14)·신규 목표 v2 전환(PLN-3). 기존 목표·행 대응(PLN-3 재생성 제안, PLN-15·16·17)은 기존 플랜 삭제로 대체(PLN-23) |
| P-09 | 설계 R3 | basis 필드 + '누적(플랜 시작~어제)' 라벨(PLN-7) |
| P-10 | BACKLOG 개별 | ACWR 범위를 메트릭 정의에서 받기, CTL 스케일 |
| P-11 | 설계 R2 | 생성일부터 시작(PLN-5) + 생성 후 재매칭 |
| P-12 | BACKLOG 개별 (+참조) | 목표 없음 문구 모순은 개별, 1초 입력은 입력 검증 참조 |
| P-13 | 참조 | error-retry-common.md(경로·재시도), 잘못된 파라미터 400 은 입력 검증 |
| P-14 | BACKLOG 개별 (+R2) | 단계 표시·입력 항목은 개별, 활성 시 진입점은 R2 409 흐름에 포함 |
| P-15 | 현행 유지 (+참조) | 메모 날짜 기준 유지(PLN-2), 길이·날짜 검증은 입력 검증 |
| P-16 | BACKLOG 개별 | 빈 메모 저장=삭제 허용 |
| P-17 | 참조 | Origin 관문(D-22 동일 원인) |
| P-18, P-19, P-21 | 참조 | 접근성 설계 |
| P-20 | 설계 R3 + BACKLOG 개별 | 되돌리기 확인 단계(PLN-8), title·문구는 개별 |
| P-22 | 참조 | 입력 검증 2.3 엔벨로프(라우팅 404 포함 여부 확인 요청) |
| P-23 | 설계 R2 | status 노출·읽기 전용·복구 버튼 |
| P-24 | BACKLOG 개별 | R1 후 rest 설명 해소, 버튼 허용 범위는 정책 |
| P-25 | BACKLOG 개별 | 로딩 스켈레톤 |

## 4. 변경 파일 표

| 파일 | 구분 | 내용 | 줄 수(예상) |
|------|------|------|------------|
| `src/training/plan_finalize.py` | 신규 | finalize_week, week_violations, 자동 교정·로그 | ~110 |
| `src/training/planner_store.py` | 신규 | planner.py 에서 저장·prefs 함수 이동, `workout_weekdays_mask` 읽기·쓰기, `resolve_run_weekdays`(workout 우선, NULL 이면 `WeekdaysRequired`) | ~110 |
| `src/training/planner.py` | 수정 | finalize 호출, 이동분 재수출, 부분 첫 주 | 300 → ~225 |
| `src/training/planner_v2.py` | 수정 | `_desc_locked` 표시(race·cold-start), 지정 요일 입력 | +10 |
| `src/db_schema_v40.py` | 신규 | (PLN-26 병합) `planned_workouts.goal_id INTEGER CHECK(source<>'planner' OR goal_id IS NOT NULL)` + `user_training_prefs.workout_weekdays_mask INTEGER NULL` ADD COLUMN, integrity_check·멱등(PLN-19·20). 기존 플랜 삭제 로직은 넣지 않음(§2.4, PLN-23) | ~40 |
| `src/db_setup.py` | 수정 | DDL(`goal_id INTEGER CHECK(...)`)·`SCHEMA_VERSION` 40·ensure 호출 | +10 |
| `src/training/plan_replace.py` | 수정 | INSERT 에 goal_id 기입 | +3 |
| `src/training/plan_backtest.py`, `plan_backtest_replan.py`, `scripts/plan_backtest.py` | 수정 | PLN-18·22·25: `Scenario.workout_weekdays_mask`(격자·이력 시나리오 모두 필수, 이력 시나리오는 호출자가 직접 명시), prefs 에 mask 기입 후 생성, mask 미지정 시나리오 거부 | +15 / +3 / +3 |
| `src/training/goals.py`, `plan_template_service.py` | 수정 | v2 일괄 전환, expect_active_goal_id, PlanConflict, 행 보존·snapshot 저장, restore, goal_id 기입, 재매칭 | +70 |
| `src/services/plan_service.py` | 수정 | goal_id 필터, status, basis | +20 |
| `src/services/plan_overview_service.py` | 신규 | 주차 요약 | ~110 |
| `src/training/week_compliance.py` | 수정 | reason(s)·actual 필드, 두 라벨, `_effective` 순위 | +25 (≤256) |
| `src/api/routes_plan.py` | 수정 | 409, mask NULL 시 run_weekdays 필수(`WeekdaysRequired` → 400), `/weeks`·`/restore` 라우트 | +40 |
| `src/services/weekly_adapt_job.py`, `src/training/rematch.py`, `src/services/plan_replan_service.py` | 수정 | `WeekdaysRequired` 시 생성·저장 보류·사유 로그(PLN-12), `save_weekly_plan`/`replace_range`·되돌리기 복원에 goal_id 전달 | +6 each |
| `src/plan.py` | 수정 | `WeekdaysRequired` 시 생성하지 않고 요일 입력 안내(CLI), `save_weekly_plan` 에 goal_id 전달 | +6 |
| `frontend/src/lib/api/plan.ts` | 수정 | 타입·getPlanWeeks·restore·409 처리 | +30 |
| `frontend/src/lib/planWeekdays.ts` | 신규 | 휴식 0~1일 판정(지정 요일 수 ≥ 6, PLN-14) 순수 함수 | ~20 |
| `frontend/src/lib/components/plan/PlanWeeksTable.svelte` | 신규 | 주차 표 | ~100 |
| `frontend/src/routes/coach/plan/[id]/+page.svelte`·`+page.ts`, `compare/+page.svelte`, 생성 폼 | 수정 | 표·사유·상태·복구, 교체·되돌리기 확인, 요일 선택·휴식 0~1일 저장 전 안내(PLN-14) | +90 |
| `tests/test_plan_finalize.py`, `test_plan_ownership.py`, `test_plan_overview.py`, `test_week_compliance_reason.py`, `test_plan_weekdays.py`, `test_db_schema_v40.py`, `test_plan_backtest_weekdays.py`, 프런트 `planWeekdays.test.ts` | 신규 | 아래 검증 | ~450 |
| 기존 테스트 픽스처(`INTO planned_workouts` 32개 중 planner 행을 넣는 약 18개 파일) | 수정 | goal_id 기입(공용 헬퍼) | — |

## 5. 단계·검증
1. R1: 7주 템플릿을 rv1 / rv2+plan_weeks NULL / rv2+plan_weeks=7 세 픽스처로 생성 → 교정 후 `week_violations == []`, 러닝 요일 ⊆ 지정 요일. 신규 목표는 plan_weeks 누락 입력에서도 v2 경로 진입. mask NULL + `run_weekdays` 없음 → 400, `run_weekdays` 전달 시 mask 저장, mask 설정 후 재생성 시 생략 가능. PLN-11: workout mask 와 rest mask 가 같은 요일을 지정하면 그 요일은 러닝(모순 저장도 허용). PLN-13: 7요일 지정 시 휴식 0일로 생성되고 `week_violations` 위반 없음. PLN-14: `planWeekdays` 가 지정 5개 → 안내 없음, 6·7개 → 안내 필요. PLN-12: mask NULL 에서 `weekly_adapt_job.run`·`rematch`·replan 은 저장 0건·사유 로그·예외 전파 없음, CLI 는 생성 없이 안내. 기존 planner 골든 테스트는 description 기대값만 갱신. PLN-18·22: 격자·이력 시나리오가 mask 를 입력으로 받아 `WeekdaysRequired` 없이 생성, 러닝 요일 ⊆ 시나리오 mask, mask 미지정 시나리오(이력 포함)는 구성 오류로 거부(결과 '실패' 집계에 안 들어감), `plan_backtest_replan` 복제 시 mask 유지, 기존 격자 통과 수 회귀 비교(`scripts/plan_backtest.py --engine v2|replan`).
2. R3 읽기: overview 합계 = planned_workouts 집계, 생성 직후 과거 날짜 매칭, 10/6~10/9 합성 주로 reasons(대표 volume_over·보조 pace_fast / 상한 탈락), ext2 픽스처(미매칭 외부 + 매칭 planner)에서 매칭 행이 effective, 수락 조정 행 > 미매칭 외부 행.
   **실데이터 확인 필요**(real_ui.db 사본, 읽기 전용 — 원인 확인용이므로 PLN-23 기존 플랜 삭제 전 사본에서 실행):
   | 확인 | 쿼리 | 판정 |
   |---|---|---|
   | goal 생성 경로 | `SELECT id,status,created_at,plan_rules_version,plan_weeks,race_date,distance_km FROM goals ORDER BY id;` | rv=1 또는 plan_weeks NULL이면 v1 경로 |
   | anchor별 규칙 버전 | `SELECT id,goal_id,anchor_monday,rules_version,status,created_at FROM plan_replans WHERE goal_id=1 ORDER BY anchor_monday;` | 주별 effective_rules_version 차이 |
   | 휴식 설정 | `SELECT rest_weekdays_mask,long_run_weekday_mask,max_q_days FROM user_training_prefs;` | mask=0이면 v1에서 휴식 0 |
   | 주간 러닝 일수 | `SELECT date(date,'weekday 0','-6 days') wk, SUM(workout_type<>'rest') runs, ROUND(SUM(distance_km),1) km FROM planned_workouts WHERE source='planner' GROUP BY wk ORDER BY wk;` | 7회가 이어지면 P-08 재현 |
   | P-06 주 매칭·외부 행 | `SELECT id,date,source,workout_type,distance_km,matched_activity_id FROM planned_workouts WHERE date BETWEEN '2026-10-05' AND '2026-10-11' ORDER BY date,id;` | 같은 날 외부 미매칭 + planner 매칭이면 PLN-10 해당 |
3. R2: 기존 플랜 삭제(§2.4 운영 절차, 코드·테스트 없음) — 백업 파일 존재·`integrity_check` ok, session_outcomes·goals 건수 재확인 기록, 사후 6종 건수 0. 그 뒤 마이그레이션 — 운영 SQLite 버전 확인(PLN-26), `workout_weekdays_mask` 기본 NULL, (PLN-19·20) planner 행 없는 DB 에서 적용 후 planner 행 goal_id NULL INSERT 거부·`garmin`/`intervals`/`manual` 행 goal_id NULL INSERT 허용·`integrity_check` ok·재실행 멱등, planner 행이 남은 DB 에서는 적용 실패·롤백·원 테이블 불변(전제 위반 검출). INSERT 경로 표의 planner 경로마다 goal_id 기입 테스트(되돌리기 복원은 신규 스냅샷 기준), 409 → 확인 재전송 → 이전 플랜 cancelled·행 보존, restore 후 active 교대, 취소 플랜 세션 응답 status=cancelled, 일요일 생성 시 첫 주 = 그 일요일 하루, 메모는 교체 전후 같은 날짜에서 동일.
4. 브라우저(DB 사본): 375/1280px 에서 /coach/plan/{id} 주차 표·사유·두 라벨, 헤더 '누적(플랜 시작~어제)' 툴팁, compare 교체 확인, 복구 버튼, replan 되돌리기 확인, 생성 폼 요일 선택·6~7요일 지정 시 저장 전 1회 안내(취소 시 요청 없음). `pytest`·`check_docs.py`·프런트 테스트 통과.
- 호환성: 기존 훈련 플랜은 삭제하고 시작한다(PLN-23, 대상·절차 §2.4 — PLN-24) — 기존 플랜·목표를 위한 이행·완충 코드는 없다. goal_id 는 planner 행만 CHECK 로 필수, 외부(garmin·intervals)·v1 행은 NULL(PLN-20). `workout_weekdays_mask` NULL 기본, 신규 생성 시 요일 입력으로 채워진다(PLN-12). 보존된 취소 플랜 행이 날짜 기준 조회에 섞이지 않도록 v2 서비스는 goal_id 필터, 날짜 기준 경로는 §8-5 확인 결과에 따라 처리. v1 화면·경로는 깨져도 허용하며 보호·호환 코드를 두지 않는다(V1-1·V1-13). 알고리즘 출력(설명·요일)이 바뀌므로 ADR-042 에 따라 버전/algo_changelog 항목 필요 여부 확인.

## 6. 결정
- PLN-1~27, 연관 HSR-1·V1-2·V1-13: 결정 완료(PLN-19 는 PLN-20 으로 재결정, PLN-21 은 PLN-20 으로 해소, PLN-24 = PLN-23 삭제 범위, PLN-25 = PLN-22 mask 출처, PLN-26 = v40 단일, PLN-27 = PLN-16 배너 삭제 유지)(표 참조, `decisions-table.md` 2026-10-11). 본문 §2 각 항목에 반영.

## 7. 범위 밖 메모
- `planned_workouts` INSERT 경로의 goal_id 기입은 §2.2 표로 이동(PLN-19). garmin_push(`garmin_workout_id` UPDATE 만)·calendar_feed(조회)는 INSERT 하지 않아 §8-5 goal_id 필터 범위 문제로만 남는다.
- compare 의 "달성 가능성" 계산(P-12)은 예측 묶음(T-08..T-13) 공식과 일치 여부 확인 필요.
- 외부 계획 행의 활동 선점은 합성 재현에서 결과 불변으로 확인. 남은 것은 §5 쿼리로 확인하는 `_effective` 해당 여부(PLN-10).
- `src/training/planner_rules.py` 가 이미 325줄(300줄 규칙 초과). 이번 설계는 이 파일을 건드리지 않으며 분리는 별도 작업.

## 8. 동기화 중 발견한 모호점
해소된 항목(1·3·7·8, 8차에서 9=PLN-25·10=PLN-26·11=PLN-24)은 삭제했다. 다른 절의 '§8-n' 참조가 유지되도록 번호는 그대로 둔다.
- **8-2.** PLN-5 부분 첫 주와 v2 주 단위 로직(`plan_replans.anchor_monday`, `schedule_for_goal` 주차·phase, 주간 볼륨 목표)의 처리 방식 — 결정표 "설계에서 정리", 미정.
- **8-4.** PLN-14 안내 문구는 구현 단계에서 후보 제시 후 사용자 확정.
- **8-5.** PLN-1 행 보존 시 날짜 기준 읽기 경로(`matcher`/`match_week_activities`, `week_compliance`, calendar_feed, garmin_push)에서 두 플랜 행 겹침 — goal_id 필터 적용 범위 미정.
- **8-6.** PLN-10 "수락된 조정 행" 식별 컬럼(`source` 값 등)이 `planned_workouts` DDL 에 없음 — 구현 시 확인.
- **8-12. 열린 질문(PLN-24 후속, §2.4):** (a) `goals` 삭제 범위 — 결정 문구가 'goals(active goal)' 이라 cancelled·completed 목표도 지우는지 불명확(PLN-24 근거는 active goal 잔존 문제). (b) 다른 번들 마이그레이션과의 선후 — v39(`race-calendar.md` §4)는 비활성 목표까지 `race_calendar` 행으로 백필하고 `goals.race_id`·`ux_goals_race` 를 만든다. §2.4 를 v39 **전**에 하면 백필 대상이 줄고, **후**에 하면 삭제된 목표를 가리키던 `race_calendar` 행(`origin='goal'`)이 남는다. v37(`plan_adjustments` 재생성·재분류 백필, `adjustment-signals.md` §3.9)도 §2.4 ② 이후면 빈 테이블 재생성이 된다. 실행 시점(v37 전 / v39 전 / v39 후~v40 전)과 `race_calendar` 정리 여부는 결정 기록이 없다.
