# Coach · 훈련 계획 — 통합 개선 설계

**작성일**: 2026-09-27 · **입력**: `31-coach-plan/data.md`(F-DATA-01~14) · `ui.md`(F-UI-01~11) · `ux.md`(F-UX-01~11) · `00-vision-criteria.md` · `03e-coach.md` 5-B/5-D~5-G · `03g-common-patterns.md` 7-1~7-5
**대상**: `/v2/coach/plan/:id`(계획 상세·주간) · `/v2/coach/plan/:id/session/:date`(세션 상세) · `/v2/coach/plan/new`(새 계획) · `/v2/coach/plan/compare`(계획 비교) · 상태 기반 조정(P7) · Today·Coach 대화와의 연결
**성격**: 설계만 다룬다(코드 수정 없음). 계산 규칙 수정안(§4.1)은 구현자가 그대로 테스트 케이스로 옮길 수 있는 수준으로 적는다.

---

## 1. 요약

**설계 목표**
1. **숫자가 맞아야 한다.** 이행률·결과 라벨·매칭은 "날짜별 유효 계획"을 하나의 모델로 삼아 다시 정의한다. 이 모델로 16.7%, `✓ 46%`, "계획대로 진행" 오표기를 없앤다(§4.1 R1~R5).
2. **계획 → 실행 → 해석 루프를 한 화면 흐름으로 잇는다.** 요일당 1행에 계획과 실제를 함께 보여 주고, 세션 상세는 처방·근거·결과·회고 4블록으로 구성한다. 활동 상세와 Coach 대화로 곧바로 드릴할 수 있게 한다.
3. **P7을 실제로 구현한다.** Today CRS 게이트 하나로 판단하고, 근거 칩 3개와 `[조정 적용]/[원래대로]`를 둔다. 결정한 내용은 이행률 계산에 반영한다.
4. **계획의 시간 구조와 목표 간극을 보여 준다.** 9주 타임라인(단계·계획/실제 km), 목표 MP와 현재 능력 MP의 차이, 대회일 예상 CTL/TSB를 표시한다.
5. **마라톤 처방 규칙을 보정한다**(M 페이스, 롱런 상한, 휴식일, 테이퍼). 이 부분은 BACKLOG `P7-PLAN-ENGINE`에 **(판단 필요)** 태그가 붙어 있으므로, 규칙만 명세하고 착수는 사용자 승인을 받은 뒤 한다(§9 S7).

**범위**: 위 4개 라우트, Today `NextSessionCard`의 계획 링크·문구, Coach 대화에서 계획으로 들어가고 나오는 경로, 관련 백엔드(`plan_service`·`match_select`·`outcome_v2`·`adjuster`·`adaptation_service`·`plan_template_service`·`periodization`/`planner_*`). v1은 범위에서 제외한다.

**상충 판단**
| 쟁점 | 의견 | 채택 | 이유 |
|---|---|---|---|
| 결과 라벨 체계 | data: 계획대로/초과/부족/강도 어긋남/건너뜀 · ux: 완료/초과/부족/**변경**/미이행 · ui: outcome 7배지 | **data 5종 + 날짜 상태 4종(예정·휴식·계획 전·대체)** | "강도 어긋남"은 회복일 과속(금 8.3km, HR 150)을 잡아내는 유일한 라벨이다. ux의 "변경(종류 다름)"은 매칭이 되지 않은 활동이므로 "놓침 + `계획 외 러닝 10.0km`" 하위 줄로 처리하고, 거리는 볼륨 이행에만 넣는다(§4.1 R5) |
| "놓침" 기준 | data: 비율<0.5면 skipped · ui/ux: `미달 46%` | **매칭 활동이 있으면 비율과 상관없이 `부족 NN%`, 매칭 활동이 없을 때만 놓침** | 7km를 뛴 날을 "놓침"으로 표시하면 사실과 다르다. 대신 세션 이행 카운트는 0.75 이상일 때만 올린다 |
| 세션 URL | ui: `session/:date/:workoutId` · ux: `session/:workoutId` · data: `?plan=` | **`/coach/plan/:id/session/:date?w=<workoutId>`** | 이행 단위가 날짜(R1)이고 Today 링크도 날짜를 쓴다. 같은 날 여러 행은 `?w`로 구분하고, `?w`가 없으면 유효 계획으로 해석한다 |
| 주간 레이아웃 | ui: 데스크톱 7열 그리드 · ux: 목록 + 주 이동 | **≥1024px 7열 그리드, 그 미만은 요일 목록**. 공통으로 `‹ N주차 ›` + `?week=` | 데스크톱에서 1,040px 단일 열 문제(F-UI-05)와 모바일 밀도를 함께 해결한다 |
| 비교 화면 축 | ui: 템플릿 비교표 · ux: 보수/균형/공격 · data: 목표 시나리오 | **대회일이 고정되면 "목표 시나리오" 3안(도전·현실·완주), 대회일이 없으면 "기간" 3안.** 레이아웃은 ui 비교표 | 이 러너의 실제 결정은 "3:19로 갈까, 낮출까"다(목표와 현재 차이 30초/km). 강도 성향은 시나리오에 내포된다 |
| 조정 휴식일의 이행 처리 | data: "쉬었다 = 이행"으로 분자에 넣음 | **분모에서 제외** | 휴식을 세션 이행으로 세면 "세션 이행"의 의미가 흐려진다. 러너에게 벌점이 없다는 점은 양쪽이 같다 |
| 편집 범위 | ux: 행 액션·계획 설정·재생성 전부 | **S5에서 조정 수락/되돌리기 + 행 액션 4종, S6에서 계획 설정 재생성** | 정확성(S1)과 표현(S2~S3)이 먼저다. 편집은 조정 기록 테이블(§7.2)을 공유하므로 한 묶음으로 구현한다 |

---

## 2. 정보 구조·배치

### 2.1 계획 상세 — 블록 순서와 근거
1. **PlanHeader**: 계획 이름·주차·D-day·목표. 가장 먼저 "어느 대회까지 몇 주 남았나"에 답한다(P4, REVIEW-05 목표 중심).
2. **GoalGapLine**: `목표 MP 4:43 · 현재 능력 5:13 (차 +30초/km) ›`. 계획 전체의 전제가 현실적인지 판단하는 근거다(F-DATA-02·11).
3. **PlanStatusStrip + AdjustmentCard 슬롯**: 오늘 상태 3칩과 결론. 조정이 있으면 이 자리에 카드가 뜬다(P7, F-UX-09: 페이지 끝에서 상단으로 옮긴다).
4. **ComplianceTriple**: `세션 2/6 · 볼륨 49% · 품질 0/1 ›`. 세 값을 한 줄에 둔다(F-DATA-01).
5. **PlanTimeline**: 9주 계획/실제 km, 단계 띠, 오늘·대회 마커, 대회일 CTL/TSB 예상. 막대를 탭하면 해당 주로 이동한다(F-UI-04, F-UX-06, F-DATA-13).
6. **WeekView**: `‹ 1주차 9/21–27 ›` + 주 합계, 요일당 1행(모바일) 또는 7열(데스크톱).
7. **계획 메뉴 `⋯`**: 계획 설정 / 새 대회 계획 / 이 계획 종료 / 외부 계획 따르기.

### 2.2 데스크톱 1280 — 계획 상세 첫 화면
```
┌ 셸 좌측 내비 ┬──────────────────────────────────────────────────────────────────────────┐
│ Today        │ ‹ 코치   42km 목표 · 2026-11-22 대회                          [⋯ 계획]   │
│ Library      │ 1주차 / 9주 · D-56 · 목표 3:19:00 · 계획 v2 (9/27 재생성)                 │
│ Coach ●      │ 목표 MP 4:43 · 현재 능력 5:13 (+30초/km) · 예측 3:40:23 [Today 예측 ›]   │
│              ├──────────────────────────────────────────────────────────────────────────┤
│              │ 상태 양호  [ACWR 1.12 적정›] [HRV +0.3% 평소›] [TSB −9›]  → 오늘 조정 없음 │
│              ├──────────────────────────────────────────────────────────────────────────┤
│              │ 세션 이행 2/6일 ›   볼륨 34.7 / 57.8km 60% ›   품질 0/1 ›   (9/21 이후)    │
│              ├──────────────────────────────────────────────────────────────────────────┤
│              │ km 80┤          ▢       ▢▢                                                │
│              │    60┤ ▣  ▢  ▢     ▢  ▢▢  ▢                                              │
│              │    40┤ ▣  ▢  ▢  ▢  ▢  ▢▢  ▢  ▢                                            │
│              │    20┤ ▣  ▢  ▢  ▢  ▢  ▢▢  ▢  ▢  ▢🏁                                       │
│              │     0┼─1──2──3──4──5──6───7──8──9                                         │
│              │      [기초  ][강화][회복][정점   ][테이퍼      ]  ▣실제 ▢계획 ·롱런        │
│              │      CTL 73 → 피크 예상 80 → 대회일 TSB +14 ›                             │
│              ├──────────────────────────────────────────────────────────────────────────┤
│              │ ‹ 1주차 9/21–27 ›        계획 57.8km · 실제 34.7km · 기초                 │
│              │ ┌월 9/21┬화 9/22┬수 9/23┬목 9/24┬금 9/25┬토 9/26┬일 9/27(오늘)┐           │
│              │ │●이지  │휴식   │●이지  │●인터벌│●회복  │●장거리│●이지        │           │
│              │ │11.5km │(조정됨)│11.5   │5.7    │6.9    │G 장거리│G 기초체력   │           │
│              │ │놓침   │HRV·BB │놓침   │놓침   │8.3 ▰▰▰│7.1 ▰▱ │9.3 ▰▰▰      │           │
│              │ │       │       │       │+계획외│⚠강도  │▼부족46│✓계획대로    │           │
│              │ │       │       │       │ 10.0km│어긋남 │원:11.5│원:22.4 대체 │           │
│              │ └───────┴───────┴───────┴───────┴───────┴───────┴─────────────┘           │
└──────────────┴──────────────────────────────────────────────────────────────────────────┘
```
(수치는 설계 예시다. `57.8km`은 R1의 유효 계획 합계로, 대체 행을 뺀 뒤 외부 계획 거리를 합한 값이다. 실제 값은 S1 구현 후 API가 결정한다.)

### 2.3 모바일 390 — 계획 상세 첫 화면(스크롤 1화면 ≈ 760px)
```
┌─────────────────────────────┐
│ ‹  42km 목표            ⋯   │ 44px 헤더
│ 1/9주 · D-56 · 목표 3:19:00 │
│ 목표 MP 4:43 · 현재 5:13 ›  │ (차 +30초/km, amber)
├─────────────────────────────┤
│ 상태 양호 → 오늘 조정 없음  │
│ [ACWR 1.12][HRV +0.3%][TSB−9]│ 가로 칩, 각 44px
├─────────────────────────────┤
│ 세션 2/6 · 볼륨 60% · 품질0/1›│
├─────────────────────────────┤
│ ▣▢▢▢▢▢▢▢▢🏁  96px 타임라인   │ 가로 스와이프 없음(9주 한 화면)
│ 기초 강화 회복 정점 테이퍼   │
├─────────────────────────────┤
│ ‹ 1주차 9/21–27 ›  34.7/57.8 │
│ 월 │●이지 11.5km      놓침  │
│ 21 │ Z2 · 저강도 유산소      │
│ 화 │ 휴식 (조정됨·BB 28)     │
│ ...                          │
│ 금 │●회복 6.9 → 8.3km ⚠강도 │
│ 25 │ ▰▰▰▰▰▰▰▰▰▰▰▰ 120%       │
│ 일▎│●이지(Garmin) 9.3km ✓    │ 오늘: teal 좌측 3px
│ 27 │ 원 계획 22.4km 장거리 대체│
└─────────────────────────────┘
│ Today │ Library │ Coach │ 하단 탭
```
- 일요일 15시 이후에는 기본 주를 다음 주로 두고, 상단에 `이번 주 요약 ›` 한 줄을 둔다(F-UX-06).

### 2.4 주요 상태 — 조정 제안(P7)
```
┌ AdjustmentCard (amber 좌측 3px, PlanStatusStrip 자리 대체) ─────────────────────┐
│ ⚠ 오늘 인터벌 → 이지 45분으로 조정 권장                                          │
│ [HRV −12% 평소보다 낮음›] [수면 39›] [ACWR 1.38 주의›]      판단: CRS 주황        │
│ 원래: 인터벌 WU10′ · 1000m×4 @4:13 · CD10′ (≈8.5km)   →   이지 7.5km 5:41–6:21   │
│                                    [원래대로]   [조정 적용]  (각 44px)            │
└───────────────────────────────────────────────────────────────────────────────────┘
적용 후: 행 배지 "조정 적용됨 · 9:12" + 토스트 "이번 주 부하 −14% · [되돌리기]" (8초)
```

### 2.5 세션 상세 — 완료된 날(데스크톱 2열 / 모바일 세로 적층)
```
┌ ‹ 42km 목표   토 9/26 · 1주차 기초      [‹ 금] [일 ›]        ▼ 부족 46%  ┐
│ [실제 장거리(Garmin) | 원 계획 이지 11.5km(대체됨)]   ← 같은 날 2행이면 세그먼트 │
├── 처방 ─────────────────────────┬── 실제 ─────────────────────────────────┤
│ 장거리 15.3km (Garmin 목표시간 1:40)│ 7.09km · 44:12 · 6:14/km  [Garmin]   │
│ 페이스 6:01–6:41/km              │ 평균 HR 141 · Z2 78% ▰▰▰▰▰▰▱▱           │
│ Z2 132–146bpm (LTHR 177 기준 ›)  │ 차이  거리 −8.2km ▼ · 페이스 범위 안    │
│ 근거 [VDOT 44.5 · 9/27 ›] [Seiler 80/20]│ [활동 보기 ›] (44px 행 링크)      │
├── 해석 ───────────────────────────────────────────────────────────────────┤
│ 계획의 46%에서 멈췄어요. 이번 주 롱런이 빠졌으니 다음 주 롱런 24.7km는 그대로  │
│ 두고, 화요일 이지는 줄이지 마세요. [근거: 주간 볼륨 60% ›] [Coach에게 묻기 ›]  │
├── 회고 (QuickInput compact) ─────────────────────────────────────────────┤
│ 느낌 RPE [1][2]…[10]   통증 [없음][있음▾]   메모 ________   [저장] 저장됨 9:12│
└───────────────────────────────────────────────────────────────────────────┘
```
- 예정된 날에는 "실제" 블록 대신 **SessionStructureBar**(WU·반복·회복·CD를 폭 = 시간 비례 막대로)와 `당일 아침 컨디션으로 조정 여부를 판단합니다 · 최근 추세 양호`를 보여 준다. 없는 사실은 단정하지 않는다(F-DATA-08).

### 2.6 새 계획 마법사 · 비교
```
① 목표 ── ② 내 일정 ── ③ 비교·확인          (스테퍼, 현재 teal 점)
① [5K][10K][하프][풀][직접]  세그먼트 44px
  대회일 2026. 11. 22.  → D-56 · 8주
  목표 [3:19:00] = 4:43/km    [예측으로 채우기]
  ┌ 러너 프로필 ─────────────────────────────┐
  │ CTL 73 · 최근 4주 44.9km/주 · 최장 24.2km │
  │ 예측 3:40:23 (3:32–3:47) [Today 예측 ›]    │
  │ 현실 범위 3:32–3:45 · 목표는 범위 밖 ⚠     │
  └───────────────────────────────────────────┘
② 주당 러닝 [3][4][5●][6][7]  (최근 8주 중앙값 5)  롱런 요일 [토][일●]
  주간 최대 시간 [   ]  현재 주간 km [44.9] (자동, 수정 가능)  부상 [없음▾]
③ (데스크톱 3열 표 / 모바일 가로 스냅 카드 + 하단 고정 [이 안으로 만들기])
              도전 3:19        현실 3:32 권장    완주 3:45
  MP          4:43             4:58              5:20
  피크 주      72km             64km             55km
  롱런 최대    28km             26km             24km
  MP 누적      64km             52km             30km
  위험         높음(MP 차 30s)   중간(램프 12%)    낮음
  주별 km      ▁▃▄▃▆▇▅▃▂        ▁▃▄▃▅▆▄▃▂        ▁▂▃▂▄▅▃▂▁
  [주차 샘플 ▾] 1주차·피크주·테이퍼주 펼침
 → 확인 시트: "9주 · 45세션을 만듭니다 · 기존 '42km 목표'(1/9주): [종료하고 교체] [대회 후 시작]"
```

---

## 3. 클릭별 동작 명세

| 요소 | 제스처 | 결과 | 뒤로가기 | URL 상태 |
|---|---|---|---|---|
| 헤더 `‹` | 탭 | Coach 홈(`/coach`) | — | — |
| 헤더 `⋯` | 탭 | 메뉴 시트: 계획 설정 / 새 대회 계획 / 외부 계획 따르기 / 이 계획 종료 | 시트 닫힘 | `?sheet=menu` |
| GoalGapLine `›` | 탭 | 분해 패널(데스크톱 우측, 모바일 풀스크린): 목표 MP, 예측 MP(출처·시각), 주별 처방 MP 수렴 곡선, `[목표 조정 ›]` | 패널 닫힘 | `?panel=goal-gap` |
| `Today 예측 ›` | 탭 | `/today#race` 예측 카드 | 계획으로 복귀 | — |
| 상태 칩(ACWR/HRV/TSB) | 탭 | MetricBreakdown 패널(한국어 제목, 산식, 범위 밴드, 28일 스파크라인) → `원천 ›` Library 메트릭 | 패널 → 계획 | `?panel=acwr` 등 |
| AdjustmentCard `[조정 적용]` | 탭 | POST accept → 행 배지·토스트(되돌리기 8초), 이행률 즉시 재계산 | — | 변화 없음 |
| AdjustmentCard `[원래대로]` | 탭 | POST revert → 카드가 1줄 요약으로 접힘(`원래 계획 유지 · 9:12`) | — | — |
| ComplianceTriple 각 항목 | 탭 | 이행 표 패널: 날짜 / 유효 계획 / 실제(활동 링크) / 라벨 / 점수, 분모 규칙 1줄 | 패널 닫힘 | `?panel=compliance` |
| PlanTimeline 막대 | 탭(모바일) / 클릭 | 해당 주로 WeekView 전환, 막대 `aria-pressed` | 이전 주 상태로(history push) | `?week=N` |
| PlanTimeline 막대 | 호버(데스크톱) / 길게(모바일) | 툴팁 `3주차 강화 · 계획 54.4 / 실제 — · 롱런 27.2km` 고정 | — | — |
| CTL/TSB 줄 `›` | 탭 | 패널: CTL 예상 궤적(계획 수행 가정) vs 현재 | 패널 닫힘 | `?panel=ctl` |
| 주 페이저 `‹ ›` | 탭 / 모바일 가로 스와이프 | 이전/다음 주 | history 한 단계 | `?week=N` |
| 요일 행/셀 | 탭 | 세션 상세(유효 계획) | 계획 상세의 같은 주·스크롤 위치 | `/session/:date` |
| 행 하위 줄 `원 계획 … 대체` | 탭 | 세션 상세의 원 계획 탭 | 동일 | `/session/:date?w=<id>` |
| `계획 외 러닝 10.0km ›` | 탭 | `/library/<activityId>` | 계획 상세 | — |
| 행 `⋯` / 길게 누르기 (S5) | 탭 / 500ms | 행 액션 시트: 다른 날로 옮기기 · 거리 줄이기 −20/−40% · 휴식으로 · 건너뛰기(사유) · Coach에게 묻기 | 시트 닫힘 | `?sheet=row-<id>` |
| 세션 세그먼트 탭 | 탭 | 같은 날 다른 workout | replace(히스토리 누적 안 함) | `?w=<id>` |
| 세션 `‹ 금` / `일 ›` | 탭 / 가로 스와이프 | 이전/다음 날 세션 | replace | `/session/:date` |
| 근거 칩 `VDOT 44.5 ›` | 탭 | 패널: 메트릭 분해 → Library 메트릭 | 패널 닫힘 | `?panel=vdot` |
| 존 칩 `Z2 132–146bpm ›` | 탭 | 패널: 존 체계(LTHR/HRmax, 출처), 5존 bpm 표 | 패널 닫힘 | `?panel=zones` |
| `활동 보기 ›` | 탭 | `/library/<activityId>` | 세션 상세 | — |
| `Coach에게 묻기 ›` | 탭 | 새 스레드 `/coach/<threadId>`: 세션 컨텍스트 첨부 + 질문 칩 3개 | 세션 상세 | `?from=session:<id>` |
| 회고 RPE 칩 | 탭 | 즉시 저장(낙관적), `저장됨 9:12` | — | — |
| 마법사 `다음 →` | 탭 | 다음 단계. 비활성이면 사유 문구를 상시 표시 | 이전 단계(입력값 보존) | `/new?step=2&d=42.195&date=…&t=11940` |
| 비교 카드 `[주차 샘플 ▾]` | 탭 | 1주차·피크주·테이퍼주 요일 목록 펼침 | — | — |
| `[이 안으로 만들기]` | 탭 | 확인 시트(세션 수, 기존 계획 처리) → 생성 후 `/coach/plan/:newId` | 새 계획에서 뒤로 가면 Coach(마법사로 돌아가지 않음, replace) | — |
| `/coach/plan/compare`(파라미터 없음) | 진입 | 307 → `/coach/plan/new` | — | — |
| Today `NextSessionCard` "계획 보기 →" | 탭 | `/coach/plan/:id?week=<그 세션 주>` | Today | — |
| Coach 답변 제안 카드 `[계획에 적용]` | 탭 | 조정과 같은 경로로 저장(source=coach), 카드에 `적용됨 · 계획 보기 ›` | — | — |

---

## 4. 지표 정의·계산 규칙·표기

### 4.1 계산 규칙 수정안 (F-DATA-01·04·05·06·08·09·10·11, F-UX-05)

현재 결함(코드 경로 확인):
- `plan_service._compliance_pct`: `source='planner'`만 세고 `superseded`를 제외하지 않는다. 외부 계획 완료는 빠지고, 계획 생성 이전 날짜도 분모에 들어간다. 그 결과 1/6 = 16.7%가 나온다.
- `match_select.pick_activity`: `0.5 ≤ 실제/계획 ≤ 1.6` 게이트를 쓰는데, 품질 세션의 `distance_km`가 반복 거리 일부(3.2km)라서 처방대로 뛴 약 9km 세션은 비율 2.8로 탈락한다.
- `match_select.is_done`: 계획 거리가 없으면(외부 계획) 항상 True를 반환한다. `classify_outcome`은 속도가 5% 빠르면 유형과 관계없이 `overperformed`로 분류하므로, 회복일 과속이 "초과 달성"이 된다.
- 프론트 `statusOf`는 `completed`면 라벨과 상관없이 초록 ✓를 붙인다.

**R1 날짜별 유효 계획(effective plan)**
- 각 날짜 d에서 해당 계획(goal)의 워크아웃 행 가운데 하나를 유효 계획으로 정한다. 우선순위는 다음 순서다.
  1. 활동이 매칭된 외부 계획(`source ∈ {garmin, intervals}`)
  2. 사용자가 **적용한** 조정 결과(`plan_adjustments.decision='accepted'`, source ∈ crs/user/coach)
  3. 외부 계획(미실행)
  4. planner 원안(`superseded=0`)
- 나머지 행은 `alternatives[]`로 내리고 화면에는 "원 계획 … 대체"로 보여 준다. 분모에는 넣지 않는다.
- 레거시: 조정 기록 테이블이 생기기 전의 `adjusted=true` 행(9/22 등)은 accepted로 간주한다(마이그레이션 1회).

**R2 이행률 분모와 기간**
- `effective_start = max(plan_version.start_date, date(plan_version.created_at))`. 계획을 재생성하면 새 버전이 되고, 이전 날짜는 이전 버전 행으로 보존한다(F-DATA-06).
- 분모 D = { d | effective_start ≤ d < today_local } ∪ { today_local, 단 완료된 경우 } 가운데 유효 계획 유형이 `rest`가 아닌 날. 조정으로 휴식이 된 날은 D에서 뺀다.
- `effective_start` 이전 날짜의 상태는 `계획 전`으로 표시하고 어떤 집계에도 넣지 않는다.

**R3 세 가지 이행 수치(한 숫자로 합치지 않음)**
| 수치 | 정의 | 표시 |
|---|---|---|
| 세션 이행 | \|{d∈D : 유효 계획에 매칭 활동이 있고 volume_ratio ≥ 0.75}\| / \|D\| | `2/6일` (분수 우선, % 병기 안 함) |
| 볼륨 이행 | Σ(기간 내 **모든** 러닝 km, 계획 외 러닝 포함) / Σ(D의 유효 계획 총거리) | `34.7 / 57.8km 60%`. 100%를 넘으면 그대로 표시(`112%`) |
| 품질 이행 | 유효 계획 유형 ∈ {interval, tempo, marathon, long_mp}인 날 중 라벨이 on_target 또는 over인 날 / 그런 날 수 | `0/1` |
- `volume_ratio`는 **시간 기준을 우선**하고, 계획 시간이 없으면 거리 기준을 쓴다. 외부 계획에 목표 시간·거리가 모두 없으면 volume_ratio = None으로 두고, 세션 이행은 "매칭됨"으로만 판정한다(`기준 없음` 회색 표기, % 숨김).
- `prediction_note`(예측 보정)는 품질 이행의 compliance_pct 평균을 쓰되, R1의 유효 계획 기준으로 다시 계산한 결과만 입력한다.
- **검증 픽스처(2026-09-21~27, effective_start = 09-21 가정)**: D = 월·수·목·금·토·일(화 조정 휴식 제외) = 6. 세션 이행 = 금(8.31/6.9, 1.20) + 일(92%) = **2/6**. 토 7.09km(0.46)는 부족이고 이행 카운트에서 빠진다. 품질 = 목 인터벌 1건이고 미이행이므로 **0/1**(화 인터벌은 조정으로 휴식이 되어 제외). 16.7%가 다시 나오면 실패다. effective_start가 실제로 09-27이면 D = {일}이 되고 결과는 `1/1`, 나머지 날짜는 `계획 전`이다.

**R4 매칭 게이트**
- 저장 규칙: 품질 세션의 `distance_km`/`duration_s`는 **WU + 반복 + 회복 조깅 + CD 전체**로 저장한다. 기존 행은 읽을 때 `structure_json`으로 총량을 계산해 덮어쓴다(마이그레이션 없이 S1에서 적용 가능). 3주차 인터벌은 3.2km가 아니라 약 8.5km / 50분이 된다.
- 연속 러닝(`is_continuous`): 유형 호환 + `0.4 ≤ 실제 시간/계획 시간 ≤ 2.0`(시간이 없으면 거리)이고, 조건을 만족하는 후보 중 비율이 가장 가까운 활동을 고른다. 게이트를 넓히는 대신 판정은 라벨(R5)이 맡는다.
- 구조 계획(반복 있음): 거리 비율 게이트를 쓰지 않는다. 유형 호환 후보 중 `outcome_v2.compare`의 compliance가 가장 높은 활동을 고르고, bout를 검출하지 못하면 시간 비율 0.5~2.0으로 폴백한다.
- 같은 날 유형이 호환되지 않거나 게이트 밖이라 매칭되지 않은 러닝은 삭제하지 않는다. `unplanned_runs[]`로 반환해 "계획 외 러닝 10.0km"로 표시하고, 볼륨 이행에 포함한다.
- 심박 존 분포(`_get_hr_zone_dist`)는 고정 근사(Z2 = 140bpm)를 쓰지 않고 **러너 프로필 존 체계**(LTHR 또는 HRmax, 출처 표기)를 사용한다.

**R5 결과 라벨(저장 `outcome_label` = 표시 1:1)**
평가 순서는 위에서 아래이며, 먼저 해당하는 라벨을 적용한다. v = volume_ratio.
| 라벨(표시) | 조건 | 아이콘·색 |
|---|---|---|
| `missed` 놓침 | 매칭 활동 없음 | ✕ · red 테두리 |
| `intensity_off` 강도 어긋남 | easy/recovery/long: 목표 페이스 상한보다 빠른 구간이 거리의 40% 초과 **또는** 평균 HR > 목표 존 상한 + 5bpm. 품질: `target_hit_pct < 60`이면서 느린 쪽 이탈이 과반 | ⚠ · amber, 근거(`평균 HR 150 > Z1 상한 132`) 병기 |
| `under` 부족 | v < 0.85, 또는 구조 계획 compliance < 60 | ▼ `46%` · amber |
| `over` 초과 | v > 1.15, 또는 구조 계획에서 세트를 모두 수행하고 과반이 목표보다 3% 넘게 빠름 | ▲ `+20%` · teal 테두리(경고 아님) |
| `on_target` 계획대로 | 그 외 | ✓ · green(✓는 이 라벨에만 사용) |
- `completed`(DB 플래그)는 R3의 세션 이행 조건(v ≥ 0.75)과 같게 두고, 라벨과는 분리한다. 화면은 `completed`가 아니라 라벨만 읽는다.
- 픽스처 기대값: 금(회복 6.9 → 8.31km 5:17/km HR 150) = **강도 어긋남**(v 1.20이지만 강도 조건이 먼저 적용된다). 토(7.09/15.3 목표) = **부족 46%**. 일(92%) = **계획대로 ✓**(0.85 ≤ v ≤ 1.15. 현행 `overperformed` 92%는 이름과 점수가 반대인 오류). 목 = **놓침** + 계획 외 러닝 10.0km.
- 날짜 상태(라벨이 아닌 것): `예정`(점선) · `휴식` · `계획 전` · `대체 →`(원 계획 하위 줄, 취소선 없이 fg-secondary).

**R6 마라톤 페이스(M)와 목표 간극 — 엔진 규칙, S7 (판단 필요)**
- `MP_goal = goal_time / 42.195`, `MP_now` = Today 레이스 허브 예측 마라톤 페이스(**같은 값, 같은 함수**, 현재 5:13). `gap = MP_now − MP_goal`(초/km).
- 처방 MP(k주차) = `max(MP_goal, MP_now_k − 2.5초 × (k − build 시작 주))`. `MP_now_k`는 매주 최신 예측으로 다시 계산한다. 처방이 예측보다 12초/km 넘게 빠르면 12초로 자른다(과도한 처방 방지).
- 세션 유형 `marathon`(M ±5초, 존 Z3 하단)과 `long_mp`(롱런 후반 N km를 M으로)를 추가한다. 롱런에서 MP가 차지하는 비중은 build 20~30%, peak 40~50%로 한다. 테이퍼 1주차에는 MP 10~13km 1회, 대회 주에는 수요일 MP 3~5km를 넣는다.
- 롱런 기본 페이스 = 처방 MP × 1.10~1.20(현재 능력 기준 5:44–6:15). 기존 E+10~50초는 폐기한다.
- 수용 조건: build 시작부터 테이퍼 1주차까지 매주 MP 구간 8km 이상 세션이 1회 이상 있을 것.

**R7 주간 구조 — S7 (판단 필요)**
- 주당 러닝 일수 기본값 = 최근 8주 주별 러닝 일수의 중앙값(이 러너는 5). 선택하지 않은 요일은 `rest`로 둔다.
- 롱런 상한 = `min(0.35 × 주간 km, 150분 ÷ 롱런 페이스 중앙값, 32km)`. 3:40 러너는 약 25km, 주 65km면 22.7km다.
- 최소 세션 = 6km 또는 35분이다. 이보다 짧은 배분이 나오면 휴식으로 합치고 거리를 다른 이지일에 재분배한다. 볼륨을 늘릴 때는 일수를 먼저 늘리지 않고 이지런 길이(8~12km)를 먼저 늘린다.
- 테이퍼: 풀코스는 기본 2주(0.70/0.50)로 하고 강도를 유지한다(MP·짧은 T). 3주 테이퍼는 전체 기간 16주 이상이고 피크 주 80km 이상일 때만 옵션으로 둔다. 대회 2주 전 주말에는 MP 구간을 포함한 20~24km 롱런을 넣는다.

**R8 상태 판단 단일화(P7)**
- 판단 원천은 **Today CRS 게이트 하나**(`status.readiness.crs`, 입력: ACWR·HRV·BB·TSB·CIRS + 체크인)다. `adjuster._fatigue_level`은 폐기하고, adjuster는 "CRS 레벨 → 세션 다운그레이드" 매핑만 맡는다.
  | CRS | 품질 세션 | 롱런 | 이지 |
  |---|---|---|---|
  | 녹 | 유지 | 유지 | 유지 |
  | 황 | 반복 수 −25% 또는 템포 → 스테디 | −15% | 유지 |
  | 주황 | 이지 같은 시간으로 교체 | −30% | −20% |
  | 적 | 휴식 | 휴식 | 휴식 또는 회복 20분 |
- 판단은 **당일에만** 한다. 미래 날짜에는 조정 상태 `future`를 반환하고 "조정 없음 — 계획대로 진행"이라고 단정하지 않는다.
- 조정은 `proposed`로 생성되고, 사용자 결정(accepted/reverted)이 있어야 R1에 반영된다. 결정이 없는 채로 날이 지나면 원안을 유효 계획으로 둔다.

**R9 HRV·ACWR·CTL 표시값**
- HRV: Today CRS와 같은 서비스 함수, 같은 날짜·provider의 값을 쓴다. `adaptation_service`에서 날짜를 확인하지 않고 최신 행을 가져오는 쿼리는 폐기한다. 판정은 개인 60일 평균 ± 1 SD 밴드로 한다. 밴드 안이면 "평소", 아래로 벗어나면 "낮음", 위로 벗어나면 "평소와 다름(높음)"이다. 위쪽 이탈도 정상으로 보지 않는다. 표시 예: `HRV 80ms · 어젯밤 [Garmin] · 평소 72–88 ›`.
- ACWR: 소수 2자리, `계산 09-27 06:10`. 시트에 "EWMA 7/42 비율 · 참조 구간 0.8–1.3은 rolling 7/28 연구의 근사"를 명시한다.
- 계획 CTL 궤적: 유효 계획 세션의 예상 부하(`시간 × IF² × 100`, 유형별 IF: 회복 0.65, 이지 0.72, 롱 0.75, M 0.84, T 0.88, I 0.95)를 현재 CTL/ATL에서 EWMA 42/7로 적분해 `ctl_peak_projected`, `ctl_race_day`, `tsb_race_day`를 구한다. 0~100 고정 막대는 폐기한다.

**R10 템플릿 위험도·예측 단일화(F-DATA-11)**
- 예측은 Today 레이스 허브 값을 쓴다(3:40:23 + 범위). 템플릿 자체 추정 12351초는 표시하지 않는다.
- 위험도 = 다음 항목 중 최고 등급: MP 간극(<5초 낮음 / 5~15초 중간 / >15초 높음), 주간 램프 최대(>10% 중간, >15% 높음), 롱런 비중(>35% 중간), 기간 < 권장 최소(중간). 달성률 기반의 `ach ≥ 70 → 낮음` 규칙은 폐기한다. 위험도 옆에 근거 문장 1개를 반드시 붙인다.

**R11 날짜**: 모든 "오늘/지난 날" 판정은 `localToday()`(Asia/Seoul)로 한다. 서버는 `date.today()`(컨테이너 TZ 확인 필요) 대신 설정된 사용자 TZ를 쓴다(F-UI-06, F-UX-10).

### 4.2 값 포맷
| 값 | 포맷 | 예 |
|---|---|---|
| 거리 | 소수 1자리 + km, 합계도 1자리 | `8.3km`, `34.7 / 57.8km` |
| 페이스 | `m:ss/km`, 범위는 en-dash | `5:41–6:21/km` |
| 페이스 차 | 부호 + `초/km`, 느림/빠름을 단어로 병기 | `+27초/km 느림` |
| 시간 | 1시간 이상 `h:mm:ss`, 미만 `mm:ss`, 계획 시간은 분 단위 `50분` | `3:19:00`, `44:12` |
| 이행 | 세션은 분수, 볼륨은 정수 %, 행 배지는 정수 % | `2/6일`, `60%`, `▼ 46%` |
| ACWR | 소수 2자리 | `1.12` |
| HRV | 정수 ms + 부호 % 1자리 | `80ms +0.3%` |
| CTL/ATL/TSB | 정수, TSB는 부호 | `CTL 73`, `TSB −9` |
| HR | 정수 bpm, 존은 `Z2 132–146bpm` | |
| 날짜 | 요일 + M/D, 입력은 `yyyy. mm. dd.`(`lang="ko"`) | `토 9/26` |
- 모든 숫자에 `.num`(mono, tabular) 클래스를 쓴다. 포맷은 `format.ts` 한 곳(`formatMetric`, `formatPaceRange`, `formatDuration`)에서만 한다. `compare/+page.svelte`의 `fmtTime` 같은 로컬 포맷 함수는 금지한다.

### 4.3 ⓘ 설명(무엇 / 좋은 범위 / 내 값 / 행동)
| 지표 | 무엇 | 좋은 범위 | 내 값 해석(예) | 행동 |
|---|---|---|---|---|
| 세션 이행 | 계획한 날 중 계획을 75% 이상 수행한 날 | 80% 이상 | 2/6 — 이번 주 롱런·인터벌을 놓침 | 다음 주 롱런은 유지하고 이지 날을 줄여서라도 롱런 우선 |
| 볼륨 이행 | 계획 거리 대비 실제 총거리 | 85~110% | 60% — 부하가 계획보다 낮음 | 램프를 올리지 말고 다음 주를 반복 |
| 품질 이행 | 인터벌·템포·MP 세션의 계획대로 수행 비율 | 75% 이상 | 0/1 | 품질 세션 요일을 옮길지 설정에서 검토 |
| 목표 간극 | 목표 MP − 현재 능력 MP | 10초/km 이하 | +30초 — 8주에 좁히기 어려움 | 현실 시나리오 비교 › |
| ACWR | 최근 7일 부하 ÷ 42일 부하(EWMA) | 0.8–1.3 | 1.12 적정 | 계획대로 |
| HRV | 어젯밤 HRV vs 개인 60일 밴드 | 밴드 안 | 평소 | — |
| 대회일 TSB | 계획대로 수행할 때 대회일 컨디션 여유 | +5 ~ +20 | +14 | 테이퍼 유지 |
- 출처 배지(P3): 외부 계획 행 `[Garmin]`/`[Intervals]`, 실제 활동 provider, HRV provider, RunPulse 합성값(VDOT·CTL·예측)에는 `RunPulse · 계산 시각`.
- 색: 결과 라벨은 R5 표의 의미색(green/amber/red)을 쓰되 **항상 아이콘과 텍스트를 함께** 표시한다. 세션 유형은 시리즈 토큰(회복·이지 slate-blue, 장거리 blue, 템포·M violet, 인터벌 pink, 대회 gold)을 쓰고 의미색과 겹치지 않게 한다. 정의되지 않은 토큰(`text-semantic-yellow`)은 쓰지 않는다.
- 용어: 사용자 화면에서는 "계획"으로 통일한다(플랜·프로그램 폐기). 비교 선택지만 "안"이라고 부른다.

---

## 5. 차트 규격

**PlanTimeline(주별 km 막대)**
- x: 주 1~N(대회 주 마지막, 🏁). y: km, nice ticks(0/20/40/60/80, 최대값 기준 20 단위 올림), 좌측 눈금 11px mono.
- 막대: 계획 = 1px outline, 실제 = 채움(지난 주·현재 주만). 롱런 = 막대 위 점(km 라벨은 툴팁에만). 막대 아래 단계 띠(기초·강화·회복·정점·테이퍼, 저채도 5색, 라벨 11px). 현재 주 = 2px 테두리 + `오늘` 마커.
- 방향: 위 = 볼륨 증가. 좋고 나쁨을 뜻하지 않으므로 의미색을 쓰지 않는다.
- 툴팁: `3주차 · 강화 · 10/5–11 · 계획 54.4km / 실제 — · 롱런 27.2km · 품질 인터벌×2`. 데스크톱은 호버, 모바일은 길게 누르면 고정되고 바깥을 탭하면 해제된다. 짧게 탭하면 주 전환이다.
- 하단 텍스트 줄: `CTL 73 → 피크 예상 80 → 대회일 TSB +14 ›`(R9). 목표 대회가 없으면 이 줄을 생략한다.
- 높이: 모바일 96px(9주가 한 화면에 들어감, 주 14주 초과 시 가로 스크롤 + 현재 주 자동 중앙), 데스크톱 120px.
- 빈 데이터: 실제가 없는 과거 주는 outline만 그리고 툴팁 `실제 기록 없음`. 계획 주가 1개면 차트를 숨기고 텍스트 1줄로 대신한다.

**PlanVsActualBar(행 내 계획 대비 막대)**
- 폭 100% = 유효 계획 volume(시간 우선). 채움 = 실제. 100%를 넘으면 경계선 뒤에 다른 톤으로 이어 그리고 최대 150%까지만 표시한다(초과분은 `+`). 오른쪽에 정수 % 라벨. 높이 4px(목록) / 6px(세션). 계획이 없으면 그리지 않는다.

**SessionStructureBar(세션 구조)**
- 가로 스택: WU / 반복(work) / 회복 / CD. 폭 = 시간 비례, 색 = 강도 시리즈 토큰. 각 블록 아래에 `10′`, `1000m @4:13`. 탭하면 블록 상세 툴팁. 실제가 있으면 아래에 실제 bout 막대(목표 적중 = 채움, 미적중 = 빗금)를 겹친다.

**GoalGap 수렴 곡선(패널)**
- x: 주, y: 페이스(초/km). **빠를수록 위**가 되도록 y축을 반전한다(U2). 선 2개: 처방 MP(계단), 예측 MP(점, 주별 실측). 목표 MP는 수평 점선. 눈금은 `m:ss`.

**ACWR·HRV 스파크라인(패널)**: 28일, 좋은 범위 밴드 음영, 최신 값 점과 값 라벨. 탭하면 날짜별 값 툴팁.

---

## 6. 로딩·빈·오류 상태

| 블록 | 로딩 | 빈 상태 | 오류 |
|---|---|---|---|
| PlanHeader·GoalGap | 텍스트 2줄 스켈레톤(높이 고정 56px) | 목표 없음: `목표 대회가 없어요 · [대회 설정 ›]` | 헤더는 계획 기본 정보만 표시하고 GoalGap 줄 생략 |
| StatusStrip | 칩 3개 자리 스켈레톤 | 웰니스 없음: `오늘 컨디션 데이터 수집 중 — 동기화 후 판단 [동기화 상태 ›]` | `상태 판단 불가 · 다시 시도` 인라인 버튼 |
| ComplianceTriple | 1줄 스켈레톤 | D가 비어 있음(계획 첫날 전): `첫 세션 9/28(월)부터 집계` | 숫자 대신 `—` + ⓘ `계산 실패, 다시 시도` |
| PlanTimeline | 막대 9개 회색 펄스 | — | 차트를 숨기고 `주별 요약을 불러오지 못함 · 다시 시도` |
| WeekView | 7행/7열 스켈레톤(행 높이 고정 → 레이아웃 점프 0) | 해당 주 세션 0: `이 주는 계획이 없어요` | 행 자리에 오류 카드 + 재시도 |
| 세션 상세 | 4블록 스켈레톤 | 계획 없는 날: `이 날은 계획이 없어요` + 그날 활동이 있으면 `계획 외 러닝 ›` | 404: `세션을 찾을 수 없음 · [이 주 계획 보기 ›]` |
| 새 계획 비교 | 3카드 스켈레톤(≤ 800ms 목표) | 옵션 0: `이 조건으로 만들 수 있는 계획이 없어요 — 대회일을 늦추거나 목표를 바꿔 보세요` + 1단계로 | 인라인 오류 + 재시도, 입력값 보존 |
| 활성 계획 없음(`/coach/plan`) | — | 현행 게이트웨이 유지(목표 프리필 `N주 로드맵 만들기`) | — |
- **공용 `routes/+error.svelte`**: 셸 안(헤더·탭 유지), px-4 py-10, 아이콘 + 사람이 읽는 제목 + 한 줄 설명 + 주 버튼(맥락별: 계획 → `새 계획 만들기`, 기본 → `Today로`) + 보조 링크. HTTP 코드는 12px 각주로만 둔다. 모든 v2 라우트에 적용한다(F-UI-03, F-UX-04).
- 쓰기 피드백: 버튼 누름 ≤ 100ms에 pressed 상태 → 낙관적 반영 → 실패하면 원복 + 토스트 `저장 실패 · 다시 시도`.
- 비활성 CTA에는 항상 사유 문구를 붙인다(`거리를 선택하면 진행할 수 있어요`).

---

## 7. 변경 컴포넌트·API

### 7.1 프론트엔드 (`frontend/src`, 파일당 300줄 이하)
| 경로 | 구분 | 내용 |
|---|---|---|
| `routes/+error.svelte` | 신규 | 공용 오류 화면(§6) |
| `routes/coach/plan/[id]/+page.svelte` | 재작성 | 조립만 담당(≤150줄). 블록은 아래 컴포넌트로 분리. `?week`, `?panel`, `?sheet` 상태 |
| `routes/coach/plan/[id]/+page.ts` | 변경 | `?week` 파라미터 전달, weeks 병렬 로드 |
| `routes/coach/plan/[id]/session/[date]/+page.svelte` | 재작성 | 세그먼트(`?w`), 처방·실제·해석·회고 4블록, 전날/다음날 페이저 |
| `routes/coach/plan/new/+page.svelte` | 재작성 | 3단계 마법사(`?step`), 입력값 URL 보존, 템플릿 중복 호출 제거 |
| `routes/coach/plan/compare/+page.ts` | 변경 | 파라미터 없으면 `redirect(307, /coach/plan/new)` |
| `routes/coach/plan/compare/+page.svelte` | 재작성 | ScenarioCompareTable(마법사 3단계에서도 재사용) |
| `lib/components/plan/PlanHeader.svelte` | 신규 | 제목·주차·D-day·버전·`⋯` 메뉴 |
| `lib/components/plan/GoalGapLine.svelte` | 신규 | 목표/현재 MP, 간극, 예측 링크 |
| `lib/components/plan/PlanStatusStrip.svelte` | 신규 | CRS 레벨 + 칩 3개(MetricBreakdown 연결) |
| `lib/components/plan/AdjustmentCard.svelte` | 신규 | 03g 7-4 형식, 근거 칩(EvidenceQuote), 적용/원래대로, 되돌리기 토스트 |
| `lib/components/plan/ComplianceTriple.svelte` | 신규 | 세 수치 + 이행 표 패널 |
| `lib/components/plan/PlanTimeline.svelte` | 신규 | §5, 비교 카드 미니 버전(`compact`) 겸용 |
| `lib/components/plan/WeekGrid.svelte` / `WeekList.svelte` | 신규 | ≥1024 / <1024 |
| `lib/components/plan/PlanDayRow.svelte` | 신규 | 유효 계획 + 실제 + PlanVsActualBar + OutcomeBadge + 대체/계획 외 하위 줄 |
| `lib/components/plan/OutcomeBadge.svelte` | 신규 | R5 라벨 5종 + 날짜 상태 4종 |
| `lib/components/plan/SessionPrescription.svelte`, `SessionActual.svelte`, `SessionStructureBar.svelte` | 신규 | §2.5 |
| `lib/components/plan/PlanWizardStepper.svelte`, `RunnerProfileCard.svelte`, `TimeInput.svelte`, `ScenarioCompareTable.svelte` | 신규 | §2.6. TimeInput: `h:mm:ss` 마스크, `inputmode=numeric`, 붙여넣기 파싱, 환산 페이스 표시 |
| `lib/components/QuickInput.svelte` | 변경 | `mode="session"`(workout_id 키, RPE·통증·메모) 추가, 03g 7-5 "Coach 세션 상세" 배치 |
| `lib/components/MetricBreakdown.svelte` | 변경 | 데스크톱 우측 패널(max-w 420px, 전폭 금지), 한국어 제목, 산식 행 |
| `lib/components/NextSessionCard.svelte` | 변경 | 문구 `계획 수립·수정은 Coach에서 →`를 `이번 주 계획 보기 →`로 바꾸고(S5 전), 완료된 오늘 세션에 `결과 보기 ›` 추가 |
| `lib/format.ts` | 변경 | `localToday()`, `formatMetric('acwr'|'hrv'|'tsb')`, `formatPaceDelta` |
| `lib/api/plan.ts` | 변경 | §7.2 타입·호출 |
| `src/app.html` | 변경 | `lang="ko"` |
| Coach 대화 `routes/coach/[threadId]` | 변경 | 컨텍스트 패널 "진행 중 계획 1/9주 · 세션 2/6", 답변 내 PlanProposalCard |

### 7.2 백엔드 API (`src/api/routes_plan.py` 외)
**GET `/api/v1/coach/plan/:id?week=N`** (확장)
```json
{"goal": {...}, "plan_version": {"v": 2, "created_at": "2026-09-27T10:02", "effective_start": "2026-09-21"},
 "goal_gap": {"mp_goal_s": 283, "mp_now_s": 313, "gap_s": 30, "prediction": {"time_s": 13223, "range_s": [12960, 13620], "source": "race_hub", "computed_at": "..."}},
 "status": {"crs_level": "green", "signals": [{"key":"acwr","value":1.12,"zone":"적정","date":"2026-09-27","computed_at":"..."},
            {"key":"hrv","value":80,"band":[72,88],"zone":"평소","provider":"garmin","date":"2026-09-26"},{"key":"tsb","value":-9}],
            "adjustment": {"state": "none|proposed|accepted|reverted|future", "id": 12, "before": {...}, "after": {...}, "reasons": [...]}},
 "compliance": {"sessions": {"done": 2, "total": 6}, "volume": {"actual_km": 34.7, "planned_km": 57.8, "pct": 60},
                "quality": {"done": 0, "total": 1}, "since": "2026-09-21", "rule": "r1-v1"},
 "load_projection": {"ctl_now": 73, "ctl_peak": 80, "ctl_race_day": 78, "tsb_race_day": 14},
 "week": {"index": 1, "start": "2026-09-21", "end": "2026-09-27", "phase": "base", "planned_km": 57.8, "actual_km": 34.7},
 "days": [{"date": "2026-09-26", "state": "done|missed|scheduled|rest|pre_plan",
           "effective": {"workout_id": 152, "source": "garmin", "type": "long", "planned_km": 15.3, "planned_min": 100, "pace": [361, 401], "zone": "Z2"},
           "actual": {"activity_id": 17323, "km": 7.09, "dur_s": 2652, "pace_s": 374, "avg_hr": 141, "provider": "garmin"},
           "outcome": {"label": "under", "volume_ratio": 0.46, "compliance_pct": 46.4, "reason": null},
           "alternatives": [{"workout_id": 6, "source": "planner", "type": "easy", "planned_km": 11.5, "status": "superseded"}],
           "unplanned_runs": [], "retro": null}],
 "next_session": {...}}
```
- `compliance_pct`(단일 값) 필드는 한 릴리스 동안 유지하되 R3 세션 이행 %로 값을 바꾸고, 그 뒤 제거한다.

**GET `/api/v1/coach/plan/:id/weeks`** (신규) → `[{"index":1,"start":"2026-09-21","phase":"base","planned_km":57.8,"actual_km":34.7,"long_km":22.4,"quality":["interval","interval"],"compliance":{"sessions":"2/6"}}, …]` — 1회 호출(현행 63회 조회 대체), 목표 ≤ 200ms.

**GET `/api/v1/coach/plan/:id/session/:date?w=<id>`** (변경): `workouts[]`(그날 모든 행 + 유효 계획 표시), `selected`, `prescription{structure, total_km, total_min, pace_range, hr_zone{z, lo_bpm, hi_bpm, system, source}}`, `rationale`, `pace_source{metric:"race_pred_vdot", value:44.5, date}`, `actual{…, zone_dist[], tss}`, `comparison[{key, planned, actual, delta, better}]`, `outcome`, `superseded_by`, `adjustment{…}`, `interpretation{text, evidence[]}`(규칙 기반, LLM 실패 시에도 채움), `retro`, `nav{prev_date, next_date}`. 선택 규칙: `?w`가 없으면 R1의 유효 계획.

**조정 (S5)**
- 테이블 `plan_adjustments(id, goal_id, workout_id, date, source['crs'|'user'|'coach'], before_json, after_json, reasons_json, decision['proposed'|'accepted'|'reverted'], created_at, decided_at)`. 추가 테이블이므로 SSOT·DDL 정합성 검사(`/check-data-consistency`) 대상이다.
- `POST /api/v1/coach/plan/adjustments/:id/accept` · `/revert` → `{adjustment, compliance, load_delta{week_pct, acwr_expected}}`
- `POST /api/v1/coach/plan/workouts/:id/action` body `{"op":"move|reduce|rest|skip","to_date?":"…","pct?":20,"reason?":"fatigue|injury|schedule"}` → 조정 행(source=user, 즉시 accepted) + 되돌리기 id.
- `GET /api/v1/coach/plan/:id/replan-preview?race_date=&target_s=&days=5&long_dow=6&weekly_max_min=` → 변경 전·후 weeks[] (S6), `POST /coach/plan/:id/replan` → 새 plan_version.
- `POST /api/v1/coach/plan/:id/end` body `{"mode":"end|after_race"}`.

**회고**: `POST /api/v1/coach/plan/workouts/:id/retro` `{"rpe":6,"pain":{"has":false},"note":"…"}`. 날짜 키 노트 API는 폐기하고, 빈 값을 허용해 삭제할 수 있게 한다. 기존 `session_note`는 그날 유효 계획의 workout으로 1회 이관한다. Coach 대화 컨텍스트(`ai/chat_context_*`)에 최근 7일 회고를 포함한다.

**템플릿**: `GET /coach/plan/templates` — `race_date`가 있으면 `{"mode":"scenario","options":[{"key":"challenge|realistic|finish","target_s","mp_s","peak_week_km","long_max_km","mp_km_total","quality_per_week","risk":{"level","reasons":[…]},"weekly_km":[…],"sample_weeks":{…}}]}`, 없으면 `mode:"duration"`(현행 3안). 위험도·예측은 R10을 따른다.

**Coach 연결**: `POST /api/v1/coach/threads` body에 `context:{"type":"plan_session","workout_id":…}` 허용. 답변 파서가 계획 변경 제안을 구조화하면 `proposal{workout_id, before, after, reasons[]}`를 메시지에 첨부하고, 적용은 `workouts/:id/action`(source=coach)을 재사용한다. 파싱에 실패하면 카드 없이 텍스트만 보여 준다(규칙 기반 폴백).

**외부 계획 (S8)**: Garmin 예정 워크아웃(캘린더/adaptive)을 **실행 전에** 인제스트한다(`parse_garmin_adaptive_task` 재사용). Intervals `%pace`는 athlete threshold pace로 속도 목표를 복원한다. 외부 계획 행에도 거리·시간·강도 요약을 채운다. 계획 설정에 `따르는 계획: RunPulse | Garmin | Intervals`(주 단위)를 둔다. 외부를 선택하면 RunPulse 추천은 `alternatives`로 접는다.

---

## 8. 수용 기준

**정확성**
- [ ] 2026-09-21~27 픽스처에서 `compliance.sessions` = 2/6(effective_start 09-21 기준), `quality` = 0/1이다. `16.7`이 어디에도 나오지 않는다(pytest 단위 + API 스냅샷).
- [ ] R5 픽스처 4건(금 강도 어긋남, 토 부족 46%, 일 계획대로, 목 놓침 + 계획 외 10.0km)이 저장 라벨과 화면 배지에서 모두 일치한다. ✓ 아이콘은 `on_target`에만 렌더된다(컴포넌트 테스트).
- [ ] 구조 계획(1000m×4, WU/CD 10분)을 약 8.5~9km로 수행한 합성 활동이 매칭되고, `on_target` 또는 `over`로 판정된다.
- [ ] 계획 HRV·ACWR 값이 같은 시각 Today CRS 게이트 값과 같고(차이 0), ACWR은 두 화면 모두 소수 2자리다.
- [ ] 미래 날짜 세션 API의 `adjustment.state`는 `future`이고, 화면에 "조정 없음 — 계획대로 진행" 문자열이 없다.
- [ ] KST 00:30에 시계를 고정한 테스트에서 어제 세션이 `missed`/`done`으로 판정된다(UTC 오판 없음).
- [ ] 템플릿 예측 = Today 레이스 허브 예측(동일 초 값). 예측이 목표보다 느리면 위험도가 `낮음`이 아니다.
- [ ] (S7) 새 풀코스 계획: 휴식일 ≥ 7 − 선택 일수, 롱런 ≤ min(35% 주간, 150분), 세션 ≥ 6km 또는 35분, build~테이퍼 1주 매주 MP 8km 이상 세션 존재, 테이퍼 2주.

**흐름·상호작용**
- [ ] 계획 목록에서 모든 행이 요일당 1행이다. 완료된 오늘 행을 탭하면 실제 결과(거리·라벨·`활동 보기`)가 보이는 세션 상세가 열린다.
- [ ] 세션 → 활동 상세 → 뒤로가기로 세션 상세에 돌아오고, 계획 상세로 돌아오면 같은 주(`?week`)와 스크롤 위치가 유지된다.
- [ ] 활성 계획이 있어도 새 대회 계획까지 2탭 이내로 도달한다(`⋯` → `새 대회 계획`, 또는 Coach 홈 `+ 다른 대회 준비`).
- [ ] 마법사 단계 표시가 1/3 → 2/3 → 3/3 순서이고, 뒤로가기로 이전 단계와 입력값이 복원된다.
- [ ] `/coach/plan/compare` 무파라미터 진입은 `/coach/plan/new`로 이동한다. 어떤 v2 오류도 SvelteKit 기본 화면을 쓰지 않는다.
- [ ] 조정 적용/원래대로/행 액션은 3탭 이내이고, 적용 후 8초 안에 되돌릴 수 있다. 결정 즉시 ComplianceTriple이 갱신된다.
- [ ] 세션 회고(RPE)는 세션 상세에서 1탭으로 저장되고, 다음 Coach 대화 컨텍스트에 포함된다(컨텍스트 스냅샷 테스트).
- [ ] 세션 상세에서 `Coach에게 묻기` → 새 스레드에 세션 컨텍스트와 질문 칩 3개가 보인다.

**시각·접근성·성능**
- [ ] 모든 인터랙티브 요소가 44×44px 이상이다(ACWR 칩, 세그먼트, 시간 입력, 저장, 헤더 `‹`).
- [ ] 텍스트 대비 ≥ 4.5:1이다(대체 하위 줄 포함, 행 `opacity` 사용 금지).
- [ ] 결과 배지는 색 없이도 구분된다(아이콘 + 텍스트).
- [ ] 계획 상세 API(`?week`) ≤ 200ms, weeks ≤ 200ms, 세션 ≤ 200ms(현행 5~37ms 수준 유지).
- [ ] 탭·주 전환 시각 피드백 ≤ 100ms, 콘텐츠 렌더 ≤ 300ms이고, 스켈레톤 높이 고정으로 CLS 0.02 이하다.
- [ ] 1280/390 두 폭에서 가로 스크롤이 없다(PlanTimeline 14주 초과 시 차트 내부 스크롤만 허용).
- [ ] 계획 화면군에 "플랜", "프로그램" 문자열이 없다.

---

## 9. 구현 순서

| 단계 | 묶음 | 의존 | 규모 |
|---|---|---|---|
| **S1 계산 정정** | R1~R5, R9 HRV/ACWR 소스 통일, R11 날짜, 품질 세션 총량 계산(읽기 시), `unplanned_runs`, 존 체계 개인화. `/coach/plan/:id` 응답에 `days[]`·`compliance{}` 추가. 픽스처 테스트 | 없음 | M |
| **S2 계획 상세 표현** | PlanHeader, ComplianceTriple, PlanDayRow·OutcomeBadge·PlanVsActualBar, WeekList/WeekGrid, 강도 색, `+error.svelte`, compare 리다이렉트, 용어 통일, `lang="ko"`, NextSessionCard 문구 | S1 | M |
| **S3 세션 상세** | `?w` 라우팅, 처방·근거·실제·해석 블록, SessionStructureBar, 페이저, 회고(workout 키) + 노트 이관, `활동 보기` | S1 | M |
| **S4 주기·부하 시각화** | `/weeks` API, PlanTimeline, `?week` 이동, R9 부하 투영, GoalGapLine + 패널, 상태 칩 → MetricBreakdown(패널 규격) | S1 | M |
| **S5 P7 조정·편집** | R8 CRS 단일화, `plan_adjustments`, accept/revert, AdjustmentCard, 행 액션 4종 + 되돌리기, NextSessionCard 문구 원복(`수정은 계획에서`) | S1, S2 | L |
| **S6 생성·생애주기** | 마법사 3단계, RunnerProfileCard, TimeInput, 시나리오 템플릿(R10), 확인 시트·기존 계획 처리, 진입점(`⋯`, Coach 홈), 계획 설정 replan-preview, 대회 후 회고 전환 | S4(미니 타임라인), R10 | L |
| **S7 처방 엔진 보정 (판단 필요)** | R6 M/long_mp, R7 휴식일·롱런 상한·최소 세션·테이퍼 2주, 품질 거리 저장 규칙. BACKLOG `P7-PLAN-ENGINE`의 사용자 승인 뒤 plan mode로 착수하고, 과거 대회 전 훈련으로 백테스트한다 | S1, S6(입력 폼: 일수·롱런 요일) | L |
| **S8 Coach 연결·외부 계획** | 세션 컨텍스트 스레드, 제안 카드 → action API, 대화 컨텍스트 패널, Garmin 사전 인제스트, Intervals %pace 복원, 따르는 계획 선택 | S3, S5 | M |

권장 릴리스 단위: {S1+S2} → {S3+S4} → S5 → S6 → S8. S7은 승인 여부에 따라 S6 뒤에 병행한다.

---

## 10. 발견 → 설계 추적표

| 발견 | 요지 | 설계 위치 | 상태 |
|---|---|---|---|
| F-DATA-01 | 이행률 16.7% 분모·분자 오류 | §4.1 R1·R2·R3, §2.2 ComplianceTriple, §8 | 반영(S1) |
| F-DATA-02 | M 페이스 0km, 목표 미반영 | §4.1 R6, §2.1 GoalGapLine | 반영(규칙 S7 판단 필요, 간극 표시는 S4) |
| F-DATA-03 | 휴식 0일·롱런 50%·32km | §4.1 R7, §2.6 ② 내 일정 | 반영(S7 판단 필요, 입력 폼 S6) |
| F-DATA-04 | 품질 세션 거리 과소 → 매칭 실패 | §4.1 R4, `unplanned_runs` | 반영(S1) |
| F-DATA-05 | 라벨 모순(✓46%, 회복 과속 ✓) | §4.1 R5, OutcomeBadge | 반영(S1·S2) |
| F-DATA-06 | 두 엔진 혼재·소급 생성 | §4.1 R2 plan_version, PlanHeader 버전 표시 | 반영(S1·S2) |
| F-DATA-07 | 세션 상세 처방 근거·결과 없음 | §2.5, §7.2 session API | 반영(S3) |
| F-DATA-08 | 표시 지표 ≠ 조정 지표, 수락 없음 | §4.1 R8, AdjustmentCard | 반영(S5) |
| F-DATA-09 | HRV 107 vs 80, 상한 없는 판정 | §4.1 R9 | 반영(S1) |
| F-DATA-10 | ACWR 자릿수·시각·정의, CTL 막대 | §4.1 R9, §5 PlanTimeline CTL 줄 | 반영(S1·S4) |
| F-DATA-11 | 선택지 1개·위험 낮음 모순·예측 3종·400 | §4.1 R10, §2.6 시나리오, §3 compare 리다이렉트 | 반영(S2·S6) |
| F-DATA-12 | 외부 계획 사후 생성·%pace 폐기 | §7.2 외부 계획, R1 우선순위 | 반영(S8), R1 부분은 S1 |
| F-DATA-13 | 9주 전체 비가시 | §5 PlanTimeline, `/weeks` API | 반영(S4) |
| F-DATA-14 | 테이퍼 3주·강도 미유지 | §4.1 R7 테이퍼 | 반영(S7 판단 필요) |
| F-UI-01 | 계획 vs 실제 없음·색 반전 | PlanDayRow·PlanVsActualBar, R5 | 반영(S2). 외부 행 병합은 R1 "요일당 1행"으로 해결 |
| F-UI-02 | 세션 상세 원 계획만·같은 URL | §2.5, §3 `?w`, 조정 블록 조건부 | 반영(S3). URL은 `:date?w=`로 결정(§1 상충) |
| F-UI-03 | compare 무스타일 400 | §6 `+error.svelte`, §3 리다이렉트 | 반영(S2) |
| F-UI-04 | 단계 시각화·CTL 임의 막대·이행률 위계 | §5 PlanTimeline, R9, ComplianceTriple 상단 배치 | 반영(S4·S2). 원형 게이지 대신 분수 텍스트 채택(세 수치를 나란히 보여야 해서) |
| F-UI-05 | 날짜·오늘·강도 색·주 합계·데스크톱 폭 | §2.2 WeekGrid, §2.3, §4.3 강도 색 | 반영(S2) |
| F-UI-06 | 상태 회색 동일·대비 1.87·UTC | R5 배지, R11, §8 대비 | 반영(S1·S2) |
| F-UI-07 | 적응 블록 어포던스·20px·영어 시트·조정 자리 | PlanStatusStrip 칩, MetricBreakdown 변경, AdjustmentCard | 반영(S4·S5). 4타일 대신 칩 3개(판단 신호만, 피로는 CRS 내부) |
| F-UI-08 | 폼 단계·날짜 형식·컨트롤·프로필 | §2.6, TimeInput, Stepper, `lang="ko"` | 반영(S6, `lang` S2) |
| F-UI-09 | 세션 하단 공백·헤더 링크 작음 | §2.5 4블록 + 페이저, 공용 헤더 44px | 반영(S3) |
| F-UI-10 | 비교 세로 스택·차이 비강조·미정의 토큰 | ScenarioCompareTable(차이만 굵게), 토큰 규칙 | 반영(S6) |
| F-UI-11 | 용어·버튼·뒤로 방식 불일치 | §4.3 용어, `‹` 헤더 통일, 주 버튼 토큰 | 반영(S2) |
| F-UX-01 | 세션이 대체 계획을 표시 | R1 유효 계획, `?w`, §2.5 | 반영(S1·S3) |
| F-UX-02 | 수정·조정 상호작용 없음·Today 문구 | AdjustmentCard, 행 액션, replan, NextSessionCard 문구 | 반영(S5·S6, 문구 S2) |
| F-UX-03 | 활성 계획 시 새 계획 진입 없음 | `⋯` 메뉴, Coach 홈 `+ 다른 대회`, 확인 시트 기존 계획 처리, 대회 후 전환 | 반영(S6) |
| F-UX-04 | 1/3→3/3, 프로필·일정 없음, 비교 1개, 즉시 생성 | §2.6 3단계·시나리오·샘플 주·확인 시트 | 반영(S6) |
| F-UX-05 | 라벨 모순·요일당 2행·계획 전 미이행 | R1·R2·R5, PlanDayRow | 반영(S1·S2). "변경" 라벨은 놓침 + 계획 외 러닝으로 대체(§1) |
| F-UX-06 | 이번 주만·구조·근거 없음 | PlanTimeline, `?week`, 일요일 다음 주 기본, SessionStructureBar | 반영(S4·S3) |
| F-UX-07 | 메모 날짜 키·미사용 | workout 키 회고, Coach 컨텍스트, 삭제 허용 | 반영(S3). 반영 결과 한 줄("다음 세션에 반영")은 S5 조정 엔진이 쓸 때만 표시 |
| F-UX-08 | Today·Coach·계획 단절 | §3 Coach에게 묻기·제안 카드·컨텍스트 패널, NextSessionCard `결과 보기` | 반영(S8, Today 링크 S2) |
| F-UX-09 | 적응 블록 위치·HRV 무반응 | PlanStatusStrip 상단 배치, 칩 전부 탭 가능 | 반영(S4) |
| F-UX-10 | ← 없음·세션 간 이동·UTC | 공용 헤더, 페이저, R11 | 반영(S2·S3·S1) |
| F-UX-11 | 경쟁 앱 기본 동등성 미달 | 주 이동·행 액션·요일 설정·완료 후 피드백·계획/실제 색(S2~S6), 근거 달린 조정·4소스 통합·예측 궤적(signature) | 반영. **워치 전송**(`garmin_push`/`caldav_push` 노출)은 보류: 쓰기 경로이고 외부 계정 부작용이 있어 S8 이후 별도 항목으로 사용자 판단 필요 |
