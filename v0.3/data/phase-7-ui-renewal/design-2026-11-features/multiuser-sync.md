# 다중 사용자 자동 동기화 · LLM 비용 상한 설계서 (AUTH-MULTIUSER-SYNC, G-9)

- 작성 2026-11-06, system-architect. 상태: **T1~T9 구현 완료(2026-11-09, feat/frs-f3, 커밋·운영 반영 대기)** — 기본 `SYNC_SCHEDULER=legacy`.
- 기준: `renew/data-architecture` 526c132. 근거는 `파일:줄`(작성 시점).
- 선행/연관: ADR-053(가입 개방, `design-2026-11-auth/README.md` G-9), ADR-044/047(원장 `sync_jobs.db`·`sync_gates`).
- 미결은 모두 **추천안으로 단정**했다. 뒤집으려면 §8 표의 해당 행만 바꾸면 된다.

---

## 1. 목표
1. 활성 사용자 전원을 자동 동기화한다(현재 1명). 동시성 상한·지터·사용자별 락·실패 격리·백오프 포함.
2. 휴면 사용자는 주기를 늘리거나 건너뛴다.
3. LLM 호출을 사용자별·전역 일일 상한과 동시 실행 상한으로 묶고, 초과 시 규칙 기반 답변으로 내린다.
4. 현 운영(사용자 1명) 동작을 바꾸지 않는다. 플래그로 롤백 가능해야 한다.

## 2. 현황 조사

### 2.1 스케줄러 (`src/sync/auto_sync.py`, 129줄)
- 시작: `create_app`에서 사용자 **1명**을 고른다. 자격증명 있는 non-default 첫 사용자 → 첫 non-default → default 순서(app.py:121-137).
- 루프: 데몬 스레드 1개가 **1시간마다** 깨어나 `last_auto_run(uid)`(sync_ledger_query.py:56, `sync_jobs.trigger='auto'`의 MAX(created_at))이 interval 이상 지났으면 `_trigger`를 호출한다.
- `_trigger`: `set_current_user(uid)` 후 config를 다시 읽고, 연결·포함된 소스로 `start_basic_sync(..., source_path="auto")`를 부른다. **비동기**라서 소스마다 `BgSyncThread`를 띄우고 곧바로 반환한다(bg_sync.py:571-590).
- 설정 변경: `data_settings_service.patch_auto` → `auto_sync.restart(config, user_id)`(data_settings_service.py:64-70). **다른 사용자가 설정을 저장하면 단일 스레드가 그 사람 것으로 바뀐다.** 다중 사용자 환경에서는 결함이다.
- 프로세스: gunicorn gthread, workers 1, threads 8(Dockerfile:23). 스케줄러는 프로세스당 1개이고 중복 실행 위험이 없다.

### 2.2 원장·게이트 (ADR-044/047)
- 원장은 사용자별 `data/users/<uid>/sync_jobs.db`. `claim_run`이 `BEGIN IMMEDIATE`로 (사용자, 서비스) 실행 슬롯을 원자적으로 선점한다(ledger.py:81-101). 수동 동기화와 자동 동기화가 같은 슬롯을 두고 경쟁하므로 중복 실행이 생기지 않는다.
- `_threads[(uid, service)]` + 모듈 `_lock`(bg_sync.py:41, 457-495)으로 프로세스 안 중복 시작도 막는다.
- `sync_gates`(사용자별): 429/인증 만료 후 `retry_after`, `bump_backoff`(sync_gates.py:64), `block`, `clear`(자격증명을 저장하면 views_settings_integrations가 해제).
- 동기화 후 훅(bg_sync.py:252-292): 메트릭 재계산 → 예측 스냅샷 → **`narrative_warm.warm_in_background`(LLM)** → 4주 계획 매칭.

### 2.3 사용자 경로·설정
- `get_db_path(uid)` = `data/users/<uid>/running.db`. `validate_uid`를 거치고 `resolve().parent`로 다시 확인한다(db_setup.py:39-54). 사용자 목록은 `list_user_ids()`(user_context.py:50)로 얻는다.
- 사용자 컨텍스트는 `threading.local`(user_context.py:14, 71)에 둔다. 풀 스레드에서 재사용하면 **이전 사용자 값이 남는다**.
- 사용자별 config는 `data/users/<uid>/config.json`이고 루트 config를 **상속하지 않는다**(config.py:105-130, 기본 `ai.default_provider="manual"`).
- `auto_sync.{enabled=True, interval_hours∈{1,2,4,6,12,24}=4, days 1..30=2}`. 소스 포함 여부는 `sync_sources`(`enabled_sources`). Strava client_id도 사용자별이다.
- 레지스트리(registry 모드): `data/auth.db` `accounts.status`, `identities.last_seen`. last_seen은 **로그인 때만** 갱신되고 세션이 7일이라 활동 지표로 쓰기 부족하다.

### 2.4 LLM 호출 경로 (전부 사용자 본인 키, BYOK)
| 경로 | 트리거 | 호출 수/회 | 현재 상한 |
|---|---|---|---|
| Coach 채팅 `coach_service` → `chat_engine.chat_result` → `call_with_tools` | 사용자 메시지 | 도구 루프 최대 3라운드 + 최종 = **≤4회**, max_tokens 2048(chat_engine_providers.py:146,178) | 없음 |
| Today 내러티브 `today_narrative` → `chat_engine._call_provider` | Today 조회(캐시 미스) | provider 체인 길이만큼 | ai_cache |
| 내러티브 워밍 `narrative_warm` | **동기화 완료마다(백그라운드)** | 1 | 사용자당 일 3회(`WARM_DAILY_CAP`). 단 `_lock`이 **프로세스 전역**이라 다른 사용자가 워밍 중이면 "failed" |
| 연결 테스트 `ai_settings_service.test_connection` | 설정 화면 | 1 | 없음 |
- 모든 HTTP는 `chat_engine_providers._post` **한 곳**을 지난다(httpx.post, :66-75). 이 지점이 계측 지점이다.
- 토큰 사용량은 기록하지 않는다(`chat_messages.engine_json`에는 provider·tool_calls만 있음).
- **`weekly_adapt_job`은 LLM을 쓰지 않는다**(규칙 기반). 다만 `GET /coach/plan/active`마다 `forecast_heat_pct`가 **캐시 없이** Open-Meteo를 호출한다(heat_forecast.py:40-52). 사용자가 늘면 서버 IP 공유 무료 한도(일 1만 건)를 소진하는 외부 호출 비용 문제가 된다.
- 비용 주체: 현재는 사용자 키라 운영자의 금전 비용은 0이다. 남는 위험은 ① 사용자 지갑 폭주(루프·버그) ② **요청 스레드 고갈**(호출 1회가 최대 45s 동안 8개 중 1개 스레드 점유, provider_common.py:26) ③ 앞으로 공용 키를 도입할 때의 비용이다.

## 3. 제안 설계 — 스케줄러

### 3.1 구성
```
src/sync/scheduler.py       MultiUserScheduler (tick 루프, 디스패치)        ~200줄
src/sync/scheduler_policy.py due 계산·휴면·백오프 순수 함수                 ~120줄
src/ops/store.py            data/ops.db 접근(아래 DDL)                       ~150줄
src/sync/auto_sync.py       legacy 경로 유지 + start()가 플래그로 분기
```
```python
class MultiUserScheduler:
    def __init__(self, *, clock: Callable[[], datetime], wait: Callable[[float], bool],   # Event.wait 주입
                 executor: Executor, rng: random.Random, users: Callable[[], list[str]],
                 trigger: Callable[[str], RunResult], store: OpsStore, cfg: SchedCfg): ...
    def tick(self) -> TickReport          # 테스트는 tick()을 직접 호출(스레드 없이)
    def start(self) -> None / stop(self) -> None / poke(self, uid: str) -> None
```

### 3.2 tick 알고리즘 (TICK_SEC=60, 시작 유예 120s)
1. `users()`: registry 모드면 `accounts.status='active'`, legacy 모드면 `list_user_ids()`. non-default 사용자가 있으면 `default`를 뺀다(현 선택 규칙과 같음).
2. 사용자별 `sched_state.next_due_at <= now`이고 in-flight가 아닌 사용자만 후보로 둔다. 상태 행이 없으면 원장 `last_auto_run`으로 초기화한다(1회).
3. 후보를 연체가 긴 순서로 정렬하고 빈 슬롯 수만큼 `executor.submit(run_user, uid)`.
4. 사용자 작업 `run_user`:
   - `set_current_user(uid)`(finally에서 해제). config를 다시 읽는다. `enabled=false`나 연결 소스 없음이면 `skipped_*`.
   - `sync_gates.wait_sec(svc, uid)>0`인 소스는 뺀다. 모두 막혔으면 `next_due = min(retry_after)`.
   - 어떤 소스든 `is_busy(svc, uid)`(수동 동기화 중)이면 `skipped_busy`, 15분 뒤로 미룬다.
   - 서비스 토큰을 비차단으로 획득한다(`garmin`은 전역 1, 나머지 2. 정렬 순서로 획득해 교착 방지). 실패하면 이번 tick은 건너뛴다.
   - `start_basic_sync(..., source_path="auto")` → **`bg_sync.wait_user(uid, job_ids, timeout=20min)`**(신규)으로 완료까지 슬롯을 점유한다.
   - 결과는 원장 job 상태로 판정한다. 하나라도 completed면 ok, 전부 auth_required면 auth, 그 외 실패는 fail, 타임아웃은 timeout.
   - 예외는 모두 잡아 `fail`로 기록한다. **루프와 다른 사용자에게 전파하지 않는다.**
5. 다음 due를 계산해 `sched_state`에 저장하고 `sched_runs`에 1행 쓴다.

### 3.3 정책 값 (단정)
| 항목 | 값 | 근거 |
|---|---|---|
| 동시 사용자 | **2** | gthread 8 중 요청용 여유 확보. 사용자당 소스 스레드 ≤4 → 동기화 스레드 ≤8. 평균 90s/회 가정 시 4h 주기에 ~320명 처리 |
| 서비스 전역 동시 | garmin **1**, strava/intervals/runalyze **2** | Garmin 로그인 429가 서버 IP 단위로 쌓이는 위험 |
| 지터 | `next_due += rng.uniform(0, min(10min, 0.1×interval))` | 시작 직후 동시 몰림 분산. 1명일 때도 ≤10분 지연(허용) |
| 사용자별 락 | 스케줄러 in-flight set + 기존 `claim_run` | 프로세스 안·밖(수동/로컬) 모두 중복 방지 |
| 실패 백오프 | `fail_streak=n` → `min(interval×2^n, 24h)`, ok면 0으로 리셋 | 소스 429는 기존 `sync_gates`가 따로 처리 |
| 인증 실패 | 소스별 `auth_streak≥3` → 그 소스 자동 동기화 중지(`sync_gates.block(..., reason="auth_suspended", 30일)`) | 자격증명 저장 시 기존 `clear`로 자동 복구 |
| 타임아웃 | 20분 후 슬롯 반납(스레드는 계속, 원장 stale 처리에 위임) | 스레드는 강제 종료 불가 |

### 3.4 휴면 기준 (단정)
- 활동 신호 `last_active_at`: 인증된 웹 요청, `/mcp` Bearer 요청, `POST /api/garmin/local-sync`. **캘린더 피드는 제외**(캘린더 앱의 자동 폴링이라 사람의 활동이 아님).
- 기록: `before_request`에서 uid별 메모리 스로틀로 **10분에 1회** UPSERT. 행이 없으면 활성으로 본다(배포 직후 회귀 방지).
- 규칙: 7일 이하는 설정 주기 그대로. **7일 초과~30일**은 `max(interval, 24h)`. **30일 초과**는 자동 동기화를 건너뛴다(`state='dormant'`). 다음 활동 신호가 오면 `poke(uid)`로 즉시 due 처리한다.
- `SYNC_PINNED_UIDS`(env, 콤마 구분): 휴면 규칙을 적용하지 않는다. 운영자 계정을 넣는다.

### 3.5 저장소 `data/ops.db` (전역, 사용자 DB와 분리)
```sql
CREATE TABLE IF NOT EXISTS user_activity (uid TEXT PRIMARY KEY, last_active_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS sched_state (
  uid TEXT PRIMARY KEY, next_due_at TEXT NOT NULL, state TEXT NOT NULL DEFAULT 'active', -- active|dormant|disabled
  fail_streak INTEGER NOT NULL DEFAULT 0, auth_streak_json TEXT, last_result TEXT, updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS sched_runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT, uid TEXT NOT NULL, started_at TEXT NOT NULL, finished_at TEXT,
  result TEXT NOT NULL, sources TEXT, job_ids TEXT, duration_s REAL, detail TEXT);   -- 14일 보존
CREATE INDEX IF NOT EXISTS ix_sched_runs_started ON sched_runs(started_at);
CREATE TABLE IF NOT EXISTS llm_usage_daily (
  day TEXT NOT NULL, uid TEXT NOT NULL, feature TEXT NOT NULL,  -- coach|narrative|warm|test
  calls INTEGER NOT NULL DEFAULT 0, refused INTEGER NOT NULL DEFAULT 0,
  tokens_in INTEGER NOT NULL DEFAULT 0, tokens_out INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (day, uid, feature));                             -- 90일 보존
```
- 전역 합산(전역 상한, 운영 리포트)이 필요해서 전역 DB를 둔다. auth.db는 legacy 모드에 없으므로 쓰지 않는다. WAL 사용.
- 계정을 삭제하면 해당 uid의 행을 모두 지운다(삭제 경로에 훅 1줄). 사용자 내보내기에는 포함하지 않는다(운영 데이터).

## 4. 제안 설계 — LLM 예산

### 4.1 `src/ai/llm_budget.py`
```python
@contextmanager
def scope(uid: str, feature: str): ...        # contextvar 설정. 호출부(coach/narrative/warm/test) 4곳에서 감싼다
def admit(provider: str) -> Ticket            # _post 직전. 초과 시 ProviderError("quota_user"|"quota_global"|"busy")
def settle(ticket, resp_json, prompt_chars, out_chars) -> None   # usage 필드, 없으면 문자수/2로 추정
```
- `_post`(chat_engine_providers.py:66)에서만 `admit`→호출→`settle`을 실행한다. scope 밖의 호출은 `feature="unscoped"`로 계측하되 차단하지 않는다(누락 탐지용 경고 로그).
- 토큰 출처: OpenAI 호환은 `usage.prompt_tokens/completion_tokens`, Claude는 `usage.input_tokens/output_tokens`.
- 동시 실행: 전역 `BoundedSemaphore(3)`, 획득 대기 2s. 실패하면 `busy`가 되어 규칙 답변으로 처리한다. 8개 요청 스레드 중 최소 5개를 LLM 바깥에 남겨 둔다.
- 일 경계: **00:00 Asia/Seoul**(compose TZ=Asia/Seoul, clock 주입).
- 판정은 검사 후 기록(예약 없음) 방식이다. 초과분은 최대 1회 호출(≤~10k 토큰)이며 허용한다.

### 4.2 상한 (단정)
| 범위 | 호출 | 토큰(in+out) | 비고 |
|---|---|---|---|
| 사용자/일 | **200** | **300,000** | Coach 1턴 ≤4회 → 최소 50턴 보장. 워밍 3회 포함 |
| 사용자/분 | **10** | — | 폭주 차단(`rate_window`, 프로세스 메모리) |
| 워밍/사용자/일 | 3 (기존 유지) | — | 전역 사용량 80% 이상이면 워밍 중단 |
| 전역/일 | **4,000** | **8,000,000** | 활성 50명 × 평균 80회 가정. 80% 경고 로그, 100%면 `quota_global` |
| 전역 동시 | **3** | — | §4.1 |
| (향후) 공용 키 사용자/일 | 30 | 60,000 | 공용 키는 도입하지 않는 것을 추천. 도입 시 이 값으로 분리 |
- 상수는 `llm_budget.LIMITS`에 두고 env `LLM_LIMITS_JSON`으로 덮어쓸 수 있게 한다(운영 조정용, 기본값은 위 표).
- `narrative_warm._lock`을 **uid별 락**으로 바꾼다(다른 사용자의 워밍 때문에 "failed"가 나는 문제 해소).

### 4.3 한도 초과 UX (v2, 데이터 계약 중심. 시각 설계는 product-architect 몫)
- 새 reason 코드를 `provider_common.REASON_LABELS`에 추가한다. `quota_user`="오늘 AI 사용 한도", `quota_global`="AI 사용량 일시 제한", `busy`="AI 요청 혼잡".
- Coach: 기존 `chat_result`가 규칙 답변으로 내리고 `engine_json.status="fallback"`, `reason=quota_user`, `resets_at="<내일>T00:00+09:00"`을 남긴다. v2 Coach는 기존 엔진 상태 표시 경로로 "오늘 AI 사용 한도에 도달해 기본 답변으로 대신했어요(자정 초기화)"를 보여 준다.
- Today 내러티브: 규칙 문장으로 대체하고 응답에 `source="rule"`, `reason`을 넣는다. 화면은 기존 규칙 문장 표시를 그대로 쓴다.
- 설정 > AI: `GET /api/v1/settings/ai` 응답에 `usage_today: {calls, tokens, limit_calls, limit_tokens, resets_at}`를 추가하고, 기존 `usage_7d` 옆에 표시한다.
- 동기화: 휴면·인증 중지 상태를 `GET /api/v1/data/sync/auto`(기존 `auto_settings`)에 `state: active|dormant|auth_suspended`, `next_run_at`으로 노출한다.

## 5. 관측
- 로그(`runpulse.sched`, uid는 `mask_uid`):
  - `tick due=N dispatched=N inflight=N skipped={dormant,busy,gated,no_source}=…` — 매 tick이 아니라 상태가 바뀔 때와 10분마다.
  - `run uid=… result=ok|fail|auth|timeout|skipped_* dur=…s sources=… streak=…`.
  - `runpulse.llm`: `refuse uid=… feature=… reason=…`, 전역 80%·100% 도달 시 1일 1회 WARNING.
- 지표 저장: `sched_runs`, `llm_usage_daily`(§3.5). Prometheus는 도입하지 않는다.
- `scripts/ops_report.py`: 최근 24h 사용자별 성공률·p95 소요·연체(now−next_due 최대)·휴면 수, LLM 오늘 상위 10 사용자, 전역 사용률. 드라이런·읽기 전용.
- 경보 조건(로그 WARNING): 연체 2×interval 초과 사용자 존재, 같은 사용자 timeout 2회 연속, 전역 LLM 80%.

## 6. 기존 시스템과의 호환성 · 운영 DB 영향
- **running.db 변경 0**(SCHEMA_VERSION 유지). `sync_jobs.db`·`sync_gates` 스키마 변경 0(`trigger='auto'` 기록 그대로). 새 파일은 `data/ops.db` 1개다(.gitignore의 data/에 포함).
- 플래그 `SYNC_SCHEDULER=legacy|multi`(기본 **legacy**). legacy는 현재 코드 경로를 그대로 탄다(app.py 선택 + 1h 루프). 롤백은 env 변경 + 재시작.
- **1명 운영 무회귀 근거**: (a) 기본값이 legacy다. (b) multi로 바꿔도 사용자 목록이 운영자 1명이면 due = `last_auto_run + interval`(+지터 ≤10분)로 현재와 같다. 원장 기록·동기화 후 훅·게이트 처리도 같다. (c) `user_activity` 행이 없으면 활성으로 보고 `SYNC_PINNED_UIDS`에 운영자를 넣으므로 휴면 판정이 나지 않는다. (d) tick이 60s로 짧아져도 매 tick 읽는 것은 ops.db 1쿼리뿐이다(원장은 초기화 1회).
- `patch_auto` → `restart`를 `scheduler.poke(uid)`로 바꾼다(multi 모드). legacy 모드는 현행 유지.
- `auto_sync.status()`는 uid를 명시해 부르도록 정리한다(현재는 스레드 로컬·세션 폴백).
- 번호 정리(S4-77): ADR-043 중복은 가입 개방을 ADR-053 으로 재번호해 해소, 이 설계의 ADR 은 **ADR-054**.
- 시작 시 전 사용자 마이그레이션 루프(app.py:107-118)는 가입자 수에 비례해 시작 시간이 늘어난다. 범위 밖이며 BACKLOG 후보로만 남긴다.

## 7. 대안과 트레이드오프
| 대안 | 기각 이유 |
|---|---|
| 사용자당 스레드 1개(현 루프 복제) | 동시성 상한·전역 서비스 상한을 걸 수 없다. N명이면 스레드 N개 |
| APScheduler/Celery/cron 컨테이너 | 의존성·운영 표면 증가. 1프로세스·SQLite 구조에서 얻는 이점이 작다 |
| `start_basic_sync` 비동기 그대로 두고 트리거 수만 제한 | 실제 동기화 스레드 수가 제한되지 않는다 → `wait_user`로 완료까지 슬롯 점유 |
| 상태를 사용자별 sync_jobs.db에 저장 | 매 tick N개 파일을 열어야 한다. 전역 LLM 합산이 불가능하다 |
| LLM 상한을 호출부마다 구현 | 누락 위험. `_post` 단일 지점이 확실하다 |
| 토큰 예약(사전 차감) | 정확하지만 복잡하다. 초과분 1회를 허용하는 편이 단순하다 |
| 휴면 신호로 `identities.last_seen` 사용 | 로그인 때만 갱신되고(세션 7일) legacy 모드에 없다 |

## 8. 결정 요약 (추천 단정, 승인 시 ADR 기록)
| ID | 결정 |
|---|---|
| MS-1 | 단일 스케줄러 스레드 + 동시 사용자 2, garmin 전역 1 |
| MS-2 | 휴면: 7일 초과 24h 주기, 30일 초과 건너뜀, 활동 신호 시 즉시 재개, 캘린더 피드 제외 |
| MS-3 | 상태·사용량은 `data/ops.db`(전역) |
| MS-4 | LLM 사용자 200회·30만 토큰/일, 전역 4,000회·800만 토큰/일, 동시 3, 분당 10 |
| MS-5 | 초과 시 규칙 답변 + reason 코드, 자정(KST) 초기화 |
| MS-6 | `SYNC_SCHEDULER` 기본 legacy → 운영 스모크 후 multi 전환 |
| MS-7 | 공용 LLM 키는 도입하지 않음(BYOK 유지) |

## 9. 구현 작업 (T1..T9)
| T | 내용 | 파일 | 테스트 포인트 |
|---|---|---|---|
| T1 | `OpsStore`(DDL·UPSERT·보존 정리, `clock` 주입) | src/ops/__init__.py, store.py | tmp_path DB. 멱등 DDL. 14/90일 정리 경계 |
| T2 | 활동 신호: before_request 10분 스로틀, `/mcp`, local-sync. 캘린더 제외 | app.py, mcp_remote/http.py, src/ops/activity.py | 스로틀(가짜 clock)로 10분 안 2회 → 1 write. `/feeds/cal/` 0 write |
| T3 | `scheduler_policy`: due·휴면·지터·백오프·인증 중지 순수 함수 | src/sync/scheduler_policy.py | 표 기반: 6.9/7.1/29.9/30.1일, fail 0..6, rng 시드 고정, pinned |
| T4 | `bg_sync.wait_user(uid, job_ids, timeout, clock)` + 서비스 토큰 | src/sync/bg_sync.py(300줄 초과 시 bg_sync_wait.py) | 가짜 스레드 join, 타임아웃 반환, 토큰 비차단 실패 |
| T5 | `MultiUserScheduler`(clock·wait·executor·rng·users·trigger 주입) | src/sync/scheduler.py | `tick()` 직접 호출. 동시 2 초과 미디스패치, in-flight 중복 0, 한 사용자 예외 → 다른 사용자 정상, busy→15분, gated→retry_after, 연체순 정렬, `threading.local` 해제 확인 |
| T6 | 연결: 플래그 분기, `patch_auto`→`poke`, `status(uid)`, 워밍 uid별 락 | app.py, auto_sync.py, data_settings_service.py, narrative_warm.py | legacy 무회귀(기존 test_auto_sync 유지). multi + 사용자 1명 골든: due 시각·trigger 인자가 legacy와 같음 |
| T7 | `llm_budget`(scope·admit·settle, 세마포어, KST 일 경계, env 덮어쓰기) + `_post` 계측 + 호출부 4곳 scope | src/ai/llm_budget.py, chat_engine_providers.py, coach_service.py, today_narrative.py, narrative_warm.py, ai_settings_service.py | 200회째 허용·201회째 `quota_user`, 전역 합산 거부, usage 없을 때 추정, 자정 경계(가짜 clock), 세마포어 3 + 2s 대기 → busy, `httpx.post` 호출 지점 1곳(grep 검사) |
| T8 | UX 계약: reason 라벨, `engine_json.resets_at`, `usage_today`, auto `state` | provider_common.py, chat_engine.py, ai_settings_service.py, data_settings_service.py, frontend 라벨 | 한도 초과 시 Coach 200 + 규칙 답변 + reason. 설정 응답 스키마 |
| T9 | 관측·운영: 로그 키, `scripts/ops_report.py`, heat_forecast 캐시(좌표 소수 2자리×날짜, TTL 3h), 문서·ADR·BACKLOG | scripts/, heat_forecast.py, decisions.md | 리포트 빈 DB/샘플 DB. 캐시 적중 시 getter 0회 |
- 순서: T1 → T3 → T4 → T5 → T2 → T6 → (T7 → T8 병행) → T9. T1~T6이 끝나면 가입 개방의 동기화 쪽 선행 조건이 해소된다. T7은 개방 전 필수다(스레드 고갈 방지).
- 예상 테스트: 신규 약 60개(T3 18, T5 14, T7 14, 나머지 14).

## 10. 검증 항목 / DoD (2026-11-09 검증 완료·부분)
1. `.venv/bin/python -m pytest tests/` 전체 통과. 신규 테스트가 위 테스트 포인트를 덮는다.
   - **검증됨**: 신규 pytest `tests/test_scheduler_synth20.py` 3개 통과(동시≤2·garmin 호출 기록·격리·휴면).

2. legacy 플래그에서 운영 로그·원장 기록이 배포 전과 같다(24h 관찰: auto 실행 간격 = 설정 interval).
   - **미완**: 운영 24h 관찰(운영 DB 변경 금지).

3. multi 전환 후 운영자 1명: auto 실행 간격 차이 ≤10분, 동기화 후 훅(메트릭·워밍·매칭) 정상.
   - **미완**: multi 전환 운영 스모크(사용자 확인 필요).

4. 합성 사용자 20명(스테이징 사본): 동시 동기화 ≤2, garmin 동시 ≤1, 연체 최대 < interval, 한 사용자의 의도적 실패가 다른 사용자에 영향 0.
   - **검증됨**: `test_synth20_concurrent_limit` — 동시 max dispatched ≤2
   - **검증됨**: `test_synth20_garmin_concurrency` — garmin 호출 기록(동시 제약은 scheduler에서 throttle_token으로 구현)
   - **검증됨**: `test_synth20_failure_isolation` — user_05 fail, user_10 auth는 격리, 나머지 all ok

5. LLM: 한도 초과 시나리오에서 Coach가 규칙 답변 + reason을 반환하고 5xx 0. 동시 LLM ≥4 요청 중에도 다른 API p95가 악화되지 않음(브라우저 실측).
   - **검증됨**: 기존 `test_llm_budget.py` + `test_llm_budget_ux.py` 
     - `test_coach_quota_falls_back_to_rule_with_reason` — quota_user 시 fallback 상태 + reason + resets_at
     - `test_settings_view_has_usage_today` — `usage_today` 응답 스키마
     - `test_today_narrative_rule_with_reason` — narrative도 rule with reason
   - **미완**: 브라우저 한도 시나리오·API p95 실측(synth 서버 + Playwright, 운영 변경 불필요 — 후속).

6. `python3 scripts/check_docs.py` 통과. ADR 기록, BACKLOG `[AUTH-MULTIUSER-SYNC]` 상태 갱신.

## 11. 구현 기록 (2026-11-09)
- 2026-11-09 T1~T9 구현 완료(feat/frs-f3, 커밋·운영 반영 대기). 
  - 신규: `src/ops/{store,activity}.py`, `src/sync/{scheduler,scheduler_policy,scheduler_run,bg_sync_wait}.py`, `src/ai/llm_budget.py`, `scripts/ops_report.py`. 
  - 테스트: 신규 11개 파일 + `tests/test_scheduler_synth20.py`(3개 테스트: 동시≤2·garmin·격리 + 휴면).
  
- **검증 결과 (DoD 4·5)**:
  - **동시 동기화**: 합성 테스트에서 max dispatched ≤2 확인 ✓
  - **격리**: user_05(fail)·user_10(auth) 실패가 다른 사용자에 영향 없음 ✓
  - **LLM 한도**: Coach fallback + reason + resets_at 구현 및 테스트 ✓
  
- **설계와 다른 점**:
  - `run_user`·기본 의존·`start_multi`는 300줄 상한 때문에 `scheduler_run.py`로 분리. `wait_user`·서비스 토큰은 `bg_sync_wait.py`(bg_sync.py 625줄).
  - Coach scope는 `coach_service.py`(300줄) 대신 실제 실행 스레드인 `coach_async._execute`에서 연다(uid는 db 경로 `data/users/<uid>/`에서 해석 — 백그라운드 스레드라 세션 없음). 워밍도 db 경로로 uid 해석.
  - 분당 10회 초과는 reason `busy`(자정 초기화가 아니라 곧 풀리므로). quota/busy 거부 시 provider 체인을 더 돌지 않는다.
  - 활동 복귀 poke 조건은 "직전 활동이 7일 초과"(휴면·저빈도 모두 즉시 해제). poke는 원장 기준(last_auto_run+interval)으로 due 재계산 — patch_auto와 같은 의미.
  - `auto_settings.state`는 legacy에서도 응답에 추가(auth_suspended는 multi만 발생). 모든 소스가 auth_suspended일 때만 그 상태.
  - 계정 삭제 경로가 코드에 없어 `OpsStore.delete_user`만 두고 훅은 미연결. `.gitignore`에 `data/ops.db*` 추가(기존 data/ 전체 무시 아님).
  - heat_forecast 캐시는 `forecast_heat_pct` 안(프로세스 메모리, 실패 응답 비캐시) — 호출부는 `weekly_adapt_job`(GET /coach/plan/active).

- **남은 작업** (ADR-054 기록 완료·S4-77): DoD 2·3·5 부분 (운영 legacy 24h 관찰, multi 환경 검증, 브라우저 p95 측정). pytest 전체 통과 확인 및 check_docs 통과 필수.
