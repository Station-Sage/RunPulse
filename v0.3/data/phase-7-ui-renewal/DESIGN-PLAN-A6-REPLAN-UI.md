# DESIGN — 안전한 재계획 UI (T9) — REPLAN 배너 링크 활성화

상태: 초안(사용자 결정 대기) · 2026-10-09 · 작성: product-architect
상위: `DESIGN-PLAN-A6-REPLAN-SAFE.md` §2.2·2.4~2.7, D1(다음 월요일)·D4(미리보기 필수)·D5(b 외부 안내)·D6(마지막 1건 되돌리기)
범위: 배너 CTA → 미리보기 → 적용 → 되돌리기 화면 흐름, 문구, 순수 함수·파일 분할. API·스키마는 범위 밖(필요한 보강은 §10에 질문으로만 남김).

## 0. 설계 요약

| 항목 | 결정(제안) |
|---|---|
| 화면 | **전용 페이지** `/coach/plan/replan` (바텀시트 아님) |
| 입력 | 접힌 "직접 입력" 3칸(주간 km·롱런 km·목표 기록), 비우면 이력 기반 |
| 비교 | Level 0 한 문장 + 주별 `전 → 후 km` 목록(처음 4주, 나머지 접기) |
| 확인 | 미리보기 화면 자체가 확인 단계. 별도 모달 없음. 입력을 바꾸면 미리보기를 다시 받아야 적용 가능 |
| 되돌리기 | 토스트가 아니라 **결과 화면의 고정 버튼**(anchor 전날까지 유효) |
| 플래그 | `REPLAN_LINK_ENABLED` 삭제, `replanHref`가 `/coach/plan/replan`을 반환 |

## 1. 사용자 시나리오

- 맥락: 2주간 세션을 절반도 못 했다(REPLAN advisory). 오늘 세션을 줄이려고 행 액션 시트를 열었더니 시트 상단에 "계획을 지금 흐름에 맞추면…" 띠가 보인다.
- 기대: "남은 기간을 지금 내 상태에 맞게 다시 짜 주되, 이미 한 기록과 이번 주는 건드리지 마."
- 두려움: "누르면 지금까지 기록·이행률이 날아가나?", "워치에 보낸 운동은 어떻게 되지?" → 첫 3초에 **"이번 주와 지난 기록은 그대로"**와 **"다음 주 월요일부터"**가 보여야 한다.

## 2. 화면 선택 — 페이지 (390px 우선)

바텀시트를 쓰지 않는 이유:
1. 배너가 이미 `RowActionSheet`(바텀시트) 안에 있다. 시트 위 시트는 포커스 트랩·Esc·뒤로가기가 겹친다.
2. 내용이 길다(대회까지 최대 20주 안팎 목록 + 입력 + 안내). `max-h-[85vh]` 시트에서 스크롤 2중.
3. 적용 후 되돌리기를 anchor 전날까지 유지하려면 새로고침·재진입 가능한 URL이 필요하다.
4. 뒤로가기 시 원래 계획 화면의 `?sheet=row-<id>`가 복원되어 행 시트로 자연스럽게 돌아간다(기존 딥링크 규약 재사용).

레이아웃(390px, 위→아래):

```
‹ 계획                                  (뒤로: history.back, 없으면 계획 화면)
남은 일정 다시 맞추기                    text-base font-semibold
┌ Level 0 카드 (bg-surface-2, rounded-lg p-3) ─────────────┐
│ 10/13(월)부터 대회 주까지 9주를 다시 짜요.                  │
│ 첫 주 52 → 38km로 낮춰 시작하고, 가장 많은 주는 64 → 58km.  │
│ 이번 주 남은 세션과 지난 기록은 그대로예요.   text-xs muted │
└──────────────────────────────────────────────────────┘
직접 입력 ▸        (접힘. 펼치면 3칸 + [다시 계산])
주별 거리           10/13 주   52 → 38km   −14
                    10/20 주   55 → 41km   −14
                    …  처음 4주 + [나머지 5주 보기]
                    11/30 주 · 대회 주  30 → 30km   =
안내(조건부)        보존·외부·건너뛴 날짜 (§5)
어떻게 계산했나요 ▸  (Level 2)
─ sticky 하단 바 (bottom-nav 위, bg-surface-1 border-t) ─
[ 10/13부터 적용 ]  [ 취소 ]           h-11, 기존 시트 버튼과 동일 클래스
```

데스크톱(lg): 같은 페이지, `max-w-xl` 중앙 정렬, 하단 바는 sticky 해제하고 목록 끝에 둔다.

## 3. 정보 계층

| Level | 내용 | 근거 데이터 |
|---|---|---|
| 0 | 적용 시작일·주 수·첫 주 변화·최대 주 변화 한 문장 + "이번 주·지난 기록 그대로" | `anchor_monday`, `before[]`, `after[]` |
| 1 | 주별 `전 → 후 km`와 차이, 대회 주 표시, 보존/외부 안내 | `before[]`/`after[]` 병합, `preserved[]`, `external[]`, `skipped_dates[]` |
| 2 | "어떻게 계산했나요": 시작 주간 거리와 출처(최근 기록/입력값), 바뀌는 세션 수, 범위(anchor~대회 주 일요일), 지난 계획·이행률·N주차는 바뀌지 않는다는 설명 | `start_km`, `start_long_km`, `target_time_sec`, `deleted_count` |

Level 0 문장 규칙(순수 함수 `replanSummary`):
- 첫 주 차이 |Δ| < 1km → "첫 주는 비슷한 거리로 시작하고", Δ<0 → "낮춰 시작하고", Δ>0 → "올려 시작하고".
- 최대 주(before 최대 vs after 최대)가 같으면 생략.
- before가 비어 있으면(기존 일정 없음) "대회 주까지 9주 일정을 새로 넣어요".

## 4. 입력

> 2026-10-09 재검토: 아래는 구현된 1차안. 이력이 있으면 입력이 사실상 무효라는 코드 근거와 대체안은 **§11**(제안, 결정 대기).

- 기본: 접힘, 빈 값. 페이지 진입 시 빈 입력으로 미리보기를 바로 요청(사용자가 아무것도 안 해도 결과가 보이게).
- 펼친 상태(각 `h-11`, `inputmode="decimal"`, 기존 `input` 클래스 재사용):
  - 최근 주간 거리(km) — placeholder "비우면 최근 기록으로 계산"
  - 최근 가장 긴 러닝(km)
  - 목표 기록 — `h:mm:ss` 또는 `mm:ss`, placeholder는 현재 목표 기록(있으면). 비우면 기존 목표 유지
- 배너 링크의 `recent_weekly_km`(2주 평균)는 **프리필하지 않는다**. 서버 이력 계산(`cold_start_km`)과 값이 달라 "비우면 이력 기반"과 충돌한다.
- 검증(클라이언트, 순수 함수): 빈 값 허용, 숫자·0 초과. 범위 경고(주간 > 200km, 롱런 > 50km, 롱런 > 주간)는 막지 않고 안내만. 오류는 칸 아래 `text-xs text-semantic-red`.
- 입력 변경 → `dirty` 상태. `[다시 계산]` 버튼 활성, **적용 버튼 비활성 + "바꾼 값으로 다시 계산해 주세요"**. 적용되는 값 = 화면에 보이는 미리보기 값을 보장한다(자동 디바운스 재요청은 하지 않음 — 계산 비용·입력 중 깜빡임).
- Level 2에 출처 표시: `start_source` 대신 입력 유무로 판단 — "시작 주간 38km · 최근 기록 기준" / "· 입력한 값 기준".

## 5. 주별 비교와 안내

주별 목록(새 컴포넌트, 표 마크업 `<table>` + `tabular-nums`):
- 행: `MM/DD 주` · `전 → 후km` · 차이(`−14`, `+3`, `=`). 차이는 `text-fg-muted`. **색 의미 없음** — 줄어드는 것이 나쁜 게 아니므로 빨강/초록을 쓰지 않는다.
- 마지막 주는 "· 대회 주" 꼬리표.
- before에만 있는 주(대회 주 이후 잔여 등)·after에만 있는 주는 없는 쪽을 `—`.
- 390px: 처음 4주 + `[나머지 N주 보기]`(버튼, `min-h-11`). 대회 주는 접혀도 항상 마지막에 보인다.
- 롱런·Q 세션 수 비교는 현재 API에 없으므로 넣지 않는다(§10 Q2).

조건부 안내(`ReplanNotices`, `rounded-lg bg-surface-2 p-3 text-xs text-fg-secondary`, 기존 `ReplanBanner` 띠와 같은 모양):

| 조건 | 문구 |
|---|---|
| `external.length > 0` | "Garmin 워치로 보낸 세션 {n}개({10/14, 10/16} 외 {k}개)는 자동으로 지울 수 없어요. 적용 후 Garmin Connect 캘린더에서 그 날짜의 운동을 지워 주세요." |
| `preserved.length > 0` | "기록이 남은 세션 {n}개는 그대로 둬요({MM/DD 세션명}…)." |
| `skipped_dates.length > 0` | "{MM/DD}에는 기존 세션이 남아 있어 새 세션을 넣지 않았어요." |
| 항상(Level 2 안) | "캘린더 구독(ICS)은 자동으로 새 일정으로 바뀌어요." |

- 외부 안내는 미리보기와 결과 화면 **둘 다**에 둔다(적용 전 판단 근거 + 적용 후 할 일).
- 외부 안내가 있을 때 적용 버튼 바로 위에 같은 띠를 한 줄 요약("Garmin 세션 2개는 직접 지워야 해요")으로 반복 — 스크롤로 놓치지 않게. 체크박스 동의는 두지 않는다(새 요소 최소화).
- CalDAV는 `external[]`에 포함되지 않는다. CalDAV 사용자에게 옛 이벤트가 남는지 확인 필요(§10 Q3).

## 6. 적용·되돌리기

적용:
- 버튼 문구 `{MM/DD}부터 적용`. `busy` 동안 비활성 + "적용하고 있어요". 요청 body = 미리보기 때 쓴 입력 + `expect_anchor = preview.anchor_monday`.
- 실패 시 자동 재시도하지 않는다(§7 네트워크 행).

결과 상태(같은 페이지, 화면 전환 없이 상단 카드만 교체):
```
10/13부터 새 일정을 적용했어요.
10/12(일)까지는 되돌릴 수 있어요.
[계획 보기]  [되돌리기]
(외부 안내 띠 — 있으면)
```
- 토스트를 쓰지 않는 이유: 기존 `Toast`는 5초 후 사라진다. 되돌리기 유효 기간은 anchor 전날까지(최대 7일)이고, 여러 주를 바꾸는 결정이라 5초 창은 짧다. 결과 카드의 버튼은 이 페이지에 머무는 동안 유지된다.
- `[계획 보기]` = 계획 화면으로 이동(`invalidateAll` 효과는 페이지 로드로 충족).
- 되돌리기는 확인 없이 실행(원 상태로 복원이라 위험이 낮다). 성공 → "원래 일정으로 돌렸어요." + `[계획 보기]`, 되돌리기 버튼 제거.
- 페이지를 떠난 뒤 되돌리기: 지금 API로는 "마지막 적용 재계획 id"를 다시 얻을 수 없다 → §10 Q1. 결정 전까지는 되돌리기를 결과 화면에서만 제공하고, 결과 문구를 "이 화면에서 {MM/DD}까지 되돌릴 수 있어요"로 바꿔 범위를 사실대로 알린다. 계획 화면에는 노출하지 않는다.

REPLAN_LOCKED(되돌리기 시): 버튼을 지우고 안내 + 선택지 하나 `[다시 미리보기]`(현재 상태 기준으로 새 재계획을 제안). 서버 메시지 3종(마지막 아님/이미 시작/새 행에 이력)은 코드 하나로 오므로 문구를 하나로 묶는다.

## 7. 오류 문구 (사실 + 영향 + 선택지 하나)

해요체, 비난·느낌표 없음. 위치: 미리보기 오류는 Level 0 카드 자리, 적용·되돌리기 오류는 하단 바 위 `role="alert"`.

| 단계 | 코드 | 문구 | 선택지 |
|---|---|---|---|
| 미리보기·적용 | 404 `NO_GOAL` | 대회일이 있는 목표가 없어요. 다시 맞출 일정이 없어서 지금은 쓸 수 없어요. | `[목표 만들기]` → `/coach/plan/new` |
| 미리보기·적용 | 409 `RACE_WEEK` | 이번 주가 대회 주라 다시 짤 남은 주가 없어요. 계획은 그대로예요. | `[계획으로 돌아가기]` (오늘 세션은 행 액션으로 조정) |
| 적용 | 409 `CONFLICT` | 미리보기 뒤에 날짜가 바뀌어 시작 주가 달라졌어요. 아직 바뀐 것은 없어요. | `[미리보기 다시 보기]` (같은 입력으로 재요청) |
| 되돌리기 | 409 `REPLAN_LOCKED` | 새 일정이 이미 시작됐거나 그 뒤에 기록이 생겨서 되돌릴 수 없어요. 지금 일정은 그대로예요. | `[다시 미리보기]` |
| 되돌리기 | 404 `NO_GOAL` | 되돌릴 재계획 기록을 찾지 못했어요. 지금 일정은 그대로예요. | `[계획 보기]` |
| 공통 | 400 `BAD_REQUEST` | (해당 입력칸 아래) 0보다 큰 숫자를 넣어 주세요. | 입력 수정 |
| 공통 | 503 | 데이터를 읽지 못했어요. 계획은 바뀌지 않았어요. | `[다시 시도]` |
| 미리보기 | 네트워크·기타 | 미리보기를 불러오지 못했어요. 계획은 바뀌지 않았어요. | `[다시 시도]` |
| 적용·되돌리기 | 네트워크·기타 | 응답을 받지 못했어요. 반영됐는지 계획 화면에서 확인해 주세요. | `[계획 보기]` — 반영 여부를 모르므로 "다시 시도"를 주지 않는다 |

## 8. 파일 분할 · 순수 함수 (각 300줄 이하)

| 파일 | 역할 | 예상 줄 |
|---|---|---|
| `frontend/src/lib/replanView.ts` (신규) | 아래 순수 함수 | ~170 |
| `frontend/src/lib/replanBanner.ts` (수정) | 플래그 삭제, `replanHref` 단순화 | ~35 |
| `frontend/src/lib/api/plan.ts` (수정) | `previewReplan`, `applyReplan`, `undoReplan` + `ReplanPreview`/`ReplanResult` 타입(`$lib/types`) | 113 → ~140 |
| `frontend/src/routes/coach/plan/replan/+page.svelte` (신규) | 상태 기계(loading·preview·dirty·applying·applied·undone·error), 하단 바 | ~170 |
| `frontend/src/routes/coach/plan/replan/+page.ts` (신규) | 빈 입력 미리보기 로드, 오류를 `data.error`로 | ~30 |
| `frontend/src/lib/components/plan/ReplanInputs.svelte` (신규) | 접힘 입력 3칸 + 다시 계산 | ~80 |
| `frontend/src/lib/components/plan/ReplanWeekTable.svelte` (신규) | 주별 목록 + 접기 | ~60 |
| `frontend/src/lib/components/plan/ReplanNotices.svelte` (신규) | 외부·보존·건너뛴 날짜 띠 | ~45 |

`replanView.ts` 순수 함수(테스트 `frontend/tests/replanView.test.mjs`, 함수마다 ≥1):

| 함수 | 입력 → 출력 | 주요 케이스 |
|---|---|---|
| `mergeWeeks(before, after)` | → `{week_start, label, before, after, delta, isRace}[]` | 한쪽만 있는 주 `null`, 정렬, 마지막 주 isRace |
| `deltaText(d)` | → `'−14'`/`'+3'`/`'='` | \|d\|<0.5 → `=`, 소수 반올림, U+2212 |
| `collapseWeeks(rows, n=4, expanded)` | → `{shown, hiddenCount}` | 대회 주는 항상 shown, n 이하면 hidden 0 |
| `replanSummary(preview)` | → Level 0 문장 | 낮춤/올림/비슷, 최대 주 동일 시 생략, before 비었음 |
| `anchorLabel(anchor)` / `undoUntilLabel(anchor)` | → `'10/13(월)'` / `'10/12(일)'` | 월 경계 |
| `canUndo(anchor, today)` | → boolean | today < anchor만 true |
| `parseReplanInputs(raw)` | → `{params, errors, warnings}` | 빈 값=undefined, 0·음수·문자 오류, 롱런>주간 경고 |
| `parseTargetTime(s)` | → 초 \| null \| 'invalid' | `3:45:00`, `45:30`, 빈 값 |
| `replanQuery(params)` | → 쿼리 문자열 | 빈 값 제외 |
| `canApply(state)` | → boolean | preview 있음·dirty 아님·busy 아님·오류 없음 |
| `externalNotice(ext)` / `preservedNotice(rows)` / `skippedNotice(dates)` | → 문구 \| null | 0건 null, 3건 초과 "외 k개" |
| `replanErrorView(err, phase)` | → `{text, action: 'retry'\|'repreview'\|'newGoal'\|'plan'\|'back'\|null, field?}` | §7 표의 모든 행, phase별 NO_GOAL 차이, 네트워크 적용 실패 = 'plan' |

`replanBanner.test.mjs`: `replanHref`가 goal 정보(`link.race_date`) 있을 때 `/coach/plan/replan`, 없으면 null.

브라우저 스모크(390px, 운영 DB 사본): 배너 → 페이지 진입 → 입력 변경 시 적용 비활성 → 다시 계산 → 적용 → 결과 카드 → 되돌리기 → 계획 화면에서 이번 주 이행률·지난 행 불변 확인. 뒤로가기 시 행 시트 복원. 외부 행이 있는 사본에서 안내 노출.

## 9. `REPLAN_LINK_ENABLED` 대체

- 상수 삭제. 백엔드가 배포됐으므로 플래그 대신 **데이터 조건**으로 노출: `replanHref(base, a)` = `a.link?.race_date ? \`${base}/coach/plan/replan\` : null` (목표 없음이면 링크 숨김 → NO_GOAL 진입 자체를 줄인다).
- 쿼리 프리필 제거(§4 이유). `/coach/plan/new` 로 가던 옛 경로는 배너에서 완전히 끊는다(새 목표 만들기는 계획 없음 화면·목표 화면에만 남음).
- 배너 CTA 문구: "남은 일정 다시 맞추기 ›" (현재 "계획 다시 맞추기"보다 범위가 분명). "이번 주 숨기기"는 유지.
- 배너 `link`의 `distance_km`·`target_time_sec`·`recent_weekly_km`는 프론트에서 더 쓰지 않는다 — `_replan_link` 정리 여부는 system-architect 판단.

## 10. 사용자·아키텍트 확인 필요

| ID | 질문 | 제안 |
|---|---|---|
| Q1 | 페이지를 떠난 뒤(최대 7일) 되돌리기를 어디서 할까 | 계획 화면 헤더에 "10/13부터 새 일정 · 10/12까지 되돌리기" 한 줄. 마지막 applied 재계획 정보를 계획 응답 등에 노출하는 API 보강 필요(system-architect). 보강 전에는 결과 화면 안에서만 |
| Q2 | 주별 롱런·Q 비교 (SAFE §2.4가 약속한 `long/q_before/after`) | Level 1에 "롱런 30→26km" 보조 줄로 넣고 싶음 — API 미포함, 보강 여부 결정 |
| Q3 | CalDAV 푸시 사용자의 옛 이벤트 | `external[]`가 Garmin만 보고함. CalDAV도 남는다면 같은 안내에 포함할지 |
| Q4 | 배너 외 진입점(계획 화면 메뉴 "남은 일정 다시 맞추기") | 이번 T9에선 배너만. advisory 없이도 원하는 사용자가 있으면 다음 단계 |
| Q5 | 적용 후 새 세션의 Garmin 자동 전송 여부 | 동작에 따라 결과 화면에 "새 세션은 {다음 동기화 때} 워치로 보내요" 한 줄 추가 |

## 11. 입력 재검토 — 이력 기반 시작점을 기본으로 (2026-10-09, 구현 완료: Q6 채택·Q7 보류·Q8 미제공, 경계 12km)

사용자 질문: "러닝 기록이 이미 있는데 최근 이력을 입력받을 필요가 있나?"

### 11.1 코드 근거 (`cold_start_km`, `plan_replan_service._start_km`)
재계획은 이력 유무와 상관없이 항상 `cold_start_km(dlabel, km4, avg16, user_km)`를 탄다(`start_load`의 `km4 ≥ 12 → history` 분기를 거치지 않음). 결과:

| 상태 (`km4`=직전 4주 주평균, `avg16`=16주 주평균) | 자동 값 | 주간 거리 입력의 실제 효과 |
|---|---|---|
| A 이력 충분 `km4 ≥ ~11` | `km4` (0.6×avg16 이 더 커도 1.1×km4 상한) | **[km4, 1.1×km4] 로 잘림.** 30km 사용자가 20 입력 → 30, 60 입력 → 33 |
| B 이력 적음 `0 < km4 < ~11` | 12km | **없음**(입력 무관 12km) |
| C 공백(부상·휴식) `km4 = 0, avg16 > 0` | 0.6×avg16 | 그대로 반영(12 이상) |
| D 신규 `km4 = 0, avg16 = 0` | 거리별 기본값(풀 20km) | 그대로 반영 |

- 롱런 입력(`recent_long_km`): 상태와 무관하게 anchor `start_long_km`으로 저장되어 꼬리 일정에 쓰인다(`schedule_for_goal.tail`). **비우면 최근 이력이 아니라 목표 생성 당시의 시작 롱런**을 쓴다 — 공백 후 재계획에서 오래된 값이 남는 문제(아키텍트 Q6).
- 목표 기록: 활성 목표 `goals.target_time_sec`에 이미 있다(`_replan_link`도 보냄). 입력은 꼬리 일정에만 쓰는 override이고 목표 행은 그대로라 "목표를 바꿨나?"가 모호하다.
- 출처 표시 오류: Level 2 "입력한 값 기준"은 입력 유무로 판단하고, `plan_replans.start_source`도 `"user" if user_km else "history"`로 저장한다. A 상태에서 20을 넣어도 실제 30(이력)인데 "입력한 값"으로 보인다 → 투명성 원칙 위반.

### 11.2 권장 UX — "시작점" 카드 + 상태별 입력 노출
Level 0 요약 바로 아래에 항상 보이는 **시작점 카드**(입력이 아니라 근거):

```
어디서 시작하나요
첫 주 30km — 최근 4주 평균 30km 그대로        (A)
첫 주 12km — 최근 4주 평균 8km, 가볍게 다시 쌓아요   (B)
첫 주 24km — 4주 쉬었어요. 쉬기 전 16주 평균 40km의 60%   (C)
첫 주 20km — 기록이 없어 풀코스 기본값으로 시작   (D)
가장 긴 러닝 18km — 최근 6주 최장 (12주 최장 21km의 85%와 비교)
목표 기록 3:45:00 — 지금 목표 그대로           [바꾸기]
```

- A·B: 주간·롱런 입력칸 **노출하지 않음**(효과가 없거나 10% 이내). REPLAN 진입 자체가 "2주 이행 부족"이라 `km4`는 이미 줄어든 실제 수준 = 사용자가 원하는 "지금 내 상태"다.
- C·D: 카드 아래 **"쉬는 동안 다른 운동을 했거나 기록이 빠졌나요? 직접 맞추기 ▸"** 접힘에 주간·롱런 2칸. D는 펼친 채 시작(기본값은 추정이라 사용자 정보가 더 낫다).
- 목표 기록: 입력 칸에서 빼고 카드의 `[바꾸기]`로만(인라인 1칸, placeholder = 현재 목표). 바꾸면 Level 0에 "목표 3:45 → 3:50 기준으로 다시 짜요"를 덧붙여 의미를 분명히 한다.
- Level 2 출처는 서버가 돌려준 실제 출처(`history|avg16|default|user`)로 표시. 입력했지만 이력에 밀렸으면 "입력 20km보다 최근 기록 30km가 커서 기록을 따랐어요".
- 다시 계산·dirty·적용 비활성 규칙(§4)은 그대로.

### 11.3 최소 변경 범위
백엔드 (응답 필드 형태·저장 의미는 system-architect 확정):
- `src/services/plan_replan_service.py` `_start_km` → `(km, src, basis)` 반환. `basis = {km4, avg16, long6, long12}` (`recent_load`, `recent_avg_km`, `recent_long_max`). `_run` 응답에 `start_source`, `basis`, `goal_target_time_sec` 추가, `plan_replans.start_source`에 실제 `src` 저장.
- Q6: 롱런 미입력 시 anchor 기준 이력값(`personalize.start_long_km(long6, long12)`)을 `start_long_km`으로 저장할지(현재 NULL → 목표 생성 당시 값).
- Q7: `schedule_for_goal.tail`이 출처를 항상 `"user"`로 넘겨 rv2에서 `cold_peak_km` 하한이 A 상태에도 적용됨 — 의도인지.
- `routes_plan_adjust._replan_link`의 `recent_weekly_km`(2주 평균, 계산식 다름)는 프론트 미사용 — 정리 여부만 판단.

프런트:
- `frontend/src/lib/types/index.ts` `ReplanPreview`에 `start_source`, `basis`, `goal_target_time_sec`.
- `frontend/src/lib/replanView.ts` 순수 함수 추가: `startState(preview) → 'A'|'B'|'C'|'D'`, `startBasisText(preview)`(카드 문구), `inputFields(state)`(노출 칸). Level 2 출처 문구를 `start_source` 기반으로.
- `frontend/src/lib/components/plan/ReplanInputs.svelte`: `fields`를 prop으로, 목표 칸 분리.
- 신규 `ReplanStartCard.svelte`(시작점 카드 + 목표 [바꾸기]) — `+page.svelte` 300줄 유지.
- `+page.svelte` 127행 출처 문구 교체, 카드 삽입.

### 11.4 테스트
- 백엔드: 상태 A/B/C/D 각각 `start_source`·`basis`·`start_km` 기대값 / A에서 `recent_weekly_km < km4` 입력 시 `start_source='history'`(또는 합의한 값) 저장 / `goal_target_time_sec` = 활성 목표 값 / (Q6 채택 시) 롱런 미입력이면 anchor 이력값 저장.
- 프런트(vitest): `startState` 경계(km4 0·11.9·11·30, avg16 0) / `startBasisText` 4종 문구 / `inputFields` A·B는 빈 배열, C 접힘, D 펼침 / 출처 문구가 입력 유무가 아닌 `start_source`를 따름.
- 브라우저 스모크(390px, 운영 DB 사본): 현재 사용자(A) 진입 시 입력칸 없음·카드 근거 표시 / 4주 활동 제거 사본(C)에서 접힌 조정 노출 / 목표 [바꾸기] → dirty → 다시 계산 → Level 0 문장 변화.

| ID | 질문 | 제안 |
|---|---|---|
| Q6 | 롱런 미입력 시 기준값 | anchor 기준 이력(`start_long_km(long6, long12)`)으로 저장 |
| Q7 | 꼬리 일정 출처 `"user"` 고정 | 실제 출처 전달(A면 `history`) |
| Q8 | A 상태에서 "더 가볍게 시작" 수동 하향 필요? | 지금은 미제공(서버가 `km4` 아래로 못 내림). 필요하면 서버 규칙 변경이 먼저 |
