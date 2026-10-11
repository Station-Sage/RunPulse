# 조정 제안 신규 수집 신호 4종 (adjustment-new-signals)

> 작성 2026-10-11 · 상태: 설계 확정(NEW-1~13 결정 반영, 구현 전) · 관련: ADJ-10(신규 수집 착수 확정), ADJ-1·2·4·13·15, NEW-1~13, RC-1~17(`bundles/race-calendar.md`), `bundles/adjustment-signals.md` §3.2~3.9, `patterns/timezone-display.md`(TZ), 접근성 계약(A11Y)
> 전제: adjustment-signals 의 `signals_json`(role: trigger/support/counter/hold/context, freshness) 과 `collect()` 수집기 구조를 그대로 쓴다. 여기서는 질병·여행·고도의 **입력·저장·화면·신호화**를 다룬다. B/C 레이스 우선순위의 저장·화면·계획 반영은 `race-calendar.md` 가 원천이며 이 문서는 신호 연결만 적는다.
> 변경 이력: 2026-10-11 초안 · 2026-10-11 설계서 동기화(NEW-1~13 확정 반영)

## 1. 근본 원인 — 왜 지금 신호가 없는가
- **입력 모델이 "하루 1장 체크인"뿐이다.** `user_inputs`(fatigue·pain·mood·note, `UNIQUE(input_date,input_type)`)는 그날의 점수만 담는다. 질병·여행·고지대는 **여러 날 이어지는 상태(에피소드)** 인데 시작·종료를 표현할 자리가 없어 `note` 자유 텍스트로만 흘러간다.
- **수집은 있으나 해석이 없다(여행·고도).** Garmin `timeZoneUnitDTO.offset`·Strava `timezone` 이 `metric_store` 의 `timezone_offset`(활동 단위, `metric_defs_misc.py:165`)으로 이미 저장되고, `activity_streams.altitude_m`·`activity_summaries.start_lat/lon` 도 있다. 그러나 "평소와 다른 시간대/고도"를 판단하는 소비처가 0이다.
- **대회 = 목표 1개 가정.** `goals` 는 활성 1건(v32 유니크)이고 우선순위 컬럼이 없다. 계획 중간 대회를 사용자가 추가하는 UI·API 가 없어 `training/constraints.b_race_week()` 는 호출자가 없다 → `race-calendar.md` 에서 해결.
- 부수: `src/services/today_service.py` 가 이미 320줄(규칙 300줄 초과) — 체크인 확장을 여기에 넣을 수 없다.

## 2. 설계(신호별)

### 2.0 공통 저장 구조(NEW-1·NEW-2 확정)
- **`context_episodes`**(신규, v38): `id, kind CHECK(kind IN ('illness','travel','altitude')), start_date, end_date NULL(진행 중), severity INTEGER NULL, detail_json TEXT DEFAULT '{}', origin CHECK(origin IN ('user','auto')), status CHECK(status IN ('candidate','confirmed','dismissed')), last_confirmed_date, created_at, updated_at`. 자동 감지는 `candidate` 로만 생기고, 사용자 확인 시 `confirmed`. **조정 신호는 confirmed 만 trigger/support 후보, candidate 는 context 로만**(오탐이 계획을 바꾸지 않게).
- **candidate 무응답(NEW-13):** 생성 후 2일 동안 확인/아니에요 응답이 없으면 `dismissed` 로 전이(같은 근거로 재생성하지 않음, 새 근거 활동이 생기면 새 candidate).
- **`race_calendar`**: v38 에서 같은 파일로 생성하지만 컬럼·인덱스·우선순위(A/B/C 필수, RC-2) 정의는 `race-calendar.md` §2.1 이 원천. 이 문서에서는 중복 정의하지 않는다.
- **스키마 순서(확정):** v37 = adjustment-signals 의 `plan_adjustments` 재생성(백업 복원만 롤백)이며 **source CHECK 에 `illness`·`travel`·`altitude` 를 미리 포함**(NEW-2, 재생성 1회로 끝냄). v38 = `context_episodes`·`race_calendar` CREATE 만 하는 가산 마이그레이션(롤백 = DROP). v39 = goals.race_id(race-calendar.md 소관).

### 2.1 질병(illness)
- **입력:** 체크인(QuickInput) "+ 상태" 펼침 안의 `아파요` 토글(NEW-7). 켜면 한 줄 보조 선택(선택 안 해도 저장됨): 정도 2단계 + (선택) 증상 위치 칩(목 위/목 아래·전신 — "neck check" 관행). 진행 중 에피소드가 있으면 다음 날 체크인 상단에 "어제 아팠어요 — 계속/나았어요" 1탭 프롬프트. 나았어요 → `end_date`.
- **자동 질문(NEW-8):** 진단·자동 생성은 하지 않는다. 안정시 심박 상승+HRV 하락이 동시에 있으면 "몸 상태 어때요?" 질문만 띄운다(진단 표현 금지, 임계는 adjustment-signals §3.5 안정시 심박 후보와 공유). 답이 "아파요"일 때만 user 에피소드 생성. `note` 키워드 파싱은 하지 않는다.
- **신호화(NEW-3):** `{"signal":"illness","value":severity,"detail":{"day_n","site"}}`. confirmed 질병은 통증처럼 **단독 OR 트리거**(ADJ-13 혼합 규칙의 OR 쪽). `primary_trigger` 순서는 **pain > illness > checkin > crs > acwr > readiness**. 동시에 BOOST hold.
- **신선도·종료(NEW-9):** 오늘 체크인에서 확인 = fresh, 마지막 확인 1~2일 전 = partial, 그 이상 미확인 진행 중 = stale 표시. **자동 종료 없음 — 종료는 사용자만.**
- **복귀:** `end_date` 이후 N일은 context(`detail.returning`) — 복귀 첫 Q-day 감량 근거 후보(N 값은 §7).

### 2.2 여행·시간대(travel)
- **자동 감지(부분):** 활동별 `metric_store.timezone_offset`(Garmin 초 단위 offset, Strava 는 `"(GMT+09:00) Asia/Seoul"` 텍스트 → 파서 필요)을 날짜순으로 보고 **홈 오프셋(최근 28일 최빈값) 대비 |Δ| ≥ 임계** 인 첫 활동일에 `candidate` 생성(`detail: {from_offset, to_offset, delta_h, direction:"east|west", evidence_activity_ids}`). 오프셋 해석은 `timezone-display.md` 의 `tz_source` 체인(교차 소스 `tz_peer.offset_sec` 포함)을 그대로 재사용하고 별도 해석기를 만들지 않는다. 추정 `fallback` 등급은 감지에서 제외(순환 추정 방지). 한계: 활동 없는 이동일·시간대 변화 없는 장거리 이동은 감지 불가 → 수동.
- **수동 입력:** "+ 상태" 안의 `이동·시차` 토글, 시차 크기 선택(없음/1~3h/4h+) 1단계. 자동 후보는 확인 프롬프트 "시차 +7시간 감지 — 맞아요?"(확인/아니에요)로 묻는다.
- **신호화(NEW-3):** `{"signal":"travel","value":delta_h,"detail":{"day_n","direction","origin"}}`. 트리거 아님 — 도착 후 창 동안 BOOST hold + 하향 support, 창 밖 context. 임계·창은 NEW-6 제안값(시차 3h/4h, 창 = 시차 h당 1일 또는 고정 3일)으로 진행 후 관찰 조정. 신선도: 근거 활동이 오늘−1일 이내 = fresh, 창 안이지만 근거 오래됨 = partial. 귀국(홈 오프셋 복귀) 감지 시 기존 travel `end_date` 갱신.

### 2.3 고도(altitude)
- **자동 감지(부분):** 활동 `activity_streams.altitude_m` 중앙값(스트림 없으면 감지 생략). 홈 고도(최근 28일 활동 중앙값의 중앙값) 대비 **절대 고도 ≥ 임계 그리고 홈+Δ ≥ 임계** 일 때 `candidate`. 외부 고도 API 호출 금지. 한계: 기압계 오차, 실내·트레드밀, 산악 트레일 당일치기 오탐.
- **수동 입력:** "+ 상태" 안의 `고지대` 토글 + (선택) 대략 고도 3단계(1,500 미만/1,500~2,500/2,500+). 자동 후보는 "고도 2,300m 활동 감지 — 지금 고지대에 있어요?".
- **신호화(NEW-3):** `{"signal":"altitude","value":altitude_m,"detail":{"day_n","band","origin"}}`. 트리거 아님 — 적응 창 동안 BOOST hold + 강도 세션 하향 support, 창 밖 context. 임계·창은 NEW-6 제안값(고도 1,500/2,000m, 적응 창 3/7일)으로 진행. 신선도: 오늘/어제 활동 근거 또는 오늘 체크인 확인 = fresh, 그 외 partial.

### 2.4 B/C 레이스 우선순위 → `race-calendar.md` 위임
- 저장(`race_calendar`, 우선순위 A/B/C 필수 — NEW-4·RC-2), 등록·수정 시트, 계획 반영(영향 미리보기 후 일괄 적용·일괄 되돌리기 — NEW-5·RC-7), `b_race_week()` 재사용은 모두 `race-calendar.md` 가 원천이다.
- 이 문서의 몫은 신호 연결뿐: adjustment-signals §3.4 `race_plan` 수집기의 `detail.priority` 를 race_calendar 값으로 채운다(`unknown` 상태 없음). 창 길이·추가 대회 recovery trigger 는 기존 D12 그대로.

### 2.5 화면(모바일 375px, 최소 입력 부담)
- **체크인(QuickInput, 156줄, NEW-7):** 피로·통증 아래 **"+ 상태" 링크 1개**만 기본 노출, 누르면 칩 1행(아파요 · 이동·시차 · 고지대) 펼침. 전부 기본 비선택, 펼치지 않아도 기존 저장 동작 불변. 칩을 켠 경우에만 보조 1행.
- **확인 프롬프트(Level 0):** 진행 중 에피소드("어제 아팠어요 — 계속/나았어요"), 자동 후보("시차 +7시간 감지 — 맞아요?"), NEW-8 질문("몸 상태 어때요?")은 접힘과 무관하게 체크인 상단 1줄로 보인다(NEW-13 의 2일 무응답 판정이 사용자가 본 적 없는 후보에 적용되지 않게).
- **에피소드 목록·단건 삭제(NEW-10):** 체크인 "+ 상태" 펼침 하단 "기록 보기" → 에피소드 목록 시트(kind·기간·출처). 행마다 삭제 버튼 → 삭제 확인 대화상자. 접근성 계약 준수: 시트·대화상자는 `use:modal`(포커스 가두기·Esc·복귀), 터치 타깃 44px(A11Y-2), 칩 `aria-pressed`, 포커스 링 2px(A11Y-8).
- **조정 카드 "왜?"(Level 1~2):** "여행 3일째 (시차 +7h, 자동 감지·확인됨)"처럼 의미 먼저 + 괄호 값·출처. 질병 문구는 진단 표현 금지. 표시 문구는 adjustment-signals D7 과 함께 맞춘다.
- **v1:** `src/web/views_training_wellness.render_checkin_card` 는 확장하지 않는다(v1 제거 예정). v1 체크인 저장은 `user_inputs` 만 쓰므로 충돌 없음.

### 2.6 개인정보·민감도(NEW-10~12 확정)
- 질병 = 건강 정보, 여행·고도 = 위치 추정 가능 정보. 저장은 kind·날짜·정도·시차/고도 **수치만**(위경도·지명 저장 안 함; 근거는 activity id 참조).
- **보존(NEW-10):** 무기한 보관(추세·재발 분석). 사용자가 에피소드 단건 삭제 가능(§2.5) — 삭제는 행 삭제.
- **내보내기·백업(NEW-11):** 내보내기 시 "에피소드·대회 캘린더 포함" 체크박스, 기본 포함.
- **AI 코치 전송(NEW-12):** 여행·고도는 기존 `coach_consent` 로 전송. **질병은 `coach_consent` 와 별도 동의가 있을 때만 전송**, 없으면 질병 신호는 로컬 규칙 엔진(조정 제안)에만 쓰인다. 동의 UI·철회 처리는 §7 확인 필요.

## 3. 변경 파일 표 (race_calendar 관련 파일은 `race-calendar.md` §변경 파일 표)
| 파일 | 신규/수정 | 내용 | 예상 줄 |
|---|---|---|---|
| `src/db_schema_v38.py` | 신규(공유) | `context_episodes` CREATE(멱등, dry_run). race_calendar 부분은 race-calendar.md | ~50 |
| `src/db_setup.py` | 수정 | DDL·마이그레이션 호출(SCHEMA_VERSION 은 race-calendar.md v39 기준) | +15 |
| `src/db_schema_v37.py` | 수정 | source CHECK 에 `illness`·`travel`·`altitude` 포함(NEW-2) | +1 |
| `src/services/context_episodes.py` | 신규 | open/extend/close/confirm/dismiss/delete/list_active, 2일 무응답 dismissed(쓰기 예외 명시) | ~180 |
| `src/services/context_autodetect.py` | 신규 | `home_offset`, `detect_tz_shift`(tz_source 체인 결과 소비), `detect_altitude`, `detect_illness_prompt`(순수) + 로더 | ~170 |
| `src/services/adjustment_signals_context.py` | 신규 | illness(OR 트리거)/travel/altitude 수집기 → signal dict(freshness 포함) | ~140 |
| `src/services/adjustment_signals.py`(adjustment-signals 소관) | 수정 | `primary_trigger` 순서에 illness 삽입 | +3 |
| `src/api/routes_context.py` | 신규 | `GET/POST/PATCH/DELETE /api/context-episodes` | ~120 |
| `src/api/routes_today.py` | 수정 | 체크인 응답에 active·candidate 에피소드·질문 플래그 동봉 | +15 |
| 질병 별도 동의 저장·조회 위치 | 미정 | NEW-12(§7) | — |
| `frontend/src/lib/components/ContextChips.svelte` | 신규 | "+ 상태" 접힘·칩 행·보조 행·확인 프롬프트 | ~160 |
| `frontend/src/lib/components/ContextEpisodeList.svelte` | 신규 | 에피소드 목록·단건 삭제(use:modal, 삭제 확인) | ~120 |
| `frontend/src/lib/components/QuickInput.svelte` | 수정 | ContextChips 삽입 | +10 |
| `frontend/src/lib/api*.ts`, `lib/types/index.ts` | 수정 | 클라이언트·타입 | +45 |
| tests: `test_db_schema_v38.py`(context 부분), `test_context_episodes.py`, `test_context_autodetect.py`, `test_adjustment_signals_context.py`, `test_routes_context.py`; 프론트 `ContextChips.test.ts`, `ContextEpisodeList.test.ts` | 신규 | 함수마다 ≥1 | ~40개 |
| 문서: 해당 `__init__.py` docstring, `files_index`(재생성), ADR(에피소드 모델·민감정보·질병 별도 동의) | 수정 | | — |

## 4. 단계·검증
1. **S0 (v37 작업 전):** v37 source CHECK 값 확정 — `illness`·`travel`·`altitude`(NEW-2) + race-calendar.md 의 `race` 를 한 번에 합의(§7). adjustment-signals 일정에 선행 의존.
2. **S1 v38 + 서비스:** `context_episodes`·서비스. 검증: 빈 DB/운영 DB **사본** 마이그레이션, 재실행 멱등, CHECK 위반 거부, `PRAGMA integrity_check`, DROP 롤백.
3. **S2 자동 감지(순수 함수):** 픽스처 — Garmin offset 32400→-25200, Strava 텍스트, offset 결측, `tz_source=fallback` 제외, 고도 스트림 없음/1일 스파이크/연속일, RHR↑만·HRV↓만·동시(질문은 동시만). candidate 중복 생성 없음(같은 에피소드 extend), 생성 후 2일 무응답 → dismissed, 경계(정확히 2일).
4. **S3 신호화:** confirmed→role 후보, candidate→context 만; confirmed illness 단독으로 트리거 성립; travel·altitude 는 트리거 집합 불변(빈도 회귀); `primary_trigger` = pain > illness > checkin > crs > acwr > readiness; freshness 경계(오늘/1~2일/stale), stale 질병이 자동 종료되지 않음; race priority 채움 회귀.
5. **S4 API·UI:** 칩 미선택 저장 = 기존 요청 본문과 동일(회귀), 에피소드 API 입력 검증(`server-input-origin-validation.md` 패턴), 삭제 후 목록·신호에서 사라짐, 375px — 접힘 시 카드 높이 증가 "+ 상태" 1줄, 44px 타깃, `aria-pressed`, `use:modal` 포커스 복귀·Esc, 삭제 확인 취소 시 무변경.
6. **S5 개인정보:** 질병 별도 동의 없음 → AI 코치 페이로드에 illness 미포함(여행·고도는 coach_consent 로 포함), 내보내기 체크박스 기본 포함·해제 시 제외.
7. 공통: 신규 파일 300줄 이하, `pytest tests/` 전체, `check_docs.py`, v1 체크인 화면 회귀(저장·표시 불변).

## 5. 결정됨(2026-10-11)
- **NEW-1** 신규 `context_episodes`·`race_calendar`(v38 가산) — 기간·자동/수동·확인 상태 표현.
- **NEW-2** v37 source CHECK 에 illness(+travel·altitude) 미리 포함 — 재생성 1회.
- **NEW-3** 질병만 단독 OR 트리거, 여행·고도는 support/context — 순서 pain > illness > checkin > crs > acwr > readiness.
- **NEW-4** 우선순위 필수(RC-2) — race-calendar.md 위임.
- **NEW-5** 대회 등록·수정 시 영향 미리보기 후 일괄 적용·일괄 되돌리기(RC-7) — race-calendar.md 위임.
- **NEW-6** 임계·창은 제안값으로 진행, 관찰 후 조정.
- **NEW-7** 상태 칩은 체크인 "+ 상태" 뒤에 접음.
- **NEW-8** RHR↑+HRV↓ 동시 시 "몸 상태 어때요?" 질문(진단 표현 금지).
- **NEW-9** 미확인 질병 에피소드는 stale 표시만, 종료는 사용자.
- **NEW-10** 무기한 보관 + 에피소드 단건 삭제 UI.
- **NEW-11** 내보내기 체크박스, 기본 포함.
- **NEW-12** 질병만 coach_consent 와 별도 동의 후 AI 전송, 여행·고도는 기존 동의.
- **NEW-13** 자동 후보 2일 무응답 시 dismissed.

## 6. 범위 밖 메모
- `today_service.py` 320줄 초과(규칙 위반) — 별도 분리 작업 필요.
- 고도·폭염에 따른 **페이스 목표 보정**(조정이 아닌 처방 변경)은 별도 설계.
- Strava `timezone` 텍스트가 `metric_store` 에 text 로 저장되는지(숫자 offset 아님) 구현 시 확인.

## 7. 동기화 중 발견한 충돌/확인 필요
- **NEW-12 별도 동의의 UI·철회 처리 미설계:** 동의를 묻는 위치·문구, 저장 위치(기존 `coach_consent` 저장소 확장 여부), 철회 시 이미 전송된 대화·요약의 처리, 철회 후 질병 신호가 들어간 조정 근거("왜?")를 AI 가 설명할 때 범위가 정해지지 않았다.
- **질병 동의가 AI 전송 범위에 미치는 영향:** 동의 없을 때 질병이 primary_trigger 인 조정 제안을 AI 코치가 받는 경우 트리거명·`signals_json` 을 가릴지(가리면 근거 없는 조정으로 보임)가 미정. `plan_adjustments.source='illness'` 자체가 건강 정보다.
- **NEW-10 단건 삭제 ↔ 조정 이력:** `plan_adjustments.signals_json`·source 에 남은 질병 사실을 에피소드 삭제 시 함께 지울지 미정(무기한 보관·삭제권과 이력 보존이 충돌).
- **NEW-11:** 사용자 데이터 전체 내보내기 기능이 아직 없다(`views_export.py` 는 활동 CSV 만) — 체크박스는 기능 신설과 함께 의미가 생긴다.
- **NEW-6 단일값 미정:** 결정이 제안 범위(시차 3h/4h, 창 h당 1일/고정 3일, 고도 1,500/2,000m, 적응 3/7일)를 그대로 승인해 구현 상수 1개씩이 정해지지 않았다. 귀국 역방향 창 적용 여부·고도 연속일(1/2일)·복귀 context 일수 N(NEW-9)도 표에 값이 없다.
- **NEW-3 순서 vs ADJ-15:** decisions-table 의 ADJ-15 순서에는 illness 가 없다 → adjustment-signals.md §3.8 동기화 필요. stale 상태 confirmed 질병이 계속 트리거인지(freshness 강등 여부)도 미정.
- **v37 source CHECK 값 합의:** 이 문서(illness·travel·altitude)와 race-calendar.md(`race`)가 각각 v37 확장을 요구 — adjustment-signals.md v37 설계에 합쳐 반영 필요. travel·altitude 는 트리거가 아니므로(NEW-3) 실제 source 로 쓰이지 않는 값이 된다.
- **NEW-7 ↔ NEW-13 해석:** 확인 프롬프트를 접힘 밖에 둔 것(§2.5)은 2일 무응답 dismissed 가 공정하려면 필요하다는 이 문서의 해석이다 — 상태 칩만 접는다는 결정 범위와 맞는지 product 확인.
