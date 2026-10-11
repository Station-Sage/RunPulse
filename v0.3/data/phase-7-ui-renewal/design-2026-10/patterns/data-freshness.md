# 설계: 데이터 신선도 반영 (지표 판정에 입력 경과일·커버리지 포함)

- 대상 ID: T-03 (`/today` Hero + UTRS 게이지), M-02 (`/library/metrics` UTRS 카드·상세, 수면 계열 상세), FRS-8 확장(`crs`·`rmr`·`rtti` 목록·상세, `/today` 상태의 CRS)
- 상태: 설계 초안 (구현 전, D1~D3·D5~D11 결정됨, D4·D12~D14 결정 필요)
- 변경 이력:
  - 2026-10-11 FRS-8 확장 설계 — `crs`·`rmr`·`rtti` 입력 분석과 메트릭별 SPEC(§2.5), 변경 파일·단계·검증 반영, 결정 D9~D13 추가
  - 2026-10-11 FRS-9~11 결정 반영(FRS-11=c) — 읽기 시점 대체 coverage 제거, `rmr`·`rtti`·`crs` Calculator가 실측 confidence 기록(1.0→1.1)·전체 재계산·단계적 롤아웃, D14 추가
- 관련 ADR: ADR-009 (Calculator raw SQL 금지 — 신선도 판정은 서비스 계층, confidence는 이미 조회한 입력으로만 계산), ADR-020 (등급은 서버 SSOT, 프론트 임계값 없음 — 신선도도 같은 원칙), ADR-044 (동기화 상태는 원장만 진실 — `source_missing` caveat의 출처), ADR-042 (Calculator 버전 변경 시 changelog — `rmr`·`rtti`·`crs` 1.1)

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
- `ReadinessGauge`, 지표 목록 카드, `[slug]` 상세, `TodayHero`가 `freshness.level`/`reasons`로 배지·유보 표시를 렌더. 표시 방식은 D3·D4.

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
- 추세 차트: `algo_changelog`의 `prev="1.0"` 항목이 반영일에 ◆ 마커("계산 방식 변경: 1.0→1.1")를 만든다. 값은 그대로이고 confidence만 바뀌므로 마커가 "값이 바뀐 것"으로 오독될 수 있다 → **D14**. 재계산 캡션(`recompute_note`)은 `algo_recompute` 마일스톤 기준인데 `recompute_all`이 행을 지운 뒤 재삽입하므로 마일스톤이 남는지 구현 시 확인.
- CRS level을 쓰는 행동 경로(`plan_adjustment_service` source='crs', `replanner`·`matcher_context`의 `crs.evaluate()` 직접 호출)는 서비스 판정을 거치지 않는다 → **D12**.

## 3. 변경 파일 표

| 구분 | 파일 | 내용 | 예상 줄 |
|---|---|---|---|
| 수정 | `src/metrics/rmr.py` | `ConfidenceBuilder` 4입력, `version="1.1"` | 66→~73 |
| 수정 | `src/metrics/rtti.py` | `ConfidenceBuilder` 4입력, `wellness_used`, `version="1.1"` | 78→~90 |
| 수정 | `src/metrics/crs.py` | `ConfidenceBuilder` 6입력(HRV rolling 없으면 estimated), `version="1.1"` | 206→~216 |
| 수정 | `src/metrics/algo_changelog.py` | `AlgoChange("rmr"/"rtti"/"crs", "1.1", <반영일>, "신뢰도를 실제 입력 데이터 기준으로 기록해요(값은 그대로예요)", "1.0")` 3항목 | +3 |
| 신규 | `src/services/metric_freshness.py` | `assess`/`assess_many`, 웰니스 필드별 최신일·metric 입력 존재 조회, role별 규칙, `min_version` 가드, upstream 전이 | ~150 |
| 신규 | `src/services/metric_freshness_spec.py` | `FRESHNESS_SPEC`, level 우선순위, 임계값, upstream 사이클 assert | ~50 |
| 신규 | `src/services/metrics_trend_service.py` | `get_metric_trend`·`_race_events` 이동(+freshness). `metrics_browser_service.py` 298줄이라 분리 | ~100 |
| 수정 | `src/services/metrics_browser_service.py` | trend 제거(−75), entry에 freshness(+8), crs `action_hint` 유보(+3), 하위호환 re-export | 298→~238 |
| 수정 | `src/services/today_service.py` | `readiness.crs` freshness 첨부 + 브리핑 신선도 전달(이미 320줄, 순증 최소화) | +6 |
| 수정 | `src/services/metric_display.py` | `action_hint(..., assertive=True)` | +4 |
| 수정 | `src/api/routes_library.py` | trend 호출 경로 변경 | ±2 |
| 수정 | `src/services/today_readiness.py` | confidence·freshness 첨부 | +12 |
| 수정 | `src/training/fatigue.py`, `src/services/race_hub_service.py` | `freshness` 인자, 유보형 분기 | +12, +10 |
| 수정 | `frontend/src/lib/types/index.ts` | `Freshness` 타입, 응답 타입 확장 | +20 |
| 수정 | `ReadinessGauge.svelte`, `TodayHero.svelte`, `routes/library/metrics/+page.svelte`(291줄), `[slug]/+page.svelte` | 배지·유보 표시(목록은 카드 컴포넌트 분리 검토) | 각 +5~15 |
| 신규 | `frontend/src/lib/freshness.ts` | level→표시 매핑(문구는 D4·D13 후) | ~40 |
| 신규/수정 | `tests/test_rmr.py`(신규), `tests/test_rtti.py`, `tests/test_crs.py` | 위 표의 confidence 값(전부/TSB 단독/웰니스 0개/HRV estimated/전부 None=0.0), `wellness_used`, 값·level 불변 회귀, 데이터 부족 `[]` 유지 | 각 +3~4개 |
| 자동 | `tests/test_algo_changelog.py` | 기존 검사가 3항목 누락·버전 불일치를 막음(수정 없음) | — |
| 신규 | `tests/test_metric_freshness.py` | fresh/partial/stale/missing, 웰니스 원값, 공유 조회, rmr confidence<0.5, rtti modifier(웰니스 14일 결측 → partial만), crs upstream·`gate_unknown`, metric 입력 결측(경과일 무시), `min_version` 미달 → `coverage_unknown`, 쿼리 수 2 고정 | ~22개 |
| 신규 | `tests/test_metric_freshness_spec.py` | SPEC ⊆ Calculator `requires`·`daily_wellness` 컬럼, `min_version` == 각 Calculator `version`, upstream 사이클 없음 | ~5개 |
| 수정 | `test_today_hero.py`, `test_fatigue.py`, `test_race_hub_service.py`, `test_metrics_browser_service.py`, `test_api_library.py`, `test_today_service.py`, `test_metric_display.py`(없으면 신규) | 추가 필드·유보 분기·`freshness=None` 회귀, crs/rmr/rtti entry·상세, `action_hint` assertive | 각 +2~5개 |
| 신규 | `frontend/tests/freshness.test.mjs` | 매핑·배지 조건 | ~6개 |
| 문서 | `v0.3/data/decisions.md`, `v0.3/data/metric_dictionary.md`(`gen_metric_dictionary.py` 재생성) | ADR-048, 버전 1.1 반영 | — |

## 4. 적용 순서와 검증 (단계적 롤아웃: 코드 배포 → 재계산 → 신선도 판정 활성)

1. **Calculator 1.1(배포 1)**: 세 Calculator + `algo_changelog` 3항목. `pytest tests/test_rmr.py tests/test_rtti.py tests/test_crs.py tests/test_algo_changelog.py`, `gen_metric_dictionary.py`. 이 시점부터 신규 일자는 1.1로 쌓여 재계산 전까지 시계열에 버전 불연속(◆)이 생긴다 — 배포 직후 2단계를 바로 수행.
2. **전체 재계산**: 운영 전 `running.db` 백업(파일 복사) → `POST /api/v1/data/recompute {"scope":"all","reason":"algo_confidence_1_1"}` → `recompute_service.start` → `engine.recompute_all(days=None)`(가장 이른 활동일부터 전 메트릭 삭제·재실행, 세 메트릭만이 아님 — 비용은 기존 전체 재계산과 동일). `scope:"90d"`는 금지(90일 밖이 1.0으로 남아 불연속·`coverage_unknown` 지속). 진행은 `GET /api/v1/data/jobs/<id>`. 완료 검증: `SELECT metric_name, algorithm_version, COUNT(*), MIN(confidence), MAX(confidence) FROM metric_store WHERE metric_name IN ('rmr','rtti','crs') GROUP BY 1,2` → 1.1만, confidence NULL 없음, `rtti`·`crs` 1.0 고정 해소. 값(`numeric_value`)은 재계산 전후 동일해야 함(before/after 표본 비교).
   - **실패/중단 복구**: 작업은 `status=failed, error_code=RECOMPUTE_FAILED`로 남는다. `engine`은 날짜 구간마다 commit하므로 1.0/1.1 혼재 상태가 될 수 있다 → 같은 요청을 다시 실행(삭제 후 재실행이라 멱등, 진행 중이면 `RECOMPUTE_RUNNING`). 반복 실패 시 백업으로 복원 후 원인 수정. 혼재 기간에도 `min_version` 가드로 1.0 행의 confidence는 판정에 쓰이지 않는다.
3. **판정 모듈(배포 2, 신선도 활성)**: `metric_freshness_spec.py`·`metric_freshness.py` + 단위 테스트. 픽스처: "웰니스 마지막 09-27, 10-11 UTRS=85 conf=0.25 components={tsb}" → `stale`+`low_coverage`, `assertive=False`; 같은 날 웰니스가 있으면 `fresh`. FRS-8: `rmr` components={tsb}, conf 0.25 → `stale`+`low_coverage`; `rtti` 웰니스 결측·ATL/CTL 당일 존재·conf 0.6 → `partial`(`modifier_missing`, stale 아님); `crs` BB·HRV 결측 + upstream UTRS stale → `stale`, reasons `upstream`·`gate_unknown`; 1.0 행 → `coverage_unknown`; 웰니스 당일 존재 시 4개 모두 `fresh`. `assess_many(['utrs','crs','rmr','rtti'])` 쿼리 수 2 고정.
4. **Today API**: `build_readiness`·`readiness.crs` 첨부. `test_today_hero` + API 테스트.
5. **판정 문구**: `readiness_decision`·`race_briefing` 인자. `freshness=None` 회귀, `assertive=False` 분기, `coach_evidence` 영향 테스트 1개.
6. **Library API**: trend 분리 이동(동작 불변 커밋 먼저) → freshness 추가 → crs `action_hint` 유보. `test_metrics_browser_service`, `test_api_library`.
7. **프론트**: 타입·매핑·컴포넌트. `frontend/tests/*.test.mjs`, `npm run check`.
8. **브라우저 확인**(로컬 DB 사본·픽스처, 재계산 완료 상태): (a) 웰니스 14일 결측 — `/today` 배지·유보 문구·caveat 병합, `/library/metrics` UTRS·crs·rmr·rtti 카드(라벨 회색/유보, `confidence_label` 변화, action hint 유보), `/library/metrics/utrs`·`/sleep_score`·`/crs`(게이트 '데이터 없음')·`/rmr`·`/rtti`(◆ 마커·재계산 캡션 표시 확인); (b) 당일 웰니스 정상 — 배지 없음(회귀). `pw/s5_wellness.mjs` 패턴으로 시나리오 1개 추가 검토.
9. 전체 `pytest tests/`, `scripts/check_docs.py`, ADR-048 기록.

## 5. 호환성·v1 의존

- API 변경은 모두 추가 필드라 하위호환. `salience.fresh` 의미 변경(D6)으로 목록 정렬·강조가 달라진다.
- **과거 행 confidence 변경**: 재계산 후 `rmr`·`rtti`·`crs`의 모든 과거 행 confidence가 실측값으로 바뀐다(값·level·text 불변). `confidence`를 읽는 소비처 — library `confidence_label`, `dashboard_service`(v1/today crs), AI 컨텍스트 중 confidence를 싣는 경로 — 의 표시가 낮아질 수 있다. v1·AI는 이 설계에서 수정하지 않지만 저장값 자체가 정확해져 혜택을 받는다.
- `readiness_decision` 헤드라인은 v2 `/today`, `coach_evidence`가 공유 → 유보 문구가 Coach 근거에도 나간다(의도된 일관성).
- v1(`src/web/views_dashboard_cards_*` 등)은 freshness를 받지 않고 UTRS 85 "좋음"을 계속 표시. v1 제거 예정(ADR-046)이라 수정하지 않는다.
- 스키마 변경 없음. 재계산은 1회(§4-2), 이후 일상 동기화는 1.1로 계산.
- CRS level을 소비하는 훈련 조정·재계획·매처 경로는 `crs.evaluate()` 직접 호출이라 freshness 혜택을 자동으로 받지 않는다(D12).

## 6. 대안 비교

| | A안: 읽기 시점 판정 + 계산 시점 confidence (추천) | B안: 계산 시점 게이팅 |
|---|---|---|
| 방식 | 값 유지, Calculator는 실측 confidence만 기록, 서비스가 입력 경과일·confidence로 `freshness` 산출 | UTRS 등이 웰니스 전무 또는 coverage 하한 미만이면 `[]` 반환하거나 재정규화를 중립값 대체로 변경 |
| 장점 | 값 정의 불변, 결손 원인 설명 가능, confidence는 v1·AI에도 정확 | 잘못된 값 자체가 생기지 않음 |
| 단점 | 버전 1.1·전체 재계산 1회, 서비스 경유 없는 소비처엔 신선도 미반영 | 값 정의 변경·과거 값 변경, 웨어러블 없는 사용자는 영구 공백 |

B안의 재정규화 정책 변경은 지표 정의 문제라 별도 결정(D7, 현행 유지)으로 분리.

## 7. 결정 필요

- **D1 stale 기준 경과일 (FRS-1, 결정 2026-10-11: 2일)**.
- **D2 partial 기준 (FRS-2, 결정 2026-10-11: 웰니스 성분 0개 또는 confidence<0.5)**.
- **D3 stale·partial 시 표시 (FRS-3, 결정 2026-10-11: (b) 값 유지 + 등급 라벨 회색/유보)**.
- **D4 문구 (FRS-4, 미결정)**: 배지 문구, 유보형 헤드라인 문구, 상세 "MM-DD 기록 기준" 표기 문구.
- **D5 caveat 병합 (FRS-5, 결정 2026-10-11: (b) freshness 하나로 병합, 규칙·문구는 구현 시)**.
- **D6 `salience.fresh` 의미 (FRS-6, 결정 2026-10-11: 입력 신선도 기준)**.
- **D7 UTRS 재정규화 정책 (FRS-7, 결정 2026-10-11: 현행 유지)**.
- **D8 2차 적용 범위 (FRS-8, 결정됨 2026-10-11)**: `crs`·`rmr`·`rtti`도 같은 규칙. §2.5·§3·§4.
- **D9 메트릭별 stale 일수 (FRS-9, 결정됨 2026-10-11: (c))**: 웰니스 입력만 공통 2일, metric 입력(acwr·atl 등)은 당일 존재만 보고 경과일 판정 안 함.
- **D10 RTTI 웰니스 결측 처리 (FRS-10, 결정됨 2026-10-11: (b))**: 웰니스 결측은 partial("보정 미적용")까지만, stale은 value_age로만.
- **D11 coverage 출처 (FRS-11, 결정됨 2026-10-11: (c))**: Calculator가 실측 confidence 기록 — `rmr`·`rtti`·`crs` 1.0→1.1, `algo_changelog` 3항목(ADR-042), 전체 재계산, 과거 행 confidence 변경. 가중치는 §2.5 표, 롤아웃은 §4-1~3.
- **D12 CRS 행동 경로 반영 (FRS-12, 미결정)**: CRS level은 조정 제안(`plan_adjustment_service` source='crs')·재계획(`replanner`)·매처 스냅샷에 쓰이고, 웰니스 결측 시 BB·HRV 게이트가 "통과"로 낙관 판정된다. (a) 표시만 유보, 행동 경로 현행 — 결측일에도 BOOST 포함 강도 상향 제안 가능 / (b) 조정 제안 evidence에 freshness·`gate_unknown`을 붙이고 문구만 유보형 — 로직 불변. D11 (c)로 저장 행 confidence가 실측이 되어 저장 행을 읽는 경로(조정 제안)는 confidence를 그대로 evidence에 실을 수 있으나, `crs.evaluate()` 직접 호출 경로는 저장 행을 읽지 않으므로 evaluate 반환에 confidence를 추가해야 함 / (c) stale이면 CRS 기반 자동 조정·BOOST 보류 — 가장 안전, `rule_version` 증가·별도 테스트. D11 (c) 덕에 "confidence < 0.5면 보류" 같은 계산 시점 기준도 선택 가능.
- **D13 결측 성분 표시 문구 범위 (FRS-13, 미결정)**: (a) 공통 문구만("일부 데이터 없이 계산") / (b) 메트릭별 결측 성분명("수면·바디배터리 없이 계산", CRS "HRV 게이트 데이터 없음") — 문구 사전 관리(`freshness.ts` +20줄). D11 (c)로 `rtti` `wellness_used`가 생겨 4개 메트릭 모두 행에서 성분명을 얻으므로 추가 조회 비용은 없음 / (c) 목록은 공통, 상세만 성분명.
- **D14 confidence만 바뀐 버전 상향의 ◆ 마커 (신규, 미결정)**: `prev="1.0"` changelog 항목이 `rmr`·`rtti`·`crs` 추세에 ◆ "계산 방식 변경: 1.0→1.1"을 만들지만 값은 그대로다. (a) 그대로 표시, 사유 문구에 "값은 그대로예요" 명시 — 무변경, 마커 의미가 약간 흐려짐 / (b) `AlgoChange`에 `value_changed: bool = True` 필드를 두고 False면 ◆ 생략(changelog 기록·ADR-042 테스트는 유지) — `algo_changelog.py`·`metrics_changelog_events.py` 소폭 수정·테스트 1~2개 / (c) `prev=None`으로 기록해 마커 생략 — 가장 단순하나 "신규 Calculator" 의미를 오용.

## 8. 범위 밖 메모

- `today_service.py`(320줄), `db_helpers.py`(754줄)가 이미 300줄 규칙 초과 — 별도 분리 작업.
- AI·Coach 컨텍스트(`src/ai/context_builders.py`, `chat_context_rich.py`)에 지표 신선도 전달 없음.
- T-03의 "ACWR 0.67(저부하)과 결이 다름"은 지표 간 일관성 문제로 신선도와 별개.
- `get_metric_trend`의 `change_pct`·`peak` 산식 문제(M-03, M-04)는 trend 분리 시 건드리지 않는다.
- `src/metrics/crs.py`의 주석 "NOTE: raw SQL 사용"은 실제 코드(전부 CalcContext)와 맞지 않고 `since` 변수는 미사용 — 1.1 수정 시 함께 정리 가능하나 동작 무관.
- `crs`가 입력 전부 None에도 행(base 60)을 만드는 것은 빈 리스트 규칙과 어긋남 — 값 정의 변경이라 별도 백로그 후보(이번엔 confidence 0.0 기록만).
