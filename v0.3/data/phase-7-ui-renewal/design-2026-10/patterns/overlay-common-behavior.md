# 설계: 오버레이 공통 동작 (Esc·포커스 이동/트랩/복귀·스크롤 잠금·배경 비활성)

- 대상 증상: E-08, C-03, S-07, S-08, S-10, D-25 (99-summary 항목 4), E-23 (ERR-7 결정으로 이 문서 소관)
- 상태: 설계 확정 — OVL-1~8 결정 반영(2026-10-11), OVL-1 은 A11Y-L1 로 수정(2026-10-12). 구현 가능
- 변경 이력: 2026-10-11 설계서 동기화(OVL-1~7·ERR-7 결정 반영, "결정 필요" → "결정됨") · 2026-10-11 5차 동기화(V1-2·V1-5: §5 MenuDrawer 를 BACKLOG `MENUDRAWER-POST-V1` 참조로 정리, §9 해소) · 2026-10-11 6차 동기화(V1-11: §5 MenuDrawer "CSV 내보내기" 링크를 EXP 화면 연결로 갱신, data-export 소관) · 2026-10-11 7차 동기화(V1-13: §5 MenuDrawer v1 링크 손상 감수 한 줄, V1-3·V1-12: §5 사용자 전환 링크 교체·production 숨김 소관 명시) · 2026-10-12 9차 동기화(A11Y-L1: §2.3·§4·§7 OVL-1 을 group+labelledby·live 없음으로 수정, §9 이중 읽기 해소 / OVL-8: §2.4 드릴 스택 history push 확정과 딥링크 닫기 규칙, §3·§5·§7 반영 / S-11 참조를 LiveRegion 으로 갱신)
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
| DemoBanner (E-23) | 시트 요소 안에서만 | 없음 | 없음 | 없음 | 없음 |
| EngineSheet, MilestonesPanel, MetricBreakdown, GarminCleanup | 확인 필요 (grep 결과 Esc 처리 없음) | 없음 | 없음 | 없음 | 없음 |

그 결과 스크린리더에는 "모달"이라고 알리면서 실제 동작은 비모달이고, 컴포넌트를 새로 만들 때마다 같은 누락이 다시 생긴다. 하나만 고쳐도(예: RowActionSheet) 다른 곳에는 반영되지 않는다.

**RC-2. 인라인 확인과 모달 확인을 구분하지 않음.**
ConnectPanel(D-25, S-10), CalendarFeedCard, McpTokenCard 의 확인 창은 문서 흐름 안에 그려지는 **인라인 블록**인데 `role="alertdialog"` 를 달고 있다. 이 역할을 쓰면 포커스 이동과 Esc 를 기대하게 되지만, 정작 확인 창이 열려도 포커스는 호출 버튼에 그대로 남는다. 파괴적 동작(연결 해제)을 확인하는 창이 키보드 사용자에게 보이지 않을 수 있다.

부수 원인: 열림 상태가 URL(`?sheet=sync`, 드릴 스택)과 컴포넌트 state 두 곳에 나뉘어 있고, 오버레이가 겹칠 때(드로어 → 동기화 시트, 드릴 패널 안 ChartScrub Esc) 맨 위 오버레이를 판정하는 기준이 없다. 그래서 Esc 처리가 `stopPropagation` 순서에 좌우된다.

## 2. 설계안 (확정: A안 — 순수 코어 + 자체 Svelte action, OVL-5)

### 2.1 순수 코어 `lib/overlayCore.ts` (신규, DOM 비의존)
- `overlayStack`: `push(id)`, `pop(id)`, `top()`, `isTop(id)` — 겹친 오버레이 중 Esc·트랩을 받을 대상을 하나로 정한다.
- `nextFocusIndex(count, current, shift)`: Tab/Shift+Tab 순환 인덱스를 계산한다.
- `scrollLock`: 참조 카운터. `acquire()`가 0→1일 때만 `body` 에 `overflow:hidden` 을 걸고 `release()`가 1→0일 때만 원래 값을 복원한다(OVL-6). 실제 style 적용은 콜백으로 주입한다. `position:fixed` 방식은 쓰지 않는다.
- `FOCUSABLE_SELECTOR` 상수: button·a[href]·input·select·textarea·[tabindex]:not([tabindex="-1"]). disabled 와 hidden 은 제외한다.

### 2.2 모달 action `lib/overlay.ts` — `use:modal={{ onClose, initialFocus?, label?, enabled? }}` (신규)
- 마운트될 때 호출 요소(`document.activeElement`)를 기억하고 → 스택에 push → 스크롤을 잠그고 → `initialFocus` 또는 `[data-autofocus]`, 없으면 첫 포커스 요소, 그것도 없으면 컨테이너(`tabindex=-1`)에 포커스한다.
- 배경 비활성(OVL-3): **포커스 트랩 + `aria-modal="true"` 만 쓴다. `inert`·DOM 이동(body 포털)은 쓰지 않는다.** 오버레이는 지금 위치에 그대로 그린다.
- 키 처리는 document 에 한 번만 등록한다. `isTop(id)` 일 때만 Esc → `onClose()`, Tab → 트랩 순환. 하위 요소가 이미 처리한 Esc(`defaultPrevented`)는 무시한다.
- 해제될 때 pop → 스크롤 잠금 해제 → 포커스 복귀. 복귀 대상이 DOM 에서 사라졌거나 다른 오버레이가 이미 위에 있으면 복귀를 건너뛰고, 대신 `main` 랜드마크로 보낸다.
- `enabled=false` 이면 아무 동작도 하지 않는다. DrillPanel 은 데스크톱(lg)에서 인라인 패널이므로 모달 동작이 들어가면 안 된다. 현재 `lg:hidden` 노드가 데스크톱에서도 마운트되기 때문에, 미디어쿼리 결과를 `enabled` 로 넘긴다.
- 배경 닫기 `<button class="absolute inset-0">` 은 Tab 순서에서 뺀다(`tabindex=-1`, `aria-hidden`). 이것이 첫 포커스 대상이 되는 것을 막기 위해서다.

### 2.3 인라인 확인 action `use:inlineConfirm={{ onCancel }}` (신규, 같은 파일)
- 역할(OVL-1, A11Y-L1 수정): 인라인 확인 블록은 `role="alertdialog"` 를 제거하고 **`role="group"` + `aria-labelledby`(확인 문구)** 로 바꾼다. **live 영역은 쓰지 않는다.** 알림은 아래 포커스 이동이 맡는다 — "취소"로 포커스가 들어가면 스크린리더가 그룹 이름(확인 문구)과 버튼 이름을 한 번 읽는다. 블록 안에 `aria-live`·`role=status|alert` 를 두지 않는다(`accessibility-layout.md` §2.3 R1, 가드 (g)).
- 열릴 때 확인 블록 안으로 포커스를 옮긴다. **파괴적 확인(연결 해제·토큰 폐기 등)의 처음 포커스는 "취소"**(OVL-2, `data-autofocus` 로 지정). 블록 안에서 Esc 를 누르면 취소하며, 닫힐 때 호출 버튼으로 포커스를 복귀한다. 트랩과 스크롤 잠금은 하지 않는다.

### 2.4 URL 연동 오버레이와 뒤로가기 (OVL-4)
- `?sheet=sync` 와 드릴 스택은 "URL 이 열림 상태의 원본"이라는 기존 방식을 그대로 둔다. 따라서 action 의 `onClose` 는 URL 을 갱신하는 함수(`setOpen(false)`, `closeDrill`)를 가리킨다.
- **시트를 열 때 history 에 push 한다.** 뒤로가기는 시트만 닫고 페이지는 그대로 둔다. 앱 안에서 열어 push 한 경우 닫기(Esc·닫기 버튼)는 `history.back()` 으로 그 항목을 되돌리고, 딥링크로 `?sheet=sync` 에 직접 진입한 경우(되돌릴 항목 없음)는 `replaceState` 로 쿼리만 지운다. 열림 경로는 `history.state` 표식으로 구분한다.
- **드릴 스택도 push 정책을 따른다(OVL-8).** 현행 `lib/drillStack.ts` 가 이미 단계마다 `pushState`(`openDrill`:28, `pushDrill`:39)하고 `popDrill` 은 `history.back()`, `closeDrill` 은 `history.go(-depth)` 다. 뒤로가기는 한 단계씩 닫는다. 해상도(모바일 시트·lg 인라인 패널)와 무관하게 같다.
- **딥링크 진입 닫기 규칙(시트·드릴 공통):** 앱 안에서 push 한 항목만 history 로 되돌리고, URL 로 직접 들어온 부분은 `replaceState` 로 쿼리만 줄인다. 현행 드릴은 `?drill=a,b` 딥링크에서 닫으면 `history.go(-2)` 로 페이지를 떠난다. 판정은 `page.state.drill`(push 한 항목에만 존재) 유무로 한다: 있으면 `history.back()`, 없으면 `replaceState(스택−1)`. `closeDrill` 은 push 한 단계 수만큼 되돌린 뒤 남은 딥링크 스택을 `replaceState` 로 지운다. 계산은 `drillStackCore.ts` 순수 함수 `closePlan(stateStack, urlStack) → { back: n, replace: string[] | null }` 로 두고 `drill-stack.test.mjs` 에 케이스를 추가한다.
- `SyncPanel` 내부의 `role="dialog"` 는 바깥 컨테이너로 옮겨 dialog 가 한 겹만 남게 한다.

### 2.5 재발 방지 검사 (OVL-7)
- 프론트 테스트에 검사를 넣는다. 위치는 접근성 정적 스캔과 같은 `tests/a11yStatic.test.mjs`(`accessibility-common.md` 2.4). `src/**/*.svelte` 에서 `role="dialog"` 가 있는데 `use:modal` 이 없으면 실패, `role="alertdialog"` 가 남아 있으면 실패(인라인 확인은 group).
- `scripts/check_docs.py` 에는 넣지 않는다.

## 3. 변경 파일 표 (경로는 `frontend/` 기준)

| 파일 | 신규/수정 | 내용 | 예상 줄 수 |
|---|---|---|---|
| `src/lib/overlayCore.ts` | 신규 | 스택·Tab 순환·overflow 잠금 카운터·selector | ~90 |
| `src/lib/overlay.ts` | 신규 | `modal`(트랩+aria-modal), `inlineConfirm`(group+labelledby, live 없음), history push/back 헬퍼 | ~140 |
| `src/lib/drillStack.ts`, `drillStackCore.ts`, `tests/drill-stack.test.mjs` | 수정 | OVL-8 딥링크 닫기(`closePlan`) | 각 +5~15 |
| `tests/overlayCore.test.mjs` | 신규 | 코어 함수마다 테스트 1개 이상 (중첩 스택, 순환 양끝, 잠금 0↔1 경계) | ~120 |
| `tests/a11yStatic.test.mjs` | 신규(접근성 설계와 공유) | dialog↔use:modal, alertdialog 잔존 검사 추가 | +20 |
| `src/lib/components/MenuDrawer.svelte` | 수정 | `use:modal`, 배경 버튼 Tab 제외 | +4 / -1 |
| `src/lib/components/shell/SyncStatusPill.svelte` | 수정 | 컨테이너에 role·`use:modal`, `keepFocus` 정리, 열 때 push | +8 / -2 |
| `src/lib/components/shell/SyncPanel.svelte` | 수정 | 내부 `role="dialog"` 제거 | -1 |
| `src/lib/components/coach/ScopeSheet.svelte` | 수정 | `use:modal`, 처음 포커스 = 시트 안 주요 버튼 | +3 |
| `src/lib/components/DrillPanel.svelte` (214줄) | 수정 | window Esc 핸들러를 action 으로 바꿈, `enabled`=모바일 | +4 / -10 |
| `src/lib/components/data/ConnectPanel.svelte` | 수정 | `use:inlineConfirm`, alertdialog → group, 취소 버튼 `data-autofocus` | +3 / -1 |
| `src/lib/components/CalendarFeedCard.svelte`, `McpTokenCard.svelte` | 수정 | 같음 | 각 +3 / -1 |
| `src/lib/components/plan/RowActionSheet.svelte` | 수정 | 자체 트랩·Esc 를 action 으로 교체 | +2 / -14 |
| `DemoBanner`(E-23), `coach/EngineSheet`, `MilestonesPanel`, `MetricBreakdown`, `plan/GarminCleanup` | 수정 | `use:modal` 적용 (재발 방지 목적의 전수 적용) | 각 +2 |

합계: 신규 3개(~350줄) + 공유 테스트 +20, 수정 약 16개(순증 약 +45줄, OVL-8 드릴 딥링크 규칙 포함). 모든 파일이 300줄 이하를 유지한다. 의존성 추가 없음.

## 4. 적용 순서와 검증

1. **코어와 테스트**: `overlayCore.ts` 와 테스트를 추가한다. 검증: `npm run test:unit` 통과.
2. **action 추가 + 1차 적용(MenuDrawer)**: 브라우저에서 375px로 E-08 재현 절차를 따른다. 메뉴 열기 → 포커스가 드로어 안으로 이동, Tab 반복 시 `activeElement.closest('[role=dialog]')` 가 항상 non-null, Esc 로 닫힘, 닫힌 뒤 포커스가 메뉴 버튼으로 복귀, 열려 있는 동안 `body` overflow 가 hidden.
3. **동기화 시트와 중첩·뒤로가기**: 드로어의 동기화 행 → 시트. 드로어가 닫히며 시트로 포커스가 넘어가고, 시트에서 Esc 를 누르면 `?sheet=sync` 가 제거되어야 한다. 시트가 열린 상태에서 뒤로가기 → 시트만 닫히고 페이지 유지, 다시 뒤로가기 → 이전 페이지. 딥링크 `?sheet=sync` 로 직접 진입했을 때도 처음 포커스가 시트 안이어야 하고, 닫으면 페이지를 떠나지 않아야 한다. 드릴(OVL-8): 2단 연 뒤 뒤로가기 2회로 한 단계씩 닫히고, 딥링크 `?drill=a,b` 진입 후 닫기·Esc 로 페이지를 떠나지 않아야 한다. (S-07, S-08)
4. **ScopeSheet (C-03)**: 첫 전송 → 처음 포커스가 시트 안에 있어야 하고, 배경의 "전송" 버튼으로 Tab 이 빠져나가지 않아야 하며, Esc 로 닫혀야 한다.
5. **DrillPanel**: 모바일에서는 트랩·Esc·잠금이 동작해야 한다. 데스크톱(lg)에서는 트랩·잠금이 없어야 하고 Esc 는 기존처럼 pop 해야 한다. ChartScrub/ActivityHeatmap 의 Esc 와 이중으로 처리되지 않는지 확인한다. (S-10)
6. **인라인 확인 (D-25, S-10)**: `/data/sources/strava` 에서 해제를 누르면 포커스가 확인 블록의 "취소" 로 이동하고, 스크린리더가 확인 문구를 한 번 읽으며(그룹 이름 + "취소", live 없음), Esc 로 취소되고, 취소 후 "연결 해제…" 버튼으로 포커스가 복귀해야 한다.
7. **DemoBanner (E-23)**: 데모 시트에서 Esc 가 포커스 위치와 무관하게 닫히고 호출 버튼으로 복귀하는지 본다.
8. **나머지 일괄 적용과 회귀 확인**: RowActionSheet 의 기존 동작(처음 포커스는 첫 액션, Esc 닫기)이 유지되어야 한다. 재발 방지 검사(2.5)를 켠다. 실행: `npm run check`, 단위 테스트 전체, 백엔드 `python3 -m pytest tests/` (영향 없음 확인용).

## 5. 호환성

- **동작 변경**: 배경 닫기 버튼이 Tab 순서에서 빠진다. 닫기는 시트 안의 닫기 버튼이나 Esc 로 한다. RowActionSheet 는 트랩 대상 selector 가 넓어진다(select·textarea·tabindex 포함). DrillPanel 은 window `stopPropagation` 방식에서 스택 판정 방식으로 바뀐다. 시트 안 차트의 Esc(ChartScrub)는 차트가 이벤트를 먼저 소비하면 그대로 두는 규칙(`defaultPrevented` 존중)을 따른다.
- **뒤로가기 동작 변경(OVL-4·OVL-8)**: 시트가 열린 상태의 뒤로가기는 지금은 페이지를 떠나지만, 변경 후에는 시트만 닫는다. 시트를 열 때마다 history 항목이 하나 생긴다. 드릴 스택은 현행 push 동작 그대로이고, 딥링크 진입 후 닫기만 페이지를 떠나지 않도록 바뀐다.
- **알려진 한계(결정으로 수용)**: `inert` 를 쓰지 않으므로(OVL-3) 일부 스크린리더 가상 커서가 배경에 접근할 수 있다. `overflow:hidden` 만 쓰므로(OVL-6) iOS Safari 에서 배경 스크롤이 샐 수 있다.
- **URL 계약 불변**: `?sheet=sync` 와 드릴 스택의 쿼리 형식은 바뀌지 않는다.
- **MenuDrawer**: 이 설계의 수정은 action 부착(§3)만. 드로어 내용은 대부분 v1 라우트 링크(`data-sveltekit-reload`)와 "v1로 돌아가기"(`ui_default` 전환)라 v1 라우트 일몰(V1-2) 시 구성·존속이 바뀐다. 일몰 전 이 링크 대상 v1 화면이 깨지는 것은 감수(V1-13) — 이 설계는 v1 링크를 보호·우회하지 않는다. 예외로 "CSV 내보내기" 링크는 V1-11 결정에 따라 v1 `/activities/export.csv` 대신 v2 내보내기(EXP) 화면으로 연결된다(`bundles/data-export.md` §3 소관 — 이 설계의 변경 아님). `/switch-user` 링크의 v2 화면 교체·production 숨김(판정은 기존 설정 키, V1-12)은 `server-input-origin-validation.md` §2.5 소관이다. 그 밖의 일몰 후 드로어 내용은 BACKLOG `MENUDRAWER-POST-V1`(V1-5) 소관이며 이 설계는 다루지 않는다. 링크 교체는 드로어의 포커스 트랩·Esc·복귀 동작에 영향이 없다.

## 6. 대안 비교 (기록용 — A안 채택)

| | A. 순수 코어 + action (채택) | B. 공용 `<Modal>` 래퍼 컴포넌트 (snippet) |
|---|---|---|
| 적용 방식 | 기존 마크업에 `use:modal` 한 줄 | 각 시트를 래퍼로 감싸도록 구조 변경 |
| 레이아웃 다양성 | 드로어(좌측)·하단 시트·팝오버·인라인을 그대로 유지 | 래퍼가 위치·배경까지 담당하면 변형 prop 이 늘어남 |
| 테스트 | 코어를 node --test 로 단위 검증 가능 | DOM 테스트 환경이 없으면 검증이 어려움 |
| 재발 방지 | 부착을 잊을 수 있음 → 2.5 프론트 정적 검사로 보완 | 래퍼를 쓰면 자동으로 보장 |
| 변경 규모 | 작음 (순증 ~25줄) | 중간 (9개 파일 구조 변경) |

외부 라이브러리(focus-trap 계열, headless UI 키트)는 도입하지 않는다(OVL-5).

## 7. 결정됨 (2026-10-11)

- **OVL-1 인라인 확인의 역할**: (b) `role="group"` + `aria-live` 알림. 근거: 비모달 블록에 alertdialog 를 다는 모호함 제거(2.3). **수정(2026-10-12, A11Y-L1 에이전트 위임 결정): `aria-live` 를 빼고 group + `aria-labelledby` + "취소" 포커스(OVL-2)만 쓴다** — 포커스 이동이 확인 문구를 이미 읽게 해 live 와 이중 낭독이 생기기 때문(`accessibility-layout.md` §5). decisions-table OVL-1 행은 원문이며 수정 기록은 메인이 한다.
- **OVL-2 파괴적 확인의 처음 포커스**: "취소". 근거: 실수로 해제될 위험을 낮춤(2.3).
- **OVL-3 배경 비활성 방식**: 포커스 트랩 + `aria-modal`, `inert` 미사용. 근거: DOM 이동에 따른 스타일·컨텍스트 회귀 회피(2.2, 5절 한계 수용).
- **OVL-4 뒤로가기로 닫기**: 시트 열 때 history push, 뒤로가기는 시트만 닫음. 근거: 모바일 기대 동작(2.4). 원문의 "드릴 스택 정책 정렬은 구현 시"는 OVL-8 로 확정됐다.
- **OVL-5 구현 방식**: 자체 `use:modal` action(A안). 근거: 기존 마크업 유지·순수 코어 단위 테스트 가능, 의존성 추가 없음.
- **OVL-6 스크롤 잠금 방식**: `overflow:hidden`. 근거: 닫을 때 스크롤 점프 없음, iOS 누수는 수용(2.1).
- **OVL-7 재발 방지 검사**: 프론트 테스트(접근성 정적 스캔과 같은 곳)에 `role=dialog` ↔ `use:modal` 검사 추가(2.5).
- **OVL-8 드릴 스택**: (a) history push(뒤로가기로 한 단계씩 닫기). 현행 `drillStack.ts` 동작을 유지하고 딥링크 닫기 규칙만 추가(2.4).
- **ERR-7**: E-23(DemoBanner Esc)은 오류·재시도 설계에서 빼고 이 문서가 맡는다(대상 증상·4절 7단계).

## 8. 범위 밖 메모

- E-23 은 DemoBanner Esc·포커스 동작만 다룬다. 배너 자체의 UX 문제는 다루지 않는다.
- S-11 토스트 알림·5초 확인은 이 패턴 밖이다(`accessibility-common.md` 2.2 Toast, 알림 경로는 `accessibility-layout.md` §2.3 LiveRegion `announce`).
- ActivityMoreMenu(`role="menu"`)의 메뉴 키보드 패턴(화살표 이동)은 별도 항목으로 다뤄야 한다.

## 9. 동기화 중 발견한 충돌/확인 필요

- 해소(OVL-8, 2026-10-12): 드릴 스택은 history push(§2.4). 딥링크 닫기 규칙을 함께 정했다.
- 해소(A11Y-15·A11Y-L1, 2026-10-12): OVL-1 의 group+live 와 OVL-2 "취소" 포커스의 이중 낭독은 live 제거로 해소(§2.3). 실기기 1회 낭독 확인은 `accessibility-layout.md` §4 체크리스트에 있다.
- OVL-7 검사 위치 `tests/a11yStatic.test.mjs` 는 `accessibility-common.md` 의 신규 파일이다. 두 설계의 구현 순서에 따라 먼저 만드는 쪽이 파일을 생성한다. group 안 live 금지 검사는 `accessibility-layout.md` 의 `a11yLayout.test.mjs` (g)가 맡는다.
- 해소(V1-5): 일몰 후 MenuDrawer 내용 정의는 BACKLOG `MENUDRAWER-POST-V1` 별도 항목(§5).
- 해소(V1-11): "CSV 내보내기" 링크는 v2 내보내기(EXP) 화면으로 연결(`bundles/data-export.md` §3, §5).
