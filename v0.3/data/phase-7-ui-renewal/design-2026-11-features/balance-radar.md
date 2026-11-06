# Training Balance Radar 설계서 (07 §7d)

- 작성: 2026-11-06 · 상태: **설계(승인 대기)** · 코드 변경 없음
- 원문: `07-migration-roadmap.md` §Phase 7d — "Training Balance Radar 메트릭 계산 — 다차원 레이더 데이터
  (stress/load/recovery/form/sleep/hrv)", `GET /api/v1/library/metrics/training-balance`, "Library 내 표시",
  검증 "6개 축 데이터 정상 렌더링". BACKLOG `[PHASE-7-REMAINING]` (3) 미배정 항목.

## 1. 원문 축 목록을 그대로 쓰지 않는 이유

원문 6축(stress/load/recovery/form/sleep/hrv) 중 4개(stress·recovery·sleep·hrv)는 **몸 상태**, 2개(load·form)는
**부하 상태**다. 이는 이미 UTRS(`utrs` + `utrs_sleep/hrv/stress/tsb/body_battery` 자식 메트릭)가 같은 입력으로
보여 주는 내용이라, 레이더로 다시 그리면 "준비도 게이지의 분해도"가 될 뿐 **훈련이 균형 잡혔는지**는 답하지 못한다.
"Training Balance"가 답해야 할 질문은 "무엇을 충분히, 무엇을 부족하게 하고 있나"이므로
**훈련 구성 4축 + 부하 1축 + 회복 1축**으로 재정의한다. 원문의 load·form은 축 5, sleep·hrv·stress는 축 6에 흡수한다.
(원문 축 변경은 설계 변경이므로 **사용자 확인 필요** — §9 결정 D1.)

## 2. 조사 결과 — 재사용 가능한 기존 값 (2026-11-06 실계정 확인, 읽기 전용)

| 값 | 출처 (metric_store, provider `runpulse:formula_v1`) | 실계정 최신값 |
|---|---|---|
| 8주 시간 기준 3구간 분포 | `tids` json: `low_pct/mid_pct/high_pct`, 경계 M·T 페이스(VDOT) | 83.1 / 8.9 / 8.0 %, pyramidal |
| 8주 주평균 km, 최장 롱런(12주), 롱런 수, 주당 품질 세션 | `marathon_shape` json: `weekly_km_8w`, `longest_12w_km`, `long_runs_12w`, `quality_sessions_per_week_8w` | 35.5 km, 24.2 km, ≥21km 4회, 0.62 |
| ACWR (EWMA 7/42, CTL<10·이력<28일이면 미산출) | `acwr` numeric | 1.11 |
| CTL/ATL/TSB | `ctl` 계열 numeric | 48.1 / – / +7.0 |
| Monotony·Strain | `monotony`, `training_strain` | 0.98 |
| 세션 유형 | `workout_type_classified` text (activity scope) | 8주: easy 18, tempo 3, steady 3, interval 2, long_run 2, race 4 |
| 수면·HRV·스트레스 | `daily_wellness`: `sleep_score`, `hrv_weekly_avg`, `hrv_last_night`, `avg_stress` | 최근 56일 57/57일 존재 |

CalcContext API로도 같은 값에 접근 가능(`get_latest_daily_metric`, `get_daily_metric_series`, `get_metric_json`,
`get_runs(with_laps)`, `get_wellness_series`, `get_active_goal`) — 즉 새 원천 계산은 필요 없다.

## 3. 레이더 축 정의 (6축)

공통: 축 점수 `score = clamp(actual / target, 0, 1.5) × 100`. **100 = 목표 도달.** 차트 반경 0~150, 100에 기준 링.
축마다 균형 구간 `[band_lo, band_hi]`을 두고 상태를 `low | balanced | high`로 판정한다(색이 아니라 텍스트로도 표시).
훈련 창은 **8주로 통일**(TIDS·marathon_shape와 같은 창; 롱런만 marathon_shape의 12주 최장).

| # | 축 (key) | actual | target (우선순위) | band | 데이터 부족 조건 → `null` + reason |
|---|---|---|---|---|---|
| A1 | 볼륨 `volume` | `marathon_shape.weekly_km_8w` | ① 활성 플랜의 같은 8주 계획 km 주평균(계획 주 ≥4) ② 직전 26주 중 `weekly_km_8w` 최댓값(개인 최고 지속 볼륨) | 80~120 | marathon_shape 없음 → `no_shape`; ②도 26주 이력 <8주 → `insufficient_history` |
| A2 | 롱런 `long_run` | `marathon_shape.longest_12w_km` | ① 활성 플랜의 최장 계획 롱런 ② 목표 거리표: 풀 30 / 하프 18 / 10K 14 / 5K 12 km ③ 목표 없음: max(10, 0.3 × A1 target) | 80~120 | `no_shape` |
| A3 | 이지 기반 `easy_base` | `tids.low_pct` | 80 % (Seiler 80/20 [가정]) | 90~115 | TIDS 미산출(VDOT 없음 또는 8주 러닝 <5) → `insufficient_runs` |
| A4 | 품질 강도 `quality` | `tids.mid_pct + tids.high_pct` | 20 % | 75~125 | `insufficient_runs` |
| A5 | 부하 균형 `load` | `acwr` | 1.0 | 80~130 (ACWR 0.8~1.3) | ACWR None(P7-PRED-89) → `acwr_warmup` |
| A6 | 회복 `recovery` | 아래 식 | 개인 기준선 = 1.0 | 90~110 | 7일 중 유효 <4일 또는 60일 중 <30일 → `no_wellness` |

A6 식: 가용 항목만 평균(최소 1개).
`sleep = mean7(sleep_score)/mean60(sleep_score)`, `hrv = mean7(hrv_last_night)/mean60(hrv_last_night)`,
`stress = mean60(avg_stress)/mean7(avg_stress)`(낮을수록 좋으므로 역수). → `actual = 평균`, `target = 1.0`.
절대값(UTRS의 0~100 선형 정규화)을 쓰지 않는 이유: HRV는 개인차가 커서 "20~100ms" 고정 범위는 축 비교를 왜곡한다.

**축별 정보량·편향 (표 하단 주석으로 노출)**
- A3·A4: 구간 경계가 VDOT 기반 M·T 페이스라 **VDOT가 과소하면 품질이 과대 집계**된다. TIDS는 레이스 랩도 포함 —
  8주 레이스 4회인 실계정은 A4의 상당 부분이 레이스다. API에 `race_share_of_quality`(가능 시)를 함께 내려 해석을 돕는다
  (TIDS json에 레이스 분리가 없으므로 1차 구현에선 `null`; §9 D3).
- A2: 12주 최장 1회 값이라 단발 레이스(하프 대회)가 롱런으로 잡힌다. 의도된 동작(지구력 자극은 실제로 있었음).
- A1 ②: 개인 최고 기준은 부상·공백 직후 낮게 보일 수 있다 — 의도된 신호. 단, 목표 대비가 아니므로 `basis`로 구분 표시.
- A5: ACWR은 TSB와 상관이 높아 TSB는 별도 축으로 두지 않고 표의 보조열에 표시(`tsb`, `monotony`).

**전체 카드 상태**: 유효 축 ≥4 → 레이더 표시(결측 축은 꼭짓점에 "수집 중" 라벨, 다각형은 그 축을 건너뛰지 않고
중심점 대신 **점선 구간**으로 표시). 유효 축 ≤3 → 차트 대신 `EmptyState` "데이터 수집 중" + 축별 사유 목록.

## 4. 정규화 기준 — 추천안: **목표 대비** (확정 추천)

| 기준 | 문제 |
|---|---|
| 최근 N주 평균 대비 | 자기 자신을 기준으로 삼아 모든 축이 구조적으로 ~100 근처에 모인다 → 모양이 항상 둥글어 "균형"을 말하지 못한다. 변화량만 보여 줌. |
| **목표 대비** | 100이 "충분"이라는 고정 의미를 가져 축 간 비교가 가능하다. 레이더의 존재 이유와 일치. |

따라서 **목표 대비를 기본**으로 하고, 목표가 정의되지 않는 곳만 명시적 대체 기준을 쓴다:
A1은 플랜 없을 때 개인 최고 지속 볼륨, A6은 원래 절대 목표가 없으므로 개인 60일 기준선.
축마다 `basis ∈ {plan, goal, default_rule, personal_peak, personal_baseline}`를 내려 화면에 "기준: 플랜/목표/개인 최고…"로 표기한다.
추세는 기준을 바꾸지 않고 **28일 전 같은 계산을 겹쳐 그리는 것**(점선 다각형)으로 해결한다.

marathon_shape의 Tanda 필요 볼륨(실계정 96.6 km)은 A1 목표로 쓰지 않는다 — 현재 35.5 km 대비 2.7배라 37%로
고정 표시되어 축이 정보를 잃는다(Tanda 역산은 예측 설명용이지 단기 처방 목표가 아님). 이 값은 표 보조열에만 표시.

## 5. Calculator vs 서비스 레이어 — 판단: **서비스 레이어로 충분, 새 Calculator 불필요**

근거
1. 6축 actual 값은 전부 기존 Calculator 산출물(tids·marathon_shape·acwr)과 원천 wellness의 단순 조합이다. 새 원천 계산 없음.
2. target은 **플랜·목표(사용자 설정)**에 의존한다. Calculator 결과로 저장하면 플랜 변경 때마다 재계산·버전 관리가
   필요하고 metric_store가 사용자 설정의 사본이 된다. 표시 시점 계산이 맞다.
3. 과거 시점 비교(28일 전)는 metric_store의 날짜별 값(`scope_id`=날짜)으로 as-of 조회가 가능하다.
4. ADR-009(Calculator 내 raw SQL 금지)·ADR-042(version→algo_changelog) 부담이 생기지 않는다. 기존 Calculator 변경 없음.

재검토 조건: (a) Coach/MCP가 "균형 점수"를 시계열로 질의해야 하거나 (b) A4의 레이스 분리가 필요해 TIDS json을
확장하는 경우 — (b)는 `tids` version 2.0→2.1 + `algo_changelog.py` 항목 + `gen_metric_dictionary.py` 재생성이 따른다(별도 승인).

서비스는 SQL을 직접 쓰지 않고 기존 서비스 함수를 조합한다: 메트릭 조회는 `metrics_service`/`metrics_trend_service` 계열,
wellness는 `wellness_service`, 계획 km는 `plan_load`(planned_workouts 주 집계), 목표는 `goal_service`/`get_active_goal` 동등 함수.
필요한 조회 함수가 없으면 해당 서비스에 추가한다(T1).

## 6. API 명세

- 파일: `src/api/routes_library_balance.py` (신규). `routes_library.py`는 이미 316줄이라 추가 금지(300줄 규칙).
  `routes_library_activities.py`처럼 `api_bp`에 등록.
- `GET /api/v1/library/metrics/training-balance?date=YYYY-MM-DD&compare_days=28`
  - `date` 생략 시 오늘(사용자 TZ). `compare_days` 0~84, 0이면 비교 생략. 형식 오류 → `api_error("INVALID_PARAM", …, 400)`.
  - DB 없음 → 503 `NOT_FOUND`(기존 라우트와 동일 패턴). 데이터 부족은 에러가 아니라 200 + `state`.
  - Werkzeug는 정적 경로를 `<slug>`보다 우선하므로 `/library/metrics/<slug>`와 충돌하지 않는다 — 테스트로 고정(T3).
- 응답 (`api_ok`, ETag 불필요 — 날짜별 가벼운 페이로드)

```json
{"data": {
  "as_of": "2026-11-06", "window_weeks": 8,
  "state": "ready | partial | collecting",
  "axes": [{
    "key": "volume", "label": "볼륨", "actual": 35.5, "unit": "km/주",
    "target": 40.0, "basis": "personal_peak", "score": 88.8,
    "band": [80, 120], "status": "balanced", "reason": null,
    "source": ["marathon_shape"], "computed_on": "2026-11-06"
  }],
  "compare": {"as_of": "2026-10-09", "axes": [{"key": "volume", "score": 81.0}]},
  "aux": {"tsb": 7.0, "monotony": 0.98, "tanda_required_km": 96.6, "tids_pattern": "pyramidal"},
  "notes": ["quality_includes_races"]
}}
```
- `state`: 유효 축 6=ready, 4~5=partial, ≤3=collecting. `status`: score<band_lo→low, >band_hi→high.
- `computed_on`이 `as_of`보다 2일 이상 오래되면 `stale: true`(기존 `metric_freshness` 규칙과 같은 문구 사용).

## 7. 화면 위치·컴포넌트·접근성

- 위치: **Library > 메트릭 브라우저(`/library/metrics`) 상단 요약 카드** + 상세 페이지 **`/library/balance`**.
  상세를 `/library/metrics/balance`로 두지 않는 이유: `[slug]` 라우트와 의미가 섞인다(메트릭 slug 아님).
  메트릭 브라우저 `+page.svelte`가 294줄이라 카드 본문은 컴포넌트로 분리하고 페이지엔 import 1줄+사용 1줄만 추가.
  Today·Coach에는 넣지 않는다(Today는 준비도 게이지가 같은 질문에 이미 답함, 중복 회피).
- 컴포넌트 (`frontend/src/lib/components/`)
  - `BalanceRadar.svelte` — 순수 SVG(기존 `TrendChart`처럼 차트 라이브러리 없음). 기하 계산은 `$lib/chart/radar.ts` 순수 함수.
    현재 다각형(실선) + 28일 전(점선) + 100 기준 링 + 균형 구간 음영. 결측 축은 꼭짓점 "수집 중".
  - `BalanceTable.svelte` — 축 | 현재 | 목표(기준) | 점수 | 상태 | 28일 전 열. 하단에 편향 주석(`notes`).
  - `TrainingBalanceCard.svelte` — 브라우저 상단 카드(작은 레이더 + 상태 텍스트 1줄 "품질 강도 부족, 나머지 균형" + 상세 링크).
    `collecting`이면 `EmptyState`로 "데이터 수집 중" + 사유.
- 접근성 (표 대안 필수)
  - 레이더는 `<figure>` 안 `<svg role="img" aria-labelledby>`; `<figcaption>`에 요약 문장(낮음·높음 축 나열).
  - `BalanceTable`은 **항상 DOM에 렌더링되고 화면에도 보인다**(토글로 숨기지 않음). `<caption>`, `<th scope>` 사용.
    모바일에선 표가 레이더 아래 바로 이어진다. 스크린리더는 표만으로 모든 정보를 얻는다(SVG에 표에 없는 정보 금지).
  - 상태는 색 + 텍스트(부족/균형/과다) + 꼭짓점 모양(▲ 과다, ▼ 부족)으로 중복 부호화. 대비 4.5:1, 다크모드 토큰 사용.
  - 키보드: 꼭짓점 포커스 불필요(표가 대안). `prefers-reduced-motion`이면 다각형 애니메이션 없음.

## 8. 구현 작업

| T | 내용 | 테스트 포인트 |
|---|---|---|
| T1 | 조회 보강: 서비스에 "as-of 일자 daily 메트릭 json/값", "기간 계획 km 주별 합", "60일 wellness 시계열" 함수가 없으면 해당 서비스에 추가 | 각 함수 단위 테스트(빈 DB → 빈 값, 에러 없음) |
| T2 | `src/services/training_balance_service.py`: 축 6개 계산(축별 순수 함수 + 조립), target 우선순위, score/band/status, state, compare | 축별: 정상·경계값(band 경계 포함)·clamp 150·결측 reason 코드; target 우선순위(플랜>목표>기본표>개인); A6 항목 일부 결측 평균; 유효 축 3/4/6 → collecting/partial/ready; compare as-of가 미래 데이터를 읽지 않음(누수) |
| T3 | `src/api/routes_library_balance.py` 라우트 등록 | 200 스키마 키 고정; date 형식 오류 400; compare_days 범위 400; DB 없음 503; `/library/metrics/training-balance`가 `<slug>` 라우트로 가지 않음 |
| T4 | 프런트 타입·로더: `$lib/types` `TrainingBalance`, `/library/balance/+page.ts` | 로더 실패 시 `LoadFailure` |
| T5 | `$lib/chart/radar.ts` + `BalanceRadar.svelte` | 순수 함수 vitest: 각도·반경·clamp·결측 점선 구간; 6축/4축 렌더 |
| T6 | `BalanceTable.svelte`, `TrainingBalanceCard.svelte`, 브라우저 상단 삽입 | 표가 모든 축·기준·상태 텍스트 포함; collecting 시 EmptyState; axe 위반 0 |
| T7 | 실계정 사본 검증(읽기 전용) + 브라우저 스모크(모바일·데스크톱, 다크) | 기대값: A3≈104, A4≈85, A5≈111, A2=24.2/30≈81(풀 목표 시); 07 검증 "6개 축 정상 렌더링" |
| T8 | 문서: 07 §7d 체크박스, `phase-7-ui-renewal/BACKLOG.md`, files_index 재생성, `check_docs.py` | 정합성 20개 검사 통과, 전체 pytest 통과 |

## 9. 사용자 결정 필요

- **D1** 원문 축(stress/load/recovery/form/sleep/hrv) → 본 설계 6축(볼륨·롱런·이지·품질·부하·회복)으로 변경 승인.
- **D2** 기본 목표표(80/20 강도, 거리별 롱런 30/18/14/12 km)를 [가정] 상태로 출시할지, 플랜 템플릿 값과 맞출지.
- **D3** A4의 레이스 분리(TIDS v2.1, algo_changelog 동반)를 1차에 포함할지 후속으로 둘지.
- **D4** 배정: BACKLOG NOW/NEXT 승격 여부(현재 미배정).
