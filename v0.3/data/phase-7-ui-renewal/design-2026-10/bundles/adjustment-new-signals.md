# 조정 제안 신규 수집 신호 4종 (adjustment-new-signals)

> 작성 2026-10-11 · 상태: 설계 초안(미확정) · 관련: ADJ-10(신규 수집 착수 결정), ADJ-1·2·4·13·15, `bundles/adjustment-signals.md` §3.2~3.9, `patterns/timezone-display.md`
> 전제: adjustment-signals 의 `signals_json`(role: trigger/support/counter/hold/context, freshness) 과 `collect()` 수집기 구조를 그대로 쓴다. 여기서는 **입력·저장·화면·신호화**만 다룬다.

## 1. 근본 원인 — 왜 지금 신호가 없는가
- **입력 모델이 "하루 1장 체크인"뿐이다.** `user_inputs`(fatigue·pain·mood·note, `UNIQUE(input_date,input_type)`)는 그날의 점수만 담는다. 질병·여행·고지대는 **여러 날 이어지는 상태(에피소드)** 인데 시작·종료를 표현할 자리가 없어 `note` 자유 텍스트로만 흘러간다.
- **수집은 있으나 해석이 없다(여행·고도).** Garmin `timeZoneUnitDTO.offset`·Strava `timezone` 이 `metric_store` 의 `timezone_offset`(활동 단위, `metric_defs_misc.py:165`)으로 이미 저장되고, `activity_streams.altitude_m`·`activity_summaries.start_lat/lon` 도 있다. 그러나 "평소와 다른 시간대/고도"를 판단하는 소비처가 0이다.
- **대회 = 목표 1개 가정.** `goals` 는 활성 1건(v32 유니크)이고 우선순위 컬럼이 없다. 계획 중간 대회는 `planned_workouts.workout_type='race'` 행으로만 존재하며 이를 사용자가 추가하는 UI·API 가 없다(세션 화면은 표시만). 그래서 `training/constraints.b_race_week()` 는 호출자가 없다.
- 부수: `src/services/today_service.py` 가 이미 320줄(규칙 300줄 초과) — 체크인 확장을 여기에 넣을 수 없다.

## 2. 설계안(신호별)

### 2.0 공통 저장 구조(추천: 에피소드 테이블 1개 + 대회 캘린더 1개, v38)
- **`context_episodes`**(신규): `id, kind CHECK(kind IN ('illness','travel','altitude')), start_date, end_date NULL(진행 중), severity INTEGER NULL, detail_json TEXT DEFAULT '{}', origin CHECK(origin IN ('user','auto')), status CHECK(status IN ('candidate','confirmed','dismissed')), last_confirmed_date, created_at, updated_at`. 자동 감지는 `candidate` 로만 생기고, 사용자 확인 시 `confirmed`. **조정 신호는 confirmed 만 trigger/support 후보, candidate 는 context 로만**(오탐이 계획을 바꾸지 않게).
- **`race_calendar`**(신규): `id, race_date, name NULL, distance_km, priority CHECK(priority IN ('B','C')), goal_id NULL, planned_workout_id NULL, status CHECK(status IN ('planned','done','cancelled')), created_at`. A 레이스는 기존 `goals` 가 유일 원천(중복 저장 안 함).
- **스키마 순서:** v37 = adjustment-signals 의 `plan_adjustments` 재생성(백업 복원만 롤백). 신규 테이블은 **v38 로 분리**(CREATE 만 하는 가산 마이그레이션 → 롤백 = DROP, v37 위험과 섞지 않음). 단 신규 신호가 source(주 트리거)가 될 가능성이 있으면 **v37 CHECK 에 값을 미리 넣어야** v38 이후 재재생성을 피한다 → NEW-2.
- 대안 비교는 §5 NEW-1.

### 2.1 질병(illness)
- **입력:** 체크인(QuickInput) 하단 "오늘 상태" 칩 행의 `아파요` 토글. 켜면 한 줄 보조 선택(선택 안 해도 저장됨): 정도 2단계 + (선택) 증상 위치 칩(목 위/목 아래·전신 — "neck check" 관행). 다음 날 체크인에 "어제 아팠어요 — 계속/나았어요" 1탭 프롬프트(진행 중 에피소드가 있을 때만). 나았어요 → `end_date`.
- **자동 감지:** 불가(진단 금지). 안정시 심박 상승+HRV 하락 동시 발생 시 "몸 상태 어때요?" 질문을 띄우는 **프롬프트 트리거**만 선택지(NEW-8). `note` 키워드 파싱은 비추천(오탐·민감 텍스트 처리).
- **신호화:** `{"signal":"illness","value":severity,"detail":{"day_n","site"}}`. 역할은 NEW-3(트리거 여부). 어떤 선택이든 **BOOST hold** 는 걸 수 있음(상향 금지는 안전 방향). 신선도: 오늘 체크인에서 확인 = fresh, 마지막 확인 1~2일 전 = partial, 그 이상 미확인 진행 중 에피소드 = stale(자동 종료 여부 NEW-9).
- **복귀:** `end_date` 이후 N일은 context(`detail.returning`) — 복귀 첫 Q-day 감량 근거 후보(N 값은 NEW-9).

### 2.2 여행·시간대(travel)
- **자동 감지(가능, 부분):** 활동별 `metric_store.timezone_offset`(Garmin 초 단위 offset, Strava 는 `"(GMT+09:00) Asia/Seoul"` 텍스트 → 파서 필요)을 날짜순으로 보고 **홈 오프셋(최근 28일 최빈값) 대비 |Δ| ≥ 임계** 인 첫 활동일에 `candidate` 생성(`detail: {from_offset, to_offset, delta_h, direction:"east|west", evidence_activity_ids}`). Garmin·Strava 둘 다 없는 Strava CSV 행은 `timezone-display.md` 체인의 `tz_peer.offset_sec`/`tz_source` 를 2차 출처로 재사용(추정 `fallback` 등급은 감지에서 제외 — 순환 추정 방지). 한계: 활동이 없는 이동일·시간대 변화 없는 장거리 이동(국내 장거리 운전 등)은 감지 불가 → 수동.
- **수동 입력:** 같은 칩 행의 `이동·시차` 토글. 자동 후보가 있으면 칩에 "시차 +7시간 감지 — 맞아요?"(확인/아니에요). 수동 입력은 시차 크기 선택(없음/1~3h/4h+) 1단계만.
- **신호화:** `{"signal":"travel","value":delta_h,"detail":{"day_n","direction","origin"}}`. 제안 역할: 도착 후 창(창 길이 NEW-6) 동안 BOOST hold + 하향 support, 창 밖은 context. 신선도: 감지 근거 활동이 오늘−1일 이내 = fresh, 창 안이지만 근거 활동 오래됨 = partial. 귀국(홈 오프셋 복귀) 감지 시 새 에피소드가 아니라 기존 travel `end_date` 갱신 + 역방향 시차 창(선택지 NEW-6).

### 2.3 고도(altitude)
- **자동 감지(가능, 부분):** 활동 `activity_streams.altitude_m` 의 중앙값(스트림 없으면 활동 고도 미상 → 감지 생략). 홈 고도(최근 28일 활동 중앙값의 중앙값) 대비 **절대 고도 ≥ 임계 그리고 홈+Δ ≥ 임계** 일 때 `candidate`. 외부 고도 API 호출 금지(위경도→고도 변환 안 함). 한계: 기압계 고도 오차, 실내·트레드밀(스트림 없음), "체류 고도"≠"달린 고도"(산악 트레일 당일치기 오탐 → 2일 연속 조건 선택지, NEW-6).
- **수동 입력:** 칩 `고지대` 토글 + (선택) 대략 고도 3단계(1,500 미만/1,500~2,500/2,500+). 자동 후보면 "고도 2,300m 활동 감지 — 지금 고지대에 있어요?".
- **신호화:** `{"signal":"altitude","value":altitude_m,"detail":{"day_n","band","origin"}}`. 제안: 적응 창 동안 BOOST hold + 강도 세션 하향 support(페이스 목표 하향은 범위 밖 — §6), 창 밖 context. 신선도: 오늘/어제 활동 근거 또는 오늘 체크인 확인 = fresh, 그 외 partial.

### 2.4 B/C 레이스 우선순위(race priority)
- **입력:** 레이스 허브 `/today/race` 에 "대회 추가" 시트(날짜·거리 필수, 이름·우선순위 선택). 우선순위 미선택 시 저장값 정책 NEW-4. 계획 상세(`/coach/plan/[id]`) 주간 목록에 대회 날짜 마커(B/C 배지) + 같은 시트 진입. 계획 중간에 이미 있는 `planned_workouts` race 행은 시트에서 "이 대회 우선순위 지정"으로 연결(`planned_workout_id`).
- **계획 반영:** 대회 추가 시 그날 계획 행을 race 로 바꿀지·주변 테이퍼를 만들지는 **계획 엔진 영역** — 선택지만(NEW-5). 최소안은 "캘린더 저장 → `race_plan` 신호에 반영 → 조정 제안이 hold/support" 로 계획 행은 그대로.
- **자동 감지:** 미래 대회는 불가. 과거 `race_result_service.candidates` 는 실적 확인용 — 대상 아님.
- **신호화:** adjustment-signals §3.4 `race_plan` 수집기의 `detail.priority` 를 `unknown` → `B|C`(캘린더) / `A`(goals) 로 채움. 창 길이·추가 대회 recovery trigger 는 기존 D12 그대로(신규 결정 없음). `b_race_week()` 재사용 여부는 NEW-5.

### 2.5 화면(모바일 375px, 최소 입력 부담)
- **체크인(QuickInput, 156줄):** 피로·통증 아래 **칩 1행**(아파요 · 이동·시차 · 고지대), 전부 기본 비선택, 하나도 안 눌러도 기존 저장 동작 불변. 칩을 켠 경우에만 보조 1행 펼침. `compact` 모드에서는 칩 행을 "+ 상태" 링크 뒤로 접음(노출 방식 NEW-7). 진행 중 에피소드·자동 후보가 있으면 칩 대신 확인 프롬프트 1줄이 먼저 보인다(Level 0: "시차 +7시간 감지 — 맞아요?").
- **조정 카드 "왜?"(Level 1~2):** 신규 신호도 같은 근거 목록에 "여행 3일째 (시차 +7h, 자동 감지·확인됨)"처럼 의미 먼저 + 괄호 값·출처. 표시 문구는 adjustment-signals D7 과 함께 결정.
- **v1:** `src/web/views_training_wellness.render_checkin_card` 는 확장하지 않는다(v1 제거 예정). v1 체크인 저장은 `user_inputs` 만 쓰므로 에피소드 테이블과 충돌 없음.

### 2.6 개인정보·민감도
- 질병 = 건강 정보, 여행·고도 = 위치 추정 가능 정보. 저장은 kind·날짜·정도·시차/고도 **수치만**(위경도·지명 저장 안 함; 근거는 activity id 참조).
- 선택지: 보존 기간(NEW-10), 내보내기·백업 포함(NEW-11), AI 코치(LLM) 전송 범위(`coach_consent` 와 연계, NEW-12), 삭제 UI(에피소드 단건 삭제는 기본 제공 권고 — 확정은 NEW-10).

## 3. 변경 파일 표
| 파일 | 신규/수정 | 내용 | 예상 줄 |
|---|---|---|---|
| `src/db_schema_v38.py` | 신규 | `context_episodes`·`race_calendar` CREATE, 멱등, dry_run | ~80 |
| `src/db_setup.py` | 수정 | DDL·`SCHEMA_VERSION=38`·마이그레이션 호출 | +25 |
| `src/db_schema_v37.py` | 수정(설계만) | NEW-2 선택 시 source CHECK 에 `illness`/`travel`/`altitude` 사전 포함 | +1 |
| `src/services/context_episodes.py` | 신규 | open/extend/close/confirm/dismiss/list_active (쓰기 예외 명시) | ~160 |
| `src/services/context_autodetect.py` | 신규 | `parse_offset`, `home_offset`, `detect_tz_shift`, `detect_altitude`(순수) + 로더 | ~170 |
| `src/services/race_calendar_service.py` | 신규 | add/list/update/cancel, goals(A)·planned race 행 병합 조회 | ~130 |
| `src/services/adjustment_signals_context.py` | 신규 | illness/travel/altitude 수집기 → signal dict(freshness 포함) | ~130 |
| `src/services/adjustment_signals_race.py` | 수정(신규 파일 예정분) | `priority` 를 race_calendar 에서 채움 | +25 |
| `src/api/routes_context.py` | 신규 | `GET/POST/PATCH /api/context-episodes` | ~110 |
| `src/api/routes_race_calendar.py` | 신규 | `GET/POST/PATCH /api/race-calendar` | ~100 |
| `src/api/routes_today.py` | 수정 | 체크인 응답에 active·candidate 에피소드 동봉 | +15 |
| `frontend/src/lib/components/ContextChips.svelte` | 신규 | 칩 행·보조 행·확인 프롬프트 | ~150 |
| `frontend/src/lib/components/QuickInput.svelte` | 수정 | ContextChips 삽입, compact 접힘 | +15 |
| `frontend/src/lib/components/RaceEntrySheet.svelte` | 신규 | 대회 추가·우선순위 시트 | ~140 |
| `frontend/src/routes/today/race/+page.svelte` | 수정 | "대회 추가" 진입, B/C 목록 | +25 |
| `frontend/src/routes/coach/plan/[id]/+page.svelte` | 수정 | 대회 마커·시트 진입 | +20 |
| `frontend/src/lib/api*.ts`, `lib/types/index.ts` | 수정 | 클라이언트·타입 | +60 |
| tests: `test_db_schema_v38.py`, `test_context_episodes.py`, `test_context_autodetect.py`, `test_race_calendar_service.py`, `test_adjustment_signals_context.py`, `test_routes_context.py`, `test_routes_race_calendar.py`; 프론트 `ContextChips.test.ts`, `RaceEntrySheet.test.ts` | 신규 | 함수마다 ≥1 | ~45개 |
| 문서: 해당 `__init__.py` docstring, `files_index`(재생성), ADR(에피소드 모델·민감정보) | 수정 | | — |

## 4. 단계·검증
1. **S0 (v37 작업 전):** NEW-2 결정 → v37 CHECK 값 확정. 이것만 adjustment-signals 일정에 선행 의존.
2. **S1 v38 + 서비스:** 테이블·`context_episodes`·`race_calendar_service`. 검증: 빈 DB/운영 DB **사본** 마이그레이션, 재실행 멱등, CHECK 위반 거부, `PRAGMA integrity_check`, DROP 롤백.
3. **S2 자동 감지(순수 함수):** 픽스처 — Garmin offset 32400→-25200, Strava 텍스트 파싱, offset 결측, `fallback` 등급 제외, 고도 스트림 없음/1일 스파이크/2일 연속. candidate 중복 생성 없음(같은 에피소드 extend).
4. **S3 신호화:** `adjustment_signals_context` 가 confirmed→role 후보, candidate→context 만 내는지; freshness 경계(오늘/1~2일/그 이상); NEW-3 선택에 따른 `primary_trigger` 순서 테스트; race priority 채움 회귀(기존 `unknown` 경로 불변).
5. **S4 API·UI:** 칩 미선택 저장 = 기존 요청 본문과 동일(회귀), 에피소드 API 입력 검증(`server-input-origin-validation.md` 패턴), 375px 브라우저 확인 — 체크인 카드 높이 증가 1행 이내(접힘 시 0), 터치 타깃 44px, 키보드·스크린리더 `aria-pressed`(accessibility-common), 확인 프롬프트 1탭 종료.
6. 공통: 신규 파일 300줄 이하, `pytest tests/` 전체, `check_docs.py`, v1 체크인 화면 회귀(저장·표시 불변).

## 5. 결정 필요
- **NEW-1 저장 모델:** (a) **신규 `context_episodes`·`race_calendar`(추천)** — 기간 상태·자동/수동·확인 상태 표현, 가산 마이그레이션 / (b) `user_inputs` 확장(새 `input_type` + `payload_json` 컬럼, 우선순위는 `planned_workouts.priority` 컬럼) — 테이블 수 적음, 하루 단위라 기간·종료 표현 불가·재계획 시 race 행 재생성으로 우선순위 유실 위험.
- **NEW-2 v37 source CHECK 사전 포함:** (a) `illness`(+`travel`·`altitude`) 미리 포함 — 이후 재생성 없음, 미사용 값 존재 / (b) 미포함 — NEW-3 에서 트리거로 정하면 v39 재생성(백업 필요) 추가.
- **NEW-3 신규 신호의 trigger 여부(ADJ-13 결합 규칙과의 관계):** (a) 전부 support/hold/context 만(트리거 집합 불변, 빈도 변화 없음) / (b) 질병만 통증처럼 단독 OR 트리거(안전 방향, 자가 보고 신뢰) / (c) 질병·여행·고도를 AND 그룹(CRS·ACWR·피로)에 편입. (b)(c)는 `primary_trigger` 순서(ADJ-15)에 위치 결정 필요(예: pain > illness > checkin …).
- **NEW-4 B/C 미선택 시:** (a) `unknown` 저장(창 길이 B/C 절반 미적용) / (b) C 로 간주 / (c) 우선순위 필수 입력.
- **NEW-5 대회 추가의 계획 반영:** (a) 캘린더만(조정 제안이 hold/support) / (b) 그날 계획 행을 race 로 바꾸는 제안 1건 생성(사용자 수락) / (c) `b_race_week()` 로 주간 재배치 제안 — 계획 엔진 범위, system-architect 협의.
- **NEW-6 창 길이·임계:** 시차 임계(3h/4h), 도착 후 창(시차 h당 1일 / 고정 3일), 귀국 역방향 창 적용 여부, 고도 임계(1,500/2,000m)·연속일 조건(1일/2일), 고도 적응 창(3/7일).
- **NEW-7 체크인 노출:** (a) 칩 행 항상 노출 / (b) "+ 상태" 뒤에 접기 / (c) 자동 후보·진행 에피소드 있을 때만 노출. 칩·프롬프트 문구 포함.
- **NEW-8 질병 프롬프트 자동 질문:** (a) 없음 / (b) RHR↑+HRV↓ 동시일 때 "몸 상태 어때요?" 질문(진단 표현 금지) — 임계는 adjustment-signals §3.5 안정시 심박 후보와 공유.
- **NEW-9 에피소드 종료:** 미확인 진행 중 질병 (a) N일 후 자동 종료 / (b) stale 로만 표시·종료는 사용자 / 복귀 context 일수 N.
- **NEW-10 보존 기간:** (a) 무기한(추세·재발 분석) / (b) N개월 후 `detail_json`·severity 삭제, kind·날짜만 / (c) 사용자 설정. 단건 삭제 UI 제공 여부.
- **NEW-11 내보내기·백업:** (a) 포함 / (b) 제외 / (c) 내보내기 시 체크박스(기본값도 결정).
- **NEW-12 AI 코치 전송:** (a) `coach_consent` 하나로 일괄 / (b) 질병만 별도 동의 / (c) 전송 안 함(로컬 규칙 엔진만 사용).
- **NEW-13 자동 후보 무응답 처리:** candidate 를 (a) 계속 context 로만 / (b) 2일 무응답 시 dismissed.

## 6. 범위 밖 메모
- `today_service.py` 320줄 초과(규칙 위반) — 별도 분리 작업 필요.
- 고도·폭염에 따른 **페이스 목표 보정**(조정이 아닌 처방 변경)은 별도 설계.
- `views_export.py` 는 활동 CSV 만 내보냄 — 사용자 데이터 전체 내보내기 기능 자체가 없어 NEW-11 은 기능 신설과 함께 의미가 생김.
- Strava `timezone` 텍스트가 `metric_store` 에 text 로 저장되는지(숫자 offset 아님) 구현 시 확인.
