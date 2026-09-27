# UX 리뷰 2026-09 — 99. 종합 (제품 총괄 리뷰)

**작성일**: 2026-09-28 · **대상**: v2(`/v2/*`) 전 영역과 v2 미구현 영역 · 계정 `pansongit@gmail.com` 실데이터
**입력**: `00`·`01`·`02`, 6개 탭 폴더의 `data/ui/ux.md`(요약·채점·최우선 개선)와 `design.md`(요약·상충 판단·구현 순서·수용 기준·추적표, 20 §11 정합 메모)
**성격**: 새 발견은 만들지 않는다. 교차 원인을 묶고, 로드맵을 병합하고, 결정 목록을 취합한다. §5.2 목표 점수와 §8 권장안은 총괄 판단이다.
**표기**: `[10]`=`10-today/`, `[20]`=`20-library-activities/`, `[21]`=`21-library-metrics/`, `[30]`=`30-coach-chat/`, `[31]`=`31-coach-plan/`, `[40]`=`40-v2-unimplemented/`. `10:S0`은 해당 design.md §9의 단계 S0이다.

---

## 1. 한 줄 결론 + 핵심 판단 5개

> **v2에는 경쟁 앱에 없는 재료가 있다(4소스 통합, 계산 공개, 대회 역산 계획). 그러나 지금 v2는 "틀린 숫자를 투명하게 보여 주는" 단계다.** 6개 영역 × 3개 관점의 평균은 **4.0/10**이다. 수치 교정 → 공통 규격 → 탭별 재구성 → 미구현 영역·기본 진입 전환 순서로 가면 약 7.8(목표)에 닿는다.

1. **가장 큰 문제는 화면이 아니라 숫자다.** CTL/ATL EMA 계수가 설계 원문 `1/τ`가 아니라 `2/(N+1)`이다(실효 τ ≈ 21/4일). 그래서 체력·피로가 약 2배 빠르게 움직인다. TRIMP 계수 두 개는 뒤바뀌어 있다. 결정에 쓰는 TSB는 조회 시각마다 바뀐다. Today 권고, 레이스 투영, UTRS·CIRS, Coach 판정, 계획 조정이 모두 이 부하 모델 위에 있다. 정보 정확성 축 평균이 **3.1**로 가장 낮다([10] data F-DATA-01~03, [21] design §7.3 C1).
2. **투명성 약속(P1·P2)이 구조적으로 닫히지 않는다.** 분해 API의 `children/inputs`가 빈 배열이다. 근거 칩 절반은 누를 수 없는 span이다. Coach 칩은 답변이 쓴 입력이 아니라 Today 브리핑을 복사한 것이다. **값 → 분해 → 원천(D1→D3)이 성립하는 메트릭이 하나도 없다.**
3. **판정이 흩어져 탭끼리 모순된다.** 프론트에 등급표가 4벌 있다. Coach는 회복 등급 enum 불일치로 "항상 쉬어라"라고 답한다. 계획 조정기는 화면에 보이는 것과 다른 지표로 판단한다. 이행률 정의는 3개다. `readiness_decision()` 하나와 서버 등급 SSOT로 통합해야 한다.
4. **v2는 혼자서 쓸 수 없다.** ☰가 비활성이고 동기화·소스·설정·내보내기가 없다. "마지막 동기화" 값은 저장소 3곳에서 서로 다르다. 소스 실패는 "쉰 날"로 계산된다. 데이터 관리 과업 13개 중 v2 안에서 완결되는 것이 0개다([40] ux T1~T13).
5. **체감 속도와 "눌러도 반응 없음"은 싸게 고칠 수 있다.** gunicorn 단일 sync 워커가 병렬 API를 직렬로 처리해서, 20ms짜리 API가 화면 안에서는 0.5~1.1s가 된다. 로딩 표시 코드는 0건이다. Today 활동 행은 링크가 아니다. 워커 설정, 진행바, `ActivityRow`만으로 U4·U9 위반 상당수가 닫힌다([02] §1).

---

## 2. 비전 대비 평가

판정: **충족** / **부분**(뼈대는 있으나 핵심이 빠짐) / **위반**(원칙과 반대로 동작하거나 경로가 없음).

### 2.1 북극성·비전 3원칙·REVIEW-05 방향

| 항목 | 판정 | 현재 상태 | 근거 |
|---|---|---|---|
| 북극성: 모아 → 번역 → 더 나은 결정 | **부분** | 모으기는 백엔드에서 동작한다(4소스 병합). 번역은 이야기 카드 수준이다. 결정은 틀린 부하 모델 때문에 **오판 위험**이 있다 | [10](10-today/data.md) F-DATA-01·06, [30](30-coach-chat/data.md) F-DATA-01 |
| ① 데이터 통합·소유권 | **부분**(v2 표면은 위반) | 병합은 되지만 v2에 동기화 시각, 소스 상태, export가 없다. 형제 소스의 존·날씨·Intervals 부하는 상세 화면에서 버려진다 | [40](40-v2-unimplemented/data.md) F-DATA-01~05, [20](20-library-activities/data.md) F-DATA-08 |
| ② 투명한 분석 | **부분** | 공식 버전·분해 시트라는 재료는 있다. 분해는 비었거나 나열이다. 소스 비교는 서로 다른 양을 비교해 거짓 ⚠를 낸다 | [21](21-library-metrics/ux.md) F-UX-03, [20](20-library-activities/data.md) F-DATA-03 |
| ③ 맥락 있는 안내 | **위반** | 권고의 입력은 TSB 하나이고, 오늘 이미 달린 사실을 모른다. Coach는 키워드 템플릿이다(LLM 404를 숨김). 계획 조정은 0 | [10](10-today/ux.md) F-UX-04, [30](30-coach-chat/ux.md) F-UX-01, [31](31-coach-plan/ux.md) F-UX-02 |
| 목표 중심 | **부분** | D-56 허브·3경로 예측은 강점이다. 목표 3:19 현실성 판정이 없고, 계획에 M 페이스 훈련이 0이다 | [10](10-today/data.md) F-DATA-08, [31](31-coach-plan/data.md) F-DATA-02 |
| 보이는 증거 | **부분** | 이야기 카드·칩의 틀은 있다. 증거가 결론과 무관하거나 비어 있다 | [20](20-library-activities/ux.md) F-UX-02 |
| 내 아카이브 | **부분** | 누적·PB·히트맵은 있다. 3.9년치에서 날짜·대회·인터벌을 찾을 경로가 없다 | [20](20-library-activities/ux.md) F-UX-04 |

### 2.2 설계 원칙 P1~P8

| # | 판정 | 현재 상태(대표 증거) | 근거 |
|---|---|---|---|
| P1 Evidence-First | **위반** | Today 칩 7개 중 4개가 가짜(span)다. Coach 칩은 결론과 모순된다(`피로 회복 필요` 옆 `UTRS 75 양호`). 계획 `rationale`은 API에만 있다 | [10](10-today/ux.md) F-UX-03, [30](30-coach-chat/data.md) F-DATA-02, [31](31-coach-plan/data.md) F-DATA-07 |
| P2 Drillable | **위반** | 빈 분해(`children=[]`), 2탭 만에 막다른 곳, D3 링크 0, 차트 포인트에서 분해로 갈 수 없음, 원시 `110.2020…` | [10](10-today/ux.md) F-UX-01, [20](20-library-activities/ux.md) F-UX-02, [21](21-library-metrics/ux.md) F-UX-02 |
| P3 Provider | **부분** | 배지는 있다. 거짓 차이(케이던스 173 vs 87), 매트릭스는 다른 활동(수영 포함)을 한 행에 비교, 사본별 RunPulse 값(RE 302 vs 27.7) | [20](20-library-activities/data.md) F-DATA-03, [21](21-library-metrics/data.md) F-DATA-03·04 |
| P4 Intent IA | **부분** | 3탭 구조는 맞다. ☰가 비활성이고, 탭 간 맥락 전달이 없고, Library 하위에서 서브탭이 사라진다 | [10](10-today/ux.md) F-UX-11, [21](21-library-metrics/ux.md) F-UX-09 |
| P5 Quiet Data | **부분** | 팔레트는 절제되어 있다. 폰트 미로드로 한글이 mono로 나오고, 이모지가 tofu로 깨지고, 대비가 3.07:1이고, 미정의 토큰과 그라데이션이 있다 | [10](10-today/ui.md) F-UI-05·06, [20](20-library-activities/ui.md) F-UI-17 |
| P6 One Finger | **위반** | 컨디션 입력 4탭에 반영 없음, 활동 RPE 0, 세션 메모는 저장만 되고 읽히지 않음 | [10](10-today/ux.md) F-UX-08, [20](20-library-activities/ux.md) F-UX-07, [31](31-coach-plan/ux.md) F-UX-07 |
| P7 State-Bound Plan | **위반** | 수락/원래대로·이동·건너뛰기 0. 표시 지표와 조정 입력이 다르다. 그런데 Today는 "수정은 Coach에서"라고 안내한다 | [31](31-coach-plan/ux.md) F-UX-02, [31](31-coach-plan/data.md) F-DATA-08 |
| P8 Ownership | **위반** | 동기화 값 3종, as-of는 날짜만 비교, export는 v1 URL로만, LLM 전송 고지 없음 | [40](40-v2-unimplemented/data.md) F-DATA-01·05, [30](30-coach-chat/ux.md) F-UX-12 |

### 2.3 U1~U10

| ID | 판정 | 현재 상태 | 근거 |
|---|---|---|---|
| U1 차트 숫자 | **위반(모바일)** | 손을 떼면 값이 사라진다. y 눈금이 없거나 패딩 경계값이다. 스트림 탭 스크럽만 좋다 | [10](10-today/ui.md) F-UI-01, [20](20-library-activities/ui.md) F-UI-03 |
| U2 방향 | **위반** | 예측 추이·페이스 선·메트릭 상세·스파크라인이 "좋아짐 = 아래"다. "피크"가 최악 기록을 가리킨다 | [10](10-today/ui.md) F-UI-02, [20](20-library-activities/ui.md) F-UI-01, [21](21-library-metrics/ux.md) F-UX-01 |
| U3 단위 | **위반** | `13223.0 sec`, 원시 부동소수, 무단위 AU·백분위, 답변 속 영문 코드 | [21](21-library-metrics/ux.md) F-UX-01, [30](30-coach-chat/ux.md) F-UX-10 |
| U4 클릭 반응 | **위반** | Today 활동 행(치명)·예측·마일스톤·가짜 칩, 히트맵, 지도, 스플릿, 웰니스, 계획 HRV, ☰가 무반응. 근력 칩은 항상 0건 | [02](02-performance.md) §4, [20](20-library-activities/ux.md) F-UX-01·03 |
| U5 설명 | **위반** | 52개 중 6개만 해석이 있다. 레지스트리 메타는 UI가 쓰지 않는다 | [21](21-library-metrics/ux.md) F-UX-04 |
| U6 분해 질 | **위반** | 나열 + 내부 ID. 가중치·기여·결론("TSB가 18.5점 깎음")이 없다 | [21](21-library-metrics/ux.md) F-UX-03 |
| U7 혁신성 | **부분** | 재료는 있으나 숨었거나 수치가 틀렸다(§3) | — |
| U8 흐름 | **위반** | 빈 시트, 엉뚱한 세션, 비교 원시 400, Story·웰니스 일자에 URL 없음, ← 고정 | [31](31-coach-plan/ux.md) F-UX-01, [40](40-v2-unimplemented/ux.md) F-UX-05 |
| U9 속도 | **부분** | 가벼운 화면은 0.3~0.5s로 좋다. Today 1.25s·Library 1.7s는 빈 화면이고, 탭 전환은 1.3s 동안 무피드백, 서브탭마다 650KB | [02](02-performance.md) §2·§4 |
| U10 최고 수준 | **미달** | 평균 4.0. 계획은 경쟁 3사 공통 기능 6개 중 0개 | §5, [31](31-coach-plan/ux.md) F-UX-11 |

---

## 3. 혁신성 — 경쟁 앱 대비 signature moment

RunPulse가 이기는 곳은 지표 개수가 아니다. **"이 숫자가 왜 이런지, 어느 기기 값인지, 그래서 무엇을 바꿨는지"를 한 탭 안에** 보여 주는 것이다. 경쟁 앱은 대부분 한 소스 안의 블랙박스 점수를 준다.

| 경쟁 앱 | 그 앱의 최고 순간 | RunPulse 지금 | 설계 후 signature | 설계 |
|---|---|---|---|---|
| **WHOOP** | Recovery + 전일 대비 + 기여 요인 3개, 지표에서 바로 묻는 Coach | 링 3개, 델타 없음, 가중치 없는 분해, 템플릿 Coach | **근거 달린 아침 브리핑**: 권고 1문장 + 개인 기준선 대비 3개 변화 → D2 기여 워터폴("TSB가 −16점"). 공식·가중치·원천 활동까지 공개 | [10](10-today/design.md) §2.4·§C3, [21](21-library-metrics/design.md) C6 |
| **Garmin Connect** | Morning Report, 워치 자동 전송, Training Readiness | Garmin 값을 그대로 표시, 오늘 달린 사실을 모르는 권고, 동기화 표면 없음 | **4소스 교차 판정**("Garmin HRV 정상, Intervals ATL 높음 → 부하 우선") + **통합 동기화 토스트**(`Garmin 원본 + Intervals 부하 합쳐짐 · TSB −15 → −18`) | [30](30-coach-chat/ux.md) F-UX-13, [40](40-v2-unimplemented/design.md) §3.2 |
| **Strava** | 지도·차트 연동 활동 상세(소셜은 비목표) | 이야기 카드는 좋다. 지도 무반응, 페이스 축 반대, 병합 사실은 5번째 탭에 있음 | **`ActivityTimeline` + 지도 스크럽** + 병합 배지 `Garmin ★ · Intervals` + "소스 차이 1건" 칩 | [20](20-library-activities/design.md) §2-4·§2-5 |
| **Runna** | 세션 구조 히어로, 계획 설정 변경, 완료 후 피드백 | 텍스트 목록, 모순 라벨, 편집·조정 0 | **근거 달린 조정 카드**(`내일 4.6km → 3km · TSB −14, 수면 66 · [수락][원래대로]`) + **예측↔계획 궤적**(따르면 3:40 → 3:2x) | [31](31-coach-plan/design.md) §2.4·R8, [30](30-coach-chat/design.md) §7.4 |
| **TrainingPeaks** | PMC, 계획/완료 색 캘린더, 워크아웃 코멘트 | PMC 계수 오류, 계획 색이 결과와 반대 | 교정된 PMC + 대회일 목표 CTL/TSB 궤적(`PlanTimeline`), 7열 주간 그리드 `● ◐ ○ ⟳`, 세션 맥락 Coach 스레드 | [31](31-coach-plan/design.md) §5·S4 |
| **Intervals.icu** | 가장 투명한 계산 공개 | 재료는 있으나 분해가 비어 있고, Intervals CTL 수집이 5/8에 멈춤 | 분해 4블록 + TSB D2의 `Intervals 폼 −6 (척도 다름)` 비교 줄. 결론을 사람 말로 먼저 보여 준다는 점이 다르다 | [10](10-today/design.md) §C3.2 |

**이미 경쟁 앱에 없는 것**(유지·강화): 3경로 레이스 예측, 개인 기온 등가 예측, 레이스 아침 폼 투영, 활동 이야기, Intervals 계획 이벤트 매칭, 소스 커버리지 띠. 모두 **수치 교정 뒤에야** signature가 된다. 지금 전면에 내세우면 역효과가 난다(예: 레이스 아침 TSB +24는 계획을 무시한 균일 부하 투영이다, [10](10-today/data.md) F-DATA-09).

---

## 4. 흐름 — 앱 전체 핵심 과업 여정

모바일 390 기준이다. 동작 = 탭·스크롤 1화면·주소 입력 1회.

| 단계 | 현재 경로·끊김 | 설계 후 경로 | 설계 |
|---|---|---|---|
| ① 아침 확인 | 1.25s 빈 화면 → 스크롤 약 4화면. 권고가 오늘 달린 사실을 모르고, TSB가 시각에 따라 뒤집힌다. 동기화 시각을 믿을 수 없다 | 스켈레톤 → 첫 뷰포트에 히어로 상태 기계(pre/done/rest) + 컨디션 1줄 + 게이지 + 레이스 1줄, 헤더 Pill. **0 동작** | [10](10-today/design.md) §2.3·§2.4 |
| ② 컨디션 입력 | 4탭, 닫기 없음, 권고 무반응. "자동 반영"은 거짓 | `QuickInput` 1탭 저장 → ≤1s 안에 권고 근거에 입력 칩. **1~2탭** | [10](10-today/design.md) §3 B2 |
| ③ 훈련(처방) | "세션 상세"는 내일 세션만. 오늘 행을 누르면 대체된 22.4km 원안이 뜬다. HR존·구조 없음 | 세션 `?w=` 4블록(처방·근거·실제·회고) + 구조 막대. **1탭** | [31](31-coach-plan/design.md) §2.5·S3 |
| ④ 결과 확인 | Today 활동 행 **무반응**. 상세의 스플릿에 정지 시간이 섞이고, RE 과대, 페이스 축 반대 | 히어로 done 상태 → `ActivityRow` → 판정 1문장 + 칩 3 + Timeline. **1탭** | [20](20-library-activities/design.md) §2-5 |
| ⑤ 근거 | 링 → 구성 → TSB → **빈 시트**. 뒤로가기를 누르면 Today를 이탈 | D2 4블록 → 원천 활동. `?drill=` 스택. **2탭으로 D3** | [10](10-today/design.md) §C3 |
| ⑥ 코치 | Today → 빈 홈 → 새 대화 → 재입력 = **4탭 + 재입력**. 활동 상세에서는 경로 0. 답은 "항상 휴식" | 어디서든 `Coach에게 묻기` → `?ctx=` 맥락 카드 + 추천 3 → 칩 1탭 전송 → SSE. **1~2탭** | [30](30-coach-chat/design.md) §2.5·S4·S6 |
| ⑦ 계획 조정 | **불가**. 새 대회 계획은 활성 계획이 있으면 진입 0 | 세션 조정 카드 [적용]/[원래대로], 행 액션 4종 + 되돌리기, 계획 `⋯`. **2탭** | [31](31-coach-plan/design.md) S5·S6 |
| ⑧ 데이터 관리 | **v2 불가**. 주소창 `/sync` → v1 이탈, 복귀 링크 없음. 소스 실패 비가시 | Pill → `지금 동기화` (T2=2), 빨간 행 → `재연결` (T4≤3), ☰ → 기준값(T8=4)·내보내기(T7=3) | [40](40-v2-unimplemented/design.md) §2.2~§2.6 |

**끊김 유형 3가지**: (1) **맥락 소실**: 날짜·활동·지표가 탭을 넘지 못한다. 해법은 `?from=` `?ctx=` `?drill=` `?date=` 쿼리 계약이다. (2) **읽기 전용의 막다름**: 판단 끝에 행동이 없다. 해법은 D2 푸터, 조정 카드, SyncPanel이다. (3) **결과가 돌아오지 않는 쓰기**: 체크인·메모·대회 분류가 판단에 반영되지 않는다. 해법은 저장 → 재판정 → 반영 표시이고, 이것을 수용 기준으로 둔다.

---

## 5. 최고 수준 여부 — 6축 채점

### 5.1 현재 점수 (각 문서 채점 취합, 셀 = `data/ui/ux` → 평균)

40 data의 시각 품질은 "—(해당 없음, 4)"라서 4로 계산했다.

| 탭 | 비전 부합 | 정보 정확성 | 시각 품질 | 반응성 | 흐름 | 혁신성 | **평균** |
|---|---|---|---|---|---|---|---|
| 10 Today | 6/5/6 **5.7** | 3/4/5 **4.0** | 5/4/6 **5.0** | 5/5/4 **4.7** | 4/5/3 **4.0** | 6/5/6 **5.7** | **4.8** |
| 20 Library 활동 | 5/6/5 **5.3** | 3/4/4 **3.7** | 5/5/6 **5.3** | 5/5/5 **5.0** | 4/6/3 **4.3** | 5/5/5 **5.0** | **4.8** |
| 21 Library 메트릭 | 4/4/4 **4.0** | 2/3/3 **2.7** | 5/4/5 **4.7** | 5/5/5 **5.0** | 3/3/2 **2.7** | 4/3/3 **3.3** | **3.7** |
| 30 Coach 대화 | 3/5/3 **3.7** | 1/3/2 **2.0** | 5/4/5 **4.7** | 7/6/5 **6.0** | 3/5/3 **3.7** | 2/4/2 **2.7** | **3.8** |
| 31 Coach 계획 | 4/4/3 **3.7** | 2/4/3 **3.0** | 5/4/5 **4.7** | 6/6/7 **6.3** | 3/3/2 **2.7** | 5/3/3 **3.7** | **4.0** |
| 40 v2 미구현 | 3/2/2 **2.3** | 3/4/3 **3.3** | 4/4/4 **4.0** | 3/3/3 **3.0** | 2/2/1 **1.7** | 4/3/3 **3.3** | **2.9** |
| **축 평균** | **4.1** | **3.1** | **4.7** | **5.0** | **3.2** | **3.9** | **4.0** |

- 최저 축은 **정확성 3.1과 흐름 3.2**다. "안 예쁘다"보다 "틀리고 끊긴다"가 문제다. 반응성이 5.0으로 높은 이유는 SPA 전환이 80~200ms로 빠르기 때문이다.
- 최저 셀은 **Coach 정확성 2.0**(등급 버그로 권고 방향이 고정)과 **미구현 흐름 1.7**(v2 완결 과업 0)이다.
- 기준점: v1 평균은 3/10이었다(00 §7). v2는 "정확한 데이터 목록"에서 "경험의 뼈대는 있으나 숫자가 틀림"으로 옮겨 왔다.

### 5.2 설계 완료 후 목표 점수 (목표, 총괄 판단)

| 탭 | 비전 | 정확성 | 시각 | 반응성 | 흐름 | 혁신성 | 평균 | 받쳐 주는 수용 기준 |
|---|---|---|---|---|---|---|---|---|
| 10 | 8 | 8 | 8 | 8 | 8 | 8 | **8.0** | 06:00·22:00 TSB 동일, 등급 경계 상수 0, 무반응 0, 빈 D2 0, 첫 뷰포트 B1~B4 |
| 20 | 8 | 8 | 8 | 8 | 8 | 8 | **8.0** | 이동시간 스플릿, RE 그룹당 1회, 페이스 반전, `?from=` 복귀 |
| 21 | 8 | 8 | 7 | 8 | 8 | 8 | **7.8** | `formatMetric`, 차트 점 → 분해 → 원천 2탭, 쌍 기반 Provider 비교 |
| 30 | 8 | 8 | 7 | 8 | 8 | 7 | **7.7** | 엔진 4상태 라벨, 근거 = 입력 스냅샷, SSE, 맥락 진입 4곳(LLM 품질은 외부 요인) |
| 31 | 8 | 8 | 7 | 8 | 8 | 8 | **7.8** | 이행 3수치, 세션 4블록, P7 수락/되돌리기. S7(엔진)이 미승인이면 비전·혁신 −1 |
| 40 | 8 | 8 | 7 | 7 | 8 | 7 | **7.5** | G1 T1=0·T2=2·T4≤3, G2 막다른 화면 0, 롤백 1줄 |
| **전체** | 8.0 | 8.0 | 7.3 | 7.8 | 8.0 | 7.7 | **≈7.8** | |

9~10점이 아닌 이유는 세 가지다. 워치 전송·네이티브 앱은 보류되었거나 범위 밖이다. LLM 품질은 외부 요인이다. 팔레트·모션 확정이 "예정"으로 남아 있다([10] design §C7). U10 도달 조건은 §3의 signature 3개(아침 브리핑, 근거 달린 조정, 4소스 통합 요약)가 **매일의 흐름 안에서** 보이는 것이다.

---

## 6. 교차 탭 근본 원인

원인 하나를 고치면 여러 탭의 발견이 함께 닫힌다. §7 Phase 1~2는 이 원인 단위로 짰다.

| # | 근본 원인 | 탭별 증상 | 해법(설계) |
|---|---|---|---|
| RC1 | **부하 모델 오류**: PMC `α=2/(N+1)` + 49일 창 절단, TRIMP 계수 뒤바뀜, 당일 TSB 시각 의존 | 권고 뒤집힘·레이스 투영(10 D-01~03), "이 날 체력 +18.7"(20 D-04), 90일 TSB −70·"42일" 라벨 불일치(21 D-01), Coach TSB −11 vs −3.3(30 D-03), BUG `DATA-CTL-WARMUP` | `pmc_v2`(연속 재귀, `tsb_morning`) + `trimp_v2` **1회 재계산**, ACWR은 EWMA 7/28로 분리. [10](10-today/design.md) §7.2, [21](21-library-metrics/design.md) C1·C1-b·C2·§7.4 |
| RC2 | **판정·등급 분산**: 프론트 등급표 4벌, Coach enum 불일치, `adjuster` 별도 입력 | CIRS 37 "주의"/"보통"(21 X-05), TSB −15 "피로 누적"(21 D-02), "항상 휴식"(30 D-01), HRV 107 "+34% 정상"(31 D-09) | 레지스트리 `bands/status/status_label` SSOT(프론트 경계 0 grep 검사) + **`readiness_decision(date)`** 공용. [10](10-today/design.md) §C7, [31](31-coach-plan/design.md) R8 |
| RC3 | **같은 이름, 다른 값**: 이행률 3정의, activity 계산을 사본마다, 디커플링 2구현, 예측 3값 | 3/7 vs 16.7% vs `✓46%`(10 D-05, 31 D-01·05), RE 302/27.7(20 D-03, 21 D-04), 비교 예측 15분 낙관(40 D-09) | 유효 계획 R1~R5 + `week_compliance`, canonical 그룹당 1회(C3), Friel 단일, R10. [31](31-coach-plan/design.md) §4.1 |
| RC4 | **동기화 원장 분열**: 저장소 3곳, 실패가 `completed, count=0`으로 기록 | as-of 거짓(40 D-01), 결손이 "쉰 날"로(40 D-02), Intervals CTL 정지를 아무도 모름(21 D-12), NEXT `SYNC-ERROR-SURFACE`·`SYNC-SOURCE-TOGGLE` | `sync_jobs` 확장 → `SyncState` 계약 → Pill·`caveats[]`·Data가 이것만 읽는다. [40](40-v2-unimplemented/design.md) S2·S3 |
| RC5 | **분해·설명 계약 부재**: 분해 API 빈 배열, 레지스트리 메타 미사용 | 빈 D2(10 X-01), 값 하나(20 X-02), 나열(21 X-03), 설명 6/52(21 X-04), 예측 근거가 DB에 있는데 비어 있음(21 D-06) | 분해 v2 API(`explain=1`, terms·기여·원천) + explainer 4종 + 메타 확장. [10](10-today/design.md) S2, [21](21-library-metrics/design.md) S1·S3 |
| RC6 | **공통 컴포넌트 부재**: 포맷터·차트 규격·칩 2종·`ActivityRow`·시트·서브탭 없음, 폰트 미로드, 미정의 토큰 | U1·U2·U3·U4 전반, 서브탭 소실(21 X-09), 한글 mono·대비(10 I-05·06) | **§C1~C8** 한 번 구현(§9), `ActivityRow`·`SubTabs`·`ErrorState` |
| RC7 | **로딩 무피드백 + 단일 워커**: 1 sync worker + `--reload`, 전 API await, `$navigating` 0, 650KB 상세, 느린 API 776·413ms | 1.25~1.7s 빈 화면, 1.3s 전환 멈춤, Coach 대기(30 X-04), 비동기 작업 진행 모델 없음(40 X-02) | 워커·스레드(P-1) → §C5 → 스트림 분리·레이아웃 공유 → 캐시 → SSE 작업 진행 공용. [02](02-performance.md) §5 |
| RC8 | **URL 상태·맥락 계약 부재** | 시트 뒤로가기 시 이탈(10 X-06), ← 고정·필터 소실(20 X-05), 기간 히스토리 누적(21 X-10), Coach 맥락(30 X-03), Story·웰니스 URL(40 X-07·08) | `?drill=` shallow routing, `?from/ctx/date/week=`, 보기 상태는 `replaceState`. [10](10-today/design.md) §C3.3 |
| RC9 | **쓰기·행동 경로 부재와 쓰기 결과 미반영**(P6·P7·P8) | RPE 0(20 X-07), 조정 0(31 X-02), ☰ 0(40 X-01), 체크인·메모 미사용(30 X-08, 31 X-07), 대회 분류 조용한 실패(10 X-09) | 피드백 저장소(D3), `plan_adjustments`, ☰ Data, §C5 쓰기 규격(입력 보존 + 토스트 + 되돌리기) |
| RC10 | **정직성 결함**: 문구가 사실과 다름 | "원본 데이터로 이어집니다", "80% 범위"(실제는 포락선), LLM 404 은닉, "자동 반영", "수정은 Coach에서", 오류를 "데이터 없음"으로 | Phase 0 문구 정정 → 4분류 상태([40](40-v2-unimplemented/design.md) §6.1), 엔진 라벨([30](30-coach-chat/design.md) §4.1), `range_kind` |

(D=F-DATA, I=F-UI, X=F-UX)

---

## 7. 통합 우선순위 로드맵

6개 design.md §9의 단계를 하나로 병합했다. 규모 S/M/L은 원문 표기를 따른다. **모든 항목은 착수 전 BACKLOG 등록이 필요하다**(workflow-rules). 현재 루트 BACKLOG NOW는 `[PHASE-7]` 설계 작성 하나뿐이다.

### Phase 0 — 핫픽스·빠른 승리 (결정 불필요)

사용자는 이 앱으로 11/22 마라톤(D-55)을 준비하고 있다. 판단을 틀리게 만드는 것부터 막는다.

| # | 내용 | 설계 | 규모 |
|---|---|---|---|
| 0-1 | Coach 회복 등급 enum·매핑 + 테스트, 틀린 답변 3건에 배너 | [30](30-coach-chat/design.md) 30:S0 | S |
| 0-2 | gunicorn workers 2~4 + threads, 운영에서 `--reload` 제거 | [02](02-performance.md) P-1 | S |
| 0-3 | 사실과 다른 문구 정정("자동 반영", "수정은 Coach에서", 없는 탭, "원본으로 이어집니다") | 30:S0, 31:S5 문구 | S |
| 0-4 | 프론트 포맷·방향 긴급 교정(원시 부동소수, 페이스 방향, 고도 도메인, 부분 구간, 근력 칩) | [20](20-library-activities/design.md) 20:S2 | S |
| 0-5 | Today 활동 행 링크화, IME 가드, 척도 앵커 라벨 | [10](10-today/design.md) §3, 30:S0 | S |

### Phase 1 — 수치 교정 (결정 D1·D2·D5·D10 선행)

| # | 내용 | 설계 | 규모 | 의존 |
|---|---|---|---|---|
| 1-1 | **부하 모델 재기준화**: `pmc_v2`·`trimp_v2`·ACWR 분리, 전 기간 재계산, Intervals CTL 대조, 1회성 변경 알림 | 10:S0, [21](21-library-metrics/design.md) 21:S0 | L | **D1**·D2 |
| 1-2 | **등급 SSOT** + TSB 관례 밴드, 프론트 등급표 제거 | 10:S0, 21:S1 | M | 1-1 |
| 1-3 | 활동 파생 수치(이동시간 스플릿, Friel, RE, TE, PB, 날씨 백필, 형제 병합, VDOT 조건, 소스 비교 quantity) | 20:S1 | L | D11 |
| 1-4 | activity 계산 그룹당 1회 + CalcContext 확장 + 정합성 검사 2종 | 21 §7.3 C3 | M | D10 |
| 1-5 | 이행 재정의 R1~R5·R9·R11, `days[]`·`compliance{}` | [31](31-coach-plan/design.md) 31:S1 | M | — |
| 1-6 | 동기화 작업 원장, `GET /data/sync-state` | [40](40-v2-unimplemented/design.md) 40:S2 | M | D5 |
| 1-7 | GAP 경사·방향(시스템 ADR) | 20:S1b | M | D11 |

### Phase 2 — 공통 규격

| # | 내용 | 설계 | 규모 | 의존 |
|---|---|---|---|---|
| 2-1 | §C4 포맷·§C8 폰트/토큰/아이콘/Stylelint·§C2 칩·§C6 배지·§C5 진행바/스켈레톤 + §C 정합 충돌 해소(D1a~D1e) | 10:S1, 21:S1, 20 §11 | M | 1-2 |
| 2-2 | 셸 기반: `lang`, safe-area, `SubTabs`, `ErrorState`·`+error.svelte`, Toast, ☰ 과도기 드로어, v1↔v2 상호 링크 | 40:S0, 31:S2 일부 | S | — |
| 2-3 | **전환 스위치 G0**(`ui_default` + 전역값) | 40:S1 | S | D6 |
| 2-4 | `ChartScrub` 코어 + FormChart·TrendChart·Sparkline 이관 | 10:S4, 21:S2 | M | 2-1 |
| 2-5 | **D2**: 분해 v2 API + explainer + `DrillPanel`·URL 스택 | 10:S2, 21:S3(API), 20:S5 | L | 1-1, 2-1 |
| 2-6 | 성능: 핵심 API 1개만 await, 스트림 분리·`[id]/+layout`, 느린 API 캐시, SWR | [02](02-performance.md) P-2~P-5, 20:S3 | M | 2-1 |

### Phase 3 — 탭별 재구성 (트랙 A 판단 루프 · B Library · C 계획)

| # | 트랙 | 내용 | 설계 | 규모 | 의존 |
|---|---|---|---|---|---|
| 3-1 | A | Today IA + **`readiness_decision()` 공용화**, 이번 주 스트립 | 10:S3 | L | 2-1, 2-5, 1-5 |
| 3-2 | A | Coach 엔진 투명성·P8(404 원인 확인 포함) | 30:S1 | M | 0-1, D8 |
| 3-3 | A | Coach 근거 v2(입력 스냅샷, 당시 → 현재) | 30:S2 | M | 2-5 |
| 3-4 | A | Coach 판정 단일화·`chip_id` 핸들러·체크인 연결 | 30:S3 | M | 3-1 |
| 3-5 | A | Coach SSE·오류 상태 기계 → 셸·스레드 관리 | 30:S4·S5 | L+M | 3-2 |
| 3-6 | B | 활동 요약 재구성(`ActivityTimeline`·판정 칩) → 지표·소스·랩·스트림 탭 | 20:S4·S6 | L+M | 1-3, 2-4, 2-5 |
| 3-7 | B | 메트릭 상세 8/4·`?date=`·"이 지표는", Library `+layout`·검색·URL 필터 | 21:S3(화면)·S4 | M | 2-5 |
| 3-8 | B | Provider 비교 쌍 기반 재구축 | 21:S6 | M | 1-4 |
| 3-9 | B | 목록·탐색·`ActivityRow` 공용화 → Library 홈 | 20:S8·S9 | L+M | 1-3 |
| 3-10 | B | 활동 행동 출구(RPE·코치에게 묻기·`⋯`) | 20:S7 | M | D3, 3-12 |
| 3-11 | C | 계획 상세 표현 → 세션 4블록(`?w=`) → `PlanTimeline` | 31:S2·S3·S4 | M×3 | 1-5 |
| 3-12 | A·C | **맥락 진입** `/coach/new?ctx=` + 진입점 4곳, Library 딥링크 | 30:S6, 10:S6 | M | 3-5 |
| 3-13 | C | **P7 조정·편집**(`plan_adjustments`, `AdjustmentCard`, 행 액션) | 31:S5 | L | 3-1, 3-11, D9 |
| 3-14 | A·C | Coach 답변 안 조정 카드 | 30:S7 | M | 3-13 |
| 3-15 | C | 계획 생성·생애주기(마법사, 시나리오 비교, `⋯`) | 31:S6 | L | 3-11 |
| 3-16 | C | 처방 엔진 보정 R6·R7 **(판단 필요)** | 31:S7 | L | **D4**, 3-15 |
| 3-17 | A | 레이스 허브 `/v2/today/race` | 10:S5 | L | 2-4, 2-5 |
| 3-18 | A·B | UTRS v2·CIRS v2, 기준선 델타, 웰니스 `/:date` | 10:S7, 21:S5 | M+M | 1-1, D7 |

### Phase 4 — 미구현 영역·기본 진입 전환

| # | 내용 | 설계 | 규모 | 게이트 |
|---|---|---|---|---|
| 4-1 | 동기화 표면(Pill·SyncPanel·SSE·안내 3곳·`caveats`) | 40:S3 | M | G1 |
| 4-2 | `/data`·`/data/sync`·`/data/sources/:p` | 40:S4 | M | G1 |
| 4-3 | 빈·오류 4분류, `load` 예외 삼키기 제거, `/welcome` | 40:S5 | M | G2 |
| 4-4 | 기준값 3열 + 재계산 전후 요약 | 40:S8 | M | G2 권장 |
| 4-5 | 계획 흐름 게이트(31 S2·S5·S6, v1 `/training` 7흐름 대응) | 40 §9.1 | — | G3 |
| 4-6 | 웰니스 일자 → Story 월 | 40:S6·S7 | S+M | G4 |
| 4-7 | 내보내기·가져오기, AI 설정·전송 고지 | 40:S9·S10 | L+S | G5 권장 |
| 4-8 | **G5 기본 전환**(2주, 복귀율 <10%) → **G6 v1 제거**(§11 계승 P0·P1 완료) | 40 §9.1·§11 | — | G5·G6 |
| 4-9 | Story 주·블록 | 40:S11 | M | — |

**순서 원칙**
- 1-1이 끝나기 전에는 1-2의 관례 밴드와 3-18을 배포하지 않는다. τ가 틀린 TSB에 관례 밴드를 입히면 판정이 더 틀어진다([21] §9).
- 2-2·2-3(상호 링크, 롤백 스위치)은 작고 안전하다. 전환보다 훨씬 앞에 둔다.
- 4-1은 1-6 직후 병행할 수 있다. 1인 개발 기준으로는 트랙 A 다음이 적절하다. 데이터를 믿을 수 있어야 Today가 의미를 갖는다.
- 합계는 대략 L 16 · M 30 · S 10이다. 한 릴리스에 L은 2개 이내를 권장한다(20 design의 R1~R4 묶음 참고).

---

## 8. 사용자 결정 필요 목록

권장안은 총괄 리뷰어 의견이다.

### 8.1 최상위 결정 — PMC α (10과 20 설계가 서로 다르다)

**현황**: 10 design §1과 §7.2는 원문 `1/τ`를 기본으로 두고, DECISIONS에서 확정해야 한다고 적었다. 20 design §7-2 ⑧은 `1−e^(−1/τ)`를 적었다. 21 design C1은 `1/42, 1/7`을 적었다. 20 §11 정합 메모 4번은 이 결정을 S1b ADR 하나로 모으자고 한다.

| τ | `1/τ` | `1−e^(−1/τ)` | 차이 |
|---|---|---|---|
| 42(CTL) | 0.02381 | 0.02353 | 1.2% |
| 7(ATL) | 0.14286 | 0.13312 | 7.3% |
| 현행 `2/(N+1)` | 0.0465 / 0.25 | — | 실효 τ ≈ 21 / 4일 |

**권장: `1/τ`를 채택하고 20 design §7-2 ⑧을 여기에 맞춰 고친다.** 이유는 네 가지다.
1. 설계 원문(`v0.2/.ai/metrics.md:176`, `CTL(n)=CTL(n−1)+(TRIMP−CTL(n−1))/42`)과 일치한다.
2. 10 §8 수용 기준의 고정 테스트("부하 0일 CTL 감소 = CTL/42")와 21 C1 재현표가 이미 `1/τ`를 전제로 한다.
3. 두 식의 차이는 CTL에서 1.2%, ATL에서 7.3%다. 핵심은 현행 `2/(N+1)`(오차 약 2배)을 버리는 것이지 두 후보 사이의 선택이 아니다.
4. 활동 화면은 "이 세션 부하 기여"만 표시하므로 어느 쪽을 택해도 UI 규격은 바뀌지 않는다(20 §11).

**검증 조건**: 재계산 후 Intervals CTL과 병행 비교(21 §7.4)에서 ATL 편차가 체계적으로 크면 `1−e^(−1/τ)`로 바꾸는 것을 ADR에 재검토 조건으로 남긴다. 연속 재귀, 전 이력 재계산, `tsb_morning` 분리, BUG `DATA-CTL-WARMUP` 처리를 같은 ADR에 묶는다.

### 8.2 §C 공통 규격 정합 — 남은 충돌 (20 design §11)

| ID | 충돌 | 권장안 | 반영 위치 |
|---|---|---|---|
| **D1a** | **PMC α**(10 `1/τ` vs 20 `1−e^(−1/τ)`) | §8.1대로 `1/τ` | 10 §7.2, 20 §7-2 ⑧, 21 C1 |
| D1b | **차이 색 토큰**: §C7에 `--delta-better/worse`가 없다. 20의 기존 안(파랑/amber)은 `--series-1`·caution과 겹친다 | §C7에 차이 2색을 추가한다. 시리즈색·의미색과 다른 색상대로 정하고 dataviz 팔레트 검증으로 확정한다. 색만으로 구분하지 않고 부호·라벨을 함께 쓴다 | 10 §C7 |
| D1c | **활동 히어로 거리 소수 2자리**(`9.30 km`) vs §C4 `n.n km` | **§C4 예외로 허용**: 활동 상세 히어로와 랩 표만 2자리를 쓴다(기기 앱 관행, 10m 단위 비교 의미 있음). 목록·요약·Today는 1자리 | 10 §C4 |
| D1d | **§C3.3 scope 문법**에 활동 scope가 없다 | 활동 토큰 `@a{id}`(예: `m.trimp@a17414`)를 §C3.3에 추가한다. Today·Coach에서 특정 활동 메트릭을 직접 열 때 필요하다 | 10 §C3.3 |
| D1e | **`★`(대표 소스) 아이콘**이 §C8 목록에 없다 | `Icon.svelte`에 `source-primary`를 추가한다. 와이어프레임의 `⚠ ✕ ▾`는 기존 아이콘으로 대응한다 | 10 §C8 |

### 8.3 착수를 막는 결정 (Phase 1~3 선행)

| ID | 결정 | 권장안 · 이유 | 출처 |
|---|---|---|---|
| **D2** | TRIMP 계수 교정(`0.64·e^(1.92x)`, 성별 프로필) | **교정. D1과 같은 재계산에 넣는다.** 수치 변경을 한 번만 겪게 하고, 1회성 알림 + CTL 상세 변경 마커로 공지한다 | [10](10-today/data.md) F-DATA-02, [21](21-library-metrics/design.md) C1-b |
| **D3** | 활동 피드백 저장소: 안 A `activity_feedback(activity_id PK…)` / 안 B `user_inputs` UNIQUE 변경 | **안 A.** 활동 단위 1:1이고 날짜 단위 체크인과 의미가 다르다. 31 S3 세션 회고(workout 키)와의 연결을 같은 ADR에 적는다 | [20](20-library-activities/design.md) §7-2 ⑦ |
| **D4** | **P7-PLAN-ENGINE**(R6 M 페이스·`long_mp`, R7 휴식일·롱런 상한·테이퍼 2주) | **승인하되 두 단계로.** 엔진 규칙은 과거 대회 전 훈련으로 백테스트한 뒤 새 계획에만 적용한다. 진행 중인 11/22 계획은 재생성하지 않고 목표 간극 표시(31 S4)와 조정 카드(S5)로 보완한다. 레이스 8주 전에 계획 전체를 바꾸는 것은 위험하다 | [31](31-coach-plan/design.md) R6·R7·S7, phase-7 `BACKLOG.md` |
| **D5** | 동기화 원장: `sync_jobs` 확장 / 새 테이블 | **확장.** `job_type·last_error·retry_after`가 이미 있다. 재계산·내보내기도 같은 원장에 넣는다. NEXT `SYNC-ERROR-SURFACE`·`SYNC-SOURCE-TOGGLE`을 흡수한다 | [40](40-v2-unimplemented/design.md) §1, S2 |
| **D6** | 기본 진입 전환: 쿠키 `use_v2`(07 원안) / 계정 `ui_default` + 전역값 | **계정 설정 + 전역값 1줄 롤백 + G0~G6.** 쿠키는 기기마다 다르고 구현도 0건이다 | [40](40-v2-unimplemented/design.md) §9.1 |
| **D7** | UTRS 가중치(BB 30%가 HRV·수면·스트레스와 이중 계산) | **1차는 HRV z-score와 아침 스냅샷만 적용하고 가중치는 유지한다.** 2차로 BB 제외안을 백테스트한 뒤 결정한다. 한 번에 바꾸면 원인을 분리할 수 없다 | [10](10-today/data.md) F-DATA-11, [21](21-library-metrics/design.md) C6 |
| **D8** | 외부 LLM 전송 동의·범위(P8) | **첫 전송 전 동의 + 입력창 위 상시 1줄 고지.** 404가 해결될 때까지 엔진 라벨로 "규칙 답변"임을 명확히 한다 | [30](30-coach-chat/design.md) §4.3 |
| **D9** | 조정 휴식의 이행률 처리 | **분모에서 제외**(설계 채택안). 결정 없이 날이 지나면 원안을 유효 계획으로 둔다 | [31](31-coach-plan/design.md) §1, R8 |
| **D10** | CalcContext `get_group_metric`·`get_group_streams`(ADR-009 확장) | **확장.** raw SQL 금지를 지키면서 그룹을 병합하는 방법이다. 설계 확정은 system-architect. BUG `AUDIT-V-CANONICAL`(판단 필요)도 이 ADR에서 함께 결정한다 | [21](21-library-metrics/design.md) C3 |
| **D11** | 활동 파생 계산 ADR(RE 대체 경로, GAP, VDOT 노력도 조건, dedup 시간대) | **한 묶음 ADR** + `check_data_consistency`에 `_unmapped > 0` 경고 | [20](20-library-activities/design.md) §7-2 ⑧ |

### 8.4 기록만 하면 되는 결정 (설계 채택안 동의 권장)

☰는 좌측, Pill은 우측 · 동기화 지연 기준은 12h 하나(오류는 즉시) · 내보내기는 CSV + 원본 JSON + manifest zip(DB 사본 보류) · D2는 ≥1024px 우측 420px, 모바일 풀스크린 · 예측 헤드라인은 신뢰도 <0.5면 `3:40 (3:26–4:03)` · 계획 비교는 목표 시나리오 3안 · 세션 URL은 `…/session/:date?w=` · 맥락 진입은 `/coach/new?ctx=&from=`, 스레드는 첫 전송 때 생성. (출처: [40] §1, [10] §1, [21] §1, [31] §1, [30] §1)

### 8.5 보류 항목과 재검토 조건

| 항목 | 이유 | 재검토 |
|---|---|---|
| **워치 푸시**(`garmin_push`·`caldav_push`) | 쓰기 경로이고 외부 계정에 부작용이 있다 | 31 S8 이후 사용자 판단. 그 전에는 ICS 구독(읽기)만 노출 |
| `대표 소스 변경` | 병합 규칙 변경은 Data 설계가 필요하다 | 4-2 이후 |
| OSM 지도 타일 | 로컬 퍼스트와 충돌한다 | 설정·전송 고지 틀(D8)과 함께 |
| 구간 PB 스트림 재계산, 심박 보정 VDOT | 검증이 필요하다 | 1-3 이후 별도 백로그 |
| 브라우저 부하 통합 판정 한 줄 | Today 권고 엔진과 공유해야 한다 | 3-1 이후 |
| Garmin Training Readiness 수집, Intervals CTL 수집 복구 | 인제스트 범위다 | 1-6과 함께 sync 과업으로 등록 권장 |
| Coach 마스터-디테일, 활동별 대화 아카이브 | 현재 규모에는 과하다 / 활동 IA와 함께 결정해야 한다 | 스레드 30개 초과 시 / 20 S7 이후 |
| 계획 비교 "지금 계획" 열 | 31 소관 | 31 S6 |

---

## 9. 공통 규격 인덱스

**정의 원본**: [10-today/design.md](10-today/design.md) §C. 다른 탭은 재정의하지 않고 참조하며, 고유 규격은 `§Cn 확장`으로 둔다. 20 design은 §11에서 "통일 예정" 9곳을 §C에 맞췄다.

| 규격 | 핵심 | 탭별 확장 위치 | 남은 충돌 |
|---|---|---|---|
| **C1 ChartScrub** | 모바일 탭 고정(손 떼도 유지), nice ticks, 패딩 경계 라벨 금지, `invert`(빠름 ↑), `interactive={false}` 금지 | 20 §5·§11(`ActivityTimeline` 거리축 1/5km, 3트랙 1 Scrub, `?seg` 지도 연동) · 21 §5(의미 밴드·이벤트 마커, 스파크라인 최소 폭) · 31 §5(`PlanTimeline`, `SessionStructureBar`) · 40 §5(웰니스 small multiples, 커버리지 띠) | — |
| **C2 칩 2종** | `DrillChip`(목적지 필수, 44px) / `InfoTag`, `kind ∈ drill·route·info` | 20 §2-5(판정 칩 3) · 30 §4.4(답변 단위, `supports/caveat`, 스냅샷) · 31 §2.4(조정 근거 칩) | — |
| **C3 D2** | 우측 420px / 모바일 풀스크린, 4블록, `?drill=` 스택, 빈 시트 금지 | 20 §3·§11(scope 생략 = 그 활동, `정밀값` 토글, `same_class_30d`) · 21 §2.3(메트릭 상세는 **인라인 패널** 예외, `?date=`) · 30 §2.3(컨텍스트 패널, 당시 → 현재) | **D1d** 활동 scope `@a{id}` |
| **C4 값 포맷** | `h:mm:ss`, `m:ss/km`, TSB 부호 정수, U+2212, 날짜 `9/27(일)` | 20 §4-1·§11(페이스 차이, 케이던스 양발, 상승고도, 기온, 천 단위, 연도 표기) · 21 §4.1(`formatMetric`) · 30 §4.5(서버 답변도 같은 포맷터) · 40 §4.1(동기화 시각) | **D1c** 히어로 거리 2자리 |
| **C5 로딩·오류** | 진행바 150ms 지연, 스켈레톤 CLS ≤ 0.05, 핵심 API 1개만 await, 쓰기 토스트 + 되돌리기 | 30 §6.2(전송 상태 기계·SSE) · 31 §6(`+error.svelte`) · **40 §6.1 전역 4분류**·§3.2 동기화 상태 기계 | — |
| **C6 출처 배지** | 테두리 + 글자, `RunPulse 계산` + 버전·시각, 기준일 병기, 30일 초과 `오래된 값` | 20 §4-3·§11(병합 배지 `Garmin ★ · Intervals`) · 21 §4.5(예외 출처만) · 30 §4.1(엔진 라벨 4상태) · 40 §4.3(소스 상태 5종) | — |
| **C7 등급·색** | 서버 `status` 5종만, 시리즈색 분리, 상태 기호 `● ◐ ○ ⟳ ◉ ┄` | 20 §11(트랙마다 `--series-1`) · 21 §4.4(밴드 띠) · 31 R5(결과 라벨 5 + 날짜 상태 4, 강도 색) | **D1b** `--delta-better/worse` |
| **C8 타이포·아이콘** | Inter + JetBrains Mono, 최소 12px, 대비 ≥ 4.5, `Icon.svelte`, 이모지 금지, Stylelint | 30 §7.1(`MessageBlock` 15/1.6) · 40 §7.1(아이콘 추가, `lang="ko"`) | **D1e** `★` 아이콘 |
| (계산) PMC | — | 10 §7.2 · 20 §7-2 ⑧ · 21 C1 | **D1a** α (§8.1) |

**§C 밖 공용 컴포넌트·계약**

| 이름 | 정의 | 사용 |
|---|---|---|
| `ActivityRow` | [20](20-library-activities/design.md) §7-1 | Today·계획 매칭·Coach 맥락·히트맵 팝오버 |
| Library 셸(`+layout`·서브탭) | [20](20-library-activities/design.md) §2-1, [21](21-library-metrics/design.md) §2.1 | Library 전체, Story·웰니스 일자 |
| `SubTabs`·`ErrorState`·`EmptyState`·`+error.svelte`·Toast | [40](40-v2-unimplemented/design.md) §7.1·§6.3 | 전 탭 |
| `SyncState`·`SyncStatusPill`·`SyncPanel` | [40](40-v2-unimplemented/design.md) §2.1·§7.3 | 셸, Today as-of·`caveats` |
| `readiness_decision(date)` | [10](10-today/design.md) §7.2, [31](31-coach-plan/design.md) R8 | Today·Coach·계획 조정 |
| `week_compliance` | [10](10-today/design.md) §7.2, [31](31-coach-plan/design.md) R1~R3 | Today 스트립·계획 헤더 |
| `QuickInput` | [10](10-today/design.md) §3 B2 | Today·Coach 홈 |
| `AdjustmentCard` | [31](31-coach-plan/design.md) §7.1, [30](30-coach-chat/design.md) §7.4 | 세션·Coach 답변 |
| 맥락 계약 `?ctx=`/`?from=` | [30](30-coach-chat/design.md) §1·§2.5 | Today·활동·D2·세션 → Coach |

---

## 10. 문서 지도

경로는 이 폴더(`v0.3/data/phase-7-ui-renewal/ux-review-2026-09/`) 기준이다.

| 파일 | 설명 |
|---|---|
| [00-vision-criteria.md](00-vision-criteria.md) | 평가 기준: 북극성, 3원칙, P1~P8, U1~U10, 성능 기준, 심각도, 6축 척도 |
| [01-sitemap.md](01-sitemap.md) | v2·v1 화면 지도, 클릭 실측 요약, 리뷰 분할 |
| [02-performance.md](02-performance.md) | 로딩·API·상호작용 측정, 단일 워커 진단, P-1~P-6 |
| **99-summary.md** | 이 문서 |
| [10-today/data.md](10-today/data.md) | PMC·TRIMP 계수, 시계 의존 TSB, 등급 4벌, 준수율, 예측 범위·목표 현실성 |
| [10-today/ui.md](10-today/ui.md) | 모바일 차트 판독, 예측 방향, 분해 시트, 폰트·대비, 첫 화면 위계 |
| [10-today/ux.md](10-today/ux.md) | 빈 드릴다운, 활동 행 무반응, 가짜 칩, 오늘을 모르는 권고, 로딩 (형식 견본) |
| [10-today/design.md](10-today/design.md) | Hero 상태 기계, D2, S0~S7, **§C 공통 규격 C1~C8** |
| [20-library-activities/data.md](20-library-activities/data.md) | RE 과대, 정지 포함 스플릿, 거짓 소스 차이, GAP·PB·VDOT·날씨 |
| [20-library-activities/ui.md](20-library-activities/ui.md) | 페이스 축, 원시 부동소수, 스플릿·랩·고도·지도 차트 문법 |
| [20-library-activities/ux.md](20-library-activities/ux.md) | 상세로 못 가는 지점, 빈 분해, 근력 0건, 아카이브 탐색, 행동 출구 |
| [20-library-activities/design.md](20-library-activities/design.md) | `ActivityTimeline`, `ActivityRow`, S1~S9, 피드백 저장소, **§11 §C 정합 메모** |
| [21-library-metrics/data.md](21-library-metrics/data.md) | τ 오류, 밴드, Provider 매트릭스·사본별 값, 예측 분해, UTRS HRV |
| [21-library-metrics/ui.md](21-library-metrics/ui.md) | 추세 차트 축·방향, 스파크라인, 배지 오버플로, 웰니스·표 |
| [21-library-metrics/ux.md](21-library-metrics/ux.md) | 원시 초·"피크", D1→D3 불성립, 나열 분해, 설명 6/52 |
| [21-library-metrics/design.md](21-library-metrics/design.md) | `formatMetric`, 인라인 분해, **계산 규칙 C1~C6·재계산 검증**, S0~S7 |
| [30-coach-chat/data.md](30-coach-chat/data.md) | 등급 버그, 칩 ≠ 답변 입력, as-of, LLM 404 은닉 |
| [30-coach-chat/ui.md](30-coach-chat/ui.md) | 칩 → 패널 값 불일치, 모바일 대화 셸, IME, 컨디션 폼 |
| [30-coach-chat/ux.md](30-coach-chat/ux.md) | 템플릿 답변, 막다른 근거, 맥락 진입 불가, 대기·오류, 스레드 관리 |
| [30-coach-chat/design.md](30-coach-chat/design.md) | 엔진 투명성·P8, 근거 스냅샷, SSE, `/coach/new?ctx=`, S0~S7 |
| [31-coach-plan/data.md](31-coach-plan/data.md) | 이행률 16.7% 오류, M 페이스 부재, 주간 구조, 라벨 모순, P7 지표 분리 |
| [31-coach-plan/ui.md](31-coach-plan/ui.md) | 계획 vs 실제 부재·색 반대, 세션 상세, 비교 오류 화면, 주기 시각화 |
| [31-coach-plan/ux.md](31-coach-plan/ux.md) | 엉뚱한 세션, 조정·수정 0, 새 계획 진입 0, 메모 미사용 |
| [31-coach-plan/design.md](31-coach-plan/design.md) | 규칙 R1~R11, `PlanTimeline`·`AdjustmentCard`, 마법사·시나리오, S1~S8 |
| [40-v2-unimplemented/data.md](40-v2-unimplemented/data.md) | 동기화 값 3종, 소스 실패 비가시, export·기준값, §A 계승 기능, §B API 재사용 |
| [40-v2-unimplemented/ui.md](40-v2-unimplemented/ui.md) | ☰ 비활성, 비교 오류, §2 셸·Data·Story·웰니스 일자 와이어프레임 |
| [40-v2-unimplemented/ux.md](40-v2-unimplemented/ux.md) | 데이터 루프 단절, 동기화 상태 기계, 롤백 부재, 오류/빈 혼동, 온보딩, §C 계승 흐름 |
| [40-v2-unimplemented/design.md](40-v2-unimplemented/design.md) | 작업 원장·`SyncState`, ☰ Data, 4분류, `/welcome`, S0~S11, **G0~G6**, **§11 v1 → v2 계승 목록** |
| `screenshots/*-desktop.png` · `*-mobile.png` | 1280 전체 페이지 / 390 @2x. v2 화면·상호작용 상태, `v1-*`는 참고 |
| `raw/*.txt` | 화면 텍스트 덤프 |
| `raw/tour.json`·`tour.mjs` | 링크·버튼·API 타이밍 원자료와 스크립트 |
| `raw/interact-{desktop,mobile}.json`·`interact.mjs`·`chip.mjs` | 클릭 반응 실측. 수용 기준 "무반응 0건" 재측정에 쓴다 |
| `../00-diagnostic-and-direction.md`, `../01-design-principles.md`, `../02-information-architecture.md`, `../03a~03g-*.md` | 비전·원칙·IA·화면 카탈로그(리뷰 기준 원본) |
| `../07-migration-roadmap.md`, `../REVIEW-05-vision-gap.md` | 전환 로드맵(쿠키 원안, D6에서 대체 권장), 방향 3문장 |
| `../DECISIONS.md`, `../BACKLOG.md` | 결정 기록 대상(D1~D11), phase-7 백로그(`P7-PLAN-ENGINE`) |
