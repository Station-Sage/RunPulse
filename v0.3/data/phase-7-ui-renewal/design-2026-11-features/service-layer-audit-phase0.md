# AUDIT-SERVICE-LAYER 0단계 — 도달성 대응표 (2026-11-11, 코드 변경 없음)

BACKLOG [AUDIT-SERVICE-LAYER] 추천 B 0단계 산출물. 1단계 이후는 **사용자 승인 대기**.

## 방법
- `src/`·`scripts/`·`tests/` 전 `.py` 를 `ast` 로 파싱해 import 그래프 작성: 함수 안 지연 import 포함, 상대 import 해석,
  `importlib.import_module("…")` 리터럴, `"src/x.py"` 경로 문자열(subprocess 대상), `"src.x.y"` 문자열(mock.patch 등) 포함.
  문자열 간선을 빼고 돌려도 분류 결과 동일(문자열 간선이 '현역' 판정을 부풀리지 않음).
- `src/sync.py` 는 같은 이름 패키지 `src/sync/` 때문에 import 불가 → 스크립트 노드로 따로 취급(subprocess 간선만).
- 분류(우선순위 순):
  - **v2-live**: `src.serve`/`src.web.app`(create_app — 모든 Blueprint·`src.api` 패키지) + subprocess 대상에서 도달. 단 아래 v1 모듈을 차단한 상태로.
  - **v1-only**: 앱에 등록됐지만 v1 HTML·v1 JSON 라우트(`views_settings_*`, `views_export`, `routes_v1_pages`, `routes_v1_sync`, `helpers*`)를 거쳐야만 도달.
  - **CLI**: `scripts/*.py`·`__main__` 가드가 있는 모듈·`src.mcp_server` 에서만 도달.
  - **test-only**: `tests/` 에서만 도달. **dead**: 어디서도 도달 불가.
- v2 프런트(`frontend/src`)의 v1 URL 참조는 grep 으로 별도 대조.

## 요약 (src/ 545모듈)

| 분류 | 모듈 | 줄 |
|---|---|---|
| v2-live | 463 | 58,332 |
| v1-only | 11 | 3,235 |
| CLI | 28 | 4,595 |
| test-only | 3 | 535 |
| dead | 40 | 7,694 (그중 `_v02_backup` 35파일 6,276) |

디렉토리별(모듈 수 / 줄):

|dir|v2-live|v1-only|CLI|test-only|dead|
|---|---|---|---|---|---|
|(root)|27 / 2371|1 / 192|4 / 868|-|-|
|ai|35 / 4909|-|-|2 / 246|4 / 1119|
|analysis|10 / 3050|-|-|-|-|
|api|31 / 3904|3 / 781|-|-|-|
|auth|9 / 497|-|-|-|-|
|import_export|10 / 1640|-|1 / 148|-|1 / 299|
|mcp_remote|7 / 539|-|-|-|-|
|metrics|58 / 6205|-|1 / 132|-|35 / 6276|
|ops|3 / 296|-|-|-|-|
|services|138 / 16447|1 / 90|2 / 377|-|-|
|sync|44 / 7034|-|11 / 1827|-|-|
|training|39 / 5285|-|4 / 610|1 / 289|-|
|utils|41 / 5077|-|2 / 191|-|-|
|validation|-|-|3 / 442|-|-|
|weather|2 / 85|1 / 105|-|-|-|
|web|9 / 993|5 / 2067|-|-|-|

**2026-10-10 재조사 수치(도달 불가 약 36,000줄)는 낡았다.** 그 뒤 v1 화면이 `v1_backup/` 으로 이동(S4-31~)했고 `bg_sync` 는 `src/sync/bg_sync.py` 로 옮겨져 현역이다. 현재 v2 비도달 합계는 약 16,000줄이며 그중 v1-only 3.2k·CLI 4.6k 는 지금도 쓰이는 경로가 있다.

## 핵심 확인 결과
- **planner_v2(·planner_v2_long)**: v2-live. `routes_plan_replan → training.planner → planner.py:221` 에서 `effective_rules_version(...) >= 2` 일 때 지연 import. 퇴역 대상 아님.
- **replanner**: test-only. `test_replanner` 만 import, `readiness.py`·`crs.py` 의 언급은 주석/docstring.
- **plan_gates·plan_gates_long·plan_backtest(_replan)**: CLI(`scripts/plan_backtest.py`) 전용. v2 경로 없음.
- **bg_sync**: v2-live(`web.app → sync.auto_sync → sync.bg_sync`). web 안이 아니라 이미 `src/sync/` 에 있다 → 3단계의 "bg_sync 이관"은 끝난 상태.
- **ai_context_legacy**: v2-live(`ai_context` 가 `build_context` 등을 재노출, `briefing.py:32,58` 사용 → coach). BACKLOG 1단계의 "죽은 코드" 판정은 틀림.
- **analysis/**: 전부 import 상 현역이지만 `src/analysis/__init__.py` 의 일괄 재노출 때문. 심볼 기준으로는 `zones_analysis`(today_service)·`recovery`·`trends`·`weekly_score`·`activity_deep`(ai_context_legacy·coach_rule_handlers)만 v2 가 쓰고, `compare`·`efficiency`·`race_readiness`·`report`(1,517줄)는 `analyze.py`·테스트만 쓴다(테스트 4파일 참조) — 함수 단위 정적 분석은 이 4개만 수행.
- **v2 가 의존하는 v1 라우트**: `/connect/strava/oauth-start`·`/connect/strava/callback`(`data_connect_service.py:86`), `/training/export.ics`(`exports.ts:33`, views_training_export=v2-live), `/api/garmin/local-sync`(외부 `scripts/garmin_local_sync.py`), `/mcp`·`/feeds/cal`(mcp_remote·calendar_feed — v2-live). 나머지 v1 URL(`/connect/garmin*`·`/connect/intervals`·`/connect/runalyze`·`/import*`·`/sync-status`·`/trigger-sync*`·`/bg-sync/*`·`/activities/export.csv`)은 v2 프런트 참조 0건(외부 북마크·운영 로그는 미확인).
- **동적 로딩**: `src/` 에 `importlib`/`__import__` 0건. subprocess 대상은 `src/sync.py`(manual_sync_service)·`src/import_history.py`(routes_v1_pages; import_service 로도 import 되어 v2-live)뿐. Jinja 템플릿은 `templates/generic_page.html` 하나를 v1 연동 화면만 렌더.

## 비현역 모듈 표 (v2-live 463개는 생략 — 위 디렉토리 요약 참조)

| 분류 | 모듈 | 줄 | 근거·비고 |
|---|---|---|---|
| v1-only | `src/api/routes_v1_pages.py` | 295 | `/import`·`/import-preview`·`/import/upload*`·`/sync-status` HTML. v2 프런트 참조 0건 |
| v1-only | `src/api/routes_v1_sync.py` | 418 | `/trigger-sync*`·`/bg-sync/*` 는 v2 참조 0건. **단 `/api/garmin/local-sync` 는 외부 클라이언트 `scripts/garmin_local_sync.py:225` 가 호출 → 유지·이관 필요** |
| v1-only | `src/api/v1_pages_helpers.py` | 68 | routes_v1_pages 전용 |
| v1-only | `src/services/manual_sync_service.py` | 90 | routes_v1_sync 전용. `src/sync.py` 를 subprocess 로 실행 |
| v1-only | `src/sync.py` | 192 | `src/sync.py` — import 불가(같은 이름 패키지 `src/sync/` 우선). v1 manual_sync subprocess + **문서화된 CLI**(CLAUDE.md) → 삭제 대상 아님 |
| v1-only | `src/weather/activity_weather.py` | 105 | `src/sync.py` 에서만 import(v2 bg_sync 경로 아님) — CLI 겸용 |
| v1-only | `src/web/helpers.py` | 880 | `app.py:194` Jinja context(_CSS·nav) — generic_page.html 렌더(v1 연동 화면)용 |
| v1-only | `src/web/helpers_svg.py` | 171 | helpers 재노출 전용 |
| v1-only | `src/web/views_export.py` | 99 | `/activities/export.csv` — v2 는 EXP 화면 사용(menuLinks.ts:25 V1-11b) |
| v1-only | `src/web/views_settings_garmin.py` | 590 | `/connect/garmin*` HTML. v2 는 `/api/v1/data/garmin` 사용. download-script/env 는 api 쪽에도 사본(routes_data_garmin) |
| v1-only | `src/web/views_settings_integrations.py` | 327 | **`/connect/strava/oauth-start`·`/callback` 은 v2 가 사용**(`data_connect_service.py:86` redirect) → 이관 전 퇴역 불가 |
| cli | `src/analyze.py` | 217 | 분석 CLI, 호출자 0. analysis.compare·report 등 유일 기능 소비자 |
| cli | `src/import_export/tz_backfill.py` | 148 | scripts/normalize_start_time.py |
| cli | `src/mcp_server.py` | 102 | **로컬 stdio MCP**(`.mcp.json` runpulse: `python3 -m src.mcp_server`) — 현역 도구, 삭제 불가 |
| cli | `src/metrics/cli.py` | 132 | 메트릭 재계산 CLI |
| cli | `src/plan.py` | 240 | 훈련 계획 CLI, 호출자 0 |
| cli | `src/services/unified_activities.py` | 17 | unified_view 재노출 shim |
| cli | `src/services/unified_view.py` | 360 | check_docs.py 는 파일 존재만 검사(경로 문자열). 실질 테스트 전용 |
| cli | `src/sync/dedup.py` | 119 | sync_cli 전용 |
| cli | `src/sync/garmin_backfill.py` | 233 | `__main__` CLI |
| cli | `src/sync/garmin_bulk_loader.py` | 250 | sync_cli 전용 |
| cli | `src/sync/garmin_v2_mappings.py` | 283 | garmin_backfill 전용 |
| cli | `src/sync/orchestrator.py` | 120 | sync_cli 전용 |
| cli | `src/sync/plan_ingest.py` | 244 | `__main__` CLI(외부 계획 수집) |
| cli | `src/sync/plan_ingest_intervals.py` | 84 | plan_ingest 전용 |
| cli | `src/sync/reextract.py` | 77 | sync_cli·backfill_stream_meta |
| cli | `src/sync/reprocess.py` | 298 | sync_cli 전용 |
| cli | `src/sync/runalyze_activity_sync.py` | 88 | sync_cli 전용 |
| cli | `src/sync/stream_meta_backfill.py` | 31 | scripts/backfill_stream_meta.py |
| cli | `src/sync_cli.py` | 309 | `python -m src.sync_cli` 데이터 CLI |
| cli | `src/training/plan_backtest.py` | 237 | scripts/plan_backtest.py |
| cli | `src/training/plan_backtest_replan.py` | 83 | scripts/plan_backtest.py |
| cli | `src/training/plan_gates.py` | 182 | 백테스트 판정기 — scripts/plan_backtest 전용(v2 미사용 확인) |
| cli | `src/training/plan_gates_long.py` | 108 | 동일 |
| cli | `src/utils/clipboard.py` | 44 | analyze.py 전용 |
| cli | `src/utils/db_status.py` | 147 | `__main__` CLI |
| cli | `src/validation/__init__.py` | 16 | `python -m src.validation` |
| cli | `src/validation/__main__.py` | 92 |  |
| cli | `src/validation/validator.py` | 334 |  |
| test-only | `src/ai/ai_parser.py` | 125 | test_ai_parser 만 |
| test-only | `src/ai/ai_schema.py` | 121 | ai_parser·test_ai_schema 만 |
| test-only | `src/training/replanner.py` | 289 | **test_replanner 만**. readiness.py·crs.py 의 언급은 주석/docstring |
| dead | `src/ai/ai_message.py` | 311 | v1 카드 AI 메시지. import 0 |
| dead | `src/ai/ai_validator.py` | 127 | ai_message 전용 |
| dead | `src/ai/context_builders.py` | 437 | ai_message 전용 |
| dead | `src/ai/prompt_config.py` | 244 | ai_message 전용 |
| dead | `src/import_export/intervals_fit.py` | 299 | import 0(자기 자신만) |
| dead | `src/metrics/reprocess.py` | 87 | import 0 (`src.sync.reprocess` 와 별개) |
| dead | `src/metrics/_v02_backup/` (34파일) | 6189 | 내부 상호 import 뿐, 외부 참조 0 |

## 1~4단계 후보 (승인 전 실행 금지)
1. **확실한 죽은 코드**(약 7.7k): `metrics/_v02_backup/`(35파일), `ai/ai_message`·`ai_validator`·`context_builders`·`prompt_config`, `import_export/intervals_fit`, `metrics/reprocess`. test-only `ai_parser`·`ai_schema`·`training/replanner`(+해당 테스트 3파일)도 후보 — replanner 는 `session_outcomes` 스키마 참조 주석이 있어 확인 필요. **`analyze.py`·`plan.py` 는 CLI(호출자 0)라 "죽음"이 아닌 "사용자 결정"**: 쓰지 않는다면 함께 제거 시 `utils/clipboard`·analysis `compare/efficiency/race_readiness/report`(+`__init__` 재노출 정리)가 따라 비게 됨. `ai_context_legacy` 는 제외(현역).
2. **v1 라우트 퇴역(리다이렉트 유지)**: `views_export`, `routes_v1_pages`(+`v1_pages_helpers`), `views_settings_garmin`, `views_settings_integrations` 의 intervals·runalyze·strava 화면, `routes_v1_sync` 의 `/trigger-sync*`·`/bg-sync/*`(+`manual_sync_service`), `helpers`·`helpers_svg`·`templates/`(마지막 HTML 소비자 제거 후). 영향 테스트 8파일(test_flask_routes·test_garmin_local_sync_api·test_index_ui_default·test_manual_sync_service·test_trigger_sync_bg_v1·test_v1_sync_guards·test_views_settings_garmin_migration·test_weather_ingest[activity_weather 는 CLI 겸용이라 유지]).
3. **v1 에 남은 v2 의존 이관**(2단계 선행 조건): Strava OAuth `oauth-start`·`callback` → `src/api`(redirect URI 변경은 Strava 앱 설정 영향, 사용자 작업 필요할 수 있음), `/api/garmin/local-sync` → api Blueprint(외부 스크립트 URL 호환 유지). `bg_sync` 이관은 이미 완료.
4. **정리**: 테스트(1·2단계 합 약 11파일), `check_docs.py:726·874·901`(sync_cli·unified_view 존재 검사), `files_index`, `src/web/__init__.py` docstring("v1 UI"), ADR·BACKLOG 수치 정정.

## 불확실성
- 정적 분석: `getattr`·문자열 디스패치·Blueprint 이외 외부(nginx·cron·운영 수동 명령)에서 부르는 경로는 잡지 못한다. 운영 컨테이너의 cron·수동 스크립트 사용 여부 미확인.
- v1 URL 의 외부 사용(북마크·운영 접근 로그) 미확인 — 2단계 전 운영 로그 1~2주 확인 권장.
- 모듈 단위 판정이라 v2-live 모듈 안의 미사용 함수(예: analysis 재노출, `web.app` 의 Jinja context)는 함수 단위로 따로 봐야 한다.
