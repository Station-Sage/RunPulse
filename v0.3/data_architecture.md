# RunPulse 데이터 아키텍처 v0.3 — Design

## Part 1: 설계 원점으로 돌아가기

### RunPulse는 어떤 앱인가

RunPulse는 단순한 러닝 로그 앱이 아닙니다. 여러 플랫폼에 흩어진 러닝 데이터를 **하나의 통합된 뷰**로 보여주고, 그 위에서 **기존 앱이 제공하지 못하는 깊은 분석**을 하고, **AI가 코칭**하고, **ML이 패턴을 발견**하는 플랫폼입니다.

이 관점에서 데이터 모델을 다시 봅니다.

**사용자가 활동 상세 페이지를 열었을 때 보고 싶은 것:**

> "오늘 10km를 52분에 뛰었다. 평균 심박 155, 최대 178. 케이던스 172. Garmin이 말하는 Training Effect는 3.2 (유산소), VO2Max 52. Intervals가 계산한 TRIMP은 85, Efficiency Factor 1.67, Decoupling 3.2%. Strava의 Relative Effort는 78. Ground Contact Time 235ms, Vertical Ratio 7.2%. 날씨는 22도, 습도 65%. RunPulse가 이 모든 걸 종합해서 분석한 결과: 이 세션의 환경 보정 페이스(FEARP)는 5:08/km, 부상 위험도(CIRS) 32점, 내 현재 체력으로 예측한 하프마라톤 기록(DARP)은 1시간 42분."

이 경험을 제공하려면, **활동 하나에 대해 50개 이상의 지표가 통합되어 있어야** 합니다. 그 중 일부는 Garmin에서, 일부는 Strava에서, 일부는 Intervals에서, 일부는 RunPulse가 직접 계산한 것입니다. 사용자는 출처를 신경쓰지 않습니다. 하나의 화면에서 전체를 봅니다.

### 데이터 모델이 풀어야 할 진짜 문제

**문제 1: 같은 활동인데 소스마다 다른 값을 가진다**

3월 25일 저녁 달리기에 대해 Garmin은 distance=10.02km, Strava는 10.05km, Intervals는 10.03km라고 합니다. 셋 다 맞습니다. GPS 알고리즘이 다를 뿐입니다. 사용자에게는 "대표값 하나"를 보여주면서도, 소스별 원본 값에 접근할 수 있어야 합니다.

**문제 2: 같은 개념인데 소스마다 다른 이름과 단위를 가진다**

Garmin의 `aerobicTrainingEffect`와 Garmin의 자체 Training Load, Intervals의 `icu_training_load`와 `trimp`은 모두 "운동 강도/부하"를 측정하지만 계산 방법이 다릅니다. 이것들을 하나로 합칠 수 없습니다. 각각 고유한 의미가 있으니까요. 하지만 "Training Effect 계열", "Training Load 계열" 같은 **의미적 분류**는 가능합니다.

**문제 3: 같은 메트릭인데 출처가 여러 개다**

TRIMP을 예로 들면:
- Intervals.icu가 제공하는 TRIMP (그들의 알고리즘)
- RunPulse가 Banister 공식으로 자체 계산한 TRIMP
- 나중에 ML 모델이 개인화 보정한 TRIMP

이 세 가지는 모두 "TRIMP"이지만 값이 다르고, 용도도 다를 수 있습니다. 소스 TRIMP은 참조용이고, RunPulse TRIMP은 내부 분석 기준이고, ML TRIMP은 개인화 추천에 쓰일 수 있습니다.

**문제 4: 메트릭은 시간이 지나면서 진화한다**

v0.2에서 UTRS를 `sleep×0.25 + hrv×0.25 + tsb×0.20 + rhr×0.15 + sleep_consistency×0.15`로 계산했다가, v0.3에서 ML이 개인별 최적 가중치를 학습하면 계수가 바뀝니다. 같은 날짜의 UTRS가 버전별로 다를 수 있고, 과거 데이터를 새 알고리즘으로 재계산해야 할 수 있습니다.

**문제 5: 종합 운동앱으로 확장된다**

러닝 → 수영, 사이클, 근력 운동으로 확장됩니다. `activity_summaries`에 `avg_pace_sec_km`이 있으면 수영에서는 의미가 없습니다. `avg_stroke_rate`이 필요합니다. 스포츠마다 고유 메트릭이 있고, 이것을 예측해서 미리 컬럼을 만들 수 없습니다.

---

## Part 2: 아키텍처 설계

### 핵심 통찰 — "Fat Summary + Metric Store" 하이브리드

순수 EAV(Entity-Attribute-Value, `metric_name`+`metric_value` 방식)와 순수 Wide Table(80+ 컬럼) 사이의 최적점을 찾습니다.

**activity_summaries는 "두꺼운 core"로 유지합니다.** 이유는 성능과 쿼리 편의성입니다. 대시보드에서 "최근 30일 running 활동의 거리/시간/페이스/심박 추세"를 보여줄 때, EAV를 매번 pivot하면 쿼리가 복잡하고 느려집니다. 자주 조회하는 핵심 수치는 컬럼으로 두는 게 맞습니다.

하지만 "모든 소스의 모든 필드를 컬럼으로"는 안 됩니다. 기준은 이것입니다:

> **이 값이 활동 목록/대시보드/필터링/정렬에서 직접 쓰이는가?**
> 
> Yes → `activity_summaries` 컬럼
> No → `metric_store` (EAV)

Training Effect 3.2는 활동 목록에서 바로 보여줄 수 있지만, HR Zone별 시간 분포 JSON은 상세 페이지에서만 씁니다. Ground Contact Time은 카드에 보여줄 수 있지만, 날씨 이슬점 온도는 FEARP 계산 입력으로만 쓰입니다.

### 저장 계층 — 5 Layer

```
Layer 0: source_payloads        ← 외부 API 응답 원문 (절대 삭제 안 함)
Layer 1: activity_summaries     ← 통합 활동 요약 (두꺼운 core, ~45컬럼)
         daily_wellness          ← 통합 일별 웰니스 요약
         daily_fitness           ← 통합 일별 피트니스 모델
Layer 2: metric_store           ← 모든 메트릭의 단일 저장소 (소스 + RunPulse + ML)
Layer 3: activity_streams       ← 시계열 고빈도 데이터 (별도 테이블)
         activity_laps           ← 랩/스플릿 데이터
Layer 4: (Views / Materialized) ← 통합 뷰, 캐시 테이블
```

---

### Layer 0: `source_payloads`

변경 없음. 이전 설계와 동일합니다. API 응답 원문 100% 보존.

```sql
CREATE TABLE source_payloads (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    source          TEXT NOT NULL,
    entity_type     TEXT NOT NULL,
    entity_id       TEXT,
    entity_date     TEXT,
    activity_id     INTEGER,
    payload         TEXT NOT NULL,
    payload_hash    TEXT,
    endpoint        TEXT,
    parser_version  TEXT DEFAULT '1.0',
    fetched_at      TEXT DEFAULT (datetime('now')),
    UNIQUE(source, entity_type, entity_id)
);
```

---

### Layer 1: Core Summaries

#### `activity_summaries` — 통합 활동 요약 (~45컬럼)

"3개 이상 소스가 공통으로 갖는 필드만"이 아니라, **"사용자가 활동 목록/카드/필터/정렬에서 직접 보거나 쓰는 모든 핵심 수치"**를 포함합니다.

Garmin만 제공하는 Training Effect라도, 그것이 활동 카드에 표시되고 사용자가 정렬/필터에 쓴다면 여기에 둡니다. 비어있으면 NULL입니다. 그게 정상입니다. Strava 활동에 Training Effect가 NULL인 건 "데이터 없음"이지 "스키마 오류"가 아닙니다.

```sql
CREATE TABLE activity_summaries (
    -- ── 식별 ──
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    source                  TEXT NOT NULL,
    source_id               TEXT NOT NULL,
    matched_group_id        TEXT,

    -- ── 기본 정보 ──
    name                    TEXT,
    activity_type           TEXT NOT NULL,       -- 정규화됨
    sport_type              TEXT,
    start_time              TEXT NOT NULL,
    
    -- ── 거리/시간 ──
    distance_km             REAL,
    duration_sec            INTEGER,
    moving_time_sec         INTEGER,
    elapsed_time_sec        INTEGER,

    -- ── 페이스/속도 ──
    avg_pace_sec_km         REAL,
    avg_speed_ms            REAL,
    max_speed_ms            REAL,

    -- ── 심박 ──
    avg_hr                  INTEGER,
    max_hr                  INTEGER,

    -- ── 케이던스 ──
    avg_cadence             INTEGER,
    max_cadence             INTEGER,

    -- ── 파워 ──
    avg_power               REAL,
    max_power               REAL,
    normalized_power        REAL,

    -- ── 고도 ──
    elevation_gain          REAL,
    elevation_loss          REAL,

    -- ── 에너지 ──
    calories                INTEGER,

    -- ── 훈련 효과/부하 (활동 카드에 직접 표시) ──
    training_effect_aerobic     REAL,       -- Garmin
    training_effect_anaerobic   REAL,       -- Garmin
    training_load               REAL,       -- Garmin / Intervals
    suffer_score                INTEGER,    -- Strava Relative Effort

    -- ── 러닝 다이내믹스 (활동 상세 카드에 표시) ──
    avg_ground_contact_time_ms  REAL,       -- Garmin
    avg_stride_length_cm        REAL,       -- Garmin / Intervals
    avg_vertical_oscillation_cm REAL,       -- Garmin
    avg_vertical_ratio_pct      REAL,       -- Garmin

    -- ── 위치 ──
    start_lat               REAL,
    start_lon               REAL,
    end_lat                 REAL,
    end_lon                 REAL,

    -- ── 환경 ──
    avg_temperature         REAL,

    -- ── 메타 ──
    description             TEXT,
    workout_label           TEXT,
    event_type              TEXT,
    device_name             TEXT,
    gear_id                 TEXT,           -- 내부 gear 테이블 참조용

    -- ── 관리 ──
    created_at              TEXT DEFAULT (datetime('now')),
    updated_at              TEXT DEFAULT (datetime('now')),

    UNIQUE(source, source_id)
);
```

**45컬럼**. 이전 v3의 28컬럼보다 많지만, 기존 v2의 80+컬럼보다는 훨씬 적습니다. 기준은 명확합니다:

"활동 목록 테이블의 컬럼으로 표시되거나, 필터/정렬 조건으로 사용되거나, 활동 카드 상단에 즉시 표시되는 값" → 여기에 둡니다.

"HR Zone별 시간, Power Zone별 시간, 스플릿별 페이스, 디커플링 원시값, 날씨 이슬점 등 상세 분석/계산 입력으로만 쓰이는 값" → `metric_store`로 갑니다.

이 구분의 실질적 효과: `SELECT * FROM activity_summaries WHERE activity_type='running' ORDER BY start_time DESC LIMIT 20`만으로 활동 목록 화면의 모든 데이터를 가져올 수 있습니다. JOIN이 필요 없습니다.

#### `daily_wellness` / `daily_fitness`

이전 설계와 동일하게 유지합니다. 자주 쓰는 핵심 일별 수치만 컬럼으로.

---

### Layer 2: `metric_store` — 통합 메트릭 저장소

이것이 이번 설계의 **핵심 혁신**입니다.

기존에는 3개 테이블로 분리했습니다:
- `activity_detail_metrics` (활동별 소스 메트릭)
- `daily_detail_metrics` (일별 소스 메트릭)  
- `computed_metrics` (RunPulse 계산 결과)

이것을 **하나의 테이블로 통합**합니다.

#### 왜 통합하는가

TRIMP을 예로 들겠습니다.

- Intervals가 제공한 TRIMP = 85
- RunPulse가 Banister 공식으로 계산한 TRIMP = 91
- ML 모델이 개인 보정한 TRIMP = 88

이 세 값은 모두 "이 활동의 TRIMP"입니다. 차이는 **누가 계산했는가(provider)**와 **어떤 알고리즘으로(version)**입니다.

이것을 서로 다른 테이블에 넣으면 "이 활동의 모든 TRIMP 값 비교"가 3-way JOIN이 됩니다. 한 테이블에 넣으면 `WHERE metric_name='trimp' AND scope_id=? ORDER BY provider`로 끝납니다.

```sql
CREATE TABLE metric_store (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- ── 범위(Scope): 이 메트릭이 무엇에 대한 값인가 ──
    scope_type      TEXT NOT NULL,          -- 'activity' | 'daily' | 'weekly' | 'athlete'
    scope_id        TEXT NOT NULL,          -- activity: activity_summaries.id
                                            -- daily: 'YYYY-MM-DD'
                                            -- weekly: 'YYYY-Www' (ISO week)
                                            -- athlete: 'profile'
    
    -- ── 메트릭 식별 ──
    metric_name     TEXT NOT NULL,          -- 정규 이름 (canonicalized)
    category        TEXT,                   -- 분류: 'hr_zone' | 'training_load' | 'running_dynamics' | 'weather' | 'prediction' | ...
    
    -- ── 출처(Provider): 누가 이 값을 만들었는가 ──
    provider        TEXT NOT NULL,          -- 'garmin' | 'strava' | 'intervals' | 'runalyze'
                                            -- 'runpulse:v1' | 'runpulse:ml_v1' | 'runpulse:ab_test_a'
    
    -- ── 값 ──
    numeric_value   REAL,                   -- 숫자형 값
    text_value      TEXT,                   -- 텍스트형 값
    json_value      TEXT,                   -- 구조화 데이터 (JSON)
    
    -- ── 추적(Provenance) ──
    algorithm_version TEXT DEFAULT '1.0',   -- 계산 알고리즘 버전
    confidence      REAL,                   -- 신뢰도 0.0~1.0 (ML 예측 등)
    raw_name        TEXT,                   -- 소스 원본 필드명 (디버깅용)
    parent_metric_id INTEGER,               -- 이 메트릭이 다른 메트릭에서 파생된 경우
    
    -- ── 관리 ──
    is_primary      BOOLEAN DEFAULT 0,      -- 같은 metric_name에 여러 provider가 있을 때 대표값
    created_at      TEXT DEFAULT (datetime('now')),
    updated_at      TEXT DEFAULT (datetime('now')),
    
    UNIQUE(scope_type, scope_id, metric_name, provider)
);

-- 핵심 인덱스
CREATE INDEX idx_ms_scope ON metric_store(scope_type, scope_id);
CREATE INDEX idx_ms_name ON metric_store(metric_name);
CREATE INDEX idx_ms_provider ON metric_store(provider);
CREATE INDEX idx_ms_category ON metric_store(category);
CREATE INDEX idx_ms_primary ON metric_store(scope_type, scope_id, metric_name) WHERE is_primary = 1;
```

#### 이 설계가 해결하는 문제들

**문제 3 해결 — 같은 메트릭, 다른 출처**

```
scope_type=activity, scope_id=511, metric_name=trimp, provider=intervals     → 85
scope_type=activity, scope_id=511, metric_name=trimp, provider=runpulse:v1   → 91
scope_type=activity, scope_id=511, metric_name=trimp, provider=runpulse:ml_v1 → 88
```

세 값이 한 테이블에 공존합니다. `is_primary=1`인 행이 UI에서 기본으로 보이는 값입니다.

**문제 4 해결 — 메트릭 버전 진화**

```
scope_type=daily, scope_id=2026-03-25, metric_name=utrs, provider=runpulse:v1, algorithm_version=1.0 → 72
scope_type=daily, scope_id=2026-03-25, metric_name=utrs, provider=runpulse:v2, algorithm_version=2.0 → 68
```

새 알고리즘 결과를 provider를 바꿔서 저장합니다. 이전 버전을 삭제하지 않으므로 A/B 비교가 가능합니다. `is_primary`를 v2로 옮기면 UI가 자동으로 새 값을 보여줍니다.

**문제 2 해결 — 같은 개념, 다른 이름**

`category` 필드로 의미적 그룹핑이 됩니다:

```sql
SELECT * FROM metric_store 
WHERE scope_type='activity' AND scope_id=511 AND category='training_load';
-- → training_load (garmin), trimp (intervals), suffer_score (strava), trimp (runpulse:v1)
```

"이 활동의 모든 훈련 부하 관련 지표"를 한 번에 가져옵니다.

**문제 5 해결 — 종합 운동앱 확장**

수영 활동이 추가되면 `metric_name`에 `avg_stroke_rate`, `swolf`, `avg_stroke_count` 같은 값이 들어옵니다. `activity_summaries` 스키마는 변경 불필요합니다. `metric_store`에 새 metric_name이 추가될 뿐입니다.

**ML/A/B 테스트 지원**

```
provider=runpulse:ab_test_a  → UTRS 계산에 body_battery 가중치 0.30
provider=runpulse:ab_test_b  → UTRS 계산에 body_battery 가중치 0.15
```

두 버전을 동시에 저장하고, 실제 사용자 피드백/결과와 비교하여 승자를 결정할 수 있습니다.

#### provider 네이밍 규칙

```
외부 소스:      garmin | strava | intervals | runalyze
RunPulse 규칙:  runpulse:rule_v{N}       (규칙 기반 계산)
RunPulse 공식:  runpulse:formula_v{N}    (논문 기반 공식)
RunPulse ML:    runpulse:ml_{model}_{N}  (ML 모델)
RunPulse AB:    runpulse:ab_{test}_{variant}
사용자 입력:    user                      (수동 입력/보정)
```

#### `is_primary` 결정 로직

같은 `(scope_type, scope_id, metric_name)`에 여러 provider가 있을 때, 어느 것을 대표값으로 보여줄지 결정하는 우선순위:

```python
PRIMARY_PRIORITY = {
    # RunPulse ML이 있으면 최우선
    "runpulse:ml": 1,
    # RunPulse 자체 계산이 있으면 다음
    "runpulse:formula": 2,
    "runpulse:rule": 3,
    # 소스 중에서는 Garmin > Intervals > Strava > Runalyze
    "garmin": 10,
    "intervals": 11,
    "strava": 12,
    "runalyze": 13,
    # 사용자 수동 입력은 항상 최우선 오버라이드
    "user": 0,
}
```

사용자가 수동으로 "이 활동의 TRIMP은 95로 보정"하면 `provider=user`로 저장하고 `is_primary=1`이 됩니다. 원본 소스값과 RunPulse 계산값은 그대로 유지됩니다.

#### 조회 패턴

```python
def get_primary_metrics(conn, scope_type, scope_id, names=None):
    """대표 메트릭값만 가져오기 (UI 표시용)"""
    sql = """
        SELECT metric_name, numeric_value, text_value, json_value, provider
        FROM metric_store
        WHERE scope_type = ? AND scope_id = ? AND is_primary = 1
    """
    if names:
        placeholders = ",".join("?" * len(names))
        sql += f" AND metric_name IN ({placeholders})"
    return conn.execute(sql, [scope_type, scope_id] + (names or [])).fetchall()

def get_all_providers(conn, scope_type, scope_id, metric_name):
    """한 메트릭의 모든 provider 값 비교 (A/B 테스트, 디버깅)"""
    return conn.execute("""
        SELECT provider, numeric_value, algorithm_version, confidence, is_primary
        FROM metric_store
        WHERE scope_type = ? AND scope_id = ? AND metric_name = ?
        ORDER BY is_primary DESC, provider
    """, [scope_type, scope_id, metric_name]).fetchall()

def get_metrics_by_category(conn, scope_type, scope_id, category):
    """카테고리별 메트릭 (활동 상세 카드 렌더링)"""
    return conn.execute("""
        SELECT metric_name, numeric_value, json_value, provider, is_primary
        FROM metric_store
        WHERE scope_type = ? AND scope_id = ? AND category = ? AND is_primary = 1
    """, [scope_type, scope_id, category]).fetchall()
```

#### 성능 고려

"EAV는 느리다"는 우려가 있을 수 있습니다. RunPulse 규모에서 이것이 문제인지 검토합니다.

예상 데이터 볼륨: 활동 500건 × 평균 40개 메트릭 = 20,000행, 일별 365일 × 30개 메트릭 = 11,000행, 합계 약 30,000~50,000행.

SQLite는 수백만 행도 인덱스가 있으면 밀리초 단위로 응답합니다. 50,000행은 전혀 문제없습니다.

만약 "이 활동의 모든 primary 메트릭"을 자주 가져와야 한다면, Layer 4에서 materialized view나 JSON 캐시 컬럼으로 최적화할 수 있습니다. 하지만 초기에는 불필요합니다.

---

### Layer 3: 시계열 & 구조화 데이터

이것은 EAV가 부적합한 데이터입니다. 한 활동의 stream이 3,600행(1시간 × 1초)이 될 수 있으므로 별도 테이블이 맞습니다.

```sql
CREATE TABLE activity_streams (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    activity_id     INTEGER NOT NULL REFERENCES activity_summaries(id),
    source          TEXT NOT NULL,
    elapsed_sec     INTEGER NOT NULL,
    distance_m      REAL,
    heart_rate      INTEGER,
    cadence         INTEGER,
    power_watts     REAL,
    altitude_m      REAL,
    speed_ms        REAL,
    latitude        REAL,
    longitude       REAL,
    grade_pct       REAL,
    temperature_c   REAL,
    created_at      TEXT DEFAULT (datetime('now')),
    UNIQUE(activity_id, source, elapsed_sec)
);

CREATE TABLE activity_laps (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    activity_id     INTEGER NOT NULL REFERENCES activity_summaries(id),
    source          TEXT NOT NULL,
    lap_index       INTEGER NOT NULL,
    start_time      TEXT,
    duration_sec    REAL,
    distance_km     REAL,
    avg_hr          INTEGER,
    max_hr          INTEGER,
    avg_pace_sec_km REAL,
    avg_cadence     REAL,
    avg_power       REAL,
    max_power       REAL,
    elevation_gain  REAL,
    calories        INTEGER,
    lap_trigger     TEXT,
    UNIQUE(activity_id, source, lap_index)
);

CREATE TABLE activity_best_efforts (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    activity_id     INTEGER NOT NULL REFERENCES activity_summaries(id),
    source          TEXT NOT NULL,
    effort_name     TEXT NOT NULL,
    elapsed_sec     REAL,
    distance_m      REAL,
    start_index     INTEGER,
    end_index       INTEGER,
    pr_rank         INTEGER,
    UNIQUE(activity_id, source, effort_name)
);
```

---

### Layer 4: Views & 보조 테이블

```sql
-- 대표 활동 뷰 (기존과 동일한 로직)
CREATE VIEW v_canonical_activities AS
WITH grouped AS (
    SELECT *,
           ROW_NUMBER() OVER (
               PARTITION BY COALESCE(matched_group_id, 'solo_' || id)
               ORDER BY 
                   CASE source 
                       WHEN 'garmin' THEN 1 
                       WHEN 'strava' THEN 2 
                       WHEN 'intervals' THEN 3 
                       WHEN 'runalyze' THEN 4 
                   END, id
           ) as rn
    FROM activity_summaries
)
SELECT * FROM grouped WHERE rn = 1;

-- 장비 테이블
CREATE TABLE gear (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    source          TEXT NOT NULL,
    source_gear_id  TEXT NOT NULL,
    name            TEXT,
    brand           TEXT,
    model           TEXT,
    gear_type       TEXT,
    total_distance_m REAL,
    status          TEXT DEFAULT 'active',
    created_at      TEXT DEFAULT (datetime('now')),
    UNIQUE(source, source_gear_id)
);

-- 날씨 캐시
CREATE TABLE weather_cache (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    date            TEXT NOT NULL,
    hour            INTEGER DEFAULT 12,
    latitude        REAL NOT NULL,
    longitude       REAL NOT NULL,
    source          TEXT NOT NULL,
    temp_c          REAL,
    humidity_pct    INTEGER,
    dew_point_c     REAL,
    wind_speed_ms   REAL,
    wind_direction_deg INTEGER,
    condition_text  TEXT,
    fetched_at      TEXT DEFAULT (datetime('now')),
    UNIQUE(date, hour, ROUND(latitude,2), ROUND(longitude,2), source)
);

-- 동기화 작업 관리
CREATE TABLE sync_jobs (
    id              TEXT PRIMARY KEY,
    source          TEXT NOT NULL,
    from_date       TEXT,
    to_date         TEXT,
    status          TEXT DEFAULT 'pending',
    total_days      INTEGER,
    completed_days  INTEGER DEFAULT 0,
    synced_count    INTEGER DEFAULT 0,
    req_count       INTEGER DEFAULT 0,
    retry_after     TEXT,
    last_error      TEXT,
    created_at      TEXT DEFAULT (datetime('now')),
    updated_at      TEXT DEFAULT (datetime('now'))
);
```

---

### 전체 테이블 목록 (13개)

| Layer | 테이블 | 역할 | 예상 행 수 |
|-------|--------|------|-----------|
| 0 | `source_payloads` | 외부 API 원문 보존 | ~3,000 |
| 1 | `activity_summaries` | 통합 활동 요약 (45컬럼) | ~600 |
| 1 | `daily_wellness` | 일별 웰니스 요약 | ~1,500 |
| 1 | `daily_fitness` | 일별 피트니스 모델 | ~1,500 |
| 2 | `metric_store` | 모든 메트릭 통합 저장소 | ~50,000 |
| 3 | `activity_streams` | 시계열 GPS/HR/Pace | ~500,000 |
| 3 | `activity_laps` | 랩/스플릿 | ~5,000 |
| 3 | `activity_best_efforts` | 베스트 에포트 | ~2,000 |
| 4 | `gear` | 장비 | ~20 |
| 4 | `weather_cache` | 날씨 캐시 | ~1,000 |
| 4 | `sync_jobs` | 동기화 작업 | ~200 |
| 4 | `v_canonical_activities` | 대표 활동 뷰 | (view) |

기존 v2의 35+ 테이블에서 **13개로 축소**했습니다. ETL 문서의 Phase 4에서 계획했던 13개 신규 Garmin 테이블(sleep_data, training_readiness, race_predictions 등)은 전부 `metric_store`의 `scope_type='daily'`로 흡수됩니다.

---

## Part 3: ETL 파이프라인

### Extractor 패턴 (이전 설계에서 유지)

순수 함수 모듈로 분리합니다. 하지만 이번에는 **출력 형태가 달라집니다**.

```python
# src/sync/extractors/garmin_extractor.py

class GarminExtractor:
    
    SOURCE = "garmin"
    
    def extract_activity_core(self, raw: dict) -> dict:
        """→ activity_summaries INSERT용 dict"""
        return {
            "name": raw.get("activityName"),
            "activity_type": normalize_activity_type(
                raw.get("activityType", {}).get("typeKey", "unknown")
            ),
            # ... 45컬럼 전부 매핑
            # 소스에 없는 필드는 키 자체를 안 넣음 (NULL 유지)
            "training_effect_aerobic": raw.get("aerobicTrainingEffect"),
            "training_effect_anaerobic": raw.get("anaerobicTrainingEffect"),
            "training_load": raw.get("activityTrainingLoad"),
            "avg_ground_contact_time_ms": raw.get("avgGroundContactTimeMilli"),
            "avg_stride_length_cm": raw.get("avgStrideLengthCM"),
            "avg_vertical_oscillation_cm": raw.get("avgVerticalOscillationCM"),
            "avg_vertical_ratio_pct": raw.get("avgVerticalRatioPct"),
        }
    
    def extract_activity_metrics(self, raw: dict, detail: dict = None) -> list[dict]:
        """→ metric_store INSERT용 dict 리스트"""
        metrics = []
        
        def _add(name, value=None, json_val=None, category=None, raw_name=None):
            if value is None and json_val is None:
                return
            metrics.append({
                "metric_name": name,
                "category": category,
                "provider": self.SOURCE,
                "numeric_value": value,
                "json_value": json_val,
                "raw_name": raw_name or name,
            })
        
        # activity_summaries에 이미 들어간 값도 metric_store에 중복 저장?
        # → NO. 이중 저장은 하지 않음.
        # activity_summaries에 없는 값만 여기에.
        
        _add("vo2max_activity", raw.get("vO2MaxValue"), 
             category="fitness", raw_name="vO2MaxValue")
        _add("steps", raw.get("steps"),
             category="general")
        _add("body_battery_diff", raw.get("differenceBodyBattery"),
             category="recovery", raw_name="differenceBodyBattery")
        _add("water_estimated_ml", raw.get("waterEstimated"),
             category="nutrition", raw_name="waterEstimated")
        _add("intensity_mins_moderate", raw.get("moderateIntensityMinutes"),
             category="training_load")
        _add("intensity_mins_vigorous", raw.get("vigorousIntensityMinutes"),
             category="training_load")
        
        if detail:
            # HR Zones
            hr_zones = detail.get("hrTimeInZone", [])
            for i, zone_ms in enumerate(hr_zones[:5]):
                if zone_ms is not None:
                    _add(f"hr_zone_{i+1}_sec", zone_ms / 1000,
                         category="hr_zone", raw_name=f"hrTimeInZone[{i}]")
            if hr_zones:
                _add("hr_zones_detail", json_val=json.dumps(hr_zones),
                     category="hr_zone", raw_name="hrTimeInZone")
            
            # Power Zones
            pz = detail.get("powerTimeInZone", [])
            for i, zone_ms in enumerate(pz[:5]):
                if zone_ms is not None:
                    _add(f"power_zone_{i+1}_sec", zone_ms / 1000,
                         category="power_zone", raw_name=f"powerTimeInZone[{i}]")
            
            # 날씨
            weather = detail.get("weatherDTO", {})
            if weather:
                _add("weather_temp_c", weather.get("temp"),
                     category="weather")
                _add("weather_humidity_pct", weather.get("relativeHumidity"),
                     category="weather")
                _add("weather_wind_speed_ms", weather.get("windSpeed"),
                     category="weather")
                _add("weather_dew_point_c", weather.get("dewPoint"),
                     category="weather")
        
        return metrics
    
    def extract_wellness_core(self, sleep_raw, hrv_raw, bb_raw, 
                                stress_raw, summary_raw, date: str) -> dict:
        """→ daily_wellness INSERT용 dict"""
        # ...

    def extract_wellness_metrics(self, **raw_payloads) -> list[dict]:
        """→ metric_store INSERT용 dict 리스트 (scope_type='daily')"""
        metrics = []
        
        # sleep 상세
        sleep = raw_payloads.get("sleep", {})
        if sleep:
            _add("sleep_deep_sec", sleep.get("deepSleepSeconds"), category="sleep")
            _add("sleep_light_sec", sleep.get("lightSleepSeconds"), category="sleep")
            _add("sleep_rem_sec", sleep.get("remSleepSeconds"), category="sleep")
            _add("sleep_awake_sec", sleep.get("awakeSleepSeconds"), category="sleep")
            _add("avg_respiration", sleep.get("averageRespiration"), category="sleep")
            # ... 전체 sleep 필드
        
        # training readiness
        tr = raw_payloads.get("training_readiness", {})
        if tr:
            _add("training_readiness_score", tr.get("score"), category="readiness")
            _add("training_readiness_level", text_value=tr.get("level"), category="readiness")
            _add("training_readiness_sleep_factor", tr.get("sleepScoreFactorPercent"), category="readiness")
            _add("training_readiness_hrv_factor", tr.get("hrvFactorPercent"), category="readiness")
            # ...
        
        # race predictions
        rp = raw_payloads.get("race_predictions", {})
        if rp:
            _add("race_pred_5k_sec", rp.get("raceTime5K"), category="prediction")
            _add("race_pred_10k_sec", rp.get("raceTime10K"), category="prediction")
            _add("race_pred_half_sec", rp.get("raceTimeHalf"), category="prediction")
            _add("race_pred_marathon_sec", rp.get("raceTimeMarathon"), category="prediction")
        
        return metrics
```

### `activity_summaries`와 `metric_store` 사이의 이중 저장 문제

`training_effect_aerobic`이 `activity_summaries`에도 있고 `metric_store`에도 있으면 동기화 문제가 생깁니다. 원칙을 정합니다:

> **`activity_summaries`에 컬럼이 있는 값은 `metric_store`에 넣지 않는다.**
>
> `activity_summaries`는 "빠른 조회용 정규화 캐시"이고, `metric_store`는 "activity_summaries에 없는 나머지 전부"입니다.

이렇게 하면 어떤 값의 정체(source of truth)가 항상 한 곳에만 있습니다.

단, **RunPulse가 같은 개념을 자체 계산한 경우**는 다릅니다:

- Garmin의 `training_load=52` → `activity_summaries.training_load = 52`
- RunPulse가 자체 계산한 training_load=58 → `metric_store` (`provider=runpulse:formula_v1`)

이렇게 하면 `activity_summaries`는 항상 소스 원본값을 보여주고, RunPulse 계산값은 `metric_store`에서 가져옵니다. UI에서 "RunPulse가 계산한 값 vs 원본 소스값"을 비교해서 보여줄 수 있습니다.

### is_primary 자동 결정 함수

```python
# src/utils/metric_priority.py

PROVIDER_PRIORITY = [
    "user",                    # 사용자 수동 입력 (최우선)
    "runpulse:ml",             # ML 모델 결과
    "runpulse:formula",        # 논문 기반 공식
    "runpulse:rule",           # 규칙 기반 계산
    "garmin",
    "intervals",
    "strava",
    "runalyze",
]

def resolve_primary(conn, scope_type: str, scope_id: str, metric_name: str):
    """같은 (scope, metric)에 여러 provider가 있을 때 is_primary 재결정"""
    rows = conn.execute("""
        SELECT id, provider FROM metric_store
        WHERE scope_type=? AND scope_id=? AND metric_name=?
    """, [scope_type, scope_id, metric_name]).fetchall()
    
    if not rows:
        return
    
    # 모든 행의 is_primary를 0으로 리셋
    ids = [r[0] for r in rows]
    conn.execute(f"UPDATE metric_store SET is_primary=0 WHERE id IN ({','.join('?'*len(ids))})", ids)
    
    # 우선순위가 가장 높은 provider 찾기
    best_id = None
    best_rank = 999
    for row_id, provider in rows:
        for rank, prefix in enumerate(PROVIDER_PRIORITY):
            if provider == prefix or provider.startswith(prefix + ":"):
                if rank < best_rank:
                    best_rank = rank
                    best_id = row_id
                break
    
    if best_id:
        conn.execute("UPDATE metric_store SET is_primary=1 WHERE id=?", [best_id])
```

---

## Part 4: 메트릭 카테고리 체계

`metric_store.category`의 값을 체계화합니다. 이것은 UI에서 "카드 그룹"으로 직접 매핑됩니다.

```python
METRIC_CATEGORIES = {
    # ── 활동별 메트릭 ──
    "hr_zone":           "심박 존 분포",
    "power_zone":        "파워 존 분포",
    "pace_zone":         "페이스 존 분포",
    "training_load":     "훈련 부하",
    "running_dynamics":  "러닝 다이내믹스",
    "efficiency":        "효율성",
    "weather":           "날씨/환경",
    "nutrition":         "영양/수분",
    "general":           "일반",
    
    # ── 일별 메트릭 ──
    "sleep":             "수면 상세",
    "hrv":               "심박변이도",
    "stress":            "스트레스",
    "recovery":          "회복",
    "readiness":         "훈련 준비도",
    "body_composition":  "체성분",
    "fitness":           "체력 지표",
    "prediction":        "예측",
    
    # ── RunPulse 2차 메트릭 ──
    "rp_load":           "RunPulse 부하 분석",      # ACWR, LSI, Monotony, Strain
    "rp_readiness":      "RunPulse 준비도",          # UTRS
    "rp_risk":           "RunPulse 부상 위험",       # CIRS
    "rp_efficiency":     "RunPulse 효율 분석",       # ADTI, DI, Decoupling
    "rp_performance":    "RunPulse 퍼포먼스",        # FEARP, VDOT, DARP
    "rp_distribution":   "RunPulse 강도 분포",       # TIDS
    "rp_maturity":       "RunPulse 성숙도",          # RMR
    "rp_classification": "RunPulse 운동 분류",       # WorkoutType
    
    # ── 미래 확장 ──
    "cycling":           "사이클링",
    "swimming":          "수영",
    "strength":          "근력 운동",
}
```

---

## Part 5: 전체 데이터 흐름 다이어그램

```
[Garmin API] [Strava API] [Intervals API] [Runalyze API]
     │            │             │               │
     ▼            ▼             ▼               ▼
 ┌─────────────────────────────────────────────────┐
 │              Layer 0: source_payloads            │
 │         (API 응답 원문 100% 보존)                  │
 └───────────────────┬─────────────────────────────┘
                     │
                     ▼
 ┌─────────────────────────────────────────────────┐
 │         Extractors (순수 함수)                     │
 │  garmin_extractor / strava_extractor / ...       │
 │  raw JSON → core_dict + metrics_list             │
 └──────┬──────────────────────┬───────────────────┘
        │                      │
        ▼                      ▼
 ┌──────────────┐    ┌─────────────────────┐
 │   Layer 1     │    │     Layer 2          │
 │ act_summaries │    │   metric_store       │
 │ daily_well.   │    │ provider=garmin/...  │
 │ daily_fit.    │    │ scope=activity/daily │
 └──────┬───────┘    └─────────┬───────────┘
        │                      │
        └──────────┬───────────┘
                   ▼
 ┌─────────────────────────────────────────────────┐
 │         Metrics Engine (src/metrics/)             │
 │  Layer 1 + Layer 2(소스) → Layer 2(RunPulse)     │
 │  provider = runpulse:formula_v1                   │
 │  TRIMP, ACWR, UTRS, CIRS, FEARP, DARP, ...      │
 └──────────────────────┬──────────────────────────┘
                        │
                        ▼
 ┌─────────────────────────────────────────────────┐
 │         metric_store (RunPulse 결과도 여기)       │
 │  provider = runpulse:formula_v1                   │
 │  is_primary 자동 결정                              │
 └──────────────────────┬──────────────────────────┘
                        │
                        ▼
 ┌─────────────────────────────────────────────────┐
 │              UI / AI Coach / Reports             │
 │  Layer 1 (빠른 목록/필터) + metric_store(상세)    │
 │  is_primary=1인 값만 기본 표시                     │
 │  provider별 비교 뷰 제공                           │
 └─────────────────────────────────────────────────┘
```

---

## Part 6: 재처리(Reprocess) & Backfill 전략

```python
# src/sync/reprocess.py

def reprocess_all(conn, source=None):
    """Layer 0(raw) → Layer 1 + Layer 2 전체 재추출
    
    API 재호출 없이 extractor 로직만 재실행.
    extractor를 수정한 후 이 함수 한 번으로 전체 반영.
    """
    query = "SELECT id, source, entity_type, entity_id, payload, activity_id FROM source_payloads"
    params = []
    if source:
        query += " WHERE source = ?"
        params.append(source)
    
    for row in conn.execute(query, params).fetchall():
        sp_id, src, etype, eid, payload_json, activity_id = row
        raw = json.loads(payload_json)
        extractor = get_extractor(src)
        
        if etype == "activity_summary":
            core = extractor.extract_activity_core(raw)
            update_activity_summary(conn, activity_id, core)
            
        elif etype == "activity_detail" and activity_id:
            metrics = extractor.extract_activity_metrics({}, raw)
            for m in metrics:
                upsert_metric(conn, "activity", str(activity_id), src, m)
                
        elif etype in ("sleep_day", "hrv_day", "stress_day", "body_battery_day",
                        "user_summary_day", "training_readiness", "wellness_day"):
            date = row_entity_date or extract_date_from_payload(raw)
            metrics = extractor.extract_wellness_metrics(**{etype: raw})
            for m in metrics:
                upsert_metric(conn, "daily", date, src, m)
    
    conn.commit()

def recompute_runpulse_metrics(conn, date_range=None):
    """Layer 1 + Layer 2(소스) → Layer 2(RunPulse) 전체 재계산
    
    RunPulse 메트릭 알고리즘을 수정한 후 이 함수로 재계산.
    """
    from src.metrics.engine import run_for_date_range
    
    if date_range:
        start, end = date_range
    else:
        # 전체 날짜 범위
        row = conn.execute(
            "SELECT MIN(substr(start_time,1,10)), MAX(substr(start_time,1,10)) "
            "FROM activity_summaries"
        ).fetchone()
        start, end = row
    
    run_for_date_range(conn, start, end)
```

이 구조의 핵심 가치: **두 가지 독립적인 재처리 경로**가 있습니다.

1. `reprocess_all()`: Extractor 로직을 고쳤을 때 — raw에서 Layer 1+2 재추출
2. `recompute_runpulse_metrics()`: 메트릭 엔진 로직을 고쳤을 때 — Layer 1+2에서 RunPulse 결과 재계산

둘 다 외부 API를 호출하지 않습니다.

---

## Part 7: 미래 확장 시나리오 검증

이 설계가 미래 요구사항을 정말 수용하는지 구체적 시나리오로 검증합니다.

### 시나리오 A: ML 개인화 TRIMP

어느 날 RunPulse에 ML 파이프라인이 추가됩니다. 사용자의 과거 6개월 데이터를 학습해서 개인화된 TRIMP 가중치를 산출합니다.

```python
# ML이 계산한 결과 저장
upsert_metric(conn, "activity", activity_id, "runpulse:ml_trimp_v1", {
    "metric_name": "trimp",
    "category": "rp_load",
    "numeric_value": 88.3,
    "algorithm_version": "ml_trimp_v1.2",
    "confidence": 0.87,
})
# is_primary 재결정 → ML이 rule보다 우선
resolve_primary(conn, "activity", activity_id, "trimp")
```

기존 데이터 구조 변경: **없음**. 새 provider가 추가될 뿐입니다.

### 시나리오 B: 수영 활동 지원

```python
# activity_summaries: activity_type='swimming', 기존 컬럼 중 해당되는 것만 채움
# (avg_pace_sec_km은 NULL, avg_hr/calories/duration은 채움)

# metric_store: 수영 전용 메트릭
upsert_metric(conn, "activity", swim_id, "garmin", {
    "metric_name": "avg_stroke_rate",
    "category": "swimming",
    "numeric_value": 28,
})
upsert_metric(conn, "activity", swim_id, "garmin", {
    "metric_name": "swolf",
    "category": "swimming",
    "numeric_value": 42,
})
upsert_metric(conn, "activity", swim_id, "garmin", {
    "metric_name": "avg_stroke_count",
    "category": "swimming",
    "numeric_value": 18,
})
```

스키마 변경: **없음**.

### 시나리오 C: A/B 테스트 — UTRS 가중치 비교

```python
# 현재 PDF 버전
upsert_metric(conn, "daily", "2026-04-02", "runpulse:formula_v1", {
    "metric_name": "utrs",
    "category": "rp_readiness",
    "numeric_value": 72,
    "algorithm_version": "pdf_weights",
})

# Claude 연구 버전
upsert_metric(conn, "daily", "2026-04-02", "runpulse:formula_v2", {
    "metric_name": "utrs",
    "category": "rp_readiness",
    "numeric_value": 68,
    "algorithm_version": "claude_weights",
})
```

UI에서 두 값을 나란히 보여주고, 사용자가 "어느 쪽이 내 체감과 맞는지" 피드백을 줄 수 있습니다. 이 피드백이 ML 학습 데이터가 됩니다.

### 시나리오 D: 새 외부 소스 추가 (예: Coros, Polar)

```python
# 새 extractor 모듈만 추가
# src/sync/extractors/coros_extractor.py

class CorosExtractor:
    SOURCE = "coros"
    def extract_activity_core(self, raw): ...
    def extract_activity_metrics(self, raw): ...
```

DB 스키마 변경: **없음**. `source='coros'`인 행이 추가될 뿐입니다.

### 시나리오 E: 사용자가 메트릭 직접 보정

"Garmin이 이 활동의 VO2Max를 52로 계산했는데, 실험실 테스트에서 54가 나왔어."

```python
upsert_metric(conn, "activity", activity_id, "user", {
    "metric_name": "vo2max_activity",
    "category": "fitness",
    "numeric_value": 54,
    "text_value": "실험실 테스트 결과",
})
# provider=user → 최우선 → is_primary=1
resolve_primary(conn, "activity", activity_id, "vo2max_activity")
```

### 시나리오 F: 주간/월간 집계 메트릭

```python
# 주간 총 거리 — 매주 월요일 배치 계산
upsert_metric(conn, "weekly", "2026-W14", "runpulse:rule_v1", {
    "metric_name": "total_distance_km",
    "category": "rp_load",
    "numeric_value": 52.3,
})

# 주간 ACWR
upsert_metric(conn, "weekly", "2026-W14", "runpulse:formula_v1", {
    "metric_name": "acwr",
    "category": "rp_load",
    "numeric_value": 1.15,
})
```

`scope_type='weekly'`, `scope_id='2026-W14'`. 스키마 변경 없이 주간 집계가 가능합니다.

---

## Part 8: metric_names 정규 사전 (완전판)

```python
# src/utils/metric_registry.py

from dataclasses import dataclass
from typing import Optional

@dataclass
class MetricDef:
    name: str                   # 정규 이름
    category: str               # 카테고리
    unit: Optional[str]         # 단위 (표시용)
    description: str            # 설명 (한국어)
    value_type: str = "numeric" # numeric | text | json
    aliases: list = None        # 소스별 별칭 목록

METRIC_REGISTRY = {
    # ── HR Zone ──
    "hr_zone_1_sec": MetricDef("hr_zone_1_sec", "hr_zone", "sec", "심박존 1 시간",
        aliases=["icu_hr_zone_times[0]", "hr_zone_time_1", "time_in_hr_zone_1"]),
    "hr_zone_2_sec": MetricDef("hr_zone_2_sec", "hr_zone", "sec", "심박존 2 시간",
        aliases=["icu_hr_zone_times[1]", "hr_zone_time_2"]),
    "hr_zone_3_sec": MetricDef("hr_zone_3_sec", "hr_zone", "sec", "심박존 3 시간",
        aliases=["icu_hr_zone_times[2]", "hr_zone_time_3"]),
    "hr_zone_4_sec": MetricDef("hr_zone_4_sec", "hr_zone", "sec", "심박존 4 시간",
        aliases=["icu_hr_zone_times[3]", "hr_zone_time_4"]),
    "hr_zone_5_sec": MetricDef("hr_zone_5_sec", "hr_zone", "sec", "심박존 5 시간",
        aliases=["icu_hr_zone_times[4]", "hr_zone_time_5"]),
    "hr_zones_detail": MetricDef("hr_zones_detail", "hr_zone", None, "심박존 전체 상세",
        value_type="json", aliases=["icu_hr_zone_times", "hrTimeInZone"]),
    
    # ── Power Zone ──
    "power_zone_1_sec": MetricDef("power_zone_1_sec", "power_zone", "sec", "파워존 1 시간"),
    "power_zone_2_sec": MetricDef("power_zone_2_sec", "power_zone", "sec", "파워존 2 시간"),
    "power_zone_3_sec": MetricDef("power_zone_3_sec", "power_zone", "sec", "파워존 3 시간"),
    "power_zone_4_sec": MetricDef("power_zone_4_sec", "power_zone", "sec", "파워존 4 시간"),
    "power_zone_5_sec": MetricDef("power_zone_5_sec", "power_zone", "sec", "파워존 5 시간"),
    "power_zones_detail": MetricDef("power_zones_detail", "power_zone", None, "파워존 전체 상세",
        value_type="json", aliases=["icu_zone_times", "powerTimeInZone"]),
    
    # ── Pace Zone ──
    "pace_zone_times": MetricDef("pace_zone_times", "pace_zone", None, "페이스존 시간 분포",
        value_type="json", aliases=["gap_zone_times"]),
    
    # ── Training Load ──
    "trimp": MetricDef("trimp", "training_load", "AU", "TRIMPexp (Banister)",
        aliases=["icu_trimp"]),
    "hrss": MetricDef("hrss", "training_load", "점", "HR Stress Score",
        aliases=["icu_hrss"]),
    "training_load_score": MetricDef("training_load_score", "training_load", "점", "종합 훈련 부하",
        aliases=["icu_training_load"]),
    "pace_load": MetricDef("pace_load", "training_load", "AU", "페이스 기반 부하"),
    "hr_load": MetricDef("hr_load", "training_load", "AU", "심박 기반 부하"),
    "power_load": MetricDef("power_load", "training_load", "AU", "파워 기반 부하"),
    "strain_score": MetricDef("strain_score", "training_load", "점", "Training Strain"),
    
    # ── Efficiency ──
    "efficiency_factor": MetricDef("efficiency_factor", "efficiency", None, "Efficiency Factor",
        aliases=["icu_efficiency_factor", "icu_power_hr"]),
    "decoupling": MetricDef("decoupling", "efficiency", "%", "Aerobic Decoupling",
        aliases=["icu_decoupling"]),
    "variability_index": MetricDef("variability_index", "efficiency", None, "Variability Index",
        aliases=["icu_variability_index"]),
    "avg_stride": MetricDef("avg_stride", "efficiency", "m", "평균 보폭",
        aliases=["average_stride"]),
    
    # ── Running Dynamics (Garmin) ──
    "ground_contact_balance": MetricDef("ground_contact_balance", "running_dynamics", "%", "좌우 GCT 밸런스",
        aliases=["avgGroundContactBalance"]),
    
    # ── Fitness ──
    "vo2max_activity": MetricDef("vo2max_activity", "fitness", "ml/kg/min", "활동 VO2Max",
        aliases=["vO2MaxValue"]),
    "effective_vo2max": MetricDef("effective_vo2max", "fitness", "ml/kg/min", "유효 VO2Max (Runalyze)"),
    "vdot": MetricDef("vdot", "fitness", "AU", "VDOT (Jack Daniels)"),
    "marathon_shape": MetricDef("marathon_shape", "fitness", "%", "마라톤 준비도 (Runalyze)"),
    "ftp": MetricDef("ftp", "fitness", "W", "Functional Threshold Power",
        aliases=["icu_ftp", "icu_pm_ftp"]),
    
    # ── Weather (활동 시점) ──
    "weather_temp_c": MetricDef("weather_temp_c", "weather", "°C", "기온"),
    "weather_humidity_pct": MetricDef("weather_humidity_pct", "weather", "%", "습도"),
    "weather_wind_speed_ms": MetricDef("weather_wind_speed_ms", "weather", "m/s", "풍속"),
    "weather_wind_direction_deg": MetricDef("weather_wind_direction_deg", "weather", "°", "풍향"),
    "weather_dew_point_c": MetricDef("weather_dew_point_c", "weather", "°C", "이슬점"),
    
    # ── Recovery ──
    "body_battery_diff": MetricDef("body_battery_diff", "recovery", "점", "Body Battery 변화량",
        aliases=["differenceBodyBattery"]),
    "water_estimated_ml": MetricDef("water_estimated_ml", "nutrition", "ml", "예상 수분 소모량"),
    
    # ── Strava 특화 ──
    "best_efforts": MetricDef("best_efforts", "general", None, "베스트 에포트",
        value_type="json"),
    "splits_metric": MetricDef("splits_metric", "general", None, "km 스플릿",
        value_type="json"),
    "kilojoules": MetricDef("kilojoules", "general", "kJ", "에너지(kJ)"),
    "perceived_exertion": MetricDef("perceived_exertion", "general", "1-10", "주관적 운동 강도"),
    
    # ── Intervals 특화 ──
    "interval_summary": MetricDef("interval_summary", "general", None, "인터벌 요약",
        value_type="json"),
    "stream_types": MetricDef("stream_types", "general", None, "사용 가능 스트림 목록",
        value_type="text"),
    "gap": MetricDef("gap", "efficiency", "sec/km", "Grade Adjusted Pace"),
    "threshold_pace": MetricDef("threshold_pace", "fitness", "sec/km", "역치 페이스"),
    "coasting_time": MetricDef("coasting_time", "general", "sec", "코스팅 시간"),
    
    # ── Runalyze 특화 ──
    "race_prediction": MetricDef("race_prediction", "prediction", None, "레이스 예측 (Runalyze)",
        value_type="json"),
    
    # ── Daily: Sleep 상세 ──
    "sleep_deep_sec": MetricDef("sleep_deep_sec", "sleep", "sec", "깊은 수면 시간"),
    "sleep_light_sec": MetricDef("sleep_light_sec", "sleep", "sec", "얕은 수면 시간"),
    "sleep_rem_sec": MetricDef("sleep_rem_sec", "sleep", "sec", "REM 수면 시간"),
    "sleep_awake_sec": MetricDef("sleep_awake_sec", "sleep", "sec", "각성 시간"),
    "avg_respiration": MetricDef("avg_respiration", "sleep", "회/분", "평균 호흡수"),
    "avg_sleep_stress": MetricDef("avg_sleep_stress", "sleep", "점", "수면중 평균 스트레스"),
    "sleep_deep_score": MetricDef("sleep_deep_score", "sleep", "점", "깊은 수면 점수"),
    "sleep_rem_score": MetricDef("sleep_rem_score", "sleep", "점", "REM 수면 점수"),
    "sleep_recovery_score": MetricDef("sleep_recovery_score", "sleep", "점", "수면 회복 점수"),
    "avg_spo2_sleep": MetricDef("avg_spo2_sleep", "sleep", "%", "수면중 평균 SpO2"),
    
    # ── Daily: Training Readiness ──
    "training_readiness_score": MetricDef("training_readiness_score", "readiness", "점", "훈련 준비도 (Garmin)"),
    "training_readiness_level": MetricDef("training_readiness_level", "readiness", None, "훈련 준비도 등급",
        value_type="text"),
    "training_readiness_sleep_factor": MetricDef("training_readiness_sleep_factor", "readiness", "%", "수면 요인"),
    "training_readiness_hrv_factor": MetricDef("training_readiness_hrv_factor", "readiness", "%", "HRV 요인"),
    "training_readiness_acute_load_factor": MetricDef("training_readiness_acute_load_factor", "readiness", "%", "급성부하 요인"),
    
    # ── Daily: Stress 상세 ──
    "stress_high_duration": MetricDef("stress_high_duration", "stress", "sec", "고스트레스 시간"),
    "stress_medium_duration": MetricDef("stress_medium_duration", "stress", "sec", "중스트레스 시간"),
    "stress_low_duration": MetricDef("stress_low_duration", "stress", "sec", "저스트레스 시간"),
    "rest_stress_duration": MetricDef("rest_stress_duration", "stress", "sec", "휴식 스트레스 시간"),
    
    # ── Daily: Race Prediction ──
    "race_pred_5k_sec": MetricDef("race_pred_5k_sec", "prediction", "sec", "5K 예측 (Garmin)"),
    "race_pred_10k_sec": MetricDef("race_pred_10k_sec", "prediction", "sec", "10K 예측 (Garmin)"),
    "race_pred_half_sec": MetricDef("race_pred_half_sec", "prediction", "sec", "하프 예측 (Garmin)"),
    "race_pred_marathon_sec": MetricDef("race_pred_marathon_sec", "prediction", "sec", "마라톤 예측 (Garmin)"),
    
    # ── Daily: Fitness Metrics ──
    "hrv_7d_avg": MetricDef("hrv_7d_avg", "hrv", "ms", "HRV 7일 평균"),
    "avg_spo2": MetricDef("avg_spo2", "fitness", "%", "일간 평균 SpO2"),
    "skin_temp": MetricDef("skin_temp", "fitness", "°C", "피부 온도"),
    "fitness_age": MetricDef("fitness_age", "fitness", "세", "피트니스 나이"),
    "endurance_score": MetricDef("endurance_score", "fitness", "점", "지구력 점수 (Garmin)"),
    "hill_score": MetricDef("hill_score", "fitness", "점", "힐 스코어 (Garmin)"),
    "heat_acclimation_pct": MetricDef("heat_acclimation_pct", "fitness", "%", "더위 적응도"),
    "altitude_acclimation": MetricDef("altitude_acclimation", "fitness", "점", "고도 적응도"),
    "training_status": MetricDef("training_status", "fitness", None, "훈련 상태 (Garmin)",
        value_type="text"),
    "training_status_feedback": MetricDef("training_status_feedback", "fitness", None, "훈련 상태 피드백",
        value_type="text"),
    
    # ── RunPulse 2차 메트릭 ──
    "utrs": MetricDef("utrs", "rp_readiness", "점", "통합 훈련 준비도 (RunPulse)"),
    "cirs": MetricDef("cirs", "rp_risk", "점", "복합 부상 위험 (RunPulse)"),
    "lsi": MetricDef("lsi", "rp_load", None, "부하 스파이크 지수"),
    "acwr": MetricDef("acwr", "rp_load", None, "급성:만성 부하 비율"),
    "monotony": MetricDef("monotony", "rp_load", None, "훈련 단조성"),
    "training_strain": MetricDef("training_strain", "rp_load", "AU", "훈련 스트레인"),
    "adti": MetricDef("adti", "rp_efficiency", "%/주", "유산소 분리 추세"),
    "di": MetricDef("di", "rp_efficiency", None, "내구성 지수"),
    "tids": MetricDef("tids", "rp_distribution", None, "훈련 강도 분포",
        value_type="json"),
    "fearp": MetricDef("fearp", "rp_performance", "sec/km", "환경 보정 페이스"),
    "darp_5k": MetricDef("darp_5k", "rp_performance", "sec", "5K 예측 (RunPulse)"),
    "darp_10k": MetricDef("darp_10k", "rp_performance", "sec", "10K 예측 (RunPulse)"),
    "darp_half": MetricDef("darp_half", "rp_performance", "sec", "하프 예측 (RunPulse)"),
    "darp_full": MetricDef("darp_full", "rp_performance", "sec", "풀 예측 (RunPulse)"),
    "runpulse_vdot": MetricDef("runpulse_vdot", "rp_performance", "AU", "VDOT (RunPulse 계산)"),
    "rmr": MetricDef("rmr", "rp_maturity", None, "러너 성숙도 레이더",
        value_type="json"),
    "workout_type": MetricDef("workout_type", "rp_classification", None, "운동 유형 분류",
        value_type="json"),
    "relative_effort": MetricDef("relative_effort", "rp_load", "점", "Relative Effort (RunPulse 계산)"),
    "race_shape": MetricDef("race_shape", "rp_performance", "%", "레이스 준비도"),
    "rtti": MetricDef("rtti", "rp_performance", None, "러닝 내성 훈련 지수"),
    "wlei": MetricDef("wlei", "rp_performance", None, "날씨 가중 노력 지수"),
    "tpdi": MetricDef("tpdi", "rp_performance", None, "실내/야외 퍼포먼스 격차"),
}

# 역방향 매핑 (소스 이름 → 정규 이름)
_ALIAS_MAP = {}
for canonical, mdef in METRIC_REGISTRY.items():
    if mdef.aliases:
        for alias in mdef.aliases:
            _ALIAS_MAP[alias] = canonical

def canonicalize(raw_name: str) -> str:
    return _ALIAS_MAP.get(raw_name, raw_name)

def get_category(metric_name: str) -> str:
    mdef = METRIC_REGISTRY.get(metric_name)
    return mdef.category if mdef else "unknown"

def get_unit(metric_name: str) -> str:
    mdef = METRIC_REGISTRY.get(metric_name)
    return mdef.unit if mdef else None
```

이 레지스트리는 **앱 전체의 Single Source of Truth**입니다. UI에서 단위를 보여줄 때, 한국어 설명을 보여줄 때, extractor에서 정규화할 때, 모두 이 레지스트리를 참조합니다.

---

## Part 9: 구현 로드맵

### Phase 1 — 기반 (1주)

1. `db_setup.py` 전면 재작성 (13개 테이블)
2. `metric_registry.py` 작성 (정규 사전)
3. `metric_priority.py` 작성 (is_primary 로직)
4. `db_helpers.py` 작성 (upsert 함수들)

### Phase 2 — Extractors (1주)

5. `garmin_extractor.py`
6. `strava_extractor.py`
7. `intervals_extractor.py`
8. `runalyze_extractor.py`
9. Extractor 단위 테스트 (fixture 기반)

### Phase 3 — Sync 재작성 (1주)

10. `garmin_activity_sync.py` 전면 재작성
11. `garmin_wellness_sync.py` 전면 재작성
12. `strava_activity_sync.py` 전면 재작성
13. `intervals_activity_sync.py` 전면 재작성
14. `reprocess.py`

### Phase 4 — Metrics Engine 정비 (3일)

15. `workout_classifier.py` → metric_store 직접 조회
16. 나머지 metrics/*.py → 정규 이름 기반 조회
17. `engine.py` → metric_store에 `provider=runpulse:formula_v1`로 저장

### Phase 5 — UI 적응 (3일)

18. `unified_activities.py` → Layer 1 + metric_store 조합
19. `views_activities_table.py` → 변경 반영
20. `views_activity_*.py` → metric_store category별 카드 렌더링

### Phase 6 — 초기 적재 & 검증 (2일)

21. 전체 sync 실행
22. Reprocess 테스트
23. Computed metrics 전체 계산
24. Sanity check

---

이것이 최종 설계입니다. `activity_summaries`를 "두꺼운 core"로 유지하면서도 무한 확장 가능한 `metric_store`, 소스 원본과 RunPulse 계산과 ML 결과를 동일 구조에서 관리하는 provider 체계, 그리고 API 재호출 없는 재처리 파이프라인. 이 세 가지가 핵심입니다.

