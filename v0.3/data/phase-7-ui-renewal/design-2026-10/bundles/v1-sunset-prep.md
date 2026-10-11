# v1 일몰 준비 — 공용 파일 view 밖 이관·v1 호출부 정리

- 작성 2026-10-11. 근거 결정: decisions-table.md V1-1(정정)~V1-11. 코드 사실은 모두 2026-10-11 grep 기준(코드 미수정).
- 일몰 정의(V1-1 정정·V1-2): v1 일몰 = **UI·라우트 일몰**. 공유 파일·함수는 유지, 재설계가 필요한 v1 파일은 재설계.
- 이 문서 범위: V1-10 4파일 이관, V1-6 loader 제거, V1-3·V1-8·V1-9 /switch-user, V1-11 MenuDrawer CSV, V1-7 suggestions 검토. V1-4(classify_surface 'v1' 분기)는 보류 유지 — 함수 자체가 아직 코드에 없음(`security-headers.md` 설계에만 존재).

## 1. 근본 원인

**RC-1. 계층 역전: v2 서버 코드가 v1 view 디렉터리(`src/web/`)를 import 한다.** `src/web/` 밖 src 파일 22곳이 `src.web.*` 4파일을 import 한다(api 19, services 4, utils 2, 중복 제외 22). v1 view 를 지우면 v2 가 깨지는 구조라 "UI·라우트만 일몰"이 파일 단위로 불가능하다.

**RC-2. 공용 로직과 v1 화면 로직이 한 파일에 섞여 있다.** `helpers.py`(903줄)는 v2 가 쓰는 3함수(`project_root`·`get_current_user_id`·`db_path`)와 v1 HTML 조립(`_CSS`·`_SYNC_JS`·`html_page`·`bottom_nav`·`fmt_*` 등)을 함께 갖는다. `/switch-user`는 로직이 `app.py:266` 라우트 안에 인라인이다.

### 1.1 import 그래프 (V1-10 4파일)

| 파일(줄) | Flask 의존 | `src/web` 밖 src importer | `src/web` 안 importer | tests |
|---|---|---|---|---|
| `bg_sync.py`(625) | 없음 | `api/routes_data.py:105`(stop_job), `services/data_settings_service.py:18`(cancel_job), `services/sync_range_service.py:66`·`services/sync_trigger_service.py:131`(비공개 `_start_or_existing`) — 4 | `app.py`(654·696·787·815·823·831·845), `auto_sync.py:36`, `views_settings_garmin.py:55` — 3 | 10: test_api_data_sync, test_auto_sync_reload, test_bg_sync_batch_error, test_bg_sync_concurrency, test_data_settings, test_provider_status_service, test_sync_range, test_sync_trigger_service, test_trigger_sync_bg_v1, test_v1_sync_guards |
| `auto_sync.py`(129) | 없음 | `services/data_settings_service.py:67`(restart) — 1 | `app.py:184`(start), `views_sync.py:181·246`(status·restart) — 2 | 3: test_auto_sync_reload, test_data_settings, test_sync_range(`_connected_sources`) |
| `helpers.py`(903) | `get_current_user_id`가 flask.session 지연 import | `api/__init__.py:63` + `api/routes_*.py` 18개(db_path·get_current_user_id), `services/sync_trigger_service.py:88`, `utils/config.py:101`, `utils/user_context.py:35` — 22 | `app.py` 포함 50개(v1 view 전부, HTML 헬퍼) | 4: test_api_today(모듈 속성 `helpers.db_path` 교체), test_flask_routes(동일), test_mcp_http_routes·test_provider_status_service(문자열 `"src.web.helpers.get_current_user_id"` monkeypatch) |
| `views_mcp_remote.py`(128) | Blueprint `/mcp` | `api/routes_mcp_tokens.py:21`(`enabled`) — 1 | `app.py:48·1152`(등록) — 1 | 2: test_mcp_http_routes, test_mcp_token_routes(`from src.web import views_mcp_remote as v`) |

- 순환: `helpers.py:7`이 `utils.config.load_config`를 import, `utils/config.py:101`이 다시 `helpers.get_current_user_id`를 지연 import(utils→web 역방향).
- `bg_sync`→`auto_sync` 방향 의존(auto_sync 가 start_basic_sync 호출). 두 파일 모두 Flask 무의존. `services/*.py` 중 flask import 0건(관례).
- 경로 참조(문서·스크립트): `files_index.md`(1048·1052·1219 + 테스트 항목, `gen_files_index.py` 재생성), `scripts/check_docs.py`·`gen_files_index.py`의 `SCAN_DIRS`(`src/web` 포함, `src/api`·`src/mcp_remote` 미포함), `src/web/__init__.py` docstring("기존 69개 뷰 파일" — 현재 84개), 진행 중 설계서 `high-severity-remaining.md:42·68`(bg_sync), `accessibility-common.md:189`(helpers.py:11), `server-input-origin-validation.md:5·86`(views_mcp_remote), Dockerfile:21 주석(auto_sync 이름만). CLAUDE.md·`.claude/rules`·skills 는 4파일 경로 참조 없음. 그 밖에 ux-review-2026-09·specs 의 과거 설계서 다수(이력 문서).

### 1.2 v1 loader `load_adjustment` (V1-6)
- 정의 `views_training_loaders.py:38-47`: `adjust_todays_plan(conn, config)` 호출 + 예외 시 None. `config` 인자는 adjuster 에서 "현재 미사용"(`adjuster.py:34`).
- 호출부 1곳: `views_training.py:83`(v1 `/training`) → 결과는 `render_adjustment_card`·컨디션 카드로만 감. 테스트 직접 참조 0건(`views_training_loaders`의 다른 함수는 test_training_fullplan·phase_g·month 가 import).
- v2 대응: `plan_service.get_todays_adjustment`(`:143`) → `GET /api/v1/coach/plan/adjustment`(`routes_plan.py:42`). data-freshness §2.7 이 래퍼 `plan_service.todays_adjustment_with_hold`와 가드 `tests/test_adjuster_callers.py`(허용: adjuster·plan_service·plan.py)를 설계함 — loader 제거가 가드 도입의 선행(0단계).

### 1.3 /switch-user (V1-3·V1-8·V1-9, SRV-6)
- `app.py:266-293` 인라인. POST: `session["user_id"]=uid` + `init_db(uid)` → `/` 리다이렉트. uid 형식 검증 없음. GET: `data/users` 하위 목록을 미이스케이프 `<option>`으로 조립, `helpers.html_page` 사용.
- `auth_cf._identify_user`는 세션에 `user_id`가 있으면 CF 헤더를 다시 보지 않음(`auth_cf.py:72`) → 운영에서도 전환값이 유지됨(SRV-6 차단 사유).
- 진입점: v2 `MenuDrawer.svelte:115`. 테스트 참조 0건. 이관 설계는 `server-input-origin-validation.md` §2.5(①서비스 분리+v2 엔드포인트·운영 404 → ②v2 화면·링크 교체 → ③v1 라우트 삭제)에 이미 있음.

### 1.4 MenuDrawer.svelte 의 v1 의존(133줄)
- quickLinks(35-41): `/dashboard` `/activities` `/wellness` `/training` `/race` `/ai-coach` `/shoes`. dataLinks(45-47): `/settings` `/guide` `/activities/export.csv`(V1-11). 하단: `/switch-user`(115), `backToV1()`(25-32: `ui_default='v1'` 저장 후 `/dashboard`).
- v2 의 그 밖의 v1 의존: `shell/SyncPanel.svelte:28·29·69·95`(`/settings`), `routes/data/export/+page.svelte:133`(`/training/export.ics`, v1 `views_training_export.py:17`). EXP 화면은 `frontend/src/routes/data/export/`(존재).

### 1.5 suggestions (V1-7)
- `get_runner_state`·`rule_based_chips` 호출처: src 는 `views_ai_coach.py:149-151`(`_load_chips`, v1 `/ai-coach` 202행) 1곳뿐. tests: test_data_quality(5)·test_integration_realdb(5).
- 같은 파일 `CHIP_REGISTRY`는 공용: `ai/briefing.py:59`·`ai/chat_engine.py:88`(v2 코치 경로)·`views_ai_coach.py:252·310`.
- v2 칩은 별도 구현: `GET /api/v1/coach/suggestions` → `ai/coach_rule_handlers.suggestion_chips`(suggestions.py 미사용).

### 1.6 v1 라우트 등록 현황(`app.py`)
- Blueprint 28개(1132-1159): v1 view 25 + 비UI 3(`mcp_remote_bp`·`calendar_feed_bp`(`/feeds/cal`, v2 `routes_data_calendar.py:22`가 URL 생성)·`api_bp`). v1 view: wellness, activity, activities, settings(+garmin·integrations·metrics), merge, export_import, export, shoes, dashboard, report, import, race, ai_coach, training(+crud·goal_crud·export), wizard, fullplan, dev, guide, sync.
- app 직접 라우트: `/switch-user`, `/`(entry_path), `/analyze/*`, `/home-legacy`, `/trigger-sync*`, `/bg-sync/*`, `/import*`, `/sync-status`, `/v2/*`(SPA), `/api/garmin/local-sync`(`scripts/garmin_local_sync.py:225`가 호출 — 비UI).

## 2. 설계안

### 2.1 이관 원칙
- 공개 함수 시그니처 불변, import 경로만 변경. `src/web/` 에 재노출 shim 을 둘지는 V1S-5(모듈 속성 교체 테스트 2건은 shim 이 있어도 새 모듈을 패치해야 동작 — 1.1 참조).
- `helpers.py`는 공용 3함수만 이관, HTML 헬퍼는 v1 과 함께 일몰(분리 방식은 V1S-2).

### 2.2 새 위치 후보(결정하지 않음)

| 대상 | 후보 A | 후보 B |
|---|---|---|
| bg_sync·auto_sync | `src/services/`(sync_*_service 이웃. 장점: v2 importer 가 이미 services. 단점: 625줄 스레드 실행기가 "Flask 무의존 서비스" 관례 안에 들어감, 300줄 초과 그대로) | `src/sync/`(동기화 엔진 계층. 장점: `ledger`·`sync_errors` 와 같은 패키지. 단점: services→sync 방향은 기존과 같으나 sync 패키지가 sync_jobs·user_context 까지 의존하게 됨) |
| helpers 공용 3함수 | `src/utils/user_context.py`에 병합(장점: `resolve_user_id`가 이미 있고 utils→web 역방향 제거. 단점: utils 에 flask.session 지연 import — `utils/public_url.py` 선례 있음) | 신규 `src/api/request_context.py`(장점: 요청 문맥이 API 계층에 머묾. 단점: services·utils 3곳이 api 를 import → 다른 역방향, `src/api`는 check_docs·files_index SCAN_DIRS 밖) |
| views_mcp_remote | `src/mcp_remote/http.py`(장점: 프로토콜 코어와 동거. 단점: 현재 Flask 무의존 패키지에 Blueprint 유입, SCAN_DIRS 밖) | `src/api/routes_mcp_remote.py` + 별도 Blueprint(접두사 없음)(장점: HTTP 라우트 계층 일원화. 단점: `api/__init__`의 `api_bp`(/api/v1)와 다른 Blueprint 를 같은 패키지에 둠, SCAN_DIRS 밖) |

### 2.3 V1-6 호출부 재설계 형태(data-freshness 열린 항목, 둘 다 가드 허용 목록 변경 없음)
- (a) `views_training.py`가 래퍼 `plan_service.todays_adjustment_with_hold`(또는 현행 `get_todays_adjustment`)를 직접 호출 — 래퍼는 예외를 전파하므로 호출부 try/except 필요. 보류일 상향 문구가 v1 에서도 사라짐.
- (b) v1 화면에 조정 입력을 넘기지 않음(`adjustment=None`) — 현행 예외 시 경로와 같은 렌더(조정 카드 미표시).

### 2.4 그 밖
- /switch-user: `server-input-origin-validation.md` §2.5 순서 그대로. 사용자 목록·uid 검증·전환을 Flask 무의존 서비스 함수로, 세션 기록은 라우트에서(서비스의 flask 무의존 관례 유지). 운영 404·MenuDrawer 링크 운영 숨김은 같은 변경(V1-9 b). 경로·화면 위치는 구현 단계 제안(V1-8 c).
- MenuDrawer CSV(V1-11 b): `dataLinks`의 `/activities/export.csv` → `{base}/data/export`(SvelteKit 내부 링크이므로 `data-sveltekit-reload` 불필요 — 구현 시 확인).
- suggestions(V1-7): 사용처 사실은 1.5. 제거/재설계 선택은 V1S-4.

## 3. 변경 파일 표

| 파일 | 구분 | 예상 영향 |
|---|---|---|
| `src/web/bg_sync.py`·`auto_sync.py` | 이동 | 새 위치(V1S-1). 내부 `from src.web.bg_sync` 1곳 갱신 |
| `src/web/helpers.py` | 분리 | 공용 3함수 이동, 나머지 v1 전용 잔류(V1S-2) |
| `src/web/views_mcp_remote.py` | 이동 | 새 위치(V1S-3), docstring 의 경로 설명 유지 |
| `src/api/__init__.py`, `src/api/routes_*.py` 19개 | 수정 | import 1줄씩 |
| `src/services/{data_settings,sync_range,sync_trigger}_service.py` | 수정 | 지연 import 경로. `_start_or_existing` 비공개명 교차 사용은 유지/공개화 여부 구현 시 확인 |
| `src/utils/config.py`, `src/utils/user_context.py` | 수정 | 지연 import 경로(후보 A 면 user_context 는 정의 보유) |
| `src/web/app.py` | 수정 | import 경로, `/switch-user` 삭제(−30줄), Blueprint 등록 경로 |
| `src/web/views_settings_garmin.py`, `views_sync.py`, v1 view 50개 | 수정/무변경 | 앞 2개는 bg_sync·auto_sync 경로. helpers HTML 만 쓰는 v1 view 는 V1S-2 에 따라 무변경 가능 |
| `src/web/views_training.py`, `views_training_loaders.py` | 수정 | `load_adjustment` 삭제(−10), `:83` 재설계(V1S-6) |
| `src/services/` 신규 사용자 전환 모듈, `src/api/` 전환 엔드포인트 | 신규 | §2.5 설계 따름 |
| `frontend/src/lib/components/MenuDrawer.svelte` | 수정 | CSV 링크 → EXP, `/switch-user` → v2 화면·운영 숨김 |
| tests 14개(1.1 표 합집합) | 수정 | import·monkeypatch 문자열 경로. `test_flask_routes`·`test_api_today`는 모듈 속성 교체 대상 변경 |
| `scripts/check_docs.py`·`gen_files_index.py` | 수정 가능 | 새 위치가 SCAN_DIRS 밖이면 추가 여부(V1S-1·3) |
| `v0.3/data/files_index.md`, `src/web/__init__.py`, 새 위치 `__init__.py` docstring | 재생성/수정 | 문서 규칙(docstring 이 SSOT) |
| 진행 중 설계서 3개(1.1 마지막 항목) | 수정 | 경로 문자열 |

## 4. 단계·검증 (1단계 = 1커밋, 각 단계 대상 테스트 → 전체 pytest)
1. **auto_sync·bg_sync 이동**(함께 — 상호 의존). 검증: 1.1 표 bg_sync·auto_sync 테스트 10개(합집합) + `grep -rn "src.web.bg_sync\|src.web.auto_sync\|from .bg_sync\|from .auto_sync" src tests` 0건.
2. **helpers 공용 3함수 분리·이동**. 검증: test_api_today·test_flask_routes·test_mcp_http_routes·test_provider_status_service + `grep -rn "src.web.helpers" src/api src/services src/utils` 0건, `python3 -c "import src.utils.config"` 순환 없음.
3. **views_mcp_remote 이동**. 검증: test_mcp_http_routes·test_mcp_token_routes, `/mcp` 404/401 동작 불변.
4. **V1-6 loader 제거**(data-freshness §2.7 0단계와 같은 단계 — 가드 도입 전). 검증: `grep -rn "load_adjustment" src` 0건, v1 UI 회귀 검증 안 함(V1-1).
5. **/switch-user v2 이관 + SRV-6**(§2.5 ①②③). 검증: 운영 설정에서 v2 엔드포인트 404, 개발 설정 전환 동작, `grep -rn "switch-user" src frontend/src` 에 v1 경로 0건.
6. **MenuDrawer CSV 링크 교체**. 검증: `npm run check`, 링크 대상 `/data/export` 렌더.
7. **V1-7 결정 반영**(V1S-4).
8. 마감: `gen_files_index.py`, `check_docs.py`, 전체 `pytest tests/`, 최종 `grep -rln "src\.web\." src --include=*.py | grep -v "^src/web/"`(목표: `ai/ai_context.py`의 template_helpers 1곳만 남음 — 범위 밖 메모).

## 5. 결정 필요 (정책성만)
- **V1S-1. bg_sync·auto_sync 새 위치**: (A) `src/services/` / (B) `src/sync/`. 파일명 유지 여부 포함(예: `bg_sync_runner.py`).
- **V1S-2. helpers 분리 방식**: (a) 공용 3함수만 이동, HTML 헬퍼는 `src/web/helpers.py` 잔류(v1 일몰 시 삭제) / (b) 파일 전체를 view 밖으로 이동(v1 HTML 코드가 view 밖에 남음). 위치는 (A) `utils/user_context.py` / (B) `api/request_context.py`.
- **V1S-3. views_mcp_remote 새 위치**: (A) `src/mcp_remote/http.py` / (B) `src/api/routes_mcp_remote.py`(별도 Blueprint).
- **V1S-4. suggestions 2함수**(V1-7 검토 결과): (a) v1 `/ai-coach`와 함께 제거(+tests 10곳 정리, `CHIP_REGISTRY` 유지) / (b) v2 `suggestion_chips`로 이미 대체됐다고 보고 지금 제거 / (c) v2 재설계로 유지 — v2 에 동일 기능(`coach_rule_handlers.answerable_chips`)이 있어 중복.
- **V1S-5. 구 경로 재노출 shim**: (a) 두지 않음(한 커밋에서 전 importer 갱신) / (b) 일몰까지 `src/web/` 에 재노출(단, monkeypatch 대상 혼동 위험).
- **V1S-6. V1-6 호출부 형태**: §2.3 (a) 래퍼 직접 호출 / (b) 조정 입력 미전달.
- **V1S-7. 새 위치가 SCAN_DIRS 밖일 때**: check_docs·gen_files_index 에 디렉터리 추가 여부.

## 6. 범위 밖 메모
- `src/ai/ai_context.py:21`이 `src/web/template_helpers.py`를 import — V1-10 목록 밖의 또 다른 공용 파일(`src/ai/__init__.py` docstring 도 의존 명시).
- `views_calendar_feed.py`(`/feeds/cal`)·`app.py`의 `/api/garmin/local-sync`는 v1 UI 가 아닌 공용 엔드포인트인데 `src/web` 에 있음 — 라우트 일몰 대상에서 제외 필요.
- v2→v1 링크: `SyncPanel.svelte`(`/settings` 4곳), `data/export/+page.svelte:133`(`/training/export.ics`), MenuDrawer quickLinks·`backToV1`·`user_settings_service`의 `ui_default` 'v1' 기본값 — V1-5 MENUDRAWER BACKLOG 항목 소관.
- `/switch-user` 폼은 select·input 이 모두 `name="user_id"`라 `request.form.get`은 첫 값(select)만 읽음 — 이관 시 소멸.
- 300줄 초과: `helpers.py` 903, `bg_sync.py` 625, `app.py` 1161 — 이동만으로는 해소 안 됨.
- V1-4 `classify_surface` 'v1' 분기는 라우트 일몰 정의 검토 후 결정(보류 유지).
