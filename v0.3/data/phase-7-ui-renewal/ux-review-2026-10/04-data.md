# 묶음 4 데이터 UX/QA 점검 (2026-10-11)

범위: /data, /data/sources(+[provider]), /data/sync, /data/import, /data/export, /data/settings(+ai, profile) 및 data 컴포넌트, CalendarFeedCard, McpTokenCard, SourceBadge/Coverage/Summary.
방법: 샌드박스(venv, DB 사본, 가짜 자격증명, 외부 DNS 차단)에서 API 직접 호출 + Playwright(1280/375px) + 코드 열람. 코드·설계·커밋 변경 없음. 외부 호출 0건(`BLOCKED-DNS` 로그만).
심각도: 상=사용자 오도·데이터 오염·보안, 중=혼란·우회 가능, 하=사소.

## 발견 사항

| ID | 화면/카드/항목 | 관점 | 증상 | 재현 | 심각도 |
|---|---|---|---|---|---|
| D-01 | 설정·내보내기·AI 화면의 내부 링크 | 편의/데이터 | `{base}` 없이 작성된 링크가 있어 클릭하면 전체 화면 "Not Found" 404. 대상: 내보내기의 `/data/import`, `/data/settings/ai`, 설정의 `/data/sources`, `/data/settings/profile`, `/data/settings/ai`, AI 페이지 뒤로가기 `/data/settings` | /v2/data/export 에서 "가져오기" 링크 클릭 → 404 | 상 |
| D-02 | 내보내기의 `/training/export.ics` 링크 | 편의 | `{base}` 없는 링크. 클릭해도 URL이 /v2/data/export 에 머묾, 다운로드 여부 불확실 | /v2/data/export 에서 ICS 링크 클릭 | 중 |
| D-03 | 개요 "활동" 타일 | 데이터 | 1,427건 표시. 소스별 행 합(588+637+202, 중복 포함)이며 sync-state activity_count 488, 중복 그룹 기준 약 626과 불일치 | GET /api/v1/data/overview vs sync-state vs DB | 상 |
| D-04 | 소스 카드(Intervals) 오류 문구 | 보안/표현 | `HTTPSConnectionPool(host='intervals.icu'… NameResolutionError…)` 원시 예외 문자열이 /data, /data/sources/intervals, /data/sync(기록)에 그대로 노출. 내부 호스트·URL·athlete id 포함, 375px에서 잘림 | 네트워크 차단 상태에서 Intervals 동기화 후 화면 확인 | 중 |
| D-05 | Intervals 연결 실패 안내 | 용어 | 네트워크 장애와 잘못된 키를 구분하지 않고 "연결하지 못했어요 (연결 실패)". 사전점검은 422 NO_SOURCES "not_connected (연결 실패)" 로 내부 코드 노출. 카드는 "미연결"로 표기 | POST /data/sources/intervals/connect (잘못된 키) | 중 |
| D-06 | 전체 동기화 상태 | 데이터 | sync-state 전체가 "동기화 기록 없음"/error 이고 last_success_at null 이나 개별 소스·기록에는 완료 11건이 있음 | GET /api/v1/data/sync-state | 중 |
| D-07 | 프로필 숫자 입력 | 데이터 | 교차 검증 없음. hrmax=125 가 lthr 178 과 함께 저장됨. 화면은 "직접 입력 125bpm" 과 자기추정 192 를 나란히 표시 | PATCH /data/profile {hrmax:125} | 중 |
| D-08 | 프로필 source_choice | 데이터 | threshold_pace=device 인데 기기값이 없어도 200으로 수락 | PATCH profile source_choice | 하 |
| D-09 | 소스 PATCH | 데이터 | 미연결 소스(runalyze)에 sync_enabled=false 가 200 | PATCH /data/sources/runalyze | 하 |
| D-10 | 가져오기 업로드 크기 제한 | 보안 | 540MB 업로드가 디스크에 기록된 뒤에야 413 TOO_LARGE. 거부된 업로드가 imports/ 에 빈 디렉터리 잔존 | 대용량 multipart POST /data/import | 중 |
| D-11 | 가져오기 CSV 판별 | 보안/안정성 | 한 필드가 128KB 초과인 깨진 CSV → 처리 안 된 `_csv.Error` 로 500 HTML 응답 | 큰 필드 CSV 업로드 | 중 |
| D-12 | 가져오기 ZIP | 보안/표현 | `../` 포함 zip 이 400 대신 500 PREVIEW_FAILED (경로 주입 자체는 차단됨) | 경로 이탈 항목 zip 업로드 | 하 |
| D-13 | 가져오기 형식 검증 | 데이터 | 임의 CSV(`a,b`)가 garmin_csv 로 수락되어 errors:1 (사유 없음). Strava CSV 를 source=garmin 으로 올려도 수락 | 업로드 | 중 |
| D-14 | 가져오기 확장자 오류문 | 용어 | source=garmin 인데도 "Strava ZIP·CSV…" 안내 | 잘못된 확장자 업로드 | 하 |
| D-15 | 내보내기 기간 오류문 | 용어 | 기간 역전 시 "from이 to보다 늦어요" 파라미터명이 그대로 노출 | 시작 2026-09-30, 종료 2026-01-01 → 활동 CSV | 하 |
| D-16 | 내보내기 미래 기간 | 데이터 | 헤더만 있는 빈 CSV 를 성공으로 내려주며 파일명에 기간 없음. Content-Type 이 `text/csv; charset=utf-8; charset=utf-8` 로 중복 | 미래 기간 export | 하 |
| D-17 | 웰니스 CSV | 데이터 | 1,093행 중 581행이 빈 채움 행 | 웰니스 CSV 다운로드 | 중 |
| D-18 | 전체 아카이브(zip) | 체감 성능 | 약 32초, 67~71MB. 진행률이 끝까지 0/1. 전량 메모리 적재, 기간 필터가 tables/raw_payloads 에 적용되지 않음 | 아카이브 요청 | 중 |
| D-19 | MCP 토큰 days | 데이터 | days:0 은 조용히 기본 90일, -5/99999999 는 409 TOKEN_LIMIT(400 BAD_DAYS 여야 함), 1.9 는 1로 절삭 | POST /mcp-tokens | 하 |
| D-20 | MCP 토큰 label | 데이터 | 배열 `["x"]` 가 문자열 "['x']" 로 수락, 40자 초과는 알림 없이 절삭 | POST /mcp-tokens | 하 |
| D-21 | 쓰기 API 본문 | 안정성 | JSON 배열 본문 `[1]` 이 500 HTML | POST /mcp-tokens | 중 |
| D-22 | 쓰기 API CSRF 방어 | 보안 | Content-Type text/plain + `Origin: http://evil.example` 의 POST/DELETE 가 그대로 수행(캘린더 피드 생성 201, 삭제 204). Origin 검사 없음, 세션 쿠키에 SameSite/Secure 미확인 | curl 로 Origin 위조 POST | 상 |
| D-23 | AI 키 입력 | 데이터 | 공백·개행·`<b>` 포함 키, 5,000자 키가 수락됨. 빈/공백 값은 변경 없음이지만 피드백 없음 | PATCH /data/settings/ai {keys:{...}} | 하 |
| D-24 | 연결 흐름(Strava) | 데이터 | 자격증명이 비어도 redirect_url 반환(검증 없음) | POST connect {} | 하 |
| D-25 | 연결 해제 대화상자(Strava) | 접근성 | role=alertdialog 이나 aria-modal 없음, Esc 로 닫히지 않음, 포커스가 호출 버튼에 남음 | 소스 상세 → 연결 해제 | 중 |
| D-26 | 전 페이지 제목 | 접근성 | `<h1>` 이 비어 있음(소스 상세만 있음) | 12개 라우트 DOM 점검 | 중 |
| D-27 | 폼 라벨 | 접근성 | 비밀번호 입력은 placeholder 만 있고 label 없음. AI 의 비활성 체크박스 5개, "서버 주소 복사" 버튼에 접근 가능한 이름 없음 | DOM 점검 | 중 |
| D-28 | 터치 타깃 (375px) | 접근성 | 32px 미만 대상: AI 35, 프로필 21, 동기화 10 | 375px 계측 | 하 |
| D-29 | 기간 지정 동기화 기본일 | 데이터 | `new Date().toISOString().slice(0,10)` 은 UTC 날짜라 KST 새벽에 하루 어긋남 | 코드 RangeSyncForm | 하 |
| D-30 | 프로필 입력 파서 | 데이터 | `parseProfileInput` 의 split(':') 이 초과 구간("5:30:99")을 수락 | 코드 | 하 |
| D-31 | 동기화 기록 시각 | 편의 | "마지막 01:38 · 다음 05:38" 에 날짜가 없어 어제/오늘 구분 불가 | /data/sync | 하 |
| D-32 | 소스 표기/문구 | 용어 | "Intervals" 영문과 한글 혼용, 설정·AI 페이지 간 문구 차이("소스 연결·자동 동기화" 등). Garmin 상세에 "인증이 만료되었어요…" 가 두 번 반복. Garmin 메시지 375px 에서 잘림 | /data/sources/garmin | 하 |
| D-33 | 캘린더 피드 URL 1회 표시 | 편의 | 새로고침하면 주소를 볼 수 없고 재발급해야 함(보안상 의도). 안내문은 충분 | 내보내기 → 캘린더 구독 | 하 |
| D-34 | 가져오기 화면 | 편의 | 소스 선택이 Strava/Garmin 뿐(Intervals·Runalyze 파일 가져오기 없음, 설계상) | /data/import | 하 |

## 확인 완료 항목 (문제 없음 포함)

- 프로필: 범위 밖 숫자·문자열·bool·1e999 는 400. 자동 동기화 간격/범위 검증 OK. 기간 동기화(역전·잘못된 형식·미래·빈 값·경로형 소스)는 400/422 로 정상 거부.
- 자격증명 노출: AI 키는 `••••끝4자리` 마스킹, API 응답·DOM·server.log 에 평문 0건. 가짜 시크릿이 로그에 0건. MCP 토큰은 POST 응답에서만 평문, 목록은 last4 만, `Cache-Control: no-store`. (샌드박스 config.json 에는 암호화 키가 없어 평문 저장 — 운영은 아래 미검증.)
- MCP 토큰: 빈/공백 라벨 400, 6번째 토큰 409 TOKEN_LIMIT(5개), 재폐기·없는 id 는 404, HTML 라벨은 텍스트로만 렌더(실행 안 됨).
- 캘린더 피드: 중복 생성 409 FEED_EXISTS, DELETE 멱등, 더블클릭이 POST 1회, 해제·재발급 버튼은 확인 대화상자(alertdialog)를 먼저 띄우고 확인 전에는 요청을 보내지 않음.
- 연결 해제: keep_data 없으면 400, 있으면 200(멱등), 대화상자에 보존 건수("가져온 활동 202건은 그대로 남아요") 안내. 알 수 없는 provider 404.
- GET 부작용 없음: /data/sync, /data/recompute, /data/export GET 은 405. 내보내기 중복 요청은 409 EXPORT_RUNNING. 없는 export/import/job id 및 경로 이탈 id 는 404. 파일명 경로 이탈은 정리됨.
- 개요 소스별 건수(588/637/202)는 DB 와 일치.
- 12개 라우트 × (1280, 375px): 가로 넘침 없음, pageerror 없음, networkidle 약 1.0~1.4초, 외부 요청 0건.
- 카피: "동기화 꺼짐 · 과거 기록은 보존돼요" 등 해제 후 안내는 명확.

## 미검증 항목과 사유

- 운영의 `CREDENTIAL_ENCRYPTION_KEY` 적용 및 `enc:` 저장: 샌드박스에 키가 없음.
- 운영 인증(auth_cf) 하의 타 사용자 접근: 샌드박스는 dev 모드라 X-User-Id/Cf-Access 헤더가 무시된 것만 확인.
- 실제 외부 동기화·429 대기·SYNC_COOLDOWN 표시: 외부 호출 차단.
- 캘린더 피드 URL 1회 표시 확인: 샌드박스에서 URL 이 응답에 없어 확인 못함. MCP 토큰 "폐기" 확인 대화상자 여부도 UI 에서 직접 확인 못함.
- 300자 파일명 업로드, Strava last_new_data_at 간극, 375px 스크린샷의 시각 품질(/tmp/pwtest/set375.png 열람 안 함), /training/export.ics 실제 다운로드 여부.
- 교차 참조: 01/02/03 문서의 T/A/M ID 와의 중복 여부는 대조하지 않음.

## 처리 기록 (2026-11-10, V2-AUDIT-INDIV 묶음 D)
- D-02 처리: 훈련 계획 ICS 는 v2 밖(Flask 루트) 라우트라 `{base}` 를 붙이지 않는 것이 맞음 — 링크에 `download="runpulse-training.ics"` 를 달아 다운로드임을 명시하고, 실제 범위(이번 주 월~일)를 제목·설명에 적음(`exports.PLAN_ICS_URL`). 문구는 TXT-1 잠정. 실제 파일 저장은 브라우저 스모크에서 속성만 확인(다운로드 이벤트는 미확인).
- D-04 처리: 원시 예외 문자열을 응답에서 뺌 — 동기화 기록(`data_service.run_dict.last_error`)은 실패 행만 한국어 문구(`sync_errors.public_message`), 소스 상태(`sync_state_service.classify_error`)는 `detail`(원문 200자)을 없애고 오류 문구에서 네트워크·시간 초과·5xx 를 분류(`classify_text`). 기록 줄·소스 상세 문구는 잘리지 않고 줄바꿈(`break-words`).
- D-05 처리: 연결 점검이 응답 없이 실패(DNS·네트워크)하면 `reason: network`(intervals_auth·runalyze) → 연결 시도 문구 "Intervals 서버에 연결하지 못했어요. 네트워크 상태를 확인하고…", 키 문제는 "연결하지 못했어요 · 잘못된 API 키". 동기화 사전점검은 `unreachable` 코드로 미연결과 구분(`connection_skip`), 전부 그 이유면 `503 SOURCE_UNREACHABLE`(프런트 안내 문구 별도). 문구 TXT-1 잠정.
- D-06 부분: 원인 후보 두 가지를 고침 — (1) 전체 기록(`/data/runs`)에 가져오기·내보내기·재계산 작업의 '완료'가 섞이던 것(동기화 소스 작업만, `list_recent_jobs(services=)`), (2) 소스별 마지막 성공을 최근 20건에서만 찾던 것(창이 실패로 가득하면 원장에서 마지막 완료 1건을 더 찾음). 시도는 있으나 성공이 없으면 "동기화 기록 없음" 대신 "성공한 동기화 없음". 점검 당시 상태(어느 소스가 켜져 있었는지)를 재현하지 못해 실제 원인이 이 둘인지는 미확인.
- D-07 처리(추천안 확정): 저장 전 상태 검사 `profile_service.check_changes` — 이번 변경이 HRmax·LTHR 를 건드렸고 사용값이 LTHR ≥ HRmax 이면 400("젖산역치 심박(178bpm)은 최대심박(125bpm)보다 낮아야 해요"). 심박을 건드리지 않는 변경은 기존 상태로 막지 않음.
- D-08 처리(추천안 확정): 고른 출처에 값이 없으면 422 SOURCE_UNAVAILABLE("역치 페이스: 기기 값이 없어 고를 수 없어요").
- D-09 처리(추천안 확정): 미연결 소스 PATCH 는 409 NOT_CONNECTED(`sync_state_service.is_connected`, 카드의 연결 축과 같은 기준).
- D-10 처리: Content-Length 가 한도(500MB+1MB)를 넘으면 본문을 받기 전에 413, 길이 없는 전송은 `request.max_content_length` 로 파싱 중 413. 크기·형식·미리보기 실패로 거부한 업로드는 디렉터리째 지움(`import_service.discard_upload`).
- D-11 처리: CSV 전체를 미리 훑어 `csv.Error`(128KB 초과 칸 등)를 400 INVALID_UPLOAD "CSV를 읽지 못했어요…"로(`import_detect`). 미리보기 중 `csv.Error`·`ValueError`·`UnicodeDecodeError` 도 400.
- D-12 처리: ZIP 은 풀기 전에 `../`·절대 경로 항목을 400 으로 거부(`import_detect.unsafe_member`, 추출 단계에도 같은 검사 유지).
- D-13 처리: CSV 는 머리글로 판별 — Strava(`Activity Date`), Garmin(`날짜`+`활동 종류|활동 유형`), 그 밖은 "알 수 없는 CSV 형식이에요". 고른 소스와 파일 종류가 다르면 "Strava 파일로 보여요. 가져올 소스를 Strava(으)로 바꿔 주세요"(미리보기·실행 모두). 영문 머리글 Garmin CSV 는 기존 임포터가 한국어 열만 읽으므로 계속 거부됨.
- D-14 처리: 확장자 안내가 고른 소스를 따름(`extension_hint`: Garmin 이면 "Garmin 활동 CSV 한 개, 또는 FIT/GPX/TCX(.gz)…").
- D-15 처리: "시작일이 종료일보다 늦어요", "시작일은 YYYY-MM-DD 형식이에요".
- D-16 처리: 시작일이 오늘 이후면 400 "시작일이 오늘 이후라 내보낼 기록이 없어요". 기간을 고르면 파일명에 기간(`runpulse_wellness_2026-01-01_2026-01-31.csv`), Content-Type 중복 제거(`content_type=`), 데이터 행 수 헤더 `X-Export-Rows` — 0 이면 화면에 "이 기간에는 기록이 없어 머리글만 담았어요". 문구 TXT-1 잠정.
- D-17 처리: 웰니스 CSV 에서 날짜 외 값이 모두 빈 행 제외.
- D-18 부분: 진행률을 테이블 단위(완료/전체)로 원장에 기록하고 이력에 "만드는 중… 3/12" 표시. 기간 필터는 이미 tables·raw_payloads 에 적용돼 있음(`export_archive._where`·`_write_raw`, 재확인). 소요 시간(약 32초)·용량·요약 CSV 의 메모리 적재는 손대지 않음(스트림 그룹 크기 조정·요약 CSV 스트리밍은 설계 필요).
- D-19 처리: `days` 는 1~365 정수만(0·음수·99999999·1.9 → 400 BAD_DAYS). 없으면 기본 90일.
- D-20 처리: `label` 이 문자열이 아니면 400 LABEL_INVALID, 40자 초과는 400 LABEL_TOO_LONG(조용히 자르지 않음).
- D-21 부분: 공용 `validation.json_object()` — 객체가 아닌 JSON(`[1]`)·깨진 JSON 은 400 INVALID_PARAM. 데이터 영역(MCP 토큰·캘린더 피드·AI 설정 PATCH/테스트)에 적용. 같은 `get_json(silent=True) or {}` 패턴이 plan·coach·shoes·today·race_calendar 등 10여 곳에 남아 있음(봉투 핸들러 덕에 HTML 500 은 아니고 JSON 500) — 묶음 밖이라 그대로.
- D-23 처리: 키 형식 검사(`ai_settings_service.key_format_error`, 프런트 `aiSettings.keyFormatError` 같은 규칙) — 공백·줄바꿈·제어문자·`<>"'\``·비ASCII·256자 초과 거부, 입력 중 안내 + 저장 버튼 비활성. 빈 값만 보내면 "API 키를 입력해 주세요". 길이 상한 256 은 임의 값(제공자별 실제 키 길이 확인 안 함).
- D-24 부분: Strava 앱 정보 형식 검사(`strava_app_ready`: Client ID 숫자, Secret 공백 없음) — 형식이 틀리면 NEEDS_APP. 값이 실제로 맞는지는 Strava OAuth 화면에서만 알 수 있어 연결 시작 시점에는 검증하지 않음(연결 흐름 자체는 설계대로 redirect).
- D-29 처리: 기간 동기화 기본 종료일을 기기 날짜로(`localDateString`).
- D-30 처리: 페이스 입력은 정확히 `m:ss`(초 00~59)만 — "5:30:99" 거부.
- D-31 처리: 자동 동기화 시각에 "오늘/어제/내일" 또는 "11월 1일"을 붙임(`dataArea.scheduleTime`, 서버 로컬 벽시계 기준).
- D-32 부분: 소스 상세에서 상태 줄과 같은 오류 문구를 두 번 보이지 않게, 375px 줄바꿈. 설정의 "소스 연결·자동 동기화" 카드는 실제 화면(소스 / 동기화 탭)에 맞춰 "소스 연결"·"자동 동기화" 두 카드로 나눔(문구 TXT-1 잠정). **보류**: 소스 이름 표기("Intervals" vs 환영 화면 "Intervals.icu") 통일은 제품 표기 결정이라 사용자 결정 필요.
- D-33·D-34: 종결(지시대로 처리 대상 아님).
- 확인 방법: pytest 신규 `tests/test_data_audit_d_sync.py`(15)·`tests/test_data_audit_d_io.py`(26), 프런트 `frontend/tests/dataAuditD.test.mjs`(5). 합성 DB 서버(사본) 375/1280 브라우저 스모크: 설정 카드·ICS download 속성·빈 기간 CSV 안내·기간 역전 문구·자동 동기화 "오늘 13:37"·AI 키 오류/저장 비활성·페이스 "5:30:99" 거부·가로 넘침 없음·pageerror 0. 프로필 교차 검사(400)·출처 없음(422)·미연결 PATCH(409)·알 수 없는 CSV(400)는 같은 서버에 curl 로 확인(합성 DB 에 LTHR 값이 없어 화면 경로로는 400 문구를 띄우지 못함).
