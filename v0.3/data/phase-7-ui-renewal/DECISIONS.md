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

---

## [P7-IMPL-ACTIVITY-TABS-LAPS] 활동 상세 탭 바 공용화 + 랩 탭

`03c-library.md` 3-C/3-D는 활동 상세 탭을 `[요약][스트림][랩][메트릭]`으로 정의한다. 구현은
요약/스트림/소스 비교 3개 페이지가 각자 탭 마크업을 복붙해(2026-09-24 대조) 구성이 서로 다르고
(요약엔 비활성 "랩"/"메트릭" 버튼, 스트림 페이지엔 "랩" 자체가 없음), 랩 데이터는 API가
`activity.laps`로 이미 내려주는데 화면이 없다.

**결정**: (1) 탭 바를 `ActivityTabs.svelte` 하나로 뽑아 세 페이지가 공유 — 탭 추가는 한 곳만
고치면 된다(다음 유닛 `ACTIVITY-METRICS-TAB`이 "메트릭" 탭을 여기 추가). (2) 랩 화면은 03c에
와이어프레임이 없어 스스로 설계: 인터벌·크루즈 세트 비교가 랩 화면의 핵심 용도라 랩별
페이스를 **가장 빠른 랩 대비 막대**로 보여준다(수치만 나열하면 세트 간 차이가 안 보임). 랩
번호는 소스마다 `lap_index`가 0/1 기반이 달라 배열 순서를 쓴다. (3) 소스 배지는 P3(Provider
Transparency)에 따라 랩 소스(`activity_laps.source`)를 표기. (4) 목업의 "소스 비교"는 3-C
탭 목록엔 없지만 7a에서 이미 만든 화면이라 탭에 유지한다(끝자리).
(5) `ActivityDetail.laps`/`streams`가 `unknown[]`이라 랩 타입을 추가로 정의.

---

## [P7-IMPL-ACTIVITY-METRICS-TAB] 활동 상세 "메트릭" 탭

`03c-library.md` 3-C 탭 목록에 "메트릭"이 있고 7a에선 비활성 버튼으로만 존재한다. 데이터는
`activity.metrics_by_category`(is_primary=1 대표값, 단위·설명·provider 포함)로 이미 내려온다.
요약 탭은 8개만 보여주므로 "이 활동의 모든 분석 수치를 보고 싶다"는 요구(앱 정체성: 분석의
투명성)를 채우는 곳이 이 탭이다.

**결정**: (1) 카테고리는 `metric_registry.METRIC_CATEGORIES`(16 도메인)의 한글 라벨·순서를
`lib/metrics.ts`에 복제한다(백엔드가 라벨을 안 내려주고, 라벨 API를 새로 만들 사안은 아님).
(2) 행 탭 → `MetricBreakdown`(`scopeType='activity'`, `scopeId=활동 id`): 백엔드
`get_metric_breakdown`이 이미 scope_type을 받는다. 입력 메트릭 드릴-인은 Today와 같은
스택 패턴(scope 이어받기). (3) 검색 입력을 둔 이유: 활동당 메트릭이 수십~백여 개라 카테고리
접기만으로는 특정 수치를 찾기 어렵다. (4) 값 포맷 함수(`formatMetricValue`)는 요약 페이지의
`metricDisplayValue`와 같은 규칙이라 `lib/metrics.ts`로 뽑고, 요약 페이지 전환은 다음 유닛
(`ACTIVITY-SUMMARY-ENRICH`)이 같은 파일을 어차피 고치므로 거기서 한다.

---

## [P7-IMPL-ACTIVITY-SUMMARY-ENRICH] 활동 요약 탭 보강 (핵심 메트릭 정정·드릴·페이스 흐름·HR 존)

`03c-library.md` 3-C 목업과 구현(`library/[id]/+page.svelte`)을 대조(2026-09-24)해 발견:
1. **핵심 메트릭 선택 로직이 사실상 깨져 있음** — `CATEGORY_ORDER`가 `performance/running/fitness/
   wellness/environment`인데 `metric_registry`의 실제 카테고리는 16 도메인(`hr/pace/load/
   efficiency/capacity/…`)이라 `power` 외엔 매칭이 없고, 결국 dict 삽입 순서로 임의의 8개가 뜬다.
   카테고리 기반 정렬을 버리고 3-C 목업이 명시한 항목(HR max·케이던스·TSS·VO2Max·효율지수·GCT…)의
   **이름 우선순위 목록**으로 고른다. avg_pace/avg_hr는 상단 통계 바가 이미 보여줘 제외.
2. **P2 위반**: `MetricCell drillable={false}` — 메트릭 탭(전 유닛)과 같은 패턴으로
   `MetricBreakdown`(scope=activity)을 연다.
3. **페이스 분포 차트·HR 존 분포 누락**: 스트림은 `activity.streams`로 이미 내려와 요약에서도
   쓸 수 있다 → 페이스/심박 스파크라인(스트림 탭 링크). HR 존은 `hr_zone_N_sec`(Garmin/Intervals
   추출)에서 비율을 계산 — `_pct` 메트릭은 어느 추출기도 안 채워서 초 단위에서 계산한다. 소스 배지
   유지(P3).
**차이(의도적)**: 목업의 "AI 코멘트"는 활동별 AI 생성 설계가 없어 제외, "환경 컨텍스트"는 다음
유닛(`ACTIVITY-ENV-CARD`), "QuickInput compact"는 체크인이 하루 1건(`UNIQUE(input_date,
input_type)`)이라 활동별 입력 모델이 없어 제외(스키마 설계 필요 — LATER).

---

## [P7-IMPL-ACTIVITY-ENV-CARD] 활동 상세 환경 컨텍스트 카드

`03c-library.md` 3-C 목업은 기온·습도·풍속·AQI + 체감 WBGT + 훈련 가능 판정 카드를 그린다.
확인 결과 활동 스코프 `metric_store`의 `weather` 카테고리에는 기온(`weather_temp_c`)·습도·풍속·
이슬점·기압·날씨 상태가 있고(추출기가 채움), **AQI·WBGT는 저장·계산이 없다**. 목업을 채우려고
값을 만들어내는 건 P1(근거 우선)·투명성 정체성에 어긋나므로 **있는 값만 카드로 보여주고 AQI/WBGT/
판정은 제외**한다(데이터가 생기면 필드 목록에 한 줄 추가). 기기 온도(`avg_temperature`)는
API 날씨 기온이 없을 때만 보조로 표시. 소스 배지는 첫 표시 항목의 provider(P3). 데이터가 없는
활동에선 카드 자체를 숨긴다(빈 카드 금지).

---

## [P7-IMPL-COACH-CHECKIN-CONTEXT] QuickInput 체크인 → Coach 채팅 컨텍스트

`03e-coach.md` 5-A는 QuickInput 캡션으로 "(Coach 질문에 자동 컨텍스트 활용)"을 명시하고, `03g` 7-5
(P6 One Finger Reach)의 존재 이유가 "10초 입력이 분석에 쓰인다"이다. 그런데 2026-09-24 대조 결과
`src/ai/`는 `user_inputs`를 **한 번도 읽지 않는다**(`chat_context_builders._build_base_context`는
메트릭·웰니스·최근 활동만). 즉 사용자가 피로도·통증을 입력해도 Coach는 모른다 — "데이터 통합/
소유" 정체성과 P6의 약속이 깨진 상태이고, 프론트에 캡션을 붙이기 전에 백엔드 배선이 먼저다.

**결정**: (1) 기본 컨텍스트에 체크인 한 줄을 추가(모든 provider·의도 공통 — 자기 보고는 어떤
질문에서도 유효). (2) 날짜 범위 [today-1, today+1]: `save_checkin()`은 SQLite `date('now')`(UTC)로
날짜를 찍고 컨텍스트의 `today`는 서버 로컬(KST)이라 새벽(00~09시)엔 하루 어긋난다 — 정확히
`today`만 조회하면 새벽에 체크인이 안 보이는 버그가 된다. (3) 새 모듈로 분리(`chat_context_
builders.py`가 이미 301줄). (4) 메모는 200자로 자름(프롬프트 크기·주입 표면 제한). 통증 enum은
한글 라벨로 변환. (5) 빌드 실패는 삼키고 채팅 계속(기존 빌더 패턴).
**후속(같은 배치)**: `COACH-HOME-QUICKINPUT`이 Coach 홈에 QuickInput compact를 붙인다 — 캡션이
사실이 된 뒤에.

---

## [P7-IMPL-COACH-HOME-QUICKINPUT] Coach 홈 QuickInput(compact) + 체크인 전용 GET

`03e-coach.md` 5-A Coach 홈 마지막 섹션이 `<QuickInput compact=true>`(오늘 컨디션 입력 →, 입력됐으면
"피로 6 · 통증 없음 ✓")인데 구현엔 없다. Today 화면에서만 체크인을 받으면 Coach 대화 직전에
입력하려는 동선(P6 One Finger Reach)이 끊긴다.

**결정**: (1) 체크인 조회용 `GET /api/v1/today/checkin` 신설 — 기존엔 `GET /today`가 체크인을
같이 내려줬지만 Coach 홈이 그걸 쓰려면 상태·브리핑 계산까지 매번 태워야 한다(서비스
`get_todays_checkin`은 이미 있어 라우트만 추가, 읽기 전용). (2) 저장은 기존 `POST /today/checkin`
재사용(같은 날짜 UPSERT라 Today와 Coach 홈 어디서 입력해도 같은 행). (3) 캡션 "Coach 답변에
자동으로 반영됩니다"는 `COACH-CHECKIN-CONTEXT`가 먼저 배선을 끝냈을 때만 사실 — 그래서 dep.

---

## [P7-IMPL-ACTIVITIES-LIST-MOBILE] 활동 목록 — 모바일 행 레이아웃 + 검색·거리 필터

합성 데이터 서버 + 헤드리스 브라우저(390px 뷰포트) 스모크(2026-09-24, 이 세션 처음으로 실제 렌더링을
확인)에서 발견: `library/activities`의 목록 행이 페이스·심박을 `hidden … sm:inline`으로 숨겨 **폰에선
날짜·이름·거리·시간·배지만 보인다**. 앱이 하단 3탭 모바일 우선이고 `03c` 3-B 목업 행이 `5:27/km HR 138`을
보여주는 것과 어긋난다 — 러닝 목록에서 페이스는 가장 먼저 보고 싶은 값.

**결정**: (1) 한 줄 flex(이름이 좁은 폭에서 잘림) → **2줄 행**: 1줄 이름+소스 배지+›, 2줄 날짜·거리·시간·페이스·심박
(공간이 좁으면 wrap). (2) 03c 3-B 필터 `[검색…]`·`[거리 ▾]` 추가 — 서비스 `get_activity_list()`가 이미 `search`·
`min_distance_m`을 지원해 라우트에 `q`·`min_km`만 연결(`min_km` 비숫자는 400). (3) 검색은 300ms 디바운스 + 요청
번호로 늦게 온 응답 무시(빠르게 타이핑할 때 이전 결과가 덮는 경합 방지). (4) 이름 LIKE의 `%`/`_`가 사용자 입력에서
와일드카드로 동작하지만 단일 사용자 로컬 앱이라 이스케이프는 하지 않음(범위 밖).

---

## [P7-IMPL-METRICS-BROWSER-PROVIDER] 메트릭 브라우저 Provider 배지 + 필터

`03c-library.md` 3-E 카드는 `[RunPulse]`/`[Garmin]` 배지를 그리고(★ P3 Provider Badge) 상단에
`[모든 Provider ▾]` 필터를 둔다. 구현은 스파크라인·카테고리 칩은 있지만 provider를 소문자 원문
텍스트(`runpulse`)로만 찍고 필터가 없다 — MetricCell·활동 목록·소스 비교가 모두 `providerLabel`/
`providerBadgeClass`로 통일한 P3 표기와 이 화면만 다르다(2026-09-24 스모크 텍스트에서 발견).

**결정**: (1) 배지는 공용 `providerLabel/providerBadgeClass` 재사용(표기 통일). (2) Provider 필터는 칩
행 — 목업의 드롭다운 대신 이미 있는 카테고리 칩과 같은 컴포넌트 문법으로(모바일 한 손 조작, 새 위젯
없음). 등장 provider가 1종뿐이면 필터가 의미 없어 숨김. (3) 필터 후 빈 카테고리는 섹션 자체를 숨김.

---

## [P7-IMPL-EVIDENCE-EMPTY-LABEL] 근거 없는 결론의 "(데이터 부족)" 표시

`03g` 7-3(P1 Evidence-First): AI 결론엔 근거 칩이 필수이고, **원천 데이터가 없는 결론은
"(데이터 부족 — 추후 업데이트)" 레이블을 표시**한다. 구현은 근거 목록이 비면 그냥 아무것도 안 그린다 —
빈 데이터베이스 스모크(2026-09-24)에서 Today L0 권고("데이터 수집 중입니다")와 L2 내러티브("훈련
기록이 아직 없습니다")가 근거 표시 없이 끝났다. 근거가 없다는 사실 자체가 투명성 정보이므로 명시한다.

**범위**: RecommendationCard(Today L0 브리핑), Today L2 내러티브, MonthNarrative 세 곳.
Coach 채팅 답변은 자유 텍스트 AI 응답이라 근거 칩을 구조화해 받는 설계가 없다(7-3의 "Coach 답변" 항목은
별도 설계가 필요해 이번 범위 밖).

---

## [P7-IMPL-PLAN-ADAPTATION-STATE] 플랜 상세 "적응 상태" 섹션(ACWR·HRV·주간 피로도)

`03e-coach.md` 5-F 목업엔 주간 세션 목록 아래 "적응 상태"(ACWR 1.12 ●적정 / HRV 58ms ●기준 −7% (경계) /
피로도 주간 평균 5.2)가 있다. 구현(`coach/plan/[id]`)엔 세션 목록만 있고 이 섹션이 없어, 플랜이
"내 상태에 묶여 조정된다"(P7 State-Bound Plan)는 근거를 사용자가 볼 수 없다(2026-09-24 스펙 대조).
데이터는 모두 이미 존재: `acwr`(일별 primary 메트릭), `daily_wellness.hrv_last_night/hrv_weekly_avg`,
`user_inputs.fatigue`(체크인).

**결정**: (1) 새 서비스 `adaptation_service.get_adaptation_status()`(읽기 전용, `plan_service.py` 확장 대신
분리 — 책임이 다르고 파일 크기 여유) + `GET /coach/plan/adaptation`. 항목이 없으면 None(빈 상태를 에러로
만들지 않음). (2) 구간은 문서화된 관례로: ACWR 0.8~1.3 적정(목업 명시)·1.3~1.5 주의·1.5 초과 위험·0.8 미만
저부하(Gabbett), HRV는 주간 평균 대비 −5% 이상 정상·−10% 이상 경계·그 미만 저하(목업 −7%가 경계인 것과
일치). 임계값은 사람이 조정 가능한 상수로 서비스 상단에 둠. (3) **P2 정직성**: `metric_store` 행이 있는 ACWR만 탭
→ `MetricBreakdown`(계산 분해), HRV·피로도는 원천이 다른 테이블이라 비대화형(EVIDENCE-DRILL의 "근거가 없는
칩은 가짜 버튼으로 만들지 않는다"와 같은 원칙). (4) 날짜는 로컬 `date.today()`(다른 서비스와 동일).
(5) 5-F 목업의 "CTL 진행 68/80 (+12 필요)"는 목표 CTL이 저장되지 않아(이전 결정 `TODAY-NEXT-SESSION`과
동일 사유) 이번에도 범위 밖.

---

## [P7-IMPL-NARRATIVE-CACHE] Today 내러티브 LLM 호출 캐시

`get_today_narrative()`는 호출마다 AI provider 체인을 실행한다(2026-09-24 합성 데이터 서버 로그에서
`/api/v1/today/narrative` 한 번에 Gemini·Groq 호출 시도가 찍히는 것으로 발견). Today 로더가 그 응답을
기다리므로 AI 키가 유효한 실사용에선 화면을 열 때마다 LLM 1회(수 초 지연 + 비용)이고, MonthNarrative
패널의 달 이동마다 또 호출된다. 저장소엔 이미 `ai_cache`(탭별 AI 해석 캐시 — ADR-011 무효화 규칙)가 있는데
내러티브만 안 쓴다.

**결정**: (1) 기존 `ai_cache`를 그대로 재사용(새 캐시 계층·스키마 없음): 탭 `today_narrative`, 키
`{조회 달 시작일}:{기준일}`. 무효화는 ai_cache 규칙(신규 활동·웰니스·날짜 변경·8h TTL)에 위임.
(2) **AI 성공 결과만** 캐시 — 규칙 기반 fallback은 싸고, AI가 복구되면 즉시 AI 결과로 바뀌어야 함.
(3) `today_service.py`가 289/300줄이라 헬퍼는 `_narrative.py`에 둠. (4) 캐시 저장 실패는 삼키고 결과는
그대로 반환(캐시는 최적화일 뿐 — 기능 실패로 만들지 않음). (5) 메트릭 재계산처럼 활동·웰니스 추가 없이
CTL만 바뀌는 경우엔 최대 8h 동안 이전 문장이 남을 수 있음 — ADR-011의 기존 트레이드오프를 그대로 수용.

---

## [P7-IMPL-PROVIDER-STATUS] Library 홈 Provider 데이터 현황

`03c-library.md` 3-A는 Library 홈 하단에 `[Garmin ●연결] 마지막 동기화 2시간 전 · 활동 312건` 형태의 Provider별
현황을 둔다(P3 Provider Transparency: 사용자가 "어떤 소스에서 어떤 데이터가 얼마나 들어와 있는지"를 한눈에
확인). 구현은 "준비 중" 문구뿐이었다(2026-09-24 합성 데이터 스모크의 Library 홈 텍스트에서 발견).

**결정**: (1) 이미 있는 데이터만 쓴다 — 활동 수·최근 활동일은 `activity_summaries.source` 집계, 마지막 동기화는
`source_payloads.fetched_at` 최댓값(새 테이블·sync 코드 변경 없음). (2) 목업의 `●연결/○미연결`은 자격증명
유무(config 읽기)가 필요한데 그건 7d Data 화면(`data_service.get_sources_status`, 03f)의 책임이고 비밀값
경계를 넘는다 — 그래서 이 화면은 **저장된 데이터 유무**(`●데이터 있음/○데이터 없음`)로 표기한다(사실만 말함).
(3) Provider는 4종 고정 순서(garmin·strava·intervals·runalyze)로 항상 4행 — 없는 provider도 "데이터 없음"으로
보여 P3 투명성(어떤 소스가 비었는지)을 살린다. (4) 활동 수는 통합 전 원본 행 수(`v_canonical_activities`가
아님) — provider별 보유량을 보이는 화면이라 중복 제거 전 수치가 맞다.

---

## [P7-IMPL-PAGE-TITLES] 페이지별 브라우저 탭 제목

`frontend/src`에 `<title>`이 하나도 없어(2026-09-24 스모크에서 `page.title()`이 전 화면 빈 문자열) 탭·기록·북마크가
전부 URL로만 보인다. 앱을 여러 탭/북마크로 쓰는 모바일 사용(P6)에서 화면 식별이 안 된다.

**결정**: (1) 제목은 각 `+page.svelte`의 `<svelte:head>`에 둔다(SvelteKit 관례 — 화면이 자기 제목을 소유).
(2) 레이아웃/`app.html`에 기본 `<title>`을 두지 않는다 — 같은 문서에 `<title>`이 둘이면 첫 번째가 이겨 페이지
제목이 가려질 수 있고, 모든 화면이 제목을 가지므로 기본값이 필요 없다. (3) 형식 `<화면> · RunPulse`. 동적
경로 두 곳(활동 상세·메트릭 상세)은 이미 로드된 이름/라벨을 써 탭에서 대상을 구분하게 한다.

---

## [P7-IMPL-STREAMS-SCRUB] 스트림 화면 시간 눈금 + 스크럽

`03c-library.md` 3-D 목업은 스트림 위에 시간 눈금(`0  15m  30m  45m  55m`)을 두고 "마우스 호버 / 터치 스크럽 →
해당 시각 수치 표시"를 명시한다. 구현은 스파크라인만 세로로 나열해 "지금 몇 분 지점인지", "그 시점 페이스·심박이
얼마인지"를 알 수 없었다(화면 하단에 "정밀 시간축은 후속 과제"라고 스스로 적어둠).

**결정**: (1) 스파크라인 축은 그대로 **포인트 인덱스**로 두고(재샘플링·SVG 축 재작성 없음) 눈금 라벨만 그
인덱스 지점의 실제 `elapsed_sec`로 붙인다 — 일시정지가 있어도 라벨이 거짓이 되지 않는다(위치는 인덱스 등간격,
라벨은 실제 시간). (2) 순수 계산(`indexAtFraction`, `axisTicks`)은 `lib/streamAxis.ts`로 빼 Node 테스트 러너로
검증(컴포넌트 테스트 러너가 없는 프로젝트라 로직만 단위 테스트). (3) 스크럽은 Pointer Events 한 벌(마우스 호버 +
터치 드래그)이고 `touch-action: pan-y`로 세로 스크롤을 뺏지 않는다. (4) 판독 줄은 높이 고정 — 스크럽 시작/종료로
아래 차트가 밀리지 않게.

---

## [P7-IMPL-TODAY-FITNESS-CHART] Today L2 인라인 CTL/ATL 추세 차트

`03a-today.md` 1-A는 L2 성장 내러티브 문단 아래에 `인라인 차트: [CTL/ATL 추세]`를 두고 탭하면 우측 패널(1-C,
이번 달 전체 이야기)로 이어지게 한다. 구현의 Today는 텍스트·근거 칩·마일스톤뿐이라 "CTL이 꾸준히 상승했다"는
문장을 눈으로 확인할 수 없었다(브라우저 스모크에서 `/today`에 `<svg>` 0개로 발견).

**결정**: (1) 새 백엔드 없음 — 3-F 메트릭 상세가 쓰는 `getMetricTrend('ctl'|'atl','4w')`를 Today 로더에서 재사용
(실패하면 차트만 생략, 페이지는 그대로). (2) 기존 `Sparkline`은 단일 계열·자동 스케일이라 CTL/ATL을 겹치지
않고 **위아래로 쌓고** 각자 현재값을 라벨로 붙인다 — 서로 다른 스케일을 한 축에 겹쳐 그리는 거짓 비교를 피함.
(2b) 목업은 ATL을 CTL 위에 같은 축으로 겹치지만, 축 통일·툴팁이 필요한 본격 차트 컴포넌트는 7b 잔여 범위라 보류.
(3) 탭 동작은 목업대로 1-C(이번 달 전체 이야기 패널)를 연다 — 메트릭 상세로의 드릴은 그 패널 안 근거 칩이 담당.

---

## [P7-IMPL-VALUE-FORMAT] 메트릭 값의 단위 인지 표기 통일

실데이터(pansongit 계정 DB 복사본, 활동 1,421건) 화면 리뷰: 수면 시간 `22440 sec`, 레이스 예측 `15750 sec`,
소스 비교의 총 시간 `8357 sec`·거리 `24207.9 m`, 활동 요약의 고도 `↑26.07999999821186 m` — 값이 원시 단위·부동소수
잡음 그대로 나온다. 웰니스 화면만 `9h 5m`로 포맷돼 화면 간 표기도 어긋난다. 합성 데이터에선 값이 작아 안 보였다.

**결정**: (1) 단위→표기 규칙을 `format.ts`의 순수 함수 `formatUnitValue` 하나로 모은다(초→시:분:초, sec/km→페이스,
1000m 이상→km, 그 외 소수 1자리·100 이상 정수). 메트릭 브라우저·소스 비교·활동 메트릭이 같이 쓴다. (2) 순수 함수라
Node 테스트 러너로 검증. (3) 소스 비교 행은 셀 값이 변환되므로 단위 줄도 변환 후 단위로 보인다.

---

## [P7-IMPL-PROVIDER-BADGE-LAYOUT] Provider 배지 컴팩트화 + 소스 비교 표 모바일 정합

실데이터 화면 리뷰: 메트릭 브라우저에서 `RunPulse · formula_v1` 배지가 카드 폭의 절반 이상을 차지해 메트릭 이름이
2글자(`Ch…`)만 남는다. Today MetricCell도 같은 배지가 2줄로 접힌다. 소스 비교 표는 480px 최소폭 + "대표값" 별도
열이라 390px에서 대표값 열이 잘린다. 합성 데이터(짧은 이름·배지 `RunPulse`)에선 안 보였다.

**결정**: (1) 카드형 표시에선 배지를 컴팩트(`RunPulse`)로 하고 공식 버전(`formula_v1`)은 title(길게 누름/호버)과
MetricBreakdown 패널에 둔다 — P3(01 문서)가 허용하는 "배지 또는 MetricBreakdown 패널에 표시". (2) 메트릭 브라우저는
이름을 카드 전폭 2줄로 먼저, 값 줄 오른쪽 아래에 배지. (3) 소스 비교 표는 대표값 열을 없애고 대표 소스 셀에 ★를
붙인다 — 모든 열이 390px에 들어오고, "왜 대표값인가"(primaryReason)는 셀 title로 유지.

---

## [P7-IMPL-STREAMS-TRUTH] 스트림 화면의 거짓 시간축·이상치 차트 교정

실데이터 리뷰: 2시간 19분 장거리 러닝의 스트림 시간 눈금이 `0…28m`로 끝난다. Garmin 상세 스트림은 downsample돼
오는데 추출기가 `directElapsedDuration`이 없을 때 샘플 인덱스 `i`를 `elapsed_sec`로 저장한다(활동 15302: 1692점,
elapsed 0..1691, 실제 8357초). 합성 데이터는 `elapsed_sec = t*10`이라 안 드러났다. 또 GPS 스파이크(페이스
`4:20 – 15:08 /km`)가 스파클라인 범위를 잡아 나머지 구간이 납작해진다.

**결정**: (1) UI는 저장값을 맹신하지 않는다 — 마지막 elapsed_sec가 활동 총 시간의 90% 미만이면 등간격 샘플로 보고
총 시간에 비례해 환산한다(`streamSeconds`). 틀린 시각을 보이느니 총 시간 기준 환산이 낫다(downsample은 등간격).
(2) 이상치는 상·하위 2% 백분위로 clamp해 차트·범위 라벨에 쓰고 화면에 그 사실을 적는다(정보를 조용히 숨기지 않음).
(3) 저장 데이터 자체(elapsed_sec=인덱스) 정정은 추출기 수정 + raw payload 재처리가 필요해 별도 BACKLOG 항목
(P7-DATA-STREAM-ELAPSED)으로 분리 — UI 교정은 그 뒤에도 무해(90% 이상이면 그대로 씀).

---

## [P7-IMPL-COACH-MARKDOWN] Coach 답변의 마크다운 렌더링

실데이터 화면 리뷰: Coach 스레드가 `**오늘의 훈련 추천**`·`- TSB -28.4 …`를 마크다운 기호 그대로 보이고, 대화
목록 미리보기에도 별표가 남는다. 합성 시드의 답변은 평문이라 안 보였다. 답변 아래 `rule`(답변 출처 내부 코드)도 그대로다.

**결정**: (1) 마크다운 전체가 아니라 챗봇이 실제로 쓰는 최소 집합(굵게·목록·제목)만 순수 함수로 해석 — 외부
마크다운 라이브러리(+sanitizer) 의존과 XSS 표면을 만들지 않는다(`{@html}` 금지, 텍스트 노드 렌더). (2) 미리보기는
`stripMarkdown`으로 기호를 제거한 한 줄. (3) `rule` 표기는 사용자 언어("규칙 기반 답변")로 — P1에서 답변 출처
투명성은 유지하되 내부 코드를 노출하지 않는다. (4) Coach 답변의 근거 칩(P1)은 별도 설계가 필요한 후속 항목이다(이 유닛 범위 아님).

---

## [P7-IMPL-TODAY-HERO] Today L0 — 권고를 먼저, 체크인은 접힌 한 줄로

03a 1-A 목업은 L0 맨 위에 QuickInput(피로도 1~10·통증·저장)을 두고 그 아래 RecommendationCard를 둔다(P6 One Finger
Reach). 실화면(390×844) 첫 화면의 45%가 입력 폼이고 권고는 접힌 경계에 걸린다 — 같은 문서가 L0의 의도로 적은
"오늘 무엇을 할까를 30초 안에 답한다"(P4 Intent-Centered)와 충돌한다. 입력은 하루 1회 10초 작업이라 매번 펼쳐 둘
이유가 없다.

**결정**: (1) 순서를 RecommendationCard → QuickInput으로 바꾸고 QuickInput은 `compact`(접힌 한 줄 `오늘 컨디션 입력 →`,
이미 입력했으면 `피로 6 · 통증 없음 ✓`) — P6은 "한 손가락 거리"이지 "항상 펼침"이 아니다: 접힌 한 줄도 탭 한 번이다.
Coach 홈이 이미 같은 compact 패턴을 쓴다(03g 7-5 표 갱신). (2) 피로도 1~10은 두 줄로 접히던 버튼 묶음을 한 줄
눈금(10칸 그리드)으로 — 눈금이 순서를 그대로 보여주고 8+2로 끊기는 어색함이 없다(칸 폭 ≈29px, 높이 44px).
(3) 03a·03g 문서의 L0 순서·배치 표를 함께 고친다.

---

## [P7-IMPL-TREND-CHART] 추세 차트: 축·공통 스케일·스크럽

실데이터 리뷰: 메트릭 상세의 추세 차트는 선 하나뿐(축·값 눈금·포인트 확인 없음)이고 "30일 변화 +742.2%"는 기준값
(4.5)이 작아 무의미한 숫자다. Today의 CTL·ATL은 각자 자기 범위로 스케일돼 ATL이 과장돼 보이고 값을 읽을 수 없다
(합성 데이터에선 값 범위가 비슷해 덜 보였다).

**결정**: (1) 한 컴포넌트(`TrendChart`)가 다계열을 **공통 y 범위**로 겹쳐 그린다 — 서로 다른 스케일을 한 화면에 놓는
거짓 비교를 없앤다(01의 PMC 관례: CTL/ATL 같은 축). (2) y 최대·최소와 x 시작·끝 날짜 눈금, 스크럽 판독(날짜·값)으로
P2의 "데이터 포인트 확인"을 채운다(스트림 스크럽과 같은 Pointer Events 패턴). (3) Today 인라인 차트는 탭이 "이번 달
이야기" 패널 열기이므로 `interactive={false}`. (4) "N일 변화"는 기준값이 작으면(<10) 절대 변화, 아니면 퍼센트 — 순수
함수 `changeLabel`로 테스트.

---

## [P7-IMPL-RACE-HUB-API] Today 목표 레이스 허브 백엔드

REVIEW-05 E1: 앱의 대표 인사이트(예측 기록)가 화면에 없고, 사용자는 D-31 레이스가 있으나 앱이 모른다. 실데이터에서
`race_pred_*_sec`가 있는데 `dashboard_service`는 존재하지 않는 `darp_*_sec`를 읽어 `race_predictions`가 항상 null이었다
(테스트가 같은 잘못된 이름을 시드해 버그를 가림 — 시드도 함께 교정).

**결정**: (1) 목표는 기존 `goals` 테이블/`training.goals` 재사용(등록 흐름은 기존 `POST /coach/plan`). 새 테이블 없음.
(2) 허브는 "가장 가까운 다가오는 활성 목표" 1개만 — 과거·완료 목표는 제외. (3) 예측은 목표 거리에 맞는 버킷의 최신
primary 값 + 90일 이력(추이 스파크용), 격차는 서버가 계산(`gap_sec`, 양수=목표보다 느림). (4) 거리 버킷 허용오차:
5K±1, 10K±1.5, 하프±2, 풀±2.5km — 그 밖 거리는 예측 없이 D-day만.

---

## [P7-IMPL-RACE-HUB-UI] Today 목표 레이스 허브 UI

REVIEW-05 E1: 러너가 앱을 여는 이유는 "레이스까지 내가 어디쯤인가"인데 첫 화면이 문장 하나였다.

**결정**: (1) 허브는 Today L0 최상단(권고 카드 위) — 목표가 있을 때만 D-day가 히어로 수치, 없으면 등록 유도 카드(기존
`/coach/plan/new` 재사용, 새 등록 UI는 만들지 않음). (2) 예측은 단일 값 + 목표 대비 격차 톤(빠름=green, 권=teal, 느림=
amber — red는 경고 의미라 쓰지 않는다). (3) 예측 추이는 `TrendChart`(비인터랙티브)를 재사용하고 y값 포맷만 주입 가능하게
확장(`formatValue`). (4) 예측 범위(±, ADR-007)는 API가 아직 범위를 주지 않아 후속.

---

## [P7-IMPL-ROUTE-MAP] 타일 없는 SVG 경로 지도

REVIEW-05 E2: 실데이터에 GPS가 20만 점 있는데 활동 상세에 지도가 없다(Strava/Garmin 기본기 미달).

**결정**: (1) **타일 지도(MapLibre/OSM) 대신 GPS 폴리라인을 직접 SVG로** 그린다 — 외부 타일 서버 요청은 로컬 퍼스트·소유권
원칙과 충돌하고 오프라인에서 깨진다(사용자 확정 2026-09-24). 배경 지도는 없다. (2) 색은 페이스(파랑→주황) 또는 심박
(청록→빨강) — 값은 5~95퍼센타일로 정규화해 이상치가 색을 지배하지 않게. (3) 등장방형 투영(위도 중앙 cos 보정), 북쪽이 위.
(4) 300점으로 다운샘플(SVG 노드 수 제한). (5) 별도 API 없이 활동 상세 응답의 `streams`를 그대로 사용.

---

## [P7-IMPL-ACTIVITY-SPLITS] km 스플릿·고도 프로필

REVIEW-05 E2: 활동 상세에 구간별 페이스와 고도가 없다(러닝 앱 기본기). 실데이터 Garmin 스트림은 `distance_m`이 null이고
`elapsed_sec`가 인덱스인 경우가 있어(P7-DATA-STREAM-ELAPSED) 저장된 시간·거리를 신뢰할 수 없다.

**결정**: (1) 클라이언트에서 재구성 — 시간은 `streamSeconds`와 같은 규칙(마지막 elapsed<0.9×총시간이면 등간격 재환산), 거리는
`distance_m` 우선, 없으면 속도 적분 후 활동 총 거리에 맞춰 스케일링. 그래서 화면에 "스트림 기반 추정"을 명시(투명성).
(2) 백엔드 API는 만들지 않는다(활동 상세 응답의 `streams`로 충분, 데이터 계층 근본 수정은 P7-DATA-STREAM-ELAPSED가 담당).
(3) 막대: 빠를수록 길게, 최고 구간 green·평균보다 빠름 blue·느림 amber. (4) 고도: 순수 SVG 면적(외부 라이브러리 없음).

---

## [P7-IMPL-ACTIVITY-HERO] 활동 요약 히어로 수치

REVIEW-05 E2/E5: 활동 상세 최상단이 같은 크기의 한 줄 통계라 위계가 없다.

**결정**: 거리를 히어로 수치(5xl mono)로 올리고 시간·평균 페이스·평균 심박을 2단계 크기의 3열 그리드로. 상승 고도는
보조 한 줄. 마크업은 스펙에 고정(위계 규칙을 디자인 토큰 수준으로 통일하는 것은 E5 후속). `Sparkline` 선 굵기 왜곡은
`vector-effect="non-scaling-stroke"`로 해결.

---

## [P7-IMPL-RUN-STORY] 활동 "이 러닝의 이야기" — 근거 있는 한 줄 판정

REVIEW-05 방향 2("보이는 증거"): 활동 상세가 숫자·차트 나열이라 "그래서 이 러닝이 어땠나"에 답하지 않는다. 비전 원칙 3
(맥락 있는 안내는 근거 동반)을 활동 단위로 적용한다.

**결정**: (1) 스플릿에서 전·후반 페이스, 심박 상승, 유산소 디커플링(효율 EF=속도/심박의 전→후반 감소율, 5% 미만이면 안정)을
계산해 헤드라인 한 문장과 근거 칸(fact)으로 보인다. 헤드라인은 규칙 기반(AI 아님)이라 재현 가능하고, 모든 문장은 fact로
검증된다. (2) 임계: 후반이 ±2% 이상 빠르면 네거티브/느리면 페이드/그 안이면 일정. 완전한 1km 구간이 4개 미만이면 표시하지
않는다. (3) 스트림 재구성 기반이라 "구간 차트로 확인" 문구로 한계를 명시. (4) 순수 함수 `runStory.ts`(테스트 6개) + 표시
`RunStory.svelte` — 추후 Coach가 같은 fact를 근거 칩으로 인용할 수 있게 구조화.

---

## [P7-IMPL-RACE-PROJECTION] 레이스 아침 폼(TSB) 예측

REVIEW-05 방향 1(목표 중심): D-day와 예측 기록만으로는 "그래서 준비가 되고 있나"에 답하지 못한다.

**결정**: (1) 현재 CTL/ATL에서 PMC와 같은 EMA(ATL 7일·CTL 42일, α=2/(N+1))로 레이스 전날까지 전방 투영해 "레이스 아침 TSB"를
두 시나리오로 보인다 — 테이퍼 적용(15일 전까지 평소, 14~8일 전 75%→7~4일 전 55%→3~1일 전 35%)과 지금처럼 유지.
(2) 하루 기준 부하는 최근 28일 평균 TRIMP(휴식일 포함, PMC와 같은 부하원) — 가정은 화면에 그대로 문구로 노출(투명성).
(3) 해석 밴드: TSB <-30 과부하, <-10 훈련 부하 높음, <5 중립, ≤25 레이스 최적(TrainingPeaks의 Fresh +5~+25 관례), 그 위 회복 과다. (4) 레이스가 없거나 당일
이전/120일 초과, CTL·ATL 없음이면 None. 서비스 `race_projection_service`(읽기 전용), `race_hub_service`가 `projection`으로 노출.
실데이터 사본 검증: 현재 TSB −28 → 테이퍼 +13(레이스 최적)/유지 −1(중립).

---

## [P7-IMPL-ARCHIVE] Library 홈 "내 러닝 아카이브"

REVIEW-05 방향 3(내 아카이브): 3.9년·518회·4,033km의 데이터가 "최근 5개 활동"으로만 표현됐다(비전 원칙 1 데이터 소유감).

**결정**: (1) Library 홈 최상단에 누적 거리 히어로 + 최근 12개월 월별 거리 + 53주 캘린더 히트맵 + 개인 최고 기록(PB). 소스
동기화 현황은 아래로 내려 유지. (2) 러닝 = `activity_type LIKE '%running%'`(v_canonical_activities로 중복 제거). PB는 Strava best
efforts(1K/1마일/5K/10K/15K/10마일)의 최소 시간 — Strava에만 있는 데이터라 출처를 그대로 둔다(후속: Garmin 랩 기반 보완).
(3) 히트맵 단계: 0 / ≤5 / ≤10 / ≤18 / 초과 km. (4) 서비스 `archive_service` + `GET /api/v1/library/archive`.

---

## [P7-IMPL-LIST-STORY] 활동 목록 주 단위 그룹·경로 썸네일

REVIEW-04/05: 목록 행이 이름+배지뿐이고 3.9년 아카이브를 "스크롤 리스트"로만 보인다. **결정**: 월요일 시작 주 단위 그룹 헤더에 주간 합계(km·횟수·시간)와 최대 주 대비 막대, 행은 거리 히어로+페이스·심박+경로 썸네일(SVG, 타일 없음). 필터는 종목·거리 칩과 검색만(네이티브 date input 제거 — 기간 필터는 후속). 썸네일 좌표는 목록 API가 32점으로 미리 줄여 내려준다(활동당 전체 스트림 전송 방지).

---

## [P7-IMPL-FORM-CHART] 피트니스-폼 시그니처 차트

REVIEW-05 E3. **결정**: CTL/ATL/TSB(PMC)는 러닝 인텔리전스의 대표 시각이지만 Today는 선 2개뿐이었다. 과거 90일 + 레이스 아침까지의 TSB 예측 두 시나리오를 한 화면에 이어 그려 "지금 어디쯤, 레이스 때 어디"를 한 눈에. 예측 구간은 점선·오늘은 세로선. 밴드(+5~+15)는 race_hub `formBand`와 같은 기준.

---

## [P7-IMPL-VISUAL-SYSTEM] 비주얼 시스템

REVIEW-05 E5. **결정**: 모든 상태 수치가 같은 사각 카드라 위계·상태 의미가 안 보인다 → 링 게이지(값 비율·의미 색). 이모지 대신 SVG 아이콘 세트. 데스크톱은 모바일을 늘린 형태였음 → ≥1024에서 Today 2열(허브·브리핑 | 상태·활동·차트).

---

## [P7-REVIEW-DESIGN-VISION] 디자인 에이전트 재검토

E1~E6 구현 후 실데이터 화면 스크린샷을 기준으로 product-architect가 비전 부합·UI/UX를 재검토하고 수정 방안을 수립한다(REVIEW-06).

---

## [P7-IMPL-FORM-CHART] 피트니스·폼 시그니처 차트 (구현 기록)

Today의 CTL/ATL 2선 차트를 **위 패널 CTL·ATL(공통 스케일) + 아래 패널 TSB 면적(0선·레이스 최적 밴드) + 오늘/레이스 세로선 +
레이스 아침까지의 TSB 예측(테이퍼/유지 점선)**으로 교체. 스크럽 판독(과거=CTL/ATL/TSB, 미래=예상 폼). 순수 계산은
`formChart.ts`(테스트 5). 밴드는 TrainingPeaks 관례에 맞춰 TSB +5~+25("Fresh")로 정정 — 초안의 +5~+15는 테이퍼 시나리오를
"회복 과다"로 과잉 판정했다.

---

## [P7-DATA-LOAD-BACKFILL] 부하(TRIMP) 누락 → CTL/TSB 과소 산출 (데이터 정합성 결함 발견·수정)

**발견**: 실데이터(사본)에서 FormChart를 그리다 CTL이 5~8월에 0~4로 붕괴한 것을 확인 — 같은 기간 월 140~180km를 달렸는데도.
원인은 러닝 활동 중 **361일치 활동에 primary TRIMP 메트릭이 없어** PMC가 그날 부하를 0으로 계산한 것(초기 적재/동기화가
`--days 7` 창만 계산). 그 결과 앱이 "TSB −28 매우 높은 피로/CIRS 나쁨"이라고 말했지만 보정 후는 CTL 69.8·ATL 67.2·TSB +2.6·
UTRS 82·CIRS 25 — **앱의 핵심 결론이 틀려 있었다**(P2 투명성·P3 맥락 있는 안내의 신뢰 문제).
추가 결함: `python -m src.metrics.cli recompute*`가 **commit 없이 종료**해 실행해도 아무것도 저장되지 않았다.

**결정/수정**: (1) `engine.backfill_missing_loads()` — avg_hr·duration이 있는데 primary TRIMP가 없는 러닝의 가장 이른 날부터
오늘까지 연속 재계산(CTL이 42일 EMA라 이후 모든 날에 영향). 누락이 없으면 아무것도 하지 않음(멱등). (2) `sync.py`가 메트릭
계산 직후 자동 실행(실패해도 sync 유지). (3) CLI `recompute-missing` 추가 + CLI commit 누락 수정. (4) `data_health_service.
get_load_coverage()` → `/today`의 `data_health`, 누락 3건↑·20%↑면 Today 상단에 "지표가 실제보다 낮게 나올 수 있어요" 안내
(투명성). (5) 사용자 DB는 **수정하지 않았다** — 검증은 사본에서(361일 누락 → 0, 1분 22초). 사용자 DB는 다음 sync 시 자동
보정되거나 `python -m src.metrics.cli recompute-missing`(환경변수 `RUNPULSE_DB`로 DB 지정)로 즉시 보정.

---

## [P7-IMPL-COACH-EVIDENCE-API] Coach 답변 근거·레이스 컨텍스트

REVIEW-05 E6 / 원칙 P1(모든 AI 결론에 근거). Coach 답변에는 근거가 없었고 컨텍스트에 레이스 예측·폼 예측이 없었다.

**결정**: (1) 근거는 Today 브리핑과 같은 소스(`get_today_briefing().evidence`, 앞 5개)를 재사용 — 화면 간 근거 일관성, 새 계산 없음. LLM이
쓴 본문에서 근거를 추출하지 않는다(환각 위험): 근거는 답변 시점의 실제 지표 스냅샷이다. (2) 저장은 `chat_messages.evidence_json`(스키마 v19) — 대화를 다시 열어도 그
시점의 근거가 보이도록. (3) 컨텍스트에 레이스 아침 예상 폼·목표 거리 예측 기록을 주입해 AI가 목표 맥락에서 답하게 한다. (4) 근거 생성 실패는 답변을 막지 않는다.

---

## [P7-IMPL-COACH-EVIDENCE-UI] Coach 근거 칩·입력창 도킹

REVIEW-04 #S2(Coach 근거 없음, 입력창 미도킹) 해소. 근거 칩은 Today와 같은 컴포넌트·드릴 패널을 재사용해 화면 간 언어를 통일한다.

---

## [P7-UI-REVIEW-0927] 실계정 UI 점검 후 계획·매칭·표시 정정 (2026-09-27, 사용자 승인)

실계정 사본으로 UI를 돌려 발견한 결함을 근본 원인 기준으로 고쳤다. 설계 결정:

(같은 날 2차 정정 — 사용자 지시: 아래 1·2·5·6번을 개정하고 7~9번을 추가했다.)

1. **계획은 목표 대회에서 거꾸로 짠다(`periodization.build_schedule`).** 계획 시작 = 대회 주 −(plan_weeks−1)주(남은 기간보다 짧게 고르면 시작이 미래). 마지막 `taper_weeks`(5·10K 1, 하프 2, 풀 3)주는 감량(대회 주 포함, 직전 부하 수준의 75/60/45%), 그 앞은 base 40%·build 35%·peak 25%. 출발점은 계획 시작 직전 4주 주평균·6주 최장 러닝(`planner_schedule.recent_load`), 부하주 간 +10% 이하, 4번째 부하주는 80% 회복주(피크 주 제외), 롱런은 부하주마다 +2km(거리별 최대·주간 거리 비율 상한, 감량 첫 주만 65%). 목표 피크는 Pfitzinger 표(`recommend_weekly_km`)이되 램프 상한이 우선. 대회일 없는 목표는 기존 CTL 규칙. 이전엔 단계를 오늘 기준 한 번만 계산해 전 주차가 같은 단계였다(as_of 로 1차 정정 → 주기화로 근본 정정). taper 는 3:1 회복주보다 우선. 템플릿 기간도 대회일로 줄이고 짧으면 "압축 일정".
   - 남은 한계: 사용자가 휴식 요일을 지정하지 않으면 7일 모두 훈련일로 쪼개져 하루 4~5km 세션이 생긴다(최근 주 러닝 빈도로 기본 휴식일을 정하는 것은 별도 검토). 롱런 상한 비율(풀·하프 0.5)은 개인화 대상.
2. **매칭은 배타·호환·구조 분석.** 다른 계획이 가져간 활동 제외(canonical 정규화), 세션 분류(classifier)가 계획 유형과 어긋나면(이지 계획에 인터벌 활동 등) 다른 세션, 거리 비율 0.5~1.6. planner 도 행마다 `structure_json` 을 만든다(`plan_structure`): 인터벌 = 워밍업+반복(세트 수·반복 거리·목표 페이스±3%·휴식)+쿨다운, 이지·회복·롱 = 연속 러닝(거리·페이스 상한 `max_only`, 목표 페이스 구간 거리 비중 ≥80%), 템플 = 연속 러닝(범위 내 비중 ≥40%). 이행률 = 볼륨 60%+페이스 40%(연속) / 세트·볼륨·목표 적중(인터벌). 볼륨은 맞고 페이스가 어긋나면 `modified`. 완료(completed=1)는 볼륨(거리/시간)과 세트 수가 각각 처방의 75% 이상. 같은 날 외부 계획이 활동을 가져가면 planner 추천안은 `superseded`, 이미 실행한 날은 컨디션 조정 대상이 아니다.
3. (원 3번 유지) **결과 라벨은 거리 이행이 우선.**
4. (원 4번 유지) **이행률은 지난 날만 분모.** 다음 세션은 다음 주까지 본다. 계획 시작 전이면 "시작 전 (N주 뒤)".
5. **마일스톤은 원본을 모두 저장하고 같은 알고리즘 안의 변화만 보여 준다.** `upsert_metric` 이 provider 무관(검토 중 알고리즘·Garmin 참조 포함)으로 1% 넘는 변화를 저장 — 버전이 다르면 `algo_recompute`(A/B 기록, 비표시), 같으면 `metric_recompute`(데이터 변화, 표시). `milestones.provider` 컬럼(스키마 v22). 표시 조회는 algo_recompute 와 shadow·ref provider 를 제외, 예측 4종 갱신은 한 줄로 병합("예측 기록 갱신"), 내러티브 캐시와 무관하게 항상 최신 규칙으로 조회. 옛 행은 v22 가 버전 차이로 분류.
6. **동기화 소스는 config `sync_sources` + 동기화 화면 체크박스.** 없으면 전부. `/sync` 의 "동기화 대상" 카드에서 체크 해제하면 자동·기본 동기화에서 빠지고(기본 동기화 패널에는 "(꺼짐)"), 다시 체크하면 즉시 포함. 기간 동기화·단일 소스 수동 동기화는 영향 없음. Strava(유료 API)·Runalyze 는 꺼 둠. 커버리지는 끈 소스를 끊김 경고 없이 "동기화 안 함"으로, 과거 데이터가 없으면 숨긴다.
7. **개인 최고 기록은 대회 기록(allout)과 구간 기록(Strava)을 함께 본다** — Strava 는 더 이상 동기화하지 않아 구간 기록이 옛 시점에서 멈춰 있었다(10K 45:34 vs 대회 44:10). 대회 거리가 표준 거리 ±1.5% 이내면 거리 비로 환산, 항목마다 출처("대회"/"구간 기록")를 표시, 하프·풀 추가(15K·10마일 제외).
8. **UI**: Today 는 좌·우 독립 열(행 정렬 빈 공간 제거, 모바일은 order 로 L0→L1→L2→다음 세션), 메트릭 브라우저는 핵심 지표(예측 4종·CTL·TSB·UTRS·CIRS) 상단 + 수면·심박 세부·환경 접기, Coach 동일 제목 대화에 날짜 부기·미리보기 2줄, 계획 페이스는 초/km → m:ss(분으로 오인해 "365:00"으로 보이던 결함).
9. **미해결(다음 검토)**: 실 DB 사본에서 `test_integration_realdb` 의 rtti(>200, 최대 351)·marathon_shape(>100, 최대 189) 범위 검사가 2건 실패 — 지표 정의(상한)와 계산 확인 필요. 이번 변경과 무관(변경 전에도 동일).

(1차 정정 기록 — 위 개정으로 대체된 항목 포함)

1-old. **계획 단계는 그 주 기준으로 계산한다.** `weeks_to_race(as_of=week_start)` — 이전엔 오늘 기준 한 번만 계산돼 16주 계획이 전 주차 같은 단계로 생성됐다. 계획 기간은 대회 주까지로 자르고(`plan_weeks_until_race`, 양 끝 포함), 대회일=`race`, 이후 요일=`rest`. taper 는 3:1 회복주보다 우선(감량 구간에서 회복주가 볼륨·롱런을 되살리던 결함). 템플릿 목록도 `race_date` 로 기간을 줄이고 권장 최소보다 짧으면 "압축 일정".
2. **매칭은 배타·호환 규칙.** 다른 계획(Garmin 저장 워크아웃·Intervals 이벤트 등 명시 연결)이 가져간 활동은 제외(그룹 재편으로 낡은 id 는 canonical 로 정규화), 거리 비율 0.5~1.6 밖이면 다른 세션. `completed=1` 은 거리 이행률 ≥0.75 일 때만 — 미만은 연결·라벨만 남기고 미이행. 같은 날 외부 계획이 활동을 가져가면 planner 추천안은 `superseded`(대체됨).
3. **결과 라벨은 거리 이행이 우선.** 짧게 뛰고 빨랐던 세션이 "초과 달성"이던 순서 결함 수정. 연속 러닝 계획(단일 work 단계)은 세트 비교가 아니라 시간(없으면 거리) 이행률.
4. **이행률은 지난 날만 분모.** 미래 계획을 분모에 넣어 6.3% 로 보이던 값 정정. 다음 세션은 다음 주까지 본다.
5. **예측 카드 기본 표시는 3경로**(Garmin / RunPulse·기기 심박 / RunPulse·자체 추정). r4 섀도 후보는 "검토 중 알고리즘" 접기, 자체 추정 근거·불확실성도 접기. 섀도·참조 provider 의 재계산은 마일스톤을 만들지 않고, 예측 재계산은 표시 시 한 줄로 합쳐 사람 말로 보인다.
6. **동기화 소스는 config `sync_sources`** (없으면 전부). Strava(유료 API)·Runalyze 는 끄고, 끈 소스는 끊김 경고 없이 "동기화 안 함"으로 표시(과거 데이터 없으면 숨김). 수동 단일 소스 동기화는 이 목록과 무관.

기존 데이터 정정 도구: `python3 -m src.training.rematch --db <db> [--replan]` (자동 매칭만 초기화 후 재계산, 수동 완료는 보존; `--replan` 은 다음 주부터 대회 주까지 재생성·대회 이후 삭제). 실 DB 적용은 백업 후 사용자 지시로만.
