# 훈련 엔진 v2 설계 문서

> 작성일: 2026-03-28
> 상태: 설계 확정 (구현 대기)
> 관련 파일: `src/training/planner.py`, `src/metrics/crs.py`(신규), `src/training/interval_calc.py`(신규)

---

## 1. 설계 목표

1. **논문 기반 훈련 처방** — 검증된 수치를 그대로 적용, 근거 없는 임의 수치 배제
2. **전체 메트릭 활용** — 1차·2차 메트릭, 웰니스, 시계열 데이터 통합
3. **사용자 커스텀** — 휴식일, 인터벌 거리 등 제약 조건 반영
4. **ML 확장 기반** — 훈련 성과 데이터 축적 → 향후 개인화 모델 연동

---

## 2. 전체 데이터 흐름

```
[입력 신호]
  피트니스:  CTL, ATL, TSB, VDOT_ADJ, eFTP, CP
  준비도:    UTRS, CIRS, DI, ACWR, Monotony, RTTI
  웰니스:    Body Battery, HRV(rMSSD), Sleep Score, Stress, Resting HR
  훈련 이력: dist_ratio, pace_delta, hr_delta, decoupling (session_outcomes)
  사용자:    가용일(rest_weekdays, blocked_dates), 인터벌 설정, 목표

       ↓

[게이트 필터] ← 논문 기반 임계값 적용
  부상 위험 / 자율신경 / 에너지 / 부하 / 단조로움

       ↓

[CRS: 복합 준비도 점수] ← 참고 점수 (0~100), 향후 ML 가중치
  게이트 통과 후 상대적 여유도 표현

       ↓

[훈련 처방]
  주간 볼륨 → 강도 배분(80/20) → 동적 스케줄 → 세부 처방

       ↓

[실행 및 피드백 수집]
  session_outcomes 테이블에 결과 저장

       ↓

[재조정] ← 피드백 반영 규칙
  다음 주 계획 자동 보정

       ↓

[ML 파이프라인 (v0.4)]
  session_outcomes → 개인화 모델 → CRS 가중치 자동 도출
```

---

## 3. 게이트 필터 (논문 기반)

각 게이트는 독립적으로 평가. 가장 엄격한 게이트가 최종 허용 레벨 결정.

### Gate 1 — 부상 위험 (ACWR)
**근거:** Gabbett 2016 "The training–injury prevention paradox" BJSM

| ACWR | 조치 |
|------|------|
| > 1.5 | Z1 이하 강제, 볼륨 증가 차단 |
| 1.3 ~ 1.5 | Z3(interval) 금지 |
| 1.0 ~ 1.3 | 최적 구간, 제약 없음 |
| < 0.8 | 저훈련 경고 (볼륨 증가 유도) |

### Gate 2 — 자율신경 회복 (HRV)
**근거:** Plews et al. 2013 "Training adaptation and heart rate variability in elite endurance athletes" IJSPP

| HRV (7일 rolling 평균 대비) | 조치 |
|--------------------------|------|
| 평균 +5% 이상 | 고강도 허용, +5% 볼륨 허용 |
| ±5% 이내 | 계획대로 |
| -5 ~ -10% | Z3 금지 |
| -10% 이하 | Z1만 허용 |

> HRV 데이터 없으면 이 게이트 스킵 (데이터 없음 처리)

### Gate 3 — 에너지 (Body Battery)
**근거:** Garmin (HRV + 활동 기반 에너지 지수)

| Body Battery | 조치 |
|-------------|------|
| ≥ 75 | 제약 없음 |
| 50 ~ 74 | 계획대로 |
| 25 ~ 49 | Z3 금지 |
| < 25 | 휴식 권장 |

> BB 없으면 Sleep Score로 대체: < 50 → Z3 금지

### Gate 4 — 피트니스 부하 (TSB)
**근거:** Coggan 2003 (TSS 모델), Banister 1991 (이중 지수 모델, τ₁=42일, τ₂=7일)

| TSB | 조치 |
|-----|------|
| > +25 | 탈훈련 주의, 볼륨 +5% (과테이퍼 방지) |
| +10 ~ +25 | 레이스 최적 상태 |
| 0 ~ +10 | 정상 훈련, 계획대로 |
| -10 ~ 0 | 계획대로 (빌드 중) |
| -20 ~ -10 | 볼륨 -10% 권고 |
| -30 ~ -20 | 볼륨 -20%, Z3 횟수 제한 |
| < -30 | 즉시 회복 주간: Z1만, 볼륨 -40% |

### Gate 5 — 단조로움 (Monotony)
**근거:** Foster 1998 "Monitoring training in athletes with reference to overtraining syndrome" Med Sci Sports Exerc

| Monotony | 조치 |
|---------|------|
| > 2.0 | 훈련 다양성 강제 (easy/hard 패턴 재배치) |
| 1.5 ~ 2.0 | 경고만 |
| < 1.5 | 정상 |

---

## 4. CRS (복합 준비도 점수) — 참고용

> **중요:** CRS의 가중치는 현재 논문으로 검증된 수치가 없음.
> 단일 지표 연구는 많으나, 복합 가중치를 제시한 검증 논문 없음.
> 상업 시스템(Garmin, WHOOP, TrainingPeaks)도 독점 알고리즘으로 미공개.
> **현재는 균등 가중치 초안으로 유지. ML 데이터 축적 후 개인화 회귀로 교체 예정.**

### 현재 CRS 구성 (초안)

```
CRS = Σ(신호_점수 × 가중치)

[A] 피로/회복 그룹 (40%)
  TSB:          15% — Coggan/Banister 기반 피트니스·피로 균형
  HRV:          15% — Plews 2013: 자율신경이 가장 민감한 단일 지표
  Body Battery: 10% — 당일 에너지 상태

[B] 부하 위험 그룹 (35%)
  ACWR:         15% — Gabbett 2016: 부상 위험의 핵심 예측 지표
  CIRS:         10% — 누적 스트레스 종합
  Monotony:      5% — Foster 1998: 단조로움 → 과훈련 선행 지표
  Sleep Score:   5% — Simpson et al. 2017

[C] 체력/효율 그룹 (25%)
  VDOT_ADJ 4주 추세: 10% — 체력 향상/하락 방향성
  DI(Decoupling): 10% — Friel 2012: 유산소 기반 효율
  RTTI:           5% — Garmin 달리기 내성
```

**⚠️ 가중치 한계 명시:**
- 위 수치는 합리적 초안이나 논문으로 검증되지 않음
- 개인차가 크기 때문에 범용 가중치는 본질적으로 부정확
- ML 피드백 루프로 개인화되기 전까지 **절대값 아닌 상대적 참고치로만 사용**

### CRS → 훈련 레벨 (게이트 통과 후 세부 조정용)

| CRS | 의미 | 추가 조정 |
|-----|------|----------|
| 85~100 | 최적 | 계획대로 또는 볼륨 +5% |
| 70~84 | 양호 | 계획대로 |
| 55~69 | 보통 | 볼륨 -5% |
| 40~54 | 피로 | 볼륨 -15% |
| < 40 | 고피로 | 게이트와 동일하게 Z1만 |

---

## 5. 훈련 강도 배분 (논문 기반)

### 80/20 원칙
**근거:** Seiler 2010 "What is best practice for training intensity and duration distribution in endurance athletes?" IJSPP 5(3):276-291

- Z1 (easy + long) ≥ **80%** of 주간 볼륨
- Z2 (tempo) + Z3 (interval): ≤ **20%**
- 중간 강도(Z2 단독) 최소화 — "gray zone" 회피
  - Stöggl & Sperlich 2014 (Frontiers in Physiology): Polarized 그룹이 VO2max +11.7% vs Threshold 그룹 +2.1%

### 3존 정의 (Seiler 2010)

| 존 | 심박 기준 | RunPulse 타입 |
|---|---------|-------------|
| Z1 | < HRmax 77% (VT1 이하) | easy, long, recovery |
| Z2 | HRmax 77~92% (VT1~VT2) | tempo, M-pace |
| Z3 | > HRmax 92% (VT2 이상) | interval |

### 세션당 볼륨 상한 (Daniels Running Formula 3판)

| 타입 | 세션 최대 | 주간 비율 상한 |
|------|----------|-------------|
| T (Tempo) | 60분 | 주간 km의 10% |
| I (Interval) | 8km | 주간 km의 8% |
| R (Repetition) | 8km | 주간 km의 5% |
| E / Long | 150분 또는 주간 25% | — |

---

## 6. 인터벌 처방 (논문 기반)

**핵심 원칙:** 반복 거리 → 소요 시간 → 휴식 비율 → 세트 수 순서로 계산

### 페이스 기준
**근거:** Daniels Running Formula — VDOT_ADJ → I-pace (%VO2max 97~100%, HRmax 98~100%)

```
I-pace = VDOT_ADJ 기반 Daniels I-pace 테이블 조회
rep_time_sec = rep_distance_m / 1000 × I_pace_sec_km
```

### 휴식 비율 (Billat 2001, Buchheit & Laursen 2013)
**근거:**
- Billat 2001 "Interval Training for Performance" Sports Medicine 31(1):13-31
  - vVO2max 강도에서 1:1 휴식 권장
  - 능동 회복(vVO2max의 60% = E-pace 수준) 권장
- Buchheit & Laursen 2013 "HIIT, Solutions to the Programming Puzzle" Sports Medicine 43(5), 43(10)

| rep 소요 시간 | 대략 거리 | 휴식 비율 | 근거 |
|-------------|---------|---------|------|
| ≤ 60초 | ≤ 400m | 1:1 | Billat 2001 |
| 60 ~ 120초 | 400 ~ 800m | 1:1 ~ 1.5:1 (선형 보간) | Billat + Buchheit |
| 120 ~ 240초 | 800 ~ 1600m | 1.5:1 | Buchheit & Laursen 2013 |
| > 240초 | > 1600m | 2:1 | Buchheit & Laursen 2013 |

```
# 선형 보간 공식 (60~120초 구간)
rest_ratio = 1.0 + 0.5 × (rep_time_sec - 60) / 60
rest_sec = round(rep_time_sec × rest_ratio / 30) × 30  # 30초 단위
```

### 세트 수 상한 (Buchheit & Laursen 2013 총 볼륨 기준)

| rep 거리 | 총 볼륨 상한 | 최대 세트 |
|---------|------------|---------|
| ≤ 200m | 2.4km | floor(2400/rep_m) |
| ≤ 400m | 4.0km | floor(4000/rep_m) |
| ≤ 800m | 4.8km | floor(4800/rep_m) |
| ≤ 1200m | 6.0km | floor(6000/rep_m) |
| > 1200m | min(8km, 주간 8%) | floor(상한/rep_m) |

```
# 세트 수 계산
total_quality_km = weekly_volume_km × 0.08  # Daniels: I 주간 8% 상한
cap_km = 위 표의 상한
sets = min(
    floor(min(total_quality_km, cap_km) × 1000 / rep_distance_m),
    max_sets_from_table
)
```

### VO2max 자극 최소 보장
**근거:** Billat 2001 — "각 반복이 최소 60초 이상일 때 VO2max 완전 자극"

```
# rep_time < 60초면 경고 (VO2max 자극 불충분 가능)
if rep_time_sec < 60:
    warning = "반복 거리가 짧아 VO2max 완전 자극에 60초 미달. 세트 수 증가 권장."
```

### 사용자 커스텀 rep 거리
- 200m ~ 2000m 범위 내 자유 입력 (320m 등 비표준 거리 포함)
- 범위 밖이면 경고 표시 후 허용 (강제 제한 없음)

---

## 7. 주간 볼륨 계산

### 기준 볼륨 (CTL 기반)
**근거:** Coggan 2003, Banister 1991

```python
# CTL(TRIMP/day) → 주간 km 근사
# 개인 보정 계수 (avg_trimp_per_km)는 최근 90일 실제 데이터에서 계산
trimp_per_km = mean(recent_90d_trimp / recent_90d_km)  # 개인화
base_weekly_km = CTL * 7 / trimp_per_km
```

### Running Shape 보정
**근거:** MarathonShape 레이블 기반 현실적 볼륨 상한

| MarathonShape | 보정 | 의미 |
|--------------|------|------|
| insufficient (<40%) | × 0.70 | CTL 과대추정 방지 |
| base (40~60%) | × 0.85 | 점진적 빌드 |
| building (60~80%) | × 1.00 | 기준 |
| ready (80~90%) | × 1.05 | 피크 준비 |
| peak (>90%) | × 1.00 | 유지 |

### 훈련 단계 보정 + 테이퍼
**테이퍼 근거:** Mujika & Padilla 2003 MSSE 35(7):1182, Bosquet et al. 2007 MSSE 39(8):1358

| 레이스까지 주 수 | 단계 | 볼륨 보정 | 강도 |
|---------------|------|---------|------|
| > 16주 | base | × 0.90 | Z3 최소화 |
| 8~16주 | build | × 1.00 | T/I 도입 |
| 3~8주 | peak | × 1.05 | Z3 최대 |
| 2주 (taper) | taper | × **0.55** | **유지** |
| 1주 | taper | × **0.45** | **유지** |
| ≤ 3일 | taper | × **0.30** | **유지** |

> **⚠️ 테이퍼 시 interval→easy 변환 금지**
> Bosquet 2007 메타분석: 강도 유지 시 퍼포먼스 평균 +2.2% 향상.
> 볼륨만 감소, 강도 유지가 핵심.

### 3:1 사이클
3주 빌드 + 1주 회복(볼륨 -25%)을 기본 단위로 관리.
매 4번째 주는 TSB 회복 여부와 무관하게 회복주로 처리.

---

## 8. 훈련 거리 옵션

| label | km | Long run 최대 | 테이퍼 | 주요 강도 |
|-------|----|-------------|--------|---------|
| 1.5k | 1.5 | 8km | 5일 | R > I (Daniels R-pace 중심) |
| 3k | 3.0 | 10km | 7일 | R + I |
| 5k | 5.0 | 13km | 7~10일 | I 중심, T 보조 |
| 10k | 10.0 | 17km | 10일 | I + T 균형 |
| half | 21.095 | 23km | 14일 | T 중심, M-pace 도입 |
| full | 42.195 | 33km | 21일 (Mujika 2003) | E + M-pace 중심 |
| custom | 사용자 입력 | 목표의 80% | 거리 비례 보간 | 거리 기반 자동 선택 |

---

## 9. 동적 스케줄 배치

### 가용일 결정
```
available_days = {Mon~Sun} - rest_weekdays_mask - blocked_dates
```

### Q-day 수 결정 (Seiler 2009 기반)
```
n = len(available_days)
n ≤ 3 → Q 1회
n = 4~5 → Q 2회
n ≥ 6 → Q 2~3회 (shape ≥ building이면 3회)
Gate 1 ACWR > 1.3 → Q-day 수 -1
```

### Q-day 배치 원칙
**근거:** Seiler & Tønnessen 2009 — 고강도 세션 간 48~72시간 회복 필수

```
1. 가용일 중 간격 최대화 알고리즘으로 Q-day 배치
2. Q-day 최소 간격: 48시간 (2일)
3. Long run: 가용 주말(토/일) 마지막 날 우선
4. Q-day 다음날: Recovery (능동 회복, vVO2max의 60% = E-pace)
5. 나머지: Easy
```

---

## 10. VDOT 계열 메트릭 사용 전략

| 페이스 타입 | 사용 메트릭 | Fallback | 근거 |
|-----------|-----------|---------|------|
| E / Long / Recovery | VDOT_ADJ → Daniels E-pace | VDOT → E-pace | 현재 체력 반영 |
| M (마라톤 페이스) | VDOT_ADJ → Daniels M-pace | VDOT → M-pace | goal=full일 때만 |
| T (Tempo) | **eFTP** (= VDOT_ADJ T-pace, DB 저장값) | VDOT_ADJ → T-pace | 계산 재사용 |
| I (Interval) | VDOT_ADJ → Daniels I-pace | VDOT → I-pace | 97~100% VO2max |
| R (Repetition) | VDOT_ADJ → Daniels R-pace | VDOT → R-pace | 1.5K/3K 목표만 |

---

## 11. DB 변경 계획 (v2 → v3)

### 신규 테이블: `user_training_prefs`
```sql
CREATE TABLE user_training_prefs (
    id                    INTEGER PRIMARY KEY DEFAULT 1,
    -- 정기 휴식 요일 (비트마스크: bit0=월(1), bit1=화(2), ..., bit6=일(64))
    rest_weekdays_mask    INTEGER NOT NULL DEFAULT 0,
    -- 일회성 차단 날짜 JSON 배열 ["2026-04-05", ...]
    blocked_dates         TEXT    NOT NULL DEFAULT '[]',
    -- 인터벌 기본 반복 거리(m): 자유 입력 (200~2000, 320 같은 비표준 포함)
    interval_rep_m        INTEGER NOT NULL DEFAULT 1000,
    -- 주간 최대 Q-day 수 (0=자동)
    max_q_days            INTEGER NOT NULL DEFAULT 0,
    updated_at            TEXT
);
```

### 신규 테이블: `session_outcomes` (ML 데이터 기반)
```sql
CREATE TABLE session_outcomes (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    planned_id      INTEGER REFERENCES planned_workouts(id),
    activity_id     INTEGER REFERENCES activity_summaries(id),
    date            TEXT NOT NULL,
    -- 달성률
    planned_dist_km REAL,
    actual_dist_km  REAL,
    dist_ratio      REAL,        -- actual/planned
    -- 페이스 편차
    planned_pace    INTEGER,     -- sec/km
    actual_pace     INTEGER,
    pace_delta_pct  REAL,        -- (actual-planned)/planned
    -- 심박 분포 (Seiler 3존 기준)
    hr_z1_pct       REAL,
    hr_z2_pct       REAL,
    hr_z3_pct       REAL,
    target_zone     INTEGER,
    actual_avg_hr   INTEGER,
    hr_delta        INTEGER,
    -- 훈련 품질
    decoupling_pct  REAL,
    trimp           REAL,
    -- 컨디션 스냅샷 (훈련 시점 CRS + 구성요소)
    crs_at_session  REAL,
    tsb_at_session  REAL,
    hrv_at_session  REAL,
    bb_at_session   INTEGER,
    acwr_at_session REAL,
    -- ML 타겟 레이블
    -- 'on_target'|'overperformed'|'underperformed'|'skipped'|'modified'
    outcome_label   TEXT,
    computed_at     TEXT DEFAULT (datetime('now'))
);
```

### `planned_workouts` 컬럼 추가
```sql
-- 인터벌 처방 상세 (JSON)
-- {"rep_m":320,"sets":10,"rest_sec":94,"recovery_pace":330,"total_quality_km":3.2}
ALTER TABLE planned_workouts ADD COLUMN interval_prescription TEXT;
```

### `goals` 컬럼 추가
```sql
-- '1.5k'|'3k'|'5k'|'10k'|'half'|'full'|'custom'
ALTER TABLE goals ADD COLUMN distance_label TEXT;
```

---

## 12. 피드백 반영 재조정 규칙

session_outcomes 데이터 기반 자동 보정:

| 조건 | 조치 | 근거 |
|------|------|------|
| 최근 3주 dist_ratio 평균 < 0.85 | 주간 볼륨 -10% | 목표 과도 탐지 |
| 최근 3주 pace_delta_pct > +5% | eFTP 재계산 트리거 | 체력 과대 추정 |
| 연속 2회 hr_delta > +10bpm | Z3→Z2 다운그레이드 + CRS 감점 | 강도 과도 |
| 최근 2회 decoupling > 5% | Long run 거리 동결 | Friel 2012: 유산소 기반 부족 |
| 최근 3회 crs_at_session 평균 < 55 | Q-day 수 -1 | 자동 보호 |

---

## 13. ML 파이프라인 설계 (v0.4 예정)

### 목적
session_outcomes가 충분히 쌓이면(목표: 100회 이상):
1. **CRS 가중치 개인화** — 각 메트릭이 실제 outcome_label에 미치는 영향을 회귀 분석으로 도출
2. **달성률 예측** — 처방 + 컨디션 → dist_ratio 예측 → 목표 거리 자동 보정
3. **스킵 예측** — 훈련 취소 가능성 예측 → 선제적 재조정 제안

### Feature Matrix

```python
# 입력 피처 (X)
features = [
    # 처방
    "workout_type",        # categorical
    "planned_dist_km",
    "planned_pace",
    "interval_rep_m",

    # 컨디션 (훈련 당일)
    "crs_at_session",
    "tsb_at_session",
    "hrv_at_session",
    "bb_at_session",
    "acwr_at_session",

    # 이력 (rolling)
    "dist_ratio_3w_avg",   # 최근 3주 달성률 평균
    "pace_delta_3w_avg",   # 최근 3주 페이스 편차
    "hr_delta_5s_avg",     # 최근 5회 HR 편차
    "skip_rate_4w",        # 최근 4주 스킵률
]

# 예측 타겟 (y)
targets = {
    "dist_ratio":       "회귀 (달성률 예측)",
    "actual_pace":      "회귀 (실제 페이스 예측 → eFTP 교정)",
    "outcome_label":    "분류 (on_target/over/under/skipped)",
}
```

### 모델 후보
- 초기: LinearRegression (dist_ratio, actual_pace), LogisticRegression (outcome_label)
- 충분한 데이터 후: GradientBoosting / XGBoost (비선형 관계 포착)
- 데이터 < 30회: 규칙 기반만 사용 (ML 비활성)

### CRS 가중치 자동 도출
```python
# outcome이 'on_target' or 'overperformed'인 세션만 사용
# outcome = f(TSB, HRV, BB, ACWR, CIRS, ...)
from sklearn.linear_model import LogisticRegression
model = LogisticRegression()
model.fit(X_signals, y_outcome_binary)
# model.coef_ → 각 신호의 실제 영향력 → 새 CRS 가중치로 적용
```

---

## 14. 영향 파일 목록

| 파일 | 변경 내용 | 단계 |
|------|----------|------|
| `src/db_setup.py` | v3 마이그레이션, 신규 테이블 3개, 컬럼 추가 2개 | 1A |
| `src/metrics/crs.py` | 신규: CRS 계산 + 게이트 필터 | 1B |
| `src/training/interval_calc.py` | 신규: 인터벌 처방 계산 (Billat/Buchheit) | 1C |
| `src/training/planner.py` | 전면 개편: 게이트 기반, 동적 배분, eFTP 페이스 | 1C |
| `src/training/goals.py` | distance_label 필드 추가 | 1A |
| `src/training/matcher.py` | session_outcomes 저장 확장 | 1E |
| `src/training/replanner.py` | 피드백 반영 재조정 규칙 | 1F |
| `src/web/views_settings.py` | 휴식 요일/날짜/인터벌 설정 UI | 1G |
| `src/web/views_training.py` | 훈련 생성 폼 (거리 옵션) | 1G |
| `src/web/views_training_cards.py` | 인터벌 카드 세트/rep/휴식 표시 | 1G |
| `src/web/views_training_crud.py` | distance_label, interval_prescription 저장 | 1G |
| `src/ml/` (신규 폴더) | feature pipeline, 모델 학습/예측 | v0.4 |

---

## 15. 참고 문헌

| 논문 | 핵심 적용 |
|------|---------|
| Banister EW. (1991). "Modeling elite athletic performance." Physiological Testing of Elite Athletes. | CTL τ₁=42일, ATL τ₂=7일 |
| Billat VL. (2001). "Interval Training for Performance." Sports Medicine 31(1):13-31. | 인터벌 1:1 휴식, vVO2max 60초 최소 |
| Bosquet L et al. (2007). "Effects of Tapering on Performance." MSSE 39(8):1358-1365. | 테이퍼 2주, 볼륨 -41~60%, 강도 유지 +2.2% |
| Buchheit M & Laursen PB. (2013). "HIIT, Solutions to the Programming Puzzle." Sports Medicine 43(5),(10). | rep 거리별 총 볼륨 상한, 휴식 비율 |
| Coggan AR. (2003). "The Training Stress Score (TSS)." TrainingPeaks white paper. | TSB 해석 기준 |
| Daniels J. (2014). Daniels' Running Formula 3rd Ed. Human Kinetics. | VDOT, E/M/T/I/R 페이스, 세션 볼륨 상한 |
| Foster C. (1998). "Monitoring training in athletes with reference to overtraining syndrome." MSSE 30(7):1164. | Monotony > 2.0 경계값 |
| Friel J. (2012). The Triathlete's Training Bible. VeloPress. | Decoupling 5% 기준 |
| Gabbett TJ. (2016). "The training–injury prevention paradox." BJSM 50(5):273-280. | ACWR 1.0~1.3 최적, >1.5 위험 |
| Halson SL. (2014). "Monitoring Training Load to Understand Fatigue in Athletes." Sports Medicine 44(S2):139-147. | 다중 지표 조합 원칙 |
| Mujika I & Padilla S. (2003). "Scientific bases for precompetition tapering strategies." MSSE 35(7):1182-1187. | 테이퍼 2주 최적, 지수형 권장 |
| Plews DJ et al. (2013). "Training adaptation and heart rate variability in elite endurance athletes." IJSPP 8(4):456-465. | HRV rolling 평균 기반 훈련 조정 |
| Seiler S. (2010). "What is best practice for training intensity and duration distribution?" IJSPP 5(3):276-291. | 80/20 배분, 3존 정의 |
| Seiler S & Tønnessen E. (2009). "Intervals, Thresholds, and Long Slow Distance." IJSPP 4(3):334-352. | 고강도 세션 간 48~72h 회복 |
| Simpson NS et al. (2017). "Optimizing sleep to maximize performance." Scandinavian Journal of Medicine & Science in Sports. | 수면과 운동 퍼포먼스 |
| Stöggl T & Sperlich B. (2014). "Polarized training has greater impact on key endurance variables." Frontiers in Physiology 5:33. | Polarized vs Threshold 효과 비교 |
