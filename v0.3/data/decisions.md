# Architecture Decision Records (ADR)

## ADR-001: weather_cache UNIQUE 제약에서 ROUND() 제거
- **날짜**: 2026-04-03
- **맥락**: SQLite는 PRIMARY KEY / UNIQUE 제약조건에 표현식(함수 호출)을 허용하지 않음
- **결정**: UNIQUE(date, hour, latitude, longitude, source)로 단순화하고, 좌표 반올림은 INSERT 전 Python에서 수행
- **결과**: 모든 SQLite 버전에서 호환, 정밀도 관리를 애플리케이션 레이어로 이동

## ADR-002: 동적 인덱스 생성 (_safe_create_indexes)
- **날짜**: 2026-04-03
- **맥락**: v0.2 실 DB에 gear_id, source 등 신규 컬럼이 없어 정적 CREATE INDEX가 실패
- **결정**: PRAGMA table_info로 컬럼 존재 여부 확인 후 조건부 인덱스 생성
- **결과**: v0.2 → v0.3 무중단 마이그레이션 가능, 기존 데이터 보존

## ADR-003: metric_store UNIQUE 키 설계
- **날짜**: 2026-04-03
- **맥락**: 동일 메트릭에 대해 여러 provider가 값을 제공할 수 있음
- **결정**: UNIQUE(scope_type, scope_id, metric_name, provider) — provider별 하나의 값만 저장
- **결과**: 다중 소스 비교 가능, is_primary 플래그로 UI 표시값 결정

## ADR-004: SyncResult dataclass로 sync 결과 표준화
- **날짜**: 2026-04-03
- **맥락**: 각 소스 sync 함수가 서로 다른 형식으로 결과를 반환하여 orchestrator에서 통합 처리 어려움
- **결정**: SyncResult dataclass에 status, counts, errors, retry_after를 통합. merge()로 여러 결과 합산. to_sync_job_dict()로 DB 기록 표준화
- **결과**: orchestrator가 소스에 관계없이 동일한 인터페이스로 결과 처리

## ADR-005: payload_hash 기반 변경 감지로 skip-unchanged 구현
- **날짜**: 2026-04-03
- **맥락**: 매번 전체 payload를 DB에 쓰면 불필요한 I/O와 재처리 발생
- **결정**: raw_store.upsert_raw_payload()가 JSON 정렬 후 SHA-256 해시 비교. 해시 동일하면 False 반환 → 하위 처리 skip
- **결과**: 반복 sync 시 변경 없는 데이터 skip, DB 쓰기 최소화

## ADR-006: Strava start_date_local 우선 사용
- **날짜**: 2026-04-03
- **맥락**: Strava API가 start_date(UTC)와 start_date_local 둘 다 반환. extractor가 start_date만 사용하여 다른 소스와 시간대 불일치, dedup 매칭 실패
- **결정**: start_date_local 우선, start_date fallback
- **결과**: cross-source dedup 시간 비교 정확도 향상

## ADR-007: ranges 형식 [low, high] 리스트 통일
- **날짜**: 2026-04-03
- **맥락**: 설계서(보강 #7)는 ranges를 [low, high] 리스트로 정의했으나, 포팅 메트릭이 단일 숫자로 구현됨
- **결정**: 전체 32개 calculator의 ranges를 [low, high] 리스트 형식으로 통일
- **결과**: UI에서 범위 시각화(게이지, 색상 바) 구현 시 일관된 데이터 구조 보장

## ADR-008: category 체계 — 소스 vs RunPulse 분리
- **날짜**: 2026-04-03
- **맥락**: metric_registry의 소스 메트릭은 training_load, efficiency 등 일반 카테고리, RunPulse calculator는 rp_ 접두사 사용
- **결정**: 의도적 분리 유지. 소스 메트릭(garmin/strava/intervals)은 도메인별 카테고리, RunPulse 메트릭은 rp_ 접두사
- **결과**: UI에서 소스별/RunPulse별 필터링 가능, 이름 충돌 방지

## ADR-010: Garmin 동기화 방식 — 로컬 토큰 발급 + CF Service Token + VPS 데이터 sync (A안)
- **날짜**: 2026-04-25
- **맥락**: VPS(AWS) IP가 Garmin `diauth.garmin.com`에 의해 차단됨. 토큰 갱신 불가 → 1시간 이상 sync 또는 자동 sync 불가. 상세 조사: `v0.3/sync/MIGRATION-01-01-IP-BLOCK-RESEARCH.md`
- **결정**: 로컬 기기(Windows/Termux)에서 토큰 발급 → CF Service Token 인증으로 VPS API 호출 → VPS에서 bg_sync 실행
- **CF 우회 방식**: `X-Garmin-Sync-Key`(커스텀 API 키) 방식 기각 — CF Zero Trust가 앞단에서 차단. CF Service Token(`CF-Access-Client-Id` + `CF-Access-Client-Secret` 헤더)으로 정식 우회.
- **포기한 것**: 전체기간 sync, 백그라운드 자동 sync
- **보류**: B안(SSH 역방향 터널) — BACKLOG 등록 / C안(공식 Garmin API) — LATER 등록
- **결과**: 개인 용도 incremental sync(~30일) 범위에서는 동작. 사용자가 매 sync마다 로컬 스크립트 실행 필요.
- **토큰 경로 구현**: `_tokenstore_path()`는 `~/.garminconnect` 대신 프로젝트 로컬 경로를 사용.
  - `user_id` 없음: `{PROJECT_ROOT}/.garminconnect`
  - `user_id` 있음: `data/users/{user_id}/.garminconnect`
  - `tokenstore` 명시: 그 경로 그대로 사용 (존재 여부 무관)

## ADR-011: AI 캐시 무효화 — 데이터 핑거프린트 기반 (2026-05-08)
- **날짜**: 2026-05-08
- **맥락**: `_is_fresh()`가 sync job 실행 여부로 캐시 유효성을 판단 → sync 직후 대시보드 접속마다 Gemini API 재호출 → 429 rate limit 발생. 시간 기반(오전/오후/저녁) 자동 갱신도 불필요한 API 호출 유발.
- **결정**: 캐시 무효화를 의미 있는 데이터 변화에만 한정. 저장 시점의 데이터 상태(`MAX(activity_summaries.id) | MAX(daily_wellness.date) | today`)를 `data_fingerprint`로 캐시에 함께 저장. 조회 시 현재 상태와 비교하여 불일치하면 stale 처리.
- **무효화 조건**: (1) 신규 활동 추가, (2) 신규 웰니스 레코드, (3) 날짜 변경, (4) TTL 8h 초과, (5) 사용자 명시적 refresh(`?refresh_ai=1`)
- **제거**: sync job 완료 후 캐시 전체 삭제하던 `invalidate_after_sync()` 함수 제거.
- **결과**: sync가 실행돼도 실제 새 데이터가 없으면 캐시 재사용 → Gemini API 호출 최소화.
- **검증**: `grep -n "invalidate_after_sync" src/` → 0건

## ADR-009: Calculator 데이터 접근 정책 — CalcContext API 전용
- **날짜**: 2026-04-04
- **맥락**: MetricCalculator 내부에서 `ctx.conn.execute()`로 raw SQL을 직접 실행하면, 스키마 변경 시 모든 calculator를 수정해야 하고, MockCalcContext로 단위 테스트가 불가능하며, A/B 테스트 시 입력 데이터를 통제할 수 없음. 메트릭 공식은 지속적으로 변경·확장될 예정이므로 calculator의 순수 함수화가 필수.
- **결정**: Calculator는 반드시 CalcContext API(13개 메서드)만 사용하여 데이터에 접근. `ctx.conn.execute()` 직접 호출 금지. 필요한 쿼리 패턴이 없으면 CalcContext에 새 API를 추가.
- **적용 범위**:
  - Level 1 (필수): 단일 scope metric/wellness → `get_metric()`, `get_wellness()` 등
  - Level 2 (필수): 히스토리 조회 → `get_daily_metric_series()`, `get_activities_in_range()`, `get_activity_metric_series()`, `get_wellness_series()`
- **신규 API (이 정책을 위해 추가됨)**:
  - `get_activity_metric_series(name, days, activity_type?, include_json?)` — activity-scope metric 시계열 + activity_type 필터
  - `get_wellness_series(days, fields?)` — daily_wellness 히스토리
  - `get_activity_metric_text(activity_id, name)` — activity-scope text_value 조회
- **결과**: 32개 calculator 전부 CalcContext API 전용으로 전환 완료. `src/metrics/*.py` 내 `ctx.conn.execute` 잔여 0건. Calculator가 순수 함수로 동작하여 Mock 테스트, A/B 테스트, 스키마 변경 시 영향 최소화.
- **검증**: `grep -rc "ctx.conn.execute" src/metrics/*.py` → 0

## ADR-012: daily_wellness merge 정책 — Garmin은 최신 non-null로 갱신 (2026-09-21)
- **날짜**: 2026-09-21
- **맥락**: `upsert_daily_wellness()`가 "기존 NULL인 필드만 채움"이라 하루 중 첫 동기화 값이 고정됨. Garmin은 하루에 여러 번 동기화되어 첫 값이 부분 하루치(걸음수 9, 활동칼로리 0, 스트레스 14, RHR 46)로 굳고, 이후 최종값(34,818보, 1,622kcal, 42, RHR 42)이 반영되지 않았음. 재처리(`reprocess`)도 같은 함수를 써서 교정 불가. 함께 발견: Garmin extractor가 실제 payload 구조(`dailySleepDTO`, `baseline.*`, `data[0].bodyBatteryValuesArray`)와 달라 수면/바디배터리/HRV baseline이 NULL이었음(2026-05-08 Intervals 동기화 종료 이후).
- **결정**: `upsert_daily_wellness(..., overwrite=False)` 옵션 추가. Garmin 경로(`garmin_wellness_sync`, `reprocess`의 garmin 소스)는 `overwrite=True`로 새 non-null 값이 기존 값을 갱신. 기본값(Intervals 등)은 기존대로 NULL만 채움. 새 값이 NULL이면 기존 값을 유지.
- **`resting_hr` 출처**: `wellness_user_summary.restingHeartRate`(일 최종값) 우선, 없으면 `wellness_sleep.restingHeartRate`. `hrvSummary.restingHeartRate`는 실제 payload에 없음. `hrv_last_night`는 `lastNightAvg`만 사용(`lastNight5MinHigh` fallback 제거).
- **저장 위치**: 컬럼 추가 없이 metric_store 사용. 신규 metric: `hrv_5min_high`, `min_respiration_sleep`, `sleep_avg_hr`, `sleep_body_battery_change`, `skin_temp_deviation`. 실제 payload에 없는 `sleep_deep_score`/`sleep_rem_score`/`sleep_recovery_score`는 제거.
- **결과**: source_payloads에서 API 호출 없이 재구축 가능(`reprocess_all(conn, source="garmin")`).
- **검증**: `tests/test_garmin_extractor.py`, `tests/test_garmin_wellness_sync.py::test_resync_updates_partial_day_values`, `tests/test_reprocess.py::test_garmin_reprocess_corrects_stale_partial_day_row`

## ADR-013: 활동 데이터 품질 가드 — 저장 진입점에서 미측정/글리치 값을 NULL 처리 (2026-09-21)
- **날짜**: 2026-09-21
- **맥락**: 실DB 범위 검증 13건 실패. 원인은 (1) Garmin이 센서 미측정을 0(심박)·-1(스트레스)로 반환, (2) GPS 글리치 최대속도(30~103 m/s), (3) 2023-10~2025-05 Garmin 러닝 케이던스가 양발 합산으로 약 2배(300~420 spm), (4) ACWR이 CTL 극소 구간에서 5를 초과, (5) 검증 기준이 소스 2종·러닝 전용·`%` 단위 가정으로 낡음.
- **결정**: `sanitize_activity_core()`(`src/sync/_helpers.py`)를 `save_activity_core()` 진입점에 적용해 모든 소스에 공통으로 avg/max HR 0 → NULL, `max_speed_ms` > 30 → NULL. 소스 고유 문제인 케이던스는 Garmin extractor의 `_running_cadence()`에서 250 spm 초과 시 절반으로 정규화(요약·랩). Garmin `avgStressLevel` < 0 → 저장 안 함. ACWR은 계산기 `ranges` 상한과 같은 5.0으로 캡(RTTI 200 캡과 동일 패턴).
- **포기한 것**: 원본 payload 자체 수정(원본은 그대로 보존, 정규화는 파생 컬럼에만 적용).
- **검증 기준 조정**: pace 상한 900 → 1800 s/km(걷기 수준 러닝 존재), group 내 source 수는 DB의 전체 source 수 이하, stride는 러닝/걷기 활동만, rtti 0~200, aerobic_decoupling_rp -50~100.
- **결과**: 기존 행 정정(HR 0 92행, stress 1행, cadence 66행, max_speed 3행, ACWR 3행) 후 `test_integration_realdb` 전부 통과.
- **검증**: `tests/test_activity_core_sanitize.py`, `tests/test_garmin_extractor.py::TestGarminDataQualityGuards`, `tests/test_integration_realdb.py`
- **정정 (2026-09-21, ADR-014)**: ACWR 5.39와 RTTI 200의 실제 원인은 '데이터 시작 / 휴식 후 복귀'가 아니라 TRIMP 미계산으로 CTL이 0에 수렴한 것이었다. 백필 후 최근 구간은 ACWR 0.87~1.56, RTTI 87~156으로 정상화됐고 남은 극단값은 백필 경계(2025-05, 2025-09)의 EMA warm-up 구간뿐이다. 캡 자체는 0 division 방어 가드로 유지한다.

## ADR-014: 메트릭 계산 순서 — 활동 → primary 확정 → prefetch → 일별 (2026-09-21)
- **날짜**: 2026-09-21
- **맥락**: CTL/ATL/TSB가 2026-09-05 이후 생성되지 않았고, 그 전에도 값이 0에 수렴해 무의미했다(2026-09-05 CTL 0.4 / ATL 0.0). 원인은 동기화 경로가 쓰는 `run_for_date_range` → `compute_for_dates`가 `run_daily_metrics`만 호출해 **활동별 TRIMP를 계산하지 않은 것**. PMC는 TRIMP 합계를 입력으로 쓰므로 마지막 TRIMP(2026-07-18) + 윈도우 49일 = 2026-09-05를 끝으로 빈 결과를 반환했다. `run_for_date`(대시보드 단일 날짜 경로)만 활동+일별을 함께 계산하고 있었다.
- **결정**: `_compute_activity_metrics_for_dates()`를 추가하고 `compute_for_dates`·`_recompute_dates`가 **활동 계산 → scope별 primary 확정 → prefetch → 일별** 순서로 실행한다. bg_sync와 sync.py는 모두 `run_for_date_range`를 거치므로 호출부 변경 없이 해결된다.
- **함정 (반드시 유지)**: `_prefetch_daily_trimp_sums()`는 `is_primary = 1`인 행만 읽고 루프 **이전에** 한 번만 실행된다. 활동 메트릭을 prefetch 이후나 루프 안에서 계산하면 맵이 낡아 PMC가 부하 0을 읽고 CTL이 아예 생성되지 않는다. `resolve_for_scope()`로 primary까지 확정한 뒤 prefetch해야 한다. 회귀 테스트가 이 순서를 검증한다.
- **함께 수정**: `recompute_recent`/`recompute_all`도 같은 순서 결함이 있어 `_recompute_dates()`로 통합. `recompute_all`에 UI(`views_settings_metrics.py`)가 이미 넘기던 `on_progress` 파라미터 추가(기존에는 TypeError). 활동 id를 들고 다니지 않는 `SyncResult` 때문에 연결 불가능했고 이제 중복이 된 `src/sync/integration.py` 삭제.
- **결과**: 2025-09-01~2026-09-21 백필 후 2026-09-21 기준 CTL 75.0 / ATL 92.4 / TSB -17.4 / ACWR 1.23. 일별 runpulse 메트릭 24종 중 23종이 당일까지 채워짐(`di`는 스트림 의존이라 별도 이슈).
- **검증**: `tests/test_round2.py::TestComputeForDatesRunsActivityMetrics`, `::TestRecomputeAll`

## ADR-015: Garmin 랩은 /splits 엔드포인트, 스트림은 증분 동기화에서만 기본 수집 (2026-09-21)
- **날짜**: 2026-09-21
- **맥락**: `activity_laps`가 전 기간 0건이었다(기존 훈련 로그의 세트 분석은 Tredict 출처). `get_activity()`(activity detail) 응답에는 `lapDTOs`가 없고 타입별 집계인 `splitSummaries` 4개만 있어 `extract_activity_laps(detail)`이 항상 빈 리스트를 반환했다. `activity_streams`도 2026-06-23 이후 0건인데, bg_sync가 쓰는 `sync_activities` 래퍼가 `include_streams`를 전달하지 않아 항상 False였다. 그 결과 스트림 의존 calculator인 `di`가 2025-08-31 이후 조용히 빈 결과를 반환했다.
- **결정(랩)**: `get_activity_splits()`(`/splits`)를 별도 호출해 `activity_splits` entity_type으로 저장하고 랩은 이 payload에서 추출한다. 실제 응답 확인 결과 `{"activityId", "lapDTOs"[], "eventDTOs"[]}` 구조이며, **랩 필드명이 activity summary와 다르다**: `averageRunCadence`(≠ `averageRunningCadenceInStepsPerMinute`), `averagePower`(≠ `avgPower`), `intensityType`(≠ `lapTrigger`). 확인하지 않고 기존 필드명을 재사용했다면 랩이 저장돼도 케이던스·파워가 전부 NULL이 됐을 것이다.
- **결정(skip 조건)**: 기존 `summary + detail` 존재 시 skip을 `summary + detail + splits`로 확장. detail만 있던 기존 활동도 다음 동기화에서 랩을 보충한다. `/splits`는 랩이 없어도 `activityId`를 담은 dict를 반환하므로 재조회 루프는 생기지 않는다.
- **결정(스트림)**: `sync_activities` 래퍼의 `include_streams` 기본값을 True로 두되 **증분 경로(bg_sync/auto-sync, `src/sync.py`)에만 적용**한다. 활동당 API 1회와 약 2,000행이 추가되므로(월 15건 기준 약 30,000행·2 MB) 증분에서는 수용 가능하지만, 1,400건 규모 초기 적재에서는 약 280만 행이 된다. `sync_cli`는 `garmin_activity_sync.sync`를 직접 호출하며 `--streams` 옵션으로 별도 제어하므로 대량 적재는 영향받지 않는다.
- **결과**: 활동당 Garmin API 호출이 1회(detail)에서 3회(detail + splits + streams)로 늘어난다. rate limiter와 429 백오프가 기존대로 적용된다. 과거 활동의 랩·스트림 보충은 해당 기간 date-range 동기화가 필요하다.
- **검증**: `tests/test_garmin_activity_sync.py::TestGarminLaps`

## ADR-016: AI/MCP 도구 응답 — columnar 압축, 주별 롤업, 읽기 전용 stdio MCP (2026-09-21)
- **날짜**: 2026-09-21
- **맥락**: MCP는 호출마다 응답이 컨텍스트에 쌓인다. 실측 시 활동 목록 1년치가 21.9KB(≈7,300 tok), 웰니스 30일이 3.9KB였고 대부분이 행마다 반복되는 키와 `6.333333333333333` 같은 자릿수였다. 또한 "최근 블록 어땠어" 한 질문에 활동 목록·피트니스·분류를 3~4회 호출해야 했다.
- **결정(형식)**: 목록형 응답은 `{"fields":[...],"rows":[[...]]}`로 통일(`src/ai/tool_format.py`). 전 행 NULL 컬럼은 헤더째 제거, 값은 필요한 자릿수로 반올림(`84.0`→`84`), JSON은 공백 없는 separators. 랩 도구도 같은 형식(`laps`→`rows`).
- **결정(롤업)**: 기간이 62일을 넘으면 일별 대신 주별로 자동 집계(`granularity=auto`). `day`를 명시해도 180일 초과는 주별로 전환하고 `note`로 알린다 — 응답 크기에 상한을 두는 것이 목적. 주 시작은 **일요일** 기본(마라톤 플랜 주차가 일요일 시작), `week_start:"mon"`으로 변경 가능. 주별 페이스는 총시간/총거리, 심박은 시간 가중 평균(평균의 평균은 짧은 조깅에 왜곡됨). 활동이 없던 주도 `runs=0` 행으로 채운다(훈련 단절이 표에서 사라지지 않도록).
- **결정(요약 도구)**: `get_training_summary`를 신설해 주별 볼륨 + 주말 CTL/ATL/TSB + 대회·퀄리티 세션(id 포함)을 1회로 제공. 분류기가 `easy`로 두는 크루즈·짧은 인터벌은 ACTIVE 랩이 있으면 `notable`에 포함하고 `sets` 컬럼으로 표시한다.
- **결정(MCP)**: (1) 유저 DB는 `RUNPULSE_USER_ID` 필수 — 기존에는 활동 0건인 `default` DB를 하드코딩해 조용히 빈 결과를 돌려줬다. (2) DB는 `mode=ro`로 연다. (3) stdio 프레임을 MCP 사양대로 줄바꿈 구분 JSON으로 수정(기존은 LSP식 Content-Length 헤더). (4) 호출 레시피를 `tool_guide.USAGE_GUIDE`로 두고 initialize `instructions`로 전달, 상세는 `.claude/skills/runpulse-data/SKILL.md`. 원격(HTTP) 노출은 범위 밖 → BACKLOG `MCP-REMOTE`.
- **부수 수정**: `workout_type_classified`는 `text_value`에 저장되는데 도구가 `numeric_value`를 읽어 `get_activity.workout_type`이 한 번도 나오지 않았고 `get_race_history`는 이름 키워드로만 매칭됐다.
- **결과**: 활동 목록 1년 ≈7,300→780 tok, 웰니스 30일 ≈1,300→380, 피트니스 30일 ≈830→330. 도구 선언은 ≈1,470→1,580 tok(도구 1개 추가, 기간 도구 4개에 `granularity` 추가 후 설명 축약). 응답 형태가 바뀌었으므로 소비자는 `fields` 헤더를 읽어야 한다 — 앱 내 AI 채팅(`chat_engine_providers`)은 LLM이 직접 읽으므로 코드 변경 없음.
- **검증**: `tests/test_ai_tool_format.py`, `test_ai_tools_compact.py`, `test_ai_tool_guide.py`(선언 5,000자·가이드 1,400자 상한, 스킬/가이드가 실제 도구명과 일치), `test_mcp_server.py`

## ADR-017: 활동 컨텍스트 Coach — 스레드 context + 활동 요약 프롬프트 주입 (2026-10-02)
- **맥락**: Library 활동 상세의 "코치에게 묻기"가 일반 `/coach` 링크였다. 설계(20-library-activities)는 활동 근거 카드와 유형별 추천 질문이 붙은 새 대화를 요구한다.
- **결정**: (1) `chat_threads.context_kind/ref`(기존 컬럼)에 `activity/{id}`를 저장하고 `get_thread`가 노출한다. (2) 근거 값·추천 질문은 `/coach/activity-context`가 서버에서 계산한다(프론트 계산 금지). (3) LLM 자유 입력 프롬프트에만 활동 한 줄 요약을 prepend하고 칩 프롬프트·규칙 폴백은 변경하지 않는다. (4) 새 route `/coach/new?activity=`, 스레드 ← 는 활동으로 복귀.
- **검증**: `tests/test_coach_activity_context.py`, `tests/test_api_coach.py`, `frontend/tests/activityEvidence.test.mjs`.


## ADR-018: 메트릭 표시 이름 SSOT — src/utils/metric_labels.py (2026-10-03)
- **맥락**: Library 메트릭 브라우저가 한글명을 프론트 하드코딩(`LABELS`)과 registry `description` 폴백으로 얻어 영문 제목·"(parent: …)" 노출·화면별 불일치가 있었다. "한글명이 없는 지표가 사라지는가?"를 검토한 결과 이름은 노출 필터가 아니며(필터는 scope=daily·기준일 값 존재·`(parent:` 구성요소 숨김뿐), 지표가 안 보이는 실제 원인은 기준일 `MAX(scope_id)` 선택과 wellness 저장 12개 지표 미노출이다(별도 BUG 후보, 사용자 지시 필요).
- **결정**: (1) `METRIC_LABELS: dict[slug, MetricLabel(name_ko, abbr)]`를 registry canonical name 키로 둔다. API(list/trend/explain)와 사전 문서는 여기서 파생한다. (2) 일별 84개는 명시 등록을 테스트로 강제하고, 그 외 scope는 `label_for` 폴백(description에서 `(parent:)` 제거 → canonical name)을 쓴다. 폴백은 노출 필터로 쓰지 않는다. (3) 계산기 `display_name`은 알고리즘 이름일 뿐 화면 표시에 쓰지 않는다. (4) CIRS는 "부상 위험", CRS는 "복합 준비도"(UTRS "훈련 준비도"와 충돌 회피).
- **기각**: `MetricDef` 필드 추가(registry 522줄 비대), 계산기 `display_name`(daily 84개 중 37개만 커버, 계산기 1:다 지표), DB 테이블.
- **검증**: `tests/test_metric_labels.py`, `tests/test_metrics_browser_service.py::test_label_registry_does_not_affect_which_metrics_are_listed`

## ADR-019: 메트릭 브라우저 8분류(의도 기준) — src/services/metric_browse_groups.py (2026-10-04)
- **맥락**: 백엔드 `_CATEGORY_LABELS` 16개(레지스트리 category)는 사용자의 "무엇을 보러 왔나"와 맞지 않고 구성요소 지표가 섞여 노출됐다. 설계 `DESIGN-S4S5-IMPL.md` §3.
- **결정**: (1) slug→(group, tier) 매핑을 `metric_browse_groups._SPEC`에 둔다(today/load/race/ability/sleep/vitals/hr_ref/env). 레지스트리 category와 별개 개념이며 `SEMANTIC_GROUPS`와도 다르다. (2) tier hidden(구성요소)은 목록에서 제외, 미등록 slug는 (other, detail). (3) 그룹 내 정렬은 salience: 최신 → 경고 등급(poor/caution) → |z|(d−28..d−1, n<7이면 null) → primary → registry 순. (4) 전체 보기는 섹션당 4카드(환경·심박 기준값 2), "모두 보기 ›"로 카테고리 필터 전환. 모바일 카드 높이 축소로 390px 스크롤 ≈2,560px. (5) 레거시 `?category=`는 `normalizeCategory`로 매핑. 열린 결정 기본값: 체중·걸음·칼로리는 vitals, BB는 "최고" 라벨, headline 추가.
- **검증**: `tests/test_metric_browse_groups.py`, `tests/test_metrics_browser_service.py`, `frontend/tests/metricGroups.test.mjs`, Playwright `pw/metric_groups.mjs`(실DB 사본).

## ADR-020: 웰니스 일 상세 /:date — 서버 등급·z 근거 규칙 (2026-10-04)
- **맥락**: 웰니스 화면이 날짜별 URL이 없고, 프론트가 임계값을 들고 "좋음/나쁨"을 판단할 위험이 있었다.
- **결정**: (1) `/library/wellness/:date`가 정본이고 `/library/wellness`·`?date=`는 redirect. 잘못된 형식은 400, 미래는 오늘로 보정. (2) 등급은 `metrics.bands.grade` SSOT, 프론트 임계값 상수 없음. (3) 기준선 창은 당일 제외(HRV·안정 심박 p25/p75=28일, 평균=7일, 수면 평균=30일), 표본 n<7이면 키 생략("기준선 수집 중 n/7"). (4) 헤드라인 근거는 28일 평균·표준편차 z 기준 |z|≥0.5 중 상위 2개(`wellness_day.Z_MIN`). (5) 날짜 이동은 history replace. (6) 30일 추세는 비동기 스트리밍.
- **검증**: `tests/test_wellness_day.py`, `tests/test_api_library.py`, `frontend/tests/wellnessDay.test.mjs`, Playwright `pw/s5_wellness.mjs`(실 DB 사본).

## ADR-021: 소스 비교 매트릭스 — 서버 행 정의·쌍 요약, 척도 비교(scale) 분리 (2026-10-05)
- **맥락**: `/library/providers`가 "같은 의미의 지표를 소스끼리 비교"한다는 기준 없이 값을 나열했고, 정의가 다른 지표(훈련 부하 AU·VO2max/VDOT)를 %로 비교해 오해를 만들 수 있었다.
- **결정**: (1) 행 정의 SSOT는 `src/utils/provider_matrix_rows.py`(8행; kind=pair_activity|pair_daily|profile|definition, compare=same|scale). 활동 상세 탭의 `SEMANTIC_GROUPS`와 분리한다. (2) 임계값(차이 15%, 표본 n<3 "표본 부족", 30일 stale, IQR×1.5 이상치)은 서버에만 둔다(`provider_matrix_collect.py`). (3) `same`은 중앙값 % 차이, `scale`은 비율 ×r로 보여 주고 경고하지 않는다. (4) 쌍 상세 `/library/providers/:group`(`group`=행 key)은 점도표+활동 목록, 이상치는 속 빈 점. (5) 메트릭 상세는 `compare_group`이 있으면 "소스 비교" 링크를 노출한다. (6) 기간은 `?days=`(4주 기본은 생략), chip은 history replace.
- **확정(U17a)**: §8-1 훈련 부하 scale ×r·경고 없음, §8-2 EF definition 행, §8-3 단일 소스 행 접힘 목록, §8-4 U9 `SEMANTIC_GROUPS`의 `("training_load_score","intervals")`→`("training_load","intervals")`.
- **검증**: `tests/test_provider_matrix_service.py`, `tests/test_api_library.py`, `frontend/tests/providerMatrix.test.mjs`, Playwright `pw/s6_providers.mjs`(실 DB 사본, 에러 없음).

## ADR-022: 활동 피드백(RPE·통증·메모)과 동기화 작업 원장 v2 (2026-10-05)
- **맥락**: 활동 주관 데이터 저장소가 없었고, 소스 403/401이 원장에 `completed`로 남아 사용자에게 오류가 보이지 않았다.
- **결정**: (1) running.db v25에 `activity_feedback(activity_id PK, rpe, pain_sites, note …)` 추가, 통증 부위 슬러그는 서비스 상수 `PAIN_SITES`. (2) 원장 SSOT는 `sync_jobs.db`, running.db `sync_jobs`는 동결. `error_code`·`http_status`·`source_path(manual|bg|auto|cli)` 열을 연결 시 멱등 추가하고 상태 `failed`를 신설. (3) 오류 코드 SSOT는 `src/sync/sync_errors.py`, 소스 전체 실패는 `SyncSourceError`로 올려 모든 경로가 `failed`로 기록. (4) 원장 쓰기는 `src/sync/ledger.py`와 bg_sync만 한다. (5) 과거 행은 소급 수정하지 않고 문자열 규칙을 폴백으로 둔다. (6) 상태명은 error-auth / error-access / error-upstream.
- **검증**: `tests/test_activity_feedback_service.py`, `tests/test_api_activity_feedback.py`, `tests/test_sync_errors.py`, `tests/test_strava_403_ledger.py`, `tests/test_sync_ledger_paths.py`, `tests/test_sync_jobs_schema.py`, `tests/test_sync_state_service.py`.

## ADR-023: 사용자 UI 설정 저장소 — DB(사용자) / config(운영자) 분리 (2026-10-05)
- **맥락**: v1/v2 UI 기본값 선택을 기기·사용자 단위로 저장하고, 운영자가 재배포 없이 전역 롤백할 수단이 필요하다.
- **결정**: running.db v25 `user_settings(key PK, value_json, updated_at)`에 화이트리스트 키(`ui_default`: v1|v2)만 저장한다. 해석 순서는 사용자 값 → `config.json`의 `ui_default_global` → `v1`. API는 `GET/PATCH /api/v1/me/preferences`. `/` 분기 연결은 G0 작업.
- **검증**: `tests/test_user_settings_service.py`.

## ADR-024: 심박 결측 러닝의 TRIMP 추정 (2026-10-07)
- 배경: 2023-10~2025-02는 러닝 대부분에 avg_hr가 없어 TRIMP가 비고 CTL이 과소 계산됨(DATA-CTL-WARMUP).
- 결정: `TRIMPEstCalculator`(name=`trimp_est`, produces=`trimp`, provider=`runpulse:rule_trimp_est`, 우선순위 30). 시기가 가까운 심박 보유 러닝 ≤60건(≥8건)으로 `avg_hr = a + b·speed` 회귀 → 추정 심박을 측정 TRIMP와 같은 Banister 식에 투입. 기울기 ≤0이면 평균 심박, 표본 부족이면 결과 없음. confidence 0.4/0.25.
- 이중 계산 방지: 측정 TRIMP(formula_v1, 우선순위 20)가 있으면 항상 그쪽이 primary. PMC·합산 소비자는 `trimp is_primary=1`만 보므로 변경 없음.
- 엔진은 이름 키(`name_to_calc`)로 정렬하므로 calculator `name`은 고유하게 두고 `produces`로 trimp를 지정.
- 한계: 심박 없이 페이스만으로 추정하므로 인터벌·언덕 활동은 과소 추정 가능(낮은 confidence로 표시). 실 DB 재계산은 별도 승인 후 수행.

## ADR-025: 수동 증분 동기화 트리거 `POST /api/v1/data/sync` (2026-10-07)
- 배경: v2 헤더 Pill/SyncPanel이 읽기 전용이라 v1 `/sync`로 이동해야 했음. v1 `/trigger-sync-bg`의 판정 로직은 라우트에 인라인.
- 결정: 판정·시작을 `src/services/sync_trigger_service.py`로 추출해 v1/v2가 공유. 판정 순서 not_connected → disabled → running → cooldown → rate_limited. 응답 202/409/422/429(+Retry-After)/400/503. `api_error(details=)` 추가(하위 호환).
- 동시성: `bg_sync._threads` 키를 `(user_id, service)`로, `start_job`의 생존 검사+등록을 락 안에서 원자화(sentinel).
- D1–D11 추천안과 사유는 `phase-7-ui-renewal/ux-review-2026-09/40-v2-unimplemented/sync-trigger-design.md` §11.
- 한계: `sync_state.json`은 v1 SSE가 원장 단독 기록으로 바뀔 때까지 병행 확인(D6). `bg_sync.py` 520줄 분리는 별도 과제(D8).

## ADR-026: Data 소스 연결/테스트/해제 API (2026-10-07)
- 결정: `POST /data/sources/:p/{connect,test,disconnect}`. 서비스 `data_connect_service`.
  - 키 방식(Intervals·Runalyze): 저장 → 연결 확인 → 실패 시 이전 값 복원(롤백). 응답에 키 값을 싣지 않는다.
  - Strava: client_id/secret이 저장돼 있어야 하며, 기존 OAuth(`/connect/strava/oauth-start`)로 `redirect_url`을 돌려준다.
  - Garmin: v2에서는 미지원(이메일/비밀번호 토큰스토어 흐름) → 기존 `/connect/garmin` 링크 안내.
  - 해제: 자격 증명만 지운다(`keep_data:true` 필수). 데이터 삭제 해제는 400.
- OAuth `return_to`: 허용목록(`/v2/data/sources/`, `/v2/welcome`)만 통과, `state` 파라미터로 전달해 콜백에서 재검증(오픈 리다이렉트 방지).
- 사유: 데이터 삭제 해제는 소스별 cascade 삭제 헬퍼가 없어 위험이 커서 보류(후속). Garmin은 인증 흐름 재작성이 별도 작업.

## ADR-027: 러너 기준값 저장 키와 단일 읽기 진입점 (2026-10-08)
- 결정: 기준값은 `config.profile.overrides`(직접 입력)와 `config.profile.source_choice`(self|device|manual)에 저장하고, 존·플랜 엔진은 `profile_service.effective_value()`만 읽는다. 옛 키(`user.max_hr`, `threshold_pace_sec_km`/`threshold_pace`, `weekly_distance_target`)는 직접 입력으로 취급하는 폴백.
- 사유: 같은 값이 키 이름 3종으로 흩어져 있어(`threshold_pace` vs `_sec_km`) 화면별 불일치가 났다. 선택값이 없을 때의 사용값은 직접 입력 → 자체 추정 → 기기 순(사용자가 명시한 값이 가장 우선, 기기 값은 사용자가 고르지 않는 한 보조).
- 한계: conn 없는 호출은 자체·기기 선택을 풀지 못한다(S8b에서 엔진에 conn 전달).

## ADR-028: 재계산 작업은 sync 원장에 `service='recompute'`로 기록 (2026-10-08)
- 결정: 재계산 작업을 새 테이블 없이 `sync_jobs`(작업 원장)에 `service='recompute'`로 저장하고, 전후 비교 결과용 `result_json` 컬럼 1개만 추가한다(ledger 23컬럼). 진행률은 `completed_days/total_days`, 상태는 `pending/running/completed/failed`를 API에서 `queued/running/done/failed`로 변환한다. 동시에 1건만(409 `RECOMPUTE_RUNNING`).
- 사유: 원장에 이미 상태·진행률·재시작 시 stale 정리·사용자별 DB가 있어 별도 테이블은 중복이다. 추천안(원장 재사용)을 택한 이유는 새 스키마·정리 로직을 만들지 않고도 같은 폴링 규약을 쓸 수 있어서다.
- 범위: `from` 범위는 엔진이 `days`만 지원하므로 오늘-from+1일로 환산. 값 변경 미리보기의 영향 일수는 hrmax/lthr/resting_hr 변경일 때만 계산(주간 목표·역치 페이스는 재계산 불필요).
- `planner_rules.get_paces_from_vdot(vdot, config, conn)`이 conn을 받아 threshold_pace의 자체/기기/직접 선택을 반영한다(`generate_weekly_plan` 경로). 롱런 페이스용 `planner_schedule._long_pace_fn`도 VDOT가 없을 때 `load_config()`(요청 사용자)와 conn으로 같은 값을 쓴다. 옛 `GET /recompute-metrics`(부작용 GET)는 새 `POST /data/recompute`로 대체 예정이며 v2 UI는 쓰지 않는다.

## ADR-029: 내보내기는 빠른 CSV 스트림 + 아카이브 작업(원장 `service='export'`) (2026-10-08)
- 결정: 활동·웰니스·부하 CSV는 요청 즉시 파일로 응답하고(UTF-8 BOM), 전체 아카이브(zip)만 `sync_jobs`에 `service='export'`로 기록하는 작업으로 만든다. 파일은 `data/users/<uid>/exports/<job>.zip`, 7일 뒤 만료(다운로드 410). 동시 1건(409 `EXPORT_RUNNING`).
- 사유: CSV는 수초 안에 끝나 작업 원장이 불필요하고, 아카이브만 원본 payload 때문에 오래 걸릴 수 있다. 원장 재사용(ADR-028)으로 새 테이블 없이 이력·상태를 얻는다. BOM은 Excel 한글 깨짐 방지.
- 활동 CSV는 매칭 그룹당 1행(소스 우선순위 garmin>strava>intervals>runalyze)에 사람용(h:mm:ss)·기계용(초) 열과 소스별 원값 열을 함께 낸다.
- 가져오기(F-DATA-08)는 후속 슬라이스.
