# race_calendar 관리 화면·계획 연동 설계 (ADJ-11·12, NEW-1·4·5)

> 작성 2026-10-11 · product-architect · 상태: 초안(결정 전) · 상위: `decisions-table.md` ADJ-11·12·NEW-1·4·5, `adjustment-signals.md` §3.4, `adjustment-new-signals.md`
> DB·API 형태는 제안 수준이며 system-architect 확인 대상이다. 정책·기본값·문구는 §5에 결정 항목으로만 올린다.

## 1. 근본 원인 (grep 2026-10-11)
- **대회의 원천이 셋으로 흩어져 있고, B/C 대회를 관리하는 곳이 없다.** ① `goals.race_date·distance_km`(활성 목표 1건 유니크, v32) ② `planned_workouts.workout_type='race'` 행(재계획 때 다시 만들어져 메타데이터가 사라짐) ③ `race_results`(v20, `activity_id` 기준 실적, 예정 대회 아님).
- **화면이 없다.** 대회 관련 화면은 `/today/race`(레이스 허브, 예측 위주)와 `/today/race/races`("예측에 쓰는 대회" = 실적 확정 목록, 39줄)뿐이다. 대회를 등록하는 길은 목표 생성(`/coach/plan/new`의 race_date) 하나뿐이고, B/C 대회 등록·수정·삭제·조회는 어디에도 없다. 앞선 설계(`adjustment-new-signals.md`)도 "추가 시트"만 두었고, 수정·삭제와 계획 반영 질문은 다루지 않았다.
- **대회에서 계획으로 이어지는 길이 끊겨 있다.** `training/constraints.b_race_week()`(B 레이스 주 재배치, 순수 함수)는 테스트(`tests/test_constraints.py`)만 부르고 실제 호출자는 없다. 안전한 재계획(`plan_replan_service.preview/apply/undo`)은 활성 goal 기준이고, 시작일은 다음 월요일로 고정, 대회 주는 거부(409 `RACE_WEEK`)한다. 그래서 가까운 B/C 대회는 재계획으로 반영할 수 없다. `plan_adjustments`(v31)는 행 단위 제안·수락·되돌리기 체계를 갖췄지만 `source` CHECK가 `crs|user|coach`뿐이다.
- 그 결과, 사용자가 "다음 달 하프 B 대회"를 알려 줄 방법이 없고, `race_plan` 신호의 priority는 `unknown`에 머물며, 계획은 대회를 모른 채로 남는다.

## 2. 설계안 (추천 = 대안 A)

### 2.1 데이터 모델 `race_calendar` (v38, 가산 마이그레이션. 앞선 초안을 아래처럼 확장하는 안)
| 필드 | 필수 | 의미 |
|---|---|---|
| `id, created_at, updated_at` | 자동 | |
| `name` | 필수 | 대회 이름 |
| `race_date` | 필수 | YYYY-MM-DD |
| `distance_km` | 필수 | 프리셋 5/10/21.0975/42.195 또는 직접 입력 |
| `priority` | 필수 | `A|B|C`(A는 활성 목표와의 관계 RC-1, 미선택 허용 여부 RC-2) |
| `goal_type`, `goal_value` | 선택 | 대회 목표. 유형 선택지는 RC-3(예: 완주/목표 기록/PB/즐기기·페이스메이킹). 기록이면 `goal_value`=초 |
| `adapt_plan` | 필수(기본값 RC-4) | "이 대회에 맞춰 훈련을 바꿀지" 0/1 |
| `plan_state` | 자동 | `unasked|accepted|later|declined|stale`: 계획 반영 질문의 상태. 대회를 수정하면 `stale`이 된다 |
| `taper_days`, `recovery_days` | 선택 | NULL이면 기본값(거리별 기본값과 B/C 절반 적용 여부는 RC-5) |
| `allow_recovery_downgrade` | 선택 | 회복 기간 하향 트리거 허용 여부(RC-6) |
| `status` | 자동 | `planned|done|cancelled` |
| `origin` | 자동 | `manual|goal|import`(가져오기 경로는 범위 밖) |
| `goal_id`, `planned_workout_id`, `race_result_id` | 선택 | 목표 A, 계획의 race 행, 확정된 실적과 연결 |
| `note` | 선택 | 메모 |
- 중복 방지: `status='planned'`인 대회 중 같은 `race_date`이면서 `distance_km`도 같은 행은 1건만 허용. A는 동시에 1건만(활성 goal 유니크와 같은 규칙).
- 완료: `race_date`가 지나면 레이스 허브의 "결과 기록" 카드에 `race_result_service.candidates`(같은 날짜, 거리 ±10%)를 띄운다. 사용자가 `confirm`하면 `race_result_id`가 연결되고 `status='done'`이 된다. 자동 전환 여부는 RC-8.

### 2.2 화면 (모바일 375px, 보이는 h1(PageHead), 44px 탭 영역, 오버레이는 `use:modal`)
- **진입:** 레이스 허브 `/today/race`에 "대회 캘린더" 카드(Level 0 한 줄 예시: "다음 대회 · 춘천 10K(B) · D-15 · 계획 반영됨"), 계획 상세 `/coach/plan/[id]` 주간 목록의 대회 날짜 마커(A/B/C 배지), 활동의 race 후보.
- **목록 `/today/race/calendar` (신규, h1 "대회 캘린더"):** 다가오는 대회와 지난 대회 두 구역. 행 구성은 배지, 이름, 날짜·D-day, 거리, 목표 한 줄, 계획 상태 칩(반영됨 / 질문 대기 / 반영 안 함 / 변경 후 미반영). Level 0은 가장 가까운 대회 1건을 의미 문장으로 보여 준다. 우상단에 "대회 추가"(44px).
- **상세 시트(Level 1→2):** 목표, 보호 기간(테이퍼 `MM/DD~MM/DD`, 회복 `~MM/DD`), 이 대회 때문에 바뀐 세션 목록(plan_adjustments 근거 칩), 연결된 실적. Level 2 "왜?"에서는 기간 계산식(거리 → 일수, B/C 보정)과 `race_plan` 신호 값을 보여 준다(투명성 원칙).
- **등록·수정 시트 `RaceEntrySheet`:** 필수 4개(날짜, 이름, 거리 칩, 우선순위 세그먼트)를 위에 두고, 나머지(목표 유형·값, 계획 조정 토글, 보호 기간 직접 설정, 메모)는 "더 설정" 아래에 접는다. A를 고르는데 활성 목표가 따로 있으면 인라인 안내와 "목표 대회 바꾸기" 경로를 보여 준다(RC-1). 저장 실패는 시트 안에 오류 문구를 두고 입력을 유지한다.
- **계획 반영 질문 `RacePlanPrompt`(저장 직후, `adapt_plan=1`일 때):** 제목 "이 대회에 맞춰 계획을 조정할까요?". 미리보기에는 바뀌는 날짜별 전→후(예: "10/24 템포 10km → 이지 6km", "10/26 레이스로 교체", "10/27 휴식")와 근거(대회 B, 테이퍼 3일)를 보여 준다. 버튼 3개.
  - **수락:** 제안을 만들고 적용한다(일괄 수락 vs 하나씩 수락은 RC-7). 적용 후에는 기존 되돌리기 규칙을 그대로 쓴다.
  - **나중에:** `plan_state='later'`. 목록 칩과 Today 힌트 1줄로 다시 진입할 수 있다.
  - **조정 안 함:** `adapt_plan=0`, `declined`. 대회 기록과 신호만 남긴다(§2.3).
- **수정:** 날짜, 거리, 우선순위, 보호 기간, `adapt_plan` 중 하나라도 바뀌면 `plan_state='stale'`로 바꾸고 같은 질문 시트를 "변경 영향" 모드로 연다. 표시는 기존 반영분 되돌리기 + 새 제안을 diff로 묶은 형태다. 이름, 목표, 메모만 바뀌면 질문하지 않는다.
- **삭제:** 확인 다이얼로그에서 영향(되돌릴 조정 N건, 연결된 실적 유지 여부)을 미리 보여 준다. 삭제할지 취소 상태로 보존할지는 RC-9.
- **빈 상태:** "등록된 대회가 없어요. 목표 외에 나갈 대회를 추가하면 그 앞뒤 훈련을 맞춰 드려요" + 추가 버튼. 데이터 수집 중 UI 규칙을 따른다.
- **오류 상태:** 목록·상세 로드 실패는 공통 `ErrorState`(재시도, `error-retry-common.md`)를 쓴다. 409 충돌(A 중복, 같은 날·같은 거리, 재계획 잠금 `REPLAN_LOCKED`, 대회 주 `RACE_WEEK`)은 코드별 안내 문구로 보여 준다(문구는 RC-10).

### 2.3 계획 연동 흐름
1. **저장 → 영향 계산(쓰기 없음):** 순수 함수 `race_impact(rows, race, windows)`가 계획 행의 전/후 목록을 돌려준다. `b_race_week()`를 일반화해서 재사용한다(테이퍼 일수와 회복 일수를 인자로 받음). race 행·rest 행·완료나 매칭이 끝난 행은 건드리지 않는다(`plan_replace` 행 보호 규칙과 같다).
2. **B/C 대회:** 전/후 차이를 행 단위 `plan_adjustments` 제안으로 바꾼다(op는 `replace|reduce|rest`, `reasons_json`에 `{key:'race_plan', race_id, priority}`). 기존 수락·되돌리기·rev 체계를 그대로 쓴다. 어떤 `source` 값으로 기록할지는 system-architect 협의 사항이다(`user` 재사용 vs CHECK 확장).
3. **A 대회(=활성 목표):** 날짜나 거리가 바뀌면 goal을 갱신하고 기존 `plan_replan_service.preview → apply → undo`로 넘긴다(다음 월요일 시작, RACE_WEEK 거부, 마지막 1건 되돌리기 규칙을 그대로 쓴다). 대회 주 안에서 바꾸면 2번 행 단위 경로로 대신 처리한다.
4. **보호 기간과 조정 제안(§3.4):** 테이퍼와 회복 기간에는 상향(BOOST)을 막고(hold), 하향은 보조 근거로만 쓴다. `adapt_plan=1`로 반영된 대회는 계획 안에 테이퍼가 이미 들어 있으므로 `race_plan` 단독 하향 트리거를 만들지 않는다(이중 감량 방지). 반영하지 않은 대회(`declined`, `later`, `stale`)의 회복 기간에 Q-day가 있을 때 하향 트리거를 허용할지는 RC-6.
5. **조정 안 함:** 계획 행은 그대로 둔다. 캘린더 기록, `race_plan` 신호, 보호 기간 hold, AI 코치 맥락만 남는다(상향 hold도 끌지는 RC-4b).
6. **AI 코칭 예시:** "다음 주 일요일 10K(B)가 있어서 목요일 템포는 가볍게 바꿔 뒀어요. (race_plan D-10, 테이퍼 3일)" "왜?"를 누르면 상세 시트의 Level 2로 간다.

### 2.4 대안
- **A(추천): 하이브리드.** A 대회는 기존 안전 재계획으로, B/C 대회는 행 단위 `plan_adjustments` 제안으로 처리한다. 이미 있는 확인·되돌리기 UX를 재사용하고, 가까운 대회(이번 주)도 다룰 수 있다. 단점은 경로가 둘이라 테스트 범위가 넓다는 점이다.
- **B: 모든 대회를 재계획 엔진 제약으로 처리.** 생성기가 race_calendar를 입력으로 받아 다시 만든다. 결과의 일관성은 높지만 다음 월요일 시작과 RACE_WEEK 거부 때문에 2주 안의 대회를 반영하지 못한다. 엔진 변경 범위도 크다(system-architect 영역).

## 3. 변경 파일 표 (예상, 300줄 이하)
| 파일 | 구분 | 내용 | 줄 |
|---|---|---|---|
| `src/db_schema_v38.py` | 수정(설계 중인 신규) | race_calendar 컬럼 확장 + 부분 유니크 인덱스 | +30 |
| `src/services/race_calendar_service.py` | 신규 | add/list/get/update/cancel·delete, goal(A) 동기화, 중복 검사 | ~180 |
| `src/services/race_plan_link.py` | 신규 | `race_impact` 호출, 제안 생성·되돌리기 묶음, plan_state 전이 | ~150 |
| `src/training/constraints.py` | 수정 | `b_race_week` → 테이퍼/회복 일수 인자 일반화(기존 시그니처 호환) | +20 |
| `src/services/adjustment_signals_race.py` | 수정 | priority·창 길이를 race_calendar에서 가져오기, adapt_plan 반영 | +30 |
| `src/api/routes_race_calendar.py` | 신규 | GET/POST/PATCH/DELETE, GET `/<id>/impact`, POST `/<id>/plan`(accept/later/decline). 경로는 v1 밖 | ~140 |
| `frontend/src/routes/today/race/calendar/+page.svelte`·`+page.ts` | 신규 | 목록, 빈 상태, 오류 상태 | ~150 |
| `frontend/src/lib/components/RaceEntrySheet.svelte` | 신규 | 등록·수정 시트 | ~180 |
| `frontend/src/lib/components/RacePlanPrompt.svelte` | 신규 | 반영 질문, 영향 diff | ~130 |
| `frontend/src/lib/components/RaceDetailSheet.svelte` | 신규 | 상세 Level 1/2, 삭제 확인 | ~140 |
| `frontend/src/routes/today/race/+page.svelte`, `coach/plan/[id]/+page.svelte` | 수정 | 캘린더 카드, 날짜 마커 | +20/+15 |
| tests: `test_race_calendar_service.py`, `test_race_plan_link.py`, `test_constraints.py`(+), `test_routes_race_calendar.py`, `test_db_schema_v38.py`(+); 프론트 `RaceEntrySheet/RacePlanPrompt/RaceDetailSheet.test.ts` | 신규·수정 | 함수마다 1개 이상 | ~50개 |

## 4. 단계·검증
1. **S0 결정:** RC-1~10 결정, system-architect와 `source` 값·API 형태 협의.
2. **S1 스키마·서비스:** v38 확장, `race_calendar_service`. 검증: 빈 DB와 DB **사본**에서 마이그레이션, 재실행 멱등, CHECK·유니크 위반 거부, goal A 동기화 왕복.
3. **S2 영향·연동:** `race_impact`, `race_plan_link`. 검증: 보호 행 불변, 제안 → 수락 → 되돌리기 왕복, 수정 시 이전 반영분 되돌리기와 새 제안 생성, A 경로의 RACE_WEEK 대체 처리, 이중 감량 없음(백테스트 픽스처).
4. **S3 API:** 응답 코드(400/404/409)와 `ErrorState` 매핑 테스트.
5. **S4 화면:** 컴포넌트 테스트, 브라우저 375px에서 등록 → 질문 → 수락 → 되돌리기, 수정 → stale → 재반영, 삭제 미리보기, 오프라인 재시도. 확인 항목: h1 1개, 탭 영역 44px 이상, 시트 Esc·포커스 복귀, 데모 모드.
6. `pytest tests/` 전체, `check_docs.py`, BACKLOG·decisions 기록.
- **호환·v1:** 재계획은 서비스 계층(`plan_replan_service`)을 직접 부르고 `/api/v1/coach/plan/replan` 라우트에는 의존하지 않는다(v1 제거 예정). 기존 goal 생성 경로는 유지하고, 생성 시 race_calendar A 행을 동기화한다(RC-1). `race_results`·`/today/race/races`는 변경하지 않는다.

## 5. 결정 필요
- **RC-1 A 대회와 활성 목표의 관계:** (a) goals를 원천으로 두고 race_calendar에 `origin='goal'` 미러 행을 둔다(시트의 날짜·거리 수정이 goal 갱신과 재계획으로 이어짐). 목록이 하나로 모이는 대신 동기화 코드가 필요하다. (b) race_calendar는 B/C만 저장하고 목록에서 goal을 합쳐 보여 준다. 단순하지만 A는 다른 화면에서 수정해야 한다. (c) race_calendar가 원천이고 goal이 참조한다. 모델은 깔끔하지만 v32 유니크와 기존 목표 화면을 다시 짜야 한다.
- **RC-2 우선순위 필수 여부(NEW-4):** (a) 필수(요청된 최소 입력) / (b) 선택 + `unknown` / (c) 선택 + C로 간주.
- **RC-3 목표 유형 선택지:** (a) 완주/목표 기록/PB 3개 / (b) 여기에 즐기기·페이스메이킹을 더한 5개. PB는 기존 기록 표시를, 기록 유형은 예측과 비교해 보여 주기를 포함할지도 정해야 한다.
- **RC-4 `adapt_plan` 기본값:** (a) B=켜짐, C=꺼짐 / (b) 항상 질문하고 기본값은 없음 / (c) 항상 꺼짐. **RC-4b:** 조정 안 함일 때도 보호 기간 상향 hold를 유지할지 여부.
- **RC-5 보호 기간:** (a) 제안값(테이퍼 3/7/14일, 회복 2/4/7일, B/C 절반)을 기본으로 하고 대회별로 덮어쓸 수 있게 한다 / (b) 기본값 고정, 덮어쓰기 없음 / (c) 프리셋 3단계(짧게/보통/길게). 절반으로 줄일 때 올림·내림 규칙도 정해야 한다.
- **RC-6 회복 기간 하향 트리거:** (a) 계획에 반영하지 않은 대회에서만 허용 / (b) 허용하지 않음(support만) / (c) 대회별 토글.
- **RC-7 수락 방식:** (a) 미리보기 한 번에 일괄 적용, 일괄 되돌리기 / (b) proposed로만 만들고 Today에서 하나씩 수락.
- **RC-8 완료 처리:** (a) 사용자가 결과를 확정할 때만 done / (b) 날짜가 지나면 자동 done + 결과 연결 안내 / (c) 미확정 대회는 N일 뒤 질문.
- **RC-9 삭제와 보존:** (a) 소프트 삭제(`cancelled`, 이력과 실적 연결 유지) / (b) 하드 삭제 + 반영분 되돌리기 / (c) 미래 대회는 하드, 지난 대회는 보존. 지난 대회 삭제 시 race_results를 남길지도 함께 정해야 한다.
- **RC-10 문구:** 질문 제목, 버튼 3개("조정할게요/나중에/조정 안 함"), 409 안내, 빈 상태 문구.

## 6. 범위 밖 메모
- 외부 캘린더나 대회 사이트 가져오기(`origin='import'`), CalDAV·Garmin에 이미 푸시된 행 정리(A6 D5와 같은 문제).
- 생성기가 race_calendar를 직접 제약으로 받는 방식(대안 B)과 다중 A 시즌 계획. 계획 엔진 영역이다.
- `/today/race/races`(실적 목록)와 캘린더의 지난 대회 구역 통합 여부. 이후 IA 정리 때 다룬다.
- 대회 데이터의 AI 코치 전송 동의는 NEW-12와 함께 다룬다.
