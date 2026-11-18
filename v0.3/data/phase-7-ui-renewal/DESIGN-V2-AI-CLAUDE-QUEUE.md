# V2-AI — Claude Code CLI 큐(claude_queue) 설계안

상태: **설계안(방향·결정 1~3 승인 2026-11-18, 구현 E1 착수 전).** 코드·DB 변경 없음. 실측은 §4.1(haiku, 4회 호출).
이미 내린 결정(재질문 안 함): 개인·테스트 용도라 약관 회색지대는 감수하고, 서비스화하면 API 로 전환한다. 본인 uid(`pansongit@gmail.com`)만 허용한다. 사용량 별도 제한은 두지 않는다. 적용 범위 5종(코치 채팅·플랜 생성·훈련 이행 분석·인사이트 다듬기·Today 내러티브). 매 호출 새 세션 방식은 쓰지 않는다.

## 1. 문제
- 외부 LLM(Groq 등)은 429 가 잦고 품질이 낮다. Anthropic API 키는 없고, 호스트에 Claude Code CLI(v2.1.310, 구독 로그인)가 있다.
- 앱은 컨테이너 `runpulse-runpulse-1`(root, `/home/ubuntu/projects/RunPulse` → `/app`) 안에서 돈다. CLI 와 인증(`~/.claude`)은 호스트 ubuntu 계정에만 있다.
- 호출은 모두 `chat_engine_providers._post`(HTTP, `llm_budget.admit/settle`)를 지난다. 입구는 두 곳이다. `_call_provider`(도구 없음: insight_polish, today_narrative, 설정 핑)와 `complete(tools=True)`(코치 채팅)다.
- `claude -p` 를 매번 새로 띄우면 기동 비용이 ~1.6s 들고 대화 맥락이 사라진다. MCP 도구를 1회 쓰면 ~8.7s 걸린다.
- 숨은 결함: `polish_open_events` 는 bg_sync 쓰기 트랜잭션(`bg_sync.py:274`, commit 전) 안에서 돈다. 여기서 큐를 기다리면 같은 DB 에 결과를 쓰려는 워커와 교착한다. 그래서 E2 에서 commit 뒤 백그라운드로 옮긴다.

## 2. 원칙
1. **판정은 서버 규칙이 한다.** 사건 발생, 플랜 유효성(게이트), 근거 선택은 기존 규칙 코드가 정한다. LLM 은 문장과 초안만 만든다.
2. **검증을 통과한 출력만 반영한다.** 종류마다 서버 검증기가 있다(숫자 집합·길이·스키마·게이트). 실패하면 버린다.
3. **폴백 순서는 `claude_queue → 기존 체인(Groq/Gemini) → 규칙`이다.** 워커가 죽었거나 한도·타임아웃에 걸리면 기다리지 않고 다음 단계로 넘어간다.
4. **큐 입력은 인젝션이 들어 있다고 전제한다.** 사용자 메시지, 메모, 활동명은 데이터 블록으로 감싸고, 쓰기 도구는 주지 않는다.
5. **워커는 `ai_*` 테이블만 쓴다.** 도메인 테이블(insight_events, planned_workouts, 캐시)은 앱이 검증한 뒤에만 쓴다.
6. **대화의 진실은 DB 의 `chat_messages` 다.** CLI 세션은 버려도 되는 캐시이고, 언제든 DB 이력으로 다시 만든다.

## 3. 아키텍처
```
[브라우저]─SSE─[Flask 컨테이너: claude_queue provider]─INSERT/poll─┐
                                                        running.db (bind mount, WAL)
[호스트 systemd: runpulse-ai-worker]─claim/heartbeat/result─┘
      └─ claude -p (stream-json, 세션 풀 2) ─stdio─ python3 -m src.mcp_server (RUNPULSE_USER_ID 고정, mode=ro)
```
- 앱↔워커는 **DB 폴링**으로 잇는다. 호스트에서 컨테이너로 들어가는 새 엔드포인트를 만들지 않는다. 앱 대기 스레드는 200ms, 유휴 워커는 300ms 간격으로 폴링한다.
- 브라우저↔앱은 기존 경로를 그대로 쓴다. 코치는 `coach_async` SSE, 나머지는 백그라운드 결과를 캐시에서 읽는다.

### 3.1 v48 DDL 초안 (`db_schema_v48.py`, 유저별 running.db, 가산만)
```sql
CREATE TABLE ai_jobs (
  id INTEGER PRIMARY KEY,
  kind TEXT NOT NULL CHECK (kind IN ('coach','insight_polish','narrative','adherence','plan_draft','deep_analysis','ping')),
  thread_key TEXT,                 -- 영속 세션 키(coach:<thread_id>). 일회성은 NULL
  priority INTEGER NOT NULL DEFAULT 5,   -- coach 1 · plan 3 · ping 2 · 백그라운드 7
  state TEXT NOT NULL DEFAULT 'queued'
    CHECK (state IN ('queued','running','done','failed','cancelled','expired')),
  model TEXT NOT NULL,             -- sonnet|haiku (config 기본값, §8 결정 2)
  system_ctx TEXT, ctx_hash TEXT,  -- 고정 맥락(앱 생성)과 해시(§4.4)
  input_json TEXT NOT NULL,        -- {"turn": "...", "seed_history": [...]} 사용자 데이터는 <data> 블록
  tools TEXT NOT NULL DEFAULT 'none' CHECK (tools IN ('none','read')),
  output_schema TEXT NOT NULL DEFAULT 'text',  -- text | json:polish_v1 | json:adherence_v1 | json:plan_draft_v1
  progress_json TEXT, partial_text TEXT,       -- 진행 단계(도구명)·부분 답변(400ms 스로틀)
  result_text TEXT, error_reason TEXT,         -- reason: cq_down|cq_timeout|quota_sub|cli_error|cancelled|stale
  cancel_requested INTEGER NOT NULL DEFAULT 0,
  attempts INTEGER NOT NULL DEFAULT 0, worker_id TEXT, session_id TEXT,
  tokens_in INTEGER, tokens_out INTEGER, cache_read INTEGER, tool_calls INTEGER,
  queue_ms INTEGER, run_ms INTEGER,
  created_at TEXT NOT NULL, claimed_at TEXT, heartbeat_at TEXT, finished_at TEXT,
  expires_at TEXT NOT NULL         -- 이 시각이 지나면 워커가 집지 않음(expired)
);
CREATE INDEX ix_ai_jobs_queue ON ai_jobs(state, priority, id);
CREATE TABLE ai_sessions (         -- 스레드 ↔ CLI 세션 매핑(워커만 씀)
  thread_key TEXT PRIMARY KEY, session_id TEXT NOT NULL, model TEXT NOT NULL, ctx_hash TEXT,
  turns INTEGER NOT NULL DEFAULT 0, ctx_tokens INTEGER NOT NULL DEFAULT 0,  -- 마지막 턴 입력+캐시 토큰
  state TEXT NOT NULL DEFAULT 'active' CHECK (state IN ('active','retired','broken')),
  retired_reason TEXT, created_at TEXT NOT NULL, last_used_at TEXT NOT NULL
);
CREATE TABLE ai_worker_state (     -- 하트비트·전역 일시정지
  worker_id TEXT PRIMARY KEY, pid INTEGER, cli_version TEXT, started_at TEXT,
  heartbeat_at TEXT, active_jobs INTEGER, paused_until TEXT, last_error TEXT
);
CREATE TABLE ai_outputs (          -- 검증 통과 결과 캐시(훈련 이행 분석 등, 앱만 씀)
  kind TEXT NOT NULL, scope_key TEXT NOT NULL, src_hash TEXT NOT NULL,
  body_json TEXT NOT NULL, job_id INTEGER, created_at TEXT NOT NULL,
  PRIMARY KEY (kind, scope_key)
);
```
- 집기(claim)는 한 문장으로 끝낸다. `UPDATE ai_jobs SET state='running', worker_id=?, claimed_at=?, heartbeat_at=?, attempts=attempts+1 WHERE id=(SELECT id FROM ai_jobs WHERE state='queued' AND expires_at>? ORDER BY priority,id LIMIT 1) RETURNING ...`
- 보존: 완료 후 7일이 지나면 `input_json/system_ctx/result_text/partial_text` 를 NULL 로 지운다. 지표 컬럼은 남긴다.

### 3.2 앱 측 provider `claude_queue` (`src/ai/provider_claude_queue.py`, 신규)
- `available(config, uid)`: `ai.claude_queue.enabled` 이고 uid 가 `ai.claude_queue.uids` 에 있고, 하트비트가 20s 안쪽이고, `paused_until` 이 지났을 때만 참이다. 키가 없는 provider 이므로 `build_chain`·`coach_engine_health`·`coach_consent` 가 쓰는 `api_key_for` 판정을 `provider_available(p, config, uid)` 로 일반화한다. `LLM_PROVIDERS` 에 추가하고 체인 맨 앞에 둔다.
- `run(kind, ..., on_progress, cancelled, deadline)`: 별도 짧은 연결로 INSERT 한 뒤 폴링한다. `progress_json` 이 바뀌면 `on_event("stage")`, `partial_text` 가 늘면 delta 를 보낸다. 취소는 `cancel_requested=1` 로 알린다. 실패하면 `ProviderError(reason)` 를 던져 `run_chain` 이 기존 체인으로 넘어간다.
- 큐 대기 상한은 10s 다. 그 안에 아무도 집지 않으면 queued 행을 cancelled 로 바꾸고 `cq_timeout` 으로 끝낸다. 실행 마감은 coach 120s, polish 60s, narrative·adherence 90s, plan 240s 다. 폴백 체인은 그 뒤에 기존 `TOTAL_BUDGET` 45s 를 새로 받는다.
- **요청 스레드에서는 기다리지 않는다.** 예를 들어 GET `/today/narrative` 는 체인에서 claude_queue 를 빼고 지금처럼 동작한다. claude 결과는 백그라운드 경로(`narrative_warm`)가 캐시에 채운다.
- 예산: `llm_budget.admit` 을 거치지 않는다. 일 200회 상한을 Groq 폴백 몫으로 남기기 위해서다. 사용량은 `ai_jobs` 토큰 컬럼에 기록한다.

### 3.3 호스트 워커 (`src/ai_worker/`, 표준 라이브러리 + src 순수 모듈만, flask import 금지)
| 파일 | 역할 |
|------|------|
| `queue_store.py` | claim·heartbeat·finish·정체 회수·만료 처리(순수 SQL, 앱과 공유 상수) |
| `cli_runner.py` | argv 생성, stream-json 파싱(assistant/tool_use/result/rate_limit_event), 일회성 실행 |
| `session_pool.py` | 스레드별 상주 프로세스 풀(§4.3) |
| `main.py` | 루프·동시성 2·uid 화이트리스트·사전 점검·시그널 처리 |

- **uid 화이트리스트**: 환경변수 `CQ_UIDS` 에 있는 uid 의 DB 만 연다. uid 는 job 내용이 아니라 **DB 경로**에서 정한다. MCP 서버 env `RUNPULSE_USER_ID` 도 그 값으로 고정한다.
- **하트비트**: 5s 마다 `ai_worker_state.heartbeat_at` 과 실행 중 job 의 `heartbeat_at` 을 갱신한다.
- **정체 회수**: running 인데 heartbeat 가 60s 넘게 멈춘 job 은 `attempts<2` 면 queued 로 되돌리고, 아니면 failed(`stale`)로 끝낸다. 워커가 기동할 때 자기 worker_id 의 running 행을 전부 같은 규칙으로 처리한다.
- **429·구독 한도**: `rate_limit_event`, 또는 `is_error` 이면서 한도 문구가 있는 result 를 받으면 `paused_until` 을 기록한다(리셋 시각을 파싱하고, 실패하면 +15분). 해당 job 은 failed(`quota_sub`)로 끝낸다. 그러면 앱이 즉시 Groq 로 폴백한다. 일시정지 중에는 claim 하지 않는다.
- **사전 점검**(기동 시, 실패하면 종료하고 이유를 로그에 남김): `claude --version` 의 메이저·마이너가 허용 목록에 있어야 한다. DB·`-wal`·`-shm` 에 ubuntu 쓰기 권한이 있어야 한다(§3.4). 빈 작업 디렉터리가 있어야 한다.

systemd unit 초안 (`deploy/runpulse-ai-worker.service`, 사용자 유닛):
```ini
[Unit]
Description=RunPulse Claude queue worker
After=network-online.target docker.service
[Service]
Type=simple
WorkingDirectory=%h/.local/state/runpulse-ai/work
Environment=PYTHONPATH=/home/ubuntu/projects/RunPulse
Environment=RUNPULSE_ROOT=/home/ubuntu/projects/RunPulse
Environment=CQ_UIDS=pansongit@gmail.com
Environment=CQ_CONCURRENCY=2
ExecStart=/usr/bin/python3 -m src.ai_worker.main
Restart=on-failure
RestartSec=10
NoNewPrivileges=yes
PrivateTmp=yes
[Install]
WantedBy=default.target
```
(`loginctl enable-linger ubuntu` 가 필요하다. 코드는 운영 저장소에서 읽으므로 `renew/data-architecture` 에 머지돼야 반영된다.)

### 3.4 컨테이너↔호스트 경로·권한
- job 에 경로를 넣지 않는다. 워커가 `RUNPULSE_ROOT/data/users/<uid>/running.db` 를 스스로 계산한다. 시스템 프롬프트 파일은 워커가 `~/.local/state/runpulse-ai/ctx/<ctx_hash>.txt` 로 쓴다(앱은 텍스트만 넘긴다).
- **소유권 위험(실측)**: 컨테이너는 root 로 돈다. 같은 디렉터리의 `sync_jobs.db` 는 이미 root 소유다. 지금 `running.db*` 는 ubuntu 소유지만, 마지막 연결이 닫힌 뒤 컨테이너가 `-wal/-shm` 을 다시 만들면 root 소유 644 가 된다. 그러면 워커 쓰기와 호스트 MCP(ro) 연결이 모두 막힌다. 근본 해결은 compose 에 `user: "1001:1001"` 을 넣는 것이다(§8 결정 1). **결정: 채택(2026-11-18).** E1 에서 compose 에 `user: "1001:1001"` 을 넣고 기존 root 소유 파일(`sync_jobs.db` 등)을 1회 chown 한다(컨테이너 중지 상태에서). 이후 위험은 "재시작 뒤 쓰기·ro 읽기 시험"(§9-1)으로 검증만 한다. 사전 점검은 안전망으로 유지한다.

## 4. 맥락·속도 (핵심)
### 4.1 실측 (2026-11-18, haiku, `--tools "" --strict-mcp-config`, /tmp 에서 실행, 산출물은 삭제함)
| 방식 | 벽시계 | CLI duration / API | 비고 |
|------|------|------|------|
| 일회성 새 세션(`--session-id`) | ~2.8s | 2.76s / 0.77s | cache_create 2909 tok(기본 시스템 프롬프트) |
| `--resume` 후속 턴 | 5.0s | 3.35s / 1.48s | 맥락 유지 확인, cache_read 3231 |
| 상주 stream-json 1턴(기동 포함) | 4.5s | init 0.9s, 첫 assistant 1.9s | |
| 상주 stream-json 2턴 | **2.7s** | 첫 assistant **0.9s**, API 1.84s | 맥락 유지 확인 |
- 결론: `--resume` 은 매번 세션 jsonl 을 다시 읽고 기동하므로 후속 턴이 새 세션보다도 느리다. 상주 프로세스는 후속 턴에서 2s 이상 줄인다. MCP 서버(파이썬 import)도 상주하므로 도구 경로에서는 절감 폭이 더 클 것으로 예상하지만, 아직 재지 않았다.
- 표본이 1회씩이고 모델도 haiku 다. E1 벤치(`scripts/ai_worker/bench.py`)에서 sonnet 으로 방식별 n=5 를 재서 p50·p95 를 낸다. 통과 기준: 상주 후속 턴 p50 ≤ 5s(도구 없음), 도구 1회 포함 ≤ 12s, 큐 오버헤드 ≤ 0.7s.

### 4.2 영속 방식 결정: **스레드별 상주 stream-json + `--resume` 복구**
- 상주 프로세스 1개가 세션 1개를 맡는다. 기동 명령은 `claude -p --input-format stream-json --output-format stream-json --verbose --include-partial-messages --session-id <uuid>` 이고, 재기동할 때는 `--resume <uuid>` 를 쓴다. 턴은 한 줄 JSON(`{"type":"user",...}`)으로 쓰고 `result` 이벤트에서 끝낸다. 한 프로세스는 한 번에 한 턴만 처리하므로 같은 스레드 요청은 직렬화된다.
- 풀 크기는 동시성과 같은 2다. 슬롯이 다 찼으면 유휴 LRU 를 먼저 종료한다. 일회성 job 도 슬롯 1개를 쓴다.
- **유휴 종료**: 10분 동안 입력이 없으면 stdin 을 닫아 정상 종료시킨다. 세션 파일은 남으므로 다음 턴은 `--resume` 으로 띄운다(5s 대, 1회만).
- **재시작 복구**: 워커가 재시작되면 상주 프로세스는 모두 사라진다. `ai_sessions.state='active'` 인 스레드는 다음 턴에서 `--resume` 을 쓴다. resume 이 실패하면(종료 코드≠0, init 이벤트 없음, "No conversation") `broken` 으로 표시하고 새 세션 + DB 이력 시드로 다시 시도한다.
- **오염·누적 대응(세션 교체 기준)**: 아래 중 하나에 해당하면 `retired` 처리하고 새 session_id 를 만든다. 첫 턴에는 DB `chat_messages` 최근 6개(각 600자 이하)를 "이전 대화" 블록으로 넣는다.
  1. 마지막 result 의 입력+캐시 토큰이 60k 를 넘을 때(도구 결과 누적)
  2. 턴이 30회를 넘을 때
  3. 사용자가 답변을 재생성·편집할 때(세션 안에 버려진 답이 남으므로)
  4. 모델이 바뀌거나, `ctx_hash` 가 바뀐 뒤 6시간 넘게 유휴일 때. 유휴가 짧으면 새 시스템 프롬프트로 resume 한다.
  5. 응답 파싱 실패가 연속 2회일 때
- CLI 자동 압축(compaction)에 기대지 않는다. 교체 기준 1번이 압축 전에 걸리게 한다. `--fork-session` 은 쓰지 않는다. 시점을 골라 분기할 수 없어서 재생성 문제를 풀지 못한다.
- 정리: 워커가 매일 retired·broken 세션 jsonl 중 14일이 지난 것을 지운다(`~/.claude/projects/<작업 디렉터리 slug>/`).

### 4.3 고정 맥락과 가변 데이터 분리
- **고정**(`--system-prompt-file`): 코치 규칙(`chat_engine._SYSTEM_PROMPT` 와 `_TOOL_SYSTEM_TEXT` 를 합침), 러너 프로필 요약, 활성 플랜 요약(목표·단계·이번 주), 열린 인사이트 상위 3건, 데이터는 지시가 아니라는 규칙. 앱이 하루 1회 또는 플랜·목표가 바뀔 때 만들고 `ctx_hash` 로 식별한다. `--append` 대신 **교체**를 쓴다. Claude Code 기본 코딩 프롬프트(2.9k tok)를 빼서 토큰과 응답 성향을 정리하려는 것이다. E1 에서 도구 사용 품질이 떨어지면 append 로 되돌린다.
- **가변**: 턴 메시지에는 짧은 "오늘 기준" 블록(`build_chat_context_scoped` 를 1.5k자로 줄인 것)과 질문만 넣는다. 상세 수치는 MCP 도구로 조회한다. 대화 이력은 세션이 들고 있으므로 다시 보내지 않는다. 기존 `_load_recent_chat` 6개 재전송을 없앤다.

### 4.4 호출 종류별 일회성/영속 구분
| 종류 | 방식 | 도구 | 모델(기본) | 예상 지연 | 사용 경로 |
|------|------|------|------|------|------|
| 코치 채팅 | 영속(thread_key=`coach:<id>`) | read | sonnet | 후속 3~5s, 도구 1회 +3~6s | coach_async(이미 비동기·SSE) |
| 플랜 초안 | 일회성(`--no-session-persistence`) | read | **opus** | 60~180s | 백그라운드 + 미리보기 |
| 훈련 이행 분석 | 일회성 | none | sonnet | 5~15s | bg_sync 이후, 주 1회 |
| 심화 분석(사용자 요청) | 일회성 | read | **opus** | 60~180s | 사용자가 버튼으로 요청(§11.6) |
| 인사이트 다듬기 | 일회성(묶음 1회) | none | haiku | 3~5s | bg_sync commit 이후 스레드 |
| Today 내러티브 | 일회성 | none | haiku | 3~8s | narrative_warm |
| 설정 핑 | 일회성 | none | haiku | ~3s | 설정 화면 |
일회성 job 은 `--no-session-persistence` 로 세션 파일을 남기지 않는다. 일회성 job 끼리 상주 프로세스를 재사용하지 않는다. 서로 무관한 job 의 맥락이 섞이기 때문이다.

### 4.5 공통 argv (워커가 생성, 테스트로 고정)
`claude -p --model <m> --system-prompt-file <ctx> --tools "" --strict-mcp-config --mcp-config <gen.json> --allowedTools <mcp__runpulse__X,...> --setting-sources "" --disable-slash-commands --output-format stream-json --verbose [--input-format stream-json --include-partial-messages] [--session-id|--resume <sid>|--no-session-persistence]`
- `gen.json` 의 runpulse 서버 설정은 `command=/usr/bin/python3`, `args=["-m","src.mcp_server"]`, `env={PYTHONPATH, RUNPULSE_USER_ID, PATH, HOME}` 이다. `--mcp-config` 의 cwd 는 무시되므로 PYTHONPATH 가 필요하다. `tools='none'` job 에는 `--mcp-config` 를 아예 넘기지 않는다.
- `--setting-sources ""` 를 쓰는 이유: 사용자 settings 에 켜져 있는 telegram 플러그인·hooks 를 빼려는 것이다. `--bare` 는 OAuth 를 지원하지 않아 못 쓴다. OAuth 가 이 옵션과 함께 동작하는지는 E1 에서 확인한다(위험 2).

## 5. 호출 종류별 설계
### 5.1 인사이트 다듬기
- `polish_open_events` 를 bg_sync commit **뒤** 백그라운드 스레드로 옮기고, 자기 연결을 쓴다(§1 교착 해소). 열린 사건을 묶어 job 1개로 보낸다. 입력은 `[{id,text}]`, 출력 스키마 `polish_v1` 은 `[{id,text}]` 다. 항목마다 기존 `insight_polish.validate`(새 숫자 금지·120자·마크다운 금지)를 거치고, 통과한 것만 `text_ai/text_src` 에 저장한다.

### 5.2 Today 내러티브
- `narrative_warm.warm_month_narrative` 가 claude_queue 를 포함한 체인을 쓴다(백그라운드라 기다려도 된다). 프롬프트는 기존 `_narrative.build_narrative_prompt` 를 그대로 쓴다. 검증기를 새로 둔다: 입력 evidence 에 없는 숫자 금지, 400자 이하. 실패하면 기존 체인으로, 그것도 실패하면 `rule_narrative` 를 쓴다. GET 경로는 §3.2 대로 기다리지 않는다.

### 5.3 훈련 이행 분석(신규, LLM 미사용 → 문장화)
- 입력(서버 계산): `week_compliance.compute`(지난 ISO 주), `outcome_v2.compare` 세션 결과, `plan_advisory.compute` 코드, 신호(`redact_illness_for_ai` 적용).
- 출력 스키마 `adherence_v1` 은 `{"summary": "≤160자", "points": [{"text": "≤80자", "evidence_key": "<입력 키>"}] (≤3), "next_focus": "≤80자"}` 다. 검증: 숫자가 입력의 부분집합이어야 하고, `evidence_key` 가 입력에 있어야 한다.
- `ai_outputs(kind='adherence', scope_key='2026-W46', src_hash=입력 해시)` 에 저장한다. 입력 해시가 같으면 다시 부르지 않는다. 노출은 Plan 주간 카드의 "지난주 리뷰"이고, 근거 칩은 Coach 근거 칩 컴포넌트를 재사용한다. 검증에 실패하면 카드를 숨기고 기존 수치 표시만 남긴다.

### 5.4 플랜 초안(LLM 은 경계 안에서 제안만)
- 현재 연결점: `planner.generate_weekly_plan`(규칙 행 dict) → `plan_finalize.finalize_week/week_violations` → 저장 `planner_store.write_planner_rows`(goal_id 강제) / 구간 교체 `plan_replace.replace_range`(이력 행 보호). 미리보기와 적용은 `plan_replan_service._run(write=False)` 의 SAVEPOINT 패턴을 쓴다. 구조 게이트는 `plan_gates` G1~G9·F1~F6 과 `plan_gates_long` 이고, 입력 변환은 지금 `plan_backtest._plan_from_rows` 로 하는데 이를 공개 함수 `rows_to_weekplans` 로 승격한다.
- LLM 입력: 규칙 계획(기준안), 경계(주간 km 목표 `planner_schedule.week_target`, 운동 요일, 롱런 상한 `long_run_rules`, 페이스 범위). 읽기 도구로 최근 훈련도 조회할 수 있다.
- 출력 스키마 `plan_draft_v1`: `{"weeks":[{"week_start":"YYYY-MM-DD","sessions":[{"date","workout_type"(기존 enum),"distance_km","target_pace_min","target_pace_max","mp_km","note"(≤60자)}]}],"rationale":["≤80자"](≤5)}`
- 서버 검증 순서: 스키마 → 경계 위반이면 거절(잘라 내지 않음) → `week_violations` 0건 → 게이트 전부 통과 → 규칙안과의 차이를 미리보기로 보여 줌 → 사용자가 "적용"하면 기존 apply 경로로 저장한다. 실패하면 규칙 계획을 보여 주고 사유(어느 게이트에서 떨어졌는지)를 표시한다. **쓰기 도구는 LLM 에 주지 않는다.**

### 5.5 코치 채팅 — 앱 내장 도구 vs RunPulse MCP 도구
| 항목 | 앱 내장(`complete(tools=True)`) | RunPulse MCP(stdio, 워커가 사용) |
|------|------|------|
| 선언 | `tool_declarations.TOOL_DECLARATIONS` 15개 | 같은 목록(`mcp_remote.protocol._declarations`), `policy.REMOTE_TOOLS` 15개와 일치 |
| 실행 | `tools.execute_tool` | 같은 함수 |
| DB 연결 | 앱의 요청 연결(쓰기 가능) | `safe_conn.connect_readonly`(ro+query_only+authorizer+시간 제한) |
| 사용 안내 | `_TOOL_SYSTEM_TEXT`(system) | `tool_guide.USAGE_GUIDE`(initialize instructions) + 고정 맥락 |
| 라운드 상한 | `_openai_compat_loop` 3회 | CLI 에 상한 플래그가 없으면 워커가 tool_use 를 세어 6회를 넘을 때 중단(E4 에서 확인) |
| 진행 표시 | `on_tool` → stage | stream-json tool_use → `progress_json` → stage |
| 사용자 바인딩 | 앱 세션 uid | `RUNPULSE_USER_ID`(DB 경로에서 정함, `resolve_db_path` 가 경로 조작 거부) |
| 민감 정보 | 체크인 메모·질병은 도구 출력에 없음(tool_exec_* grep 결과 해당 필드 없음) | 같음 |
- 흐름: `coach_service.generate_reply` → `run_chain` 에서 맨 앞의 claude_queue 가 job 을 넣는다(thread_key). 워커는 상주 세션으로 턴을 보내고 tool_use·partial 을 기록한다. 앱 대기 스레드가 이를 stage/delta SSE 로 내보낸다(지금 하고 있는 "완성 답변 잘라 보내기"를 실제 스트리밍으로 대체). 답변이 끝나면 기존 근거 칩 검증과 `[추천: …]` 파싱을 그대로 쓴다.
- 취소: `cancel_requested` 를 받으면 워커가 stream-json interrupt 제어 메시지를 보낸다. 지원되지 않으면 프로세스를 종료하고 세션을 `broken` 으로 표시한다(E4 에서 확인).
- 동의: `coach_consent.provider` 에 `claude_queue` 를 고를 수 있게 한다. `fallback_enabled` 이면 Groq 로 이어진다.

## 6. 보안
1. **도구**: `--tools ""`(Bash·Read·Write·WebFetch 등 내장 도구 전부 차단), `--allowedTools` 는 `REMOTE_TOOLS` 에서 만든 명시 목록, `--strict-mcp-config`, `--setting-sources ""`, `--disable-slash-commands`, 빈 작업 디렉터리. 네트워크 도구가 없으므로 인젝션이 성공해도 외부로 빼돌릴 수 없다.
2. **uid 고정**: 앱 설정 `ai.claude_queue.uids` 와 워커 `CQ_UIDS` 를 둘 다 통과해야 한다. 워커는 job 필드의 uid 를 믿지 않는다.
3. **인젝션**: 시스템 프롬프트(고정 규칙)와 사용자 데이터(`<data>` 블록)를 분리한다. 모든 출력은 종류별 스키마·숫자 검증을 거친다. 플랜은 게이트를 통과하고 사용자가 확인해야 적용된다.
4. **시크릿**: job 에 config·키를 넣지 않는다. MCP 서브프로세스 env 는 최소 4개뿐이다. 앱은 `~/.claude` 에 접근하지 않는다. 워커 로그에는 프롬프트·답변 본문을 남기지 않는다.
5. **민감 신호**: 프롬프트는 기존 빌더만 쓴다(`chat_context`, `coach_evidence` 가 `redact_illness_for_ai` 적용). 새 빌더(§5.3·5.4)도 신호를 넘기기 전에 이를 호출해야 하고, 테스트로 강제한다. `exclude_notes` 동의도 그대로 따른다.
6. **쓰기 요청**: 새 API(`POST /api/v1/ai/ping`, 플랜 초안 요청·적용)는 Origin 관문을 거친다.

## 7. 관측·운영
- `GET /api/v1/ai/queue/status`(본인): 하트비트 경과, `paused_until`, 대기 건수, 24h queue_ms·run_ms p50/p95, 실패 사유별 건수, 오늘 토큰, 상주 세션 수. 설정 화면의 엔진 상태(`coach_engine_health`)에 claude_queue 줄을 추가한다.
- 한도 소모: `ai_jobs` 토큰·캐시 컬럼과 `paused_until` 이력(`ai_worker_state.last_error`). 한도에 걸린 횟수를 주간 집계로 본다.
- 장애: 워커가 죽으면 하트비트가 20s 를 넘기는 순간부터 즉시 폴백한다(대기 없음). CLI 오류가 연속 5회 나면 워커가 스스로 10분 일시정지한다.
- **롤백**: `ai.claude_queue.enabled=false` 로 끈다(호출마다 읽으므로 즉시 반영). `systemctl --user stop runpulse-ai-worker` 를 해도 하트비트 판정으로 자동 폴백한다. v48 테이블은 가산이라 그대로 둔다.
- 개인정보: 대화는 구독 경로로 Anthropic 에 간다(감수하기로 결정함). 호스트 세션 jsonl 은 14일, `ai_jobs` 본문은 7일 뒤 지운다. 로그에는 job id·kind·지연·토큰만 남긴다.

## 8. 구현 단계
| 단계 | 범위 | 테스트 | 브라우저 검증 | 롤백 |
|------|------|------|------|------|
| E1 | v48 마이그레이션, `queue_store`, `cli_runner`(일회성), `main`(사전 점검·하트비트·회수·한도 일시정지), systemd unit, kind=`ping`, 벤치 | claim 경합·정체 회수·만료·일시정지(tmp DB), argv 고정, stream-json 파서(fixture), 사전 점검(권한 거부) | 설정 화면 핑이 claude_queue 로 응답 | 유닛 중지, 플래그 off |
| E2 | `provider_claude_queue` + `provider_available` 일반화, 인사이트 다듬기(commit 뒤 이동·묶음), 내러티브 워밍 | 하트비트 만료·cq_timeout·quota_sub 폴백, 요청 경로 비대기, 묶음 검증, 교착 회귀(sync 중 enqueue) | Today 배너·내러티브가 AI 문장으로 표시되고, 워커를 끄면 규칙 문장 | 플래그 off |
| E3 | 훈련 이행 분석 + `ai_outputs` + Plan 주간 카드 | 입력 해시 재사용, 숫자·evidence_key 검증, redact 강제 | Plan 지난주 리뷰 카드, 실패 시 숨김 | 플래그 off(카드 숨김) |
| E4 | 코치 채팅: `session_pool`(상주·유휴 종료·resume 복구·교체 기준), MCP 연결, 진행·partial SSE, 취소, 동의 옵션 | 교체 기준 5종, broken 복구(시드 이력), 도구 상한, Bash 차단 계약 테스트(실제 CLI, opt-in 마커), 취소 | 대화 3턴(맥락 유지·도구 진행 표시·스트리밍), 워커 재시작 뒤 이어짐 | 동의 provider 를 groq 로 |
| E5 | 플랜 초안: `rows_to_weekplans` 공개, `plan_draft_v1` 검증, 미리보기·적용 | 스키마·경계 거절·게이트 실패 폴백, 쓰기는 기존 apply 경로만 | 초안 미리보기 → 적용 → 되돌리기 | 플래그 off(규칙 계획만) |
- 의존 관계: E1 → E2 → {E3, E4}(병렬 가능) → E5. E5 는 E4 의 도구 격리·MCP 연결을 재사용한다.

## 9. 가장 위험한 가정 3개
1. **컨테이너(root)와 호스트(ubuntu)가 bind mount 위의 같은 WAL DB 를 안전하게 함께 쓴다.** 검증(E1): 컨테이너를 재시작해 `-wal` 을 새로 만들게 한 뒤 워커 쓰기와 MCP ro 읽기를 시험한다. 같은 시간에 sync 와 job 쓰기를 섞어 `busy_timeout` 을 확인한다. 실패하면 §8 결정 1 을 적용한다.
2. **CLI 격리 플래그가 OAuth 를 유지하면서 플러그인·hooks·내장 도구를 막고, 상주 stream-json 이 도구 포함 다중 턴·interrupt 를 안정적으로 처리한다.** CLI 자동 업데이트로 동작이 바뀔 수도 있다. 검증(E1·E4): 실제 CLI 계약 테스트("ls 실행해" 프롬프트에서 tool_use 가 0건이어야 함, init 이벤트의 tools·mcp_servers 목록 확인), 기동 시 버전 허용 목록 검사.
3. **구독 한도와 지연이 5종 전부를 감당한다**(상주 후속 턴 p50 ≤ 5s, 한도 도달은 드묾). 검증: E1 벤치(sonnet n=5), E2~E4 2주간 `ai_jobs` 토큰·`quota_sub` 집계. 넘치면 백그라운드 종류를 haiku 로 내리거나 빈도를 낮춘다.

## 10. 결정 기록 (2026-11-18)
1. 컨테이너 사용자 `1001:1001` 채택(§3.4). 기존 root 소유 파일 1회 chown.
2. 모델 기본값(config 로 변경 가능): 코치·이행 분석 sonnet / 인사이트 다듬기·내러티브 haiku / **플랜 초안 opus / 사용자 요청 심화 분석 opus**. opus 는 지연·한도 소모가 크므로 §11.6 의 사용자 트리거 때만 쓴다.
3. 필요한 CLI/MCP 도구는 식별해 추가 개발한다(§11).

## 11. 필요 CLI/MCP 도구 (갭 분석)
### 11.1 현황
- MCP 도구 15종(`TOOL_DECLARATIONS` = `tools._DISPATCH` = `REMOTE_TOOLS`)은 `metric_store`·`v_canonical_activities`·`activity_laps`·`daily_wellness`·`weather_cache` 만 읽는다. 아래 데이터는 AI 가 볼 수 없다.
- 실측(운영 DB): `source_payloads` 에 garmin 수면 상세(1145건·35KB), 스트레스·HRV·BB, 훈련 상태·준비도·성숙도 등 일별 payload 와 활동 스트림(1.1MB/건), strava 스트림·상세가 있다. 정규화 컬럼으로 옮기지 않은 필드가 대부분이다.
- 데이터 CLI 는 `scripts/` 의 백필·진단류뿐이며 AI 용 조회 CLI 는 없다.

### 11.2 추가할 읽기 전용 도구(우선순위순)
| 도구 | 읽는 곳 | 용도 | 제한 |
|------|------|------|------|
| `list_raw_payloads` | `source_payloads` 카탈로그 | 어떤 source/entity_type 이 어느 기간에 있는지 | 행 수·기간·평균 크기만, 본문 없음 |
| `get_raw_payload` | `source_payloads` | 정규화에 없는 필드 확인(수면 단계, 스트레스 곡선, 훈련 상태 등) | source·entity_type·date(또는 activity_id) 필수, `fields`(점 경로) 투영, 본문 상한 6k자·배열 자르기, 스트림류 본문은 거절하고 `get_activity_stream` 으로 유도, 좌표·이메일·계정 식별자 제거 |
| `get_activity_stream` | `activity_streams`/`activity_stream_meta` | 심박·페이스·고도·케이던스 시계열 | 채널 지정, 구간(from_sec,to_sec), 리샘플 간격(기본 30s)·최대 300점, 구간 통계(평균·최대·기울기) 동봉 |
| `get_wellness_series` | `wellness_series`(v46) | HRV·안정 심박·수면·BB 일별 계열과 7/28일 기준선 | 기간 ≤ 120일, 지표 선택 |
| `get_plan_adherence` | `week_compliance`·`session_outcomes`·`plan_adjustments` | 주간 이행률·세션별 계획 대비 결과(훈련 이행 분석·플랜 초안의 입력) | 기간 ≤ 8주 |
| `get_insights` | `insight_events` | 열린 사건·근거 신호 | state 필터, 건수 ≤ 10 |
| `get_checkins` | `user_inputs`·`activity_feedback` | 컨디션 체크인·세션 후 피드백 | 기간 ≤ 28일, `redact_illness_for_ai` 적용 |
| `get_predictions` | `prediction_snapshots`·`activity_best_efforts`·`race_results` | 예측 추이·최고 기록(심화 분석) | 기간·거리 필터 |
| `get_plan_constraints` | `user_training_prefs`·`plan_gates` 한계값 | 플랜 초안이 게이트를 넘지 않도록 사전에 알림 | 읽기 전용 상수 + 사용자 설정 |
- 위 9종이 필요한 이유별 사용처: 코치(전부 read), 플랜 초안(`get_plan_adherence`·`get_wellness_series`·`get_plan_constraints`·`get_predictions`·`get_training_plan`), 심화 분석(전부).
- 정리: 새 계산은 만들지 않고, 이미 계산·저장된 값을 노출한다. 서비스 함수가 있으면 그대로 호출한다(`week_compliance.compute` 등).

### 11.3 정책(기존 규칙 유지)
- 새 도구도 `TOOL_DECLARATIONS`·`_DISPATCH`·`REMOTE_TOOLS` 에 같이 넣는다(`unclassified_tools` 테스트가 강제). 원격 HTTP MCP 에 `get_raw_payload`·`get_activity_stream` 을 노출할지는 별도 분류한다: 기본은 `REMOTE_DENIED`(원격 토큰으로 원자료 반출 금지), 워커용 로컬 MCP 만 허용하도록 허용 집합을 분리한다(`LOCAL_ONLY_TOOLS`).
- 연결은 `safe_conn.connect_readonly`. 응답은 `tool_format` 의 압축 규칙(fields/rows)과 크기 상한을 따른다. 노트·질병 필드는 `exclude_notes`/`redact_illness_for_ai` 를 지난다(질병 동의 없으면 제거).
- 도구 설명은 `tool_guide.USAGE_GUIDE` 에 "정규화 도구로 답이 안 될 때만 raw" 규칙을 추가해 남용을 막는다.

### 11.4 CLI
- `python -m src.ai.tool_cli <tool> '<json args>' [--user UID] [--db PATH]`: 같은 `_DISPATCH` 를 셸에서 호출한다(읽기 전용 연결). 용도: 도구 출력 크기·내용 점검, 벤치, 회귀 재현. AI 호출 경로와 코드가 같아 별도 구현이 없다.

### 11.5 구현 순서
- E1 에 `tool_cli` + `list_raw_payloads`/`get_raw_payload` 를 포함한다(워커·벤치가 바로 쓴다). 나머지 도구는 소비하는 단계에 묶는다: `get_wellness_series`·`get_activity_stream`·`get_insights`·`get_checkins`·`get_predictions` → E4(코치), `get_plan_adherence` → E3, `get_plan_constraints` → E5.

### 11.6 심화 분석(사용자 요청, opus)
- 트리거: 활동 상세·Coach 에서 "심화 분석" 버튼 → `kind=deep_analysis`(v48 `ai_jobs.kind` 에 추가). 입력은 대상(활동 id 또는 기간)과 선택 질문.
- opus·read 도구·일회성, 마감 240s, 결과는 `ai_outputs`(kind=`deep_analysis`, scope_key=대상)에 저장해 같은 입력이면 재사용한다. 진행은 stage SSE, 취소는 `cancel_requested`.
- 출력은 `deep_v1` 스키마(요약·근거 키·권장 행동)이며 숫자는 도구 응답에 있는 값만 허용한다(§5.2 내러티브와 같은 검증). 실패하면 사용자에게 사유를 보여 주고 폴백은 없다(사용자가 요청한 작업이므로 규칙 문장으로 대체하지 않는다).
