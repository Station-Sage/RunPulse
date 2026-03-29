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

## 전체 코드 구조 (v0.2 기준, 2026-03-25)

```
src/
├── db_setup.py              ← DB 초기화/마이그레이션 (15+ 테이블, 1026줄)
├── sync.py                  ← 동기화 CLI 진입점 + engine 후크
├── analyze.py               ← 분석 CLI 진입점
├── plan.py                  ← 훈련 계획 CLI 진입점
├── serve.py                 ← Flask 서버 (포트: 18080)
│
├── sync/                    ← v0.2에서 모듈 분리 (Garmin/Strava/Intervals 각각)
│   ├── garmin.py            ← Garmin 통합 sync 오케스트레이터
│   ├── garmin_auth.py       ← Garmin 인증
│   ├── garmin_activity_sync.py   ← 활동 + splits + backfill
│   ├── garmin_api_extensions.py  ← streams/gear/exercise_sets
│   ├── garmin_daily_extensions.py ← race_predictions/training_status/fitness/HR/stress/BB
│   ├── garmin_athlete_extensions.py ← profile/stats/personal_records
│   ├── garmin_wellness_sync.py   ← 웰니스 (수면/HRV/BB/스트레스/SPO2)
│   ├── garmin_v2_mappings.py     ← ZIP/detail 필드 매핑
│   ├── garmin_backfill.py        ← 기존 활동 보강
│   ├── garmin_helpers.py         ← 공통 헬퍼
│   ├── strava.py            ← Strava 통합 sync 오케스트레이터
│   ├── strava_auth.py       ← OAuth2 토큰 관리
│   ├── strava_activity_sync.py   ← 활동/streams/laps/best_efforts
│   ├── strava_athlete_sync.py    ← profile/stats/gear
│   ├── intervals.py         ← Intervals.icu 통합 sync 오케스트레이터
│   ├── intervals_auth.py    ← API 인증
│   ├── intervals_activity_sync.py ← 활동/intervals/streams
│   ├── intervals_athlete_sync.py  ← profile/stats
│   ├── intervals_wellness_sync.py ← 웰니스/피트니스
│   └── runalyze.py          ← Runalyze VDOT/Marathon Shape
│
├── metrics/                 ← 2차 메트릭 계산 엔진 (23개 파일)
│   ├── engine.py            ← 배치 오케스트레이터
│   ├── store.py             ← computed_metrics DB UPSERT 헬퍼
│   ├── gap.py               ← GAP + NGP (경사 보정 페이스)
│   ├── lsi.py               ← 부하 스파이크 지수
│   ├── fearp.py             ← 환경 보정 페이스
│   ├── adti.py              ← 유산소 분리 추세
│   ├── tids.py              ← 훈련 강도 분포
│   ├── relative_effort.py   ← Relative Effort (Strava 방식)
│   ├── marathon_shape.py    ← Marathon Shape (Runalyze 방식)
│   ├── acwr.py              ← 급성/만성 부하 비율
│   ├── trimp.py             ← TRIMPexp + HRSS
│   ├── monotony.py          ← Monotony + Strain
│   ├── utrs.py              ← 통합 훈련 준비도
│   ├── cirs.py              ← 복합 부상 위험
│   ├── decoupling.py        ← Aerobic Decoupling + EF
│   ├── di.py                ← 내구성 지수
│   ├── darp.py              ← 레이스 예측 (VDOT + DI)
│   ├── rmr.py               ← 러너 성숙도 레이더 (5축)
│   ├── vdot.py              ← VDOT 계산
│   ├── rtti.py              ← 러닝 내성 훈련 지수 (Sprint 5)
│   ├── wlei.py              ← 날씨 가중 노력 지수 (Sprint 5)
│   └── tpdi.py              ← 실내/야외 퍼포먼스 격차 (Sprint 5)
│
├── analysis/
│   ├── compare.py           ← 기간 비교
│   ├── trends.py            ← 주간 추세
│   ├── recovery.py          ← 회복 상태 평가
│   ├── weekly_score.py      ← 주간 종합 점수
│   ├── efficiency.py        ← Aerobic EF + Cardiac Decoupling
│   ├── zones_analysis.py    ← HR/Pace 존 분포
│   ├── activity_deep.py     ← 단일 활동 심층 분석
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
├── services/
│   └── unified_activities.py ← DB 레벨 2단계 페이지네이션 + 통합 활동 조회
│
├── import_export/
│   ├── strava_archive.py    ← Strava ZIP 아카이브 임포트
│   ├── strava_csv.py        ← Strava CSV 파싱
│   ├── garmin_csv.py        ← Garmin CSV 파싱
│   └── intervals_fit.py     ← Intervals.icu FIT 파싱
│
├── web/                     ← Flask 블루프린트 (12개 등록)
│   ├── app.py               ← Flask 앱 팩토리 + context_processor (1351줄 ⚠️)
│   ├── bg_sync.py           ← 백그라운드 동기화 스레드
│   ├── sync_ui.py           ← 병렬 동기화 SSE 프로그레스
│   ├── helpers.py           ← SVG/ECharts/bottom_nav/다크테마 (1033줄 ⚠️)
│   ├── views_dashboard.py   ← GET /dashboard
│   ├── views_dashboard_cards.py ← 대시보드 하위 카드 렌더러
│   ├── views_activities.py  ← GET /activities (필터/정렬/그룹)
│   ├── views_activity.py    ← GET /activity/deep (2차 메트릭 통합) (1529줄 ⚠️)
│   ├── views_activity_merge.py ← 활동 그룹 관리
│   ├── views_report.py      ← GET /report (기간별 분석)
│   ├── views_report_sections.py ← 레포트 하위 섹션 렌더러
│   ├── views_race.py        ← GET /race (DARP 레이스 예측)
│   ├── views_training.py    ← GET /training 메인 라우트 (3-tier: loaders → cards → 조립)
│   ├── views_training_cards.py  ← 훈련 카드 렌더러 S1~S7 (7열 캘린더, AI 추천)
│   ├── views_training_loaders.py ← 훈련 DB 로더 (goal, workouts, metrics, sync)
│   ├── views_ai_coach.py    ← GET /ai-coaching (브리핑+추천칩)
│   ├── views_wellness.py    ← GET /wellness (수면/HRV/BB 트렌드)
│   ├── views_import.py      ← GET/POST /import/strava-archive
│   ├── views_settings.py    ← GET /settings (4소스 연결) (857줄 ⚠️)
│   ├── views_export_import.py ← CSV 임포트/내보내기
│   └── views_shoes.py       ← /shoes
│
├── weather/
│   └── provider.py          ← Open-Meteo API (무료, 키 없음)
│
└── utils/
    ├── api.py               ← 외부 API 래퍼 (모든 API 호출은 여기서)
    ├── config.py            ← config.json 로드/저장
    ├── dedup.py             ← 중복 활동 매칭/그룹 관리
    ├── pace.py              ← 페이스 변환
    ├── zones.py             ← HR/Pace 존 계산
    ├── clipboard.py         ← termux-clipboard-set 래퍼
    ├── raw_payload.py       ← 원시 API 응답 저장/조회
    ├── sync_jobs.py         ← 동기화 작업 관리
    ├── sync_policy.py       ← 동기화 정책
    └── sync_state.py        ← 동기화 상태 추적

templates/
├── base.html               ← 공통 레이아웃 (stylesheet/nav/sync context_processor)
├── dashboard.html           ← 대시보드
├── ai_coaching.html         ← AI 코칭
├── race.html                ← 레이스 예측
├── generic_page.html        ← 범용 페이지 래퍼
└── macros/
    ├── gauge.html           ← 반원 게이지 SVG 매크로
    ├── radar.html           ← 레이더 차트 SVG 매크로
    └── no_data.html         ← 데이터 없음 카드 매크로
```

---

## v0.2 추가 모듈 상세

> 전체 구조는 위 "전체 코드 구조" 섹션 참조. 여기는 핵심 모듈의 함수 시그니처만 기술.

### src/metrics/ — 함수 시그니처
- 일별 메트릭: `calc_*(conn, date: str) -> float | None`
- 활동별 메트릭: `calc_*(conn, activity_id: int) -> float | None`
- 복합 결과: `calc_*(conn, ...) -> dict`
- engine: `run_for_date(conn, date)`, `run_for_date_range(conn, start, end)`, `recompute_all(conn)`
- store: `save_metric(conn, date, name, value, json)`, `load_metric(conn, date, name)`

---

## v0.2에서 대폭 수정된 기존 파일

| 파일 | 변경 내용 |
|------|-----------|
| `src/db_setup.py` | 15+ 테이블, activity_summaries 80컬럼, migrate_db 전면 확장 |
| `src/sync.py` | sync 완료 콜백 + 4소스 ThreadPoolExecutor 병렬화 |
| `src/web/app.py` | 12개 블루프린트, context_processor, template_folder |
| `src/web/bg_sync.py` | 백그라운드 sync + 메트릭 재계산 + SSE 진행률 |
| `src/web/views_activity.py` | 2차 메트릭 + FEARP + DI + classification + source 비교 |
| `src/web/views_activities.py` | 필터/정렬/그룹핑/페이지네이션 대폭 확장 |
| `src/web/helpers.py` | SVG 게이지/레이더 + ECharts CDN + bottom_nav + 다크 테마 CSS |

---

## DB 스키마 — v0.2 추가 테이블

### computed_metrics
```sql
CREATE TABLE IF NOT EXISTS computed_metrics (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    date         TEXT NOT NULL,
    activity_id  INTEGER REFERENCES activity_summaries(id),  -- NULL=일별, NOT NULL=활동별
    metric_name  TEXT NOT NULL,
    metric_value REAL,
    metric_json  TEXT,
    computed_at  TEXT DEFAULT (datetime('now')),
    UNIQUE(date, activity_id, metric_name)
);
```

### weather_data
```sql
CREATE TABLE IF NOT EXISTS weather_data (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    date         TEXT NOT NULL,
    hour         INTEGER NOT NULL DEFAULT 12,
    latitude     REAL NOT NULL,
    longitude    REAL NOT NULL,
    temp_c       REAL,
    feels_like_c REAL,
    humidity_pct INTEGER,
    wind_speed_ms REAL,
    precipitation_mm REAL,
    cloudcover_pct INTEGER,
    fetched_at   TEXT DEFAULT (datetime('now')),
    UNIQUE(date, hour, latitude, longitude)
);
```

### v0.2 추가 테이블
- `activity_laps` — 활동별 랩/스플릿 (36컬럼)
- `activity_streams` — GPS/시계열 스트림 데이터
- `activity_best_efforts` — 베스트 에포트 (1K~마라톤)
- `activity_exercise_sets` — 운동 세트 (근력/인터벌)
- `athlete_profile` — 소스별 선수 프로필
- `athlete_stats` — 누적 통계 스냅샷
- `gear` — 신발/장비
- `sync_jobs` — 동기화 작업 추적

### 핵심 테이블 (v0.2에서 대폭 확장)

**activity_summaries** (80+ 컬럼)
- 기본: `id, source, source_id, activity_type, start_time, distance_km, duration_sec`
- v0.2 추가: `name, sport_type, moving_time_sec, avg_speed_ms, max_speed_ms, aerobic_training_effect, anaerobic_training_effect, training_load, vo2max_activity, icu_*, strava_gear_id, ...`

**daily_fitness** (일별 피트니스)
- `date, source, ctl, atl, tsb, ramp_rate, garmin_vo2max, runalyze_evo2max, runalyze_vdot, runalyze_marathon_shape`

**daily_wellness** (일별 웰니스)
- `date, source, sleep_score, sleep_hours, hrv_value, hrv_sdnn, resting_hr, avg_sleeping_hr, body_battery, stress_avg, readiness_score, fatigue, mood, motivation, steps, weight_kg`

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
| 반원 게이지 | SVG (Jinja2 매크로) | UTRS, CIRS |
| 레이더 차트 | 순수 SVG polygon (Jinja2 매크로) | RMR 5축 |
| 라인 차트 | ECharts (CDN) | PMC (CTL/ATL/TSB) |
| 바 차트 | ECharts (CDN) | TIDS, TRIMP 주간, 거리 추세 |
| 수치 카드 | HTML + CSS | 요약 지표 |

### 하단 네비게이션 (6+1탭)
```
홈(대시보드) | 활동 | 레포트 | 훈련 | AI코치 | 설정 (+개발자)
```
`src/web/helpers.py`의 `bottom_nav()` 함수. `base.html`에서 `{{ bottom_nav(active_tab) }}` 호출.
레이스 예측(`/race`)은 레포트 탭 하위, 웰니스(`/wellness`)는 상단 드롭다운 nav에서 접근.

---

## 주요 규칙

1. **메트릭 데이터 없을 때**: `None` 반환 → UI에서 "데이터 수집 중" 표시 (에러 없음)
2. **DI**: 90분+ 세션 8주 3회 미달 → `None` 반환 → "장거리 세션 부족 (8주 3회 이상 필요)" 표시
3. **FEARP**: GPS 고도 없으면 `grade_factor=1.0`; 날씨 API 실패 시 `temp=15, humidity=50`
4. **CIRS**: Garmin GCT 비대칭 데이터 없으면 `asym_risk=0`, 나머지 3요소만으로 정규화 계산
5. **메트릭 계산식**: `v0.2/.ai/metrics.md` (PDF 원본) 기준 구현. 차이 시 PDF 우선
6. **두 버전 설계**: 구현은 PDF 버전으로, `metrics_by_claude.md`는 추후 비교/선택용 보존
