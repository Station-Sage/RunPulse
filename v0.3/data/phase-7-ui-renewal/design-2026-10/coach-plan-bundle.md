# 설계: 훈련 계획 묶음 (P-01~P-25)

- 대상: `ux-review-2026-10/05-coach-plan.md` P-01~P-25 · 작성일 2026-10-11 · 상태: 초안(구현 전 결정 필요 항목 있음)
- 범위: 플랜 생성 파이프라인(`src/training/planner*`), 플랜 소유·교체(`goals`, `plan_replace`), 읽기 모델(`plan_service`, `week_compliance`, `routes_plan`), v2 `frontend/src/routes/coach/plan/*`
- 참조만: 입력·Origin 검증 → `server-input-origin-validation.md`, 오류·재시도 → `error-retry-common.md`, 접근성 → 별도 접근성 설계

## 1. 근본 원인

### R1. 주간 플랜이 여러 단계에서 바뀌는데 파생 필드는 첫 단계에서 한 번만 만든다 (P-01, P-02, P-08)
- `planner.generate_weekly_plan` 이 `description(wtype, dist, day)`·`structure` 를 v1 거리로 먼저 채운다. 이후 `planner_v2.apply_v2`(`_shakeout` L72·74, 휴식 전환 L91·111, 최소거리 L116), `planner_v2_long._shrink`/`rebalance`/`plan_long_week`, `apply_ladder` 가 `distance_km`·`workout_type` 을 바꾸지만 description 은 일부 경로(`trim_run_days`, `plan_long_week` 강등)에서만 다시 만든다.
- 결과: 거리 컬럼과 설명이 어긋나고(P-01 10.0 vs "16.1km"), rest 로 바뀐 행에 "3.7km 이지런" 이 남는다(P-02). `_finalize_rows` 는 rest 행의 페이스·구조만 비우고 설명은 건드리지 않는다.
- 주간 불변식(러닝 일수 상한, rest ↔ 거리 0, 설명 거리 = 컬럼 거리)을 검사하는 곳이 없다. v1 경로(`effective_rules_version < 2`)는 `rest_weekdays_mask=0` 이면 `available` 이 7일이라 휴식일 0이 그대로 저장된다(P-08 후보 원인, goal 1 의 rules_version 확인 필요).

### R2. planned_workouts 에 플랜 소유자가 없다 (P-03, P-11, P-15, P-23, P-09 일부)
- `planned_workouts` 는 날짜 키로만 존재하고 `goal_id` 가 없다. 플랜 = "활성 목표 + 그 날짜 범위의 행" 이라는 암묵 규칙이다.
- 그래서 새 플랜 생성은 `add_goal` 이 기존 active 를 무조건 `cancelled` 로 바꾸고(`goals.py` L102), `replace_range(today~9999)` 가 이력 없는 미래 행을 지운다(P-03). 확인 단계·복구 스냅샷이 없다. `replace_range` 는 snapshot 을 반환하지만 `create_plan_from_template` 이 버린다.
- 같은 이유로 `get_active_plan(goal_id)` 는 goal_id 와 무관하게 "오늘 주의 행" 을 돌려주고, 취소된 플랜 세션도 현재 행으로 보인다(P-23). 메모도 날짜 키라 플랜 간 공유된다(P-15).
- 시작 주는 `today - weekday()` 로 고정이라 일요일 생성 시 지난 6일이 1주차에 들어간다(P-11).

### R3. 읽기 모델이 "이번 주" 하나뿐이고 매칭은 동기화 시점에만 돈다 (P-06, P-07, P-08 검증 불가, P-09)
- `plan_service.get_active_plan` 은 `_current_week_start()` 한 주만 조회한다. 전체 주차 볼륨·단계·테이퍼를 돌려주는 API 가 없다(P-07). 사용자가 P-08 을 검증할 화면도 없다.
- `match_week_activities` 는 `bg_sync`·앱 시작·v1 CRUD 에서만 호출된다. v2 `POST /coach/plan` 은 생성 후 재매칭하지 않아, 과거 날짜를 포함한 새 행은 활동이 있어도 `matched_activity_id` 가 비어 "놓침" 이 된다(P-06·P-11). 날짜 범위로만 조회하므로 보호된 이전 플랜 행이 같은 날 활동을 먼저 차지했을 가능성도 있다(검증 필요).
- `outcome_label` 은 페이스 판정을 볼륨보다 먼저 해 10km/6.5km 초과도 "강도 어긋남" 이 되고, 판정 사유·실제 거리/페이스가 응답에 없다(P-06). 헤더는 누적(`_plan_compliance`), 목록은 주간(`week_compliance.compute`)으로 기준이 달라 모순처럼 보인다(P-09).

## 2. 설계안 (추천: A안)

### 2.1 R1 — 마지막 단계에서 한 번 파생 + 불변식 검사
- 신규 `src/training/plan_finalize.py`: `finalize_week(rows, *, run_day_cap) -> list[dict]` 가 모든 변형이 끝난 뒤 `description`·`structure` 를 (type, distance, date) 에서 다시 만든다. race·cold-start 노트처럼 의도된 설명은 `_desc_locked` 플래그로 보존.
- 같은 모듈 `week_violations(rows, run_day_cap) -> list[str]`: rest↔거리, 설명 km = 컬럼 km(±0.1), 러닝 일수 ≤ cap, 롱런 ≤ 주간의 일정 비율. 생성 시 위반은 로그 + 테스트에서 assert, 운영 저장은 막지 않는다(결정 D4).
- `generate_weekly_plan` 마지막 줄을 `finalize_week(apply_race_week(...))` 로 바꾼다. `planner.py` 가 300줄이라 `save_weekly_plan`·prefs 함수(L218~)를 `planner_store.py` 로 옮긴다(재수출 유지).
- v1 경로 휴식일 0(P-08)은 `run_day_cap = _run_days()` 를 v1 에도 적용할지 결정 D3.

### 2.2 R2 — 플랜 소유권 + 교체 확인
- `planned_workouts.goal_id INTEGER NULL` 추가(SCHEMA_VERSION +1). 백필: 각 goal 의 `_plan_date_range` 에 들어가는 planner 행에 goal_id 기입, 겹치면 최신 goal. 외부(Garmin 등) 행은 NULL 유지.
- `create_plan_from_template(..., expect_active_goal_id)`: 활성 플랜이 있는데 기대값이 다르면 `PlanConflict` → API 409 `ACTIVE_PLAN_EXISTS`(현재 플랜 요약 포함). 클라이언트는 확인 후 다시 보낸다(compare 의 `expect_anchor` 패턴 재사용).
- 교체 시 `replace_range` snapshot 을 버리지 않고 보존 정책(D1)에 따라 저장. 조회(`get_active_plan(goal_id)`, 세션 상세)는 `goal_id` 로 필터하고 `goal.status` 를 응답에 실어 취소 플랜을 읽기 전용 표시(P-23).
- 메모 키를 (goal_id, date) 로 옮길지(P-15) 는 D2. 시작 주 규칙(P-11)은 D5.

### 2.3 R3 — 전체 주차 읽기 모델 + 생성 직후 재매칭 + 판정 사유
- 신규 `src/services/plan_overview_service.py`: `get_plan_overview(conn, goal_id) -> {weeks:[{week_start, phase, planned_km, actual_km, run_days, rest_days, long_km, quality_n, compliance_pct}], basis}`. phase 는 `schedule_for_goal` 값 사용. API `GET /coach/plan/<id>/weeks`.
- `create_plan_from_template`·replan 적용 후 `rematch.rematch(conn, start, min(end, today))` 호출(같은 트랜잭션 밖, 실패 시 로그만).
- `week_compliance` entry 에 `reason`(코드: `no_activity`, `pace_fast`, `volume_over`, `volume_under`, `cross`) 과 `actual_km`, `actual_pace` 추가. 라벨 우선순위(볼륨 vs 강도)는 D6. 헤더 지표에 `basis: "cumulative" | "week"` 를 실어 프런트가 라벨을 붙인다(문구는 D7).
- 프런트: `PlanWeeksTable.svelte`(신규)로 주차 표, 주간 목록 행에 실제값·사유 표시.

### 대안
- B안(스키마 무변경): goal_id 없이 교체 시 이전 플랜 행 전체를 `goals.plan_snapshot_json` 에 저장, 조회는 날짜 범위 유지. 변경 작음. 그러나 P-15·P-23·매칭 행 충돌은 근본 해결 안 됨.
- C안(R1만 우선): 파생 필드 재생성·불변식만 적용하고 R2·R3 는 후속. 데이터 상 심각도(P-01·P-02)는 빨리 닫히지만 P-03 손실 위험이 남음.
- 추천: A안. 단 단계 1(R1)·단계 2(R3 읽기·재매칭)는 스키마 무관이라 먼저, R2 스키마는 D1·D2 결정 후.

## 3. ID 처리 매핑

| ID | 처리 | 근거 |
|----|------|------|
| P-01, P-02 | 설계 R1 | 파생 필드 재생성 |
| P-03 | 설계 R2 | 409 확인 + 스냅샷 보존(D1) |
| P-04, P-05 | 참조 | server-input-origin-validation.md 2.4 |
| P-06 | 설계 R3 | 재매칭·사유·우선순위(D6), 크로스 라벨 포함 |
| P-07 | 설계 R3 | plan overview API·표 |
| P-08 | 설계 R1+R3 | 불변식·가시화, 테이퍼 규칙 자체는 D3 |
| P-09 | 설계 R3 | basis 필드, 문구 D7 |
| P-10 | BACKLOG 개별 | ACWR 범위를 메트릭 정의에서 받기, CTL 스케일 |
| P-11 | 설계 R2 | 시작 주 규칙 D5 + 생성 후 재매칭 |
| P-12 | BACKLOG 개별 (+참조) | 목표 없음 문구 모순은 개별, 1초 입력은 입력 검증 참조 |
| P-13 | 참조 | error-retry-common.md(경로·재시도), 잘못된 파라미터 400 은 입력 검증 |
| P-14 | BACKLOG 개별 (+R2) | 단계 표시·입력 항목은 개별, 활성 시 진입점은 R2 409 흐름에 포함 |
| P-15 | 설계 R2 (+참조) | 플랜 간 공유는 D2, 길이·날짜 검증은 입력 검증 |
| P-16 | BACKLOG 개별 | 빈 메모 저장=삭제 허용 |
| P-17 | 참조 | Origin 관문(D-22 동일 원인) |
| P-18, P-19, P-21 | 참조 | 접근성 설계 |
| P-20 | BACKLOG 개별 | title·문구, 되돌리기 확인은 D8 |
| P-22 | 참조 | 입력 검증 2.3 엔벨로프(라우팅 404 포함 여부 확인 요청) |
| P-23 | 설계 R2 | status 노출·읽기 전용 |
| P-24 | BACKLOG 개별 | R1 후 rest 설명 해소, 버튼 허용 범위는 정책 |
| P-25 | BACKLOG 개별 | 로딩 스켈레톤 |

## 4. 변경 파일 표

| 파일 | 구분 | 내용 | 줄 수(예상) |
|------|------|------|------------|
| `src/training/plan_finalize.py` | 신규 | finalize_week, week_violations | ~90 |
| `src/training/planner_store.py` | 신규 | planner.py 에서 저장·prefs 함수 이동 | ~90 |
| `src/training/planner.py` | 수정 | finalize 호출, 이동분 재수출 | 300 → ~220 |
| `src/training/planner_v2.py` | 수정 | `_desc_locked` 표시(race·cold-start) | +5 |
| `src/db_setup.py` + 마이그레이션 | 수정 | planned_workouts.goal_id, 백필 | +30 |
| `src/training/goals.py`, `plan_template_service.py` | 수정 | expect_active_goal_id, PlanConflict, snapshot 보존, goal_id 기입, 재매칭 | +40 |
| `src/services/plan_service.py` | 수정 | goal_id 필터, status, basis | +20 |
| `src/services/plan_overview_service.py` | 신규 | 주차 요약 | ~110 |
| `src/training/week_compliance.py` | 수정 | reason·actual 필드, 라벨 순서 | +20 (≤251) |
| `src/api/routes_plan.py` | 수정 | 409, `/weeks` 라우트 | +30 |
| `frontend/src/lib/api/plan.ts` | 수정 | 타입·getPlanWeeks·409 처리 | +30 |
| `frontend/src/lib/components/plan/PlanWeeksTable.svelte` | 신규 | 주차 표 | ~100 |
| `frontend/src/routes/coach/plan/[id]/+page.svelte`·`+page.ts`, `compare/+page.svelte` | 수정 | 표·사유·상태, 교체 확인 | +60 |
| `tests/test_plan_finalize.py`, `test_plan_ownership.py`, `test_plan_overview.py`, `test_week_compliance_reason.py` | 신규 | 아래 검증 | ~350 |

## 5. 단계·검증
1. R1: 리뷰 재현(7주 템플릿 생성) 픽스처로 모든 행 `week_violations == []`. 기존 planner 골든 테스트는 description 기대값만 갱신(거리 불변 확인).
2. R3 읽기: overview 합계 = planned_workouts 집계, 생성 직후 과거 날짜 활동 매칭 테스트(P-06 10/8·10/9 재현), reason 별 단위 테스트, 10km/6.5km → D6 결과.
3. R2(결정 후): 마이그레이션 백필 테스트(겹치는 goal), 409 → 확인 재전송 → 이전 플랜 보존 확인, 취소 플랜 세션 응답 status=cancelled.
4. 브라우저(DB 사본): 375/1280px 에서 /coach/plan/{id} 주차 표·사유, compare 선택 시 확인 단계, 취소 플랜 세션 표시. `pytest`·`check_docs.py`·프런트 테스트 통과.
- 호환성: v1 화면(`views_training_crud`)은 날짜 기준 조회를 유지하므로 goal_id NULL 허용·필터는 v2 서비스에만 적용. v1 제거 후 NOT NULL 승격 검토. `POST /coach/plan` 409 는 v1 이 호출하지 않음(확인 필요). 알고리즘 출력(설명)이 바뀌므로 ADR-042 에 따라 버전/algo_changelog 항목 필요 여부 확인.

## 6. 결정 필요
- D1 교체 시 이전 플랜 보존: (a) cancelled 로 두고 행·스냅샷 보존, 복구 버튼 제공 — 안전, 저장 증가 (b) 보존하되 복구 없음 — 단순 (c) 현행 삭제 + 확인만 — 최소 변경, 손실 위험 유지.
- D2 메모 키: (a) (goal_id, date) — 플랜별 독립 (b) 날짜 유지 — 같은 날 실제 훈련 기록이라는 해석.
- D3 휴식일·테이퍼 규칙(P-08): v1 경로에 러닝 일수 상한 적용 / v2 로 일괄 전환 / 현행 유지. 테이퍼 볼륨·마지막 롱런 시점은 코치 정책.
- D4 불변식 위반 시: 저장 차단 / 자동 교정 / 로그만.
- D5 시작 주(P-11): 이번 주 월요일(현행) / 생성일부터 / 다음 월요일.
- D6 판정 우선순위: 볼륨 초과를 강도보다 먼저 / 둘 다 표시 / 현행.
- D7 헤더 누적 지표 라벨 문구·표시 기준.
- D8 replan 되돌리기 확인 단계 여부(P-20).
- D9 스키마 변경(A안) vs 스냅샷만(B안).

## 7. 범위 밖 메모
- `planned_workouts` 가 goal 없이 쓰이는 다른 경로(weekly_adapt_job, garmin_push, calendar_feed)의 goal_id 기입은 R2 구현 시 별도 점검 필요.
- compare 의 "달성 가능성" 계산(P-12)은 예측 묶음(T-08..T-13) 공식과 일치 여부 확인 필요.
- matcher 의 이전 플랜 보호 행이 활동을 선점하는지 사본 데이터로 확인 필요(P-06 2차 원인 후보).
- `src/training/planner_rules.py` 가 이미 325줄(300줄 규칙 초과). 이번 설계는 이 파일을 건드리지 않으며 분리는 별도 작업.
