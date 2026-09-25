# REVIEW-08 — 메트릭 감사 (의미·정합성·예측 입력 적합성)

- 작성: 2026-09-25, running-data-coach (Claude). REVIEW-07(예측 리뉴얼)의 부록이다.
- 개정: **r3 (2026-09-25)** — 실행 검증 중 새로 찾은 결함 §R3를 추가하고, 수정 유닛(`specs/PRED-8x-metric-fixes.md`, 우선순위 표 포함)과 각 결함의 해결 유닛을 연결했다. 수치는 실DB를 `mode=ro`로 복제한 `/tmp` 사본에서 명세 코드를 실행한 결과다.
- 데이터: `data/users/pansongit@gmail.com/running.db` 읽기 전용. 코드는 `src/metrics/*.py`, `src/metrics/engine.py::ALL_CALCULATORS`(32개 calculator)를 읽었다.
- 재현: `python3 /tmp/coach_analysis/20_metric_inventory.py`, `21_metric_consistency.py`, `16_weather_fields.py`, `garmin_laps.py`
- 정적 정합성(`scripts/check_data_consistency.py`, 16개 검사)은 **오류 0**이다. 이 검사는 registry·DDL·extractor의 구조만 보고 **값의 의미는 검증하지 않는다**. 아래 결함은 모두 그 검사를 통과한 상태에서 나온 것이다.
- 표기: **[사실]** DB·코드로 확인 / **[가정]** 추정

---

## 1. 요약 — 결함 Top 10

| # | 메트릭 | 결함 | 심각도 | 수정안 |
|---|---|---|---|---|
| 1 | `race_pred_*` (darp) | 거리 무관 속도식에 30일 평균 VDOT를 넣는다. 레이스 대비 +36% 느리게 나온다 | **예측** | REVIEW-07 v2로 교체 |
| 2 | `marathon_shape`, `vdot_adj`, `rri` | 일별 `runpulse_vdot`(존재하지 않음)에 의존해서 **0행**이다 | **예측**·화면 | `perf_vdot` 신설 후 의존성 교체, vdot_adj는 폐기 |
| 3 | 활동 메트릭 전반 | 중복 활동 행에도 계산된다(trimp 960행 중 615행이 비canonical). 비canonical 시리즈를 합산하는 `teroi`는 28일 TRIMP가 **2.03배로 과대**된다(4,537 대 2,233). `rec`, `sapi`, `tpdi`, `critical_power`도 같은 API(`get_activity_metric_series`)를 쓴다 | **예측**(부하 입력)·화면 | API에 `canonical_only=True` 기본값 적용. 활동 메트릭은 canonical에만 계산하거나, 집계 시 canonical로 필터 |
| 4 | `runpulse_vdot` | 6.3~397.4. moving_time 붕괴 2건(287.9, 397.4). 이지·트레일 포함 이상치 48건(<25) | **예측** | 붕괴 가드. 레이스는 elapsed 기준 |
| 5 | `gap_rp` (GAP) | 이름과 설명은 "Minetti 경사 보정"인데, Garmin 유래 스트림의 `grade_pct`가 **전부 NULL**이라 보정계수가 1이 된다. `elapsed_sec`도 샘플 인덱스라 사실상 "정지 제외 평균 페이스"다 | **예측**(GAP 입력)·라벨 불일치 | Garmin 원본의 `avgGradeAdjustedSpeed`(활동·랩)와 `directGradeAdjustedSpeed`(스트림)를 쓴다(2025-05 이후 90%). 스트림 extractor가 `sumElapsedDuration`·`sumDistance`를 보존하도록 수정 |
| 6 | `rec` | 958일 **모두 100**. EF를 ×1000 스케일(중앙값 19.3)로 저장하는데 식은 원단위(≈0.8~2.0)를 가정한다 → 항상 포화된다 | 화면 | 식을 EF 저장 스케일에 맞춘다(÷1000) 또는 백분위 정규화 |
| 7 | `di` | 665일 중 580일(87%)이 100. 스트림 샘플 수로 절반을 나누고, 후반이 빠르면 100에서 잘린다. 네거티브 스플릿 롱런이 많은 이 러너에게는 무의미하다 | **예측**(DARP 입력)·화면 | 랩 기반 "후반 25% GAP 페이스/HR 대비 전반" 비율로 교체. 상한 없이 저장하고 해석 밴드만 둔다 |
| 8 | `workout_type_classified` | 품질 세션 재현율 27%. 결과적으로 `tids`는 1,000일 중 945일이 "mixed"로 포화된다 | **예측**(세션 신호)·화면 | 랩 구조 v2(재현율 79%, REVIEW-07 §2-3) |
| 9 | `eftp` | 최대 1,079초/km(2024-01, 표본 1). 1차 경로가 죽어서(#2와 같은 원인) 추정 경로만 돈다 | **예측**·화면 | 입력을 `perf_vdot`의 T 페이스로 교체. 표본 3개 미만이면 미산출 |
| 10 | `fearp` | 환경 보정에 기기 온도(손목)를 쓴다. 습도 메트릭 `weather_humidity_pct`는 **0행**이다. `sapi`·`tpdi`(fearp 입력)는 0행이다(원인 미조사) | 화면 | 날씨 인제스트(REVIEW-07 U-W) 후 재정의 |

**r3 해결 유닛**: #1 → P7-PRED-51, #2 → P7-PRED-52(사본 재계산에서 marathon_shape·rri·vdot_adj 0 → 약 400일), #3 → P7-PRED-14·81(teroi 28일 TRIMP 4,537 → 2,233), #4 → P7-PRED-84, #5 → P7-PRED-12·13(랩 GAP 2,786개, 활동 `gap` 261개, 스트림 실제 초), #6 → P7-PRED-82(rec 100 → 55.2, 개인 백분위), #7 → 판단 필요(P7-PRED-89), #8 → P7-PRED-23, #9 → P7-PRED-52, #10 → P7-PRED-32·83(sapi 0 → 392일).

---

## R3. r3에서 새로 찾은 결함 [사실 — 사본에서 실행 확인]

| # | 위치 | 결함 | 영향 | 해결 |
|---|---|---|---|---|
| R3-1 | `src/sync/reprocess.py::reprocess_all` | (a) `activity_summaries`를 지우고 다시 넣어 **활동 id가 전부 바뀐다**(1,423개 중 유지 0) → race_results·planned_workouts·session_outcomes·활동 metric·채팅 근거 참조 파손. (b) summary payload 없는 활동(Strava 102개) **영구 삭제**. (c) detail/splits/streams payload의 옛 `activity_id`를 먼저 써서 **랩 3,360개·스트림 전부 고아**. (d) `_clear_derived_data(source)`가 요약 삭제 후 id를 모아 랩·스트림을 못 지움 | **데이터 파손**(실행 시) | P7-PRED-13: 제자리 재추출 모듈 + (c)(d) 수정 + payload 없는 활동이 있으면 `force` 없이 거부 |
| R3-2 | Garmin 스트림 extractor | `directElapsedDuration`만 찾아 **샘플 번호를 초로 저장**, `sumDistance`·`directGradeAdjustedSpeed` 유실(최대 경과 2,013 → 실제 13,334초) | GAP·디커플링·스트림 세그먼트 | P7-PRED-12 → 13 재추출 |
| R3-3 | `sapi.py` | fearp json에 기온이 없고, 폴백이 존재하지 않는 `weather_cache.temperature`를 조회(테이블도 0행) → 항상 빈 결과, 0행. Calculator 내부 raw SQL(ADR-009 위반) | 화면 | P7-PRED-83 |
| R3-4 | `session_outcomes` DDL | `planned_id` 유일 제약이 없는데 매처는 `ON CONFLICT(planned_id)` → **저장이 항상 OperationalError** | 계획 이행 데이터 0 | P7-PRED-11(유일 인덱스) |
| R3-5 | registry `gap` | garmin 별칭 `avgGradeAdjustedSpeed`(m/s)인데 단위 sec/km, extractor가 추출하지 않아 0행 | GAP 표시·입력 | P7-PRED-12(1000/속도 변환, 261개) |
| R3-6 | `garmin_daily_extensions.py` LT | `lactateThresholdHeartRate.heartRate`를 찾지만 실제 키는 `speed_and_heart_rate.heartRate`, FTP는 `power.functionalThresholdPower` → `garmin_lthr`·`garmin_ftp` 0건. 레이스 예측은 스냅샷 2개 | 기기 참조 (b)·(a) | P7-PRED-25 |
| R3-7 | `metrics.cli recompute-all` | runpulse 메트릭을 **전부 지우고 90일만** 재계산 | 과거 메트릭 소실 | 판단 필요(P7-PRED-87). 런북은 `recompute --days` 사용 |
| R3-8 | `src/weather/provider.py` | 없는 `weather_data` 테이블 사용, `_v02_backup/fearp.py`만 참조 | 죽은 코드 | 판단 필요(P7-PRED-86) |
| R3-9 | `tids.py` | 세션 **수** 기준 비율이라 분류기 v2 뒤에도 2025-09 이후 mixed 306일·pyramidal 79·polarized 5(현재 분포 저 60.6 / 중 15.2 / 고 24.2%) | 화면 | 판단 필요(P7-PRED-88: 세그먼트 시간 기준) |
| R3-10 | `metric_store` 테스트 시드 | marathon_shape·rri·eftp·vdot_adj 테스트가 존재하지 않는 일별 `runpulse_vdot`을 시드해 통과 → 실DB 0행을 테스트가 못 잡음 | 검증 공백 | P7-PRED-52에서 `race_pred_vdot`으로 교체 |
| R3-11 | 활동 시작 시각 | Garmin은 현지 시각, Strava 행은 `Z` 접미사(현지로 보임) 혼재 | 기상 보간 시각 | 현지로 취급 [가정] |

## R3-표. 수정 번들 우선순위 (Q12) — 상세는 `specs/PRED-8x-metric-fixes.md`

| 우선 | 유닛 | 결함 | 상태 |
|---|---|---|---|
| P0 | P7-PRED-13 | R3-1 | 명세 완료 |
| P0 | P7-PRED-11 | R3-4 | 명세 완료 |
| P1 | P7-PRED-12 | #5, R3-2, R3-5 | 명세 완료 |
| P1 | P7-PRED-25 | R3-6 | 명세 완료 |
| P1 | P7-PRED-52 | #2, R3-10 | 명세 완료 |
| P1 | P7-PRED-81 | #3 | 명세 완료 |
| P1 | P7-PRED-84 | #4 | 명세 완료 |
| P2 | P7-PRED-82 | #6 | 명세 완료 |
| P2 | P7-PRED-83 | #10, R3-3 | 명세 완료 |
| P2 | P7-PRED-23 | #8 | 명세 완료 |
| P3 판단 필요 | P7-PRED-86~90 | R3-7·8·9, #7, acwr·lsi·adti·rtti·hrss, vdot_adj·fearp | 사용자 결정 |

---

## 2. 메트릭 인벤토리와 실측 (runpulse provider, 2026-09-25)

### 2-1. 1차 메트릭 (활동 scope)

| 메트릭 | requires | 입력 | 행(비canonical) | 분포(min / p50 / max) | 판정 |
|---|---|---|---|---|---|
| trimp | – | avg_hr, 시간, HRmax/RHR | 960 (615) | 7.1 / 78.6 / 460.6 | 정상. 중복 행이 문제 |
| hrss | trimp | trimp × 상수 | 960 | 4.8 / 52.2 / 297.3 | trimp와 **r=1.00, 비율 1.54 고정** → 정보가 중복된다 |
| relative_effort | – | HR 존 시간 | 960 | 0.1 / 105 / 1,221 | trimp와 r=0.87. 스케일이 달라 화면에서 혼동된다 |
| wlei | trimp | trimp × 환경 | 960 | 7.1 / 83 / 483 | 기기 온도 의존 |
| efficiency_factor_rp | – | 속도/HR ×1000 | 960 | 7.0 / 19.3 / 39.2 | 정상(스케일 주의, #6) |
| aerobic_decoupling_rp | – | 스트림 절반 EF | 446 | −38 / 6.6 / 29 | 스트림 시간축 문제. 극단값 −38%. 랩 기반 권장 |
| gap_rp | – | 스트림 grade | 610 (150) | 234 / 364 / 1,365 | **라벨 불일치(#5)** |
| fearp | – | 페이스, 기기 온도 | 1,093 | 197 / 353 / 1,329 | 기기 온도, 습도 없음(#10) |
| runpulse_vdot | – | 거리, moving | 1,069 (611) | 6.3 / 31.5 / 397 | #4 |
| workout_type_classified | – | 평균 HR, 존 | 1,093 | easy 621 · recovery 197 · tempo 88 · long 74 · … | #8 |

### 2-2. 2차 메트릭 (일별 집계·복합)

| 메트릭 | requires | 행 / 기간 | 분포 | 판정 |
|---|---|---|---|---|
| ctl / atl / tsb / ramp_rate | trimp (canonical 합) | 950 / 2023-10~ | ctl 0.2~80 (현재 72.8) | canonical이라 정상. intervals ctl과 r=0.82, 비율 1.42(스케일 차이. 화면에서 두 값을 병기할 때 설명 필요) |
| acwr | ctl, atl | 950 | 0~5.0 (0인 날 145, 5.0 상한 4) | 초기와 공백기에 0 또는 상한 → "데이터 부족"으로 표시해야 한다 |
| lsi | trimp | 329 | 0.34~101 | 휴식 후 첫 러닝에서 폭발(2024-06-28 101) → 분모 하한 필요 |
| monotony / training_strain | trimp | 665 | 0.41~4.26 | 정상 범위 |
| utrs (+5개 하위) | tsb, wellness | 950 | 0~94.5 | 하위 항목은 wellness가 있는 2025-05 이후만 있다 → 이전에는 TSB 단독 |
| cirs (+4개 하위) | acwr, lsi, ctl, tsb | 950 | 0.1~97 | acwr·lsi 결함을 물려받는다 |
| crs | acwr, tsb, cirs, utrs | 1,091 | 텍스트 4종 | 정상 동작. 입력 결함을 물려받는다 |
| rmr | tsb | 950 | 0~95.5 | 정상 |
| adti | ctl | 941 | −100~100 (26%가 포화) | 포화 과다 → 스케일 재검토 |
| rtti | ctl, atl | 950 | 0~200 (상한·하한 15%) | 포화 |
| teroi | ctl, trimp(비canonical) | 950 | −10.7~11.5 | **#3 이중 합산** |
| rec | ef, decoupling | 958 | **모두 100** | #6 |
| di | streams | 665 | 100이 87% | #7 |
| tids | classifier | 1,000 | mixed 94.5% | #8 |
| eftp | vdot(죽음), 활동 | 1,035 | 269~1,079초/km | #9 |
| critical_power | power_curve | 171 / 2025-07~ | 192~248 W | 러닝 파워 전용. 예측에는 쓰지 않음 |
| race_pred_* | vdot | 978 | 마라톤 2:07:23~6:34:11 | #1 (범위 자체가 비상식적) |
| marathon_shape, vdot_adj, rri | 일별 vdot | **0** | – | #2 |
| sapi, tpdi | fearp | **0** | – | 원인 미조사 |

### 2-3. 부하 메트릭 간 정합 (canonical 러닝 2025-04~, n≈300)

| 쌍 | r | 중앙 비율 |
|---|---|---|
| trimp : hrss | 1.00 | 1.54 (완전 중복) |
| trimp : intervals training_load | 0.96 | 1.66 |
| trimp : garmin training_load | 0.75 | 0.67 |
| trimp : relative_effort | 0.87 | 0.49 |
| garmin TL : intervals TL | 0.77 | 2.54 |

해석 [판단]: 부하의 "순서"는 소스끼리 대체로 일치하지만(r 0.75~0.96), 스케일이 제각각이라 한 화면에 여러 개를 두면 모순처럼 보인다. PMC 기준은 trimp 하나로 두고, 나머지는 소스 비교 화면에만 둔다. hrss는 trimp의 상수배라 폐기하거나 별칭으로 둔다.

### 2-4. 중복 활동의 집계 반영 [사실]

- 일별 PMC 계열(ctl/atl/tsb/acwr/monotony/lsi)은 `v_canonical_activities`로 합산하므로 **이중 반영이 없다**.
- `get_activity_metric_series`는 `activity_summaries`에 조인하고 is_primary도 거르지 않는다. 이를 쓰는 `teroi`(확인: 2.03배), `rec`, `sapi`, `tpdi`, `critical_power`는 중복 활동이 섞인다.
- 활동 scope 메트릭을 중복 행에도 계산하는 것 자체는 화면(소스별 활동 상세)에서 쓰일 수 있다. 다만 집계에서는 반드시 canonical로 걸러야 한다.

---

## 3. 원본 payload에서 확인한 미활용 데이터 (예측 입력 후보) [사실]

| 필드 | 소스 / 위치 | 커버리지(canonical 러닝) | 현재 사용 |
|---|---|---|---|
| `avgGradeAdjustedSpeed` (활동·랩), `directGradeAdjustedSpeed` (스트림) | Garmin activity_detail / splits / streams | 2025-H2 90%, 2026 91% | 미사용 (gap_rp가 자체 계산 실패) |
| `elevationLoss` (랩) | Garmin splits | 동일 | 미사용 |
| `averageTemperature` (랩·활동, 기기) | Garmin | 2025-H2 90%, 2026 90% | 요약 avg만 사용 |
| `intensityType` (WARMUP/INTERVAL/RECOVERY/COOLDOWN/ACTIVE/REST) | Garmin splits | 2025-H2 이후 100% | 미사용(분류기 v2 입력 후보) |
| `directWorkoutComplianceScore` (활동·랩) | Garmin | 2025-H2 79%, 2026 60% | 미사용. 이지 세션에도 0~100이 넓게 퍼져 있어 의미 검증이 필요하다 [가정] |
| `directWorkoutRpe`, `directWorkoutFeel` | Garmin detail | 199건 | 미사용 |
| `sumElapsedDuration`, `sumDistance` (스트림) | Garmin streams | payload 전체 | **extractor에서 유실** → activity_streams 시간축 오류의 원인 |
| `lactateThresholdHeartRate` 177, `lactateThresholdSpeed` 0.3806(×10 m/s → 4:23/km) | Garmin user_profile / lactate_threshold_day (2026-05-01) | 1회 스냅샷 | 미사용 |
| 날씨(외기) | Garmin 활동 weather 엔드포인트 / intervals `has_weather` | **0** (intervals has_weather=False 100%, Garmin weather 미수집) | 없음 (REVIEW-07 §2-9) |

---

## 4. 예측 입력으로서의 판정

| 메트릭 / 데이터 | 판정 | 조건(선행 수정) |
|---|---|---|
| runpulse_vdot (레이스·구간) | **사용** | #4 가드 |
| 랩 기반 작업구간 VDOT(GAP) — 신규 `run_effort` | **사용** | Garmin GAP 인제스트 |
| HR@LTHR 기온 보정 속도 — 신규 `hr_pace_model` | **사용**(가중 20%) | LTHR·기온 인제스트 |
| workout_type v2 | 사용(세션 선택·설명) | #8 |
| 주간 거리·롱런(canonical) | **사용**(마라톤 Tanda·셰이프) | – |
| ctl / atl / tsb | 보류 — 예측 중앙값에는 넣지 않고 레이스 당일 폼 시나리오(기존 race_projection)에만 쓴다 | 롤링 백테스트에서 볼륨 항(TV)이 개선을 보이지 않음 |
| acwr, cirs, utrs, crs, rmr | 보류(신뢰도의 부상·회복 경고로만) | acwr·lsi 결함 수정 |
| efficiency_factor, decoupling | 설명 전용 | 랩 기반 재계산 |
| di | 폐기 후 재정의(랩 후반 유지율) | #7 |
| rec, teroi, adti, rtti, tids, sapi, tpdi, fearp, wlei, hrss | 예측에 쓰지 않음 | 후속 백로그(§5) |
| marathon_shape | 사용(v2, 설명·범위) | #2 |
| vdot_adj | 폐기 | – |
| critical_power | 쓰지 않음 | – |
| Garmin race_pred | 교차 검증 표시만 — r3: 예측 3종 중 (a)로 병기, 중앙값에는 안 넣음(보정 후 20% 혼합이 대회에서 악화) | P7-PRED-25 스냅샷·이력 |

---

## 5. 후속 백로그 후보 (예측과 직접 관계없음)

> r3: 1·2는 P7-PRED-81·82로 명세화했다. 6(sapi 0행)은 원인이 R3-3으로 확인되어 P7-PRED-83. 3·4·5·7은 판단 필요(P7-PRED-89)로 남는다.

| 우선 | 항목 | 심각도 |
|---|---|---|
| 1 | `get_activity_metric_series` canonical 기본값 → teroi·rec·sapi·tpdi 재계산 | 화면 |
| 2 | rec 스케일 수정 | 화면 |
| 3 | acwr·lsi 분모 하한과 "데이터 부족" 상태 | 화면 |
| 4 | adti·rtti 포화 스케일 재검토 | 화면 |
| 5 | hrss 폐기 또는 별칭 처리. 부하 메트릭 화면 병기 원칙(한 화면에 한 기준) | 화면 |
| 6 | sapi·tpdi 0행 원인 조사 | 화면 |
| 7 | 화면 라벨 정정: gap_rp "경사 보정" → 보정 전 표기(GAP 인제스트 전까지) | 라벨 |
