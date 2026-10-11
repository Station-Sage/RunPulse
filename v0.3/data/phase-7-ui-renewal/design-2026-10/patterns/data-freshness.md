# 설계: 데이터 신선도 반영 (지표 판정에 입력 경과일·커버리지 포함)

- 대상 ID: T-03 (`/today` Hero + UTRS 게이지), M-02 (`/library/metrics` UTRS 카드·상세, 수면 계열 상세), FRS-8 확장(`crs`·`rmr`·`rtti` 목록·상세, `/today` 상태의 CRS)
- 상태: 설계 초안 (구현 전, D1~D3·D5~D8 결정됨, D4·D9~D13 결정 필요)
- 변경 이력:
  - 2026-10-11 FRS-8 확장 설계 — `crs`·`rmr`·`rtti` 입력 분석과 메트릭별 SPEC(§2.5), 변경 파일·단계·검증 반영, 결정 D9~D13 추가
- 관련 ADR: ADR-009 (Calculator raw SQL 금지 — 신선도 판정은 서비스 계층에 둠), ADR-020 (등급은 서버 SSOT, 프론트 임계값 없음 — 신선도도 같은 원칙), ADR-044 (동기화 상태는 원장만 진실 — `source_missing` caveat의 출처), ADR-042 (Calculator 버전 변경 시 changelog — B안에만 해당)

## 1. 근본 원인

**RC-1. "신선함"을 지표 행의 날짜로만 판단하고, 입력 데이터의 날짜·완결성은 응답 계약에 없다.**
- UTRS(`src/metrics/utrs.py`)는 가용 성분만으로 `score / total_weight` 재정규화한다. 웰니스가 없는 날도 TSB(가중치 0.25) 하나로 매일 새 행이 생기고, TSB 성분 하나가 점수 100%를 결정한다(`components={"tsb":84.8}` → 85 "매우 좋음"). confidence 0.25는 저장되지만 소비처가 버린다.
- 그래서 기준일 행이 "오늘 값"으로 존재하므로 `metrics_browser_service`의 `salience.fresh=True`, `last_value_date == date`가 되어 목록 카드의 "MM-DD 기준" 표시도 뜨지 않는다. 입력(웰니스 마지막 09-27)과 값의 날짜가 다르다는 정보 자체가 없다.
- `today_readiness.build_readiness`는 `{value, delta_1d, status, provider, version}`만 내보내고 confidence·components를 뺀다(`dashboard_service`는 confidence를 싣지만 v2 게이지 경로는 쓰지 않는다).
- `get_metric_trend`는 `points[-1]`을 `current`로 쓰고 오늘과의 거리를 내보내지 않는다. 웰니스 원값(수면 등)은 14일 전 값이 "현재"로 표시된다.

**RC-2. 판정(등급·헤드라인)과 결손 경고가 서로 다른 채널이라, 경고가 판정을 바꾸지 못한다.**
- 결손 경고는 동기화 원장 기반 `sync_state_service`의 `caveats[source_missing]`(provider 단위)로만 `briefing_state.caveats`에 실린다.
- 등급·문구 생성기 `bands.grade`, `fatigue.readiness_decision`, `race_hub_service.race_briefing`은 입력 신선도를 인자로 받지 않는다. 결과적으로 "컨디션 여유가 있어 핵심 세션을 소화하기 좋습니다"(TSB만으로 판정)라는 단정 문구와 "데이터가 14일째 들어오지 않아..." 꼬리 경고가 동시에 나간다.

## 2. 설계안 (추천: A안 — 읽기 시점 서비스 판정)

### 2.1 신선도 판정 모듈 — `src/services/metric_freshness.py` (신규)
- 메트릭별 입력 출처 선언(상수, SSOT): `FRESHNESS_SPEC = {"utrs": {"wellness": ["body_battery_high","sleep_score","hrv_weekly_avg","avg_stress"], "metrics": ["tsb"]}, ...}`. 웰니스 원값 메트릭(`MetricDef.storage == "wellness"`)은 자기 컬럼이 곧 입력이므로 자동 처리. 적용: `utrs` + 웰니스 원값 + `crs`·`rmr`·`rtti`(FRS-8, 메트릭별 SPEC은 §2.5). SPEC 상수는 `src/services/metric_freshness_spec.py`로 분리(§3).
- 인터페이스:
  ```python
  def assess(conn, metric_name: str, basis_date: str, row: dict | None) -> dict
  def assess_many(conn, names: list[str], basis_date: str, rows: dict) -> dict[str, dict]  # 웰니스 MAX(date) 1회 조회 공유
  # 반환: {level: "fresh"|"partial"|"stale"|"missing", value_date, age_days,
  #        inputs: {"wellness": {"last_date", "days"}}, coverage, used_inputs: [...],
  #        reasons: [{code: "input_stale"|"low_coverage"|"value_old", ...}], assertive: bool}
  ```
- 판정 규칙: `value_age = basis - value_date`, `input_age = basis - 웰니스 입력 필드 중 non-null 최신일`, `coverage = row.confidence`, `used_inputs = json_value.components 키`. 임계값은 모듈 상수: stale = 입력 경과일 2일 이상(D1), partial = 웰니스 성분 0개 또는 coverage < 0.5(D2). coverage 출처가 메트릭마다 달라 §2.5의 `coverage` 모드로 일반화한다.
- `assertive = (level == "fresh")`. 화면·문구 생성기는 이 플래그만 본다(프론트 임계값 없음, ADR-020과 같은 원칙).
- SQL은 이 서비스 모듈에만 둔다(`daily_wellness`의 필드별 `MAX(date) WHERE col IS NOT NULL AND date <= ?` 1쿼리). Calculator 무변경이므로 ADR-009와 무관. `db_helpers.py`(754줄)에는 추가하지 않는다.

### 2.2 응답 계약 확장 (전부 추가 필드, 기존 키 불변)
- `/api/v1/today` `readiness.{utrs|cirs|tsb}`에 `confidence`, `freshness` 추가.
- `/api/v1/library/metrics` 각 entry에 `freshness` 추가(`last_value_date`·`confidence_label`·`salience.fresh`는 유지, `salience.fresh`는 `freshness.level == "fresh"`로 의미를 맞춤 — 결정 필요 D6).
- `/api/v1/library/metrics/<slug>` trend에 `current_date`, `freshness` 추가.

### 2.3 판정 문구가 신선도를 받도록 — 경고를 판정 입력으로 승격 (RC-2)
- `fatigue.readiness_decision(..., freshness=None)`, `race_hub_service.race_briefing(hub, tsb, freshness=None)`: `freshness`가 주어지고 `assertive=False`면 "컨디션" 근거 단정 문구 대신 유보형 변형을 고르고 evidence에 `{"type":"freshness", ...}` 항목을 붙인다. 기본값 `None`이면 현재 동작 그대로(호출부 점진 이관).
- `today_service.get_today_briefing`은 UTRS 신선도를 한 번 계산해 두 함수에 전달만 한다(+3줄).
- 동기화 caveat(`source_missing`)는 원장 기반 "소스가 끊김" 신호로 그대로 둔다. 데이터 기반 `freshness`와의 화면 병합 방식은 결정 필요 D5.

### 2.4 프론트(v2)
- `ReadinessGauge`, 지표 목록 카드, `[slug]` 상세, `TodayHero`가 `freshness.level`/`reasons`로 배지·유보 표시를 렌더. 표시 방식은 결정 필요 D3·D4.

### 2.5 FRS-8 확장: `crs`·`rmr`·`rtti` 메트릭별 SPEC

**코드 확인 결과(입력).** 세 Calculator 모두 CalcContext API만 사용한다(`get_wellness()`는 `daily_wellness WHERE date = scope_id` **당일 정확 일치**, `get_metric()`은 같은 날 `metric_store`). 따라서 "당일 웰니스 필드가 있었는가"는 서비스가 필드별 `MAX(date) WHERE col IS NOT NULL AND date <= value_date`로 재구성할 수 있다(필드 최신일 == value_date ⇔ 그 성분 사용). 저장 행의 confidence는 메트릭마다 의미가 달라 그대로 쓸 수 없다.

| 메트릭 | 웰니스 입력(당일) | 메트릭 입력(당일) | 저장 confidence | 행에서 결측 성분 확인 | 웰니스 결측 시 동작 |
|---|---|---|---|---|---|
| `utrs` | body_battery_high, sleep_score, hrv_weekly_avg, avg_stress | tsb | 성분 가중치 합(실측 coverage) | `json_value.components` 키 | 가용 성분 재정규화(TSB 단독 100%) |
| `rmr` (v1.0, `rmr.py`) | resting_hr, body_battery_high, sleep_score | tsb | **미기록(None)** | `json_value.components` 키 (resting_hr/body_battery/sleep/tsb) | UTRS와 같은 재정규화 → TSB 단독 점수 |
| `rtti` (v1.0, `rtti.py`) | body_battery_high, sleep_score (보정 인자 `wellness_factor`) | atl, ctl | **1.0 고정** | 불가(`wellness_factor`만 저장, 1.0이 "결측"인지 "정상"인지 구분 안 됨) → 입력 조회로 판정 | `wf=1.0`(보정 없음, 낙관 쪽) |
| `crs` (v1.0, `crs.py`) | body_battery_high, hrv_weekly_avg(+7일 `get_wellness_series` 평균) | acwr, tsb, cirs, **utrs** | **1.0 고정** | `json_value.signals.body_battery`·`hrv_today`가 null | HRV·BB 게이트 "데이터 없음 (통과)" → LEVEL_FULL, 점수 base=UTRS(없으면 60) |

**판단.** 네 메트릭 모두 "입력 경과일/coverage/결측 성분"을 SPEC으로 표현할 수 있다. 단 (1) coverage를 행의 confidence에서 읽을 수 있는 건 UTRS뿐이고, (2) CRS는 UTRS를 입력으로 쓰므로 신선도가 전이되며, (3) RTTI의 웰니스는 점수 성분이 아니라 보정 인자라 "웰니스 없음 = 값이 틀림"이 아니다. 이 세 가지를 SPEC 필드로 흡수한다.

**SPEC 형식(확장).**
```python
FRESHNESS_SPEC = {
  "utrs": {"wellness": ["body_battery_high","sleep_score","hrv_weekly_avg","avg_stress"],
           "metrics": ["tsb"], "coverage": "row_confidence", "wellness_role": "component"},
  "rmr":  {"wellness": ["resting_hr","body_battery_high","sleep_score"],
           "metrics": ["tsb"], "coverage": "wellness_present_ratio", "wellness_role": "component"},
  "rtti": {"wellness": ["body_battery_high","sleep_score"],
           "metrics": ["atl","ctl"], "coverage": "wellness_present_ratio", "wellness_role": "modifier"},
  "crs":  {"wellness": ["body_battery_high","hrv_weekly_avg"],
           "metrics": ["acwr","tsb","cirs"], "upstream": ["utrs"],
           "coverage": "wellness_present_ratio", "wellness_role": "gate"},
}
```
- `coverage` 모드: `row_confidence` = 행 confidence 사용(UTRS). `wellness_present_ratio` = 선언 웰니스 필드 중 value_date에 존재한 비율(필드별 최신일 조회 결과 재사용, 추가 쿼리 없음). 대체 정의 채택·하한 적용 여부는 **D11**.
- `wellness_role`: `component`(점수 성분, UTRS와 동일 규칙), `modifier`(보정 인자 — 규칙은 **D10**), `gate`(게이트 통과 판정에 쓰임 — 결측 시 게이트가 "통과"로 낙관 판정됨을 reasons에 `gate_unknown`으로 남김).
- `upstream`: 상위 메트릭의 freshness를 먼저 산출해 **나쁜 쪽(level 우선순위 missing>stale>partial>fresh)**을 취하고 reasons에 `{code:"upstream", metric:"utrs"}`를 붙인다. 사이클 없음(SPEC 로드 시 assert). UTRS 웰니스 필드 조회는 `assess_many`의 공유 조회에 포함되어 추가 쿼리 0.
- `metrics` 입력(acwr/tsb/cirs/atl/ctl)은 활동 기반 일별 행이라 같은 날 행 존재 여부만 본다(`metric_store` 1쿼리, `scope_id = value_date AND metric_name IN (...)`). 없으면 reasons `metric_missing`(level은 partial). 이들의 "입력 활동 경과일"은 판정하지 않는다(CTL/ATL은 무활동일도 감쇠로 정상 산출되므로 범위 밖).

**메트릭별 판정 요약(D1=2일, D2=성분 0개 또는 coverage<0.5 적용 시).**

| 메트릭 | stale | partial | 비고 |
|---|---|---|---|
| `utrs` | 웰니스 필드 최신일이 basis−2일 이전, 또는 value_age ≥ 2 | components에 웰니스 0개, 또는 confidence < 0.5 | 기존 §2.1 |
| `rmr` | 동일(웰니스 3필드 기준) | components에 웰니스 0개, 또는 present_ratio < 0.5(3필드 중 1개 이하) | UTRS와 같은 "TSB 단독 점수" 문제가 그대로 있음 |
| `rtti` | value_age ≥ 2 (웰니스 경과일 반영 여부는 D10) | 웰니스 2필드 모두 결측(보정 미적용) | 값 자체(ATL/CTL 비)는 유효 |
| `crs` | 자기 웰니스 stale 또는 upstream `utrs` stale | BB·HRV 모두 결측, 또는 upstream partial, 또는 metric 입력 결측 | 게이트 "통과"가 결측 때문이면 `gate_unknown` |

- 판정은 모두 읽기 시점, 스키마·재계산·Calculator 변경 없음 → **Calculator 버전 증가·`algo_changelog`(ADR-042) 불필요**. 예외: D11에서 (c) "Calculator가 confidence를 기록"을 고르면 `rmr`·`rtti`·`crs` 1.0→1.1, `algo_changelog.py` 3항목, 전체 재계산이 필요하다.

**적용 화면.**
- `/library/metrics` 목록: `crs`·`rmr`·`rtti` entry에 `freshness`, `salience.fresh`(FRS-6 입력 기준). FRS-3에 따라 값 유지 + 등급 라벨 회색/유보. `crs`는 `action_hint`(CRS level 기반 행동 문구, `metric_display.action_hint`)가 단정형이므로 `assertive=False`면 hint를 유보형/생략(+3줄).
- `/library/metrics/<slug>` 상세: trend에 `current_date`·`freshness`, 결측 성분 표시(reasons의 필드명). `crs` 상세의 게이트 목록은 `gate_unknown` 게이트를 "데이터 없음"으로 구분 표시.
- `/today`: 게이지는 utrs/cirs/tsb라 변경 없음. `get_today_status`의 `readiness.crs`(dashboard_service 경유)에 `freshness` 첨부. `rmr`·`rtti`는 today 노출 없음 → library만.
- CRS level을 쓰는 행동 경로(`plan_adjustment_service` source='crs' 조정 제안, `replanner`·`matcher_context`의 `crs.evaluate()` 직접 호출)는 서비스 판정을 거치지 않는다. 반영 여부는 **D12**.

## 3. 변경 파일 표

| 구분 | 파일 | 내용 | 예상 줄 |
|---|---|---|---|
| 신규 | `src/services/metric_freshness.py` | `assess`/`assess_many`, 웰니스 필드별 최신일·metric 입력 존재 조회, coverage 모드, upstream 전이 | ~170 |
| 신규 | `src/services/metric_freshness_spec.py` | `FRESHNESS_SPEC`(utrs·rmr·rtti·crs), level 우선순위, 임계값 상수, upstream 사이클 assert (FRS-8 확장으로 판정 모듈 300줄 여유 확보 위해 분리) | ~60 |
| 신규 | `src/services/metrics_trend_service.py` | `get_metric_trend`·`_race_events` 이동(+freshness). `metrics_browser_service.py`가 298줄이라 분리 필요 | ~100 |
| 수정 | `src/services/metrics_browser_service.py` | trend 제거(−75), entry에 freshness(+8), crs `action_hint` 유보 분기(+3), 하위호환 re-export | 298→~238 |
| 수정 | `src/services/today_service.py` | `get_today_status` `readiness.crs`에 freshness 첨부(dashboard_service 반환 구조 불변 원칙에 따라 additive) | +3 |
| 수정 | `src/services/metric_display.py` | `action_hint(..., assertive=True)` 인자 — False면 유보형/None | +4 |
| 수정 | `src/api/routes_library.py` | trend 호출 경로 변경 | ±2 |
| 수정 | `src/services/today_readiness.py` | confidence·freshness 첨부 | +12 |
| 수정 | `src/training/fatigue.py` | `freshness` 인자, 유보형 헤드라인 분기 | +12 |
| 수정 | `src/services/race_hub_service.py` | `race_briefing` `freshness` 인자 | +10 |
| 수정 | `src/services/today_service.py` | 신선도 계산·전달 (이미 320줄, 순증 최소화) | +3 |
| 수정 | `frontend/src/lib/types/index.ts` | `Freshness` 타입, 각 응답 타입 확장 | +20 |
| 수정 | `ReadinessGauge.svelte`, `TodayHero.svelte`, `routes/library/metrics/+page.svelte`(291줄), `[slug]/+page.svelte` | 배지·유보 표시 (목록 페이지는 카드 컴포넌트 분리 검토) | 각 +5~15 |
| 신규 | `frontend/src/lib/freshness.ts` | level→표시 매핑(문구는 D4 결정 후) | ~40 |
| 신규 | `tests/test_metric_freshness.py` | fresh/partial/stale/missing, 웰니스 원값, 공유 조회 + FRS-8: rmr present_ratio, rtti modifier, crs upstream 전이·`gate_unknown`, metric 입력 결측, 쿼리 수 고정 | ~22개 |
| 신규 | `tests/test_metric_freshness_spec.py` | SPEC이 실제 Calculator 입력과 일치(각 Calculator `requires` ⊇ `metrics`+`upstream`, wellness 필드가 `daily_wellness` 컬럼에 존재), upstream 사이클 없음 | ~4개 |
| 수정 | `tests/test_today_hero.py`, `test_fatigue.py`, `test_race_hub_service.py`, `test_metrics_browser_service.py`, `test_api_library.py` | 추가 필드·유보 분기·`freshness=None` 회귀, crs/rmr/rtti entry·상세 freshness, crs action_hint 유보 | 각 +2~5개 |
| 수정 | `tests/test_metric_display.py`(없으면 신규), `tests/test_today_service.py` | `action_hint` assertive 분기, `readiness.crs.freshness` | +2개씩 |
| 신규 | `frontend/tests/freshness.test.mjs` | 매핑·배지 조건 | ~6개 |
| 문서 | `v0.3/data/decisions.md` | ADR-048 (결정 확정 후) | — |

## 4. 적용 순서와 검증

1. **판정 모듈**: `metric_freshness_spec.py`·`metric_freshness.py` + 단위 테스트. 픽스처는 "웰니스 마지막 09-27, 10-11 UTRS=85 conf=0.25 components={tsb}" → `stale` + `low_coverage`, `assertive=False`; 같은 날 웰니스가 있으면 `fresh`. FRS-8 픽스처(같은 DB): `rmr` components={tsb} → `stale`+partial 사유; `rtti` 웰니스 결측·ATL/CTL 당일 존재 → D10 결정대로; `crs` 자기 BB·HRV 결측 + upstream UTRS stale → `stale`, reasons에 `upstream`·`gate_unknown`; 웰니스 당일 존재 시 4개 모두 `fresh`. `assess_many(['utrs','crs','rmr','rtti'])`의 쿼리 수가 2(웰니스 필드 최신일 1 + metric 입력 존재 1)로 고정인지 확인. `pytest tests/test_metric_freshness*.py`.
2. **Today API**: `build_readiness`에 첨부, `get_today_status` `readiness.crs`에 첨부. `test_today_hero` + API 테스트로 `readiness.utrs.freshness.level`·`readiness.crs.freshness.level` 확인.
3. **판정 문구**: `readiness_decision`·`race_briefing`에 인자 추가. `freshness=None` 회귀 테스트로 기존 문구 불변 확인, `assertive=False` 분기 테스트. `coach_evidence`(규칙 경로)가 같은 함수를 쓰므로 영향 확인 테스트 1개.
4. **Library API**: trend 분리 이동(동작 불변 커밋 먼저) → freshness 추가(utrs·웰니스 원값·crs·rmr·rtti 동시) → crs `action_hint` 유보. `test_metrics_browser_service`, `test_api_library`.
5. **프론트**: 타입·매핑·컴포넌트. `frontend/tests/*.test.mjs`, `npm run check`.
6. **브라우저 확인**(운영 DB 아님, 로컬 DB 사본·픽스처): (a) 웰니스 14일 결측 시나리오 — `/today` 게이지 배지·히어로 유보 문구·caveat 중복 여부, `/library/metrics` UTRS 카드, `/library/metrics/utrs`, `/library/metrics/sleep_score` 상세, `/library/metrics` crs·rmr·rtti 카드(라벨 회색/유보·action hint 유보), `/library/metrics/crs`(게이트 '데이터 없음' 구분)·`/rmr`·`/rtti` 상세; (b) 당일 웰니스 있는 정상 시나리오 — 배지 없음(회귀). 기존 Playwright `pw/s5_wellness.mjs` 패턴으로 시나리오 1개 추가 검토.
7. 전체 `pytest tests/`, `scripts/check_docs.py`, ADR-048 기록.

## 5. 호환성·v1 의존

- API 변경은 모두 추가 필드라 하위호환. 단 `salience.fresh` 의미 변경(D6)을 택하면 목록 정렬·강조가 달라진다.
- `readiness_decision` 헤드라인은 v2 `/today`, `coach_evidence`(Coach 규칙 경로)가 공유 → 유보 문구가 Coach 근거에도 나간다(의도된 일관성이지만 Coach 응답 변화).
- v1(`src/web/views_dashboard_cards_*`, `views_ai_coach_cards` 등)은 metric_store를 직접 읽으므로 이 설계의 혜택을 받지 않고 85 "좋음"을 계속 표시한다. v1 제거 예정(ADR-046)이라 수정하지 않는 것을 전제로 한다.
- AI 컨텍스트 빌더(`src/ai/context_builders.py` 등)는 UTRS 값만 싣는다. 신선도 전달은 범위 밖(메모 참고).
- 메트릭 값·DB 스키마·Calculator 무변경 → 재계산 불필요. FRS-8 확장도 동일(D11 (c) 선택 시에만 예외).
- CRS level을 소비하는 훈련 조정·재계획·매처 스냅샷 경로는 `crs.evaluate()`를 직접 호출하므로 이 설계의 혜택을 자동으로 받지 않는다(D12).

## 6. 대안 비교

| | A안: 읽기 시점 서비스 판정 (추천) | B안: 계산 시점 게이팅 |
|---|---|---|
| 방식 | 저장값 유지, 서비스가 입력 경과일·confidence로 `freshness` 산출 | UTRS가 웰니스 전무 또는 coverage 하한 미만이면 `[]` 반환하거나 재정규화를 중립값 대체로 변경 |
| 장점 | 스키마·재계산 없음, 모든 메트릭에 같은 규칙, 결손 원인 설명 가능 | 잘못된 값 자체가 생기지 않음, v1·AI 컨텍스트도 자동 혜택 |
| 단점 | 저장값 85는 그대로라 서비스 경유하지 않는 소비처(v1, AI)엔 미반영 | Calculator 버전 증가·`algo_changelog`·전체 재계산, 과거 이력 값 변경, 웨어러블 없는 사용자는 UTRS 영구 공백, "얼마나 오래됐는지" 설명은 여전히 서비스 몫 |

추천: A안. B안의 재정규화 정책 변경은 지표 정의 문제라 별도 결정(D7)으로 분리한다.

## 7. 결정 필요

- **D1 stale 기준 경과일 (FRS-1, 결정 2026-10-11: 2일)**: 입력 웰니스가 N일 이상 없으면 stale. 선택지 1일(당일 없으면 stale — 엄격, 아침 동기화 전엔 매일 경고) / 2일(하루 지연 허용) / 3일 이상(경고 적음, 이번 결측 같은 장기 공백만 잡음).
- **D2 partial 기준 (FRS-2, 결정 2026-10-11: 웰니스 성분 0개 또는 confidence<0.5)**: confidence 하한(예: 0.5 미만) / "웰니스 성분 0개"일 때만 / 둘 다. 하한이 높을수록 경고가 잦다.
- **D3 stale·partial 시 UTRS 표시 (FRS-3, 결정 2026-10-11: (b) 값 유지 + 등급 라벨 회색/유보)**: (a) 값·등급 유지 + 배지 (b) 값 유지, 등급 라벨 숨김 또는 회색 (c) 값 숨기고 "데이터 수집 중". (a)는 정보 손실 없음·단정 위험 남음, (c)는 가장 안전·TSB 기반 신호 손실.
- **D4 문구 (FRS-4, 미결정)**: 배지 문구, 유보형 헤드라인 문구, 상세 "MM-DD 기록 기준" 표기 문구.
- **D5 caveat 병합 (FRS-5, 결정 2026-10-11: (b) freshness 하나로 병합, 규칙·문구는 구현 시)**: 히어로에서 동기화 `source_missing`과 데이터 `freshness` 경고를 (a) 둘 다 (b) freshness 하나로 병합 (c) caveat만 유지하고 헤드라인만 유보형.
- **D6 `salience.fresh` 의미 (FRS-6, 결정 2026-10-11: 입력 신선도 기준)**: 행 날짜 기준 유지 / 입력 신선도 기준으로 변경(목록 강조 순서 변화).
- **D7 UTRS 재정규화 정책(B안 요소) (FRS-7, 결정 2026-10-11: 현행 유지)**: 현행 유지 / 웰니스 0개면 미산출 / 결측 성분을 중립값으로 대체. 변경 시 버전 증가·재계산·과거 값 변경 동반.
- **D8 2차 적용 범위 (FRS-8, 결정됨(확장 설계 반영) 2026-10-11)**: UTRS·readiness와 함께 `crs`·`rmr`·`rtti`도 같은 규칙 적용. 확장 설계는 §2.5, 파일은 §3, 검증은 §4. 같은 구현 묶음으로 진행하되 아래 D9~D13이 정해진 뒤 착수.
- **D9 메트릭별 stale 일수**: (a) 전 메트릭 2일 공통, 웰니스·metric 입력 모두 경과일 판정 — 단순·문구 통일, 활동 없는 날 오경고 가능 / (b) SPEC에 `stale_days` override 허용, 기본 2일 — 유연하나 "왜 이 지표만 다른지" 이해 비용·테스트 증가 / (c) 웰니스 입력만 공통 2일, metric 입력(acwr·atl 등)은 당일 존재만 보고 경과일 판정 안 함(현 설계안) — 활동 기반 지표 오경고 없음, 대신 부하 지표 자체의 지연은 못 잡음.
- **D10 RTTI 웰니스(보정 인자) 결측 처리**: (a) UTRS와 같은 규칙(웰니스 2일 결측 → stale, 라벨 회색) — 일관적이나 ATL/CTL 비라는 유효한 값까지 유보 / (b) 웰니스 결측은 partial("보정 미적용")까지만, stale은 value_age로만 — 값의 성격에 맞고 경고가 덜 과함 / (c) RTTI는 신선도 적용 제외 — 가장 단순, FRS-8 결정과 어긋남.
- **D11 confidence가 없거나 1.0 고정인 메트릭의 coverage**(`rmr` None, `rtti`·`crs` 1.0): (a) 선언 웰니스 필드 중 당일 존재 비율로 대체하고 0.5 하한 적용(현 설계안) — 무변경·읽기 시점, 단 UTRS(가중치 기반)와 비율 정의가 다름 / (b) 대체 coverage 없이 "웰니스 성분 0개"만 partial — 단순, 1개만 있는 경우 단정 유지 / (c) Calculator가 실측 confidence를 기록하도록 수정 — 저장값이 정확해져 v1·AI도 혜택, 대신 `rmr`·`rtti`·`crs` 버전 1.0→1.1, `algo_changelog` 3항목(ADR-042), 전체 재계산, 과거 행 confidence 변경.
- **D12 CRS 행동 경로 반영**: CRS level은 훈련 조정 제안(`plan_adjustment_service` source='crs')·재계획(`replanner`)·매처 스냅샷에 쓰이고, 웰니스 결측 시 BB·HRV 게이트가 "통과"로 낙관 판정된다. (a) 표시만 유보, 행동 경로 현행 — 범위 최소, 결측일에도 강도 상향(BOOST 포함) 제안 가능 / (b) 조정 제안 evidence에 freshness·`gate_unknown`을 붙이고 문구만 유보형 — 근거 노출, 로직 불변 / (c) stale이면 CRS 기반 자동 조정 제안·BOOST 보류 — 가장 안전, 조정 규칙 변경이라 `rule_version` 증가와 별도 테스트 필요.
- **D13 결측 성분 표시 문구 범위**(D4의 하위): (a) 공통 문구만("일부 데이터 없이 계산") / (b) 메트릭별 결측 성분명 노출("수면·바디배터리 없이 계산", CRS "HRV 게이트 데이터 없음") — 설명력 높음, 문구 사전 관리 필요(`frontend/src/lib/freshness.ts` +20줄) / (c) 목록은 공통, 상세만 성분명.

## 8. 범위 밖 메모

- `today_service.py`(320줄), `db_helpers.py`(754줄)가 이미 300줄 규칙 초과 — 별도 분리 작업.
- AI·Coach 컨텍스트(`src/ai/context_builders.py`, `chat_context_rich.py`)에 지표 신선도 전달 없음.
- T-03의 "ACWR 0.67(저부하)과 결이 다름"은 지표 간 일관성 문제로 신선도와 별개.
- `get_metric_trend`의 `change_pct`·`peak` 산식 문제(M-03, M-04)는 trend 분리 시 건드리지 않는다.
- `src/metrics/crs.py`의 주석 "NOTE: raw SQL 사용"은 실제 코드(전부 CalcContext 사용)와 맞지 않고, `since` 변수는 미사용이다. 신선도와 무관한 정리 대상.
- `crs`·`rtti`의 `confidence=1.0` 고정, `rmr`의 confidence 미기록은 지표 정의 문제(D11 (c)를 고르지 않으면 별도 백로그 후보).
