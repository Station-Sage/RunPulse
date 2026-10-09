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

## 12. 보류 항목 정리 — Q7·Q8·후속 (2026-10-09, system-architect 분석, Q7·Q1 API·link 정리 구현 2026-10-09)

| 항목 | 결론 |
|---|---|
| Q7 꼬리 출처 `"user"` 고정 | **구현** (실제 출처 전달. 저장 방식은 12.1 (가)/(나) 중 사용자 선택) |
| Q8 수동 하향 | **불필요**(현 시점). 재검토 조건은 12.2 |
| Q1 마지막 재계획 id API | **구현 가능** (읽기 전용, 작음) |
| `_replan_link.recent_weekly_km` 정리 | **구현 가능** (사용처 없음) |
| Garmin 외부 삭제(D5/T8) | **사용자 결정 필요** — 삭제 API 있음(SAFE §T8 기록 정정) |
| Q3 CalDAV | **불필요(종결 제안)**, 사용자 확인 |
| Q5 적용 후 자동 전송 | **사실 확인 완료** — 자동 전송 없음. 안내 문구는 product |
| Q2 롱런·Q 전/후 비교, Q4 계획 화면 진입점 | **사용자 결정 필요**(범위) |

### 12.1 Q7 — 꼬리 일정 출처

**코드 근거.** `_build`는 `rv ≥ 2 and src != "history"`일 때 `peak = max(peak, cold_peak_km(dlabel))`(풀 48·하프 32·10k 28·5k 20, 그 외 라벨은 10k 값). `tail`은 항상 `"user"`를 넘기므로 A 상태 재계획에도 하한이 걸린다. 반면 `base`는 실제 출처라 A 목표에는 하한이 없다 → **재계획 꼬리만 피크가 올라가는 불일치**.

**실제 출력 차이**(`build_schedule` 직접 계산, 풀, 시작 롱런 18, cap 없음):

| 조건 | 피크 | 주별 km |
|---|---|---|
| VDOT 있음 + 표준 거리 | Pfitzinger 표×1.05(풀 ≥57.8, 하프 ≥42, 10k ≥31.5, 5k ≥26.3) ≥ 하한 | **차이 없음** |
| VDOT 없음, 시작 30, 10주 | 39 → **48** | 5~8주차 39 → 39.9/43.8/48/48 |
| VDOT 없음, 시작 20, 10주 | 26 → **48** | 26 → 26.6/29.2/32.1/35.3 |
| 남은 주 ≤ 4 | 램프 10%에 막혀 | 차이 없음 |
| `1.5k`/`3k`/`custom` + 낮은 VDOT | 표값 < 28 | 28로 상승 |

REPLAN 진입은 "2주 이행 부족"인데 원래 계획보다 피크를 올리는 것은 의도와 반대다. 하한은 콜드(B·C·D)에서만 유지한다.

**설계.**
- `plan_anchor.Anchor`에 `start_source: str = "user"`(기본값 = 기존 동작, `extra_anchor`·레거시 호환). `load_anchors` SELECT에 `start_source` 추가.
- `planner_schedule.schedule_for_goal.tail`: `_build(..., "history" if a.start_source == "history" else "user", ...)`.
- `plan_replan_service._run` INSERT: 저장값 결정(아래). 현재 `"user" if src=="user" else "history"`는 floor/avg16/default를 `history`로 저장해 그대로 읽으면 C·D의 하한이 사라진다 — **저장 매핑을 같이 바꿔야 한다**.

| 저장 방식 | 내용 | 트레이드오프 |
|---|---|---|
| (가) 권장 | 스키마 v33: `plan_replans.start_source` CHECK를 `('user','history','floor','avg16','default')`로 확장(테이블 재생성·복사), 실제 `src` 저장 | 출처 보존·§11.3 원안과 일치. 마이그레이션 1개 |
| (나) | 스키마 유지. `'history' if src=='history' else 'user'` 저장, 컬럼 의미를 "history=이력, user=콜드(입력·floor·avg16·default)"로 문서화 | 변경 최소, 출처 정보 손실 |

레거시 행: T9 배포 당일이라 소수. 배포 전 `SELECT id,start_source,start_km FROM plan_replans WHERE status='applied'`로 확인하고, B·C·D에서 `history`로 저장된 행만 수동 보정(`floor` 또는 (나)라면 `user`).

**변경 파일**: `src/training/plan_anchor.py`, `src/training/planner_schedule.py`(tail 1줄), `src/services/plan_replan_service.py`(INSERT), (가)면 `src/db_schema_v33.py` 신규 + `src/db_setup.py` `SCHEMA_VERSION=33`. 문서: `decisions.md` ADR-035 부록 R에 한 줄, `architecture.md` 스키마 버전.

**테스트**
- `tests/test_planner_schedule_cold.py`: VDOT 없음·풀·A anchor(`history`, 30km, 10주) → 꼬리 피크 39 / C anchor(`avg16`) → 48 유지 / VDOT 있음 → 변경 전후 동일(회귀).
- `tests/test_plan_anchor.py`: `start_source` 로드, 컬럼 없는 옛 행 기본값 `"user"`.
- `tests/test_plan_replan_service.py`·`test_plan_replan_start.py`: A/B/C/D 저장값 = 응답 `start_source`((나)면 매핑값).
- (가) 마이그레이션: v32 DB의 행 보존, `floor` INSERT 허용.

**회귀 위험**
- VDOT 없는 A 상태 사용자의 적용된 anchor: 배포 후 `schedule_for_goal` 소비자(`readiness_warning`, `story_period`, 코치 핸들러, `week_target`)의 목표가 낮아진다. 이미 생성된 `planned_workouts`는 그대로라 **목표와 행이 잠깐 어긋날 수 있다**(다음 재생성/재계획에서 해소). 준비 볼륨 경고가 새로 뜰 수 있다(정직한 결과).
- 범위 밖 관찰: `_note_cold_start`는 목표 수준 출처(`plan_start_source`)만 보므로 콜드로 만든 목표를 A 상태에서 재계획해도 1주차 근거 문구가 "기록이 적어…"로 남는다(index 0 주에만 붙으므로 anchor 주에는 해당 없음, 영향 작음).

### 12.2 Q8 — "더 가볍게 시작" 수동 하향

**결론: 불필요(현 시점).** 근거:
- `km4`는 오늘 기준 28일 합 ÷ 4(이동 평균)라 최근 공백을 자동으로 깎는다. 직전 주 40km 사용자 기준: 1주 쉼(40,40,40,0) → 30(75%), 2주 쉼(40,40,0,0) → 20~22(50~55%), 3주 쉼 → 10 → B 상태 12km. Daniels 복귀 지침(6~28일 공백이면 50~75%로 재개)과 같은 범위이며, 0.6×avg16을 섞어도 상한이 1.1×km4라 위로 많이 가지 않는다.
- 단기 피로·통증은 주간 단위가 아니라 세션 단위 도구가 이미 담당한다: 행 액션(줄이기/쉬기/건너뛰기/이지로), 통증 단계(`plan_pain.py`, PAIN_REPEAT), 계획 자체의 회복주(3:1).
- 자유 하향 입력은 §11 원칙(A·B 입력칸 없음)과 충돌하고, 시작 부하를 근거 없이 바꾸는 경로를 연다.

**재검토 조건**(이 중 하나라도 실제 사례가 나오면 서버 규칙부터 바꾼다):
- 통증·질병으로 공백 없이 **볼륨을 유지한 채** 재계획(km4는 높지만 몸은 아님) — PAIN_REPEAT 발급 상태에서 재계획 진입.
- 이때 안: 자유 입력 대신 서버 규칙 `lighter=true` → `start_km = max(12, floor(0.8×km4))`. 꼬리에서는 이력 기반으로 취급해야 한다(콜드 하한이 붙으면 "가볍게"인데 피크가 오른다) — (가)면 출처 값 `lighter` 추가, (나)면 `history`로 저장. 화면 표현은 product-architect.

### 12.3 후속 분류

**지금 구현 가능**

1. Q1 마지막 재계획 id API
   - 서비스: `plan_replan_service.last_undoable(conn, today) -> dict | None` — 활성 목표의 마지막 `applied` 행이고 `today < anchor_monday`일 때 `{replan_id, anchor_monday, undo_until(anchor-1일)}`, 아니면 None. `undo()`의 잠금 조건 중 "새 행 이력" 검사는 비싸므로 여기선 하지 않고 undo 시점의 `REPLAN_LOCKED`에 맡긴다.
   - API: `GET /coach/plan/replan/last` (`src/api/routes_plan_replan.py`, 74줄 → ~85줄). 응답 `{"last": {...} | null}`.
   - 프런트 위치·문구는 §10 Q1 안(product 확정 사항).
   - 테스트: `tests/test_plan_replan_service.py`(없음/applied 미래/anchor 당일 None/undone 제외/두 개 중 마지막), `tests/test_api_plan_replan.py` 1건.
   - 회귀 위험: 읽기 전용, 없음.
2. `_replan_link.recent_weekly_km` 제거
   - 프런트는 `link.race_date`만 사용(`replanBanner.ts:29`). 제거하면 advisory 응답마다 `week_compliance.compute` 2회가 사라진다. `distance_km`·`target_time_sec`는 비용이 없어 유지.
   - 변경: `src/api/routes_plan_adjust.py` `_replan_link`, `frontend/src/lib/replanBanner.ts` 타입에서 필드 삭제. 테스트: 링크에 필드 없음 1건. 위험: 없음(`/coach/plan/compare`의 `recent_weekly_km`은 별개 경로).

**사용자 결정 필요**

3. Garmin 외부 삭제(D5/T8): SAFE §T8의 "삭제 API 없음"은 사실과 다르다 — 운영 컨테이너의 `garminconnect`에 `delete_workout(workout_id)`, `unschedule_workout(scheduled_id)`가 있다. 우리는 행마다 별도 템플릿을 업로드하고 `garmin_workout_id`(템플릿 id)를 저장하므로 `delete_workout`로 정리 가능. 결정할 것: ① 실제 계정에 비가역 삭제를 할지 ② 시점(적용 직후 vs 되돌리기 기간 종료 후) ③ 되돌리기 시 복원 행의 `garmin_workout_id` 처리(NULL 복원 → 재전송 필요). 채택 시 원칙: 커밋 후 best-effort(재시도 1회 → 로그 → 계속), 실패해도 재계획은 성공, 결과의 `external[]`에 삭제 성공 여부 표시.
4. Q2 주별 롱런·Q 전/후 비교: `_weekly_km`과 같은 방식으로 `long_km`, `q_count` 집계 추가는 간단하나 응답·화면 범위 결정이 먼저.
5. Q4 계획 화면 진입점: product 결정. 서버는 변경 없음(advisory 없이도 preview/apply 가능).

**불필요 / 확인 완료**

6. Q3 CalDAV: `caldav` 패키지가 `requirements.txt`에서 주석 처리, 운영 컨테이너에서 `ImportError` → 운영에서 CalDAV 푸시는 동작하지 않고 푸시 이력도 DB에 남지 않는다. `external[]`에 넣을 근거 데이터 자체가 없으므로 종결 제안(CalDAV 지원 재개는 LATER 대상).
7. Q5: Garmin 전송은 v0.2 수동 경로(`src/web/views_training_export.py`)뿐, 자동 전송 없음. 재계획으로 생긴 새 세션은 워치에 가지 않는다 — 결과 화면 안내 여부는 product.

## 13. 보류 4건 결정안 (2026-10-09, product-architect 초안 — 확정 아님, 사용자 승인 대기)

§11~§12(Q7·Q8·Q1 API·link 정리)와 ADR-035 부록 R은 재설계하지 않고 전제로 삼는다. 작업 단위는 서비스/API/프런트/테스트 단위 합산.

### 13.1 Garmin 외부 삭제 (D5/T8)

**코드 사실.** `garminconnect`에 `delete_workout`·`unschedule_workout` 있음(운영 컨테이너 확인). `src`에는 호출처 없음. 우리가 저장하는 건 템플릿 id(`garmin_workout_id`)뿐, `scheduled_id`는 저장 안 함. `undo()`는 삭제 행 전체(garmin_workout_id 포함)를 그대로 복원한다. `plan_ingest.py`는 Garmin 캘린더에서 읽어온 행에도 같은 컬럼을 채운다(= 사용자가 직접 만든 워크아웃 가능).

| 선택지 | 내용 | 평가 |
|---|---|---|
| A | 현행: 안내만 | 안전, 사용자가 워치 일정을 직접 지워야 함 |
| B | apply 직후 자동 삭제 | 비가역인데 동의 없음. undo 시 복원 행이 죽은 id를 가리킴. 기각 |
| C | 되돌리기 기간 종료 후 자동 | 예약 작업 필요, 사용자가 모르는 새 삭제. 기각 |
| **D 추천** | 결과 화면에 별도 버튼 `[Garmin에서 지우기]`, 확인 시트 1회 | 명시적 동의, undo와 충돌을 문구로 해소 |

**추천 D 설계.**
- 시점: apply와 분리. 결과 카드 외부 안내 띠(§5)의 보조 버튼. 미리보기 단계에는 두지 않는다(적용 전 삭제 금지).
- 확인 시트(사실+영향+선택지 하나): "Garmin 캘린더의 세션 {n}개({10/14, 10/16}…)를 삭제해요. 삭제 후에는 되돌리기를 해도 워치 일정은 돌아오지 않아요." `[삭제]` `[취소]`. 체크박스 없음.
- 안전장치: 대상은 이번 재계획 `replaced_json.deleted` 중 garmin_workout_id가 있고 RunPulse가 만든 행(`source`가 garmin 가져오기가 아닌 것)만. 삭제 전 `get_workout_by_id`로 존재 확인. 이력 있는 보호 행(preserved)은 대상 아님.
- 실패: 행별 재시도 1회 → 로그 → 계속. 별도 사용자 요청이라 sync/재계획 성공에 영향 없음. 결과 "{k}개 지웠어요, {m}개는 직접 지워 주세요({날짜})". 재시도 버튼은 실패분만.
- undo 처리: 삭제 성공한 항목은 `replaced_json`의 garmin_workout_id를 NULL로 갱신 → undo로 복원돼도 NULL(재전송 시 `push_weekly_plan`이 다시 올림, 중복 id 없음). 삭제 후 되돌리기 시 결과 문구: "Garmin 일정은 복원되지 않아요. 다시 보내려면 내보내기에서 전송하세요."
- 선행 확인: 실계정 1건 스모크로 `delete_workout`가 예약 일정도 함께 지우는지 확인. 안 지우면 `scheduled_id` 저장이 선행되어야 함(미해결 시 D 보류).

| 항목 | 값 |
|---|---|
| 규모 | 4단위 (서비스 `garmin_cleanup`, API POST, 확인 시트, 테스트·스모크) |
| 위험 | 비가역 삭제(확인 시트로 완화), 사용자 자작 워크아웃 오삭제(source 필터+존재 확인), 예약 잔존(스모크로 선확인), 토큰 만료 시 전량 실패(안내로 처리) |

### 13.2 Q3 CalDAV 종료

**실제 상태.** `requirements.txt`에서 `caldav` 주석 처리 → 운영에서 `push_workout_to_caldav` import 시 ImportError. 푸시 이력은 DB에 남지 않아 `external[]` 대상 아님. 그런데 진입점은 살아 있다: 설정 CalDAV 섹션·연결 테스트(`views_settings*.py`), 계획 내보내기 메뉴 "CalDAV 캘린더"(`views_training_cards.py`, `views_training_export.py`), 가이드 문구(`views_guide.py`). 사용자는 누르면 실패한다.

| 선택지 | 영향 범위 | 평가 |
|---|---|---|
| A 코드 제거 | `caldav_push.py`, 라우트 2, 설정 섹션, 가이드, 관련 테스트, config의 caldav 키 | 정리되나 되돌리기 어려움, 5파일+ |
| **B 추천** 진입점 비활성 표시 | 메뉴 항목 제거, 설정 섹션을 "현재 제공하지 않아요. 캘린더 구독(ICS)을 사용하세요" 한 줄로, 가이드 문구 정정. 코드·테스트 유지 | 실패 경험 제거, 재개 여지(LATER) |
| C 패키지 설치로 재개 | requirements 복구+이미지 재빌드 | 수요 근거 없음, 외부 서버 쓰기 책임 증가. 기각 |

| 항목 | 값 |
|---|---|
| 규모 | B: 3단위 (UI 3곳 + 테스트 1, 문서 1줄은 LATER 기록) |
| 위험 | 저장된 caldav 자격증명이 config에 남음(표시만 제거, 삭제는 사용자 몫) / 옛 CalDAV 이벤트는 우리가 추적하지 않으므로 재계획 안내 대상 아님 |

§5의 "CalDAV는 `external[]`에 포함되지 않는다"는 이 결정으로 종결.

### 13.3 Q2 주별 롱런·비교 범위

**근거.** §5가 "API에 없어 넣지 않음", SAFE §2.4는 `long/q_before/after`를 약속, §12.3-4는 `_weekly_km`과 같은 방식의 집계 추가가 간단하다고 평가. 선택할 것은 지표와 노출 깊이.

| 선택지 | 내용 | 평가 |
|---|---|---|
| A | 미제공(현행) | 단순, SAFE 약속 미이행 |
| **B 추천** | 롱런 km만 전→후, 주 행 탭 시 보조 줄 "롱런 30→26km" (Level 2) | 롱런이 이번 변경의 체감 핵심, 390px 표 유지 |
| C | 롱런 + Q 세션 수 | Q 수는 주 1~2개로 변화가 적고 행 밀도만 증가 |
| D | 표에 열 추가 | 390px에서 가로 압박. 기각 |

범위: 전체 남은 주 응답, 화면은 기존 "처음 4주+나머지 보기" 규칙 그대로. 대회 주는 롱런 비교 제외(레이스가 롱런이므로 오해 소지).

| 항목 | 값 |
|---|---|
| 규모 | B: 3단위 (서비스 `long_km` 집계, API 필드·테스트, 프런트 펼침 행). C는 +1 |
| 위험 | 롱런 정의(주 최대 거리 vs `long` 타입) 불일치 → 서비스 한 곳에서 정의, 미리보기·결과 일관 / 응답 필드 추가라 기존 클라이언트 영향 없음 |

### 13.4 Q4 플랜 화면 진입점

**위치 근거.** 플랜 상세(`/coach/plan/[id]`) 헤더에는 `← 코치`, 목표명, 주차·레이스 문구, CTL, 준수율이 있고 메뉴는 없다. 배너는 행 액션 시트 안에서만 보이고 "이번 주 숨김" 후엔 재진입 경로가 없다.

| 선택지 | 평가 |
|---|---|
| A 배너만(현행) | 숨김 뒤 경로 없음, advisory 없는 원함 사용자 불가 |
| **B 추천** 헤더 보조 링크 | 준수율 줄 아래 `text-xs` 링크 한 줄, 항상 발견 가능, 공격적이지 않음 |
| C 행 액션 시트 메뉴 | 시트를 열어야 보임, 세션 단위 도구와 의미 혼동 |

**B 상세.**
- 문구: "남은 일정 다시 맞추기 →" (설명 없음, 아이콘 없음, `text-fg-muted` 보조 스타일, `min-h-11`). 이동: `/coach/plan/replan`.
- 노출: 활성 목표 있음 + 레이스 날짜 미래 + 재계획이 가능한 남은 주 수(서버 REPLAN 조건과 동일 기준, 확인 필요) + 통증 중 아님(배너와 동일). REPLAN 배너가 지금 보이면 링크는 숨겨 중복 방지.
- 되돌리기 가능한 재계획이 있으면(`last_undoable`) 링크 대신 "10/13부터 새 일정 · 10/12까지 되돌리기" 한 줄이 Q1 안으로 같은 자리를 차지(Q1 UI와 자리 공유).

| 항목 | 값 |
|---|---|
| 규모 | B: 2단위 (노출 조건 순수 함수+테스트, 헤더 링크) |
| 위험 | 불필요한 잦은 재계획 유도 → 문구 중립+미리보기에서 "변화 없음" 상태 지원 / 헤더 정보 밀도 증가(한 줄 한정) |

### 13.5 사용자 승인 목록

1. Garmin 삭제를 D(결과 화면 별도 버튼 + 확인 시트, RunPulse가 만든 행만, 성공 시 복원 행 garmin_workout_id를 NULL 처리)로 진행하되, 실계정 스모크로 예약 일정 삭제 여부 확인 후 착수할까요?
2. CalDAV를 B(진입점 3곳 비활성·코드 유지, 재개는 LATER)로 종결할까요?
3. 주별 비교에 롱런 km만(B, 행 탭 보조 줄, 대회 주 제외) 추가할까요?
4. 플랜 상세 헤더에 "남은 일정 다시 맞추기 →" 링크(B)를 REPLAN 배너 비노출·통증 아님·레이스 미래 조건으로 추가할까요?

## 14. §13.3·§13.4 재검토 — Q2 롱런 비교 · Q4 진입점 (2026-10-09, product-architect 독립 검증 — 확정 아님, 사용자 승인 대기)

§13.3·§13.4를 코드로 다시 확인한 결과 전제 일부가 사실과 다르다. 기존 절은 그대로 두고 아래로 정정·보강한다.

### 14.1 코드 사실 (§13 정정 포함)

| # | 사실 | 근거 | §13 영향 |
|---|---|---|---|
| F1 | preview `before/after`는 `{week_start, planned_km}`뿐. 행 타입·최대 거리 없음 → **프런트에서 롱런 계산 불가, 백엔드 변경 필수** | `plan_replan_service._weekly_km` | §13.3 "API 필드 추가" 맞음, "프런트만" 불가 확인 |
| F2 | 대회일 행은 `workout_type='race'`, 롱런은 `long`/`long_mp`(`plan_advisory.LONG_TYPES`, `planner` `_LONG`). 타입으로 집계하면 대회 주 레이스는 자연히 빠진다 | `planner*.py`, `plan_advisory.py` | §13.3 "대회 주 제외"는 별도 규칙이 아니라 정의로 해결 |
| F3 | 서버의 "최소 주" 조건은 없다. `anchor(다음 월요일) > race`면 `RACE_WEEK`, 그 외엔 **대회 주 1주만 다시 짜는 것도 허용** | `_goal_and_anchor` | §13.4 "서버 REPLAN 조건과 동일 기준(확인 필요)" → 서버 기준만 따르면 테이퍼 1주 재계획 링크가 노출됨 |
| F4 | `REPLAN` advisory는 대회 근접을 보지 않는다(이행률·쉼만). 대회 직전 주에 배너가 떠서 미리보기가 `RACE_WEEK`로 실패할 수 있다 | `plan_advisory._replan` | 신규 결함 후보 |
| F5 | 배너의 `isPain`은 **시트에서 지금 고른 사유가 통증인지**다(지속 상태 아님). 지속 통증 신호는 서버 `/coach/plan/advisories`가 최근 3일 통증 행이면 빈 목록을 주는 것뿐 | `RowActionSheet.svelte`, `routes_plan_adjust.plan_advisories` | §13.4 "통증 중 아님(배너와 동일)"은 헤더에 그대로 옮길 수 없음 |
| F6 | 배너는 `RowActionSheet`(바텀시트) 안에만 있다. 헤더와 같은 층에 동시에 보이지 않는다 | 동일 | §13.4 "배너 보이면 링크 숨김"은 성립 조건이 없음. 구현하려면 헤더가 advisories를 따로 불러야 하고, 결과적으로 **재계획이 가장 권장될 때 링크가 사라지는 역설** |
| F7 | `/coach/plan/[id]`는 임의 goal_id를 받는다(`get_active_plan(goal_id)`), 응답에 `goal.status` 있음. 재계획 서비스는 항상 **활성 목표**만 다룬다 | `routes_plan.get_plan_by_id`, `PlanGoal.status` | 지난/취소 목표 화면에 링크가 뜨면 다른 목표를 재계획하게 됨 → 조건 누락 |
| F8 | `GET /coach/plan/replan/last`(`last_undoable`)는 있으나 프런트 호출처 없음. 적용 후 anchor 전에 다시 들어가면 같은 anchor로 재계획이 **겹쳐 쌓이고**, undo는 마지막 것만 되돌려 원래 일정이 아니라 1차 재계획 상태로 돌아간다 | `plan_replan_service.undo`, `replan/+page.svelte` | §13.4의 "Q1 자리 공유"는 선택이 아니라 진입점 추가의 **선행 조건** |

### 14.2 Q2 — 롱런 비교

코칭 관점: 플래너의 주별 롱런은 주간 거리에 대략 비례해 움직이므로 주마다의 "30→26km"는 주간 km 차이를 다시 말하는 것에 가깝다. 러너가 적용 여부를 정할 때 실제로 묻는 것은 "대회 전에 충분히 긴 롱런을 한 번은 하나"다 — 즉 **남은 기간 최장 롱런 한 숫자**. 주 행 탭 펼침은 390px에서 표 행을 버튼으로 바꿔야 하고(행 높이 44px 확보 → 4주 목록이 화면 밖으로), 숨겨진 정보라 발견률도 낮다.

| 선택지 | 내용 | 평가 |
|---|---|---|
| A | 미제공 | SAFE §2.4 약속 미이행 |
| B (§13.3안) | 주 행 탭 시 보조 줄 | 결정 기여 낮음, 표 인터랙션·접근성 비용, 대회 주 예외 규칙 필요 |
| **E 추천** | Level 1 요약 한 줄: "가장 긴 롱런 32 → 28km (11/16 주)". `|Δ| < 2km`면 "가장 긴 롱런은 그대로 32km" 또는 생략. 주별 값은 Level 2 "어떻게 계산했나요" 안 목록에만 선택적으로 | 결정 질문에 직접 답함, 표 변경 없음, 390px 1줄 |
| F | 요약 + 롱런 횟수(예 ≥ 목표 거리 70%) | 거리별 기준이 코칭 판단을 확정하는 셈 → 보류 |

- 색·판정 없음(§5 원칙 유지). "부족해요" 같은 평가 문구 금지 — 숫자와 주만.
- 위치: Level 0 카드 바로 아래 또는 주별 표 제목 옆. Level 0 문장에는 넣지 않는다(이미 2문장).
- 작업: 2단위 — ① 서비스 `_weekly_km`에 `long_km`(그 주 `long`/`long_mp` 최대 거리, 없으면 null) 추가 + 테스트(대회 주 null, preserved 롱런 포함 여부 명시) ② `replanView.longPeakText` 순수 함수 + 테스트 + 한 줄 표시.
- 위험: before가 `source='planner'`가 아닌 일정(Garmin 가져오기)일 때 before 롱런 null → "새로 넣어요" 문구와 같이 after만 표시. 롱런 정의를 서비스 한 곳에 둬 결과 화면과 일치.

### 14.3 Q4 — 진입점

| 선택지 | 평가 |
|---|---|
| A 배너만 | 숨김 후 경로 없음(§13.4 동의) |
| **B' 추천** 플랜 상세 헤더 링크(조건 정정) | 계획을 "다시 보는" 맥락과 일치 |
| T Today(`NextSessionCard`) | Today는 오늘 실행 화면. 전략 결정 진입점이 매일 노출되면 잦은 재계획 유도. 행 시트 배너가 이미 Today에서도 열림 → 추가 불필요 |
| S 설정 | 너무 깊음, 목표 편집과 혼동. 기각 |

**B' 노출 조건(순수 함수 `replanEntry(plan, today, last)`):**
1. `goal.status === 'active'` (F7) 그리고 `race_date` 있음.
2. 다음 월요일 ≤ 대회 주 월요일 − 7일, 즉 **재계획 범위가 2주 이상**(F3). 대회 직전 주·대회 주엔 숨김 — 테이퍼를 다시 짜는 것은 이득이 없다. 서버보다 엄격한 클라이언트 기준임을 명시.
3. `last`(= `/replan/last`)가 있으면 링크 대신 "10/13부터 새 일정 · 10/12까지 [되돌리기]" (F8, Q1 UI 동시 구현).
4. 통증: 헤더에서는 **조건으로 쓰지 않는다**. 사용자가 직접 누르는 진입이고, 재계획은 최근 기록(통증으로 줄어든 부하 포함) 기반이라 위험을 키우지 않는다. 통증 직후 2일 제안 흐름(`plan_pain.proposal`)과 겹치지 않도록 미리보기 화면 Level 2에 "통증이 있으면 먼저 쉬는 일정을 정리하세요" 한 줄만 조건부로(선택, 서버 신호 필요 시 별도 1단위).
5. 배너 중복 조건 삭제(F6). 대신 REPLAN advisory가 있을 때 링크 문구를 바꾸지 않는다 — 헤더가 advisories를 부르지 않게 해 호출 1회 절약.

- 390px: 준수율 줄 아래 한 줄, 시각은 `text-xs`, 탭 영역만 `min-h-11`(패딩). 헤더가 이미 4줄이라 아이콘·설명 추가 금지.
- 작업: 3단위 — ① `replanEntry` 순수 함수 + 테스트(활성 아님/대회 2주 미만/last 있음/race 없음) ② `getReplanLast` API 함수 + 헤더 링크·되돌리기 줄 ③ 재계획 페이지 진입 시 `last` 있으면 미리보기 대신 적용 상태 표시(겹침 방지, F8).
- 위험: ③ 없이 링크만 내면 재계획 중첩 → undo 의미 왜곡. 서버에도 "같은 goal에 아직 시작 전 applied가 있으면 preview/apply 거부(또는 그 행을 먼저 undo)" 가드를 두는 것이 근본책 — system-architect 판단 필요.

### 14.4 별도 확인 필요 (§13 범위 밖, 발견)

- F4: `plan_advisory._replan`에 "anchor ≤ 대회 주 월요일 − 7일" 조건 추가 여부(배너 → RACE_WEEK 실패 방지). 1단위.
- F8 서버 가드 여부(위).

### 14.5 사용자 승인 목록 (§13.5 3·4 대체안)

3'. 롱런은 주 행 펼침(B) 대신 **최장 롱런 전→후 요약 한 줄**(E, 2단위, 서비스 `long_km` 추가)로 할까요?
4'. 헤더 링크 조건을 **활성 목표 + 재계획 범위 2주 이상 + 마지막 재계획 시작 전이면 되돌리기 줄로 대체**로 바꾸고, 배너 중복·통증 조건은 빼며, 재계획 중첩 방지(③)를 같이 할까요?
5'. F4(advisory 대회 근접 조건)·F8 서버 가드를 system-architect 검토로 넘길까요?
