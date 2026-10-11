# race_calendar 관리 화면·계획 연동·목표 원천 재설계 (ADJ-11·12·17, NEW-1·4·5, RC-1~38)

> 작성 2026-10-11 · product-architect · 상태: RC-1~38·V1-1(V1-2 정정)·V1-13·PLN-23 결정 반영(2026-10-11) · 상위: `decisions-table.md` ADJ-11·12·17·NEW-1·4·5·RC-1~38·V1-1·V1-2·V1-13·PLN-23, `adjustment-signals.md` §3.4, `adjustment-new-signals.md`
> DB·API 형태는 system-architect 확인 대상이다. 정책·기본값·문구는 `decisions-table.md` RC-* 결정이 기준이다(§5).

**변경 이력**
- 2026-10-11 초안(결정 전).
- 2026-10-11 RC-1~10 결정 반영: RC-1 (c) race_calendar 원천 + goals 참조 재설계(§2.1·§2.2·§2.6), 상태 머신(§2.4), 신규 결정 RC-11~17 추가.
- 2026-10-11 설계서 동기화(RC-11~17 확정 반영): §2.1·§2.2(불변식 3)·§2.3·§2.4·§2.5·§2.6·§2.7·§3·§4·§5 갱신, §7 추가.
- 2026-10-11 설계서 동기화(TZ-1 추가 결정·RC-4b/RC-6 정합·NEW-11): '오늘' = `reference_today` 헬퍼(§2.9 신설, §2.6-5·§2.7·§3·§4), §2.4 '미반영 대회' 정의 명시, 내보내기는 `data-export.md` 링크(§2.10, 대안은 §2.11로 이동), §5를 '결정 완료(표 참조)'로 축약, §7을 '동기화 중 발견한 모호점'으로 정리.
- 2026-10-11 2차 동기화(RC-18·RC-19·ADJ-17): 지난 날짜 대회 등록 허용+확인 문구(§2.4 전이·§2.7 시트·§2.9 검증·§4 검증), race_date 없는 비활성 목표는 목표 생성일로 대회 생성(§2.1·§4 백필 3단계·dry-run 리포트), '지난 대회' 구역 기준 정리(§2.7), race 주 트리거 위치(§2.4), §7 해소 표시.
- 2026-10-11 3차 동기화(RC-20~22): 지난 날짜 등록 대회도 날짜 규칙 그대로 RC-6 하향·계획 반영 질문 대상(§2.4·§4), RC-19 백필은 대회 행만 생성하고 `goals.race_date` 캐시는 NULL 유지(§2.1·§2.2 불변식 4 예외·§3 `check_data_consistency.py`·§4 백필 3·4단계), 미래 날짜 done 대회는 별도 표시 후 사용자 정리(§2.7, 화면 표시 방식은 §7 열린 질문).
- 2026-10-11 4차 동기화(RC-23·24·V1-1): 미래 날짜 done 대회는 목록 '확인 필요' 배지 + 신호·D-day 제외 코드 경로 열거(§2.4·§2.7·§2.8 신설·§3·§4), RC-21 예외 행 수정 시 `push_cache`가 `race_date` 캐시를 채워 불변식 4 예외 해소(§2.2·§2.3·§3·§4), v1 화면·경로 호환 서술 제거(§1·§2.1·§2.3·§3·§4·§6, V1-1 일몰).
- 2026-10-11 5차 동기화(RC-25·26·27, V1-1 정정·V1-2): '확인 필요' 대회는 별도 구역(§2.7·§2.8·§3·§4), RC-21 예외 행 캐시는 날짜를 실제로 입력·변경한 저장에서만 채움(§2.1·§2.2·§2.3·§3·§4), cancelled 대회 수정 허용 + cancelled → planned 복원 경로 신설(§2.4·§2.7·§2.12 신설·§3·§4), v1 일몰 = UI·라우트 일몰로 정정 — 공유 함수 `add_goal`·`update_goal` 유지 근거 복원(§1·§2.3·§3·§4·§7).
- 2026-10-11 6차 동기화(RC-28~34): 복원 시 취소 직전 adapt_choice·plan_state 복원(RC-28, 보존 필드 제안 §2.1·§2.12), 지난 날짜 복원은 RC-18 확인 후 done(RC-29), A 충돌 시 기존 A 강등 확인(RC-30), '취소됨' 접힘 구역(RC-31, §2.7), '확인 필요' 행 '예정으로 되돌리기'(RC-32, §2.4·§2.7·§2.8·§2.13 신설), '확인 필요' 행 결과 기록 카드 제외(RC-33, §2.6-5·§2.8), 같은 날짜 재선택은 '입력' 아님(RC-34, §2.2). §3·§4·§5·§7 갱신.
- 2026-10-11 7차 동기화(RC-35~38·PLN-23·V1-13): 불변식 3 완화 'A 이거나 활성 목표 미연결'(RC-35, §2.2·§3 `check_data_consistency.py`), 복원 시 직전 applied면 일괄 적용 재실행·실패 처리 제안(RC-36, §2.12), '예정으로 되돌리기' 후 unasked·A 충돌은 RC-30(RC-37, §2.13), 보존 컬럼 `cancel_prev_*` 확정·보존 값 없는 행 서술(RC-38, §2.1·§2.12), 기존 플랜 삭제에 따른 v39 백필·계획 연동 정리(PLN-23, §2.6·§4), v1 호환 서술 제거(V1-13, §3·§4·§7). §5·§7 열린 질문 갱신.

## 1. 근본 원인 (grep 2026-10-11)
- **대회의 원천이 셋으로 흩어져 있고, B/C 대회를 관리하는 곳이 없다.** ① `goals.race_date·distance_km`(활성 목표 1건 유니크 `ux_goals_one_active`, v32) ② `planned_workouts.workout_type='race'` 행(재계획 때 다시 만들어져 메타데이터가 사라짐) ③ `race_results`(v20, `activity_id` 기준 실적, 예정 대회 아님).
- **대회 사실을 쓰는 경로가 목표 쪽에 흩어져 있다.** `training/goals.add_goal`(188줄) 호출자: `plan_template_service.py:181`(신규 화면 `/coach/plan/new`), `src/plan.py:79`(CLI), `training/plan_backtest.py:67`·`plan_backtest_replan.py:20`(백테스트). v1 화면 호출자(`web/views_training_wizard.py:366` 온보딩 마법사, `web/views_training_goal_crud.py:52` 목표 CRUD)는 UI·라우트라 일몰 대상이다(V1-1, V1-2 정정). `add_goal`·`update_goal`은 `src/training/goals.py`의 **공유 함수라 일몰과 무관하게 유지**한다(V1-2). `update_goal`이 race_date·distance_km를 직접 고친다(현재 호출자는 v1 `views_training_wizard.py:299` 하나). `goals.race_date`를 읽는 곳은 `src/` 40여 파일(planner·replanner·race_hub·today_hero·ai 컨텍스트 등)이다.
- **화면이 없다.** 대회 화면은 `/today/race`(예측 위주)와 `/today/race/races`(실적 확정 목록, 39줄)뿐이다. 등록 경로는 목표 생성의 race_date 하나뿐이고 B/C 등록·수정·삭제·조회는 없다.
- **대회에서 계획으로 이어지는 길이 끊겨 있다.** `training/constraints.b_race_week()`는 테스트만 부른다. `plan_replan_service.preview/apply/undo`는 활성 goal 기준이고 다음 월요일 시작·대회 주 거부(409 `RACE_WEEK`)라 가까운 B/C 대회를 반영할 수 없다. `plan_adjustments`(v31)의 `source` CHECK는 `crs|user|coach`뿐이다(v37 재생성에서 확장 예정).
- 그 결과 B/C 대회를 알릴 방법이 없고, `race_plan` 신호 priority는 `unknown`이며, 목표와 대회가 같은 사실을 두 곳에 들고 있게 된다.

## 2. 설계안 (확정 = 대안 A 하이브리드 + RC-1 (c))

### 2.1 데이터 모델
**원칙(RC-1 c):** 대회 사실(이름·날짜·거리·우선순위·대회 목표)의 원천은 `race_calendar` 한 곳이다. `goals`는 "그 대회를 위한 훈련 계획의 목표"(plan_weeks, 규칙 버전, 시작 부하, 상태)를 갖고 `goals.race_id`로 대회를 참조한다. `goals.race_date·distance_km·target_time_sec`는 **읽기 호환 캐시**로 남긴다(40여 개 읽기 경로를 바꾸지 않기 위함). 캐시는 `race_goal_sync` 한 곳만 쓴다. `goals.name`은 목표 자체 이름이라 동기화하지 않는다.

`race_calendar` (v38 생성, 가산)
| 필드 | 필수 | 의미 |
|---|---|---|
| `id, created_at, updated_at` | 자동 | |
| `name`, `race_date`, `distance_km` | 필수 | 이름, YYYY-MM-DD, 프리셋 5/10/21.0975/42.195 또는 직접 입력 |
| `priority` | 필수 | `A|B|C` CHECK, 미선택 불가(RC-2) |
| `goal_type`, `goal_value` | 선택 | `finish|time|pb` CHECK(RC-3). `time`이면 `goal_value`=초, `pb`는 기존 PB를 표시하고 값은 비움 |
| `adapt_choice` | 자동 | `unasked|later|adapt|no_adapt`, 기본 `unasked`. 기본 선택값은 없고 항상 묻는다(RC-4 b) |
| `plan_state` | 자동 | `none|applied|stale`: 계획에 실제 반영된 상태 |
| `cancel_prev_adapt_choice`, `cancel_prev_plan_state` | 자동 | 취소 직전 값 보존(RC-28, **RC-38 a 확정: 새 컬럼, v38 DDL**). NULL 허용·기본값 NULL, CHECK는 각각 `adapt_choice`·`plan_state`와 같은 값 + NULL. 취소(cancelled 전이) 때 기록, 복원 때 읽고 NULL로 비움. NULL = "보존 값 없음"(§2.12) |
| `taper_days`, `recovery_days` | 선택 | NULL이면 거리별 기본값(§2.5), 값이 있으면 대회별 덮어쓰기(RC-5 a) |
| `status` | 자동 | `planned|done|cancelled` |
| `origin` | 자동 | `manual|goal|import`(goal=v39 백필 또는 목표 생성 경로, import는 범위 밖) |
| `planned_workout_id`, `race_result_id` | 선택 | 계획의 race 행, 확정 실적 |
| `note` | 선택 | 메모 |
- 앞선 초안의 `goal_id`(역방향 참조)·`allow_recovery_downgrade`(RC-6으로 규칙화)·`adapt_plan` 0/1은 없앤다. 참조 방향은 `goals.race_id → race_calendar.id` 하나다.
- 인덱스: `ux_race_planned_same`(`race_date, distance_km` WHERE status='planned'), `ux_race_one_a`(`priority` WHERE priority='A' AND status='planned').

`goals` 변경 (v39)
- `race_id INTEGER REFERENCES race_calendar(id)` NULL 허용. race_date 없는 활성 목표는 NULL로 두고 날짜 입력 배너로 유도, 입력 시 A 대회 생성·연결(RC-11 b). race_date 없는 비활성 목표는 **목표 생성일(`goals.created_at`의 날짜)을 race_date로 써서 대회를 만들고 연결**한다(RC-19 b, §4 백필 3단계). 이때 **대회 행만 만들고 `goals.race_date` 캐시는 NULL로 둔다**(RC-21 b, 불변식 4 예외). 이 대회를 나중에 캘린더 시트에서 수정하면서 **날짜를 실제로 입력·변경한 경우에만** `push_cache`가 `race_date` 캐시를 채워 예외가 해소된다(RC-24 a + RC-26 a, §2.2). 날짜를 그대로 둔 저장은 예외를 유지한다. 따라서 v39 이후 race_id NULL은 'race_date 없는 활성 목표'뿐이고, `race_id IS NOT NULL AND race_date IS NULL`은 'RC-19 백필로 연결되고 아직 날짜가 입력·변경되지 않은 비활성 목표'뿐이다.
- `ux_goals_race`(`race_id` WHERE race_id IS NOT NULL AND status='active'): 한 대회에 활성 목표 1건.
- `ux_goals_one_active`(v32)는 **그대로 둔다.** 회귀 위험 없이 "활성 목표 1개"를 계속 보장한다.

### 2.2 불변식 ('A 대회 하나'의 새 표현)
1. 활성 목표 ≤ 1 (`ux_goals_one_active`, v32 유지).
2. planned A 대회 ≤ 1 (`ux_race_one_a`).
3. **(RC-35 b로 완화, 결정 문구 'A 이거나 활성 목표 미연결')** 활성 목표에 race_id가 있으면 그 대회는 `status IN ('planned','done')`이다(done은 RC-17: 대회가 지나도 목표는 사용자가 완료할 때까지 활성). 완화 전의 두 조건 — "활성 목표의 대회는 `priority='A'`", "planned A 대회는 활성 목표가 참조" — 은 더 이상 강제하지 않는다. 완화로 허용되는 상태(현 설계가 만드는 경우만):
   - **활성 목표에 연결되지 않은 A:** §2.2 교체 규칙으로 남은 done A(이전 A가 done이면 그대로 둔다 — 아래), RC-30 복원으로 planned/done이 된 A(연결 목표는 cancelled·completed), RC-37 '예정으로 되돌리기'로 planned가 된 A(연결 목표 completed).
   - **활성 목표가 연결된 B:** RC-30 강등(복원 A와 충돌한 기존 A가 활성 목표 대회일 때). RC-35는 강등 전에 목표 연결 변경을 요구하지 않는다((a) 기각) — 목표는 활성·연결 그대로, 대회만 B·`unasked`·`none`. **해석 주의:** 결정 문구를 대회 행마다 "A 이거나 활성 목표에 미연결"로 글자 그대로 읽으면 이 상태(활성 목표 → B)는 위반이다. RC-35가 '목표 연결 변경 먼저'(a)를 기각하고 강등을 허용했으므로 이 설계는 허용 쪽으로 읽었다 — 확인 필요(§7 열린 질문 R1).
   - 정상 흐름에서는 여전히 **A 지정 = 목표 대회 지정**이다. A는 목표 생성·교체 흐름(RC-30 복원·RC-37 되돌리기 제외)으로만 만들어지고, 캘린더 시트에서 A를 고르면 목표 생성 화면으로 넘어간다. 교체 시 이전 planned A는 B로 강등, `adapt_choice='unasked'`·`plan_state='none'`(질문 대기, RC-15 b). 이전 A가 이미 done이면 그대로 둔다(활성 목표 미연결 done A — 완화된 불변식 3 허용). **RC-30과의 관계:** 이 '그대로 둔다'는 목표 교체 경로 규칙이고, RC-30 복원 경로는 기존 A가 planned이든 done이든 강등을 묻는다(RC-35 (c) 기각). 두 경로 결과 모두 완화된 불변식 3을 만족한다. planned A ≤ 1은 불변식 2(`ux_race_one_a`)가 계속 지킨다.
4. 캐시 일치: 활성·비활성 목표 모두 `goals.race_date/distance_km/target_time_sec` = 참조 대회 값. **예외(RC-21 b):** RC-19 백필로 생성일 대회에 연결된 비활성 목표(`status != 'active' AND race_id IS NOT NULL AND race_date IS NULL`)는 `race_date` 캐시가 NULL인 것을 허용한다(`distance_km`·`target_time_sec`는 일치 대상 그대로). 생성일은 실제 대회 날짜가 아니므로 캐시로 퍼뜨리지 않는다. **예외 해소(RC-24 a, RC-26 a):** 사용자가 이 대회 행을 캘린더 시트(`race_calendar_service.update`)로 수정해 저장할 때 **`race_date`를 실제로 입력·변경한 경우에만** 같은 트랜잭션에서 `race_goal_sync.push_cache`가 연결 목표의 `race_date` 캐시를 대회 값으로 채운다 — 그 뒤로 이 행은 예외가 아니며 일반 불변식 4를 따른다. 날짜를 바꾸지 않은 저장(생성일 그대로)은 `race_date` 캐시를 NULL로 두고 예외를 유지한다(생성일을 캐시로 퍼뜨리지 않음, RC-21 취지). `distance_km`·`target_time_sec` 캐시는 예외 대상이 아니므로 어떤 저장이든 대회 값으로 맞춘다. 판정은 서비스에서 저장 전 행의 `race_date`와 요청 값을 비교한다(변경 = 값이 다름). 같은 날짜를 시트에서 다시 골라 저장해도 값이 같으면 '입력'으로 보지 않는다(RC-34 a, 예외 유지 — 시트가 별도 '날짜 확인' 신호를 보낼 필요 없음). 예외 행은 status done/cancelled이며, RC-27로 cancelled 행도 수정 가능하므로 같은 규칙이 적용된다.
- 1·2는 DB 인덱스, 3·4는 서비스(`race_goal_sync`)와 `check_data_consistency.py` 신규 검사 2건으로 지킨다(불변식 3 검사 조건은 RC-35 완화와 동일하게 갱신 — 활성 목표가 연결한 대회가 존재하고 `status IN ('planned','done')`인지만 본다. `priority='A'` 조건과 "planned A ⇒ 활성 목표 참조" 역방향 검사는 하지 않는다(R1 해석 확정 시 함께 조정). 불변식 4 검사는 위 예외 행(캐시 `race_date IS NULL`인 비활성 연결 목표)의 `race_date` 비교만 건너뛴다 — 날짜 미변경 저장으로 NULL이 유지된 행도 여기에 포함되고(RC-26), 날짜 입력·변경으로 캐시가 채워진 행은 일반 비교 대상(RC-24))(SQLite 트리거는 마이그레이션·테스트 부담 대비 이득이 작아 쓰지 않는다).

### 2.3 쓰기 경로와 화면 역할 (어느 쪽에서 고쳐도 한 곳이 갱신)
| 진입 | 고치는 것 | 실제 쓰기 |
|---|---|---|
| 대회 캘린더 시트 `RaceEntrySheet` | B/C 대회 전부, A 대회의 이름·날짜·거리·대회 목표 | `race_calendar_service.update` → A이면 같은 트랜잭션에서 `race_goal_sync.push_cache`(RC-21 예외 행은 `race_date`를 실제로 입력·변경한 경우에만 `race_date` 캐시를 채워 예외 해소, RC-24·26). cancelled 행도 수정 가능(RC-27 b) |
| 목표 생성 `/coach/plan/new` | 대회 고르기(등록된 B/C 또는 새 대회) + 계획 조건 | `goal_service.create_goal_with_race`: 대회 행 생성·승격(A) → `add_goal(race_id=…)` |
| 목표 수정(계획 상세 `/coach/plan/[id]`) | 계획 조건, "대회 바꾸기" | 대회 사실 변경은 캘린더 시트를 같은 컴포넌트로 연다(별도 폼 없음) |
| race_date 없는 활성 목표 배너(Today·계획 상세) | 대회 날짜·거리 입력(RC-11 b) | `race_goal_sync.attach_race`: A 대회 생성 + `goals.race_id`·캐시 한 트랜잭션 |
| CLI(`plan.py`)·공유 함수 호출자 | 기존과 같음 | `add_goal(race_date=…)` 호환 래퍼가 대회 행을 만들고 연결. `update_goal(race_date|distance_km)`은 `race_calendar_service.update`로 위임(공유 함수 유지, V1-2) |
| 대회 캘린더 시트 "다시 활성화"(cancelled 행) | status cancelled → planned(RC-27 추가) | `race_calendar_service.restore` (§2.12) |
- 대회 사실을 고치는 UI는 `RaceEntrySheet` 하나다. 목표 화면은 그 시트를 재사용하고, 날짜·거리 변경은 **저장 전 재계획 미리보기를 거쳐야 저장된다**(RC-13 a, 미리보기 취소 시 아무것도 쓰지 않음).
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
| cancelled | 무관(직전 값은 `cancel_prev_*`에 보존, RC-28) | none | X | X | X | 취소됨(수정 가능 RC-27 b, "다시 활성화" §2.12, '취소됨' 접힘 구역 RC-31) |
| planned/done, A(활성 목표 연결) | adapt 고정 | applied | O | X | O | 목표 대회 |
| done, `race_date ≥ today`(미래 날짜 done, RC-22·23) | 무관 | 무관 | **X** | **X** | **X** | **확인 필요** 배지(결과 기록 카드도 제외 RC-33, '예정으로 되돌리기' RC-32) |
- **미래 날짜 done 행(RC-23 a):** 위 마지막 행이 다른 done 행보다 우선한다. 사용자가 정리(날짜 수정 또는 삭제)하기 전까지 어떤 대회 신호·D-day에도 쓰지 않고 목록에만 '확인 필요' 배지로 보인다. 제외 경로 목록은 §2.8.
- **활성 목표 미연결 A(RC-35 완화로 생김):** RC-37로 되돌린 A는 `unasked`·`none`, RC-30 복원 A는 복원 값(RC-28·RC-36)을 가진다. 이 행들이 'adapt 고정' 행이 아니라 adapt_choice별 일반 행(질문 대기 등)을 따르는지는 결정 문구에 없다 — §7 열린 질문 R3(현 설계는 일반 행을 따르는 것으로 서술).
- 테이퍼 기간 하향은 어떤 상태에서도 보조 근거로만 쓴다(§3.4). `no_adapt`는 캘린더 표시만 남고 조정 신호에는 전혀 들어가지 않는다.
- **race 주 트리거 위치(ADJ-17 a):** RC-6 회복 하향 트리거(source=`race`)는 `adjustment-signals.md` §3.8 주 트리거 순서 `pain > illness > checkin > race > crs > acwr > readiness`에서 체크인 바로 뒤다. 같은 날 통증·질병·체크인 통증 트리거가 함께 있으면 source는 그쪽이 되고 race는 support 이하로 기록된다. 순서는 추후 백테스트·ML 재검토 대상(`LATER.md` 기록).
- **RC-4b ↔ RC-6 정합(결정 표 기준):** RC-4b가 우선한다. RC-6(a)의 "계획에 반영하지 않은 대회"는 `adapt_choice IN ('unasked','later')`(질문 대기·나중에)만 뜻하고, `no_adapt`('조정 안 함')는 회복 하향 트리거를 포함한 어떤 대회 신호에도 들어가지 않는다. `adjustment-signals.md` §3.4의 `detail.unplanned=true`도 이 두 상태에만 붙인다.
- **전이:** 등록 → unasked. 지난 날짜(`race_date < reference_today`) 등록(RC-18 c)도 같은 경로로 planned·unasked로 저장되고, 다음 조회 때 기존 지연 done 전이(RC-8)로 done이 된다(별도 분기 없음). **RC-20 a:** 지난 날짜 등록분도 날짜 규칙 그대로 다룬다 — 회복 창(`race_date` + 회복 일수) 안이면 done·unasked 행으로 RC-6 회복 하향 트리거 대상이 되고 계획 반영 질문도 띄운다(등록 경로·이력용 여부로 제외하지 않음). 회복 창이 이미 지났으면 날짜 규칙상 신호가 생기지 않는다. 질문 응답 → adapt(일괄 적용 성공 시 applied) / later / no_adapt. 시트를 닫으면 unasked 유지. later·no_adapt는 목록 칩에서 다시 고를 수 있다. applied 대회의 날짜·거리·우선순위·보호 기간 수정 → stale(no_adapt·unasked·later는 질문 없이 값만 바뀜). 일괄 되돌리기 → plan_state none, adapt_choice later. A 교체로 강등된 이전 A → B·unasked·none(RC-15). 날짜 경과 → done(RC-8), A이면 목표는 활성 유지(RC-17). 삭제 → cancelled, applied였으면 같은 트랜잭션에서 반영분 일괄 되돌리기(RC-9). A는 질문 없이 adapt·applied(계획이 목표에서 생성). **cancelled 수정(RC-27 b):** 이름·날짜·거리·우선순위·목표·보호 기간·메모를 고칠 수 있고 status는 cancelled 그대로, adapt_choice·plan_state는 바뀌지 않으며 질문·신호·D-day는 없다(제외는 status 기준). **취소 시 값 보존(RC-28):** cancelled 전이(RC-9) 직전의 adapt_choice·plan_state를 보존 필드에 기록한 뒤 RC-9 되돌리기를 적용한다(§2.12). **복원(RC-27 추가·RC-28~30):** `race_date ≥ today`면 cancelled → planned, 지난 날짜면 RC-18 확인 문구 후 cancelled → done(RC-29, RC-8·RC-20 규칙 적용). adapt_choice·plan_state는 취소 직전 값으로 되돌린다(RC-28·RC-38). 직전 값이 applied였으면 복원 때 일괄 적용을 다시 실행한다(RC-36 b, 실패 처리는 §2.12). A 행이 다른 A와 충돌하면 기존 A(planned·done 모두) 강등 확인(RC-30, 불변식 3 완화 RC-35). 복원 후에는 해당 status의 표 행대로 신호·D-day 대상에 복귀하고, 이후 전이는 위 규칙을 그대로 따른다. **예정으로 되돌리기(RC-32 a):** '확인 필요'(미래 날짜 done) 행만 수정 시트 버튼으로 done → planned, adapt_choice `unasked`·plan_state `none`으로 초기화(RC-37 a), A 충돌은 RC-30 규칙(§2.13).
- 적용 실패(409 등)면 adapt_choice·plan_state를 바꾸지 않는다.

**상태 전이 요약(status 축)**
| 출발 | 이벤트 | 도착 | 근거 |
|---|---|---|---|
| (없음) | 등록(지난 날짜 포함) | planned | RC-18·RC-20 |
| planned | `race_date < today` 조회·동기화 | done | RC-8 |
| planned | 삭제 | cancelled | RC-9 |
| done | 삭제(배지 행 정리 포함) | cancelled | RC-9·RC-23 |
| done(미래 날짜) | 날짜를 과거로 수정 | done(일반) | RC-23, §2.8 |
| cancelled | 수정 | cancelled | RC-27 b |
| cancelled | 다시 활성화(`race_date ≥ today`) | planned | RC-27 추가·RC-28·RC-30·RC-35·RC-36·RC-38, §2.12 |
| cancelled | 다시 활성화(`race_date < today`, RC-18 확인 후) | done | RC-29(RC-8·RC-20)·RC-36, §2.12 |
| done(미래 날짜, '확인 필요') | 예정으로 되돌리기 | planned(`unasked`·`none`) | RC-32 a·RC-37 a, §2.13 |
| done(일반, 과거 날짜) | planned 되돌리기 | — | 경로 없음(RC-32는 '확인 필요' 행 한정) |

### 2.5 보호 기간 (RC-5 a)
- 기본: 테이퍼 5·10K 3일 / 하프 7일 / 풀 14일, 회복 2 / 4 / 7일. B/C는 절반 **올림**(테이퍼 2/4/7일, 회복 1/2/4일, RC-16 a). `taper_days·recovery_days`가 있으면 그 값을 그대로 쓴다(절반 미적용).
- 상세 시트 Level 2 "왜?"에 거리 → 기본 일수 → B/C 보정 → 덮어쓰기 여부를 보여 준다.

### 2.6 계획 연동 흐름
1. **저장 → 영향 계산(쓰기 없음):** 순수 함수 `race_impact(rows, race, windows)`. `b_race_week()`를 일반화(테이퍼·회복 일수 인자)해 재사용한다. race·rest·완료·매칭된 행은 건드리지 않는다.
2. **B/C 대회 일괄 적용(RC-7 a):** `RacePlanPrompt` 미리보기(날짜별 전→후, 근거 칩) 한 번에 수락 → 행 단위 `plan_adjustments`를 한 묶음(`batch_id`)으로 적용, 묶음 단위로 되돌린다. `source='race'`는 v37 재생성에 포함하도록 system-architect와 협의한다.
   - **PLN-23(기존 플랜 삭제) 영향:** `race_impact`·일괄 적용·RC-6 회복 하향은 그 시점 `planned_workouts`에 있는 행(새로 만든 계획)만 대상으로 하고, `race_plan` 신호 수집(`adjustment-signals.md` §3.4)은 `race_calendar`만 읽는다 — 기존 플랜 행에 의존하는 경로가 없어 기존 행 이관·보정 로직을 두지 않는다. 계획이 없거나 창 안에 행이 없으면 `race_impact` 결과는 0건이다(빈 결과의 화면 처리는 기존 설계 범위, PLN-23로 새로 생기는 분기 아님). 기존 race 행(`workout_type='race'`)과 `race_calendar.planned_workout_id`를 잇는 백필도 하지 않는다(새 계획 생성 때만 채움).
3. **A 대회:** 날짜·거리 변경 시 저장 전 `plan_replan_service.preview`를 보여 주고(RC-13 a), 수락하면 `race_calendar` 갱신 + 캐시 + `apply`를 한 흐름으로, 이후 `undo`(다음 월요일 시작, 마지막 1건 되돌리기 규칙 유지). 대회 주 안의 변경은 2번 경로로 대체한다.
4. **보호 기간 신호:** §2.4 표대로. applied 대회는 `race_plan` 단독 하향 트리거를 만들지 않는다.
5. **완료(RC-8 b):** `race_date < 오늘`(오늘 = `reference_today`, §2.9)인 planned 행은 조회·동기화 시점에 `done`으로 바꾸고(지연 전이, 별도 스케줄러 없음) 레이스 허브 "결과 기록" 카드에 `race_result_service.candidates`(같은 날짜, 거리 ±10%)를 띄운다. '확인 필요' 행(`is_needs_review`, §2.8)은 이 카드에서 제외한다(RC-33 a). 확정하면 `race_result_id` 연결. A 대회 done 시 목표는 활성 유지하고 허브·Today에 "결과 기록·다음 목표" 카드를 띄워 사용자가 목표를 완료한다(RC-17 b, 현재 동작과 같음).
6. **AI 코칭 예시:** "다음 주 일요일 10K(B)가 있어서 목요일 템포는 가볍게 바꿔 뒀어요. (race_plan D-10, 테이퍼 기간)" → "왜?"는 상세 Level 2.

### 2.7 화면 (모바일 375px, h1(PageHead) 1개, 44px 탭 영역, 오버레이 `use:modal`)
- **진입:** 레이스 허브 "대회 캘린더" 카드(예: "다음 대회 · 춘천 10K(B) · D-15 · 반영됨"), 계획 상세 주간 목록의 A/B/C 배지, 목표 생성의 "등록된 대회에서 고르기".
- **목록 `/today/race/calendar`(h1 "대회 캘린더"):** '확인 필요'(있을 때만)·다가오는·지난·'취소됨'(있을 때만, 기본 접힘) 네 구역(RC-25 b·RC-31 a), 행 = 배지·이름·D-day·거리·목표 한 줄·§2.4 칩. 우상단 "대회 추가". D-day·구역 경계는 응답에 동봉된 `today`(§2.9)로 계산하고 브라우저 날짜를 쓰지 않는다.
  - 구역 기준(현 설계 정리): 먼저 `is_needs_review`(§2.8)가 참인 행을 **'확인 필요' 구역**으로 뺀다(RC-25 b). 나머지 cancelled 아닌 행은 `race_date`와 `today` 비교로 나눈다(`race_date ≥ today` = 다가오는, 그 외 = 지난). 따라서 '다가오는' 구역에는 미래 날짜 done 행이 들어가지 않는다. RC-18 지난 날짜 등록 대회와 RC-19 생성일 대회는 날짜가 과거라 '지난' 구역에 들어간다. cancelled 행은 날짜와 무관하게 **'취소됨' 접힘 구역**에 모은다(RC-31 a) — 구역 머리(예: "취소됨 N", 44px)를 눌러 펼치고, 행을 열면 수정 모드 시트("다시 활성화" 버튼, §2.12)가 열린다. cancelled 행이 없으면 구역을 그리지 않는다. 구역 순서는 '확인 필요'·다가오는·지난·취소됨(취소됨 맨 아래)을 제안한다(구현 중 확인).
  - **'확인 필요' 구역(RC-22 c·RC-23 a·RC-25 b):** `status='done' AND race_date ≥ today`(RC-12 b의 미래 날짜 completed 목표 백필분)는 다가오는/지난 구역이 아닌 **별도 '확인 필요' 구역**에 보여 주고 사용자가 정리하게 한다. 행의 §2.4 칩 자리에 '확인 필요' 배지를 쓰고 D-day는 표시하지 않는다(D-day 제외, §2.8). 해당 행이 없으면 구역을 그리지 않는다. 서버는 목록 응답에서 이 행들을 구분할 수 있게 내려 준다(예: `needs_review: true` 또는 구역별 배열, 필드 형태는 S0에서 확정). 정리는 기존 시트의 수정(날짜 고치기)·삭제(cancelled) 경로와 수정 시트의 **'예정으로 되돌리기'** 버튼(RC-32 a, §2.13)으로 한다. 이 행은 레이스 허브 '결과 기록' 카드 후보에 넣지 않는다(RC-33 a). 구역 순서(목록 맨 위 제안)와 구역 안내 문구는 구현 중 확인(§7).
- **등록·수정 시트:** 필수 4개(날짜·이름·거리 칩·우선순위 세그먼트) 위, 나머지(목표 유형·값, 보호 기간 덮어쓰기, 메모)는 "더 설정"에 접는다. **지난 날짜 확인(RC-18 c):** 날짜가 응답의 `today`(§2.9)보다 이전이면 저장 전에 확인 문구를 한 번 띄우고, 확인하면 저장한다(취소 시 입력 유지). 문구 초안 "지난 날짜예요. 지난 대회로 기록할까요?" — **최종 문구는 사용자 확정 필요**. A를 고르면 "목표 대회로 지정하면 훈련 계획을 이 대회에 맞춰 새로 만들어요" 안내(기존 A가 있으면 "지금 목표 대회는 B로 바뀌어요" 병기, RC-15) 후 목표 생성으로 이동. 저장 실패는 시트 안 문구 + 입력 유지.
- **계획 반영 질문:** 제목 "이 대회에 맞춰 계획을 조정할까요?", 버튼 "조정할게요 / 나중에 / 조정 안 함"(RC-10, 최종 문구는 구현 중 확인). 수정 시 "변경 영향" 모드(기존 반영분 되돌리기 + 새 제안 diff).
- **날짜 입력 배너(RC-11):** "목표 대회 날짜를 알려 주시면 대회 캘린더에 등록하고 계획을 맞춰요" + 입력(날짜·거리) → 대회 생성.
- **결과 기록·다음 목표 카드(RC-17):** A 대회 done 후 "결과 기록"(후보 연결)·"다음 목표 정하기"·"목표 완료".
- **삭제:** 확인 다이얼로그에 되돌릴 조정 N건·연결 실적 유지 안내 → cancelled(RC-9). A 삭제는 목표 취소를 함께 묻는다(목표 화면과 같은 확인).
- **취소된 대회(RC-27):** cancelled 행을 열면 `RaceEntrySheet`가 수정 모드로 열리고(저장해도 cancelled 유지, 질문 없음), 시트 하단에 **"다시 활성화"** 버튼(44px)을 둔다 → §2.12 복원. 버튼은 cancelled 행에서만 보인다. 문구 초안 "다시 활성화" — 최종 문구는 구현 중 확인(RC-10과 같은 방식). 날짜가 `today`보다 이전이면 누를 때 RC-18 확인 문구를 먼저 띄운다(RC-29, 취소 시 무변경). 복원 행이 A이고 다른 A(planned/done)가 있으면 "지금 목표 대회는 B로 바뀌어요"(RC-15 문구) 확인을 띄운다(RC-30, 취소 시 무변경).
- **예정으로 되돌리기(RC-32 a):** '확인 필요' 행을 열면 수정 시트 하단에 **"예정으로 되돌리기"** 버튼(44px)을 둔다 → §2.13. 버튼은 `needs_review` 행에서만 보인다. 되돌린 행은 계획 반영 질문 대기(`unasked`, RC-37). A 행이 다른 A와 충돌하면 RC-30과 같은 강등 확인(취소 시 무변경). 문구 초안 그대로, 최종 문구는 구현 중 확인.
- **빈 상태:** "등록된 대회가 없어요. 목표 외에 나갈 대회를 추가하면 그 앞뒤 훈련을 맞춰 드려요" + 추가 버튼. **오류:** 공통 `ErrorState`, 409(A 중복·같은 날 같은 거리·`REPLAN_LOCKED`·`RACE_WEEK`)는 코드별 문구.

### 2.8 미래 날짜 done 대회 제외 경로 (RC-23 a)
판정은 한 곳: `race_calendar_service.is_needs_review(row, today)` = `status='done' AND race_date ≥ today`(today = `reference_today`, §2.9). 아래 경로는 모두 이 함수로 행을 거른다(경로마다 조건을 다시 쓰지 않음).
| 경로 | 처리 |
|---|---|
| `race_calendar_service.list`(목록 API) | 행은 포함, '확인 필요' 구역으로 분류(RC-25 b)·`needs_review` 표시·D-day 값 없음(배지만). '다가오는' 구역에는 넣지 않음 |
| `race_calendar_service` "다음 대회" 조회 → 레이스 허브 "대회 캘린더" 카드(§2.7 진입) | 제외(다음 대회·D-day 후보 아님) |
| `adjustment_signals_race` `race_plan` 수집기(`adjustment-signals.md` §3.4, −14~+21일 `planned|done`) | 제외 — hold·support·trigger·`detail.others` 어디에도 넣지 않음 |
| RC-6 회복 하향 트리거(source=`race`, done·unasked/later 행) | 제외 |
| `race_plan_link`(계획 반영 질문·`RacePlanPrompt`·일괄 적용) | 제외(질문 띄우지 않음) |
| AI 코치 대회 맥락(`race_plan` 신호 경유, `coach_evidence` 등) | 신호 수집에서 빠지므로 자동 제외 — 별도 경로가 `race_calendar`를 직접 읽으면 같은 함수로 거름(구현 시 grep) |
| 레이스 허브 "결과 기록" 카드(§2.6-5, `race_result_service.candidates` 대상 조회) | 제외(RC-33 a) |
- 기존 D-day 경로(Today·레이스 허브의 `goals.race_date` 읽기 40여 곳)는 활성 목표만 본다. 미래 날짜 done 대회는 RC-12 b상 completed(비활성) 목표에 연결되므로 이 경로에 나타나지 않는다 — 비활성 목표를 읽는 경로가 있는지는 구현 시 grep 확인.
- 정리 후: 날짜를 과거로 고치면 일반 done 행(§2.4 날짜 규칙)으로 '지난' 구역, 미래로 둔 채 수정하면 여전히 '확인 필요' 구역, 삭제하면 cancelled. "예정으로 되돌리기"를 누르면 planned 행(§2.13)이 되어 '다가오는' 구역으로 가고 신호·D-day 대상이 된다(RC-32 a). 삭제 후 "다시 활성화" 2단계 경로는 안내하지 않는다(직접 경로로 대체).

### 2.9 '오늘' 기준일 (TZ-1 추가 결정)
- 이 번들에서 날짜 전용 값과 비교하는 '오늘'은 모두 `src/utils/reference_day.reference_today(conn)` 하나로 구한다: **사용자의 최근 활동의 현지 시간대 기준 날짜, 활동이 없으면 서버 로컬 날짜 폴백**. 헬퍼 정의·테스트는 `patterns/timezone-display.md` §2.4가 원천이고 여기서는 쓰는 곳만 적는다.
- 사용처: 지연 done 전이(`race_date < 오늘`, §2.6-5), 미래 날짜 done 판정(`is_needs_review`, §2.8), D-day·다가오는/지난 구역(§2.7, API가 `reference_today_info()`의 `today`를 목록·상세 응답에 동봉), `race_date` 입력 검증에서 '오늘'과 비교하는 모든 곳(`race_calendar_service`), RC-11 배너·`attach_race`의 날짜 검증.
- 지난 날짜(RC-18 c): `race_calendar_service.add`는 `race_date < 오늘`을 **거부하지 않는다**(400 없음). 확인은 시트(§2.7)에서 저장 전에 하고, 서버는 형식·중복·A 규칙만 검사한다.
- `race_calendar_service`는 한 요청 안에서 헬퍼를 한 번 부르고 값을 넘겨 쓴다.

### 2.10 내보내기 (NEW-11)
- 대회 캘린더는 사용자 데이터 전체 내보내기의 체크박스 항목(기본 포함)이다. 설계는 `bundles/data-export.md`가 원천이며 이 문서에 복제하지 않는다.

### 2.11 대안 (기록용)
- B: 모든 대회를 재계획 엔진 제약으로 처리 — 2주 안 대회 반영 불가, 엔진 변경 큼. 채택 안 함.
- RC-1 (a) 미러·(b) B/C만 저장 — 사용자가 (c)를 골라 채택 안 함.

### 2.12 취소된 대회 수정·다시 활성화 (RC-27~30·RC-35·RC-36·RC-38)
- **수정(RC-27 b):** `race_calendar_service.update`는 cancelled 행을 거부하지 않는다. status는 cancelled 그대로이고, §2.4 표대로 신호·D-day·계획 반영 질문 대상이 아니다(status 기준 제외 유지). RC-21 예외 행(백필 cancelled 목표의 생성일 대회)이면 RC-26 규칙으로 `push_cache`가 동작한다(날짜 값이 실제로 바뀐 저장에서만 `race_date` 캐시 채움, 같은 날짜 재선택은 변경 아님 RC-34). 수정은 보존 필드(`cancel_prev_*`)를 바꾸지 않는다. 중복 인덱스 `ux_race_planned_same`·`ux_race_one_a`는 planned만 보므로 cancelled 수정은 이 검사에 걸리지 않는다.
- **취소 시 값 보존(RC-28 b):** `race_calendar_service.cancel`은 status를 cancelled로 바꾸기 **전에** 현재 `adapt_choice`·`plan_state`를 보존 필드에 기록하고, 그다음 RC-9 되돌리기(applied면 반영분 일괄 되돌리기 → plan_state none·adapt_choice later)를 적용한다. 같은 트랜잭션.
  - **보존 방식(RC-38 a 확정):** 새 컬럼 `cancel_prev_adapt_choice`·`cancel_prev_plan_state`를 **v38 DDL**(race_calendar CREATE)에 넣는다 — NULL 허용, 기본값 NULL, 같은 CHECK 값 + NULL. 취소 때 기록, 복원 때 읽고 NULL로 비움(§2.1). `adapt_choice`·`plan_state`는 계속 "현재 상태"만 뜻하고, §2.4 표의 cancelled 행(plan_state none)과 RC-9 되돌리기 전이는 그대로다. (기각: 기존 컬럼 유지·이력 유도.)
  - **보존 값이 없는 행(기본값 NULL):** 컬럼이 race_calendar 생성(v38)과 함께 생기므로 "컬럼 도입 전에 취소된 race_calendar 행"은 존재하지 않는다. 보존 필드가 NULL인 cancelled 행은 **v39 백필이 만든 cancelled 행**(cancelled 목표 → cancelled A 대회, §4 백필 2·3단계)뿐이다 — 백필은 취소 동작(`cancel`)을 거치지 않으므로 보존 필드를 쓰지 않는다(NULL 그대로, 백필 대회의 `plan_state`는 none). 이 행을 복원할 때의 값은 §2.12 열린 질문 R2(제안 아래).
- **복원(RC-27 추가 + RC-28~30, 필수 경로):** `race_calendar_service.restore(conn, race_id, today, *, confirm_past=False, demote_existing_a=False)`. API `POST /api/v1/race-calendar/<id>/restore`(본문 `confirm_past`·`demote_existing_a`, 경로·필드 형태는 S0에서 확정), 화면은 §2.7 "다시 활성화" 버튼. cancelled가 아닌 행은 409(상태 불일치).
  - **도착 status:** `race_date ≥ today`면 planned. `race_date < today`면 **done**(RC-29 b) — 시트가 RC-18 확인 문구를 먼저 띄우고, 확인해야 서버가 처리한다(`confirm_past` 없이 지난 날짜면 409 `CONFIRM_PAST`, 시트가 문구를 띄우는 근거). done 판정은 RC-8 규칙(`race_date < reference_today`)을 restore 안에서 같은 `today`로 적용한 결과이며, 이후 RC-20대로 회복 창(`race_date` + 회복 일수) 안이면 RC-6 회복 하향·계획 반영 질문 대상(복원된 adapt_choice가 unasked·later일 때), 창 밖이면 신호 없음. 복원은 미래 날짜여도 planned로 가므로 '확인 필요'(done 전용)가 되지 않는다.
  - **값 복원(RC-28 b·RC-38 a):** `adapt_choice`·`plan_state` ← 보존 필드, 보존 필드는 NULL로 비운다. 보존 필드가 NULL(v39 백필 cancelled 행, 위)이면 복원 값은 열린 질문 R2. 복원 후 §2.4 표의 해당 행대로 신호·D-day 대상에 복귀한다(RC-27 추가 문구).
  - **applied 재반영(RC-36 b):** 보존 `cancel_prev_plan_state='applied'`면 복원 때 일괄 적용을 다시 실행한다. 코드 사실(grep 2026-10-11): `plan_adjustment_service.accept`(`:164-176`)는 `reverted → accepted`를 **당일 행만** 허용한다(`date != today` → `LOCKED` — 지난 날짜뿐 아니라 미래 날짜 행도, 원본 변경 시 `STALE`). 그래서 RC-9로 reverted된 옛 묶음 행을 하나씩 다시 accept하는 방식은 당일 행 외에는 실패한다 → "accept 재실행"은 `race_plan_link`의 일괄 적용(RC-7, 사용자가 '조정할게요'를 고를 때와 같은 함수)을 복원 트랜잭션에서 다시 부르는 것으로 설계한다: 현재 계획에 대해 `race_impact`를 다시 계산하고 새 `batch_id` 묶음을 적용, 성공 시 `adapt`·`applied`. 미리보기(`RacePlanPrompt`) 없이 실행한다(RC-36 문구가 재실행이므로).
    - **실패 처리 제안(결정 아님, 열린 질문 R4):** ① 지난 날짜(`date < today`) 행은 `race_impact` 대상에서 뺀다(지난 훈련을 바꾸지 않음, §2.6-1 완료·매칭 행 제외와 같은 취지) — 대회가 이미 지나 모든 영향 행이 과거면 적용할 행 0건. ② 적용할 행이 0건이거나 적용이 실패(409 `LOCKED`·`STALE`·`REPLAN_LOCKED` 등)하면 **제안 (가)** 복원은 진행하고 `adapt_choice='adapt'`·`plan_state='stale'`('변경 후 미반영' 칩, 사용자가 칩에서 다시 반영) / (나) 복원 전체를 409로 거부(무변경) / (다) 복원 진행 + `later`·`none`. ③ 일부 행만 실패할 때 묶음 전체를 실패로 볼지(제안: 전체 실패 — RC-7 묶음 단위 원칙).
  - **A 충돌(RC-30 a·RC-35 b):** 복원 행이 `priority='A'`이고 다른 A(status planned 또는 done)가 있으면 서버는 409 `A_CONFLICT`(기존 A 요약 포함)를 돌려주고, 시트는 "지금 목표 대회는 B로 바뀌어요"(RC-15 문구) 확인을 띄운다. 확인하면 `demote_existing_a=true`로 다시 보내 같은 트랜잭션에서 기존 A를 RC-15 규칙(→ B·`adapt_choice='unasked'`·`plan_state='none'`)으로 강등한 뒤 복원한다. 확인을 취소하면 아무것도 바꾸지 않는다. `ux_race_one_a`(planned A ≤ 1)는 강등이 복원보다 먼저 실행되므로 지켜진다. **불변식 3(RC-35 b):** 기존 A가 활성 목표 대회여도 목표 연결 변경 없이 강등하고(활성 목표 → B, §2.2 해석 R1), 기존 A가 done이어도 강등한다((c) 기각 — §2.2 '이전 A가 done이면 그대로'는 목표 교체 경로 한정). 복원된 A는 연결 목표(cancelled)를 다시 활성화하지 않고 활성 목표 미연결 A로 둔다(완화된 불변식 3 허용).
  - 저장 전 검사(planned로 갈 때): 같은 날짜·거리 planned 행이 있으면 409(`ux_race_planned_same`). done으로 가는 복원은 두 인덱스(planned 전용) 검사 대상이 아니다.
  - 한 트랜잭션: (강등) + status·adapt_choice·plan_state 갱신 + 보존 필드 비움 + (applied였으면 일괄 적용 재실행, RC-36) + `updated_at`. 실패 시 처리는 위 R4 제안을 따르며, R4 결정 전에는 "실패 시 아무것도 바꾸지 않음"이 기본이다.
- 해소: 보존 방식(RC-38 a), applied 재반영(RC-36 b), 강등과 불변식 3·done 기존 A 강등(RC-35 b). **남은 열린 질문(§7):** R1 불변식 3 완화 문구 해석(§2.2), R2 보존 값 없는 행의 복원 값 — 제안: 등록·RC-37과 같은 `unasked`·`none`(대안: 백필 목표 상태에서 유도한 값 `adapt`·`none` 등), R4 RC-36 재반영 실패 처리(위 제안 (가)).

### 2.13 '확인 필요' 행 예정으로 되돌리기 (RC-32 a·RC-37 a)
- `race_calendar_service.reopen(conn, race_id, today, *, demote_existing_a=False)` → status done → planned, **`adapt_choice='unasked'`·`plan_state='none'`으로 초기화**(RC-37 a — 대상 행 대부분이 RC-12 b 백필 done·adapt·applied·A라 실제 반영 없는 applied를 남기지 않음; plan_state none은 §2.4 표에서 unasked와 짝인 값). 등록과 같이 계획 반영 질문 대상이 된다. 대상은 `is_needs_review(row, today)`가 참인 행만(§2.8). 아니면 409(상태 불일치). API `POST /api/v1/race-calendar/<id>/reopen`(경로 형태는 S0에서 확정), 화면은 §2.7 수정 시트 "예정으로 되돌리기" 버튼.
- 저장 전 검사는 등록과 같다: 같은 날짜·거리 planned 행이 있으면 409(`ux_race_planned_same`), A 행이 다른 A(planned·done)와 충돌하면 **RC-30 규칙 그대로**(RC-37 a): 409 `A_CONFLICT` → 시트 강등 확인 → `demote_existing_a=true`로 기존 A를 B·`unasked`·`none` 강등 후 되돌리기, 취소 시 무변경. 되돌린 A는 연결 목표(completed)를 다시 활성화하지 않고 활성 목표 미연결 A로 둔다(RC-35 완화된 불변식 3 허용, §2.4 R3).
- 한 트랜잭션: (강등) + status·adapt_choice·plan_state 갱신 + `updated_at`. 시트에서 날짜·이름 등을 함께 고친 경우 수정 저장(§2.3)과 되돌리기를 한 요청으로 묶을지, 수정 저장 후 되돌리기를 따로 부를지는 S0에서 확정(API 형태).
- 되돌린 행은 planned이고 `race_date ≥ today`라 '다가오는' 구역으로 가며 신호·D-day·계획 반영 질문 대상이 된다(§2.4 planned 행).
- 해소(RC-37 a·RC-35 b): 되돌린 행 값 = unasked·none, A 충돌 = RC-30 강등 확인, 활성 목표 미연결 planned A 허용. PLN-23(기존 플랜 삭제)로 백필 applied 행이 가리킬 기존 계획도 없으므로 초기화와 충돌하지 않는다.

## 3. 변경 파일 표 (RC-1 c 반영 재산정, 모두 300줄 이하)
| 파일 | 구분 | 내용 | 줄 |
|---|---|---|---|
| `src/db_schema_v38.py` | 신규(설계 중) | race_calendar 생성 + 인덱스 2개(context_episodes와 같은 파일), 취소 직전 값 보존 컬럼 `cancel_prev_adapt_choice`·`cancel_prev_plan_state`(RC-38 a, NULL 허용·기본 NULL, §2.12) | +44 |
| `src/db_schema_v39.py` | 신규 | 직전 DB 파일 자동 백업(RC-14), goals.race_id 추가, 전 목표 백필(RC-12, race_date 없는 비활성 목표는 생성일로 대회 행만 생성·캐시 NULL 유지 RC-19·21), `ux_goals_race`, 캐시 재동기화(멱등) | ~150 |
| `src/db_setup.py` | 수정 | SCHEMA_VERSION 39, ensure_v38·v39 호출 | +6 |
| `frontend/src/lib/components/RaceDateBanner.svelte`·`GoalResultCard.svelte` | 신규 | RC-11 배너, RC-17 카드(Today·허브 배치) | ~70/~80 |
| `src/training/goals.py` | 수정 | `_COLS`에 race_id, `add_goal(race_id=…)` + race_date 호환 래퍼, `update_goal` 대회 필드 위임(공유 함수 유지, V1-2) | 188→~225 |
| `src/services/race_calendar_service.py` | 신규 | add/list/get/update/cancel/restore, 지연 done 전이, 중복·A 검사(지난 날짜 허용, RC-18), 목록 3구역 분류('확인 필요'·다가오는·지난, RC-25)·`is_needs_review`(RC-22·23, §2.8 경로 공용), '다음 대회' 조회에서 제외, cancelled 행 수정 허용(RC-27 b)·`cancel` 시 직전 adapt_choice·plan_state 보존(RC-28)·`restore`(미래 → planned·지난 날짜 → done RC-29, 값 복원 RC-28·RC-38, applied였으면 `race_plan_link` 일괄 적용 재실행 RC-36, A 충돌 강등 RC-30·RC-35, §2.12)·`reopen` '확인 필요' done → planned·unasked·none, A 충돌 RC-30(RC-32·RC-37, §2.13), 목록 '취소됨' 구역 분류(RC-31), update 시 `race_date` 값 변경 여부(같은 값 = 미변경, RC-34)를 `push_cache`에 전달(RC-26), '오늘'은 `reference_today`(§2.9) | ~270(300 근접 — `restore`·`reopen`은 `race_calendar_state.py`로, 조회는 `race_calendar_query.py`로 분리 제안) |
| `src/utils/reference_day.py` | 신규(타 설계) | '오늘' 기준일 헬퍼 — `patterns/timezone-display.md` §2.4 소관, 이 번들은 사용만 | TZ 참조 |
| `src/services/race_goal_sync.py` | 신규 | 캐시 쓰기(RC-21 예외 행은 `race_date`를 실제로 입력·변경한 저장에서만 `race_date` 캐시 채움 RC-24·26, `distance_km`·`target_time_sec`는 항상), A 승격·교체(이전 A→B 강등, RC-15 — 복원 시 강등 RC-30도 같은 함수), `attach_race`(RC-11), 불변식 검사 함수 | ~150 |
| `src/services/goal_service.py` | 신규 | `create_goal_with_race`(목표+대회 한 트랜잭션) | ~80 |
| `src/services/plan_template_service.py` | 수정 | add_goal 호출에 race_id 전달(선택한 대회) | 202→~215 |
| `src/services/race_plan_link.py` | 신규 | race_impact 호출, 묶음 적용·되돌리기, 상태 전이, 미래 날짜 done 행 질문 제외(RC-23) | ~165 |
| 레이스 허브 결과 기록 후보 조회(`race_result_service` 또는 허브 서비스, 구현 시 grep 확정) | 수정 | '확인 필요' 행 제외(RC-33, `is_needs_review`) | +5 |
| `src/training/constraints.py` | 수정 | `b_race_week` 일수 인자 일반화(시그니처 호환) | +20 |
| `src/services/adjustment_signals_race.py` | 수정 | race_calendar·§2.4 표 기반 신호, 미래 날짜 done 행 제외(RC-23, `is_needs_review`) | +45 |
| `src/api/routes_race_calendar.py` | 신규 | CRUD, `/<id>/impact`, `/<id>/plan`(adapt/later/no_adapt/undo), `/<id>/restore`(RC-27~30, 409 상태 불일치·중복·`CONFIRM_PAST`·`A_CONFLICT`), `/<id>/reopen`(RC-32, 409 상태 불일치·중복), 목록 응답에 `needs_review`·구역 구분('확인 필요'·다가오는·지난·취소됨, RC-23·25·31) | ~185 |
| 목표 생성 API 핸들러(`src/api/routes_plan*.py`, 구현 시 grep 확정) | 수정 | race_id 입력 수용 | +20 |
| `scripts/check_data_consistency.py` | 수정 | 불변식 3(RC-35 완화: 활성 목표 연결 대회 존재·`planned|done`만, priority·planned A 역방향 검사 없음 — R1 해석 확정 시 조정)·4(RC-21 예외 행 — 캐시 `race_date` NULL인 비활성 연결 목표, 날짜 미변경 저장으로 NULL이 유지된 행 포함(RC-26) — 의 `race_date` 비교만 제외, 날짜 입력·변경으로 채워진 행은 비교 RC-24) 검사 2건 | +30 |
| `scripts/race_backfill_dry_run.py` | 신규 | DB 사본에 v39 실행 후 리포트(쓰기는 사본만) | ~90 |
| `frontend/src/routes/today/race/calendar/+page.svelte`·`+page.ts` | 신규 | 목록·빈·오류 상태, '확인 필요' 구역(RC-25)·배지·D-day 미표시(RC-23), '취소됨' 접힘 구역(RC-31) | ~180 |
| `frontend/src/lib/components/RaceEntrySheet.svelte`·`RacePlanPrompt.svelte`·`RaceDetailSheet.svelte` | 신규 | 시트 3종(RaceEntrySheet에 지난 날짜 확인 문구 RC-18, cancelled 수정 모드·"다시 활성화" 버튼 RC-27·지난 날짜 확인 RC-29·A 강등 확인 RC-30, '확인 필요' 행 "예정으로 되돌리기" 버튼 RC-32) | ~235/~130/~140 |
| `frontend/src/routes/coach/plan/new/+page.svelte`, `lib/planPrefill.ts`, `lib/api/plan.ts`, `lib/types/index.ts` | 수정 | 대회 고르기, race_id 전달(대회 캘린더 API 클라이언트 `restore`·`reopen` 포함은 구현 시 파일 확정) | +40/+15/+10/+10 |
| `frontend/src/routes/today/race/+page.svelte`, `coach/plan/[id]/+page.svelte` | 수정 | 캘린더 카드, 배지, "대회 바꾸기" | +20/+25 |
| tests: `test_db_schema_v39.py`, `test_race_calendar_service.py`, `test_race_goal_sync.py`, `test_goal_service.py`, `test_race_plan_link.py`, `test_routes_race_calendar.py`, `test_goals.py`(+), `test_plan_template_service.py`(+), `test_constraints.py`(+), `test_db_schema_v32.py`(회귀 유지); 프론트 시트 3종 | 신규·수정 | 함수마다 1개 이상 | ~75개 |
- 바꾸지 않음: `goals.race_date`를 읽는 40여 파일(캐시 유지), `race_results`, `/today/race/races`.
- v1(V1-13): v1 UI·라우트는 깨져도 된다 — 이 번들은 v1 파일을 고치지 않고 v1 보호·호환 코드도 넣지 않는다. 공유 함수(`training/goals.add_goal`·`update_goal`)는 CLI·백테스트·v2 경로 때문에 유지·수정 대상이다.

## 4. 스키마 순서·마이그레이션·단계·검증
**버전 순서(확정 제안):** v37 `plan_adjustments` 재생성(`source`에 `race` 포함) → v38 `context_episodes`·`race_calendar` 생성(가산만) → **v39 goals.race_id + 백필**. goals 참조를 v38에 넣지 않는 이유: v38은 다른 번들과 공유하는 가산 단계라 실패·롤백이 쉬워야 하고, 백필은 race_calendar 최종 컬럼에 의존하며 실패 시 v38까지 묶여 막히면 안 된다.

**v39 백필 절차(직전 백업 + 한 트랜잭션, 멱등, RC-14 a):**
0. user_version < 39이면 트랜잭션 전에 DB 파일을 SQLite backup API로 같은 폴더에 복사(`running.db.pre-v39-<타임스탬프>`, 커밋 대상 아님). 백업 실패 시 마이그레이션 중단.
1. `goals.race_id` 컬럼이 없으면 추가.
2. `race_date IS NOT NULL AND race_id IS NULL`인 목표를 id 순으로: 같은 날짜·거리(±0.01km)의 cancelled 아닌 대회가 있으면 연결, 없으면 생성(`origin='goal'`, name=goal.name, goal_type=target_time_sec 유무로 time/finish, goal_value=target_time_sec). 활성 목표 → `priority='A'`, adapt_choice `adapt`, plan_state(그 목표의 planned_workouts가 있으면 `applied`, 없으면 `none`), status planned. 비활성 목표도 전부(RC-12 b): completed → status done·adapt·applied, cancelled → status cancelled·plan_state none, 둘 다 `priority='A'`. 재사용은 활성 목표는 planned 대회, 비활성 목표는 같은 상태 대회만(불변식 3 보호).
3. race_date 없는 목표: **활성**이면 race_id NULL 유지, 앱에서 날짜 입력 배너로 유도(RC-11 b, 마이그레이션은 대회를 만들지 않음). **비활성**이면 목표 생성일 `date(goals.created_at)`을 race_date로 써서 2단계와 같은 규칙으로 대회를 만들거나 재사용하고 `goals.race_id`만 연결한다(RC-19 b; completed → done, cancelled → cancelled, `priority='A'`, `origin='goal'`). **`goals.race_date` 캐시는 NULL로 둔다(RC-21 b)** — 이 단계는 캐시를 쓰지 않는다. `goals.created_at`은 `NOT NULL DEFAULT (datetime('now'))`(무표기 UTC)라 값은 항상 있다 — 날짜 추출 시 UTC/현지 변환 여부는 구현 시 확인. 생성일로 만든 행임을 알 수 있게 `note`에 표시를 남기는 것을 제안한다(값 형식은 구현 시).
4. 이미 연결된 목표의 캐시가 대회 값과 다르면 **goals 값을 대회에 반영**하고 로그(롤백 후 구 코드가 goals만 고친 경우의 재동기화). 불변식 4 예외 행(`status != 'active' AND race_date IS NULL`)의 `race_date`는 비교·반영하지 않는다(NULL로 대회 날짜를 덮지 않음, RC-21).
5. `ux_goals_race` 생성. 불변식 3(RC-35 완화 조건, §2.2) 위반이 있으면 예외 → 트랜잭션 롤백, user_version 미갱신.
- **PLN-23 영향:** v39 백필은 `planned_workouts`를 쓰지·지우지 않는다(2단계에서 활성 목표의 `plan_state` 판정용으로 행 존재만 읽음) → 기존 플랜 삭제와 무관, 단순화할 부분 없음.

**롤백·호환:**
- 코드 롤백(v36~38 코드로 되돌림): 스키마는 앞으로만 간다. 구 코드는 user_version ≥ 자기 버전이면 마이그레이션을 건너뛰고, race_id·race_calendar를 모른 채 캐시 컬럼(race_date 등)을 그대로 읽고 쓴다 → 동작한다. 재업그레이드 시 v39 4단계가 차이를 흡수한다(ensure_v39는 user_version과 무관하게 재동기화 함수를 한 번 더 부를 수 있게 분리).
- 데이터 롤백: 중단 시 단일 트랜잭션 롤백으로 v38 상태 유지, 손상·오판 시 0단계 백업 파일로 복원(RC-14 a).
- v1 화면·경로: 깨져도 된다(V1-13) — 호환을 고려하지 않는다. 공유 함수 `add_goal`·`update_goal`의 호출 계약(`race_date` 호환 래퍼)은 CLI·백테스트·v2 경로 기준으로 지킨다.

**단계:**
1. **S0** system-architect와 `source='race'`·API 형태·v37~39 순서 확정. 선행: `reference_day.py`(timezone-display.md 단계 5-1).
2. **S1 스키마** v38·v39, 검증: 빈 DB/DB **사본** 마이그레이션, 재실행 멱등, `race_backfill_dry_run.py` 리포트(목표 수/연결/재사용/생성/race_date 없음(활성 NULL 유지·비활성 생성일 사용 건수 분리, RC-19)/캐시 차이), 불변식 1~4 위반 0, 백업 파일 생성·복원 리허설, 비활성 목표 done/cancelled 매핑, race_date 없는 비활성 목표 → 생성일 날짜로 대회 생성·연결(RC-19)되고 `goals.race_date`는 NULL 유지(RC-21)·재실행 시 4단계가 대회 날짜를 바꾸지 않음·`check_data_consistency.py` 불변식 4 위반 0, race_date 없는 활성 목표 → NULL 유지, 미래 날짜 completed 목표 → done 대회 행 생성(RC-22 표시 대상 건수를 리포트에 포함), `test_db_schema_v32.py` 그대로 통과.
3. **S2 서비스·목표 경로** `race_calendar_service`·`race_goal_sync`·`goal_service`·goals.py 래퍼. 검증: **활성 목표 유니크 회귀**(add_goal 2회 → 활성 1건, 새 목표 대회만 A, 이전 planned A는 B·unasked), 캘린더에서 A 날짜 수정 → goals 캐시 갱신, `update_goal(race_date)` → race_calendar 갱신(양방향 왕복), CLI·백테스트(`plan_backtest*.py`) 경로 회귀, RC-21 예외 행(생성일 대회·캐시 NULL)을 캘린더 시트로 수정하며 날짜 변경 → 같은 트랜잭션에서 `goals.race_date` 캐시 채워짐·이후 `check_data_consistency.py` 불변식 4 일반 비교 통과(RC-24), 같은 행을 날짜 그대로 두고 이름·거리만 수정 → `race_date` 캐시 NULL 유지·`distance_km` 캐시는 갱신·불변식 4 위반 0(RC-26), cancelled 예외 행 수정에도 같은 두 결과(RC-27 b), cancelled 행 수정 → status cancelled 유지·adapt_choice·plan_state 불변(RC-27 b), 같은 날짜를 다시 골라 저장 → 값 미변경으로 `race_date` 캐시 NULL 유지(RC-34), `cancel` → 보존 필드에 직전 adapt_choice·plan_state 기록 후 RC-9 되돌리기(RC-28), `restore`: 미래 날짜 → planned·보존 값 복원·보존 필드 NULL(RC-28)·지난 날짜 `confirm_past` 없으면 409·있으면 done(RC-29)·A 충돌 시 409 `A_CONFLICT`·`demote_existing_a` → 기존 A B·unasked·none 강등 후 복원·`ux_race_one_a` 위반 0(RC-30)·cancelled 아닌 행 409·같은 날짜·거리 planned 존재 시 409·실패 시 무변경(RC-27), 활성 목표 대회인 기존 A(planned·done 모두) 강등 후 `check_data_consistency.py` 불변식 3 위반 0(RC-35), 보존 applied 행 복원 → `race_plan_link` 일괄 적용 재실행·새 `batch_id`·`adapt`·`applied`(RC-36, 실패 분기는 R4 확정 후), 보존 필드 NULL 백필 cancelled 행 복원(R2 확정 후), `reopen`: '확인 필요' 행만 planned·`unasked`·`none`·그 외 409·중복 409·A 충돌 409 `A_CONFLICT`→강등 후 되돌리기(RC-32·RC-37), plan_template_service 생성 경로, race_date 없는 목표 → `attach_race`, A done 후 목표 활성 유지.
4. **S3 영향·연동** `race_impact`·`race_plan_link`. 검증: 보호 행 불변, 묶음 적용 → 되돌리기 왕복, B/C 절반 올림 일수, stale → 재반영, 삭제 시 되돌리기, §2.4 표 행별 신호 테스트(no_adapt 무신호, later·unasked done 하향 허용, applied 하향 없음), 지연 done 전이가 `reference_today`를 쓰는지(최근 활동 +7·UTC 날짜 경계 픽스처, 활동 없음 → 서버 로컬 폴백), 지난 날짜 등록 대회가 회복 창 안이면 RC-6 하향 트리거·계획 반영 질문 대상, 창 밖이면 신호 없음(RC-20), 미래 날짜 done 행(`race_date ≥ today`)은 `race_plan` 수집·RC-6 트리거·계획 반영 질문·'다음 대회' 조회에서 모두 빠지고 목록에는 `needs_review`로 남음, `today` 경계(정확히 오늘 날짜 = 배지 대상)(RC-23, §2.8), 목록 응답에서 배지 행이 '확인 필요' 구역에만 있고 '다가오는'에 없음(RC-25), cancelled 행은 §2.4 신호·D-day·질문에서 빠지고 복원 후 planned 행은 `race_plan` 수집·'다음 대회' 조회에 다시 잡힘(RC-27), 지난 날짜 복원(done) 행이 회복 창 안이고 복원 값이 unasked·later면 RC-6 하향·계획 반영 질문 대상(RC-29·RC-20), '확인 필요' 행이 결과 기록 후보에서 빠지고 `reopen` 후 planned 행은 신호·'다음 대회'에 잡힘(RC-33·RC-32), 목록 응답에서 cancelled 행은 '취소됨' 구역에만 있음(RC-31).
5. **S4 API** 400/404/409 매핑, 지난 날짜 등록 → 201(거부 없음)·다음 조회에서 done(RC-18), `POST /<id>/restore` 200/404/409(상태·중복·`CONFIRM_PAST`·`A_CONFLICT`, RC-27~30), `POST /<id>/reopen` 200/404/409(RC-32). **S5 화면** 375px 브라우저: 등록 → 질문 → 일괄 적용 → 되돌리기, 지난 날짜 입력 시 확인 문구 → 취소(입력 유지)/확인(저장 후 '지난' 구역, 회복 창 안이면 계획 반영 질문 노출 RC-20), 미래 날짜 done 행이 별도 '확인 필요' 구역에 배지·D-day 미표시로 보임(행 없으면 구역 없음) → 수정·삭제로 정리(RC-22·23·25), '취소됨' 구역 기본 접힘·펼치기(RC-31) → 취소된 대회 열기 → 수정 저장(취소됨 유지) → "다시 활성화" → 다가오는 구역·D-day 표시·취소 전 칩 복원(RC-27·28), 지난 날짜 cancelled 행 "다시 활성화" → RC-18 확인 문구 → 취소(무변경)/확인('지난' 구역, RC-29), A cancelled 행 복원 시 강등 확인 → 취소(무변경)/확인(RC-30), '확인 필요' 행 "예정으로 되돌리기" → 다가오는 구역·D-day 표시(RC-32), 목표 생성에서 B 대회 고르기 → A 승격, 계획 상세 "대회 바꾸기"(저장 전 미리보기·취소 시 무변경), 날짜 입력 배너, 결과 기록·다음 목표 카드, 삭제 미리보기, 데모 모드, h1·44px·Esc 포커스 복귀.
6. `pytest tests/` 전체, `check_docs.py`, `check_data_consistency.py`, BACKLOG·decisions 기록.

## 5. 결정 필요
- 결정 완료(표 참조: `decisions-table.md` RC-1~38, V1-1·V1-2·V1-13, PLN-23, 연관 ADJ-11·12·17, NEW-4·5·11, TZ-1 추가 결정). 화면은 A11Y-2(44px) 준수.
- 사용자 확정 대기: RC-18 지난 날짜 확인 문구(§2.7 초안, TXT-1).
- 결정 필요(§7 R1~R4): R1 불변식 3 완화 문구 해석(§2.2), R2 보존 값 없는 행의 복원 값(§2.12), R3 활성 목표 미연결 A의 §2.4 행(§2.4), R4 RC-36 재반영 실패 처리(§2.12).

## 6. 범위 밖 메모
- 외부 캘린더 가져오기(`origin='import'`), CalDAV·Garmin에 푸시된 race 행 정리(A6 D5와 같은 문제).
- 생성기가 race_calendar를 직접 제약으로 받는 방식, 다중 A 시즌 계획(계획 엔진 영역).
- goals 캐시 컬럼(race_date·distance_km·target_time_sec) 제거와 읽기 경로 40여 곳 전환.
- `/today/race/races`와 캘린더 지난 대회 구역 통합(IA 정리 때). 대회 데이터 AI 전송 동의는 NEW-12와 함께.

## 7. 동기화 중 발견한 모호점
- RC-17(b)로 A 대회가 done이어도 목표가 활성이므로, RC-1 설계의 불변식 3(`status='planned'`)을 `planned|done`으로 넓혔다(§2.2, `check_data_consistency.py` 검사 조건 반영).
- 해소(RC-19·RC-21·RC-24): 생성일로 대회 행만 생성, `goals.race_date` 캐시 NULL 유지(불변식 4 예외), 캘린더 시트 수정 시 `push_cache`가 캐시를 채워 예외 해소(§2.2). (`goals.distance_km`는 `NOT NULL`이라 백필 대회 거리는 항상 있음, `db_setup.py` goals DDL.) 해소(RC-26·RC-27 b): 날짜를 실제로 입력·변경한 저장에서만 캐시를 채우고, cancelled 행도 수정 가능(§2.2·§2.12). 해소(RC-34 a): 같은 날짜 재선택은 '입력' 아님(값 비교만, §2.2).
- 해소(RC-22·RC-23): 미래 날짜 done 대회는 목록 '확인 필요' 배지, 신호·D-day 제외(§2.4·§2.7·§2.8). 해소(RC-25 b): 별도 '확인 필요' 구역(§2.7). 해소(RC-33·RC-32): 결과 기록 카드 제외, 수정 시트 '예정으로 되돌리기'(§2.13). 해소(RC-37 a): 되돌린 행은 unasked·none, A 충돌은 RC-30(§2.13). **남은 부분:** 구역 순서·안내 문구(목록 맨 위 제안, 구현 중 확인).
- RC-27 복원 세부: 해소(RC-28·RC-29·RC-30·RC-31·RC-35·RC-36·RC-38).
- **열린 질문(7차 동기화):**
  - **R1 (RC-35 문구 해석):** 'A 이거나 활성 목표 미연결'을 대회 행마다 글자 그대로 읽으면 RC-30이 활성 목표의 A를 강등한 결과(활성 목표 → B)가 위반이다. RC-35가 '목표 연결 변경 먼저'(a)를 기각했으므로 설계는 이 상태를 허용으로 읽고 `check_data_consistency.py` 불변식 3을 "활성 목표 연결 대회 존재·`planned|done`"으로만 줄였다(§2.2). 이 해석이 맞는지, 아니면 강등 시 활성 목표 연결을 끊는(목표 `race_id` 처리) 뜻인지 확인 필요.
  - **R2 (RC-36·RC-38):** 보존 필드 NULL 행(v39 백필 cancelled 행뿐)의 복원 값 — 제안 `unasked`·`none`(등록·RC-37과 같음).
  - **R3:** 활성 목표 미연결 A(RC-30 복원·RC-37 되돌리기)가 §2.4 'A·adapt 고정·applied' 행이 아니라 adapt_choice별 일반 행을 따르는지(설계 서술은 일반 행).
  - **R4 (RC-36):** 재반영 실패 처리 — 지난 날짜 행 제외, 0건·409 시 (가) 복원 진행 + `adapt`·`stale`(제안) / (나) 복원 거부 / (다) `later`·`none`, 일부 실패 시 묶음 전체 실패 여부(§2.12).
- RC-15(b)는 planned A 교체만 정의한다. A가 이미 done(RC-17로 목표 활성)인 상태에서 새 목표를 만들 때 이전 A를 그대로 두는 것은 설계 해석이다(RC-35 완화로 남은 done A는 활성 목표 미연결 A로 허용 — 불변식 3과는 정합).
- PLN-23(기존 플랜 삭제): v39 백필은 `planned_workouts`를 읽기만 해 영향 없음(§4), 계획 연동·`race_plan` 수집은 기존 플랜 행에 의존하지 않음(§2.6-2). 기존 race 행 ↔ `planned_workout_id` 백필은 하지 않는다.
- RC-13(a)는 "목표 화면" 한정이다. 캘린더 시트에서 A의 날짜·거리를 고치는 경우도 같은 컴포넌트·§2.6-3 경로라 저장 전 미리보기를 적용했다. 범위 확인 필요.
- 해소(RC-18·RC-20): 지난 날짜 등록 허용 + 확인 문구(문구는 TXT-1 확정 대기), 날짜 규칙 그대로 RC-6 하향·계획 반영 질문 대상(§2.4).
- 해소(ADJ-17): race는 checkin 바로 뒤(§2.4).
- 자동 done 전이 시점이 '최근 활동 시간대' 기준이라, 사용자가 시간대를 옮긴 직후(새 시간대 활동 전)에는 전이가 하루 이르거나 늦을 수 있다(헬퍼 해석 모호점은 timezone-display.md §7).
- V1-2·V1-13 적용: v1 UI·라우트는 깨져도 되고 보호·호환 코드는 넣지 않는다. 공유 함수 `add_goal`·`update_goal`은 CLI·백테스트(`plan_backtest.py:67`·`plan_backtest_replan.py:20`)·v2 경로 때문에 유지하며 `update_goal` 위임도 유지한다(§1·§3·§4).
