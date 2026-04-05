# Phase 5 Service Layer 설계

> 3개 서비스 모듈의 함수 시그니처, 반환 구조, SQL 패턴을 정의한다.
> 모든 서비스는 sqlite3.Connection을 첫 인자로 받고, dict/list를 반환한다.

## 공통 규칙

1. 서비스 함수는 DB에서 읽기만 한다 (쓰기 없음)
2. SQL은 직접 작성하되, db_helpers의 읽기 함수가 있으면 우선 사용
3. metric_store 조회 시 반드시 is_primary = 1 포함 (비교 뷰 제외)
4. distance_m은 서비스에서 km 변환하지 않음 — template_helpers가 담당
5. metric_name은 항상 snake_case (calculator가 저장한 그대로)
6. 반환 dict의 key는 snake_case, 한글 없음

## 사용 가능한 db_helpers 읽기 함수

    get_primary_metric(conn, scope_type, scope_id, metric_name) -> dict|None
    get_primary_metrics(conn, scope_type, scope_id, names=None) -> list[dict]
    get_all_providers(conn, scope_type, scope_id, metric_name) -> list[dict]
    get_metrics_by_category(conn, scope_type, scope_id, category) -> list[dict]
    get_metric_history(conn, ...) -> list[dict]
    get_activity(conn, activity_id) -> dict|None
    get_activity_list(conn, ...) -> list[dict]

---

## 1. activity_service.py

### get_activity_list

시그니처:

    def get_activity_list(
        conn,
        filters: dict = None,
        sort_by: str = "start_time",
        sort_dir: str = "DESC",
        page: int = 1,
        per_page: int = 20,
    ) -> dict:

filters 키: activity_type, date_from, date_to, min_distance_m, search

반환 구조:

    {
        "activities": [
            {
                "id": int,
                "source": str,
                "name": str,
                "activity_type": str,
                "start_time": str,
                "distance_m": float,
                "duration_sec": int,
                "avg_pace_sec_km": float,
                "avg_hr": int,
                "elevation_gain": float,
                "training_load": float,
                ... (activity_summaries 44컬럼 전부)
            },
        ],
        "total": int,
        "page": int,
        "per_page": int,
        "total_pages": int,
    }

SQL 패턴:

    SELECT * FROM v_canonical_activities
    WHERE activity_type = ? AND start_time BETWEEN ? AND ?
    ORDER BY start_time DESC
    LIMIT ? OFFSET ?

설계 결정: workout_type은 목록에서 제외, 상세에서만 표시.
목록에 필요하면 나중에 LEFT JOIN 추가.

### get_activity_detail

시그니처:

    def get_activity_detail(conn, activity_id: int) -> dict:

반환 구조:

    {
        "core": {
            activity_summaries 44컬럼
        },
        "metrics_by_category": {
            "rp_load": [
                {
                    "metric_name": "trimp",
                    "numeric_value": 91.2,
                    "text_value": null,
                    "json_value": null,
                    "provider": "runpulse:formula_v1",
                    "confidence": 0.9,
                    "unit": "AU",
                    "description": "심박 기반 훈련 부하 점수"
                },
                ...
            ],
            "rp_performance": [...],
            "rp_efficiency": [...],
            (11개 rp_* 카테고리)
        },
        "source_comparison": {
            "garmin": {"distance_m": 10020, "avg_hr": 155, ...},
            "strava": {"distance_m": 10050, "avg_hr": 154, ...},
        },
        "semantic_groups": {
            "training_load": {
                "display_name": "훈련 부하",
                "strategy": "show_all",
                "members": [
                    {"metric_name": "trimp", "provider": "runpulse:formula_v1", "value": 91.2},
                    {"metric_name": "trimp", "provider": "intervals", "value": 85.0},
                    {"metric_name": "training_load", "provider": "garmin",
                     "value": 52.0, "source_table": "activity_summaries"},
                ],
            },
            ...
        },
        "streams": [...] | null,
        "laps": [...] | null,
        "best_efforts": [...] | null,
    }

SQL 패턴 — core:

    SELECT * FROM activity_summaries WHERE id = ?

SQL 패턴 — metrics_by_category (is_primary만):

    SELECT metric_name, category, numeric_value, text_value, json_value,
           provider, confidence, algorithm_version
    FROM metric_store
    WHERE scope_type = 'activity' AND scope_id = CAST(? AS TEXT) AND is_primary = 1
    ORDER BY category, metric_name

SQL 패턴 — source_comparison:

    SELECT * FROM activity_summaries WHERE matched_group_id = ?

SQL 패턴 — semantic_groups (모든 provider):

    SELECT metric_name, provider, numeric_value, text_value, json_value
    FROM metric_store
    WHERE scope_type = 'activity' AND scope_id = CAST(? AS TEXT)
    ORDER BY metric_name, provider

SQL 패턴 — streams:

    SELECT * FROM activity_streams WHERE activity_id = ? ORDER BY elapsed_sec

SQL 패턴 — laps:

    SELECT * FROM activity_laps WHERE activity_id = ? ORDER BY lap_index

SQL 패턴 — best_efforts:

    SELECT * FROM activity_best_efforts WHERE activity_id = ? ORDER BY distance_m

metrics_by_category 조립 로직:

    db_helpers.get_primary_metrics()로 전체 가져온 후 category별 그룹핑.
    각 메트릭에 metric_registry에서 unit, description을 추가.

semantic_groups 조립 로직:

    metric_groups.SEMANTIC_GROUPS를 순회하며,
    metric_store의 모든 provider 행 + activity_summaries 컬럼(training_load, suffer_score 등)을
    매칭하여 members 리스트를 구성.
    activity_summaries 컬럼 값은 source_table: "activity_summaries"로 구분.

### get_activity_streams

시그니처:

    def get_activity_streams(conn, activity_id: int, source: str = None) -> list[dict]:

반환: [{elapsed_sec, distance_m, heart_rate, cadence, ...}, ...]

### get_activity_trend

시그니처:

    def get_activity_trend(
        conn, metric_name: str, days: int = 90, activity_type: str = None
    ) -> list[dict]:

반환: [{"date": str, "value": float, "activity_id": int}, ...]

SQL 패턴:

    SELECT substr(a.start_time, 1, 10) AS date,
           m.numeric_value AS value,
           a.id AS activity_id
    FROM metric_store m
    JOIN v_canonical_activities a ON CAST(m.scope_id AS INTEGER) = a.id
    WHERE m.scope_type = 'activity'
      AND m.metric_name = ?
      AND m.is_primary = 1
      AND a.start_time >= date('now', ?)
    ORDER BY a.start_time

### activity_service.py DoD

- [ ] get_activity_list: v_canonical_activities에서 필터/정렬/페이징 동작
- [ ] get_activity_detail: core + metrics_by_category + source_comparison + semantic_groups 반환
- [ ] metrics_by_category의 category가 metric_store에 저장된 category 기준
- [ ] semantic_groups에 activity_summaries 컬럼(training_load, suffer_score)도 포함
- [ ] get_activity_streams: elapsed_sec 순 정렬
- [ ] get_activity_trend: 날짜+값+activity_id 반환, is_primary=1 필터
- [ ] scope_id는 항상 TEXT로 CAST
- [ ] distance_m 그대로 반환 (km 변환 안 함)

---

## 2. dashboard_service.py

### get_dashboard_data

시그니처:

    def get_dashboard_data(conn, date: str = None) -> dict:

date: 기준일 (기본: 오늘)

반환 구조:

    {
        "date": str,
        "wellness": {
            daily_wellness 15컬럼
        },
        "readiness": {
            "utrs": {"value": 72.3, "level": "양호",
                     "components": {...}, "confidence": 0.8},
            "cirs": {"value": 28.1, "level": "낮음"},
            "crs": {"value": 65.0, "level": "보통"},
        },
        "training_status": {
            "ctl": float, "atl": float, "tsb": float,
            "ramp_rate": float, "acwr": float,
            "training_phase": str,
        },
        "recent_activities": [
            {"id": int, "name": str, "start_time": str,
             "distance_m": float, "duration_sec": int},
        ],
        "race_predictions": {
            "darp_5k": int, "darp_10k": int,
            "darp_half": int, "darp_marathon": int,
        },
        "weekly_summary": {
            "run_count": int,
            "total_distance_m": float,
            "total_duration_sec": int,
            "avg_pace_sec_km": float,
        },
    }

readiness 조립:

    get_primary_metric(conn, "daily", date, "utrs") -> utrs_row
    utrs_row["numeric_value"] → value
    utrs_row["json_value"] → components (JSON parse)
    interpret_metric_level("utrs", value) → level

training_phase 판단 로직:

    tsb > 15  → "tapering"
    tsb > 5   → "recovering"
    ramp_rate > 3   → "building"
    ramp_rate < -3  → "detraining"
    그 외     → "maintaining"

race_predictions:

    get_primary_metrics(conn, "daily", date,
        names=["darp_5k", "darp_10k", "darp_half", "darp_marathon"])

weekly_summary:

    SELECT COUNT(*), SUM(distance_m), SUM(duration_sec)
    FROM v_canonical_activities
    WHERE activity_type = 'running'
      AND start_time >= date(?, '-7 days')

### get_pmc_chart_data

시그니처:

    def get_pmc_chart_data(conn, days: int = 90) -> list[dict]:

반환: [{"date": str, "ctl": float, "atl": float, "tsb": float}, ...]

SQL 패턴 (RunPulse PMC — metric_store에서):

    SELECT scope_id AS date, metric_name, numeric_value
    FROM metric_store
    WHERE scope_type = 'daily'
      AND metric_name IN ('ctl', 'atl', 'tsb')
      AND is_primary = 1
      AND scope_id >= date('now', '-90 days')
    ORDER BY scope_id

결과를 date별로 pivot하여 반환.

소스별 PMC 비교가 필요하면 daily_fitness 테이블 사용:

    SELECT date, source, ctl, atl, tsb FROM daily_fitness
    WHERE date >= date('now', '-90 days')
    ORDER BY date, source

### get_daily_metric_chart

시그니처:

    def get_daily_metric_chart(conn, metric_name: str, days: int = 30) -> list[dict]:

반환: [{"date": str, "value": float}, ...]

SQL 패턴:

    SELECT scope_id AS date, numeric_value AS value
    FROM metric_store
    WHERE scope_type = 'daily'
      AND metric_name = ?
      AND is_primary = 1
      AND scope_id >= date('now', ?)
    ORDER BY scope_id

### dashboard_service.py DoD

- [ ] get_dashboard_data: wellness + readiness + training_status + recent + predictions + weekly 반환
- [ ] readiness의 level이 metric_dictionary의 범위 해석과 일치
- [ ] training_phase 판단 로직 동작
- [ ] get_pmc_chart_data: metric_store에서 ctl/atl/tsb 조회, date별 pivot
- [ ] get_daily_metric_chart: scope_type='daily' is_primary=1 조회
- [ ] race_predictions: darp_5k~darp_marathon 반환 (없으면 null)

---

## 3. wellness_service.py

### get_wellness_detail

시그니처:

    def get_wellness_detail(conn, date: str = None) -> dict:

반환 구조:

    {
        "date": str,
        "core": {
            daily_wellness 15컬럼
        },
        "metrics_by_category": {
            "sleep": [
                {"metric_name": "sleep_deep_sec", "numeric_value": 3600, ...},
                {"metric_name": "sleep_rem_sec", ...},
            ],
            "stress": [...],
            "hrv": [...],
            "readiness": [...],
        },
        "readiness_summary": {
            "utrs": {...},
            "cirs": {...},
        },
    }

SQL 패턴 — core:

    SELECT * FROM daily_wellness WHERE date = ?

SQL 패턴 — daily metrics by category:

    SELECT metric_name, category, numeric_value, text_value, json_value,
           provider, confidence
    FROM metric_store
    WHERE scope_type = 'daily' AND scope_id = ?
      AND is_primary = 1
      AND category IN ('sleep', 'stress', 'hrv', 'readiness', 'wellness',
                        'rp_readiness', 'rp_risk', 'rp_recovery')
    ORDER BY category, metric_name

참고: 소스 메트릭(sleep_deep_sec 등)은 category='sleep',
RunPulse 메트릭(utrs 등)은 category='rp_readiness'.
둘 다 포함해야 완전한 상세 뷰가 됨.

### get_wellness_trend

시그니처:

    def get_wellness_trend(conn, days: int = 30) -> dict:

반환 구조:

    {
        "dates": [str, ...],
        "sleep_score": [int|null, ...],
        "hrv_last_night": [float|null, ...],
        "resting_hr": [int|null, ...],
        "body_battery_high": [int|null, ...],
        "avg_stress": [int|null, ...],
        "utrs": [float|null, ...],
        "weight_kg": [float|null, ...],
    }

구현 방식:

    1. daily_wellness에서 날짜 범위 조회 → core 컬럼 채움
    2. metric_store에서 utrs 시계열 조회 → utrs 채움
    3. 날짜 리스트를 기준으로 정렬, 빈 날짜는 null

### wellness_service.py DoD

- [ ] get_wellness_detail: core + metrics_by_category + readiness_summary 반환
- [ ] metrics_by_category에 소스 메트릭(sleep 등)과 RP 메트릭(utrs 등) 모두 포함
- [ ] get_wellness_trend: daily_wellness 컬럼 + metric_store daily 메트릭 혼합 시계열
- [ ] None 처리: 특정 날짜에 데이터 없으면 null (빈 값 아님)
