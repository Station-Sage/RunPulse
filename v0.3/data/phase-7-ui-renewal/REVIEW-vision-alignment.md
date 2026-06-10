Phase 7 UI Renewal 설계 검토 — 앱 철학 정합성 리뷰

검토 대상: v0.3/data/phase-7-ui-renewal/ 폴더 전체 (00~07 설계서 + BACKLOG.md)
근거 문서: CLAUDE.md, README.md, v0.3/data/architecture.md, v0.3/data/decisions.md(ADR-001~011), v0.3/data/phase-5.md(서비스 레이어 설계), v0.3/data/phase-7(preview).md(Future Vision 전 9장), CHANGELOG.md
검토일: 2026-06-10
검토 관점: "UI 설계 초안이 RunPulse의 앱 철학(비전)에 부합하는가, 그리고 재정의된 데이터 구조 위에서 실제로 구현 가능한가"

아래는 다음 에이전트가 그대로 사용할 수 있도록 정리한 검토 결과입니다. 동일 내용을 v0.3/data/phase-7-ui-renewal/REVIEW-vision-alignment.md로 저장하기를 권장합니다.

0. 검토 방법

판단 기준은 두 축입니다. 하나는 비전 정합성으로, phase-7(preview).md가 정의한 세 원칙(데이터 통합·소유권, 투명한 분석, 맥락 있는 안내)과 "되지 않을 것"(소셜·라이브 트래커·정적 PDF·클라우드 종속), 그리고 4개 진화 축(Intelligence / Insight Depth / Data Expansion / Experience)에 UI 설계가 얼마나 충실한지를 봅니다. 다른 하나는 데이터 구조 정합성으로, 재정의된 데이터 아키텍처(architecture.md, phase-16, ADR-001011)와 UI 설계서의 데이터 레이어 확장안(D1~D5)이 충돌 없이 맞물리는지를 봅니다.

각 설계서를 개별 평가한 뒤, 근거 문서 원문과 교차 검증해 갭과 모순을 추출했습니다.

1. 종합 평가

설계 초안의 전반적 완성도는 높습니다. 진단 문서(00)가 현 UI를 3/10, 데이터 레이어를 8.5/10으로 정량화하고 그 5.5점 갭을 "데이터가 아니라 UI 표현력의 부재"로 정확히 짚은 점이 이 리뉴얼의 출발점을 설득력 있게 만듭니다. 8개 설계 원칙이 비전의 세 원칙에서 직접 파생되고, 7개 핵심 컴포넌트와 7장 KPI까지 추적 가능하게 연결된 거버넌스 구조도 탄탄합니다.

| 평가 축 | 점수 | 근거 |
|---|---|---|
| 비전 계승도 | 9/10 | 세 원칙 → 8 설계원칙 → 컴포넌트 → KPI 추적이 일관 |
| 데이터 구조 정합성 | 6.5/10 | D1·D5에서 기존 자산·ADR과 어긋나는 서술 존재 |
| 설계서 내부 정합성 | 7/10 | 문서 간 단계·스키마 불일치 3건 |
| 구현 준비도 | 8/10 | DDL·API·마이그레이션이 구체적, 단 일부 전제 검증 필요 |

핵심 결론은, 비전 방향은 거의 흠잡을 데 없으나, "재정의된 데이터 구조 위에서 구현 가능한가"를 검증하는 단계에서 몇 가지 사실관계 오류가 발견된다는 것입니다. 이는 설계 방향의 문제가 아니라, 설계서가 기존 데이터 문서(특히 phase-5와 ADR-009)를 정확히 반영하지 못한 데서 오는 정합성 문제입니다.

2. 비전 정합성 — 잘 계승된 부분

먼저 보존해야 할 강점입니다. 진단 문서가 "현 UI는 Strava 활동 리스트 + Garmin 카드 + Intervals 차트를 차용한 외형일 뿐, RunPulse 고유 자산이 일급 시민이 아니다"라고 진단한 것은 비전 8장(차별화 전략)의 문제의식과 정확히 일치합니다. 이에 대한 처방인 5+1 의도 중심 IA(Today/Story/Library/Plan/Coach + Data)는 비전의 페르소나("왜 쉬어야 하는지, 어떤 수치가 근거인지 함께 보고 싶은 사람")를 화면 구조로 잘 번역했습니다.

특히 비전과 강하게 결합된 세 가지가 인상적입니다. 첫째, `` 컴포넌트를 모든 AI 결론에 의무화한 것은 비전 원칙 3(맥락 있는 안내는 항상 근거 동반)과 7장 KPI(답변당 근거 2개 이상, 근거 추적성)를 동시에 충족합니다. 둘째, "Drillable Everything" 원칙은 비전 8장의 결정적 문장 "PMC를 구성하는 모든 활동의 모든 메트릭이 한 번의 클릭으로 도달 가능"을 디자인 의무로 박았습니다. 셋째, 단일 프로세스 배포 + Tauri 미래 옵션으로 "클라우드 종속이 아니다"라는 비전 8장 원칙을 기술 제약으로 지킨 것은 SvelteKit 도입과 로컬 퍼스트 정체성 사이의 긴장을 잘 해소한 결정입니다.

3. 비전 정합성 — 갭과 개선안

방향은 옳지만 비전의 일부 요구가 설계에 충분히 내려오지 않은 지점들입니다.

G1 — 다중 경로 프로그램 비교가 Plan을 3단계(7c)로 미룸. 비전 2.3은 "단일 플랜이 아닌 3~5개 프로그램 병렬 비교 + PlanFitReport"를 RunPulse의 핵심 차별점으로 명시합니다(Qin et al. 2025 연구의 네 반응 클러스터가 근거). 그런데 마이그레이션 로드맵은 이를 가장 마지막 직전 단계로 배치합니다. 비전상 가장 강한 차별점이 사용자에게 가장 늦게 도달하는 구조입니다. 개선안: Plan의 "비교 뷰"는 데이터 의존도가 낮은 정적 비교부터 2단계(7b)에서 골격을 노출하고, ML 개인화(PlanFitReport의 적합도 스코어)만 3단계로 분리하는 단계 쪼개기를 검토.

G2 — 정체성 매트릭스 화면이 설계서에 구체화되지 않음. 진단 문서 4.4와 컴포넌트 카탈로그는 "시맨틱 그룹 13개 × provider 4개 매트릭스"를 RunPulse 정체성의 표현물로 규정하지만, 화면 카탈로그(03)에는 /library/providers의 와이어프레임이 7행 비교 수준으로만 묘사됩니다. 비전 9장("이 앱 하나로 충분한가? Yes")을 시각적으로 증명할 핵심 화면이 가장 얇게 설계되어 있습니다. 개선안: 13×4 매트릭스 전용 화면의 셀 상호작용(클릭 시 provider별 값·is_primary 근거·합성 방식 표시)을 화면 카탈로그에 추가.

G3 — provider 우선순위(is_primary)의 *근거*를 보여주는 UI 부재. 비전 0.2와 architecture P4/ADR-003은 동일 메트릭의 다중 provider 중 하나를 primary로 선택하는 우선순위 규칙을 갖습니다. ``은 값 비교는 하지만 "왜 이 provider가 대표값인가"를 설명하지 않습니다. 이는 투명성 원칙(비전 원칙 2)의 미세 누락입니다. 개선안: ProviderComparison에 우선순위 근거 툴팁/배지 추가.

G4 — 날씨·환경 데이터가 UI에 노출되지 않음. 비전 3.3(환경 영향 분석)과 Insight Depth 축은 FEARP·날씨 보정을 강조하지만, 화면 카탈로그에 weather_cache/날씨 메트릭을 표시하는 화면이 없습니다. architecture에 따르면 날씨는 metric_store(category=weather) 또는 weather_cache에 존재합니다. 개선안: 활동 상세에 환경 컨텍스트 카드 추가.

G5 — 사용자 입력 진입점이 Today에 편중. 비전 5.3과 7장 KPI(입력 도달 60%), 그리고 자체 원칙 P6("한 손가락 거리")는 Today·Coach·Library·Activity 상세 모두에 ``을 요구합니다. 그러나 화면 카탈로그에서 QuickInput은 주로 Today에서만 구체화됩니다. 개선안: 활동 상세·Coach·Library 화면 와이어프레임에도 QuickInput 슬롯 명시.

4. 데이터 구조 정합성 — 핵심 정정 사항 (가장 중요)

여기가 이번 검토의 가장 실질적인 발견입니다. 설계서의 데이터 레이어 확장안(D1~D5)을 재정의된 데이터 문서 원문과 대조한 결과, 설계서가 기존 설계·결정을 부정확하게 서술한 지점이 셋 있습니다. 이를 바로잡지 않으면 다음 에이전트가 잘못된 전제로 구현을 시작합니다.

C1 — D5(서비스 레이어)는 "신설"이 아니라 "기존 미구현 설계의 구현"이다. 진단 문서는 D5를 src/services/ 신설로, BACKLOG의 AUDIT-SERVICE-LAYER 해결책으로 제시합니다. 그러나 phase-5.md(Consumer Migration, 1577줄)에 이미 서비스 레이어 설계가 존재합니다(예: activity_service.get_activity_detail 등). D5는 신규 설계가 아니라 phase-5에서 정의됐으나 미구현 상태인 설계의 구현 + UI용 확장입니다. 이를 "신설"로 표기하면 phase-5 설계와 중복·충돌하는 별도 설계를 다시 만들 위험이 있습니다. 정정: D5 서술을 "phase-5 서비스 레이어 설계의 구현 및 확장"으로 수정하고 phase-5를 명시적 전제 문서로 인용.

C2 — 서비스 레이어의 데이터 접근 패턴 서술이 ADR-009와 어긋난다. 일부 설계 서술은 서비스 함수가 CalcContext API만 쓰는 것처럼 암시하지만, ADR-009는 CalcContext API 한정 사용 규칙을 Calculator(32개)에만 적용합니다(ctx.conn.execute 직접 호출 금지는 calculator 대상). phase-5의 서비스 레이어 예시 코드는 실제로 conn.execute() 기반 raw SQL을 사용합니다. 즉 서비스 레이어와 Calculator는 데이터 접근 정책이 다릅니다. 충돌은 없으나, 설계서가 둘을 혼동하면 구현 단계에서 잘못된 제약을 적용하게 됩니다. 정정: "CalcContext는 Calculator 전용 정책이며, 서비스 레이어는 db_helpers/raw SQL을 사용한다"를 06 문서에 명시.

C3 — D1(메트릭 분해 스키마)이 기존 자산을 무시한다. D1은 합성 메트릭의 json_value에 새 분해 스키마({components:[{label,value,weight,raw}]})를 표준화하려 합니다. 그러나 (a) metric_store에는 이미 json_value와 parent_metric_id 컬럼이 있고, (b) data-layer-extensions(06) 문서 자체는 "JSON 표준화 대신 기존 parent_metric_id를 활성화해 메트릭 트리를 표현"하기로 결정합니다. 즉 진단 문서(00)의 D1 서술(JSON 스키마 표준화)과 06 문서의 D1 결정(parent_metric_id 트리)이 서로 모순됩니다. 추가로 ADR-007(모든 calculator range를 [low,high]로 표준화)과 ConfidenceBuilder 등 기존 자산과의 관계도 정리되지 않았습니다. 정정: D1을 단일 접근(parent_metric_id 트리 또는 json_value 분해 중 하나)으로 통일하고, 00과 06의 서술을 일치시킬 것. 권장은 06의 parent_metric_id 방식(스키마 변경 최소).

추가로 데이터 구조 측면의 경미한 점검 사항으로, athlete_profile_snapshots의 UNIQUE 제약이 snapshot_date 단독이면 하루에 여러 트리거(수동/동기화 후)로 스냅샷을 만들 때 충돌하므로 (snapshot_date, snapshot_trigger) 복합키 검토가 필요하고, parent_metric_id 활성화 시 재처리 경로(recompute_runpulse_metrics())에서 자식 메트릭이 고아 행으로 남지 않도록 정리 로직을 정의해야 하며, D1로 자식 메트릭 행이 늘면 metric_store 예상 행 수(약 55k)가 갱신되어야 합니다.

5. 설계서 내부 정합성 — 문서 간 불일치

I1 — Coach 단계 배치 모순. 진단 문서 4.1은 비전 6장 로드맵을 재검토해 "Coach MVP는 1단계(7a)에 Today·입력과 함께 묶는다"로 수정했고 5.4 마이그레이션 표도 1단계에 Coach MVP를 넣습니다. 이는 잘 정정되었으나, 일부 후속 문서(BACKLOG/요약)에서는 Coach가 마지막(7d)에 가까운 인상을 줍니다. 조치: 07 로드맵과 BACKLOG에서 Coach MVP가 7a임을 일관 표기.

I2 — "Library 먼저" 잔재. 분기점 D 초안의 "Library 먼저 → Today" 순서는 4.1에서 폐기됐는데, 일부 문서에 잔재 표현이 남아 있을 수 있습니다. 조치: 폐기된 순서 서술 제거.

I3 — BACKLOG의 문서 카운트/상태 정합성. BACKLOG의 DONE 항목과 실제 폴더 파일(00~07)의 버전 표기(v0.1/v0.2 혼재)를 한 번 정렬할 필요.

6. 우선순위별 후속 작업 (다음 에이전트용 체크리스트)

P0 — 데이터 구조 사실관계 정정 (구현 전 필수)
- C1: D5를 "phase-5 서비스 레이어 설계의 구현·확장"으로 재서술, phase-5를 전제 문서로 인용.
- C2: CalcContext=Calculator 전용 / 서비스 레이어=db_helpers·raw SQL 명시.
- C3: D1을 단일 방식으로 통일(권장 parent_metric_id), 00·06 서술 일치.

P1 — 비전 정합성 보강
- G1: Plan 비교 뷰 단계 쪼개기(정적 비교 7b, ML 적합도 7c).
- G2: 13×4 정체성 매트릭스 전용 화면 구체화.
- G3: provider 우선순위 근거 UI 추가.

P2 — 데이터 구조 보정
- athlete_profile_snapshots UNIQUE 키 복합화 검토.
- parent_metric_id 재처리 경로 고아 행 정리 로직 정의.
- metric_store 예상 행 수 재산정.

P3 — 비전·화면 누락 채우기
- G4 환경/날씨 카드, G5 QuickInput 전 영역 배치.
- 알림 트리거 규칙, Story 생성 스펙, 온보딩 흐름, 접근성·i18n 토큰, 에러 바운더리 정책.

P4 — 내부 정합성 정리
- I1 Coach 단계, I2 Library 잔재, I3 BACKLOG 카운트 정렬.
