# 설계: 데이터 신선도 반영 (지표 판정에 입력 경과일·커버리지 포함)

- 대상 ID: T-03 (`/today` Hero + UTRS 게이지), M-02 (`/library/metrics` UTRS 카드·상세, 수면 계열 상세), FRS-8 확장(`crs`·`rmr`·`rtti` 목록·상세, `/today` 상태의 CRS)
- 상태: 설계 확정 (구현 전, D1~D21 = FRS-1~21 전부 결정됨 2026-10-11)
- 변경 이력:
  - 2026-10-11 FRS-8 확장 설계 — `crs`·`rmr`·`rtti` 입력 분석과 메트릭별 SPEC(§2.5), 변경 파일·단계·검증 반영, 결정 D9~D13 추가
  - 2026-10-11 FRS-9~11 결정 반영(FRS-11=c) — 읽기 시점 대체 coverage 제거, `rmr`·`rtti`·`crs` Calculator가 실측 confidence 기록(1.0→1.1)·전체 재계산·단계적 롤아웃, D14 추가
  - 2026-10-11 FRS-12~14 결정 반영 — BOOST 보류(§2.6, `adjuster_v2`), 결측 성분 문구 목록/상세 분리, `AlgoChange.value_changed`, D15~D17 추가
  - 2026-10-11 FRS-15~17 결정 반영 — A1+A2 모두 BOOST 보류(adjuster 인자 주입), 한 줄 보류 사유(문구는 FRS-4), 해제 = BB·HRV 당일 + CRS fresh, D18·D19 추가
  - 2026-10-11 FRS-18(c) 래퍼 설계, FRS-19(a) — `plan_service.todays_adjustment_with_hold` 단일 진입점·호출부 이관 순서(§2.7), Hero `as_planned`+`hold_reason`, D20·D21 추가
  - 2026-10-11 설계서 동기화(FRS-4·20·21 확정 반영)
- 관련 ADR: ADR-009 (Calculator raw SQL 금지 — 신선도 판정은 서비스 계층, confidence는 이미 조회한 입력으로만 계산), ADR-020 (등급은 서버 SSOT, 프론트 임계값 없음 — 신선도도 같은 원칙), ADR-044 (동기화 상태는 원장만 진실 — `source_missing` caveat의 출처), ADR-042 (Calculator 버전 변경 시 changelog — `rmr`·`rtti`·`crs` 1.1), ADR-035 (조정 제안 행의 `rule_version` — BOOST 보류로 `adjuster_v2`)

## 1. 근본 원인

**RC-1. "신선함"을 지표 행의 날짜로만 판단하고, 입력 데이터의 날짜·완결성은 응답 계약에 없다.**
- UTRS(`src/metrics/utrs.py`)는 가용 성분만으로 `score / total_weight` 재정규화한다. 웰니스가 없는 날도 TSB(가중치 0.25) 하나로 매일 새 행이 생기고, TSB 성분 하나가 점수 100%를 결정한다(`components={"tsb":84.8}` → 85 "매우 좋음"). confidence 0.25는 저장되지만 소비처가 버린다.
- 그래서 기준일 행이 "오늘 값"으로 존재하므로 `metrics_browser_service`의 `salience.fresh=True`, `last_value_date == date`가 되어 목록 카드의 "MM-DD 기준" 표시도 뜨지 않는다. 입력(웰니스 마지막 09-27)과 값의 날짜가 다르다는 정보 자체가 없다.
- `today_readiness.build_readiness`는 `{value, delta_1d, status, provider, version}`만 내보내고 confidence·components를 뺀다(`dashboard_service`는 confidence를 싣지만 v2 게이지 경로는 쓰지 않는다).
- `get_metric_trend`는 `points[-1]`을 `current`로 쓰고 오늘과의 거리를 내보내지 않는다. 웰니스 원값(수면 등)은 14일 전 값이 "현재"로 표시된다.

**RC-2. 판정(등급·헤드라인)과 결손 경고가 서로 다른 채널이라, 경고가 판정을 바꾸지 못한다.**
- 결손 경고는 동기화 원장 기반 `sync_state_service`의 `caveats[source_missing]`(provider 단위)로만 `briefing_state.caveats`에 실린다.
- 등급·문구 생성기 `bands.grade`, `fatigue.readiness_decision`, `race_hub_service.race_briefing`은 입력 신선도를 인자로 받지 않는다. 결과적으로 "컨디션 여유가 있어 핵심 세션을 소화하기 좋습니다"(TSB만으로 판정)라는 단정 문구와 "데이터가 14일째 들어오지 않아..." 꼬리 경고가 동시에 나간다.

## 2. 설계안 (추천: A안 — 읽기 시점 서비스 판정, coverage만 계산 시점 기록)

### 2.1 신선도 판정 모듈 — `src/services/metric_freshness.py` (신규)
- 메트릭별 입력 출처 선언(상수, SSOT): `FRESHNESS_SPEC`(§2.5). 웰니스 원값 메트릭(`MetricDef.storage == "wellness"`)은 자기 컬럼이 곧 입력이므로 자동 처리. 적용: `utrs` + 웰니스 원값 + `crs`·`rmr`·`rtti`(FRS-8). SPEC 상수는 `src/services/metric_freshness_spec.py`로 분리(§3).
- 인터페이스:
  ```python
  def assess(conn, metric_name: str, basis_date: str, row: dict | None) -> dict
  def assess_many(conn, names: list[str], basis_date: str, rows: dict) -> dict[str, dict]  # 웰니스 MAX(date) 1회 조회 공유
  # 반환: {level: "fresh"|"partial"|"stale"|"missing", value_date, age_days,
  #        inputs: {"wellness": {"last_date", "days"}}, coverage, used_inputs: [...],
  #        reasons: [{code: "input_stale"|"low_coverage"|"value_old"|..., ...}], assertive: bool}
  ```
- 판정 규칙: `value_age = basis - value_date`, `input_age = basis - 웰니스 입력 필드 중 non-null 최신일`, `coverage = row.confidence`(**전 메트릭 공통, 저장값 그대로** — FRS-11 (c)), `used_inputs` = 행 json에서 읽은 성분(§2.5). 임계값은 모듈 상수: stale = 웰니스 입력 경과일 2일 이상(D1·D9), partial = 웰니스 성분 0개 또는 coverage < 0.5(D2).
- `assertive = (level == "fresh")`. 화면·문구 생성기는 이 플래그만 본다(프론트 임계값 없음, ADR-020과 같은 원칙).
- SQL은 이 서비스 모듈에만 둔다(`daily_wellness`의 필드별 `MAX(date) WHERE col IS NOT NULL AND date <= ?` 1쿼리 — stale 판정용). `db_helpers.py`(754줄)에는 추가하지 않는다.

### 2.2 응답 계약 확장 (전부 추가 필드, 기존 키 불변)
- `/api/v1/today` `readiness.{utrs|cirs|tsb}`에 `confidence`, `freshness` 추가.
- `/api/v1/library/metrics` 각 entry에 `freshness` 추가(`last_value_date`·`confidence_label`·`salience.fresh`는 유지, `salience.fresh`는 `freshness.level == "fresh"`로 의미를 맞춤 — D6).
- `/api/v1/library/metrics/<slug>` trend에 `current_date`, `freshness` 추가.

### 2.3 판정 문구가 신선도를 받도록 — 경고를 판정 입력으로 승격 (RC-2)
- `fatigue.readiness_decision(..., freshness=None)`, `race_hub_service.race_briefing(hub, tsb, freshness=None)`: `freshness`가 주어지고 `assertive=False`면 "컨디션" 근거 단정 문구 대신 유보형 변형을 고르고 evidence에 `{"type":"freshness", ...}` 항목을 붙인다. 기본값 `None`이면 현재 동작 그대로(호출부 점진 이관).
- `today_service.get_today_briefing`은 UTRS 신선도를 한 번 계산해 두 함수에 전달만 한다(+3줄).
- 동기화 caveat(`source_missing`)는 원장 기반 "소스가 끊김" 신호로 그대로 둔다. 화면 병합은 D5((b) freshness 하나로 병합).

### 2.4 프론트(v2)
- `ReadinessGauge`, 지표 목록 카드, `[slug]` 상세, `TodayHero`가 `freshness.level`/`reasons`로 배지·유보 표시를 렌더. 표시는 D3(값 유지 + 등급 라벨 회색/유보), 문구는 D4(`freshness.ts` 문구 사전, §2.6-B).

### 2.5 FRS-8 확장: `crs`·`rmr`·`rtti` — Calculator confidence 기록 + 메트릭별 SPEC

**코드 확인 결과(입력).** 세 Calculator 모두 CalcContext API만 사용한다(`get_wellness()`는 `daily_wellness WHERE date = scope_id` **당일 정확 일치**, `get_metric()`은 같은 날 `metric_store`). 현재 confidence는 `rmr` 미기록(None), `rtti`·`crs` 1.0 하드코딩 — metric-conventions 규칙 3(ConfidenceBuilder로 설정) 위반. UTRS는 `ConfidenceBuilder.add_input(k, is_available=k in components, weight=w)` 패턴.

**Calculator confidence 기록(FRS-11 (c)).** 세 Calculator 모두 이미 조회한 값의 None 여부만으로 `ConfidenceBuilder`를 채운다 — 추가 조회·raw SQL 없음(ADR-009), 값·등급·반환 조건 불변(빈 리스트 규칙 그대로: `rmr` 성분 0개, `rtti` ATL/CTL 없음·이력 부족 시 `[]`).

| Calculator (1.0→1.1) | 입력 → `add_input` 가중치 | 대표 결과(confidence / `confidence_label`) | json 추가 |
|---|---|---|---|
| `rmr` | resting_hr 0.25, body_battery 0.25, sleep 0.25, tsb 0.25 (점수 가중치와 동일, `is_available = k in components`) | 전부 1.0 높음 / TSB 단독 0.25 낮음 / 웰니스 1개+TSB 0.5 보통 | 없음(`components` 기존) |
| `rtti` | atl 0.3, ctl 0.3, body_battery_high 0.2, sleep_score 0.2 | 전부 1.0 / 웰니스 1개 0.8 / 웰니스 0개 0.6 보통(값 자체는 유효 → partial은 coverage 아닌 "보정 미적용" 규칙으로) | `wellness_used: [...]` (1.0이 "정상"인지 "결측"인지 구분) |
| `crs` | acwr 0.2, hrv_weekly_avg 0.2, body_battery_high 0.15, tsb 0.15, cirs 0.15, utrs 0.15 (게이트 5 + 점수 base). hrv_today는 있으나 7일 rolling 없음 → `is_estimated=True` | 전부 1.0 / BB·HRV 결측 0.65 보통 / 웰니스·UTRS 결측 0.5 | 없음(`signals` null로 식별) |

- `crs`는 입력이 전부 None이어도 현재 행(base 60)을 만든다. 이번엔 반환 조건을 바꾸지 않고 confidence 0.0으로 기록만 한다(빈 리스트 전환은 값 정의 변경이라 범위 밖, §8).
- upstream(UTRS) confidence는 CRS confidence에 곱하지 않는다(`get_metric`은 값만 반환, API 확장 회피). 전이는 읽기 시점 `upstream` 규칙이 맡는다.

**SPEC 형식(FRS-9 (c)·FRS-10 (b) 반영).**
```python
FRESHNESS_SPEC = {
  "utrs": {"wellness": ["body_battery_high","sleep_score","hrv_weekly_avg","avg_stress"],
           "metrics": ["tsb"], "wellness_role": "component"},
  "rmr":  {"wellness": ["resting_hr","body_battery_high","sleep_score"],
           "metrics": ["tsb"], "wellness_role": "component", "min_version": "1.1"},
  "rtti": {"wellness": ["body_battery_high","sleep_score"],
           "metrics": ["atl","ctl"], "wellness_role": "modifier", "min_version": "1.1"},
  "crs":  {"wellness": ["body_battery_high","hrv_weekly_avg"],
           "metrics": ["acwr","tsb","cirs"], "upstream": ["utrs"],
           "wellness_role": "gate", "min_version": "1.1"},
}
```
- coverage 모드(`row_confidence`/`wellness_present_ratio`)는 **제거** — 모든 메트릭이 `row.confidence`를 쓴다.
- `min_version`: 행 `algorithm_version`이 미달(재계산 전 1.0 행)이면 저장 confidence를 신뢰하지 않고 `coverage=None`, reasons `coverage_unknown` → partial은 "웰니스 성분 0개" 규칙만 적용. 재계산 중단으로 1.0/1.1이 섞여도 1.0 하드코딩값이 "충분"으로 읽히지 않게 하는 안전장치.
- `wellness_role`: `component`(UTRS 규칙), `modifier`(FRS-10 (b): 웰니스 경과일로 stale 판정 안 함, 당일 `wellness_used` 비면 partial + reasons `modifier_missing`("보정 미적용")), `gate`(결측 게이트가 "통과"로 낙관 판정된 것을 reasons `gate_unknown`).
- `upstream`: 상위 메트릭 freshness를 먼저 산출해 **나쁜 쪽(missing>stale>partial>fresh)**을 취하고 reasons `{code:"upstream", metric:"utrs"}`. 사이클 없음(SPEC 로드 시 assert). UTRS 웰니스 조회는 `assess_many` 공유 조회에 포함(추가 쿼리 0).
- `metrics` 입력(FRS-9 (c)): 같은 날 행 존재만 본다(`metric_store` 1쿼리, `scope_id = value_date AND metric_name IN (...)`). 없으면 reasons `metric_missing`(partial). 경과일은 판정하지 않는다(CTL/ATL은 무활동일도 감쇠로 정상 산출).
- 결측 성분명은 행에서 읽는다: `utrs`·`rmr` `components` 키, `rtti` `wellness_used`, `crs` `signals`의 null. 입력 재구성 쿼리 불필요.

**메트릭별 판정 요약(D1=2일, D2=성분 0개 또는 confidence<0.5).**

| 메트릭 | stale | partial | 비고 |
|---|---|---|---|
| `utrs` | 웰니스 필드 최신일 ≤ basis−2, 또는 value_age ≥ 2 | 웰니스 성분 0개, 또는 confidence < 0.5 | 기존 §2.1 |
| `rmr` | 동일(웰니스 3필드) | 웰니스 성분 0개, 또는 confidence < 0.5(TSB 단독 0.25) | "TSB 단독 점수" 문제가 저장 confidence로 드러남 |
| `rtti` | value_age ≥ 2만 | `wellness_used` 빈 목록(`modifier_missing`) | confidence 0.6이라 coverage로는 partial 안 됨 — 의도 |
| `crs` | 자기 웰니스 stale 또는 upstream `utrs` stale | BB·HRV 모두 결측, confidence < 0.5, upstream partial, metric 입력 결측 | 결측 게이트는 `gate_unknown` |

**적용 화면.**
- `/library/metrics` 목록: `crs`·`rmr`·`rtti` entry에 `freshness`, `salience.fresh`(FRS-6). FRS-3에 따라 값 유지 + 등급 라벨 회색/유보. `crs` `action_hint`(`metric_display.action_hint`)는 단정형이므로 `assertive=False`면 유보형/생략(+3줄). `confidence_label`(0.7/0.4 경계)이 재계산 후 과거·현재 모두 실측 기준으로 바뀐다(웰니스 결측일 `rtti`·`crs` "높음"→"보통", `rmr` None→"낮음" 등).
- `/library/metrics/<slug>` 상세: trend에 `current_date`·`freshness`, 결측 성분 표시. `crs` 게이트 목록은 `gate_unknown` 게이트를 "데이터 없음"으로 구분.
- `/today`: 게이지는 utrs/cirs/tsb라 변경 없음. `get_today_status`의 `readiness.crs`에 `freshness` 첨부. `rmr`·`rtti`는 library만.
- 추세 차트: 1.1 항목은 `value_changed=False`라 ◆를 만들지 않는다(§2.6-C, D14). 재계산 캡션 폴백(`recompute_note`)은 `algo_recompute` 마일스톤 기준인데 `recompute_all`이 행을 지운 뒤 재삽입하므로 마일스톤이 남는지 구현 시 확인.
- 결측 성분 표시는 목록 공통 문구·상세 성분명(§2.6-B, D13). CRS 행동 경로는 §2.6-A(D12).

### 2.6 FRS-12~17 결정 반영

**A. BOOST 보류(D12 (c')) — 코드 확인 결과.** 강도 상향이 나가는 지점은 둘이고, 하향 경로와 코드상 분리돼 있다.
- (A1) CRS 행 `json.level == 4`("볼륨 +5%") → `metric_display.action_hint`(library `crs` 카드·상세, `/today` `readiness.crs`). UTRS가 TSB 단독 85 → `crs_score ≥ 80`, BB·HRV 게이트 결측 "통과", TSB>5 → BOOST가 되는 것이 RC-1의 행동판.
- (A2) `adjuster.adjust_todays_plan`의 `volume_boost`(TSB>10·당일 BB>70, CRS 무관) → `today_hero` `verdict="up"`, `plan.py` CLI. `plan_adjustments`에는 저장되지 않는다(`ensure_proposal`은 `adjusted=True` 하향만 저장). **D15 (b) 결정: A1·A2 모두 보류.**
- `adjust_todays_plan` 호출부 전수와 v2 호출부의 래퍼 이관은 §2.7(D18 (c) 결정). `plan.py`(CLI)는 미수정.
- `plan_adjustment_service`의 `source='crs'`는 이름과 달리 `readiness_decision`(피로도) 기반 하향만 만든다. `replanner`·`matcher_context`는 존재하지 않는 `crs.evaluate` import로 예외가 삼켜진다 — (c')의 영향 없음(§8, `evaluate()` 복원으로 결정 — BACKLOG).
- **게이트 불명 판정에 새 저장값 불필요**: CRS 행 `signals.body_battery`·`signals.hrv_today`가 null이면 해당 게이트가 "(통과)"로 낙관 판정된 것(1.0 행에도 존재 → `min_version` 무관). confidence(BB·HRV 결측 0.65)는 보조 지표로만 쓰고 판정 키로 쓰지 않는다(가중치 변경에 취약).
- **판정·해제 조건(D17 (a) 결정)**: `metric_freshness.boost_hold(fr) -> {hold, reasons}` 순수 함수. 해제는 CRS `level == "fresh"` **이고** `signals.body_battery`·`signals.hrv_today` 모두 당일 non-null **이고 HRV 7일 rolling이 형성**(`is_estimated` 아님 — 행에서 식별할 키는 구현 시 확인, 없으면 crs 1.1 json에 `hrv_rolling: bool` 추가)일 때만. 그 외(stale·partial·missing, CRS 행 없음, `gate_unknown` 하나라도) → hold. reasons는 `[{code:"crs_stale"|"crs_missing"|"gate_unknown", gates:[...]}]`(사유 문구 원천). `crs_boost_hold(conn, date)`는 crs 행 1건 조회 + `assess` + `boost_hold`(서비스 계층, ADR-009). Calculator·저장 level 불변(1.2 없음).
- **적용(D15 (b) 결정)**: A1 — `action_hint(..., boost_hold=None)`: `level==4`이고 hold면 level 3 문구 + 사유 한 줄, level 0~3은 무시. A2 — `adjust_todays_plan(..., boost_hold=None)`: adjuster는 **이미 계산된 `{hold, reasons}` dict를 인자로만 받는다**(training → services import 없음, 계층 역전 없음). 원래 상향 조건(TSB>10·BB>70)이 참**이고** hold일 때만 `volume_boost=False`, `boost_held=True`, `boost_hold_reasons` 추가(상향 조건이 거짓인 날은 사유를 만들지 않음 — 매일 "보류" 노이즈 방지). hold가 아니거나 `None`이면 **키 추가 없이** 현행 dict 그대로(회귀 비교가 dict 동등성으로 가능). 하향 분기(`fatigue` high/moderate)는 이 인자를 읽지 않는다.
- **사유 표시(D16 (b)·D19 (a) 결정)**: `today_hero`는 `boost_held`면 `verdict`를 기본값 `"as_planned"`로 두고 `adjustment = {"reason": None, "from": t, "to": t, "hold_reason": boost_hold_reasons}`(t = `_label(adjusted_type)`, 하향과 상호배타 — `adjusted`가 우선)를 싣는다. 신규 verdict 값 없음. 문구는 `boost_hold.reasons`에서 프론트 `freshness.ts`의 `boostHoldCaption(reasons)`가 생성(FRS-4 확정: "HRV·바디배터리 데이터가 없어 강도 상향은 보류했어요", 화면 확인 후 미세 조정). library `crs` 카드·상세의 level 4 보류도 같은 함수.
- **rule_version(ADR-035)**: `RULE_VERSION` `adjuster_v1`→`adjuster_v2`. (b)로 제안 생성 함수 자체(`adjust_todays_plan` 분기)가 바뀌므로 상향 실효가 가장 크다. 저장 행은 하향뿐이라 같은 입력에서 v1/v2의 `after`·`reasons`는 동일 — 마이그레이션 없음, `ensure_proposal` UPDATE는 내용이 다를 때만 실행되므로 기존 `proposed` v1 행은 rev 불변. `pain_v1` 불변.

**B. 결측 성분 문구(D13 (c)).** `assess`가 정규화 키를 내보낸다: `missing_inputs: [...]`(utrs·rmr `components` 키, rtti `wellness_used` 여집합 → SPEC 웰니스 필드명으로 정규화), crs는 `unknown_gates: ["body_battery","hrv"]`. `frontend/src/lib/freshness.ts`:
- `INPUT_LABELS`(필드→성분명: `body_battery_high` 바디배터리, `sleep_score` 수면, `hrv_weekly_avg` HRV, `avg_stress` 스트레스, `resting_hr` 안정 심박, `tsb`·`atl`·`ctl` 훈련 부하, `acwr`·`cirs`·`utrs` 지표명) + 메트릭별 템플릿(`component`: "{성분} 없이 계산", `modifier`(rtti): "{성분} 보정 미적용", `gate`(crs): "{게이트} 게이트 데이터 없음").
- `listCaption(fr)` = 결측이 있으면 공통 "일부 데이터 없이 계산", `detailCaption(metric, fr)` = 템플릿 적용. 사전에 없는 키는 공통 문구로 폴백.
- **문구 사전(D4 = FRS-4 확정, 화면 확인 후 미세 조정)**: `BADGE_TEXT = {stale: "입력이 오래됐어요", partial: "일부 데이터 없이 계산"}`, `HOLD_HEADLINE = "최근 데이터가 부족해 참고용이에요"`(유보형 헤드라인), `basisCaption(d)` = "MM-DD 기록 기준", `BOOST_HOLD_TEXT = "HRV·바디배터리 데이터가 없어 강도 상향은 보류했어요"`(`boostHoldCaption`).

**C. ◆ 생략(D14 (b)).** `AlgoChange`에 `value_changed: bool = True`(마지막 필드, 기본값으로 기존 항목 무수정). `rmr`·`rtti`·`crs` 1.1은 `value_changed=False`. `metrics_changelog_events`: `changelog_events`의 hits 필터에 `c.value_changed` 추가(상위 지표 전파 ◆도 함께 사라짐), `version_events`는 `(calculator, to)`가 `value_changed=False` 항목과 일치하는 data 불연속 이벤트를 제거(재계산 중단 시 1.0/1.1 혼재 ◆ 방지; 현 `versions` dict는 버전 문자열만 키라 계산기 간 충돌 — 같이 수정). `recompute_caption`은 logged가 비면 기존 폴백.

### 2.7 FRS-18 (c) 래퍼 `todays_adjustment_with_hold` — 결정됨(2026-10-11)

**호출부 전수(grep `adjust_todays_plan|volume_boost`, 2026-10-11 기준).** 현재 `boost_hold`를 넘기는 곳은 없다(인자 자체가 미구현).

| 파일:줄 | 구분 | 이관 후 hold | 반환값 사용처 |
|---|---|---|---|
| `services/plan_service.py:145` `get_todays_adjustment` | v2 API(`routes_plan.py:42`) | 래퍼 | dict 전체 JSON → 프론트 플랜 타입 `volume_boost`(렌더 없음) |
| `services/plan_service.py:177` `get_session_detail` | v2 API(`routes_plan.py:107`) | 래퍼 | `adjustment` 전체 → `SessionAdjustment.volume_boost`(렌더 없음) |
| `services/coach_evidence.py:152` `_candidates` | v2 Coach 근거 | 래퍼 | `adjusted`·타입·거리 → plan 근거 label(`volume_boost` 미사용) |
| `ai/chat_readiness.py:22` `attach_readiness`(← `ai_context_legacy:108`) | AI | 래퍼 | `ctx["plan_adjustment"]` → `plan_line`(`adjusted`만). ctx 전체의 프롬프트 직렬화 여부는 구현 시 확인 |
| `ai/coach_rule_handlers.py:49` `_session_line` | AI 규칙 | 래퍼(`config` 위치인자 제거) | `adjusted`·타입 → 문장(`volume_boost` 미사용) |
| `services/today_hero.py:143` | v2 Hero | 래퍼(§2.6 직접 전달 대신) | `adjusted`→`"down"`, `volume_boost`→`"up"`, 보류→`hold_reason` |
| `services/plan_adjustment_service.py:98` `ensure_proposal` | v2 제안 저장 | 래퍼(`plan_pain.proposal` 우선 유지) | `adjusted=True` 하향만 저장 — hold 무관, `rule_version` 실효용 |
| `plan.py:117` | CLI | 미수정 | `:136` `volume_boost` 출력 |

→ 현재 실제 불일치는 plan API JSON(필드만, 미렌더)과 AI ctx다. Coach 문장 경로 3곳은 `volume_boost`를 읽지 않으므로 이관만으로는 문구가 변하지 않는다 → **D20 (b)**: `_session_line` 규칙 문장과 `coach_evidence` plan 근거에 `boost_held`면 보류 한 줄(FRS-4 문구) 추가. `plan_line`(AI ctx)은 래퍼 dict의 `boost_held`·reasons 필드만.

**래퍼(서비스 계층, `plan_service.py`).**
```python
def todays_adjustment_with_hold(conn, date: str | None = None, *, hold: dict | None = None) -> dict | None:
    """adjust_todays_plan + BOOST 보류(D12·D15) 단일 진입점. 계획 없으면 None."""
    day = date or _date.today().isoformat()          # adjuster와 같은 기준일로 정규화 → hold와 같은 날
    if hold is None:
        hold = _safe_boost_hold(conn, day)           # metric_freshness.crs_boost_hold 1회
    return adjust_todays_plan(conn, date=day, boost_hold=hold)
```
- 반환: `adjust_todays_plan`과 동일 dict(보류 시에만 `boost_held`·`boost_hold_reasons` 추가, §2.6-A). 계획 없음·완료 → `None`.
- **조회 1회**: CRS 행 조회+`assess`+`boost_hold`는 래퍼 안 `_safe_boost_hold` 한 곳에서만(쿼리 ≤3). 상향 조건을 먼저 보고 지연 조회하는 안은 adjuster 이중 호출 또는 보류 로직 복제가 필요해 기각.
- **중복 방지**: 모듈 전역 캐시는 두지 않는다(동기화 후 stale·conn 수명 문제). 같은 요청에서 CRS freshness를 이미 산출한 호출자(`today_service`의 `readiness.crs`)는 `hold=boost_hold(fr)`로 넘겨 추가 쿼리 0.
- **에러·데이터 부족**: CRS 행 없음·stale은 `crs_boost_hold`가 hold로 판정(D17 a). `crs_boost_hold` 예외는 `log.warning` 후 `{"hold": True, "reasons": [{"code": "crs_missing"}]}`(불명 → 보류, D17과 같은 방향) — 래퍼가 새 예외를 만들지 않는다. `adjust_todays_plan` 자체의 예외는 **현행대로 전파**(호출부별 기존 처리 유지: plan_service 미처리, Coach·AI 3곳 try/except) — 회귀 불변 우선.
- **계층**: `ai/`→`services/`는 기존 방향(`coach_rule_plan_handlers`→`plan_service`, `chat_engine`·`ai_context` 등). `services/`→`ai/`는 `ai_cache`·provider 인프라뿐이라 역전 아님. ai 2곳은 기존 관례대로 함수 내 지연 import. `today_hero`는 이미 `plan_service`를 지연 import. `plan_service`는 `plan_adjustment_service`·`coach_evidence`를 import하지 않아 순환 없음(구현 시 import 목록 재확인).
- **직접 호출 차단**: adjuster 기본값 `boost_hold=None`이 현행이다. 가드 테스트 `tests/test_adjuster_callers.py`: `src/`에서 `adjust_todays_plan(` 직접 호출은 `adjuster.py`·`plan_service.py`(래퍼)·`plan.py`만 허용(정규식 스캔).

**FRS-19 (a) 전달 경로.** adjuster `boost_hold_reasons` → 래퍼 → `today_hero`: `elif adj.get("boost_held")`면 verdict `"as_planned"` 유지 + `adjustment.hold_reason` → `/api/v1/today` → 프론트 `todayHero.ts`가 `view.adjustment` 생성 시 `hold_reason`이 있으면 `boostHoldCaption(hold_reason)`, 없으면 기존 "from → to" 문자열. **D21 (b)**: `view.adjustment`에 종류 필드 `kind: "down" | "hold"`를 넘기고 `TodayHero.svelte`는 `hold`면 중립(회색) 한 줄, `down`이면 기존 amber 박스(+5줄). 타입은 **필드 추가만**: `BriefingStateFields.adjustment`에 `hold_reason?: BoostHoldReason[]`, 플랜 응답 2타입(`volume_boost` 보유)에 `boost_held?: boolean`·`boost_hold_reasons?: BoostHoldReason[]`. verdict 유니언 불변.

**이관 순서(1호출부 = 1커밋, 각 단계 대상 테스트 통과 후 다음).** 선행: §4 5-1의 adjuster `boost_hold` 인자(None 현행)·`crs_boost_hold`.
1. 래퍼 추가(호출자 없음) + `test_plan_service` 4개: hold 주입·`hold=` 전달 시 crs 미조회·crs 예외 → hold·계획 없음 → None.
2. `plan_service` 145·177 → 래퍼. `test_plan_service`·`test_api_plan*`.
3. `coach_evidence:152` → 래퍼 + `boost_held`면 plan 근거에 보류 한 줄(D20 b). `test_coach_evidence`(+1).
4. `ai/chat_readiness:22` → 래퍼. `test_chat_readiness`(없으면 `test_ai_context*`).
5. `ai/coach_rule_handlers:49` → 래퍼 + `_session_line` 보류 한 줄(D20 b). `test_coach_rule*`(+2: 보류 한 줄·비보류 문장 불변).
6. `plan_adjustment_service:98` → 래퍼 + `RULE_VERSION` v2. `test_plan_adjustment_service`·`test_api_plan_adjustments`.
7. `today_hero:143` → 래퍼 + `hold_reason`(FRS-19) + 프론트 타입·`todayHero.ts` 종류 필드·`TodayHero.svelte` 회색 분기(D21 b). `test_today_hero`, `npm run check`.
8. 가드 테스트 + 일관성 테스트 `tests/test_boost_hold_consistency.py`: **보류일 픽스처**(TSB>10·BB>70·HRV null) → `get_todays_adjustment`·`get_session_detail.adjustment`·`attach_readiness` ctx 모두 `volume_boost=False`·`boost_hold_reasons` 존재, `coach_evidence`·`_session_line`은 래퍼 경유(spy)·보류 한 줄 포함(D20 b), Hero `as_planned`+`hold_reason`. **비보류 픽스처**(웰니스·CRS fresh) → 4곳 출력이 `adjust_todays_plan(conn, date=d)` 직접 결과와 dict 동등, Coach 문장 동일(회귀). ~8개.

## 3. 변경 파일 표

| 구분 | 파일 | 내용 | 예상 줄 |
|---|---|---|---|
| 수정 | `src/metrics/rmr.py` | `ConfidenceBuilder` 4입력, `version="1.1"` | 66→~73 |
| 수정 | `src/metrics/rtti.py` | `ConfidenceBuilder` 4입력, `wellness_used`, `version="1.1"` | 78→~90 |
| 수정 | `src/metrics/crs.py` | `ConfidenceBuilder` 6입력(HRV rolling 없으면 estimated), `version="1.1"` | 206→~216 |
| 수정 | `src/metrics/algo_changelog.py` | `value_changed: bool = True` 필드, `AlgoChange("rmr"/"rtti"/"crs", "1.1", <반영일>, "신뢰도를 실제 입력 데이터 기준으로 기록해요(값은 그대로예요)", "1.0", value_changed=False)` 3항목 | +4 |
| 수정 | `src/services/metrics_changelog_events.py` | hits `value_changed` 필터, `version_events` 무변경 버전 data 이벤트 제거·`(calculator, version)` 키 | +5 |
| 신규 | `src/services/metric_freshness.py` | `assess`/`assess_many`, 웰니스 필드별 최신일·metric 입력 존재 조회, role별 규칙, `min_version` 가드, upstream 전이, `missing_inputs`·`unknown_gates`, `boost_hold`·`crs_boost_hold` | ~170 |
| 수정 | `src/training/adjuster.py` | `boost_hold: dict | None = None` 인자 주입 → hold면 `volume_boost=False`·`boost_held`·`boost_hold_reasons`(D15 b) | +5 |
| 수정 | `src/services/plan_service.py` | `todays_adjustment_with_hold`·`_safe_boost_hold`(D18 c), 145·177 이관 | 214→~238 |
| 수정 | `src/services/plan_adjustment_service.py` | `RULE_VERSION="adjuster_v2"`, 98행 래퍼 경유 | +2 |
| 수정 | `src/services/today_hero.py` | 143행 래퍼 경유(`today_service`가 `hold=` 전달 가능), `boost_held`면 verdict `as_planned`+`adjustment.hold_reason`(D16 b·D19 a) | 203→~210 |
| 수정 | `src/services/coach_evidence.py`, `src/ai/coach_rule_handlers.py` | 래퍼 교체(지연 import) + `boost_held`면 plan 근거·`_session_line`에 보류 한 줄(D20 b, FRS-4 문구) | 각 +4~6(216→~222) |
| 수정 | `src/ai/chat_readiness.py` | 래퍼 교체만(ctx에 `boost_held`·reasons 필드) | ±2 |
| 신규 | `src/services/metric_freshness_spec.py` | `FRESHNESS_SPEC`, level 우선순위, 임계값, upstream 사이클 assert | ~50 |
| 신규 | `src/services/metrics_trend_service.py` | `get_metric_trend`·`_race_events` 이동(+freshness). `metrics_browser_service.py` 298줄이라 분리 | ~100 |
| 수정 | `src/services/metrics_browser_service.py` | trend 제거(−75), entry에 freshness(+8), crs `action_hint` 유보(+3), 하위호환 re-export | 298→~238 |
| 수정 | `src/services/today_service.py` | `readiness.crs` freshness 첨부 + 브리핑 신선도 전달(이미 320줄, 순증 최소화) | +6 |
| 수정 | `src/services/metric_display.py` | `action_hint(..., assertive=True, boost_hold=False)` — level 4 보류 시 level 3 문구 | +6 |
| 수정 | `src/api/routes_library.py` | trend 호출 경로 변경 | ±2 |
| 수정 | `src/services/today_readiness.py` | confidence·freshness 첨부 | +12 |
| 수정 | `src/training/fatigue.py`, `src/services/race_hub_service.py` | `freshness` 인자, 유보형 분기 | +12, +10 |
| 수정 | `frontend/src/lib/types/index.ts` | `Freshness`·`BoostHoldReason` 타입, 응답 타입 확장, `adjustment.hold_reason?`·플랜 2타입 `boost_held?`·`boost_hold_reasons?`(추가만, verdict 유니언 불변) | +26 |
| 수정 | `frontend/src/lib/todayHero.ts` | `hold_reason` 있으면 `boostHoldCaption`, 없으면 기존 문자열 + 종류 필드 `kind: "down"\|"hold"`(D21 b) | +6 |
| 수정 | `ReadinessGauge.svelte`, `TodayHero.svelte`, `routes/library/metrics/+page.svelte`(291줄), `[slug]/+page.svelte` | 배지·유보 표시(목록은 카드 컴포넌트 분리 검토), `TodayHero`는 `kind=="hold"` 중립(회색) 한 줄 분기(D21 b, +5) | 각 +5~15 |
| 신규 | `frontend/src/lib/freshness.ts` | level→표시 매핑, `INPUT_LABELS`·role별 템플릿, `listCaption`/`detailCaption`·`boostHoldCaption`, FRS-4 문구 사전(§2.6-B) | ~60 |
| 신규/수정 | `tests/test_rmr.py`(신규), `tests/test_rtti.py`, `tests/test_crs.py` | 위 표의 confidence 값(전부/TSB 단독/웰니스 0개/HRV estimated/전부 None=0.0), `wellness_used`, 값·level 불변 회귀, 데이터 부족 `[]` 유지 | 각 +3~4개 |
| 수정 | `tests/test_algo_changelog.py` | 기존 누락·버전·prev 체인 검사 유지 + `value_changed=False`면 `prev` 필수 1개 | +1개 |
| 수정 | `tests/test_metrics_changelog_events.py` | 무변경 항목 ◆·전파 ◆ 없음, 혼재 data 이벤트 제거, `value_changed=True` 회귀 | +3개 |
| 수정 | `tests/test_adjuster.py`, `tests/test_plan_adjustment_service.py`, `tests/test_today_hero.py` | D15 (b) 신규 +3: ① hold면 `volume_boost=False`·`boost_held`·reasons ② **하향 불변** — 같은 입력에서 hold 유무와 무관하게 fatigue high/moderate `adjusted_type`·reasons 동일 ③ `boost_hold=None` 현행 회귀. 그 외 신규 제안 `adjuster_v2`·기존 v1 `proposed` rev 불변, Hero `"down"` 불변·`"up"`만 `"as_planned"`+`hold_reason` | 각 +2~3개 |
| 신규/수정 | `tests/test_plan_service.py`(+4), `tests/test_boost_hold_consistency.py`(~8), `tests/test_adjuster_callers.py`(1) | §2.7 래퍼 단위·호출부 4곳+Hero 보류일 일관성·비보류 dict 동등 회귀·직접 호출 가드 | ~13개 |
| 수정 | `tests/test_coach_evidence.py`(+1), `tests/test_coach_rule*`(+2) | D20 (b) 보류 한 줄·비보류 문장 불변 회귀 | +3개 |
| 신규 | `tests/test_metric_freshness.py` | fresh/partial/stale/missing, 웰니스 원값, 공유 조회, rmr confidence<0.5, rtti modifier(웰니스 14일 결측 → partial만), crs upstream·`gate_unknown`, metric 입력 결측(경과일 무시), `min_version` 미달 → `coverage_unknown`, 쿼리 수 2 고정, `missing_inputs` 정규화, `boost_hold`(D17 a: stale·partial·CRS 행 없음·BB만 null·HRV만 null → hold, fresh+BB·HRV 당일 → 해제, `hrv_today`만 있고 rolling 미형성 → hold, 1.0 행 signals로 판정) | ~29개 |
| 신규 | `tests/test_metric_freshness_spec.py` | SPEC ⊆ Calculator `requires`·`daily_wellness` 컬럼, `min_version` == 각 Calculator `version`, upstream 사이클 없음 | ~5개 |
| 수정 | `test_today_hero.py`, `test_fatigue.py`, `test_race_hub_service.py`, `test_metrics_browser_service.py`, `test_api_library.py`, `test_today_service.py`, `test_metric_display.py`(없으면 신규) | 추가 필드·유보 분기·`freshness=None` 회귀, crs/rmr/rtti entry·상세, `action_hint` assertive·level 4 보류/level 0~3 불변 | 각 +2~5개 |
| 신규 | `frontend/tests/freshness.test.mjs` | 매핑·배지 조건, FRS-4 문구, 목록 공통/상세 성분명·미등록 키 폴백, `todayHero` `kind` 분기(D21 b) | ~11개 |
| 문서 | `v0.3/data/decisions.md`, `v0.3/data/metric_dictionary.md`(`gen_metric_dictionary.py` 재생성) | ADR-048(신선도·BOOST 보류·`value_changed`), 버전 1.1 반영 | — |

## 4. 적용 순서와 검증 (단계적 롤아웃: 코드 배포 → 재계산 → 신선도 판정 활성)

1. **Calculator 1.1(배포 1)**: `value_changed` 필드·이벤트 필터를 먼저(동작 불변 커밋), 이어 세 Calculator + `algo_changelog` 3항목(`value_changed=False`). `pytest tests/test_rmr.py tests/test_rtti.py tests/test_crs.py tests/test_algo_changelog.py tests/test_metrics_changelog_events.py`, `gen_metric_dictionary.py`. 재계산 전 1.0/1.1 혼재 구간에도 ◆는 나오지 않는다(§2.6-C) — 그래도 배포 직후 2단계를 바로 수행.
2. **전체 재계산**: 운영 전 `running.db` 백업(파일 복사) → `POST /api/v1/data/recompute {"scope":"all","reason":"algo_confidence_1_1"}` → `recompute_service.start` → `engine.recompute_all(days=None)`(가장 이른 활동일부터 전 메트릭 삭제·재실행, 세 메트릭만이 아님 — 비용은 기존 전체 재계산과 동일). `scope:"90d"`는 금지(90일 밖이 1.0으로 남아 불연속·`coverage_unknown` 지속). 진행은 `GET /api/v1/data/jobs/<id>`. 완료 검증: `SELECT metric_name, algorithm_version, COUNT(*), MIN(confidence), MAX(confidence) FROM metric_store WHERE metric_name IN ('rmr','rtti','crs') GROUP BY 1,2` → 1.1만, confidence NULL 없음, `rtti`·`crs` 1.0 고정 해소. 값(`numeric_value`)은 재계산 전후 동일해야 함(before/after 표본 비교).
   - **실패/중단 복구**: 작업은 `status=failed, error_code=RECOMPUTE_FAILED`로 남는다. `engine`은 날짜 구간마다 commit하므로 1.0/1.1 혼재 상태가 될 수 있다 → 같은 요청을 다시 실행(삭제 후 재실행이라 멱등, 진행 중이면 `RECOMPUTE_RUNNING`). 반복 실패 시 백업으로 복원 후 원인 수정. 혼재 기간에도 `min_version` 가드로 1.0 행의 confidence는 판정에 쓰이지 않는다.
3. **판정 모듈(배포 2, 신선도 활성)**: `metric_freshness_spec.py`·`metric_freshness.py` + 단위 테스트. 픽스처: "웰니스 마지막 09-27, 10-11 UTRS=85 conf=0.25 components={tsb}" → `stale`+`low_coverage`, `assertive=False`; 같은 날 웰니스가 있으면 `fresh`. FRS-8: `rmr` components={tsb}, conf 0.25 → `stale`+`low_coverage`; `rtti` 웰니스 결측·ATL/CTL 당일 존재·conf 0.6 → `partial`(`modifier_missing`, stale 아님); `crs` BB·HRV 결측 + upstream UTRS stale → `stale`, reasons `upstream`·`gate_unknown`; 1.0 행 → `coverage_unknown`; 웰니스 당일 존재 시 4개 모두 `fresh`. `assess_many(['utrs','crs','rmr','rtti'])` 쿼리 수 2 고정. `boost_hold`: 위 crs 픽스처 → hold, BB만 null·HRV만 null·rolling 미형성·CRS 행 없음 → hold, fresh+BB·HRV 당일 → 해제(D17 a).
4. **Today API**: `build_readiness`·`readiness.crs` 첨부. `test_today_hero` + API 테스트.
5. **판정 문구**: `readiness_decision`·`race_briefing` 인자. `freshness=None` 회귀, `assertive=False` 분기, `coach_evidence` 영향 테스트 1개.
5-1. **BOOST 보류(D12·D15 b·D16 b·D17 a·D20 b·D21 b, `adjuster_v2`)**: 테스트 먼저(하향·휴식 결과가 hold 유무와 무관하게 동일함을 고정, adjuster +3) → `adjust_todays_plan(boost_hold=None)` 인자 주입(None 현행, 동작 불변 커밋) → `action_hint` level 4 보류+사유 → §2.7 이관 1~8단계(래퍼 → plan_service → coach_evidence → AI 2곳 → `ensure_proposal`+`RULE_VERSION` → Hero `as_planned`+`hold_reason` → 가드·일관성 테스트). `pytest tests/test_adjuster.py tests/test_plan_service.py tests/test_plan_adjustment_service.py tests/test_api_plan_adjustments.py tests/test_today_hero.py tests/test_boost_hold_consistency.py tests/test_adjuster_callers.py tests/test_coach_evidence.py tests/test_replanner.py`(replanner는 무변경 회귀). 배포 후 `SELECT rule_version, COUNT(*) FROM plan_adjustments WHERE source='crs' GROUP BY 1`로 신규 행 v2 확인.
6. **Library API**: trend 분리 이동(동작 불변 커밋 먼저) → freshness 추가 → crs `action_hint` 유보. `test_metrics_browser_service`, `test_api_library`.
7. **프론트**: 타입·매핑·컴포넌트. `frontend/tests/*.test.mjs`, `npm run check`.
8. **브라우저 확인**(로컬 DB 사본·픽스처, 재계산 완료 상태): (a) 웰니스 14일 결측 — `/today` 배지·유보 문구·caveat 병합, `/library/metrics` UTRS·crs·rmr·rtti 카드(라벨 회색/유보, `confidence_label` 변화, action hint 유보), `/library/metrics/utrs`·`/sleep_score`·`/crs`(게이트 '데이터 없음', BOOST 보류 사유)·`/rmr`·`/rtti`(◆ 없음·상세 성분명·목록 공통 문구); `/today` Hero 상향 보류 시 중립(회색) 사유 한 줄·하향 amber 박스 유지(D21 b), Coach 근거 보류 한 줄(D20 b), FRS-4 문구 화면 확인 후 미세 조정; (b) 당일 웰니스 정상 — 배지 없음, BOOST 표시(회귀). `pw/s5_wellness.mjs` 패턴으로 시나리오 1개 추가 검토.
9. 전체 `pytest tests/`, `scripts/check_docs.py`, ADR-048 기록.

## 5. 호환성

- API 변경은 모두 추가 필드라 하위호환. `salience.fresh` 의미 변경(D6)으로 목록 정렬·강조가 달라진다.
- **과거 행 confidence 변경**: 재계산 후 `rmr`·`rtti`·`crs`의 모든 과거 행 confidence가 실측값으로 바뀐다(값·level·text 불변). `confidence`를 읽는 소비처 — library `confidence_label`, `dashboard_service`(v1/today crs), AI 컨텍스트 중 confidence를 싣는 경로 — 의 표시가 낮아질 수 있다. AI 컨텍스트의 confidence 표시는 이 설계에서 수정하지 않지만 저장값 자체가 정확해져 혜택을 받는다.
- `readiness_decision` 헤드라인은 v2 `/today`, `coach_evidence`가 공유 → 유보 문구가 Coach 근거에도 나간다(의도된 일관성).
- 스키마 변경 없음. 재계산은 1회(§4-2), 이후 일상 동기화는 1.1로 계산.
- BOOST 보류는 읽기 시점 판정이라 저장 CRS level·과거 `plan_adjustments` 행은 불변. `rule_version`은 신규·내용 변경 행만 `adjuster_v2`(ADR-035, 기존 v1 행 유지). v2 서비스·Coach·AI 호출부는 래퍼로 Hero와 같은 보류 결과를 받는다(D18 c). `boost_hold=None` 기본값으로 `plan.py`(CLI)만 현행 상향 표시. 보류가 아닌 날은 모든 호출부 출력이 dict 단위로 현행과 같다. Hero verdict 유니언·API 기존 키 불변(D19 a, 필드 추가만).
- **알려진 한계(D17 a)**: HRV 7일 rolling 미형성 사용자(HRV 미지원 기기, 착용 7일 미만, 수면 중 미착용 잦음)와 BB 미지원 기기 사용자는 **장기간·사실상 영구히 BOOST가 나오지 않는다**. 하향·휴식은 정상. 보류 사유 한 줄로 원인은 드러나지만 해제 수단은 없다(수동 해제 (c)는 미채택).
- D20 (b): Coach 규칙 문장·`coach_evidence`는 보류 한 줄을 말하고, LLM ctx는 `boost_held`·reasons 필드만 받는다. CRS level 4를 싣는 AI 컨텍스트 경로는 §8.

## 6. 대안 비교

| | A안: 읽기 시점 판정 + 계산 시점 confidence (추천) | B안: 계산 시점 게이팅 |
|---|---|---|
| 방식 | 값 유지, Calculator는 실측 confidence만 기록, 서비스가 입력 경과일·confidence로 `freshness` 산출 | UTRS 등이 웰니스 전무 또는 coverage 하한 미만이면 `[]` 반환하거나 재정규화를 중립값 대체로 변경 |
| 장점 | 값 정의 불변, 결손 원인 설명 가능, confidence는 AI 등 모든 소비처에 정확 | 잘못된 값 자체가 생기지 않음 |
| 단점 | 버전 1.1·전체 재계산 1회, 서비스 경유 없는 소비처엔 신선도 미반영 | 값 정의 변경·과거 값 변경, 웨어러블 없는 사용자는 영구 공백 |

B안의 재정규화 정책 변경은 지표 정의 문제라 별도 결정(D7, 현행 유지)으로 분리.

## 7. 결정됨(2026-10-11)

decisions-table FRS-1~21과 1:1(D_n = FRS-n).
- **D1** stale 기준 2일. **D2** partial = 웰니스 성분 0개 또는 confidence<0.5. **D3** (b) 값 유지 + 등급 라벨 회색/유보.
- **D4 문구**: 배지 stale "입력이 오래됐어요"/partial "일부 데이터 없이 계산", 유보형 헤드라인 "최근 데이터가 부족해 참고용이에요", 상세 "MM-DD 기록 기준", BOOST 보류 "HRV·바디배터리 데이터가 없어 강도 상향은 보류했어요". 최종은 화면 확인 후 미세 조정(§2.6-B 문구 사전).
- **D5** (b) `source_missing`과 freshness를 freshness 하나로 병합(규칙·문구는 구현 시). **D6** `salience.fresh` = 입력 신선도 기준. **D7** UTRS 재정규화 현행 유지.
- **D8** `crs`·`rmr`·`rtti`도 같은 규칙(§2.5·§3·§4). **D9** (c) 웰니스 입력만 2일, metric 입력은 당일 존재만. **D10** (b) RTTI 웰니스 결측은 partial("보정 미적용")까지, stale은 value_age로만.
- **D11** (c) Calculator 실측 confidence — 1.0→1.1, `algo_changelog` 3항목(ADR-042), 전체 재계산(§4-1~3).
- **D12** (c') CRS stale·게이트 불명이면 BOOST만 보류, 감량·휴식 유지, `adjuster_v2`(§2.6-A). **D13** (c) 목록 공통 문구, 상세만 성분명(§2.6-B). **D14** (b) `value_changed=False`면 ◆ 생략(§2.6-C).
- **D15** (b) A1+A2 모두 보류, adjuster는 `boost_hold` dict 인자 주입. **D16** (b) 한 줄 사유(D4 문구). **D17** (a) BB·HRV(7일 rolling 포함) 당일 확보 + CRS fresh일 때만 해제(§5 알려진 한계).
- **D18** (c) `plan_service.todays_adjustment_with_hold` 단일 진입점, v2 호출부 7곳 1커밋씩 이관, `plan.py` 미수정·가드 테스트(§2.7). **D19** (a) Hero `"as_planned"` + `adjustment.hold_reason`.
- **D20** (b) 규칙 문장(`_session_line`)·`coach_evidence` plan 근거에 보류 한 줄(FRS-4 문구), 테스트 +3, `coach_rule_handlers` 216→~222줄(§2.7 3·5단계).
- **D21** (b) Hero 보류 사유는 중립(회색) 한 줄 — `todayHero.ts` 종류 필드 `kind`, `TodayHero.svelte` 분기 +5줄(§2.7 FRS-19 경로).

## 8. 범위 밖 메모

- `today_service.py`(320줄), `db_helpers.py`(754줄)가 이미 300줄 규칙 초과 — 별도 분리 작업.
- AI·Coach 컨텍스트(`src/ai/context_builders.py`, `chat_context_rich.py`)에 지표 신선도 전달 없음.
- T-03의 "ACWR 0.67(저부하)과 결이 다름"은 지표 간 일관성 문제로 신선도와 별개.
- `get_metric_trend`의 `change_pct`·`peak` 산식 문제(M-03, M-04)는 trend 분리 시 건드리지 않는다.
- `src/metrics/crs.py`의 주석 "NOTE: raw SQL 사용"은 실제 코드(전부 CalcContext)와 맞지 않고 `since` 변수는 미사용 — 1.1 수정 시 함께 정리 가능하나 동작 무관.
- `replanner.py:142`·`matcher_context.py:84`가 존재하지 않는 `src.metrics.crs.evaluate`를 import → 예외 삼킴으로 CRS Q-day 경고 미발생, `planned_workouts` 매칭 스냅샷 `crs_at_session` 항상 NULL. [CRS-EVALUATE-MISSING]: `evaluate()` 복원으로 결정(BACKLOG) — 저장 CRS(·신선도)를 읽는 읽기 전용 함수, FRS-12·15~18과 함께 구현.
- `plan_adjustments.source='crs'`는 실제로 `readiness_decision` 기반 — BACKLOG [ADJUSTMENT-SOURCE-CRS-LABEL] 등록됨.
- `crs`가 입력 전부 None에도 행(base 60)을 만드는 것은 빈 리스트 규칙과 어긋남 — 값 정의 변경이라 별도 백로그 후보(이번엔 confidence 0.0 기록만).

## 동기화 중 발견한 충돌/확인 필요

- FRS-18 결정 문구는 이관 대상을 "plan_service·coach_evidence·AI 2곳"(4곳)으로 적지만 본문 D18·§2.7은 Hero·`ensure_proposal` 포함 7곳. 본문 유지, 표와의 범위 차이 확인 필요.
- CRS-EVALUATE-MISSING `evaluate()` 복원 결정이 §3 변경 파일 표·§4 단계에 없고, §4 5-1은 `test_replanner`를 "무변경 회귀"로 둔다 — 복원 시 재계획 Q-day 경고·`crs_at_session`이 바뀌므로 본 설계 범위 포함 여부와 테스트 기대값 확인 필요.
- FRS-4 BOOST 보류 문구는 BB·HRV 결측(`gate_unknown`) 기준 한 문장뿐 — `crs_stale`·`crs_missing` 사유의 문구는 미정(화면 확인 시 조정 범위로 처리 가능한지 확인).
- 유보형 헤드라인은 서버(`fatigue.readiness_decision`·`race_briefing`), Coach 보류 한 줄은 Python(D20 b)에서 생성되어 FRS-4 문구가 프론트 `freshness.ts`와 백엔드에 이중 정의된다(ADR-020 서버 SSOT 원칙과의 정합 확인 필요).
- FRS-20 (b)의 "규칙 문장"에 `plan_line`(`ai/chat_readiness`)이 포함되는지 불명확 — 본문은 `_session_line`·`coach_evidence`만 문구 추가로 해석.
- (V1-1 동기화) 가드 테스트 허용 목록에서 v1 `views_training_loaders.py`를 뺐으나, 이 v1 파일이 일몰 전까지 `src/`에 남아 `adjust_todays_plan`을 직접 호출하면 가드 테스트가 실패한다 — 스캔 범위·일몰 순서 확인 필요.
- (V1-1 동기화) §5 confidence 소비처의 `dashboard_service`(v1/today crs)가 v1 화면 전용 경로인지(§1 RC-1은 "v2 게이지 경로는 쓰지 않는다"로 서술) 불명 — 문구 유지, v1 전용이면 삭제 대상.
- (V1-1 동기화) §2.7 표의 `ai_context_legacy`(chat_readiness 호출원)를 `non-running-activities.md` §5는 v1 쪽 사본으로 서술 — 레거시 v1 화면 경로인지 AI 공용 경로인지 확인 필요(이관 대상 유지).
