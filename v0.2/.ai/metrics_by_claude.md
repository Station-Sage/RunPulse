# v0.2 메트릭 정의 — Claude 연구 버전

> 이 파일은 Claude가 공개된 자료(논문, 플랫폼 문서, 커뮤니티 분석 등)를 바탕으로
> 독립적으로 조사·추정한 계산식입니다.
>
> PDF 원본 기반 확정 계산식은 `metrics.md` 참조.
> 나중에 두 버전을 비교하여 최종 채택 또는 사용자 선택 옵션으로 구현 예정.

---

## 1차 메트릭 (소스별 sync)

### Garmin
| 메트릭 | 필드 | 단위 | 비고 |
|--------|------|------|------|
| VO2Max | `vo2max_precise` | ml/kg/min | daily_fitness |
| HRV Status | `hrv_weekly_average` | ms | daily_fitness |
| Body Battery | `body_battery_delta` | 0-100 | daily_fitness |
| Sleep Score | `sleep_score` | 0-100 | daily_fitness |
| Stress (고스트레스) | `stress_high_duration` | 분 | daily_fitness |
| Training Effect (유산소) | `aerobic_te` | 0-5 | activity_detail_metrics |
| Training Effect (무산소) | `anaerobic_te` | 0-5 | activity_detail_metrics |
| Recovery Time | `recovery_time` | 시간 | activity_detail_metrics |
| Ground Contact Time | `gct_ms` | ms | activity_detail_metrics |
| Vertical Oscillation | `vo_cm` | cm | activity_detail_metrics |
| Vertical Ratio | `vr_pct` | % | activity_detail_metrics |
| Cadence | `avg_cadence` | spm | activity_summaries |

### Strava
| 메트릭 | 필드 | 단위 | 비고 |
|--------|------|------|------|
| Relative Effort | `suffer_score` | 정수 | activity_detail_metrics |
| Best Efforts | `best_efforts` | JSON | activity_detail_metrics |
| HR Stream | stream.heartrate | bpm[] | activity_detail_metrics |
| Pace Stream | stream.velocity_smooth | m/s[] | activity_detail_metrics |
| Altitude Stream | stream.altitude | m[] | activity_detail_metrics |
| Cadence Stream | stream.cadence | rpm[] | activity_detail_metrics |

### Intervals.icu
| 메트릭 | 필드 | 단위 | 비고 |
|--------|------|------|------|
| CTL (Fitness) | `ctl` | TSS | daily_fitness |
| ATL (Fatigue) | `atl` | TSS | daily_fitness |
| TSB (Form) | `tsb` | TSS | daily_fitness |
| TRIMP | `trimp` | AU | activity_detail_metrics |
| HR Zones | `hr_zones` | JSON | activity_detail_metrics |

### Runalyze
| 메트릭 | 필드 | 단위 | 비고 |
|--------|------|------|------|
| eVO2Max | `effective_vo2max` | ml/kg/min | activity_detail_metrics |
| VDOT | `vdot` | AU | activity_detail_metrics |
| Marathon Shape | `marathon_shape` | % | activity_detail_metrics |
| Race Prediction | `race_prediction` | JSON {5k,10k,half,full} | activity_detail_metrics |

---

## 2차 메트릭 (RunPulse 계산 — Claude 추정)

### UTRS — Unified Training Readiness Score (통합 훈련 준비도)
- **범위**: 0–100 (높을수록 훈련 준비 완료)
- **Claude 추정 계산식**:
  ```
  UTRS = 0.30 * normalize(body_battery_end, 0, 100)
       + 0.25 * normalize(tsb + 50, 0, 100)          # TSB 일반적으로 -30~+20
       + 0.20 * normalize(sleep_score, 0, 100)
       + 0.15 * normalize(hrv_ratio, 0, 100)          # HRV / 개인 기준치
       + 0.10 * (1 - normalize(stress_high_duration, 0, 480))
  ```
- **근거**: Body Battery는 Garmin의 핵심 회복 지표(30%), TSB는 훈련 부하 균형(25%), 수면은 회복(20%), HRV는 자율신경 상태(15%), 스트레스는 역방향(10%)
- **입력 소스**: Garmin(body_battery, sleep_score, hrv, stress), Intervals.icu(TSB)
- **등급**: 0-40(빨강,휴식), 41-60(주황,경량), 61-80(초록,보통), 81-100(파랑,최적)

### CIRS — Composite Injury Risk Score (복합 부상 위험 스코어)
- **범위**: 0–100 (낮을수록 안전)
- **Claude 추정 계산식**:
  ```
  ACWR = 7일_총부하 / 28일_일평균부하
  LSI  = 이번주거리 / 지난주거리

  CIRS = 0.40 * acwr_risk(ACWR)
       + 0.25 * lsi_risk(LSI)              # 주간 거리 급상승
       + 0.20 * consecutive_days_risk(연속훈련일수)  # 연속 훈련일 기반 피로
       + 0.15 * normalize(ctl - tsb, 0, 100)        # 누적 피로
  ```
  ```python
  # acwr_risk
  if ACWR > 1.5: return 100
  elif ACWR > 1.3: return 70
  elif ACWR < 0.8: return 30
  else: return 0

  # lsi_risk
  if LSI > 1.3: return 100
  elif LSI > 1.1: return 50
  else: return 0

  # consecutive_days_risk
  if days >= 6: return 100
  elif days >= 5: return 80
  elif days >= 4: return 60
  else: return 0
  ```
- **근거**: ACWR이 부상 위험의 가장 강한 지표(40%), 주간 급증은 스트레스 누적(25%), 연속 훈련은 근골격계 회복 저하(20%), 전체 피로 수준(15%)
- **등급**: 0-20(안전), 21-50(주의), 51-80(경고), 81-100(위험)

### FEARP — Field-Equivalent Adjusted Running Pace (환경 보정 페이스)
- **정의**: 실제 달린 페이스를 표준 조건(15°C, 습도 50%, 평지, 해발 0m)으로 환산
- **Claude 추정 계산식**:
  ```python
  temp_factor  = 1 + max(0, temp_c - 15) * 0.004     # 15°C 초과 시 1°C당 +0.4%
  humid_factor = 1 + max(0, humidity - 50) * 0.001   # 50% 초과 시 1%당 +0.1%
  alt_factor   = 1 - altitude_m * 0.00011            # 100m당 -1.1% (VO2 기반)
  grade_factor = 1 + grade_pct * 0.03               # 1% 경사당 +3%

  adj_factor = temp_factor * humid_factor / alt_factor / grade_factor
  fearp_sec_km = actual_pace_sec_km / adj_factor
  ```
- **근거**: 더위와 습도에 따른 퍼포먼스 저하 연구(Ely et al., 2010); 고도별 VO2max 저하 곡선; GAP 근사 경사 보정

### DARP — Dynamic Age-Adjusted Race Predictor (레이스 예측)
- **정의**: 현재 피트니스 기반 목표 거리 완주 예상 시간
- **Claude 추정 계산식 (Riegel 공식 기반)**:
  ```python
  base_time = known_race_time * (target_dist / known_dist) ** 1.06
  vdot_factor = runalyze_vdot / 50.0  # 50을 기준치로 정규화
  di_factor = 1 + (1 - di_score/100) * 0.05  # DI 낮을수록 후반 저하
  darp = base_time * di_factor / vdot_factor
  ```
- **근거**: Riegel(1977) 지구력 경기 예측 공식; VDOT은 현재 피트니스 보정; DI는 마라톤 후반부 저하 보정

### DI — Durability Index (내구성 지수)
- **범위**: 0–100 (높을수록 후반 페이스 유지력 우수)
- **Claude 추정 계산식**:
  ```python
  # 최근 8주 90분+ 세션에서 전반(1/3) vs 후반(1/3) 페이스 비교
  pace_drop_pct = (avg_pace_last_third - avg_pace_first_third) / avg_pace_first_third * 100
  DI = 100 - clamp(pace_drop_pct * 5, 0, 100)  # 1% 저하당 5점 감점
  ```
- **근거**: Maronese et al. DI 개념; 페이스 저하율이 내구성의 직관적 지표

### RMR — Runner Maturity Radar (러너 성숙도 레이더)
- **정의**: 6개 축 레이더 차트 (각 0-100)
- **Claude 추정 6개 축**:
  1. **유산소 용량**: VO2Max / 65 * 100
  2. **역치 강도**: LTHR / HRmax * 100
  3. **지구력**: DI 점수
  4. **동작 효율성**: 케이던스 정규화(170-185spm=100) + Vertical Ratio 역수
  5. **회복력**: body_battery 회복 속도 + sleep_score
  6. **경제성**: Running Economy (EF 정규화)
- **근거**: 러너 발달의 6차원 모델 (유산소/역치/지구/동작/회복/경제)

### PMC — Performance Management Chart
- **계산 방법**: intervals.icu 동기화 데이터 그대로 사용
- **자체 계산 (폴백)**:
  ```python
  CTL_today = CTL_yesterday * exp(-1/42) + TRIMP_today * (1 - exp(-1/42))
  ATL_today = ATL_yesterday * exp(-1/7)  + TRIMP_today * (1 - exp(-1/7))
  TSB_today = CTL_today - ATL_today
  ```

### ACWR — Acute:Chronic Workload Ratio
- **계산식**:
  ```python
  acute   = sum(trimp, last_7_days)
  chronic = mean(trimp_per_day, last_28_days)
  ACWR = acute / (chronic * 7)
  ```
- **스위트스팟**: 0.8–1.3

### Aerobic Decoupling (Pa:HR)
- **계산식**:
  ```python
  ef1 = avg_pace_first_half  / avg_hr_first_half
  ef2 = avg_pace_second_half / avg_hr_second_half
  decoupling_pct = (ef1 - ef2) / ef1 * 100
  ```
- **기준**: <5% 양호, 5-10% 보통, >10% 낮은 유산소 피트니스

### TIDS — Training Intensity Distribution Score
- **계산식**: Garmin HR Zone 또는 intervals.icu Zone 데이터 집계
  ```python
  zone_pcts = [zone_i_min / total_min * 100 for zone_i in zones]
  # 80/20 규칙: (Z1+Z2) >= 80% 이상이 이상적
  ```
- **분배 모델**: 폴라리제드(80/5/15%), 피라미드(70/20/10%), 건강유지(60/30/10%)

### TRIMP — Training Impulse (TRIMPexp)
- **계산식 (Banister 1991)**:
  ```python
  hrr = (hr_avg - hr_rest) / (hr_max - hr_rest)
  TRIMP = duration_min * hrr * 0.64 * exp(1.92 * hrr)  # 남성
  ```
- **입력**: intervals.icu trimp 우선, 없으면 자체 계산

---

## 버전 비교 요약

| 메트릭 | Claude 버전 | PDF 버전 (metrics.md) | 주요 차이 |
|--------|-------------|----------------------|-----------|
| UTRS | body_battery×0.30 + tsb×0.25 + sleep×0.20 + hrv×0.15 + stress×0.10 | sleep×0.25 + hrv×0.25 + tsb×0.20 + rhr×0.15 + sleep_consistency×0.15 | body_battery 제거, sleep consistency 추가 |
| CIRS | ACWR×0.4 + LSI×0.25 + consecutive×0.20 + fatigue×0.15 | ACWR×0.4 + Monotony×0.2 + Spike×0.3 + Asymmetry×0.1 | Monotony/Asymmetry 기반으로 전환 |
| DI | 페이스 저하율법 (pace_drop * 5) | pace/HR 비율법 DI(t) = pace_ratio/HR_ratio | HR 변화 고려 여부 |
| RMR | 6개 축 (경제성 포함) | 5개 축 (경제성 제외) | 경제성 축 유무 |
| FEARP | 동일 (기온/습도/고도/경사) | 동일 | 거의 동일 |
