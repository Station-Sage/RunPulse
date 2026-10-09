# DESIGN — 부작용 없는 재계획(REPLAN) — A6 링크 활성화 전제

상태: 구현 완료(T1~T7·T9 배포, T8은 한계로 종결) · 2026-10-09 · 작성: system-architect
상위: ADR-035 부록 "A6 REPLAN 배너"·"K1/K2 확인 결과", `DESIGN-PLAN-A6-REPLAN.md` §3
범위: 재계획의 데이터 의미(목표 정체성, 교체 범위, 조정·매칭 보존, 롤백·미리보기, API). UI는 범위 밖(product-architect).

## 1. 진단 검증 (코드 직접 확인)

| ID | 내용 | 판정 | 근거 |
|---|---|---|---|
| K1 | `add_goal`이 기존 active를 종료하지 않음 → active 중복 | **정확** | `src/training/goals.py:83-91` INSERT만. `goals.status` CHECK = `active/completed/cancelled` (`db_setup.py:473`) |
| K1a | 중복 시 활성 목표 선택 기준이 코드마다 다름 | **추가** | `get_active_goal`: `created_at DESC, id DESC`. `plan_move`·`plan_adjustment_service`·`plan_advisory`·`routes_plan_adjust`: `id DESC`. `race_hub_service`·`activity_impact_service`: `race_date ASC, id DESC`. **CalcContext `context_runs.get_active_goal`: `race_date` 오름차순, id 기준 없음** → 대회일이 같으면 비결정적. 대회일·거리를 바꿔 다시 만들면 Race hub·marathon_shape는 **옛 목표**, 계획 화면은 새 목표를 보는 식으로 갈린다 |
| K1b | 새 goal = 계획의 정체성 리셋 | **추가** | `plan_service._plan_date_range`/`_effective_start`가 goal의 `plan_weeks`·`created_at`에서 범위를 구한다(`planned_workouts`에 goal_id 없음). 새 goal이면 이행률 기록·N주차가 1부터 다시 시작. `plan_progression`(goal_id 키, v29) 사다리 단계가 0으로 리셋. `plan_rules_version`은 기존 goal 값이 아니라 그 시점 플래그로 다시 정해진다 |
| K2 | `save_weekly_plan` 날짜별 DELETE(source='planner') 후 INSERT, 시작 = 이번 주 월요일 | **정확** | `planner.py:231-255`, `plan_template_service.py:183-190` |
| K2a | 끊긴 `session_outcomes`가 활동을 계속 점유 | **추가(중대)** | 삭제된 행을 가리키는 outcome이 남고, `matcher.match_week_activities`가 `session_outcomes WHERE planned_id != ?`로 활동을 claimed 처리(`matcher.py:91-93`) → 새 행이 같은 활동과 다시 매칭되지 않음 → 이번 주 지난 날이 **미이행으로 바뀐다**(REPLAN 조건을 스스로 강화) |
| K2b | 수락 조정 stale | 정확 | `plan_overlay._matches`는 workout_id 체인 + 지문. 새 id에는 조정이 걸리지 않아 사용자 skip(D9 `state='skipped'`)·휴식이 사라지고 원안이 다시 보인다 |
| K2c | proposed 조정 고아 | 추가 | `ensure_proposal`은 새 workout_id로 새 제안을 만들고 옛 proposed 행은 영구 proposed로 남는다 |
| K2d | 외부 푸시 중복 | 추가 | Garmin: 새 행은 `garmin_workout_id` NULL → 재전송 시 Garmin 캘린더에 중복, 옛 예약은 남음(`garmin_push.py:95`). CalDAV UID = `runpulse-<workout id>` → 옛 이벤트 잔존 + 새 이벤트(`caldav_push.py:80`). ICS 피드는 날짜+슬롯 UID라 영향 없음 |
| K3 | `user_training_prefs` 초기화 | **추가(재계획과 무관한 기존 버그)** | `create_plan_from_template`이 `upsert_user_training_prefs(conn)`를 기본값으로 호출(`plan_template_service.py:181`) → 휴식 요일·차단일·롱런 요일·인터벌 반복거리·max_q가 매번 0/기본값으로 덮어써짐(레거시 설정 화면 값 손실) |
| K4 | 원자성 없음 | 추가 | `add_goal`·`save_weekly_plan`(주마다)·`upsert_user_training_prefs`가 각각 commit → 도중 실패 시 목표만 있고 계획 일부만 있는 상태 |
| K5 | 같은 goal로 다시 생성해도 "지금 흐름"이 반영되지 않음 | **추가(설계 핵심)** | `schedule_for_goal`은 시작 부하를 `as_of=min(plan_start, today)`=계획 시작일 기준으로 계산(`planner_schedule.py:133`). goal을 재사용해 미래 주만 다시 만들면 **원래 램프를 그대로 재현**한다. 현재 POST가 "맞추는" 효과를 내는 이유는 새 goal의 시작 주가 이번 주로 바뀌기 때문뿐 |
| K6 | 다른 목표로 새로 만들 때 옛 미래 행 잔존 | 추가 | 새 대회일이 옛 대회일보다 이르면 그 뒤 날짜의 옛 planner 행이 남아 Today·matcher·ICS(날짜 기준 조회)에 나타남 |

참고: `rematch.replan_future`(CLI)가 이미 "오늘 이후·미완료만 재생성"을 구현했지만 K5(같은 goal 램프 재현)·K2a(완료 판정에 outcomes 미반영)·조정 미고려 문제가 같고 원자성도 없다. 재사용하지 않고 아래 서비스로 대체한다.

## 2. 재계획의 의미 (제안)

> **재계획 = 같은 목표(goal) 안에서 일정의 "기준점(anchor)"을 새로 찍고, 기준점 이후 미래 주만 다시 만든다.** 목표 행·지난 계획·매칭·조정 이력은 그대로 둔다.

### 2.1 목표 정체성 — goal 재사용 + 기준점 이력 (D2 추천)
- 새 테이블 `plan_replans`(스키마 v32). goal은 하나로 유지되고 기준점만 쌓인다.

```sql
CREATE TABLE IF NOT EXISTS plan_replans (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    goal_id         INTEGER NOT NULL,
    anchor_monday   TEXT    NOT NULL,          -- 새 일정이 시작되는 월요일(교체 범위 시작)
    start_km        REAL,                      -- 기준점 시작 주간 km(입력 또는 직전 실제)
    start_long_km   REAL,
    start_source    TEXT    NOT NULL,          -- 'user' | 'history'
    target_time_sec INTEGER,                   -- 목표 기록을 바꿨다면 새 값(없으면 NULL)
    replaced_json   TEXT    NOT NULL DEFAULT '[]',  -- 교체 전 행 스냅샷(되돌리기용)
    status          TEXT    NOT NULL DEFAULT 'applied' CHECK (status IN ('applied','undone')),
    created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
    undone_at       TEXT
);
CREATE INDEX IF NOT EXISTS idx_plan_replans_goal ON plan_replans(goal_id, status, anchor_monday);
```
- `schedule_for_goal`: applied 기준점들을 날짜순으로 접는다. 기준점 이전 주 = 기존 일정(접두), 기준점 이후 = `build_schedule(남은 주, start_km, start_long, …)`(시작 부하 `as_of=anchor`). `week_target`의 인덱스는 원래 계획 시작 기준 그대로 → N주차·이행률·`plan_progression`·`plan_adjustments.goal_id`·Race hub 모두 불변(K1·K1b·K5 해소).
- 기준점이 없으면 출력이 현재와 바이트 단위로 같아야 한다(회귀 테스트).
- `goals.status`에 `superseded` 추가 불필요 → CHECK 변경용 테이블 재생성 마이그레이션 없음.

### 2.2 교체 범위 — 다음 월요일부터 (D1 추천)
- `anchor_monday` = 오늘 이후 첫 월요일(오늘이 월요일이어도 다음 주 월요일 — 오늘 행은 이미 Today·조정 대상).
- 근거: ADR-035 조정은 수락 당일만, move는 `CROSS_WEEK` 금지 → **다음 주 이후에는 accepted 조정이 구조적으로 없다**. 매칭·outcome도 미래라 없다. 부분 주 합성(이미 한 롱런 + 새 롱런 중복, Q 간격) 문제도 생기지 않는다. "이번 주 = 행 액션(ADR-035), 다음 주부터 = 재계획"으로 역할이 갈린다.
- 이번 주 남은 날은 바뀌지 않으므로 미리보기에 "다음 주 월요일(MM-DD)부터 적용"을 명시해야 한다(UI 표기는 product-architect).
- 거부: 대회 주가 이번 주면 409 `RACE_WEEK`. 활성 goal 없음 404 `NO_GOAL`. 이미 같은 anchor로 applied 기준점이 있으면 그 기준점을 대체(이전 것 undone 처리 후 재적용, 한 트랜잭션).

### 2.3 행 보호 규칙 (방어적 불변식)
교체 범위 `[anchor_monday, race_date]`의 `source='planner'` 행 중 아래는 지우지 않고 `preserved[]`로 보고한다(구조상 0건이 정상, 발생 시 로그).
- `completed=1` 또는 `matched_activity_id IS NOT NULL` 또는 `session_outcomes.planned_id`가 존재
- `plan_adjustments`에 accepted 행이 있음(workout_id 기준, move면 `after.date` 포함)

지우는 행에 달린 **proposed** 조정은 삭제한다(사용자 결정이 없고 `ensure_proposal`이 조회 시 새 id로 다시 만든다. reverted로 바꾸면 '거절'과 구분이 안 된다).

### 2.4 미리보기·되돌리기 (D4·D6 추천: 둘 다)
- 미리보기(쓰기 없음): 주별 전/후 `{week, km_before, km_after, long_before, long_after, q_before, q_after}` + `anchor_monday` + `preserved` 예상. 생성기(`generate_weekly_plan`)는 쓰기를 하지 않으므로 기준점을 인메모리로 넘겨 계산(T2에서 확인·보장).
- 적용: 한 트랜잭션(SAVEPOINT) — 기준점 INSERT, 교체 행 스냅샷을 `replaced_json`에 저장, DELETE/INSERT, proposed 정리. 모든 단계 commit 금지 버전 사용(K4).
- 되돌리기: 마지막 applied 기준점만, 조건 = 그 기준점으로 만든 행이 아직 하나도 매칭·완료·조정되지 않음(실제로는 `anchor_monday` 전까지). 스냅샷 복원 + `status='undone'`. 조건 위반 409 `REPLAN_LOCKED`.

### 2.5 API — 재계획 전용 엔드포인트 (추천)
- `GET  /api/v1/coach/plan/replan/preview?recent_weekly_km=&recent_long_km=&target_time_sec=`
- `POST /api/v1/coach/plan/replan` body `{recent_weekly_km?, recent_long_km?, target_time_sec?, expect_anchor}` → `{replan_id, anchor_monday, weeks:[…], preserved:[…], external:[…]}`. `expect_anchor`가 서버 계산과 다르면 409 `CONFLICT`(미리보기 이후 날짜가 넘어간 경우).
- `POST /api/v1/coach/plan/replan/<id>/undo`
- 대상 goal은 서버의 활성 goal(클라이언트 goal_id 불신, 동시에 `goal_id`를 보내면 불일치 409).
- 거리·대회일을 바꾸는 것은 재계획이 아니라 새 목표 → 기존 `POST /coach/plan`(아래 2.6).
- `POST /coach/plan`에 `replan` 플래그를 얹지 않는 이유: 같은 엔드포인트가 "새 goal 생성"과 "goal 유지"라는 반대 의미를 갖게 되고, 기존 폼 호출이 실수로 교체 범위를 바꿀 위험이 생긴다.

### 2.6 `POST /coach/plan`(새 목표) 정합성 — K1·K3·K4·K6 (D3 추천)
- 불변식: 활성 goal은 최대 1개. 새 goal 생성 시 기존 active → `cancelled`(기존 값, 마이그레이션 없음) + 그 goal의 오늘 이후 미참조 planner 행을 2.3 규칙으로 삭제.
- DB 수준 보장: v32에 `CREATE UNIQUE INDEX ux_goals_one_active ON goals(status) WHERE status='active'`. 마이그레이션은 기존 중복을 `get_active_goal` 기준 최신 1개만 남기고 나머지 `cancelled`.
- 활성 goal 조회를 `goals.get_active_goal` 하나로 통일(직접 SQL 7곳 교체). CalcContext `get_active_goal`은 `ORDER BY race_date, id DESC`로 결정적 정렬(Calculator 쪽 raw SQL 아님, CalcContext 내부 수정).
- K3: 기본값 upsert 제거 → 행이 없을 때만 `INSERT OR IGNORE`.
- K4: 생성 전체를 한 트랜잭션으로(내부 함수 `commit=False`).

### 2.7 외부 출력
- ICS: 날짜+슬롯 UID라 추가 작업 없음.
- Garmin/CalDAV 푸시 행(`garmin_workout_id` 있음)을 교체하면 외부에 옛 항목이 남는다 → D5.

## 3. 사용자 결정 필요

| ID | 질문 | 선택지 | 추천 |
|---|---|---|---|
| D1 | 교체 시작일 | (a) 다음 월요일 (b) 내일 + 부분 주 합성 규칙(롱런·Q 중복 방지, move 대상일 잠금) | **(a)** — 조정·매칭 충돌이 구조적으로 없음. (b)는 합성 규칙·잠금 범위가 새로 필요 |
| D2 | 목표 정체성 | (a) goal 재사용 + `plan_replans` 기준점 (b) 새 goal + `superseded` 상태(CHECK 변경 위해 goals 재생성 마이그레이션, 이행률·사다리·N주차 체인 처리 필요) | **(a)** |
| D3 | 새 목표 생성 시 기존 활성 목표 | (a) `cancelled` + 미래 미참조 행 삭제 + 유니크 인덱스 (b) 동시 활성 허용 | **(a)** — `planned_workouts`에 goal_id가 없어 두 계획이 날짜로 충돌 |
| D4 | 미리보기 | (a) 필수(미리보기 → 적용) (b) 즉시 적용 | **(a)** |
| D5 | Garmin/CalDAV 푸시된 미래 행 | (a) 교체 시 외부 항목 삭제까지 구현(Garmin 삭제 API 가용성 확인 필요) (b) 응답 `external[]`로 알리고 외부 정리는 사용자 | **(a)**, 불가하면 (b) + 별도 BACKLOG |
| D6 | 되돌리기 | (a) 마지막 1건, 기준점 시작 전까지 (b) 없음 | **(a)** |
| D7 | K3(설정 초기화) | 재계획과 별개 BUG로 등록·선수정 여부 | 등록 후 T7로 선수정 |

## 4. 구현 단계 (파일 300줄 이하, 새 함수마다 테스트 ≥1)

| T | 내용 | 파일 | 테스트 |
|---|---|---|---|
| T1 | 스키마 v32: `plan_replans`, `ux_goals_one_active`(중복 정리 포함) | `src/db_schema_v32.py`(신규), `src/db_setup.py` SCHEMA_VERSION | `tests/test_db_schema_v32.py`: 멱등, 중복 active 정리, 두 번째 active INSERT 실패 |
| T2 | 기준점 접기: `plan_anchor.fold(conn, goal)` + `schedule_for_goal`이 사용, 인메모리 기준점 인자(미리보기용) | `src/training/plan_anchor.py`(신규), `planner_schedule.py`(185줄) | `tests/test_plan_anchor.py`: 기준점 없음 = 기존과 동일, 기준점 후 시작 부하 = anchor 기준, 주 인덱스 불변, 생성기 쓰기 없음 |
| T3 | 보호 교체: `replace_range(conn, plan, start, end, commit=False)` → `{deleted, preserved, snapshot, external}`, proposed 정리 | `src/training/plan_replace.py`(신규) | `tests/test_plan_replace.py`: matched/outcome/accepted 보호, proposed 삭제, 스냅샷 복원 왕복 |
| T4 | 서비스: `preview`/`apply`/`undo`, SAVEPOINT, RACE_WEEK·NO_GOAL·CONFLICT·REPLAN_LOCKED | `src/services/plan_replan_service.py`(신규) | `tests/test_plan_replan_service.py`: 각 함수·거부 코드, 실패 시 롤백 |
| T5 | API 3개 | `src/api/routes_plan_replan.py`(신규, blueprint 등록) | `tests/test_api_plan_replan.py`: 200/400/404/409/503 |
| T6 | `POST /coach/plan` 정합성: 기존 active cancel + 미래 행 정리(T3 재사용), 단일 트랜잭션, 활성 goal 조회 통일, CalcContext 정렬 | `plan_template_service.py`, `goals.py`(`commit` 인자), `context_runs.py`, 직접 SQL 7곳 | `tests/test_plan_template_service.py` 보강, `tests/test_goals.py`: active 1개 보장 |
| T7 | K3: prefs 기본값 덮어쓰기 제거 | `plan_template_service.py`, `planner.py`(`ensure_user_training_prefs`) | 기존 prefs 유지 테스트 |
| T8 | 외부 정리(D5 결과에 따라) | `src/training/garmin_push.py`, `caldav_push.py` | 삭제 호출 mock 테스트 |
| T9 | 프론트: `REPLAN_LINK_ENABLED` 대상 = 재계획 미리보기(UI 설계는 product-architect) | `frontend/src/lib/replanBanner.ts` 외 | mjs 순수 함수 + 390px 브라우저 스모크 |
| T10 | 문서: ADR-035 부록 R 갱신, architecture 테이블 목록, `check_docs.py`, BACKLOG | 문서 | `pytest`, `check_docs.py` |

순서: T7 → T1 → T2 → T3 → T4 → T5 → T6 → T8 → T9 → T10 (T7은 독립 BUG로 먼저 가능).

## 5. 검증 항목
1. 기준점 없는 goal의 `schedule_for_goal`·`generate_weekly_plan` 출력이 변경 전과 동일(스냅샷 비교, 운영 DB 사본).
2. 재계획 후 이번 주·지난 주 `week_compliance` 수치 불변, `plan_adjustments` stale 0건, `session_outcomes` 고아 0건.
3. 재계획 후 N주차·`plan_progression` 단계·`plan_rules_version` 불변.
4. 활성 goal 2개 상태를 만들 수 없음(유니크 인덱스), 모든 활성 goal 조회가 같은 id 반환.
5. 미리보기 호출 전후 DB 해시 동일(쓰기 없음).
6. 적용 중 예외 주입 시 DB가 적용 전과 동일.
7. 운영 DB 사본에서 실제 페이지 로드(계획·Today·Race hub)로 확인.

## 6. 구현 상태 (2026-10-09)
- T1~T7 백엔드 완료·배포(스키마 v32, `plan_replans`, 재계획 preview/apply/undo API). T9 프론트 `/coach/plan/replan` 완료(설계 `DESIGN-PLAN-A6-REPLAN-UI.md`), 배너 링크는 `link.race_date` 조건으로 활성화.
- 사용자 결정은 D1~D7만 존재(D8 이상 없음).
- T8: Garmin/CalDAV 에 삭제 API 가 없어 자동 정리 불가. API 가 `external[]` 로 Garmin 세션을 알리고 UI 가 직접 지우도록 안내한다.
- 후속: 외부 삭제 수단 조사, 페이지를 떠난 뒤 되돌리기용 "마지막 재계획 id" API(UI 설계 Q1).
