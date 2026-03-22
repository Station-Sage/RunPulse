# v0.2 아키텍처

---

## 전체 구조 변화

```
v0.1 (완료): 4소스 sync → DB → 기초분석 → Flask 기본 웹
                                               ↓
v0.2 (진행): + [2차 메트릭 엔진] + [고도화 대시보드 UI]
               computed_metrics 테이블
               weather_data 테이블
```

---

## v0.1 기존 코드 구조 (건드리지 않는 파일들)

```
src/
├── db_setup.py              ← DB 초기화/마이그레이션 (v0.2에서 테이블 추가)
├── sync.py                  ← 동기화 CLI 진입점 (v0.2에서 후크 추가)
├── analyze.py               ← 분석 CLI 진입점
├── plan.py                  ← 훈련 계획 CLI 진입점
├── serve.py                 ← Flask 서버 (포트: 18080)
│
├── sync/
│   ├── garmin.py            ← Garmin Connect 활동/웰니스/생체역학
│   ├── strava.py            ← Strava OAuth2 활동/스트림/상세
│   ├── intervals.py         ← Intervals.icu CTL/ATL/TSB/HR존
│   └── runalyze.py          ← Runalyze VDOT/Marathon Shape/Race Prediction
│
├── analysis/
│   ├── compare.py           ← 기간 비교
│   ├── trends.py            ← 주간 추세, ACWR
│   ├── recovery.py          ← 회복 상태 평가
│   ├── weekly_score.py      ← 주간 종합 점수 (0-100)
│   ├── efficiency.py        ← Aerobic EF + Cardiac Decoupling
│   ├── zones_analysis.py    ← HR/Pace 존 분포
│   ├── activity_deep.py     ← 단일 활동 심층 분석 (v0.2에서 확장)
│   ├── race_readiness.py    ← 레이스 준비도
│   └── report.py            ← 마크다운 리포트
│
├── ai/
│   ├── ai_context.py        ← 분석 데이터 → AI 프롬프트 변환
│   ├── ai_schema.py         ← AI 훈련 계획 JSON 스키마
│   ├── ai_parser.py         ← AI 응답 파싱
│   ├── briefing.py          ← AI 코치 브리핑 자동 생성
│   ├── suggestions.py       ← 추천 칩 생성
│   └── prompt_templates/    ← 10종 프롬프트 템플릿 (.txt)
│
├── training/
│   ├── goals.py             ← 레이스 목표 CRUD
│   ├── planner.py           ← 주간/월간 훈련 계획
│   └── adjuster.py          ← 컨디션 기반 계획 조정
│
├── web/
│   ├── app.py               ← Flask 앱, 블루프린트 등록 (v0.2에서 추가)
│   ├── bg_sync.py           ← 백그라운드 동기화 스레드 (v0.2에서 후크 추가)
│   ├── views_activity.py    ← /activities, /activity/deep (v0.2에서 확장)
│   ├── views_activity_merge.py ← 활동 그룹 관리
│   ├── views_settings.py    ← /settings, /connect/*
│   ├── views_export_import.py ← CSV/GPX 임포트/내보내기
│   ├── views_shoes.py       ← /shoes
│   └── helpers.py           ← connected_services() 등 공통 헬퍼
│
└── utils/
    ├── api.py               ← 외부 API 래퍼 (모든 API 호출은 여기서)
    ├── config.py            ← config.json 로드/저장
    ├── dedup.py             ← 중복 활동 매칭/그룹 관리
    ├── pace.py              ← 페이스 변환
    ├── zones.py             ← HR/Pace 존 계산
    └── clipboard.py         ← termux-clipboard-set 래퍼
```

---

## v0.2 새로 추가되는 모듈

### src/metrics/ — 2차 메트릭 계산 엔진
```
src/metrics/
├── __init__.py
├── lsi.py           ← 부하 스파이크 지수 (today_load / rolling_21day_avg)
├── fearp.py         ← 환경 보정 페이스 (날씨×고도×경사)
├── adti.py          ← 유산소 분리 추세 (8주 선형 회귀)
├── tids.py          ← 훈련 강도 분포 (폴라리제드/피라미드/건강유지)
├── acwr.py          ← 급성/만성 부하 비율
├── trimp.py         ← TRIMPexp 자체 계산 (intervals.icu 폴백)
├── utrs.py          ← 통합 훈련 준비도 (5요소 가중합)
├── cirs.py          ← 복합 부상 위험 (ACWR×0.4 + Mono×0.2 + Spike×0.3 + Asym×0.1)
├── decoupling.py    ← Aerobic Decoupling (Pa:HR 전/후반 비교)
├── di.py            ← 내구성 지수 (pace/HR 비율법, 90분+ 세션 필요)
├── darp.py          ← 레이스 예측 (VDOT + DI 보정)
├── rmr.py           ← 러너 성숙도 레이더 (5축)
└── engine.py        ← 배치 오케스트레이터 (sync 완료 후 자동 실행)
```

각 함수 시그니처:
- 일별 메트릭: `compute_*(conn, date: str) -> float | None`
- 활동별 메트릭: `compute_*(conn, activity_id: int) -> float | None`
- 복합 결과: `compute_*(conn, ...) -> dict`
- engine: `recompute_recent(conn, days: int = 7) -> None`

### src/weather/ — Open-Meteo 날씨 API
```
src/weather/
├── __init__.py
└── provider.py      ← get_weather(lat, lon, date_str) -> dict
                        {temp_c, humidity_pct, wind_kmh, ...}
                        결과는 weather_data 테이블에 캐싱
```

### src/web/ — 새 뷰 블루프린트
```
src/web/
├── views_dashboard.py     ← GET /dashboard (홈 대시보드)
├── views_report.py        ← GET /report?period=week (분석 레포트)
├── views_race.py          ← GET /race?distance=half (레이스 예측)
└── views_training_plan.py ← GET /training (훈련 계획 캘린더)
```

### templates/ — 새 Jinja2 매크로/템플릿
```
templates/
├── macros/
│   ├── nav.html      ← 하단 5탭 네비게이션 매크로
│   ├── gauge.html    ← 반원 게이지 SVG 매크로 (UTRS/CIRS)
│   └── radar.html    ← 레이더 차트 SVG 매크로 (RMR 5축)
├── dashboard.html
├── report.html
├── race.html
└── training_plan.html
```

---

## v0.2 수정되는 기존 파일

| 파일 | 변경 내용 |
|------|-----------|
| `src/db_setup.py` | `computed_metrics`, `weather_data` 테이블 추가; `migrate_db()` 업데이트 |
| `src/sync.py` | sync 완료 콜백에 `engine.recompute_recent(conn)` 추가 |
| `src/web/app.py` | 새 블루프린트 4개 등록; `/` → `/dashboard` 리다이렉트 |
| `src/web/bg_sync.py` | 백그라운드 sync 완료 후 메트릭 재계산 후크 |
| `src/web/views_activity.py` | `activity_deep`에 FEARP 섹션 + 2차 메트릭 카드 추가 |

---

## DB 스키마 — v0.2 추가 테이블

### computed_metrics (새 테이블)
```sql
CREATE TABLE IF NOT EXISTS computed_metrics (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    date         TEXT NOT NULL,                     -- YYYY-MM-DD
    metric_name  TEXT NOT NULL,                     -- 'utrs', 'cirs', 'acwr', 'lsi', 'di', 'rmr', ...
    metric_value REAL,                              -- 단일 숫자 (복합값은 metric_json)
    metric_json  TEXT,                              -- JSON (rmr, tids 등 복합 구조)
    computed_at  TEXT DEFAULT (datetime('now')),
    UNIQUE(date, metric_name)                       -- ON CONFLICT DO UPDATE
);
```

저장 패턴:
- 일별 단일값: `('2026-03-22', 'utrs', 72.5, NULL)`
- 활동별: metric_name에 activity_id 포함 `('2026-03-22', 'fearp_12345', 285.3, NULL)`
- 복합값: `('2026-03-22', 'rmr', NULL, '{"유산소용량":80,"역치강도":70,...}')`

### weather_data (새 테이블)
```sql
CREATE TABLE IF NOT EXISTS weather_data (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    activity_id  INTEGER REFERENCES activity_summaries(id),
    date         TEXT,
    lat          REAL,
    lon          REAL,
    temp_c       REAL,
    humidity_pct REAL,
    wind_kmh     REAL,
    source       TEXT DEFAULT 'open-meteo',
    fetched_at   TEXT DEFAULT (datetime('now'))
);
```

### 기존 핵심 테이블 (v0.1, 수정 없음)

**activity_summaries** (통합 활동 목록)
- 주요: `id, source, source_id, activity_type, start_time, distance_km, duration_sec, avg_pace_sec_km, avg_hr, matched_group_id`

**activity_detail_metrics** (활동별 소스 고유 지표)
- 주요: `id, activity_id, source, metric_name, metric_value, metric_json`
- 예: garmin `aerobic_te`, strava `suffer_score`, intervals `trimp`, runalyze `vdot`

**daily_fitness** (일별 피트니스)
- 주요: `date, ctl, atl, tsb, vo2max_precise, hrv_weekly_average, body_battery_delta, sleep_score, resting_hr`

**daily_wellness** (일별 웰니스)
- 주요: `date, source, sleep_score, hrv_value, resting_hr, body_battery, stress_avg`

---

## 데이터 흐름

### sync 완료 후 자동 메트릭 계산
```
sync 완료 (src/sync.py 또는 bg_sync.py)
    └─► engine.recompute_recent(conn, days=7)
            ├─ lsi.compute(conn, date)      → computed_metrics
            ├─ tids.compute(conn, date)     → computed_metrics
            ├─ adti.compute(conn, date)     → computed_metrics
            ├─ acwr.compute(conn, date)     → computed_metrics
            ├─ utrs.compute(conn, date)     → computed_metrics
            ├─ cirs.compute(conn, date)     → computed_metrics
            └─ di.compute(conn)             → computed_metrics

활동 sync 시
    └─► fearp.compute(conn, activity_id)
            └─ weather.get_weather(lat, lon, date) → weather_data 캐싱
            → activity_detail_metrics
```

### 웹 요청 흐름
```
브라우저 → Flask
    /dashboard → views_dashboard.py
        └─ computed_metrics + daily_fitness + activity_summaries 조회
        └─ Jinja2 렌더링 (Chart.js 데이터 JSON 임베딩)

    /report?period=week → views_report.py
        └─ 기간별 집계 + TIDS + TRIMP 차트 데이터

    /race?distance=half → views_race.py
        └─ DARP 계산 + DI 조회 + 페이스 전략

    /activity/deep/<id> → views_activity.py (기존 + FEARP 섹션 추가)
```

---

## 웹 UI 디자인 시스템

### 색상 (다크 테마)
```css
background: linear-gradient(135deg, #1a1a2e, #16213e, #0f3460);
accent-cyan:   #00d4ff   /* UTRS, 긍정 지표 */
accent-green:  #00ff88   /* 안전, 좋음 */
accent-red:    #ff4444   /* 경고, 위험 */
accent-orange: #ffaa00   /* 주의 */
card: background: rgba(255,255,255,0.05); border-radius: 20px; backdrop-filter: blur(10px);
```

### 차트 컴포넌트
| 컴포넌트 | 구현 방식 | 용도 |
|---------|-----------|------|
| 반원 게이지 | SVG + CSS conic-gradient | UTRS, CIRS |
| 레이더 차트 | 순수 SVG polygon | RMR 5축 |
| 라인 차트 | Chart.js (CDN) | PMC (CTL/ATL/TSB) |
| 바 차트 | Chart.js (CDN) | TIDS, TRIMP 주간 |
| 수치 카드 | HTML + CSS | 요약 지표 |

### 하단 네비게이션 (5탭)
```
홈(대시보드) | 활동 | 훈련 | AI 코치 | 설정
```
`templates/macros/nav.html`에 Jinja2 매크로로 공통화.
사용법: `{% from 'macros/nav.html' import bottom_nav %}{{ bottom_nav('dashboard') }}`

---

## 주요 규칙

1. **메트릭 데이터 없을 때**: `None` 반환 → UI에서 "데이터 수집 중" 표시 (에러 없음)
2. **DI**: 90분+ 세션 8주 3회 미달 → `None` 반환 → "장거리 세션 부족 (8주 3회 이상 필요)" 표시
3. **FEARP**: GPS 고도 없으면 `grade_factor=1.0`; 날씨 API 실패 시 `temp=15, humidity=50`
4. **CIRS**: Garmin GCT 비대칭 데이터 없으면 `asym_risk=0`, 나머지 3요소만으로 정규화 계산
5. **메트릭 계산식**: `design/.ai/metrics.md` (PDF 원본) 기준 구현. 차이 시 PDF 우선
6. **두 버전 설계**: 구현은 PDF 버전으로, `metrics_by_claude.md`는 추후 비교/선택용 보존
