# DESIGN — [SYNC-SOURCE-TOGGLE] 소스별 동기화 on/off

- 작성: 2026-10-08, system-architect (설계 초안, 결정은 사용자)
- 상위 결정: `99-summary.md` D5 "동기화 원장 = `sync_jobs` 확장(SYNC-ERROR-SURFACE·SYNC-SOURCE-TOGGLE 흡수)"
- 재사용(재설계 안 함): `40-v2-unimplemented/design.md` §3.2 상태 기계(`disabled` 행·[다시 포함]·[동기화에서 제외]), §7.2 "끈 소스 정리", §7.3 `PATCH /data/sources/:p {sync_enabled}`, S2·S3
- 범위: 이미 구현된 부분을 확인하고 **남은 구멍만** 정의한다.

---

## 1. 배경과 문제

### 1.1 BACKLOG 문구는 일부 낡았다

BACKLOG(2026-09-27 작성)는 "`_connected_sources`가 자격증명만 본다"고 적었다. 하지만 이후 커밋에서 대부분 구현됐다.

| 항목 | 현재 상태 | 근거 |
|---|---|---|
| 설정 키 | `config["sync_sources"]: list[str]`. 키가 없으면 4개 소스 전부(하위 호환) | `src/utils/config.py` `enabled_sources`·`set_sync_source` (527dadd·29f82ef, 2026-09-27) |
| 자동 동기화 필터 | `_connected_sources`가 `enabled_sources`와 교집합을 낸다. `start_basic_sync`도 다시 거른다 | `src/web/auto_sync.py:20-32`, `src/web/bg_sync.py:536-541` |
| v2 수동 동기화 | `plan_incremental`·`trigger_range`가 꺼진 소스를 `SkipReason(code="disabled")`로 건너뛴다 | `src/services/sync_trigger_service.py:94-107`, `sync_range_service.py:67-81` |
| CLI | `--source all`이면 `enabled_sources`를 따르고, 단일 소스를 지정하면 무시한다(의도) | `src/sync.py:123` |
| API | `PATCH /api/v1/data/sources/<p> {sync_enabled: bool}`. 끄면 활성 작업을 중지한다 | `src/api/routes_data.py:160-169`, `data_settings_service.set_source_enabled` (9022317, 2026-10-07) |
| SyncState | `sources[].enabled`. 꺼진 소스는 `state="disabled"`이고 `overall`·`caveats`·`open_errors`에서 빠진다 | `src/services/sync_state_service.py:91-107, 145` |
| 프론트 | `/data/sources/[provider]`에 토글·[되돌리기]가 있고, `syncState.ts`에 `disabled → ○ 동기화 꺼짐`이 있다 | `frontend/src/routes/data/sources/[provider]/+page.svelte:73-79`, `frontend/src/lib/syncState.ts:92` |
| v1 | `/sync`의 "동기화 대상" 카드(`sync_sources_post`) | `src/web/views_sync.py:142-170` |
| 운영 데이터 | 루트 `config.json`과 `data/users/pansongit@gmail.com/config.json`은 `strava` 키를 되돌렸고 `sync_sources=["garmin","intervals"]`이다. 남은 `strava_disabled` 키는 0건 | 2026-10-08 조사(키만 확인, 값은 보지 않음) |

### 1.2 남은 구멍(실제 결함)

| ID | 결함 | 영향 |
|---|---|---|
| **G1** | **자동 동기화 스레드가 시작 시점의 config 사본을 계속 쓴다.** `_loop(config, …)` → `_trigger(config, …)` → `_connected_sources(config)`. `PATCH /data/sources/:p`는 요청마다 새로 읽은 dict에만 저장하고 `auto_sync.restart`를 부르지 않는다 | 화면에서 소스를 꺼도 **컨테이너를 다시 시작할 때까지** 자동 동기화가 그 소스를 계속 부른다. 이 BACKLOG의 원래 증상이 그대로 남아 있다. 반대로 켜도 반영되지 않는다. 자격증명 갱신(Strava 토큰 갱신, Intervals 키 교체)도 같은 이유로 반영되지 않는다 |
| **G2** | v1 `POST /trigger-sync-stream`(SSE, `app.py:684~`)은 `source=all`일 때 `checkers.keys()` 전부를 돌고 `enabled_sources`를 보지 않는다 | v1 "전체 동기화"가 꺼진 Strava를 불러 403을 원장에 남긴다. 다만 SyncState는 꺼진 소스의 오류를 숨기므로 Pill에는 드러나지 않는다 |
| **G3** | 단일 소스를 명시하는 경로(`/bg-sync/start`·`/bg-sync/resume`, `app.py:991-1042`)는 꺼짐을 보지 않는다. `resume_job`은 끌 때 `stopped`가 된 작업을 다시 살린다 | 꺼진 소스의 중지 작업을 v1 [재개]로 되살릴 수 있다 |
| **G4** | 끌 때 작업 정리가 `stop_job` → `status="stopped"`이다. 설계 40 §3.2·§7.2는 `cancelled`로 정했다 | `stopped`는 재개할 수 있는 상태라 G3로 이어진다. 원장 의미도 "사용자가 중지"와 "제외로 취소"를 구별하지 못한다 |
| **G5** | `strava_disabled` 같은 레거시 키를 정규화하는 코드가 없다. 지금은 0건이지만 같은 수동 우회가 다시 생기면 문제가 된다. `_SENSITIVE_FIELDS`가 `("strava", …)`만 알아서 `strava_disabled` 아래 값은 복호화하지도 새로 암호화하지도 않는다 | 다른 사용자 디렉터리나 백업 복원 시 자격증명이 평문으로 저장되거나 연결이 끊긴 것처럼 보일 수 있다 |
| **G6** | `/data/sync` 소스 행에 상태별 행동 버튼이 없다. 설계 40 §3.2에는 `disabled` → [다시 포함], `error-access` → [동기화에서 제외]가 있다. 문구 `과거 N건 보존`도 빠졌다 | 403이 난 Strava를 끄려면 소스 상세까지 들어가야 한다. 설계 40에 이미 있는 S3/S4 미구현분이다 |
| G7(관찰, 확인 필요) | `auto_sync.restart`는 `stop()` 다음에 `_stop_event.wait(2)`를 하는데, 이벤트가 이미 set이라 즉시 돌아온다. 이어진 `start()`가 아직 살아 있는 옛 스레드를 보고 "이미 실행 중"이라며 건너뛸 수 있다. 그러면 `PATCH /data/sync/auto` 뒤에 스레드가 0개가 된다 | 자동 동기화가 조용히 멈춘다. G1 수정을 restart 방식으로 하면 이 경쟁 조건을 더 자주 밟는다 |

---

## 2. 제안 설계

### 2.1 저장 위치와 키 스키마 — **현행 유지**: `config.json`의 `sync_sources`

```jsonc
// data/users/<uid>/config.json (default 사용자는 루트 config.json)
{
  "sync_sources": ["garmin", "intervals"],   // 포함 목록(allow-list). 순서는 ALL_SOURCES로 정규화
  "auto_sync": {"enabled": true, "interval_hours": 1, "days": 14},
  "strava": {"refresh_token": "enc:…", …}    // 자격증명은 그대로 둔다(끄기 ≠ 연결 해제)
}
```

규칙:

1. 키가 없거나 list가 아니면 = 4개 전부 포함(현행 하위 호환).
2. 목록에 없는 이름(오타·미래 소스)은 `enabled_sources`가 무시한다(현행).
3. **끄기와 연결 해제는 다르다.** 끄기는 `sync_sources`에서만 뺀다. 자격증명과 과거 데이터(`source_payloads`·`metric_store` provider 행)는 유지한다. 연결 해제는 `POST /data/sources/:p/disconnect {keep_data}`(설계 40 §7.3)가 맡는다.
4. 사용자별 격리: `get_config_path(uid)`가 `data/users/<uid>/config.json`을 쓰므로 사용자마다 따로 저장된다. DB(`running.db`·`sync_jobs.db`)에는 저장하지 않는다(§4 대안 A).

**레거시 키 마이그레이션(G5)** — `src/utils/config.py`에 `_migrate_legacy_source_keys(loaded: dict) -> dict`를 둔다. 순수 함수이고 멱등이다.

```
for src in ALL_SOURCES:
    legacy = f"{src}_disabled"
    if legacy in loaded:
        if not loaded.get(src):            # 정식 키가 비었을 때만 옮김(덮어쓰기 금지)
            loaded[src] = loaded[legacy]
        del loaded[legacy]
        cur = loaded.get("sync_sources")
        base = cur if isinstance(cur, list) else list(ALL_SOURCES)
        loaded["sync_sources"] = [s for s in base if s != src]   # 의도("끈다")를 보존
```

- 호출 위치는 `load_config`에서 JSON을 읽은 **직후**, `_default_config` 병합과 `decrypt_config_credentials` **이전**이다. 정식 키로 옮겨져야 `enc:` 값이 복호화되고, 다음 `save_config`에서 암호화된다.
- 파일에는 즉시 쓰지 않는다. 다음 `save_config` 때 반영된다(읽기 경로에 부작용 금지).
- 정식 키와 레거시 키가 둘 다 비어 있지 않으면 정식 키를 우선하고 레거시 키는 버린다. 이때 `log.warning`을 남기며 값은 로그에 쓰지 않는다.

### 2.2 적용 규칙 — "포함 여부는 **일괄·자동** 경로에서 강제, **명시적 단일 소스**는 경로별"

| 경로 | 꺼진 소스 처리 | 변경 |
|---|---|---|
| 자동 `auto_sync._trigger` | 제외 | **G1**: `_trigger`가 실행할 때마다 `load_config(user_id=user_id)`를 다시 읽는다. `_loop`가 들고 있던 config는 `auto_sync` 설정값(주기·기간) 판단에만 쓴다 |
| v2 `POST /data/sync`·`/data/sync/range`·`/trigger-sync-bg` | `SkipReason("disabled")`로 제외. 단일 소스를 지정해도 제외 | 없음(현행) |
| v1 `POST /trigger-sync-stream` | 제외하고 `source_done{skipped, reason:"disabled"}` SSE를 낸다 | **G2**: `sources_to_sync` 결정 직후 `enabled_sources`로 거른다. `app.py`가 이미 1363줄이므로 3~4줄만 추가하고 늘리지 않는다 |
| v1 `/bg-sync/start`·`/bg-sync/resume` | 409 `{"error":"동기화 대상에서 꺼져 있어요"}` | **G3**: `start_job`·`resume_job` 앞에 가드를 둔다. 공용 함수 `src/utils/config.is_source_enabled(config, src)`를 쓴다 |
| 연결 직후 초기 동기화(`views_settings_garmin`·`/api/garmin/local-sync`) | 꺼져 있으면 시작하지 않고 메시지 "동기화 대상에서 꺼져 있어 가져오지 않았어요" | G3 일부. 재연결이 곧 포함 의사라고 보지 않는다(열린 질문 Q2) |
| CLI `src/sync.py --source X` | **허용**(운영자 진단용). `--source all`만 필터 | 없음. docstring에 명시 |
| 끄는 순간의 활성 작업 | `pending`/`running`/`paused`/`stopped`/`rate_limited` → **`cancelled`**. 실행 중이면 스레드에 stop 신호를 보낸 뒤 상태를 `cancelled`로 확정 | **G4**: `data_settings_service._stop_pending` → 새 `bg_sync.cancel_job(service, user_id, reason="source_disabled")`. `error_code="source_disabled"`, `last_error="동기화 대상에서 제외됨"` |

`cancelled` 상태: `sync_jobs.status`는 TEXT 자유값이라 DDL을 바꾸지 않는다. `classify_error`는 이미 `completed`가 아니면서 오류 문구가 없는 경우를 `unknown`으로 분류할 수 있다. 따라서 `cancelled`를 `running/pending/paused/stopped`와 같은 "오류 아님" 집합에 추가한다. `resume_job`의 허용 상태(`paused, stopped, rate_limited`)에는 `cancelled`를 넣지 않는다. 그러면 G3의 재개 경로가 구조적으로 막힌다.

### 2.3 API 계약

설계 40 §7.3을 유지한다. 과제가 요구한 GET/PUT 대신 기존 PATCH를 쓴다(대안 C).

```
GET /api/v1/data/sync-state                    # 현행. sources[].enabled, state="disabled"
GET /api/v1/data/sources/:p                    # 현행. detail.enabled
GET /api/v1/data/sync/sources                  # (신규, 선택) 일괄 조회
  200 {"data": {"sources": [
        {"provider":"garmin","sync_enabled":true,"connection":"connected"},
        {"provider":"strava","sync_enabled":false,"connection":"connected"}, …]}}

PATCH /api/v1/data/sources/:p {"sync_enabled": bool}   # 현행 + 응답 확장
  200 {"data": {"provider":"strava","sync_enabled":false,
                "cancelled_job_ids":[123],              # 추가(G4)
                "auto_sync_applies":"next_run"}}        # 추가: 자동 동기화 반영 시점 안내
  400 INVALID_PARAM (sync_enabled 누락·비불리언)
  404 NOT_FOUND (알 수 없는 provider)
```

- 멱등: 같은 값을 다시 보내도 200이고 `cancelled_job_ids=[]`이다.
- 미연결 소스도 켜고 끌 수 있다(사전 설정). SyncState는 `connection`이 우선이라 `not_connected`로 보인다.
- `GET /data/sync/sources`는 `/data/sync-state`의 `sources[]`가 같은 정보를 이미 주므로 **만들지 않는 것을 추천**한다. 표면이 하나 늘 뿐이다.
- 일괄 PUT `{sync_sources:[…]}`은 v1 폼에만 필요하고, v1은 `sync_sources_post`가 이미 있으므로 만들지 않는다.

### 2.4 프론트 UI 위치와 문구 (설계 40 §3.2 그대로, 구현 누락분만)

| 위치 | 상태 | 표시 | 행동 |
|---|---|---|---|
| `/data/sources/[provider]` | 전체 | 현행 토글 `켜짐/꺼짐`, 끈 직후 `동기화에서 제외했어요 [되돌리기]` | 현행. 보조 문구를 추가한다: `끄면 자동·전체 동기화에서 빠져요. 과거 기록 {n}건은 그대로 남아요.` |
| `/data/sync` 소스 행 | `disabled` | `○ 동기화 꺼짐 · 과거 {n}건 보존` | **[다시 포함]** 버튼 → `PATCH {sync_enabled:true}`, 토스트 `{Strava}를 동기화에 다시 포함했어요` |
| `/data/sync` 소스 행 | `error-access` | 현행 문구 + `{다른 소스} 데이터로 계속됩니다` | **[동기화에서 제외]** → `PATCH false`, 토스트 `{Strava}를 동기화에서 제외했어요 [되돌리기 5s]` |
| SyncPanel(Pill 시트) | `disabled` | 행을 아래쪽으로 내리고 흐리게 표시 | 행동 없음. 소스 상세로 이동만 |
| `/data/sync` [지금 동기화] | — | 현행 `connected && enabled`가 0개면 비활성 | 비활성일 때 `동기화할 소스가 없어요 · 소스에서 켜기` 링크 |

`{n}`: `data_service.source_detail` 커버리지(`ProviderCoverageItem.total`)를 그대로 쓴다. 새 쿼리는 만들지 않는다.

### 2.5 as-of / Pill / caveats 영향 (현행 확인 + 고정)

| 신호 | 꺼진 소스 처리 | 근거 |
|---|---|---|
| `overall.level`·`label_ko`·`last_success_at` | 제외(`active` 집합만) | `sync_state_service.py:145-155` |
| `open_errors`·`caveats[source_missing]` | 제외 | 같은 파일 `:158-164` |
| `connected_count` | **포함**(연결 수이지 활성 수가 아님). 빈 상태 판정(§3.3 `connected_count`)이 "연결 0"과 "모두 꺼짐"을 구별하지 못한다 | Q3 |
| `latest_data_date` | 포함(과거 데이터 MAX). 끈 소스가 최신 데이터 소스였다면 날짜가 더는 오르지 않고 stale로 이어진다. 이는 사실이므로 의도한 동작으로 둔다 | — |
| `provider_status_service` 끊김 경고 | 제외(현행) | `provider_status_service.py:60-75` |
| 커버리지 차트 | 꺼짐 + 과거 0건이면 숨기고, 과거 데이터가 있으면 흐리게 표시(현행) | `SourceCoverage.svelte:18-19` |
| metric_store / is_primary | **영향 없음**. 끄기는 수집만 멈춘다. 이미 저장된 `provider="strava"` 행은 우선순위 계산에 계속 참여한다 | 단일 저장소 원칙 |

---

## 3. 기존 시스템과의 호환성

- D5와 충돌하지 않는다. 원장에 새 상태값 `cancelled`와 `error_code="source_disabled"`만 추가하고 DDL 변경은 없다(SCHEMA_VERSION 유지).
- 설계 40 §3.2·§7.2·§7.3의 문구와 API를 그대로 쓴다. 다른 점은 응답 필드 2개 추가(`cancelled_job_ids`, `auto_sync_applies`)뿐이다.
- v1 `sync_sources_post`와 같은 키를 공유하므로 두 화면이 일관된다.
- 멀티 사용자: 자동 동기화는 지금도 사용자 한 명(`_sync_uid`, `app.py:222-239`)만 돈다. 이 설계는 그 한계를 바꾸지 않는다. G1 수정(실행마다 다시 읽기)은 나중에 사용자별 루프로 확장해도 그대로 유효하다.
- `credential_store`: 마이그레이션이 복호화 전에 돌기 때문에 `_SENSITIVE_FIELDS`를 확장할 필요가 없다.

## 4. 대안과 트레이드오프

| 대안 | 내용 | 선택하지 않은 이유 |
|---|---|---|
| A. DB 저장(`user_training_prefs`나 새 `source_settings` 테이블) | 사용자별 DB에 on/off를 둔다 | 자격증명·`auto_sync` 설정이 모두 config.json에 있어서, 둘로 나누면 "연결됨 + 꺼짐" 판정이 저장소 두 곳을 읽게 된다. 이미 구현·테스트된 키를 옮기는 비용만 생긴다 |
| B. `config.<source>.enabled` (BACKLOG 예시) | 소스 블록 안에 플래그를 둔다 | 소스 블록이 비면(미연결) 설정이 사라진다. `update_service_config`가 블록을 통째로 갱신할 때 덮어쓸 위험이 있고, `enabled_sources` 한 곳 판정이 깨진다. 이미 `sync_sources`로 구현됐다 |
| C. 과제 문구의 GET/PUT 일괄 엔드포인트 | `PUT /data/sync/sources {sources:[…]}` | 설계 40 §7.3이 소스 단위 PATCH로 확정했고 이미 구현됐다. 일괄 PUT은 동시 토글에서 마지막 쓰기가 이기는(lost update) 문제를 키운다 |
| D. G1을 `PATCH` 뒤 `auto_sync.restart`로 해결 | 토글할 때마다 스레드를 재시작 | G7 경쟁 조건을 자주 밟는다. 재시작 자체가 즉시 실행을 유발하지는 않지만 상태가 불안정해진다. 실행마다 다시 읽는 방식이 더 단순하고 자격증명 갱신도 함께 해결한다 |
| E. 끄면 `stopped` 유지(현행) | 상태값 추가 없음 | 재개 가능 상태라 G3 우회가 남고, "사용자 중지"와 "제외 취소"를 원장에서 구별하지 못한다 |

## 5. 테스트 목록

| 파일 | 테스트 | 수 |
|---|---|---|
| `tests/test_config_sync_sources.py` (신규) | 레거시 `strava_disabled` → `strava`로 이동하고 `sync_sources`에서 빠짐 / 정식 키가 있으면 덮어쓰지 않음 / 멱등(두 번 적용해도 같음) / `sync_sources` 없을 때 기준 = 전부 / `enc:` 값이 이동 후 복호화 경로를 탄다(키 fixture) / `is_source_enabled` | 6 |
| `tests/test_auto_sync_reload.py` (신규) | `_trigger`가 실행마다 `load_config`를 다시 읽는다: 시작 후 파일에서 strava를 끄면 다음 `_trigger`의 sources에 strava가 없다 / 켜면 들어간다 / 로드가 실패하면 시작 config로 폴백하고 로그를 남긴다 | 3 |
| `tests/test_auto_sync_restart.py` (신규, G7) | `restart` 뒤 스레드가 정확히 1개 살아 있다(옛 스레드 join) | 1 |
| `tests/test_data_settings.py` (확장) | 끄면 활성 작업이 `cancelled`·`error_code=source_disabled`가 되고 응답에 `cancelled_job_ids`가 있다 / 같은 값 재전송 시 `[]` / `resume_job`이 `cancelled`를 거부 | 3 |
| `tests/test_sync_state_service.py` (확장) | `cancelled` 최신 작업은 오류가 아니다(`classify_error is None`) / 꺼진 소스의 403은 `open_errors`·`caveats`에 없다(회귀 고정) | 2 |
| `tests/test_v1_sync_guards.py` (신규) | `/trigger-sync-stream source=all`이 꺼진 소스를 `reason:"disabled"`로 skip / `/bg-sync/start`·`/bg-sync/resume` 꺼진 소스 409 / garmin local-sync가 꺼져 있으면 시작하지 않음 | 4 |
| 프론트 `frontend/src/lib/syncState.test.ts` (신규, 대상 `syncState.ts` 217줄) | `disabled` 행 문구에 `과거 N건 보존` / 행동 매핑 `disabled→include`, `error-access→exclude` | 2 |
| 브라우저 스모크 `pw/sync_source_toggle.mjs` | `/data/sync`에서 Strava [다시 포함] → 행이 `idle-*`/`never`로 바뀜 → [동기화에서 제외] → `○ 동기화 꺼짐`, Pill 색 불변 | 1 |

합계: 백엔드 19, 프론트 2, 스모크 1.

## 6. 구현 슬라이스 (각 파일 300줄 이하 유지)

| 슬라이스 | 변경 | 파일(현재 줄 수 → 예상) | 테스트 |
|---|---|---|---|
| **T1 자동 동기화 반영(G1·G7)** — 최우선, 원래 증상 해소 | `_trigger`에서 `load_config(user_id=…)` 다시 읽기(실패 시 인자 config로 폴백). `restart`는 `_thread.join(timeout=5)` 후 `start` | `src/web/auto_sync.py` (122 → ~135) | reload 3 + restart 1 |
| **T2 레거시 키·헬퍼(G5)** | `_migrate_legacy_source_keys`, `is_source_enabled`. 이미 남은 `if result` 뒤 도달 불가 블록(`load_config` return 이후)은 건드리지 않고 별도 정리 항목으로 둔다 | `src/utils/config.py` (188 → ~215) | 6 |
| **T3 끄기 = cancelled(G4)** | `bg_sync.cancel_job` 추가, `_stop_pending` 교체, `classify_error` 비오류 집합에 `cancelled` 추가, 응답 `cancelled_job_ids` | `src/services/data_settings_service.py` (79 → ~95), `src/services/sync_state_service.py` (175, +1), `src/web/bg_sync.py`(581줄, 이미 초과: `cancel_job`은 **`src/web/bg_sync_control.py` 신규**에 두고 `stop_job`을 재사용) | 3 + 2 |
| **T4 v1 경로 가드(G2·G3)** | `/trigger-sync-stream` 필터, `/bg-sync/start`·`/resume` 409, garmin 초기 동기화 가드. `app.py`(1363줄, 이미 초과)는 **추가 3~6줄만** 넣고 가드 로직은 `is_source_enabled` 호출로 끝낸다 | `src/web/app.py`, `src/web/views_settings_garmin.py` | 4 |
| **T5 프론트 행동(G6)** | `/data/sync` 행 [다시 포함]/[동기화에서 제외] 버튼, 토스트·되돌리기, `syncState.ts`에 행동 매핑, 상세 보조 문구 | `frontend/src/routes/data/sync/+page.svelte` (76 → ~120), `frontend/src/lib/syncState.ts` (217 → ~235), `frontend/src/routes/data/sources/[provider]/+page.svelte` (120 → ~125) | 2 + 스모크 1 |
| **T6 문서** | BACKLOG 항목을 "남은 구멍 G1~G6"으로 고쳐 쓰거나 완료 처리, DECISIONS에 "포함 목록 = `config.sync_sources`, 끄기 ≠ 해제, 끄기 = cancelled" 기록, `sync.py` docstring에 CLI 예외 명시 | 문서 | `check_docs.py` |

순서: T1 → T3 → T2 → T4 → T5 → T6. T1만으로 BACKLOG 원래 증상이 해소된다. T1·T2·T3·T4는 서로 독립이라 병렬로 진행할 수 있다.

## 7. 검증 항목

1. 운영 컨테이너에서 `PATCH /data/sources/strava {sync_enabled:true}` → 다음 자동 주기 로그 `[auto_sync] 트리거: sources=[…]`에 strava가 포함되고, `false`로 되돌리면 빠진다. 재시작 없이 확인한다.
2. 끈 직후 `sync_jobs`에서 해당 소스의 활성 행이 `cancelled`이고, `/bg-sync/resume`이 409를 낸다.
3. `/data/sync-state`에서 strava가 `state="disabled"`이고 `overall.level`이 strava의 과거 403과 무관하다.
4. `grep -rn "_disabled\"" data/users/*/config.json` 0건. 마이그레이션 함수 적용 전후 `enabled_sources` 결과가 같다.
5. `PATCH /data/sync/auto` 후 `auto_sync.status()["running"] is True`(G7).
6. 브라우저 스모크: `/data/sync`에서 다시 포함하고 다시 제외할 때 Pill 색이 바뀌지 않고, 토스트 [되돌리기]가 동작한다.

## 8. 열린 질문 (추천안 포함)

| # | 질문 | 선택지 | 추천 |
|---|---|---|---|
| Q1 | BACKLOG 항목 처리 | (a) G1~G6로 고쳐 쓰고 유지 (b) T1만 하고 완료, 나머지는 설계 40 S3/S4로 이관 | **(b)**. 원래 증상은 G1뿐이고, G6은 설계 40 S3·S4 소관이다. G2~G5는 같은 PR에 넣을 만큼 작다 |
| Q2 | 꺼진 소스를 재연결(OAuth·키 저장)하면 자동으로 켤까 | (a) 자동으로 켬 (b) 꺼진 상태 유지 + 안내 `동기화에서 꺼져 있어요 [포함]` | **(b)**. 키 교체만 하려는 경우가 있다. 재연결 화면에 포함 버튼을 하나 둔다 |
| Q3 | 모두 꺼짐 + 연결 ≥1 일 때 빈 상태 분류 | (a) `connected_count` 의미 유지 + `enabled_count` 필드 추가 (b) `connected_count`를 활성 수로 재정의 | **(a)**. 계약 의미를 바꾸지 않고 필드만 추가한다. 빈 상태 문구는 `동기화할 소스가 모두 꺼져 있어요` |
| Q4 | CLI 단일 소스 명시 시 꺼짐 무시 | (a) 무시 유지 (b) `--force` 요구 | **(a)**. 운영자 진단용이고 현행 docstring과 테스트가 이미 그렇게 고정돼 있다 |
| Q5 | 끈 소스 작업의 상태값 | (a) `cancelled` 신설 (b) `stopped` + `error_code=source_disabled` | **(a)**. 설계 40과 이름이 같고, 재개 불가가 구조적으로 보장된다 |
| Q6 | Strava 재활성 조건 | 403 Inactive가 풀리는 시점을 알 수 없음 | 자동 감지는 하지 않는다. 사용자가 [다시 포함]을 누르면 첫 실행 결과가 `error-access`면 행에 [동기화에서 제외]가 다시 뜬다. 상태 기계로 충분하다 |
