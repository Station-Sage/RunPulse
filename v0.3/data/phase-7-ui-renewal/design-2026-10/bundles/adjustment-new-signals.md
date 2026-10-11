# 조정 제안 신규 수집 신호 4종 (adjustment-new-signals)

> 작성 2026-10-11 · 상태: 설계 확정(NEW-1~26·V1-1 결정 반영, 구현 전. 문구는 TXT-1 미확정) · 관련: ADJ-10(신규 수집 착수 확정), ADJ-1·2·4·13·15·17, NEW-1~26, V1-1, TXT-1, RC-1~19(`bundles/race-calendar.md`), `bundles/adjustment-signals.md` §3.2~3.9, `patterns/timezone-display.md`(TZ), 접근성 계약(A11Y)
> 전제: adjustment-signals 의 `signals_json`(role: trigger/support/counter/hold/context, freshness) 과 `collect()` 수집기 구조를 그대로 쓴다. 여기서는 질병·여행·고도의 **입력·저장·화면·신호화**를 다룬다. B/C 레이스 우선순위의 저장·화면·계획 반영은 `race-calendar.md` 가 원천이며 이 문서는 신호 연결만 적는다.
> 변경 이력: 2026-10-11 초안 · 2026-10-11 설계서 동기화(NEW-1~13 확정 반영) · 2026-10-11 설계서 동기화(NEW-10 삭제 시 조정 이력 익명화, NEW-11 전체 내보내기 포함 → `data-export.md` 링크, NEW-12 1회 별도 동의·철회·일반화, TZ-1 '오늘' 헬퍼, v38 롤백 문구 보정, §5 축약·§7 모호점 정리) · 2026-10-11 2차 동기화(NEW-14 동의 이력 별도 테이블 스키마 초안, NEW-15 철회 즉시 일반화, NEW-16 severity 미포함, NEW-17 재질문 없음+안내 문구 위치, NEW-18 여행·고도 삭제 시 이력 불변, NEW-19 stale 질병 재확인 요청 제안, NEW-20 NEW-6 상수 표, ADJ-17 주 트리거 순서, 유니크 인덱스 충돌 사실 확인) · 2026-10-11 3차 동기화(NEW-21 `illness_consent_events` v38 합류, NEW-22 재확인 7일·Today 배너+체크인 프롬프트 병행·대기 중 트리거 유지, NEW-23 질병 삭제 시 `reasons_json` 익명화·질병 단독 근거 proposed 다음 조회 철회·저장된 AI 요약 삭제(코드 사실 grep), NEW-15·17·19 문구는 TXT-1로 구현 단계 제시) · 2026-10-11 4차 동기화(NEW-24 `ai_cache` 질병 근거 표지·표지 없는 과거분은 전체 삭제·commit 없는 삭제 헬퍼, NEW-25 질병 삭제 시 `chat_messages` 삭제 여부 질문 단계·API, NEW-26 `summary` 칩 질병 라벨 → '컨디션 신호', V1-1 v1 체크인 서술 제거)

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
- **스키마 순서(확정):** v37 = adjustment-signals 의 `plan_adjustments` 재생성(백업 복원만 롤백)이며 **source CHECK 에 `illness`·`travel`·`altitude` 를 미리 포함**(NEW-2, 재생성 1회로 끝냄). v38 = `context_episodes`·`race_calendar`·`illness_consent_events`(NEW-21 a) CREATE 만 하는 가산 마이그레이션(롤백 = DROP, 단 v39 적용 전까지만 — v39 `goals.race_id` 이후는 전진 전용, `race-calendar.md` §4·`adjustment-signals.md` §3.9). v39 = goals.race_id(race-calendar.md 소관).
- **'오늘' 기준(TZ-1 추가 결정):** 이 문서의 '오늘'(신선도 fresh/partial/stale 판정, 자동 후보 2일 무응답, 복귀 창·도착 후 창·적응 창의 day_n)은 `reference_today(conn)`(사용자 최근 활동의 현지 시간대 기준 날짜, 활동 없으면 서버 로컬 날짜) 하나로 구한다. 정의는 `patterns/timezone-display.md` §2.4.

### 2.1 질병(illness)
- **입력:** 체크인(QuickInput) "+ 상태" 펼침 안의 `아파요` 토글(NEW-7). 켜면 한 줄 보조 선택(선택 안 해도 저장됨): 정도 2단계 + (선택) 증상 위치 칩(목 위/목 아래·전신 — "neck check" 관행). 진행 중 에피소드가 있으면 다음 날 체크인 상단에 "어제 아팠어요 — 계속/나았어요" 1탭 프롬프트. 나았어요 → `end_date`.
- **자동 질문(NEW-8):** 진단·자동 생성은 하지 않는다. 안정시 심박 상승+HRV 하락이 동시에 있으면 "몸 상태 어때요?" 질문만 띄운다(진단 표현 금지, 임계는 adjustment-signals §3.5 안정시 심박 후보와 공유). 답이 "아파요"일 때만 user 에피소드 생성. `note` 키워드 파싱은 하지 않는다.
- **첫 입력 시 별도 동의(NEW-12):** `아파요`를 처음 켤 때 1회만 AI 코치 전송 동의를 따로 묻는다(§2.6). 동의 여부와 무관하게 에피소드 저장·로컬 조정은 그대로 동작.
- **신호화(NEW-3):** `{"signal":"illness","value":severity,"detail":{"episode_id","day_n","site"}}`(`episode_id`는 NEW-10 단건 삭제 시 익명화 대상을 찾는 키). confirmed 질병은 통증처럼 **단독 OR 트리거**(ADJ-13 혼합 규칙의 OR 쪽). `primary_trigger` 순서는 **pain > illness > checkin > race > crs > acwr > readiness**(ADJ-17, `adjustment-signals.md` §3.8). 동시에 BOOST hold.
- **신선도·종료(NEW-9):** 오늘 체크인에서 확인 = fresh, 마지막 확인 1~2일 전 = partial, 그 이상 미확인 진행 중 = stale 표시. **자동 종료 없음 — 종료는 사용자만.**
- **stale 재확인 요청(NEW-19 c, NEW-22 b):** stale인 confirmed 질병은 `last_confirmed_date`로부터 **7일**(상수 `ILLNESS_RECONFIRM_DAYS = 7`, '오늘' = `reference_today`)이 지나면 재확인을 요청한다. **위치는 둘 다:** 체크인 상단 Level 0 프롬프트를 재확인 문구로 바꿔 재사용하고, 체크인을 열지 않는 사용자를 위해 **Today 상단 1줄 배너를 병행**한다(같은 응답 버튼 계속/나았어요, 어느 쪽에서 답해도 둘 다 사라짐). '계속' → `last_confirmed_date` 갱신(fresh), '나았어요' → `end_date`. **재확인 대기·무응답 동안 트리거 지위는 유지**한다(stale 표시는 그대로, 강등·자동 종료 없음 — NEW-9). 문구는 TXT-1로 구현 단계에서 후보 제시(초안 "아직 아파요? 마지막 확인 N일 전", 미확정).
- **복귀:** `end_date` 이후 N일은 context(`detail.returning`) — 복귀 첫 Q-day 감량 근거 후보(N 값은 §7).

### 2.2 여행·시간대(travel)
- **자동 감지(부분):** 활동별 `metric_store.timezone_offset`(Garmin 초 단위 offset, Strava 는 `"(GMT+09:00) Asia/Seoul"` 텍스트 → 파서 필요)을 날짜순으로 보고 **홈 오프셋(최근 28일 최빈값) 대비 |Δ| ≥ 임계** 인 첫 활동일에 `candidate` 생성(`detail: {from_offset, to_offset, delta_h, direction:"east|west", evidence_activity_ids}`). 오프셋 해석은 `timezone-display.md` 의 `tz_source` 체인(교차 소스 `tz_peer.offset_sec` 포함)을 그대로 재사용하고 별도 해석기를 만들지 않는다. 추정 `fallback` 등급은 감지에서 제외(순환 추정 방지). 한계: 활동 없는 이동일·시간대 변화 없는 장거리 이동은 감지 불가 → 수동.
- **수동 입력:** "+ 상태" 안의 `이동·시차` 토글, 시차 크기 선택(없음/1~3h/4h+) 1단계. 자동 후보는 확인 프롬프트 "시차 +7시간 감지 — 맞아요?"(확인/아니에요)로 묻는다.
- **신호화(NEW-3):** `{"signal":"travel","value":delta_h,"detail":{"day_n","direction","origin"}}`. 트리거 아님 — 도착 후 창 동안 BOOST hold + 하향 support, 창 밖 context. 임계·창은 §2.7 상수 표(NEW-20: 승인 범위 중간값 고정)를 쓰고 관찰 후 조정. 신선도: 근거 활동이 오늘−1일 이내 = fresh, 창 안이지만 근거 오래됨 = partial. 귀국(홈 오프셋 복귀) 감지 시 기존 travel `end_date` 갱신.

### 2.3 고도(altitude)
- **자동 감지(부분):** 활동 `activity_streams.altitude_m` 중앙값(스트림 없으면 감지 생략). 홈 고도(최근 28일 활동 중앙값의 중앙값) 대비 **절대 고도 ≥ 임계 그리고 홈+Δ ≥ 임계** 일 때 `candidate`. 외부 고도 API 호출 금지. 한계: 기압계 오차, 실내·트레드밀, 산악 트레일 당일치기 오탐.
- **수동 입력:** "+ 상태" 안의 `고지대` 토글 + (선택) 대략 고도 3단계(1,500 미만/1,500~2,500/2,500+). 자동 후보는 "고도 2,300m 활동 감지 — 지금 고지대에 있어요?".
- **신호화(NEW-3):** `{"signal":"altitude","value":altitude_m,"detail":{"day_n","band","origin"}}`. 트리거 아님 — 적응 창 동안 BOOST hold + 강도 세션 하향 support, 창 밖 context. 임계·창은 §2.7 상수 표(NEW-20)를 쓴다. 신선도: 오늘/어제 활동 근거 또는 오늘 체크인 확인 = fresh, 그 외 partial.

### 2.4 B/C 레이스 우선순위 → `race-calendar.md` 위임
- 저장(`race_calendar`, 우선순위 A/B/C 필수 — NEW-4·RC-2), 등록·수정 시트, 계획 반영(영향 미리보기 후 일괄 적용·일괄 되돌리기 — NEW-5·RC-7), `b_race_week()` 재사용은 모두 `race-calendar.md` 가 원천이다.
- 이 문서의 몫은 신호 연결뿐: adjustment-signals §3.4 `race_plan` 수집기의 `detail.priority` 를 race_calendar 값으로 채운다(`unknown` 상태 없음). 창 길이·추가 대회 recovery trigger 는 기존 D12 그대로.

### 2.5 화면(모바일 375px, 최소 입력 부담)
- **체크인(QuickInput, 156줄, NEW-7):** 피로·통증 아래 **"+ 상태" 링크 1개**만 기본 노출, 누르면 칩 1행(아파요 · 이동·시차 · 고지대) 펼침. 전부 기본 비선택, 펼치지 않아도 기존 저장 동작 불변. 칩을 켠 경우에만 보조 1행.
- **확인 프롬프트(Level 0):** 진행 중 에피소드("어제 아팠어요 — 계속/나았어요"), stale 질병 재확인(NEW-22, Today 배너 병행), 자동 후보("시차 +7시간 감지 — 맞아요?"), NEW-8 질문("몸 상태 어때요?")은 접힘과 무관하게 체크인 상단 1줄로 보인다(NEW-13 의 2일 무응답 판정이 사용자가 본 적 없는 후보에 적용되지 않게).
- **에피소드 목록·단건 삭제(NEW-10·18):** 체크인 "+ 상태" 펼침 하단 "기록 보기" → 에피소드 목록 시트(kind·기간·출처). 행마다 삭제 버튼 → 삭제 확인 대화상자. 질병 에피소드 삭제 확인에는 조정 이력 익명화·AI 요약 삭제를 함께 안내(§2.6 NEW-23, 문구 제안: "관련 조정 기록과 AI 요약에서 아팠던 기록도 지워요. 조정 기록 자체는 남아요", 미확정). 여행·고도 에피소드 삭제는 조정 이력을 바꾸지 않으므로 그 안내를 붙이지 않는다(NEW-18).
- **질병 삭제 시 코치 대화 삭제 질문(NEW-25 c):** 질병 에피소드 삭제 확인 대화상자 안에 **코치 대화(`chat_messages`)도 삭제할지 묻는 단계**를 둔다. 제안: 같은 대화상자 안의 선택 항목으로 두고 '삭제'를 누를 때 선택값(`delete_chat: bool`)을 함께 보낸다 — 별도 2단 대화상자 여부·기본 선택값은 결정에 없어 product 확인(§7). 여행·고도 삭제에는 묻지 않는다. 문구는 TXT-1로 구현 단계에서 후보 제시(미확정). 삭제 범위(전체 대화/특정 스레드·기간)는 §7 열린 질문.
- **질병 별도 동의(NEW-12·17):** 첫 `아파요` 입력 직후 1회 시트(`use:modal`) — 동의/동의 안 함. **안내 문구 위치(NEW-17):** 이 시트 본문 하단, 두 버튼 바로 위에 한 줄(초안 "동의하지 않아도 나중에 설정 > AI 코치에서 언제든 켤 수 있어요") — 문구는 TXT-1로 구현 단계에서 후보 제시(미확정). '동의 안 함'을 고르면 다시 묻지 않는다(이후 질병 입력에서 시트 없음). 설정 화면(AI 코치 설정)에 같은 항목의 토글과 철회 안내(초안 "철회하면 지금 대화를 포함해 이후 메시지부터 보내지 않아요. 이미 보낸 내용은 되돌릴 수 없어요", NEW-15, TXT-1 미확정). 접근성 계약 준수: 시트·대화상자는 `use:modal`(포커스 가두기·Esc·복귀), 터치 타깃 44px(A11Y-2), 칩 `aria-pressed`, 포커스 링 2px(A11Y-8).
- **조정 카드 "왜?"(Level 1~2):** "여행 3일째 (시차 +7h, 자동 감지·확인됨)"처럼 의미 먼저 + 괄호 값·출처. 질병 문구는 진단 표현 금지. 표시 문구는 adjustment-signals D7 과 함께 맞춘다.
- v1 화면·경로: 일몰 예정(V1-1), 고려하지 않음.

### 2.6 개인정보·민감도(NEW-10~12 확정)
- 질병 = 건강 정보, 여행·고도 = 위치 추정 가능 정보. 저장은 kind·날짜·정도·시차/고도 **수치만**(위경도·지명 저장 안 함; 근거는 activity id 참조).
- **보존(NEW-10):** **무기한 보관**(추세·재발 분석). 사용자가 에피소드 단건 삭제 가능(§2.5) — 삭제는 행 삭제.
- **여행·고도 삭제(NEW-18 c):** `context_episodes` 행만 지우고 `plan_adjustments`(`signals_json`·`reasons_json`·proposed 행 포함)와 AI 요약은 **바꾸지 않는다**. 아래 NEW-10·NEW-23 익명화·철회·삭제는 **질병에만** 적용된다.
- **단건 삭제 시 조정 이력 익명화(NEW-10 추가 결정):** 질병 에피소드 삭제와 같은 트랜잭션에서 `plan_adjustments`를 고친다 — ① `signals_json`에서 그 에피소드의 질병 항목(`signal='illness'`, `detail.episode_id` 일치) 제거 ② 그 결과 해당 행의 `source='illness'`이면 `'readiness'`로 치환 ③ **`reasons_json`의 질병 칩 익명화(NEW-23), `summary` 칩의 질병 라벨은 '컨디션 신호'로 치환(NEW-26)** ④ **저장된 AI 요약 삭제(NEW-23, 대상 식별은 NEW-24 표지 규칙)** ⑤ **사용자가 대화 삭제를 고른 경우에만 `chat_messages` 삭제(NEW-25)** ⑥ 나머지(`after_json`·decision·rev·조정 제안의 휴식·감량 이력)는 유지. decision 상태와 무관하게 적용(`adjustment-signals.md` §3.1 불변식·§3.11 동결의 예외). `context_episodes.delete_episode(conn, id, *, delete_chat=False)`가 담당, 반환에 익명화 행 수·삭제한 AI 요약 수·삭제한 대화 메시지 수(여행·고도는 항상 0, `delete_chat` 무시).
- **NEW-23 상세 (코드 사실 grep 2026-10-11):**
  - **`reasons_json`:** `plan_adjustments.reasons_json TEXT NOT NULL DEFAULT '[]'`, 형식 `[{key, label, value?, target?}]`(`db_schema_v31.py:17`, 근거 칩 원천). 현재 쓰는 곳은 `plan_adjustment_service._build`(`key='summary'`·`'readiness'`), `plan_move.py:129`, `plan_advisory.py:155`이고 질병 칩은 아직 없다. 설계: 질병 칩은 `key='illness'`와 `episode_id`를 담아 만들고(adjustment-signals 칩 생성 쪽), 삭제 시 `episode_id`가 일치하는 칩을 일반 라벨 '컨디션 신호'(NEW-16과 같은 라벨)로 바꾸고 `value`·`episode_id`를 뺀다.
  - **`summary` 칩(NEW-26 a):** `key='summary'` 칩은 자유 텍스트(`adjustment_reason`)라 `episode_id`가 없다. 익명화 대상 행(위 ①에서 해당 에피소드 질병 항목이 제거된 행)의 `summary` 칩에 질병 라벨이 들어 있으면 칩 문구를 '컨디션 신호'로 치환한다(칩 항목 자체는 남김). NEW-23(`reasons_json`도 익명화)·NEW-16(라벨 '컨디션 신호')과 같은 라벨이다. 질병 라벨 판정 방식(생성 시 질병 문구 상수에서 만든 라벨과 일치 비교 등)은 구현 시 확정 — 자유 텍스트 키워드 파싱은 하지 않는 것을 제안(§7).
  - **질병만 근거였던 proposed 행 철회:** 삭제 트랜잭션은 철회하지 않는다. **다음 조회 때**(ADJ-6 재기록 경로) `decision='proposed'`이고 익명화 후 `signals_json`에 `role='trigger'` 항목이 하나도 남지 않은 행을 `decision='reverted'`로 바꾼다(질병이 유일한 트리거였던 행만 해당, 다른 트리거가 남은 행은 그대로). 코드 사실: 현재 `ensure_proposal`은 새 제안이 없으면 기존 proposed 행을 그대로 반환한다(`plan_adjustment_service.py:101-102`) — 이 철회 경로는 v37 재기록 설계(adjustment-signals 소관)에 추가해야 한다.
  - **AI 요약 저장 위치:** `ai_cache` 테이블(`src/ai/ai_cache.py`, 컬럼 `tab, cache_key, content_json, generated_at, data_fingerprint`, `UNIQUE(tab, cache_key)`, 앱 DB와 같은 `conn`으로 접근·`_ensure_table`로 지연 생성). 확인된 탭: `today_narrative`(key `{month_start}:{date}`, `services/_narrative.py:161-168`), `today_narrative_warm`(key = 날짜, `services/narrative_warm.py`), `ai_message.get_card_ai_message` 경유 카드 탭(key = 활동 ID·기간 등). 코치 대화는 `chat_messages`(`id, role, content, chip_id, ai_model, thread_id, evidence_json, created_at`, `db_setup.py:397-406`)·`chat_threads`에 따로 저장된다.
  - **같은 트랜잭션 범위:** `context_episodes` DELETE + `plan_adjustments`의 `signals_json`·`source`·`reasons_json` UPDATE + `ai_cache` DELETE(+ `delete_chat=True`면 `chat_messages` DELETE, NEW-25)를 한 트랜잭션으로 묶는다(모두 같은 SQLite 연결). 코드 사실: `ai_cache.invalidate()`(`:97-104`)·`set_cached()`·`narrative_warm` 저장은 내부에서 `conn.commit()`을 부르므로 재사용하면 트랜잭션이 쪼개진다 → **commit 없는 삭제 헬퍼를 `ai_cache.py`에 추가**(예: `delete_illness_marked(conn) -> int`, 아래 NEW-24 규칙으로 대상 선택, `conn.commit()` 호출 없음)해 `delete_episode`가 부른다. `chat_messages` 삭제도 commit 없이 같은 연결에서 실행(기존 대화 삭제 함수가 commit 하면 같은 이유로 재사용하지 않음, 구현 시 grep). proposed 철회는 다음 조회 시점이라 이 트랜잭션 밖이다.
  - **AI 요약 삭제 대상 식별(NEW-24 c):** 현재 `ai_cache` 행에는 `episode_id`·질병 여부 표지가 없다(key는 날짜·활동·기간 단위). 그래서 — ① **앞으로 생성하는 `ai_cache` 행에 질병 근거 표지를 단다**: 생성 시 AI 컨텍스트에 질병 신호가 들어갔으면 표지(질병 포함)를 기록 ② 질병 에피소드 삭제 시 **표지된 행만 삭제** ③ **표지 도입 이전 생성분은 표지가 없으므로 해당 사용자 `ai_cache` 전체 삭제**로 처리(다음 조회에서 재생성). 스키마 변경: `ai_cache`에 표지 컬럼(또는 키) 추가 — 코드 사실: `ai_cache`는 `db_setup.py`가 아니라 `ai_cache._ensure_table`(`:151-167`)이 지연 생성하고 `data_fingerprint`도 같은 함수의 `ALTER TABLE … ADD COLUMN`(실패 무시)로 붙였다 → 같은 패턴 재사용을 제안. 표지를 쓰는 곳(grep 2026-10-11): `set_cached`(`ai_cache.py:55`, 호출자 `ai_message.py:234`·`_narrative.py:168`이 표지 값을 넘김)와 `narrative_warm.py:38`의 직접 INSERT. **표지 방식 세부(열린 질문, §7):** 컬럼 vs `cache_key` 접미 표지, 값 형태(불리언 / 근거 `episode_id` 목록), '표지 도입 이전 행'과 '질병 없음으로 생성된 행'의 구분(예: NULL = 도입 이전, 0 = 질병 없음).
  - **유니크 인덱스 확인 항목(코드 사실, 해결안 미결정):** `ux_plan_adj_live`는 `(workout_id, date, source) WHERE decision IN ('proposed','accepted')`(`db_schema_v31.py:29-30`)라 ②의 UPDATE는 같은 workout·date에 live `readiness` 행이 이미 있으면 유니크 위반이다. 현재 코드는 자동 행이 `source='crs'` 하나이고 `ensure_proposal`이 날짜당 live 자동 행을 1개로 유지(새 제안 전 기존 proposed를 reverted)하므로(`plan_adjustment_service.py:83-121`) 지금은 충돌 경로가 없다 — v37 이후 live `illness`·`readiness` 행 공존 가능 여부에 달려 있으며 §4 S0에서 확인한다.
- **내보내기·백업(NEW-11):** 사용자 데이터 **전체 내보내기 기능 신설을 이번 작업에 포함**(에피소드·대회 캘린더 체크박스, 기본 포함). 설계는 `bundles/data-export.md`가 원천 — 이 문서에 복제하지 않는다.
- **AI 코치 전송(NEW-12):** 여행·고도는 기존 `coach_consent` 로 전송. 질병은 `coach_consent` 와 **별도 동의**:
  - 동의 시점: 질병을 **처음 입력할 때 1회**(§2.5). 이후 다시 묻지 않음 — '동의 안 함'을 고른 사용자도 재질문 없이 설정에서만 켠다(NEW-17 a, 시트 안내 문구는 §2.5).
  - 저장(NEW-14 c): **별도 테이블에 동의·철회 이력을 보존**한다(아래 스키마 초안). 현재 상태 = 가장 최근 행, '처음 입력' 판정 = 행 0건.
  - 철회: 설정에서 언제든. **철회 즉시, 진행 중인 대화를 포함해 이후 메시지부터** 질병을 일반화해 보낸다(NEW-15 a — 컨텍스트 빌더가 메시지마다 현재 동의 상태를 읽음, 대화 단위 캐시 금지). **이미 전송된 메시지는 되돌릴 수 없음**을 철회 화면에서 고지.
  - 동의 없음(미동의·철회): AI 코치에 질병을 보내지 않고 **'컨디션 신호'로 일반화**해 보낸다 — 컨텍스트 빌더가 `illness` 신호를 일반 `condition`(라벨 '컨디션 신호')으로 바꾸고 **신호 있음만 보낸다: 정도(severity·`value`)와 질병 고유 detail(증상 위치·`day_n` 등)은 모두 뺀다**(NEW-16 a). `plan_adjustments.source='illness'`도 AI 전송본에서는 같은 라벨로 바꾼다(저장값·앱 안 "왜?"는 그대로). 그래서 조정 근거가 비지 않는다.
  - 질병 정보가 AI 컨텍스트로 들어가는 경로(조정 근거 `coach_evidence`, 체크인 AI 컨텍스트 등)는 한 함수(`redact_illness_for_ai`)를 거친다. 경로 목록은 구현 시 grep.
  - **스키마(NEW-14, v38 합류 — NEW-21 a):** `src/db_schema_v38.py`의 가산 DDL에 함께 넣는다(롤백 = DROP, v39 적용 전까지만 — §2.0과 같은 규칙).
    ```sql
    CREATE TABLE IF NOT EXISTS illness_consent_events (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        action     TEXT NOT NULL CHECK (action IN ('grant','decline','revoke')),
        via        TEXT NOT NULL CHECK (via IN ('first_input','settings')),
        created_at TEXT NOT NULL DEFAULT (datetime('now'))   -- 무표기 UTC(기록 시각)
    );
    ```
    추가 전용(UPDATE·DELETE 없음). 동의 = 최신 행 `action='grant'`. `decline`은 첫 입력 시트의 '동의 안 함'(재질문 방지 근거), `revoke`는 설정에서의 철회, 설정에서 다시 켜면 `grant`(via `settings`). 기존 `coach_consent`는 수정하지 않는다.

### 2.7 NEW-6 구현 상수(NEW-20 a — 승인 범위의 중간값 하나로 고정)
| 상수(제안 이름) | 승인 범위(NEW-6) | 고정값 | 비고 |
|---|---|---|---|
| `TRAVEL_TZ_DELTA_H` 시차 임계 | 3h / 4h | **3.5h**(12,600초) | 오프셋은 15분 단위라 3.5h 비교 자체는 가능. 단 정시 시간대끼리는 사실상 4h와 같아진다 — **구현 시 값 확인 필요** |
| `TRAVEL_WINDOW_DAYS` 도착 후 창 | 시차 h당 1일 / 고정 3일 | **`ceil((abs(Δh) + 3) / 2)`일**(두 방식의 중간: Δ7h → 5일, Δ4h → 4일) | 범위가 수치가 아닌 두 공식이라 중간을 공식으로 제안 — **구현 시 값 확인 필요** |
| `ALTITUDE_THRESHOLD_M` 고도 임계 | 1,500 / 2,000m | **1,750m** | 정수, 그대로 사용 |
| `ALTITUDE_ADAPT_DAYS` 적응 창 | 3 / 7일 | **5일** | 정수, 그대로 사용 |
| 고도 연속일 조건 | 1일 / 2일 | 미정 | 정수 중간값이 없고 NEW-6 결정 문구에도 값이 없다(§7) |
| 귀국 역방향 창 적용 여부 | 적용/미적용 | 미정 | NEW-6 결정 문구에 없음(§7) |
상수는 `context_autodetect.py`(감지)·`adjustment_signals_context.py`(창) 모듈 상수로 두고 설정화하지 않는다(NEW-20 a). 관찰 후 조정은 상수 수정으로 한다.

## 3. 변경 파일 표 (race_calendar 관련 파일은 `race-calendar.md` §변경 파일 표)
| 파일 | 신규/수정 | 내용 | 예상 줄 |
|---|---|---|---|
| `src/db_schema_v38.py` | 신규(공유) | `context_episodes`·`illness_consent_events`(NEW-14·21) CREATE(멱등, dry_run). race_calendar 부분은 race-calendar.md | ~65 |
| `src/db_setup.py` | 수정 | DDL·마이그레이션 호출(SCHEMA_VERSION 은 race-calendar.md v39 기준) | +15 |
| `src/db_schema_v37.py` | 수정 | source CHECK 에 `illness`·`travel`·`altitude` 포함(NEW-2) | +1 |
| `src/services/context_episodes.py` | 신규 | open/extend/close/confirm/dismiss/delete/list_active, 2일 무응답 dismissed(쓰기 예외 명시), '오늘'=`reference_today`, `delete_episode`의 질병 이력 익명화(NEW-10·23·26: `signals_json`·`source`·`reasons_json`(질병 칩·`summary` 칩 '컨디션 신호') + AI 요약 삭제(NEW-24) + `delete_chat` 선택 시 `chat_messages` 삭제(NEW-25), 같은 트랜잭션; 여행·고도는 이력 불변 NEW-18), stale 질병 재확인 대상 조회(NEW-19·22, `ILLNESS_RECONFIRM_DAYS=7`) | ~255 |
| `src/ai/ai_cache.py` | 수정 | `_ensure_table`에 질병 근거 표지 컬럼 추가(NEW-24, 기존 `ALTER … ADD COLUMN` 패턴), `set_cached` 표지 인자, commit 없는 삭제 헬퍼(표지된 행 + 표지 도입 이전 행이 있으면 전체 삭제, `delete_episode` 트랜잭션용). 표지 형태는 §7 | +30 |
| `src/ai/ai_message.py`, `src/services/_narrative.py`, `src/services/narrative_warm.py` | 수정 | 생성 컨텍스트에 질병 신호 포함 여부를 표지로 저장(NEW-24) | +각 3 |
| `src/services/plan_adjustment_service.py`(v37 재기록, adjustment-signals 소관) | 수정 | 다음 조회 때 트리거 없는 proposed 행 → `reverted`(NEW-23), 질병 칩에 `key='illness'`·`episode_id` | +15 |
| `src/services/context_autodetect.py` | 신규 | `home_offset`, `detect_tz_shift`(tz_source 체인 결과 소비), `detect_altitude`, `detect_illness_prompt`(순수) + 로더, §2.7 감지 상수 | ~175 |
| `src/services/adjustment_signals_context.py` | 신규 | illness(OR 트리거)/travel/altitude 수집기 → signal dict(freshness 포함) | ~140 |
| `src/services/adjustment_signals.py`(adjustment-signals 소관) | 수정 | `primary_trigger` 순서에 illness 삽입(전체 순서는 ADJ-17) | +3 |
| `src/api/routes_context.py` | 신규 | `GET/POST/PATCH/DELETE /api/context-episodes`(질병 DELETE는 `delete_chat` 불리언 수용 — 쿼리/본문 형태는 구현 시, NEW-25; 여행·고도는 무시) | ~125 |
| `src/api/routes_today.py` | 수정 | 체크인 응답에 active·candidate 에피소드·질문 플래그·stale 질병 재확인 플래그(NEW-22, Today 배너·체크인 프롬프트 공용) 동봉 | +18 |
| `frontend/src/routes/today/+page.svelte` | 수정 | stale 질병 재확인 1줄 배너(NEW-22, 계속/나았어요, 44px) | +20 |
| `src/services/illness_consent.py` | 신규 | NEW-12·14~17: `illness_consent_events` 추가 전용 기록(grant/decline/revoke), 현재 상태=최신 행, 첫 입력 여부=행 0건, `redact_illness_for_ai`(미동의 시 '컨디션 신호' 일반화, severity·detail 제외, 메시지마다 상태 조회) | ~100 |
| AI 컨텍스트 빌더(`coach_evidence.py`, 체크인 AI 컨텍스트 등, 구현 시 grep) | 수정 | 질병 경로를 `redact_illness_for_ai` 경유로 | +각 3 |
| 설정 화면(AI 코치 설정, 구현 시 grep) + `frontend/src/lib/components/IllnessConsentSheet.svelte` | 신규·수정 | 첫 입력 1회 동의 시트(버튼 위 '나중에 설정에서 동의 가능' 안내, NEW-17), 설정 토글·철회 고지 | ~85 / +20 |
| `src/utils/reference_day.py` | 신규(타 설계) | '오늘' 헬퍼 — `patterns/timezone-display.md` §2.4 소관 | TZ 참조 |
| 전체 내보내기 | 신규(타 설계) | NEW-11 — `bundles/data-export.md` §3 변경 파일 표 참조 | 참조 |
| `frontend/src/lib/components/ContextChips.svelte` | 신규 | "+ 상태" 접힘·칩 행·보조 행·확인 프롬프트 | ~160 |
| `frontend/src/lib/components/ContextEpisodeList.svelte` | 신규 | 에피소드 목록·단건 삭제(use:modal, 삭제 확인, 질병 삭제 시 코치 대화 삭제 여부 질문 NEW-25) | ~135 |
| `frontend/src/lib/components/QuickInput.svelte` | 수정 | ContextChips 삽입 | +10 |
| `frontend/src/lib/api*.ts`, `lib/types/index.ts` | 수정 | 클라이언트·타입 | +45 |
| tests: `test_db_schema_v38.py`(context·`illness_consent_events` 부분), `test_context_episodes.py`(NEW-22~26 포함), `test_ai_cache.py`(+, 표지 컬럼 추가 멱등·표지 저장·commit 없는 삭제), `test_context_autodetect.py`, `test_adjustment_signals_context.py`, `test_routes_context.py`, `test_illness_consent.py`; 프론트 `ContextChips.test.ts`, `ContextEpisodeList.test.ts`, `IllnessConsentSheet.test.ts` | 신규 | 함수마다 ≥1 | ~48개 |
| 문서: 해당 `__init__.py` docstring, `files_index`(재생성), ADR(에피소드 모델·민감정보·질병 별도 동의) | 수정 | | — |

## 4. 단계·검증
1. **S0 (v37 작업 전):** v37 source CHECK 값은 adjustment-signals.md §3.9 의 11값(`illness`·`travel`·`altitude`·`race` 포함)으로 합의됨 — 일정만 선행 의존. `illness_consent_events`는 v38 합류로 확정(NEW-21). **확인 항목:** v37 이후 `ensure_proposal` 설계에서 같은 workout·date에 live `illness`·live `readiness` 행이 공존할 수 있는지 — 공존 가능하면 NEW-10 ② UPDATE가 `ux_plan_adj_live`(`db_schema_v31.py:29-30`) 위반(§2.6, 해결안은 확인 후 결정). NEW-23 proposed 철회 경로를 v37 재기록 설계에 포함하는지, NEW-24 `ai_cache` 표지 형태(§7)를 함께 확정. 선행: `reference_day.py`(timezone-display.md 단계 5-1).
2. **S1 v38 + 서비스:** `context_episodes`·`illness_consent_events`(v38 같은 파일, NEW-21)·서비스. 검증: 빈 DB/운영 DB **사본** 마이그레이션, 재실행 멱등, CHECK 위반 거부(`action`·`via`), `PRAGMA integrity_check`, DROP 롤백(가산 테이블 3개, v39 적용 전).
3. **S2 자동 감지(순수 함수):** 픽스처 — Garmin offset 32400→-25200, Strava 텍스트, offset 결측, `tz_source=fallback` 제외, 고도 스트림 없음/1일 스파이크/연속일, RHR↑만·HRV↓만·동시(질문은 동시만). §2.7 상수 경계(시차 3.5h 미만/이상, 고도 1,750m 미만/이상, 도착 후 창 `ceil((abs(Δh)+3)/2)`일, 적응 창 5일). candidate 중복 생성 없음(같은 에피소드 extend), 생성 후 2일 무응답 → dismissed, 경계(정확히 2일, '오늘'=`reference_today` 주입).
4. **S3 신호화:** confirmed→role 후보, candidate→context 만; confirmed illness 단독으로 트리거 성립; travel·altitude 는 트리거 집합 불변(빈도 회귀); `primary_trigger` = pain > illness > checkin > race > crs > acwr > readiness(ADJ-17); freshness 경계(오늘/1~2일/stale), stale 질병이 자동 종료되지 않음, `last_confirmed_date`+7일 경계(6일 미노출·7일 노출, '오늘'=`reference_today` 주입)에서 체크인 프롬프트와 Today 배너 둘 다 노출, 한쪽 응답 시 둘 다 사라짐(NEW-22)·'계속' → fresh·'나았어요' → end_date, 재확인 대기·무응답 동안 트리거 유지(역할 불변); race priority 채움 회귀.
5. **S4 API·UI:** 칩 미선택 저장 = 기존 요청 본문과 동일(회귀), 에피소드 API 입력 검증(`server-input-origin-validation.md` 패턴), 삭제 후 목록·신호에서 사라짐, 375px — 접힘 시 카드 높이 증가 "+ 상태" 1줄, 44px 타깃, `aria-pressed`, `use:modal` 포커스 복귀·Esc, 삭제 확인 취소 시 무변경.
6. **S5 개인정보:** (NEW-12·17) 첫 질병 입력에만 동의 시트 1회, 시트에 '나중에 설정에서 동의 가능' 안내 노출, '동의 안 함' 후 두 번째 입력은 묻지 않음(`decline` 행 1건), 설정 토글로 나중에 동의 → `grant` 행; (NEW-14) 동의·철회·재동의가 행으로 누적되고 현재 상태 = 최신 행; 미동의·철회 → AI 코치 페이로드에 `illness`·`source='illness'` 문자열 없음, 대신 '컨디션 신호'(NEW-16: severity·`value`·detail 모두 없음), 여행·고도는 coach_consent 로 포함; (NEW-15) 대화 도중 철회 → 같은 대화의 다음 메시지부터 일반화, 철회 전 메시지 기록은 변경하지 않음; 동의 없이도 로컬 조정 트리거 동일. (NEW-10) 질병 에피소드 삭제 → 해당 `episode_id` 질병 항목만 `signals_json`에서 제거, `source='illness'`→`'readiness'`, `after_json`·decision·rev 불변, 다른 에피소드 항목 불변, 한 트랜잭션(중간 실패 시 둘 다 롤백). (NEW-23) 질병 삭제 → `reasons_json`의 해당 `episode_id` 질병 칩만 일반 라벨로 바뀜, 같은 트랜잭션에서 `ai_cache` 대상 행 삭제(중간 실패 시 에피소드·이력·캐시 모두 롤백, commit 헬퍼 미사용 단언), 질병이 유일한 트리거였던 proposed 행은 다음 조회에서 `reverted`·다른 트리거가 남은 행은 유지·accepted 행은 철회 안 함. (NEW-26) 익명화 대상 행의 `summary` 칩 질병 라벨 → '컨디션 신호'(칩 개수 불변), 익명화 대상이 아닌 행의 `summary` 칩 불변. (NEW-24) 표지 컬럼 추가 재실행 멱등, 질병 신호가 들어간 생성분만 표지, 삭제 시 표지된 행만 삭제·표지 안 된(질병 없음) 행 유지, 표지 도입 이전 행이 남아 있으면 `ai_cache` 전체 삭제, 삭제 헬퍼가 commit 하지 않음(트랜잭션 롤백 시 캐시 복원). (NEW-25) 질병 삭제 대화상자에 대화 삭제 질문 노출·여행·고도에는 없음, `delete_chat=false` → `chat_messages` 불변, `true` → 대상 대화 삭제가 같은 트랜잭션(중간 실패 시 롤백), 반환 개수 일치. (NEW-18) 여행·고도 에피소드 삭제 → `plan_adjustments` 전 행 바이트 단위 불변·`ai_cache` 불변. (NEW-11) 내보내기 검증은 `data-export.md` §4.
7. 공통: 신규 파일 300줄 이하, `pytest tests/` 전체, `check_docs.py`.

## 5. 결정 필요
- 결정 완료(표 참조: `decisions-table.md` NEW-1~26, 추가 결정 NEW-10·11·12, 연관 ADJ-13·15·17, RC-2·7, TZ-1, V1-1).
- 사용자 확정 대기 문구(TXT-1, 미확정): NEW-15 철회 고지, NEW-17 동의 시트 안내, NEW-19 재확인 프롬프트(§2.1·§2.5 초안), NEW-25 대화 삭제 질문(§2.5). 구현 단계에서 후보 문구를 제시하고 사용자가 확정한다.

## 6. 범위 밖 메모
- `today_service.py` 320줄 초과(규칙 위반) — 별도 분리 작업 필요.
- 고도·폭염에 따른 **페이스 목표 보정**(조정이 아닌 처방 변경)은 별도 설계.
- Strava `timezone` 텍스트가 `metric_store` 에 text 로 저장되는지(숫자 offset 아님) 구현 시 확인.

## 7. 동기화 중 발견한 모호점
- 해소(NEW-14·NEW-21): 질병 동의는 별도 테이블 `illness_consent_events`, v38 합류.
- 해소(NEW-15): 철회 즉시 이후 메시지부터 일반화.
- 해소(NEW-16): '컨디션 신호'에 severity 미포함.
- 해소(NEW-17): 다시 묻지 않음 + 시트 안 안내(문구 사용자 확정 대기).
- 해소(NEW-23·24·25·26): `reasons_json` 익명화 + 질병 단독 근거 proposed 다음 조회 철회 + 저장된 AI 요약 삭제(§2.6). 대상 식별은 NEW-24(앞으로 생성분 표지, 과거분은 전체 삭제), 대화는 NEW-25(사용자에게 묻기), `summary` 칩은 NEW-26('컨디션 신호' 치환).
- **열린 질문(NEW-24 표지 방식):** 컬럼 vs `cache_key` 접미 표지, 값 형태(불리언/`episode_id` 목록 — 목록이면 다른 질병 에피소드 표지 행은 남길 수 있음), '도입 이전(NULL)'과 '질병 없음(0)' 구분. 또 "해당 사용자 `ai_cache` 전체 삭제"는 단일 사용자 DB(`ai_cache`에 사용자 컬럼 없음)에서 테이블 전체 삭제가 되는데, 표지 도입 이전 행이 하나라도 남아 있을 때 표지 없음(질병 없음) 신규 행까지 지울지, 도입 이전 행만 지울지는 결정 문구로 갈리지 않는다(설계는 '전체'로 적음).
- **열린 질문(NEW-25):** 대화 삭제 범위 — 전체 `chat_messages`/에피소드 기간에 생성된 메시지/해당 스레드(`thread_id`) 단위인지, 빈 스레드가 된 `chat_threads` 행 처리, 질문 UI가 같은 대화상자의 선택 항목인지 2단 대화상자인지와 기본 선택값. 문구는 TXT-1.
- **열린 질문(NEW-26):** `summary` 칩 자유 텍스트에서 '질병 라벨'을 판정하는 방법(생성 시 질병 문구 상수와 일치 비교 제안, 키워드 파싱 미채택 제안). 질병 문구를 생성 단계에서 `summary`에 넣지 않으면 이 경로 자체가 불필요해지는지는 adjustment-signals 칩 생성 설계와 함께 확인.
- 해소(NEW-18·NEW-23): 여행·고도 삭제 시 이력 변경 없음, 질병만 trigger였던 proposed 행은 다음 조회 때 철회.
- NEW-10 `illness`→`readiness` 치환과 유니크 인덱스: 코드상 현재는 충돌 경로 없음, v37 이후 live 행 공존 가능 여부에 달림 — §2.6·§4 S0 확인 항목(해결안 미결정).
- TZ-1 추가 결정은 대회 날짜 필드를 열거한다. 에피소드 신선도·2일 무응답·체크인 `input_date`에 같은 헬퍼를 쓰는 것은 이 문서의 적용 해석이다.
- 해소(NEW-20): §2.7 상수 표. 남은 부분: 시차 3.5h·도착 후 창 공식은 구현 시 값 확인 필요, 귀국 역방향 창 적용 여부·고도 연속일(1/2일, 정수 중간값 없음)·복귀 context 일수 N(NEW-9)은 값 미정.
- 해소(NEW-19·NEW-22): 7일, 체크인 프롬프트 + Today 배너 병행, 대기 중 트리거 유지. 문구는 TXT-1.
- NEW-2 로 v37 CHECK 에 들어간 `travel`·`altitude` 는 NEW-3(트리거 아님)상 실제 source 로 쓰이지 않는다 — 결정 표가 "미사용 값 존재"를 감수한 것으로 해석.
- **NEW-7 ↔ NEW-13 해석:** 확인 프롬프트를 접힘 밖에 둔 것(§2.5)은 2일 무응답 dismissed 가 공정하려면 필요하다는 이 문서의 해석이다 — 상태 칩만 접는다는 결정 범위와 맞는지 product 확인.
