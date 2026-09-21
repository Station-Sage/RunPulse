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
