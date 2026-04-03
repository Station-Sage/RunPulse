## Phase 6 상세 설계 – Initial Data Load & Validation

Phase 6는 Phases 1~5에서 만든 모든 인프라를 실제 데이터로 채우고 검증하는 단계입니다. 빈 DB에서 출발해 "프로덕션 수준의 완전한 데이터"가 들어간 상태로 끝나야 합니다.

---

### 1. Phase 6의 목표

Phase 6가 완료되면 다음 상태에 도달해야 합니다.

첫째, 모든 소스(Garmin·Strava·Intervals·Runalyze)의 과거 활동 데이터가 `source_payloads` → `activity_summaries` → `metric_store` → `activity_streams` → `activity_laps` → `activity_best_efforts` 경로로 빠짐없이 적재되어 있어야 합니다. 둘째, Garmin·Intervals 웰니스 데이터가 `daily_wellness`·`daily_fitness`에 적재되어 있어야 합니다. 셋째, RunPulse 자체 메트릭(Phase 4 Metric Engine)이 전체 기간에 대해 계산·저장되어 있어야 합니다. 넷째, dedup이 완료되어 `matched_group_id`가 정상 배정되어 있어야 합니다. 다섯째, 자동 검증 스크립트가 전 항목 PASS를 리포트해야 합니다.

---

### 2. 데이터 로드 전략

#### 2.1 로드 순서

데이터 의존성 그래프에 따라 다음 순서로 적재합니다.

**Step 1 – Garmin Bulk Export 적재.** Garmin Connect에서 다운로드한 ZIP 파일(활동별 JSON·FIT·GPX)을 파싱합니다. 이 단계에서 `source_payloads`에 원본 JSON을 저장하고, `garmin_extractor`를 호출해 `activity_summaries`와 `metric_store`를 채웁니다. FIT 파일이 있으면 `activity_streams`와 `activity_laps`도 함께 적재합니다. Bulk Export를 먼저 처리하는 이유는 Garmin API의 일일 호출 제한(Rate Limit)을 우회하면서 가장 많은 양의 과거 데이터를 확보할 수 있기 때문입니다.

**Step 2 – Garmin API 보충 동기화.** Bulk Export에 포함되지 않은 최근 데이터(마지막 export 이후)를 API로 가져옵니다. `source_payloads`에 이미 동일 `entity_id`가 있으면 `payload_hash` 비교 후 변경분만 업데이트합니다.

**Step 3 – Garmin 웰니스 API 동기화.** Sleep, HRV, Body Battery, Stress, Training Readiness, User Summary 등 웰니스 엔드포인트를 날짜 역순으로 호출합니다. `daily_wellness`와 `metric_store`(scope_type=`daily`)를 채웁니다.

**Step 4 – Strava API 전체 동기화.** OAuth 토큰으로 활동 목록을 페이지네이션하며 수집합니다. 각 활동의 상세(detail)와 스트림(streams)을 가져와 적재합니다. Strava API는 15분당 100회·일일 1,000회 제한이 있으므로 `RateLimiter`가 자동으로 대기·재시도합니다.

**Step 5 – Intervals.icu API 전체 동기화.** 활동 목록과 웰니스를 가져옵니다. Intervals는 Rate Limit이 비교적 관대하므로 빠르게 끝납니다. `daily_fitness`(CTL·ATL·TSB)도 이 단계에서 적재합니다.

**Step 6 – Runalyze API 전체 동기화.** 활동 목록과 상세를 가져옵니다. Runalyze는 스트림을 제공하지 않으므로 `activity_streams`는 건너뜁니다.

**Step 7 – Dedup 실행.** 전체 `activity_summaries`를 스캔해 `start_time` 5분 이내 + `distance_m` 3% 이내 + 서로 다른 소스 조합을 찾아 `matched_group_id`(UUID)를 배정합니다.

**Step 8 – Metric Engine 전체 재계산.** `engine.recompute_all()`을 호출해 모든 RunPulse 메트릭(TRIMP, HRSS, GAP, VDOT, PMC, ACWR, UTRS, CIRS 등)을 계산·저장합니다. 토폴로지 정렬에 따라 1차 메트릭 → 2차 메트릭 순으로 실행됩니다.

**Step 9 – Primary 해소.** 전체 `metric_store`에 대해 `resolve_primaries`를 실행해 각 (scope_type, scope_id, metric_name) 조합에 `is_primary=1`이 정확히 하나만 존재하도록 정리합니다.

#### 2.2 Garmin Bulk Export 파서

별도 모듈 `src/sync/garmin_bulk_loader.py`를 작성합니다.

```python
class GarminBulkLoader:
    """Garmin Export ZIP → DB 적재"""

    def __init__(self, conn, zip_path: str):
        self.conn = conn
        self.zip_path = zip_path

    def load(self, include_streams: bool = True) -> BulkLoadResult:
        """
        1. ZIP 압축 해제 (임시 디렉토리)
        2. activity_*.json 파일 목록 수집
        3. 각 JSON 파일에 대해:
           a. source_payloads UPSERT (source='garmin', entity_type='activity_bulk')
           b. garmin_extractor.extract_activity_core → activity_summaries UPSERT
           c. garmin_extractor.extract_activity_metrics → metric_store UPSERT
           d. 매칭 FIT/GPX 파일이 있으면 → activity_streams, activity_laps INSERT
        4. BulkLoadResult 반환 (total, loaded, skipped, errors)
        """
```

`BulkLoadResult` dataclass는 `total_files`, `loaded_count`, `skipped_count` (이미 존재하는 payload_hash), `error_count`, `errors` (파일명+예외 메시지 리스트)를 포함합니다. FIT 파일 파싱에는 `fitparse` 라이브러리를 사용하며, GPX 파싱에는 `gpxpy`를 사용합니다.

#### 2.3 Full Sync CLI 확장

`src/sync.py`에 `initial-load` 명령을 추가합니다.

```
python -m src.sync initial-load \
    --garmin-zip ~/Downloads/garmin_export.zip \
    --garmin-api-days 30 \
    --strava-days 0 \        # 0 = 전체
    --intervals-days 0 \
    --runalyze-days 0 \
    --include-streams \
    --compute-metrics
```

이 명령은 위 Step 1~9를 순서대로 실행합니다. 각 Step 완료 시 콘솔에 진행 상황(소스명, 건수, 소요 시간, 에러 수)을 출력합니다. `--dry-run` 옵션을 지원해 API 호출 없이 Bulk Export 파싱만 시뮬레이션할 수 있습니다.

---

### 3. 검증 프레임워크 (Validation Suite)

#### 3.1 설계 원칙

검증은 "사람이 눈으로 확인"하는 것이 아니라, 재현 가능한 자동화 스크립트로 실행되어야 합니다. 모든 검증 항목은 PASS/WARN/FAIL 중 하나를 반환하며, 최종 리포트에 요약됩니다.

#### 3.2 검증 모듈 (`src/validation/validator.py`)

```python
@dataclass
class CheckResult:
    name: str                # 검증 항목명
    status: str              # 'PASS' | 'WARN' | 'FAIL'
    expected: Any            # 기대값 또는 범위
    actual: Any              # 실측값
    message: str = ''        # 상세 메시지

class DataValidator:
    def __init__(self, conn):
        self.conn = conn
        self.results: list[CheckResult] = []

    def run_all(self) -> list[CheckResult]:
        """모든 검증 실행 후 결과 리스트 반환"""
        self._check_row_counts()
        self._check_source_distribution()
        self._check_unmapped_ratio()
        self._check_metric_density()
        self._check_primary_uniqueness()
        self._check_provider_distribution()
        self._check_dedup_consistency()
        self._check_data_quality()
        self._check_wellness_coverage()
        self._check_fitness_continuity()
        self._check_referential_integrity()
        self._check_metric_engine_coverage()
        return self.results

    def print_report(self):
        """콘솔에 검증 결과 요약 출력"""
```

#### 3.3 검증 항목 상세 (12개 카테고리)

**Check 1 – Row Counts (행 수 검증).** 각 테이블의 행 수가 합리적인 범위 안에 있는지 확인합니다. 예를 들어 2년간 러닝 기록이라면 `activity_summaries`에 400~800행, `daily_wellness`에 600~730행, `metric_store`에 30,000~80,000행이 예상됩니다. 행 수가 예상 범위의 50% 미만이면 WARN, 10% 미만이면 FAIL입니다. 기준값은 `--expected-activities`, `--expected-days` CLI 파라미터로 오버라이드 가능합니다.

**Check 2 – Source Distribution (소스 분포).** `activity_summaries`에서 `SELECT source, COUNT(*) GROUP BY source`를 실행해 각 소스별 건수가 0이 아닌지 확인합니다. 동기화 대상으로 설정된 소스의 건수가 0이면 FAIL입니다.

**Check 3 – Unmapped Metric Ratio (_unmapped 비율).** `metric_store`에서 `category = '_unmapped'`인 행의 비율을 계산합니다. 전체 메트릭 대비 5% 이하면 PASS, 5~15%면 WARN(새 필드 추가 필요 시사), 15% 초과면 FAIL입니다.

**Check 4 – Metric Density (활동당 메트릭 수).** `SELECT scope_id, COUNT(*) FROM metric_store WHERE scope_type='activity' GROUP BY scope_id`를 실행해 활동별 메트릭 수를 계산합니다. 평균 10개 이상이면 PASS, 5~10이면 WARN, 5 미만이면 FAIL입니다. 또한 메트릭이 0인 활동이 있으면 개별 WARN을 발행합니다.

**Check 5 – Primary Uniqueness (Primary 유일성).** `SELECT scope_type, scope_id, metric_name, COUNT(*) FROM metric_store WHERE is_primary=1 GROUP BY scope_type, scope_id, metric_name HAVING COUNT(*) > 1`이 0행을 반환해야 PASS입니다. 1행이라도 있으면 FAIL이며, 중복 목록을 상세 메시지에 포함합니다.

**Check 6 – Provider Distribution (공급자 분포).** `metric_store`에서 `SELECT provider, COUNT(*) GROUP BY provider`를 실행합니다. `runpulse:formula` 또는 `runpulse:ml` 행이 0이면 Metric Engine이 실행되지 않은 것이므로 FAIL입니다. 각 소스 provider(garmin, strava 등)의 비율이 극단적으로 치우쳐 있으면 WARN입니다.

**Check 7 – Dedup Consistency (중복 제거 일관성).** `matched_group_id`가 NULL이 아닌 행들을 그룹별로 검사합니다. 같은 그룹 내 같은 source가 2건 이상이면 FAIL(동일 소스끼리 dedup되면 안 됨)입니다. 그룹 내 `distance_m` 편차가 5%를 넘으면 WARN(dedup 기준 3%보다 넓지만 비정상은 아님)입니다. 그룹 내 `start_time` 편차가 10분을 넘으면 WARN입니다.

**Check 8 – Data Quality (데이터 품질).** `activity_summaries`에서 핵심 컬럼의 이상값을 검사합니다. `distance_m < 0` 또는 `distance_m > 200000`(200km 초과)이면 WARN, `duration_sec < 0`이면 FAIL, `avg_hr`가 30 미만이거나 250 초과면 WARN, `avg_cadence`가 50 미만이거나 300 초과면 WARN, `avg_pace_sec_km`이 `distance_m`과 `duration_sec`로 계산한 값과 10% 이상 차이나면 WARN입니다.

**Check 9 – Wellness Coverage (웰니스 커버리지).** 활동이 존재하는 날짜 범위 내에서 `daily_wellness`의 커버리지(채워진 날 / 전체 날)를 계산합니다. 90% 이상이면 PASS, 70~90%면 WARN, 70% 미만이면 FAIL입니다. `sleep_score`와 `resting_hr`가 모두 NULL인 날의 수도 별도 보고합니다.

**Check 10 – Fitness Continuity (피트니스 연속성).** `daily_fitness`에서 `ctl`, `atl`, `tsb`의 시계열이 연속적인지 확인합니다. 3일 이상 연속 빈 날(gap)이 있으면 WARN, 7일 이상이면 FAIL입니다. `ctl`이 음수이거나 비합리적으로 큰 값(>300)이면 WARN입니다.

**Check 11 – Referential Integrity (참조 무결성).** `metric_store.scope_id`가 `activity_summaries.id` 또는 날짜 형식(YYYY-MM-DD)인지 확인합니다. `activity_streams.activity_id`가 `activity_summaries.id`에 존재하는지 확인합니다. `source_payloads.activity_id`가 NULL이 아닌 경우 대응하는 `activity_summaries` 행이 존재하는지 확인합니다. 어느 하나라도 고아(orphan) 행이 있으면 FAIL입니다.

**Check 12 – Metric Engine Coverage (엔진 커버리지).** Phase 4에서 정의한 모든 calculator의 `produces` 목록을 수집하고, 실제 `metric_store`에서 `provider LIKE 'runpulse%'`인 metric_name 목록과 대조합니다. 등록된 모든 metric이 1건 이상 존재하면 PASS, 일부 누락이면 WARN(해당 metric 목록 표시), 절반 이상 누락이면 FAIL입니다.

#### 3.4 검증 리포트 출력 형식

```
═══════════════════════════════════════════════════════════
  RunPulse v4 Data Validation Report
  Date: 2026-04-03  DB: runpulse.db
═══════════════════════════════════════════════════════════

 #  Check                    Status  Expected      Actual        
── ──────────────────────── ────── ──────────── ────────────
 1  Row Counts               PASS   400~800       623           
 2  Source Distribution       PASS   4 sources     4 (G:623 S:580 I:610 R:415)
 3  Unmapped Ratio            PASS   < 5%          2.3%          
 4  Metric Density            PASS   ≥ 10/act      18.4          
 5  Primary Uniqueness        PASS   0 duplicates  0             
 6  Provider Distribution     PASS   rp > 0        rp:12340 G:8200 S:5100 I:6300
 7  Dedup Consistency         PASS   no same-src   0 violations  
 8  Data Quality              WARN   no outliers   3 outliers    
    → activity 412: avg_hr=28 (below 30)
    → activity 587: distance_m=195230 (above 200km)
    → activity 103: pace deviation 12%
 9  Wellness Coverage         PASS   ≥ 90%         94.2%         
10  Fitness Continuity        PASS   no gap ≥ 7d   max gap: 2d   
11  Referential Integrity     PASS   0 orphans     0             
12  Engine Coverage           PASS   18/18 metrics 18/18         

═══════════════════════════════════════════════════════════
  SUMMARY: 11 PASS  |  1 WARN  |  0 FAIL
═══════════════════════════════════════════════════════════
```

---

### 4. 회귀 테스트 통합

#### 4.1 기존 테스트 어댑터

Phases 1~5에서 작성된 ~263개 pytest를 Phase 6 완료 후에도 모두 통과시켜야 합니다. 스키마 변경에 영향받는 테스트는 `conftest.py`의 fixture를 업데이트합니다.

#### 4.2 Phase 6 전용 테스트 (`tests/test_phase6_validation.py`)

```python
class TestBulkLoader:
    """GarminBulkLoader 단위 테스트"""

    def test_load_single_activity_json(self, tmp_zip, test_db):
        """단일 활동 JSON이 포함된 ZIP → activity_summaries 1행 생성"""

    def test_load_with_fit_file(self, tmp_zip_with_fit, test_db):
        """FIT 파일 포함 ZIP → activity_streams 행 생성"""

    def test_skip_existing_payload(self, tmp_zip, test_db):
        """동일 payload_hash → skipped_count 증가, loaded_count 불변"""

    def test_error_handling(self, corrupted_zip, test_db):
        """손상된 JSON → error_count 증가, 나머지 정상 처리"""


class TestInitialLoadCLI:
    """initial-load CLI 통합 테스트"""

    def test_dry_run_no_api_calls(self, mock_apis, test_db):
        """--dry-run 시 API 호출 0회"""

    def test_full_load_order(self, mock_apis, test_db):
        """Step 1~9 순서대로 실행되는지 호출 순서 검증"""


class TestDataValidator:
    """검증 스크립트 단위 테스트"""

    def test_all_pass_on_clean_data(self, populated_db):
        """정상 데이터 → 12개 모두 PASS"""

    def test_primary_uniqueness_fail(self, db_with_duplicate_primary):
        """중복 primary → Check 5 FAIL"""

    def test_orphan_metric_fail(self, db_with_orphan_metric):
        """고아 metric_store 행 → Check 11 FAIL"""

    def test_unmapped_warn(self, db_with_high_unmapped):
        """unmapped 10% → Check 3 WARN"""

    def test_empty_source_fail(self, db_missing_strava):
        """Strava 0건 → Check 2 FAIL"""
```

#### 4.3 성능 벤치마크 테스트

초기 로드 후 주요 쿼리의 응답 시간을 측정합니다. `get_activity_list` (100건 페이지) < 200ms, `get_activity_detail` (메트릭 포함) < 100ms, `get_dashboard_data` < 500ms, `engine.recompute_recent(30)` < 30초를 기준으로 PASS/FAIL을 판정합니다. SQLite WAL 모드와 인덱스가 올바르게 적용되어 있어야 이 기준을 충족할 수 있습니다.

---

### 5. 데이터 마이그레이션 (기존 v3 DB가 있는 경우)

기존 RunPulse v3 사용자가 v4로 업그레이드하는 경우를 위한 마이그레이션 스크립트 `src/migration/v3_to_v4.py`를 제공합니다.

마이그레이션은 세 단계로 진행됩니다. 첫째, v3 DB를 백업(`runpulse_v3_backup_YYYYMMDD.db`)합니다. 둘째, v3의 `activities` 테이블을 읽어 v4 `activity_summaries` 스키마로 변환합니다. 이때 컬럼명 매핑(예: `distance` → `distance_m`, `avg_pace` → `avg_pace_sec_km`)과 단위 변환(km → m)을 적용합니다. 셋째, v3의 원본 JSON이 남아 있다면 `source_payloads`에 적재하고, Extractor를 돌려 `metric_store`를 채운 뒤 Metric Engine을 실행합니다. 원본 JSON이 없으면 `activity_summaries`만 채우고 `metric_store`는 다음 동기화 시 API에서 재수집합니다.

마이그레이션 CLI는 `python -m src.migration.v3_to_v4 --v3-db path/to/old.db --v4-db path/to/new.db`로 실행합니다.

---

### 6. 운영 도구

#### 6.1 검증 CLI

```
python -m src.validation.validator \
    --db runpulse.db \
    --expected-activities 600 \
    --expected-days 700 \
    --output report.txt
```

`--json` 옵션을 추가하면 머신 리더블 JSON 형식으로 출력합니다.

#### 6.2 DB 상태 대시보드 CLI

```
python -m src.utils.db_status --db runpulse.db
```

출력 예시:
```
Table                Rows      Size(MB)  Last Updated
───────────────────  ────────  ────────  ────────────
source_payloads      4,821     48.2      2026-04-03
activity_summaries   623       0.3       2026-04-03
metric_store         52,140    4.1       2026-04-03
activity_streams     487,230   112.5     2026-04-03
activity_laps        3,412     0.2       2026-04-03
daily_wellness       694       0.1       2026-04-03
daily_fitness        1,038     0.1       2026-04-03
sync_jobs            47        0.01      2026-04-03
```

#### 6.3 데이터 스냅샷

초기 로드 완료 후 `runpulse.db`의 VACUUM + WAL checkpoint를 실행하고 `runpulse_initial_YYYYMMDD.db.gz`로 백업합니다. 이후 문제 발생 시 이 스냅샷에서 복원할 수 있습니다.

---

### 7. 작업 순서 & 예상 시간

| # | 작업 | 파일 | 예상 시간 |
|---|------|------|-----------|
| 1 | GarminBulkLoader 구현 | `src/sync/garmin_bulk_loader.py` | 3 h |
| 2 | FIT 파일 파서 통합 | `src/sync/fit_parser.py` | 2 h |
| 3 | initial-load CLI 명령 추가 | `src/sync.py` | 1 h |
| 4 | DataValidator 구현 (12개 체크) | `src/validation/validator.py` | 4 h |
| 5 | 검증 CLI 추가 | `src/validation/__main__.py` | 0.5 h |
| 6 | DB 상태 대시보드 CLI | `src/utils/db_status.py` | 1 h |
| 7 | v3→v4 마이그레이션 스크립트 | `src/migration/v3_to_v4.py` | 2 h |
| 8 | BulkLoader 테스트 | `tests/test_bulk_loader.py` | 2 h |
| 9 | DataValidator 테스트 | `tests/test_phase6_validation.py` | 3 h |
| 10 | 성능 벤치마크 테스트 | `tests/test_performance.py` | 1.5 h |
| 11 | 마이그레이션 테스트 | `tests/test_migration.py` | 1.5 h |
| 12 | 실제 데이터 초기 로드 실행 | (운영) | 2 h |
| 13 | 검증 실행 & 이슈 수정 | (운영) | 2 h |
| 14 | 스냅샷 생성 & 문서화 | (운영) | 0.5 h |
| | **합계** | | **~26 h** |

---

### 8. Definition of Done (완료 기준)

1. `initial-load` CLI가 Step 1~9를 오류 없이 완료한다.
2. `DataValidator.run_all()`이 12개 체크 중 FAIL 0개를 보고한다.
3. WARN 항목이 있다면 원인이 문서화되어 있다(예: 울트라마라톤으로 인한 거리 초과).
4. `source_payloads`에 모든 소스의 원본 JSON이 저장되어 있다.
5. `activity_summaries`의 46개 컬럼이 Extractor 출력과 1:1 매칭된다.
6. `metric_store`에서 `provider LIKE 'runpulse%'` 행이 Phase 4에서 등록한 모든 calculator의 metric을 포함한다.
7. `matched_group_id`가 배정된 그룹 내에 동일 소스 중복이 없다.
8. 성능 벤치마크 4개 항목이 모두 기준 이내이다.
9. 기존 ~263개 pytest가 전부 통과한다.
10. Phase 6 전용 테스트가 전부 통과한다.
11. v3→v4 마이그레이션이 테스트 DB에서 정상 작동한다.
12. `runpulse_initial_YYYYMMDD.db.gz` 스냅샷이 생성되어 있다.

---

### 9. Phase 6 이후 (Phase 7 Preview)

Phase 6 완료로 RunPulse v4의 데이터 파이프라인이 "end-to-end 작동 상태"에 도달합니다. Phase 7에서는 다음을 진행합니다: 멀티스포츠 지원(cycling, swimming 타입 추가 및 스포츠별 metric calculator), ML 파이프라인 통합(provider=`runpulse:ml`로 모델 예측값 저장), 사용자 피드백 루프(사용자가 metric 값을 오버라이드하면 provider=`user`로 저장하고 primary 즉시 전환), 신규 데이터 소스 추가(COROS, Polar, Apple Health 등 새 extractor만 추가하면 나머지 파이프라인은 재사용), 그리고 실시간 동기화(webhook 기반 자동 sync).

---
