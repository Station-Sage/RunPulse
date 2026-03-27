# v0.2 메트릭 정의 — PDF 원본 버전

> 이 파일은 사용자가 제공한 PDF 원본(HTML 변환)에서 추출한 확정 계산식입니다.
>
> - `design/1_러닝플랫폼_1차_상세메트릭.html` — 7개 플랫폼 1차 메트릭
> - `design/2_러닝플랫폼_2차_가공메트릭_후보군.html` — 16개 2차 가공 메트릭
>
> Claude 연구 버전 비교: `metrics_by_claude.md` 참조.
> 나중에 두 버전을 비교하여 최종 채택 또는 사용자 선택 옵션으로 구현 예정.

---

## 1차 메트릭 핵심 공식 (PDF 1번 파일)

### PMC — ATL/CTL/TSB (정확한 공식)
```python
# tau_atl=7일, tau_ctl=42일
atl_today = atl_prev * exp(-1/7)  + load * (1 - exp(-1/7))
ctl_today = ctl_prev * exp(-1/42) + load * (1 - exp(-1/42))
tsb_today = ctl_today - atl_today
```

**TSB Form 해석 (intervals.icu 기준):**
| TSB 범위 | 상태 |
|----------|------|
| +25 이상 | 탈훈련 (Fresh but Detrained) |
| +5 ~ +25 | 레이스 준비 (Race Ready) |
| -10 ~ +5 | 최적 훈련 (Optimal Training) |
| -30 ~ -10 | 고강도 훈련 (High Load) |
| -30 이하 | 과훈련 (Overtraining) |

**부하값 우선순위:** Power TSS > rTSS (pace 기반) > HRSS (HR 기반)

### TRIMP — TRIMPexp (Banister 1991)
```python
hr_ratio = (hr_avg - hr_rest) / (hr_max - hr_rest)
y = 1.92  # 남성 / 여성: 1.67
TRIMP = duration_min * hr_ratio * 0.64 * exp(y * hr_ratio)

# HRSS (기준: LTHR에서 1시간 = 100점)
lthr_ratio = (hr_lthr - hr_rest) / (hr_max - hr_rest)
trimp_ref = 60 * lthr_ratio * 0.64 * exp(y * lthr_ratio)
HRSS = (TRIMP / trimp_ref) * 100
```

### Monotony & Training Strain (Banister)
```python
monotony = mean(trimp_7days) / std(trimp_7days)   # std=0이면 inf
strain   = monotony * sum(trimp_7days)
```

### Aerobic Decoupling (Intervals.icu 방식)
```python
# NGP(m/min) = Normalized Grade Pace 기반 EF 사용
mid = len(series) // 2
ef1 = pace_series[:mid].mean() / hr_series[:mid].mean()
ef2 = pace_series[mid:].mean() / hr_series[mid:].mean()
decoupling_pct = (ef1 - ef2) / ef1 * 100
# 기준: <5% 양호, 5~10% 보통, >10% 낮은 유산소 피트니스
```

### GAP — Grade Adjusted Pace (Strava)
```python
# 오르막 (grade >= 0)
effort_factor = 1 + 0.0333 * grade_pct + 0.0001 * grade_pct**2
# 내리막 (grade < 0, 최소 -10% 적용)
g = max(grade_pct, -10)
effort_factor = 1 + 0.0333 * g + 0.0001 * g**2

GAP = actual_pace / effort_factor  # min/km 단위 그대로
```

### Strava Relative Effort
```python
zone_coefficients = [0.5, 1.0, 2.0, 3.5, 5.5]  # Zone 1~5
RE = sum(time_in_zone_sec[i] / 60 * coeff[i] for i in range(5))
```

### VDOT — Jack Daniels (Daniels-Gilbert 공식)
```python
velocity = distance_m / time_min  # m/min
vo2 = -4.60 + 0.182258 * velocity + 0.000104 * velocity**2
pct_max = (0.8
           + 0.1894393 * exp(-0.012778 * time_min)
           + 0.2989558 * exp(-0.1932605 * time_min))
VDOT = vo2 / pct_max
```

### Effective VO2max (Runalyze)
```python
velocity = 1000 / pace_min_per_km  # m/min
hr_ratio = (hr_avg - hr_rest) / (hr_max - hr_rest)
pct_vo2max = 0.64 * hr_ratio + 0.37
vo2 = velocity * 0.2 + 3.5
vo2max = (vo2 / pct_vo2max) * correction_factor  # correction_factor: 0.85~0.95
```

### Race Shape (RunPulse v3) — 5요소 종합 준비도
```python
# 거리별 목표 (Pfitzinger/Daniels 기반)
#              주간볼륨     최장거리     장거리기준  장거리횟수  기간
# 10K:     35~45km     12~20km      12km+      4회      6주
# 하프:    45~60km     18~28km      16km+      5회      8주
# 마라톤:  60~80km     28~37km      25km+      6회     12주

# 5요소 가중 배합 — 거리별 차등 (스포츠과학 논문 기반)
#                 볼륨  최장  빈도  일관성 페이스
# 10K  (Midgley): 20%   8%   5%   27%   40%  ← VO2max/역치 지배
# 하프 (Schmid):  28%  18%  12%   17%   25%  ← 균형
# 마라톤(Hagan):  34%  27%  19%   10%   10%  ← 볼륨/장거리 지배
#
# References:
#   Hagan et al. (1981,1987) — 마라톤 r: 주간거리-0.76, 최장-0.60, 빈도-0.43
#   Schmid et al. (2012) — 하프 예측: 훈련속도 > 주간km > 빈도
#   Midgley et al. (2007) — 10K: VO2max가 성적 분산 80% 설명
weekly_score  = min(1.0, weekly_avg / target_weekly)
long_score    = min(1.0, longest_km / target_long)
freq_score    = min(1.0, long_run_count / target_count)
# 일관성: N주 주당 횟수 변동계수(CV) 기반
consistency   = active_ratio × cv_score × freq_score
# 장거리 페이스 품질: VDOT E-pace ±15% 범위 내 비율
quality       = good_pace_runs / total_long_runs

shape_pct = (weekly * 0.35 + long * 0.20 + freq * 0.20
           + consistency * 0.15 + quality * 0.10) * 100
```

### maxHR (최대심박 추정)
```python
# A. Strava stream 기반 (가장 정확)
#    30초 슬라이딩 윈도우 평균 HR의 최대값
#    References: ACSM(2018), Beltz(2016), Robergs(2002)
maxHR = max(mean(hr[i:i+30]) for i in range(len(hr)-30))

# B. 활동 max_hr 기반 (fallback)
#    고강도 활동(avg_hr/max_hr > 75%) 상위 10개 → IQR 이상치 제거 → 최대값

# 시계열 저장: computed_metrics('maxHR', date)
# 28일 캐시 재사용 (단기간 maxHR 변동 미미)
```

### VDOT (소스 우선순위)
```python
# 1. 최근 레이스 기록 (8주 이내, 가장 정확)
#    - HR 검증: avg_hr ≥ maxHR × 82%
#    - 거리 검증: 공식 거리(5K/10K/하프/풀) ±5%
#    - FEARP 환경 보정 (날씨/고도/경사)
#    - 복수 레이스: 중앙값, 교차 검증 ±20%
# 2. 고강도 활동 가중 평균 (레이스 없을 때)
# 3. Runalyze / Garmin fallback
```

### VDOT_ADJ (현재 체력 보정 VDOT)
```python
# 역치 페이스 추출 (3단계 fallback):
# A. Strava stream: HR 역치 구간(Karvonen HRR 85~92%) 실제 속도
#    - 인터벌 세션에서도 고강도 구간만 추출
#    - HR 스파이크 ±30bpm 제거, 속도 0.5m/s+ 필터
# B. 연속 역치런: avg_hr 역치 범위, 20~60분, IQR 이상치 제거
# C. HR-페이스 회귀: HR 88%에서 예측 (최후 fallback)

# 역치 HR 범위 — Karvonen HRR 개인화
#   References: Karvonen(1957), Daniels(2014)
hrr = maxHR - restingHR  # restingHR = 웰니스 7일 중앙값
hr_lo = restingHR + hrr × 0.75   # LT 하한
hr_hi = restingHR + hrr × 0.88   # LT 상한

# Daniels T-pace 역보간 → VDOT_ADJ
# 보정 범위 (Daniels/Pugh 1970/Garmin 기준):
#   레이스 0~4주: ±3%, 4~8주: ±5%, 8주+: ±7%
```

### CTL/ATL/TSB 자체 계산 (RunPulse)
```python
# Intervals.icu 미제공 날짜를 DailyTRIMP 기반으로 자체 계산
CTL(n) = CTL(n-1) + (TRIMP(n) - CTL(n-1)) / 42  # 만성 훈련 부하
ATL(n) = ATL(n-1) + (TRIMP(n) - ATL(n-1)) / 7   # 급성 훈련 부하
TSB(n) = CTL(n) - ATL(n)                          # 훈련 스트레스 밸런스
# Intervals 값 있으면 유지, 없는 날짜만 채움
```

### rTSS — Running TSS (TrainingPeaks)
```python
ngp_m_per_min  = 1000 / ngp_min_per_km
ftp_m_per_min  = 1000 / ftp_pace_min_per_km
IF = ngp_m_per_min / ftp_m_per_min
rTSS = (duration_sec * ngp_m_per_min * IF) / (ftp_m_per_min * 3600) * 100
```

### Vertical Ratio (Garmin)
```python
VR = (vertical_oscillation_cm / stride_length_cm) * 100  # 이상: 6~8%
```

### Critical Power (Stryd)
```python
P(t) = W_prime / t + CP          # 2파라미터 모델
# CP, W' 추정: P*t = W' + CP*t 선형 회귀
work = [p * t for p, t in zip(powers, durations)]
coeffs = np.polyfit(durations, work, 1)
CP = coeffs[0]; W_prime = coeffs[1]
```

---

## 2차 메트릭 확정 공식 (PDF 2번 파일)

### 구현 우선순위 매트릭스 (PDF 기준)

| 우선순위 | 메트릭 | 계산 난이도 | 데이터 요건 |
|---------|--------|------------|------------|
| ★★★★★ | CIRS | 중 | TRIMP, Garmin GCT |
| ★★★★★ | FEARP | 하 | Strava GPS, 날씨 API |
| ★★★★★ | DI | 중 | Strava stream, 90분+ 세션 |
| ★★★★★ | DARP | 중 | Runalyze VDOT, DI |
| ★★★★☆ | UTRS | 중 | Garmin 수면/HRV, intervals.icu TSB |

**0-3개월 즉시 구현:** LSI, FEARP, ADTI, TIDS, SAPI
**3-6개월 구현:** CIRS, UTRS, DI, REC, RRI
**6-12개월 (ML):** TQI, TEROI, PLTD

---

### UTRS — Unified Training Readiness Score
- **범위**: 0–100 (높을수록 훈련 준비 완료)
- **PDF 확정 계산식**:
  ```
  UTRS = sleep_score      × 0.25  # Garmin sleep score (0-100)
       + hrv_status       × 0.25  # HRV 정규화 점수 (0-100)
       + tsb_normalized   × 0.20  # TSB 정규화 (TSB -30~+25 → 0~100)
       + resting_hr_score × 0.15  # 안정 심박 역정규화 (낮을수록 높은 점수)
       + sleep_consistency × 0.15 # 수면 일관성 (7일 취침/기상 편차 역수)
  ```
  ```python
  tsb_normalized     = clamp((tsb + 30) / 55 * 100, 0, 100)
  resting_hr_score   = clamp((80 - resting_hr) / 30 * 100, 0, 100)  # 50~80bpm 범위
  sleep_consistency  = clamp(100 - std(sleep_start_7days_min) / 60 * 20, 0, 100)
  ```
- **등급**: 0-40(휴식), 41-60(경량 훈련), 61-80(보통), 81-100(최적)

---

### CIRS — Composite Injury Risk Score
- **범위**: 0–100 (낮을수록 안전)
- **PDF 확정 계산식**:
  ```
  CIRS = ACWR_risk     × 0.4   # 급성/만성 부하 비율
       + Monotony_risk × 0.2   # 훈련 단조성
       + Spike_risk    × 0.3   # 주간 부하 급상승
       + Asym_risk     × 0.1   # 좌우 비대칭 (GCT 기반)
  ```
  ```python
  # ACWR_risk
  ACWR = sum(trimp_7d) / mean(trimp_28d_daily)
  acwr_risk = 100 if ACWR > 1.5 else 70 if ACWR > 1.3 else 30 if ACWR < 0.8 else 0

  # Monotony_risk
  mono = mean(trimp_7d) / std(trimp_7d)
  mono_risk = 100 if mono > 2.0 else 60 if mono > 1.5 else 0

  # Spike_risk (LSI 기반)
  LSI = this_week_load / last_week_load
  spike_risk = 100 if LSI > 1.3 else 50 if LSI > 1.1 else 0

  # Asym_risk (Garmin GCT 좌우 비대칭)
  asym_pct = abs(gct_left - gct_right) / ((gct_left + gct_right) / 2) * 100
  asym_risk = min(100, asym_pct * 5)  # 20% 비대칭 = 100점
  # Garmin GCT 데이터 없으면 asym_risk = 0, 나머지 3요소 정규화
  ```
- **등급**: 0-20(안전), 21-50(주의), 51-80(경고), 81-100(위험)

---

### LSI — Load Spike Index
- **정의**: 갑작스러운 훈련량 급증 감지
- **PDF 확정 계산식**:
  ```python
  LSI = today_load / rolling_21day_avg_load
  ```
- **기준**: <0.8(훈련 부족), 0.8-1.3(정상), 1.3-1.5(주의), >1.5(위험)

---

### FEARP — Field-Equivalent Adjusted Running Pace
- **정의**: 실제 페이스를 표준 조건(15°C, 습도 50%, 평지, 해발 0m)으로 환산
- **PDF 확정 계산식**:
  ```python
  temp_factor     = 1 + max(0, temp_c - 15) * 0.004      # 1°C당 +0.4%
  humidity_factor = 1 + max(0, humidity_pct - 50) * 0.001 # 1%당 +0.1%
  altitude_factor = 1 - altitude_m * 0.00011              # 100m당 -1.1%
  # grade_factor: GAP effort_factor (위 GAP 공식)

  fearp = actual_pace_sec_km / (temp_factor * humidity_factor / altitude_factor / grade_factor)
  ```
- **Fallback**: GPS 고도 없으면 grade_factor=1.0; 날씨 API 실패 시 temp=15, humidity=50

---

### ADTI — Aerobic Decoupling Trend Index
- **정의**: 8주 Aerobic Decoupling 값의 선형 회귀 기울기 (개선 추세)
- **PDF 확정 계산식**:
  ```python
  slope, _ = np.polyfit(range(len(weekly_decoupling)), weekly_decoupling, 1)
  ADTI = slope  # 음수=개선(감소), 양수=악화(증가)
  ```
- **기준**: <-0.5%/주 우수한 개선, -0.5~0 완만한 개선, >0 악화

---

### DI — Durability Index
- **정의**: 장거리 세션에서 심박 대비 페이스 유지력
- **PDF 확정 계산식**:
  ```python
  # t구간의 pace/HR 비율을 초반(t=0) 대비로 비교
  DI(t) = (pace_t / pace_0) / (HR_t / HR_0)
  # DI >= 1.0: 후반에도 같은 HR에서 같은 pace 유지 (이상적)
  # DI < 1.0: 같은 HR이어도 후반 pace 저하 (내구성 부족)

  # 요약: 최근 8주 90분+ 세션의 DI 구간별 평균
  di_summary = mean(DI_values_across_sessions)
  ```
- **최소 데이터 요건**: 90분+ 세션, 8주간 3회 이상 (미충족 시 None 반환)
- **None 처리**: UI에서 "장거리 세션 부족 (8주 3회 이상 필요)" 표시

---

### DARP — Dynamic Adjusted Race Predictor (v4)
- **정의**: Daniels VDOT 테이블 기반 + DI + Race Shape + EF 4요소 보정 레이스 예측
- **계산식**:
  ```python
  # 1. Daniels 테이블에서 기본 예측 시간 (선형 보간)
  base_time = daniels_table.get_race_predictions(vdot)[dist_key]

  # 2. DI 보정 (하프/풀만, 0~100 스케일)
  #    DI 70+ → 0%, DI 0 → +8%
  di_penalty = (70 - clamp(DI, 0, 100)) / 70 * 0.08  if DI < 70

  # 3. Race Shape 보정 (거리별 가중)
  #    Shape 80+ → 0%, Shape 0 → 최대 15%
  #    5K ×0.3, 10K ×0.5, 하프 ×0.8, 풀 ×1.0
  shape_penalty = (80 - clamp(Shape, 0, 100)) / 80 * 0.15 * dist_factor

  # 4. EF 보정 (10K 이상, 7일 평균)
  #    EF ≥ 1.0 → 최대 -3% 보너스, EF < 1.0 → 최대 +3% 페널티
  ef_bonus = -min(0.03, (EF - 1.0) * 0.06)  if EF >= 1.0
  ef_bonus = +min(0.03, (1.0 - EF) * 0.06)  if EF < 1.0

  darp_time = base_time × (1 + di_penalty) × (1 + shape_penalty) × (1 + ef_bonus)
  ```
- **저장**: `computed_metrics` (date, 'DARP_5k'/'DARP_10k'/'DARP_half'/'DARP_full', value=time_sec)
- **UI**: 모든 예측 카드에 VDOT / DI / Shape / EF 4배지 일관 표시

---

### RMR — Runner Maturity Radar
- **정의**: **5개 축** 레이더 차트 (각 0-100)
- **PDF 확정 5개 축**:
  ```python
  axes = {
    "유산소용량":   clamp(vo2max / 65 * 100, 0, 100),
    "역치강도":     clamp(hr_lthr / hr_max * 100, 0, 100),
    "지구력":       di_summary * 100,          # DI 0~1 → 0~100
    "동작효율성":   cadence_score * 0.5 + vr_score * 0.5,
    "회복력":       (body_battery_score + sleep_score) / 2,
  }

  # cadence_score: 170-185 spm = 100, 이탈 시 감점
  cadence_score = clamp(100 - abs(cadence - 178) * 3, 0, 100)
  # vr_score: VR 6~8% = 100 (낮을수록 좋음)
  vr_score = clamp(100 - max(0, vr_pct - 6) * 20, 0, 100)
  ```

---

### TIDS — Training Intensity Distribution Score
- **정의**: 심박존별 훈련 강도 분포 + 목표 모델 편차
- **PDF 확정 목표 모델**:
  | 모델 | Zone1-2 | Zone3 | Zone4-5 |
  |------|---------|-------|---------|
  | 폴라리제드 | 80% | 5% | 15% |
  | 피라미드 | 70% | 20% | 10% |
  | 건강유지 | 60% | 30% | 10% |

  ```python
  z12 = (z1_min + z2_min) / total_min * 100
  z3  = z3_min / total_min * 100
  z45 = (z4_min + z5_min) / total_min * 100

  # 폴라리제드 편차 (낮을수록 좋음)
  polar_dev = abs(z12 - 80) + abs(z3 - 5) + abs(z45 - 15)
  ```
- **저장**: `computed_metrics` (date, 'tids', JSON {z12, z3, z45, polar_dev, pyramid_dev, health_dev})

---

## 버전 비교 요약

| 메트릭 | Claude 버전 (metrics_by_claude.md) | PDF 버전 (이 파일) | 핵심 차이 |
|--------|-----------------------------------|-------------------|-----------|
| **UTRS** | body_battery×0.30 + tsb×0.25 + sleep×0.20 + hrv×0.15 + stress×0.10 | sleep×0.25 + hrv×0.25 + tsb×0.20 + rhr×0.15 + sleep_consistency×0.15 | body_battery 제거, sleep consistency 추가 |
| **CIRS** | ACWR×0.4 + LSI×0.25 + consecutive×0.20 + fatigue×0.15 | ACWR×0.4 + Monotony×0.2 + Spike×0.3 + Asym×0.1 | Monotony/Asymmetry 기반 전환 |
| **DI** | 페이스 저하율법 (pace_drop_pct × 5) | pace/HR 비율법 DI(t) = (pace_t/pace_0)/(HR_t/HR_0) | HR 변화 고려 여부 |
| **RMR** | 6개 축 (경제성 포함) | 5개 축 (경제성 제외) | 경제성 축 유무 |
| **FEARP** | 동일 (기온/습도/고도/경사) | 동일 | 거의 동일 |
| **TRIMP** | 동일 (Banister TRIMPexp) | 동일 | 동일 |
| **ACWR** | 동일 | 동일 | 동일 |
