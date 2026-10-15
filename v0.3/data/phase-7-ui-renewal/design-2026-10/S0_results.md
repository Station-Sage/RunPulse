# S0 점검 결과 (2026-10-12)

읽기 전용 사실 확인. 코드 수정 없음. 확인하지 못한 것은 '미확인'.

## 1. 코드로 확정된 사실

| 항목 | 결과 |
|---|---|
| SCAN_DIRS | `check_docs.py`는 9개 폴더(+ tests·scripts를 별도 추가), `gen_files_index.py`는 11개. 둘 다 `src/api`·`src/mcp_remote`·`src/import_export`·`src/analysis`를 포함하지 않는다. S2에서 `src/mcp_remote/`가 새 위치가 되면 두 스크립트에 추가해야 한다 |
| 현재 스키마 | `SCHEMA_VERSION = 36` (`src/db_setup.py:32`), `db_schema_v20~v36.py` 존재. v37 이후는 새 파일 |
| 개발 환경 SQLite | 3.45.1. 운영 컨테이너(`runpulse-runpulse-1`)는 3.46.1 (2026-10-12, `sqlite3.sqlite_version`만 조회, DB 미접근) |
| APP_ENV 판정 | `auth_cf.py:23-24`, `app.py:156`, `app.py:707`이 각각 같은 식으로 판정한다(분산). SEC에서 단일 헬퍼로 모을지 S3에서 결정 |
| CSP·csp-report | `src/`에 `Content-Security-Policy`·`csp-report` 문자열 없음. 전부 신규 구현 |
| session 키 | `session["user_id"]`만 쓰고 `app.py:235,270`, `auth_cf.py:65` |
| `get_db_path` | `src/db_setup.py:39`, 시그니처 `(user_id=None, *, create=True)`. ValueError 처리 방식은 **미확인(S3에서 읽음)** |
| TZ-23 | `import_export/strava_csv.py:384-387`이 `start_time`을 무조건 덮어쓴다(확인). 1327 정정 파생 값은 **미확인** |
| HSR-13 | `match_select.pick_activity`는 `(id,date,dist,…)` 행 리스트를 받아 단일 후보를 반환. 후보 집계 위치는 설계서대로 matcher쪽(S4~S6) |
| FRS-26 | hrv 7일 창은 `analysis/recovery.py:132`(7일 평균 비교)와 `services/wellness_day.py:87-91`(mean7/28)에 각각 있다. 의미 통일 필요 여부는 S4 설계 확인 사항 |
| FRS-27 | `badge`·`hold_headline` 문자열은 `src/services`에서 발견되지 않음(프런트·다른 경로일 수 있음). **미확인** |
| 비UI 라우트(app.py 직접) | `/trigger-sync*`, `/api/garmin/local-sync`, `/bg-sync/*`, `/import*`, `/sync-status`, `/switch-user`, `/analyze/*`, `/home-legacy`, `/` (v1 일몰 대상과 공용 구분 필요) |

## 2. v1 일몰 importer (src 쪽, `src.web.*`를 쓰는 비-web 파일)

- bg_sync/auto_sync: `services/data_settings_service`, `services/sync_range_service`, `services/sync_trigger_service`, `api/routes_data`, `web/views_settings_garmin`
  - 테스트 약 14곳 (`test_bg_sync_*`, `test_api_data_sync`, `test_data_settings`, `test_sync_*`, `test_auto_sync_reload`, `test_v1_sync_guards`, `test_trigger_sync_bg_v1`, `test_provider_status_service`)
- `src.web.helpers`: `utils/user_context.py`, `utils/config.py`, `services/sync_trigger_service.py`, `api/*` 20여 파일(`db_path`, `get_current_user_id`)
- `src.web.template_helpers`: `ai/ai_context.py`
- `src.web.views_mcp_remote.enabled`: `api/routes_mcp_tokens.py`
- 총 79건. S2에서 이관 대상은 `bg_sync`·`auto_sync`·`helpers`·`template_helpers`·`views_mcp_remote`의 공용 부분

## 3. goal_id 필터 경로 분류 (coach-plan-bundle §8-5)

기준: 교체·복구 이후 날짜의 planner 행을 **날짜만으로** 고르는 경로 = 겹침 가능 → 필터.
아래는 grep 계수(`planned_workouts` 언급 수 / `goal_id` 언급 수 / source 조건 수)에 근거한 1차 분류이며, 파일별 SQL 판독은 S6 착수 시 확정한다.

- **이미 goal_id를 쓰는 경로(필터 불요 가능성 높음)**: `plan_move`, `plan_service`, `progression_service`, `plan_adjustment_service`, `plan_replan_service`, `weekly_adapt_job`, `planner`, `rematch`(부분), `routes_plan_adjust`, `coach_rule_plan_handlers`
- **goal_id 없이 날짜로 읽음 → 겹침 가능 후보(필터 검토 필요)**: `matcher`, `week_compliance`, `planned_query`, `plan_overlay`, `adjuster`, `plan_load`, `plan_advisory`, `plan_pain`, `plan_replan_diff`, `replanner`, `calendar_feed_service`, `garmin_push`, `week_digest`, `outcome_store`, `plan_replace`, `analysis/weekly_score`, `ai/context_builders`, `ai/chat_context_builders`, `ai/coach_rule_handlers`, `ai/tool_exec_context`, `ai/ai_context_legacy`
- 특이: `matcher.py:51-52`는 `(source_system, source) IN ('planner','runpulse')` 정렬만 하고 goal_id는 보지 않는다. 헬퍼는 `src/training/planned_query.py`(PLN-33 a)

## 4. 사용자 확인·결정이 필요한 항목

2. BACKLOG NOW에 구현 단계 항목이 없음 → S1~S8을 NOW(최대 3개)로 어떻게 올릴지 — **승인 2026-10-16**: 단일 `[V2-IMPL]` 항목으로 단계 진행 상태를 갱신하는 현행 방식 유지(NOW 3개 이내)
3. Q5(인증 통과 요청만 집계) 문서 반영(SEC-10·SEC-12 수정) — **승인 2026-10-16, 반영 확인 완료**: decisions-table SEC-10·SEC-12 행, `patterns/security-headers.md` §4, `patterns/server-input-origin-validation.md` §4·§해소 항목에 이미 기재됨
4. race-calendar §8 6항목, FRS-27 badge·hold_headline, TZ-23 1327 파생 값, `get_db_path` ValueError는 미확인. 해당 단계(S3/S4/S6) 착수 시 확인

## 5. S1 진입 조건

- 점검 결과상 S1(`crs.evaluate()` 복원, ADJ-22)을 막는 항목 없음. 단 `adjustment-signals` §3.13·ADJ-23 확인(미완)이 S1 시작 시 첫 작업
- (2026-10-13) S1 완료 — `S1_results.md`. `adjustment-signals` §3.13·ADJ-23 확인: ADJ-23(`adjuster_version`·수락률 N)은 신규 `adjuster_frequency.py`·`user_settings` 범위로 S1과 무관(S6).
