# v2 `POST /api/v1/data/sync` — SyncPanel "지금 동기화" 직접 실행 설계

- 상태: **설계 초안(승인 대기)** · 작성 2026-10-07 · 브랜치 `renew/data-architecture`
- 상위 계약: `design.md` §2.2(SyncPanel), §3.2(상태 기계), §7.2(원장), §7.3(API)
- 선행 완료: Phase 4-1 슬라이스 1·2(SyncStatusPill, 읽기 전용 SyncPanel, `?sheet=sync`, 드로어 요약), `GET /api/v1/data/sync-state`
- 범위: **증분(incremental) 수동 동기화 트리거 + 진행 표시 + 결과 반영**. 기간 동기화(range)·취소·SSE·자동 동기화 설정은 범위 밖(§8 결정 필요 사항 참조)

---

## 1. 배경과 문제

1. SyncPanel의 "지금 동기화"는 v1 `/sync` 화면으로 페이지를 이동시킨다(`SyncPanel.svelte:3,31`). v2 셸에서 흐름이 끊기고, 결과가 패널·Pill에 바로 반영되지 않는다.
2. 실행 경로가 v1에 5개 흩어져 있다: `/trigger-sync`(app.py:504, 동기 subprocess), `/trigger-sync-stream`(SSE, :696), `/trigger-sync-bg`(:873), `/bg-sync/start`(:1036), `auto_sync._trigger`. 이 중 **`/trigger-sync-bg`가 v2와 의미가 같다**(백그라운드 시작 → 즉시 응답 → 폴링). 단 사전 검사(연결·실행 중·cooldown·시작일 계산) 로직이 라우트 함수 안에 인라인돼 있어 재사용할 수 없다.
3. 확인된 구조 사실(설계에 영향):
   - 작업 원장 `sync_jobs`는 **`running.db`가 아니라 사용자별 `sync_jobs.db`**(`sync_jobs._jobs_db_path`)에 있고, 열 추가는 `sync_jobs_schema.ensure_ledger()`의 멱등 `ALTER`(LEDGER_COLUMNS)로 관리된다. 즉 `db_setup.SCHEMA_VERSION`(현재 v30)과 **무관**하다.
   - `bg_sync._threads`는 **서비스 키만**(`"garmin"`)으로 스레드를 등록한다. 사용자 A의 Garmin 스레드가 살아 있으면 사용자 B의 `start_job("garmin")`은 B의 원장에서 active job을 찾지 못해 `""`를 반환하고 조용히 건너뛴다(멀티유저 충돌).
   - `start_job()`은 "스레드 생존 검사 → 락 해제 → `create_job` → 락 재획득 등록" 순서라, 동시 요청 2건이 모두 검사를 통과하면 같은 서비스에 작업이 2개 생길 수 있다(경쟁 조건).
   - `BgSyncThread`는 `status="completed"`를 먼저 쓰고 그 뒤에 메트릭 재계산·예측 스냅샷·warmup을 수행한다(bg_sync.py:202~228). 원장상 "완료" 시점에 Today 지표는 아직 갱신 전일 수 있다.
   - `api_error(code, message, status)`는 추가 필드를 싣지 못한다. 프론트 `ApiError`도 `code/status/message`만 보존한다.

## 2. 제안 설계 — API 계약

### 2.1 요청

```
POST /api/v1/data/sync
Content-Type: application/json

{ "sources": ["garmin","intervals"],   // 선택. 생략/빈 배열 = 연결+포함(enabled)된 전체
  "mode": "incremental" }              // 선택. 기본 incremental. "range"는 이번 범위에서 400
```

- `sources` 원소는 `garmin|strava|intervals|runalyze`만 허용. 그 외 값 → `400 INVALID_PARAM`.
- 본문이 JSON이 아니어도 빈 객체로 간주(버튼 호출은 `{}`).
- 시작일은 서버가 결정한다: 기존 `_days_since_last_sync([src])`(activity_summaries 기준, 1~365일, 기본 7) 그대로. 클라이언트가 날짜를 보내지 않는다(range 모드 몫).

### 2.2 서버 판정(소스별, 순서 고정)

| 순서 | 검사 | 재사용 대상 | 실패 시 skip code |
|---|---|---|---|
| 1 | 자격증명 연결 | `check_*_connection(config)` | `not_connected` |
| 2 | 포함 여부 | `enabled_sources(config)` | `disabled` |
| 3 | 실행 중 | 원장 `get_active_job(service)`의 `running/pending` + 스레드 생존 | `running` |
| 4 | cooldown | `check_incremental_guard(src, get_last_sync_at(src))` | `cooldown`(+`retry_after_sec`) |
| 5 | rate limit 대기 | `get_retry_after_sec(service)` > 0 | `rate_limited`(+`retry_after_sec`) |

- v1의 `sync_state.is_running()`(sync_state.json)은 검사에서 **제외**한다(§7.2 "sync_state.json 쓰기 중단" 방향과 일치, 원장만 진실). 단 v1 SSE 경로가 아직 json만 쓰는 경우를 막기 위해 S1 동안은 둘 다 본다 → 결정 D6.

### 2.3 응답

| 결과 | HTTP | 본문 |
|---|---|---|
| 1개 이상 시작 | `202` | `api_ok({runs, skipped}, 202)` |
| 대상 소스 0개(전부 not_connected/disabled) | `422` | `api_error("NO_SOURCES", "동기화할 연결된 소스가 없어요")` |
| 시작 0개, skip이 전부 `running` | `409` | `api_error("SYNC_RUNNING", "이미 동기화 중이에요", details={runs})` |
| 시작 0개, skip에 `cooldown`/`rate_limited` 포함(나머지는 running) | `429` | `api_error("SYNC_COOLDOWN", message_ko, details={retry_after_sec, skipped})` + `Retry-After` 헤더 |
| `sources` 형식 오류, `mode=range` | `400` | `INVALID_PARAM` |
| `running.db` 없음 | `503` | `NOT_FOUND`(기존 sync-state와 동일 규약) |

```json
// 202
{"data": {
  "runs":    [{"id":"5f1c…","provider":"garmin","state":"queued","from":"2026-10-05","to":"2026-10-07"}],
  "skipped": [{"provider":"strava","code":"cooldown","message_ko":"Strava 동기화가 최근에 실행되었습니다. 1분 후 …","retry_after_sec":72},
              {"provider":"intervals","code":"running","job_id":"9a2e…"}]
}}
```

- 부분 시작은 202이며 skip 사유를 같이 준다(§3.2 "blocked" 행 표시에 그대로 사용).
- 409/429 우선순위: 하나라도 시작 가능하면 202. 시작 0개일 때 cooldown/rate_limited가 하나라도 있으면 429(사용자가 기다리면 되는 상황), 전부 running이면 409.
- 진행 상태 조회는 **신규 엔드포인트를 만들지 않고** 기존 `GET /api/v1/data/sync-state`의 `sources[].state="running"`·`running{job_id, progress_pct}`를 쓴다(§7.3의 `/sync/status`는 sync-state와 내용이 겹치므로 보류 → 결정 D4).
- **`api_error` 확장**(하위 호환): `api_error(code, message, status=400, details: dict | None = None)` → `{"error":{"code","message","details"?}}`. 프론트 `ApiError`에 `details?: unknown` 보존 추가.

### 2.4 인증·계정

- 라우트에서 `user_id = get_current_user_id()` 1회 → `load_config(user_id=…)`, `db_path(user_id)`, 서비스 호출에 명시 전달. 스레드에는 기존처럼 `BgSyncThread(user_id=…)`가 `set_current_user()`로 thread-local을 설정.
- `get_current_user_id()`는 세션이 없으면 `"default"`를 돌려준다. **쓰기 엔드포인트가 비로그인 상태에서 default 사용자 데이터를 동기화하는 것**을 허용할지는 기존 v1(`/trigger-sync-bg`)과 같은 수준(앱 `before_request`·`auth_cf` 훅에 의존)으로 두되, 차단 여부는 결정 D5.
- CSRF: 현재 `/api/v1` POST 전체에 토큰 검사가 없다(동일 출처 + 쿠키). 이 엔드포인트만 다르게 하지 않는다. 필요 시 API 전역 과제로 분리.

## 3. 백엔드 구조 — bg_sync/sync_jobs 재사용

### 3.1 신규 서비스 `src/services/sync_trigger_service.py`(~150줄)

```python
@dataclass(frozen=True)
class SkipReason:
    provider: str
    code: str                     # not_connected|disabled|running|cooldown|rate_limited|start_failed
    message_ko: str
    retry_after_sec: int | None = None
    job_id: str | None = None

@dataclass(frozen=True)
class TriggerResult:
    runs: list[dict]              # {id, provider, state:"queued", from, to}
    skipped: list[SkipReason]

def plan_incremental(config: dict, user_id: str, sources: list[str] | None,
                     today: date | None = None) -> tuple[list[str], dict[str, str], list[SkipReason]]:
    """§2.2 판정만 수행(부작용 없음). (시작할 소스, 소스별 from_date, skip 목록)."""

def trigger_incremental(config: dict, user_id: str, sources: list[str] | None,
                        source_path: str = "v2") -> TriggerResult:
    """plan → 소스별 bg_sync.start_job. 한 소스 시작 실패는 SkipReason(start_failed)로 담고 다음 소스 계속."""
```

- `plan_incremental`은 순수 판정이라 단위 테스트가 쉽다(연결 검사·가드·원장 조회는 주입 또는 monkeypatch).
- `_days_since_last_sync`는 app.py 내부 함수 → **서비스 모듈로 이동**하고 app.py는 import로 바꾼다(동작 동일).
- **v1 `/trigger-sync-bg`도 이 서비스를 호출하도록 치환**(응답 형식 `{ok, started, skipped, job_ids}`는 어댑터로 유지). 판정 로직의 단일 소스화. app.py 줄 수도 감소.
- `source_path="v2"`로 원장에 기록 → 기존 `source_path` 열(이미 존재) 재사용, 스키마 변경 없음.

### 3.2 동시성·멀티유저 보정(`bg_sync.py`, 최소 변경)

1. `_threads` 키를 `service` → `(user_id, service)`로 변경. `start_job/pause_job/stop_job/resume_job/get_status`에 `user_id` 인자(기본 `"default"`, 기존 호출 호환). → v1 동작 변경이 따르므로 **결정 D3**.
2. `start_job`의 "생존 검사 + 스레드 등록"을 락 하나 안에서 수행(검사 통과 시 자리표시(sentinel)를 먼저 넣고 `create_job` 후 실제 스레드로 교체, 예외 시 제거). 중복 클릭·다중 탭 경쟁 제거. D3과 독립적으로 적용 가능.
3. `start_job`이 기존 job_id를 돌려준 경우(이미 살아 있음) 서비스는 이를 `runs`가 아니라 `skipped(code="running", job_id)`로 분류한다. 현재는 호출자가 구분할 수 없으므로 반환값을 `(job_id, created: bool)`로 바꾸는 내부 헬퍼 `_start_or_existing()`를 두고 `start_job`은 기존 시그니처 유지.

`bg_sync.py`는 이미 520줄(300줄 규칙 초과 기존 부채). 이번 변경은 위 3개에 한정하고 파일 분리는 별도 과제로 남긴다(결정 D8). 새 로직은 서비스 파일에 둔다.

### 3.3 sync_jobs 스키마 확장 여부

| 필요한 것 | 현재 | 판단 |
|---|---|---|
| 트리거 구분(v2 수동/auto/bg) | `source_path` 열 존재 | **변경 불필요** — `"v2"` 값만 추가 |
| 진행률 n/m, 커서 날짜 | `completed_days/total_days/current_from` | 변경 불필요 |
| 오류 코드 | `error_code/http_status` 존재 | 변경 불필요 |
| 결과 카운트(활동 2·웰니스 1 토스트) | `synced_count` 단일 정수 | §3.2 `done-new` "활동 2 · 웰니스 1"에는 부족 → `counts_json` 필요 |
| `started_at/finished_at` | `created_at/updated_at`로 근사 | 정확도 요구 시 추가 |

- 최소안: **이번 범위는 스키마 변경 없이** 진행(토스트는 `synced_count` 합계 "새 데이터 N건"으로 표시).
- 확장안: `LEDGER_COLUMNS`에 `counts_json TEXT`, `trigger TEXT`, `started_at TEXT`, `finished_at TEXT` 추가 → `ensure_ledger`의 멱등 ALTER로 자동 적용. `sync_jobs.db`는 별도 파일이므로 **`running.db` 마이그레이션 v31은 필요 없다**. 단 `_COLS`/`SyncJob` 필드 순서·`create_job` INSERT 자리수(현재 18개) 동시 수정 필요 → 결정 D2.
- `/check-data-consistency`가 원장 열을 검사 대상으로 삼는지 확인 필요(검증 V7).

### 3.4 "Garmin never" 문제와의 관계

- 현상: `sync_state_service._source_state`는 원장 최근 20건에 `completed`가 없으면 `last_success_at=None` → `state="never"`, 전체 `level="stale"`.
- v2 트리거는 항상 `bg_sync.start_job → create_job`을 거치므로, **v2로 한 번 성공하면 Garmin 원장에 completed 행이 생겨 never가 해소된다.** 다만 이것은 증상 완화이고 근본 원인은 별개다.
- 근본 원인 후보(추측 금지, 검증 V5로 확인): (a) Garmin 데이터가 원장을 쓰지 않는 경로로 들어온다(예: 외부 스크립트가 payload를 직접 적재, 또는 SSE/subprocess 경로가 다른 사용자 `sync_jobs.db`에 기록), (b) Garmin bg 작업이 `auth_required/stopped/rate_limited`로 끝나고 `completed`에 도달하지 못한다, (c) 최근 20건이 모두 비완료다.
- 설계 측 보완 제안(결정 D7): 원장에 성공 기록이 없고 `source_payloads.fetched_at`(=`last_new_data_at`)이 있으면 `never` 대신 "원장 기록 없음 · 마지막 수신 HH:MM"(`idle-unknown` 또는 `last_new_data_at` 기준 idle 판정)으로 표시. 원장 단일화 원칙(F-DATA-01)과 충돌하므로 사용자 결정 사항.
- 트리거 판정과의 관계: cooldown은 `get_last_sync_at`(원장 completed ∪ sync_state.json) 기준이라 never 상태에서는 가드가 걸리지 않는다 → 버튼은 정상 동작한다.

### 3.5 오류 처리 규칙 준수(coding-rules)

- **sync 중단 금지**: 소스별 `try/except` — 한 소스의 `start_job` 예외는 `ledger.fail_run(service, source_path="v2", code="unknown")`로 원장에 남기고 `skipped(code="start_failed")`로 응답, 나머지 소스는 계속 시작.
- **재시도 1회**: 외부 API 재시도는 `BgSyncThread._run_one_batch` 기존 로직에 맡긴다(이 엔드포인트는 외부 API를 직접 부르지 않는다). 서비스에서 재시도하는 것은 `start_job` 시점의 SQLite `database is locked` 1회뿐(0.5초 후). 프론트 POST는 **자동 재시도하지 않는다**(비멱등; 사용자가 버튼을 다시 누르면 409/202로 수렴).
- 로깅: `log.info("[data_sync] user=%s started=%s skipped=%s")`.

## 4. 프론트엔드

### 4.1 파일

| 파일 | 변경 | 예상 줄 |
|---|---|---|
| `lib/api/data.ts` | `triggerSync(sources?)` 추가 | +10 |
| `lib/api/client.ts` | `ApiError.details` 보존 | +3 |
| `lib/syncState.ts` | 타입 `SyncTriggerResult`, 순수 함수 `triggerButtonView(state, trigger, now)`, `runProgress(state)`(n/m) | ~111 → ~170 |
| `lib/syncStore.svelte.ts` | 폴링 루프를 Pill에서 스토어로 이동(`startPolling/kick`), `triggering`, `lastTrigger`, 완료 전이 감지 | ~20 → ~80 |
| `components/shell/SyncStatusPill.svelte` | 자체 setTimeout 루프 제거 → `startPolling()` 호출 | 감소 |
| `components/shell/SyncPanel.svelte` | `/sync` 링크 → 버튼, skip/오류 줄, "기간 지정 ›"은 v1 `/sync` 유지 | ~34 → ~90 |

### 4.2 폴링 연동(핵심)

- 현재 루프는 Pill 안에서 `tick → setTimeout(pollIntervalMs(data))`라, POST 직후에도 **최대 60초 뒤에야** 5초 간격으로 전환된다.
- 스토어에 `kick()`를 둔다: 대기 중 타이머를 취소하고 즉시 `loadSyncState()` 후 재스케줄. POST 202 직후 `kick()`.
- 서버가 원장에 `pending`을 쓰기 전 경합으로 첫 응답이 running이 아닐 수 있으므로, `lastTrigger.at`으로부터 15초 동안은 `pollIntervalMs`가 5초를 반환하도록 `pollIntervalMs(state, triggeredAt?)` 확장.
- 탭 비가시(`document.hidden`) 시 폴링 일시중지는 이번 범위 밖(기존과 동일).

### 4.3 버튼 상태(`triggerButtonView` 순수 함수로 결정 — 단위 테스트 대상)

| 조건 | 라벨 | 활성 |
|---|---|---|
| 연결·포함 소스 0개 | `연결된 소스가 없어요` + [연결 관리 ›](v1 /settings) | 비활성 |
| `triggering`(POST 응답 대기) | `요청 중…` | 비활성 |
| sync-state에 running 소스 존재 | `동기화 중 n/m` (n=완료, m=이번 실행 대상) | 비활성(중지는 D1) |
| 429 응답 후 `retry_after_sec` 남음 | `n분 후 가능`(초 단위 카운트다운, 클라이언트 시계) | 비활성 |
| 그 외 | `지금 동기화` | 활성 |

- 버튼: 패널 하단 전폭, 높이 44px(모바일 터치 기준), primary 톤. 모바일 시트(`?sheet=sync`)와 데스크톱 팝오버가 같은 `SyncPanel` 컴포넌트를 쓰므로 분기 없음.
- 응답 처리: 202 → `kick()`, skip 목록은 해당 소스 행 아래 회색 한 줄(`⏱ 1분 후 가능`, `이미 동기화 중`). 409 → "이미 동기화 중이에요" + `kick()`. 429 → 카운트다운. 422 → 연결 안내. 네트워크/5xx → "요청하지 못했어요. 다시 눌러 주세요"(재시도 버튼은 동일 버튼).
- 소스 오류 행(`error-auth`/`error-access`/`error-upstream`): 기존 `sourceLine` 표시 유지 + 행동 링크만 추가 — `error-auth` → [재연결 ›](v1 연결 화면), `error-access` → [설정 ›], `error-upstream` → 전체 버튼으로 재시도. 오류 소스는 POST 대상에서 **빼지 않는다**(서버가 실행해 보고 다시 원장에 기록; error-auth 소스를 자동 제외할지는 D9).
- 완료 전이: 스토어가 직전 `level="running"` → 현재 ≠ running을 감지하면 (1) `invalidateAll()` 대신 Today·Library 키만 `invalidate('app:today')` 등으로 무효화, (2) 결과 요약을 패널 상단 1줄(`동기화 완료 · 새 데이터 N건 · Strava 실패 1`)로 표시. 전역 토스트 컴포넌트는 아직 없으므로 토스트 도입은 D10. 메트릭 재계산이 completed 이후에 돌아가므로 무효화는 전이 감지 후 10초 1회 추가 재요청(또는 D2 확장안의 `finished_at`을 재계산 종료 시각으로 정의).

## 5. 기존 시스템과의 호환성

- `running.db` 스키마(v30): 변경 없음. 원장 확장 시에도 `sync_jobs.db`의 멱등 ALTER만 사용.
- v1 `/trigger-sync-bg`·`/bg-sync/*`·자동 동기화: 서비스 치환 후에도 응답 형식 동일. `_threads` 키 변경(D3) 시 `get_status(service)` 시그니처에 `user_id` 기본값을 두어 호출부 호환.
- `sync-state` 계약: 변경 없음(선택적으로 `last_trigger` 미포함). 폴링만으로 진행 표시 가능.
- §7.3 계약과의 차이: §7.3은 `202 {runs:[{id,provider,state}]}`만 정의 → 본 설계는 `skipped`, `from/to` 추가와 `NO_SOURCES(422)` 추가. §7.3 문서 갱신 필요.
- metric_store·CalcContext·Calculator: 영향 없음(동기화 후 재계산은 기존 BgSyncThread 경로).

## 6. 대안과 트레이드오프

| 대안 | 미채택 이유 |
|---|---|
| v2 라우트에서 v1 `/trigger-sync-bg`를 내부 호출/리다이렉트 | form 인코딩·응답 형식이 다르고 판정 로직이 계속 app.py에 갇힌다 |
| `/trigger-sync-stream`(SSE) 재사용 | 브라우저 연결에 실행이 묶인다(시트 닫으면 끊김). bg 스레드가 이미 연결 독립 |
| 전용 `/data/sync/status` 폴링 엔드포인트 신설 | sync-state가 같은 정보를 이미 제공. 중복 계약 증가 |
| `sync_jobs`를 `running.db`로 이관 후 v31 | 범위 대비 과도. 원장 파일 분리는 쓰기 경합 회피 이점도 있음 |
| 소스별 개별 POST(`/data/sync/:provider`) | 패널 버튼은 "전체"가 주 동선. `sources` 배열로 충분 |
| 409 대신 항상 202 + 기존 job 반환 | 클라이언트가 "새로 시작했는지" 구분 못 함. 부분 시작은 202+skipped로 이미 표현 |

## 7. 테스트 계획

| 파일 | 대상 | 예상 수 |
|---|---|---|
| `tests/test_sync_trigger_service.py` | `plan_incremental`: 미연결/꺼짐/실행 중/cooldown/rate_limited/정상, sources 필터, from_date 계산 / `trigger_incremental`: 한 소스 start 예외 시 나머지 계속 + fail_run 기록, 기존 스레드 생존 시 running skip | 12 |
| `tests/test_api_data_sync.py` | 202 본문·`source_path="v2"` 원장 기록, 409(전부 running), 429(+Retry-After, details), 422, 400(잘못된 source, mode=range), user_id 전달(다른 사용자 DB에 기록되지 않음) | 9 |
| `tests/test_bg_sync_concurrency.py` | 동시 `start_job` 2건 → 작업 1개, (D3 채택 시) 사용자 A/B 같은 서비스 동시 시작 | 3 |
| `tests/test_api_error_details.py` 또는 기존 api 테스트 | `api_error(details=…)` 하위 호환 | 2 |
| 기존 `/trigger-sync-bg` 테스트 | 서비스 치환 후 응답 형식 회귀 | 기존 유지 +1 |
| `frontend/src/lib/syncState.test.ts` | `triggerButtonView` 5상태, `runProgress` n/m, `pollIntervalMs(…, triggeredAt)` 15초 창 | 9 |
| `frontend/src/lib/syncStore.test.ts` | `kick()` 타이머 재설정, running→idle 전이 감지 1회만 발화 | 3 |

- 외부 API는 호출하지 않는다: `BgSyncThread`는 monkeypatch로 즉시 종료하는 더미 스레드로 대체.
- 브라우저 스모크(REVIEW.md 규율): 모바일 시트·데스크톱 팝오버에서 버튼 → 진행 표시 → 완료 문구 → Today 갱신 확인. 실 운영 DB에서의 실행은 사용자 승인 후.

## 8. 결정 필요 사항(추측으로 확정하지 않음)

| ID | 질문 | 선택지 / 설계자 의견 |
|---|---|---|
| D1 | 실행 중 "중지" 버튼(`POST /data/sync/runs/:id/cancel` → `stop_job`)을 이번에 포함? | §2.2 와이어프레임엔 있음. 포함 시 S4 슬라이스 추가 |
| D2 | 원장 확장(`counts_json`·`trigger`·`started_at`·`finished_at`)을 지금 할지 | 최소안(무변경, "새 데이터 N건") vs 확장안(§3.2 "활동 2·웰니스 1"). 어느 쪽이든 v31 불필요 |
| D3 | `bg_sync._threads` 키를 `(user_id, service)`로 바꿀지(v1 동작 변경) | 실제 다중 사용자 운영 여부에 달림 |
| D4 | §7.3의 `/data/sync/status`·`/data/sync/stream`(SSE)을 폐기하고 sync-state 폴링으로 일원화할지 | 설계자 의견: 일원화 |
| D5 | 세션 없는 `"default"` 사용자로 쓰기 요청 허용 여부 | v1과 동일 유지 vs 401 차단 |
| D6 | 실행 중 판정에서 `sync_state.json`(`is_running`)을 언제 제외할지 | v1 SSE 경로가 원장 단독 기록으로 바뀐 뒤 |
| D7 | 원장 기록 없음 + 수신 데이터 있음일 때 `never` 대신 다른 상태로 표시할지 | 원장 단일화 원칙과 충돌, V5 결과 보고 결정 |
| D8 | `bg_sync.py`(520줄) 분리 리팩터를 이 작업에 포함할지 | 설계자 의견: 별도 과제 |
| D9 | `error-auth`/`error-access` 소스를 "지금 동기화" 대상에서 자동 제외할지 | 제외 시 무의미한 401/403 호출 감소, 대신 회복 감지 지연 |
| D10 | 전역 토스트 컴포넌트 도입(§3.2 "토스트 1개 요약") | 미도입 시 패널 상단 1줄로 대체 |
| D11 | `mode:"range"`(기간 지정·과거 데이터) v2 구현 시점 | 이번엔 400 + v1 `/sync` 링크 유지 |

## 9. 구현 슬라이스(결정 없이 진행 가능한 부분)

| 슬라이스 | 내용 | 결정 의존 |
|---|---|---|
| S1 백엔드 판정·트리거 | `sync_trigger_service.py`, `api_error(details)`, `POST /data/sync`(incremental), `start_job` 락 원자화, `/trigger-sync-bg` 서비스 치환, pytest | 없음(D3·D6은 현행 유지로 시작) |
| S2 프론트 버튼·폴링 | `triggerSync`, 스토어 폴링 이전·`kick`, `triggerButtonView`, SyncPanel 버튼·skip 줄·오류 행 링크, 단위 테스트, 브라우저 스모크 | 없음 |
| S3 완료 반영 | running→idle 전이 감지, Today·Library 무효화, 패널 상단 결과 1줄 | D10(토스트)은 후속 |
| S4 (조건부) 중지 | cancel 엔드포인트 + 버튼 | D1 |
| S5 (조건부) 원장 확장·멀티유저 | `LEDGER_COLUMNS` 확장, `(user_id, service)` 키 | D2, D3 |

## 10. 검증 항목

- V1 `POST` 후 `sync_jobs.db`에 `source_path='v2'` 행이 생기고 `sync-state`가 5초 내 `running`을 보이는가.
- V2 버튼 2회 연타·두 탭 동시 클릭 시 서비스당 작업이 1개만 생기는가(409 수렴).
- V3 한 소스 시작 실패가 다른 소스 시작을 막지 않는가, 실패가 원장에 남는가.
- V4 완료 후 Today 지표가 재계산 반영 값으로 바뀌는가(completed 이후 재계산 지연 고려).
- V5 운영 컨테이너 `sync_jobs.db`에서 Garmin 행의 `status`·`source_path` 분포와 Garmin payload 적재 경로를 대조해 never 원인 확정(읽기 전용).
- V6 v1 `/trigger-sync-bg`·자동 동기화 회귀 없음(응답 형식, auto 원장 기록).
- V7 `/check-data-consistency`·`check_docs.py`가 원장 열·신규 서비스 파일을 인식하는가.
- V8 신규·변경 파일 300줄 이하(`bg_sync.py` 기존 초과분 제외, 증가 최소화).

## 11. 결정 D1–D11 — 추천안 채택 (2026-10-07, 사용자 승인 "추천안대로")

| # | 결정 | 사유 |
|---|------|------|
| D1 | 중지 버튼 **포함, 단 S4로 분리**(S1–S3 후) | `stop_job`이 이미 있어 비용 낮고, 실수로 시작한 동기화를 되돌릴 수단이 없으면 429/쿨다운 정책과 맞물려 사용자가 갇힘. 다만 S1–S3 범위를 키우지 않기 위해 후속 슬라이스 |
| D2 | 원장 확장 **보류(최소안)**. 결과 요약은 "새 데이터 N건" | `create_job` INSERT 18자리·`SyncJob` 필드 순서 동시 수정 위험 대비 이득이 작음. 상세 카운트는 요구가 생기면 S5 |
| D3 | `_threads` 키 `(user_id, service)` **채택(코드 반영)** | 서로 다른 사용자가 같은 서비스를 동시에 돌리면 단일 키는 서로를 "실행 중"으로 오판·덮어씀. 기본값 호환으로 v1 호출부 변경 없음 |
| D4 | `/data/sync/status`·SSE **폐기, sync-state 폴링 일원화** | 내용이 중복되고 진실 소스가 둘이 되면 불일치가 생김. 적응형 폴링으로 충분 |
| D5 | 비로그인 default 쓰기 **v1과 동일 유지** | 인증은 앱 `before_request`/`auth_cf` 훅 책임. 이 엔드포인트만 따로 막으면 정책이 갈라짐. 차단은 전역 보안 과제로 분리 |
| D6 | S1 동안 원장 + `sync_state.json` **둘 다 확인** | v1 SSE 경로가 json에만 쓰므로 한쪽만 보면 중복 시작 가능. v1이 원장 단독 기록으로 바뀌면 json 검사 제거 |
| D7 | **V5(프로덕션 원장 읽기 전용 확인) 후 결정**. 잠정: 표시만 "원장 기록 없음 · 마지막 수신" | 원인이 데이터 부재인지 기록 누락인지 모른 채 상태 모델을 바꾸면 원장 단일화 원칙을 훼손할 수 있음 |
| D8 | `bg_sync.py` 분리는 **별도 과제** | 동시성 수정과 대규모 이동을 한 커밋에 섞으면 회귀 원인 추적이 어려움 |
| D9 | error-auth/access 소스도 **POST 대상에서 제외하지 않음** | 사용자가 재연결한 뒤 회복을 즉시 감지해야 함. 서버가 실행해 결과를 원장에 다시 기록 |
| D10 | 전역 토스트 **미도입**, 패널 상단 1줄 | 토스트 컴포넌트는 접근성(aria-live)·큐 정책까지 설계가 필요한 별도 항목 |
| D11 | `mode:"range"` **400 유지**, v1 `/sync` 링크 유지 | 과거 구간 백필은 쿼터·소요 시간 안내 UX가 필요해 증분과 분리가 안전 |
