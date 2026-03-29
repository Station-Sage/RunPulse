# 훈련탭 UX 재설계 — 설계 문서

최종 업데이트: 2026-03-28

---

## 개요

현재 훈련탭의 주요 문제점:
- 훈련 환경 설정이 Settings 탭에 분리되어 있음
- Wizard 없이 버튼 하나로 4주 고정 플랜 생성 (커스터마이즈 불가)
- 전체 훈련 계획 뷰 없음 (주별 1주 단위만 표시)
- 워크아웃 편집 불가
- 계획 vs 실제 달성 비교 없음
- 기존 목표 불러오기/관리 미흡
- 현재 상태 기반 목표 달성 가능성 분석 없음

---

## DB 변경 (SCHEMA_VERSION 3.1)

### 버전 표기 방식
- SQLite `PRAGMA user_version`은 정수형만 지원 → **내부 정수: 4**
- `schema_meta` 테이블에 `display_version TEXT DEFAULT '3.0'` 컬럼 추가
- 마이그레이션 v4 실행 시 `display_version = '3.1'` 로 설정
- UI/로그에서는 `display_version` 값을 사용하여 "3.1" 표시

### 신규 컬럼 (마이그레이션 v4)

**`goals` 테이블 추가 컬럼**
```sql
ALTER TABLE goals ADD COLUMN weekly_km_target REAL;   -- 사용자 목표 주간 km
ALTER TABLE goals ADD COLUMN plan_weeks INT;           -- 사용자 선택 훈련 기간 (주)
ALTER TABLE goals ADD COLUMN target_pace_sec_km INT;   -- 목표 페이스 (초/km) ← Wizard에서 입력
```
> `target_pace_sec_km`이 이미 있으면 스킵 (`_add_column_if_missing` 사용)

**`schema_meta` 테이블 추가 컬럼**
```sql
ALTER TABLE schema_meta ADD COLUMN display_version TEXT DEFAULT '3.0';
```

---

## 거리별 훈련 기간 규칙 (논문 기반)

| 거리 | 최솟값 | 추천(최적) | 테이퍼 | 참고 문헌 |
|------|--------|-----------|--------|----------|
| 5K | 6주 | 8~10주 | **1주** | Daniels 2014 §6, Pfitzinger |
| 10K | 8주 | 10~12주 | **1주** | Daniels 2014 §7 |
| Half Marathon | 12주 | 14~16주 | **2주** | Pfitzinger & Douglas 2009 |
| Full Marathon | 16주 | 18~20주 | **3주** | Mujika & Padilla 2003, Bosquet 2007 |
| Custom | 6주 | 12주 | **1~3주** | 거리 비례 내삽 |

### 사용자 단축 허용 정책
- 최솟값 미만 입력 가능 (강제 차단 없음)
- 최솟값 미만 시 Wizard Step 3에서 경고:
  > ⚠️ 선택한 기간(N주)은 {거리} 권장 최솟값({M주})보다 짧습니다.
  > 이 경우 목표 달성 가능률이 낮게 추정됩니다.
- 최솟값 미만 기간에 따른 달성률 페널티 적용 (아래 readiness 계산 참조)

### 테이퍼 주 계산
```python
def get_taper_weeks(distance_km: float) -> int:
    if distance_km <= 10:  return 1
    if distance_km <= 21.1: return 2
    return 3
```

### 훈련 단계 배분 (Build-Peak-Taper)
총 훈련 기간에서 테이퍼를 제외한 나머지를 아래 비율로 배분:
| 단계 | 비율 | 내용 |
|------|------|------|
| Base | 40% | 유산소 기반, Easy + Long |
| Build | 35% | 볼륨 증가, Tempo 추가 |
| Peak | 25% | 강도 최고, Interval 포함 |
| Taper | 고정 | 볼륨 -40~50%, 강도 유지 |

> 단, 기간이 짧을수록 Base 비율 축소, Build/Peak 직접 진입

---

## Wizard 4단계 설계

### Step 1: 레이스 목표
```
입력:
  - 종목: 5K / 10K / Half / Full / Custom(km 직접)
  - 레이스 날짜: datepicker (오늘 이후만)
  - 목표 완주 시간 또는 목표 페이스(/km) — 둘 중 하나 입력 시 나머지 자동 계산
```

### Step 2: 훈련 환경
```
입력:
  - 주간 휴식 요일: 체크박스 복수 선택 (일/월/화/수/목/금/토)
  - 일회성 쉬는 날: datepicker + [추가] (최대 10개)
  - 인터벌 트랙 길이: 200m / 400m / 1000m 선택
  - 훈련 기간: 슬라이더/숫자 입력 (기본값: 추천값, 최솟값 아래 시 경고 배지)
```

### Step 3: 상태 분석 결과 표시
```
자동 계산 (readiness.py):
  ┌─────────────────────────────────────────────────┐
  │ 📊 현재 상태 분석                                │
  ├─────────────────┬───────────────────────────────┤
  │ VDOT_ADJ        │ 45.2  (목표 달성 필요: 48.0)  │
  │ DI (지구력)     │ 보통  (롱런 부족)              │
  │ EF (효율)       │ 상승 중 ✅                     │
  │ Running Shape   │ 72/100                        │
  ├─────────────────┴───────────────────────────────┤
  │ 추천 기간: 14주 (최솟값 12주)                    │
  │ 선택 기간: 10주 ⚠️ (권장보다 짧음)               │
  │                                                 │
  │ 현재 페이스 유지 시 예상 기록: 1:56:30           │
  │ 훈련 완료 시 예상 기록:       1:52:00            │
  │ 목표 기록:                    1:50:00           │
  │                                                 │
  │ 목표 달성 가능률: ██████░░░░ 61%                │
  │                                                 │
  │ [기간 늘리기 → 14주] [목표 조정] [그대로 진행]   │
  └─────────────────────────────────────────────────┘
```

### Step 4: 플랜 요약 + 생성
```
표시:
  - 훈련 기간 N주 (Base M주 / Build M주 / Peak M주 / Taper M주)
  - 주간 예상 km 범위 (시작 → 최고 → 테이퍼)
  - 주당 훈련일 수 (환경 설정 기반)
  - [✅ 플랜 생성] 버튼
```

---

## `src/training/readiness.py` — 상태 분석 + 예측 모델

### 주요 함수

```python
def analyze_readiness(
    conn: sqlite3.Connection,
    goal_distance_km: float,
    goal_time_sec: int,
    target_weeks: int,
) -> dict:
    """
    현재 훈련 상태를 분석하여 목표 달성 가능성 추정.

    Returns:
        achievability_pct  : float  # 0~100
        recommended_weeks  : dict   # {"min": int, "optimal_min": int, "optimal_max": int}
        projected_time_now : int    # 현재 페이스 유지 시 예상 기록 (초)
        projected_time_end : int    # 훈련 완료 시 예상 기록 (초)
        required_vdot      : float  # 목표 달성 필요 VDOT
        current_vdot       : float  # 현재 VDOT_ADJ
        vdot_gap           : float  # required - current
        weekly_vdot_gain   : float  # 주당 VDOT 향상 추정치
        status_summary     : str    # 상태 해설 텍스트 (한국어)
        warnings           : list[str]  # 경고 메시지
    """
```

### VDOT 기반 달성 가능률 계산

```
1. goal_time_sec + goal_distance_km → required_vdot  (Daniels 역산 공식)
2. 현재 vdot_adj → current_vdot
3. vdot_gap = required_vdot - current_vdot
4. weekly_vdot_gain 추정:
     [원칙 — 논문 근거 있음]
     - 훈련 수준 높을수록 향상폭 작아짐
       Jones & Carter 2000 (메타분석): VO2max 연간 향상률
         미훈련 15~25%, 중급 5~10%, 엘리트 1~3%
       Bouchard et al. 1999 (HERITAGE Family Study): 훈련 반응 개인차
     [수치 — 연간 향상률에서 역산한 추정값]
     sum(e^(-0.05w), w=0..15) ≈ 11.28 이용해 역산:
     - VDOT < 30:  0.50/주  (연 15~25% → 16주 ~5~8 VDOT)
     - VDOT 30~40: 0.20/주  (연 10~15% → 16주 ~1.5~3 VDOT)
     - VDOT 40~50: 0.12/주  (연  5~10% → 16주 ~0.7~1.4 VDOT, 상한값)
     - VDOT 50~60: 0.12/주  (추정)
     - VDOT 60+:   0.06/주  (추정)
     - 지수 감소: gain × exp(-0.05 × week) — 적응 둔화 모델링
     - DI/RTTI/EF 보정: ±5~10%
     TODO(v0.4-ML): session_outcomes 50회+ 시 개인화 회귀 모델로 교체
5. projected_vdot = current_vdot + Σ(weekly_gain, target_weeks)
6. achievability_pct:
     - projected_vdot >= required_vdot → 100%
     - projected_vdot < required_vdot → 100% × (projected/required)^2
     - 기간이 최솟값 미만 → 최대 70% 상한 페널티
7. DI 낮음(-10%), RTTI 과훈련(-10%), EF 낮음(-5%) 보정
```

### 기록 예측 (Riegel + VDOT 혼합)

```
projected_time_now:
  - 현재 vdot_adj → Daniels 공식으로 goal_distance_km 예상 기록

projected_time_end:
  - projected_vdot → Daniels 공식으로 goal_distance_km 예상 기록

# 향후 ML 전환 포인트 (주석으로 표시):
# TODO: session_outcomes 50회 이상 축적 시 개인화 회귀 모델로 교체 가능
# ref: src/training/session_outcomes 누적 데이터 활용
```

### 주간 km 추천

```python
def recommend_weekly_km(
    current_vdot: float,
    distance_label: str,  # "5k", "10k", "half", "full"
    phase: str,           # "base", "build", "peak", "taper"
    week_index: int,      # 0-based, 현재 주차
    total_weeks: int,
) -> float:
    """
    Pfitzinger 주간 볼륨 테이블 + VDOT 보정.
    - VDOT < 35 → 초급 테이블
    - VDOT 35~50 → 중급 테이블
    - VDOT > 50 → 고급 테이블
    3:1 사이클 (Foster 1998): 3주 점진적 증가 후 1주 회복 (-20%)
    """
```

---

## 훈련탭 레이아웃 재설계

### 섹션 구성 (위에서 아래)

```
[헤더] 훈련 계획 · v3.1 · D-84 · 14주차 중 3주차 완료 (21%)

[S0] 메시지 (조건부)

[S1] 활성 목표 카드 (Wizard 트리거 포함)
     ├─ 목표 없을 때: "🗓️ 훈련 계획 시작하기" 버튼 → Wizard
     └─ 목표 있을 때: 목표 정보 + [수정] 버튼 → Wizard(수정 모드)

[S2] 훈련 분석 카드 (신규)
     ├─ 달성도 진행바 (주차/전체)
     ├─ Q-day 완수율, 페이스 준수율
     ├─ 목표 달성 가능률 + 예상 기록
     └─ 상태 해설 텍스트

[S3] 이번 주 플랜 (기존 주간 캘린더)
     └─ 각 워크아웃: 편집 버튼(⚙️) 클릭 → inline 편집 패널

[S4] 체크인 (기존)

[S5] 인터벌 처방 (기존, 오늘 인터벌 있을 때만)

[S6] 전체 훈련 계획 (신규, Collapsible)
     ├─ [표 뷰] / [캘린더 뷰] 토글
     ├─ 표 뷰: 행=주차, 열=요일, 셀=타입+km
     ├─ 캘린더 뷰: 월별 달력
     └─ 각 셀 클릭 → 편집

[S7] 계획 vs 실제 비교 (신규, Collapsible)
     ├─ 기간 선택: 주별 / 월별
     ├─ 바 차트: 계획 km vs 실제 km
     ├─ 타입별 완수율 (Easy/Tempo/Interval/Long)
     └─ AI 해설 카드

[S8] AI 훈련 추천 (기존)

[S9] 훈련 환경 설정 (Settings에서 이동, Collapsible ▶ 펼치기)
     ├─ 휴식 요일 설정
     ├─ 일회성 쉬는 날
     └─ 인터벌 트랙 설정

[S10] 이전 목표 관리 (Collapsible)
      └─ 목록: 이름 / 거리 / 날짜 / [불러오기]

[S11] 동기화 상태 (기존)
```

---

## 파일 구조

| 파일 | 작업 내용 |
|------|----------|
| `src/training/readiness.py` | **신규** — 상태 분석 + 예측 모델 |
| `src/web/views_training_wizard.py` | **신규** — Wizard 렌더러 (4단계) |
| `src/web/views_training_fullplan.py` | **신규** — 전체 계획 표/캘린더 + 비교 차트 |
| `src/web/views_training.py` | 수정 — 레이아웃 재조정, 신규 섹션 연결 |
| `src/web/views_training_cards.py` | 수정 — 분석 카드, 편집 버튼, 설정 Collapsed, 목표 관리 |
| `src/web/views_training_crud.py` | 수정 — `/training/prefs`, Wizard 처리, 편집 AJAX |
| `src/web/views_training_loaders.py` | 수정 — 전체 플랜 로더, 비교 데이터 로더 |
| `src/training/planner.py` | 수정 — 전체 계획 생성, 거리별 테이퍼/기간 |
| `src/web/views_settings.py` | 수정 — `_render_training_prefs_section` 제거 |
| `src/db_setup.py` | 수정 — 마이그레이션 v4 추가 (display_version='3.1') |

### 테스트 파일

| 파일 | 내용 |
|------|------|
| `tests/test_readiness.py` | **신규** — analyze_readiness, recommend_weekly_km |
| `tests/test_training_wizard.py` | **신규** — Wizard 라우트 통합 테스트 |

---

## 구현 순서 (Phase)

### Phase A: DB 마이그레이션 + readiness.py (기반)
1. `db_setup.py` 마이그레이션 v4 추가 (`display_version='3.1'`, goals 컬럼)
2. `src/training/readiness.py` 신규 작성
3. `tests/test_readiness.py` 작성

### Phase B: 훈련 설정 이동 + 환경 설정 Collapsible
1. `views_settings.py`에서 `_render_training_prefs_section` 제거
2. `views_training_cards.py`에 `render_training_prefs_collapsed()` 추가
3. `views_training_crud.py`에 `POST /training/prefs` 라우트 추가

### Phase C: Wizard
1. `views_training_wizard.py` 신규 — 4단계 렌더러
2. `views_training_crud.py`에 Wizard 처리 라우트 추가
3. `tests/test_training_wizard.py` 작성

### Phase D: 워크아웃 편집 메뉴 ✅ 완료
- `views_training_cards.py`: `_render_edit_panel()` + `_WORKOUT_EDIT_JS` (⚙️ AJAX)
- `views_training_crud.py`: `PATCH /training/workout/<id>`, `GET /interval-calc`
- D-fix1: `/training/calendar-partial` + `rpWeekNav()` (스크롤 버그 수정)
- D-fix2: "📤 내보내기 ▾" 드롭다운 (Garmin/CalDAV/ICS/링크복사 통합)

### Phase E: 전체 계획 뷰 + 월간 뷰 ✅ 완료
- E-1: `views_training_fullplan.py` 신규 (`GET /training/fullplan`, 주별 Collapsible)
- E-1: `views_training_loaders.py`: `load_full_plan_weeks()`
- E-2: `views_training_month.py` 신규 (`?view=month`, 4주×7일 그리드)
- E-2: `load_month_workouts()`, `load_actual_activities(end_date)`, `_week_view_tabs()` 3탭

### Phase F: Wizard + 목표 카드 인터랙션 ✅ 완료 (2026-03-28)
- F-1: Wizard edit 모드 (`?mode=edit&goal_id=N`) — pre-populate + UPDATE + 재생성 체크박스
- F-2: 목표 카드 ✏️ → Wizard edit 모드 직접 링크
- F-3: 목표 카드 ✕ → AJAX skip + replanner + 인라인 알림(재조정 변경사항)
- F-4: 목표 카드 ✓ → AJAX confirm + matched/activity_summary + match-check 폴링 엔드포인트

### Phase G: 목표 관리 개선 ✅ 완료 (2026-03-28)
- G-1: 목표 리스트 (수행률 바, D-day, 상태 배지) — `views_training_goals.py` 신규
- G-2: 클릭 → AJAX 드릴다운 (주차별 수행도)
- G-3: 목표 취소 → AJAX (인라인 처리)
- G-4: 훈련 가져오기 — 소스 목표 선택 + 새 시작일 + 범위(전체/특정일/기간) + 미리보기 + 실행

### Phase G+: 캘린더 AJAX 전환 ✅ 완료 (2026-03-28)
- `rpNavTo(href, calUrl)` 추가 — 월간 화살표·탭 전환 full reload → AJAX (스크롤 유지)

### Phase H: 훈련 캘린더 UX 고도화
- [ ] H-1: 모바일 스와이프 주 이동
  - `#rp-calendar`에 `data-week-offset`, `data-view="week|month"` 추가
  - touchstart/end 50px 임계값, `|deltaY| < |deltaX|` (수직 스크롤 구분)
  - week: `rpWeekNav(offset±1)` / month: `rpNavTo(href, calUrl)`
  - 구현: `WORKOUT_EDIT_JS` (views_training_week.py), `_month_js` (views_training_month.py)
- [ ] H-2: 워크아웃 카드 클릭 → 상세 팝업 모달 (주간·월간 공통)
  - 카드에 `data-wid/wtype/dist/pace-min/pace-max/date/completed/label` 추가
  - `rpOpenWorkout(el)` → 공통 모달 `#rp-wmodal` (하단 슬라이드업)
  - 모달 액션: ✓ 완료 (POST /confirm AJAX) / ✕ 스킵 (POST /skip AJAX) / ✏️ 수정
  - 성공 후 캘린더 갱신: `rpWeekNav` 또는 `rpNavTo`
  - 주간 기존 인라인 버튼: `event.stopPropagation()` 추가 (팝업과 공존)
- [ ] H-3: 월간 훈련 카드 미리보기
  - 데스크탑: `mouseenter` → `#rp-tip` position:absolute 툴팁 (타입/거리/페이스)
  - 모바일: 200ms 롱탭(touchstart+timer) → 미리보기 / 단순탭(<200ms) → 모달
  - 툴팁 내용: data 속성에서 읽어 JS로 생성 (서버 요청 없음)

---

## 추가 지표 (신규)

| 지표 | 설명 | 계산 위치 |
|------|------|----------|
| **훈련 진행률** | 전체 플랜 기간 중 현재 주차 비율 | readiness.py |
| **Q-day 달성률** | 이번 달 계획된 Quality day 대비 실제 완료 | readiness.py |
| **페이스 준수율** | 계획 페이스 ±5% 이내 달린 워크아웃 비율 | readiness.py |
| **목표 달성 가능률** | VDOT 성장 모델 기반 추정 (0~100%) | readiness.py |
| **예상 완주 기록** | 현재 유지 시 / 훈련 완료 시 두 가지 | readiness.py |

---

## 미래 확장 포인트 (주석으로 표기)

```python
# TODO(v0.4-ML): session_outcomes 50회+ 축적 시 아래 추정식을 개인화 회귀 모델로 교체
# - 입력: current_vdot, di, ef, fearp, running_shape, weeks_trained
# - 출력: projected_time_sec, achievability_pct
# - ref: src/training/replanner.py의 session_outcomes 스키마 참조
```
