# RunPulse Metric Dictionary

> 자동 생성: 2026-04-05 | 32 calculators | 13 semantic groups
>
> 이 문서는 RunPulse가 계산하는 모든 메트릭의 정의, 해석, 범위를 정리한 공식 사전입니다.
> UI 툴팁, AI 코칭 프롬프트, 사용자 도움말의 원본(single source of truth)으로 사용됩니다.
>
> **이 파일을 직접 수정하지 마세요.** `python scripts/gen_metric_dictionary.py`로 재생성합니다.

---

## 1. 데이터 흐름 개요

```
Garmin/Strava/Intervals/Runalyze
        |
        v
  [Extractors] --- raw JSON ---> source_payloads (Layer 0)
        |
        v
  activity_summaries (Layer 1)     daily_wellness (Layer 1)
        |                                |
        v                                v
  metric_store (Layer 2) <--- CalcContext API <--- Calculators
        |
        v
  [UI / AI Coach / API]
```

모든 RunPulse 메트릭은 `metric_store` 테이블에 `provider=runpulse:formula_v1`로 저장됩니다.
소스(Garmin 등)가 제공하는 원본 메트릭도 같은 테이블에 각 소스 provider로 저장되며,
`is_primary=1` 플래그로 대표값이 선택됩니다.

---

## 2. Activity-Scope 메트릭 (10개)

운동이 기록될 때마다 계산되는 메트릭입니다.

### TRIMP (Banister)

| 항목 | 값 |
|------|-----|
| 메트릭 이름 | `trimp` |
| 설명 | 심박 기반 훈련 부하 점수. 운동 시간과 심박 강도를 종합한 부하 지표. |
| 단위 | AU |
| 카테고리 | `rp_load` |
| 의존성 | 소스 데이터 직접 사용 |

**범위 해석:**

| 등급 | 범위 | 의미 |
|------|------|------|
| recovery | 0 ~ 50 | 회복 수준 |
| easy | 50 ~ 100 | 쉬운 강도 |
| moderate | 100 ~ 200 | 보통 |
| hard | 200 ~ 350 | 높은 강도 |
| very_hard | 350 ~ 999 | 매우 높은 강도 |

---

### HRSS

| 항목 | 값 |
|------|-----|
| 메트릭 이름 | `hrss` |
| 설명 | TRIMP을 젖산역치 심박으로 정규화한 스트레스 점수. 1시간 LTHR 운동 = 100. |
| 단위 | 점 |
| 카테고리 | `rp_load` |
| 의존성 | `trimp` |

---

### 유산소 분리

| 항목 | 값 |
|------|-----|
| 메트릭 이름 | `aerobic_decoupling_rp` |
| 설명 | 후반부 효율 저하율. <5% = 좋은 유산소 체력. |
| 단위 | % |
| 카테고리 | `rp_efficiency` |
| 의존성 | 소스 데이터 직접 사용 |
| 해석 | 낮을수록 좋음 |

**범위 해석:**

| 등급 | 범위 | 의미 |
|------|------|------|
| excellent | -5 ~ 5 | 우수 |
| good | 5 ~ 10 | 양호 |
| fair | 10 ~ 15 | 보통 |
| poor | 15 ~ 100 | 미흡 |

---

### GAP (경사 보정 페이스)

| 항목 | 값 |
|------|-----|
| 메트릭 이름 | `gap_rp` |
| 설명 | Minetti 모델로 경사를 보정한 평지 환산 페이스. |
| 단위 | sec/km |
| 카테고리 | `rp_performance` |
| 의존성 | 소스 데이터 직접 사용 |
| 해석 | 낮을수록 좋음 |

---

### 운동 유형

| 항목 | 값 |
|------|-----|
| 메트릭 이름 | `workout_type` |
| 설명 | 거리, 심박, 존 분포 기반 규칙 분류. |
| 단위 | 무차원 |
| 카테고리 | `rp_classification` |
| 의존성 | 소스 데이터 직접 사용 |

---

### VDOT (Daniels)

| 항목 | 값 |
|------|-----|
| 메트릭 이름 | `runpulse_vdot` |
| 설명 | Jack Daniels VDOT. 거리와 시간으로 추정한 VO₂Max 지표. |
| 단위 | 무차원 |
| 카테고리 | `rp_performance` |
| 의존성 | 소스 데이터 직접 사용 |
| 해석 | 높을수록 좋음 |

**범위 해석:**

| 등급 | 범위 | 의미 |
|------|------|------|
| beginner | 20 ~ 35 | 초보 |
| intermediate | 35 ~ 50 | 중급 |
| advanced | 50 ~ 60 | 상급 |
| elite | 60 ~ 85 | 엘리트 |

---

### 효율 계수 (EF)

| 항목 | 값 |
|------|-----|
| 메트릭 이름 | `efficiency_factor_rp` |
| 설명 | 평균속도/평균심박 × 1000. 높을수록 효율적. |
| 단위 | 무차원 |
| 카테고리 | `rp_efficiency` |
| 의존성 | 소스 데이터 직접 사용 |
| 해석 | 높을수록 좋음 |

---

### FEARP (환경 보정 페이스)

| 항목 | 값 |
|------|-----|
| 메트릭 이름 | `fearp` |
| 설명 | 기온, 습도, 고도를 보정한 환경 보정 페이스. |
| 단위 | sec/km |
| 카테고리 | `rp_performance` |
| 의존성 | 소스 데이터 직접 사용 |
| 해석 | 낮을수록 좋음 |

---

### Relative Effort

| 항목 | 값 |
|------|-----|
| 메트릭 이름 | `relative_effort` |
| 설명 | 심박존 기반 노력도 점수 (Strava 방식) |
| 단위 | AU |
| 카테고리 | `rp_load` |
| 의존성 | 소스 데이터 직접 사용 |

**범위 해석:**

| 등급 | 범위 | 의미 |
|------|------|------|
| low | 0 ~ 50 | 낮음 |
| moderate | 50 ~ 100 | 보통 |
| high | 100 ~ 200 | 높음 |
| very_high | 200 ~ 999 | 매우 높음 |

---

### WLEI (날씨 가중 노력)

| 항목 | 값 |
|------|-----|
| 메트릭 이름 | `wlei` |
| 설명 | TRIMP에 기온/습도 스트레스 계수를 적용한 실제 신체 부담 지수 |
| 단위 | AU |
| 카테고리 | `rp_load` |
| 의존성 | `trimp` |

**범위 해석:**

| 등급 | 범위 | 의미 |
|------|------|------|
| low | 0 ~ 50 | 낮음 |
| moderate | 50 ~ 100 | 보통 |
| high | 100 ~ 200 | 높음 |
| very_high | 200 ~ 999 | 매우 높음 |

---

## 3. Daily-Scope 메트릭 (22개)

매일 최근 활동과 웰니스 데이터를 종합하여 계산됩니다.

### PMC (ATL/CTL/TSB)

| 항목 | 값 |
|------|-----|
| 메트릭 이름 | `ctl`, `atl`, `tsb`, `ramp_rate` |
| 설명 | Performance Management Chart. 42일 만성부하(CTL), 7일 급성부하(ATL), 훈련균형(TSB). |
| 단위 | AU |
| 카테고리 | `rp_load` |
| 의존성 | `trimp` |

---

### ACWR

| 항목 | 값 |
|------|-----|
| 메트릭 이름 | `acwr` |
| 설명 | 급성:만성 부하 비율. 최적 범위 0.8~1.3. |
| 단위 | 무차원 |
| 카테고리 | `rp_load` |
| 의존성 | `ctl`, `atl` |

**범위 해석:**

| 등급 | 범위 | 의미 |
|------|------|------|
| low | 0 ~ 0.8 | 낮음 |
| optimal | 0.8 ~ 1.3 | 최적 |
| caution | 1.3 ~ 1.5 | 주의 |
| danger | 1.5 ~ 5 | 위험 |

---

### 부하 급증 지수 (LSI)

| 항목 | 값 |
|------|-----|
| 메트릭 이름 | `lsi` |
| 설명 | 당일 부하 / 21일 평균. >1.5면 급격한 부하 증가. |
| 단위 | 무차원 |
| 카테고리 | `rp_load` |
| 의존성 | `trimp` |

**범위 해석:**

| 등급 | 범위 | 의미 |
|------|------|------|
| normal | 0 ~ 1.3 | 정상 |
| elevated | 1.3 ~ 1.5 | 상승 |
| spike | 1.5 ~ 10 | 급증 |

---

### 단조로움 (Monotony)

| 항목 | 값 |
|------|-----|
| 메트릭 이름 | `monotony`, `training_strain` |
| 설명 | 7일 훈련 부하의 변동성 지표. >2.0은 과훈련 위험. |
| 단위 | 무차원 |
| 카테고리 | `rp_load` |
| 의존성 | `trimp` |
| 해석 | 낮을수록 좋음 |

**범위 해석:**

| 등급 | 범위 | 의미 |
|------|------|------|
| varied | 0 ~ 1.5 | 다양함 |
| moderate | 1.5 ~ 2.0 | 보통 |
| monotonous | 2.0 ~ 10 | 단조로움 |

---

### 훈련 준비도 (UTRS)

| 항목 | 값 |
|------|-----|
| 메트릭 이름 | `utrs` |
| 설명 | 수면, HRV, 체력 상태, 스트레스를 종합한 훈련 준비도. |
| 단위 | 점 |
| 카테고리 | `rp_readiness` |
| 의존성 | `tsb` |
| 해석 | 높을수록 좋음 |

**범위 해석:**

| 등급 | 범위 | 의미 |
|------|------|------|
| poor | 0 ~ 30 | 미흡 |
| low | 30 ~ 50 | 낮음 |
| moderate | 50 ~ 70 | 보통 |
| good | 70 ~ 85 | 양호 |
| excellent | 85 ~ 100 | 우수 |

---

### 부상 위험 지수 (CIRS)

| 항목 | 값 |
|------|-----|
| 메트릭 이름 | `cirs` |
| 설명 | ACWR, LSI, 연속훈련일, 피로도를 종합한 부상 위험도. |
| 단위 | 점 |
| 카테고리 | `rp_risk` |
| 의존성 | `acwr`, `lsi`, `ctl`, `tsb` |
| 해석 | 낮을수록 좋음 |

**범위 해석:**

| 등급 | 범위 | 의미 |
|------|------|------|
| low | 0 ~ 30 | 낮음 |
| moderate | 30 ~ 50 | 보통 |
| high | 50 ~ 70 | 높음 |
| critical | 70 ~ 100 | 위험 |

---

### 내구성 지수 (DI)

| 항목 | 값 |
|------|-----|
| 메트릭 이름 | `di` |
| 설명 | 장거리 달리기에서 후반 페이스 유지 능력. 0~100. |
| 단위 | 점 |
| 카테고리 | `rp_endurance` |
| 의존성 | 소스 데이터 직접 사용 |
| 해석 | 높을수록 좋음 |

---

### 레이스 예측 (DARP)

| 항목 | 값 |
|------|-----|
| 메트릭 이름 | `darp_5k`, `darp_10k`, `darp_half`, `darp_marathon` |
| 설명 | VDOT과 내구성 지수 기반 레이스 시간 예측. |
| 단위 | sec |
| 카테고리 | `rp_prediction` |
| 의존성 | `runpulse_vdot` |
| 해석 | 낮을수록 좋음 |

---

### 강도 분포 (TIDS)

| 항목 | 값 |
|------|-----|
| 메트릭 이름 | `tids` |
| 설명 | 8주간 훈련 강도 분포. polarized/threshold/pyramidal/mixed. |
| 단위 | 무차원 |
| 카테고리 | `rp_distribution` |
| 의존성 | `workout_type` |

---

### 회복 준비도 (RMR)

| 항목 | 값 |
|------|-----|
| 메트릭 이름 | `rmr` |
| 설명 | 안정심박, 체력배터리, TSB, 수면을 종합한 회복 상태. |
| 단위 | 점 |
| 카테고리 | `rp_recovery` |
| 의존성 | `tsb` |
| 해석 | 높을수록 좋음 |

**범위 해석:**

| 등급 | 범위 | 의미 |
|------|------|------|
| poor | 0 ~ 30 | 미흡 |
| low | 30 ~ 50 | 낮음 |
| moderate | 50 ~ 70 | 보통 |
| good | 70 ~ 85 | 양호 |
| excellent | 85 ~ 100 | 우수 |

---

### 훈련 추세 (ADTI)

| 항목 | 값 |
|------|-----|
| 메트릭 이름 | `adti` |
| 설명 | 28일간 CTL 변화율. 양수=상승, 음수=하락. |
| 단위 | 무차원 |
| 카테고리 | `rp_trend` |
| 의존성 | `ctl` |
| 해석 | 높을수록 좋음 |

**범위 해석:**

| 등급 | 범위 | 의미 |
|------|------|------|
| declining | -100 ~ -10 | 하락 |
| stable | -10 ~ 10 | 안정 |
| building | 10 ~ 100 | 상승 중 |

---

### TEROI (훈련 효과 ROI)

| 항목 | 값 |
|------|-----|
| 메트릭 이름 | `teroi` |
| 설명 | TRIMP 투입 대비 CTL 증가율. 높을수록 효율적 훈련. |
| 단위 | 무차원 |
| 카테고리 | `rp_trend` |
| 의존성 | `ctl`, `trimp` |
| 해석 | 높을수록 좋음 |

**범위 해석:**

| 등급 | 범위 | 의미 |
|------|------|------|
| negative | -100 ~ 0 | 음수 |
| low | 0 ~ 5 | 낮음 |
| good | 5 ~ 15 | 양호 |
| excellent | 15 ~ 100 | 우수 |

---

### TPDI (실내/실외 격차)

| 항목 | 값 |
|------|-----|
| 메트릭 이름 | `tpdi` |
| 설명 | 실내 vs 실외 달리기 FEARP 격차. 0에 가까울수록 일관됨. |
| 단위 | % |
| 카테고리 | `rp_trend` |
| 의존성 | `fearp` |
| 해석 | 낮을수록 좋음 |

**범위 해석:**

| 등급 | 범위 | 의미 |
|------|------|------|
| consistent | 0 ~ 5 | 일관됨 |
| moderate | 5 ~ 10 | 보통 |
| large | 10 ~ 100 | 큰 격차 |

---

### REC (러닝 효율성)

| 항목 | 값 |
|------|-----|
| 메트릭 이름 | `rec` |
| 설명 | EF와 Decoupling 기반 통합 러닝 효율성 (0~100) |
| 단위 | 무차원 |
| 카테고리 | `rp_efficiency` |
| 의존성 | `efficiency_factor_rp`, `aerobic_decoupling_rp` |
| 해석 | 높을수록 좋음 |

**범위 해석:**

| 등급 | 범위 | 의미 |
|------|------|------|
| poor | 0 ~ 30 | 미흡 |
| fair | 30 ~ 50 | 보통 |
| good | 50 ~ 70 | 양호 |
| excellent | 70 ~ 100 | 우수 |

---

### RTTI (훈련 내성 지수)

| 항목 | 값 |
|------|-----|
| 메트릭 이름 | `rtti` |
| 설명 | ATL/CTL 기반 훈련 내성. 100=적정, >100 과부하, <70 여유. |
| 단위 | % |
| 카테고리 | `rp_load` |
| 의존성 | `ctl`, `atl` |

**범위 해석:**

| 등급 | 범위 | 의미 |
|------|------|------|
| under | 0 ~ 70 | 여유 |
| optimal | 70 ~ 100 | 최적 |
| overload | 100 ~ 130 | 과부하 |
| danger | 130 ~ 300 | 위험 |

---

### Critical Power (CP)

| 항목 | 값 |
|------|-----|
| 메트릭 이름 | `critical_power` |
| 설명 | 임계 파워 (W). 2파라미터 선형 회귀 모델. |
| 단위 | W |
| 카테고리 | `rp_performance` |
| 의존성 | `power_curve` |
| 해석 | 높을수록 좋음 |

**범위 해석:**

| 등급 | 범위 | 의미 |
|------|------|------|
| low | 0 ~ 200 | 낮음 |
| moderate | 200 ~ 280 | 보통 |
| high | 280 ~ 500 | 높음 |

---

### SAPI (계절 성과 지수)

| 항목 | 값 |
|------|-----|
| 메트릭 이름 | `sapi` |
| 설명 | 기온 구간별 FEARP 비교. 100=기준 동일, >100 더 빠름. |
| 단위 | 무차원 |
| 카테고리 | `rp_performance` |
| 의존성 | `fearp` |
| 해석 | 높을수록 좋음 |

**범위 해석:**

| 등급 | 범위 | 의미 |
|------|------|------|
| poor | 0 ~ 85 | 미흡 |
| normal | 85 ~ 100 | 정상 |
| good | 100 ~ 150 | 양호 |

---

### RRI (레이스 준비도)

| 항목 | 값 |
|------|-----|
| 메트릭 이름 | `rri` |
| 설명 | VDOT/CTL/DI/CIRS 기반 레이스 준비도 종합 지수 (0~100) |
| 단위 | 무차원 |
| 카테고리 | `rp_performance` |
| 의존성 | `runpulse_vdot`, `ctl`, `di`, `cirs` |
| 해석 | 높을수록 좋음 |

**범위 해석:**

| 등급 | 범위 | 의미 |
|------|------|------|
| insufficient | 0 ~ 40 | 부족 |
| building | 40 ~ 60 | 상승 중 |
| ready | 60 ~ 80 | 준비됨 |
| peak | 80 ~ 100 | 피크 |

---

### eFTP (역치 페이스)

| 항목 | 값 |
|------|-----|
| 메트릭 이름 | `eftp` |
| 설명 | 기능적 역치 페이스 추정 (sec/km). 낮을수록 빠름. |
| 단위 | sec/km |
| 카테고리 | `rp_performance` |
| 의존성 | `runpulse_vdot` |
| 해석 | 낮을수록 좋음 |

**범위 해석:**

| 등급 | 범위 | 의미 |
|------|------|------|
| elite | 150 ~ 210 | 엘리트 |
| advanced | 210 ~ 260 | 상급 |
| intermediate | 260 ~ 320 | 중급 |
| beginner | 320 ~ 600 | 초보 |

---

### VDOT 보정

| 항목 | 값 |
|------|-----|
| 메트릭 이름 | `vdot_adj` |
| 설명 | 역치 페이스 기반 현재 체력 VDOT 보정값 |
| 단위 | 무차원 |
| 카테고리 | `rp_performance` |
| 의존성 | `runpulse_vdot` |
| 해석 | 높을수록 좋음 |

**범위 해석:**

| 등급 | 범위 | 의미 |
|------|------|------|
| beginner | 20 ~ 35 | 초보 |
| intermediate | 35 ~ 45 | 중급 |
| advanced | 45 ~ 55 | 상급 |
| elite | 55 ~ 85 | 엘리트 |

---

### Marathon Shape

| 항목 | 값 |
|------|-----|
| 메트릭 이름 | `marathon_shape` |
| 설명 | 마라톤 훈련 완성도 (%). 주간볼륨+장거리런 기반. |
| 단위 | % |
| 카테고리 | `rp_performance` |
| 의존성 | `runpulse_vdot` |
| 해석 | 높을수록 좋음 |

**범위 해석:**

| 등급 | 범위 | 의미 |
|------|------|------|
| insufficient | 0 ~ 30 | 부족 |
| base | 30 ~ 50 | 기초 |
| building | 50 ~ 70 | 상승 중 |
| ready | 70 ~ 85 | 준비됨 |
| peak | 85 ~ 100 | 피크 |

---

### CRS (훈련 준비도)

| 항목 | 값 |
|------|-----|
| 메트릭 이름 | `crs` |
| 설명 | 게이트 기반 복합 준비도. level 0~4 + CRS 참고 점수 0~100. |
| 단위 | 무차원 |
| 카테고리 | `rp_readiness` |
| 의존성 | `acwr`, `tsb`, `cirs`, `utrs` |
| 해석 | 높을수록 좋음 |

**범위 해석:**

| 등급 | 범위 | 의미 |
|------|------|------|
| rest | 0 ~ 20 | 휴식 필요 |
| easy_only | 20 ~ 40 | 가벼운 운동만 |
| moderate | 40 ~ 60 | 보통 |
| full | 60 ~ 80 | 전면 훈련 가능 |
| boost | 80 ~ 100 | 고강도 가능 |

---

## 4. 시맨틱 그룹 (13개)

같은 개념을 측정하는 여러 소스/메트릭을 하나의 그룹으로 묶어 UI에서 비교 뷰를 제공합니다.

### 유산소 분리 (`decoupling`)

표시 전략: **prefer_runpulse**

| 메트릭 | 제공자 |
|--------|--------|
| `aerobic_decoupling_rp` | runpulse:formula_v1 |
| `decoupling` | intervals |

### TRIMP (`trimp`)

표시 전략: **prefer_runpulse**

| 메트릭 | 제공자 |
|--------|--------|
| `trimp` | runpulse:formula_v1 |
| `trimp` | intervals |

### 훈련 부하 (`training_load`)

표시 전략: **show_all**

| 메트릭 | 제공자 |
|--------|--------|
| `training_load_score` | intervals |
| `training_load` | garmin |
| `suffer_score` | strava |
| `hrss` | runpulse:formula_v1 |
| `wlei` | runpulse:formula_v1 |
| `rtti` | runpulse:formula_v1 |

### VO2Max (`vo2max`)

표시 전략: **prefer_runpulse**

| 메트릭 | 제공자 |
|--------|--------|
| `runpulse_vdot` | runpulse:formula_v1 |
| `vo2max_activity` | garmin |
| `effective_vo2max` | runalyze |

### 레이스 예측 (`race_prediction`)

표시 전략: **show_all**

| 메트릭 | 제공자 |
|--------|--------|
| `darp_5k_sec` | runpulse:formula_v1 |
| `darp_10k_sec` | runpulse:formula_v1 |
| `darp_half_sec` | runpulse:formula_v1 |
| `darp_marathon_sec` | runpulse:formula_v1 |
| `rri` | runpulse:formula_v1 |
| `marathon_shape` | runpulse:formula_v1 |

### 훈련 준비도 (`readiness`)

표시 전략: **prefer_runpulse**

| 메트릭 | 제공자 |
|--------|--------|
| `crs` | runpulse:formula_v1 |
| `utrs` | runpulse:formula_v1 |
| `training_readiness` | garmin |

### 회복 상태 (`recovery`)

표시 전략: **show_all**

| 메트릭 | 제공자 |
|--------|--------|
| `body_battery_high` | garmin |
| `body_battery_low` | garmin |
| `rmr` | runpulse:formula_v1 |

### 상대적 노력도 (`relative_effort`)

표시 전략: **show_all**

| 메트릭 | 제공자 |
|--------|--------|
| `relative_effort` | runpulse:formula_v1 |
| `suffer_score` | strava |
| `training_load_score` | intervals |

### 임계 파워/페이스 (`threshold_power`)

표시 전략: **show_all**

| 메트릭 | 제공자 |
|--------|--------|
| `critical_power` | runpulse:formula_v1 |
| `eftp` | runpulse:formula_v1 |
| `icu_ftp` | intervals |

### 러닝 효율성 (`running_efficiency`)

표시 전략: **prefer_runpulse**

| 메트릭 | 제공자 |
|--------|--------|
| `rec` | runpulse:formula_v1 |
| `efficiency_factor_rp` | runpulse:formula_v1 |
| `efficiency_factor` | intervals |

### VDOT (`vdot`)

표시 전략: **prefer_runpulse**

| 메트릭 | 제공자 |
|--------|--------|
| `runpulse_vdot` | runpulse:formula_v1 |
| `vdot_adj` | runpulse:formula_v1 |
| `vo2max_activity` | garmin |
| `effective_vo2max` | runalyze |

### 훈련 트렌드 (`training_trend`)

표시 전략: **show_all**

| 메트릭 | 제공자 |
|--------|--------|
| `teroi` | runpulse:formula_v1 |
| `tpdi` | runpulse:formula_v1 |
| `adti` | runpulse:formula_v1 |

### 환경별 성과 (`seasonal_performance`)

표시 전략: **show_all**

| 메트릭 | 제공자 |
|--------|--------|
| `sapi` | runpulse:formula_v1 |
| `fearp` | runpulse:formula_v1 |

## 5. 계산 의존성 그래프

```
Activity-scope:
  (소스 직접) --> trimp
  trimp --> hrss
  (소스 직접) --> aerobic_decoupling_rp
  (소스 직접) --> gap_rp
  (소스 직접) --> workout_type
  (소스 직접) --> runpulse_vdot
  (소스 직접) --> efficiency_factor_rp
  (소스 직접) --> fearp
  (소스 직접) --> relative_effort
  trimp --> wlei

Daily-scope:
  trimp --> ctl, atl, tsb, ramp_rate
  ctl + atl --> acwr
  trimp --> lsi
  trimp --> monotony, training_strain
  tsb --> utrs
  acwr + lsi + ctl + tsb --> cirs
  (소스 직접) --> di
  runpulse_vdot --> darp_5k, darp_10k, darp_half, darp_marathon
  workout_type --> tids
  tsb --> rmr
  ctl --> adti
  ctl + trimp --> teroi
  fearp --> tpdi
  efficiency_factor_rp + aerobic_decoupling_rp --> rec
  ctl + atl --> rtti
  power_curve --> critical_power
  fearp --> sapi
  runpulse_vdot + ctl + di + cirs --> rri
  runpulse_vdot --> eftp
  runpulse_vdot --> vdot_adj
  runpulse_vdot --> marathon_shape
  acwr + tsb + cirs + utrs --> crs
```

## 6. 카테고리 분류

| 카테고리 | 한글명 | 포함 메트릭 |
|----------|--------|------------|
| `rp_classification` | 운동 분류 | `workout_type` |
| `rp_distribution` | 강도 분포 | `tids` |
| `rp_efficiency` | 러닝 효율성 | `aerobic_decoupling_rp`, `efficiency_factor_rp`, `rec` |
| `rp_endurance` | 내구성 | `di` |
| `rp_load` | 훈련 부하 | `trimp`, `hrss`, `ctl`, `atl`, `tsb`, `ramp_rate`, `acwr`, `lsi`, `monotony`, `training_strain`, `relative_effort`, `wlei`, `rtti` |
| `rp_performance` | 성과 지표 | `gap_rp`, `runpulse_vdot`, `fearp`, `critical_power`, `sapi`, `rri`, `eftp`, `vdot_adj`, `marathon_shape` |
| `rp_prediction` | 레이스 예측 | `darp_5k`, `darp_10k`, `darp_half`, `darp_marathon` |
| `rp_readiness` | 훈련 준비도 | `utrs`, `crs` |
| `rp_recovery` | 회복 상태 | `rmr` |
| `rp_risk` | 부상 위험 | `cirs` |
| `rp_trend` | 훈련 추세 | `adti`, `teroi`, `tpdi` |

## 7. 소스별 원본 메트릭 (참고)

RunPulse가 계산하는 메트릭 외에, 각 소스가 제공하는 원본 메트릭도 `metric_store`에 저장됩니다.

| 소스 | 주요 메트릭 예시 |
|------|-----------------|
| Garmin | `vo2max_activity`, `training_readiness`, `body_battery_high/low`, `training_load` |
| Strava | `suffer_score`, `perceived_exertion`, `achievement_count` |
| Intervals.icu | `training_load_score`, `efficiency_factor`, `icu_ftp`, `decoupling` |
| Runalyze | `effective_vo2max`, `marathon_shape` |
