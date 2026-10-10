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

## ADR-030: AI 설정은 config(키·제공자)와 coach_consent(범위)를 한 PATCH로 동기화, 키는 응답에 싣지 않음 (2026-10-08)
- 결정: `GET/PATCH /data/settings/ai`, `POST /data/settings/ai/test`. 제공자·키는 `config["ai"]`에, 메모 제외·폴백은 `coach_consent`에 쓰되 PATCH 한 번에 둘을 맞춘다. 응답은 키 값을 절대 내지 않고 `key_state(set/missing/invalid)`와 마스크(끝 4자리)만 낸다. `invalid`는 저장된 테스트 결과가 아니라 건강 상태의 마지막 401에서 유도한다.
- 사유: 두 저장소가 따로 갱신되면 제공자 변경과 동의 상태가 어긋난다. 별도 테스트 결과 저장은 만료·불일치 관리가 필요해 건강 상태 재사용이 단순하다.
- 범위: 설계서의 `activities_days`·`gps` 스위치는 백엔드에 대응 항목이 없어 만들지 않았다. `scope_catalog()`의 고정 항목은 읽기 전용 고지로, 사용자가 바꿀 수 있는 것은 체크인 메모(`exclude_notes`)뿐이다.
- 외부 AI(프롬프트 복사·MCP 도구 목록) 섹션은 MCP-REMOTE 작업과 함께 후속.


## ADR-031: 가져오기 미리보기는 DB 사본에서 실제 임포터를 돌려 계산, 작업은 원장 `service='import'` (2026-10-08)
- 결정: `POST /data/import/preview`는 업로드를 임시 폴더에 저장하고 `backup()`한 DB 사본에서 실제 임포터를 실행해 신규·중복·보강·오류 수를 센다(본 DB 무변경). `POST /data/import`가 같은 업로드를 본 DB에 적용하며 `sync_jobs`에 `service='import'`로 기록한다(동시 1건, 409 `IMPORT_RUNNING`). 이력은 `GET /data/imports`.
- 사유: 미리보기 전용 계산기를 따로 두면 실제 가져오기와 결과가 어긋난다. 사본 실행은 단일 진실원을 유지한다. 중복은 source_id 스킵 수, 소스 간 병합은 `assign_group_id`(시작 ±60초·거리 ±3%) 그룹 수.
- 동반 수정: v12에서 `activity_summaries`의 `calories`·`export_filename` 컬럼이 빠졌는데 임포터(strava_csv/archive, garmin_csv, intervals_fit, import_history)가 여전히 INSERT해 실패하던 문제를 현재 스키마에 맞춰 정리.
- 후속 수정: 임포터의 `update_changed_fields`/백필 호출이 없는 `distance_km` 컬럼을 넘겨 기존 행 갱신이 무동작이던 것을 `distance_m`(×1000)으로 정리해, 재가져오기 시 바뀐 거리가 반영된다.

## ADR-032: Story는 월·주·블록을 한 서비스에서 조회, 강도 분포는 HR 존 메트릭 합산 (2026-10-08)
- 결정: `GET /library/story/<period>`가 `YYYY-MM`·`YYYY-Www`·`b-<planId>-<phase>`를 받아 `story_service.get_story`로 응답한다. 기간 해석은 `story_period`, 통계는 `story_stats`로 분리. 블록은 활성 플랜이 없으면 400 `INVALID_PERIOD`.
- 강도 분포(Z1-2/Z3/Z4-5)는 활동별 `build_hr_zones`(hr_zones_detail 또는 hr_zone_time_1..5)를 합산한다. 존 데이터가 있는 활동의 시간이 전체의 50% 미만이면 `status="insufficient"`로 비율을 숨긴다.
- CTL 값이 없는 기간은 CTL 칩과 문장을 생략한다(에러 아님).
- 사유: `activity_summaries`에는 존 컬럼이 없고 존 시간은 metric_store에 있어, 기존 읽기 경로를 재사용해야 소스별 차이가 한곳에서 처리된다. 일부 활동만 존이 있을 때 비율을 내면 왜곡된다.

## ADR-033: 캘린더 구독은 토큰 URL 공개 피드, 토큰은 해시 조회 + Fernet 재표시 (2026-10-08)
- 결정: `/feeds/cal/<token>.ics`는 CF Access를 우회하는 공개 경로이며 세션·쿠키를 쓰지 않는다. 토큰은 `rpcal_` + `token_urlsafe(32)`; 조회는 sha256 해시만 쓰고(전역 DB `data/calendar_feeds.db`), 카드에서 다시 보여줄 수 있도록 Fernet `enc:` 암호문을 함께 저장한다(키가 없으면 NULL → "재발급해야 다시 볼 수 있어요"). 관리 API는 `GET/POST(rotate)/DELETE /api/v1/data/calendar-feed`.
- 방어: 토큰당 60/시간, 실패 IP당 20/10분 제한(초과 429), 모든 실패는 동일한 404 + `X-Robots-Tag: noindex`, gunicorn 접근 로그의 토큰 마스킹(`RedactingLogger`).
- 담기는 정보: 날짜·종류·거리, 목표 페이스·심박 존, 인터벌 구성. 메모·AI 설명, 건강 수치, 완료 여부, 대회명·장소는 제외. 기간은 오늘 −28일 이후.
- 사유: 구글·애플 캘린더는 로그인 없이 URL만 가져가므로 URL 자체가 비밀이어야 한다. 해시 조회는 DB 유출 시 피드 접근을 막고, 재표시용 암호문은 키가 있을 때만 둔다.
- 설계서에는 ADR-032로 적혀 있으나 번호는 Story가 먼저 사용해 033으로 기록.
- 운영 작업: Cloudflare Access에 `/feeds/cal/*` Bypass 정책 추가, 컨테이너 재빌드(Dockerfile `--logger-class`).

## ADR-034: 원격 MCP는 Flask `/mcp` 읽기 전용 + 앱 Bearer 토큰, 웹·CLI 발급 (2026-10-08)
- 결정: Streamable HTTP(POST만) `/mcp`를 Flask 블루프린트로 제공한다. 설정 `mcp_remote.enabled`(기본 false)가 킬 스위치이며 꺼지면 404. `auth_cf`는 `/mcp` 정확 경로만 우회하고 쿠키·세션은 쓰지 않는다. 인증은 Bearer `rpmcp_`+43자, 조회는 sha256 해시(전역 `data/mcp_tokens.db`), 사용자 바인딩, 만료 90일, 즉시 폐기, 사용자당 활성 5개, 원문은 발급 시 1회만 노출.
- 안전: 프로토콜 코어(`mcp_remote.protocol`)를 stdio 서버와 공유하되 허용 도구(`policy.REMOTE_TOOLS`)만 노출하고, 읽기 전용 연결(`safe_conn`: query_only·authorizer·ATTACH 차단·시간 제한)과 일반화 오류를 쓴다. 배치·64KB 초과·Origin 불일치·미지원 버전은 거부.
- 방어·감사: tools/call 120/10분·1500/일, 인증 실패 IP당 20/10분(429), 모든 실패는 동일한 401. `mcp_audit`에 토큰·도구·인자(500자)·상태·지연·IP 해시를 90일 보관. 토큰 발급·폐기도 같은 표에 `token_issue`/`token_revoke`로 기록.
- 발급: CLI `scripts/mcp_token.py`와 웹 `GET/POST/DELETE /api/v1/settings/mcp-tokens`(세션 사용자 한정, no-store) + 설정 카드 "외부 AI 연결". 서버가 꺼져 있어도 토큰은 미리 만들 수 있고 카드가 "아직 꺼짐"을 표시한다.
- 사유: 서버 대 서버 클라이언트는 CF 로그인을 할 수 없고, CF 서비스 토큰만으로는 사용자 바인딩이 안 된다. 앱 토큰이 사용자 스코프를 보장한다.
- 운영 작업(코드 밖, 켜기 전 필수): (1) CF Access에 `<host>/mcp` 경로 앱 추가 — Genspark가 커스텀 헤더 여러 개를 지원하면 Service Auth, 아니면 Bypass(D1), (2) 서비스 토큰 발급(Service Auth 시), (3) WAF rate limit, (4) `/mcp` 캐시 우회, (5) `config.json`에 `"mcp_remote": {"enabled": true}` 후 컨테이너 재시작.

## ADR-035: 조정 수락은 `plan_adjustments` 테이블에 영속화하고 읽을 때 계획에 겹쳐 적용 (2026-10-08)
- 결정: 스키마 v31 `plan_adjustments`(proposed/accepted/reverted, rev, before/after/reasons JSON, rule_version)에 조정 이력을 저장한다. 원본 `planned_workouts`는 수정하지 않고, `get_planned_workouts`가 accepted 조정만 읽기 시점에 겹쳐 적용한다(`training/plan_overlay`). 유효 계획 순위(R1)는 `실행된 외부 계획 > 수락된 조정 > 외부 계획 > planner 원안`이며 조정 휴식일은 이행률 분모에서 제외한다(D9). 수락·되돌리기는 당일만, rev 불일치는 409 `CONFLICT`.
- 세부 결정: (1) 제안은 조회 시 멱등 upsert(`ensure_proposal`)로 만들어 Today·계획·Coach가 같은 id를 공유. (2) v1 조정 후 거리는 유형만 바꾸고 원본 유지(휴식은 NULL), R8 비율은 `rule_version` 상향으로 후속. (3) 원본 행이 바뀌거나 재생성되면 stale로 표시하고 적용하지 않음. (4) ICS 피드·Garmin/CalDAV 푸시에는 v1에서 반영하지 않음(후속).
- 사유: 읽기 시점 오버레이는 원본 불변으로 되돌리기가 단순하고, 조정 이력이 남아 거절·되돌림을 구분할 수 있다. 설계: `phase-7-ui-renewal/DESIGN-PLAN-ADJUSTMENTS.md`.
- 추가(2026-10-09, 행 액션 T8): 사용자 직접 조정은 `source='user'`로 즉시 accepted 생성(`POST /coach/plan/workouts/<id>/action`: reduce/rest/skip, 당일만). (B1) 수락된 코치(crs) 조정이 있으면 직접 조정이 대체(기존 건 reverted). (B2) 줄이기는 유효 계획(조정 반영 후) 기준으로 계산. reduce 규칙: 최대 50%, 결과 3.0km 미만 불가, 품질 유형(interval/tempo/threshold/marathon/race) 불가. `GET /coach/plan/adjustment`는 `user_adjustment`도 반환. D9 개정(사용자 결정 2026-10-09): 사용자 직접 건너뛴 날(source='user' rest)은 `state='skipped'`로 지난 날에 한해 세션·볼륨·핵심 분모에 원래 계획 기준으로 포함(미이행). 코치 제안 휴식(crs)만 분모 제외 유지. 설계: `DESIGN-PLAN-ROW-ACTION.md`, `DESIGN-PLAN-ROW-ACTION-COACHING.md`.

### ADR-035 부록: `move` op (2026-10-09)
- 저장: move 행(`op='move'`, `date`=원래 날짜, `after.date`=목적일) + 맞바꿈 행(목적일 세션을 오늘로, reasons의 `pair`로 연결)을 한 트랜잭션에 기록. overlay는 읽을 때 `date`를 바꾸고 재정렬.
- 되돌리기: 어느 쪽 행을 되돌려도 pair 전체와 이후 종속 조정이 함께 되돌려진다.
- 거절(409 `details.reason`): RACE_FIXED, PAIN_NO_MOVE, ALREADY_MOVED, NOT_TODAY, OUT_OF_RANGE(내일~+3일), CROSS_WEEK, TAPER_LOCK, TARGET_DONE, TARGET_HARD(쉬움·휴식·빈 날만 허용), HARD_SPACING. `to_date` 누락은 400.
- 이유 `injury`는 통증으로 취급해 이동 불가.

### ADR-035 부록: Q 세션 reduce·easy (2026-10-09)
- 인터벌은 reps −1/−2(남은 reps ≥2, 남은 reps×2 ≥ 원래 sets), 템포·역치·마라톤은 pct 20/30(작업 구간 하한 2km/5km), 롱런은 pct 15/20/30/40(16km 미만이면 easy 로 전환). 페이스는 바꾸지 않는다.
- Q 감량은 `after`에 `interval_prescription`·`structure_json`을 함께 기록(overlay `_FIELDS` 확장). `easy` op 은 거리 유지·페이스 제거, 저장 op 은 `replace`.
- 에러 코드: NO_STRUCTURE, BELOW_FLOOR(3.0km), NO_BASIS, PCT_NOT_FOR_QUALITY, RACE_FIXED. 구현: `src/services/plan_reduce.py`.

### ADR-035 부록: load_delta (2026-10-09)
- 세션 부하 = 유형 계수 K × km × u(최근 90일 이지 러닝 TRIMP/km 중앙값, 표본<10이면 전체 러닝, 없으면 8.8). 지난 날은 실제 TRIMP, 오늘 이후는 계획(overlay 적용)으로 채워 이번 주 합계 변화율과 주말 ACWR(α=1/7, 1/42) 전/후를 낸다.
- move 는 부하 불변이라 null. 이력이 없으면 null(에러 없음). 응답은 POST action 의 `load_delta`와 `GET .../action/preview`. UI 는 ACWR 이 0.8/1.3 경계를 넘을 때만 강조색. 구현: `src/services/plan_load.py`.
- 백테스트(운영 DB, `scripts/plan_load_backtest.py`, 2026-10-09): 계획 km≈실제 km(±25%)인 6주 중앙 절대오차 10.0%. 계획 이행 편차까지 포함한 전체 21주는 64%(모델이 아니라 계획 vs 실제 km 차이). 미리보기는 '계획대로 달렸을 때'의 추정치로 표기.

### ADR-035 부록: 통증 단계 (2026-10-09)
- 이유 키 `injury`→`pain`. 통증 선택 시 정도(mild/moderate/severe)와 부위 1~3곳 필수(UI), 서버는 정도·부위 값만 검증 (`plan_pain.resolve`).
- mild: reduce/easy/rest/skip 허용(Q·롱은 이지 기본). moderate·severe: op 무관 `rest`로 강제. 통증이면 move 금지(`PAIN_NO_MOVE`).
- moderate/severe 기록 후 D+1~D+2 세션은 `ensure_proposal`에서 `plan_pain.proposal`이 우선 제안(severe 휴식, moderate Q·롱 휴식·그 외 거리 ×0.6, `rule_version=pain_v1`).
- 14일 내 통증 2회 또는 같은 부위 반복 시 `PAIN_REPEAT` advisory(액션 응답 `advisories[]`). A1~A6은 후속.

### ADR-035 부록: 경고 A1~A6 (2026-10-09)
- `src/services/plan_advisory.py`: REST_STREAK·Q_DROPPED_2·LONG_DROPPED_2W·WEEK_LOAD_DROP·ACWR_LOW·REPLAN. 거부하지 않고 액션 응답 `advisories[]`로만 안내(토스트 첫 항목).
- 같은 코드는 ISO 주당 1회: 발급 시 새 조정 행 `reasons_json`에 `{"key":"advisory","code"}`를 남기고 그 주 행에서 중복 판정. 통증 사유 조정은 세지도 발급하지도 않음. REPLAN 이 켜지면 REST_STREAK 은 숨김.
- 집계 대상: accepted 조정 중 rest/skip, 품질→이지 전환.

### ADR-035 부록: A6 REPLAN 배너 (2026-10-09)
- `GET /coach/plan/advisories?date=` 읽기 전용(발급 기록 안 함). 최근 72시간 내 accepted 통증 조정이 있으면 빈 목록. REPLAN 항목에 `link`(목표 거리·대회일·목표 기록·최근 2주 실제 주간 km).
- 시트 상단 `ReplanBanner`(role=note 정보 띠), ISO 주 단위 숨김(localStorage `rp.replanHidden`), 통증 사유 선택 시 숨김, 배너가 보이면 토스트에서 REPLAN 생략, 초기 포커스는 첫 액션 버튼.
- "계획 다시 맞추기" 링크는 `REPLAN_LINK_ENABLED=false`. `POST /coach/plan` 의 부수효과(새 goal 행 생성, planner 행 삭제 후 재삽입) 확인(K1/K2) 후 켠다.

#### 외부 출력 반영 (ADR-035 부록)
- CalDAV/Garmin 푸시는 `get_planned_workouts(overlay=True)`로 이미 조정 반영. ICS 피드(`calendar_feed_service._overlaid_rows`)도 같은 오버레이를 적용: 휴식으로 바뀐 날은 이벤트 제외, 이동은 새 날짜, 조정된 이벤트의 DTSTAMP는 `decided_at`(캘린더 클라이언트 갱신). 범위 밖에서 들어오는 move를 위해 ±7일 넓게 읽고 범위로 다시 거른다. UID는 날짜+슬롯 기반이라 이동 시 옛 UID 소멸·새 UID 생성(구독 클라이언트가 자연 갱신).

#### K1/K2 확인 결과 (A6 재계획 링크, 2026-10-09)
- 링크 자체는 `/coach/plan/new` 폼 프리필일 뿐이나, 제출(`POST /coach/plan` → `create_plan_from_template`)에 부작용이 있어 링크는 계속 off.
- K1: `add_goal`이 기존 활성 목표를 종료하지 않아 활성 목표가 둘이 된다.
- K2: `save_weekly_plan`이 같은 날짜의 `source='planner'` 행을 삭제·재삽입하고 시작 주가 이번 주(월요일)라 이번 주 지난 날의 행까지 새 id로 바뀐다 → `matched_activity_id`·`session_outcomes.planned_id`·`plan_adjustments.workout_id` 연결이 끊긴다.
- 활성화 전제(설계 필요): 재계획은 오늘 이후 날짜만 교체, 기존 목표를 `cancelled/superseded`로 전환, 이동·조정 이력 보존. 별도 설계 후 진행.

#### 재계획 의미 (ADR-035 부록 R, 2026-10-09, 구현·배포 완료)
- 후속(2026-10-09, 스키마 v33): `plan_replans.start_source` 에 실제 출처(history/floor/user/avg16/default) 저장 → 꼬리 주가 A 상태(history)에서 cold 피크로 올라가던 불일치 해소. `GET coach/plan/replan/last`(Q1, 프런트 연결은 미착수). 배너 link 의 `recent_weekly_km` 제거.
- 검증: K1·K2 정확. 추가 확인: K1a 활성 목표 조회 정렬이 코드마다 다름(CalcContext는 id 기준 없음), K1b 새 goal이면 이행률·N주차·`plan_progression` 리셋, K2a 끊긴 `session_outcomes`가 활동을 계속 점유해 새 행이 재매칭되지 않음(지난 날이 미이행으로 바뀜), K2c proposed 조정 고아, K2d Garmin/CalDAV 중복, K3 `create_plan_from_template`이 `user_training_prefs`를 기본값으로 덮어씀(기존 버그), K4 단계별 commit으로 원자성 없음, K5 같은 goal로 미래만 다시 만들면 시작 부하가 계획 시작일 기준이라 원래 램프를 재현, K6 새 목표가 옛 목표의 미래 행을 남김.
- 제안: 재계획 = 같은 goal 안에서 기준점(`plan_replans`, v32)을 새로 찍고 **다음 월요일부터** 미래 주만 교체. 이동은 CROSS_WEEK 금지, 수락은 당일만이라 교체 범위에 accepted 조정·매칭이 구조적으로 없음. 방어적으로 matched/outcome/accepted 행은 보존, proposed 조정은 삭제. 미리보기(쓰기 없음)·한 트랜잭션 적용·마지막 1건 되돌리기. 전용 API `GET .../replan/preview`, `POST .../replan`, `POST .../replan/<id>/undo`. `POST /coach/plan`(새 목표)은 활성 1개 불변식(기존 active→`cancelled`, 부분 유니크 인덱스, 조회 통일), prefs 덮어쓰기 제거, 단일 트랜잭션.
- 구현 결과: T1~T7·T9 배포. 링크는 `link.race_date` 가 있을 때 `/coach/plan/replan` 으로 연결. Garmin/CalDAV 는 삭제 API 부재로 `external[]` 안내만(T8 한계). 되돌리기는 결과 화면에서만(Q1 후속).
- 결정 D1~D7(시작일, goal 정체성, 기존 목표 처리, 미리보기, 외부 푸시 정리, 되돌리기, K3 BUG 등록). 설계·T1~T10: `phase-7-ui-renewal/DESIGN-PLAN-A6-REPLAN-SAFE.md`. 링크는 결정·구현 전까지 off 유지.

#### 재계획 입력 재검토 — 이력 기반 시작점 (A6 §11, 2026-10-09, 구현 완료)
- 문제: 러닝 기록이 있어도 주간·롱런 입력을 받았으나 A 상태(km4≥12)에서는 [km4, 1.1×km4]로 잘려 효과가 없거나 오해를 줬다.
- 결정: 서버가 `start_source`(history/floor/user/avg16/default)·`basis`·`goal_target_time_sec`를 돌려주고, 화면은 "시작점" 카드로 근거를 보여 준다. 주간·롱런 입력은 C(공백)·D(신규)에서만 노출, 목표 기록은 카드에서 인라인 수정.
- DB `plan_replans.start_source` CHECK(user/history)는 유지: 저장은 `user` 아니면 `history`, 세분 출처는 응답에만.
- Q6 채택: 롱런 미입력이면 `start_long_km(long6, long12)`를 저장. Q7(꼬리 일정 출처 "user" 고정) 보류, Q8(수동 하향) 미제공.


#### 재계획 진입 규칙 Q4 (ADR-035 부록 R, 2026-10-09)
- `plan_replan_service.entry_state` 가 노출 규칙의 단일 출처 `{eligible, reason: NO_GOAL|RACE_NEAR|PENDING, last}`. 배너(`plan_advisory`)·`GET coach/plan/replan/last`(`{last, entry}`)·플랜 상세 헤더 링크가 모두 이를 쓰고 프런트는 규칙을 복제하지 않는다. RACE_NEAR = 다음 월요일부터 대회 주까지 2주 미만.
- 적용 후 되돌리지 않은 재계획이 있으면 새 재계획은 `REPLAN_PENDING`(409, `error.details.last`). 되돌림 불가 사유는 `_undo_blocker` 한 곳(마지막 아님·시작됨·새 행에 이력)으로 모아 undo·last_undoable·가드가 공유.
- 프런트: 플랜 상세 헤더에 되돌리기 줄 또는 "남은 일정 다시 맞추기 →", 재계획 화면은 REPLAN_PENDING 에서 되돌리기 후 미리보기 재계산.

### ADR-036: CalDAV 연동 복구·정상화 (R1, 2026-10-09)
- 사용자 선택으로 제거(R2) 대신 복구. `caldav>=1.4,<2` 를 requirements 에 고정(이전엔 주석이라 임포트 에러).
- UID = 날짜+슬롯(`{date}-{slot}@runpulse-caldav`, ICS 피드와 같은 겹침 적용 행), DTEND = DTSTART+1일. 같은 UID 재전송은 덮어쓰기라 멱등. 전송 기록은 `caldav_pushes`(스키마 v34).
- 계획에서 사라진 일정은 `push_range` 가 원격 삭제(1회 재시도 → 로그 → 계속). 재계획 apply 직후 `sync_after_replan` 이 보낸 적 있는 범위만 자동 동기화(preview 에선 안 함, 실패해도 적용은 유지, 결과 `caldav` 키). 사용자가 직접 지울 일이 없어 `external`(Garmin 전용)에는 넣지 않음.
- 연결 테스트는 사유 3종(모듈 없음/인증·URL/캘린더 없음). Google 은 OAuth 전용이라 미지원을 설정 화면에 명시.

### ADR-037: 동기화 소스 포함 목록 (SYNC-SOURCE-TOGGLE, 2026-10-10)
- 포함 목록 = `config.sync_sources` 단일 출처(`enabled_sources`/`is_source_enabled`). 끄기 ≠ 연결 해제(자격증명·과거 데이터 보존), 끄기 = 활성 job `cancelled`.
- 레거시 수동 우회 키 `<소스>_disabled` 는 `load_config` 가 읽을 때 정식 키로 옮기고 목록에서 제외(멱등, 파일 미수정, 값은 로그에 남기지 않음).
- CLI `--source <이름>` 은 명시 실행이라 포함 여부와 무관. `--source all` 만 목록을 따른다.
- G6 은 `/data/sync` 행 버튼(T5)으로 완료. v1 뷰 제거는 별개 작업이라 AUDIT-V-CANONICAL 은 BACKLOG 에 그대로 둔다.

### ADR-038: 생애주기 화면(S0/S1/S2) 판단 D-L1~D-L8 확정 (2026-10-10)
- D-L1: 사이트를 공개한다. 노출 방식은 (b) 별도 공개 정적 사이트(랜딩·데모 빌드). 앱 인증 경계(CF Access·`_identify_user`)는 변경하지 않는다.
- D-L2: 데모 데이터 = `scripts/synth_smoke` 합성 스냅샷의 정적 내보내기, Coach 는 미리 생성한 대화 1개(라이브 LLM 호출 0).
- D-L3: 가입은 초대제 유지, S0 CTA 는 "초대 요청". D-L4: Garmin 연결은 v1 `/connect/garmin` 왕복 유지.
- D-L5: 첫 백필 90일. D-L6: 신규 가입자 `ui_default` 는 v2(기존 사용자 유지). D-L7: "소량" = 핵심 3게이지 중 하나라도 미해금.
- D-L8: L1·L7 → L2·L3 → L4 → L5·L6 순. 설계: `phase-7-ui-renewal/DESIGN-P7-REVIEW03-LIFECYCLE.md`.


### ADR-039: 계획 규칙 버전은 anchor 단위, v1→v2 전환은 사용자가 승인한 재계획으로만 (2026-10-10)
- D4 개정: 진행 중 계획의 엔진 전환은 자동이 아니라 사용자가 미리보기를 확인하고 적용한 재계획에서만 일어난다(`REPLAN_UPGRADE_ENABLED`, 기본 off).
- D-U16-2("목표당 고정") 대체: 규칙 버전은 `plan_replans.rules_version`(anchor 단위)이며, 그 주 이전 마지막 applied anchor 값이 우선하고 없으면 `goals.plan_rules_version`(`effective_rules_version`). 되돌리면(undone) 이전 버전으로 복귀.
- 재계획 API: `rules_version`(전환 요청)·`expect_rules_version`(미리보기 때 본 현재 버전, 불일치 시 409 `RULES_MISMATCH`). 미리보기는 `structure_diff`(종류·구조 행 수 전/후, 달라진 날)를 돌려준다.
- 검증: 합성 격자 재계획 백테스트(`plan_backtest.py --engine replan`, 1596건) 하드 게이트 위반 0.

### ADR-040: Garmin VO2max 정밀값 (GARMIN-VO2MAX-PRECISE, 2026-10-10)
- D1: 일별 메트릭 `vo2max`(provider garmin, daily, numeric=`vo2MaxPreciseValue` 소수 1자리, 없으면 정수값)로 저장. 소스는 `get_max_metrics_range`(≤365일/호출, 측정일만 존재), raw 는 `maxmet_day`.
- D2: SEMANTIC_GROUPS `vo2max` 에 daily 멤버 추가, 제공자 매트릭스 garmin 셀을 daily `vo2max` 로 교체.
- D3: 소비처는 `utils/vo2max_source`(정밀값 vs 활동 정수값 중 더 최근 날짜, 동일 날짜면 정밀값, 나이 제한 없음).
- D4: 죽은 user_summary `vo2MaxValue` 경로(`_upsert_vo2max`, wellness fitness 블록, Garmin `extract_fitness`)를 제거.
- D5: `training_status_day` 는 건드리지 않고 ATL/CTL 파서 결함은 BUG 로 등록.
- 과거 백필은 `scripts/backfill_garmin_vo2max.py`(기본 dry-run), 실 DB 쓰기는 백업 + 사용자 승인 후.

### ADR-041: Garmin 훈련 상태 부하 저장 (GARMIN-TRAINING-STATUS-PARSER, 2026-10-10)
- 가민 급성/만성 부하는 PMC(`atl`/`ctl`, provider intervals/자체계산)와 단위·산식이 달라 `garmin_acute_load`/`garmin_chronic_load` 로 분리 저장. 플래너·분석이 읽는 `atl`/`ctl` 은 오염시키지 않는다.
- payload 는 `mostRecentTrainingStatus.latestTrainingStatusData[기기ID]` 중첩 구조; `primaryTrainingDevice` 레코드 우선, 없으면 첫 레코드.

### ADR-042: 알고리즘 변경 이력 ◆ 마커 (2026-10-10)
- D1: 단일 소스는 코드 레지스트리 `src/metrics/algo_changelog.py`(순수 데이터). DB 스키마 변경 없음(SCHEMA_VERSION 35 유지). 날짜는 코드 반영일(커밋 날짜).
- D2: 전 기간 재계산이 행을 지우고 다시 쓰므로 데이터 불연속이 없다. ◆ 는 정보 표시(사유 한 줄 + "과거 값도 다시 계산")이며 시계열 단절 표시가 아니다.
- D3: 상위 지표(requires 역추적) 변경도 해당 차트에 전파(예: TRIMP→ctl). 같은 날짜 변경은 1건으로 병합. 신규 Calculator(prev=None)는 마커 없음.
- D4: `tests/test_algo_changelog.py` 가 Calculator version≠"1.0" 의 항목 누락을 막는다. version 을 올리면 레지스트리 항목을 함께 추가한다.

### ADR-043: 지표 설명 프리페치·Coach 지표 프리필 (2026-10-10)
- D1: 차트 스크럽(hover·드래그·핀) 시 일자별 explain 을 프리페치하고 30초 메모리 캐시로 패널 요청과 공유한다(실패는 캐시하지 않음).
- D2: Coach 프리필 계약은 `/coach/new?metric=<slug>&date=<YYYY-MM-DD>`(slug `[a-z0-9_]+`, 형식 불일치는 무시). 스레드 컨텍스트는 `{kind:'metric', ref:'slug@date'}`, 질문 3개는 클라이언트에서 생성.
- D3: 백엔드 프롬프트는 아직 `activity` 종류만 요약하므로 `metric` 컨텍스트는 저장·뒤로가기 링크용이다(프롬프트 주입은 LLM 연동 항목).

