# DESIGN-CLEANUP — 구조·정리 항목 설계안 (2026-10-04)

출처: `BACKLOG.md` `[P7-UXR-DESIGN-PENDING]` "구조·정리" 문단(201~204행), `IMPL-PROGRESS.md` 199·252·273·276행.
읽기 전용 조사 결과다. 코드·DB 변경 없음. "미확인"은 조사를 끝내지 못한 부분이다.

## 1. `src/utils/metric_registry.py` (522줄) 분리

**근거**: 구성은 MetricDef 13~40행, METRIC_CATEGORIES 46~64행, `_DEFINITIONS` 71~461행(224개, 이름 중복 0), 인덱스 빌드 468~474행, 공개 API 481~522행.
정의 블록 경계는 Layer1 activity_summary·wellness(71~154), Layer2 hr~load(156~292), Layer2 efficiency~meta/athlete(293~461)이다.
**import 사용처**: services 5곳, `web/template_helpers.py:9`, `sync/extractors/base.py:114`,
scripts `gen_data_master.py:26`·`check_data_consistency.py:42`(`get_by_storage`, `MetricDef`)·`check_docs.py:493`,
tests `test_metric_registry.py:3`(**private `_ALIAS_MAP`** import)·`test_phase1_schema.py:31`·`test_metric_labels.py:7`·`test_integration_realdb.py:976`.
`gen_metric_dictionary.py`는 registry를 import하지 않는다(영향 없음).
**텍스트 grep 의존**: `.claude/skills/system-design-conventions/SKILL.md:34`의 `grep -c "MetricDef(" src/utils/metric_registry.py`와
`design-audit/checklist.md:10`. 분리하면 이 두 곳의 카운트가 틀어진다.

**선택지**
- A(권장): 기존 파일을 파사드로 남긴다. `metric_def.py`(MetricDef dataclass, 순환 import 방지)와
  `metric_defs_layer1.py`(~90줄), `metric_defs_load.py`(~145줄), `metric_defs_misc.py`(~175줄)를 새로 둔다.
  `metric_registry.py`는 `_DEFINITIONS = LAYER1 + LOAD + MISC`로 **순서를 보존**해 concat하고, CATEGORIES·인덱스·API·하위호환 alias·`_ALIAS_MAP`을 유지한다(~140줄). 모든 import 경로가 그대로 유지된다.
- B: `src/utils/metric_registry/` 패키지로 전환한다. `__init__`이 재노출하므로 경로는 호환된다. 다만 파일 경로를 문자열로 쓰는 문서(files_index, SKILL)가 많아 변경 면적이 크다.
- C: 데이터를 YAML/JSON으로 옮긴다. SSOT 형식이 바뀌는 설계 변경이므로 이번 범위가 아니다.

**커밋 단위**
1. `refactor: MetricDef를 metric_def.py로 분리 (registry 재노출)`
2. `refactor: metric_registry 정의 블록 3개 모듈로 분리`. 분리 전후 `[d.name for d in _DEFINITIONS]` 동일성을 검증하는 테스트를 추가한다(신규 테스트 1개).
3. `docs: SKILL/checklist grep 레시피 갱신`(`grep -c "MetricDef(" src/utils/metric_def*.py`) + `gen_files_index.py` 재생성.

**위험·테스트**: 순서가 바뀌면 METRIC_REGISTRY dict 순서가 달라져 소비처 출력 순서가 변할 수 있다. 커밋 2의 테스트가 이를 막는다.
`pytest tests/test_metric_registry.py tests/test_phase1_schema.py tests/test_metric_labels.py`, `check_docs.py`, `check_data_consistency.py`를 실행한다.

## 2. `src/ai/ai_context.py` (462줄) 분리

**근거**: 두 계열이 섞여 있다.
- (a) 서비스 레이어 경로: `build_daily_briefing`(31), `build_activity_analysis`(115), `build_ai_context`(176). 약 186줄.
- (b) 레거시 dict 경로: `_RUN_TYPES`(188), `build_context`(193), `format_context_text`(284), `format_activity_context`(409). 약 275줄.

**사용처**
- (b)는 `ai/briefing.py:32,58`(운영 경로)와 `tests/test_ai_context.py`, `tests/test_chat_readiness.py:11`에서 쓴다.
- (a)는 **운영 호출처가 없다**. grep 결과 `tests/test_ai_context.py`와 `scripts/check_docs.py:878`(검사 19가 `def build_ai_context` 문자열 존재를 확인)뿐이다.
- `mock.patch("src.ai.ai_context....")` 형태의 patch 대상은 없다.

**선택지**
- A(권장): (b)를 `src/ai/ai_context_legacy.py`(~280줄)로 옮긴다. `ai_context.py`는 (a)와 재노출(`from .ai_context_legacy import build_context, format_context_text, format_activity_context`)만 남긴다(~195줄). 경로가 호환되고 check_docs 19도 통과한다.
- B: (a)가 dead code이므로 삭제하고 (b)만 남긴다. 그러면 check_docs 19 수정과 phase-5 문서 정정이 필요하다. **판단 필요**(Q1).

**커밋**
1. `refactor: ai_context 레거시 dict 경로를 ai_context_legacy.py로 분리`. 재노출 경로 테스트 1개를 추가한다.
2. (B를 택하면 별도로) `refactor: 미사용 build_ai_context 계열 제거`.

**테스트**: `pytest tests/test_ai_context.py tests/test_chat_readiness.py tests/test_briefing.py`.

## 3. `engine_label("legacy_rule")` → "규칙 답변"

**근거**
- `src/services/coach_engine_health.py:33-47`의 `engine_label`은 미지 status를 기본값 `"규칙 답변"`으로 반환한다. `legacy_rule` 전용 분기가 없다.
- `legacy_rule`은 `message_engine_view`(65행)가 engine_json이 NULL이고 ai_model이 없을 때 직접 만든다. 이때 라벨은 `"규칙 답변(이전 방식)"`으로 하드코딩된다. 같은 status에 라벨 출처가 둘인 셈이다.
- `engine_label`의 호출처는 70행 한 곳과 테스트뿐이다. 저장 경로(`EngineInfo.status` = ok|fallback|rule_only|rule_by_choice, `chat_engine_result.py:36`)는 `legacy_rule`을 쓰지 않는다. 따라서 `engine_label("legacy_rule")`은 현재 도달하지 않는다.
- **더 큰 문제(코드상 추론, 브라우저 미확인)**: 오류 행은 `coach_service.py:264`와 `coach_async.py:220`에서 status만 'error'로 바꾸고 engine_json을 NULL로 둔다. 그래서 재로딩하면 `engine.status="legacy_rule"`, 라벨 "규칙 답변(이전 방식)"이 된다. `MessageBlock.svelte:52-53`이 이 라벨을 표시하고, `bannerFor`(`coachEngine.ts:41-47`)는 null이 되어 오류 배너와 [다시 생성]이 뜨지 않는다.
- cancelled 행은 `_store_reply`가 결과 엔진(ok 등)을 저장하므로 "중단됨" 표시가 재로딩 후 사라질 가능성이 있다(미확인).

**권장안**
1. `engine_label`에 `legacy_rule` → `"규칙 답변(이전 방식)"` 분기를 추가하고, 65행이 이 함수를 쓰게 해 라벨 출처를 하나로 만든다. 기본값은 `"답변 엔진 정보 없음"`으로 바꾼다. 문구는 Q2로 확인한다.
2. `message_engine_view`가 행의 `status`(error/cancelled/pending/working)를 받아 engine_json보다 우선 적용한다. error는 `status:"error"`로 바꾸고, pending/working은 engine=None으로 둔다.

**커밋**
1. `fix(coach): legacy_rule 라벨 단일화` + `test_coach_engine_health` 케이스 추가.
2. `fix(coach): 오류·중단 행 엔진 뷰를 행 status 기준으로`. `test_coach_service`에 error 행 케이스를 추가하고, Playwright로 오류 행 재로딩 스모크를 돌린다.

## 4. `HIGHER_IS_BETTER` 위치

**근거**: 같은 이름의 dict가 **두 개** 있다.
- `src/services/metric_display.py:15` — 6키(tsb·ctl·atl·utrs·cirs·rri). 사용처는 `metrics_explain.py:31,39,167`, `metrics_browser_service.py:11,186`, `display_meta`(35행).
- `src/web/template_helpers.py:43` — 28키, 레거시 Jinja 색상 판정(166행). `tests/test_template_helpers.py:130,135`가 사용한다.
- 값 충돌은 없다(utrs·cirs·rri는 같은 값). `src/metrics/bands.py`에 방향(direction) 정보가 있는지는 **미확인**이다.

**선택지**
- A: bands.py로 이동해 등급 밴드와 방향을 한 SSOT로 묶는다(bands.py의 구조 확인이 선행돼야 한다).
- B(잠정 권장): 현 위치를 유지한다. 표시 메타는 "API 표시 계약"에 속하고 bands는 "등급 판정"에 속하므로 레이어가 다르다.
- 어느 쪽이든 template_helpers의 28키 사본은 별도 정리 대상이다. Jinja 화면 폐기 여부에 따라 달라진다.

결정은 Q3. 커밋은 이동 1건 + 재노출 유지 + `tests/test_metric_bands.py` 케이스 1개다.

## 5. 미사용 코드 (grep 검증, `frontend/` 기준. `node_modules`·`build` 제외, 테스트·동적 import 포함)

| 대상 | 판정 | 근거 |
|---|---|---|
| `lib/status.ts` | **이미 삭제됨** | 파일 없음, `bbb66de`에서 제거 |
| `raceHub.ts` `formBand` | **이미 삭제됨** | export 없음(`bbb66de`), 남은 것은 주석 `formChart.ts:28`, `tests/raceHub.test.mjs:4` |
| `lib/metricMeaning.ts` | **삭제 불가** | `routes/library/metrics/+page.svelte:10`과 `tests/metricMeaning.test.mjs:3`이 사용. `Meaning` interface(2~5행)만 미사용이므로 제거 가능 |
| `components/RecommendationCard.svelte` | **삭제 안전** | import 0건. `types/index.ts:80-98`의 `RecommendationAction`·`RecommendationCardProps`도 함께 제거(다른 참조 0) |
| `components/ScoreRing.svelte` | **삭제 안전** | import 0건. `lib/scoreRing.ts`는 `ReadinessGauge.svelte:3`과 테스트가 쓰므로 **유지**. `drillStack.ts:19` 주석 갱신 |

`import.meta.glob`이나 템플릿 문자열 동적 import는 없다.
커밋 `chore(frontend): 미사용 RecommendationCard·ScoreRing·Meaning 제거` 1건으로 묶는다. 이후 `npm run check`, unit, build를 돌린다.
`04-component-catalog.md`의 언급 정정 여부는 Q4로 확인한다.

## 6. 10-docs `display_name_ko` → `name_ko`/`abbr`

- `display_name_ko`를 포함한 파일은 `ux-review-2026-09/10-today/design.md`, `21-library-metrics/design.md`, `BACKLOG.md`이다.
- "§4(~176행)·§7.2(~242행)"이 어느 파일의 행인지, 정확한 원문은 **미확인**이다(조사 중단).
- 정정 기준은 확인했다. API 필드는 `name_ko`·`abbr`이다(`metric_display.py:20-35`, `metric_labels.label_for` SSOT). 프론트 표시명은 `displayLabel` = `abbr ? "name_ko (abbr)" : name_ko`(`metricMeaning.ts:18`)이다.
- 수정안: `display_name_ko` → "`name_ko`(+선택 `abbr`, SSOT `src/utils/metric_labels.py`)"로 바꾼다. 행 단위 diff는 `grep -n display_name_ko` 후 작성한다.

## 7. 상세 페이지 `#3b82f6` 토큰화

`frontend/src/routes/library/metrics/[slug]/+page.svelte`의 해당 행 위치와 기존 토큰 정의(tailwind/CSS 변수, 차트 색상 상수)는 **미확인**이다.
다음 단계는 `grep -rn "3b82f6\|--color-\|accent" frontend/src/app.css frontend/src/lib/*Chart*.ts`로 차트 색상 토큰을 찾는 것이다.
차트 라이브러리는 CSS 변수를 직접 해석하지 못할 수 있으므로 `getComputedStyle`로 읽는 헬퍼가 있는지도 확인해야 한다.

## 사용자 질문

- **Q1**: `build_daily_briefing`/`build_activity_analysis`/`build_ai_context`는 운영 호출처가 없다. 분리만 할까요, 삭제할까요?
- **Q2**: legacy_rule 라벨과 미지 status 기본 문구를 무엇으로 할까요? 오류 행 엔진 뷰 수정(3-2)도 이번 범위에 넣을까요?
- **Q3**: HIGHER_IS_BETTER를 bands.py로 옮길까요, 유지할까요? template_helpers 28키 사본은 어떻게 처리할까요?
- **Q4**: 컴포넌트 삭제 시 설계 문서(04-component-catalog)의 언급도 정정할까요?
