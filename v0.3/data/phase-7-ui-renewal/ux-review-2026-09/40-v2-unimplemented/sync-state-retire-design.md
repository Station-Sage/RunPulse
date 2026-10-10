# `sync_state.json` 퇴역 — 작업 원장 단일화 설계

**상위 설계**: `design.md` §1 판단표 24행(원장 = `sync_jobs` 확장), §7.2 `sync_state.json` 행("쓰기 중단, 읽는 곳은 원장 파생 함수로 교체"), §8 셸·원장 수용 기준("`sync_state.json` 쓰기 0회(grep)"), §9 S2.
**관련 설계**: `sync-trigger-design.md` §2.2·D6("S1 동안 원장 + json 둘 다 확인, v1 SSE가 원장 단독 기록이 되면 json 검사 제거") — 이 문서가 D6의 종료 조건을 만든다.
**성격**: 설계만 다룬다(코드 수정 없음). 작성일 2026-10-10. 구현 착수 전 사용자 확인 필요.

---

## 1. 배경과 문제

상위 설계는 `last_sync_at` 하나만 다룬다. 실제 `src/utils/sync_state.py`(`data/users/{uid}/sync_state.json`)는 아래를 모두 담고, `src` 전역 약 42곳에서 호출된다.

| 묶음 | 키 | 쓰는 곳 | 읽는 곳 |
|---|---|---|---|
| 실행 중 | `is_running`, `started_at`, `current_mode` | `mark_running`(app.py 수동 경로 2곳) | `is_running`(app.py 2곳, `sync_trigger_service`, `sync_range_service`), `get_all_states` |
| 결과 | `last_sync_at`, `last_count`, `last_partial`, `last_error` | `mark_finished`(app.py 8곳, `sync.py`, `sync/strava.py`, `sync/runalyze.py`) | `get_last_sync_at`(helpers:898, app.py 쿨다운, trigger 서비스), `get_all_states`(v1 대시보드 카드) |
| 요청 제한 | `retry_after` | `set_retry_after`(garmin_helpers 백오프, runalyze 403), `clear_retry_after`(Runalyze 토큰 저장) | `get_retry_after_sec`(bg_sync 2곳, app.py 2곳, trigger·range 서비스, garmin_helpers, runalyze) |
| 한도 상태 | `rate_state` | `mark_finished(rate_state=)` — **호출하는 곳 없음** | `get_rate_state` — **외부 호출 없음** |
| 자동 동기화 | `_auto_sync.last_run` | `mark_auto_sync_ran`(auto_sync._trigger) | `get_last_auto_sync`(auto_sync 루프·status, views_sync, routes_data, data_settings_service) |
| 사용자 해석 | (파일 아님) `set_current_user`, `_resolve_user_id` | sync.py, bg_sync, auto_sync, export/import/recompute 서비스 | `sync_jobs._conn`도 이 함수에 의존 |

현재 구조의 결함:

1. **이중 기록·불일치.** 수동 경로는 부모(app.py)가 json에, 자식(`sync.py --job-id`)이 원장에 쓴다. bg·자동은 원장만 쓴다. `get_last_sync_at`이 둘 중 늦은 값을 고르는 봉합으로 버티고 있다(F-DATA-01).
2. **프로세스 간 경쟁.** `_LOCK`은 프로세스 내 `threading.Lock`이다. subprocess(`sync.py`)·웹 워커가 같은 파일을 read-modify-write 하므로 갱신이 유실될 수 있다. `is_running` 검사와 `mark_running` 사이에도 원자성이 없다.
3. **읽기 부작용.** `is_running()`이 stale(시작 1시간 초과)을 감지하면 읽는 도중 파일을 고친다.
4. **stdout 파싱.** 수동 경로는 `"활동 N개 동기화"`·`"⚠️"`·`"일부"` 문자열로 건수·부분 실패를 추정한다(`_already_finished`).
5. **user_id 해석 함수가 상태 파일 모듈에 있다.** `sync_jobs._conn`이 `sync_state._resolve_user_id`를 import하므로 파일을 지우려면 먼저 옮겨야 한다.

현행 사실(설계 근거, 2026-10-10 확인):
- 원장은 `running.db`가 아니라 **사용자별 `data/users/{uid}/sync_jobs.db`**(`sync_jobs._jobs_db_path`)이다. DDL은 `src/utils/sync_jobs_schema.py`의 `CREATE_SQL` + `LEDGER_COLUMNS`(멱등 `ALTER`)가 맡는다.
- `db_setup.py:395`의 `_DDL_SYNC_JOBS`(`running.db`, 열 `source`·`job_type`)는 **src 어디서도 읽거나 쓰지 않는 잔재**다. 상위 설계가 말한 "`job_type`이 이미 있다"는 이 잔재 테이블 이야기다.
- 로컬 `sync_state.json` 2개: `default`(`_auto_sync.last_run`만), `pansongit@gmail.com`(garmin·strava·intervals 결과 키 + `_auto_sync`). `retry_after`·`rate_state` 키는 없다. 운영 데이터는 OCI docker 컨테이너 볼륨에 있으므로 별도 확인 필요.

---

## 2. 제안 설계

### 2.1 필드 1:1 매핑

| json 필드 | 새 출처 | 저장/파생 | 근거 |
|---|---|---|---|
| `is_running` | `sync_jobs` 행 `status IN ('pending','running')` **이고** `updated_at`이 `STALE_SEC`(600초) 이내 | 파생 | 원장 행이 실행 단위 그 자체. 수동 경로는 부모가 subprocess 시작 전에 행을 선점(§2.3)하므로 json이 따로 필요 없다 |
| `started_at` | `sync_jobs.started_at`(이미 존재, `update_job(status='running')`이 채움) | 파생 | — |
| `current_mode` | `sync_jobs.params_json.mode`(`basic`/`hist`) | **새 열 `params_json`** | 읽는 곳 없음. 상위 설계 §7.2가 이미 `params_json`을 열 목록에 넣었으므로 같이 도입해 정보 손실만 막는다 |
| `last_sync_at` | 서비스별 최근 `status='completed'` 행의 `COALESCE(finished_at, updated_at)` | 파생 | 현재 `get_last_sync_at`·`sync_state_service`가 각각 계산한다 → **함수 1개**(`last_success_at`)로 합치고 둘 다 그걸 쓴다 |
| `last_count` | `sync_jobs.synced_count`(+ `counts_json`) | 파생 | `finish_run(synced=)`이 이미 기록 |
| `last_partial` | `status='completed' AND error_code = 'partial_rate_limited'` | 파생 | 부분 실패의 실체는 "실행 도중 요청 제한 게이트가 걸림"이다. `finish_run`이 게이트의 `job_id`가 자기 행인지 보고 코드를 붙인다(§2.4). stdout 파싱 폐기 |
| `last_error` | 최근 행 `last_error`/`error_code` → `classify_error` | 파생 | 이미 `sync_state_service.classify_error`가 있음 |
| `last_error`(stale) | stale 행을 `status='stopped'`, `error_code='stale'`로 닫음 | 원장 쓰기(선점 트랜잭션 안에서만) | 읽기 부작용 제거(§2.3) |
| `retry_after` | **새 소형 테이블 `sync_gates`**(같은 `sync_jobs.db`) | 저장 | §2.2 |
| `rate_state` | 없음(폐기) | — | 쓰는 곳·읽는 곳 모두 없음(dead). 한도 사용량은 `SyncJob.rate_limit`(`req_count` 파생)이 이미 제공 |
| `_auto_sync.last_run` | `MAX(created_at) WHERE trigger='auto'` | 파생 | 자동 실행은 `start_basic_sync(..., source_path='auto')`로 원장 행을 만든다. 별도 기록 불필요 |
| `get_all_states()` 반환 모양 | `ledger_query.legacy_card_states(user_id)` | 파생 | v1 대시보드 카드(`sync_ui.sync_card_html`)가 읽는 키(`is_running`·`cooldown_sec`·`last_error`·`last_sync_at`)만 같은 모양으로 낸다. v1 퇴역 시 함께 삭제 |

#### 원장에 없는 것의 저장 방식 결정

| 항목 | 새 열 | 새 `job_type` | 별도 소형 테이블 | 결정 |
|---|---|---|---|---|
| 요청 제한 게이트(`retry_after`) | 작업 행의 `retry_after`에 기록 후 "서비스별 최근 미래값"으로 파생 | — | `sync_gates(service PK)` | **소형 테이블.** 게이트는 작업보다 오래 산다(다음 작업 시작을 막는다). 깊은 공급자 코드(garmin_helpers·runalyze)는 job_id를 모른다. 토큰 재설정 시 해제가 과거 작업 행을 고쳐 쓰면 원장이 이력이 아니게 된다. 작업 행의 `retry_after` 열은 "이 작업이 언제까지 멈췄었다"는 이력으로 계속 쓴다 |
| 자동 동기화 마지막 실행 | — | `job_type='auto_tick'` 행 | `_auto_sync` KV | **둘 다 아님 — 파생.** `trigger='auto'` 행이 이미 그 사실이다. tick 행은 "최근 작업" UI를 오염시키고 KV는 원장 밖 진실을 하나 더 만든다 |
| 수동 SSE의 `is_running` | — | — | — | **추가 저장 없음.** 부모가 subprocess 전에 `claim_run`으로 원장 행을 선점하고 그 id를 `--job-id`로 넘긴다(현재도 `--job-id` 전달은 함). 자식은 같은 행을 재사용 |
| `current_mode` | `params_json` | — | — | **새 열.** 상위 설계와 동일 열 |

### 2.2 `sync_gates` DDL(`sync_jobs_schema.py`에 추가)

```sql
CREATE TABLE IF NOT EXISTS sync_gates (
    service      TEXT PRIMARY KEY,           -- garmin|strava|intervals|runalyze
    retry_after  TEXT NOT NULL,              -- 서버 로컬 ISO(원장과 같은 규약)
    backoff_sec  INTEGER NOT NULL,           -- 직전 대기 길이(지수 백오프 기준)
    reason_code  TEXT NOT NULL,              -- rate_limited | auth_expired (sync_errors 코드 재사용)
    set_at       TEXT NOT NULL,
    job_id       TEXT                        -- 설정 당시 실행 중이던 원장 행(없으면 NULL)
);
```

`LEDGER_COLUMNS`에 `"params_json": "TEXT"` 추가. 인덱스 2개 추가:
`idx_sync_jobs_trigger ON sync_jobs(trigger, created_at)`(자동 마지막 실행), `idx_sync_jobs_busy ON sync_jobs(service, status, updated_at)`(실행 중 판정).

`src/utils/sync_gates.py`(~90줄) API:

```python
def wait_sec(service: str, user_id: str | None = None) -> int | None: ...       # 만료면 None
def bump_backoff(service: str, *, reason: str = "rate_limited",
                 user_id: str | None = None) -> int: ...  # 활성 게이트면 backoff_sec*2(최대 86400), 아니면 900
def block(service: str, seconds: int, *, reason: str, user_id: str | None = None) -> None: ...  # runalyze 403 24h
def clear(service: str, user_id: str | None = None) -> None: ...                  # DELETE
def gate(service: str, user_id: str | None = None) -> Gate | None: ...           # 원자료(partial 판정용)
```

현행 백오프는 "남은 초 × 2"라 시간이 지날수록 다음 대기가 짧아지는 버그성 동작이다. `backoff_sec`를 저장해 "직전 대기 × 2"로 바로잡는다.

### 2.3 실행 중 판정·선점·stale(동시성)

```python
# src/sync/ledger.py (확장, ~150줄)
def claim_run(service: str, from_date: str, to_date: str, *, source_path: str,
              params: dict | None = None, job_id: str | None = None,
              user_id: str | None = None) -> str | None:
    """BEGIN IMMEDIATE 안에서 (1) 같은 service의 stale running/pending을 stopped(error_code='stale')로 닫고
    (2) 신선한 running/pending이 있으면 None, (3) 없으면 행을 running으로 넣고 id 반환."""

@contextmanager
def heartbeat(job_id: str, every_sec: int = 60, user_id: str | None = None): ...
    # 데몬 스레드가 every_sec마다 updated_at만 갱신. with 종료 시 정지.

# src/utils/sync_ledger_query.py (신규, ~130줄, 읽기 전용·부작용 없음)
STALE_SEC = 600
def busy_job(service: str, user_id: str | None = None) -> SyncJob | None: ...
def is_busy(service: str, user_id: str | None = None) -> bool: ...
def last_success_at(service: str, user_id: str | None = None) -> datetime | None: ...
def last_auto_run(user_id: str | None = None) -> datetime | None: ...
def legacy_card_states(user_id: str | None = None) -> dict[str, dict]: ...
```

- **원자성**: 검사와 삽입을 SQLite `BEGIN IMMEDIATE` 한 트랜잭션으로 묶는다. 파일 잠금이 프로세스 경계를 넘으므로 웹 워커·subprocess·bg 스레드 사이 경쟁이 사라진다. 현 `_LOCK`(프로세스 내)보다 강하다.
- **stale**: 기준을 "시작 후 1시간"에서 "**`updated_at` 하트비트 600초 무갱신**"으로 바꾼다. 600초는 기존 `cleanup_stale_running_jobs_all_users(older_than_sec=600)`와 같은 값이다. 하트비트는 `sync.py`(subprocess 단일 블로킹 호출)와 `BgSyncThread.run`이 `with heartbeat(job_id):`로 감싼다. 프로세스가 죽으면 하트비트가 멎으므로 10분 뒤 자동으로 잠금이 풀린다. 1시간 넘게 걸리는 정상 CLI 장기 동기화가 stale로 오판되던 문제도 사라진다.
- **읽기 무부작용**: `is_busy`는 stale 행을 무시만 한다. 닫는 쓰기는 `claim_run`과 기존 시작 시 정리(`cleanup_stale_running_jobs_all_users`)만 한다.
- `paused`·`rate_limited`는 실행 중으로 보지 않는다(현 trigger 서비스가 `running/pending`만 보는 판정과 같다). `rate_limited`인 bg 작업은 게이트가 새 시작을 막는다.
- `sync_state_service._source_state`의 `running`도 `busy_job`을 써서 stale 행을 "동기화 중"으로 보이지 않게 맞춘다. `last_success_at`도 같은 함수를 쓴다(진실 1곳).
- bg 경로: `bg_sync.start_job`이 `create_job` 대신 `claim_run`을 쓴다. `create_job`의 "같은 서비스 미완료 행 stopped 정리" 동작은 `claim_run` 안의 stale 정리 + 기존 동작으로 유지한다. INSERT 본문은 `sync_jobs.py`에서 `_insert_job(conn, ...)`으로 떼어 `create_job`·`claim_run`이 공유한다.

### 2.4 쓰기 경로(4종 모두 원장 단독)

| 경로 | 시작 | 진행 | 종료 |
|---|---|---|---|
| 수동(`/trigger-sync`, `/trigger-sync-stream`) | 부모 `claim_run(source_path='manual', params={'mode'})` → None이면 `reason='running'` 건너뜀 | 자식 `sync.py --job-id`가 `start_run`으로 같은 행 재사용 + `heartbeat` | 자식 `finish_run`. 부모는 타임아웃·비정상 종료 때만 `fail_run`(현행 `_ledger_fail`). 건수는 stdout 대신 `get_job(id).synced_count`, 부분 실패는 `error_code` |
| bg(`/trigger-sync-bg`, trigger·range 서비스) | `claim_run(source_path='bg'/'range')` | `update_job` 진행 + `heartbeat` | 현행 그대로 |
| 자동(`auto_sync._trigger`) | `start_basic_sync(source_path='auto')` → 내부 `claim_run` | bg와 동일 | bg와 동일. `mark_auto_sync_ran` 삭제 |
| CLI(`sync.py`) | `start_run(source_path='cli')` | `heartbeat` | `finish_run`. `mark_finished` 삭제 |

`finish_run`의 부분 실패 판정: `g = sync_gates.gate(service)`가 있고 `g.job_id == job_id`면 `partial_code='partial_rate_limited'`(`sync_errors.MESSAGES_KO`에 등록). 공급자 코드가 job_id를 알 수 있도록 `user_context.set_current_job(job_id)`(스레드 로컬)를 `sync.py`·`BgSyncThread.run`이 설정하고 `sync_gates.bump_backoff`가 읽어 `job_id`에 넣는다.

### 2.5 user_id 해석 — `src/utils/user_context.py`(신규, ~50줄)

```python
def set_current_user(user_id: str) -> None: ...
def resolve_user_id(user_id: str | None) -> str: ...   # 인자 → 스레드 로컬 → Flask 세션 → "default"
def set_current_job(job_id: str | None) -> None: ...
def current_job() -> str | None: ...
```

- 우선순위는 현행과 동일(동작 보존). `sync_jobs._conn`, `sync_gates`, `sync_ledger_query`가 모두 이 함수 하나를 쓴다.
- **명시 전달 원칙**: 요청 핸들러·서비스는 `user_id`를 인자로 넘긴다. 스레드 로컬 폴백은 user_id를 받을 수 없는 깊은 공급자 코드(garmin_helpers·runalyze·bg 내부)만을 위한 것이다.
- 정정 대상(현재 세션 폴백에 기대어 어긋날 수 있는 곳): `auto_sync.status()`가 인자 없이 `get_last_auto_sync()`를 부르는데, 자동 루프는 `start(config, user_id)`로 시작한 사용자 것이다 → 모듈에 `_user_id`를 보관하고 `status()`가 그 값을 쓴다. `bg_sync.get_status`의 `get_retry_after_sec(service)`·`get_latest_job(service)`에는 이미 받은 `user_id`를 넘긴다.
- DB 위치: 모든 원장·게이트는 `get_db_path(uid).parent / "sync_jobs.db"`에 있다. 게이트도 사용자별이다(현 json과 같음). Strava 한도는 앱 단위라 사용자별 게이트가 실제 한도보다 느슨하다. 현행과 같으므로 이 설계 범위 밖으로 두고 기록만 한다.

### 2.6 호출처별 교체

| 파일:행 | 현재 | 교체 |
|---|---|---|
| `src/sync.py:21,118` | `set_current_user` | `user_context.set_current_user` + `set_current_job` |
| `src/sync.py:33,69` | `mark_finished(error)` | 삭제(`finish_run`이 기록) + `with heartbeat` |
| `src/sync/strava.py:27,83` | `mark_finished` | 삭제. `bg_mode` 인자는 의미가 없어지므로 제거 |
| `src/sync/runalyze.py:13,83,106-107` | `get_retry_after_sec`·`set_retry_after(86400)`·`mark_finished` | `sync_gates.wait_sec`·`block(reason='auth_expired')`. `mark_finished` 삭제(예외 → `classify_exception` → `finish_run`) |
| `src/sync/garmin_helpers.py:9,76-98` | `get_retry_after_sec`+`set_retry_after` | `sync_gates.bump_backoff(service)` |
| `src/web/app.py:492-496` | `get_all_states` | `ledger_query.legacy_card_states(uid)` |
| `src/web/app.py:509-700`, `702-870` | `is_running`·`mark_running`·`mark_finished`·`get_last_sync_at`·`get_retry_after_sec`, stdout 파싱, `bg_get_status` 이중 검사 | 두 라우트의 소스별 본문을 **`src/services/manual_sync_service.py`**(~200줄)의 `run_one(src, mode, days, user_id, emit=None)` 하나로 추출. 판정 = `claim_run` 결과 + `sync_gates.wait_sec` + `last_success_at` 쿨다운. `_already_finished` 삭제 |
| `src/web/bg_sync.py:35,105,169,587` | `get_retry_after_sec`·`set_current_user` | `sync_gates.wait_sec(service, user_id)`·`user_context`. `start_job` → `claim_run`. `run()`에 `heartbeat`·`set_current_job` |
| `src/web/auto_sync.py:37-38,59,69-70,125-126` | `set_current_user`·`mark_auto_sync_ran`·`get_last_auto_sync` | `user_context`, 삭제, `ledger_query.last_auto_run(user_id)` |
| `src/web/helpers.py:898` | `get_last_sync_at` | `ledger_query.last_success_at(src, user_id)` |
| `src/web/views_settings_integrations.py:16,311` | `clear_retry_after("runalyze")` | `sync_gates.clear("runalyze", user_id)` |
| `src/web/views_sync.py:177` | `get_last_auto_sync`(import) | 삭제(`auto_sync.status()` 사용) |
| `src/services/sync_trigger_service.py:85,116` | `is_running`·`get_last_sync_at`·`get_retry_after_sec` + `bg_status` | `is_busy`·`last_success_at`·`sync_gates.wait_sec`. bg 행도 같은 원장이므로 `bg_status` 이중 검사 제거(D6 종료) |
| `src/services/sync_range_service.py:64,83` | `get_retry_after_sec`·`is_running` | 동일 교체 |
| `src/services/data_settings_service.py:66-72`, `src/api/routes_data.py:174-178` | `get_last_auto_sync(user_id)` | `ledger_query.last_auto_run(user_id)` |
| `src/services/export_service.py:188`, `recompute_service.py:79`, `import_service.py:162` | `set_current_user` | `user_context.set_current_user` |
| `src/utils/sync_jobs.py:137` | `sync_state._resolve_user_id` | `user_context.resolve_user_id` |
| `src/services/sync_state_service.py` | 자체 `success`·`running` 계산 | `last_success_at`·`busy_job` 사용 |

---

## 3. 교체 방식 비교와 추천

| 안 | 내용 | 장점 | 단점 |
|---|---|---|---|
| A. 어댑터 | `sync_state.py` 공개 함수 시그니처 유지, 내부만 원장 위임 | 호출처 무수정, diff 최소 | `mark_running(service, mode)`·`mark_finished(service, count)`는 job_id가 없어 원장 행에 대응시킬 수 없다 → "서비스의 최근 행"을 추측해 고치거나 고아 행을 만든다. 수동 경로에선 자식도 같은 실행을 기록하므로 **이중 행**이 생긴다. 이름이 "json 상태"인 모듈이 원장 계약을 숨겨 이후 독자를 오도한다. stdout 파싱·비원자 검사가 그대로 남는다 |
| B. 호출처 직접 수정 | 모든 호출처가 원장 API를 직접 사용 | 근본 해결 | 공통 읽기 질의를 호출처마다 다시 쓰면 "마지막 성공" 정의가 또 갈라진다 |
| **C. 목적별 새 모듈 + 호출처 수정(추천)** | 쓰기는 이미 있는 `ledger.start/finish/fail_run` + 새 `claim_run`으로 일원화. 읽기는 `sync_ledger_query`(파생 전용), 게이트는 `sync_gates`, 사용자 해석은 `user_context`. 호출처는 의미에 맞는 새 함수를 직접 부른다. `sync_state.py`는 마지막 단계에서 **삭제** | 쓰기 경로가 job_id 기반 하나로 정리되고, 파생 정의는 함수 1곳, 원자 선점·하트비트가 들어갈 자리가 생긴다 | 호출처 약 20개 파일 수정. 단계 분할(§5)로 각 커밋을 녹색으로 유지해야 한다 |

**추천: C.** A는 쓰기 함수를 의미 있게 위임할 수 없어 땜질이 된다. 단계 진행 중에만 `sync_state.py`의 읽기 함수가 새 모듈로 위임하는 임시 재수출을 허용하고, S5에서 파일째 지운다(최종 상태에 어댑터 없음).

---

## 4. 기존 사용자 데이터 전환과 롤백

| 키 | 처리 | 근거 |
|---|---|---|
| `retry_after`(미래 시각) | `sync_gates`로 **일회 이관**(`reason_code='rate_limited'`, `backoff_sec=남은 초`) | 버리면 Garmin 429 직후 재호출 위험. 로컬엔 없지만 운영엔 있을 수 있다 |
| `retry_after`(과거) | 무시 | 만료 |
| `last_sync_at`·`last_count`·`last_partial`·`last_error`·`is_running`·`started_at`·`current_mode` | 무시 | 원장에 이미 대응 행이 있다(`get_last_sync_at`이 원장을 병합해 왔음). 합성 "migrated" 행을 넣으면 원장 이력이 오염된다. 원장에 completed가 없는 소스는 쿨다운이 풀려 한 번 더 동기화를 허용할 뿐이다(안전한 쪽) |
| `_auto_sync.last_run` | 무시 | 배포 직후 자동 동기화 1회가 즉시 돌 수 있다. 무해 |
| `rate_state` | 무시 | dead |

- 실행: `src/utils/sync_state_retire.py`(~60줄)의 `retire_all_users()`를 앱 시작 시 `cleanup_stale_running_jobs_all_users` 옆에서 호출한다. 사용자 디렉터리를 돌며 게이트 이관 후 파일을 `sync_state.json.retired-YYYYMMDD`로 **이름만 바꾼다**(삭제 아님). 이름 바꾼 파일이 있으면 건너뛰므로 멱등이다.
- 운영: 데이터 볼륨이 있는 docker 컨테이너 안에서 실행돼야 한다(앱 시작 훅이므로 자동).
- **롤백**: 코드 되돌림 + `python3 -m src.utils.sync_state_retire --restore`(이름 원복). 추가한 `sync_gates` 테이블·`params_json` 열·인덱스는 추가형이라 구 코드가 무시한다. 구 `get_last_sync_at`은 원장을 병합하므로 전환 기간의 동기화 이력도 손실 없이 보인다. 전환 기간에 설정된 게이트만 잃는다(최대 24시간 영향).

---

## 5. 구현 단계(각 단계 독립 커밋, 모두 녹색)

| 단계 | 내용 | 새/변경 파일(예상 줄) | 커밋 |
|---|---|---|---|
| **R0 user_context 분리** | `set_current_user`·`resolve_user_id`·`set_current_job` 이동. `sync_state.py`는 재수출. 호출처 7곳 import 교체 | `utils/user_context.py`(~50) | `refactor:` |
| **R1 게이트 테이블** | `sync_gates` DDL + `params_json` 열 + 인덱스 2개(`sync_jobs_schema.py`). `sync_gates.py`. 게이트 읽기/쓰기 호출처 전부 교체(garmin_helpers·runalyze·views_settings_integrations·bg_sync·app.py·trigger·range). `retire_all_users`의 게이트 이관 부분(이름 변경은 아직 안 함). `sync_state.py`에서 retry 함수 삭제 | `utils/sync_gates.py`(~90), `utils/sync_state_retire.py`(~60) | `feat:` |
| **R2 선점·하트비트·질의** | `sync_jobs.py`에서 `_insert_job` 추출 + 정리 함수를 `utils/sync_jobs_maintenance.py`로 분리(현 293줄이라 추가 여유 없음). `ledger.claim_run`·`heartbeat`. `sync_ledger_query.py`. bg `start_job`→`claim_run`, `run()` 하트비트. `is_running` 호출처(trigger·range) 교체, `bg_status` 이중 검사 제거 | `sync_jobs_maintenance.py`(~80), `sync_ledger_query.py`(~130), `ledger.py`(~150) | `feat:` |
| **R3 수동 경로 원장 단독** | `manual_sync_service.run_one` 추출, app.py 두 라우트가 사용. `mark_running/finished`·stdout 파싱·`_already_finished` 삭제. `sync.py`·`strava.py`·`runalyze.py`의 `mark_finished` 삭제, `finish_run` 부분 실패 판정, `MESSAGES_KO['partial_rate_limited']` | `services/manual_sync_service.py`(~200), app.py 약 -250줄 | `refactor:` |
| **R4 읽기 전환** | `last_success_at`·`last_auto_run`·`legacy_card_states`로 helpers·app 대시보드·auto_sync(+`status` user 보관)·views_sync·routes_data·data_settings_service·sync_state_service 교체. `mark_auto_sync_ran` 삭제 | — | `refactor:` |
| **R5 퇴역** | `src/utils/sync_state.py` 삭제, `retire_all_users`에 파일 이름 변경 활성화, `.gitignore` 정리, `utils/__init__.py` docstring·`files_index` 재생성, ADR 기록, `sync-trigger-design.md` D6 종료 표기 | — | `chore:` + `docs:` |

### 5.1 테스트 계획(새 함수당 최소 1개)

| 파일 | 대상 | 예상 수 |
|---|---|---|
| `tests/test_user_context.py` | 인자 우선, 스레드 로컬, 세션 없음 → default, 스레드 간 격리, `current_job` | 5 |
| `tests/test_sync_gates.py` | `wait_sec` 없음/만료/활성, `bump_backoff` 최초 900·2배·상한 86400, `block`, `clear`, `job_id` 기록, 사용자별 DB 분리 | 9 |
| `tests/test_ledger_claim.py` | 빈 원장 선점, 신선한 running 있으면 None, stale(600초) 닫고 선점(`error_code='stale'`), 두 스레드 동시 선점 시 1개만 성공, 두 **프로세스**(multiprocessing) 동시 선점, `heartbeat`가 `updated_at` 갱신·종료 시 정지, `params_json` 저장 | 7 |
| `tests/test_sync_ledger_query.py` | `is_busy`(stale 무시·paused 제외), `last_success_at`(finished_at 우선·updated_at 폴백·실패 무시), `last_auto_run`(trigger='auto'만), `legacy_card_states` 키 모양 | 7 |
| `tests/test_sync_ledger_partial.py` | 실행 중 게이트 설정 → `partial_rate_limited`, 다른 job의 게이트는 무시 | 2 |
| `tests/test_manual_sync_service.py` | 성공 시 건수=원장 `synced_count`, 비정상 종료 `fail_run`, 타임아웃, 선점 실패 시 skip(subprocess 모킹) | 4 |
| `tests/test_sync_state_retire.py` | 미래 retry 이관, 과거 무시, 이름 변경·멱등, `--restore` | 4 |
| `tests/test_sync_paths_ledger.py` | 상위 §8 "네 경로 모두 원장 행" 통합 4건 + 각 경로 후 `sync_state.json` 미생성 | 4 |
| 기존 수정 | `test_data_settings`, `test_sync_trigger_service`, `test_sync_range`, `test_strava_403_ledger`, `test_auto_sync_reload`의 `sync_state` 모킹 → 새 모듈 | 5개 파일 |

합계 신규 약 42개.

### 5.2 완료 검증(DoD)

1. `grep -rnE "utils\.sync_state( import|\b)|utils import sync_state|sync_state\.json" src scripts | grep -v sync_state_retire` → 0행(`sync_state_service`는 패턴에 걸리지 않음).
2. `test ! -f src/utils/sync_state.py`.
3. `grep -rn "mark_running\|mark_finished\|mark_auto_sync_ran\|_already_finished" src` → 0행.
4. 통합 테스트: 네 경로 실행 후 tmp 프로젝트 루트에 `sync_state.json`이 생기지 않는다.
5. 같은 시점 Pill·사이드바·Data 개요·v1 대시보드 "마지막 성공"이 `last_success_at` 한 값과 같다(상위 §8 첫 항목).
6. 수동 동기화 중 프로세스를 kill하면 10분 이내 재시작 가능하다(브라우저/실제 서버 확인).
7. `python3 -m pytest tests/` 전체 통과, `python3 scripts/check_docs.py` 통과.

### 5.3 DDL 등록·정합성 검사 영향

- 원장은 `running.db`가 아니므로 **`db_setup.py`에 등록하지 않고 `SCHEMA_VERSION`도 올리지 않는다.** `sync_jobs.db` DDL의 단일 소스는 `sync_jobs_schema.py`(`CREATE_SQL`·`LEDGER_COLUMNS`·새 `GATES_SQL`)이다. 상위 설계 §7.2의 "DDL은 `db_setup.py`"는 사실과 다르므로 정정이 필요하다(사용자 결정 2).
- `/check-data-consistency`·`check_docs.py`에 검사 1개 추가 제안: `LEDGER_COLUMNS` 키 ⊆ `SyncJob` 필드 = `_COLS` 열 순서, `sync_gates` 열 = `Gate` 필드. 현재는 이 셋이 어긋나도 잡을 장치가 없다.
- `system-design-conventions` SKILL의 "Pipeline 테이블 11개 … sync_jobs"는 `running.db` 잔재 테이블을 가리킨다. 잔재 처리(사용자 결정 1) 후 문구를 갱신한다.

---

## 6. 기존 시스템과의 호환성

- **상위 design.md**: §7.2·§8과 같은 방향. 차이점 2가지. (a) DDL 위치(위 5.3). (b) 상위 설계가 열거한 `error_message_ko`·`job_type`은 이 작업에 필요하지 않아 넣지 않는다. 재계산·내보내기 원장화(S8)에서 다룬다.
- **sync-trigger-design.md D6**: R2에서 trigger 서비스의 json 검사가 사라지므로 D6의 "둘 다 확인" 기간이 끝난다.
- **sync_state_service(SyncState 계약)**: 응답 스키마 변화 없음. `running`·`last_success_at` 계산만 공통 함수로 바뀐다. stale 행이 "동기화 중"으로 보이던 오표시가 사라진다.
- **ADR-009 / metric_store**: 무관(메트릭 계산 경로 아님).
- **v1 화면**: `sync_ui.sync_card_html`의 입력 모양을 `legacy_card_states`가 유지하므로 v1 화면은 바뀌지 않는다. 단 `last_sync_at` 값이 원장 기준으로 바뀐다(의도한 변화).
- **동작 변화(의도)**: stale 기준 1시간 → 하트비트 10분. 자동 동기화 tick이 "행이 하나라도 생긴 실행" 기준이 된다. 모든 소스가 건너뛰어진 tick은 다음 시간에 다시 시도한다(이전엔 interval 동안 쉼). 백오프는 "직전 대기 × 2"로 바뀐다.

## 7. 대안과 트레이드오프(채택하지 않은 것)

| 대안 | 기각 이유 |
|---|---|
| 게이트를 작업 행 `retry_after`에서 파생 | 공급자 코드에 job_id가 필요하고, 토큰 재설정 해제가 이력 행을 고쳐 쓴다. 작업 없이 게이트만 남는 경우(403 후 24h)를 표현하기 어렵다 |
| 부분 유니크 인덱스 `UNIQUE(service) WHERE status IN ('pending','running')`로 선점 | 깔끔하지만 stale 행이 남으면 영구 차단된다. 기존 원장에 중복 running 행이 있을 수 있어 인덱스 생성이 실패할 수 있다. `BEGIN IMMEDIATE`로 같은 보장을 얻는다 |
| 자동 tick 전용 `job_type='auto_tick'` 행 / `_auto_sync` KV 테이블 | 위 2.1 결정표 |
| 별도 `sync_status` 소형 테이블로 json을 그대로 옮김 | 저장소만 바뀔 뿐 원장과의 이중 진실이 그대로다 |
| 하트비트 없이 `started_at` 1시간 유지 | 프로세스가 죽은 뒤 1시간 잠김, 1시간 넘는 정상 실행은 오판 |
| stdout 파싱 유지 | 출력 문구를 바꾸면 집계가 깨진다. 원장 `synced_count`가 이미 있다 |

## 8. ADR 후보(`v0.3/data/decisions.md`, 다음 번호 ADR-044부터)

1. **sync_state.json 퇴역 — 동기화 상태의 단일 진실은 `sync_jobs.db` 원장**, 모든 실행 경로는 job_id 기반 `claim/start/finish/fail_run`으로만 쓴다.
2. **요청 제한 게이트는 작업과 분리한 `sync_gates`(서비스당 1행)**에 둔다. 작업 행 `retry_after`는 이력 용도. 백오프 기준은 직전 대기.
3. **실행 중 판정 = 하트비트(600초) + `BEGIN IMMEDIATE` 원자 선점.** 읽기 함수는 부작용이 없다.
4. **user_id/job 컨텍스트는 `user_context` 모듈 하나.** 요청·서비스 계층은 명시 전달, 스레드 로컬은 공급자 내부 전용.
5. **`sync_jobs.db` DDL 소스는 `sync_jobs_schema.py`**(running.db·`SCHEMA_VERSION`과 독립), 정합성 검사 대상에 포함.
6. **json 전환 정책**: 활성 게이트만 이관, 나머지는 버리고 파일은 이름 변경으로 보존(롤백용).

---

## 9. 사용자 결정 필요

| # | 항목 | 추천 |
|---|---|---|
| 1 | `running.db`의 잔재 `sync_jobs` 테이블(`db_setup.py:395`, 미사용)을 이번에 지울지 | **이번 범위 밖, 별도 백로그.** DROP은 `SCHEMA_VERSION` 상향·사용자 DB 마이그레이션이 필요해 위험 성격이 다르다 |
| 2 | 상위 `design.md` §7.2의 "DDL은 `db_setup.py`" 문구를 "`sync_jobs_schema.py`(사용자별 `sync_jobs.db`)"로 정정할지 | 정정 |
| 3 | stale 기준을 하트비트 10분으로 바꾸는 동작 변화 승인 | 승인 |
| 4 | json 전환: 활성 `retry_after`만 이관하고 나머지는 버림, 파일은 삭제 대신 이름 변경 | 승인 |
| 5 | R3에서 app.py 수동 두 라우트를 `manual_sync_service`로 추출(범위 확장, 약 -250줄) | 승인. 추출하지 않으면 같은 교체를 두 번 해야 하고 1398줄 파일이 그대로 남는다 |

## 10. 구현 기록

완료 2026-10-10. R0~R5 전 단계 구현·배포. 전체 테스트 2984 passed 기준 + R4/R5 갱신분.
- R0 `utils/user_context.py` 분리 / R1 `sync_gates` 테이블 / R2 `claim_run`·`heartbeat`·`sync_ledger_query` / R3 `manual_sync_service` 추출(app.py -250줄), `mark_running/finished` 제거 / R4 읽기 전환(`last_success_at`·`last_auto_run`·`legacy_card_states`) / R5 `utils/sync_state.py` 삭제, `sync_state_retire` 이관 활성(`RENAME_ENABLED=True`, 파일은 `.retired-YYYYMMDD`로 이름 변경).
- 잔여: `running.db`의 `sync_jobs` 잔재(`db_setup.py:395`) DROP은 별도 백로그(SYNC-JOBS-LEGACY-DROP).
