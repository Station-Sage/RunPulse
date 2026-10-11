# 설계: 훈련 계획 묶음 (P-01~P-25)

- 대상: `ux-review-2026-10/05-coach-plan.md` P-01~P-25 · 작성일 2026-10-11 · 상태: 결정 확정(2026-10-11, PLN-1~19), 구현 전 — 실데이터 확인·후속 확인 항목 남음(§5, §8)
- 변경 이력: 2026-10-11 원인 검증 반영 — P-06(매칭 비율 상한·판정 순서·_effective 순위), P-08(v1 폴백·운영 경로 휴식 보장 부재) 원인 확정 및 실데이터 확인 항목 추가
- 변경 이력: 2026-10-11 설계서 동기화 — `decisions-table.md` PLN-1~10 결정을 본문(설계안·변경 파일·단계·검증·호환성)에 반영, HSR-1 과의 단일 결정 관계 반영
- 변경 이력: 2026-10-11 PLN-3 보강 반영 — 지정 요일 저장 `user_training_prefs.workout_weekdays_mask`(NULL=미지정), 기존 v1 목표 즉시 재생성 제안(미리보기·확인, 자동 재생성 아님). 결정 섹션 축약
- 변경 이력: 2026-10-11 2차 동기화 — PLN-11(workout mask 우선)·PLN-12(mask NULL 이면 모든 생성 경로에서 요일 입력 전 생성 보류)·PLN-13(최소 휴식일 하한 없음) 반영, §8 해소 항목 축약
- 변경 이력: 2026-10-11 3차 동기화 — PLN-14(휴식 0~1일 저장 전 1회 안내)·PLN-15(보류 중 기존 행 유지 + '요일 입력 전까지 갱신 안 됨' 표시)·PLN-16(코치 화면 배너, v1 범위 제외)·PLN-17(요일 입력 전까지 주간 적응 정지 + 안내) 반영. v1 변경 파일·단계 제거
- 변경 이력: 2026-10-11 4차 동기화 — V1-1(v1 화면·경로는 v2 완료 시 일몰, 설계·검증·호환성에서 고려하지 않음): 레거시 v1 UI 호출·호환 서술 제거. 'v1 템플릿/v1 폴백/v1 목표'(plan_weeks NULL·rules_version<2 데이터·알고리즘 용어)는 유지
- 변경 이력: 2026-10-11 5차 동기화 — V1-1 정정·V1-2(v1 일몰 = UI·라우트 일몰, 공유 파일·함수 유지): §2 PLN-12 에 v1 위저드 mask NULL 위험을 '라우트 일몰 시 소멸하는 위험'으로 한 줄 복원(grep 재확인)
- 변경 이력: 2026-10-11 6차 동기화 — PLN-18(백테스트 `plan_backtest*` 입력에 요일 mask 지정: §2.1·§4·§5), PLN-19(`planned_workouts.goal_id` 이번 작업에서 NOT NULL 승격, 백필 완료 후: §2.2 마이그레이션 순서·NULL 잔존 처리·INSERT 경로 grep, §4·§5·호환성), V1-2 정합 재확인(v1 라우트의 INSERT 경로는 라우트 일몰 시 소멸, 공유 함수 `save_weekly_plan`·`replace_range` 는 유지)
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
  - 사용자 요청 경로(v2 `POST /coach/plan`·`regen-preview`, CLI `src/plan.py:162`): 생성하지 않고 요일 입력을 요구한다(v2 는 400 + 요일 선택 단계, CLI 는 안내 메시지).
  - v1 라우트(라우트 일몰 시 소멸하는 위험, V1-2): `/training/wizard/complete`(`views_training_wizard.py:351·410`)·`/training/generate`(`views_training.py:239`)는 요일 없이 `generate_weekly_plan` 을 호출하고, 위저드는 생성 전에 미래 planner 행 DELETE·`add_goal` 을 커밋(`:331-334·366·381`)하므로 mask NULL 이면 `WeekdaysRequired` 로 생성이 막혀 플랜 행이 빈다(`except Exception` 으로 500 은 없음). 라우트 일몰 전까지 존재(2026-10-11 grep 재확인).
  - 자동 경로(`weekly_adapt_job.run`·`rematch.py:82`·`plan_replan_service.py:128`): **안전한 보류** — 해당 실행에서 생성·저장하지 않고 기존 `planned_workouts` 행을 그대로 둔 채(PLN-15) 사유를 로그에 남긴다(`weekly_adapt_job` 은 기존 rules_version<2 분기처럼 0 반환). 기존 사용자(goal 1 등)도 요일 입력 전까지 **주간 적응을 정지**한다(PLN-17, mask 추론·마지막 규칙 1회 계속 없음).
  - 백테스트 경로(PLN-18 b): `plan_backtest.py:70-74`·`plan_backtest_replan.py:22-30` 은 현재 `rest_weekdays_mask=rest_mask(scn.days)` 만 쓰고 `generate_weekly_plan` 을 부르므로 mask NULL 이면 `WeekdaysRequired` 로 깨진다. **백테스트 입력(`Scenario`)에 요일 mask 를 지정**한다 — `Scenario.workout_weekdays_mask: int` 필드를 추가하고, 시나리오 실행 시 `upsert_user_training_prefs(conn, workout_weekdays_mask=scn.workout_weekdays_mask, rest_weekdays_mask=…)` 로 메모리 DB prefs 에 넣은 뒤 생성한다(운영 `resolve_run_weekdays` 경로를 그대로 탄다, 백테스트 전용 우회 없음). 격자 시나리오는 격자 정의의 `days` 와 `DAY_ORDER`(`plan_backtest.py:28`)로 만든 mask 를 **입력값으로 명시**해 넣고, `plan_backtest_replan` 의 `Scenario(**scn.__dict__)` 복제(`:53·81`)는 필드를 그대로 이어받는다. mask 미지정 시나리오는 생성 전에 구성 오류로 거부한다(`WeekdaysRequired` 를 결과 '실패'로 세지 않음). 이력 시나리오의 mask 는 §8-9. G1 게이트(`plan_gates.py:71`)는 백테스트 전용으로 유지(PLN-13).
  - 보류 표시·안내(PLN-15·16·17): 플랜 읽기 응답(`plan_service`·`/weeks`)에 `weekdays_required: true`(mask NULL 이고 active goal 존재)를 싣고, v2 플랜 화면은 기존 행을 그대로 보여 주며 '요일 입력 전까지 갱신 안 됨' 표시를 단다. 안내 채널은 **코치 화면 배너**(요일 입력으로 연결, 주간 적응 정지 사실 포함). 배너 외 알림 채널은 두지 않는다. 문구는 구현 단계에서 후보 제시.
- 기존 v1 목표(PLN-3, goal 1 등 — rules_version<2 또는 plan_weeks NULL 인 active goal): **즉시 재생성을 제안**하되 자동 재생성은 하지 않는다. 플랜 화면에 제안 배너 → `GET /coach/plan/<id>/regen-preview`(저장 없이 v2 초안 주차 요약 + 현행 대비) 미리보기 → 사용자 확인 시 PLN-1 교체 흐름(이전 플랜 cancelled·행 보존·복구 가능)으로 재생성. mask 가 NULL 이면 미리보기 전에 요일 선택을 받는다. 마이그레이션·동기화는 기존 목표를 건드리지 않는다. 테이퍼 볼륨·마지막 롱런 시점, 컨디션 기반 변경(adjuster·weekly_adapt, ADR-035 확인 후)은 이 설계 범위 밖.

### 2.2 R2 — 플랜 소유권 + 교체 확인 + 복구
- `planned_workouts.goal_id` 추가 + 백필 + **NOT NULL 승격을 이번 작업에서 수행**(PLN-19 a, 백필 완료 후). 백필: 각 goal 의 `_plan_date_range` 에 들어가는 planner 행에 goal_id 기입, 겹치면 최신 goal.
- **마이그레이션 버전·순서(제안):** 현재 `SCHEMA_VERSION = 36`(`db_setup.py:32`), v37(`plan_adjustments` 재생성)·v38(가산 테이블)·v39(`goals.race_id` 백필, `race-calendar.md`)이 다른 번들에 배정돼 있으므로 이 번들은 그 뒤에 둔다.
  - **v40** = `planned_workouts.goal_id INTEGER NULL` + `user_training_prefs.workout_weekdays_mask INTEGER NULL` 가산(`ALTER … ADD COLUMN`) + goal_id 백필. dry-run(`dry_run=True`: 기입 n·NULL 잔존 n·잔존 행 `source`/`source_system` 분포·샘플 id) 공유, 멱등(컬럼 있으면 skip, 백필은 `WHERE goal_id IS NULL` 만).
  - **v41** = NOT NULL 승격. SQLite 는 컬럼 제약을 바꿀 수 없으므로 v27 패턴(`db_schema_v27.py`: `planned_workouts__vNN` 생성 → `INSERT … SELECT` → RENAME, 인덱스 재생성, 행 수·id 일치 검증)으로 재생성. `running.db.bak-v40-<ts>` 백업 + `PRAGMA integrity_check` 선행. 백필과 버전을 나눠 사본에서 v40 결과(NULL 잔존 0)를 확인한 뒤 v41 을 적용할 수 있게 한다. 역마이그레이션 = 백업 복원.
  - v39 와의 선후: 데이터 의존은 없다(goal_id 백필은 `goals` 날짜 범위만 쓰고 `race_id` 를 읽지 않음). 순서는 번호 순차성 때문이며, v39 가 전진 전용(`race-calendar.md` §4)이므로 v40·v41 롤백은 v39 이후 상태로만 돌아간다.
- **NULL 행 잔존 시 처리:** v41 은 승격 전 `SELECT COUNT(*) FROM planned_workouts WHERE goal_id IS NULL` 이 0 이 아니면 **승격하지 않고 트랜잭션 롤백 + 잔존 분포 로그**(원 테이블·v40 결과 유지, 앱 기동은 계속). 잔존이 예상되는 행: ① 외부 계획 행(`sync/plan_ingest.store_planned`, 이전 설계는 'NULL 유지') ② 어떤 goal 범위에도 들지 않는 planner 행(범위 밖 고아) ③ v1 화면의 `manual`·`imported` 행. ①~③을 어느 goal 로 귀속할지(또는 삭제·별도 보관할지)는 결정 문구에 없다 → §8-8 열린 질문. 이 질문이 풀리기 전에는 ① 때문에 실데이터에서 v41 이 중단된다.
- **승격 전 goal_id NULL 가능 INSERT 경로(grep 2026-10-11, `INTO planned_workouts`):** 승격 시 모두 goal_id 를 채워야 한다.

  | 경로 | 위치 | 호출자 | 처리 |
  |---|---|---|---|
  | `planner.save_weekly_plan` | `planner.py:238`(→ `planner_store.py` 이동) | `plan_template_service.py:194`, `weekly_adapt_job.py:53`, `rematch.py:87`, CLI `plan.py:165`, v1 `views_training_wizard.py:352·411`·`views_training.py:240` | goal_id 인자 추가(공유 함수 유지, V1-2 — v1 호출자는 라우트 일몰 시 소멸) |
  | `plan_replace.replace_range` | `plan_replace.py:53` | `plan_replan_service.py:130`, `plan_template_service.py:183`(빈 plan) | 행 dict 또는 인자로 goal_id 기입 |
  | replan 되돌리기 복원 | `plan_replan_service.py:237` | `plan_replans.replaced_json` 의 `deleted` 행을 컬럼 그대로 재INSERT | v40 이전 저장 스냅샷에는 `goal_id` 키가 없음 → `plan_replans.goal_id` 로 보충 |
  | PLN-1 복구(`restore`) | 신규(`goals.plan_snapshot_json`) | `POST /coach/plan/<id>/restore` | 스냅샷 행에 goal_id 포함, 없으면 대상 goal id |
  | 외부 계획 수집 | `sync/plan_ingest.py:121` | Garmin 등 동기화 | goal 없는 외부 행 — §8-8 결정 전까지 승격 차단 요인 |
  | v1 수동 추가 | `web/views_training_crud.py:39`(`source='manual'`) | v1 라우트 | 라우트 일몰 시 소멸(V1-2). 일몰 전 v41 이면 INSERT 실패 → §8-8 |
  | v1 범위 복사 | `web/views_training_goal_crud.py:374`(`source='imported'`) | v1 라우트 | 동일 |
  | v27 재생성 복사 | `db_schema_v27.py:22` | 과거 마이그레이션 | v40 이전 실행, 영향 없음 |

  테스트 픽스처: `tests/` 에서 `INTO planned_workouts` 를 직접 쓰는 파일 32개 — v41 이후 goal_id 필요(공용 헬퍼로 처리).
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
| P-08 | 설계 R1 | 지정 요일(`workout_weekdays_mask`) 준수·workout mask 우선(PLN-11)·미지정 시 생성 경로에서 입력 요구·자동 경로 보류(PLN-12)·휴식 하한 없음(PLN-13)·휴식 0~1일 저장 전 안내(PLN-14)·보류 중 행 유지+표시(PLN-15)·코치 배너(PLN-16)·주간 적응 정지(PLN-17)·신규 목표 v2 전환·기존 목표 재생성 제안(PLN-3) |
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
| `src/db_schema_v40.py` | 신규 | `planned_workouts.goal_id` NULL 가산 + 백필(겹치면 최신 goal), `user_training_prefs.workout_weekdays_mask INTEGER NULL`, dry_run·멱등 | ~80 |
| `src/db_schema_v41.py` | 신규 | `planned_workouts` 재생성으로 `goal_id NOT NULL` 승격(PLN-19), 백업·integrity_check·NULL 잔존 시 중단 롤백·행 수/id 검증·멱등 | ~80 |
| `src/db_setup.py` | 수정 | DDL(`goal_id INTEGER NOT NULL`)·`SCHEMA_VERSION` 41·ensure 호출 | +10 |
| `src/training/plan_replace.py`, `src/sync/plan_ingest.py` | 수정 | INSERT 에 goal_id 기입(plan_ingest 는 §8-8 결정 후) | +각 3 |
| `src/training/plan_backtest.py`, `plan_backtest_replan.py`, `scripts/plan_backtest.py` | 수정 | PLN-18: `Scenario.workout_weekdays_mask`, prefs 에 mask 기입 후 생성, mask 미지정 시나리오 거부 | +15 / +3 / +3 |
| `src/training/goals.py`, `plan_template_service.py` | 수정 | v2 일괄 전환, expect_active_goal_id, PlanConflict, 행 보존·snapshot 저장, restore, goal_id 기입, 재매칭, v1 목표 판별·재생성 미리보기(저장 없음) | +80 |
| `src/services/plan_service.py` | 수정 | goal_id 필터, status, basis, `weekdays_required`(PLN-15·17) | +25 |
| `src/services/plan_overview_service.py` | 신규 | 주차 요약 | ~110 |
| `src/training/week_compliance.py` | 수정 | reason(s)·actual 필드, 두 라벨, `_effective` 순위 | +25 (≤256) |
| `src/api/routes_plan.py` | 수정 | 409, mask NULL 시 run_weekdays 필수(`WeekdaysRequired` → 400), `/weeks`·`/restore`·`/regen-preview` 라우트 | +50 |
| `src/services/weekly_adapt_job.py`, `src/training/rematch.py`, `src/services/plan_replan_service.py` | 수정 | `WeekdaysRequired` 시 생성·저장 보류(기존 행 유지)·사유 로그(PLN-12), `save_weekly_plan`/`replace_range` 에 goal_id 전달, 되돌리기 복원 행 goal_id 보충(PLN-19) | +8 each |
| `src/plan.py` | 수정 | `WeekdaysRequired` 시 생성하지 않고 요일 입력 안내(CLI), `save_weekly_plan` 에 goal_id 전달 | +6 |
| `frontend/src/lib/api/plan.ts` | 수정 | 타입(`weekdays_required` 포함)·getPlanWeeks·restore·regenPreview·409 처리 | +40 |
| `frontend/src/lib/planWeekdays.ts` | 신규 | 휴식 0~1일 판정(지정 요일 수 ≥ 6, PLN-14) 순수 함수 | ~20 |
| `frontend/src/lib/components/plan/PlanWeeksTable.svelte` | 신규 | 주차 표 | ~100 |
| `frontend/src/routes/coach/plan/[id]/+page.svelte`·`+page.ts`, `compare/+page.svelte`, 생성 폼 | 수정 | 표·사유·상태·복구, 교체·되돌리기 확인, 요일 선택·휴식 0~1일 저장 전 안내(PLN-14), '요일 입력 전까지 갱신 안 됨' 표시(PLN-15), v1 목표 재생성 제안 배너·미리보기 | +120 |
| 코치 화면(`frontend/src/routes/coach/+page.svelte` 또는 공용 배너 컴포넌트, 구현 시 위치 확인) | 수정 | `weekdays_required` 시 요일 입력 배너(PLN-16·17) | +20 |
| `tests/test_plan_finalize.py`, `test_plan_ownership.py`, `test_plan_overview.py`, `test_week_compliance_reason.py`, `test_plan_weekdays.py`, `test_db_schema_v40.py`, `test_db_schema_v41.py`, `test_plan_backtest_weekdays.py`, 프런트 `planWeekdays.test.ts` | 신규 | 아래 검증 | ~550 |
| 기존 테스트 픽스처(`INTO planned_workouts` 32개 파일) | 수정 | goal_id 기입(공용 헬퍼) | — |

## 5. 단계·검증
1. R1: 7주 템플릿을 rv1 / rv2+plan_weeks NULL / rv2+plan_weeks=7 세 픽스처로 생성 → 교정 후 `week_violations == []`, 러닝 요일 ⊆ 지정 요일. 신규 목표는 plan_weeks 누락 입력에서도 v2 경로 진입. mask NULL + `run_weekdays` 없음 → 400, `run_weekdays` 전달 시 mask 저장, mask 설정 후 재생성 시 생략 가능. PLN-11: workout mask 와 rest mask 가 같은 요일을 지정하면 그 요일은 러닝(모순 저장도 허용). PLN-13: 7요일 지정 시 휴식 0일로 생성되고 `week_violations` 위반 없음. PLN-14: `planWeekdays` 가 지정 5개 → 안내 없음, 6·7개 → 안내 필요. PLN-12·15·17: mask NULL 에서 `weekly_adapt_job.run`·`rematch`·replan 은 저장 0건·기존 행 불변·사유 로그(goal 1 형태 기존 사용자 픽스처 포함, 주간 적응 결과 없음), 플랜 읽기 응답 `weekdays_required=true`·mask 저장 후 false, CLI 는 생성 없이 안내. 기존 planner 골든 테스트는 description 기대값만 갱신. PLN-18: 격자 시나리오가 mask 를 입력으로 받아 `WeekdaysRequired` 없이 생성, 러닝 요일 ⊆ 시나리오 mask, mask 미지정 시나리오는 구성 오류로 거부(결과 '실패' 집계에 안 들어감), `plan_backtest_replan` 복제 시 mask 유지, 기존 격자 통과 수 회귀 비교(`scripts/plan_backtest.py --engine v2|replan`).
2. R3 읽기: overview 합계 = planned_workouts 집계, 생성 직후 과거 날짜 매칭, 10/6~10/9 합성 주로 reasons(대표 volume_over·보조 pace_fast / 상한 탈락), ext2 픽스처(미매칭 외부 + 매칭 planner)에서 매칭 행이 effective, 수락 조정 행 > 미매칭 외부 행.
   **실데이터 확인 필요**(real_ui.db 사본, 읽기 전용):
   | 확인 | 쿼리 | 판정 |
   |---|---|---|
   | goal 생성 경로 | `SELECT id,status,created_at,plan_rules_version,plan_weeks,race_date,distance_km FROM goals ORDER BY id;` | rv=1 또는 plan_weeks NULL이면 v1 경로 |
   | anchor별 규칙 버전 | `SELECT id,goal_id,anchor_monday,rules_version,status,created_at FROM plan_replans WHERE goal_id=1 ORDER BY anchor_monday;` | 주별 effective_rules_version 차이 |
   | 휴식 설정 | `SELECT rest_weekdays_mask,long_run_weekday_mask,max_q_days FROM user_training_prefs;` | mask=0이면 v1에서 휴식 0 |
   | 주간 러닝 일수 | `SELECT date(date,'weekday 0','-6 days') wk, SUM(workout_type<>'rest') runs, ROUND(SUM(distance_km),1) km FROM planned_workouts WHERE source='planner' GROUP BY wk ORDER BY wk;` | 7회가 이어지면 P-08 재현 |
   | P-06 주 매칭·외부 행 | `SELECT id,date,source,workout_type,distance_km,matched_activity_id FROM planned_workouts WHERE date BETWEEN '2026-10-05' AND '2026-10-11' ORDER BY date,id;` | 같은 날 외부 미매칭 + planner 매칭이면 PLN-10 해당 |
3. R2: 마이그레이션 백필 테스트(겹치는 goal)·`workout_weekdays_mask` 기본 NULL, (PLN-19) v40 사본 dry-run 분포·재실행 멱등, v41: NULL 0 이면 승격 후 goal_id NULL INSERT 거부·행 수/id 일치·`integrity_check` ok·재실행 멱등, NULL 잔존 픽스처(외부 행 1건)면 승격 중단·원 테이블 불변·잔존 분포 로그, INSERT 경로 표의 v2 경로마다 goal_id 기입 테스트(되돌리기 복원은 goal_id 없는 옛 스냅샷 포함), v1 목표(rv1 또는 plan_weeks NULL)에 재생성 제안 노출·`regen-preview` 는 DB 무변경·마이그레이션/동기화 후에도 기존 목표 행 불변, 확인 시 교체 흐름으로 재생성, 409 → 확인 재전송 → 이전 플랜 cancelled·행 보존, restore 후 active 교대, 취소 플랜 세션 응답 status=cancelled, 일요일 생성 시 첫 주 = 그 일요일 하루, 메모는 교체 전후 같은 날짜에서 동일.
4. 브라우저(DB 사본): 375/1280px 에서 /coach/plan/{id} 주차 표·사유·두 라벨, 헤더 '누적(플랜 시작~어제)' 툴팁, compare 교체 확인, 복구 버튼, replan 되돌리기 확인, 생성 폼 요일 선택·6~7요일 지정 시 저장 전 1회 안내(취소 시 요청 없음), mask NULL 상태에서 플랜 화면 기존 행 + '요일 입력 전까지 갱신 안 됨' 표시와 코치 화면 배너, goal 1 재생성 제안 배너·미리보기. `pytest`·`check_docs.py`·프런트 테스트 통과.
- 호환성: goal_id 는 v40 에서 NULL 허용으로 들어오고 v41 에서 NOT NULL(PLN-19). 외부 행·v1 수동 행 귀속은 §8-8 미정 — 정해지기 전에는 v41 이 중단되어 NULL 허용 상태로 남는다. `workout_weekdays_mask` NULL 기본 — 기존 사용자는 다음 생성·재생성 시점까지 영향 없으나, PLN-12·17 로 자동 경로(weekly_adapt·rematch·replan)는 요일 입력 전까지 보류되어 주간 적응이 멈추고 기존 행은 유지된다(PLN-15, 코치 배너로 안내), 기존 v1 목표는 사용자 확인 전까지 그대로. 보존된 취소 플랜 행이 날짜 기준 조회에 섞이지 않도록 v2 서비스는 goal_id 필터, 날짜 기준 경로는 §8-5 확인 결과에 따라 처리. v1 화면·경로 호환은 고려하지 않는다(일몰 예정, V1-1). 알고리즘 출력(설명·요일)이 바뀌므로 ADR-042 에 따라 버전/algo_changelog 항목 필요 여부 확인.

## 6. 결정
- PLN-1~19, 연관 HSR-1·V1-2: 결정 완료(표 참조, `decisions-table.md` 2026-10-11). 본문 §2 각 항목에 반영.

## 7. 범위 밖 메모
- `planned_workouts` INSERT 경로의 goal_id 기입은 §2.2 표로 이동(PLN-19). garmin_push(`garmin_workout_id` UPDATE 만)·calendar_feed(조회)는 INSERT 하지 않아 §8-5 goal_id 필터 범위 문제로만 남는다.
- compare 의 "달성 가능성" 계산(P-12)은 예측 묶음(T-08..T-13) 공식과 일치 여부 확인 필요.
- 외부 계획 행의 활동 선점은 합성 재현에서 결과 불변으로 확인. 남은 것은 §5 쿼리로 확인하는 `_effective` 해당 여부(PLN-10).
- `src/training/planner_rules.py` 가 이미 325줄(300줄 규칙 초과). 이번 설계는 이 파일을 건드리지 않으며 분리는 별도 작업.

## 8. 동기화 중 발견한 모호점
1. 해소(PLN-13·PLN-14).
2. PLN-5 부분 첫 주와 v2 주 단위 로직(`plan_replans.anchor_monday`, `schedule_for_goal` 주차·phase, 주간 볼륨 목표)의 처리 방식 — 결정표 "설계에서 정리", 미정.
3. 해소(PLN-11).
4. 해소(PLN-12·15·16·17). 남은 것: 안내·표시 문구(PLN-14 안내, PLN-15 표시, PLN-16 배너)는 구현 단계에서 후보 제시 후 사용자 확정.
5. PLN-1 행 보존 시 날짜 기준 읽기 경로(`matcher`/`match_week_activities`, `week_compliance`, calendar_feed, garmin_push)에서 두 플랜 행 겹침 — goal_id 필터 적용 범위 미정.
6. PLN-10 "수락된 조정 행" 식별 컬럼(`source` 값 등)이 `planned_workouts` DDL 에 없음 — 구현 시 확인.
7. V1-1 적용 해석: 'v1 목표'(rules_version<2 또는 plan_weeks NULL 인 기존 goal)·'v1 템플릿/폴백'(planner 알고리즘)은 레거시 UI 가 아니라 데이터로 남으므로 재생성 제안·검증을 유지했다. NOT NULL 승격 여부는 해소(PLN-19) — 남은 외부 행 귀속은 §8-8.
8. **열린 질문(PLN-19):** NOT NULL 승격 시 goal 이 없는 행의 처리 — 외부 계획 행(`plan_ingest`, 이전 설계의 'NULL 유지'와 충돌), goal 범위 밖 planner 고아 행, v1 `manual`·`imported` 행을 활성 goal 귀속/삭제/별도 보관 중 무엇으로 할지 결정 문구에 없다. 또 v1 라우트 일몰이 v41 보다 늦으면 일몰 전까지 해당 INSERT 가 실패한다 — 일몰과 v41 선후 확인 필요. 현재 설계는 잔존 시 승격 중단(안전 쪽)만 적었다.
9. **열린 질문(PLN-18):** 이력(history) 시나리오는 `days=0`(`plan_backtest.py:143`)으로 만들어져 지정할 요일이 입력에 없다 — 이력 시나리오 mask 를 무엇으로 줄지(고정 기본값, 실DB `user_training_prefs` 값, 실제 활동 요일 등) 결정 문구에 없다.
