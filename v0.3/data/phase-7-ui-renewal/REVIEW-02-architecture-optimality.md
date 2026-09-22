# REVIEW-02 — 아키텍처 최적성 관점 UI 설계 검토

> **검토 대상**: `v0.3/data/phase-7-ui-renewal/` (00~07 설계서 + BACKLOG.md)
> **근거 문서**: `architecture.md` (v0.3.1), `decisions.md` (ADR-001~011),
> `phase-3.md` (Sync/Reprocess), `phase-4.md` (Metrics Engine)
> **검토일**: 2026-06-10
> **검토 관점**: REVIEW-01(정합성/오탈자 검토)과 달리, 본 문서는
> **"아키텍처의 고유 강점을 UI가 최대한 활용하는 최적 설계인가"** 를 평가한다.

---

## 0. 요약

REVIEW-01은 설계서 간 표기 일치(교정·proofreading)를 다뤘다. 본 검토는 한 단계
위에서 **architecture.md가 의도한 "업계에 없던 최적 설계"의 4대 강점을 UI가
실제로 살리는가**를 본다.

| 아키텍처 강점 | UI 계승도 | 비고 |
|---|---|---|
| ① Provider 추상화 (전 소스 보존 + primary 선택) | 부분 (6/10) | 비교 UI는 있으나 primary 근거가 데이터와 불일치 (F3) |
| ② metric_store EAV 확장성 (소스/종목/ML/버전 무한 확장) | 낮음 (3/10) | 매트릭스 세로축 고정, 버전 표현 없음 (F1·F2) |
| ③ 재처리 가능성 (공식·ML 갱신 후 과거 재계산) | **없음 (1/10)** | **가장 성숙하게 구현됐으나 UI에 신호 0** (F1) |
| ④ SSOT 투명성 (metric_registry 단일 정의·추적성) | 높음 (9/10) | EvidenceQuote·Drillable로 잘 계승 |

**결론**: ④는 우수, ①은 보정 필요, **②·③은 사실상 미활용**.
가장 시급한 보강은 ③(메트릭 진화/재처리의 UI 표현)이다.

---

## F1. 메트릭 진화·재처리가 UI에 전혀 드러나지 않음 (최우선)

### 근거 (데이터 레이어는 이미 완성됨)
- **`phase-4.md` §4-4**: Metrics Engine은 metric_store에 쓸 때
  `provider='runpulse:formula_v1'` 로 **버전을 provider 문자열에 인코딩**한다.
- **`phase-4.md` §4-4**: `clear_runpulse_metrics()` 는
  `provider LIKE 'runpulse%'` 로 동작 → `formula_v2`, `ml_v1` 등이
  공존·교체 가능한 구조.
- **`phase-3.md` §3-8**: `reprocess_all()` (Extractor 경로) 구현·테스트 완료(DoD ✅).
- **`phase-4.md` §4-4·§4-8**: `recompute_all()` (Engine 경로) 구현·테스트 완료
  (DoD 7번 "재계산 동일 결과 재현" ✅).

→ 즉 **재처리는 두 경로 모두 구현 완료된, 가장 성숙한 강점**이다.

### 문제
- `04-component-catalog.md` 의 `ProviderKey` enum:
  `garmin|strava|intervals|runalyze|runpulse` — **버전 접미사 없음**.
  데이터에 실재하는 `runpulse:formula_v1` 값을 UI가 표현하지 못한다.
- 00~07 어디에도 다음이 없다:
  - 마지막 재계산 시각 ("이 지표는 2026-06-09에 재계산됨")
  - 적용된 공식/ML 버전 (`formula_v1`)
  - 이전 버전 대비 값 변화 (diff)

### 권고
1. `ProviderKey` 를 `runpulse:${string}` 패턴 수용하도록 확장
   (예: `'runpulse:formula_v1' | 'runpulse:ml_v1'`).
2. `<MetricCell>` 배지: RunPulse 메트릭은 버전·confidence 노출
   ("RunPulse · formula_v1 · conf 0.82").
3. `<MetricBreakdown>` 패널: 최종 계산 시각 + 공식 버전 + (가능 시) 직전 값 diff.
4. Story/Timeline 영역: "지표 재계산됨" 이벤트를 narrative 항목으로 노출 가능.

---

## F2. Library 매트릭스 — 가로축은 OK, 세로축이 고정되어 EAV 확장성 위배

### 정정 (REVIEW-01 대비)
이전 검토에서 "13×4 매트릭스의 13이 하드코딩"이라 본 것은 **부정확**했다.
- **`phase-4.md` §4-5**: `SEMANTIC_GROUPS` 가 **코드에 13개로 명시 정의**됨
  (`src/utils/metric_groups.py`). → 가로축 13그룹은 SSOT 반영이며 정당.

### 실제 문제: 세로축(provider)이 그룹마다 다른데 UI는 "× 4" 고정
`SEMANTIC_GROUPS` 의 비교 소스는 그룹별로 상이하다:

| 그룹 | 비교 소스 (phase-4 §4-5) |
|---|---|
| trimp | intervals (1개) |
| training_load | garmin, intervals, strava (3개) |
| training_trend | — (없음) |
| readiness | garmin |
| race_prediction | — (없음) |
| vo2max / vdot | garmin, runalyze |

→ "13 × 4 고정 매트릭스"는 빈 칸을 양산하고, Apple Health·COROS·Whoop·Polar
추가 시(architecture.md 미래 확장 시나리오) 세로축이 자동 확장되지 않는다.

### 권고
- 가로축: `SEMANTIC_GROUPS` 13개 고정 (현행 유지).
- 세로축: **그룹별 비교 소스 ∪ 실제 연결된 provider 집합**으로 동적 렌더링.
- 데이터 출처: `metric_registry` + 연결 provider 목록 → 신규 소스 추가 시
  코드 수정 없이 매트릭스 확장.

---

## F3. is_primary 근거 — UI가 데이터 레이어에 없는 동적 로직을 가정함

### 근거 (정적 우선순위가 코드 진실원)
- **`phase-3.md` §3-7**: `v_canonical_activities` 뷰가
  `garmin > intervals > strava > runalyze` **정적 순서**로 대표 1건 선택.
- **`phase-3.md` §3-5**: `resolve_primaries` → `resolve_all_primaries` 가
  metric_store의 `is_primary` 를 이 규칙으로 결정.
- **`decisions.md` ADR-003**: metric_store UNIQUE `(scope_type, scope_id,
  metric_name, provider)` + `is_primary` 플래그 구조만 정의(근거 로직은 미정의).
- **`architecture.md`**: "is_primary 결정 = 우선순위 garmin > intervals >
  strava > runalyze, RunPulse 자체 메트릭은 always primary".

### 문제
- `04-component-catalog.md` 의 `<ProviderComparison>` `primaryReason` 모델이
  `coverage` / `manual` / `default_order` 같은 **동적 근거**를 가정.
  → 데이터 레이어에 존재하지 않는 로직. UI가 발명한 것.

### 정정 사항 (이전 PATCH 메모 오류 포함)
- 이전 PA-2/PATCH 메모의 "metric_priority.py / ADR-003 근거"는 부정확.
  **실제 진실원은 `dedup.py` + `v_canonical_activities` 뷰의 정적 순서**.

### 권고 (택1)
- (A·권장) UI는 정적 순서를 근거로 표시:
  "Garmin — 소스 우선순위 1순위" / "RunPulse — 자체 산출(always primary)".
- (B) 동적 근거(coverage 등)를 원하면 **데이터 레이어 신규 설계가 선행**돼야 함
  (현 구조는 정적 순서만 지원).

---

## F4. Fat Summary vs metric_store 경로가 서비스 API에 구분 안 됨 (성능)

### 근거
- **`architecture.md`** "Fat Summary + Metric Store" 하이브리드:
  센서·단순 파생값은 `activity_summaries`(빠른 경로), 알고리즘·ML 결과는
  `metric_store`(EAV). 행 수: summaries ~600 vs metric_store ~55k.
- **`07-migration-roadmap.md`**: API 응답 목표 < 200ms.

### 문제
- 서비스 레이어(D5)·API에서 `get_activity_detail()` 등이 두 경로를 구분하지
  않으면, 요약 화면(Today 트렌드 등)에서도 metric_store(55k EAV)를 조회해
  200ms 목표를 위협할 수 있다.

### 권고
- 서비스 레이어에서 요약/트렌드는 `activity_summaries` 직조회,
  상세 드릴다운만 `metric_store` 조회로 경로 분리 명시 (06 또는 05에 정책 추가).

---

## 우선순위 (다음 에이전트용)

| 순위 | 항목 | 보강 대상 문서 |
|---|---|---|
| **AO-1** | 메트릭 진화 표현 (버전 배지 + 재계산 시각/diff) | 04(ProviderKey), 03(MetricBreakdown 화면), 01(원칙 보강 검토) |
| **AO-2** | Library 매트릭스 세로축 동적화 | 03(화면), 04(ProviderComparison) |
| **AO-3** | is_primary 정적 근거로 정렬 (동적 근거 제거) | 04(primaryReason 모델), 06(D2 백필 주석) |
| **AO-4** | 서비스 API 경로 분리 (summary vs metric_store) | 05 또는 06 |

> **주의**: AO-3은 이전 PATCH 메모의 "metric_priority.py/ADR-003" 표현이
> 부정확했으므로, 근거를 `dedup.py` + `v_canonical_activities`(정적 순서)로
> 정정해 반영할 것.

---

## 변경 이력
| 날짜 | 내용 |
|---|---|
| 2026-06-10 | REVIEW-02 최초 작성. phase-3/phase-4 정독 기반 F1~F4 도출. REVIEW-01의 13×4 매트릭스 판단(F2) 및 PATCH의 is_primary 근거(F3) 정정 포함. |
