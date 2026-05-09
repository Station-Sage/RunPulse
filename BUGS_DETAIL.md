# BUGS_DETAIL

> v0.2 버그는 전체 재개발 대상이므로 아카이브됨.
> v0.3 버그만 기록한다.

## #STREAM-CONSUMERS — activity_streams v0.2→v0.3 소비자 마이그레이션 (2026-04-27)

### 배경
v0.3 DDL: `activity_streams`는 typed columns (`elapsed_sec, heart_rate, cadence, speed_ms, power_watts, altitude_m, latitude, longitude, distance_m`).
v0.2 방식 `stream_type TEXT / data_json TEXT`는 완전 폐기됨.
`route_svg.py:_load_latlng` 은 이미 수정 완료. 나머지 5개 소비자 미수정.

### 공통 수정 패턴
**기존**: `SELECT stream_type, data_json FROM activity_streams WHERE activity_id=?`
→ `{stream_type: json.loads(data_json)}` dict 반환

**변경 후**: `SELECT elapsed_sec, heart_rate, cadence, speed_ms, power_watts, altitude_m, latitude, longitude, distance_m FROM activity_streams WHERE activity_id=? ORDER BY elapsed_sec`
→ typed column 배열로 동일한 dict 구성 (소비자 코드 변경 최소화)

하위 호환 dict 키 매핑:
| typed column | dict key |
|---|---|
| `heart_rate` | `heartrate` |
| `speed_ms` | `velocity_smooth` |
| `power_watts` | `watts` |
| `altitude_m` | `altitude` |
| `distance_m` | `distance` |
| `latitude + longitude` | `latlng` (→ `[[lat, lon], ...]`) |
| `elapsed_sec` | `time` |

### 소비자별 상세

#### 1. `src/web/views_activity_map.py:_load_coords` (line 36-60) — 활동 지도 탭
- 현재: `SELECT data_json WHERE stream_type='latlng'` → JSON 파싱
- 필요: `SELECT latitude, longitude … ORDER BY elapsed_sec` (route_svg.py와 동일 패턴)
- 영향 탭: 활동 상세 > 지도

#### 2. `src/analysis/activity_deep.py:~120` — 활동 심층 분석 탭
- 현재: Strava 활동에 대해 `SELECT stream_type, data_json` → `_calc_pace_splits(stream)` 호출
- 사용 키: `velocity_smooth`, `time`, `distance`
- 필요: typed columns → `{"velocity_smooth": [...], "time": [...], "distance": [...]}` 재구성
- 영향 탭: 활동 상세 > 심층 분석

#### 3. `src/analysis/efficiency.py:_load_stream_data` (line 69) — 효율 분석
- 현재: `path="db:{activity_id}"` 형식으로 호출, 모든 stream_type 로드
- 사용 키: `heartrate`, `velocity_smooth`, `cadence`, `watts`
- 필요: typed columns → 동일 dict 재구성
- 영향 탭: 활동 상세 > 효율 분석

#### 4. `src/analysis/zones_analysis.py:_load_stream` (line 105) — 존 분석
- 현재: 동일 패턴
- 사용 키: `heartrate`, `cadence`
- 필요: typed columns → 동일 dict 재구성
- 영향 탭: 활동 상세 > 존 분석

#### 5. `src/ai/tools.py:~377` — AI 도구 (스트림 컨텍스트)
- 현재: 모든 stream 로드 후 latlng_lat/lon 또는 latlng 형식으로 처리
- 사용 키: `latlng_lat`, `latlng_lon`, `latlng`, `heartrate`, `cadence`, `watts`
- 필요: typed columns → 동일 dict 재구성
- 영향: AI 코치 > 활동 분석 시 GPS/HR 컨텍스트

### 구현 방안
`src/utils/db_helpers.py`에 `load_activity_streams(conn, activity_id) → dict` 헬퍼 추가.
5개 소비자 모두 이 함수로 교체하여 중복 제거.

### 완료 (2026-04-28)
- `src/utils/db_helpers.py` — `load_activity_streams()` 헬퍼 추가
- `src/web/views_activity_map.py` — `_load_coords()` 교체
- `src/analysis/activity_deep.py` — `_get_stream()` 교체
- `src/analysis/efficiency.py` — `_load_stream()` DB 분기 교체
- `src/analysis/zones_analysis.py` — `_load_stream()` DB 분기 교체
- `src/ai/tools.py` — `_exec_get_activity_detail()` streams 로딩 교체

---

## #GARMIN-V2-MAPPINGS — garmin_v2_mappings.py 컬럼명 불일치 (2026-04-28)

### 증상
`garmin_backfill.py` 실행 시 `OperationalError: table activity_summaries has no column named avg_vertical_ratio_percent` 발생.

### 근본 원인
`src/sync/garmin_v2_mappings.py` line 72, 174:
```python
"avg_vertical_ratio_percent": act.get("avgVerticalRatio"),  # 잘못된 컬럼명
```
DDL(`src/db_setup.py` line 109): `avg_vertical_ratio_pct REAL`

`garmin_backfill.py`는 `upsert_activity()`를 거치지 않고 raw `INSERT INTO activity_summaries ({cols}) VALUES (...)` 사용 → 화이트리스트 필터 없음 → 존재하지 않는 컬럼명 그대로 SQL에 포함됨.

### 추가 확인 필요
`garmin_v2_mappings.py`에는 DDL에 없는 컬럼이 다수 존재:
`bmr_calories`, `device_id`, `steps`, `lap_count`, `body_battery_diff`, `water_estimated_ml` 등.
backfill 실행 시 이 컬럼들도 같은 이유로 실패함.
`garmin_backfill.py`가 `upsert_activity()` 경유하도록 수정하거나, `garmin_v2_mappings.py` 반환 dict를 DDL 컬럼명만 포함하도록 정리 필요.

### 영향 범위
- `garmin_backfill.py`만 영향 (표준 sync/reprocess 경로는 `garmin_extractor.py` 사용, 무관)
- `garmin_extractor.py`는 `avg_vertical_ratio_pct`를 정확히 사용 중 ✅

### 필요 변경

#### 1. `garmin_v2_mappings.py` 컬럼명 수정 ✅ (2026-04-28 완료)
- line 72, 174, 251: `avg_vertical_ratio_percent` → `avg_vertical_ratio_pct`

#### 2. `garmin_backfill.py` raw SQL → whitelist 필터 적용

`garmin_backfill.py`에는 raw SQL 경로가 두 곳 존재:

**INSERT 경로** (line 127, `insert_new=True` 시):
```python
# 현재 — non-DDL 컬럼 포함 시 OperationalError
cols = ", ".join(fields.keys())
placeholders = ", ".join(["?"] * len(fields))
conn.execute(f"INSERT INTO activity_summaries ({cols}) VALUES ({placeholders})", ...)
```
→ `upsert_activity(conn, fields)` 로 교체.
`upsert_activity()`는 `_ACTIVITY_COLUMNS` 화이트리스트로 자동 필터 + ON CONFLICT 처리.
단, `_hr_zone_times`, `_power_zone_times`는 이미 `fields.pop()` 되므로 영향 없음.

**UPDATE 경로** (line 166, 기존 레코드 갱신):
```python
# 현재 — non-DDL 컬럼 포함 시 OperationalError
set_clause = ", ".join(f"{k}=?" for k in fields.keys())
conn.execute(f"UPDATE activity_summaries SET {set_clause} WHERE source='garmin' AND source_id=?", ...)
```
`upsert_activity()` 직접 사용 불가 — `exp_` → 실제 ID 업그레이드 케이스에서
`fields["source_id"] = aid`를 설정해도 ON CONFLICT가 `exp_` source_id로는 매칭되지 않음.

→ `db_helpers._ACTIVITY_COLUMNS`를 import해 필터 후 기존 UPDATE 구조 유지:
```python
from src.utils.db_helpers import _ACTIVITY_COLUMNS as _ALLOWED_COLS
# fields 필터 (non-DDL 제거)
allowed = set(_ALLOWED_COLS)
fields = {k: v for k, v in fields.items() if k in allowed}
# 이후 기존 UPDATE SQL 그대로 사용
```

**비 DDL 컬럼 처리 방침**:
- `bmr_calories`, `device_id`, `steps`, `lap_count`, `body_battery_diff`, `water_estimated_ml` —
  DDL `activity_summaries`에 없음 → 화이트리스트 필터로 자동 제거, 별도 처리 불필요
  (이후 DDL에 추가할 경우 `_ACTIVITY_COLUMNS`에도 동시 추가 필요)

---

## #P5J — Phase 5-J: distance_km → distance_m 마이그레이션

**범위 결정 (2026-04-09):**

`views_activities_table.py`는 `unified_activities.get_unified_activities()`를 통해
소스별 그룹화 + Provenance 추적(`UnifiedField`)을 수행한다.
`activity_service.get_activity_list()`는 그룹화/Provenance 기능이 없으므로
단순 전환 시 소스별 서브행 UI가 깨진다.

→ `views_activities_table.py` 및 `unified_activities.py`는 **변경 제외**.
→ Phase 7 UI 재설계 시 `activity_service`로 전환한다.

**변경 대상 (activity_summaries를 직접 읽는 소비자):**
- `src/analysis/` — report.py, trends.py, weekly_score.py, compare.py, activity_deep.py, race_readiness.py
- `src/ai/` — context_builders.py, chat_context_rich.py, chat_context_format.py, tools.py, chat_engine_rules.py
- `src/web/views_dashboard.py`, views_dashboard_loaders.py, views_report.py, views_report_loaders.py, views_race.py, views_race_enhanced.py 등

**유지 대상 (km이 올바른 단위):**
- `src/import_export/` — 외부 CSV 컬럼명 매핑
- `src/training/` — planned_workouts.distance_km (사용자 지정 km 목표)
- `src/web/views_training_*.py` — 훈련 계획 뷰
- `src/db_setup.py` — goals.distance_km, planned_workouts.distance_km 스키마
- `src/services/unified_activities.py` — Phase 7까지 현행 유지

**DoD #9**: `src/web/views_export.py` 신규 (activity CSV 내보내기, distance_m → km 변환)
**DoD #12**: `tests/test_consumer_migration.py` 신규 (~15개 스모크 테스트)

---

## #METRIC-VO2MAX — vo2max 계열 metric_name 불일치 (발견: 2026-05-08)

### 증상
VO2Max 데이터가 activity 상세, race readiness, 피트니스 트렌드에서 항상 None.

### 근본 원인
canonical은 `vo2max_activity` (scope='activity', provider='garmin')이나,
구버전 이름(`garmin_vo2max`)과 삭제된 테이블(`daily_fitness`)을 아직 참조함.

### 영향 파일 (확인 완료: 2026-05-09)
| 파일 | 문제 | 수정 방법 |
|---|---|---|
| `src/analysis/trends.py:222` | fallback metric `"vo2max"` — 이름 틀림 | `"vo2max_activity"` 로 변경 (직접 수정) |
| `src/analysis/race_readiness.py:239` | `_latest_daily(..., "garmin_vo2max")` — 이름·scope 모두 틀림 | `_latest_metric(..., "vo2max_activity")` (직접 수정) |
| `src/analysis/activity_deep.py:392-404` | `daily_fitness` 테이블 쿼리 — v11 삭제됨, 항상 None | metric_store 개별 조회로 교체 (직접 수정) |
| `src/web/views_dashboard_cards_fitness.py:212` | `vj.get("garmin_vo2max")` — 값 None | trends.py 수정 후 자동 해결 |
| `src/web/views_activity_g2_performance.py:131` | `fitness_ctx.get("garmin_vo2max")` — 값 None | activity_deep.py 수정 후 자동 해결 |

### 완료 (2026-05-09)
- `src/analysis/trends.py:222` — `"vo2max"` → `"vo2max_activity"` ✅
- `src/analysis/race_readiness.py:239-241` — `_latest_daily(..., "garmin_vo2max")` → `_latest_metric(..., "vo2max_activity")`, runalyze fallback도 `_latest_metric(..., "effective_vo2max")` ✅
- `src/analysis/activity_deep.py:391+` — `daily_fitness` 블록 → metric_store 조회로 교체 (CTL/ATL/TSB: daily scope, vo2max/evo2max/vdot: activity scope) ✅
- `src/web/views_dashboard_cards_fitness.py:212` — trends.py 수정으로 자동 해결 ✅
- `src/web/views_activity_g2_performance.py:131` — activity_deep.py 수정으로 자동 해결 ✅

---

## #METRIC-MISSING — 미구현 메트릭 코드 참조 (발견: 2026-05-08) ✅ 완료 2026-05-09

### 확인 결과 (2026-05-09)
| 메트릭 | 상태 |
|---|---|
| `running_tolerance_*` | ✅ 구현됨 — `garmin_daily_extensions.py::sync_daily_running_tolerance()`가 metric_store에 저장 |
| `sleep_end_timestamp` / `sleep_start_timestamp` | ✅ 코드 참조 없음 (정리됨) |
| `hr_zone_distribution` | ✅ `activity_deep.py:332` — `iv.get("hr_zones_detail")`로 수정 (구형 키 `hr_zone_distribution` 대체) |
| `icu_hr_zone_times` | ✅ `intervals_extractor.py`에서 metric_store에 직접 저장 |

### daily_fitness 잔존 참조 정리 (2026-05-09)
- `src/ai/suggestions.py:75` — TSB 쿼리 → metric_store 교체 ✅
- `src/web/views_dev.py:441,460` — `daily_fitness` count/group → metric_store 집계로 교체 ✅
- `src/sync/runalyze.py:_upsert_daily_fitness()` — 삭제된 테이블 쓰기 dead code 제거 ✅

