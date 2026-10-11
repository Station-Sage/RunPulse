# 조정 제안 신규 수집 신호 4종 (adjustment-new-signals)

> 작성 2026-10-11 · 상태: 설계 확정(NEW-1~34·V1-1·V1-2 결정 반영, 구현 전. 문구는 TXT-1 미확정) · 관련: ADJ-10(신규 수집 착수 확정), ADJ-1·2·4·13·15·17, NEW-1~34, V1-1·V1-2, TXT-1, RC-1~19(`bundles/race-calendar.md`), `bundles/adjustment-signals.md` §3.2~3.9, `patterns/timezone-display.md`(TZ), 접근성 계약(A11Y)
> 전제: adjustment-signals 의 `signals_json`(role: trigger/support/counter/hold/context, freshness) 과 `collect()` 수집기 구조를 그대로 쓴다. 여기서는 질병·여행·고도의 **입력·저장·화면·신호화**를 다룬다. B/C 레이스 우선순위의 저장·화면·계획 반영은 `race-calendar.md` 가 원천이며 이 문서는 신호 연결만 적는다.
> 변경 이력: 2026-10-11 초안 · 2026-10-11 설계서 동기화(NEW-1~13 확정 반영) · 2026-10-11 설계서 동기화(NEW-10 삭제 시 조정 이력 익명화, NEW-11 전체 내보내기 포함 → `data-export.md` 링크, NEW-12 1회 별도 동의·철회·일반화, TZ-1 '오늘' 헬퍼, v38 롤백 문구 보정, §5 축약·§7 모호점 정리) · 2026-10-11 2차 동기화(NEW-14 동의 이력 별도 테이블 스키마 초안, NEW-15 철회 즉시 일반화, NEW-16 severity 미포함, NEW-17 재질문 없음+안내 문구 위치, NEW-18 여행·고도 삭제 시 이력 불변, NEW-19 stale 질병 재확인 요청 제안, NEW-20 NEW-6 상수 표, ADJ-17 주 트리거 순서, 유니크 인덱스 충돌 사실 확인) · 2026-10-11 3차 동기화(NEW-21 `illness_consent_events` v38 합류, NEW-22 재확인 7일·Today 배너+체크인 프롬프트 병행·대기 중 트리거 유지, NEW-23 질병 삭제 시 `reasons_json` 익명화·질병 단독 근거 proposed 다음 조회 철회·저장된 AI 요약 삭제(코드 사실 grep), NEW-15·17·19 문구는 TXT-1로 구현 단계 제시) · 2026-10-11 4차 동기화(NEW-24 `ai_cache` 질병 근거 표지·표지 없는 과거분은 전체 삭제·commit 없는 삭제 헬퍼, NEW-25 질병 삭제 시 `chat_messages` 삭제 여부 질문 단계·API, NEW-26 `summary` 칩 질병 라벨 → '컨디션 신호', V1-1 v1 체크인 서술 제거) · 2026-10-11 5차 동기화(NEW-27·28 `ai_cache` 불리언 표지 + 항상 사용자 `ai_cache` 전체 삭제(표지는 삭제 판정 미사용, 컬럼 존치 재확인), NEW-29·30 삭제할 코치 대화 스레드 선택·기본 '삭제함'·전체 선택·빈 `chat_threads` 삭제, NEW-31 질병 칩 구조화 키 치환·과거 칩 전수 치환, NEW-32 고도 연속 1일, NEW-33 귀국 역방향 절반 창, NEW-34 복귀 context 질병 7일·여행·고도 3일, V1-2 v1 일몰 = UI·라우트)

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
- **복귀(NEW-34 c):** `end_date` 이후 **7일**(`ILLNESS_RETURN_CONTEXT_DAYS = 7`, §2.7)은 context(`detail.returning`) — 복귀 첫 Q-day 감량 근거 후보. 여행·고도는 3일(§2.2·§2.3).

### 2.2 여행·시간대(travel)
- **자동 감지(부분):** 활동별 `metric_store.timezone_offset`(Garmin 초 단위 offset, Strava 는 `"(GMT+09:00) Asia/Seoul"` 텍스트 → 파서 필요)을 날짜순으로 보고 **홈 오프셋(최근 28일 최빈값) 대비 |Δ| ≥ 임계** 인 첫 활동일에 `candidate` 생성(`detail: {from_offset, to_offset, delta_h, direction:"east|west", evidence_activity_ids}`). 오프셋 해석은 `timezone-display.md` 의 `tz_source` 체인(교차 소스 `tz_peer.offset_sec` 포함)을 그대로 재사용하고 별도 해석기를 만들지 않는다. 추정 `fallback` 등급은 감지에서 제외(순환 추정 방지). 한계: 활동 없는 이동일·시간대 변화 없는 장거리 이동은 감지 불가 → 수동.
- **수동 입력:** "+ 상태" 안의 `이동·시차` 토글, 시차 크기 선택(없음/1~3h/4h+) 1단계. 자동 후보는 확인 프롬프트 "시차 +7시간 감지 — 맞아요?"(확인/아니에요)로 묻는다.
- **신호화(NEW-3):** `{"signal":"travel","value":delta_h,"detail":{"day_n","direction","origin"}}`. 트리거 아님 — 도착 후 창 동안 BOOST hold + 하향 support, 창 밖 context. 임계·창은 §2.7 상수 표(NEW-20: 승인 범위 중간값 고정)를 쓰고 관찰 후 조정. 신선도: 근거 활동이 오늘−1일 이내 = fresh, 창 안이지만 근거 오래됨 = partial. 귀국(홈 오프셋 복귀) 감지 시 기존 travel `end_date` 갱신.
- **귀국 역방향 창(NEW-33 c):** 귀국(홈 오프셋 복귀)에도 시차 적응 창을 적용하되 **출국 창의 절반**(`TRAVEL_RETURN_WINDOW_DAYS`, §2.7)이다. 창 안 역할은 출국 창과 같다(BOOST hold + 하향 support, `detail.direction`은 귀국 방향, `detail.phase="return"` 제안). 창 기점은 귀국 활동일(`end_date`).
- **복귀 context(NEW-34 c):** `end_date` 이후 **3일**(`TRAVEL_ALTITUDE_RETURN_CONTEXT_DAYS = 3`)은 context(`detail.returning`). 귀국 역방향 창과 겹치는 날의 역할 우선(창의 hold·support 우선 제안)은 §7 열린 질문.

### 2.3 고도(altitude)
- **자동 감지(부분):** 활동 `activity_streams.altitude_m` 중앙값(스트림 없으면 감지 생략). 홈 고도(최근 28일 활동 중앙값의 중앙값) 대비 **절대 고도 ≥ 임계 그리고 홈+Δ ≥ 임계** 인 활동일이 **연속 1일 이상**(NEW-32 a — 1일 활동만으로도 후보 생성, 스파이크 제외 규칙 없음)이면 `candidate`. 외부 고도 API 호출 금지. 한계: 기압계 오차, 실내·트레드밀, 산악 트레일 당일치기 오탐.
- **수동 입력:** "+ 상태" 안의 `고지대` 토글 + (선택) 대략 고도 3단계(1,500 미만/1,500~2,500/2,500+). 자동 후보는 "고도 2,300m 활동 감지 — 지금 고지대에 있어요?".
- **신호화(NEW-3):** `{"signal":"altitude","value":altitude_m,"detail":{"day_n","band","origin"}}`. 트리거 아님 — 적응 창 동안 BOOST hold + 강도 세션 하향 support, 창 밖 context. 임계·창은 §2.7 상수 표(NEW-20)를 쓴다. 신선도: 오늘/어제 활동 근거 또는 오늘 체크인 확인 = fresh, 그 외 partial. 복귀: `end_date` 이후 **3일** context(`detail.returning`, NEW-34 c).

### 2.4 B/C 레이스 우선순위 → `race-calendar.md` 위임
- 저장(`race_calendar`, 우선순위 A/B/C 필수 — NEW-4·RC-2), 등록·수정 시트, 계획 반영(영향 미리보기 후 일괄 적용·일괄 되돌리기 — NEW-5·RC-7), `b_race_week()` 재사용은 모두 `race-calendar.md` 가 원천이다.
- 이 문서의 몫은 신호 연결뿐: adjustment-signals §3.4 `race_plan` 수집기의 `detail.priority` 를 race_calendar 값으로 채운다(`unknown` 상태 없음). 창 길이·추가 대회 recovery trigger 는 기존 D12 그대로.

### 2.5 화면(모바일 375px, 최소 입력 부담)
- **체크인(QuickInput, 156줄, NEW-7):** 피로·통증 아래 **"+ 상태" 링크 1개**만 기본 노출, 누르면 칩 1행(아파요 · 이동·시차 · 고지대) 펼침. 전부 기본 비선택, 펼치지 않아도 기존 저장 동작 불변. 칩을 켠 경우에만 보조 1행.
- **확인 프롬프트(Level 0):** 진행 중 에피소드("어제 아팠어요 — 계속/나았어요"), stale 질병 재확인(NEW-22, Today 배너 병행), 자동 후보("시차 +7시간 감지 — 맞아요?"), NEW-8 질문("몸 상태 어때요?")은 접힘과 무관하게 체크인 상단 1줄로 보인다(NEW-13 의 2일 무응답 판정이 사용자가 본 적 없는 후보에 적용되지 않게).
- **에피소드 목록·단건 삭제(NEW-10·18):** 체크인 "+ 상태" 펼침 하단 "기록 보기" → 에피소드 목록 시트(kind·기간·출처). 행마다 삭제 버튼 → 삭제 확인 대화상자. 질병 에피소드 삭제 확인에는 조정 이력 익명화·AI 요약 삭제를 함께 안내(§2.6 NEW-23, 문구 제안: "관련 조정 기록과 AI 요약에서 아팠던 기록도 지워요. 조정 기록 자체는 남아요", 미확정). 여행·고도 에피소드 삭제는 조정 이력을 바꾸지 않으므로 그 안내를 붙이지 않는다(NEW-18).
- **질병 삭제 시 코치 대화 삭제 질문(NEW-25 c·NEW-29 c·NEW-30 c):** 질병 에피소드 삭제 확인 대화상자 안에 **코치 대화도 삭제할지 묻는 단계**를 둔다. ① 선택 항목 "코치 대화도 삭제" — **기본값 '삭제함'**(프라이버시 우선, NEW-30) ② 켜져 있으면 그 아래에 **스레드 목록**(제목·마지막 메시지 시각, 기존 `GET /api/v1/coach/threads` → `coach_service.list_threads` 재사용)을 체크박스로 펼치고 **기본 전체 선택**(NEW-30) — 사용자가 지울 스레드를 고른다(NEW-29) ③ '삭제'를 누르면 선택한 스레드 id 목록(`chat_thread_ids`)을 함께 보낸다. '삭제 안 함'으로 끄거나 하나도 선택하지 않으면 빈 목록 = 대화 불변. 스레드가 0개면 이 단계를 숨긴다. 스레드 목록이 길 때의 스크롤·표시 상한은 구현 시 375px 기준으로 정한다. 여행·고도 삭제에는 묻지 않는다. 문구는 TXT-1로 구현 단계에서 후보 제시(미확정). 접근성: 체크박스 44px 타깃·라벨 연결, `use:modal` 안에서 포커스 순서 유지.
- **질병 별도 동의(NEW-12·17):** 첫 `아파요` 입력 직후 1회 시트(`use:modal`) — 동의/동의 안 함. **안내 문구 위치(NEW-17):** 이 시트 본문 하단, 두 버튼 바로 위에 한 줄(초안 "동의하지 않아도 나중에 설정 > AI 코치에서 언제든 켤 수 있어요") — 문구는 TXT-1로 구현 단계에서 후보 제시(미확정). '동의 안 함'을 고르면 다시 묻지 않는다(이후 질병 입력에서 시트 없음). 설정 화면(AI 코치 설정)에 같은 항목의 토글과 철회 안내(초안 "철회하면 지금 대화를 포함해 이후 메시지부터 보내지 않아요. 이미 보낸 내용은 되돌릴 수 없어요", NEW-15, TXT-1 미확정). 접근성 계약 준수: 시트·대화상자는 `use:modal`(포커스 가두기·Esc·복귀), 터치 타깃 44px(A11Y-2), 칩 `aria-pressed`, 포커스 링 2px(A11Y-8).
- **조정 카드 "왜?"(Level 1~2):** "여행 3일째 (시차 +7h, 자동 감지·확인됨)"처럼 의미 먼저 + 괄호 값·출처. 질병 문구는 진단 표현 금지. 표시 문구는 adjustment-signals D7 과 함께 맞춘다.
- v1 화면·경로: 일몰 예정(V1-1), 고려하지 않음. 일몰은 UI·라우트 일몰을 뜻하며 공유 파일·함수는 유지한다(V1-2 정정). 이 문서가 쓰는 공유 로직(`user_inputs` 저장 `today_service.save_checkin`, `coach_service.list_threads` 등)은 v2 서비스 계층에 있어 일몰 영향이 없다(grep 2026-10-11: `src/web`에서 `user_inputs`·`chat_threads` 직접 조회 없음).

### 2.6 개인정보·민감도(NEW-10~12 확정)
- 질병 = 건강 정보, 여행·고도 = 위치 추정 가능 정보. 저장은 kind·날짜·정도·시차/고도 **수치만**(위경도·지명 저장 안 함; 근거는 activity id 참조).
- **보존(NEW-10):** **무기한 보관**(추세·재발 분석). 사용자가 에피소드 단건 삭제 가능(§2.5) — 삭제는 행 삭제.
- **여행·고도 삭제(NEW-18 c):** `context_episodes` 행만 지우고 `plan_adjustments`(`signals_json`·`reasons_json`·proposed 행 포함)와 AI 요약은 **바꾸지 않는다**. 아래 NEW-10·NEW-23 익명화·철회·삭제는 **질병에만** 적용된다.
- **단건 삭제 시 조정 이력 익명화(NEW-10 추가 결정):** 질병 에피소드 삭제와 같은 트랜잭션에서 `plan_adjustments`를 고친다 — ① `signals_json`에서 그 에피소드의 질병 항목(`signal='illness'`, `detail.episode_id` 일치) 제거 ② 그 결과 해당 행의 `source='illness'`이면 `'readiness'`로 치환 ③ **`reasons_json`의 질병 칩 익명화(NEW-23), `summary` 칩의 질병 라벨은 구조화 키로 찾아 '컨디션 신호'로 치환(NEW-26·31)** ④ **저장된 AI 요약 삭제 = 해당 사용자 `ai_cache` 전체 삭제(NEW-23·28)** ⑤ **사용자가 선택한 코치 대화 스레드만 삭제(NEW-25·29·30) — 선택 스레드의 `chat_messages` 전부와, 그 결과 빈 스레드가 된 `chat_threads` 행** ⑥ 나머지(`after_json`·decision·rev·조정 제안의 휴식·감량 이력)는 유지. decision 상태와 무관하게 적용(`adjustment-signals.md` §3.1 불변식·§3.11 동결의 예외). `context_episodes.delete_episode(conn, id, *, chat_thread_ids: Sequence[int] = ())`가 담당(빈 시퀀스 = 대화 불변 — API 미지정 시 기본값, 화면 기본값은 전체 선택이라 화면이 목록을 채워 보냄), 반환에 익명화 행 수·삭제한 AI 요약(`ai_cache`) 행 수·삭제한 대화 메시지 수·삭제한 스레드 수(여행·고도는 항상 0, `chat_thread_ids` 무시).
- **NEW-23 상세 (코드 사실 grep 2026-10-11):**
  - **`reasons_json`:** `plan_adjustments.reasons_json TEXT NOT NULL DEFAULT '[]'`, 형식 `[{key, label, value?, target?}]`(`db_schema_v31.py:17`, 근거 칩 원천). 현재 쓰는 곳은 `plan_adjustment_service._build`(`key='summary'`·`'readiness'`), `plan_move.py:129`, `plan_advisory.py:155`이고 질병 칩은 아직 없다. 설계: 질병 칩은 `key='illness'`와 `episode_id`를 담아 만들고(adjustment-signals 칩 생성 쪽), 삭제 시 `episode_id`가 일치하는 칩을 일반 라벨 '컨디션 신호'(NEW-16과 같은 라벨)로 바꾸고 `value`·`episode_id`를 뺀다.
  - **`summary` 칩(NEW-26 a·NEW-31 a):** `key='summary'` 칩은 자유 텍스트(`adjustment_reason`)라 문구만으로는 질병 여부를 알 수 없다 → **질병 문구가 들어간 칩은 생성 시 구조화 키를 단다**(adjustment-signals 칩 생성 쪽, 예: 칩에 `illness_episode_id` 필드 — 필드 이름은 구현 시). 삭제 시에는 **그 키가 해당 `episode_id`와 일치하는 칩만** 문구를 '컨디션 신호'로 치환하고 키를 뺀다(칩 항목 자체는 남김, 단어 사전·키워드 매칭 없음). NEW-23·NEW-16과 같은 라벨. **과거 칩(키 도입 이전 생성분)은 전수 치환**한다(NEW-31: 키가 없어 질병 여부를 판정할 수 없으므로 — 치환 대상 행 범위는 §7 열린 질문).
  - **질병만 근거였던 proposed 행 철회:** 삭제 트랜잭션은 철회하지 않는다. **다음 조회 때**(ADJ-6 재기록 경로) `decision='proposed'`이고 익명화 후 `signals_json`에 `role='trigger'` 항목이 하나도 남지 않은 행을 `decision='reverted'`로 바꾼다(질병이 유일한 트리거였던 행만 해당, 다른 트리거가 남은 행은 그대로). 코드 사실: 현재 `ensure_proposal`은 새 제안이 없으면 기존 proposed 행을 그대로 반환한다(`plan_adjustment_service.py:101-102`) — 이 철회 경로는 v37 재기록 설계(adjustment-signals 소관)에 추가해야 한다.
  - **AI 요약 저장 위치:** `ai_cache` 테이블(`src/ai/ai_cache.py`, 컬럼 `tab, cache_key, content_json, generated_at, data_fingerprint`, `UNIQUE(tab, cache_key)`, 앱 DB와 같은 `conn`으로 접근·`_ensure_table`로 지연 생성). 확인된 탭: `today_narrative`(key `{month_start}:{date}`, `services/_narrative.py:161-168`), `today_narrative_warm`(key = 날짜, `services/narrative_warm.py`), `ai_message.get_card_ai_message` 경유 카드 탭(key = 활동 ID·기간 등). 코치 대화는 `chat_messages`(`id, role, content, chip_id, ai_model, thread_id, evidence_json, created_at`, `db_setup.py:397-406`)·`chat_threads`에 따로 저장된다.
  - **같은 트랜잭션 범위:** `context_episodes` DELETE + `plan_adjustments`의 `signals_json`·`source`·`reasons_json` UPDATE + `ai_cache` 전체 DELETE(+ `chat_thread_ids`가 있으면 해당 스레드 `chat_messages` DELETE 후 빈 `chat_threads` DELETE, NEW-29·30)를 한 트랜잭션으로 묶는다(모두 같은 SQLite 연결). 코드 사실: `ai_cache.invalidate()`(`:97-104`)·`set_cached()`·`narrative_warm` 저장은 내부에서 `conn.commit()`을 부르므로 재사용하면 트랜잭션이 쪼개진다 → **commit 없는 삭제 헬퍼를 `ai_cache.py`에 추가**(예: `delete_all_no_commit(conn) -> int`, `conn.commit()` 호출 없음)해 `delete_episode`가 부른다. 대화 삭제도 commit 없이 같은 연결에서 실행 — 코드 사실(grep 2026-10-11): `coach_service.py`에는 스레드·메시지 삭제 함수가 없고 쓰기 함수는 모두 commit 한다 → `context_episodes`(또는 `coach_service`에 commit 없는 `delete_threads_no_commit(conn, ids) -> (messages, threads)` 추가, 위치는 구현 시)에서 실행. 빈 스레드 판정 = 삭제 후 `chat_messages`에 그 `thread_id` 행 0건. proposed 철회는 다음 조회 시점이라 이 트랜잭션 밖이다.
  - **AI 요약 삭제 대상(NEW-24 c → NEW-27 a·NEW-28 b):** 현재 `ai_cache` 행에는 `episode_id`·질병 여부 표지가 없다(key는 날짜·활동·기간 단위). 결정 — ① **표지 = `ai_cache` 불리언 컬럼**(질병 근거 사용 여부, NEW-27): 생성 시 AI 컨텍스트에 질병 신호가 들어갔으면 1 ② **질병 에피소드 삭제 시 표지 구분 없이 해당 사용자 `ai_cache` 전체 삭제**(NEW-28, 다음 조회에서 재생성). 단일 사용자 DB(`ai_cache`에 사용자 컬럼 없음)라 실제로는 테이블 전체 행 삭제다. NULL(도입 전)/0(질병 없음) 구분은 하지 않는다.
  - **NEW-27 ↔ NEW-28 관계(명시):** 삭제는 항상 전체이므로 **표지 컬럼은 삭제 판정에 쓰이지 않는다.** 표지 컬럼의 다른 소비처는 현재 설계에 없다. 그래서 컬럼 추가(`_ensure_table` `ALTER … ADD COLUMN`, `set_cached` 인자, 생성 3곳의 값 전달)를 **유지할지 설계에서 재확인**한다(§7 열린 항목 — 결정 표 NEW-27 단서). 재확인 전까지 변경 파일 표·검증에는 '조건부(재확인 후)'로 둔다. 코드 사실(참고): `ai_cache`는 `db_setup.py`가 아니라 `ai_cache._ensure_table`(`:151-167`)이 지연 생성하고 `data_fingerprint`도 같은 함수의 `ALTER TABLE … ADD COLUMN`(실패 무시)로 붙였다. 표지를 쓸 곳(grep 2026-10-11): `set_cached`(`ai_cache.py:55`, 호출자 `ai_message.py:234`·`_narrative.py:168`)와 `narrative_warm.py:38`의 직접 INSERT.
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
| `ALTITUDE_MIN_CONSECUTIVE_DAYS` 고도 연속일 조건 | 1일 / 2일 | **1일**(NEW-32 a) | 스파이크 제외 규칙 없음 |
| `TRAVEL_RETURN_WINDOW_DAYS` 귀국 역방향 창 | 적용 / 미적용 / 절반 | **출국 창(`TRAVEL_WINDOW_DAYS` 공식)의 절반**(NEW-33 c) | 절반의 정수화(올림/내림)는 결정 문구에 없음 — **구현 시 값 확인 필요**(§7) |
| `ILLNESS_RETURN_CONTEXT_DAYS` 질병 복귀 context | 3일 / 7일 / 종류별 | **7일**(NEW-34 c) | `end_date` 이후 |
| `TRAVEL_ALTITUDE_RETURN_CONTEXT_DAYS` 여행·고도 복귀 context | 3일 / 7일 / 종류별 | **3일**(NEW-34 c) | `end_date` 이후 |
상수는 `context_autodetect.py`(감지)·`adjustment_signals_context.py`(창·복귀 context) 모듈 상수로 두고 설정화하지 않는다(NEW-20 a). 관찰 후 조정은 상수 수정으로 한다.

## 3. 변경 파일 표 (race_calendar 관련 파일은 `race-calendar.md` §변경 파일 표)
| 파일 | 신규/수정 | 내용 | 예상 줄 |
|---|---|---|---|
| `src/db_schema_v38.py` | 신규(공유) | `context_episodes`·`illness_consent_events`(NEW-14·21) CREATE(멱등, dry_run). race_calendar 부분은 race-calendar.md | ~65 |
| `src/db_setup.py` | 수정 | DDL·마이그레이션 호출(SCHEMA_VERSION 은 race-calendar.md v39 기준) | +15 |
| `src/db_schema_v37.py` | 수정 | source CHECK 에 `illness`·`travel`·`altitude` 포함(NEW-2) | +1 |
| `src/services/context_episodes.py` | 신규 | open/extend/close/confirm/dismiss/delete/list_active, 2일 무응답 dismissed(쓰기 예외 명시), '오늘'=`reference_today`, `delete_episode(conn, id, *, chat_thread_ids=())`의 질병 이력 익명화(NEW-10·23·26·31: `signals_json`·`source`·`reasons_json`(질병 칩·구조화 키 일치 `summary` 칩 '컨디션 신호', 키 없는 과거 칩 전수 치환) + `ai_cache` 전체 삭제(NEW-28) + 선택 스레드 `chat_messages`·빈 `chat_threads` 삭제(NEW-29·30), 같은 트랜잭션; 여행·고도는 이력 불변 NEW-18), stale 질병 재확인 대상 조회(NEW-19·22, `ILLNESS_RECONFIRM_DAYS=7`). 300줄 근접 시 익명화를 `context_episodes_delete.py`로 분리 | ~270 |
| `src/ai/ai_cache.py` | 수정 | commit 없는 전체 삭제 헬퍼(NEW-28, `delete_episode` 트랜잭션용). **조건부(§7 재확인 후):** `_ensure_table`에 불리언 표지 컬럼 추가(NEW-27, 기존 `ALTER … ADD COLUMN` 패턴)·`set_cached` 표지 인자 | +10(+20 조건부) |
| `src/ai/ai_message.py`, `src/services/_narrative.py`, `src/services/narrative_warm.py` | 수정(조건부) | 생성 컨텍스트에 질병 신호 포함 여부를 불리언 표지로 저장(NEW-27) — §7 컬럼 존치 재확인 후 | +각 3 |
| `src/services/plan_adjustment_service.py`(v37 재기록, adjustment-signals 소관) | 수정 | 다음 조회 때 트리거 없는 proposed 행 → `reverted`(NEW-23), 질병 칩에 `key='illness'`·`episode_id`, 질병 문구가 들어간 `summary` 칩에 구조화 키(NEW-31) | +20 |
| `src/services/context_autodetect.py` | 신규 | `home_offset`, `detect_tz_shift`(tz_source 체인 결과 소비), `detect_altitude`, `detect_illness_prompt`(순수) + 로더, §2.7 감지 상수 | ~175 |
| `src/services/adjustment_signals_context.py` | 신규 | illness(OR 트리거)/travel/altitude 수집기 → signal dict(freshness 포함) | ~140 |
| `src/services/adjustment_signals.py`(adjustment-signals 소관) | 수정 | `primary_trigger` 순서에 illness 삽입(전체 순서는 ADJ-17) | +3 |
| `src/api/routes_context.py` | 신규 | `GET/POST/PATCH/DELETE /api/context-episodes`(질병 DELETE는 JSON 본문 `chat_thread_ids: int[]` 수용 — 미지정·빈 배열 = 대화 불변, 정수 배열·중복 제거·존재하지 않는 id 무시 검증, NEW-29; 여행·고도는 무시) | ~130 |
| `src/api/routes_today.py` | 수정 | 체크인 응답에 active·candidate 에피소드·질문 플래그·stale 질병 재확인 플래그(NEW-22, Today 배너·체크인 프롬프트 공용) 동봉 | +18 |
| `frontend/src/routes/today/+page.svelte` | 수정 | stale 질병 재확인 1줄 배너(NEW-22, 계속/나았어요, 44px) | +20 |
| `src/services/illness_consent.py` | 신규 | NEW-12·14~17: `illness_consent_events` 추가 전용 기록(grant/decline/revoke), 현재 상태=최신 행, 첫 입력 여부=행 0건, `redact_illness_for_ai`(미동의 시 '컨디션 신호' 일반화, severity·detail 제외, 메시지마다 상태 조회) | ~100 |
| AI 컨텍스트 빌더(`coach_evidence.py`, 체크인 AI 컨텍스트 등, 구현 시 grep) | 수정 | 질병 경로를 `redact_illness_for_ai` 경유로 | +각 3 |
| 설정 화면(AI 코치 설정, 구현 시 grep) + `frontend/src/lib/components/IllnessConsentSheet.svelte` | 신규·수정 | 첫 입력 1회 동의 시트(버튼 위 '나중에 설정에서 동의 가능' 안내, NEW-17), 설정 토글·철회 고지 | ~85 / +20 |
| `src/utils/reference_day.py` | 신규(타 설계) | '오늘' 헬퍼 — `patterns/timezone-display.md` §2.4 소관 | TZ 참조 |
| 전체 내보내기 | 신규(타 설계) | NEW-11 — `bundles/data-export.md` §3 변경 파일 표 참조 | 참조 |
| `frontend/src/lib/components/ContextChips.svelte` | 신규 | "+ 상태" 접힘·칩 행·보조 행·확인 프롬프트 | ~160 |
| `frontend/src/lib/components/ContextEpisodeList.svelte` | 신규 | 에피소드 목록·단건 삭제(use:modal, 삭제 확인) | ~120 |
| `frontend/src/lib/components/IllnessDeleteChatPicker.svelte` | 신규 | 질병 삭제 대화상자 안 코치 대화 삭제 단계(NEW-25·29·30: 기본 '삭제함', `GET /api/v1/coach/threads` 스레드 체크박스 기본 전체 선택, 스레드 0개면 숨김) | ~90 |
| `frontend/src/lib/components/QuickInput.svelte` | 수정 | ContextChips 삽입 | +10 |
| `frontend/src/lib/api*.ts`, `lib/types/index.ts` | 수정 | 클라이언트·타입 | +45 |
| tests: `test_db_schema_v38.py`(context·`illness_consent_events` 부분), `test_context_episodes.py`(NEW-22~31 포함), `test_ai_cache.py`(+, commit 없는 전체 삭제; 조건부: 표지 컬럼 추가 멱등·표지 저장), `test_context_autodetect.py`, `test_adjustment_signals_context.py`, `test_routes_context.py`, `test_illness_consent.py`; 프론트 `ContextChips.test.ts`, `ContextEpisodeList.test.ts`, `IllnessDeleteChatPicker.test.ts`, `IllnessConsentSheet.test.ts` | 신규 | 함수마다 ≥1 | ~55개 |
| 문서: 해당 `__init__.py` docstring, `files_index`(재생성), ADR(에피소드 모델·민감정보·질병 별도 동의) | 수정 | | — |

## 4. 단계·검증
1. **S0 (v37 작업 전):** v37 source CHECK 값은 adjustment-signals.md §3.9 의 11값(`illness`·`travel`·`altitude`·`race` 포함)으로 합의됨 — 일정만 선행 의존. `illness_consent_events`는 v38 합류로 확정(NEW-21). **확인 항목:** v37 이후 `ensure_proposal` 설계에서 같은 workout·date에 live `illness`·live `readiness` 행이 공존할 수 있는지 — 공존 가능하면 NEW-10 ② UPDATE가 `ux_plan_adj_live`(`db_schema_v31.py:29-30`) 위반(§2.6, 해결안은 확인 후 결정). NEW-23 proposed 철회 경로를 v37 재기록 설계에 포함하는지, NEW-27 `ai_cache` 불리언 표지 컬럼 존치 여부(NEW-28 전체 삭제로 삭제 판정 미사용, §7)를 함께 재확인. 선행: `reference_day.py`(timezone-display.md 단계 5-1).
2. **S1 v38 + 서비스:** `context_episodes`·`illness_consent_events`(v38 같은 파일, NEW-21)·서비스. 검증: 빈 DB/운영 DB **사본** 마이그레이션, 재실행 멱등, CHECK 위반 거부(`action`·`via`), `PRAGMA integrity_check`, DROP 롤백(가산 테이블 3개, v39 적용 전).
3. **S2 자동 감지(순수 함수):** 픽스처 — Garmin offset 32400→-25200, Strava 텍스트, offset 결측, `tz_source=fallback` 제외, 고도 스트림 없음/1일 활동만으로 candidate 생성(NEW-32, 연속 1일 경계)/연속일 extend, RHR↑만·HRV↓만·동시(질문은 동시만). §2.7 상수 경계(시차 3.5h 미만/이상, 고도 1,750m 미만/이상, 도착 후 창 `ceil((abs(Δh)+3)/2)`일, 귀국 역방향 창 = 출국 창의 절반(NEW-33, 정수화는 §7 확인 후), 적응 창 5일). candidate 중복 생성 없음(같은 에피소드 extend), 생성 후 2일 무응답 → dismissed, 경계(정확히 2일, '오늘'=`reference_today` 주입).
4. **S3 신호화:** confirmed→role 후보, candidate→context 만; confirmed illness 단독으로 트리거 성립; travel·altitude 는 트리거 집합 불변(빈도 회귀); `primary_trigger` = pain > illness > checkin > race > crs > acwr > readiness(ADJ-17); freshness 경계(오늘/1~2일/stale), stale 질병이 자동 종료되지 않음, `last_confirmed_date`+7일 경계(6일 미노출·7일 노출, '오늘'=`reference_today` 주입)에서 체크인 프롬프트와 Today 배너 둘 다 노출, 한쪽 응답 시 둘 다 사라짐(NEW-22)·'계속' → fresh·'나았어요' → end_date, 재확인 대기·무응답 동안 트리거 유지(역할 불변); 복귀 context 경계(NEW-34: 질병 `end_date`+7일 포함·+8일 제외, 여행·고도 +3일 포함·+4일 제외, `detail.returning`, role=context); 귀국 역방향 창 안 BOOST hold+support·창 밖 context(NEW-33); race priority 채움 회귀.
5. **S4 API·UI:** 칩 미선택 저장 = 기존 요청 본문과 동일(회귀), 에피소드 API 입력 검증(`server-input-origin-validation.md` 패턴), 삭제 후 목록·신호에서 사라짐, 375px — 접힘 시 카드 높이 증가 "+ 상태" 1줄, 44px 타깃, `aria-pressed`, `use:modal` 포커스 복귀·Esc, 삭제 확인 취소 시 무변경.
6. **S5 개인정보:** (NEW-12·17) 첫 질병 입력에만 동의 시트 1회, 시트에 '나중에 설정에서 동의 가능' 안내 노출, '동의 안 함' 후 두 번째 입력은 묻지 않음(`decline` 행 1건), 설정 토글로 나중에 동의 → `grant` 행; (NEW-14) 동의·철회·재동의가 행으로 누적되고 현재 상태 = 최신 행; 미동의·철회 → AI 코치 페이로드에 `illness`·`source='illness'` 문자열 없음, 대신 '컨디션 신호'(NEW-16: severity·`value`·detail 모두 없음), 여행·고도는 coach_consent 로 포함; (NEW-15) 대화 도중 철회 → 같은 대화의 다음 메시지부터 일반화, 철회 전 메시지 기록은 변경하지 않음; 동의 없이도 로컬 조정 트리거 동일. (NEW-10) 질병 에피소드 삭제 → 해당 `episode_id` 질병 항목만 `signals_json`에서 제거, `source='illness'`→`'readiness'`, `after_json`·decision·rev 불변, 다른 에피소드 항목 불변, 한 트랜잭션(중간 실패 시 둘 다 롤백). (NEW-23) 질병 삭제 → `reasons_json`의 해당 `episode_id` 질병 칩만 일반 라벨로 바뀜, 같은 트랜잭션에서 `ai_cache` 대상 행 삭제(중간 실패 시 에피소드·이력·캐시 모두 롤백, commit 헬퍼 미사용 단언), 질병이 유일한 트리거였던 proposed 행은 다음 조회에서 `reverted`·다른 트리거가 남은 행은 유지·accepted 행은 철회 안 함. (NEW-26·31) 구조화 키가 해당 `episode_id`와 일치하는 `summary` 칩만 '컨디션 신호'로 치환·키 제거(칩 개수 불변), 다른 에피소드 키·질병 키 없는 신규 칩 불변, 키 도입 이전 과거 칩은 전수 치환(범위는 §7 확정 후), 키워드 매칭 코드 없음. (NEW-28) 질병 삭제 → 표지 값과 무관하게 `ai_cache` 0행(질병 없음·NULL 행 포함), 삭제 헬퍼가 commit 하지 않음(트랜잭션 롤백 시 캐시 복원). 조건부(NEW-27 존치 시): 표지 컬럼 추가 재실행 멱등·질병 신호가 들어간 생성분만 1. (NEW-25·29·30) 질병 삭제 대화상자에 대화 삭제 단계 노출·여행·고도에는 없음, 기본값 '삭제함'·스레드 전체 선택, 스레드 0개면 단계 숨김, '삭제 안 함'/선택 0개 → `chat_thread_ids=[]` → `chat_messages`·`chat_threads` 불변, 일부 선택 → 선택 스레드 메시지만 삭제·비선택 스레드 불변·빈 스레드 행 삭제, API 미지정 시 대화 불변, 잘못된 id(문자열·음수) 400·없는 id 무시, 같은 트랜잭션(중간 실패 시 롤백), 반환 개수(메시지·스레드) 일치. (NEW-18) 여행·고도 에피소드 삭제 → `plan_adjustments` 전 행 바이트 단위 불변·`ai_cache` 불변. (NEW-11) 내보내기 검증은 `data-export.md` §4.
7. 공통: 신규 파일 300줄 이하, `pytest tests/` 전체, `check_docs.py`.

## 5. 결정 필요
- 결정 완료(표 참조: `decisions-table.md` NEW-1~34, 추가 결정 NEW-10·11·12, 연관 ADJ-13·15·17·18, RC-2·7, TZ-1, V1-1·V1-2).
- 사용자 확정 대기 문구(TXT-1, 미확정): NEW-15 철회 고지, NEW-17 동의 시트 안내, NEW-19 재확인 프롬프트(§2.1·§2.5 초안), NEW-25·29·30 대화 삭제 단계(§2.5). 구현 단계에서 후보 문구를 제시하고 사용자가 확정한다.

## 6. 범위 밖 메모
- `today_service.py` 320줄 초과(규칙 위반) — 별도 분리 작업 필요.
- 고도·폭염에 따른 **페이스 목표 보정**(조정이 아닌 처방 변경)은 별도 설계.
- Strava `timezone` 텍스트가 `metric_store` 에 text 로 저장되는지(숫자 offset 아님) 구현 시 확인.

## 7. 동기화 중 발견한 모호점
- 해소(NEW-14·NEW-21): 질병 동의는 별도 테이블 `illness_consent_events`, v38 합류.
- 해소(NEW-15): 철회 즉시 이후 메시지부터 일반화.
- 해소(NEW-16): '컨디션 신호'에 severity 미포함.
- 해소(NEW-17): 다시 묻지 않음 + 시트 안 안내(문구 사용자 확정 대기).
- 해소(NEW-23~26): `reasons_json` 익명화 + 질병 단독 근거 proposed 다음 조회 철회 + 저장된 AI 요약 삭제(§2.6).
- 해소(NEW-27·28): 표지 = `ai_cache` 불리언 컬럼, 삭제는 표지 구분 없이 사용자 `ai_cache` 전체(NULL/0 구분 없음).
- **설계에서 재확인(NEW-27 단서):** NEW-28 로 항상 전체 삭제하므로 불리언 표지 컬럼은 삭제 판정에 쓰이지 않고, 현재 설계에 다른 소비처도 없다 — 컬럼·`set_cached` 인자·생성 3곳 변경을 존치할지 재확인(§3·§4에 '조건부'로 표시).
- 해소(NEW-29·30): 대화 삭제는 사용자가 스레드 선택, 대화상자 기본 '삭제함'·스레드 기본 전체 선택, 빈 `chat_threads` 함께 삭제. 같은 대화상자 안 단계로 설계(§2.5).
- **남은 확인(NEW-29):** `thread_id`가 NULL인 스레드 도입 이전 `chat_messages`(스레드 목록에 안 나옴)를 대상에 넣을지 결정 문구에 없다 — 현재 설계는 선택 스레드만 지우므로 남는다.
- 해소(NEW-26·31): `summary` 칩 질병 판정 = 생성 시 구조화 키, 그 키로만 치환. **남은 확인:** 키 없는 과거 칩 '전수 치환'의 범위 — 익명화 대상 행(삭제 에피소드 질병 항목이 있던 행)의 과거 `summary` 칩만인지, 모든 `plan_adjustments` 행의 과거 `summary` 칩인지 결정 문구로 갈리지 않는다(과거 행에는 질병 항목이 `signals_json`에 없을 수 있어 대상 행 식별 자체가 어려움).
- 해소(NEW-18·NEW-23): 여행·고도 삭제 시 이력 변경 없음, 질병만 trigger였던 proposed 행은 다음 조회 때 철회.
- NEW-10 `illness`→`readiness` 치환과 유니크 인덱스: 코드상 현재는 충돌 경로 없음, v37 이후 live 행 공존 가능 여부에 달림 — §2.6·§4 S0 확인 항목(해결안 미결정).
- TZ-1 추가 결정은 대회 날짜 필드를 열거한다. 에피소드 신선도·2일 무응답·체크인 `input_date`에 같은 헬퍼를 쓰는 것은 이 문서의 적용 해석이다.
- 해소(NEW-20·32·33·34): §2.7 상수 표. 남은 부분: 시차 3.5h·도착 후 창 공식은 구현 시 값 확인 필요, 귀국 절반 창의 정수화(올림/내림, 결정 문구에 없음)는 구현 시 값 확인 필요.
- **열린 질문(NEW-33 ↔ NEW-34):** 여행 `end_date`(귀국) 이후 귀국 역방향 창(hold+support)과 복귀 context 3일이 겹치는 날의 처리 — 창 역할 우선·창 종료 후 남은 날만 context로 볼지, 둘 다 기록할지(설계는 창 우선 제안).
- 해소(NEW-19·NEW-22): 7일, 체크인 프롬프트 + Today 배너 병행, 대기 중 트리거 유지. 문구는 TXT-1.
- NEW-2 로 v37 CHECK 에 들어간 `travel`·`altitude` 는 NEW-3(트리거 아님)상 실제 source 로 쓰이지 않는다 — 결정 표가 "미사용 값 존재"를 감수한 것으로 해석.
- **NEW-7 ↔ NEW-13 해석:** 확인 프롬프트를 접힘 밖에 둔 것(§2.5)은 2일 무응답 dismissed 가 공정하려면 필요하다는 이 문서의 해석이다 — 상태 칩만 접는다는 결정 범위와 맞는지 product 확인.
