# 설계: 오버레이 공통 동작 (Esc·포커스 이동/트랩/복귀·스크롤 잠금·배경 비활성)

- 대상 증상: E-08, C-03, S-07, S-08, S-10, D-25 (99-summary 항목 4)
- 상태: 설계 초안 — 구현 전 "7. 결정 필요" 확인 필요
- 범위: `frontend/src/lib/components/` 의 드로어·시트·다이얼로그·인라인 확인 창 (v2 전용)

## 1. 근본 원인

**RC-1. 모달 동작을 맡는 공통 부품이 없음 — 선언만 복사되고 동작은 화면마다 다르게 만듦.**
`role="dialog" aria-modal="true"` 마크업은 컴포넌트 9곳에 복사되어 있지만, 실제 키보드·포커스 동작은 제각각이다.

| 컴포넌트 | Esc | 처음 포커스 | 트랩 | 포커스 복귀 | 스크롤 잠금 |
|---|---|---|---|---|---|
| MenuDrawer (E-08, S-07/08) | 없음 | 없음 | 없음 | 없음 | 없음 |
| SyncStatusPill + SyncPanel `?sheet=sync` (S-07/08) | 없음 | 없음 (`keepFocus`) | 없음 | 없음 | 없음 |
| coach/ScopeSheet (C-03) | 없음 | 없음 | 없음 | 없음 | 없음 |
| DrillPanel (S-10) | window, `stopPropagation` | heading | 없음 | 없음 | 없음 |
| plan/RowActionSheet | 있음 | 있음 | 자체 구현 | 없음 | 없음 |
| DemoBanner | 시트 요소 안에서만 | 없음 | 없음 | 없음 | 없음 |
| EngineSheet, MilestonesPanel, MetricBreakdown, GarminCleanup | 확인 필요 (grep 결과 Esc 처리 없음) | 없음 | 없음 | 없음 | 없음 |

그 결과 스크린리더에는 "모달"이라고 알리면서 실제 동작은 비모달이고, 컴포넌트를 새로 만들 때마다 같은 누락이 다시 생긴다. 하나만 고쳐도(예: RowActionSheet) 다른 곳에는 반영되지 않는다.

**RC-2. 인라인 확인과 모달 확인을 구분하지 않음.**
ConnectPanel(D-25, S-10), CalendarFeedCard, McpTokenCard 의 확인 창은 문서 흐름 안에 그려지는 **인라인 블록**인데 `role="alertdialog"` 를 달고 있다. 이 역할을 쓰면 포커스 이동과 Esc 를 기대하게 되지만, 정작 확인 창이 열려도 포커스는 호출 버튼에 그대로 남는다. 파괴적 동작(연결 해제)을 확인하는 창이 키보드 사용자에게 보이지 않을 수 있다.

부수 원인: 열림 상태가 URL(`?sheet=sync`, 드릴 스택)과 컴포넌트 state 두 곳에 나뉘어 있고, 오버레이가 겹칠 때(드로어 → 동기화 시트, 드릴 패널 안 ChartScrub Esc) 맨 위 오버레이를 판정하는 기준이 없다. 그래서 Esc 처리가 `stopPropagation` 순서에 좌우된다.

## 2. 설계안 (추천: A안 — 순수 코어 + Svelte action)

### 2.1 순수 코어 `lib/overlayCore.ts` (신규, DOM 비의존)
- `overlayStack`: `push(id)`, `pop(id)`, `top()`, `isTop(id)` — 겹친 오버레이 중 Esc·트랩을 받을 대상을 하나로 정한다.
- `nextFocusIndex(count, current, shift)`: Tab/Shift+Tab 순환 인덱스를 계산한다.
- `scrollLock`: 참조 카운터. `acquire()`가 0→1일 때만 잠그고 `release()`가 1→0일 때만 원래 값을 복원한다. 실제 style 적용은 콜백으로 주입한다.
- `FOCUSABLE_SELECTOR` 상수: button·a[href]·input·select·textarea·[tabindex]:not([tabindex="-1"]). disabled 와 hidden 은 제외한다.

### 2.2 모달 action `lib/overlay.ts` — `use:modal={{ onClose, initialFocus?, label?, enabled? }}` (신규)
- 마운트될 때 호출 요소(`document.activeElement`)를 기억하고 → 스택에 push → 스크롤을 잠그고 → 배경을 비활성화한다(아래 결정 D-3) → `initialFocus` 또는 `[data-autofocus]`, 없으면 첫 포커스 요소, 그것도 없으면 컨테이너(`tabindex=-1`)에 포커스한다.
- 키 처리는 document 에 한 번만 등록한다. `isTop(id)` 일 때만 Esc → `onClose()`, Tab → 트랩 순환.
- 해제될 때 pop → 스크롤 잠금 해제 → 포커스 복귀. 복귀 대상이 DOM 에서 사라졌거나 다른 오버레이가 이미 위에 있으면 복귀를 건너뛰고, 대신 `main` 랜드마크로 보낸다.
- `enabled=false` 이면 아무 동작도 하지 않는다. DrillPanel 은 데스크톱(lg)에서 인라인 패널이므로 모달 동작이 들어가면 안 된다. 현재 `lg:hidden` 노드가 데스크톱에서도 마운트되기 때문에, 미디어쿼리 결과를 `enabled` 로 넘긴다.
- 배경 닫기 `<button class="absolute inset-0">` 은 Tab 순서에서 뺀다(`tabindex=-1`, `aria-hidden`). 이것이 첫 포커스 대상이 되는 것을 막기 위해서다.

### 2.3 인라인 확인 action `use:inlineConfirm={{ onCancel }}` (신규, 같은 파일)
- 열릴 때 확인 블록 안으로 포커스를 옮기고, 블록 안에서 Esc 를 누르면 취소하며, 닫힐 때 호출 버튼으로 포커스를 복귀한다. 트랩과 스크롤 잠금은 하지 않는다.
- 역할 이름(`alertdialog` 유지 / `group` 으로 변경)과 처음 포커스를 받을 버튼은 결정 D-1, D-2 에 따른다.

### 2.4 URL 연동 오버레이
- `?sheet=sync` 와 드릴 스택은 "URL 이 열림 상태의 원본"이라는 기존 방식을 그대로 둔다. 따라서 action 의 `onClose` 는 URL 을 갱신하는 함수(`setOpen(false)`, `closeDrill`)를 가리킨다.
- `SyncPanel` 내부의 `role="dialog"` 는 바깥 컨테이너로 옮겨 dialog 가 한 겹만 남게 한다.
- 뒤로가기로 닫는 동작은 결정 D-4 에 따른다.

## 3. 변경 파일 표 (경로는 `frontend/` 기준)

| 파일 | 신규/수정 | 내용 | 예상 줄 수 |
|---|---|---|---|
| `src/lib/overlayCore.ts` | 신규 | 스택·Tab 순환·스크롤 잠금 카운터·selector | ~90 |
| `src/lib/overlay.ts` | 신규 | `modal`, `inlineConfirm` action | ~120 |
| `tests/overlayCore.test.mjs` | 신규 | 코어 함수마다 테스트 1개 이상 (중첩 스택, 순환 양끝, 잠금 0↔1 경계) | ~120 |
| `src/lib/components/MenuDrawer.svelte` | 수정 | `use:modal`, 배경 버튼 Tab 제외 | +4 / -1 |
| `src/lib/components/shell/SyncStatusPill.svelte` | 수정 | 컨테이너에 role·`use:modal`, `keepFocus` 정리 | +5 / -1 |
| `src/lib/components/shell/SyncPanel.svelte` | 수정 | 내부 `role="dialog"` 제거 | -1 |
| `src/lib/components/coach/ScopeSheet.svelte` | 수정 | `use:modal`, 처음 포커스 = 시트 안 주요 버튼 | +3 |
| `src/lib/components/DrillPanel.svelte` (214줄) | 수정 | window Esc 핸들러를 action 으로 바꿈, `enabled`=모바일 | +4 / -10 |
| `src/lib/components/data/ConnectPanel.svelte` | 수정 | `use:inlineConfirm` | +2 |
| `src/lib/components/CalendarFeedCard.svelte`, `McpTokenCard.svelte` | 수정 | `use:inlineConfirm` (같은 계열이라 함께) | 각 +2 |
| `src/lib/components/plan/RowActionSheet.svelte` | 수정 | 자체 트랩·Esc 를 action 으로 교체 | +2 / -14 |
| `DemoBanner`, `coach/EngineSheet`, `MilestonesPanel`, `MetricBreakdown`, `plan/GarminCleanup` | 수정 | `use:modal` 적용 (재발 방지 목적의 전수 적용) | 각 +2 |

합계: 신규 3개(~330줄), 수정 약 14개(순증 약 +20줄). 모든 파일이 300줄 이하를 유지한다.

## 4. 적용 순서와 검증

1. **코어와 테스트**: `overlayCore.ts` 와 테스트를 추가한다. 검증: `npm run test:unit` 통과.
2. **action 추가 + 1차 적용(MenuDrawer)**: 브라우저에서 375px로 E-08 재현 절차를 따른다. 메뉴 열기 → 포커스가 드로어 안으로 이동, Tab 반복 시 `activeElement.closest('[role=dialog]')` 가 항상 non-null, Esc 로 닫힘, 닫힌 뒤 포커스가 메뉴 버튼으로 복귀, 열려 있는 동안 `body` overflow 가 잠김.
3. **동기화 시트와 중첩**: 드로어의 동기화 행 → 시트. 드로어가 닫히며 시트로 포커스가 넘어가고, 시트에서 Esc 를 누르면 `?sheet=sync` 가 제거되어야 한다. 딥링크 `?sheet=sync` 로 직접 진입했을 때도 처음 포커스가 시트 안이어야 한다. (S-07, S-08)
4. **ScopeSheet (C-03)**: 첫 전송 → 처음 포커스가 시트 안에 있어야 하고, 배경의 "전송" 버튼으로 Tab 이 빠져나가지 않아야 하며, Esc 로 닫혀야 한다.
5. **DrillPanel**: 모바일에서는 트랩·Esc·잠금이 동작해야 한다. 데스크톱(lg)에서는 트랩·잠금이 없어야 하고 Esc 는 기존처럼 pop 해야 한다. ChartScrub/ActivityHeatmap 의 Esc 와 이중으로 처리되지 않는지 확인한다. (S-10)
6. **인라인 확인 (D-25, S-10)**: `/data/sources/strava` 에서 해제를 누르면 포커스가 확인 블록 안으로 이동하고, Esc 로 취소되며, 취소 후 "연결 해제…" 버튼으로 포커스가 복귀해야 한다.
7. **나머지 일괄 적용과 회귀 확인**: RowActionSheet 의 기존 동작(처음 포커스는 첫 액션, Esc 닫기)이 유지되어야 한다. 실행: `npm run check`, 단위 테스트 전체, 백엔드 `python3 -m pytest tests/` (영향 없음 확인용).

## 5. 호환성·v1 의존

- **동작 변경**: 배경 닫기 버튼이 Tab 순서에서 빠진다. 닫기는 시트 안의 닫기 버튼이나 Esc 로 한다. RowActionSheet 는 트랩 대상 selector 가 넓어진다(select·textarea·tabindex 포함). DrillPanel 은 window `stopPropagation` 방식에서 스택 판정 방식으로 바뀐다. 시트 안 차트의 Esc(ChartScrub)는 차트가 이벤트를 먼저 소비하면 그대로 두는 규칙(`defaultPrevented` 존중)이 필요하다.
- **URL 계약 불변**: `?sheet=sync` 와 드릴 스택의 쿼리 형식은 바뀌지 않는다.
- **v1 의존**: action 자체는 v1 에 의존하지 않는다. 다만 MenuDrawer 는 "과도기 드로어"로, 내용의 대부분이 v1 링크(`data-sveltekit-reload`)와 "v1로 돌아가기"다. v1 이 제거되면 드로어의 내용이 바뀌거나 드로어 자체가 사라질 수 있으므로 MenuDrawer 수정은 최소(action 부착)로 한정한다. v1 템플릿은 수정하지 않는다.

## 6. 대안 비교

| | A. 순수 코어 + action (추천) | B. 공용 `<Modal>` 래퍼 컴포넌트 (snippet) |
|---|---|---|
| 적용 방식 | 기존 마크업에 `use:modal` 한 줄 | 각 시트를 래퍼로 감싸도록 구조 변경 |
| 레이아웃 다양성 | 드로어(좌측)·하단 시트·팝오버·인라인을 그대로 유지 | 래퍼가 위치·배경까지 담당하면 변형 prop 이 늘어남 |
| 테스트 | 코어를 node --test 로 단위 검증 가능 | DOM 테스트 환경이 없으면 검증이 어려움 |
| 재발 방지 | 부착을 잊을 수 있음 → check 스크립트/grep 검사 보완 필요 | 래퍼를 쓰면 자동으로 보장 |
| 변경 규모 | 작음 (순증 ~20줄) | 중간 (9개 파일 구조 변경) |

외부 라이브러리(focus-trap 계열, headless UI 키트)는 의존성 추가 여부가 사용자 결정 사항이라 D-5 로 분리했다.

## 7. 결정 필요

- **D-1 인라인 확인의 역할**: (a) `alertdialog` 를 유지하고 포커스 이동과 Esc 만 추가 — 마크업 변경이 적지만, 비모달 alertdialog 라는 모호함이 남는다. (b) `role="group"` + `aria-live` 알림으로 변경 — 의미가 정확하지만 스크린리더 안내 문구가 바뀐다. (c) 소스 해제만 모달 alertdialog 로 승격 — 파괴적 동작을 강하게 보호하지만, 인라인 맥락(활동 N건 유지 안내)이 화면에서 분리된다.
- **D-2 파괴적 확인의 처음 포커스**: "취소" — 실수로 해제될 위험이 낮다. 또는 "연결 해제" — 의도한 사용자에게 한 단계가 짧다.
- **D-3 배경 비활성 방식**: (a) 오버레이를 body 로 옮기고 앱 루트에 `inert` — 완전한 모달이 되지만 DOM 이동으로 인한 스타일·컨텍스트 회귀 위험이 있다. (b) 트랩과 `aria-modal` 만 사용 — 단순하지만 일부 스크린리더의 가상 커서가 배경에 접근할 수 있다.
- **D-4 뒤로가기로 닫기**: 시트를 열 때 history 에 push — 모바일의 기대와 맞지만, 뒤로가기 한 번이 페이지 이동이 아니게 된다. 또는 현행 `replaceState` 유지 — 뒤로가기를 누르면 페이지를 떠난다. 드릴 스택과 정책을 맞출지도 함께 정해야 한다.
- **D-5 구현 방식**: A안(자체 action) / B안(래퍼) / 외부 라이브러리 도입 중 선택. 외부 라이브러리는 의존성 추가 정책 판단이 필요하다.
- **D-6 스크롤 잠금 방식**: `overflow:hidden` 만 사용(iOS Safari 에서 배경 스크롤이 샐 수 있음) 또는 `position:fixed` + 스크롤 위치 복원(확실하지만 닫을 때 스크롤 점프 위험이 있음).
- **D-7 재발 방지 검사**: `role="dialog"` 가 있는데 `use:modal` 이 없으면 실패하는 검사를 프론트 테스트에 넣을지, `scripts/check_docs.py` 계열에 넣을지, 넣지 않을지.

## 8. 범위 밖 메모

- E-23 DemoBanner Esc 는 같은 계열이라 적용 대상에 포함했지만, 배너 자체의 UX 문제는 다루지 않는다.
- S-11 토스트 라이브 영역·5초 확인은 이 패턴 밖이다.
- ActivityMoreMenu(`role="menu"`)의 메뉴 키보드 패턴(화살표 이동)은 별도 항목으로 다뤄야 한다.
