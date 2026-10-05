# DESIGN-U17 — UX 후속 4건 (S6 §8-1..4 · 내러티브 캐시 워밍 · MonthNarrative 레이어링 · ◆ 알고리즘 버전 마커)

> 작성 2026-10-05 · 상태: 설계안(사용자 승인 대기) · 코드·DB 변경 없음
> 전제: 파일 ≤300줄, Calculator raw SQL 금지(ADR-009, CalcContext), 신규 함수당 테스트 ≥1, sync 중단 금지, 메트릭 없음 → "데이터 수집 중".
> 이미 설계된 것은 다시 설계하지 않는다: S6 본체(DESIGN-S6-IMPL, ADR-021), ▲대회·◇기준대회 마커(B-6), narrative 지연 로드(IMPL-PROGRESS 2-6 4차), U15·U16·U18.

## 0. 결정 요약

| # | 항목 | 권장 결정 | 규모 | DB 변경 |
|---|---|---|---|---|
| A | S6 §8-1..4 | 현행 임시 구현(①scale ②EF definition ③접힘 목록)을 **확정**하고 ADR-021에 기록. ④`training_load_score`→`training_load` 교정은 **적용**하되 활동 탭 회귀 확인 단위를 따로 둔다 | S | 없음 |
| B | 내러티브 캐시 워밍 | 동기화 완료(메트릭 재계산 **뒤**)에 **이번 달 1건만** 백그라운드 사전 생성. 동의(D8) 없으면 워밍 금지. 일 호출 상한 3회. 실패 시 아무것도 쓰지 않음(요청 시 기존 규칙 기반 폴백) | M | `ai_cache` 행 쓰기만 |
| C | MonthNarrative | (C1) 오버레이 → 라우트 `/today/month/[ym]`로 바꿔 DrillPanel과 겹치지 않게 함. (C2) 월간 프롬프트 입력을 **주간 다이제스트(규칙 기반, LLM 아님)** 4~5개로 계층화 | M | 없음 |
| D | ◆ 버전 마커 | `/trend` 대표 시계열 안에서 `(provider, algorithm_version)`이 바뀐 첫 날에 ◆. 전 기간 재계산이라 시계열 안의 불연속이 없으면 ◆ 대신 캡션 1줄("9/26부터 계산 v2 · 전 기간 다시 계산됨") | S+M | 없음 |

## 1. 근거 조사 (실 DB 사본 `/tmp/u18_ro.db`, 읽기 전용)

- **S6:** `src/utils/provider_matrix_rows.py`(116줄)에 training_load·ctl이 이미 `compare="scale"`. `ProviderMatrix.svelte`는 `single_source[]`를 "한 소스에만 있는 지표 n개" 접힘으로 이미 렌더. `metric_groups.py:30`에는 여전히 `("training_load_score","intervals")`가 남아 있음 → §8-1·2·3은 **안대로 구현 후 승인만 미결**, §8-4만 미적용.
- **내러티브 캐시:** `_narrative.get/set_narrative_cache` → `ai_cache` tab=`today_narrative`, key=`{month_start}:{date}`. 신선도는 `ai_cache._is_fresh`: TTL 8h + 지문 `today|MAX(activity_summaries.id)|MAX(daily_wellness.date)`. **문제:** 지문에 메트릭 재계산이 없어서, 활동은 그대로인데 재계산만 일어난 경우(예: PMC v2 전 기간 재계산) 낡은 문장이 8h까지 남는다.
- **동기화 완료 지점:** `src/web/bg_sync.py:192~` `status="completed"` → `metrics_engine.run_for_date_range` → `record_snapshots` → 계획 매칭. 파일이 이미 498줄이므로 **새 로직은 별도 모듈**, bg_sync에는 호출 3줄만 넣는다.
- **동의:** `chat_engine` 은 `consent`/`require_consent` 로 외부 호출을 막는다. today narrative 경로는 현재 동의를 확인하지 않는다(별도 확인 필요 — §8 결정 B-1).
- **오버레이 충돌:** `MonthNarrative.svelte:127`과 `DrillPanel.svelte:131` 모두 `fixed inset-0 z-50`. MonthNarrative 안 evidence 칩이 DrillPanel을 열면 같은 z층에서 DOM 순서로 겹친다(IMPL-PROGRESS:121). `today_service.py`는 299줄.
- **버전:** 일별 행은 provider별로 전 기간 단일 버전(예: ctl `runpulse:formula_v1` 2.0 1073행, intervals 1.0). 여러 버전은 **provider 차이**에서 온 것. `milestones`에 `algo_recompute` 4행(2026-09-26, race_pred_* 1.0→2.0) — 단 `_MILESTONE_TRACKED_METRICS` 7개 지표만 기록, `date`는 **재계산 실행일**. PMC v2(ctl/atl/tsb)는 ctl만 추적 대상.
- **부분 재계산 위험:** Calculator `version`을 올린 뒤 동기화가 최근 N일만 재계산하면 한 시계열 안에 1.0/2.0이 섞인다 — 이것이 ◆가 정말 필요한 진짜 불연속이다. `/trend`는 `is_primary=1`만 읽으므로 대표 provider가 바뀌는 날도 같은 종류의 불연속이다.

## 2. A — S6 §8-1..4

**사용자 시나리오.** Intervals에서 Load 85, Garmin에서 Training Load 160을 본 러너가 "누가 맞아?"를 묻는다. 답은 "둘 다 맞고 척도가 달라요"여야 하며 ⚠는 오해를 키운다.

| § | 결정 | Level 0 표현 | 근거 |
|---|---|---|---|
| 8-1 | training_load·ctl = `scale`. % 차이와 ⚠ 없음, "척도 ×1.9 (IQR 1.7–2.1)" | "정의가 다른 부하라 비율로 봐요. 비율이 일정하면 정상이에요" | EPOC·HR부하·HRSS는 다른 양 |
| 8-2 | EF = `definition`. 환산 규칙 확정 전 비교 안 함 | "Intervals와 RunPulse는 EF 단위가 달라 비교하지 않아요" | 실측 11.5배, ÷1000 불일치 |
| 8-3 | 한 소스 행 = 표 밖 접힘 목록(현행) | 접힘 라벨 "비교 상대가 없는 지표 n개 ›" (현 문구 "한 소스에만 있는 지표"를 S6 설계 문구로 정정) | `—` 줄이 표의 절반을 차지하면 스캔 비용 증가 |
| 8-4 | `metric_groups.py:30` 교정 적용 | 활동 상세 "소스 비교" 탭에 Intervals 부하 열이 새로 나타남 | 615건 노출, 이름 버그 |

- **API 계약:** 변경 없음(ADR-021 응답 그대로). 8-4는 `SEMANTIC_GROUPS` 1튜플 교체.
- **프론트:** `ProviderMatrix.svelte` 접힘 라벨 문구 1곳. 활동 탭 `ProviderComparison.svelte`는 새 열이 `scale` 의미임을 몰라 % 차이 ⚠를 띄울 수 있음 → training_load 행에 한해 차이 칩 대신 "척도 다름 ›"(탭 시 `/library/providers/training_load` 이동). 판정은 `compare_group_for_slug(slug).compare == "scale"`을 서버가 내려 주는 기존 필드로 하고 프론트 하드코딩 금지.
- **거부한 대안:** 8-1 % 유지(⚠ 남발), 8-2 ÷11.5 경험 환산(근거 없는 상수), 8-3 `—` 셀 유지, 8-4 매트릭스만 교정(두 화면 불일치).
- **완료 기준:** ADR-021에 8-1..4 "확정" 기록, 활동 탭에서 Intervals 부하가 보이고 ⚠가 뜨지 않음(실 DB 사본 Playwright), 기존 S6 스모크 `pw/s6_providers.mjs` 회귀 없음.

## 3. B — 내러티브 캐시 워밍

**첫 3초 목표.** 아침에 Today를 열면 "이번 달 이야기"가 스켈레톤 없이 이미 있다. 지금은 동기화 직후 첫 방문자가 LLM 지연(수 초)을 떠안는다.

### 3.1 결정
- **트리거:** `bg_sync` 완료 → 메트릭 재계산·예측 스냅샷 **이후**(순서 필수: 재계산 전 문장은 바로 낡음). 크론(06:00)은 쓰지 않는다 — 입력이 바뀌는 시점은 동기화뿐.
- **범위:** 오늘이 속한 달 1건(`month_start:today`). 과거 달은 요청 시 생성(현행).
- **가드(순서대로 하나라도 거짓이면 건너뜀, 로그만):** ① AI 내러티브 동의(D8) 있음 ② 이미 신선한 캐시 없음 ③ 오늘 워밍 호출 < `WARM_DAILY_CAP=3` ④ 같은 사용자 워밍 실행 중 아님(프로세스 내 lock).
- **비용 상한:** 동기화 1회당 최대 1호출, 하루 3호출. 카운터는 `ai_cache` tab=`today_narrative_warm`, key=`YYYY-MM-DD` 행의 `{"calls": n}`(새 테이블 없음).
- **실패 폴백:** 예외·타임아웃(20s)·파싱 실패 → 캐시에 아무것도 쓰지 않음, `sync_jobs.last_error`에 남기지 않음(동기화 실패처럼 보이면 안 됨, 로그만). 사용자 요청 시 기존 경로(LLM 시도 → 실패 시 `rule_narrative`)가 그대로 동작.
- **신선도 보강:** 지문에 `MAX(metric_store.updated_at)`(daily ctl 한 행만) 추가 → 재계산만 있어도 무효화. `ai_cache._compute_fingerprint`는 모든 tab 공용이라 영향 범위를 테스트로 고정.

### 3.2 계약
- `src/services/narrative_warm.py`(신규, ~90줄): `warm_month_narrative(conn, today: str, *, consent_ok: bool, now=None) -> str` → 반환 `"warmed"|"fresh"|"no_consent"|"capped"|"failed"`. 내부에서 `today_service.get_narrative(conn, date=today)`를 호출하고 결과 `source=="ai"`일 때만 성공으로 센다(규칙 문장은 캐시 안 됨 — 현 규약 유지).
- `bg_sync.py`: 메트릭 블록 직후 `threading.Thread(daemon=True)`로 위 함수 호출(3줄). 동기화 완료 응답을 늦추지 않는다.
- 프론트 변경 없음. 선택: 응답의 `generated_at`으로 L2 하단 "오늘 07:12 동기화 후 작성" 캡션(투명성).

### 3.3 거부한 대안
- 06:00 크론: 동기화가 없으면 같은 입력으로 반복 호출 / 동기화가 늦으면 낡음.
- 규칙 문장 먼저 → LLM 교체(C안): 화면에서 문장이 바뀌는 "깜빡임"이 신뢰를 깎음. 단, 동의 없는 사용자에게는 이미 이 상태(규칙 문장만).
- 지난달·주간까지 일괄 워밍: 비용 대비 방문 빈도 낮음.

### 3.4 완료 기준
동기화 후 첫 `/today/narrative`가 캐시 적중(서버 로그 + Playwright 응답시간 < 300ms), 동의 끔 상태에서 외부 호출 0건(목 프로바이더 호출 수 검증), 하루 4번째 동기화에서 `capped`.

## 4. C — MonthNarrative

### 4.1 C1 레이어링 (BACKLOG의 "레이어링 검증")
- **결정:** 오버레이를 라우트로 바꾼다 — `/today/month/[ym]`(예 `2026-10`). 뒤로 가기·공유·새로고침이 자연스럽고, 그 화면 위의 DrillPanel이 유일한 오버레이가 된다(§C3.1 "오버레이 하나").
- **진입:** Today의 `onMonth` 2곳 → `goto('/today/month/' + ym)`. 월 이동 ‹ › 는 `replaceState`(히스토리 오염 방지), 닫기 ‹ = 뒤로.
- **정보 계층:** L0 한 문장(월 이야기 첫 문장) / L1 근거 칩 3~5(CTL 변화·거리·최장·수면) / L2 월간 CTL·ATL 차트 + 마일스톤 + 주간 다이제스트 펼침(C2).
- **파일:** `routes/today/month/[ym]/+page.svelte`(MonthNarrative 본문 이동, ≤250줄) + `+page.ts`. `MonthNarrative.svelte`(284줄)는 오버레이 껍데기 제거 후 본문 컴포넌트로 축소하거나 삭제.
- **거부:** z-index 규약만 정하기(B안) — 두 모달 중첩·포커스 트랩 2개·스크롤 잠금 충돌이 남음. DrillPanel 스택 항목화 — 월 화면은 drill이 아니라 독립 목적지.

### 4.2 C2 주간→월간 계층 (요청 범위)
**의도.** 월 이야기가 "이번 달 CTL +6"만 말하지 않고 "2주차 롱런이 전환점이었어요"처럼 주 단위 근거를 짚게 한다. 동시에 프롬프트 토큰을 줄인다.

- **주간 다이제스트(규칙 기반, LLM 없음)** `src/services/week_digest.py`(신규, ~120줄, 서비스이므로 SQL은 `db_helpers` 경유):
  `week_digest(conn, week_start: str) -> WeekDigest`
  ```
  {week_start, week_end, run_count, distance_km, long_run_km, quality_count,
   ctl_start, ctl_end, tsb_min, sleep_avg, plan_done, plan_total,
   flags: ["peak_week"|"deload"|"missed_long"|"race"...], partial: bool}
  ```
  데이터 없음 → 값 `None`, `flags=[]`(에러 아님). `partial`은 진행 중인 주.
- **월간 입력:** `build_narrative_prompt`에 `weeks: list[WeekDigest]`(월요일 시작, 달과 겹치는 주 4~6개)를 추가. 프롬프트 지시: "주 번호를 인용할 때는 `(W2 롱런 28km)` 형식". 출력 계약은 기존 `{text, source, evidence, highlights}` + `weeks_cited: [week_start]`(선택). evidence 칩이 주를 가리키면 `{"type":"week","week_start":...}` → 탭 시 L2 주간 펼침으로 스크롤.
- **캐시 키:** 월간 키는 그대로 `today_narrative:{month_start}:{date}`. 주간 다이제스트는 결정적·저비용이므로 **캐시하지 않는다**. 지난 달은 `date`가 그달 말일로 고정되므로 자연히 영구 적중(지문 변화 시만 재생성).
- **거부:** 주간도 LLM 문장 생성 후 월간에 연결(호출 5배, 오류 전파) / 월간 원시 일별 행 전체 투입(토큰 과다, 주 단위 맥락 손실).

## 5. D — ◆ 알고리즘 버전 마커

**질문.** "9월 말에 CTL이 갑자기 4 뛰었는데, 내가 뭘 한 거야?" — 답이 "계산식이 바뀌었어요"라면 그 사실이 차트 위에 있어야 한다(메트릭 진화 추적 = 차별점).

### 5.1 의미 규칙
1. **시계열 내 불연속(◆ 점 마커):** `/trend` 대표 시계열에서 전날 대비 `(provider, algorithm_version)`이 달라진 첫 날. 라벨: 버전만 바뀜 → "계산 방식 변경: v1.0→v2.0", provider만 바뀜 → "출처 변경: Intervals→RunPulse".
2. **전 기간 재계산(캡션, ◆ 점 없음):** 시계열 안 불연속이 없지만 `milestones.type='algo_recompute'`가 이 지표에 있으면 차트 아래 캡션 1줄 "9/26부터 계산 v2.0 · 과거 값도 모두 다시 계산됐어요 ›". 이 날짜에 점을 찍으면 그날 값이 튄 것처럼 오해하므로 찍지 않는다.
3. 기간 밖 이벤트는 표시 안 함. 같은 날 ▲·◇·◆가 겹치면 readout에 모두 나열, 축 아래 기호는 ◆ > ◇ > ▲ 우선 1개.

### 5.2 계약
- `src/services/metrics_version_events.py`(신규, ~80줄, B-6 `metrics_basis_events.py` 패턴):
  - `version_change_events(conn, slug, d0, d1) -> list[{date, kind:"version_change", from, to, label}]` — `get_metric_history(..., scope_type="daily")` 대표 행의 `provider`·`algorithm_version` 순회. 행에 해당 컬럼이 없으면 `db_helpers`에 컬럼만 추가 노출.
  - `recompute_note(conn, slug, d0, d1) -> {date, from, to, text} | None` — `milestones` `algo_recompute` 최신 1건.
- `metrics_browser_service.py`(295줄, 여유 5줄): `events` 합치는 줄에 `+ version_change_events(...)` 1줄, `"recompute_note": recompute_note(...)` 1줄. 초과 시 events 조립을 `metrics_trend_events.py`로 이동(▲·◇·◆ 한곳).
- 프론트 `TrendChart.svelte`: 기호 분기 `basis_change ◇ / version_change ◆ / race ▲`, ◆ 색 `--color-semantic-amber`(주의, 위험 아님). readout 라벨 확장. 캡션은 `trend/+page.svelte`에서 `recompute_note`가 있으면 렌더, ›는 메트릭 explain의 "계산 버전" 블록(`metrics_explain.py:227` version 필드)으로 이동.
- `types/index.ts` events kind 유니온에 `version_change` 추가, `recompute_note` 필드.
- 미추적 지표(atl/tsb 등): 캡션은 없음. `_MILESTONE_TRACKED_METRICS` 확장은 sync 성능 영향이 있어 이번 범위 밖(§8 D-2).

### 5.3 거부한 대안
신규 `metric_events`/changelog 테이블(단일 저장소 원칙 대비 이득 적음, milestones가 이미 기록) / milestones 날짜에 ◆ 점(전 기간 재계산을 불연속으로 오인) / 모든 provider 시계열에 ◆(대표 시계열만 차트에 그림).

### 5.4 완료 기준
합성 DB(한 시계열에 1.0/2.0 혼재, provider 전환 1회)에서 ◆ 2개·라벨 정확, 실 DB 사본 race_pred_marathon 90일 → ◆ 0개·캡션 1줄(9/26 v1.0→v2.0), ctl → 둘 다 없음.

## 6. 구현 단위(U17a..)와 순서

| 단위 | 내용 | 파일 | 규모 | 선행 |
|---|---|---|---|---|
| U17a | §8 확정 기록 + 8-4 교정 + 활동 탭 scale 칩 + 접힘 문구 | `metric_groups.py`, `ProviderComparison.svelte`, `ProviderMatrix.svelte`, `decisions.md` ADR-021 | S | §8-1..4 승인 |
| U17b | ◆ 서버 이벤트·캡션 | `metrics_version_events.py`(신), `metrics_browser_service.py`, (`db_helpers.get_metric_history` 컬럼) | S | — |
| U17c | ◆ 프론트 | `TrendChart.svelte`, `trend/+page.svelte`, `types/index.ts` | S | U17b |
| U17d | 지문 보강 | `ai_cache.py` | XS | — |
| U17e | 워밍 | `narrative_warm.py`(신), `bg_sync.py` 3줄 | M | U17d, D8 결정 |
| U17f | MonthNarrative 라우트화 | `routes/today/month/[ym]/*`, `today/+page.svelte`, `MonthNarrative.svelte` 축소 | M | — |
| U17g | 주간 다이제스트 + 월간 프롬프트 계층 | `week_digest.py`(신), `_narrative.py`(204줄) 프롬프트, 월 화면 L2 주간 펼침 | M | U17f |

병렬 가능: {U17a}, {U17b→c}, {U17d→e}, {U17f→g}. 권장 실행 순서: a → b·c → d·e → f → g (사용자 체감 대비 위험 순).

## 7. 테스트 계획 (신규 함수당 ≥1)

- U17a: `test_metric_groups` 교정 튜플, 활동 비교 서비스가 training_load 행에 `compare=scale` 반환.
- U17b: `test_metrics_version_events` — 혼재 버전 ◆1, provider 전환 ◆1, 단일 버전 0, 데이터 없음 `[]`; `recompute_note` 있음/없음.
- U17c: `trendChart.ts` 순수 헬퍼(기호 우선순위) 노드 테스트 + Playwright 스모크.
- U17d: 지문이 metric 재계산 시 바뀜, 다른 tab 캐시 동작 불변.
- U17e: `warm_month_narrative` 5개 반환값 각각(목 프로바이더·고정 now), 실패 시 캐시 행 0, 동기화 경로 예외 비전파.
- U17f: Playwright — 월 화면에서 칩 → DrillPanel 1개만 `aria-modal`, 뒤로 가기로 Today 복귀, ‹ › 히스토리 길이 불변.
- U17g: `week_digest` 정상/빈 주/진행 중 주, 프롬프트에 W 블록 포함, 출력 `weeks_cited` 누락 시 정상 처리.

전부: `pytest` 통과, `check_docs.py` 0 오류, `gen_files_index.py` 재생성, 브라우저 실검증(성능 작업 포함).

## 8. 열린 결정 (사용자 판단)

- **A-1..4** S6 §8-1..4 확정 여부(위 권장안).
- **B-1** today narrative 경로가 현재 D8 동의를 확인하지 않는 것으로 보임 — 워밍뿐 아니라 요청 시 생성에도 동의 가드를 적용할지.
- **B-2** 하루 워밍 상한 3회 / 타임아웃 20s 적정 여부.
- **C-1** 월 화면 URL `/today/month/[ym]` vs `/library/month/[ym]`.
- **C-2** 주간 다이제스트를 Today L2에도 노출할지(WeekStrip과 중복 검토).
- **D-1** ◆·캡션을 일반 사용자에게 상시 노출할지(1-1 PMC v2 1회성 알림과 중복). 권장: 노출 — "계산 과정 투명 공개"가 차별점.
- **D-2** `_MILESTONE_TRACKED_METRICS`에 atl·tsb 추가(PMC 캡션 완결) 여부 — sync 비용 측정 후.
