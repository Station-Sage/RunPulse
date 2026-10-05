# DESIGN-U15 — 활동 피드백(3-10)·동기화 오류 표면화(#10) 확정 설계 (2026-10-05)

출처: `DESIGN-PENDING-12.md` §5·§10, `40-v2-unimplemented/design.md` §3.2·§7.2·§7.3·§8, `99-summary.md` D3·D5·D6.
상태: **설계 확정**(사용자 지시 "설계 모듈 돌려서 확정하고 진행"). 열린 질문 없음. 구현은 아래 U15a~U15j 순서로 한다.
근거 표기: `파일:줄`은 이번 조사에서 직접 확인했다.

---

## 0. 확정 결정 요약

| # | 결정 | 근거 |
|---|---|---|
| F1 | 활동별 입력은 **신규 `activity_feedback` 테이블**(활동 1:1)에 둔다. `user_inputs`는 그대로 둔다 | `user_inputs`는 `UNIQUE(input_date, input_type)`(`src/db_setup.py:439-451`)라서 같은 날 활동 2개를 구분할 수 없다. 재생성(B안)을 하면 체크인 경로(`today_service`·`plan_service`·`adaptation_service`·`chat_context_checkin`)가 영향을 받는다. `metric_store`(C안)에는 텍스트(note·부위)가 섞인다 |
| F2 | RPE는 **정수 1–10**(Foster CR-10 변형, 0 없음)이고 DDL CHECK로 강제한다 | session-RPE(RPE×분) 부하 대체 시 바로 쓸 수 있는 척도다. 0은 "입력 안 함"과 구분할 수 없어 NULL로 표현한다 |
| F3 | 통증 정도는 `pain TEXT`이고 프론트 `PainLevel`(`none/mild/moderate/severe`, `frontend/src/lib/types/index.ts:12`)과 같은 값을 쓴다. 검증은 서비스 상수로 하고 DDL CHECK는 두지 않는다 | 체크인과 같은 어휘라서 QuickInput을 재사용할 수 있다. 열거값이 바뀌어도 테이블을 재작성하지 않아도 된다 |
| F4 | 통증 부위는 **포함**한다. `pain_sites TEXT`(JSON 배열)이고 고정 슬러그 12개 중 최대 3개다 | 부상 패턴(같은 부위 반복)을 코치·리스크에서 쓰려면 자유 텍스트가 아닌 슬러그가 필요하다 |
| F5 | 키는 **캐노니컬 activity_id**다. 쓸 때는 캐노니컬로 정규화한다. 읽을 때는 현재 그룹(`activity_summaries.matched_group_id`) 구성원 id 중 `updated_at`이 가장 최근인 행을 쓴다 | 재매칭으로 캐노니컬이 바뀌어도 입력을 잃지 않는다. FK 제약은 두지 않는다(스키마 전체 관례, `db_setup.py:436-438`) |
| F6 | 메모는 500자 이하다. 코치 전송은 `coach_consent`의 메모 제외 토글을 따른다. RPE·통증 정도·부위는 활동 컨텍스트에 포함한다 | D8 동의 정책과 일관된다 |
| F7 | 이번 범위에서는 CalcContext API를 **추가하지 않는다**. 이름 `get_activity_feedback(activity_id)`만 ADR로 예약한다 | 소비 Calculator가 아직 없다(YAGNI). ADR-009에 따라 Calculator가 raw SQL로 읽는 길은 막아 둔다 |
| F8 | `⋯` 메뉴는 4항목이다: 메모·RPE 기록 / 원본 열기(소스별, 읽기 전용) / GPX 내려받기 / 코치에게 묻기(기존). **DB 쓰기는 피드백 하나뿐이다** | 원본 열기와 GPX는 조회 전용이라 운영 DB 위험이 없다 |
| F9 | GPX 범위: **단일 활동, GPX 1.1, 서버에서 생성해 스트림으로 응답**한다(파일 저장 없음). 위치 정보가 없으면(트레드밀 등) 항목을 비활성화하고 사유를 보여 준다. 일괄·TCX·FIT·아카이브는 40 §7.3 export 작업으로 넘긴다 | 원장 작업이 필요 없는 범위로 한정한다. `activity_streams`에 latitude·longitude·altitude_m·heart_rate·cadence가 있다(`db_setup.py:205-222`) |
| S1 | **원장 SSOT는 `sync_jobs.db`**(`src/utils/sync_jobs.py:112-149`, 별도 파일)다. 4경로가 모두 여기에 쓴다. `running.db`의 `sync_jobs`(`db_setup.py:395-409`, orchestrator 전용)는 **동결**(신규 쓰기 중단, 열 추가 없음, DROP은 별도 ADR)한다 | `sync_state_service`·대시보드·`get_last_sync_at`이 이미 `sync_jobs.db`를 읽는다. 원장이 두 개면 "마지막 성공"이 둘로 갈린다(40 §8 첫 수용 기준 위반) |
| S2 | `sync_jobs.db.sync_jobs`에 `error_code TEXT`, `http_status INTEGER`, `source_path TEXT`를 추가한다(추가형, 연결 시 멱등 ALTER). 상태 열거에 `failed`를 추가한다 | 문자열 매칭(`sync_state_service.py:22-28`)으로 오류를 분류하던 방식을 열 값 기반으로 바꾼다 |
| S3 | `source_path ∈ {manual, bg, auto, cli}`이다. 40 설계의 `trigger`(range/onboarding/system)는 4-1에서 같은 열의 값만 늘린다 | 4경로 식별이 이번 목표다. 열을 하나만 두어 중복을 막는다 |
| S4 | 오류 분류 SSOT는 신규 `src/sync/sync_errors.py`다. 코드는 `auth_expired`(401)·`subscription_required`(403)·`rate_limited`(429)·`upstream_5xx`·`timeout`·`network`·`parse`·`unknown`이다 | 40 §3.2 상태 기계와 §8 수용 기준(403 → `subscription_required`)에 맞춘다. 기존 코드 `forbidden`은 폐기하고 폴백 매핑만 남긴다 |
| S5 | **Strava 403 근본 원인**은 두 가지다. ① `src/sync/strava.py:29-39` 래퍼가 `SyncResult`를 버리고 `synced_count`(0)만 반환한다. ② `strava_activity_sync.py:67`이 `HTTPError`의 상태 코드를 버린다. 수정 방법은 다음과 같다. 소스 동기화 결과가 `failed`이면 레거시 래퍼 4종이 `SyncSourceError(code, http_status, message)`를 raise하고, 모든 경로가 이를 원장 `failed`로 기록한다 | bg 루프(`bg_sync.py:192`)는 예외가 없으면 무조건 `completed`로 기록한다 |
| S6 | 과거에 `completed, count=0`으로 남은 행은 **소급 수정하지 않는다**. 원장은 사실 기록이고 원인을 재판정할 수 없기 때문이다. 다음 실행부터 `failed`가 남는다 | 데이터 조작을 피한다 |
| S7 | `user_settings(key PK, value_json, updated_at)` key-value 테이블을 **running.db에 둔다**(DB가 사용자별 파일이다, `db_setup.py:39-49`). 허용 키는 서비스 화이트리스트로 관리하며 이번에는 `ui_default`만 둔다. 전역 롤백 값 `ui_default_global`은 **config.json 1줄**(재배포 없이 컨테이너 재시작으로 반영)이다 | D6이다. 사용자 설정은 DB, 운영자 스위치는 config로 나눈다. `user_training_prefs`에 섞지 않는다(B안 기각). config 단독(C안)은 기기·사용자 단위 저장이 불가하다 |
| M1 | running.db는 **SCHEMA_VERSION 24 → 25** 한 번(`activity_feedback`+`user_settings`)으로 묶는다. 백업과 사본 검증은 1회만 한다 | 운영 DB를 변경하는 횟수를 줄인다 |

---

## 1. U15-A 활동 피드백

### 1.1 DDL (`src/db_schema_v25.py`, create_tables에서 `ensure_v25` 호출)

```sql
-- ADR-022: 활동별 주관 입력. user_inputs(날짜 체크인)와 분리. FK 없음(스키마 관례).
CREATE TABLE IF NOT EXISTS activity_feedback (
    activity_id  INTEGER PRIMARY KEY,               -- 쓰기 시점 캐노니컬 id
    rpe          INTEGER CHECK (rpe IS NULL OR rpe BETWEEN 1 AND 10),
    pain         TEXT,                              -- none|mild|moderate|severe (서비스 검증)
    pain_sites   TEXT,                              -- JSON 배열, 슬러그 ≤3
    note         TEXT CHECK (note IS NULL OR length(note) <= 500),
    created_at   TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at   TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_actfb_updated ON activity_feedback(updated_at);

-- ADR-023(S7): 사용자 UI 설정 key-value
CREATE TABLE IF NOT EXISTS user_settings (
    key         TEXT PRIMARY KEY,
    value_json  TEXT NOT NULL,
    updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
);
```
- `pain_sites` 슬러그(서비스 상수 `PAIN_SITES`)는 `foot, ankle, achilles, calf, shin, knee, it_band, hamstring, quad, hip, lower_back, other`다.

### 1.2 서비스 `src/services/activity_feedback_service.py` (목표 ≤180줄)

```python
PAIN_LEVELS = ("none", "mild", "moderate", "severe")
PAIN_SITES = (...)           # 위 12개
NOTE_MAX = 500

class FeedbackError(ValueError): code: str   # INVALID_RPE|INVALID_PAIN|INVALID_SITE|NOTE_TOO_LONG

def validate(payload: dict) -> dict            # 정규화(빈 문자열→None, 부위 중복 제거·정렬)
def get_feedback(conn, activity_id: int) -> dict | None
    # 그룹 구성원 id 목록 → activity_feedback IN (...) ORDER BY updated_at DESC LIMIT 1
def put_feedback(conn, activity_id: int, payload: dict) -> dict | None
    # 활동 없음 → LookupError. 정규화 후 모든 필드 None → 삭제하고 None 반환.
    # 캐노니컬로 정규화하고 UPSERT. 같은 그룹 다른 구성원 행은 삭제(그룹당 1행 유지).
def delete_feedback(conn, activity_id: int) -> bool
def feedback_for_activities(conn, ids: list[int]) -> dict[int, dict]   # 목록 배지·코치용 일괄 조회
```
- 캐노니컬 판정은 `src/utils/canonical.py`를 재사용한다. 서비스 계층이라 SQL을 써도 된다(ADR-009는 Calculator에만 적용).
- 응답 형태는 `{activity_id, rpe, pain, pain_sites:[...], note, updated_at}`다.

### 1.3 API — 신규 라우트 파일 2개

`src/api/routes_library.py`는 이미 315줄이라 손대지 않는다. 등록 방식은 `routes_library_activities.py`(36줄)와 같은 `api_bp` 패턴을 따른다. 피드백은 `routes_library_feedback.py`(≤100줄), 원본·GPX는 `routes_library_export.py`(≤90줄)에 둔다.

| 메서드 | 경로 | 파일 | 응답 |
|---|---|---|---|
| GET | `/api/v1/library/activities/<int:id>/feedback` | feedback | `200 {feedback: {...}\|null}`. 활동 없음 `404 NOT_FOUND` |
| PUT | 같음, body `{rpe?, pain?, pain_sites?, note?}` | feedback | `200 {feedback}`(전부 비면 `null`). 검증 실패 `400 {code: INVALID_*}` |
| DELETE | 같음 | feedback | `204` |
| GET | `/api/v1/library/activities/<int:id>/source-links` | export | `200 {links:[{provider, url, label_ko}]}` |
| GET | `/api/v1/library/activities/<int:id>/export.gpx` | export | `200 application/gpx+xml`, `Content-Disposition: attachment; filename=runpulse-YYYYMMDD-<id>.gpx`. 위치 없음 `404 {code: NO_GPS}` |

활동 상세 응답(`activity_detail_service`)에는 `feedback`(1.2 `get_feedback`)과 `menu: {has_gps: bool, source_links: [...]}`를 추가한다. 상세 화면에서 추가 요청은 0회다. 단독 GET은 편집 후 재조회용이다.

### 1.4 원본 열기·GPX 서비스

- `src/services/activity_source_links.py`(≤80줄): 그룹 구성원마다 `(source, source_id)`로 URL을 만든다. URL 템플릿은 상수이고 읽기 전용이며 외부 호출은 없다.
  - garmin `https://connect.garmin.com/modern/activity/{sid}` · strava `https://www.strava.com/activities/{sid}` · intervals `https://intervals.icu/activities/{sid}` · runalyze `https://runalyze.com/activity/{sid}`
  - `source_id`가 비었거나 소스가 미지원이면 그 링크를 뺀다. 프론트는 `target=_blank rel="noopener noreferrer"`로 연다.
- `src/services/activity_gpx.py`(≤150줄): 그룹 구성원 중 `latitude IS NOT NULL` 점이 가장 많은 소스의 `activity_streams`를 쓴다. `time = start_time(UTC) + elapsed_sec`(Z 표기)이고, `ele`=altitude_m, `gpxtpx:TrackPointExtension`에 hr·cad를 넣는다. XML은 `xml.etree.ElementTree`로 생성한다(문자열 조립 금지, 이스케이프 보장). 위치 점이 10개 미만이면 `NO_GPS`다. DB 쓰기와 파일 저장은 없다.

### 1.5 프론트엔드

- `QuickInput.svelte`: `scope: 'day' | 'activity'` prop을 추가한다(기본 `'day'`라서 기존 호출부는 바뀌지 않는다). `activity`일 때 피로·기분 대신 RPE 1–10 세그먼트(라벨 1 매우 쉬움 / 5 보통 / 7 힘듦 / 10 최대)와 통증 부위 칩(통증 ≠ none일 때만, 최대 3)을 보여 준다. `onSave` 계약은 그대로이고 payload만 scope별로 다르다. 활동용 필드는 처음부터 `QuickInputActivityFields.svelte`로 분리한다(300줄 규칙 선제 대응).
- 신규 `ActivityMoreMenu.svelte`: `⋯` 버튼, 시트/팝오버, 항목 4개(F8), 탭 영역 ≥44px. GPX는 `has_gps=false`면 비활성화하고 "위치 기록이 없는 활동이에요"를 보여 준다.
- 신규 `frontend/src/lib/api/activityFeedback.ts`: get/put/delete. 저장하면 활동 상세 캐시를 무효화한다.
- 활동 목록 행: RPE가 있으면 작은 배지(`RPE 7`)를 표시한다. 데이터는 목록 API가 `feedback_for_activities`로 일괄 제공한다(N+1 금지).

### 1.6 코치 연동

`src/services/coach_activity_context.py`가 활동 컨텍스트에 `rpe·pain·pain_sites`를 싣는다. `note`는 `coach_consent`의 메모 제외 토글(`checkin_notes=false`)이면 뺀다. 체크인 메모 정책과 같다.

---

## 2. U15-B 설정·원장 확장·오류 표면화

### 2.1 현재 4경로 실측

| 경로 | 진입 | 실행 | 현재 기록 | 문제 |
|---|---|---|---|---|
| manual | `POST /trigger-sync`, `/trigger-sync-stream`(`src/web/app.py:489,677`) | subprocess `src/sync.py --source --days --user`(`app.py:612`) → 레거시 `sync_garmin/strava/...` | `sync_state.json`(`mark_finished`)만 | 원장 행 없음. 오류는 stderr 꼬리 문자열로만 남음 |
| bg | `POST /trigger-sync-bg`(`app.py:850`) → `BgSyncThread` | 레거시 `sync_activities`(`bg_sync.py:299-`) | `sync_jobs.db` | 래퍼가 int만 반환해서 403이어도 `completed`(`bg_sync.py:192`) |
| auto | `auto_sync._trigger` → `start_basic_sync`(`auto_sync.py:33-49`) | bg와 같음 | `sync_jobs.db` | bg와 구분되지 않음 |
| cli | `python3 src/sync.py`(수동과 같은 코드), `src/sync_cli.py sync` → `orchestrator.full_sync` | 신규 `*_activity_sync.sync`(SyncResult) | `src/sync.py`는 없음. `sync_cli`는 **running.db** `sync_jobs`(`orchestrator.py:101`) | 원장이 갈라짐 |

부수 발견: `src/utils/db_status.py:60`은 running.db `sync_jobs`에 없는 `started_at` 열을 조회한다(현재 깨짐). `views_training_loaders.py:343`도 running.db 테이블을 읽는다. 둘 다 U15h에서 원장 리더로 바꾼다.

### 2.2 `sync_jobs.db` 스키마 확장 — 신규 `src/utils/sync_jobs_schema.py` (≤60줄)

`sync_jobs.py`(257줄)의 `_conn()` 안 CREATE를 이 모듈로 옮기고 열 보장을 추가한다.

```python
LEDGER_COLUMNS = {"error_code": "TEXT", "http_status": "INTEGER", "source_path": "TEXT"}
_ensured: set[str] = set()   # 경로별 1회만 PRAGMA (연결마다 반복 방지)

def ensure_ledger(conn, path: str) -> None:
    conn.execute(CREATE_SQL)                                    # 기존 15열 그대로
    if path in _ensured: return
    cols = {r[1] for r in conn.execute("PRAGMA table_info(sync_jobs)")}
    for name, decl in LEDGER_COLUMNS.items():
        if name not in cols:
            conn.execute(f"ALTER TABLE sync_jobs ADD COLUMN {name} {decl}")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_sync_jobs_service ON sync_jobs(service, created_at)")
    _ensured.add(path)
```
- `SyncJob` dataclass에 `error_code`, `http_status`, `source_path`를 추가한다(기본값 None, 끝에 추가). `_COLS`는 18열이 된다. `create_job(..., source_path=)` 인자를 추가한다.
- 상태 열거는 `pending/running/paused/stopped/completed/rate_limited/auth_required/failed`다. `auth_required`는 호환용으로 유지하고 `error_code=auth_expired`를 함께 기록한다.
- `sync_jobs.db`는 `SCHEMA_VERSION` 관리 대상이 아니다. 열 존재 검사 기반 멱등 ALTER가 유일한 마이그레이션이다.

### 2.3 오류 분류 — 신규 `src/sync/sync_errors.py` (≤120줄)

```python
class SyncSourceError(Exception):
    def __init__(self, code: str, message: str, http_status: int | None = None): ...

ERROR_CODES = ("auth_expired", "subscription_required", "rate_limited",
               "upstream_5xx", "timeout", "network", "parse", "unknown")

def classify_exception(exc: BaseException) -> tuple[str, int | None]:
    # requests.HTTPError → status: 401→auth_expired, 403→subscription_required,
    #   429→rate_limited, ≥500→upstream_5xx, 그 외 4xx→unknown
    # requests.Timeout→timeout, requests.ConnectionError→network,
    # ValueError/JSONDecodeError/KeyError→parse, 그 외→unknown

def from_result(result: SyncResult) -> SyncSourceError | None:
    # status=='failed' and synced_count==0 → 예외 객체, 아니면 None

MESSAGES_KO = {code: (message_ko, action)}   # action: reconnect|disable|wait|retry
```
- `SyncResult`(65줄)에 `error_code: str | None`, `http_status: int | None`를 추가한다(`merge`는 마지막 값을 쓴다). `to_sync_job_dict`도 함께 확장한다.
- `strava_activity_sync.py:67`: `except requests.HTTPError as e:`로 바꾸고 `result.error_code, result.http_status = classify_exception(e)`, `last_error`에 `"Strava {status}: ..."`를 넣는다. intervals·runalyze·garmin 신규 sync 모듈의 목록 조회 실패 지점에도 같은 패턴을 적용한다(각 1곳).
- 레거시 래퍼 4종(`src/sync/strava.py:29`, `intervals.py:28`, `runalyze.py:57`, `garmin.py:56`)은 내부 `SyncResult`에서 `from_result()`가 객체를 돌려주면 raise한다. `runalyze.py:103-106`의 403 전용 `mark_finished` 분기는 raise로 바꾼다. 24시간 대기 정책은 `retry_after`로 유지한다.
- **부분 실패**(동기화 n>0 + 오류)는 raise하지 않는다. 원장 `completed`에 `error_code`를 남기고 상태 서비스가 `done-new`에 경고 꼬리표를 붙인다.

### 2.4 원장 기록 진입점 — 신규 `src/sync/ledger.py` (≤120줄)

```python
def start_run(service, from_date, to_date, *, source_path, job_id=None, user_id=None) -> str
def finish_run(job_id, *, synced: int, error: SyncSourceError | None = None,
               partial_code: str | None = None) -> None
    # error 있음 → status='failed', error_code, http_status, last_error=message[:300]
    # 없음 → status='completed' (+ partial_code가 있으면 error_code만 기록)
def fail_run(job_id, code, message, http_status=None) -> None   # 부모 프로세스용(타임아웃 등)
```
`src/utils/sync_jobs.py`의 `create_job`/`update_job` 위에 얇게 얹는다. **원장 쓰기는 이 모듈과 `bg_sync`만** 한다.

### 2.5 경로별 배선

| 경로 | 변경 |
|---|---|
| manual | `app.py`가 부모에서 `job_id=uuid4()`를 만들고 subprocess 인자에 `--job-id <id> --trigger manual`을 추가한다. `src/sync.py._sync_source`는 `start_run(job_id=…)` 후 `finish_run`을 호출한다(SyncSourceError를 잡아 기록). 부모는 타임아웃·returncode≠0이면 `fail_run(job_id, "timeout"\|"unknown", stderr_tail)`을 호출한다(이미 failed면 덮어쓰지 않는다). `app.py`(1384줄)에는 **인자 2개·호출 2줄만** 추가하고(수동 경로 2곳 각각) 로직은 `ledger`에 둔다 |
| bg | `_run_one_batch`에서 `SyncSourceError`를 잡으면 `update_job(status='failed', error_code, http_status, last_error)` 후 루프를 종료한다. `completed` 분기(`bg_sync.py:192`)에는 오류 없이 끝난 경우만 도달한다. `create_job(source_path='bg')` |
| auto | `start_basic_sync(..., source_path='auto')` 인자를 추가하고 `auto_sync._trigger`가 전달한다 |
| cli | `src/sync.py` 직접 실행 시 `--trigger` 기본값은 `cli`다. `orchestrator.full_sync`는 `record_sync_job`(running.db) 대신 `ledger.start_run/finish_run(source_path=…)`을 쓴다(`sync_cli`는 `cli`를 넘긴다). `src/sync/_helpers.py:record_sync_job`은 삭제한다(`tests/test_orchestrator.py` 6곳은 원장 리더로 수정) |

`mark_finished`(sync_state.json)는 **이번에 제거하지 않는다**. retry_after·rate_state 저장소로 남겨 두고 "마지막 성공" 판정에서는 이미 원장이 우선한다(`sync_state.py:115-131`). json 제거는 4-1이다.

### 2.6 상태 서비스 — `src/services/sync_state_service.py` (163줄)

- `classify_error(job)`: `job.error_code`가 있으면 `MESSAGES_KO[error_code]`로 `{code, message_ko, action, http_status, source_path, at}`를 만든다. 없으면(과거 행) 기존 `_ERROR_RULES` 문자열 규칙을 폴백으로 쓰고 `forbidden`은 `subscription_required`로 매핑한다.
- 상태명은 40 §3.2에 맞춘다: `auth_expired → error-auth`, `subscription_required → error-access`, `rate_limited/upstream_5xx/timeout/network/parse/unknown → error-upstream`.
- `failed`는 성공 후보에서 제외한다(`completed`만 성공).
- 분류표는 `sync_errors.py`로 옮겨 이 파일 줄 수를 유지한다.
- 프론트 표면(☰ 배지·Data 행·토스트)은 기존 4-1 범위다. 이번 단위의 계약은 `GET /api/v1/data/sync-state` 응답의 `state`·`last_error`까지다.

### 2.7 사용자 설정 — `src/services/user_settings_service.py` (≤80줄) + `src/api/routes_me.py` (≤60줄)

```python
ALLOWED = {"ui_default": ("v1", "v2")}
def get_setting(conn, key, default=None); def set_setting(conn, key, value)   # 화이트리스트 밖이면 ValueError
def resolve_ui_default(conn, config) -> str   # 사용자 값 → config["ui_default_global"] → "v1"
```
- API: `GET /api/v1/me/preferences` → `{ui_default, ui_default_global}`, `PATCH`는 `{ui_default}`를 받고 잘못된 값이면 400이다.
- `/` 분기(`app.py:305-307`) 연결과 드로어 링크는 2-3(G0) 작업이다. **이번에는 저장소와 API만 만든다.** `config.json.example`에 `"ui_default_global": "v1"` 1줄을 추가한다(config.json은 커밋 금지).

---

## 3. 마이그레이션·운영 DB 절차

### 3.1 코드 측 멱등성

- running.db: `SCHEMA_VERSION = 25`. `ensure_v25(conn)`는 `CREATE TABLE/INDEX IF NOT EXISTS`만 실행하고 `create_tables()`에서 `ensure_v24` 다음에 호출한다(`db_setup.py:729-730` 패턴). `migrate_db` docstring에 `v25` 줄을 추가한다. 기존 테이블은 변경하지 않는다.
- sync_jobs.db: `ensure_ledger`가 열 존재 검사 후 ALTER한다(2.2).
- **롤백 안전성**: 두 변경 모두 추가형이다. v24 코드가 v25 DB를 열면 `current >= SCHEMA_VERSION`(`db_setup.py:814`)이라 무시하고, 새 테이블과 열을 읽지 않으므로 **코드만 되돌려도 동작한다**. 단, v24 코드의 `sync_jobs.py`는 `SELECT {15열}`을 명시하므로 추가 열과 충돌하지 않는다. DB 복원은 데이터 손상 시에만 한다.

### 3.2 운영 절차 (OCI docker 컨테이너, 사용자 DB 디렉터리 `data/users/<uid>/`)

1. **정지 조건 확인**: `GET /api/v1/data/sync-state`에 `running`이 없음을 확인한다. auto_sync 다음 실행까지 30분 이상 남은 시각을 고른다.
2. **백업**(컨테이너 안, WAL 일관성 보장을 위해 `cp` 대신 온라인 백업 사용):
   ```bash
   D=data/users/<uid>; T=$(date +%Y%m%d)
   sqlite3 $D/running.db   ".backup $D/running.db.bak-$T-pre-v25-feedback"
   sqlite3 $D/sync_jobs.db ".backup $D/sync_jobs.db.bak-$T-pre-ledger-v2"
   ```
3. **사본 검증**: 백업 사본을 `/tmp/u15/`에 복사하고 새 코드로 `migrate_db`와 `sync_jobs_schema.ensure_ledger`를 사본에만 실행한다. 확인 항목은 다음과 같다.
   - `PRAGMA user_version` = 25, `PRAGMA integrity_check` = ok
   - `activity_feedback`·`user_settings` 존재. `PRAGMA table_info(sync_jobs)`(sync_jobs.db)에 3열 추가
   - 기존 테이블 행 수 전후 동일(activity_summaries·metric_store·user_inputs·sync_jobs)
   - 같은 스크립트를 2회 실행해도 오류 없음(멱등)
4. **배포**: 컨테이너를 재시작하면 앱 시작 시 `init_db → migrate_db`가 실행된다. 로그에서 `스키마 마이그레이션: v24 → v25`를 확인한다. sync_jobs.db는 첫 원장 연결 시 ALTER된다.
5. **운영 스모크**: 피드백 PUT/GET 1건 후 DELETE(테스트 흔적 제거), Strava 수동 동기화 1회 → 원장 `status=failed, error_code=subscription_required, http_status=403, source_path=manual` 확인, Data/셸 상태 `error-access` 확인(브라우저 390·1280).
6. **롤백**: 기능 문제면 이전 이미지로 재시작한다(DB 유지, 3.1). 데이터 손상이면 컨테이너를 정지하고 `-wal/-shm`을 삭제한 뒤 백업 파일로 교체하고 재시작한다.
7. IMPL-PROGRESS에 백업 파일명과 반영 시각을 기록한다(기존 관례).

---

## 4. 구현 단위 (순서 = 의존 순)

| 단위 | 내용 | 신규/변경 파일 | 규모 |
|---|---|---|---|
| **U15a** | running.db v25 스키마 | 신규 `src/db_schema_v25.py`(≤40). 변경 `src/db_setup.py`(SCHEMA_VERSION·호출 2줄·docstring) | S |
| **U15b** | 피드백 서비스 + API | 신규 `src/services/activity_feedback_service.py`(≤180), `src/api/routes_library_feedback.py`(≤100). `src/api/__init__.py` import 1줄 | M |
| **U15c** | 원본 링크·GPX | 신규 `src/services/activity_source_links.py`(≤80), `src/services/activity_gpx.py`(≤150), `src/api/routes_library_export.py`(≤90). 변경 `activity_detail_service.py`(feedback·menu 필드) | M |
| **U15d** | 프론트 입력·메뉴 | 변경 `QuickInput.svelte`(scope). 신규 `QuickInputActivityFields.svelte`, `ActivityMoreMenu.svelte`, `lib/api/activityFeedback.ts`. 활동 상세·목록 배지 연결 | M |
| **U15e** | 코치 컨텍스트·목록 배지 데이터 | 변경 `coach_activity_context.py`, `activity_list_rows.py`(`feedback_for_activities`) | S |
| **U15f** | 오류 분류·SyncResult·레거시 래퍼 raise | 신규 `src/sync/sync_errors.py`(≤120). 변경 `sync_result.py`, `strava_activity_sync.py`, `strava.py`, `intervals.py`, `runalyze.py`, `garmin.py`(+ 각 신규 sync 모듈 목록 조회 실패 지점) | M |
| **U15g** | 원장 확장 + 4경로 배선 | 신규 `src/utils/sync_jobs_schema.py`(≤60), `src/sync/ledger.py`(≤120). 변경 `sync_jobs.py`, `bg_sync.py`, `auto_sync.py`, `src/sync.py`, `app.py`(인자·호출 최소), `orchestrator.py`, `_helpers.py`(record_sync_job 삭제) | M |
| **U15h** | 상태 서비스·리더 정리 | 변경 `sync_state_service.py`, `db_status.py`, `views_training_loaders.py`(원장 리더로) | S |
| **U15i** | 사용자 설정 저장소·API | 신규 `src/services/user_settings_service.py`(≤80), `src/api/routes_me.py`(≤60). 변경 `config.json.example` | S |
| **U15j** | 문서·검증·운영 반영 | `decisions.md` ADR-022·023, `architecture.md`·`phase_summary.md` 테이블 수(+2), 폴더 `__init__.py` docstring, `gen_files_index.py`, `check_docs.py`, `/check-data-consistency`, 3.2 운영 절차 | S |

- U15a~e(피드백)와 U15f~i(동기화)는 독립적이다. 다만 **운영 반영은 U15a와 U15g를 한 번에** 한다(백업 1회, M1).
- 파일 300줄 규칙: 신규 파일은 모두 ≤180줄로 설계했다. 기존 초과 파일(`app.py` 1384, `routes_library.py` 315, `bg_sync.py` 498)은 늘리지 않거나 최소 줄만 추가하고, 분리는 별도 정리 항목으로 둔다.

---

## 5. 테스트 계획

| 파일 | 내용 | 예상 수 |
|---|---|---|
| `tests/test_db_schema_v25.py` | v24 DB → v25, 2회 실행 멱등, user_version=25, rpe CHECK(0·11 거부), note 501자 거부, 기존 테이블 행 수 불변 | 6 |
| `tests/test_activity_feedback_service.py` | 정상 upsert, 같은 날 활동 2개 독립, 전부 빈 값 → 삭제, 잘못된 pain/site/부위 4개 거부, 그룹 구성원 id로 조회(재매칭 후 유지), 캐노니컬 정규화 시 비캐노니컬 행 정리, 일괄 조회 | 9 |
| `tests/test_api_activity_feedback.py` | GET 없음→null, 활동 없음 404, PUT 200, PUT 400(code), DELETE 204, 상세 응답에 feedback·menu 포함 | 6 |
| `tests/test_activity_source_links.py` | 4소스 URL, source_id 없음 제외 | 3 |
| `tests/test_activity_gpx.py` | 유효 GPX 1.1(파싱·trkpt 수·시간 Z), hr 확장, 위치 없음 NO_GPS, 위치 점 최다 소스 선택, 특수문자 이름 이스케이프 | 5 |
| `tests/test_sync_errors.py` | 401/403/429/503/418, Timeout, ConnectionError, JSONDecodeError 분류, from_result(실패·부분·성공) | 11 |
| `tests/test_strava_403_ledger.py` | requests 403 주입 → bg 작업 `failed`·`subscription_required`·403, `completed` 아님(40 §8 수용 기준). 부분 실패 → completed+error_code | 3 |
| `tests/test_sync_ledger_paths.py` | manual(`_sync_source` + `--job-id`)·bg·auto·cli(full_sync) 각 1행, `source_path` 값 확인, 부모 fail_run이 failed 행을 덮어쓰지 않음 | 5 |
| `tests/test_sync_jobs_schema.py` | 15열 구 sync_jobs.db → 18열, 멱등, 기존 행 보존 | 3 |
| `tests/test_sync_state_service.py`(수정) | error_code 우선, 과거 행 문자열 폴백(`forbidden`→`subscription_required`), `failed`는 성공 아님, 상태명 error-auth/access/upstream | +4 |
| `tests/test_orchestrator.py`(수정) | running.db 대신 원장 기록 확인 | 6 수정 |
| `tests/test_user_settings_service.py` · `tests/test_api_me.py` | 화이트리스트, 잘못된 값 거부, resolve 우선순위(사용자→전역→v1), GET/PATCH | 4 + 3 |
| `frontend/tests/quickInputScope.test.mjs` | scope=activity payload(rpe·pain_sites), 부위 3개 제한, day scope 회귀 없음 | 3 |
| Playwright `pw/u15_feedback.mjs` | 실 DB 사본: `⋯` → 기록 → 새로고침 후 유지, GPX 다운로드, 원본 링크 href, 390/1280 콘솔 에러 0 | 1 시나리오 |

합계 신규 약 70건, 수정 10건. 전체 `python3 -m pytest tests/` 통과가 조건이다.

---

## 6. ADR 문안 (`v0.3/data/decisions.md`에 그대로 추가)

```markdown
## ADR-022: 활동별 주관 입력 activity_feedback — user_inputs와 분리 (2026-10-05)
- **맥락**: 3-10은 활동마다 RPE·통증·메모를 받는다. `user_inputs`는 `UNIQUE(input_date,input_type)`라 같은 날 두 활동을 구분할 수 없고, UNIQUE를 바꾸려면 테이블을 재작성해야 하며 체크인 경로가 영향을 받는다. `metric_store`는 수치 저장소라 메모·부위 텍스트에 맞지 않는다.
- **결정**: (1) 신규 `activity_feedback(activity_id PK, rpe 1–10 CHECK, pain, pain_sites JSON ≤3, note ≤500, created_at, updated_at)`, FK 없음. (2) 키는 쓰기 시점 캐노니컬 id이고, 읽기는 현재 그룹 구성원 중 최신 행이다(재매칭 내성). (3) 척도는 RPE 정수 1–10, 통증은 체크인과 같은 4단계, 부위는 고정 슬러그 12개. (4) 코치 전송 시 note는 coach_consent 메모 토글을 따른다. (5) 부하 계산(session-RPE, 심박 결측 대체)에 쓸 때는 CalcContext `get_activity_feedback(activity_id)`를 추가해 읽는다. raw SQL은 금지(ADR-009). 이 API는 소비 Calculator와 함께 추가한다. (6) 31 S3 세션 회고는 activity_id로 이 테이블을 조인하며 별도 저장소를 만들지 않는다. (7) `⋯` 메뉴의 원본 열기·GPX(단일 활동, GPX 1.1, 저장 없음)는 읽기 전용이라 DB를 쓰지 않는다.
- **검증**: `tests/test_db_schema_v25.py`, `tests/test_activity_feedback_service.py`, `tests/test_api_activity_feedback.py`, `tests/test_activity_gpx.py`, Playwright `pw/u15_feedback.mjs`.

## ADR-023: 동기화 원장 단일화(sync_jobs.db)·오류 코드 열·사용자 설정 key-value (2026-10-05)
- **맥락**: 원장이 `sync_jobs.db`(bg·auto)와 running.db `sync_jobs`(orchestrator)로 갈라져 있었다. 수동·CLI(`src/sync.py`)는 원장에 쓰지 않았다. 레거시 래퍼가 SyncResult를 버려 Strava 403이 `completed, count=0`으로 남았다. 오류 분류는 last_error 문자열 매칭이었다.
- **결정**: (1) 원장 SSOT는 `sync_jobs.db`. running.db `sync_jobs`는 동결(쓰기 중단, DROP은 별도 결정). (2) `error_code`·`http_status`·`source_path(manual|bg|auto|cli)` 열을 추가(연결 시 멱등 ALTER)하고 상태 `failed`를 추가. (3) 오류 코드 SSOT는 `src/sync/sync_errors.py`(auth_expired·subscription_required·rate_limited·upstream_5xx·timeout·network·parse·unknown). 소스 실패는 `SyncSourceError`로 올려 모든 경로가 `failed`로 기록하고, 부분 실패는 completed+error_code로 기록. (4) 원장 쓰기는 `src/sync/ledger.py`와 bg_sync만 한다. (5) 과거 행은 소급 수정하지 않고 문자열 규칙을 폴백으로 둔다. (6) 사용자 UI 설정은 running.db `user_settings(key, value_json)`에 화이트리스트 키로 저장하고, 운영자 롤백 값 `ui_default_global`은 config 1줄로 둔다.
- **검증**: `tests/test_sync_errors.py`, `tests/test_strava_403_ledger.py`, `tests/test_sync_ledger_paths.py`(4경로), `tests/test_sync_jobs_schema.py`, `tests/test_sync_state_service.py`, `tests/test_user_settings_service.py`.
```

---

## 7. 검토했으나 채택하지 않은 대안

| 대안 | 기각 이유 |
|---|---|
| `user_inputs` UNIQUE 변경(B) | SQLite 테이블 재작성 + 체크인 경로 회귀 위험. 날짜 체크인과 활동 평가는 의미가 다르다 |
| `metric_store`에 provider=`user`로 RPE 저장(C) | RPE 수치만이면 가능하지만 pain_sites·note가 분리 저장소를 요구한다. 향후 session-RPE 부하는 Calculator가 `activity_feedback`을 읽어 `metric_store`(runpulse:formula_v*)에 산출하는 방식이 단일 저장소 원칙에 맞다 |
| 피드백 키를 `matched_group_id`로 | 그룹 id는 재매칭 시 재발급될 수 있고 단독 활동은 NULL일 수 있다 |
| running.db `sync_jobs`를 SSOT로 통합 | 읽기 측(상태 서비스·대시보드)이 이미 sync_jobs.db를 쓰고, 별도 파일은 쓰기 경합 회피 목적으로 도입됐다(`sync_jobs.py:113`) |
| 오류 메시지 문자열 매칭 유지 | 403 문자열이 없는 실패(`"Strava activity list fetch failed"`)를 놓친 것이 이번 결함의 직접 원인이다 |
| GPX를 활동 파일 저장 + 다운로드 링크 | 파일 수명·정리 작업이 필요해 export 원장(4-1 이후)과 묶어야 한다 |

---

## 8. Definition of Done

1. `SCHEMA_VERSION=25`. 사본에서 v24→v25를 2회 실행해도 멱등이고 integrity ok, 기존 행 수 불변.
2. 같은 날 두 활동에 서로 다른 RPE를 저장하고 각각 조회할 수 있다. 재매칭 후에도 유지된다.
3. `⋯` 메뉴 4항목이 동작한다. GPX는 위치 없는 활동에서 비활성화되고, 원본 링크는 그룹 구성원 소스별로 나온다.
4. Strava 403 주입 시 원장은 `failed / subscription_required / 403`이고 상태는 `error-access`다. `completed`는 0건이다.
5. 수동·bg·자동·CLI 4경로가 모두 `sync_jobs.db`에 `source_path`가 다른 행을 남긴다. running.db `sync_jobs` 신규 쓰기는 0건이다(grep: `record_sync_job` 0).
6. `GET|PATCH /api/v1/me/preferences`가 동작하고 `resolve_ui_default` 우선순위 테스트를 통과한다.
7. 신규 파일은 모두 300줄 이하이고 기존 초과 파일은 순증이 최소다.
8. `pytest` 전체 통과, `check_docs.py` 통과, ADR-022·023 기록, 테이블 수 문서 갱신.
9. 운영 반영 시 백업 2개 파일명과 반영 시각을 IMPL-PROGRESS에 기록하고, 브라우저 스모크(390·1280)를 확인한다.

## 9. 구현 기록
(구현 후 작성: 완료일, 실제 테스트 수, 변경 파일 목록, 운영 백업 파일명)
