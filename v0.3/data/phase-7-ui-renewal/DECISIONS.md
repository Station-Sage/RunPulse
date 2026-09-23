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
