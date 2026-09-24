# Phase 7 — 사람 결정 대기

무인 실행(`scripts/autopilot/`)이 스스로 판단하지 않고 여기 적어두는 갈림길. 형식은
`## [ID] 제목` — ID는 관련 BACKLOG 항목, 없으면 `GENERAL`. 답은 "**결정:**" 줄만
채우면 된다. 답이 채워지면 `stage: blocked`였던 항목을 `queued`로 되돌리고 이 섹션은
지우지 않는다(이력).

---

## [GENERAL] 무인 실행 범위 — 이 4가지는 자동으로 바꾸지 않음

**배경**: 2026-09-21 스파이크 이후 제안한 경계. 자동 실행이 아래를 바꾸려면 반드시
여기 먼저 적고 멈춘다.

1. `00-diagnostic-and-direction.md`의 확정 결정 A~D (IA/기술스택/디자인/마이그레이션)
2. `01-design-principles.md`의 8개 원칙
3. `06-data-layer-extensions.md`의 D1~D5 (스키마 결정)
4. `CLAUDE.md` / `.claude/rules/*`

**결정:** 기본값 적용 중(2026-09-22, "진행 진행" 이후 이의 없음). 바꾸고 싶으면 언제든 여기 적어주세요.

---

## [GENERAL] 추가 사용량(overage) 설정

**배경**: 2026-09-21 스파이크에서 `rate_limit_event.overageStatus: "allowed"`,
`isUsingOverage: false` 확인. 한도에 닿으면 차단이 아니라 초과 과금으로 넘어갈 수 있는
계정 설정으로 보이나, 이 세션에서는 계정 설정 화면을 볼 수 없어 확인 불가.

**선택지**:
- A. claude.ai 설정에서 추가 사용량을 끄기 (한도 도달 시 확실히 차단 — 예산 상한이
  실질적 안전판이 됨)
- B. 켜둔 채로 `ledger.py`의 일간/주간 상한만 신뢰 (설정값이 틀리면 과금 위험)

**권고**: A. 자동 실행의 안전판은 확인 가능한 원장이어야 한다.

**결정:** (미정)

---

## [GENERAL] 실행 시간대 기본값

**배경**: "자주 접속 안 함"이라는 답만 받음, 구체적 비활동 시간대는 미확인. 시스템
타임존은 Asia/Seoul(KST). `settings.py` 기본값을 KST 02:00–06:00로 잠정 설정.

**결정:** 기본값(KST 02–06시) 적용 중. 다른 시간대를 원하면
`scripts/autopilot/settings.py`의 `NIGHT_START_HOUR`/`NIGHT_END_HOUR`를 바꿔주세요.

---

## [P7-REALIGN-SCOPE] 00~07 재정렬 — 유닛 분해 방식

**배경**: REVIEW-02·REVIEW-03가 00·01·03·04·05·07에 걸쳐 있는 변경을 요구한다
(BACKLOG.md "결정 완료 사항" 표 참조). 문서 하나 전체를 무인 유닛 하나로 맡기면
범위가 커서 검토가 어렵고, 실패 시 되돌리기도 어렵다.

**선택지**:
- A. 문서 1개 = 유닛 1개 (00, 01, 03, 04, 05, 07 각각 하나씩, 총 6유닛)
- B. 변경 성격별로 더 잘게 — 예: "00의 결정 A 텍스트 갱신", "01의 P8→P8' 갱신",
  "03의 Today 4층 구조 반영", "03의 Story/Plan 흡수 재배치"처럼 REVIEW-03 §5/§10에
  나열된 변경 단위로 쪼갠다 (문서당 2~4유닛, 총 12~16유닛)
- C. 사람이 먼저 03(68KB, 가장 큼)을 영역별 파일로 분리한 뒤 A나 B 진행

**권고**: C 다음 B. 03을 쪼개지 않은 채로 통째로 다시 쓰게 하면 무인 실행이 매번
68KB를 읽어야 해 토큰이 크고, REVIEW-03이 요구하는 변경도 국소적이라 잘게 쪼개는 쪽이
검토하기 쉽다.

**결정:** C 채택. `P7-AUTO-SPLIT-03`을 큐에 올림 — 현재 IA(5+1) 구조 그대로 내용
변경 없이 영역별 파일로만 분리(REVIEW-03 채택 여부와 무관하게 필요한 작업이라 IA
결정을 기다리지 않고 먼저 진행). B(REVIEW-03 변경 단위별 유닛 생성)는 아래
[GENERAL] IA 최종 확인 이후 진행.

---

## [GENERAL] REVIEW-03 IA 최종 확인 — 나머지 재정렬 작업 전부의 유일한 선행 조건

**배경**: 2026-09-22 재점검 결과 정정 — REVIEW-02(F1~F4/AO-1~AO-4)는 **이미 전부
01·03·04·06에 반영 완료**(2026-06-10 changelog 확인, "REVIEW-02 반영" 항목들).
아직 미반영인 건 REVIEW-03(Today as Gateway·모바일 IA·P8')뿐이고, 이게 02에만(그것도
이번에 처음 커밋) 반영됨. 00의 결정 A, 01의 원칙 8, 03의 화면 재배치, 07의 단계
분배가 전부 이 하나의 결정에 걸려있다 — REVIEW-03 자체는 과거 세션이 작성한 권고이지
사용자가 직접 확정한 것이 아니다.

**REVIEW-03 요지** (`REVIEW-03-today-as-gateway-and-mobile-ia.md`):
- IA: 5+1 영역 → 하단 3탭(Today/Library/Coach) + 상단 3선 메뉴. Story 독립 라우트
  제거(Today 흡수), Plan을 현황(Today)·작업(Coach)으로 분할.
- P8(Local-First Identity) → P8'(Data Ownership & Transparency): SaaS 확정, 서버
  가공, `email@db` 격리 저장, "로컬 DB" 표현 금지.
- Today를 4층 계층적 관여 모델(L0 즉시 브리핑 ~ L3)의 관문으로 재정의.

**선택지**:
- A. REVIEW-03을 그대로 채택 — 00/01/03/07을 이 방향으로 재정렬 (권고, 이미
  02·BACKLOG.md가 이 방향을 전제로 갱신되어 있어 되돌리는 것보다 일관됨)
- B. 부분 수정 후 채택 — 어느 부분이 다른지 여기 적어주면 그 부분만 반영
- C. 반려 — 5+1 IA 유지, REVIEW-03 폐기(02의 이번 커밋도 되돌려야 함)

**결정:** A. REVIEW-03 그대로 채택 (2026-09-22, AskUserQuestion으로 확인). 00 결정 A,
01 원칙 8, 03 화면구조(내용), 07 단계분배를 이 방향으로 재정렬하는 유닛을 큐에 올린다.

---

## [P7-REALIGN-SCOPE] Phase 7a~7d 재정렬 — 사람이 직접 판단 (후속)

**배경**: 위 항목 채택 후 00 §4(Phase 순서 논거)·§5.4·07(화면 분배)의 실제 재설계가
남았다. 무인 실행이 스스로 판단하지 않도록 앞서 큐에 올리지 않고 두었는데, 2026-09-22
사용자가 "오토파일럿을 만든 이유는 에이전트가 트레이드오프를 보고 판단하는 것"이라며,
사람이 관여 가능한 이 세션에서 비전 문서 기준으로 직접 판단·재작성하라고 지시.

**결정**: Today L2(내러티브)를 7a 완성형이 아니라 7b로 이연. 근거는 `phase-7(preview).md`
§6의 그룹1(데일리 브리핑)/그룹2(내러티브 보고서) 우선순위 분리 — IA상 위치(Story가
Today L2로 흡수됨)와 콘텐츠 숙성 우선순위는 별개 축이라는 판단. 그 외 단계 경계·데이터
레이어(D1~D5) 배분은 변경 없음, 영역 이름만 신 IA 라벨로 재서술. 상세는 00 §4.1,
`07-migration-roadmap.md` v0.2 작성 이력 참조. 2026-09-22 세션에서 직접 작성 완료
(무인 실행 아님).

**보류된 부차 발견 2건** (사용자 지시 — "러닝이 우선"):
1. PWA 타이밍 — 비전 그룹1은 PWA를 데일리 브리핑과 동급 1순위로 뒀는데 00/07은 Cache-First
   풀 전략을 7c에 유지 중(REVIEW-03과 무관한 기존 결정). 재개 시: 7a에 설치 가능성만 넣고
   오프라인 캐시는 7c 유지하는 절충안 검토.
2. 멀티스포츠 — 비전 그룹1 항목(activity_type 확장)인데 00/07 어디에도 없음. Phase 7이
   "UI 리뉴얼" 스코프라 데이터 레이어 작업이 원래 범위 밖일 가능성 — 재개 시 다른
   BACKLOG/로드맵에 살아있는지 먼저 확인.

---

## [P7-IMPL-D1-REST-RRI] RRI(race_readiness) 자식 메트릭 저장 방식 — 06 문서 원안과 충돌

**배경**: `P7-IMPL-D1-REST`(utrs/cirs/race_readiness 자식 메트릭 저장) 착수 전 확인 중
발견. `06-data-layer-extensions.md` §D1의 "영향 범위" 표는 `race_readiness_calculator.py`
(실제 파일명은 `src/metrics/rri.py`, `RRICalculator`, `name="rri"` — 문서의 파일명도
구식)의 자식을 "UTRS, CIRS, 훈련 완성도"라고 적어뒀다. 이건 utrs/cirs 행 자체를 RRI의
자식으로 재소속시키라는 뜻인데, `metric_store.parent_metric_id`는 컬럼 하나(1개 부모만
가능)라 utrs/cirs가 동시에 "자기 자신의 트리의 부모"(이번에 utrs/cirs 자신도 각자
body_battery/tsb/sleep/hrv/acwr/lsi 등을 자식으로 저장하게 됨)이면서 "RRI의 자식"일
수 없다 — 트리 소유권 충돌.

utrs/cirs 쪽은 문제없음: 각 Calculator의 `compute()`가 이미 만드는 `components` dict
(예: utrs의 body_battery/tsb/sleep/hrv/stress, cirs의 acwr/lsi/consecutive/fatigue)를
`utrs_*`/`cirs_*` 이름의 신규 자식 행으로 저장하면 됨 — 기존 공유 메트릭(진짜 tsb,
hrv_weekly_avg 등)과 이름이 겹치지 않는 RRI/UTRS/CIRS 각자의 파생값이라 D1(PMC)과
동일 패턴으로 충돌 없이 적용 가능.

**선택지** (Telegram으로 최초 문의 시 제시):
- A. RRI는 이번 유닛에서 제외 — utrs+cirs만 먼저 저장, RRI는 이 결정 이후 별도 유닛
- B. RRI도 같은 패턴 적용 — "UTRS/CIRS를 자식으로" 원안을 버리고, RRI 자신의 계산
  factor(`vdot_pct`, `ctl_pct`, `di_factor`, `safety`)를 `rri_*` 신규 자식 행으로 저장
- C. 원안 그대로 — utrs/cirs 행의 `parent_metric_id`를 RRI 저장 시점에 덮어써 재소속
  (비권장 — 순서 의존성 발생)

**추가 조사(2026-09-22, 사용자 지시 "메트릭들을 확인해봐")**: 위 분석 중 "1개 컬럼이라
동시에 부모·자식 불가"라는 진단이 부정확했다는 게 드러남 — 진짜 제약은 (1)
`_save_results()`의 `name_to_id`가 Calculator 호출마다 초기화돼 애초에 Calculator 간
연결 자체가 안 됨(엔지니어링 이슈, 고치면 됨), (2) `parent_metric_id` 컬럼 하나엔 부모가
하나뿐이라 **같은 메트릭을 2개 이상의 합성 지표가 동시에 "내 자식"이라 주장할 수 없음**
(모델링 이슈). 32개 Calculator 전체의 `requires` 그래프를 조사한 결과 이 다중-소비가
예외가 아니라 흔한 패턴임을 확인(`trimp`→6곳, `ctl`→6곳, `runpulse_vdot`→5곳, `tsb`→4곳,
`cirs`→2곳 등). 즉 B/C 둘 다 "RRI가 CIRS를 소유"라는 잘못된 전제였다 — RRI는 CIRS를
낳지 않는다, 이미 독립적으로 존재하는 CIRS 값을 **입력으로 읽을** 뿐이다. 이건 애초에
`parent_metric_id`(소유 분해)가 아니라 Calculator의 기존 `requires` 속성(이미 정확성
검증됨 — `_topological_sort()`가 실행 순서 결정에 씀)이 표현해야 할 관계.

**결정**: D(신규, 채택) — `parent_metric_id`는 계속 소유 분해 전용(A 유지, utrs/cirs만
저장·RRI는 자식 없음). RRI가 CIRS/VDOT/CTL/DI를 "입력으로 썼다"는 건 스키마·엔진 변경
없이 `metrics_service.get_metric_breakdown()`이 Calculator의 `requires`를 조회해
`inputs` 목록으로 응답에 얹는 방식으로 해결(`04-component-catalog.md` C3
`MetricBreakdownData.inputs`, `06-data-layer-extensions.md` D1 "2026-09-22 정정" 참조).
사용자 확인 완료(2026-09-22, "맞네" — 대화로 확정, B/C는 기각). 실제 `get_metric_
breakdown()` 구현은 완료(`P7-IMPL-METRIC-BREAKDOWN`, 2026-09-23 병합).

---

## [P7-DESIGN-7B-API] `get_provider_comparison()` — 03c §3-G MVP 스코프 축소

`03c-library.md` §3-G는 두 모드를 정의: 3-G-1(정체성 매트릭스, 기간 집계 × 13개
SEMANTIC_GROUPS) / 3-G-2(활동별 비교, 활동 1건 × Provider). 이번 유닛은 **3-G-2만
구현**(2026-09-23) — 3-G-1은 기간 집계 로직이 새로 필요하고(현재 `_build_semantic_
groups()`는 활동 1건 스코프), `primaryReason` 판정도 그룹별 `strategy`(prefer_
runpulse/show_all)에 따라 메트릭마다 달라져야 해서(03c 예시의 TSS 행처럼 show_all
그룹인데도 특정 provider가 대표로 뽑히는 근거가 문서상 불명확) 범위가 더 크다.
LATER로 남김.

**cross-provider 조회 방식 확인**: `metric_store`는 provider별로 각자의
`activity_summaries.id`(자기 소스의 활동 행)에 스코프됨(`src/sync/extractors/base.py`
`_metric()`은 category만 정하고, scope_id는 sync 파이프라인이 그 provider의 활동
행 id로 지정) — 즉 그룹 내 형제 활동마다 metric_store 행이 따로 있다.
`activity_service._build_semantic_groups()`는 활동 1건의 `scope_id`만 조회하므로
그대로 재사용하면 형제 provider의 metric_store 값을 놓친다. `get_provider_
comparison()`은 `activity_groups`(D2)로 형제 id를 모은 뒤 `WHERE scope_id IN (...)`로
전체 조회해야 함 — 기존 헬퍼 재사용 대신 새로 작성.

**primaryReason 단순화**: 03c 3-G-2 예시처럼 메트릭마다 다른 근거를 계산하지 않고,
활동 그룹 전체에 `activity_groups.primary_source`(D2가 이미 계산해둔 정적 우선순위
결과) 하나를 균일 적용. RunPulse만 값을 가진 메트릭(다른 provider 열이 전부 비어
있는 행)만 예외로 `ruleType: "runpulse_always"`. 정체성 매트릭스(3-G-1) 구현 시
메트릭별 판정이 필요해지면 그때 재검토.

**파일 위치**: `activity_service.py`가 이미 283/300줄이라(coding-rules.md 300줄
캡) 새 파일 `src/services/provider_comparison_service.py`로 분리 — BACKLOG NEXT
원문의 `activity_service.get_provider_comparison()` 표기와 다르지만 캡 준수가 우선.

**엔드포인트**: `GET /api/v1/library/activities/:id/providers` — 03c가 쓴 `/library/
providers`(페이지 라우트, 3-G-1용 매트릭스 API 자리)는 이번엔 안 만듦, activity
하위 라우트로 스코프.

---

## [P7-DESIGN-7B-API] `get_today_narrative()` + `milestones` 테이블 — AI 생성 확정

`03a-today.md` 1-A L2의 "성장 내러티브"(자연어 요약)와 1-D "전체 마일스톤"(🎯 누적
거리·🏃 PB·🔄 재계산)은 `get_metric_breakdown`/`get_provider_comparison`과 달리
기존 데이터 재조립만으로 안 되는 두 가지 새 결정이 필요했음 — 사용자에게 확인
(2026-09-23):
1. **내러티브 생성 방식**: AI 생성 채택(규칙 기반 대신) — 단, `src.ai.chat_engine`의
   기존 provider 체인(`_build_chat_provider_chain`/`_call_provider`, Coach 기능이
   이미 씀)을 그대로 재사용하고, 체인 전체 실패 시 규칙 기반 템플릿으로 fallback
   (coding-rules.md 정책 그대로 — 완전히 새로운 AI 연동이 아니라 기존 패턴 재사용).
2. **`milestones` 테이블**: 이번 스코프에 포함(LATER로 미루지 않음) — 새 테이블 + 탐지
   로직(`distance_threshold`/`pb`/`metric_recompute` 3종)까지 같이 설계.

상세 설계는 plan mode로 진행(2026-09-23, 사용자 승인) — 탐지는 `src/sync.py`의
기존 "동기화 후 메트릭 계산" try/except 자리에 같은 패턴으로 추가해 `today_service`의
읽기 전용 원칙을 유지. `metric_recompute` 감지는 `upsert_metric()`에 훅을 걸되
헤드라인급 소수 메트릭(ctl/runpulse_vdot/race_pred_*/rri)으로 allow-list 제한(전체
메트릭에 걸면 sync 성능 저하). PB 버킷은 `metric_groups.py`의 `race_prediction`
그룹 명명(5k/10k/half/marathon)을 그대로 따름. 구현은 `P7-IMPL-MILESTONES` →
`P7-IMPL-TODAY-NARRATIVE`(의존) 두 유닛으로 분리(AUTOPILOT QUEUE 참조).

---

## [P7-IMPL-7B-TODAY-L2] `<TimelineNarrative>`(C7) 스펙과 실제 백엔드 응답 불일치 — 축소 구현

`04-component-catalog.md` C7이 정의한 `NarrativeContent`(마크다운 서브셋 파싱,
`[chart:slug]` 인라인 스파크라인, `body: NarrativeSegment[]`, `highlights` 수치
카드)는 실제 `get_today_narrative()`(`P7-IMPL-TODAY-NARRATIVE`, 이미 병합) 응답
(`{date, text, source, evidence, milestones}` — 순수 텍스트 + 평면 evidence 배열)
보다 훨씬 크다. `Milestone.type`도 문서(`distance_milestone`/`pace_pb`/`ctl_peak`/
`metric_recompute`/`custom`)와 실제 `milestones` 테이블(`distance_threshold`/`pb`/
`metric_recompute`, `P7-IMPL-MILESTONES` 설계 시 확정)이 다르다 — DB 쪽이 이미
테스트와 함께 병합돼 있으므로 문서 표기가 구식, DB를 기준으로 프론트에서 매핑.

**결정**: 이번 유닛(`P7-IMPL-7B-TODAY-L2`)은 C7 전체 스펙을 구현하지 않는다 —
`text`를 단락으로, `evidence`를 `<EvidenceQuote>` 칩으로, `milestones`를 아이콘+
날짜 리스트로 보여주는 단순 버전만. 마크다운/인라인 태그 파싱, SVG 스파크라인
차트, `highlights` 카드, "이번 달 전체 이야기" 확장 패널(03a-today.md 1-C)은
전부 LATER(`P7-IMPL-TIMELINE-NARRATIVE-FULL`) — 백엔드에 `highlights`/구조화
`body` 필드가 생기기 전까진 프론트만 먼저 만들어봐야 의미가 없음.

**C3 `<MetricBreakdown>`도 문서 스펙보다 실제 API가 작다** — `metrics_service.
get_metric_breakdown()`(`P7-IMPL-METRIC-BREAKDOWN` 설계 시 이미 축소 결정,
DECISIONS.md 위쪽 항목 참조)는 `weight`/`formula`/`computedAt`/`version`/
`prevValue`를 안 주고, children/inputs 각 항목 키도 문서의 `slug`가 아니라
`name`이다(`_metric_item()` 참조). 그리고 `children`은 한 단계만 조회한다
(`parent_metric_id`가 자기 id인 행만 — 조부모/손자 관계 없음, `metrics_
service.py`에 재귀 없음) — 즉 children은 "펼침/접힘 가능한 트리"가 아니라
**평평한 목록**이다(각 항목에 자기 children이 없으므로 인라인 펼침 UI
자체가 불필요). `inputs`만 실제로 drillable(탭하면 그 slug로 API를 새로
호출해 새 MetricBreakdown을 마운트, 04 스펙의 재귀 마운트 그대로 — 이 부분은
스펙과 일치). 프론트 타입은 문서의 `MetricBreakdownNode`를 그대로 베끼지
말고 실제 응답 키(`name`)로 새로 정의할 것.

---

## [P7-IMPL-7B-LIBRARY-HUB] `/library` 홈 재설계 — IA 결정 + Provider 현황 카드 제외

`03c-library.md` 3-A는 `/library`를 `[활동][메트릭][웰니스][Provider 비교]`
4-탭 허브로 그리는데, 실제 구현은 `/library` 자체가 3-B(필터+페이지네이션
활동 목록)였다 — 문서 원문(3-B 제목)은 이미 `/library/activities`를 의도하고
있었고, 이전 구현(`P7-IMPL-SVELTE-2A`)이 3-A가 없는 상태에서 3-B를 임시로
`/library`에 얹어놓은 것이었다(2026-09-23 plan mode 조사로 확인, Explore
서브에이전트 3개 병렬 투입).

**IA 결정**: "활동" 탭 = `/library` 자체(홈/최근 활동 요약 뷰). 전체 필터
목록은 별도 탭이 아니라 "최근 활동" 섹션의 "전체 보기" 링크로만 도달
(`/library/activities`, 기존 3-B 내용 그대로 이동). 목업의 밑줄이 "활동"
탭 아래 있는 것도 이 해석과 일치(활동 탭 = 홈 콘텐츠 자체).

**Provider 데이터 현황 카드는 이번 스코프에서 제외**(정적 "준비 중" 표시만).
근거: (1) provider 연결 여부를 판정하는 공용 헬퍼가 없음 — `src/web/
auto_sync.py`의 비공개 `_connected_sources()`뿐이고, `check_*_connection()`
4개 중 Intervals/Runalyze 2개는 매 호출마다 실제 네트워크 요청을 함(홈 화면
로드마다 쓰기엔 부적합). (2) "마지막 동기화" 시각이 서로 다른 값을 가진
3개 소스로 쪼개져 있음 — DDL상 `sync_jobs` 테이블은 존재하지만 비어있고
실제로 쓰이지 않음, 실제 최신 상태는 별도 파일인 `sync_jobs.db`(
`src/utils/sync_jobs.py`)가 갖고 있음, `sync_state.json`의 per-service
`last_sync_at`은 활성 auto-sync 경로가 갱신하지 않아 stale. `src/utils/
db_status.py::get_status()`의 `recent_sync` 계산도 존재하지 않는 컬럼
(`started_at`)을 조회해 항상 빈 배열을 반환하는 버그가 있음(bare except로
숨겨져 있었음 — 이번엔 안 건드림, 범위 밖). (3) 이 화면의 진짜 주인은
`src/services/data_service.py`인데, 이 파일 자체가 이미 "Phase 7a에서는
구현하지 않는다"는 docstring을 가진 명시적 스텁이다(상단 ☰ 메뉴 "Data"
화면, `03f-data.md`, Phase 7d 몫, D5 참조) — 지금 얼기설기 만들면 그
작업과 충돌·중복만 된다. 3개 disagreeing 소스를 정리하는 것 자체가
ADR급 판단이 필요해 Phase 7d 몫으로 명시적으로 남긴다.

구현은 `P7-IMPL-7B-LIBRARY-HUB`(순수 프론트, IA 이동 + 홈 화면) →
`P7-IMPL-7B-WELLNESS`(백엔드: `wellness_service.py`의 `_WELLNESS_CATEGORIES`
버그 수정 + 라우트 2개, 프론트: `/library/wellness`) 두 유닛으로 분리
(AUTOPILOT QUEUE 참조). 웰니스 서비스 버그(카테고리명이 실제 16-domain
taxonomy와 안 맞아 `hr`/`sleep`/`body`/`stress` 카테고리 행을 전혀 못
잡던 것)는 기존 테스트가 `readiness`만 커버해서 지금까지 안 걸렸던 죽은
코드 버그 — 회귀 테스트를 새로 추가해 재발을 막는다.

---

## [P7-IMPL-COACH-PLAN-ACTIVE] Coach 플랜(5-C~5-G) — 기존 `src/training/`
엔진 재사용, 신규 알고리즘 없음

`03e-coach.md` 5-C~5-G(플랜 생성·비교·진행·조정)를 설계하려고 조사하다가
(2026-09-23, Explore 서브에이전트 1개 + 직접 조사) `src/training/`에 이미
성숙한 v0.1/v0.2 규칙 기반 훈련 계획 엔진이 있는 걸 발견했다 —
`planner.py`(Seiler 80/20·Daniels VDOT·주기화, 테스트 있음),
`adjuster.py`(HRV/수면/BB/TSB 기반 오늘 세션 강도 조정), `readiness.py`
(거리별 추천 훈련 기간 + 기간별 목표 달성 가능성 예측, Daniels VDOT 성장
모델), `goals.py`(목표 CRUD), `matcher.py`/`replanner.py`(실제 활동 매칭 +
스킵 시 재조정) — 전부 논문 근거 주석과 함께 이미 구현·테스트돼 있고,
레거시 Flask 뷰(`src/web/views_training*.py`)가 이미 실제로 쓰고 있다.
Phase 7b Coach 작업은 **이 엔진을 새 API/SvelteKit에 연결하는 것**이지
새로 설계하는 게 아니다.

**핵심 재사용 매핑**:
- 5-F "상태 기반 조정" = `adjuster.adjust_todays_plan(conn)` 거의 그대로.
  단 **읽기 전용**(오늘 날짜만, DB에 안 씀) — "조정 수락" 버튼이 실제로
  반영할 쓰기 경로가 코드 어디에도 없다(grep 확인). 이번 스코프는 표시만,
  수락 영속화는 `P7-IMPL-COACH-PLAN-ADJUSTMENT-ACCEPT`(LATER)로 분리 —
  `planned_workouts`에 조정 결과를 반영할 컬럼/전략 설계가 필요해 스키마
  변경을 수반할 수 있음.
- 5-D/5-E "정적 템플릿 3~5개 비교" = 새 커리큘럼 설계 불필요.
  `readiness.get_recommended_weeks(distance_km)`가 이미 거리별
  min/optimal_min/optimal_max/taper 기간을 반환하고,
  `readiness.analyze_readiness(conn, distance_km, target_time_sec,
  target_weeks)`가 기간(주)을 입력받아 완전히 다른 달성 가능성·예상 기록을
  계산하는 기존 함수라, 3개의 기간값에 대해 그대로 호출하면 목업이 요구하는
  "기간별 비교"가 나온다. 목업의 "균형형/단기집중/장기빌드업"이라는 스타일
  차이는 실제로는 순수 "기간 차이"로 근사한다(엔진 자체에 스타일/철학
  파라미터가 없음 — `generate_weekly_plan()`은 완전히 결정론적, 목표당
  플랜이 하나뿐).
- "새 프로그램 생성" 실행 자체 = `views_training_wizard.py`의
  `POST /training/wizard/complete`가 이미 하는 것(`add_goal()` → `UPDATE
  goals SET plan_weeks=?` → 주차 루프 `generate_weekly_plan()`+
  `save_weekly_plan()`)을 서비스 함수로 그대로 옮긴다.
- 5-F "진행률"은 `session_outcomes.dist_ratio` 기반 진짜 컴플라이언스
  지표가 어디에도 없어(레거시 화면들도 안 씀) — 레거시
  `views_training_cards.py`/`views_training_fullplan.py`가 쓰는 단순
  "완료 개수/비휴식일수" 비율을 그대로 재사용(새 지표 설계 안 함).

**명시적 제외**: 5-G(일일 세션 상세 — 임의 과거/미래 날짜 조정 근거)는
`adjust_todays_plan()`이 오늘 날짜로 하드코딩돼 있어 날짜 파라미터화가
필요(`P7-IMPL-COACH-PLAN-SESSION-DETAIL`/LATER). "조정 수락" 영속화는 위
설명대로 별도(`P7-IMPL-COACH-PLAN-ADJUSTMENT-ACCEPT`/LATER). 커스텀 훈련
prefs UI(휴식 요일 등)도 범위 밖 — `upsert_user_training_prefs()`를 기본값
으로만 호출.

구현은 `P7-IMPL-COACH-PLAN-ACTIVE`(5-F+Coach 홈, 의존성 없음) →
`P7-IMPL-COACH-PLAN-CREATE`(5-C/D/E, ACTIVE의 `get_active_plan()`을 5-C
진입 판단에 씀) 두 유닛으로 분리(AUTOPILOT QUEUE 참조). `get_static_plan_
templates()`는 `target_time_sec`이 없는 "완주" 목표 케이스를 처리해야
한다 — `analyze_readiness()`가 `goal_time_sec=None`이면 내부에서 크래시
하므로, VDOT 데이터가 있으면 현재 실력 기준 예상 완주 시간을 effective
target으로 대신 쓰고, VDOT 데이터 자체가 없으면 달성 가능성 필드를 전부
None으로 비워 반환한다(에러 raise 안 함 — coding-rules.md 원칙).

---

## [P7-IMPL-TIMELINE-NARRATIVE-FULL] `<TimelineNarrative>`(C7) 완전판 — AI 임베디드 마크업 제외, 기존 trend API 재사용

`04-component-catalog.md` C7의 `NarrativeContent`는 `body: NarrativeSegment[]`
(AI가 생성한 자유 텍스트 안에 `[chart:slug]`/`<EvidenceQuote>` 태그를 섞어
넣고 프론트가 마크다운 서브셋으로 파싱)를 요구한다. **이 부분은 이번에도
구현하지 않는다** — AI가 신뢰성 있게 구조화 태그를 텍스트에 섞어 emit하도록
프롬프트를 설계하는 건 파싱 실패 시 규칙 기반 fallback으로 되돌리기 어렵고
(coding-rules.md "AI 응답 파싱 실패: graceful fallback" 원칙과 정면 충돌 —
현재 `_narrative.py`의 fallback은 완전한 대체 텍스트 생성이지, 부분 파싱
복구가 아님), `P7-IMPL-7B-TODAY-L2`에서 이미 검증된 "text 평문 + evidence
배열 + milestones 배열" 3분리 구조가 잘 작동한다. 대신 `highlights`/인라인
차트/월 탐색은 **AI가 생성하지 않는 고정 UI 요소**로 프론트에서 조립한다.

**핵심 발견 — 인라인 차트에 새 백엔드 불필요**: `P7-IMPL-7B-METRICS-BROWSER`
때 만든 `GET /api/v1/library/metrics/<slug>/trend?period=`
(`metrics_browser_service.get_metric_trend()`)가 이미 `ctl`/`atl` 등 임의
메트릭의 기간별 시계열을 반환하고, 프론트 `getMetricTrend()`
(`frontend/src/lib/api/metrics.ts`)와 `<Sparkline>`(`P7-IMPL-7B-STREAMS`)도
이미 있다. 03a 1-C의 "인라인 차트 [CTL/ATL 추세]"와 "탭 시 확장 → CTL+ATL
2단 스파크라인"(2단계 드릴다운)은 이 기존 API+컴포넌트를 그대로 두 번 호출
(`getMetricTrend('ctl','4w')`, `getMetricTrend('atl','4w')`)하는 것만으로
구현된다 — 새 trend 엔드포인트/쿼리 설계 불필요.

**명시적 제외**: "ATL 급상승 원인"(1-C 확장 패널의 "6/7 Tempo Run TSS 98"
같은 스파이크 원인 근거)은 "이 기간 중 어떤 활동이 급상승을 유발했는가"를
판정하는 새 분석 로직이 필요해 범위 밖 — 스파크라인만 보여주고 원인 근거는
LATER. `highlights`의 `bestPace`도 제외(어느 기간·거리 기준의 "최고 페이스"
인지 정의가 불명확 — PB 판정은 `milestone_service`의 레이스 태그 활동
기준인데 이건 임의 활동 포함 월간 통계라 다른 개념, 새로 정의하지 않음).

**구현**:
- `today_service.get_today_narrative(conn, date=None, config=None, year=None,
  month=None)` — `year`/`month` 추가(둘 다 없으면 기존과 동일하게 오늘 기준).
  값이 있으면 그 달 전체(`{year}-{month:02d}-01` ~ 그 달 말일, 단 이번 달이면
  말일 대신 오늘까지 — 미래 데이터 없음)로 `month_start`/`date`를 계산해 기존
  로직 그대로 재사용(변경 최소화). AI 프롬프트에도 "이번 달"이 아니라 실제
  연월을 넣어 과거 달 조회 시 시제가 안 맞지 않게 한다.
- `highlights` 필드 추가: `{"total_distance_km", "activity_count",
  "longest_run_km", "peak_ctl"}` — `total_distance_km`/`activity_count`는
  기존 월간 집계 쿼리에 `MAX(distance_m)` 컬럼만 추가해 `longest_run_km`까지
  같이 뽑고, `peak_ctl`은 `db_helpers.get_metric_history(conn, 'ctl',
  date_from=month_start, date_to=date)`의 `numeric_value` 최댓값.
- API: `GET /api/v1/today/narrative`에 `?year=&month=` 옵셔널 쿼리 파라미터
  추가(둘 다 있어야 적용, 하나만 오면 무시하고 기존 동작).
- 프론트: 새 `MonthNarrative.svelte`(우측/하단 시트 패널, `MetricBreakdown.
  svelte`의 `fixed inset-0` + `absolute inset-x-0 bottom-0 rounded-t-2xl`
  오버레이/시트 패턴 그대로 재사용) — 헤더에 "← YYYY년 M월 →" 이전/다음 달
  버튼(다음 달이 미래면 비활성화), 본문은 Today L2와 같은 텍스트+evidence+
  milestones 렌더링 재사용, `highlights` 통계 행, CTL 스파크라인(탭하면 같은
  패널 안에서 CTL+ATL 2단으로 확장 — 새 패널 마운트 아님, 로컬 `$state`
  토글). Today L2에 "[이번 달 전체 이야기 보기 →]" 버튼 추가해 이 패널을 연다.

---

## [P7-IMPL-COACH-PLAN-SESSION-DETAIL] 5-G 일일 세션 상세 — 조정 비교는
타입만, 수치는 있는 그대로(가짜 TSS/거리 델타 안 만듦)

`03e-coach.md` 5-G 목업은 "Long Run 18km → 16km", "예상 TSS 105 → 92" 같은
구체적 수치 변화를 보여준다. 실제로 확인해보니 `src.training.adjuster.
adjust_todays_plan()`은 **워크아웃 타입만 하향**한다(`_DOWNGRADE_HIGH`/
`_DOWNGRADE_MOD` — interval/tempo/long → easy/rest 매핑)뿐, `distance_km`/
`target_pace_*`/TSS는 재계산하지 않고 원본 그대로 반환한다. 목업의 "16km"/
"TSS 92"는 실제로 어디서도 계산되지 않는 수치다 — 지어내지 않고, **워크아웃
타입 변경 + 근거만** 비교 화면에 보여준다(예: "Long Run → Easy Run로 조정,
근거: HRV 58ms/체감 피로 7"). 거리·페이스는 조정 여부와 무관하게 계획된
값 그대로 한 번만 표시.

**"조정 수락"/"원래 계획으로" 버튼은 이번에도 안 만든다** — 03e-coach.md
5-G 문서 자체가 "Phase 7c에서 세션 조정 승인 API(`PUT .../accept-
adjustment`)와 연동"이라고 명시해뒀다(`P7-IMPL-COACH-PLAN-ADJUSTMENT-
ACCEPT`/LATER와 동일 결정 — 이미 5-F에서 정한 "표시만" 원칙과 일관).
**세션 메모는 이번에 포함**(문서가 Phase 7c로 미룬 건 승인 API뿐, 메모는
아님) — 새 테이블 없이 기존 `user_inputs`(D3, `UNIQUE(input_date,
input_type)`)에 `input_type='session_note'`로 upsert, `today_service.
save_checkin()`/`get_todays_checkin()`과 완전히 동일한 패턴.

**URL은 문서의 `/coach/plan/:id/session/:week/:day`가 아니라
`/coach/plan/:id/session/:date`로 단순화** — `planned_workouts`가 애초에
`date`(ISO)로 키가 잡혀 있고, 주차/요일은 화면에 라벨로 보여주면 되지
URL 파라미터로 쓸 이유가 없다(주차→날짜 역산 로직을 새로 만들 필요도 없어짐).

**날짜 파라미터화 범위**: `adjust_todays_plan()`이 `date.today()`를
직접 참조하는 지점 3곳 — 본체의 `planned_workouts WHERE date=?`, 내부
`_get_todays_wellness()`의 `daily_wellness WHERE date=?`, `_get_latest_tsb()`
(이건 날짜 필터 자체가 없이 항상 전역 최신값). 셋 다 `date: str | None =
None`(기본값 오늘, 하위 호환)로 파라미터화 — `_get_latest_tsb(conn,
date=None)`는 `date`가 있으면 `scope_id <= date` 조건 추가(과거 조회 시
미래 TSB가 안 섞이게, 없으면 기존과 동일 "전역 최신"). 미래 날짜 조회 시
`daily_wellness`/TSB 둘 다 데이터가 없어 `_fatigue_level({}, None)` →
`score=0` → `"low"`(조정 없음)로 자연스럽게 수렴 — 크래시 없음, 별도
분기 불필요(이미 확인함).

**week_index 계산**: `plan_service._week_index_absolute()`가 "오늘 기준"만
계산하므로, 임의 날짜 기준으로 일반화한 `_week_index_for_date(goal,
target_date)`를 추가(내부적으로 `_plan_date_range()` 재사용, "오늘 Monday"
대신 "target_date의 Monday"로 주차 차이 계산 — `P7-IMPL-COACH-PLAN-ACTIVE`
리뷰 때 고친 goal-scoping 로직과 동일 기반).

**구현 순서**: 단일 유닛(백엔드 파라미터화 + 서비스 함수 1개 + API 2개 +
프론트 페이지 1개로 충분히 작음, 분리 불필요).

---

## [P7-IMPL-PROVIDER-MATRIX] 정체성 매트릭스(3-G-1) — 기간 집계 설계 확정

`P7-DESIGN-7B-API`(3-G-2 유닛) 때 LATER로 미뤄둔 두 가지 — 기간 집계 로직,
그룹별 `strategy`에 따른 `primaryReason` 판정 — 조사 후 이번에 직접 설계
확정(2026-09-23, 사용자가 "오토파일럿 진행" 승인한 조사 범위 안에서 판단).

**그룹 정의 재확인**: 03c 3-G-1 목업은 예시 행으로 CTL/ATL/TSB(피트니스),
평균 페이스/최대 속도, HR avg/max, HRV/Body Battery/Sleep Score, TSS/IF를
보여주지만, 같은 섹션의 서두 문장(204행)은 "**시맨틱 그룹 13개** × Provider
4개"라고 명시 — `src/utils/metric_groups.py`의 `SEMANTIC_GROUPS`가 정확히
13개. 목업 예시 행(CTL/페이스/HR/수면)은 그 13개 그룹 멤버에 하나도 없다
(수면·HRV·BodyBattery는애초 scope='daily' 웰니스라 활동 기반 그룹 개념과
안 맞음, CTL/ATL/TSB는 일별 피트니스 단일값이라 Provider 비교 대상이
아님 — RunPulse 자체 계산치뿐). **결정**: 문서 서두의 명시적 수치("13개")를
근거로 목업 예시 행은 삽화로 간주, 3-G-1 = `SEMANTIC_GROUPS` 13개 ×
기간 집계로만 구현. 3-G-2가 이미 포함하는 "Raw 메트릭 행"(activity_summaries
컬럼) 섹션은 3-G-1에 포함 안 함 — 기간 집계 시 raw 컬럼(페이스/HR 등)까지
포함하면 어느 걸 "이 기간의 대표 페이스"로 볼지에 대한 별도 집계 함수
(평균? 최신?)가 필요해져 범위가 다시 커짐, 그리고 "13개"라는 문서 근거가
없으므로 범위 밖으로 유지.

**기간 집계 전략**: 그룹 내 각 (metric_name, provider) 조합마다 "기간 내
가장 최근 활동에서 그 provider가 보고한 값" 하나를 대표값으로 사용(평균/
합산 아님). 근거: `SEMANTIC_GROUPS` 멤버들은 성격이 다름(VO2Max/VDOT/
threshold_power처럼 시점 스냅샷인 것 vs training_load/trimp처럼 세션당
누적인 것) — 그룹마다 다른 집계 함수(평균 vs 합산 vs 최신)를 새로 설계·
검증하는 대신, "최신값"이라는 단일 규칙을 전체에 균일 적용해 설계 표면을
줄임(3-G-2의 활동 1건 비교와 동일한 해석 축 위에 있음 — "지금 이
활동에서" → "최근 이 기간에서"). 활동 목록은 `v_canonical_activities`
(matched_group_id 기준 소스 우선순위 1건만 남기는 기존 뷰) 재사용해
`start_time` 기준 최신순 정렬, 각 canonical 활동의 형제(matched_group_id
전체, 없으면 자기 자신)에서 `metric_store` 조회 — 3-G-2의 형제 조회
로직과 동일 패턴, provider당 최초 발견(=최신) 값만 채택.

**primaryReason(기간 대표 소스) 판정**: 활동 1건엔 `activity_groups.
primary_source`가 하나뿐이지만 기간에는 여러 활동 그룹이 걸쳐 있음 —
기간 내 모든 matched_group_id의 `primary_source` 최빈값(SQL GROUP BY
COUNT, 동률 시 `_SOURCE_PRIORITY` 낮은 순)을 "기간 대표 소스"로 정하고,
`provider_comparison_service._preferred_provider()`를 그대로 재사용(그룹마다
같은 기간 대표 소스를 넘겨 호출 — 3-G-2가 활동 1건의 `primary_source`를
전체 행에 균일 적용하던 것과 동일 패턴, 그룹별로 다르게 판정하지 않음
— DESIGN-7B-API 때 "그룹별 strategy 문서상 불명확"이라 미뤘던 부분을
이 균일 규칙으로 대체). discrepancy(불일치 감지)는 서로 다른 날짜의
값끼리 비교하게 될 수 있음(provider마다 "최신"이 다른 활동일 수 있어서)
— 이 한계는 인지하되 그대로 허용(3-G-2와 동일 계산 로직 재사용, 새
경고 문구 불필요 — 프론트 `<ProviderComparison>`의 기존 "⚠ 소스 간 차이"
범례가 그대로 의미 있음).

**파일 분리**: `provider_comparison_service.py`가 이미 279줄이라(캡 300)
새 함수를 넣으면 캡 초과 — `src/services/provider_matrix_service.py`
신설, `provider_comparison_service.py`의 `_preferred_provider`/
`_build_values`/`_calc_discrepancy`/`_ordered_providers`를 그대로 import
재사용(중복 작성 안 함).

**프론트 재사용**: `<ProviderComparison>` 컴포넌트는 03c 목업 자체가
`<ProviderComparison showPrimaryReason=true>`로 3-G-1에 재사용을 명시해둔
컴포넌트 — 수정 없이 그대로 사용(데이터 shape만 `mode: 'period'`로
확장, "불일치 범례"·"대표값 ★" 렌더링 로직 전부 기존 그대로). 목업의
"[정체성 매트릭스]/[활동별 비교]" 탭 전환 UI(한 페이지에서 모드 전환 +
활동 선택 드롭다운)는 이번 스코프 밖 — 활동별 비교는 이미 활동 상세
페이지(`/library/[id]/providers`)에서 별도 진입 가능하므로 굳이 통합 안 함,
`/library/providers`는 매트릭스 전용 페이지로 신설. 기간 선택은 목업의
"[최근 4주 ▾]" 드롭다운 대신 버튼 3개(4주/8주/12주)로 단순화(다른 화면의
기간 선택 패턴과 일관 — `library/metrics/[slug]`의 기간 버튼 참조).

**기존 비활성 버튼 연결**: `frontend/src/routes/library/+page.svelte`(홈
탭바)와 `frontend/src/routes/library/metrics/[slug]/+page.svelte`(메트릭
상세, "Provider 비교" 버튼) 둘 다 이 유닛을 기다리며 `disabled`로 남겨둔
자리 — 이번에 `{base}/library/providers`로 연결. 메트릭 상세 쪽은 특정
슬러그로 스크롤/필터링하지 않고 매트릭스 페이지 전체로 이동(해당 슬러그가
13개 그룹 멤버가 아닐 수도 있음 — 앵커 연동은 범위 밖, 후속 필요 시
별도 설계).

---

## [P7-IMPL-TODAY-NEXT-SESSION] Today L2 "다음 세션 현황" — 표시 전용 블록

`03a-today.md` 1-A(Phase 7b 완성형)의 L2 3번째 블록("다음 세션 현황, 구 Plan
'보기' 흡수")이 현재 `/today`에 없다 — 내러티브·마일스톤은 붙었지만 이 블록과 L3
링크 블록은 미구현(1-A' 7a 스텁이 약속한 "이번 주 준수율·다음 세션" 한 줄도 빠져
있음). 백엔드는 이미 전부 있다: `GET /coach/plan/active`(week_index·workouts·
goal.plan_weeks), `GET /coach/plan/adjustment`(오늘 조정) — 새 API 불필요, 프론트
전용 유닛(2026-09-24).

**문서 불일치 확인**: `07-migration-roadmap.md` 7c 산출물에는 "Today L2 '다음
세션' — Plan 연동 활성화, 상태 조정 반영"이 있지만, 화면 명세인 `03a-today.md`
1-A는 이 블록을 "Phase 7b 완성형 기준"에 포함시키고 있고 Coach 정적 플랜(5-F/
5-G)이 이미 병합돼 재료가 다 있다. **결정**: 화면 명세(03a)를 따라 표시 전용
부분을 지금 구현, 7c에 남기는 건 "조정 수락/원래대로" 버튼(승인 API 필요,
`P7-IMPL-COACH-PLAN-ADJUSTMENT-ACCEPT` — 5-G와 같은 선례)뿐.

**목업 대비 축소**:
1. "CTL 68/80 (+12 필요)" — 활성 플랜/목표에 목표 CTL 값이 저장돼 있지 않다
   (`ActivePlan`에 `ctl_current`만 있음). 지어내지 않고 "CTL {현재}"만 표시.
2. 오늘 조정("⚠ 상태 조정") — `/coach/plan/adjustment`는 오늘 날짜 전용이라
   보여줄 세션이 오늘일 때만 표시. 다른 날짜 세션은 "세션 상세 →" 링크만(상세
   페이지가 그 날짜 기준으로 조정을 다시 계산함).
3. 이번 주 준수율 — API의 `compliance_pct`(플랜 전체 기간 대비 완료율, 미래
   워크아웃도 분모에 들어가 "달성률"에 가까움)를 쓰지 않고, `workouts`(이번 주)
   에서 휴식 제외 완료/전체를 프론트에서 계산(목업의 "5/7 완료" 의미 그대로).
4. 보여줄 "다음 세션" = 오늘 이후(포함) 이번 주 첫 비휴식 워크아웃. 이번 주에
   없으면 "이번 주 남은 세션이 없습니다"(다음 주 조회 API 없음 — 범위 밖).
5. 활성 플랜 없음(404) → 빈 상태 카드 + "Coach에서 플랜 만들기 →"(/coach/plan).

**부수 정리**: `WORKOUT_LABELS`가 coach 플랜 상세·세션 상세 두 페이지에 중복
정의돼 있음 — 이 유닛이 세 번째 사용처가 되므로 `$lib/format.ts`로 이동
(`race` 라벨 추가: DB CHECK 제약에 있는데 두 사본 모두 누락).

---

## [P7-IMPL-EVIDENCE-DRILL] 근거 칩(EvidenceQuote) 탭 → 계산 분해 패널 — 죽은 칩 연결

`03g-common-patterns.md` 7-3(P1 Evidence-First): "칩 탭 → 원천 데이터 표시". 현재
`<EvidenceQuote>`는 `onOpen`이 없으면 비대화형 `<span>`으로 그려지는데(컴포넌트 주석:
"7a엔 열어줄 MetricBreakdown 패널이 없어서"), 패널이 7b에 생긴 뒤에도 사용처 3곳
(Today L0 RecommendationCard, Today L2 내러티브, MonthNarrative 패널) 어디서도
`onOpen`을 넘기지 않아 **모든 근거 칩이 죽어 있다**(2026-09-24 코드 대조로 발견).
07 로드맵 7b 검증 기준 "드릴다운 3레벨: Summary → Breakdown → Library"의 첫 고리가
빠진 상태.

**칩마다 드릴 가능 여부가 다르다**: 브리핑/내러티브 근거 슬러그는 `tsb`·`utrs`·`ctl`
(RunPulse 일별 메트릭 — `metric_store` 대표 행 있음)과 `monthly_distance`·
`sleep_score`(활동 집계·웰니스 컬럼 — `metric_store` 행 없음, `get_metric_breakdown`
이 None→404). 전부 탭 가능하게 하면 일부 칩이 "불러올 수 없습니다"로 끝나는 가짜
버튼이 된다. 프론트에 허용 슬러그 목록을 하드코딩하면 백엔드 변경과 어긋나므로,
**백엔드가 근거 항목마다 `drill` 참조를 붙인다**: `{"scope_type": "daily",
"scope_id": <그 근거가 기준한 날짜>}` — 그 날짜에 `metric_store` 대표 행(`get_primary_
metric`)이 실제로 있을 때만, 없으면 `null`. 프론트는 `drill != null`인 칩만
`onOpen`을 넘긴다(나머지는 기존처럼 비대화형 span — 정직한 표시).
`scope_id`를 근거별로 들고 가는 이유: MonthNarrative의 과거 달은 근거 기준일이
말일이라 Today가 쓰는 `status.date`(오늘)와 다르다.

**같이 발견된 실버그 — `MetricBreakdown`이 slug 변경에 재조회하지 않음**: 컴포넌트가
데이터를 `onMount`에서 한 번만 가져온다. Today는 "입력 메트릭" 탭(`onDrillInput`) 시
`drillStack`에 slug를 push해 **같은 인스턴스의 `slug` prop만 바꾸는데** 재조회가
없어 패널이 첫 메트릭 내용 그대로 남는다 — 드릴-인이 사실상 동작하지 않음. 칩
드릴을 붙이면 더 자주 밟게 되므로 같은 유닛에서 `$effect`로 slug/scopeType/scopeId
변경 시 재조회(경합 방지용 취소 플래그 포함)하도록 고친다.

**코드 정리**: `adaptEvidence()`가 Today 페이지와 MonthNarrative에 중복 정의돼 있고
이 유닛이 둘 다 바꿔야 하므로 `$lib/evidence.ts`로 합친다. `today_service.py`가
286/300줄이라 드릴 부착 헬퍼는 `_narrative.py`에 둔다.

---

## [P7-IMPL-TODAY-MILESTONES-PANEL] Today "전체 마일스톤" 패널(1-D) + PB 활동 링크

`03a-today.md` 1-D: L2 "[전체 마일스톤 →]" → 우측 패널에 전체 마일스톤 목록(PB는
활동 상세로 링크, 재계산은 상세 문구). 백엔드는 이미 있다 — `GET /api/v1/today/
milestones?limit=`(`get_today_milestones`, 병합 완료). 프론트엔 API 함수도 버튼도
패널도 없어 API가 미사용 상태(2026-09-24 대조로 발견). 프론트 전용.

**결정**: (1) `getTodayMilestones(limit)` 추가, 신규 `MilestonesPanel.svelte`(기존
MonthNarrative/MetricBreakdown과 같은 하단 시트 오버레이 패턴). (2) 목업의 링크 대상
`/library/activities/4821`은 실제 라우트가 `/library/[id]`라 그쪽으로(마일스톤
`activity_id`는 `activity_summaries.id`). (3) 재계산(`metric_recompute`)은 `detail`
컬럼 문구를 그대로 표시(백엔드가 이미 "formula_v2 적용 — CTL 66→68" 형태로 채움 —
프론트가 old/new 값으로 문구를 조립하지 않음). (4) 페이지네이션은 없이 `limit=50`
단일 조회(목업에도 페이지네이션 없음, 마일스톤은 누적 100km 단위·PB·재계산이라
수십 건을 넘기 어려움).
(5) Today L2의 마일스톤 5개 목록에도 PB 활동 링크를 붙이고 "전체 마일스톤 →" 버튼을
추가.
