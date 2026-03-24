# RunPulse UI 설계 명세서 (v0.2)

> **기준**: `design/app-UI/*.html` 프로토타입 기반
> **목적**: Jinja2 템플릿 구현 시 참조하는 단일 진실 소스
> **구현 방식**: Flask `render_template()` + Jinja2 템플릿

---

## 1. 공통 디자인 시스템

### 1-1. 색상 토큰 + 폰트 + 브레이크포인트

```css
/* 배경 */
background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);

/* 강조색 (다크 테마 기준, 3번 문서 라이트 팔레트 대신 유지) */
--cyan:   #00d4ff   /* 주요 지표, 긍정, 활성 */
--green:  #00ff88   /* 안전, 완료, 양호 */
--orange: #ffaa00   /* 주의 */
--red:    #ff4444   /* 경고, 위험 */

/* 카드 */
background: rgba(255,255,255,0.05);
border: 1px solid rgba(255,255,255,0.1);
border-radius: 20px;
backdrop-filter: blur(10px);

/* 텍스트 */
primary: #fff
secondary: rgba(255,255,255,0.7)
muted: rgba(255,255,255,0.5)

/* 폰트 (3번 문서 권장) */
font-family: 'Noto Sans KR', 'Inter', -apple-system, sans-serif;
/* CDN: <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700&family=Inter:wght@400;600&display=swap"> */

/* 반응형 브레이크포인트 (3번 문서 권장) */
/* 모바일:  max-width: 320px (소형)  */
/* 태블릿: max-width: 768px          */
/* 소형 데스크톱: max-width: 1024px  */
/* 대형 데스크톱: max-width: 1440px  */
/* 현재 프로젝트 주력: 320~768px (Termux 모바일 웹) */
```

### 1-2. 공통 컴포넌트 CSS 패턴

| 컴포넌트 | 클래스명 | 특징 |
|---------|---------|------|
| 섹션 타이틀 | `.section-title::before` | 좌측 4px 그라디언트 바 |
| 배지 | `.badge` | border-radius: 20px, 컬러별 `.badge-{type}` |
| 그라디언트 텍스트 | `.score-value` | cyan→green, `-webkit-background-clip: text` |
| 카드 호버 | `.score-card:hover` | `translateY(-5px)` |
| 프라이머리 버튼 | `.action-btn.primary` | `gradient(#00d4ff, #00ff88)` |
| 경고 배너 | `.cirs-alert` | 상단 고정 배너, orange(>50) / red(>75) |
| 지도 컨테이너 | `.map-container` | 활동 상세 전체 화면 60%, Mapbox GL JS |

### 1-4. 외부 라이브러리 CDN

| 라이브러리 | 용도 | CDN | 폴백 |
|-----------|------|-----|------|
| **Apache ECharts** | 모든 차트 (PMC, TRIMP, 추세 등) | `https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js` | SVG 정적 이미지 |
| **Mapbox GL JS** | 활동 궤적 지도 시각화 | `https://api.mapbox.com/mapbox-gl-js/v3/mapbox-gl.js` | Leaflet.js 폴백 |
| **Noto Sans KR + Inter** | 한국어·영문 폰트 | Google Fonts CDN | 시스템 폰트 |

> **Chart.js 대신 ECharts 선택 이유** (3번 문서 권장):
> - 줌·패닝 내장 (PMC 차트에서 필요)
> - 한국어 텍스트 렌더링 안정
> - 고성능 캔버스 렌더링 (모바일 60fps)
>
> **Mapbox GL JS 주의사항**: Free tier에서 월 25,000 지도 로드까지 무료. 개인 프로젝트 범위에서 충분.
> Mapbox 토큰은 `config.json`에 저장, 코드에 하드코딩 금지.

### 1-3. 공유 Jinja2 매크로 파일

| 파일 | 내용 |
|------|------|
| `templates/macros/base.html` | `page_shell(title)` — head, 공통 CSS, body 래퍼 |
| `templates/macros/nav.html` | `bottom_nav(active_tab)` — 5탭 하단 네비게이션 |
| `templates/macros/gauge.html` | `half_gauge(value, max, color)` — 반원 게이지 SVG |
| `templates/macros/radar.html` | `radar_chart(axes, values)` — 5축 레이더 SVG |
| `templates/macros/no_data.html` | `no_data_card(title, message)` — "데이터 수집 중" 카드 |

---

## 2. 네비게이션 구조

### 2-1. 하단 탭 바 (7탭, 개발자 탭은 릴리즈 시 제외)

```
홈  |  활동  |  레포트  |  훈련  |  AI코치  |  설정  |  [개발자]
🏠      🏃       📊       🗓️       🤖        ⚙️        🛠️

/dashboard  /activities  /report  /training  /ai-coach  /settings  /dev
```

> architecture.md의 `홈|활동|훈련|AI코치|설정` + 원래 spec의 `레포트` 탭 통합 → 6탭.
> `개발자` 탭은 개발 중에만 노출. 릴리즈 시 `bottom_nav`에서 조건부 제거.
> 모바일 7탭: 아이콘+레이블 최소화, 각 탭 가로 ~50px 기준.

### 2-2. 탭별 하위 화면

| 탭 | 탭 키 | 메인 URL | 하위 화면 | 비고 |
|----|-------|---------|---------|------|
| 홈 | `dashboard` | `/dashboard` | `/wellness` (회복·웰니스 상세) | |
| 활동 | `activities` | `/activities` | `/activity/deep/<id>` (활동 상세) | |
| 레포트 | `report` | `/report` | `/race` (레이스 예측) | |
| 훈련 | `training` | `/training` | `/training/new` (새 훈련 추가) | |
| AI코치 | `ai-coach` | `/ai-coach` | — | |
| 설정 | `settings` | `/settings` | `/shoes` (신발 목록) | `/sync-status`·`/import`·`/import-export`는 설정 내 섹션으로 통합 (Sprint 8) |
| 개발자 | `dev` | `/dev` | `/db`, `/payloads`, `/config`, `/analyze/*` | **릴리즈 시 제외** |

> **중복 정리 원칙**
> - 동일 기능이 여러 탭에서 진입 가능한 경우 → 한 탭에 귀속, 나머지는 **링크**(네비게이션 없음)
> - 예: 레이스 예측은 레포트 탭 귀속. 훈련 탭의 "DARP 반영" 버튼은 `/race`로 이동하는 링크.
> - 예: 웰니스는 홈 탭 귀속. 대시보드에서 "상세 →" 링크로 진입.
> - 예: 활동 상세는 활동 탭 귀속. 대시보드·레포트에서도 동일 URL로 이동.

### 2-3. `bottom_nav(active_tab)` 매크로 스펙

```html
<!-- 사용법 -->
{% from 'macros/nav.html' import bottom_nav %}
{{ bottom_nav('dashboard') }}
{# active_tab: 'dashboard'|'activities'|'report'|'training'|'ai-coach'|'settings'|'dev' #}
```

**HTML 구조**:
```
.bottom-nav (position: fixed, bottom:0, backdrop-filter: blur)
  .nav-items (max-width: 720px, margin: auto, flex, justify: space-around)
    .nav-item[.active] × 7 (flex-col, align-center, padding: 6px 10px)
      .nav-item-icon (font-size: 20px)
      .nav-item-label (font-size: 10px)
    <!-- 개발자 탭은 IS_DEV 플래그 또는 config.dev_mode=true 일 때만 렌더 -->
    {% if config.dev_mode %}
    .nav-item[data-tab="dev"]
    {% endif %}
```

---

## 3. 화면별 명세

### 화면 → 탭 귀속 전체 맵

| 탭 | 화면 (spec 섹션) | URL | 역할 |
|----|-----------------|-----|------|
| 홈 | 3-1 | `/dashboard` | 메인 — UTRS/CIRS 게이지, PMC 차트, RMR 레이더, 최근 활동 |
| 홈 | 3-1-C | `/wellness` | 서브 — 회복·웰니스 상세 (대시보드에서 링크) |
| 활동 | 3-1-B | `/activities` | 메인 — 통합 활동 목록, 필터, 그룹 |
| 활동 | 3-3 | `/activity/deep/<id>` | 서브 — 활동 상세 (활동 목록·대시보드 최근 활동에서 링크) |
| 레포트 | 3-2 | `/report` | 메인 — 기간별 집계 분석, TIDS, TRIMP, AI 인사이트 |
| 레포트 | 3-4 | `/race` | 서브 — DARP 레이스 예측 (레포트 메인에서 링크) |
| 훈련 | 3-6 | `/training` | 메인 — 훈련 계획 캘린더 |
| 훈련 | — | `/training/new` | 서브 — 새 훈련 항목 추가 |
| AI코치 | 3-5 | `/ai-coach` | 메인 — 브리핑, 추천 칩, 채팅 |
| 설정 | 3-7 | `/settings` | 메인 — 소스연동·동기화·데이터관리·앱설정 |
| 설정 | 3-7-B | `/shoes` | 서브 — 신발 목록 |
| 개발자 | 3-8 | `/dev` | 메인 — DB·Payload·Config·레거시 분석 (**릴리즈 시 제외**) |

> **중복 방지 원칙**: 동일 기능은 한 탭에만 귀속. 다른 탭에서는 링크로만 접근.
> - AI 훈련 추천 텍스트: 훈련 탭에 요약 표시 + "AI 코치에게 더 묻기 →" 링크 (/ai-coach)
> - 레이스 예측: 레포트 탭 귀속. 훈련 탭·AI코치에서는 `/race` 링크 버튼으로만 접근.
> - 활동 상세: 활동 탭 귀속. 대시보드·레포트에서도 동일 URL 링크.

---

### 3-1. 대시보드 (`/dashboard`)

**파일**: `templates/dashboard.html`
**뷰**: `src/web/views_dashboard.py`
**소스 파일**: `design/app-UI/dashboard.html`

#### 섹션 구성 (위→아래)

```
[CIRS 경고 배너]  ← 조건부, 상단 고정 (3번 문서 권장)
  {% if cirs > 75 %} .cirs-alert.danger  "⚡ 부상 위험 높음 — 오늘은 완전 휴식을 권장합니다."
  {% elif cirs > 50 %} .cirs-alert.warning  "⚠ 부상 위험 주의 — 훈련 강도를 낮추세요."
  {% endif %}

Header
  ├── 로고: "🏃‍♂️ RunPulse"
  └── 날짜: {{ today }}

[Score Row] 2-col grid
  ├── UTRS 카드  (3번 문서 하위 요인 추가)
  │   ├── half_gauge(utrs, 100, 'utrs')
  │   ├── 수치: {{ utrs }}  상태 레이블: {{ utrs_label }}
  │   └── 하위 요인 2×3 grid (소형 수치)
  │       수면 {{ utrs_sleep }} / HRV {{ utrs_hrv }} / 부하 {{ utrs_load }}
  │       심박 {{ utrs_hr }} / 이력 {{ utrs_history }} / 스트레스 {{ utrs_stress }}
  └── CIRS 카드
      ├── half_gauge(cirs, 100, 'cirs')
      ├── 수치: {{ cirs }}
      └── ACWR: {{ acwr }}

[PMC 차트] ECharts Line  ← Chart.js → ECharts 교체 (줌/패닝 지원)
  └── 라벨: {{ pmc_labels }}  (최근 90일 날짜)
      datasets: CTL(cyan), ATL(green), TSB(orange)
      데이터: {{ pmc_ctl }}, {{ pmc_atl }}, {{ pmc_tsb }}
      위험 구간 배경: TSB < -20이면 주황, < -30이면 빨강

[RMR 레이더] 순수 SVG 5축  (3번 문서: 이전 기간 오버레이 추가)
  └── 축: 유산소용량 / 역치강도 / 지구력 / 동작효율성 / 회복력
      현재값: {{ rmr_values }}  (0~100 리스트 5개)
      3개월 전: {{ rmr_prev_values }}  (없을 시 생략)

[최근 활동] 최대 5개  (3번 문서 활동 카드 스타일)
  └── 각 항목: 날씨/장소 + [지도 썸네일] + 4-stat grid
              {{ act.date }} / {{ act.distance_km }}km / {{ act.avg_pace }} / {{ act.avg_hr }}
              배지: FEARP / CIRS / UTRS 기여
      링크: /activity/deep/{{ act.id }}

bottom_nav('dashboard')
```

#### Jinja2 컨텍스트 변수

| 변수 | 타입 | DB 출처 | 없을 때 |
|------|------|---------|---------|
| `today` | str | `date.today()` | — |
| `utrs` | int\|None | `computed_metrics` WHERE metric_name='utrs' | None |
| `utrs_label` | str | utrs 수치 기반 분기 (85~100 준비됨, 70~84 양호, 55~69 주의, <55 휴식권장) | "데이터 수집 중" |
| `utrs_sleep` | int\|None | computed_metrics metric_name='utrs_sub' JSON['sleep'] | None |
| `utrs_hrv` | int\|None | 위 JSON['hrv'] | None |
| `utrs_load` | int\|None | 위 JSON['load'] | None |
| `utrs_hr` | int\|None | 위 JSON['hr'] | None |
| `utrs_history` | int\|None | 위 JSON['history'] | None |
| `utrs_stress` | int\|None | 위 JSON['stress'] | None |
| `cirs` | int\|None | `computed_metrics` WHERE metric_name='cirs' | None |
| `acwr` | float\|None | `computed_metrics` WHERE metric_name='acwr' | None |
| `pmc_labels` | list[str] | `daily_fitness`.date 최근 90일 | [] |
| `pmc_ctl` | list[float] | `daily_fitness`.ctl | [] |
| `pmc_atl` | list[float] | `daily_fitness`.atl | [] |
| `pmc_tsb` | list[float] | `daily_fitness`.tsb | [] |
| `rmr_values` | list[float] 5개 | `computed_metrics` WHERE metric_name='rmr' (JSON) | [0,0,0,0,0] |
| `rmr_prev_values` | list[float] 5개 | 3개월 전 rmr (없으면 None) | None |
| `recent_acts` | list[UnifiedActivity] | `fetch_unified_activities(page=1, page_size=5)` | [] |

#### Graceful Fallback 규칙

- `utrs is None` → `half_gauge` 자리에 `no_data_card("UTRS", "sync 후 표시됩니다")` 표시
- `pmc_labels == []` → Chart.js 캔버스 숨기고 `no_data_card` 표시
- `rmr_values == [0,0,0,0,0]` → 레이더 자리에 `no_data_card` 표시
- `recent_acts == []` → "최근 활동 없음" 안내 메시지

---

### 3-1-B. 통합 활동 목록 (`/activities`) ← v0.1 기존, 5탭 "활동" 탭 본체

**파일**: 기존 `views_activities.py` (inline HTML 유지, v0.2에서 다크 테마로 전환 예정)
**Sprint**: Sprint 3에서 다크 테마 CSS 적용 + 하단 nav 추가, 기능 변경 없음

#### 섹션 구성

```
[필터 폼] (접기/펼치기)
  ├── 소스 필터: 전체 | Garmin | Strava | Intervals | Runalyze
  ├── 종목 필터: 전체 | 달리기 | 수영 | 근력 | 하이킹
  ├── 날짜 범위: {{ date_from }} ~ {{ date_to }}
  ├── 거리 범위: {{ min_dist }} ~ {{ max_dist }} km
  ├── 페이스 범위: {{ min_pace }} ~ {{ max_pace }} /km
  ├── 시간 범위: {{ min_dur }} ~ {{ max_dur }} 분
  ├── 검색어: {{ q }}
  └── 정렬: 날짜|거리|시간|페이스|심박 + 오름차순|내림차순

[요약 바]
  └── 총 {{ total_count }}개 활동 / 총 {{ total_dist_km }} km

[활동 테이블] (행 클릭 → /activity/deep/<id>)
  각 행:
  ├── 소스 배지: 색상 원형 (Garmin=#0055b3, Strava=#FC4C02, Intervals=#00884e, Runalyze=#7b2d8b)
  ├── 날짜·시간
  ├── 종목 아이콘 + 이름
  ├── 거리 (km)
  ├── 페이스 (/km)
  ├── 시간
  ├── 심박수
  ├── 고도 상승
  ├── 캘로리
  └── 그룹 표시: 동일 활동 소스 수 배지 (클릭 → 서브행 펼침)

[그룹 서브행] (펼침 시)
  └── 각 소스별 상세 값 비교 테이블
      병합/분리 버튼 (POST /activities/merge, /activities/ungroup)

[자동 그룹 버튼]
  └── POST /activities/auto-group → 기간 내 중복 활동 자동 매칭

[페이지네이션]
  └── ← 이전 / 페이지 {{ page }}/{{ total_pages }} / 다음 →
```

#### 기능 URL
| 기능 | URL | 메서드 |
|------|-----|--------|
| 활동 목록 | `/activities` | GET |
| 활동 병합 | `/activities/merge` | POST (JSON body: `{ids: []}`) |
| 활동 분리 | `/activities/ungroup` | POST (JSON body: `{id: int}`) |
| 자동 그룹 | `/activities/auto-group` | POST |

---

### 3-1-C. 회복·웰니스 (`/wellness`) ← v0.1 기존, 누락 추가

**파일**: 기존 `views_wellness.py` (inline HTML 유지, v0.2에서 다크 테마 적용 예정)
**접근**: 대시보드 회복 카드의 "상세 →" 링크

#### 섹션 구성

```
Header: "회복·웰니스"  날짜 선택: {{ date }}  ← →

[훈련 준비도 카드]
  └── training_readiness_score: {{ readiness }}  (0~100)
      해석 텍스트

[회복 상태 카드]
  ├── recovery_score: {{ recovery_score }}
  ├── grade: {{ grade }} (excellent|good|moderate|poor)
  └── 색상 배지

[수면 카드]
  ├── 수면 점수: {{ sleep_score }}
  ├── 수면 시간: {{ sleep_hours }}h
  └── REM/깊은 수면 비율

[HRV 카드]
  ├── HRV: {{ hrv_value }} ms
  ├── RMSSD: {{ hrv_sdnn }} ms
  └── 추세 (주간 평균 대비)

[기타 지표 카드]
  ├── 바디 배터리: {{ body_battery }}
  ├── 스트레스 평균: {{ stress_avg }}
  ├── SpO2: {{ spo2_avg }}%
  └── 안정 심박: {{ resting_hr }} bpm

[7일 추세 카드]
  └── 최근 7일 recovery_score 라인 차트 (SVG 또는 Chart.js)

[활동 카드]
  ├── 걸음 수: {{ steps }}
  └── 체중: {{ weight_kg }} kg

bottom_nav('dashboard')  {# 웰니스는 홈 탭 하위 #}
```

#### Jinja2 컨텍스트 변수

| 변수 | DB 출처 | 없을 때 |
|------|---------|---------|
| `date` | URL 파라미터 또는 오늘 | today |
| `readiness` | `daily_wellness`.`training_readiness_score` (Garmin 상세) | None |
| `recovery_score` | `daily_wellness`.`readiness_score` | None |
| `sleep_score` | `daily_wellness`.`sleep_score` | None |
| `hrv_value` | `daily_wellness`.`hrv_value` | None |
| `body_battery` | `daily_wellness`.`body_battery` | None |
| `resting_hr` | `daily_wellness`.`resting_hr` | None |
| `trend_data` | 최근 7일 `daily_wellness` | [] |

---

### 3-2. 분석 레포트 (`/report`)

**파일**: `templates/report.html`
**뷰**: `src/web/views_report.py`
**소스 파일**: `design/app-UI/analysis_report.html`

#### 섹션 구성

```
Header: "분석 레포트"

[기간 선택 탭] (GET 파라미터 ?period=week)
  오늘 | 이번 주* | 이번 달 | 이번 분기 | 올해 | 최근 1년 | 사용자 정의

[레포트 헤더 카드]
  └── 제목: {{ period_label }}
      메타: {{ date_range }} / {{ act_count }}개 활동 / {{ total_duration }}

[요약 카드] 2×2 grid
  ├── 총 거리: {{ total_dist_km }} km  (change: {{ dist_change_pct }}%)
  ├── 총 시간: {{ total_duration_str }}  (change: {{ dur_change_pct }}%)
  ├── 평균 UTRS: {{ avg_utrs }}  (change: {{ utrs_change }})
  └── CIRS 평균: {{ avg_cirs }}  (change: {{ cirs_change }})

[활동 추세 차트] Chart.js Line
  └── 주별 거리 추세: {{ trend_labels }}, {{ trend_dist }}

[훈련 강도 분포 (TIDS)] 가로 분할 바
  └── Easy {{ tids_easy }}% / Tempo {{ tids_tempo }}% / Threshold {{ tids_threshold }}%
      설명: {{ tids_comment }}

[주간 부하 (TRIMP)] 바 차트
  └── {{ trimp_labels }} (요일), {{ trimp_values }}

[세부 메트릭 테이블]
  └── 페이스 / 심박수 / Aerobic Decoupling / Training Effect / FEARP

[AI 인사이트] 3개 카드
  └── {{ insights }}  list[{icon, title, body}]

[액션 버튼]
  └── PDF 다운로드(미구현) / 훈련 플랜 조정 →/training

bottom_nav('report')
```

#### Jinja2 컨텍스트 변수

| 변수 | 타입 | 없을 때 |
|------|------|---------|
| `period` | str | 'week' |
| `period_label` | str | "주간 분석 레포트" |
| `date_range` | str | — |
| `act_count` | int | 0 |
| `total_dist_km` | float | 0.0 |
| `total_duration_str` | str | "0:00:00" |
| `dist_change_pct` | float\|None | None |
| `avg_utrs` | float\|None | None |
| `avg_cirs` | float\|None | None |
| `trend_labels` | list[str] | [] |
| `trend_dist` | list[float] | [] |
| `tids_easy/tempo/threshold` | float | 0 |
| `tids_comment` | str | "" |
| `trimp_labels` | list[str] | ['월','화','수','목','금','토','일'] |
| `trimp_values` | list[float] | [0]*7 |
| `metrics_table` | list[dict] | [] |
| `insights` | list[dict] | [] |

---

### 3-3. 활동 상세 (`/activity/deep/<id>`)

**파일**: 기존 `views_activity.py` 확장 (현재 inline HTML → Jinja2 미전환)
**소스 파일**: `design/app-UI/activity_detail.html`
**Sprint**: Sprint 4 (현재 Sprint 3에서는 스킵)

> Sprint 3에서는 기존 views_activity.py 그대로 유지.
> Sprint 4에서 아래 섹션을 추가한다.

#### 추가될 섹션 (Sprint 4)

```
[지도 — 전체 화면 상단 60%]  (3번 문서 모바일 활동 상세 권장)
  Mapbox GL JS 궤적 표시 + FEARP 히트맵 오버레이 (선택)
  → Mapbox 토큰 없으면 Leaflet.js 폴백 (OpenStreetMap)

[핵심 메트릭 — 수평 스크롤 카드]  (3번 문서 권장)
  거리 / 페이스 / 시간 / 심박수 / 고도 / 케이던스  (각 카드 swipe 이동)

[FEARP 섹션] — 신규
  ├── 실제 페이스: {{ actual_pace }}  vs  보정 페이스: {{ fearp_pace }}  (평지 15°C 기준)
  └── 환경 영향 분해 배지: 기온 {{ temp_delta }}초 / 습도 {{ humidity_delta }}초 / 경사 {{ grade_delta }}초

[2차 메트릭 배지 행]  (3번 문서 권장: FEARP·CIRS·DI 배지)
  FEARP {{ fearp_pace }} | CIRS {{ cirs_label }} | DI {{ di_score }}

[2차 메트릭 상세 카드]
  ├── UTRS 기여도: {{ utrs_contribution }}
  ├── CIRS 부상 위험: {{ cirs_score }} / {{ cirs_label }}
  ├── Aerobic Decoupling: {{ decoupling_pct }}%
  ├── Training Effect: {{ te_score }}
  └── Running Dynamics: GCT {{ gct_ms }}ms
```

#### Jinja2 변수 (Sprint 4 추가분)

| 변수 | 출처 |
|------|------|
| `fearp_pace` | `activity_detail_metrics` WHERE metric_name='fearp' |
| `fearp_factors` | `weather_data` JOIN `activity_summaries` |
| `utrs_contribution` | `computed_metrics` |
| `cirs_score` | `computed_metrics` |
| `decoupling_pct` | `activity_detail_metrics` WHERE metric_name='decoupling' |
| `te_score` | `activity_detail_metrics` WHERE metric_name='training_effect' (Garmin) |
| `gct_ms` | `activity_detail_metrics` WHERE metric_name='avg_gct' (Garmin) |

---

### 3-4. 레이스 예측 (`/race`)

**파일**: `templates/race.html`
**뷰**: `src/web/views_race.py`
**소스 파일**: `design/app-UI/race_prediction.html`

#### 섹션 구성

```
Header: "레이스 예측 (DARP)"  ← 버튼

[레이스 선택] (GET ?distance=half)
  5K | 10K | 하프마라톤* | 마라톤 | 커스텀({{ custom_km }}km)

[예측 결과 카드] (gradient border, cyan)
  ├── 예상 완료 시간: {{ predicted_time }}
  ├── 평균 페이스: {{ predicted_pace }}/km
  └── 스플릿 통계:
      5K: {{ split_5k }} / 10K: {{ split_10k }} / {{ mid_label }}: {{ split_mid }} / 예상 순위: {{ rank_pct }}%

[내구성 지수 (DI)] 가로 게이지
  ├── di_score: {{ di_score }}/100
  ├── 게이지 바: DI 위치에 마커
  └── 설명: {{ di_description }}

[페이스 전략] 타임라인
  └── 구간별: {{ pace_segments }}  list[{range_label, pace_str, color}]
      color: 'green'|'yellow'|'red'

[히팅 더 월] (red gradient 배경)
  ├── 확률: {{ htw_pct }}%
  └── 설명: {{ htw_description }}

[훈련 플랜 조정] (cyan 배경)
  └── 권장 사항: {{ training_adjust_text }}
      버튼: "훈련 플랜에 반영하기" → POST /training/apply-darp

bottom_nav('report')  {# 레이스 예측은 레포트 탭 하위 화면 #}
```

#### Jinja2 컨텍스트 변수

| 변수 | 타입 | 없을 때 |
|------|------|---------|
| `distance` | str | 'half' |
| `distance_km` | float | 21.0975 |
| `predicted_time` | str\|None | None |
| `predicted_pace` | str\|None | None |
| `split_5k/10k/mid` | str\|None | None |
| `rank_pct` | str\|None | None |
| `di_score` | int\|None | None |
| `di_description` | str | "" |
| `pace_segments` | list[dict] | [] |
| `htw_pct` | int\|None | None |
| `htw_description` | str | "" |
| `training_adjust_text` | str | "" |

---

### 3-5. AI 코칭 (`/ai-coach`)

**파일**: `templates/ai_coach.html`
**뷰**: `src/web/views_ai_coach.py` (기존 AI 뷰 확장 또는 신규)
**소스 파일**: `design/app-UI/ai_coaching.html`

#### 섹션 구성

```
Header: "AI 코칭"

[코치 프로필] (cyan gradient 배경)
  ├── 아바타: 🤖
  ├── 이름: "RunPulse AI 코치"
  └── 상태: 온라인 (pulse 애니메이션)

[오늘의 브리핑]
  └── 브리핑 카드 (left-border: cyan):
      날짜: {{ briefing_date }}
      액션 버튼: 재생성(POST /ai-coach/briefing) / 공유
      내용: {{ briefing_html | safe }}

[추천 칩]
  └── {{ chips }}  list[{icon, text, prompt}]
      클릭 시 채팅 입력창에 해당 프롬프트 자동 입력

[대화 이력]
  └── {{ messages }}  list[{role: 'ai'|'user', content, time}]
      role=ai: cyan 배경 버블 / role=user: 오른쪽 정렬

[고정: 채팅 입력창] (position: fixed, bottom: 80px)
  ├── input[type=text] placeholder="AI 코치에게 질문하세요..."
  ├── 전송 버튼 (gradient circle)
  └── 빠른 질문 가로 스크롤:
      {{ quick_questions }}  list[str]
```

#### Jinja2 컨텍스트 변수

| 변수 | 타입 | 없을 때 |
|------|------|---------|
| `briefing_date` | str | today |
| `briefing_html` | str | "브리핑을 생성해보세요" |
| `chips` | list[dict] | [] |
| `messages` | list[dict] | [] |
| `quick_questions` | list[str] | 기본 4개 |
| `utrs` / `cirs` / `darp_half` | float\|None | None (브리핑 컨텍스트용) |

---

### 3-6. 훈련 계획 (`/training`)

**파일**: `templates/training_plan.html`
**뷰**: `src/web/views_training_plan.py`
**소스 파일**: `design/app-UI/training_plan.html`

#### 섹션 구성

```
Header: "훈련 계획"
  버튼: 공유 / "+ 새 훈련" → /training/new

[이번 주 요약] 4-stat grid
  ├── 훈련 완료: {{ completed_count }}/{{ total_count }}  (progress bar)
  ├── 목표 km: {{ target_km }}  (progress: {{ actual_km }}/{{ target_km }})
  ├── 목표 시간: {{ target_time_str }}  (progress: {{ actual_time_pct }}%)
  └── UTRS: {{ utrs }}  (progress bar)

[캘린더 뷰] (GET ?view=week|month|day, ?year=&month=&week=)
  ├── 네비게이션: ← {{ display_period }} →
  ├── 뷰 선택: 월 | 주* | 일
  └── 주간 뷰: 7열 grid
      각 열: 요일/날짜 + 워크아웃 아이템
      .workout-item.{type}  type: easy|tempo|interval|long|rest
        ├── workout_type: Easy Run / Interval / Tempo / Long Run / Rest
        └── distance: {{ w.distance_km }}km

[AI 훈련 요약]  ← AI코치 탭의 최신 브리핑 중 훈련 관련 발췌 (읽기 전용)
  └── 내용: {{ ai_training_recommendation }}  (최근 브리핑 발췌, 1~2줄)
      버튼: "AI 코치에게 더 묻기 →" → /ai-coach  {# 전체 인터랙션은 AI코치 탭 #}

[캘린더 연동 상태]
  └── {{ sync_platforms }}  list[{icon, name, status}]
      (Google/Naver/Garmin/TrainingPeaks)

bottom_nav('training')
```

#### Jinja2 컨텍스트 변수

| 변수 | 타입 | 없을 때 |
|------|------|---------|
| `view` | str | 'week' |
| `display_period` | str | "2026년 3월 4주" |
| `completed_count` / `total_count` | int | 0 |
| `target_km` / `actual_km` | float | 0 |
| `utrs` | int\|None | None |
| `week_days` | list[dict] | 7개 (워크아웃 빈 리스트) |
| `ai_training_recommendation` | str | "" |
| `sync_platforms` | list[dict] | [] |

**`week_days` 항목 구조**:
```python
{
  "day_label": "화",
  "date": "19",
  "is_today": bool,
  "workouts": [
    {"id": int, "type": "interval", "label": "Interval", "distance_km": 8.0, "completed": bool}
  ]
}
```

---

### 3-7. 설정 (`/settings`) + 서브 화면들

**파일**: `templates/settings.html`
**뷰**: `src/web/views_settings.py` (기존 확장)
**소스 파일**: `design/app-UI/settings_sync.html`

#### 섹션 구성

```
Header: "설정"

─── A. 소스 연동 ───────────────────────────────────────────
[소스 연동 상태] 4개 카드 (Garmin/Strava/Intervals/Runalyze)
  각 카드: 상태 배지 + 마지막 동기화: {{ last_sync_at[source] }}
           연결/해제 버튼 → /connect/{source}

─── B. 동기화 ──────────────────────────────────────────────
[동기화 설정]
  ├── 동기화 기간: {{ sync_days }}일  (select: 7/30/90/180/365)
  ├── 자동 동기화: {{ auto_sync_enabled }}  (toggle)
  └── 마지막 전체 동기화: {{ last_full_sync }}

[수동 동기화 + 현황 인라인]  ← /sync-status 서브 화면 통합
  ├── 소스별 동기화 버튼 (POST /trigger-sync)
  ├── 진행 중인 작업 (폴링: GET /bg-sync/status)
  │     각 job: 소스 / 진행률 바 / 일시정지·중단 버튼
  └── 백그라운드 동기화 제어: start|pause|stop|resume

─── C. 데이터 관리 ────────────────────────────────────────
[파일 임포트]  ← 기존 /import + /import-export 통합
  ├── GPX/FIT/TCX 파일 업로드 (POST /import/upload, 다중 파일)
  ├── .zip 아카이브 업로드 (POST /import/upload-archive)
  ├── CSV 임포트 (POST /import-export, 미리보기 후 적용)
  └── Strava 벌크: activities.csv + GPX 아카이브

[데이터 익스포트]
  └── 기간 선택 + CSV 다운로드 버튼

[신발 목록 바로가기]  → /shoes

─── D. 앱 설정 ────────────────────────────────────────────
[앱 설정]
  ├── AI 모델: {{ ai_model }}  (select)
  └── 기본 레이스 거리: {{ default_race_dist }}  (select)

bottom_nav('settings')
```

> **통합 변경**: `/sync-status` 서브 화면 제거 → 설정 B섹션으로 흡수.
> **통합 변경**: `/import`(GPX/FIT) + `/import-export`(CSV) → 설정 C섹션으로 통합.
> **이동**: 개발자 도구 → `개발자` 탭으로 이동.

#### Jinja2 컨텍스트 변수

| 변수 | 타입 | 출처 |
|------|------|------|
| `source_statuses` | dict[str,str] | `check_*_connection()` × 4 |
| `last_sync_at` | dict[str,str] | sync_jobs 최근 완료 |
| `sync_days` | int | `config.sync.days` |
| `auto_sync_enabled` | bool | `config.sync.auto` |
| `sync_jobs` | list[dict] | sync_jobs WHERE status='running' |
| `ai_model` | str | `config.ai.model` |
| `default_race_dist` | str | `config.default_race_dist` |

---

### 3-7-B. 신발 목록 (`/shoes`) ← v0.1 기존

**파일**: 기존 `views_shoes.py` (유지)
**접근**: 설정 화면 → "신발 목록" 링크

#### 섹션 구성

```
Header: "신발 목록"

[신발 테이블]
  └── 브랜드 / 모델 / 이름 / 기본 스포츠 종목 / 소스(Strava)

[신발 없을 때]
  └── "Strava 임포트 후 자동으로 등록됩니다" 안내

bottom_nav('settings')
```

---

### 3-8. 개발자 탭 (`/dev`) — **릴리즈 시 제외**

> 기존 `app.py` inline HTML 유지. 다크 테마 전환 불필요.
> `bottom_nav`에서 `config.dev_mode` 플래그로 조건부 노출.
> 릴리즈 전 해당 탭 라우트 및 nav 항목 제거.

#### 섹션 구성

```
Header: "개발자 도구"  [DEV 배지]

─── DB ────────────────────────────────────────────────────
[DB 테이블 뷰어]  → /db
  └── 전체 테이블 열람, 테이블 선택 드롭다운

[Payload 뷰어]  → /payloads → /payloads/view
  └── raw_source_payloads 목록 + 개별 JSON 상세

─── 설정 ──────────────────────────────────────────────────
[DB 경로 설정]  → /config
  └── 현재 DB 경로 표시 + 변경 폼 (POST /config/db-path)

─── 레거시 분석 ────────────────────────────────────────────
[레거시 CLI 분석 뷰]  (v0.2 신규 화면으로 대체 예정, 임시 유지)
  ├── Today 분석 → /analyze/today  (대체: /dashboard)
  ├── Full 레포트 → /analyze/full  (대체: /report)
  └── Race 준비도 → /analyze/race  (대체: /race)

bottom_nav('dev')
```

| URL | 기능 | 릴리즈 처리 |
|-----|------|------------|
| `/dev` | 개발자 탭 홈 (위 섹션 목록) | **제거** |
| `/db` | DB 테이블 뷰어 | **제거** |
| `/payloads` | Payload 목록 | **제거** |
| `/payloads/view` | Payload 상세 | **제거** |
| `/config` | DB 경로 설정 | **제거** |
| `/config/db-path` | DB 경로 변경 POST | **제거** |
| `/analyze/today` | 레거시 Today 분석 | `/dashboard` 리다이렉트 후 **제거** |
| `/analyze/full` | 레거시 Full 레포트 | `/report` 리다이렉트 후 **제거** |
| `/analyze/race` | 레거시 Race 준비도 | `/race` 리다이렉트 후 **제거** |

---

## 4. 공유 SVG 컴포넌트 명세

### 4-1. `half_gauge(value, max, color_type)` 반원 게이지

```
color_type:
  'utrs'  → conic-gradient: red→orange→green (낮음→높음)
            구간별 색상 (3번 문서 권장):
            85~100 #00ff88 (준비됨)
            70~84  #00d4ff (양호)
            55~69  #ffaa00 (주의)
            40~54  #ff8800 (경고)
            0~39   #ff4444 (휴식 필요)
  'cirs'  → conic-gradient: green→orange→red (낮음→높음, 역방향)

SVG 구조:
  width=200, height=100
  .gauge-bg: conic-gradient from 180deg, mask: radial circle 60%
  .gauge-needle: rotate( (value/max * 180 - 90)deg )

needle 각도 계산:
  rotate_deg = (value / max) * 180 - 90
  value=0   → -90deg (왼쪽 끝)
  value=50  →   0deg (정중앙)
  value=100 →  90deg (오른쪽 끝)
```

데이터 없을 때: `no_data_card(title)` 대체

### 4-2. `radar_chart(values)` 5축 레이더 SVG

```
axes = ['유산소용량', '역치강도', '지구력', '동작효율성', '회복력']
center = (150, 150), radius = 120

각 축 각도 (i → 360/5 * i - 90도):
  0: -90deg  (정상단, 유산소용량)
  1:  -18deg (역치강도)
  2:   54deg (지구력)
  3:  126deg (동작효율성)
  4:  198deg (회복력)

polygon points:
  x = cx + r * (v/100) * cos(angle)
  y = cy + r * (v/100) * sin(angle)

스타일:
  배경 격자: opacity=0.1, 20/40/60/80/100 5단계
  축 라벨: 폰트 12px, rgba(255,255,255,0.7)
  데이터 polygon: fill rgba(0,212,255,0.2), stroke #00d4ff, stroke-width 2
```

데이터 없을 때: `no_data_card("RMR 레이더")` 대체

---

## 5. URL 라우팅 정리

### 5-1. v0.2 신규 (Jinja2 템플릿)

| URL | 메서드 | 뷰 함수 | 탭 | Sprint |
|-----|--------|---------|-----|--------|
| `/` | GET | redirect → `/dashboard` | — | S3 |
| `/dashboard` | GET | `views_dashboard.dashboard` | 홈 | S3 |
| `/report` | GET | `views_report.report` | 레포트 | S4 |
| `/race` | GET | `views_race.race` | 레포트 | S5 |
| `/ai-coach` | GET | `views_ai_coach.ai_coach` | AI코치 | S6 |
| `/ai-coach/briefing` | POST | `views_ai_coach.regenerate_briefing` | AI코치 | S6 |
| `/ai-coach/chat` | POST | `views_ai_coach.chat` | AI코치 | S6 |
| `/training` | GET | `views_training_plan.training` | 훈련 | S7 |
| `/training/new` | GET/POST | `views_training_plan.new_workout` | 훈련 | S7 |

### 5-2. v0.1 기존 (inline HTML 유지, 하단 nav 추가)

| URL | 메서드 | 뷰 함수 | 탭 | v0.2 처리 |
|-----|--------|---------|-----|---------|
| `/activities` | GET | `views_activities.activities_list` | 활동 | 다크 테마 + nav 추가 |
| `/activity/deep` | GET | `views_activity.activity_deep_view` | 활동 | Sprint 4에서 섹션 확장 |
| `/wellness` | GET | `views_wellness.wellness_view` | 홈 | 다크 테마 + nav 추가 |
| `/settings` | GET | `views_settings.settings_view` | 설정 | Jinja2 전환 (Sprint 8) |
| `/connect/garmin` | GET/POST | `views_settings.*` | 설정 | 유지 |
| `/connect/strava` | GET/POST | `views_settings.*` | 설정 | 유지 |
| `/connect/intervals` | GET/POST | `views_settings.*` | 설정 | 유지 |
| `/connect/runalyze` | GET/POST | `views_settings.*` | 설정 | 유지 |
| `/shoes` | GET | `views_shoes.shoes_list` | 설정 | nav 추가 |
| `/import` | GET/POST | `app.import_view` | 설정 | 설정 C섹션으로 통합 (Sprint 8) |
| `/import/upload` | POST | `app.import_upload` | 설정 | 유지 |
| `/import/upload-archive` | POST | `app.import_archive` | 설정 | 유지 |
| `/import-export` | GET/POST | `views_export_import.*` | 설정 | 설정 C섹션으로 통합 (Sprint 8) |
| `/sync-status` | GET | `app.sync_status` | 설정 | 설정 B섹션으로 통합 (Sprint 8) |
| `/trigger-sync` | POST | `app.trigger_sync` | 설정 | 설정 B섹션 버튼 |
| `/bg-sync/start\|pause\|stop\|resume` | POST | `bg_sync.*` | 설정 | 설정 B섹션 연동 |
| `/bg-sync/status` | GET | `bg_sync.status` | — | JSON 폴링 유지 |
| `/activities/merge` | POST | `views_activity_merge.*` | — | 유지 |
| `/activities/ungroup` | POST | `views_activity_merge.*` | — | 유지 |
| `/activities/auto-group` | POST | `views_activity_merge.*` | — | 유지 |

### 5-3. 개발자 탭 (`/dev`) — **릴리즈 시 전체 제거**

| URL | 메서드 | 설명 | 릴리즈 대체 |
|-----|--------|------|------------|
| `/dev` | GET | 개발자 탭 홈 | **제거** |
| `/db` | GET | DB 테이블 뷰어 | **제거** |
| `/payloads` | GET | Payload 목록 | **제거** |
| `/payloads/view` | GET | Payload 상세 | **제거** |
| `/config` | GET | DB 경로 설정 | **제거** |
| `/config/db-path` | POST | DB 경로 변경 | **제거** |
| `/analyze/today` | GET | 레거시 Today 분석 | `/dashboard` 리다이렉트 |
| `/analyze/full` | GET | 레거시 Full 레포트 | `/report` 리다이렉트 |
| `/analyze/race` | GET | 레거시 Race 준비도 | `/race` 리다이렉트 |

---

## 6. Sprint별 구현 범위

### Sprint 3 (이번): 대시보드 신규 + 기존 화면 다크 테마 적용

| # | 파일 | 내용 |
|---|------|------|
| S3-1 | `src/db_setup.py` | computed_metrics, weather_data 테이블 추가 |
| S3-2 | `templates/macros/base.html` | 공통 shell (head, CSS, body 래퍼) |
| S3-3 | `templates/macros/nav.html` | **7탭** 하단 네비게이션 (개발자 탭 조건부) |
| S3-4 | `templates/macros/gauge.html` | 반원 게이지 SVG |
| S3-5 | `templates/macros/radar.html` | 5축 레이더 SVG |
| S3-6 | `templates/macros/no_data.html` | "데이터 수집 중" fallback 카드 |
| S3-7 | `templates/dashboard.html` | 대시보드 Jinja2 템플릿 |
| S3-8 | `src/web/views_dashboard.py` | 대시보드 블루프린트 |
| S3-9 | `src/web/app.py` | blueprint 등록, `/` → `/dashboard` |
| S3-10 | 기존 views (activities, wellness, shoes 등) | 다크 테마 CSS + 하단 nav 추가 |
| S3-11 | `tests/test_dashboard.py` | 대시보드 뷰 테스트 |
| S3-12 | git 커밋 | |

### Sprint 4: 분석 레포트 + 활동 상세 확장
- `templates/report.html` + `views_report.py`
- `views_activity.py` FEARP 섹션 + 2차 메트릭 카드 추가

### Sprint 5: 레이스 예측
- `templates/race.html` + `views_race.py`

### Sprint 6: AI 코칭
- `templates/ai_coach.html` + `views_ai_coach.py`

### Sprint 7: 훈련 계획 캘린더
- `templates/training_plan.html` + `views_training_plan.py`

### Sprint 8: 설정 화면 Jinja2 전환 + 개발자 탭 정리 + 마무리
- `templates/settings.html` + `views_settings.py` 확장
  - B섹션: `/sync-status` 페이지 흡수 (별도 라우트 제거)
  - C섹션: `/import` + `/import-export` 통합
- `templates/dev.html` + `src/web/views_dev.py` (개발자 탭)
- 전체 화면 하단 nav 통일 검증
- **릴리즈 준비**: `config.dev_mode=false` 설정 → 개발자 탭 nav에서 자동 제거
- `/analyze/*` → 신규 화면으로 리다이렉트 후 제거

---

## 7. 구현 시 주의사항

---

## 8. 모바일 앱 확장 전략

### 8-1. 확장 로드맵

```
현재 (v0.2, Sprint 3~8)
  Flask/Jinja2 SSR  ─────────────────── 웹 브라우저 (Termux/Android)
          │
          ▼ Sprint 9 (PWA)
  웹앱 + Service Worker + Manifest  ─── 홈 화면 추가, 오프라인 지원
          │
          ▼ Phase 10 (API Layer)
  Flask REST API /api/v1/*  ─────────── 모바일 앱·외부 클라이언트 대응
          │
          ▼ Phase 11 (모바일 앱)
  React Native 앱 (iOS + Android)  ──── 네이티브 기능 (알림, GPS, 카메라)
```

### 8-2. 현재 구현이 모바일 확장에 미치는 영향

| 결정 | 모바일 친화적? | 이유 |
|------|--------------|------|
| Blueprint 구조 | ✅ | 서비스 레이어 분리 → API 엔드포인트가 같은 서비스 재사용 |
| Jinja2 템플릿 | ⚠ 부분 | HTML 렌더링은 웹 전용. 단, 뷰 함수 로직은 재사용 가능 |
| 비즈니스 로직을 Python 서비스에 | ✅ | `src/services/`, `src/metrics/`은 API 레이어에서 그대로 사용 |
| 세션 기반 인증 | ⚠ | 모바일 앱은 JWT/토큰 인증 필요. Phase 10에서 추가 |
| SQLite 로컬 파일 | ⚠ | 앱 여러 기기 사용 시 동기화 문제. Phase 11에서 서버 배포 고려 |

### 8-3. 지금 당장 해야 할 API-Friendly 설계 원칙

> Flask 뷰 함수에서 HTML·JSON 모두 서빙하는 패턴. 추가 공수 최소.

```python
# 예시: 동일 뷰 함수에서 HTML/JSON 분기
@bp.route('/api/v1/dashboard', methods=['GET'])
@bp.route('/dashboard', methods=['GET'])
def dashboard():
    data = _build_dashboard_data()  # 서비스 레이어 호출
    if request.headers.get('Accept') == 'application/json':
        return jsonify(data)         # 모바일 앱용 JSON
    return render_template('dashboard.html', **data)  # 웹용 HTML
```

**Sprint 3~8에서 지켜야 할 규칙**:
1. 뷰 함수에 데이터 변환 로직 직접 작성 금지 → 반드시 `src/services/` 함수로 분리
2. Jinja2 컨텍스트 변수는 JSON 직렬화 가능한 타입만 (dict, list, int, float, str, None)
3. 화면당 `_build_{화면명}_data(conn) -> dict` 헬퍼 함수 작성 → 나중에 API에서 그대로 재사용
4. 인증이 필요한 화면은 `@login_required` 데코레이터로 통일 (Phase 10에서 JWT로 교체 용이)

### 8-4. Sprint 9: PWA 기초 (모바일 앱 전 단계)

| 작업 | 내용 |
|------|------|
| `static/manifest.json` | 앱 이름, 아이콘, 시작 URL, 테마 색상 |
| `static/sw.js` | Service Worker — 오프라인 캐싱 (최근 활동 목록) |
| `templates/macros/base.html` 수정 | `<link rel="manifest">` + `<meta theme-color>` 추가 |
| 홈 화면 추가 배너 | "앱으로 추가하기" 버튼 (beforeinstallprompt 이벤트) |

### 8-5. Phase 10: REST API 레이어

| 엔드포인트 | 반환 | 대응 HTML |
|-----------|------|----------|
| `GET /api/v1/dashboard` | JSON | `/dashboard` |
| `GET /api/v1/activities` | JSON (페이지네이션) | `/activities` |
| `GET /api/v1/activity/<id>` | JSON | `/activity/deep/<id>` |
| `GET /api/v1/report` | JSON | `/report` |
| `GET /api/v1/race` | JSON | `/race` |
| `GET /api/v1/training` | JSON | `/training` |
| `POST /api/v1/ai-coach/chat` | JSON | `/ai-coach` |

### 8-6. Phase 11: React Native 앱 (장기)

- **언어**: TypeScript + React Native
- **API**: Phase 10의 `/api/v1/*` 호출 (동일 Flask 백엔드)
- **지도**: Mapbox GL JS → React Native Mapbox SDK 교체 (동일 토큰)
- **차트**: ECharts → Apache ECharts for React Native 또는 Victory Native
- **인증**: Flask 서버에 JWT 발급 엔드포인트 추가
- **배포**: Termux 환경 유지 + (선택) Railway/Fly.io 클라우드 배포로 기기 공유

---

1. **ECharts CDN**: `<script src="https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js">` — 로드 실패 시 캔버스 숨기고 SVG fallback. Chart.js 대신 ECharts 사용 (줌/패닝, 한국어, 고성능).
2. **PMC 차트**: `daily_fitness` 테이블에서 CTL/ATL/TSB가 없으면 빈 배열 → ECharts 빈 캔버스 → `no_data_card` 대체. TSB < -20 구간 배경색 표시.
3. **Mapbox GL JS**: 활동 궤적 지도에 사용. 토큰은 `config.json`의 `mapbox_token` 키. 토큰 없거나 로드 실패 시 Leaflet.js + OpenStreetMap으로 자동 폴백.
4. **폰트 CDN**: `<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700&family=Inter:wght@400;600&display=swap">` — `base.html` 매크로에 포함.
5. **하단 네비게이션 높이**: `padding-bottom: 100px` 콘텐츠 영역에 적용 필수 (고정 nav와 겹침 방지).
6. **5초 규칙** (3번 문서): 대시보드 최상단에는 핵심 지표 2~3개만 (UTRS/CIRS 게이지). 한 화면에 7개 이하 주요 메트릭.
7. **computed_metrics 없을 때**: 에러 500 발생하지 않도록 모든 DB 쿼리는 `fetchone()` → None 처리.
8. **XSS 방지**: `briefing_html | safe`는 AI 응답을 `bleach.clean()`으로 위생 처리 후 전달.
9. **모바일 반응형**: 주력 대상 320~768px. 활동 상세 지도는 화면 높이의 60% (`height: 60vh`).
10. **기존 뷰 영향 없음**: `/activities`, `/wellness`, `/activity/deep` 등 기존 뷰는 inline HTML 그대로 유지 (Sprint 4~8에서 단계적 전환).
11. **API-Friendly 설계**: 모든 뷰 함수에서 데이터 수집 로직을 `_build_{name}_data(conn) -> dict` 헬퍼로 분리. 모바일 API Phase 10에서 재사용. 섹션 8-3 참고.
