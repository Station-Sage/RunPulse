# 설계: 데이터 신선도 반영 (지표 판정에 입력 경과일·커버리지 포함)

- 대상 ID: T-03 (`/today` Hero + UTRS 게이지), M-02 (`/library/metrics` UTRS 카드·상세, 수면 계열 상세)
- 상태: 설계 초안 (구현 전, 사용자 결정 필요 항목 있음)
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
- 메트릭별 입력 출처 선언(상수, SSOT): `FRESHNESS_SPEC = {"utrs": {"wellness": ["body_battery_high","sleep_score","hrv_weekly_avg","avg_stress"], "metrics": ["tsb"]}, ...}`. 웰니스 원값 메트릭(`MetricDef.storage == "wellness"`)은 자기 컬럼이 곧 입력이므로 자동 처리. 1차 적용: `utrs` + 웰니스 원값. 2차 후보: 웰니스를 쓰는 `crs`, `rmr`, `rtti`.
- 인터페이스:
  ```python
  def assess(conn, metric_name: str, basis_date: str, row: dict | None) -> dict
  def assess_many(conn, names: list[str], basis_date: str, rows: dict) -> dict[str, dict]  # 웰니스 MAX(date) 1회 조회 공유
  # 반환: {level: "fresh"|"partial"|"stale"|"missing", value_date, age_days,
  #        inputs: {"wellness": {"last_date", "days"}}, coverage, used_inputs: [...],
  #        reasons: [{code: "input_stale"|"low_coverage"|"value_old", ...}], assertive: bool}
  ```
- 판정 규칙: `value_age = basis - value_date`, `input_age = basis - 웰니스 입력 필드 중 non-null 최신일`, `coverage = row.confidence`, `used_inputs = json_value.components 키`. 임계값(경과일 N, coverage 하한)은 모듈 상수로 두되 값은 결정 필요 D1·D2.
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

## 3. 변경 파일 표

| 구분 | 파일 | 내용 | 예상 줄 |
|---|---|---|---|
| 신규 | `src/services/metric_freshness.py` | SPEC 상수, `assess`/`assess_many`, 웰니스 최신일 조회 | ~120 |
| 신규 | `src/services/metrics_trend_service.py` | `get_metric_trend`·`_race_events` 이동(+freshness). `metrics_browser_service.py`가 298줄이라 분리 필요 | ~100 |
| 수정 | `src/services/metrics_browser_service.py` | trend 제거(−75), entry에 freshness(+8), 하위호환 re-export | 298→~235 |
| 수정 | `src/api/routes_library.py` | trend 호출 경로 변경 | ±2 |
| 수정 | `src/services/today_readiness.py` | confidence·freshness 첨부 | +12 |
| 수정 | `src/training/fatigue.py` | `freshness` 인자, 유보형 헤드라인 분기 | +12 |
| 수정 | `src/services/race_hub_service.py` | `race_briefing` `freshness` 인자 | +10 |
| 수정 | `src/services/today_service.py` | 신선도 계산·전달 (이미 320줄, 순증 최소화) | +3 |
| 수정 | `frontend/src/lib/types/index.ts` | `Freshness` 타입, 각 응답 타입 확장 | +20 |
| 수정 | `ReadinessGauge.svelte`, `TodayHero.svelte`, `routes/library/metrics/+page.svelte`(291줄), `[slug]/+page.svelte` | 배지·유보 표시 (목록 페이지는 카드 컴포넌트 분리 검토) | 각 +5~15 |
| 신규 | `frontend/src/lib/freshness.ts` | level→표시 매핑(문구는 D4 결정 후) | ~40 |
| 신규 | `tests/test_metric_freshness.py` | fresh/partial/stale/missing, 웰니스 원값, 공유 조회 | ~12개 |
| 수정 | `tests/test_today_hero.py`, `test_fatigue.py`, `test_race_hub_service.py`, `test_metrics_browser_service.py`, `test_api_library.py` | 추가 필드·유보 분기·`freshness=None` 회귀 | 각 +2~4개 |
| 신규 | `frontend/tests/freshness.test.mjs` | 매핑·배지 조건 | ~6개 |
| 문서 | `v0.3/data/decisions.md` | ADR-048 (결정 확정 후) | — |

## 4. 적용 순서와 검증

1. **판정 모듈**: `metric_freshness.py` + 단위 테스트. 픽스처는 "웰니스 마지막 09-27, 10-11 UTRS=85 conf=0.25 components={tsb}" → `stale` + `low_coverage`, `assertive=False`; 같은 날 웰니스가 있으면 `fresh`. `pytest tests/test_metric_freshness.py`.
2. **Today API**: `build_readiness`에 첨부. `test_today_hero` + API 테스트로 `readiness.utrs.freshness.level` 확인.
3. **판정 문구**: `readiness_decision`·`race_briefing`에 인자 추가. `freshness=None` 회귀 테스트로 기존 문구 불변 확인, `assertive=False` 분기 테스트. `coach_evidence`(규칙 경로)가 같은 함수를 쓰므로 영향 확인 테스트 1개.
4. **Library API**: trend 분리 이동(동작 불변 커밋 먼저) → freshness 추가. `test_metrics_browser_service`, `test_api_library`.
5. **프론트**: 타입·매핑·컴포넌트. `frontend/tests/*.test.mjs`, `npm run check`.
6. **브라우저 확인**(운영 DB 아님, 로컬 DB 사본·픽스처): (a) 웰니스 14일 결측 시나리오 — `/today` 게이지 배지·히어로 유보 문구·caveat 중복 여부, `/library/metrics` UTRS 카드, `/library/metrics/utrs`, `/library/metrics/sleep_score` 상세; (b) 당일 웰니스 있는 정상 시나리오 — 배지 없음(회귀). 기존 Playwright `pw/s5_wellness.mjs` 패턴으로 시나리오 1개 추가 검토.
7. 전체 `pytest tests/`, `scripts/check_docs.py`, ADR-048 기록.

## 5. 호환성·v1 의존

- API 변경은 모두 추가 필드라 하위호환. 단 `salience.fresh` 의미 변경(D6)을 택하면 목록 정렬·강조가 달라진다.
- `readiness_decision` 헤드라인은 v2 `/today`, `coach_evidence`(Coach 규칙 경로)가 공유 → 유보 문구가 Coach 근거에도 나간다(의도된 일관성이지만 Coach 응답 변화).
- v1(`src/web/views_dashboard_cards_*`, `views_ai_coach_cards` 등)은 metric_store를 직접 읽으므로 이 설계의 혜택을 받지 않고 85 "좋음"을 계속 표시한다. v1 제거 예정(ADR-046)이라 수정하지 않는 것을 전제로 한다.
- AI 컨텍스트 빌더(`src/ai/context_builders.py` 등)는 UTRS 값만 싣는다. 신선도 전달은 범위 밖(메모 참고).
- 메트릭 값·DB 스키마·Calculator 무변경 → 재계산 불필요.

## 6. 대안 비교

| | A안: 읽기 시점 서비스 판정 (추천) | B안: 계산 시점 게이팅 |
|---|---|---|
| 방식 | 저장값 유지, 서비스가 입력 경과일·confidence로 `freshness` 산출 | UTRS가 웰니스 전무 또는 coverage 하한 미만이면 `[]` 반환하거나 재정규화를 중립값 대체로 변경 |
| 장점 | 스키마·재계산 없음, 모든 메트릭에 같은 규칙, 결손 원인 설명 가능 | 잘못된 값 자체가 생기지 않음, v1·AI 컨텍스트도 자동 혜택 |
| 단점 | 저장값 85는 그대로라 서비스 경유하지 않는 소비처(v1, AI)엔 미반영 | Calculator 버전 증가·`algo_changelog`·전체 재계산, 과거 이력 값 변경, 웨어러블 없는 사용자는 UTRS 영구 공백, "얼마나 오래됐는지" 설명은 여전히 서비스 몫 |

추천: A안. B안의 재정규화 정책 변경은 지표 정의 문제라 별도 결정(D7)으로 분리한다.

## 7. 결정 필요

- **D1 stale 기준 경과일**: 입력 웰니스가 N일 이상 없으면 stale. 선택지 1일(당일 없으면 stale — 엄격, 아침 동기화 전엔 매일 경고) / 2일(하루 지연 허용) / 3일 이상(경고 적음, 이번 결측 같은 장기 공백만 잡음).
- **D2 partial 기준**: confidence 하한(예: 0.5 미만) / "웰니스 성분 0개"일 때만 / 둘 다. 하한이 높을수록 경고가 잦다.
- **D3 stale·partial 시 UTRS 표시**: (a) 값·등급 유지 + 배지 (b) 값 유지, 등급 라벨 숨김 또는 회색 (c) 값 숨기고 "데이터 수집 중". (a)는 정보 손실 없음·단정 위험 남음, (c)는 가장 안전·TSB 기반 신호 손실.
- **D4 문구**: 배지 문구, 유보형 헤드라인 문구, 상세 "MM-DD 기록 기준" 표기 문구.
- **D5 caveat 병합**: 히어로에서 동기화 `source_missing`과 데이터 `freshness` 경고를 (a) 둘 다 (b) freshness 하나로 병합 (c) caveat만 유지하고 헤드라인만 유보형.
- **D6 `salience.fresh` 의미**: 행 날짜 기준 유지 / 입력 신선도 기준으로 변경(목록 강조 순서 변화).
- **D7 UTRS 재정규화 정책(B안 요소)**: 현행 유지 / 웰니스 0개면 미산출 / 결측 성분을 중립값으로 대체. 변경 시 버전 증가·재계산·과거 값 변경 동반.
- **D8 2차 적용 범위**: `crs`·`rmr`·`rtti`까지 같은 SPEC으로 확장할지, 시점.

## 8. 범위 밖 메모

- `today_service.py`(320줄), `db_helpers.py`(754줄)가 이미 300줄 규칙 초과 — 별도 분리 작업.
- AI·Coach 컨텍스트(`src/ai/context_builders.py`, `chat_context_rich.py`)에 지표 신선도 전달 없음.
- T-03의 "ACWR 0.67(저부하)과 결이 다름"은 지표 간 일관성 문제로 신선도와 별개.
- `get_metric_trend`의 `change_pct`·`peak` 산식 문제(M-03, M-04)는 trend 분리 시 건드리지 않는다.
