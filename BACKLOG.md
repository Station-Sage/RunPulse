# BACKLOG

## NOW

- **[PHASE-7]** UI Renewal 설계 문서 작성 진행 중 → `v0.3/data/phase-7-ui-renewal/BACKLOG.md` 참조

## BUGS

- **[AUDIT-SERVICE-LAYER]** 웹 UI 각 뷰가 raw SQL 직접 작성 (40+곳). Phase 5 설계에서 요구한 `activity_service`, `metrics_loader`, `wellness_loader` 서비스 레이어 미구현. UI 재설계 시 함께 정리 필요.
- **[AUDIT-V-CANONICAL]** `views_report.py` 등 일부 뷰에서 `v_canonical_activities` 대신 `activity_summaries` 직접 쿼리 → 중복 활동 포함 위험. **(판단 필요)** UI 재설계 범위와 함께 결정.

## 미해결 확인 사항 (MIGRATION-04 §6)
- [중간] curl_cffi ARM64 wheel 존재 여부 (AWS Graviton) — Dockerfile 빌드
- [낮음] test_flask_routes.py garmin 라우트 포함 여부 — 테스트 커버리지

## NEXT

## DONE (recent)
- **[TEST-REALDB-INTEGRATION]** `tests/test_integration_realdb.py` 신규 (97개 테스트, 20 클래스): pansongit@gmail.com 실 DB session-scoped read-only 연결, Part1(원시 무결성)·Part2(분석 파이프라인)·Part3(서비스 레이어)·Part4(보조 검증) 풀 커버리지. 컬럼명 수정(`sport`→`activity_type`, `elapsed_duration_sec`→`elapsed_time_sec`, `elevation_gain_m`→`elevation_gain`, `lat/lon`→`latitude/longitude`, `altitude`→`altitude_m`, `group_id`→`matched_group_id`). 1188 passed.
- **[TEST-DATA-QUALITY]** `tests/test_data_quality.py` 신규 (45개 테스트): 4주 러너 픽스처 기반으로 trends/compare/weekly_score/race_readiness/activity_deep/suggestions/dashboard/wellness 분석 파이프라인의 물리적 범위·의미론적 정확성 검증. `conn.lastrowid` → `cursor.lastrowid` 수정. 1091 passed.
- **[BUG-TRENDS-DAILY-FITNESS]** `fitness_trend()` CTL/ATL/TSB 항상 None 수정: `_fitness_last_from_daily_metrics(scope_type='daily')` + `_fitness_last_from_activity_metrics(scope_type='activity')` 분리, 죽은 코드 `_fitness_last_from_daily()`/`_fitness_last_from_metrics()` 제거. 1046 passed.
- **[LOG-OVERHAUL]** 로그 중앙화: `src/utils/log_config.py` 신규 (dictConfig + stdout + werkzeug WARNING). 진입점 4곳(`serve.py`, `sync.py`, `sync_cli.py`, `mcp_server.py`) basicConfig → setup_logging() 전환. `sync.py` print() 12건 → log, `bg_sync.py` print() 1건 → log. Dockerfile CMD → gunicorn --reload (auto-reload + docker logs 완전 캡처). 1043 passed.
- **[BUG-PACE-FORMAT]** `pace.py` `seconds_to_pace()`/`format_duration()` — float 입력 시 `:02d` format code 에러. `int(seconds)` 변환 추가. grouped activity `/activity/deep` 조회 오류 해소.
- **[#P5J distance_km→distance_m]** `matcher.py` 2곳 `SELECT distance_km FROM v_canonical_activities` → `distance_m / 1000.0 AS distance_km` 수정. 나머지 292개 참조는 `planned_workouts.distance_km`(올바름) 또는 이미 alias 패턴으로 정상. `views_export.py`/`test_consumer_migration.py` 기완료. 1043 passed.
- **[BUG-ACTIVITY-GROUP-NULL]** `save_activity_core()`에 `assign_group_id()` 호출 추가 (`_helpers.py:25`). `auto_group_all()` 역소급 실행 — 922 NULL → 173 NULL, 462 그룹 형성. 1043 passed.
- **[BUG-BASIC-SYNC-DISCONNECT]** 기본/기간 동기화 모두 bg_sync 방식으로 전환 (브라우저 연결 독립). `/trigger-sync-bg` 라우트 + `start_basic_sync()` 추가. `doSync` SSE 경로 제거, `syncStatusShow/Update/Hide` 함수 제거, bg-mode 체크박스 제거. 1043 passed.
- **[BUG-SYNC-STATUS-STALE]** `get_status()`가 완료된 작업 대신 구 paused 작업 반환 — `sync_jobs.py`에 `get_latest_job()` 추가 + `bg_sync.get_status()`가 이를 사용하도록 변경. `create_job()`에서 신규 작업 시작 시 기존 paused/stopped 작업 자동 정리.
- **[BUG-STREAMS-DUPLICATE]** `upsert_streams_batch` INSERT → INSERT OR IGNORE 전환 (`db_helpers.py:609`). Strava source_payloads 547건 + activity_streams 232,336건 삭제 후 전체 재동기화.
- **[BUG-FROMDATE-IGNORED / BUG-INCLUDE-WEEKLY / BUG-CLEAR-NEEDS-RESYNC]** `strava.py`/`intervals.py` wrapper가 `from_date`/`to_date`를 `_act_sync.sync()`에 전달하지 않던 버그 수정. `intervals_activity_sync.py` `sync()` 시그니처에 `from_date`/`to_date` 추가 + Strava 페이지네이션 루프 추가. `views_race.py` `include_weekly=False` kwarg 제거. `db_setup.py`에 `clear_needs_resync()` no-op 추가. 1043 passed.
- **[BUG-METRIC-VO2MAX / BUG-METRIC-MISSING]** VO2Max 항상 None 수정: `trends.py` fallback metric, `race_readiness.py` scope/이름, `activity_deep.py` daily_fitness→metric_store 교체, `hr_zone_distribution`→`hr_zones_detail` 키 수정. `daily_fitness` 잔존 참조 3곳 정리(`suggestions.py` TSB, `views_dev.py` count, `runalyze.py` dead code). 1043 passed.
- **[TEST-STALE-DATES / TEST-GARMIN-AUTH / TEST-ENSURE-DEPS]** 테스트 9건 수정: 픽스처 하드코딩 날짜 → 상대 날짜, garmin_auth B안(테스트를 구현에 맞게 수정 + explicit-path 폴백 버그 수정), `patch.dict(sys.modules, {"garminconnect": None})` 격리 방식 채택. 1043 passed.
- **[GARMIN-REPROCESS]** source_payloads → 활동 18건·웰니스 15건·메트릭 43건 재구축 완료. `device_name/gear_id=NULL` — activity_detail 미보존, Garmin IP 블록 해소 후 API 재호출 필요.
- **[BUG-GEMINI-429]** `ai_cache` 데이터 핑거프린트 기반 무효화 — 신규 활동·웰니스·날짜 변경 시에만 재호출 (ADR-011)
- **[BUG-6]** `daily_wellness` v0.3 컬럼명 전면 수정 (5컬럼 rename, source 필터 제거, `source_payloads` 스키마 맞춰 test_raw_payload.py 재작성, `upsert_payload` activity_id COALESCE 버그 수정)
- **[BUG-5]** `garmin_backfill.py` Layer 0 설계 정합성 수정 (`upsert_activity()` 전환, whitelist 필터, metric_store 라우팅)
- **[BUG-4]** `garmin_api_extensions.py` DDL 3컬럼 수정, `activity_exercise_sets` DDL 추가
- **[BUG-3]** activity_streams 소비자 5개 v0.3 typed columns 마이그레이션
- Garmin 인증 실패: ADR-010 A안 (local sync 스크립트 + VPS 업로드 API), 17 tests
- **[DB-RESET]** `activity_summaries` DDL 컬럼 누락 → DB DROP 재생성, Strava/Intervals 재동기화
- fix: strava/intervals sync_activities/sync_wellness undefined 버그 수정
- garminconnect 0.3.x 마이그레이션 (MIGRATION-01~04) — curl_cffi, tokenstore, MFA, 38 new tests
