# S4 잔여(8분류·4카드·§3b 정렬) + S5 웰니스 `/:date` — 구현 명세

> 작성 2026-10-04 (product-architect). 근거: `21-library-metrics/design.md` §2.2·§2.4·§3·§6·§7.2(d)·§11-3b, `99-summary.md` §8.5, `IMPL-PROGRESS.md` S4 1~3차.
> 실측 근거: `METRIC_REGISTRY`에서 `scope == "daily"`인 메트릭 **84개**(registry 카테고리 10종). 16개 카테고리 중 `pace`·`power`·`running_dynamics`·`volume`·`athlete`·`meta`는 daily 메트릭이 **0개**라서 브라우저에 나오지 않는다(activity/athlete scope 전용).
> 상태: 설계 제안. `(판단 필요)` 표시 항목은 사용자가 결정한다.

---

## 1. 8분류 매핑

### 1.1 그룹 키·라벨·순서 (§2.2 블록 순서 그대로)

| 순서 | key | 라벨 | 의도(이 묶음을 여는 질문) |
|---|---|---|---|
| 1 | `today` | 오늘 상태 | 오늘 달려도 되나? |
| 2 | `load` | 훈련 부하 | 요즘 얼마나 쌓였나? |
| 3 | `race` | 레이스 예측 | 대회에서 몇 분이 나오나? |
| 4 | `ability` | 능력·효율 | 엔진이 커지고 있나? |
| 5 | `sleep` | 수면 | 잘 잤나? |
| 6 | `vitals` | 생체 신호 | 몸이 평소와 다른가? |
| 7 | `hr_ref` | 심박 기준값 | 존·기준선이 맞나? (참조값이라 뒤에 둔다) |
| 8 | `env` | 환경 | 날씨가 기록을 얼마나 바꾸나? |
| 9 | `other` | 기타 | 미분류 안전망(§1.4). 평소에는 비어 있어서 숨는다 |

`load`·`sleep`은 기존 registry 카테고리 키와 같은 값을 쓴다. 기존 `?category=load|sleep` 링크가 그대로 동작한다. "레이스 준비도"는 RRI와 이름이 충돌하므로 쓰지 않는다.

### 1.2 slug 단위 매핑 (daily 84개 전수)

tier: **P** = 대표(섹션 4장 후보), **D** = 세부(섹션에 나오지만 정렬상 대표 뒤), **C** = 구성요소(목록·검색에서 숨김. 상위 지표 분해·추세에서만 노출).

| 그룹 | P | D | C (숨김) | 원래 registry 카테고리 |
|---|---|---|---|---|
| today (6+12) | utrs, cirs, crs, rri | training_readiness_score, training_readiness_level | utrs_body_battery·_tsb·_sleep·_hrv·_stress, cirs_acwr·_lsi·_consecutive·_fatigue, training_readiness_hrv_factor·_sleep_factor·_recovery_factor | readiness 17 + **rri(capacity)** |
| load (14) | acwr, tsb, ctl, atl | ramp_rate, rtti, lsi, monotony, training_strain, running_tolerance_load, running_tolerance_score, training_response | running_tolerance_optimal_min·_max (밴드 경계값) | load 14 |
| race (7) | race_pred_marathon_sec, race_pred_half_sec, race_pred_10k_sec, race_pred_5k_sec | race_pred_vdot, vdot_adj, marathon_shape | — | prediction 5 + **vdot_adj·marathon_shape(capacity)** |
| ability (7) | vo2max, rec, critical_power, eftp | garmin_ftp, lt_speed_ref, sapi | — | capacity 5 + efficiency 1 + **lt_speed_ref(hr)** |
| sleep (9) | sleep_score, sleep_duration_sec, sleep_deep_sec, sleep_rem_sec | sleep_light_sec, sleep_awake_sec, sleep_avg_hr, sleep_body_battery_change | sleep_start_time (텍스트. 지금도 `_WELLNESS_TEXT`로 제외) | sleep 14 − 5 |
| vitals (15) | body_battery_high, avg_stress, avg_spo2, skin_temp_deviation | body_battery_low, min_spo2, avg_respiration_sleep, min_respiration_sleep, steps, active_calories, weight_kg | stress_high/medium/low/rest_duration_sec (avg_stress 분해) | body 5 + stress 5 + **SpO2·호흡·피부온도 5(sleep)** |
| hr_ref (13) | resting_hr, hrv_last_night, hrv_weekly_avg, hrmax_self | lthr_self, hrmax_ref, lthr_ref, hrv_5min_high, hrv_status | hrv_baseline_low, hrv_baseline_balanced_low·_upper (밴드 경계), hr_profile (복합 JSON) | hr 14 − lt_speed_ref |
| env (1) | heat_model | — | — | weather 1 |

합계 18+14+7+7+9+15+13+1 = 84. 목록에 나오는 카드는 P+D = 59개다.

**registry 카테고리와 다르게 배치한 6개와 이유**
- `rri` capacity→today: 설계 §2.2가 오늘 상태에 명시했다.
- `vdot_adj`·`marathon_shape` capacity→race: §2.2 "VDOT·Shape"는 예측 묶음이다.
- `lt_speed_ref` hr→ability: 심박이 아니라 속도 역치다.
- SpO2·호흡·피부온도 sleep→vitals: §2.2 "생체 신호"에 명시했다. 수면 중에 측정하지만 사용자는 "아픈가?"를 묻는 맥락에서 찾는다.
- BB·스트레스·걸음·칼로리·체중 → vitals: 8분류에 "신체" 그룹이 없다. 결정이 아닌 신호라서 오늘 상태(복합 판정)에 넣지 않는다. `(판단 필요)` 체중·걸음·칼로리를 별도 그룹으로 뺄지 정해야 한다. 이 안은 9번째 그룹을 만들지 않는 쪽이다.

### 1.3 매핑 위치 결정: **백엔드** (registry `category`는 건드리지 않고 별도 필드 추가)

근거
1. **매핑 단위가 카테고리가 아니라 slug다.** 위 6건처럼 같은 registry 카테고리(capacity·sleep·hr)가 여러 그룹으로 나뉜다. 프론트가 이 매핑을 가지면 84개 slug 사전이 TS에 복제된다. 이는 표시명 SSOT(ADR-018, `metric_labels.py`)와 "프론트 밴드 상수 0개"(§8) 원칙에 어긋난다.
2. **소비자가 여럿이다.** 브라우저, 웰니스 `/:date`(코어 카드 묶음), Coach 맥락, 검색이 같은 분류를 써야 한다.
3. **누락 검출을 테스트로 강제할 수 있다.** Python 테스트에서 registry daily 전수와 매핑 키를 비교할 수 있다(§1.4).
4. registry `category`는 `metric_store.category` 컬럼, `wellness_service._WELLNESS_CATEGORIES`, extractor가 쓰는 **저장 분류**다. 표시 의도로 바꾸면 저장 경로가 흔들린다. 그래서 **표시 전용 상위 그룹을 별도 필드로 둔다**.
   - 이름 주의: 기존 `src/utils/metric_groups.SEMANTIC_GROUPS`는 Provider 비교 그룹이라 다른 개념이다. 새 매핑은 `browse_group` 같은 별도 이름으로 두고 metric_labels와 같은 층에 둔다. 모듈 위치는 system-architect가 정한다.

**API 변화 (`GET /api/v1/library/metrics`)**
- `categories[]` 요소: `{category: <group key>, label, total, metrics}`. 순서는 §1.1 순서를 서버가 보장한다. 빈 그룹은 생략한다.
- 각 metric에 `group`, `tier`("primary"|"detail"), `source_category`(기존 registry 카테고리, 디버그·호환용), `salience`(§2.3)를 추가한다.
- tier C는 응답에서 **제외**한다. 분해·상세 API에서만 보인다. 프론트의 `isComponentMetric`(label 정규식 `(parent:`)은 삭제 대상이다. TR factor 3개·밴드 경계 5개처럼 정규식이 못 잡던 항목도 함께 정리된다.
- 프론트에 남는 것: 그룹 표시 순서는 서버 순서를 그대로 쓴다. 기존 `COLLAPSED = {sleep, hr, weather}`는 4카드 제한(§2.1)이 대신하므로 삭제한다.

**URL 호환**: 기존 `?category=` 값은 서버가 아니라 프론트 `+page.ts`에서 한 번 치환한다. 치환 후 `replaceState`로 URL을 정규화한다.
`readiness→today`, `prediction→race`, `capacity|efficiency→ability`, `hr→hr_ref`, `body|stress→vitals`, `weather→env`, 나머지 미지 키→`all`. `load`·`sleep`은 그대로 둔다.

### 1.4 미분류 처리 규칙
- **런타임(관대)**: 매핑에 없는 daily slug는 `group="other"`, `tier="detail"`로 응답한다. 숨기지 않는다. 데이터가 사라지는 것보다 "기타"에 보이는 편이 낫다(§0 투명성 원칙). `other`는 항상 마지막 그룹이고, 비면 칩과 섹션 모두 숨는다.
- **개발(엄격)**: 테스트가 `{daily slug} − {매핑 키} = ∅`과 `{매핑 키} − {daily slug} = ∅`을 모두 검사한다. 새 daily Calculator를 추가하면 매핑을 갱신하지 않는 한 테스트가 실패한다. `check_docs.py` 검사 추가는 선택이다.
- 매핑 키는 있는데 그날 값이 없는 경우는 지금처럼 응답에서 생략한다(90일 창, `last_value_date`).

---

## 2. 모바일 4카드 + "모두 보기 ›" + §3b 정렬

### 2.1 섹션 카드 제한 규칙

| 조건 | 섹션당 카드 | "모두 보기 ›" | 헤더 |
|---|---|---|---|
| 전체 보기(`category=all`, 검색어 없음) | **최대 4장**(모바일 2열×2행, 데스크톱 4열×1행. §2.2 와이어 공통) | 표시 대상이 4장을 넘을 때만 | `훈련 부하 (12)` — 괄호 수 = 필터 화면에서 보일 카드 수 |
| 카테고리 필터(`category=<key>`) | 전부 | 없음 | 같음 |
| 검색 중(`q` 있음) | 전부, 그룹 구분 없이 평면 | 없음 | `'{q}' 결과 N` |
| Provider 필터 | 위 규칙을 그대로 적용. 제한은 Provider 필터를 **적용한 뒤** 센다 | | |

- 4장을 뽑는 기준: §2.3 정렬 결과의 앞 4장이다. "내 지표"에 고정된 slug는 전체 보기 섹션에서 빼고 센다(현행 유지). 헤더 괄호 수에는 포함한다.
- "모두 보기 ›" 탭 동작(§3 표): `selectedCategory = key` → `?category=key` **replace** → 그리드 상단으로 스크롤(`scrollIntoView`, 칩 줄이 sticky면 그 아래). 활성 칩이 가로 스크롤 밖에 있으면 보이도록 스크롤한다. 되돌아가는 경로는 "전체" 칩이다(history 미적재. §3 "이전 필터").
- 터치 타깃은 44px 이상(§C2)이다. 텍스트는 `모두 보기 ›`이고, 접근성 이름은 `훈련 부하 12개 모두 보기`로 둔다.
- 수용 기준: 390px 전체 보기 스크롤 길이 ≤ 2,700px(§8). 8그룹 × (헤더 40 + 2행 × 175 + 간격 24) ≈ 3,300px라서 **초과 위험**이 있다. 대응책은 `(판단 필요)` 두 가지 중 하나다.
  - (a) env·hr_ref 섹션은 전체 보기에서 2장(1행)만 보인다.
  - (b) 모바일 카드 높이를 150px로 줄인다(스파크라인은 목록에서 이미 비활성화). 이렇게 하면 ≈2,900px이다.
  - 권장은 (a)+(b)이고, 결과는 ≈2,600px이다.

### 2.2 정렬 입력 필드 (서버가 metric마다 계산)

| 필드 | 정의 |
|---|---|
| `value`, `last_value_date` | 기존과 같다 |
| `fresh` | `last_value_date == date`(기준일 당일 값인지) |
| `status` | `bands.with_grade` 결과(excellent/good/neutral/caution/poor). 밴드가 없으면 null(현재 utrs·crs·cirs·tsb·rri·acwr 6개만 있음) |
| `z` | 기준일 값 v_d의 평소 대비 편차. `(v_d − mean(B)) / max(sd(B), floor)`. B = d−28..d−1의 값 있는 날. **\|B\| < 7이면 null** |
| `floor` | `min_span / 4`(display_meta의 스파크라인 최소 폭 재사용). 거의 일정한 지표(체중·HRmax)의 작은 흔들림이 z를 폭발시키지 않게 막는다 |
| `tier` | §1.2 P/D |
| `registry_index` | registry 선언 순서(결정적 최종 동률 해소용) |

"당일 변화"를 전일 대비 Δ가 아니라 **평소 대비 수준 편차**로 정의한 이유: 예측·VDOT·eFTP처럼 가끔 갱신되는 지표는 Δ가 대부분 0이다. 수면·HRV처럼 매일 바뀌는 지표는 Δ가 잡음이다. 수준 편차는 두 경우 모두 "오늘 값이 평소와 얼마나 다른가"로 같은 척도가 된다. 한계: 꾸준히 오르는 CTL은 |z|≈1.5가 상시로 나온다. 이 정도는 상위권 노출로 허용한다.

### 2.3 정렬 키 (사전식, 앞이 우선)

```
salience_key = (
  0 if fresh else 1,                                  # ① 당일 값 먼저, 지난 값(MM-DD 기준)은 뒤로
  0 if status in {poor, caution} else 1,              # ② 경고 상태 우선 (§11-3b "상태 비중립 우선")
  -round(|z|, 1) if z is not None else +inf,          # ③ 평소 대비 편차 큰 순, z 없음은 맨 뒤
  0 if tier == P else 1,                              # ④ 대표 > 세부
  registry_index,                                     # ⑤ 결정적 동률 해소
)
```
- **동률 처리**: ③은 소수 1자리로 반올림한 뒤 비교한다(0.04 차이로 매일 순서가 바뀌는 깜빡임을 막는다). 같으면 ④, 그다음 ⑤로 가므로 항상 전순서다.
- excellent는 ②에서 경고로 치지 않는다. 좋은 쪽으로 크게 벗어난 경우는 ③으로 올라온다.
- 서버가 `categories[].metrics`를 **정렬된 상태로** 반환한다. 프론트는 순서를 바꾸지 않는다(필터만 한다). `salience:{z, fresh, rank}`를 응답에 넣어 스모크·디버그에 쓴다.
- 정렬 적용 범위: 전체 보기 섹션과 카테고리 필터 화면이다. **"내 지표"는 사용자가 고정한 순서를 유지한다.** 검색 결과는 일치도(정확 slug/약어 > 한글명 접두 > 부분) 순이고, 동률일 때 salience를 쓴다.
- 카드 표기(선택): |z| ≥ 2이면 기존 변화 캡션 옆에 InfoTag `평소와 다름`을 붙인다. 색은 §C7 status만 쓰고 z로 색을 정하지 않는다.
- 테스트 케이스(최소): ① 당일 vs 지난 값 ② caution이 |z| 큰 neutral보다 앞섬 ③ \|B\|<7 → z null → 섹션 맨 뒤 ④ 동일 |z| 반올림 동률 → tier → registry 순서 ⑤ sd=0 → floor 적용.

---

## 3. S5 웰니스 `/library/wellness/:date`

### 3.1 라우트
- 신규 `routes/library/wellness/[date]/+page.{svelte,ts}`. 핵심 API 1개만 await한다(§C5). 추세는 비동기 스트리밍한다.
- `/library/wellness`(날짜 없음) → 오늘 날짜로 `replaceState`. `/library/wellness?date=YYYY-MM-DD`(10-today D2 링크) → `/library/wellness/YYYY-MM-DD`로 replace한다.
- `:date` 형식 오류 → `+error.svelte`(400). 미래 날짜 → 오늘로 replace한다.
- ‹ › / 7일 점 / 모바일 스와이프 → `/library/wellness/:date` **replace**(§3).

### 3.2 API — `GET /api/v1/library/wellness?date=` 확장(기존 필드 유지 + §7.2(d) 추가)

```jsonc
{
  "date": "2026-09-27",
  "has_record": true,              // daily_wellness 행 또는 daily 메트릭이 하나라도 있으면 true
  "is_today": true,
  "headline": {                    // 신규 제안(§7.2(d) 밖) — 프론트 임계값 0개 원칙 때문에 서버가 만든다
    "status": "neutral", "status_label": "보통",          // = UTRS 등급
    "text": "회복 보통 — 수면이 짧았어요",
    "reasons": [                                           // §2.2 z로 |z| 상위 2개, 후보 = 수면시간·HRV·안정심박·BB
      {"slug":"sleep_duration_sec","value":15240,"baseline":25320,"delta":-10080,"direction":"worse","chip":"수면 4h14m"},
      {"slug":"hrv_last_night","value":107,"baseline":79,"direction":"better","chip":"HRV 107 · 평소 79"}
    ]
  },
  "readiness": {"utrs":{"value":60,"status":"neutral","status_label":"보통"},
                "cirs":{"value":37,"status":"neutral","status_label":"보통"}},   // 값 없으면 null
  "sleep": {"score":52,"duration_sec":15240,"mean30_sec":25320,
            "stages":{"deep":3420,"light":10920,"rem":960,"awake":960}},          // 단계 하나라도 없으면 stages=null
  "body_battery": {"high":76,"low":16,"charged":48},   // charged = sleep_body_battery_change
  "baselines": {
    "hrv_last_night":{"mean7":79,"p25":72,"p75":88,"garmin_band":[76,111],"n":28},  // band = hrv_baseline_balanced_low/upper
    "resting_hr":{"mean7":44,"p25":39,"p75":49,"n":28},
    "sleep_duration_sec":{"mean30":25320,"n":30}
  },                               // n<7이면 해당 키 생략
  "as_of": {"avg_stress":"21:42","steps":"21:42"},     // is_today일 때만. daily_wellness.updated_at(로컬 HH:MM)
  "core": {...}, "metrics_by_category": {...}, "readiness_summary": {...},  // 기존 필드(하위호환, v1 사용처 정리 후 제거)
  "nav": {"prev":"2026-09-26","next":null},            // 기록 있는 가장 가까운 날짜. 미래·없음 → null
  "week": [{"date":"2026-09-22","status":"good"}, ...7개, 월~일]  // status = UTRS 등급, 값 없으면 "none"
}
```
- 기준선 창: mean7 = d−7..d−1, p25/p75 = d−28..d−1이다(§2.2 z와 같은 창이라 헤드라인과 카드의 "평소"가 일치한다). 당일은 창에 포함하지 않는다.
- `(판단 필요)` BB "기상" 값: 수집 원천에 기상 시점 BB가 없다. `high`(일 최고 ≈ 기상 직후)를 쓰되 라벨은 **"최고"**로 둔다. 와이어의 "기상76"은 원천 수집이 추가될 때까지 표기를 보류한다(정직한 라벨 원칙).
- 추세: `GET /library/wellness/trend?days=30&end=YYYY-MM-DD` — `end` 파라미터를 신규로 추가해서 선택일 기준으로 끝나게 한다. 지금은 오늘 고정이다. 시리즈마다 `band:{p25,p75}`를 추가한다.
- 오류: 날짜 형식 오류 → 400 `INVALID_PARAM`. DB 없음 → 503(현행). **기록 없음은 200 + `has_record:false`**다(§C5 "데이터 없음 ≠ 불러오기 실패").

### 3.3 화면 블록 (모바일 1열 순서 = 데스크톱 좌1/3·우2/3 배치, §2.4)

| # | 블록 | Level | 데이터 | 탭 동작 |
|---|---|---|---|---|
| 1 | 날짜 바 `‹ 9월 26일 (금) │ 9월 27일 (토) · 오늘 │ ›` + [달력] | 0 | `date`, `nav` | ‹ ›: 해당 날짜로 replace. `nav.next=null`이면 › 비활성 |
| 2 | 7일 회복 점 `● ● ○ ◐` | 0 | `week` | 점: 그 날짜로 replace. "none"은 `┄` |
| 3 | 헤드라인 1줄 (의미 먼저, 수치는 괄호) | 0 | `headline.text` + reasons의 delta | — |
| 4 | 근거 DrillChip 2~3개 | 1 | `headline.reasons[].chip` | `/library/metrics/{slug}?date=` push |
| 5 | 준비도·부상위험 2칸 | 1 | `readiness` | `/library/metrics/utrs?date=`(분해 열림) push |
| 6 | 수면 카드 (점수·시간·Δ평소 + 단계 막대) | 1 | `sleep`, `baselines.sleep_duration_sec` | sleep_duration_sec 상세 push |
| 7 | 코어 카드 2열: HRV(밴드), 안정심박(p25–p75), BB 최고/최저/충전, 스트레스·걸음(`as_of` 기준) | 1 | `baselines`, `body_battery`, `core` | 각 메트릭 상세 `?date=` push |
| 8 | 30일 small multiples(수면 점수·HRV·준비도, x축 공유, p25–p75 띠, 선택일 세로선) | 2 | trend API | §C1 스크럽. 점 탭 → 그 날짜로 replace |

헤드라인 문구 규칙: `"회복 {status_label} — {reason1 문장}. {reason2 문장}."`. reason 문장은 서버 템플릿으로 만든다(예: worse 수면 → "수면이 짧았어요 (4h14m, 평소 7h02m보다 −2h48m)"). reasons가 0개(전부 평소 범위)이면 "회복 {label} — 평소와 비슷해요."로 쓴다.

### 3.4 로딩·빈 데이터

| 상황 | 처리 |
|---|---|
| 로딩 | 블록 1~7 최종 치수 스켈레톤(CLS ≤ 0.05). 추세는 별도 스켈레톤 |
| `has_record:false` | 블록 1·2는 유지하고 3~7 대신 "9월 20일 웰니스 기록이 없어요" + [가장 가까운 날짜로](`nav.prev ?? nav.next`. 둘 다 null이면 버튼 숨김 + [동기화 상태 보기]) |
| UTRS 없음(웰니스만 있음) | 헤드라인 "회복 판정 수집 중 — {reasons}", 블록 5는 "데이터 수집 중" 카드, 점은 `┄` |
| 개별 필드 없음 | 해당 카드만 "—" + 작게 "기록 없음". 블록 전체는 숨기지 않는다(레이아웃 고정) |
| 기준선 n<7 | "평소" 대신 "기준선 수집 중 (n/7일)". 밴드·Δ 생략. reasons 후보에서 제외 |
| 수면 단계 null | 막대 자리에 "단계 데이터 없음"(높이 유지) |
| 오늘·부분 데이터 | 스트레스·걸음에 `{as_of} 기준` 표기(§C6) |
| 오류 | §C5 블록 오류 `불러오지 못했어요 · [다시 시도]`. 추세 오류는 추세 블록만 처리한다 |

### 3.5 S5 수용 기준(발췌, §8 대응)
- 모든 수치 카드·칩이 이동한다. 날짜 이동(‹ ›·스와이프·7일 점)이 replace로 동작한다. `?date=` 호환 링크가 `/:date`로 정규화된다.
- 헤드라인·카드의 "평소"가 같은 창이고, UTRS·CIRS 등급이 브라우저·Today와 같다. 프론트 임계값 상수는 0개다.
- 기록 없는 날짜에서 200 + 빈 상태가 나오고, 오류 상태와 시각적으로 구분된다.

---

## 4. 열린 결정 요약
1. 체중·걸음·칼로리를 `vitals`에 둘지 별도 그룹을 둘지(§1.2).
2. 2,700px 대응: env·hr_ref 2장 + 카드 150px(§2.1).
3. BB "기상" 라벨을 "최고"로 둘지(§3.2).
4. `headline`을 §7.2(d) 밖 필드로 추가하는 것 승인(§3.2).
