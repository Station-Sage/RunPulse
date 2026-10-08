# DESIGN-PLAN-ROW-ACTION — 행 액션 시트 (Phase 7c 계획 조정 마지막 UI)

- 상태: 설계 초안 (2026-10-09). 구현 전 사용자 확인 필요(§9)
- 상위: `DESIGN-PLAN-ADJUSTMENTS.md`(ADR-035, T8), `ux-review-2026-09/31-coach-plan/design.md` §2.4·§3(행 `⋯` 행)·§7.2 조정(S5)·§8 수용 기준
- 백엔드 계약(T8 완료): `POST /api/v1/coach/plan/workouts/<id>/action` `{op, pct?, reason?, via?}` → 201 `{adjustment, compliance, week_planned_km{before,after}}`. 되돌리기 `POST /coach/plan/adjustments/<id>/revert`. 당일만.
- 범위 밖: 다른 날로 옮기기(move, 409 UNSUPPORTED), replan(S6), Coach 제안 카드(S8). 31 §3의 5개 항목 중 v1은 **줄이기·휴식·건너뛰기·Coach에게 묻기** 4개만 노출한다.

---

## 1. 사용자 시나리오

- **아침, 계획 화면**: "오늘 10km 템포인데 어제 야근으로 4시간 잤다. 줄이고 싶다." → 오늘 행 `⋯` → `거리 줄이기 −40%` → 적용. 3탭.
- **점심, Today**: "저녁 회식이 잡혔다." → 다음 세션 카드 `바꾸기` → `건너뛰기` + 사유 `일정` → 적용.
- **목요일 행을 미리 보는 월요일**: "목요일 인터벌이 부담된다." → 목 행 `⋯` → "당일 아침에 바꿀 수 있어요" 안내 + `Coach에게 묻기`. 미리 바꾸지 못하게 하는 이유를 한 줄로 설명한다(조정은 그날 컨디션을 보고 판단, R8).

첫 3초의 느낌: "내 계획을 내가 바꿀 수 있고, 바꾼 결과가 주간에 어떤 영향을 주는지 바로 보인다. 벌점은 없다."

## 2. 진입점

| 화면 | 위치 | 표시 조건 | via |
|---|---|---|---|
| 계획 상세 `/coach/plan/:id` | 주간 행 오른쪽 끝 `⋯` 버튼(44×44, 아이콘 16px) + 행 길게 누르기 500ms | 아래 행 상태표 | `plan` |
| 세션 상세 `/session/:date` | 처방 블록 아래 보조 버튼 `이 세션 바꾸기` | 오늘·미완료·rest 아님 | `session` |
| Today `NextSessionCard` | 다음 세션 줄 오른쪽 텍스트 버튼 `바꾸기` | 다음 세션이 오늘이고 미완료 | `today` |

행 상태별 처리(계획 상세, 날짜는 로컬 `today`, 상태는 서버 `week.days`·행 필드만 사용):

| 행 | `⋯` | 시트 내용 |
|---|---|---|
| 오늘 · 미완료 · 거리 있음 | 표시 | 전체 시트(§3) |
| 오늘 · 미완료 · 거리 없음(시간 처방) | 표시 | 줄이기 비활성 "거리가 정해지지 않은 세션이에요", 휴식·건너뛰기 가능 |
| 오늘 · 휴식(원래 rest) | 숨김 | — |
| 오늘 · 사용자 조정 적용 중 | 표시 | 현재 조정 요약 + `되돌리기` + 다른 op로 바꾸기(§6) |
| 오늘 · 완료(`completed` 또는 `matched_activity_id`) | 숨김 | — (완료 뒤 계획을 바꾸면 이행률 조작이 된다) |
| 오늘 · 대체됨(`superseded`, 반투명 행) | 숨김 | — |
| 미래 | 표시(흐린 색 `text-fg-muted`) | 잠금 안내 시트(§3.4) |
| 과거 | 숨김 | — (되돌릴 것도 바꿀 것도 없다) |

- 행 전체가 지금 `<a>`이므로 `⋯`는 `<a>` 밖의 형제 `<button>`으로 둔다(중첩 상호작용 금지). 행 레이아웃은 `[요일][본문 a.flex-1][상태][⋯]`.
- 길게 누르기는 보조 제스처다. 접근 가능한 기본 경로는 `⋯` 버튼이다. 길게 누르기 후 링크 이동이 일어나지 않도록 `click`을 막는다.

## 3. 시트 구성

모바일(<1024px) 하단 시트, 데스크톱 `⋯` 앵커 팝오버(폭 320px). 기존 `coach/ScopeSheet.svelte`·`EngineSheet.svelte`의 시트 골격(dialog, Esc, 바깥 탭 닫힘)을 따른다. URL `?sheet=row-<workoutId>`(push, 뒤로가기 = 닫기).

### 3.1 오늘 세션 — 기본(390px)

```
┌───────────────────────────────────────────┐
│ ───                                       │  핸들
│ 오늘 템포 10.0km 바꾸기                      │  제목(h2)
│ 바꾼 내용은 오늘 안에 되돌릴 수 있어요          │  보조 1줄
├───────────────────────────────────────────┤
│ ○ 거리 줄이기                               │  radio 행 56px
│    [−20% 8.0km] [−40% 6.0km] [다른 비율]    │  선택 시 펼침, 칩 44px
│ ○ 휴식으로 바꾸기                            │
│    회복을 위해 오늘은 쉬어요                    │
│ ○ 건너뛰기                                  │
│    오늘은 뛰지 못해요                          │
├───────────────────────────────────────────┤
│ 이유 (선택)  [피곤해요] [통증이 있어요] [일정]   │  칩 44px, 단일 선택·재탭 해제
├───────────────────────────────────────────┤
│ 이번 주 계획 57.8km → 53.8km                  │  미리보기(op 선택 후)
│ [Coach에게 묻기 ›]          [적용]           │  적용 = 주 버튼 44px
└───────────────────────────────────────────┘
```

- 탭 수: `⋯`(1) → op 또는 비율 칩(2) → `적용`(3). 비율 칩을 누르면 `거리 줄이기`가 자동 선택된다. 사유는 선택이라 탭 수에 넣지 않는다(31 §8 "3탭 이내").
- `적용`은 op가 선택되기 전 비활성이고 버튼 위에 `바꿀 방법을 고르세요`를 상시 표시한다(비활성 사유 숨김 금지).
- 미리보기 km는 프론트 계산: `after = round(km × (1 − pct/100), 1)`(백엔드 `_user_after`와 같은 식), 주간 after = 현재 주 계획 합 − (before − after). 휴식·건너뛰기는 그 세션 km 전부를 뺀다. 서버 응답의 `week_planned_km`가 최종 값이며 토스트는 서버 값을 쓴다.
- 기본 선택 없음. 실수 적용을 막고 "의미 먼저"를 위해 각 op 아래 한 줄 설명을 둔다.

### 3.2 비율

| 칩 | pct | 비고 |
|---|---|---|
| `−20%` | 20 | 31 §3 프리셋 |
| `−40%` | 40 | 31 §3 프리셋 |
| `다른 비율` | 10~90, 10 단위 스테퍼 `[−] 30% [+]` | API는 1~99 허용, UI는 10 단위로 제한 |

각 칩에 결과 km를 함께 적는다(`−20% 8.0km`). 결과가 3km 미만이면 칩 아래 `3km 미만은 휴식이 나을 수 있어요` 안내(차단 아님).

### 3.3 휴식 vs 건너뛰기

백엔드에서는 둘 다 `workout_type=rest`가 되어 이행률 분모에서 빠진다(D9). 구분은 **기록의 의미**다.
- 휴식으로 바꾸기: 의도적 회복. 행 배지 `휴식으로 바꿈`.
- 건너뛰기: 외부 사정. 행 배지 `건너뜀 · 일정`(사유가 있으면 붙임).
- 사유 칩은 세 op 모두에 붙일 수 있다. 건너뛰기를 고르면 사유 줄을 강조(테두리)하지만 필수는 아니다.

사유 → API: `피곤해요`=fatigue, `통증이 있어요`=injury, `일정`=schedule.

### 3.4 미래 행 — 잠금 안내 시트

```
│ 목 인터벌 8.5km                               │
│ (lock) 당일 아침에 바꿀 수 있어요                │  Icon lock + 문구(색만으로 전달 금지)
│ 그날 컨디션(HRV·수면·부하)을 보고 코치가 먼저       │
│ 제안하고, 직접 줄이거나 쉴 수도 있어요.             │
│ [Coach에게 묻기 ›]                 [닫기]       │
```
op 목록은 렌더하지 않는다(비활성 목록을 늘어놓지 않는다). `Coach에게 묻기`는 `/coach/new?ctx=plan_session:<workoutId>&from=…`(31 §3).

### 3.5 Coach에게 묻기

모든 시트 하단 보조 링크. 사유 `통증이 있어요`가 적용된 직후에는 결과 토스트 대신 시트 안에 `통증이 계속되면 Coach와 상의해 보세요 ›`를 2초 강조한다(§4 참조, 의학 판단은 하지 않는다).

## 4. 확인·결과 피드백

`적용` 탭 → 버튼 `적용 중…`(시트 유지, 이중 탭 차단) → 201 →
1. 시트 닫힘, 포커스는 그 행의 `⋯`로 복귀.
2. 화면 `invalidateAll()`(AdjustmentCard와 같은 규칙, 전역 스토어 없음). 행·이행률·주간 km가 서버 값으로 갱신.
3. 토스트(§C5, 5s, `role=status`) + `[되돌리기]`.

| op | 토스트 문구 (의미 먼저, 숫자는 뒤) |
|---|---|
| reduce | `오늘 8.0km로 줄였어요 · 이번 주 57.8→55.8km` |
| rest | `오늘은 쉬어요 · 이번 주 57.8→47.8km` |
| skip | `오늘 세션을 건너뛰었어요 · 이번 주 57.8→47.8km` |
| 토스트 되돌리기 성공 | `원래 계획으로 돌렸어요` (3s, 되돌리기 없음) |

- `week_planned_km.before == after` 또는 null이면 주간 부분을 생략한다.
- 이행률은 문구에 넣지 않는다. 헤더 ComplianceTriple이 바로 바뀌는 것으로 충분하다(31 §8). 휴식·건너뛰기 후 세션 분모가 1 줄어드는 점은 Level 2(`x.compliance` 시트 분모 규칙 1줄)에서 설명한다.
- 토스트가 사라진 뒤 되돌리기 경로: 행 배지 줄의 `되돌리기`(§5) 또는 `⋯` 시트의 현재 조정 요약(§6). 당일 안에서만.

## 5. 행 표시 (적용 후)

오버레이 응답의 행 필드 `adjusted`, `adjustment{id, source, op, decided_at}`, `original`을 쓴다(현재 `PlannedWorkout` 타입에 없음 → 추가).

```
│ 수 │ 템포 8.0km  5:05–5:20            직접 조정 ⋯ │
│    │ 원래 10.0km · 9:12 [되돌리기]                  │  하위 줄 12px, 되돌리기 44px 터치 영역
│ 수 │ 휴식으로 바꿈 · 피곤해요              직접 조정 ⋯ │
│    │ 원래 템포 10.0km · 9:12 [되돌리기]             │
```
- 배지 문구: source=user `직접 조정`, source=crs `코치 조정`. 색은 `text-fg-secondary`(경고색 쓰지 않음 — 벌점 아님).
- `[되돌리기]`는 오늘 행에만. 지난 날은 `원래 10.0km` 줄만 남긴다.
- 시간은 `decided_at`을 로컬 HH:MM.

## 6. 기존 AdjustmentCard(코치 조정, source=crs)와의 상호작용

현재 백엔드 사실(코드 확인):
- `create_user_adjustment`는 같은 source(user)의 live 조정만 reverted 처리한다. crs 조정은 그대로 둔다.
- `get_day_adjustment`(`_live`)는 crs만 본다 → AdjustmentCard는 user 조정을 모른다.
- 오버레이 `live_adjustments`는 한 workout에 여럿이면 최신 id가 이긴다. user의 `before`는 **원본** 행이다. 따라서 crs `인터벌→이지` 수락 후 user `−20%`를 하면 결과가 `인터벌 6.8km`가 되어 코치 강도 하향이 사라진다. 카드는 계속 "조정 적용됨(인터벌→이지)"을 보여 화면이 서로 어긋난다.

설계 규칙(§9 결정 1의 추천안 기준):

| 오늘 crs 상태 | 시트 상단 | op 동작 | 적용 후 AdjustmentCard |
|---|---|---|---|
| none·future·declined·undone·expired·stale | 없음 | 그대로 | 변화 없음 |
| proposed | 안내 `코치 제안: 인터벌 → 이지 · 직접 바꾸면 이 제안은 닫혀요` + `[제안 보기 ›]`(시트 닫고 카드로 스크롤) | 적용 시 제안은 거절 처리(B1) | 1줄 `직접 조정으로 대신했어요` |
| accepted | 안내 `코치 조정(이지)이 적용 중이에요 · 직접 바꾸면 이것으로 대체돼요` | 줄이기 기준 = **현재 유효 계획**(이지 8.5km) (B2) | 1줄 `직접 조정으로 대체됨` |

- 같은 날 user 조정이 있으면 카드 슬롯(계획 상단·세션·Today)은 crs 카드 대신 **UserAdjustmentLine** 1줄을 보여 준다: `오늘 직접 조정함 · 8.0km로 줄임 · 9:12 [되돌리기]`. 진실은 하나: "오늘 유효한 조정"은 최신 accepted 하나다.
- 사용자 조정 되돌리기 후: 원본 계획으로 돌아간다. 거절 처리된 crs 제안은 다시 뜨지 않는다(`ensure_proposal`은 reverted가 있으면 새 제안 안 만듦). 카드 문구는 `조정을 거절했어요 · 원래 계획대로 진행해요`가 아니라 `원래 계획대로 진행해요`로 줄인다(adjustmentView `declined` 문구가 user 경유일 때 오해 소지 → `decided_via`/대체 여부로 분기, B3).
- 이미 user 조정이 있는 행의 시트: 상단에 `현재: 8.0km로 줄임 · 9:12 [되돌리기]`, 아래 op 목록은 그대로(다른 op 적용 = 기존 user 조정 대체, 백엔드가 이미 처리). 현재 op·비율은 선택된 상태로 연다.
- Today `NextSessionCard`는 `workout_type !== 'rest'`인 행만 다음 세션으로 고른다. 오늘을 휴식·건너뛰기로 바꾸면 오늘이 카드에서 사라지고 내일 세션이 뜬다. 카드 상단에 UserAdjustmentLine `오늘은 쉬기로 했어요 · 9:12 [되돌리기]`를 둬서 되돌리기 경로를 잃지 않게 한다.

## 7. 오류·잠금 문구

시트가 열린 상태에서 오류가 나면 시트를 닫지 않고 `적용` 위에 `role=alert` 한 줄. 선택값은 보존한다(§C5).

| 응답 | 조건 | 문구 | 후속 |
|---|---|---|---|
| 400 BAD_REQUEST | pct 범위, 거리 없음 | 서버 message 그대로(한국어 보장됨: `거리가 없는 세션은 줄일 수 없어요` 등) | 시트 유지 |
| 404 NOT_FOUND | 행 삭제(재생성) | `계획이 바뀌어 이 세션을 찾을 수 없어요` | 2s 후 시트 닫고 `invalidateAll` |
| 409 LOCKED | 자정을 넘김, 탭이 오래 열려 있음 | `오늘 세션만 바꿀 수 있어요 · 날짜가 바뀌어 화면을 새로 고쳤어요` | `invalidateAll`, 시트는 §3.4 잠금 형태로 전환 |
| 409 UNSUPPORTED | (UI에서 move 미노출, 방어용) | `아직 지원하지 않는 변경이에요` | 시트 유지 |
| 409 기타 | 상태 경합 | `다른 곳에서 상태가 바뀌어 최신 내용으로 갱신했어요`(AdjustmentCard와 동일) | `invalidateAll` |
| 503 | DB 없음 | `데이터를 불러올 수 없어요 · 잠시 후 다시 시도해 주세요` | 시트 유지 |
| 네트워크 | — | `처리하지 못했어요 · 잠시 후 다시 시도해 주세요` | 시트 유지, `적용` 재활성 |
| 되돌리기 409 LOCKED | 날이 지남 | `지난 날의 조정은 되돌릴 수 없어요` | 토스트 자리 오류 3s, 되돌리기 버튼 제거 |

## 8. 접근성

- 시트: `role="dialog"` `aria-modal="true"` `aria-labelledby`=제목. 열릴 때 포커스는 첫 radio, 닫힐 때 호출한 `⋯`(또는 `바꾸기`)로 복귀. 포커스 트랩, Esc 닫힘.
- op 선택은 `role="radiogroup"`(aria-label `바꿀 방법`), 비율·사유 칩도 각각 radiogroup(`aria-checked`). 화살표 키 이동. 사유는 재탭 해제가 가능하므로 "선택 안 함"을 키보드로도 고를 수 있게 `Space` 토글.
- `⋯` 버튼: `aria-label="수요일 템포 10.0km 바꾸기"`, `aria-haspopup="dialog"`, `aria-expanded`. 미래 행은 `aria-label="목요일 인터벌 8.5km · 당일에 바꿀 수 있어요"`.
- 비활성 op: `aria-disabled="true"` + 사유 문구를 `aria-describedby`로 연결(`disabled` 속성은 포커스를 막으므로 쓰지 않음).
- 미리보기 km 변화는 `aria-live="polite"`. 토스트는 기존 `role=status`.
- 터치 대상 44px 이상, 핸들은 장식(`aria-hidden`). `prefers-reduced-motion`이면 시트 슬라이드 없이 페이드.
- 잠금은 아이콘 + 문구로 전달(색만 쓰지 않음).

## 9. 결정 필요 (백엔드 영향은 system-architect 확인)

1. **결정 필요 — crs 조정과 user 조정이 겹칠 때.** 추천: (B1) user action이 같은 workout·날짜의 live crs 조정을 함께 reverted 처리하고 (B2) `reduce` 기준을 오버레이된 유효 계획(crs 수락분 반영)으로 한다. 이유: §6의 "강도 하향 소실"과 카드·행 불일치를 서버 한 곳에서 막는다. 대안(UI만): crs accepted일 때 줄이기 비활성 `코치 조정을 먼저 되돌린 뒤 줄일 수 있어요` — 탭 수가 늘고 의도가 반대로 전달된다.
2. **결정 필요 — `GET /coach/plan/adjustment`가 user 조정도 반환할지.** 추천: 응답에 `user_adjustment`(오늘 live user 조정) 필드를 추가해 Today·세션·계획이 같은 UserAdjustmentLine을 그린다. 대안: 각 화면이 오버레이 행 필드(`adjustment.source='user'`)로 판단 — Today는 오늘 행이 rest가 되면 NextSessionCard에서 빠져 정보를 잃는다.
3. **결정 필요 — 건너뛰기의 이행률 처리.** 현재 휴식과 같이 분모에서 제외. 추천: v1 유지(벌점 없음 원칙, D9와 일관). 이력(`op=skip`, 사유)은 남으므로 주간 회고·Coach 컨텍스트에서 "이번 주 2회 건너뜀"으로 별도 표시 가능(후속).
4. **결정 필요 — move 노출.** 추천: v1에서 메뉴에 넣지 않는다(비활성 항목·"준비 중" 미노출). S6 이후 추가.

## 10. 컴포넌트 분해

| 파일 | 종류 | 역할 |
|---|---|---|
| `lib/rowActionView.ts` | 신규, 순수 | `rowActionMode(w, day, today)`→`'full'\|'locked'\|'hidden'`, `opAvailability(w, crsState)`, `reducePreview(km, pct)`, `weekPreview(weekKm, w, op, pct)`, `toastText(op, resp)`, `actionErrorText(err)`, `reasonLabel(key)`. 판정 규칙은 §2 표 그대로 |
| `lib/components/plan/RowActionSheet.svelte` | 신규 | props `{workout, mode, crs?: TodaysAdjustment, weekPlannedKm, via, onApplied(resp), onClose}`. 시트 골격 + op/비율/사유 radiogroup + 미리보기 + 오류. API 호출은 내부, 성공 시 `onApplied` |
| `lib/components/plan/UserAdjustmentLine.svelte` | 신규 | `{adjustment, original, via, onChange}` 1줄 요약 + 되돌리기. 행 하위 줄·카드 슬롯·Today 공용 |
| `lib/components/plan/RowActionButton.svelte` | 신규(선택) | `⋯` 버튼 + 길게 누르기 액션. 계획 행 전용이면 페이지에 인라인 |
| `lib/adjustmentView.ts` | 변경 | `userAdjustmentSummary(adj, original)`, user 대체 시 `declined` 문구 분기 |
| `lib/api/plan.ts` | 변경 | `workoutAction(id, {op, pct?, reason?, via})`: `Promise<WorkoutActionResult>` |
| `lib/types/index.ts` | 변경 | `PlannedWorkout`에 `adjusted?`, `adjustment?{id,source,op,decided_at}`, `original?`. `WorkoutActionResult` |
| `routes/coach/plan/[id]/+page.svelte` | 변경 | 행에 `⋯`(a 밖 형제), `?sheet=row-<id>` 동기화, 시트·Toast 배치, 행 배지·하위 줄. 212줄 → 300줄 초과 시 주간 목록을 `PlanWeekList.svelte`로 분리 |
| `routes/coach/plan/[id]/session/[date]/+page.svelte` | 변경 | `이 세션 바꾸기` 버튼 + 시트 + Toast |
| `lib/components/NextSessionCard.svelte` | 변경 | `바꾸기` 버튼, 오늘 user 조정 시 UserAdjustmentLine |

토스트 되돌리기는 응답의 `adjustment.id`로 `revertAdjustment(id, via)` 호출 후 `invalidateAll()`.

## 11. 테스트 항목

`frontend/tests/rowActionView.test.mjs`(순수 함수):
- [ ] `rowActionMode`: 오늘·미완료=full, 오늘·완료=hidden, 오늘·matched=hidden, superseded=hidden, 원래 rest=hidden, 미래=locked, 과거=hidden
- [ ] 거리 null이면 reduce 비활성 + 사유 문구
- [ ] `reducePreview(10, 20)`=8.0, `(8.5, 40)`=5.1(백엔드 `round(km*(1-p/100),1)`과 동일)
- [ ] `weekPreview` rest/skip은 세션 km 전부 차감, reduce는 차이만
- [ ] `toastText` 3 op 문구, before==after·null이면 주간 부분 생략
- [ ] `actionErrorText`: 400 서버 문구 그대로, 404·409 LOCKED·UNSUPPORTED·기타·503·네트워크 문구
- [ ] crs proposed/accepted 상태별 상단 안내 문구

`frontend/tests/adjustmentView.test.mjs`(추가): `userAdjustmentSummary` reduce/rest/skip+사유, user 대체 시 crs 문구 분기.

컴포넌트·스모크(브라우저, 390px):
- [ ] 오늘 행 `⋯` → `−20%` → `적용` = 3탭, 토스트 문구·서버 주간 km 일치, ComplianceTriple 즉시 갱신
- [ ] 토스트 `되돌리기` → 행 원복, 5s 후 행 하위 줄 `되돌리기`로도 원복
- [ ] 휴식 적용 후 Today: 오늘 UserAdjustmentLine 표시, 다음 세션은 내일
- [ ] 미래 행 `⋯` → 잠금 시트, op 목록 없음, `Coach에게 묻기` 링크 ctx 포함
- [ ] 완료된 오늘 행·과거 행에 `⋯` 없음
- [ ] `?sheet=row-<id>` 새로고침 시 시트 복원, 뒤로가기 = 닫기
- [ ] 키보드만으로 열기→선택→적용→포커스 `⋯` 복귀, Esc 닫힘(axe 위반 0)
- [ ] 시계 23:59 → 00:01 경과 후 적용 = LOCKED 문구 + 잠금 시트 전환
- [ ] (결정 1 반영 시) crs accepted 상태에서 −20% → 결과 유형 이지 유지, 카드 1줄 `직접 조정으로 대체됨`

수용 기준(31 §8 연결): 행 액션 3탭 이내, 적용 후 5s 토스트 또는 행 하위 줄에서 당일 되돌리기, 결정 즉시 이행률 갱신.
