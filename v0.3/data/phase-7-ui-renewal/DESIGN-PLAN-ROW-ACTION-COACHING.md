# DESIGN-PLAN-ROW-ACTION-COACHING — 행 액션(move·reduce·rest·skip) 코칭 규칙

- 상태: 설계 초안 (2026-10-09). 코드 미반영. 구현 전 사용자 확인 필요(§8)
- 범위: `create_user_adjustment`(source=user|coach)의 안전장치, `move` op 규칙·오버레이 계약, `load_delta`, 반복 조정 경고, 통증 사유
- 상위: ADR-035, `DESIGN-PLAN-ADJUSTMENTS.md`, `31-coach-plan/design.md` §3(행 액션 시트)·§4.1 R1·R2·R7·R8·R9·§7.2
- 지키는 ADR-035 불변식: 원본 `planned_workouts` 불변, 읽기 시점 오버레이, **결정은 당일만**(출발 세션 date == today), 지문 불일치 시 stale, D9(조정 휴식일은 분모 제외)
- 공통 응답: 정책 거부는 `409 CONFLICT`, `details = {reason:"POLICY", rule:<코드>, message, suggest:[op…]}`. 경고는 거부하지 않고 응답 `advisories[]`로 준다

## 0. 근거 데이터 (실 계정 DB, 읽기 전용 조회 2026-10-09)

| 사실 | 값 | 설계에 쓰는 곳 |
|---|---|---|
| 현재 계획(goal 1, 11/22 풀) 주 구조 | 월 easy · **화 Q** · 수 recovery · **목 Q** · 금 recovery · 토 easy · **일 long** | move 간격 규칙(§1) |
| 품질 세션 `distance_km` | 인터벌 3.2km 저장, 실제 처방은 1000m×4 + WU/CD 각 10분(≈50분). 반복 거리 일부만 저장(R4 결함) | 품질 세션에 거리 % 감소 금지(§2) |
| 하드 세션(≥18km, 또는 5km 이상 5:00/km보다 빠름, 또는 TRIMP≥150) 간 간격, 2025-06~ | 37건, 1일 간격 1회, 4일 1회, 나머지 6일 이상 | 하드 연속일 금지가 이 러너 이력과 맞음 |
| 롱런(≥18km) 요일 | 일 14 · 토 2 · 월 1 · 화 1 | 일요일 롱런은 주 안 이동 여지가 없음(§1 D) |
| 러닝일 간 간격 분포 | 1일 167 · 2일 67 · 3일 28 · 4일+ 19 | 연속 이지일은 제약하지 않음 |
| 최근 실제 주간 km(ISO 38~41) | 52 · 35 · 22 · 24 (계획 약 54) | 반복 skip 경고가 곧 자주 켜질 상황 → 경고 상한·replan 유도(§3) |
| TRIMP/km(개인 중앙값) | 이지(≥5:30/km) 8.8 · 5:00–5:30 9.8 · 롱(≥18km) 10.1 · <5:00 10.8 (n=10, 신뢰 낮음) | 유형 계수(§5) |
| 주간 TRIMP ≈ Σkm×8.8×계수 | 67주 중앙 오차: 계수 없음 8.0% · 유형 계수 7.2% (**표본 내 적합, 가정**) | load_delta는 5% 단위로 반올림 표시 |
| 오늘 ACWR / TSB | 1.05 / +4.7 | 미리보기 예시 |
| `activity_feedback.pain`, `skip_reason` 기록 | 0건 / 0건 | 통증 규칙은 이력 백테스트 불가 → 보수적 고정 규칙(§4) |

유형 묶음(이하 공통): **HARD** = {interval, tempo, threshold, marathon, long_mp, long, race}, **Q** = HARD − {long, race}, **EASY** = {easy, recovery}.

## 1. move — 다른 날로 옮기기

입력: `{"op":"move","to_date":"YYYY-MM-DD","reason?":"fatigue|schedule|pain|other"}`. 출발 세션 = 오늘의 **유효 계획**(R1). 목표일 세션 = to_date의 유효 계획.

### 1.1 검사 순서(먼저 걸린 규칙으로 거부)

| # | 조건 | 결정 | rule / suggest |
|---|---|---|---|
| M1 | 출발 유형 = race | 거부 | `RACE_FIXED` / — |
| M2 | reason = pain | 거부 | `PAIN_NO_MOVE` / [rest] (§4) |
| M3 | 출발 세션이 이미 move로 옮겨온 세션(오버레이 op=move의 결과) | 거부. 연기는 1회만 | `ALREADY_MOVED` / [reduce, rest, skip] |
| M4 | to_date ≤ today 또는 to_date > today+3 | 거부 | `OUT_OF_RANGE` / — |
| M5 | to_date가 출발일과 다른 ISO 주(월~일) | 거부. 주간 볼륨·이행률·replan 단위가 주라서 | `CROSS_WEEK` / [reduce, skip] |
| M6 | to_date ≥ race_date − 3 이고 출발 ∈ Q, 또는 to_date ≥ race_date − 10 이고 출발 = long | 거부 | `TAPER_LOCK` / [reduce, skip] |
| M7 | 목표일에 매칭 활동이 있거나 completed=1 | 거부 | `TARGET_DONE` / — |
| M8 | 목표일 유효 계획 ∈ HARD | 거부(하드 2개 한 날·하드 맞교환 금지) | `TARGET_HARD` / 다른 날 |
| M9 | 출발 ∈ HARD 이고 이동 후 to_date−1 또는 to_date+1의 유효 계획 ∈ HARD | 거부. 하드 사이 최소 1일 비하드 | `HARD_SPACING` / [reduce, replace→easy] |
| M10 | 그 밖 | 허용 | — |

- M9 판정은 **이동·스왑을 적용한 뒤의** 주 계획으로 한다(스왑으로 오늘에 오는 세션은 EASY라 하드 아님).
- 현 계획 구조(화·목 Q, 일 long)에 적용한 결과: 화 Q → 수(목 Q 인접)·목(M8)·금(목 Q 인접) 모두 거부. 목 Q → 금 **허용**(금 recovery가 목으로 스왑, 금–일 사이 토 easy), 목 Q → 토 거부(일 long 인접). 일 long은 M5로 거부. **화 Q는 옮길 곳이 없다** — 의도된 결과다. 이때 시트는 `[이지로 바꾸기]`·`[건너뛰기]`를 먼저 보여 준다.
- EASY 세션 move는 M4~M8만 적용된다(이 러너는 연속 러닝일이 흔함, §0).

### 1.2 목표일에 세션이 있을 때

| 목표일 유효 계획 | 처리 |
|---|---|
| 없음 또는 rest | 출발 세션만 이동. 오늘은 휴식(D9로 분모 제외) |
| EASY | **스왑**: 목표 세션을 오늘로 옮긴다. 주간 볼륨 보존. 사용자는 오늘 스왑된 세션을 다시 rest·skip 할 수 있다(별도 조정) |
| HARD | M8 거부 |

### 1.3 저장·오버레이 계약 (스키마 변경 없음)

- 이동 행: `op='move'`, `date`=출발일, `after_json = {...before, "date": to_date}`, `reasons_json`에 `{"key":"pair","adj_id":<스왑행 id>}`.
- 스왑 행: 목표 workout에 `op='move'`, `date`=to_date(원래 날짜), `after.date`=today, `reasons`에 `{"key":"pair","adj_id":<이동행 id>}`, `decision='accepted'`. 두 행은 한 트랜잭션.
- `plan_overlay.apply`: op=move면 지문 확인 후 `w["date"] = after["date"]`, `original.date`에 원래 날짜. 호출 측(`get_planned_workouts`)은 **주 단위 조회 후 덮어쓰기**이므로 M5(같은 주)로 범위 문제가 없다.
- `live_adjustments`의 기간 필터는 출발일 기준이다. 같은 주라 그대로 동작한다.
- revert: 이동 행을 되돌리면 pair 행도 같이 reverted. 당일 규칙은 이동 행의 date(=오늘)로 판정한다. 스왑 행을 단독으로 되돌리는 API 호출은 이동 행으로 위임한다.
- 옮겨온 세션에 그날 reduce/rest/skip을 걸 수 있어야 한다. `create_user_adjustment`의 당일 검사는 **오버레이 후 date**로 하고, 새 조정은 같은 workout_id·`date`=오버레이 날짜로 별도 행에 저장한다(이동 행은 그대로). `live_adjustments`는 workout당 한 행이 아니라 `[move 행, 그 밖 op 행]`을 담고, 적용 순서는 move → 그 밖 op. 지문 비교는 move 행만 원본 date로, 그 밖 op 행은 오버레이 date로 한다.

## 2. reduce — 거리 줄이기

입력: `{"op":"reduce","pct":20,"reason?":…}` 또는 품질 세션은 `{"op":"reduce","reps":-1}` / `{"op":"replace","to_type":"easy"}`.

### 2.1 유형별 동작

| 출발 유형 | 허용 입력 | after | 근거 |
|---|---|---|---|
| easy, recovery | pct ∈ {20, 30, 40, 50} (시트 프리셋 −20/−40, 31 §3) | distance × (1−pct), 0.1km 반올림. 유형·페이스 유지 | 이지는 볼륨이 자극의 본체 |
| long | pct ∈ {15, 20, 30, 40} (프리셋 −15/−30, R8 황·주황과 같은 값) | 같음. after < 16km이면 유형 `easy`로 표기 | 16km 미만은 롱런 자극(≥90분)이 없음 |
| interval | `reps` −1 또는 −2. pct는 400 `PCT_NOT_FOR_QUALITY` | 반복 수 감소, WU/CD·반복 페이스·회복 유지. 남는 반복 ≥ 2와 work 거리 ≥ 원래의 50% | VO2 자극은 목표 강도에서의 시간. 페이스를 늦추거나 WU/CD를 깎으면 구조가 깨진다 |
| tempo, threshold, marathon, long_mp | pct ∈ {20, 30} → **work 구간만** 감소. work < 2.0km(threshold) / 5km(MP)가 되면 거부 | work 구간 축소, WU/CD 유지 | 역치 자극은 연속 20분 전후가 하한(가정: Daniels T 최소 블록) |
| Q 공통 | `replace→easy` 항상 허용 | 같은 **시간**의 이지(R8 주황) | 강도를 빼고 시간을 보존 |
| race | 거부 `RACE_FIXED` | — | — |

- 품질 세션 축소는 `after`에 `structure_json`(·`interval_prescription`)을 넣어야 한다. 오버레이 `_FIELDS`에 두 키를 추가하고 지문(workout_type·distance_km·date)은 그대로 둔다. 구조가 없는 외부 계획 Q는 reps 축소를 막고 `replace→easy`만 허용한다(`NO_STRUCTURE`).
- 전체 pct를 품질 세션에 적용하지 않는 이유: 저장된 `distance_km`가 반복 일부(3.2km)라 결과가 의미 없는 숫자가 되고(§0), 페이스 목표가 그대로라 매처·라벨이 "부족"으로 판정한다.
- 페이스는 어떤 reduce에서도 바꾸지 않는다(느린 인터벌은 다른 세션이다).

### 2.2 하한

| 조건 | 결정 |
|---|---|
| after 거리 < 3.0km 또는 이지 페이스 환산 < 20분 | 거부 `BELOW_FLOOR`, suggest [rest]. 20분 미만 러닝은 부하는 작고 일정 부담만 남는다(R8 적 "회복 20분"이 하한) |
| pct > 50 | 400 INVALID_PARAM. 절반 넘게 줄일 거면 rest가 맞다 |
| 원본 거리 없음(외부 계획) | easy/long은 시간 기반 처방이 있으면 시간 × (1−pct), 없으면 `NO_BASIS` 거부 |

## 3. skip/rest 반복 경고 (`advisories[]`, 거부하지 않음)

### 3.1 정의
- rest와 skip의 차이: rest = 계획이 쉬는 날로 바뀜(D9 분모 제외). skip = 하지 않음을 기록(분모 유지, `missed`가 아니라 `skipped` 라벨, 사유 저장). **결정 필요 1**
- 세는 대상: 최근 7일(오늘 포함) accepted 조정 중 op ∈ {rest, skip} 및 Q→easy 전환. source는 user·crs·coach 모두(몸이 보낸 신호는 출처와 무관).

### 3.2 임계값

| 코드 | 조건 | 수준 | 문구 예 |
|---|---|---|---|
| A1 `REST_STREAK` | 7일 rest/skip ≥ 3 | info | "최근 7일 중 3일을 쉬었어요. 지금 주간 계획이 일정에 비해 많을 수 있어요. [주간 계획 다시 맞추기 ›]" |
| A2 `Q_DROPPED_2` | 연속 2개 Q가 rest/skip/easy 전환 | caution | "품질 세션 두 번을 이어서 쉬었어요. 다음 품질 세션은 반복을 하나 줄여서 시작하면 부담이 덜해요." |
| A3 `LONG_DROPPED_2W` | 2주 연속 long이 skip/rest 또는 16km 미만 | caution (풀 목표만) | "2주째 롱런이 짧았어요. 대회까지 롱런 기회가 N번 남았어요. [이번 주 롱런 확인 ›]" |
| A4 `WEEK_LOAD_DROP` | load_delta.week_pct ≤ −30% | info | "이번 주 부하가 원래 계획보다 약 30% 줄어요." |
| A5 `ACWR_LOW` | acwr_expected < 0.8 이고 A1 또는 A4 | info | "이번 주는 회복 주에 가까워요(ACWR 0.7)." |
| A6 `REPLAN` | 2주 연속 A1, 또는 직전 2주 세션 이행 < 50% | info, 행 액션 시트 상단 고정 | "최근 2주 실제 거리가 계획의 약 45%예요. 계획을 지금 흐름에 맞추면 남은 기간을 더 잘 쓸 수 있어요. [계획 다시 맞추기 ›]"(S6) |

- 같은 코드는 ISO 주당 1회만 띄운다(서버가 이번 주 발급 여부를 조정 행 reasons에서 계산). A6이 켜지면 A1은 숨긴다. 이 러너는 지금(ISO 40~41 실제 22~24km / 계획 ~54) A6에 해당해, 경고 반복 대신 replan 하나로 모은다.
- 문구 원칙: 주어는 사람이 아니라 계획·주간 부하. "놓침·실패·포기·게으름" 금지, 느낌표 금지. 구조 = 사실(숫자 1개) + 영향 + 선택지 1개. 쉬는 결정 자체를 문제 삼지 않는다. 통증 사유일 때는 A1~A6을 띄우지 않는다(§4).

## 4. 통증(pain) 사유

입력: `reason:"pain"`이면 `pain_level ∈ {mild, moderate, severe}`(필수), `pain_sites ⊆ PAIN_SITES`(선택, 최대 3) — `activity_feedback_service`의 값을 재사용. `reasons_json`에 `{"key":"pain","level","sites"}` 저장.

| level | 오늘 세션 | 이후 2일(when today가 되었을 때 CRS 제안) | 허용 op | 안내 |
|---|---|---|---|---|
| mild | Q·long → `replace→easy` 기본 제안, EASY는 그대로 또는 reduce | Q·long이면 easy 제안(proposed, 수락은 사용자) | reduce, replace→easy, rest, skip | "달리는 동안 통증이 커지면 멈추세요." |
| moderate | rest로 고정(다른 op 무시) | Q·long → rest 제안, EASY → reduce 40% 제안 | rest | "통증이 2~3일 이어지면 진료를 받아 보세요." |
| severe | rest로 고정 | 모든 세션 rest 제안 | rest | "부기·체중 부하 시 통증이 있으면 진료를 먼저 받으세요." |

- move는 금지(M2): 아픈 날의 하드 세션을 주 안에 미루면 회복 기간이 짧아진다.
- 반복: 14일 안 pain 조정 2회 이상(부위 무관) 또는 같은 부위 2회 → `PAIN_REPEAT` caution "같은 부위 통증이 2주 사이 두 번 기록됐어요. 통증이 사라질 때까지 품질 세션은 미뤄 두는 게 안전해요." 진단·병명 언급 금지.
- 이후 2일 제안은 ADR-035 당일 판단 원칙대로 그날 `ensure_proposal`에서 만든다. 저장된 pain 조정이 72시간 안에 있으면 adjuster 결과보다 위 표를 우선(`rule_version='pain_v1'`).

## 5. load_delta — 주간 부하 변화 미리보기

응답 필드(31 §7.2): `load_delta = {week_pct, acwr_before, acwr_expected, basis:"trimp_km_v1"}`. 행 액션 시트는 미리보기 GET(`.../action/preview`, 같은 입력)으로, 수락 응답은 같은 값으로 준다.

**세션 예상 부하** `L(w) = km_eff(w) × u × k(type)`
- `u` = 최근 90일 이지(평균 페이스 ≥ 5:30/km, 1km 초과) 활동의 TRIMP/km 중앙값. 표본 < 10이면 8.8 대신 전체 러닝 중앙값. 이 러너 8.8.
- `k`: recovery 0.95(가정), easy 1.00, long 1.15, tempo·threshold·marathon·long_mp 1.11, interval 1.23(n=10, 신뢰 낮음), race 1.25(가정). 개인 표본이 유형별 ≥ 15건이면 개인값으로 대체.
- `km_eff`: 구조가 있으면 R4대로 WU+반복+회복+CD 총량(시간 구간은 이지 페이스 중앙값으로 km 환산), 없으면 `distance_km`. rest·skip = 0.
- R9와 같은 TRIMP 척도다(TSS 척도 쓰지 않음).

**주간 변화** (ISO 주 월~일)
```
B = Σ_{d<today} actual_trimp(d) + Σ_{d≥today} L(effective_before(d))   # 이 조정을 뺀 유효 계획
A = 같은 식, effective_after(d)                                       # 이 조정을 넣은 유효 계획
week_pct = round((A − B) / B × 100 / 5) × 5     # 5% 단위(오차 중앙 ~7%, §0)
```
**ACWR 투영**: `src/metrics/acwr`와 같은 정의(EWMA α = 2/(N+1), 7/42일)로, 어제까지 실제 일별 TRIMP에 오늘~일요일 `L`을 이어 붙여 일요일 값 `acwr_before`·`acwr_expected`를 낸다. `pmc.ewma_loads`를 재사용하되 CalcContext 대신 conn용 일별 부하 조회 헬퍼를 둔다. CTL < 10이면 null.
- 표시: `이번 주 부하 −15% · ACWR 1.05 → 0.92`. 경계 0.8·1.3을 넘을 때만 색(§C7 caution). move는 week_pct ≈ 0이 정상이고 ACWR만 미세하게 변한다.
- 예(오늘 10-09 recovery 3.9km → rest): L = 3.9 × 8.8 × 0.95 ≈ 33 TRIMP. 주 B가 약 430이라고 가정하면 week_pct ≈ −8 → `−10%`(B 값은 설명용 가정).

## 6. source=coach 제약
- coach는 §1~§4 규칙을 똑같이 통과해야 하고, 추가로 readiness 레벨이 허용하는 것보다 강도를 올릴 수 없다(기존 COACH_OPS 원칙). coach의 move는 사용자 수락 카드(proposed)로만 만들고 즉시 accepted 금지 — 이동은 일정 판단이라 사용자만 안다. **결정 필요 3**

## 7. 테스트 목록 (구현 담당)
- move: M1~M10 각 1케이스(현 계획 주 구조 픽스처로 화 Q→수 HARD_SPACING, 월 easy→수 스왑, 일 long CROSS_WEEK, 11/19 Q TAPER_LOCK), 스왑 두 행 원자성, revert 시 pair 동반, 옮겨온 세션에 당일 rest 적용, 오버레이 후 `week_compliance` 분모(D9).
- reduce: easy 20%·50%·51%(400), 하한 3km, long 30% → 16km 미만 easy 표기, interval pct → 400, reps −1 구조, tempo work < 2km 거부, 외부 Q NO_STRUCTURE.
- advisories: A1~A6 경계값(2/3회, 7일 창 경계), 주당 1회, pain이면 미발급.
- pain: level별 op 강제, 72시간 제안 우선순위, PAIN_REPEAT.
- load_delta: 손계산 픽스처 일치, CTL<10 null, 5% 반올림. **백테스트**: 지난 67주 각 주 월요일 시점 투영 vs 실제 주간 TRIMP 오차(목표 중앙 ≤ 10%)를 스크립트로 확인 후 계수 확정.

## 8. 결정 필요
1. **skip을 분모에 남길지.** 추천: 남긴다(rest만 D9 제외). 이유: 모두 rest로 처리되면 이행률이 늘 높게 보이고 A6(replan 유도)의 근거가 사라진다. 대안: skip도 제외하고 A1로만 신호.
2. **move 범위 +3일·같은 주.** 추천 그대로. 대안: 롱런만 다음 주 월요일 허용 — 이 계획에서는 화 Q와 인접해 M9로 어차피 막힌다.
3. **coach move는 proposed로만.** 추천 그대로.
4. **품질 세션 reduce를 reps 기반으로 바꾸는 범위.** 추천: planner Q만(structure_json 있음). 외부 계획 Q는 easy 전환만.
