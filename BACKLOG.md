# BACKLOG

## NOW

- **[PHASE-7]** UI Renewal 설계 문서 작성 진행 중 → `v0.3/data/phase-7-ui-renewal/BACKLOG.md` 참조

## BUGS

- **[BUG-INDOOR-RUN-TYPE]** Garmin `indoor_running`(16건, 2023-12~2025-02, 88 km)이 러닝으로 정규화되지 않아 TRIMP·분석·MCP 러닝 집계에서 제외됨. **코드 수정 완료(2026-09-26, `_RUNNING_TYPES`에 추가)** — 기존 DB 16건(`activity_type='indoor_running'`) 정정·재계산은 실 DB 작업(백필 런북과 함께)으로 남음.
- **[AUDIT-SERVICE-LAYER]** 웹 UI 각 뷰가 raw SQL 직접 작성 (40+곳). Phase 5 설계에서 요구한 `activity_service`, `metrics_loader`, `wellness_loader` 서비스 레이어 미구현. UI 재설계 시 함께 정리 필요.
- **[AUDIT-V-CANONICAL]** `views_report.py` 등 일부 뷰에서 `v_canonical_activities` 대신 `activity_summaries` 직접 쿼리 → 중복 활동 포함 위험. **(판단 필요)** UI 재설계 범위와 함께 결정.

## 미해결 확인 사항 (MIGRATION-04 §6)
- ~~[중간] curl_cffi ARM64 wheel 존재 여부~~ → 해결: OCI A1(aarch64)에서 이미지 빌드·Garmin 동기화 정상 (2026-09-27)
- [낮음] test_flask_routes.py garmin 라우트 포함 여부 — 테스트 커버리지

## NEXT

- **[SYNC-SOURCE-TOGGLE]** 토글·자동/v2 수동 필터는 구현됨. T1(자동 동기화가 실행마다 config 재로딩, 2026-10-08)로 재시작 없이 반영. 남은 구멍은 `ux-review-2026-09/DESIGN-SYNC-SOURCE-TOGGLE.md` G2~G6(v1 경로 가드, 끄면 cancelled, 레거시 `*_disabled` 마이그레이션, `/data/sync` 행 버튼) — 설계 40 S3/S4로 이관. 전체 보류 목록: `ux-review-2026-09/IMPL-PROGRESS.md` 「보류·인수인계」.

- **[MCP-REMOTE]** R1~R8 구현·배포 완료(ADR-034, 기본 `enabled=false`). **운영자 조치 남음**: CF Access `/mcp` 정책(Genspark 커스텀 헤더 지원 확인 후 Service Auth 또는 Bypass) + WAF/캐시 규칙 → `config.json`에 `mcp_remote.enabled=true` → 실제 클라이언트(`claude mcp add --transport http`, Genspark) 스모크. 완료 후 DONE으로 이동.

## 사용자 조치 필요 (Claude가 대신 할 수 없음)

- **[USER-MCP-ENABLE]** 원격 MCP 켜기: (1) Cloudflare Access에 `/mcp` 정책 추가 — Genspark가 커스텀 헤더 여러 개를 지원하면 Service Auth, 아니면 Bypass(앱 Bearer 토큰이 인증) (2) WAF·캐시 규칙(`/mcp` 캐시 제외, 속도 제한) (3) `config.json`에 `"mcp_remote": {"enabled": true}` 후 컨테이너 재시작 (4) 설정 > "외부 AI 연결" 카드에서 토큰 발급(브라우저 실사용 확인 겸) → `claude mcp add --transport http runpulse https://<host>/mcp --header "Authorization: Bearer rpmcp_..."` 및 Genspark 스모크.
- **[USER-CAL-FEED]** 캘린더 구독: Cloudflare Access에 `/feeds/cal/*` Bypass 추가 → 구글 캘린더에서 실제 구독·갱신 확인.
- **[USER-CONNECTOR-OAUTH]** claude.ai 커넥터 Google Drive·Notion·Strava·Tredict는 OAuth 인증 필요(claude.ai 커넥터 설정 또는 대화형 세션 `/mcp`). 인증 전까지 해당 연동 사용 불가.
- **[USER-PYTEST-MCP]** `pytest` MCP 서버가 `CONNECTION_CLOSED`로 연결 실패 — 설정·실행 명령 확인 필요.
- **[USER-DECISION]** `AUDIT-V-CANONICAL`(판단 필요), `SYNC-SOURCE-TOGGLE` G2~G6 착수 여부, Phase 7c(조정 수락 영속화) 방향.

## DONE (recent)
- **[MARATHON-LOG-LAPS]** 9/4·9/10·9/17 세션 랩을 일일 로그 및 W13·W14·W15 주간 로그에 반영(2026-10-08, 로그는 gitignore). 9/4는 랩 구분이 계획 3×2k와 불일치해 세트 해석 보류로 기재.
- **[MCP-CLIENT-VERIFY]** 실클라이언트(Claude Code 세션)에서 `mcp__runpulse__get_training_summary` 호출 성공(2026-10-08, 주별 요약·notable 정상 반환) — ADR-016 stdio 프레임 수정 검증 완료. 로컬 `.mcp.json`의 `sqlite`(default DB) 항목 정정은 로컬 설정이라 미수행.
- **[UI-S12-STORY]** 훈련 이야기(월·주) 구현(ADR-032). `/api/v1/library/story/<period>` + `story_service/period/stats` 3모듈, 프론트 `/library/story/[period]`(Svelte 5) 이전·다음·월/주 전환·강도 분포·대표 세션·마일스톤. 블록 스코프는 `NotImplemented`(계획 페이즈 날짜 매핑 미정) → 400.
- **[OPS-OCI-MIGRATION]** 서버를 AWS Lightsail(x86_64) → OCI 춘천 A1(aarch64, 4 OCPU/24GB)로 이전(2026-09-27 01:39 KST 전환, 다운타임 약 2분). DB 4개 integrity_check·테이블별 행 수 일치 확인. 컨테이너 포트는 127.0.0.1 바인딩(`docker-compose.override.yml`, git 제외), cloudflared는 token-file 방식. 같은 날 AI 기본 모델 종료(404) 대응으로 `config.json`의 `ai.gemini_model=gemini-flash-latest`, `ai.groq_model=openai/gpt-oss-120b` 설정(코드 기본값 `gemini-2.0-flash`/`llama-3.3-70b-versatile`은 둘 다 서비스 종료 — 코드 기본값 갱신은 미수행).
- **[BUG-CHAT-RULE-FALLBACK]** `chat_engine_rules.rule_based_response()`와 `briefing.py`의 클립보드 프롬프트 조립 함수(`build_briefing_prompt`/`build_chip_prompt`) 3곳이 전부 Phase 5 리라이트 때 고아가 된 `ai_context.build_context`/`format_context_text`/`format_activity_context`를 import — AI provider 미설정 시 마지막 안전망인 rule fallback이 ImportError로 죽고 있었음. 3개 함수를 현재 스키마 기준으로 재작성해 복원: `activity_summaries.distance_km`→`distance_m`(변환), 삭제된 `daily_fitness` 테이블→`metric_store`(`db_helpers.get_primary_metrics`), `calculate_weekly_score()`의 `data` 중첩 dict→top-level로 평탄화, `get_planned_workouts()`의 `week_start` 인자화 대응, `deep_analyze()`가 이제 `avg_pace`를 포맷된 문자열로 반환하는 것에 맞춰 `format_activity_context` 조정. 신규 테스트 21+7건(`test_ai_context.py`/`test_briefing.py`, `rule_based_response()` 실호출 회귀 테스트 포함). 1421 passed.
- **[MCP-TOKEN-OPT]** AI/MCP 도구 토큰 최적화(ADR-016). (1) 목록 응답을 `fields`+`rows` columnar로 통일·반올림·전NULL 컬럼 제거·compact JSON, (2) 62일 초과 구간 주별 롤업(180일 상한, 일요일 시작, 공백 주 `runs=0` 채움) + `get_training_summary` 신설(주별 볼륨·CTL/TSB·대회/퀄리티 세션 1회), (3) 호출 레시피 `tool_guide.USAGE_GUIDE`(MCP instructions) + `.claude/skills/runpulse-data`. 실측: 활동 목록 1년 ≈7,300→780 tok, 웰니스 30일 ≈1,300→380. MCP 서버 결함 3건 동봉 수정 — `default`(활동 0건) DB 하드코딩 → `RUNPULSE_USER_ID` 필수, 쓰기 가능 연결 → `mode=ro`, LSP식 Content-Length 프레임 → MCP 사양(줄바꿈 JSON). `workout_type_classified`를 `numeric_value`에서 읽어 `workout_type`이 한 번도 안 나오던 도구 버그 수정. `tools` 모듈 분리 유지(전부 300줄 이하). 1376 passed. **실제 MCP 클라이언트(Claude Code 등) 연결 검증은 미수행** — 서브프로세스 프로토콜 왕복만 확인.
- **[AI-TOOLS-LAPS]** 랩 기반 AI/MCP 도구 추가. `get_activity_laps`(랩별 페이스·심박·케이던스·파워·구간 유형), `compare_workout_sets`(세션 간 세트 페이스 비교 + 후반 드리프트) 신규. 출력은 키 반복 대신 `fields` 헤더 + 값 배열, 전부 NULL인 컬럼은 헤더에서 제거해 토큰 절감. `get_activity`/`get_activities_range` 응답에 `activity_id` 추가 — 없으면 상세·랩 도구를 호출할 방법이 없었음. 전체 14개 도구를 실 DB로 점검해 3건 확인: `get_activity`가 존재하지 않는 `calories` 컬럼 조회(활동 칼로리는 이미 `metric_store`에 1,374건 있어 `detail["metrics"]`로 반환됨 → 컬럼 제거), `get_weather`가 v0.2 테이블 `weather_data` 조회(→ `weather_cache` + 실제 컬럼명). `compare_periods`는 점검 스크립트의 인자 이름 오류였고 정상. 스트림 복구로 새로 들어온 심박 0(미측정) 행은 `_positive_int`로 NULL 처리(요약에 적용한 `sanitize_activity_core`와 동일 원칙). `tools.py` 705줄 → 선언/활동·랩 실행기/일별·기간 실행기 3개 모듈로 분리(전부 300줄 이하, 로직 변경 없음). 1306 passed.
- **[DATA-LAPS-EMPTY / DATA-STREAMS-EMPTY]** 랩은 `get_activity()` 응답에 없고 `/splits`에만 있어 `activity_laps`가 전 기간 0건이었음 → `get_activity_splits()` 호출 추가, `activity_splits` payload 저장, 랩 추출을 이 payload 기준으로 변경(ADR-015). 실제 응답 확인 결과 랩 필드명이 summary와 달라(`averageRunCadence`/`averagePower`/`intensityType`) 함께 수정 — 확인 없이 기존 이름을 썼다면 케이던스·파워가 전부 NULL이 됐을 것. skip 조건에 splits를 포함해 기존 활동도 다음 동기화에서 보충됨. 스트림은 bg_sync가 쓰는 `sync_activities` 래퍼가 `include_streams`를 전달하지 않아 2026-06-23 이후 0건이었고(→ `di`가 조용히 빈 결과), 증분 경로만 기본 True로 전환. 대량 초기 적재는 `sync_cli --streams`로 분리 유지. 1284 passed.
  - **남은 작업**: 과거 활동(9/4·9/10·9/17 인터벌 등)의 랩 보충은 해당 기간 date-range 동기화 필요. auto-sync는 2일 창이라 자동으로 채워지지 않음.
- **[DATA-FITNESS-GAP]** CTL/ATL/TSB가 "9/5 이후 없음"이 아니라 **2026-05 이후 값 자체가 0에 수렴한 무의미한 값**이었음(2026-09-05 CTL 0.4/ATL 0.0). 원인은 동기화 경로(`run_for_date_range`→`compute_for_dates`)가 활동별 TRIMP를 계산하지 않은 것 — 마지막 TRIMP(7/18)+윈도우 49일=9/5에서 생성 중단. 활동→primary→prefetch→일별 순서로 수정(ADR-014), `recompute_recent`/`recompute_all` 동일 결함 통합, `recompute_all`에 UI가 넘기던 `on_progress` 추가(기존 TypeError), 중복이 된 `src/sync/integration.py` 삭제. 백업(`running.db.bak-20260921-pre-trimp-backfill`) 후 2025-09-01~2026-09-21 백필 → 9/21 CTL 75.0/ATL 92.4/TSB -17.4/ACWR 1.23으로 정상화. 1280 passed.
- **[TEST-REALDB-RANGES]** `test_integration_realdb.py` 13건 실패 해소(1275 passed). 데이터 결함 수정: 심박 0(92행)·스트레스 -1(1행)·GPS 속도 글리치 30 m/s 초과(3행)는 저장 진입점 `sanitize_activity_core`/Garmin 스트레스 가드로 NULL 처리, Garmin 케이던스 2배 값(2023-10~2025-05, 66행)은 250 spm 초과 시 절반 정규화, ACWR은 계산기에 5.0 캡(ADR-013). 기존 행은 백업(`running.db.bak-20260921-pre-dq-fix`) 후 정정. 테스트 기준 조정: 소스 수 상한, pace 상한 1800, 수영 등 stride 제외, rtti 0~200, decoupling 음수 허용. 관찰(미수정): 같은 source 안 중복 그룹 25건(주로 Intervals 근력 훈련 이중 등록).
- **[DATA-WELLNESS-SLEEP-BB / DATA-WELLNESS-HRV-SPO2-SKIN]** Garmin wellness extractor가 실제 payload 구조와 불일치(`dailySleepDTO`, `hrvSummary.baseline`, `data[0].bodyBatteryValuesArray`)해 수면/바디배터리/HRV baseline이 NULL이던 문제 수정(테스트 fixture도 실제 구조로 교체). `daily_wellness`가 "NULL만 채움"이라 당일 초반 부분값(걸음수 9, RHR 46 등)에 고정되던 문제는 `upsert_daily_wellness(overwrite=True)`(Garmin 경로 한정)로 해결(ADR-012). 신규 metric 5종(`hrv_5min_high`, `min_respiration_sleep`, `sleep_avg_hr`, `sleep_body_battery_change`, `skin_temp_deviation`) 등록, 미사용 `sleep_*_score` 3종 제거. pansongit DB 백업(`running.db.bak-20260921-pre-wellness-reprocess`) 후 `_reprocess_wellness`로 1087일 재구축, payload 대비 불일치 0건. 신규 테스트 포함 관련 141 passed.
- **[BUG-AUTO-SYNC-USER-ID]** `auto_sync._trigger()` 스레드에 `set_current_user()` 미호출 → `create_job()`이 "default" DB에 job 생성 → BgSyncThread가 실제 유저 DB에서 job 못 찾음 → 즉시 종료. `_trigger()` 첫 줄에 `set_current_user(user_id)` 추가로 수정.
- **[BUG-CONSISTENCY-FP]** check_data_consistency.py 🔴 2건 수정: (1) `workout_label` metric_registry `meta` 카테고리 등록, (2) DDL 파서 정규식 `BOOLEAN` 타입 누락 → PASS 복원.
- **[AUTO-SYNC]** 자동 주기 동기화 구현: `src/web/auto_sync.py` daemon thread, `src/utils/sync_state.py` 타임스탬프 함수, `config.json.example` auto_sync 섹션, 동기화 탭 설정 UI (활성화/주기/범위) + POST `/sync/auto-sync-settings`. 1091 passed.
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
