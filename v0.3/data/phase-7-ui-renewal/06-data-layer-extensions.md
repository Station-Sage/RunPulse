# Phase 7 UI Renewal — 데이터 레이어 확장 (D1~D5)

**문서 상태**: Draft v0.4  
**작성일**: 2026-06-10  
**전제 문서**: `00-diagnostic-and-direction.md`, `05-tech-architecture.md`  
**후속 문서**: `07-migration-roadmap.md`

---

## 이 문서의 목적

Phase 7 UI가 필요로 하는 데이터 레이어 변경 5건을 ADR 형식으로 정의한다.  
각 항목에 대해 현재 상태(문제), 결정, DDL, 마이그레이션 전략, 테스트 요건을 기록한다.

**구현 우선순위**

| ID | 내용 | 단계 | 차단 여부 |
|----|------|------|----------|
| **D5** | `src/services/` 서비스 레이어 | Phase 7a | 모든 API 구현 차단 |
| **D3** | `user_inputs` / `ai_feedback` 테이블 | Phase 7a | QuickInput, Coach 차단 |
| **D1** | `parent_metric_id` 트리 활성화 (Calculator 자식 메트릭 행 저장) | Phase 7a | MetricBreakdown 차단 |
| **D2** | 활동 그룹 마스터 테이블 | Phase 7b | Library Provider 비교 |
| **D4** | `athlete_profile_snapshots` 테이블 | Phase 7c | Plan 생성 고도화 |

---

## D5. 서비스 레이어 구현 (`src/services/`)

### 현재 상태 (문제)

`AUDIT-SERVICE-LAYER` 버그: 웹 뷰 40+ 곳에서 raw SQL 직접 작성.  
Flask API 라우터를 추가하면 같은 쿼리가 또 복사된다.  
**phase-5 설계에서 `activity_service`, `metrics_loader`, `wellness_loader` 등 서비스 레이어를 이미 명시했으나 미구현 상태.**  

### 결정

D5는 신규 설계가 아닌 **phase-5 서비스 레이어 설계의 구현 및 UI용 확장**이다.  
phase-5 문서(`v0.3/data/phase-5.md`)를 전제 문서로 참조하고, 여기서 정의된 인터페이스와 충돌하지 않도록 구현한다.

**데이터 접근 정책 (중요)**:
- **서비스 레이어** (`src/services/`): `db_helpers` 및 raw SQL 사용. CalcContext는 사용하지 않는다.
- **Calculator** (`src/calculators/`): `CalcContext` API만 사용한다 (ADR-009). `conn.execute()` 직접 호출 금지.

이 둘은 독립된 레이어이며 데이터 접근 정책이 다르다. 혼동하면 ADR-009 위반이 발생한다.

API 라우터는 서비스 함수만 호출한다.  
기존 뷰(`views_*.py`)는 서비스 레이어로 점진적 교체 — Phase 7a에서 API 신규 경로만 커버,  
기존 HTML 뷰는 마이그레이션 단계에서 순차 교체.

### 디렉터리 구조

```
src/services/
├── __init__.py
├── today_service.py          # Today 화면 데이터 집계
├── story_service.py          # Story 내러티브 생성 + 하이라이트
├── activity_service.py       # 활동 목록, 상세, 스트림
├── metrics_service.py        # 메트릭 조회, 분해 트리
├── wellness_service.py       # 웰니스 일별/기간 조회
├── plan_service.py           # 훈련 프로그램 CRUD + 세션 상태 조정
├── coach_service.py          # 대화 스레드, AI 호출 래핑
└── data_service.py           # 소스 상태, 동기화 트리거
```

### 서비스 인터페이스 (핵심 함수 명세)

```python
# today_service.py

def get_today_status(conn) -> TodayStatus:
    """UTRS, CIRS, TSB 등 오늘 상태 지표 반환."""

def get_today_briefing(conn) -> Briefing:
    """AI 브리핑 (캐시 우선, 없으면 생성). EvidenceQuote 배열 포함."""

def get_recent_activities(conn, limit: int = 3) -> list[ActivitySummary]:
    """최근 N개 활동 요약 반환."""

def save_checkin(conn, fatigue: int, pain: str, note: str) -> UserInput:
    """QuickInput 체크인 저장. → user_inputs 테이블 (D3)."""
```

```python
# activity_service.py

def list_activities(conn, sport=None, from_date=None, to_date=None,
                    page=1, per_page=20) -> tuple[list[Activity], int]:
    """활동 목록 + 전체 건수. v_canonical_activities 사용."""

def get_activity_detail(conn, activity_id: int) -> ActivityDetail:
    """활동 상세 + 메트릭. metric_store join."""

def get_activity_streams(conn, activity_id: int) -> StreamData:
    """activity_streams 조회 → 타입별 배열 반환."""

def get_provider_comparison(conn, activity_id: int) -> list[ComparisonRow]:
    """동일 활동의 소스별 메트릭 비교."""
```

```python
# metrics_service.py

def list_metric_groups(conn, group: str = None,
                       provider: str = None) -> list[MetricGroup]:
    """메트릭 시맨틱 그룹 목록 + 현재값."""

def get_metric_detail(conn, slug: str, period: str = '3m',
                      provider: str = None) -> MetricDetail:
    """메트릭 현재값 + 추세 + 계산 분해 트리."""

def get_metric_breakdown(conn, slug: str,
                         provider: str = None) -> BreakdownNode:
    """metric_store parent_metric_id 트리 탐색 → D1 표준화 스키마 사용."""
```

### 쿼리 경로 분리 정책 (AO-4 — 200ms 목표 보장)

아키텍처는 두 가지 데이터 경로를 제공한다:

| 경로 | 테이블 | 행 수 | 용도 |
|------|--------|-------|------|
| **Fat Summary 경로** | `activity_summaries` | ~600행 | 요약·목록·트렌드 |
| **EAV 경로** | `metric_store` | ~55k행 | 상세 드릴다운 전용 |

서비스 함수는 두 경로를 혼용하지 않는다:

```python
# 허용: 요약/목록 → activity_summaries 직조회
def list_activities(conn, ...)  # activity_summaries 단독 쿼리
def get_today_status(conn, ...)  # activity_summaries + 집계

# 허용: 상세 드릴다운 → metric_store 한정 조회
def get_metric_breakdown(conn, slug, ...)  # metric_store JOIN

# 금지: 요약 화면용 트렌드를 metric_store EAV로 전체 조회
# ❌ SELECT * FROM metric_store WHERE ...  (Today 트렌드 목적)
```

위반 시 Today 트렌드 같은 요약 화면에서 metric_store 55k행을 풀스캔해 200ms 목표 위협.

### 마이그레이션 전략

1. `src/services/` 디렉터리 생성, 각 서비스 파일 stub 작성
2. `src/api/routes_*.py`에서 서비스 함수 호출 (신규 API 경로)
3. 기존 `views_*.py`는 유지 — 서비스 함수 참조로 점진 교체 (Phase 7b~7c)

### 테스트 요건

```python
# tests/test_services.py (신규)
# - 각 서비스 함수: 최소 1개 정상 케이스 + 1개 빈 데이터 케이스
# - test_integration_realdb.py Part3(서비스 레이어) 섹션 활용
```

---

## D1. parent_metric_id 트리 활성화

### 현재 상태 (문제)

`metric_store.json_value TEXT` 컬럼에 메트릭별로 서로 다른 JSON 구조 저장.  
예시:
```json
// hr_zones_detail
{"z1": 8, "z2": 67, "z3": 20, "z4": 5, "z5": 0}

// training_load_detail (추정)
{"ctl": 68, "atl": 72, "tsb": -4}

// pace_distribution
[{"pace_bin": "5:00-5:30", "pct": 45}, ...]
```

`parent_metric_id` 컬럼이 있으나 **미사용** (NULL).  
`MetricBreakdown` 컴포넌트(C3)가 계산 트리를 일관되게 표시할 수 없다.

### 결정

**json_value 내부 스키마를 표준화하지 않는다.**  
대신 `metric_store.parent_metric_id`를 활성화해 계산 트리를 DB 행으로 표현하고,  
`metrics_service.get_metric_breakdown()`이 이를 트리로 조립한다.

**이유**: json_value 내부 형식은 메트릭마다 다르며 표준화 비용이 크다.  
트리 구조를 별도 행(`parent_metric_id` 참조)으로 표현하면 json_value 마이그레이션 없이  
MetricBreakdown이 동작한다.

### 스키마 변경 (DDL)

추가 컬럼 없음 — `parent_metric_id`는 이미 존재.  
**마이그레이션 작업**: Calculator가 합성 메트릭 저장 시 하위 메트릭도 함께 저장하도록 수정.

```python
# 예: CTL 저장 시 하위 메트릭(TSS)도 행으로 저장

# 기존 (부모만 저장)
upsert_metric(conn, scope_type='daily', scope_id=date,
              metric_name='ctl', numeric_value=68.0, provider='runpulse')

# 변경 후 (부모 + 자식 저장, parent_metric_id 연결)
parent_id = upsert_metric(conn, ..., metric_name='ctl', numeric_value=68.0)
upsert_metric(conn, ..., metric_name='tss_42d_ema',
              numeric_value=64.2, parent_metric_id=parent_id,
              text_value='42일 지수이동평균(TSS)')
```

### 영향 범위

변경이 필요한 Calculator 목록:

| Calculator | 합성 메트릭 | 하위 저장 필요 |
|-----------|-----------|--------------|
| `fitness_calculator.py` | CTL, ATL, TSB | TSS, ramp_rate |
| `utrs_calculator.py` | UTRS | HRV Index, Sleep Score, Body Battery, TSB |
| `cirs_calculator.py` | CIRS | Recovery Score 하위 지표 |
| `race_readiness_calculator.py` | Race Readiness | UTRS, CIRS, 훈련 완성도 |

### json_value 내부 스키마 문서화

MetricBreakdown에서 leaf 노드 표시 시 `json_value` 원본을 그대로 사용.  
각 메트릭의 `json_value` 구조는 Calculator 모듈 docstring에 명시 (별도 JSON Schema 불필요).

### 마이그레이션 전략

1. `upsert_metric()` 헬퍼에 `parent_metric_id` 파라미터 추가 (기본 None)
2. 위 4개 Calculator 수정 → 자식 메트릭 행 저장
   - Phase 7a: fitness_calculator (CTL/ATL/TSB)
   - Phase 7b: utrs / cirs / race_readiness
3. 기존 `parent_metric_id = NULL` 레코드는 유지 (leaf로 처리)
4. `metrics_service.get_metric_breakdown()` 구현

**고아 행 정리 (중요)**: `recompute_runpulse_metrics()` 재처리 흐름에서 부모 메트릭을 덮어쓸 때 기존 자식 행이 고아로 남지 않도록, Calculator 수정 시 자식 저장 전 기존 자식 행 삭제 또는 `upsert_metric()`에서 `parent_metric_id` 기반 덮어쓰기(ON CONFLICT DO UPDATE)를 구현해야 한다.

**metric_store 예상 행 수**: 현재 약 55k. D1 적용으로 합성 메트릭당 자식 행이 4개 내외 추가되므로, 완전 적용 후 약 60~65k로 증가 예상. 인덱스 전략은 변경 불필요.

### 테스트 요건

```python
# tests/test_metric_breakdown.py (신규)
def test_ctl_has_child_metrics():
    """CTL 저장 후 parent_metric_id로 TSS 자식 행 존재 확인."""

def test_breakdown_tree_depth():
    """UTRS → 자식 4개 (HRV, Sleep, BB, TSB) 트리 깊이 2 확인."""

def test_breakdown_missing_parent():
    """parent_metric_id = NULL인 메트릭 → 단일 leaf 노드 반환."""
```

---

## D3. user_inputs / ai_feedback 테이블 신설

### 현재 상태 (문제)

사용자의 주관적 데이터(RPE, 피로도, 통증)와 AI 피드백 저장 테이블 없음.  
`QuickInput` 컴포넌트(C5)가 저장할 곳 없음.  
Coach 대화에서 답변 품질 평가 저장 불가.

### 결정

두 테이블을 신설한다.

### DDL

```sql
-- user_inputs: 사용자 주관적 체크인 데이터
CREATE TABLE IF NOT EXISTS user_inputs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    input_date      TEXT NOT NULL,                    -- YYYY-MM-DD
    input_type      TEXT NOT NULL,                    -- 'checkin' | 'session_note' | 'race_result'
    fatigue         INTEGER,                          -- 1~10 (체크인)
    pain            TEXT,                             -- 'none'|'mild'|'moderate'|'severe'
    mood            INTEGER,                          -- 1~5 (선택)
    note            TEXT,                             -- 자유 텍스트
    activity_id     INTEGER REFERENCES activity_summaries(id),
    created_at      TEXT DEFAULT (datetime('now')),
    UNIQUE(input_date, input_type)                    -- 날짜당 타입별 1건
);

-- ai_feedback: AI 응답 품질 피드백
CREATE TABLE IF NOT EXISTS ai_feedback (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    thread_id       TEXT NOT NULL,                    -- Coach 스레드 ID
    message_id      TEXT NOT NULL,                    -- AI 메시지 ID
    rating          INTEGER,                          -- 1(나쁨) ~ 5(좋음)
    thumbs          TEXT,                             -- 'up' | 'down'
    comment         TEXT,
    created_at      TEXT DEFAULT (datetime('now')),
    UNIQUE(thread_id, message_id)
);
```

### 인덱스

```sql
CREATE INDEX IF NOT EXISTS idx_ui_date
    ON user_inputs(input_date);
CREATE INDEX IF NOT EXISTS idx_ui_type
    ON user_inputs(input_date, input_type);
CREATE INDEX IF NOT EXISTS idx_af_thread
    ON ai_feedback(thread_id);
```

### `daily_wellness` 연계

체크인 데이터(`user_inputs`)는 `daily_wellness`와 별개 테이블 유지.  
UTRS 계산 시 `user_inputs.fatigue`를 조회해 가중치 반영 가능 (Calculator 선택 사항).

```python
# wellness_service.py 에서 날짜별 조합
def get_wellness_for_date(conn, date: str) -> WellnessEntry:
    wellness = _fetch_daily_wellness(conn, date)
    user_input = _fetch_user_input(conn, date, 'checkin')
    return WellnessEntry(
        **wellness,
        user_fatigue=user_input.fatigue if user_input else None,
        user_pain=user_input.pain if user_input else None,
    )
```

### 마이그레이션 전략

1. `db_setup.py`에 `_DDL_USER_INPUTS`, `_DDL_AI_FEEDBACK` 추가
2. `DB_TABLES` 목록에 추가
3. `migrate()` 함수에서 신규 테이블 생성 (기존 DB 무영향)

### 테스트 요건

```python
# tests/test_user_inputs.py (신규)
def test_save_checkin():
    """fatigue=7, pain='mild' 저장 후 조회 일치 확인."""

def test_checkin_unique_per_day():
    """같은 날 두 번 저장 시 UNIQUE 제약 → REPLACE 동작 확인."""

def test_wellness_merge():
    """daily_wellness + user_inputs 병합 조회 결과 검증."""
```

---

## D2. 활동 그룹 마스터 테이블 신설

### 현재 상태 (문제)

`activity_summaries.matched_group_id TEXT` — 같은 활동의 멀티소스 묶음 ID.  
`v_canonical_activities` 뷰에서 `ROW_NUMBER() PARTITION BY matched_group_id`로 중복 제거.

문제:
- 그룹 마스터 테이블 없음 → 그룹 생성 날짜, 멤버 수 조회 불가
- `ProviderComparison` 컴포넌트(C4)가 그룹 ID → 소스 목록 매핑을 JOIN 없이 못 함
- 어느 소스가 "primary"인지 DB 레벨에서 불분명

### 결정

`activity_groups` 마스터 테이블 신설.  
`activity_summaries.matched_group_id`가 `activity_groups.group_id`를 참조한다.

### DDL

```sql
CREATE TABLE IF NOT EXISTS activity_groups (
    group_id        TEXT PRIMARY KEY,                 -- UUID or hash (기존 matched_group_id 값)
    primary_source  TEXT NOT NULL,                    -- 'garmin' | 'strava' | ...
    activity_date   TEXT NOT NULL,                    -- YYYY-MM-DD
    distance_m      REAL,                             -- 그룹 대표 거리 (primary 기준)
    member_count    INTEGER DEFAULT 1,
    created_at      TEXT DEFAULT (datetime('now')),
    updated_at      TEXT DEFAULT (datetime('now'))
);
```

### 기존 데이터 마이그레이션

```sql
-- 기존 matched_group_id로부터 activity_groups 행 생성
-- provider 우선순위: garmin(1) > intervals(2) > strava(3) > runalyze(4) — architecture.md is_primary 규칙과 동일
-- MIN(source) 알파벳 정렬은 garmin < intervals < runalyze < strava이므로 runalyze/strava 구간에서 우선순위와 역전됨.
INSERT OR IGNORE INTO activity_groups (group_id, primary_source, activity_date, distance_m, member_count)
SELECT
    matched_group_id AS group_id,
    CASE MIN(CASE source
             WHEN 'garmin'     THEN 1
             WHEN 'intervals'  THEN 2
             WHEN 'strava'     THEN 3
             WHEN 'runalyze'   THEN 4
             ELSE 5 END)
        WHEN 1 THEN 'garmin'
        WHEN 2 THEN 'intervals'
        WHEN 3 THEN 'strava'
        WHEN 4 THEN 'runalyze'
        ELSE MIN(source) END  AS primary_source,  -- dedup.py / v_canonical_activities 정적 순서 기준
    DATE(MIN(start_time)) AS activity_date,
    AVG(distance_m) AS distance_m,
    COUNT(*) AS member_count
FROM activity_summaries
WHERE matched_group_id IS NOT NULL
GROUP BY matched_group_id;
```

### `ProviderComparison` 서비스 연계

```python
# activity_service.py

def get_provider_comparison(conn, activity_id: int) -> list[ComparisonRow]:
    """activity_id → group_id → 같은 그룹의 모든 소스 조회."""
    group_id = _get_group_id(conn, activity_id)
    if not group_id:
        # 단일 소스 활동: 해당 소스만 반환
        return _single_source_comparison(conn, activity_id)

    members = _get_group_members(conn, group_id)  # 같은 그룹 activity_id 목록
    return _build_comparison_rows(conn, members)
```

### 마이그레이션 전략

1. `_DDL_ACTIVITY_GROUPS` DDL 추가, `migrate()` 등록
2. `assign_group_id()` 호출 시 `activity_groups` 동시 upsert — `primary_source`는 `dedup.py` / `v_canonical_activities` 뷰의 정적 순서(garmin > intervals > strava > runalyze)로 결정. `ProviderComparison.primaryReason` 컴포넌트가 표시하는 "왜 이 provider가 대표값인가"와 동일 기준을 써야 한다 (AO-3 정합성).
3. 기존 레코드 백필 스크립트 (`scripts/backfill_activity_groups.py`)

### 테스트 요건

```python
def test_group_master_created_on_match():
    """두 소스 매칭 시 activity_groups 행 자동 생성 확인."""

def test_provider_comparison_grouped():
    """같은 그룹의 두 활동 → ProviderComparison rows에 두 소스 모두 포함."""

def test_provider_comparison_single():
    """그룹 없는 활동 → single-source rows 반환."""
```

---

## D4. athlete_profile_snapshots 테이블 신설

### 현재 상태 (문제)

`athlete_profile` — 소스당 1행 현재 상태만 저장.  
`athlete_stats` — Strava/Garmin 집계 통계 스냅샷 (날짜별).

문제:
- Plan 생성 시 "러너 프로필 자동 분석" (03-screen-catalog.md 4-C)에서  
  CTL·베스트 기록 등 피트니스 히스토리가 필요하나 `athlete_profile`에 없음
- `athlete_stats`는 외부 소스 기준, RunPulse 계산 피트니스 레벨 없음

### 결정

`athlete_profile_snapshots` 테이블 신설.  
Plan 생성 또는 레이스 완료 시 현재 피트니스 상태를 스냅샷으로 저장.

### DDL

```sql
CREATE TABLE IF NOT EXISTS athlete_profile_snapshots (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot_date       TEXT NOT NULL,                -- YYYY-MM-DD
    snapshot_trigger    TEXT NOT NULL DEFAULT 'manual', -- 'plan_create' | 'race_complete' | 'weekly_auto' | 'manual'
    -- 피트니스 상태 (RunPulse 계산)
    ctl                 REAL,
    atl                 REAL,
    tsb                 REAL,
    utrs                REAL,
    vo2max_estimate     REAL,
    -- 달리기 프로필
    weekly_distance_km  REAL,                         -- 최근 8주 평균
    long_run_km         REAL,                         -- 최근 8주 최대 Long Run
    best_half_sec       INTEGER,                      -- 기록 하프마라톤 (초)
    best_marathon_sec   INTEGER,
    -- 원본 JSON (추가 지표 확장용)
    profile_json        TEXT,
    created_at          TEXT DEFAULT (datetime('now')),
    UNIQUE(snapshot_date, snapshot_trigger)           -- 같은 날 같은 트리거는 1건만
);
```

### Plan 생성 연계

```python
# plan_service.py

def generate_plan_options(conn, race_distance, race_date, goal_time) -> list[ProgramOption]:
    snapshot = _get_or_create_snapshot(conn)     # D4
    current_ctl = snapshot.ctl or _latest_ctl(conn)
    weekly_km = snapshot.weekly_distance_km or _calc_avg_weekly_km(conn)

    # VDOT 추정 → 목표 달성 가능성 평가
    vdot = estimate_vdot(current_ctl, snapshot.best_half_sec)
    ...
```

### 마이그레이션 전략

1. DDL 추가, `migrate()` 등록 (기존 DB 무영향)
2. 기존 데이터로 초기 스냅샷 1건 생성 (`scripts/init_profile_snapshot.py`)
3. Plan 생성 API 호출 시 스냅샷 자동 생성

### 테스트 요건

```python
def test_snapshot_created_on_plan_generate():
    """Plan 생성 API 호출 시 athlete_profile_snapshots 행 생성 확인."""

def test_snapshot_values_from_metric_store():
    """스냅샷 CTL 값이 metric_store 최신 CTL과 일치 확인."""
```

---

## 전체 마이그레이션 실행 순서

### Phase 7a (UI 구현 전 전제조건)

```
1. D5: src/services/ stub 생성
2. D3: user_inputs, ai_feedback DDL 추가 + migrate() 등록
3. D1: upsert_metric() parent_metric_id 파라미터 추가
       + fitness_calculator 자식 메트릭 저장 수정 (Today용 CTL/ATL/TSB)
4. src/api/ 블루프린트 생성, serve.py 등록
5. frontend/ SvelteKit 초기화
```

### Phase 7b

```
6. D1: utrs/cirs/race_readiness Calculator 자식 메트릭 저장 수정 (3개)
       — Library MetricBreakdown 노출용
7. D2: activity_groups DDL + 백필 스크립트 실행
8. activity_service.get_provider_comparison() 구현
9. metrics_service.get_metric_breakdown() 구현
```

### Phase 7c

```
8. D4: athlete_profile_snapshots DDL + 초기 스냅샷 생성
9. plan_service.generate_plan_options() 구현
```

---

## 영향 받는 파일 목록

| 파일 | 변경 유형 | 항목 |
|------|---------|------|
| `src/db_setup.py` | 추가 | D2, D3, D4 DDL + DB_TABLES + migrate() |
| `src/db_helpers.py` | 수정 | D1: `upsert_metric()` parent_metric_id 파라미터 |
| `src/calculators/fitness_calculator.py` | 수정 | D1: 자식 메트릭 저장 |
| `src/calculators/utrs_calculator.py` | 수정 | D1: 자식 메트릭 저장 |
| `src/calculators/cirs_calculator.py` | 수정 | D1: 자식 메트릭 저장 |
| `src/calculators/race_readiness_calculator.py` | 수정 | D1: 자식 메트릭 저장 |
| `src/matchers/matcher.py` | 수정 | D2: assign_group_id() → activity_groups upsert |
| `src/services/` | 신규 (phase-5 설계 구현) | D5 전체 |
| `src/api/` | 신규 | D5 소비 |
| `scripts/backfill_activity_groups.py` | 신규 | D2 백필 |
| `scripts/init_profile_snapshot.py` | 신규 | D4 초기화 |
| `tests/test_services.py` | 신규 | D5 |
| `tests/test_metric_breakdown.py` | 신규 | D1 |
| `tests/test_user_inputs.py` | 신규 | D3 |

---

## 작성 이력

- v0.4 (2026-06-10): REVIEW-02 반영 — AO-3: D2 SQL 주석·마이그레이션 전략 primary_source 근거를 `metric_priority.py` → `dedup.py / v_canonical_activities 정적 순서`로 정정; AO-4: D5에 쿼리 경로 분리 정책(activity_summaries vs metric_store) 추가
- v0.3 (2026-06-10): D1 Calculator 단계 배분을 07 로드맵과 정렬 (7a=fitness, 7b=utrs/cirs/race_readiness). 실행 순서 동기화.
- v0.2 (2026-06-10): REVIEW 반영 — D1 마이그레이션 순서 Calculator 4개로 통일(race_readiness 추가), D2 백필 primary_source를 MIN(source) 알파벳 정렬에서 metric_priority.py 우선순위 기반 CASE 식으로 수정, assign_group_id() G3 정합성 주석 추가
- v0.1 (2026-06-10): 초안 — D1~D5 ADR, DDL, 마이그레이션 전략, 테스트 요건, 실행 순서
