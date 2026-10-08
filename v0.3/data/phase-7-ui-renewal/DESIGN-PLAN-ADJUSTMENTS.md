# DESIGN-PLAN-ADJUSTMENTS — Coach 조정 수락 영속화 (`plan_adjustments`, A안)

- 상태: 설계 초안 (2026-10-08). 구현 전 사용자 확인 필요(§8)
- 범위: `P7-IMPL-COACH-PLAN-ADJUSTMENT-ACCEPT`, 99-summary 3-13의 조정 수락·되돌리기 부분. 3-14(Coach 답변 안 카드)가 쓸 계약까지
- 승인된 방향: A안. 새 테이블 `plan_adjustments`에 조정 이력을 저장하고, 읽을 때 계획에 겹쳐 적용(오버레이)한다. 이 문서는 방향을 다시 논의하지 않는다
- 상위 명세: `ux-review-2026-09/31-coach-plan/design.md` §4.1 R1·R2·R8, §7.2 "조정 (S5)", `30-coach-chat/design.md` §7.4, 99-summary D9
- 범위 밖: R8 레벨별 매핑 표(녹·황·주황·적) 구현, 행 액션 4종의 UI(스키마만 수용, T8), replan(S6), R11 사용자 TZ

---

## 1. 현재 동작과 갭

| 위치 | 현재 동작 |
|---|---|
| `src/training/adjuster.py` `adjust_todays_plan(conn, date=)` | 그날 미완료 `planned_workouts` 1행을 골라 `readiness_decision`으로 `workout_type`만 낮춘다(`_DOWNGRADE_HIGH/MOD`). 거리·페이스는 바꾸지 않는다. **DB에 쓰지 않고**, 호출할 때마다 다시 계산한다 |
| 호출처 | `plan_service.get_todays_adjustment`·`get_session_detail`, `today_hero`(L139), `coach_evidence`(L142), `src/plan.py` CLI |
| API | `GET /api/v1/coach/plan/adjustment` → adjuster 결과를 그대로 반환. id는 **workout id**이고 조정 id는 없다 |
| 프론트 | `coach/plan/[id]/+page.svelte:117`("오늘 조정됨" 배너), `session/[date]/+page.svelte:57·83`, `NextSessionCard.svelte:42`. 수락·원래대로 버튼은 없다 |
| 유효 계획 | `planned_query.get_planned_workouts` → `week_compliance._effective`(R1)가 정한다. 순위에 "적용한 조정"이 없다 |

갭:
1. 수락할 대상(조정 id)과 수락 결과를 저장하는 곳이 없다.
2. 수락해도 R1·R3(이행률)·Today·Coach 어디에도 반영되지 않는다. D9(조정 휴식은 분모에서 제외)를 만족할 수 없다.
3. 제안이 그날 안에서도 바뀔 수 있다(동기화로 HRV·BB가 갱신됨). 사용자가 본 제안과 수락되는 내용이 같다는 보장이 없다.
4. `planned_workouts`에 `goal_id`가 없다. 행은 `save_weekly_plan`(날짜별 DELETE 후 INSERT), `rematch`, wizard, `plan_ingest`가 삭제하거나 다시 쓴다. workout_id에 거는 참조는 깨질 수 있다.
5. 레거시 데이터: 조정은 지금까지 한 번도 저장된 적이 없다. 31 R1의 "`adjusted=true` 행 1회 이관"은 이관할 데이터가 없으므로 **백필하지 않는다**.

## 2. 테이블 DDL (스키마 v31)

관례(v29·v30)대로 `src/db_schema_v31.py`의 `ensure_v31(conn)`가 멱등으로 처리하고, `create_tables()` 끝의 ensure 체인에 추가한다. `SCHEMA_VERSION = 31`. 구현 시점에 v31이 이미 쓰였으면 다음 번호를 쓴다.

```sql
CREATE TABLE IF NOT EXISTS plan_adjustments (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    goal_id      INTEGER,                 -- 생성 시점 활성 목표(planned_workouts에 goal_id 없음). 없으면 NULL
    workout_id   INTEGER NOT NULL,        -- planned_workouts.id (FK 선언 없음: 원본 행은 재생성될 수 있음)
    date         TEXT    NOT NULL,        -- 조정 대상 날짜(YYYY-MM-DD)
    source       TEXT    NOT NULL CHECK (source IN ('crs','user','coach')),
    op           TEXT    NOT NULL DEFAULT 'replace'
                         CHECK (op IN ('replace','reduce','rest','skip','move')),
    before_json  TEXT    NOT NULL,        -- 원본 지문: {workout_type, distance_km, target_pace_min, target_pace_max, description}
    after_json   TEXT    NOT NULL,        -- 적용 값: 같은 키 + move면 {"date": "<to_date>"}
    reasons_json TEXT    NOT NULL DEFAULT '[]',  -- [{key, label, value?, target?}] (근거 칩 원천)
    rule_version TEXT    NOT NULL,        -- 제안 규칙 버전, 예: 'adjuster_v1' (R8 도입 시 'r8_v1')
    decision     TEXT    NOT NULL DEFAULT 'proposed'
                         CHECK (decision IN ('proposed','accepted','reverted')),
    rev          INTEGER NOT NULL DEFAULT 1,     -- proposed 상태에서 내용이 갱신될 때마다 +1
    accepted_at  TEXT,                    -- 한 번이라도 accepted 된 시각(되돌리기와 거절 구분용)
    decided_at   TEXT,                    -- 마지막 결정 시각
    decided_via  TEXT CHECK (decided_via IN ('plan','session','today','coach') OR decided_via IS NULL),
    created_at   TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at   TEXT    NOT NULL DEFAULT (datetime('now'))
);
-- 한 workout·날짜·출처에 살아 있는(proposed|accepted) 조정은 하나
CREATE UNIQUE INDEX IF NOT EXISTS ux_plan_adj_live
    ON plan_adjustments(workout_id, date, source) WHERE decision IN ('proposed','accepted');
CREATE INDEX IF NOT EXISTS idx_plan_adj_date ON plan_adjustments(date, decision);
CREATE INDEX IF NOT EXISTS idx_plan_adj_goal ON plan_adjustments(goal_id, date);
```

- 이력 의미: 행 하나가 조정 제안 하나다. 상태 전이는 `decision`·`accepted_at`·`decided_at`으로 남긴다. reverted 행을 다시 제안하면 새 행을 만든다(부분 유니크 인덱스가 허용).
- 표시 상태는 저장하지 않고 계산한다. `state = proposed|accepted|declined(reverted, accepted_at NULL)|undone(reverted, accepted_at NOT NULL)|expired(proposed, date < today)|stale(§3.3)`.
- `APP_TABLES`에 `plan_adjustments`를 추가한다(앱 데이터, 재계산 대상 아님. `provider LIKE 'runpulse%'` 삭제와 무관). 문서 체크리스트: architecture.md·phase_summary.md 테이블 수, `/check-data-consistency`.

## 3. 서비스 레이어

새 모듈 2개. 원본 `planned_workouts`는 **불변**이다. 이 기능은 `UPDATE planned_workouts`를 하지 않는다.

### 3.1 `src/services/plan_adjustment_service.py` (쓰기·조회)

```python
def ensure_proposal(conn, date: str) -> dict | None:
    """adjust_todays_plan(date) 결과가 adjusted면 proposed 행을 멱등 upsert하고 반환.
    - 같은 (workout_id, date, 'crs')에 proposed 행이 있고 after/reasons가 바뀌었으면 같은 id에서 갱신, rev+1.
    - accepted 행이 있으면 재계산하지 않고 그 행을 반환(수락 내용 고정).
    - 같은 날 reverted 행만 있으면 새 제안을 만들지 않는다(사용자가 이미 거절·되돌림).
    - 미래 날짜는 만들지 않는다(R8: 판단은 당일만). 데이터 부족이면 None(에러 raise 안 함)."""

def get_day_adjustment(conn, date: str, *, ensure: bool = True) -> dict:
    """{state, adjustment|None}. state ∈ none|future|proposed|accepted|declined|undone|expired|stale.
    Today·계획·세션·Coach가 모두 이 함수 하나를 쓴다(30 §7.4: 같은 id)."""

def accept(conn, adj_id: int, *, rev: int, via: str | None) -> dict:
    """proposed|reverted(당일) → accepted. rev 불일치·날짜 지남·stale이면 AdjustmentConflict."""

def revert(conn, adj_id: int, *, via: str | None) -> dict:
    """proposed → reverted(거절), accepted → reverted(되돌리기). 당일만 허용."""

def list_adjustments(conn, *, goal_id: int | None, start: str, end: str) -> list[dict]:
    """기간 이력(최신순), 계산된 state 포함."""

def create_user_adjustment(conn, workout_id: int, op: str, params: dict, source: str = "user") -> dict:
    """행 액션·Coach 제안(T8). 즉시 accepted로 생성. coach는 readiness intensity_cap을 넘지 못함."""

class AdjustmentConflict(Exception): code: str  # 'REV_MISMATCH'|'LOCKED'|'STALE'|'INVALID_TRANSITION'
```

- 상태 전이표: `proposed→accepted`, `proposed→reverted`, `accepted→reverted`, `reverted→accepted`. 마지막 둘은 `date == today`일 때만 허용한다(31 §2.4: 되돌리기는 당일 안). 그 외는 `INVALID_TRANSITION`.
- `after_json` 생성 규칙(v1, `rule_version='adjuster_v1'`): 유형은 adjuster의 `adjusted_type`. 결과가 rest면 거리·페이스는 NULL. 그 밖에는 원본 거리를 유지하고 페이스는 NULL(유형 기본 페이스는 표시에서 계산). 결정 필요 2(§8).
- 커밋은 서비스 함수 안에서 한다(기존 `save_session_note` 관례). `ensure_proposal`은 GET 경로에서 쓰기를 한다. 결정 필요 1.

### 3.2 `src/training/plan_overlay.py` (읽기 시점 적용)

```python
def live_adjustments(conn, start: str, end: str) -> dict[int, dict]:
    """기간 안 accepted 행만 {workout_id: row}. move는 원래 날짜와 이동 날짜 모두를 포함."""

def apply(rows: list[dict], adjs: dict[int, dict]) -> list[dict]:
    """원본 행 dict를 복사해 after 값을 덮어쓴다. 원본 dict와 DB는 바꾸지 않는다.
    덧붙이는 필드: adjusted=True, adjustment={id, source, op, decided_at}, original={before 값}.
    지문(before_json의 workout_type·distance_km·date)이 현재 행과 다르면 적용하지 않고 adjustment_stale=True."""
```

- 진입점은 하나다. `planned_query.get_planned_workouts()`가 끝에서 `apply()`를 호출한다(`overlay: bool = True` 인자). `week_compliance`·`plan_service`·`today_hero.build_week`·`_next_session`이 자동으로 따라온다.
- R1 우선순위 변경(`week_compliance._effective`): `실행된 외부 계획 > adjusted(accepted) 행 > 외부 계획 > planner 원안`. 31 R1 순서와 같다.
- D9: 조정 결과가 rest인 날은 기존 로직대로 `state='rest'`가 되어 분모에서 빠진다. 그날 실제로 뛴 활동은 `claimed`에서 빼서 `unplanned_runs`로 집계한다(휴식 조정일 러닝이 사라지지 않게).
- adjuster 이중 제안 방지: `get_day_adjustment`는 accepted 행이 있으면 adjuster 결과보다 그 행을 먼저 반환한다. adjuster 자체(제안 엔진)는 그대로 둔다.
- matcher(`match_week_activities`)는 지금 원본 행을 직접 SELECT한다. T6에서 오버레이 값으로 유형·거리 게이트를 보도록 바꾼다. 원본 행의 `completed`·`matched_activity_id` 쓰기는 지금처럼 원본 행에 한다.

### 3.3 원본이 바뀐 경우 (stale)

원본 행이 삭제되거나(계획 재생성) 지문이 달라지면(`replanner`의 거리 갱신, `plan_ingest` 덮어쓰기) 조정을 적용하지 않는다. 이력에는 `state='stale'`로 표시한다. 날짜 기준 재바인딩은 하지 않는다. 결정 필요 3.

## 4. API 엔드포인트 (`src/api/routes_plan.py`, 300줄 초과 시 `routes_plan_adjust.py`로 분리)

응답은 `api_ok(data)` → `{"data": …}`, 오류는 `api_error(code, message, status, details)`.

| 메서드·경로 | 요청 | 응답 `data` | 오류 |
|---|---|---|---|
| `GET /coach/plan/adjustment?date=` (확장) | date 생략 = 오늘 | 기존 adjuster 필드(1릴리스 유지) + `state`, `adjustment` | 503 NOT_FOUND(DB 없음) |
| `POST /coach/plan/adjustments/<id>/accept` | `{"rev": 2, "via": "plan"}` | `{adjustment, compliance, week_planned_km: {before, after}}` | 404 NOT_FOUND, 409 CONFLICT(`details.reason`=REV_MISMATCH·LOCKED·STALE·INVALID_TRANSITION, `details.current`=최신 행), 400 INVALID_PARAM |
| `POST /coach/plan/adjustments/<id>/revert` | `{"via": "session"}` | 같은 형태 | 404, 409, 400 |
| `GET /coach/plan/<goal_id>/adjustments?from=&to=` | 기본 = 계획 시작~오늘 | `{"items": [adjustment…]}` | 404(목표 없음), 400 |
| `POST /coach/plan/workouts/<id>/action` (T8) | `{"op":"reduce","pct":20}` 등 31 §7.2 | `{adjustment, compliance}` | 400, 404, 409 |

`adjustment` 객체:
```json
{"id": 12, "rev": 2, "date": "2026-10-08", "workout_id": 341, "goal_id": 3,
 "source": "crs", "op": "replace", "state": "proposed", "decision": "proposed",
 "before": {"workout_type": "interval", "distance_km": 8.5},
 "after":  {"workout_type": "easy", "distance_km": 8.5},
 "reasons": [{"key": "bb", "label": "Body Battery 42", "target": "m.body_battery"}],
 "rule_version": "adjuster_v1", "created_at": "…", "decided_at": null, "accepted_at": null}
```
- `CONFLICT`는 새 오류 코드다. 기존 코드 목록(NOT_FOUND·INVALID_PARAM·BAD_REQUEST…)에 없으므로 `src/api/__init__.py` 주석에 추가한다.
- `get_plan_by_id`·`get_session_detail` 응답의 `adjustment` 필드는 `get_day_adjustment()` 결과로 바꾼다. 세션 상세의 미래 날짜는 `state='future'`(31 §8 수용 기준).
- 세션 상세 `workout`은 오버레이된 유효 계획이고, `original`에 원본을 함께 준다("원래 계획" 블록용).

## 5. 프론트 변경점

| 파일 | 변경 |
|---|---|
| `frontend/src/lib/types*.ts` | `PlanAdjustment`, `AdjustmentState` 타입 추가. `TodaysAdjustment`에 `state`, `adjustment?` 추가(기존 필드 유지) |
| `frontend/src/lib/api/plan.ts` | `acceptAdjustment(id, rev, via)`, `revertAdjustment(id, via)`, `listAdjustments(goalId, from?, to?)`. 409면 `details.current`로 카드를 갱신 |
| `frontend/src/lib/components/plan/AdjustmentCard.svelte` (신규) | props `{adjustment, via, compact?}`. 수락·원래대로 호출 → 결과 `adjustment`로 자체 상태 갱신 + `onchange` 콜백. 시각 규격은 31 §2.4(product 영역) |
| `routes/coach/plan/[id]/+page.svelte` | L117 배너를 AdjustmentCard로 교체. 수락·되돌리기 후 `invalidate`로 plan 데이터(이행률·주 목록) 다시 읽기 |
| `routes/coach/plan/[id]/session/[date]/+page.svelte` | L57·L83 블록: `state`별 분기(future는 "조정 없음" 문구 제거). 원래 계획은 `original`, 오늘 계획은 오버레이 값 |
| `lib/components/NextSessionCard.svelte` + `routes/today/+page.ts` | `showAdjustment` 조건을 `state ∈ {proposed, accepted}`로. proposed면 compact 카드 |
| Coach H1·답변 카드 (3-14) | 같은 `GET /coach/plan/adjustment`의 id로 compact 카드. 이 문서 범위에서는 계약만 정한다 |

전역 스토어는 만들지 않는다. 세 화면이 같은 API를 읽고, 쓰기 후에는 각 화면이 다시 읽는다(진실 소스를 서버 하나로 둔다).

## 6. 테스트 목록

| 파일 | 내용 |
|---|---|
| `tests/test_db_schema_v31.py` | ensure_v31 두 번 호출해도 멱등, CHECK 위반 거부, 부분 유니크(살아 있는 행 2개 금지, reverted 후 새 행 허용), user_version=31 |
| `tests/test_plan_adjustment_service.py` | ensure_proposal 멱등(같은 id), 입력 변화 시 rev+1·같은 id, accepted 뒤 재계산 안 함, reverted 뒤 새 제안 안 만듦, 미래 날짜 None, 전이표 전체(허용 4·거부 나머지), 지난 날짜 LOCKED, rev 불일치 REV_MISMATCH, 데이터 부족 시 None |
| `tests/test_plan_overlay.py` | after 덮어쓰기와 원본 dict·DB 불변, 지문 불일치 시 미적용 + stale, 원본 행 삭제 시 stale, move가 두 날짜에 반영 |
| `tests/test_week_compliance.py` (추가) | R1 순위에 accepted 조정 반영, D9 픽스처: 9/23(화) 인터벌→휴식 accepted면 분모 6·품질 0/1(31 R3), 같은 날 proposed만 있으면 원안 유지, 휴식 조정일 러닝이 unplanned_runs로 집계 |
| `tests/test_plan_service.py` (추가) | 세션 상세 `workout`=오버레이·`original`=원본, 미래 날짜 state=future |
| `tests/test_api_plan_adjustments.py` | accept/revert 200·404·409(details.current 포함)·400, `GET adjustment`에 state·id 포함, 기존 필드 유지 |
| `tests/test_matcher.py` (추가, T6) | interval→easy 수락일에 이지 활동이 유효 계획에 매칭 |
| `frontend/tests/adjustmentCard.test.mjs` | state별 렌더 분기, 409 응답 시 current로 갱신 |
| 일관성 | 같은 날 Today·계획·Coach evidence가 같은 adjustment id·state를 반환(API 스냅샷) |

## 7. 구현 단계 (각 단계 독립 커밋, 테스트 통과 상태 유지)

- **T1** `feat(db)`: `db_schema_v31.py` + `create_tables` 체인 + `SCHEMA_VERSION=31` + `APP_TABLES` + 스키마 테스트. 문서(architecture·phase_summary 테이블 수, files_index) 갱신.
- **T2** `feat(plan)`: `plan_overlay.py`(live_adjustments·apply) + 단위 테스트. 아직 아무도 호출하지 않는다.
- **T3** `feat(plan)`: `plan_adjustment_service.py`(ensure_proposal·get_day_adjustment·accept·revert·list) + 테스트.
- **T4** `feat(plan)`: `get_planned_workouts`에 오버레이 연결, `_effective` R1 순위 변경, 휴식 조정일 unplanned 처리. 회귀 테스트로 `test_week_compliance`·`test_plan_service` 전체 확인.
- **T5** `feat(api)`: accept/revert/list 엔드포인트, `GET adjustment`·plan·session 응답 확장, `CONFLICT` 코드 + API 테스트.
- **T6** `feat(training)`: matcher가 오버레이 값으로 게이트를 본다 + 테스트.
- **T7** `feat(web)`: 타입·API 함수·`AdjustmentCard` + 계획·세션·Today 연결 + 프론트 테스트. 브라우저 스모크(수락 → 이행률 변화 → 되돌리기).
- **T8** (선택, 3-13 행 액션) `create_user_adjustment` + `POST workouts/<id>/action` + 테스트. UI(행 액션 시트)는 product 설계 후.
- **T9** `docs`: `DECISIONS.md` ADR, BACKLOG 항목 LATER→DONE, `coach_evidence`가 `get_day_adjustment`를 쓰도록 정리(3-14 준비).

## 8. 결정 필요

1. **결정 필요 — 제안 행을 언제 만드나.** 추천: 조회 시 멱등 upsert(`ensure_proposal`, GET에서 쓰기). 이유: Today·계획·Coach가 같은 id를 공유해야 하고(30 §7.4), 사용자가 본 제안 내용을 고정해야 한다(rev). 대안은 "수락 시에만 accepted 행 생성"이다. GET이 순수해지지만 id 공유가 안 되고, 거절 이력도 남지 않는다.
2. **결정 필요 — v1 `after` 거리 규칙.** 추천: 유형만 바꾸고 거리는 원본 유지, 휴식은 NULL(adjuster 현행과 같음). R8 매핑(−15%·−30% 등)은 R8 구현 때 `rule_version`을 올려 넣는다. 이유: 이번 범위를 영속화로 한정하고, 규칙 변경과 저장 변경을 섞지 않는다. `rule_version`이 있어서 나중에 공존할 수 있다.
3. **결정 필요 — 원본 행이 바뀌면.** 추천: stale로 두고 적용하지 않는다. 이유: 재생성된 계획 위에 예전 조정을 덮으면 사용자가 보지 않은 조합이 생긴다. 대안(같은 날짜의 새 planner 행에 재바인딩)은 대부분 당일 조정이라 이득이 작다.
4. **결정 필요 — 외부 출력 반영.** ICS 캘린더 피드(`calendar_feed_service`), `garmin_push`·`caldav_push`는 원본 SQL을 직접 읽는다. 추천: v1에서는 반영하지 않고 후속 항목으로 남긴다. 이유: 외부 기기에 이미 보낸 워크아웃의 갱신·삭제 의미를 따로 설계해야 한다. 반영하지 않으면 캘린더에 원안이 보인다는 한계를 문서에 적는다.

그 밖의 사항(되돌리기 당일 한정, 결정 없이 지난 제안은 원안 유지, 레거시 백필 없음)은 31·99 설계에서 이미 정해졌거나 사실로 확인된 것이라 결정 항목에 넣지 않는다.
