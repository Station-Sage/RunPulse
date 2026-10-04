# DESIGN-PENDING-12 — Phase 3 보류 12건 설계안 (2026-10-04)

출처: `../BACKLOG.md [P7-UXR-DESIGN-PENDING]`(185~200행). 작성 방식은 읽기 전용 조사이며, 코드와 DB는 바꾸지 않았다.
근거 표기 규칙은 다음과 같다. `파일:줄`은 이번 조사에서 grep이나 Read로 직접 확인한 것이다. "문서 근거"는 IMPL-PROGRESS나 design.md의 기술만 보고 코드에서는 다시 확인하지 않은 것이다. "미확인"은 코드에서 확인하지 못한 것이다.
조사가 턴 한도로 일찍 끝나서 항목 5·6·7·8·10은 코드 확인이 불완전하다. 착수할 때 (a)를 다시 확인해야 한다.

## 요약 표

| # | 항목 | 권장안 | 규모 | 실 DB 변경 | 사용자 결정 |
|---|---|---|---|---|---|
| 1 | UTRS 입력 드릴 | 입력 항목 `drill`을 원천 wellness 슬러그(`m.hrv_weekly_avg` 등)로 지정하고, DrillPanel은 미지원 슬러그를 "추세로 이동"으로 처리 | S | 없음 | 패널 안 이동인지 페이지 이동인지 |
| 2 | RRI 등급 SSOT | `bands.py`에 `rri` 추가(Calculator `ranges`는 유지). 분해는 현행 factor 표현 유지 | S | 없음 | 등급 라벨 문구 |
| 3 | D1d `@a{id}` | 토큰 문법만 먼저 추가하고, 활동 explainer는 TRIMP 1종부터 | M | 없음 | 활동 drill 대상 지표 범위 |
| 4 | S1b PMC·GAP | 대부분 1-1·1-7에서 흡수됨. 남은 3건만 분리 등록 | S(정리) | 잔여 중 일부 있음 | 잔여 3건 착수 여부 |
| 5 | 3-10 RPE·`⋯` | D3 안 A(`activity_feedback`) ADR 초안. **사용자 승인 전 착수 금지** | M | 스키마 추가(마이그레이션) | ADR 승인 |
| 6 | 3-16(D4) | 2단계(백테스트 → 새 계획에만 적용). **사용자 승인 전 착수 금지** | L | 없음(새 계획만) | D4 승인·백테스트 기준 |
| 7 | 내러티브 캐시 워밍·MonthNarrative | 동기화 완료 훅에서 1회 사전 생성 + 기존 캐시 키 재사용. 레이어링은 MonthNarrative를 라우트/시트로 변경 | M | 캐시 행만 | LLM 호출 예산 |
| 8 | 목표 달성 가능성·`x.taper`·예측 explain | `race_pred_marathon_sec` explainer(입력 조회 `produces` 수정) → `x.taper` → 가능성 순서 | M+M | 없음 | 가능성 표현 방식 |
| 9 | S2 이월 | min_span·끝점·캡션 먼저, 이벤트 마커는 `metric_store` 버전 변경 + 대회 목록에서 파생(새 테이블 없음) | S+M | 없음 | ◆ 버전 마커 노출 범위 |
| 10 | 계정 설정·sync_jobs 확장 | D5·D6 권장안대로. `user_settings` key-value + `sync_jobs` 열 추가(추가형) | M | 스키마 추가 | 설정 저장 위치 |
| 11 | 다운샘플·SWR | **이미 완료**(2-6 3·5·6차). 항목 종료하고 잔여(narrative 워밍)는 7로 합침 | 0 | 없음 | 종료 확인 |
| 12 | 활동 목록 기간 필터 | 기간 칩(프리셋 + 월) + 모든 필터를 URL(replaceState)에 동기화. API는 이미 있음 | S~M | 없음 | 프리셋 목록 |

## 1. UTRS 입력 항목(utrs_hrv·utrs_sleep) 드릴 대상

**(a) 현재**
- UTRS·CIRS 항목에는 `drill` 키가 없다(`src/services/metrics_explain_composite.py:44-48`, `:85-88`). TSB는 `drill` m.ctl·m.atl(`metrics_explain.py:105,108`), CTL·ATL은 `m.trimp`(`:125`)를 가진다.
- UTRS 원천은 daily_wellness 컬럼 `body_battery_high`·`sleep_score`·`hrv_weekly_avg`·`avg_stress`(`src/metrics/utrs.py:45,57,62,67`)다. 네 컬럼 모두 registry에 `storage="wellness"` 슬러그로 있다(`src/utils/metric_registry.py:129,134,146,153`). 따라서 `/library/metrics/<slug>`로 추세를 볼 수 있다(`metrics_browser_service.py:165-168`).
- 프론트 DrillPanel은 `EXPLAIN_SUPPORTED_SLUGS`(`frontend/src/lib/api/metrics.ts:5`, 6종)에 없는 슬러그에 "이 지표는 아직 분해 보기를 지원하지 않아요"를 띄운다(`DrillPanel.svelte:144-145`). **기존 결함**: CTL·ATL의 `m.trimp` drill이 이 막다른 화면으로 간다. 메트릭 상세 인라인 패널은 drill을 `goto(/library/metrics/{slug}?date=)`로 처리한다(`routes/library/metrics/[slug]/+page.svelte:52-55`).

**(b) 선택지**
- A. `drill`을 원천 wellness 슬러그로 지정(`utrs_hrv`→`m.hrv_weekly_avg`, `utrs_sleep`→`m.sleep_score`, BB·stress 동일, `utrs_tsb`→`m.tsb`). DrillPanel은 미지원 슬러그일 때 빈 문구 대신 "값·7일 평균 + 추세 보기 ›"를 보여 주는 경량 카드로 렌더한다. 장점은 백엔드 4줄이면 되고 TRIMP 막다름도 함께 해소된다는 점이다. 단점은 분해 4블록이 아닌 축약 화면이라는 점이다.
- B. 입력 지표마다 explainer 신설(HRV 개인 기준선 등). 3-18(UTRS v2, HRV z-score)과 중복되어 비용이 크다.
- C. wellness 상세(`/library/wellness?date=`)로 보낸다. 웰니스 `/:date`(21 S5)가 아직 없어서 도착지가 불완전하다.

**(c) 권장: A.** 3-18 UTRS v2가 HRV z-score를 도입하면 그때 `hrv_weekly_avg` 경량 카드를 explainer로 승격한다. `utrs_tsb`는 정규화된 값(`tsb+30`/60)이라 drill을 `m.tsb`로 두고 라벨에 "원값 TSB"를 명시한다.

**(d)** `metrics_explain_composite.py`(라벨 dict에 drill 슬러그 추가), `DrillPanel.svelte`(미지원 분기 → 경량 카드 + 추세 링크), 테스트 `test_metrics_explain.py` +2. DB 변경은 없다.

**(e)** 패널 안 스택 push(경량 카드)인지, 추세 페이지로 바로 이동인지 정해야 한다(권장은 push. 뒤로가기 스택이 유지된다).

## 2. RRI 등급 SSOT와 분해 형태

**(a) 현재**
- `bands.py:15-38`의 `BANDS`에 `rri`가 없다.
- `RRICalculator.ranges`는 insufficient 0-40 / building 40-60 / ready 60-80 / peak 80-100(`src/metrics/rri.py:27`)이고, 공식은 곱셈형이다(`:59`).
- explain의 `grade(slug)`(`metrics_explain.py:154`)가 None이라 RRI는 status가 비고, `_bands_v2`도 빈 값이다(문서 근거).
- 다른 Calculator도 `ranges`를 그대로 가진 채 `bands.py`와 병행한다(`utrs.py:21`, `cirs.py:23`, `acwr.py:29`). 따라서 "ranges 제거"는 기존 관례가 아니다.
- `check_data_consistency.py` 17번 검사는 프론트 등급 함수만 검사한다(`:360-367`). 그러므로 `BANDS`에 항목을 추가해도 이 검사에 걸리지 않는다. check_docs 영향은 미확인이다.
- 분해는 이미 `role="factor"`·`ratio` 표현으로 구현돼 있다(`metrics_explain_composite.py:96-131`).

**(b) 선택지**
- A. `BANDS["rri"]` 4구간을 추가하고 `ranges`는 유지한다(UTRS와 같은 관례). 분해는 현행 그대로 둔다.
- B. A에 더해 factor 분해에 "가장 낮은 인수 = 제한 요인" 태그를 단다(UTRS의 `loss` 1위 태그에 대응).
- C. RRI 분해를 log 합으로 바꿔 가산형 막대로 표현한다. 사용자가 이해하기 어려워서 비권장이다.

**(c) 권장: A, 이후 B.** 경계는 `ranges`와 동일하게 두고 status는 poor/caution/good/excellent로 매핑한다. B는 S3 `PredictionEvidence`와 묶는다. `bands.py` 상단 docstring의 "경계는 Calculator ranges와 같다"는 규칙에 RRI를 포함한다.

**(d)** `bands.py`(+3줄), 테스트 `test_bands`(파일명 미확인) +1. 프론트는 status를 그대로 렌더한다(변경 없음 예상, 미확인). DB 변경은 없다.

**(e)** 라벨 문구 확정(안: 부족 / 준비 중 / 준비됨 / 최적)이 필요하다.

## 3. D1d 활동 scope(`@a{id}`) explain

**(a) 현재**
- 라우트는 `scope_type` 쿼리를 그대로 넘긴다(`routes_library.py:85,97`). 그러나 explainer 6종은 모두 daily 질의이고(`get_metric_explain`, `metrics_explain.py:143-152`), 활동 scope에 대응하는 explainer가 없다.
- 프론트 토큰은 `@YYYY-MM-DD`·`@YYYY-MM`만 지원한다(문서 근거 IMPL-PROGRESS 2-5 6차). 활동 판정 칩은 기존 MetricBreakdown을 쓴다(IMPL-PROGRESS 3-6).

**(b) 선택지**
- A. 토큰 문법만 추가한다(`parseDrillToken`이 `@a17414` → `{scopeType:'activity', scopeId:'17414'}`). 활동 explainer는 TRIMP(심박 존 × 시간, 스트림 근거) 1종으로 시작하고, 나머지 활동 지표는 v1 폴백을 유지한다.
- B. 활동 지표 일괄(TRIMP·RE·디커플링·GAP·VDOT) explainer. 카피 작성 부담이 크다(IMPL-PROGRESS 2-5 2차).
- C. 보류를 유지한다. 3-8·3-9에 필요 화면이 없으면 계속 미룬다.

**(c) 권장: A.** 항목 1의 `m.trimp` 막다름과 3-6 판정 칩을 함께 해소한다. CTL·ATL의 `m.trimp` drill은 daily 합(`daily_trimp_sum`)이므로 daily `trimp` 경량 카드에서 원천 활동 Top3를 `@a{id}`로 연결한다.

**(d)** `drillStackCore.ts`(파서 + 테스트), `DrillPanel.svelte`(scopeType 전달), 신규 `metrics_explain_activity.py`(약 80줄, 300줄 규칙 때문에 분리), `routes_library.py` 분기 없음. DB 변경은 없다.

**(e)** 첫 활동 explainer를 TRIMP로 할지 RE로 할지 정해야 한다.

## 4. S1b PMC 감쇠·GAP 보강

**(a) 현재**
- PMC는 이미 `α=1/τ`(`src/metrics/pmc.py:88`), version "2.0"(`:67`), 252일 창(`:7`)이다. 1-1에서 운영 반영됐다.
- GAP v2(Minetti, 고도 30m 창)는 1-7에서 완료됐다(문서 근거 IMPL-PROGRESS:25).
- 잔여 1: `DATA-CTL-WARMUP`. 창 절단은 해소됐지만 2025-09 이전 활동의 심박이 없어 TRIMP가 없다(`BACKLOG.md:9`).
- 잔여 2: Garmin `gap_speed_ms` 소스 GAP 저장(④, IMPL-PROGRESS:25).
- 잔여 3: ACWR 정의 통일(D1f, 99-summary:283). 현행 코드 정의는 미확인이다.

**(b) 선택지**
- A. S1b를 종료하고 잔여 3건을 개별 항목으로 분리한다.
- B. 잔여 3건을 하나의 ADR로 묶어 착수한다.
- C. 현 상태를 유지한다(보류).

**(c) 권장: A.** S1b의 본체(감쇠식·GAP 경사)는 끝났다. 잔여 처리는 다음과 같다.
- ① 심박 결측 TRIMP: 페이스·RPE 기반 대체 부하. 새 Calculator가 필요하므로 사용자 판단 대상이다.
- ② 소스 GAP 저장: Extractor 추가와 재동기화가 필요하다.
- ③ ACWR: 3-18 앞에 결정한다.

**(d)** 문서 정리만 한다(BACKLOG 항목 분리). ①과 ②를 실행하면 실 DB 변경이 있다(재계산·재동기화, 백업 필수).

**(e)** 잔여 ①(2025-09 이전 CTL 과소)을 고칠 가치가 있는지 정해야 한다. 현재 값에는 영향이 없다(`BACKLOG.md:9`).

## 5. 3-10 RPE 입력·`⋯` 메뉴 — **사용자 승인 전 착수 금지 (⑦ ADR)**

**(a) 현재**
- 설계는 `PUT /api/v1/library/activities/:id/feedback {rpe, pain, pain_site?, note?}`다(20 design:406).
- `user_inputs`가 `UNIQUE(input_date, input_type)`라서 같은 날 2개 활동을 구분할 수 없다는 점은 문서 근거이고, DDL은 미확인이다.
- `activity_feedback` 테이블 존재 여부는 미확인이다(grep하지 않음).
- `⋯` 메뉴(원본 링크·GPX)의 코드 상태는 미확인이다. "코치에게 묻기"는 완료됐다(IMPL-PROGRESS:255-259).

**(b) 선택지**
- A. 신규 `activity_feedback(activity_id PK, rpe INT CHECK 1-10, pain TEXT, pain_site TEXT, note TEXT, updated_at)`.
- B. `user_inputs`를 재생성하고 UNIQUE를 바꾼다(SQLite라 테이블 재작성이 필요하고 기존 체크인 경로에 영향).
- C. `metric_store`에 scope=activity, provider=`user`로 저장한다. 단일 저장소 원칙에는 맞지만 note·pain_site 같은 텍스트가 섞여 부자연스럽다.

**(c) 권장: A**(99-summary D3 권장과 동일).
- 근거: 활동과 1:1이고, 날짜 체크인과 의미가 다르며, 추가형 마이그레이션이다.
- RPE를 부하 계산에 쓰는 시점(session-RPE, 항목 4 ①)이 오면 Calculator가 CalcContext API(`get_activity_feedback`, 신규, ADR-009)로 읽는다. raw SQL은 금지다.
- 31 S3 세션 회고(workout 키)와의 연결은 같은 ADR에 적는다.
- `⋯` 메뉴의 "원본 열기"(`core.source_url`)는 읽기 전용이라 ADR과 분리해 먼저 진행할 수 있다. 이 부분도 승인 후 진행한다.

**(d)** `db_setup.py`(DDL·SCHEMA_VERSION +1), 신규 `activity_feedback_service.py`, `routes_library.py`(293줄이라 새 라우트 파일로 분리 권장), `QuickInput.svelte`(scope prop), 문서(decisions.md ADR, architecture 테이블 수). 운영 DB에 스키마를 추가하므로 백업이 필요하다.

**(e)** ADR 승인 여부, RPE 척도(1-10 확정 여부), 통증 부위 입력 포함 여부, GPX 내보내기 범위를 정해야 한다.

## 6. 3-16(D4) 처방 엔진 보정 R6·R7 — **사용자 승인 전 착수 금지**

**(a) 현재**
- 99-summary:219·299 D4 권장안: "승인하되 두 단계. 백테스트 후 새 계획에만 적용, 진행 중인 11/22 계획은 재생성하지 않음."
- 계획 엔진 코드의 현 R6·R7 반영 상태는 미확인이다(조사 안 함).
- 의존: 3-15(문서 근거).

**(b) 선택지**
- A. 2단계: ① 과거 대회 전 N주 훈련으로 백테스트 하네스(읽기 전용) ② 통과 시 새 계획 생성에만 적용.
- B. 즉시 적용 + 진행 중 계획 재생성. 레이스 7주 전이라 위험하다.
- C. 11/22 대회 이후로 연기한다.

**(c) 권장: A**(①은 지금 시작 가능, ②는 11/22 이후 기본값). 진행 중 계획은 3-13 조정 카드로 보완한다.

**(d)** 계획 엔진 모듈(경로 미확인), 백테스트 스크립트(신규), 테스트. 기존 계획을 재생성하지 않으므로 DB 변경은 없다.

**(e)** D4 승인, 백테스트 통과 기준(예: 과거 계획 대비 롱런·M 페이스 분량 오차), 적용 시점(대회 전/후)을 정해야 한다.

## 7. 내러티브 캐시 워밍·MonthNarrative 레이어링

**(a) 현재**
- `get_narrative_cache`/`set_narrative_cache`는 성공한 AI 결과만 캐시한다(문서 근거 IMPL-PROGRESS:135). 캐시 키 구조와 무효화 조건은 미확인이다.
- 프론트는 narrative를 비동기 `{#await}`로 분리했다(IMPL-PROGRESS:157-163). 따라서 화면이 막히지는 않는다.
- MonthNarrative는 `fixed inset-0` 오버레이라 DrillPanel과 겹칠 위험이 있다(문서 근거 IMPL-PROGRESS:121).

**(b) 선택지(워밍)**
- A. 동기화 완료 후 1회 사전 생성: sync 파이프라인 끝에서 백그라운드 스레드로 생성하고, 실패해도 무시한다(sync 중단 금지 규칙).
- B. 정해진 시각(06:00) 크론.
- C. 워밍하지 않고 규칙 기반 즉시 문구를 먼저 보여 준 뒤 LLM으로 교체한다.

**(b') 선택지(레이어링)**
- A. MonthNarrative를 라우트(`/today/month`)나 DrillPanel 스택 항목으로 바꾼다(오버레이 하나로 통일).
- B. z-index 규약만 정하고 중첩을 허용한다.

**(c) 권장: 워밍 A + 레이어링 A.**
- 입력 데이터가 바뀌는 시점은 동기화뿐이다. 캐시 키는 `(date, 입력 해시)`를 권장한다. 현 키 구조는 미확인이므로 확인 후 맞춘다.
- 호출 비용은 동기화 1회당 최대 1회로 제한된다.
- 레이어링은 오버레이를 하나로 유지하는 방식이 §C3.1과 정합한다.

**(d)** `src/sync.py` 또는 sync 서비스 끝 훅(경로 미확인), `_narrative.py`, `MonthNarrative.svelte`. DB 변경은 캐시 행 쓰기뿐이다(캐시 테이블 존재 여부 미확인).

**(e)** LLM 사전 생성 허용 여부(외부 전송 동의 D8과의 관계: 동의가 없으면 워밍 금지), 1일 호출 상한을 정해야 한다.

## 8. 목표 달성 가능성·`x.taper`·explain `race_pred_marathon_sec`

**(a) 현재**
- explainer에 예측 계열이 없다(`EXPLAIN_SUPPORTED_SLUGS`는 6종, `metrics.ts:5`).
- 21 design:340에 따르면 입력 조회가 `c.name == slug`라서 `darp` 산출물의 입력이 빈다. 수정안은 `slug in c.produces`이고, 해당 코드 위치는 미확인이다.
- 투영 칩은 `x.taper`가 없어 `/v2/today/race`로 대체 연결돼 있다(IMPL-PROGRESS:231).
- 가능성(필요 개선 %)은 미구현이다(IMPL-PROGRESS:206).

**(b) 선택지**
- A. 순서: ① `produces` 조회 수정 + `race_pred_marathon_sec` explainer(evidence: 범위·신뢰·제한 요인, 21 V8 기준) ② `x.taper`(TSB 투영, 계획 기반) ③ 가능성 = (예측 − 목표)/예측 %.
- B. 가능성부터 한다. 근거 없는 수치가 먼저 노출되므로 비권장이다.

**(c) 권장: A.** ③은 신뢰도 <0.5일 때 범위로만 표시한다(99-summary:310 예측 헤드라인 규칙).

**(d)** `metrics_explain_*`(신규 `metrics_explain_prediction.py`), `metrics_service`(produces 조회, 위치 미확인), `PredictionEvidence.svelte`(신규), coach 투영 칩 `chipTarget`. DB 변경은 없다.

**(e)** 가능성을 % 대신 "필요 VDOT +n"으로 보여 줄지 정해야 한다.

## 9. S2 이월 — 이벤트 마커·Sparkline min_span·끝점·캡션

**(a) 현재**
- `/trend` `bands`·이동평균·결측 끊김은 완료됐다. `spanRange`도 이미 있다(IMPL-PROGRESS:297, 프론트 코드 재확인은 하지 않음).
- 스펙: 마커 ▲레이스·◆계산 변경(21 design:263), min_span 값 표(:271).
- 마커 데이터 소스는 미정이다.

**(b) 선택지(마커 소스)**
- A. 파생: ▲는 레이스 확정 활동(대회 목록, `/v2/today/race/races`가 쓰는 소스, 경로 미확인), ◆는 `metric_store`의 해당 지표 `algorithm_version`/provider 버전이 바뀐 첫 날(컬럼명 미확인). `/trend`에 `events[]`를 추가한다.
- B. 신규 `metric_events` 테이블. 단일 저장소 원칙 대비 이득이 적다.

**(c) 권장: 1단계로 Sparkline min_span·끝점·캡션(프론트 + `metric_display.py` min_span 값), 2단계로 마커 A.**

**(d)** `metric_display.py`, `Sparkline.svelte`, `metrics_browser_service.py`(trend events), `TrendChart.svelte`. DB 변경은 없다.

**(e)** ◆ 버전 마커를 일반 사용자에게 노출할지(1-1 PMC v2 1회성 알림과 중복 여부) 정해야 한다.

## 10. 계정 설정 스키마(2-3)·`sync_jobs` 열 확장·오류 표면화

**(a) 현재**
- D5 권장은 `sync_jobs` 확장이다(`job_type·last_error·retry_after`가 이미 있음, 99-summary:300).
- D6 권장은 계정 `ui_default` + 전역값이다(:301).
- Strava 403이 completed로 남는다(IMPL-PROGRESS:22).
- 실제 `sync_jobs` 컬럼과 설정 테이블 존재 여부는 미확인이다(`grep "CREATE TABLE" src/db_setup.py`를 실행하지 않음).

**(b) 선택지**
- A. `user_settings(key PK, value_json, updated_at)` key-value 1개 + `sync_jobs`에 `error_code TEXT`, `http_status INT`, `source_path TEXT`(4경로 식별)를 추가한다.
- B. `user_training_prefs`에 열을 추가한다. 훈련 선호와 UI 설정이 섞인다.
- C. config.json에 둔다. 다중 사용자 DB 구조와 맞지 않고 커밋 금지 파일이다.

**(c) 권장: A.** 추가형 ALTER로 멱등 마이그레이션한다. 오류 분류(`auth`/`rate_limit`/`network`/`parse`)는 서비스 계층 상수로 둔다. 4경로가 모두 `sync_jobs`에 쓰도록 바꾸는 작업은 4-1의 전제다.

**(d)** `db_setup.py`(SCHEMA_VERSION +1), `sync_state_service`, 동기화 4경로(경로 미확인), 문서(architecture 테이블 수). 운영 DB 스키마가 바뀌므로 백업이 필요하다.

**(e)** 설정 저장 위치(A 동의 여부), `ui_default` 전역 롤백 값의 위치를 정해야 한다.

## 11. 요약 탭 스트림 다운샘플·탭 재방문 SWR — **완료 상태, 항목 종료 권장**

**(a) 현재**
- 다운샘플은 `_downsample_streams`, 최대 500점, `stream_point_count`다(IMPL-PROGRESS:165-173).
- SWR은 `loadCache.ts`, Today·Library 홈에 적용됐다(:146-154).
- ETag는 `api_ok_cacheable`(`routes_library.py:11,59-60`에서 확인)이다.
- 이후 3-6 백엔드에서 `streams`를 기본 응답에서 제외했다(`?include=streams`, IMPL-PROGRESS:290).

**(b)/(c)** 보류 사유가 이미 해소됐으므로 BACKLOG에서 제거한다. 남은 narrative 워밍은 항목 7로 합친다. 다른 라우트에 SWR을 확장하는 건 측정상 이득이 작아 하지 않는다(:154).

**(d)** BACKLOG 문서 수정만 한다. **(e)** 종료 동의 여부만 확인하면 된다.

## 12. 활동 목록 기간 필터

**(a) 현재**
- API는 이미 `from`/`to`/`sport`/`dist_min`/`search`를 지원한다(`routes_library.py:20-33`). 정렬은 서비스에 `sort_by` 화이트리스트가 있지만(`activity_service.py:35-46`) 라우트에 노출되지 않았다.
- 프론트는 URL의 `from`/`to`를 load에서만 읽는다(`routes/library/activities/+page.ts:12-16`). 기간 선택 UI는 없고 주석에 "기간 필터는 후속"이라고 적혀 있다(`+page.svelte:23`). 표시되는 것은 "기간 해제" 칩뿐이다(`:115`).
- 종목·거리·검색 상태는 URL에 반영되지 않는다(`:44-48,89-91`). "기간 해제"도 URL을 바꾸지 않아 새로고침하면 기간이 되살아난다(`:115`). 이는 F-UX-05의 결함이다.

**(b) 선택지**
- A. 기간 칩 하나(프리셋: 전체·최근 30일·이번 달·올해 + 월 선택 시트)를 두고, 모든 필터를 `from,to,month,sport,type,dist_min,sort,q`로 replaceState 동기화한다(20 design:197 규격).
- B. 네이티브 date input. 이전에 제거된 방식이라 비권장이다.
- C. 연-월 스크러버(S8 전체)와 함께 한다. 규모가 L이다.

**(c) 권장: A를 먼저 하고, C(스크러버·facets·무한 스크롤)는 3-9에서.** `month=YYYY-MM`은 프론트에서 from/to로 변환하므로 API 변경이 필요 없다. `sort`만 라우트에 노출(+5줄)한다.

**(d)** `activities/+page.svelte`·`+page.ts`, 신규 `lib/activityFilters.ts`(URL↔상태 순수 함수 + 노드 테스트), `routes_library.py`(sort). DB 변경은 없다.

**(e)** 프리셋 목록과 sort 옵션(최신·거리·페이스)을 정해야 한다.

## 항목 간 의존·권장 착수 순서

의존 관계:
- 1 → 3: TRIMP 막다름을 1에서 경량 카드로 우선 해소하고, 3에서 `@a` 연결로 완결한다.
- 2 → 8: `PredictionEvidence`와 RRI 제한 요인 태그를 함께 구현한다.
- 9(◆) ↔ 4: 버전 마커는 PMC v2 변경일을 표시한다.
- 10 → 4-1(동기화 표면) → 7 워밍 훅의 오류 기록.
- 5 ↔ 4 ①: RPE는 심박 결측 부하를 대체할 수 있다. ADR에 함께 적는다.
- 6 ← 3-15·3-13.

권장 순서(결정이 필요 없거나 작은 것부터):
1. **11 종료**(문서만).
2. **12**(S~M, DB 없음).
3. **2**(S).
4. **1**(S).
5. **9 1단계**(S).
6. **3**(M).
7. **8**(M+M).
8. **9 2단계**(M).
9. **4 정리**(문서).
10. **7**(D8 동의 정책 확인 후).
11. **10**(스키마, 백업).
12. **5**(ADR 승인 후).
13. **6**(D4 승인 후, 백테스트부터).

5·6은 사용자 승인 전 착수 금지다. 10·5는 운영 DB 스키마를 변경하므로 `running.db.bak-<날짜>-<사유>` 백업 후 사본으로 검증한다.
