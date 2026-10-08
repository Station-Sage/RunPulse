# DESIGN — 계획 캘린더 .ics 구독 URL (2026-10-08, 초안)

> 근거: `40-v2-unimplemented/design.md` 121행(내보내기 카드 ③ "계획 캘린더 `.ics` + 구독 URL"), 592행(#10 "기존 엔드포인트 · 구독 URL 복사").
> 범위: 설계만. 확정은 사용자 승인 후. 기존 결정(ADR-023/029/030, `/training/export.ics` 유지)은 건드리지 않는다.

## 1. 배경과 문제

- 기존 `/training/export.ics`(`src/web/views_training_export.py`)는 **세션 사용자 전용 다운로드**다. Google/Apple 캘린더는 쿠키·헤더를 못 보내므로 구독할 수 없다.
- 인증 구조: Cloudflare Zero Trust가 엣지에서 로그인 → `auth_cf._identify_user`가 `CF-Access-Authenticated-User-Email`로 `session["user_id"]` 세팅. 운영 모드에서 헤더가 없으면 **401**. 사용자 DB는 `data/users/<email>/running.db`(`db_setup.get_db_path`).
- 따라서 공개 피드에는 (a) CF Access를 우회하는 경로, (b) `auth_cf`의 예외 경로, (c) **토큰→user_id 조회 수단**이 모두 필요하다. 사용자별 DB만으로는 (c)가 불가능하다(어느 DB를 열지 모름). 선례: `/api/garmin/local-sync`가 `auth_cf`를 건너뛰고 본문 키로 2차 인증한다.
- 기존 ICS 결함(구독 시 문제가 커짐): `UID`·`DTSTAMP` 없음(RFC 5545 필수, 구독 시 중복/갱신 실패), 종일 이벤트인데 `DTEND`=`DTSTART`, 텍스트 이스케이프·75옥텟 줄 접기 없음, `description` 자유 텍스트를 그대로 노출, 1주만 출력.

## 2. 결정 요약 (잠정 추천안 검증 결과)

| 항목 | 결정 | 잠정안 대비 |
|---|---|---|
| 토큰 | `secrets.token_urlsafe(32)`(256bit) + 접두 `rpcal_` → 총 ~49자 | 유지 + 접두(유출 스캔용) |
| 저장 위치 | **전역 인덱스 `data/calendar_feeds.db`**(SQLite, 1테이블) | 사용자별 DB 불가 → 전역 필수 |
| 해시 | 조회는 `sha256(token)`(UNIQUE), 재표시용으로 **Fernet 암호문** 함께 저장 | 보완: 해시+재표시 양립 |
| 경로 | `GET /feeds/cal/<token>.ics` (Flask, `/api/v1` 밖) | 신규 |
| 무효화 | 재발급=UPSERT로 해시 교체(즉시 무효), 해제=행 삭제 | 유지 |
| 로그 | gunicorn 접근 로그 리댁션 로거 + `auth_cf` 경로 로그 이전 차단 | 보완: 현재 접근 로그가 경로 전체를 남김 |
| 레이트리밋 | 프로세스 내 버킷(워커 1개 전제) + CF WAF 규칙 권고 | 신규 |
| 내용 | 구조화 필드로 서버가 만든 텍스트만. 자유 텍스트·AI·HR bpm·완료 여부·목표명 제외 | 보완 |

## 3. 저장소 설계

### 3.1 왜 전역 인덱스인가
- 사용자별 DB: 토큰으로 DB를 찾을 수 없다. 모든 `data/users/*/running.db` 순회는 사용자 수에 비례하고 테스트용 디렉터리(`u`, `test@test.com` 등)까지 열게 됨 → 기각.
- 사용자 config.json: 같은 이유로 조회 불가, 운영자 영역(ADR-023) → 기각.
- 토큰에 user_id 암호화 삽입(무상태): 조회는 되지만 폐기에 사용자별 버전 카운터가 따로 필요하고, 서버 키 교체 시 전원 URL 무효, 토큰이 길어짐 → 대안으로만 기록(§9).
- 전역 인덱스는 "토큰 → 사용자" 단 하나의 사실만 담으므로 ADR-023(사용자 데이터=사용자 DB)과 충돌하지 않는다. **피드 내용은 여전히 사용자 DB에서 읽는다.**

### 3.2 DDL (`data/calendar_feeds.db`, 파이프라인/앱 테이블 수에 포함하지 않음)
```sql
CREATE TABLE IF NOT EXISTS calendar_feeds (
    user_id         TEXT PRIMARY KEY,          -- 1인 1피드
    token_hash      TEXT NOT NULL UNIQUE,      -- hex(sha256(token))
    token_enc       TEXT,                      -- credential_store Fernet "enc:..." (재표시용)
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    last_access_at  TEXT,                      -- 10분 단위로만 갱신(쓰기 억제)
    last_client     TEXT                       -- 'google'|'apple'|'outlook'|'other' (UA 족 분류만, 원문 저장 금지)
);
```
- 사용자 DB `SCHEMA_VERSION`(30) 변경 없음. `export_service._ARCHIVE_TABLES`에 들어갈 일도 없음(아카이브로 토큰 유출 경로 차단).
- 발급/재발급: `INSERT ... ON CONFLICT(user_id) DO UPDATE SET token_hash=?, token_enc=?, created_at=datetime('now'), last_access_at=NULL, last_client=NULL` — 한 문장이라 구 토큰 무효와 신 토큰 유효가 원자적.
- 동시성: gthread 8스레드 → `timeout=10`, WAL. 쓰기는 발급·해제·접근 시각(10분 1회)뿐.

### 3.3 해시 vs 재표시
- 해시만 저장하면 URL은 발급 직후 1회만 보여 줄 수 있다. 카드가 "복사" 버튼을 상시 제공하려면 가역 저장이 필요하다.
- 가역 사본의 추가 위험은 작다: 인덱스 파일을 읽을 수 있는 공격자는 같은 호스트의 `running.db`(피드 원본 전체)도 읽을 수 있다. 그래도 평문 대신 기존 `credential_store`(Fernet, `CREDENTIAL_ENCRYPTION_KEY`)로 암호화해 백업·파일 유출 시 노출을 줄인다.
- 키 부재(개발 모드 평문 통과) 시 `token_enc=NULL`로 두고 UI는 "다시 보려면 재발급" 상태로 표시. 운영은 키 필수(기존 정책과 동일).
- 조회는 항상 `token_hash`로만. 복호화는 `GET /api/v1/data/calendar-feed`(본인 세션)에서만.

## 4. 공개 엔드포인트

### 4.1 경로와 인증 우회
- `GET|HEAD /feeds/cal/<token>.ics` — 새 블루프린트 `calendar_feed_bp`(`src/web/views_calendar_feed.py`).
- 운영자 조치(코드 밖): Cloudflare Access에 **`/feeds/cal/*` Bypass 정책** 추가. 없으면 Google이 CF 로그인 HTML을 받아 구독 실패. 체크리스트에 명시.
- `auth_cf._identify_user`: 맨 앞(세션 검사·로그보다 먼저)에서 `request.path.startswith("/feeds/cal/")`이면 `return None`. 세션을 읽지도 쓰지도 않는다 → 로그인한 브라우저로 열어도 **세션 사용자가 아니라 토큰 소유자 기준**, Set-Cookie도 발생하지 않음.
- 핸들러는 `db_path()`(세션 의존)를 쓰지 않고 `get_db_path(uid, create=False)` → 파일 없으면 404.

### 4.2 응답
| 상황 | 상태 | 본문 |
|---|---|---|
| 정상 | 200 | VCALENDAR |
| 내용 동일(If-None-Match 일치) | 304 | 없음 |
| 형식 불일치·미존재·해제·재발급된 구 토큰·DB 없음 | **404 동일 응답** | `Not Found` (구분 정보 없음, 열거 방지) |
| 레이트리밋 | 429 | `Retry-After` |
| 서버 오류 | 503 | 캘린더 앱이 기존 이벤트 유지하도록 빈 캘린더 대신 오류 |

헤더:
```
Content-Type: text/calendar; charset=utf-8
Content-Disposition: inline; filename="runpulse-plan.ics"
Cache-Control: private, no-cache        # CF·공유 캐시 저장 금지, 매번 재검증
ETag: "<sha256(body)[:32]>"             # 304 지원 (make_conditional)
Last-Modified: <max(planned_workouts.updated_at)>
X-Robots-Tag: noindex, nofollow
Referrer-Policy: no-referrer
X-Content-Type-Options: nosniff
```
- ETag가 의미 있으려면 본문이 결정적이어야 한다: `DTSTAMP`=행 `updated_at`(없으면 날짜 00:00Z), 현재 시각 금지. 이벤트는 날짜·슬롯 순 정렬.
- 갱신 힌트: `REFRESH-INTERVAL;VALUE=DURATION:PT6H`, `X-PUBLISHED-TTL:PT6H`. Apple/Outlook은 참고, **Google은 무시(실측 8~24시간+)** → UX 문구로 고지.

### 4.3 레이트리밋
- 전제: gunicorn `--workers 1`(Dockerfile). 프로세스 메모리 고정 창 카운터(`src/utils/rate_window.py`, 스레드 락).
  - 토큰별: 60회/시간 초과 시 429(정상 클라이언트는 시간당 수 회).
  - IP별 404: 20회/10분 초과 시 해당 IP 429 10분(추측 공격 억제; 256bit라 실효보다 소음 차단 목적). IP는 `CF-Connecting-IP` 우선, 메모리에만 보관.
- 워커를 늘리면 무력화 → 그때 CF WAF Rate Limiting 규칙(`/feeds/cal/*`, 120/10분/IP)으로 대체. 문서에 권고로 남김.

### 4.4 로그 리댁션
- 현재 gunicorn `--access-logfile -` 가 요청줄 전체를 남김 → 토큰이 로그에 기록됨. `src/web/gunicorn_logging.py`에 `glogging.Logger` 서브클래스(`RedactingLogger`)를 두고 `/feeds/cal/<...>` → `/feeds/cal/[redacted].ics`로 치환. Dockerfile CMD에 `--logger-class src.web.gunicorn_logging.RedactingLogger` 추가.
- 앱 로그: 핸들러는 경로·토큰을 절대 로그하지 않고 `user_id` 대신 `token_hash[:8]`만 debug로. `auth_cf`의 401 경고(`path=%s`)는 예외 처리가 앞서므로 도달하지 않음 — 테스트로 고정.
- 남는 위험: Cloudflare 엣지 로그·브라우저 기록·캘린더 업체 서버. 운영자 수용 위험으로 문서화.

## 5. 피드 내용 (유출 시 위험 범위)

원칙: **구조화 열에서 서버가 생성한 문자열만 싣는다. 자유 텍스트 열은 전부 제외.** 유출돼도 "어떤 날 어떤 종류 몇 km를 계획했다"까지만 알 수 있게 한다.

| 포함 | 제외 (이유) |
|---|---|
| 날짜(종일), 종류 한국어 라벨, 거리 km | `description`(수동 입력 가능 자유 텍스트) |
| 목표 페이스 범위 `m:ss–m:ss/km` | `rationale`(엔진/AI 설명), 세션 메모(`save_session_note`), AI 코치 코멘트 |
| 인터벌 처방 요약(`1000m × 5`, 구조화 필드에서 생성) | `skip_reason`, `completed`, `matched_activity_id`(이행 여부·실제 기록) |
| 목표 심박 **존 번호**(`Z2`)만 | 심박 bpm·역치·최대심박(개인 생체 기준값), 웰니스·수면·HRV 일체 |
| 대회일: `대회 42.2km` | 목표명·대회명·장소(특정 시각 위치 노출 → 신변 위험) |
| `X-WR-CALNAME:RunPulse 훈련 계획` | 이메일/user_id(UID·CALNAME 어디에도 넣지 않음) |

- 범위: 오늘 −28일 ~ 활성 계획 종료일(상한 +370일), 최대 500 이벤트. 휴식일 제외(기존 동작).
- 이벤트: `DTSTART;VALUE=DATE:D`, `DTEND;VALUE=DATE:D+1`, `UID:<date>-<slot>-<sha256(token_hash|date|slot)[:12]>@runpulse` — 계획 재생성(행 id 교체)에도 같은 날 같은 슬롯은 같은 UID → 캘린더 중복 방지. 토큰 교체 시 UID도 바뀌어 구 구독과 섞이지 않음.
- `SUMMARY:RunPulse · 템포 3.7km`, `DESCRIPTION:목표 4:33–4:48/km · Z3`, `TRANSP:TRANSPARENT`(바쁨 표시 안 함), `VALARM` 없음.
- 이스케이프(`\\ ; , \n`), 75옥텟 접기, CRLF.
- 빌더는 `src/services/calendar_feed_service.build_ics(conn, frm, to, uid_salt)` 하나로 두고 **기존 `/training/export.ics`도 같은 빌더로 전환**(경로·`week` 파라미터·첨부 다운로드 동작은 유지, 내용만 RFC 준수 + 동일 제외 기준). 기존 엔드포인트 유지 결정과 충돌 없음.

## 6. 인증 API 계약 (`/api/v1`, 세션 필수, `{data}`/`{error}` 포맷)

```
GET    /api/v1/data/calendar-feed
200 {"data": {"enabled": true,
              "url": "https://<host>/feeds/cal/rpcal_xxx.ics",     # enabled && 복호화 가능할 때만
              "webcal_url": "webcal://<host>/feeds/cal/rpcal_xxx.ics",
              "revealable": true,                                  # false면 '재발급해야 다시 볼 수 있어요'
              "created_at": "2026-10-08T09:00:00Z",
              "last_access_at": "2026-10-08T11:10:00Z" | null,
              "last_client": "google" | "apple" | "outlook" | "other" | null,
              "refresh_hint_hours": 6,
              "contents": ["날짜·종류·거리", "목표 페이스·심박 존", "인터벌 구성"],
              "excluded": ["메모·AI 설명", "심박 수치·웰니스", "완료 여부", "대회명·장소"]}}
200 {"data": {"enabled": false, ...contents, excluded}}

POST   /api/v1/data/calendar-feed        body {"rotate": false}
201 {"data": <위와 동일, 새 url>}
409 {"error": {"code": "FEED_EXISTS", "message": "이미 구독 주소가 있어요"}}   # 존재 + rotate=false (더블클릭 방지)
POST   ... body {"rotate": true}  → 201, 구 URL 즉시 404

DELETE /api/v1/data/calendar-feed        → 204 (없어도 204, 멱등)
```
- 호스트: 기존 `_PUBLIC_BASE_URL`(`views_settings_integrations.py`, Strava 콜백에 사용 중)을 공용 헬퍼로 끌어올려 사용. 미설정 시 `request.url_root`(개발용). CF 뒤 `http://` 오인 방지.
- 응답에 `Cache-Control: no-store`(URL 자체가 비밀).
- 라우트 파일: `src/api/routes_data_calendar.py` (`api/__init__.py` import 목록에 추가).

## 7. 프론트 UX (`/data/export` 카드 ③ 확장)

기존 `.ics 다운로드` 링크는 유지하고 같은 카드 안에 구독 블록을 둔다. 컴포넌트 `frontend/src/lib/components/data/CalendarFeedCard.svelte`, API `frontend/src/lib/api/calendarFeed.ts`.

- 미발급: 제목 `캘린더 앱에서 구독` / 본문 `구글·애플 캘린더에 주소를 등록하면 계획이 바뀔 때 자동으로 반영돼요.` / 버튼 `[구독 주소 만들기]`.
- 발급됨:
  - 읽기 전용 입력칸(가운데 말줄임 `…/feeds/cal/rpcal_ab…x9.ics`) + `[주소 복사]` → 토스트 `주소를 복사했어요. 다른 사람과 공유하지 마세요.` 클립보드 불가 시 입력칸 전체 선택으로 폴백.
  - `[Apple 캘린더에 추가]`(webcal 링크) · `Google 캘린더 추가 방법 ›`(설정 › 다른 캘린더 › URL로 추가 안내 2줄).
  - 상태 줄: `마지막으로 가져간 곳: Google · 2시간 전` / 없으면 `아직 가져간 앱이 없어요`. 모르는 앱이 가져가면 유출 의심 단서가 된다.
  - 고지 줄: `Google 캘린더는 반영까지 최대 하루 걸릴 수 있어요.` + `담기는 정보 ›`(contents/excluded 펼침).
  - 보조 동작: `주소 다시 만들기…` · `구독 끊기…`(텍스트 버튼).
- 확인 대화상자(기존 `ConnectPanel`의 인라인 `role="alertdialog"` 패턴 재사용):
  - 재발급: `지금 주소는 바로 쓸 수 없게 돼요. 이 주소를 등록한 캘린더마다 새 주소로 다시 등록해야 해요.` [다시 만들기] [취소]
  - 해제: `구독 주소를 없애요. 등록한 캘린더에는 더 이상 새 계획이 반영되지 않아요(이미 받은 일정은 앱에 남을 수 있어요).` [구독 끊기] [취소]
- `revealable=false`: 입력칸 대신 `보안상 주소를 다시 보여 줄 수 없어요. 새로 만들면 복사할 수 있어요.` + [주소 다시 만들기…].
- 설정 화면 진입점: 요구사항의 "설정 화면에서 재발급"은 `/data/export` 카드 내 동작으로 충족(설정 › 고급에 별도 행을 두지 않음 — 같은 기능 2곳 금지 원칙, 592행 #8과 동일 기준). 사용자 결정 필요 시 링크만 추가.

## 8. 테스트 목록

`tests/test_calendar_feed_service.py` (빌더, ~10)
1. 휴식일 제외, 종일 `DTEND`=다음날 2. `UID`·`DTSTAMP` 존재·결정적(두 번 생성 바이트 동일) 3. 이스케이프(`,;\` 줄바꿈) 4. 75옥텟 접기(한글 다바이트 경계) 5. **제외 필드 미포함**: description/rationale/skip_reason/세션메모/bpm/목표명 문자열을 심은 픽스처에서 본문에 없음 6. 존 번호·페이스 범위 포맷 7. 범위 −28일~종료, 500 상한 8. 계획 없음 → 이벤트 0인 유효 VCALENDAR 9. 재생성(행 id 변경) 후 UID 동일 10. CALNAME/UID에 user_id·이메일 없음.

`tests/test_calendar_feed_index.py` (인덱스, ~7)
1. 발급 → 해시 조회로 uid 반환 2. 재발급 시 구 토큰 조회 None(원자) 3. 해제 후 None 4. DB에 평문 토큰 없음(파일 바이트 검색) 5. 키 없음 → `token_enc` NULL·`revealable=false` 6. 접근 시각 10분 억제 7. UA 족 분류.

`tests/test_calendar_feed_routes.py` (공개+API, ~14)
1. 운영 모드(CF 헤더 없음)에서 공개 경로 200 2. 다른 사용자 세션 쿠키로 열어도 토큰 소유자 피드 3. 응답에 Set-Cookie 없음 4. 잘못된/구/해제 토큰 모두 동일 404 본문 5. If-None-Match → 304 6. 헤더(Cache-Control·Content-Type·X-Robots-Tag) 7. 토큰별 429 + Retry-After 8. IP별 404 반복 → 429 9. **caplog에 토큰 문자열 없음**(성공·404·429) 10. 사용자 DB 없음 → 404, 디렉터리 생성 안 함 11. GET/POST/DELETE 계약, POST 409 `FEED_EXISTS` 12. rotate 후 구 URL 404 13. API 응답 `no-store` 14. 기존 `/training/export.ics` 첨부 응답 유지 + 새 빌더 사용.

`tests/test_gunicorn_logging.py` (~2): 리댁션 치환, 다른 경로 불변.
`tests/test_export_service.py` 추가 1: 아카이브에 calendar_feeds·토큰 미포함.
프론트: `CalendarFeedCard` 상태 3종(미발급/발급/revealable=false) 렌더, 확인 대화상자 흐름 — 브라우저 스모크(메모리 규칙: 실제 페이지 확인) 포함.

## 9. 대안과 트레이드오프

| 대안 | 기각 이유 |
|---|---|
| 사용자 DB `user_settings`에 토큰 | 토큰→사용자 조회 불가. `set_setting` 화이트리스트가 enum 값 전용이라 구조도 안 맞음 |
| 전 사용자 DB 순회 조회 | 사용자 수 비례 I/O, 테스트 디렉터리까지 열림, 타이밍 차 |
| 무상태 암호화 토큰(`Fernet(uid, ver)`) | 폐기용 버전 카운터 저장 필요(결국 상태), 서버 키 교체=전원 무효, URL 길이 ~140자 |
| 해시만 저장(1회 표시) | 가장 안전하나 "복사" 상시 제공 불가. 추가 위험이 작아 기각, 키 없을 때 자동 폴백으로만 사용 |
| 토큰을 쿼리스트링(`?t=`) | 로그·리퍼러 노출이 경로와 동일, 일부 캘린더가 쿼리 제거 → 경로 방식 |
| `/api/v1/` 하위 공개 경로 | 세션 전제 블루프린트 훅(`_refresh_today_metrics` 등)과 섞이고 CF Bypass 범위가 넓어짐 |
| 사용자 다중 피드(기기별) | 1인 단일 사용 맥락에서 과설계. 테이블 PK만 바꾸면 확장 가능 |
| CalDAV 푸시(기존 `/training/push-caldav`) | 사용자가 CalDAV 서버 설정 필요, Google 미지원 — 병존 |

## 10. 구현 슬라이스와 파일

| 슬라이스 | 내용 | 파일 |
|---|---|---|
| C1 빌더 | RFC 준수 ICS 빌더 + 제외 기준, 기존 다운로드 전환 | 신규 `src/services/calendar_feed_service.py`, 수정 `src/web/views_training_export.py`, 신규 `tests/test_calendar_feed_service.py` |
| C2 인덱스 | 전역 DB·발급/재발급/해제/조회·Fernet | 신규 `src/services/calendar_feed_index.py`, (credential_store에 단일 값 암복호 헬퍼 추가 필요 시) 수정 `src/utils/credential_store.py`, 신규 `tests/test_calendar_feed_index.py` |
| C3 공개 경로 | 블루프린트·auth_cf 예외·레이트리밋·헤더 | 신규 `src/web/views_calendar_feed.py`, `src/utils/rate_window.py`, 수정 `src/web/auth_cf.py`, `src/web/app.py`(등록), 신규 `tests/test_calendar_feed_routes.py` |
| C4 로그 | gunicorn 리댁션 로거 | 신규 `src/web/gunicorn_logging.py`, 수정 `Dockerfile`, 신규 `tests/test_gunicorn_logging.py` |
| C5 API | GET/POST/DELETE, 공용 base URL 헬퍼 | 신규 `src/api/routes_data_calendar.py`, 수정 `src/api/__init__.py`, `src/web/views_settings_integrations.py`(헬퍼 이동) |
| C6 UI | 카드·확인 대화상자·토스트 | 신규 `frontend/src/lib/api/calendarFeed.ts`, `frontend/src/lib/components/data/CalendarFeedCard.svelte`, 수정 `frontend/src/routes/data/export/+page.{ts,svelte}` |
| C7 문서·운영 | ADR-032 기록, CF Bypass 체크리스트, 파일 인덱스 | `v0.3/data/decisions.md`, `scripts/gen_files_index.py` 실행 |

순서: C1 → C2 → C3+C4(같은 PR, 로그 리댁션 없이 공개 경로 배포 금지) → C5 → C6 → C7. 운영 배포 전 CF `/feeds/cal/*` Bypass 적용·Google 실제 구독 1회 확인.

## 11. 검증 항목 (DoD)

1. 운영 모드에서 CF 헤더·쿠키 없이 피드 200, 다른 경로는 여전히 401.
2. 재발급 직후 구 URL 404, 새 URL 200.
3. gunicorn 접근 로그·앱 로그·caplog 어디에도 토큰 원문 없음.
4. 피드 본문에 §5 제외 항목 0건(픽스처 기반 테스트).
5. 동일 데이터 재요청 시 304, ETag 불변.
6. `calendar_feeds.db`에 평문 토큰 없음, 아카이브 zip에 미포함.
7. Google·Apple 캘린더 실구독 스모크(이벤트 표시, 중복 없음, 계획 변경 반영).
8. `python3 -m pytest tests/` 전체 통과, `scripts/check_docs.py` 통과.

## 12. 사용자 결정 필요

- (D1) 재표시 허용(Fernet 사본) vs 1회 표시(해시만). 추천: 재표시.
- (D2) 대회일 이벤트에 목표명 포함 여부. 추천: 제외(기본), 필요 시 후속 토글.
- (D3) 재발급·해제 진입점을 `/data/export` 카드로 한정할지, 설정 › 고급에도 링크를 둘지. 추천: 카드 한정.
- (D4) 과거 범위 −28일 적정성.
