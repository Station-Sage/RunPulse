# 설계: 훈련 계획 묶음 (P-01~P-25)

- 대상: `ux-review-2026-10/05-coach-plan.md` P-01~P-25 · 작성일 2026-10-11 · 상태: 결정 확정(2026-10-11, PLN-1~10), 구현 전 — 실데이터 확인·후속 확인 항목 남음(§5, §8)
- 변경 이력: 2026-10-11 원인 검증 반영 — P-06(매칭 비율 상한·판정 순서·_effective 순위), P-08(v1 폴백·운영 경로 휴식 보장 부재) 원인 확정 및 실데이터 확인 항목 추가
- 변경 이력: 2026-10-11 설계서 동기화 — `decisions-table.md` PLN-1~10 결정을 본문(설계안·변경 파일·단계·검증·호환성)에 반영, HSR-1 과의 단일 결정 관계 반영
- 범위: 플랜 생성 파이프라인(`src/training/planner*`), 플랜 소유·교체(`goals`, `plan_replace`), 읽기 모델(`plan_service`, `week_compliance`, `routes_plan`), v2 `frontend/src/routes/coach/plan/*`
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
- `match_week_activities`는 `bg_sync` 완료 후(v2 동기화 포함, 최근 4주)·앱 시작·v1 CRUD에서 호출된다. v2 `POST /coach/plan`은 생성 후 재매칭하지 않는다. P-06 10/8·10/9는 거리 비율 상한(`match_select.py:10,40-41`, 2.5배·1.83배 > 1.6)으로 탈락했다(합성 재현으로 확정). 외부 계획 행이 먼저 정렬·매칭(`matcher.py:51`)되어도 결과는 같았다.
- `outcome_label`은 이지 페이스 판정을 볼륨보다 먼저 한다(`week_compliance.py:69-72`). 10/6·10/7의 10km·6km가 "강도 어긋남"이 되고(확정), 사유·실제 거리/페이스는 응답에 없다. `_effective` 순위(48-52)는 미매칭 외부 행을 매칭된 planner 행보다 우선해 missed를 만든다(결함 재현됨, 이번 데이터 해당 여부 불명, §5). 헤더는 누적(`_plan_compliance`), 목록은 주간(`week_compliance.compute`)이라 기준이 다르다(P-09).

## 2. 설계안 (확정: A안, PLN-9)

### 2.1 R1 — 마지막 단계에서 한 번 파생 + 불변식 자동 교정
- 신규 `src/training/plan_finalize.py`: `finalize_week(rows, *, run_weekdays) -> list[dict]` 가 모든 변형이 끝난 뒤 `description`·`structure` 를 (type, distance, date) 에서 다시 만든다. race·cold-start 노트처럼 의도된 설명은 `_desc_locked` 플래그로 보존.
- 같은 모듈 `week_violations(rows, run_weekdays) -> list[str]`: rest↔거리, 설명 km = 컬럼 km(±0.1), 러닝 요일 ⊆ 지정 요일, 롱런 ≤ 주간의 일정 비율. 위반은 **자동 교정 + 로그**(PLN-4): rest 행 거리 0·설명 재생성, 지정 요일 밖 러닝 행 → rest, 설명 불일치 → 재생성. 생성·저장은 막지 않으며 테스트에서는 교정 전 위반 0 을 assert.
- `generate_weekly_plan` 마지막 줄을 `finalize_week(apply_race_week(...))` 로 바꾼다. `planner.py` 가 300줄이라 `save_weekly_plan`·prefs 함수(L218~)를 `planner_store.py` 로 옮긴다(재수출 유지).
- P-08(PLN-3): 원칙은 **사용자가 지정한 운동 요일 준수**. 지정이 없으면 계획 생성 시 요일 선택을 요구한다(`POST /coach/plan` 입력에 `run_weekdays` 필수, 프런트 생성 폼에 요일 선택 단계). 구현은 (c) **신규 목표는 v2 규칙으로 일괄 전환** — `add_goal` 이 rules_version=2 와 v2 진입 조건(target 산출에 필요한 `plan_weeks`)을 항상 채워 v1 폴백 경로에 들어가지 않게 한다. 지정 요일은 `user_training_prefs`(지정 요일 마스크)에 저장해 v2·`finalize_week` 가 공통으로 읽는다. 테이퍼 볼륨·마지막 롱런 시점, 컨디션 기반 변경(adjuster·weekly_adapt, ADR-035 확인 후)은 이 설계 범위 밖.

### 2.2 R2 — 플랜 소유권 + 교체 확인 + 복구
- `planned_workouts.goal_id INTEGER NULL` 추가(SCHEMA_VERSION +1). 백필: 각 goal 의 `_plan_date_range` 에 들어가는 planner 행에 goal_id 기입, 겹치면 최신 goal. 외부(Garmin 등) 행은 NULL 유지.
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
| P-08 | 설계 R1 | 지정 요일 준수·요일 선택 요구·신규 목표 v2 전환(PLN-3) |
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
| `src/training/planner_store.py` | 신규 | planner.py 에서 저장·prefs 함수 이동 | ~90 |
| `src/training/planner.py` | 수정 | finalize 호출, 이동분 재수출, 부분 첫 주 | 300 → ~225 |
| `src/training/planner_v2.py` | 수정 | `_desc_locked` 표시(race·cold-start), 지정 요일 입력 | +10 |
| `src/db_setup.py` + 마이그레이션 | 수정 | planned_workouts.goal_id, 백필, 지정 요일 prefs 필요 시 | +35 |
| `src/training/goals.py`, `plan_template_service.py` | 수정 | v2 일괄 전환, expect_active_goal_id, PlanConflict, 행 보존·snapshot 저장, restore, goal_id 기입, 재매칭 | +60 |
| `src/services/plan_service.py` | 수정 | goal_id 필터, status, basis | +20 |
| `src/services/plan_overview_service.py` | 신규 | 주차 요약 | ~110 |
| `src/training/week_compliance.py` | 수정 | reason(s)·actual 필드, 두 라벨, `_effective` 순위 | +25 (≤256) |
| `src/api/routes_plan.py` | 수정 | 409, run_weekdays 필수, `/weeks`·`/restore` 라우트 | +40 |
| `frontend/src/lib/api/plan.ts` | 수정 | 타입·getPlanWeeks·restore·409 처리 | +35 |
| `frontend/src/lib/components/plan/PlanWeeksTable.svelte` | 신규 | 주차 표 | ~100 |
| `frontend/src/routes/coach/plan/[id]/+page.svelte`·`+page.ts`, `compare/+page.svelte`, 생성 폼 | 수정 | 표·사유·상태·복구, 교체·되돌리기 확인, 요일 선택 | +80 |
| `tests/test_plan_finalize.py`, `test_plan_ownership.py`, `test_plan_overview.py`, `test_week_compliance_reason.py` | 신규 | 아래 검증 | ~380 |

## 5. 단계·검증
1. R1: 7주 템플릿을 rv1 / rv2+plan_weeks NULL / rv2+plan_weeks=7 세 픽스처로 생성 → 교정 후 `week_violations == []`, 러닝 요일 ⊆ 지정 요일. 신규 목표는 plan_weeks 누락 입력에서도 v2 경로 진입. 지정 요일 없는 생성 요청 400. 기존 planner 골든 테스트는 description 기대값만 갱신.
2. R3 읽기: overview 합계 = planned_workouts 집계, 생성 직후 과거 날짜 매칭, 10/6~10/9 합성 주로 reasons(대표 volume_over·보조 pace_fast / 상한 탈락), ext2 픽스처(미매칭 외부 + 매칭 planner)에서 매칭 행이 effective, 수락 조정 행 > 미매칭 외부 행.
   **실데이터 확인 필요**(real_ui.db 사본, 읽기 전용):
   | 확인 | 쿼리 | 판정 |
   |---|---|---|
   | goal 생성 경로 | `SELECT id,status,created_at,plan_rules_version,plan_weeks,race_date,distance_km FROM goals ORDER BY id;` | rv=1 또는 plan_weeks NULL이면 v1 경로 |
   | anchor별 규칙 버전 | `SELECT id,goal_id,anchor_monday,rules_version,status,created_at FROM plan_replans WHERE goal_id=1 ORDER BY anchor_monday;` | 주별 effective_rules_version 차이 |
   | 휴식 설정 | `SELECT rest_weekdays_mask,long_run_weekday_mask,max_q_days FROM user_training_prefs;` | mask=0이면 v1에서 휴식 0 |
   | 주간 러닝 일수 | `SELECT date(date,'weekday 0','-6 days') wk, SUM(workout_type<>'rest') runs, ROUND(SUM(distance_km),1) km FROM planned_workouts WHERE source='planner' GROUP BY wk ORDER BY wk;` | 7회가 이어지면 P-08 재현 |
   | P-06 주 매칭·외부 행 | `SELECT id,date,source,workout_type,distance_km,matched_activity_id FROM planned_workouts WHERE date BETWEEN '2026-10-05' AND '2026-10-11' ORDER BY date,id;` | 같은 날 외부 미매칭 + planner 매칭이면 PLN-10 해당 |
3. R2: 마이그레이션 백필 테스트(겹치는 goal), 409 → 확인 재전송 → 이전 플랜 cancelled·행 보존, restore 후 active 교대, 취소 플랜 세션 응답 status=cancelled, 일요일 생성 시 첫 주 = 그 일요일 하루, 메모는 교체 전후 같은 날짜에서 동일.
4. 브라우저(DB 사본): 375/1280px 에서 /coach/plan/{id} 주차 표·사유·두 라벨, 헤더 '누적(플랜 시작~어제)' 툴팁, compare 교체 확인, 복구 버튼, replan 되돌리기 확인, 생성 폼 요일 선택. `pytest`·`check_docs.py`·프런트 테스트 통과.
- 호환성: goal_id NULL 허용(외부 행). 보존된 취소 플랜 행이 날짜 기준 조회에 섞이지 않도록 v2 서비스는 goal_id 필터, 날짜 기준 경로는 §8-2 확인 결과에 따라 처리. v1 제거 후 NOT NULL 승격 검토. `POST /coach/plan` 409·run_weekdays 필수는 v1 이 호출하지 않음(확인 필요). 알고리즘 출력(설명·요일)이 바뀌므로 ADR-042 에 따라 버전/algo_changelog 항목 필요 여부 확인.

## 6. 결정됨(2026-10-11, `decisions-table.md` PLN-1~10)
- PLN-1(D1) 교체 시 cancelled 로 행·스냅샷 보존 + 복구 버튼 — P-03 손실 위험 제거.
- PLN-2(D2) 메모는 날짜 기준 유지 — 플랜과 무관한 훈련 기록으로 취급.
- PLN-3(D3) 지정 운동 요일 준수 원칙, 지정 없으면 생성 시 요일 선택 요구, 구현 (c) 신규 목표 v2 일괄 전환 — 기존 goal 처리·최소 휴식일 수는 §8 확인.
- PLN-4(D4) 불변식 위반 시 자동 교정 + 로그(생성은 막지 않음).
- PLN-5(D5) 생성일부터 시작(첫 주 부분 주, 지난 날짜 제외).
- PLN-6(D6) 둘 다 표시: 대표 라벨=볼륨 초과, 보조=페이스 빠름 + reason 필드.
- PLN-7(D7) 헤더 '누적(플랜 시작~어제)' 라벨 + 기준 툴팁(서버 basis), 목록은 '이번 주'.
- PLN-8(D8) replan 되돌리기에 확인 단계 추가.
- PLN-9(D9) A안 스키마 변경 — planned_workouts.goal_id + 백필.
- PLN-10(D10) 매칭된 행 최우선(출처 무관), 수락된 조정 행은 미매칭 외부 행보다 위 — 조정 행 의미는 구현 시 검토.
- 연관: 거리 비율 상한은 HSR-1((c) 같은 날 후보 1개면 비율 무시, 여럿이면 상한 유지)과 단일 결정.

## 7. 범위 밖 메모
- `planned_workouts` 가 goal 없이 쓰이는 다른 경로(weekly_adapt_job, garmin_push, calendar_feed)의 goal_id 기입은 R2 구현 시 별도 점검 필요.
- compare 의 "달성 가능성" 계산(P-12)은 예측 묶음(T-08..T-13) 공식과 일치 여부 확인 필요.
- 외부 계획 행의 활동 선점은 합성 재현에서 결과 불변으로 확인. 남은 것은 §5 쿼리로 확인하는 `_effective` 해당 여부(PLN-10).
- `src/training/planner_rules.py` 가 이미 325줄(300줄 규칙 초과). 이번 설계는 이 파일을 건드리지 않으며 분리는 별도 작업.

## 8. 동기화 중 발견한 충돌/확인 필요
1. PLN-3 후속 확인(결정표 명시): 기존 목표(goal 1 등)를 v2 로 재생성할지 그대로 둘지, 요일 지정 필수화 후에도 최소 휴식일 수 하한이 필요한지 미정. G1 게이트(`plan_gates.py:71`) 재사용 여부도 결정표에 언급 없음.
2. PLN-1 은 취소 플랜 행을 보존하지만 `planned_workouts` 는 날짜 기준으로 읽는 경로가 많다(v1 `views_training_crud`, `matcher`/`match_week_activities`, `week_compliance`, calendar_feed, garmin_push). 이 경로들이 goal_id 로 걸러지지 않으면 같은 날짜에 두 플랜 행이 겹친다. 기존 호환성 서술("필터는 v2 서비스에만")과 충돌.
3. PLN-3 의 지정 요일 저장 위치: 현재 `user_training_prefs` 는 `rest_weekdays_mask`(휴식 요일)만 있고 "운동 요일" 마스크가 없다. 기존 mask 를 반전해 쓸지, 새 컬럼인지 미정.
4. PLN-5(생성일부터·부분 첫 주)와 v2 주 단위 로직(`plan_replans.anchor_monday`, `schedule_for_goal` 주차·phase, 주간 볼륨 목표)의 부분 주 처리 방식이 정해지지 않았다.
5. PLN-10 "수락된 조정 행" 을 식별하는 컬럼(`source` 값 등)이 `planned_workouts` DDL 에 명시돼 있지 않다 — 구현 시 확인.
