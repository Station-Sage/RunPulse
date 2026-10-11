# v1 일몰 준비 — 공용 파일 view 밖 이관·v1 호출부 정리

- 작성 2026-10-11. 근거 결정: decisions-table.md V1-1(정정)~V1-13, V1S-1~7. 코드 사실은 모두 2026-10-11 grep 기준(코드 미수정).
- 변경 이력: 2026-10-11 7차 동기화 — V1S-1~7·V1-12·V1-13 반영(새 위치 확정, 후보 비교 삭제, 이관 순서·변경 파일 표·단계·검증을 확정 위치 기준으로 재작성, importer 실측 24파일로 정정).
- 일몰 정의(V1-1 정정·V1-2): v1 일몰 = **UI·라우트 일몰**. 공유 파일·함수는 유지, 재설계가 필요한 v1 파일은 재설계.
- v1 손상 허용(V1-13): v1 보호·호환·완충 코드를 설계에 넣지 않는다. v1 화면이 깨지는 지점은 "감수(V1-13)"로만 적는다.
- 이 문서 범위: V1-10 4파일 이관(V1S-1·2·3·5·7), V1-6 loader 제거(V1S-6), V1-3·V1-8·V1-9·V1-12 /switch-user, V1-11 MenuDrawer CSV, V1-7 suggestions 제거(V1S-4). V1-4(classify_surface 'v1' 분기)는 보류 유지 — 함수 자체가 아직 코드에 없음(`security-headers.md` 설계에만 존재).

## 1. 근본 원인

**RC-1. 계층 역전: v2 서버 코드가 v1 view 디렉터리(`src/web/`)를 import 한다.** `src/web/` 밖 src 파일 24곳이 `src.web.*` 4파일을 import 한다(api 19, services 3, utils 2 — 2026-10-11 grep, 6차의 "22곳"은 helpers 단독 수). v1 view 를 지우면 v2 가 깨지는 구조라 "UI·라우트만 일몰"이 파일 단위로 불가능하다.

**RC-2. 공용 로직과 v1 화면 로직이 한 파일에 섞여 있다.** `helpers.py`(903줄)는 v2 가 쓰는 3함수(`project_root`·`get_current_user_id`·`db_path`, 182-200행)와 v1 HTML 조립(`_CSS`·`_SYNC_JS`·`html_page`·`bottom_nav`·`fmt_*` 등)을 함께 갖는다. `/switch-user`는 로직이 `app.py:266` 라우트 안에 인라인이다.

### 1.1 import 그래프 (V1-10 4파일)

| 파일(줄) | Flask 의존 | `src/web` 밖 src importer | `src/web` 안 importer | tests |
|---|---|---|---|---|
| `bg_sync.py`(625) | 없음 | `api/routes_data.py:105`(stop_job), `services/data_settings_service.py:18`(cancel_job), `services/sync_range_service.py:66`·`services/sync_trigger_service.py:131`(비공개 `_start_or_existing`) — 4 | `app.py`(654·696·787·815·823·831·845), `auto_sync.py:36`, `views_settings_garmin.py:55` — 3 | 10: test_api_data_sync, test_auto_sync_reload, test_bg_sync_batch_error, test_bg_sync_concurrency, test_data_settings, test_provider_status_service, test_sync_range, test_sync_trigger_service, test_trigger_sync_bg_v1, test_v1_sync_guards |
| `auto_sync.py`(129) | 없음 | `services/data_settings_service.py:67`(restart) — 1 | `app.py:184`(start), `views_sync.py:181·246`(status·restart) — 2 | 3: test_auto_sync_reload, test_data_settings, test_sync_range(`_connected_sources`) |
| `helpers.py`(903) | `get_current_user_id`가 flask.session 지연 import | `api/__init__.py:63` + `api/routes_*.py` 18개(db_path·get_current_user_id), `services/sync_trigger_service.py:88`, `utils/config.py:101`, `utils/user_context.py:35` — 22 | 3함수 사용 26개(`app.py` 포함), HTML 헬퍼만 쓰는 v1 view 다수 | 4: test_api_today(모듈 속성 `helpers.db_path` 교체), test_flask_routes(동일), test_mcp_http_routes·test_provider_status_service(문자열 `"src.web.helpers.get_current_user_id"` monkeypatch) |
| `views_mcp_remote.py`(128) | Blueprint `/mcp` | `api/routes_mcp_tokens.py:21`(`enabled`) — 1 | `app.py:48·1152`(등록) — 1 | 2: test_mcp_http_routes, test_mcp_token_routes(`from src.web import views_mcp_remote as v`) |

- 순환: `helpers.py:7`이 `utils.config.load_config`를 import, `utils/config.py:101`이 다시 `helpers.get_current_user_id`를 지연 import(utils→web 역방향). V1S-2 이동으로 이 역참조가 사라진다(결정 근거).
- `bg_sync`→`auto_sync` 방향 의존(auto_sync 가 start_basic_sync 호출). 두 파일 모두 Flask 무의존.
- 경로 참조(문서·스크립트): `files_index.md`(1048·1052·1219 + 테스트 항목, `gen_files_index.py` 재생성), `scripts/check_docs.py`·`gen_files_index.py`의 `SCAN_DIRS`(2026-10-11: `src/sync`·`src/utils`·`src/web` 포함, `src/api`·`src/mcp_remote` 미포함), `src/web/__init__.py` docstring("기존 69개 뷰 파일" — 현재 84개), `src/mcp_remote/__init__.py` docstring(모듈 목록), 진행 중 설계서 `high-severity-remaining.md:42·68`(bg_sync), `accessibility-common.md:189`(helpers.py:11), Dockerfile:21 주석(auto_sync 이름만). CLAUDE.md·`.claude/rules`·skills·`check_docs.py` 경로 하드코딩은 4파일 참조 없음. 그 밖에 ux-review-2026-09·specs 의 과거 설계서 다수(이력 문서, 수정 안 함).

### 1.2 v1 loader `load_adjustment` (V1-6)
- 정의 `views_training_loaders.py:38-47`: `adjust_todays_plan(conn, config)` 호출 + 예외 시 None. `config` 인자는 adjuster 에서 "현재 미사용"(`adjuster.py:34`).
- 호출부 1곳: `views_training.py:83`(v1 `/training`) → 결과는 `render_adjustment_card`·컨디션 카드로만 감. 테스트 직접 참조 0건. `views_training.py`의 `config`는 :112·:139 에서도 쓰이므로 유지.
- v2 대응: `plan_service.get_todays_adjustment`(`:143`) → `GET /api/v1/coach/plan/adjustment`(`routes_plan.py:42`). data-freshness §2.7 가드 `tests/test_adjuster_callers.py`(허용: adjuster·plan_service·plan.py)는 loader 제거가 선행(0단계).

### 1.3 /switch-user (V1-3·V1-8·V1-9·V1-12, SRV-6)
- `app.py:266-293` 인라인. POST: `session["user_id"]=uid` + `init_db(uid)` → `/` 리다이렉트. uid 형식 검증 없음. GET: `data/users` 하위 목록을 미이스케이프 `<option>`으로 조립, `helpers.html_page` 사용.
- `auth_cf._identify_user`는 세션에 `user_id`가 있으면 CF 헤더를 다시 보지 않음(`auth_cf.py:72`) → 운영에서도 전환값이 유지됨(SRV-6 차단 사유).
- 진입점: v2 `MenuDrawer.svelte:115`. 테스트 참조 0건. 이관 설계는 `server-input-origin-validation.md` §2.5.

### 1.4 MenuDrawer.svelte 의 v1 의존(133줄)
- quickLinks(35-41): `/dashboard` `/activities` `/wellness` `/training` `/race` `/ai-coach` `/shoes`. dataLinks(45-47): `/settings` `/guide` `/activities/export.csv`(V1-11). 하단: `/switch-user`(115), `backToV1()`(25-32).
- v2 의 그 밖의 v1 의존: `shell/SyncPanel.svelte:28·29·69·95`(`/settings`), `routes/data/export/+page.svelte:133`(`/training/export.ics`). EXP 화면은 `frontend/src/routes/data/export/`(존재).

### 1.5 suggestions (V1-7 → V1S-4)
- `get_runner_state`·`rule_based_chips` 호출처: src 는 `views_ai_coach.py:149-151`(`_load_chips`, 함수 내 지연 import + `except Exception` → `[]`) 1곳뿐. tests: `test_data_quality.py` `TestSuggestionsRanges`(7개, 모듈 상단 import :21)·`test_integration_realdb.py` `TestSuggestionsRangesReal`(5개).
- 두 함수 전용 심볼: `RunnerState`(데이터클래스)·`_RUN_TYPES`(:39) — 두 함수와 위 테스트 외 사용처 0건.
- 같은 파일 `CHIP_REGISTRY`는 공용: `ai/briefing.py:59`·`ai/chat_engine.py:88`(v2 코치 경로)·`views_ai_coach.py:252·310`.
- v2 칩은 별도 구현: `GET /api/v1/coach/suggestions` → `ai/coach_rule_handlers.suggestion_chips`·`answerable_chips`(suggestions.py 미사용).

### 1.6 v1 라우트 등록 현황(`app.py`)
- Blueprint 28개(1132-1159): v1 view 25 + 비UI 3(`mcp_remote_bp`·`calendar_feed_bp`(`/feeds/cal`, v2 `routes_data_calendar.py:22`가 URL 생성)·`api_bp`).
- app 직접 라우트: `/switch-user`, `/`(entry_path), `/analyze/*`, `/home-legacy`, `/trigger-sync*`, `/bg-sync/*`, `/import*`, `/sync-status`, `/v2/*`(SPA), `/api/garmin/local-sync`(`scripts/garmin_local_sync.py:225`가 호출 — 비UI).

## 2. 설계안

### 2.1 이관 원칙
- 공개 함수 시그니처 불변, import 경로만 변경.
- **shim 없음(V1S-5)**: `src/web/` 에 구 경로 재노출을 두지 않는다. 한 모듈 이동 = 한 커밋이며, 그 커밋에서 src(`src/web` 안 포함)·tests 의 모든 importer·monkeypatch 문자열을 갱신한다.
- v1 화면 보호 코드 없음(V1-13). v1 화면 회귀 검증은 하지 않는다.

### 2.2 확정 위치 (결정 2026-10-11)

| 대상 | 새 위치 | 결정 |
|---|---|---|
| `bg_sync.py`·`auto_sync.py` | `src/sync/` (이 문서는 파일명 유지로 표기: `src/sync/bg_sync.py`·`src/sync/auto_sync.py`) | V1S-1 (B) |
| `helpers.py` 공용 3함수 `project_root`·`get_current_user_id`·`db_path` | `src/utils/user_context.py`에 병합. HTML 헬퍼는 `src/web/helpers.py` 잔류(v1 일몰 시 삭제) | V1S-2 (a)+(A) — `utils/config.py:101` web 역참조 제거 |
| `views_mcp_remote.py` | `src/mcp_remote/http.py` (Blueprint `mcp_remote_bp` 포함, Flask 의존이 패키지에 유입) | V1S-3 (A) |
| SCAN_DIRS | 새 위치가 밖이면 `check_docs.py`·`gen_files_index.py`에 추가 — 2026-10-11 기준 `src/mcp_remote`만 해당(`src/sync`·`src/utils`는 이미 포함). 실제 값은 구현 첫 단계에서 재확인 | V1S-7 (a) |

### 2.3 V1-6 호출부 재설계 (V1S-6 (b))
- `views_training.py:83` `adjustment = load_adjustment(conn, config)` → `adjustment = None`(조정 입력 미전달). import 목록(:34-36)에서 `load_adjustment` 제거, `views_training_loaders.py:38-47` 삭제.
- 감수(V1-13·V1S-6): v1 `/training` 조정 카드·컨디션 카드의 조정 문구는 일몰 전까지 표시되지 않는다.

### 2.4 suggestions 2함수 제거 (V1S-4 (b))
- `src/ai/suggestions.py`에서 `get_runner_state`·`rule_based_chips` 삭제. 두 함수 전용인 `RunnerState`·`_RUN_TYPES`도 사용처 0건이 되므로 함께 삭제(구현 시 grep 재확인). `CHIP_REGISTRY` 유지, 모듈 docstring 갱신.
- tests: `test_data_quality.py`의 `TestSuggestionsRanges`(7)와 :21 import, `test_integration_realdb.py`의 `TestSuggestionsRangesReal`(5) 삭제.
- 감수(V1-13): v1 `/ai-coach` 추천 칩은 사라진다. `_load_chips`는 지연 import 실패를 `except Exception`으로 받아 `[]`를 돌려주므로 앱 기동·다른 라우트에는 영향이 없다.
- `suggestions.py:39` `_RUN_TYPES` 사본이 사라지므로 NRA-8 별도 BACKLOG 대상 사본 목록에서 빠진다(`non-running-activities.md` §7).

### 2.5 그 밖
- /switch-user: `server-input-origin-validation.md` §2.5 순서(①서비스 분리+v2 엔드포인트·production 404 → ②v2 화면·링크 교체 → ③v1 라우트 삭제). 사용자 목록·uid 검증·전환을 Flask 무의존 서비스 함수로, 세션 기록은 라우트에서. `get_current_user_id`는 `src.utils.user_context`에서 import. production 404·MenuDrawer 링크 production 숨김은 같은 변경(V1-9 b). production 판정은 **기존 환경/설정 키 재사용**(V1-12 a) — 어느 키인지는 구현 첫 단계에서 코드로 확인. 경로·화면 위치는 구현 단계 제안(V1-8 c).
- MenuDrawer CSV(V1-11 b): `dataLinks`의 `/activities/export.csv` → `{base}/data/export`(SvelteKit 내부 링크, `data-sveltekit-reload` 불필요 — 구현 시 확인).

## 3. 변경 파일 표

| 파일 | 구분 | 내용 |
|---|---|---|
| `src/web/bg_sync.py`·`auto_sync.py` → `src/sync/bg_sync.py`·`src/sync/auto_sync.py` | 이동 | V1S-1. `auto_sync` 내부 `from src.web.bg_sync` → `src.sync.bg_sync` |
| `src/services/{data_settings,sync_range,sync_trigger}_service.py` | 수정 | bg_sync·auto_sync 지연 import 경로(4줄), `sync_trigger_service.py:88` helpers → `src.utils.user_context`. `_start_or_existing` 비공개명 교차 사용은 현행 유지 |
| `src/api/routes_data.py` | 수정 | `:105` bg_sync 경로 + `:10` helpers 경로 |
| `src/utils/user_context.py` | 수정 | 3함수 정의 수용, `:35` 지연 import 제거(같은 모듈 호출) |
| `src/utils/config.py` | 수정 | `:101` → `src.utils.user_context`(utils→web 역참조 제거) |
| `src/api/__init__.py`, `src/api/routes_*.py` 18개 | 수정 | helpers import 1줄씩 → `src.utils.user_context` |
| `src/web/helpers.py` | 수정 | 3함수 정의 삭제(182-200행), HTML 헬퍼만 잔류. shim 없음 |
| `src/web/` 안 3함수 사용 26개(`app.py` 포함) | 수정 | `from src.web.helpers import db_path, html_page` 형태는 3함수만 `src.utils.user_context`로 분리 import |
| `src/web/app.py` | 수정 | bg_sync 7곳·auto_sync 1곳·`mcp_remote_bp` 등록 import 경로, `/switch-user` 삭제(−30줄) |
| `src/web/views_settings_garmin.py`, `views_sync.py` | 수정 | bg_sync·auto_sync 경로 |
| `src/web/views_mcp_remote.py` → `src/mcp_remote/http.py` | 이동 | V1S-3. docstring 경로 설명 갱신 |
| `src/api/routes_mcp_tokens.py` | 수정 | `:7` helpers 경로, `:21` → `src.mcp_remote.http` |
| `src/web/views_training.py`, `views_training_loaders.py` | 수정 | V1S-6: `:83` → `adjustment = None`, `load_adjustment` 삭제(−10) |
| `src/ai/suggestions.py` | 수정 | V1S-4: 2함수·`RunnerState`·`_RUN_TYPES` 삭제, `CHIP_REGISTRY` 유지 |
| `src/services/` 신규 사용자 전환 모듈, `src/api/` 전환 엔드포인트 | 신규 | `server-input-origin-validation.md` §2.5, production 판정 기존 키(V1-12) |
| `frontend/src/lib/components/MenuDrawer.svelte` | 수정 | CSV 링크 → EXP, `/switch-user` → v2 화면·production 숨김 |
| tests 14개(1.1 표 합집합) | 수정 | 아래 §4 단계별 patch 경로 변경 |
| `tests/test_data_quality.py`, `tests/test_integration_realdb.py` | 수정 | suggestions 테스트 클래스 2개 삭제 |
| `scripts/check_docs.py`·`gen_files_index.py` | 수정 | `SCAN_DIRS`에 `src/mcp_remote` 추가(V1S-7) |
| `v0.3/data/files_index.md`, `src/web/__init__.py`, `src/sync/__init__.py`, `src/mcp_remote/__init__.py`, `src/utils/__init__.py` docstring | 재생성/수정 | 문서 규칙(docstring 이 SSOT) |
| 진행 중 설계서 2개(`high-severity-remaining.md`, `accessibility-common.md`) | 수정 | 경로 문자열 |

## 4. 단계·검증 (1단계 = 1커밋, 각 단계 대상 테스트 → 전체 pytest)

0. **구현 첫 단계 확인(커밋 없음)**: (a) V1-12 production 판정에 쓸 기존 환경/설정 키를 코드로 확인 (b) V1S-7 `SCAN_DIRS` 실측 (c) importer 재grep — `grep -rnE "src\.web(\.| import )(bg_sync|auto_sync|helpers|views_mcp_remote)" src tests`.
1. **bg_sync·auto_sync → `src/sync/`**(함께 — 상호 의존). importer 갱신 순서: `src/web` 밖 4파일(`data_settings_service:18·67`, `sync_range_service:66`, `sync_trigger_service:131`, `routes_data:105`) → `src/web` 안(`auto_sync` 내부, `app.py` 8곳, `views_settings_garmin:55`, `views_sync:181·246`) → tests(`src.web.bg_sync`·`src.web.auto_sync` 문자열과 `import src.web.bg_sync as …`·`from src.web import bg_sync` → `src.sync.*`: test_data_settings·test_sync_trigger_service·test_sync_range·test_provider_status_service·test_v1_sync_guards 외 1.1 표 10개). 검증: 해당 테스트 + `grep -rnE "src\.web\.(bg_sync|auto_sync)|from \.(bg_sync|auto_sync)|from src\.web import (bg_sync|auto_sync)" src tests` 0건.
2. **helpers 3함수 → `src/utils/user_context.py`**. 순서: ① `user_context.py`에 3함수 추가·`:35` 지연 import 제거 → ② `utils/config.py:101` → ③ `services/sync_trigger_service.py:88` → ④ `api/__init__.py:63` + `api/routes_*.py` 18개 → ⑤ `src/web` 안 26개 → ⑥ `helpers.py`에서 정의 삭제 → ⑦ tests: `test_api_today`·`test_flask_routes`의 모듈 속성 교체 대상 `src.web.helpers` → `src.utils.user_context`(교체가 실제 호출 경로에 닿는지 바인딩 위치 재확인), `test_mcp_http_routes`·`test_provider_status_service`의 `"src.web.helpers.get_current_user_id"` → `"src.utils.user_context.get_current_user_id"`. 검증: 4개 테스트 + `grep -rn "src.web.helpers" src/api src/services src/utils` 0건, `grep -rnE "helpers import .*(project_root|get_current_user_id|db_path)" src tests` 0건, `python3 -c "import src.utils.config"` 순환 없음.
3. **views_mcp_remote → `src/mcp_remote/http.py`** + `SCAN_DIRS`에 `src/mcp_remote` 추가(V1S-7). importer: `app.py:48`, `routes_mcp_tokens.py:21`. tests: `test_mcp_http_routes`(`src.web.views_mcp_remote` 문자열 → `src.mcp_remote.http`), `test_mcp_token_routes`(`from src.web import views_mcp_remote as v` → `from src.mcp_remote import http as v`). 검증: 두 테스트, `/mcp` 404/401 동작 불변, `check_docs.py`가 `src/mcp_remote` docstring을 검사.
4. **V1S-6 loader 제거**(data-freshness §2.7 0단계와 같은 단계 — 가드 도입 전). 검증: `grep -rn "load_adjustment" src` 0건. v1 화면 검증 없음(감수, V1-13).
5. **V1S-4 suggestions 제거**. 검증: `grep -rnE "get_runner_state|rule_based_chips|RunnerState" src tests` 0건(`views_ai_coach.py:149` 지연 import 1곳 제외 — 처리 방식은 §5 열린 질문), `test_chat_engine*`·`test_briefing*`(CHIP_REGISTRY 사용) 통과.
6. **/switch-user v2 이관 + SRV-6**(§2.5 ①②③, 2단계 이후 — 새 서비스가 `src.utils.user_context`를 import). 검증: 0단계에서 확인한 기존 키로 production 설정 시 v2 엔드포인트 404·링크 숨김, 개발 설정 전환 동작, `grep -rn "switch-user" src frontend/src`에 v1 경로 0건.
7. **MenuDrawer CSV 링크 교체**. 검증: `npm run check`, 링크 대상 `/data/export` 렌더.
8. 마감: `gen_files_index.py`, `check_docs.py`, 전체 `pytest tests/`, 최종 `grep -rln "src\.web\." src --include=*.py | grep -v "^src/web/"`(목표: `ai/ai_context.py`의 template_helpers 1곳만 남음 — 범위 밖 메모).

## 5. 결정

결정 완료(decisions-table.md V1-1~V1-13, V1S-1~7 표 참조). 남은 열린 질문:
- 새 파일명: V1S-1 은 위치(`src/sync/`)만 정했고 파일명 유지 여부(예 `bg_sync_runner.py`)는 기록이 없다 — 이 문서는 기존 이름으로 표기.
- `views_ai_coach._load_chips`(v1)의 지연 import 를 그대로 둘지(호출마다 경고 로그) 칩 로드를 지울지 — 어느 쪽도 앱 기동에는 영향 없음.

## 6. 범위 밖 메모
- `src/ai/ai_context.py:21`이 `src/web/template_helpers.py`를 import — V1-10 목록 밖의 또 다른 공용 파일(`src/ai/__init__.py` docstring 도 의존 명시).
- `views_calendar_feed.py`(`/feeds/cal`)·`app.py`의 `/api/garmin/local-sync`는 v1 UI 가 아닌 공용 엔드포인트인데 `src/web` 에 있음 — 라우트 일몰 대상에서 제외 필요.
- v2→v1 링크: `SyncPanel.svelte`(`/settings` 4곳), `data/export/+page.svelte:133`(`/training/export.ics`), MenuDrawer quickLinks·`backToV1`·`user_settings_service`의 `ui_default` 'v1' 기본값 — V1-5 MENUDRAWER BACKLOG 항목 소관.
- 300줄 초과: `helpers.py` 903(3함수 이동 후에도 초과), `bg_sync.py` 625, `app.py` 1161 — 이동만으로는 해소 안 됨.
- V1-4 `classify_surface` 'v1' 분기는 보류 유지.
