# AUD 오류 분기 페이지 계약 — 근본원인·설계·개발 큐

대상 결함: AUD-68c84e(error-state-missing), AUD-8c3aa4(pageerror), AUD-295255(no-h1), AUD-4eee31(no-h1, 73d2efc2 로 B안 적용됨)
작성: 2026-11-23, 브랜치 feat/frs-f3. 이 문서는 설계 초안이다. §5 결정 항목은 사용자가 확정한다.

---

## 1. 사실 확인 (코드 근거)

### 1.1 AUD-8c3aa4 — 실제 결함이다. 리뷰의 reject/unsure 판정은 틀렸다
- `frontend/src/routes/+layout.ts:8` 에 `ssr = false` 가 있다. 앱이 SPA 모드라 첫 진입은 hydrate 가 아니라 `navigate({type:'enter'})` 로 처리된다
  (`node_modules/@sveltejs/kit/src/runtime/client/client.js:404-408`, kit 2.70.3).
- 이 경로의 `create_navigation(current, …)` 는 `from: { url: current.url }` 을 만든다(`client.js:3353-3356`).
  첫 진입 시점의 `current.url` 은 `null` 로 초기화돼 있다(`client.js:268-274`).
  그래서 afterNavigate 가 받는 `from` 은 null 이 아니고, `from.url` 만 null 이다. 타입 정의(`url: URL`)와 실제 값이 다르다.
- `routes/today/month/[ym]/+page.svelte:57` `from?.url.pathname` 은 `from` 만 옵셔널로 검사하고 `url` 은 검사하지 않는다.
  그래서 딥링크·새로고침·새 탭으로 들어오면 매번 `Cannot read properties of null (reading 'pathname')` 이 난다.
  스윕 결과와도 맞다(`coverage_ledger.json`: empty·error·small 6셀 모두 같은 예외).
  하네스나 리터럴 `[ym]` 때문에 생긴 산물이 아니다. 리터럴 `[ym]` 은 load 에서 307 리다이렉트되지만, 예외는 그것과 무관하게 첫 진입에서 난다.
- 같은 문제를 다른 곳에서는 이미 피해 갔다. `routes/library/[id]/+layout.svelte:23` 은 `nav.from?.url?.pathname ?? null` 로 쓴다.
  가드가 헬퍼 없이 화면마다 따로 들어가 있다는 뜻이다.
- 사용자에게 보이는 영향: 예외 때문에 `fromPath` 기록이 끊긴다. 같은 afterNavigate 배치(`client.js:2042` forEach)에서 이 콜백 뒤에 등록된 콜백도 실행되지 않는다.

### 1.2 AUD-295255 — today 맞다. 추정이 아니라 스윕 기록으로 확인했다
- `coverage_ledger.json`: `/today|error|390·desktop :: no-h1`. `/today|empty` 에는 no-h1 이 없다.
- `routes/today/+page.svelte:102` 는 `<PageHead title="Today" heading={null} />` 로 고정돼 있다. 오류 분기(104-113)는 ErrorState 만 렌더한다.
  h1 은 성공 분기 안의 `TodayHero.svelte:39` 와 `today/ColdStartProgress.svelte:13` 만 그린다.
- 교차검토 반론 검토: ColdStartProgress 는 `data.today` 가 있는 성공 분기(117 이후, 132-133)에서만 렌더된다.
  그래서 "오류 분기 h1 + ColdStart h1" 이 겹칠 일은 없다. 반면 빈 분기(`TodayEmpty`)에는 이미 h1 이 있다(스윕에서 empty no-h1 이 없음).
  따라서 원 설계안 `heading={data.today ? null : '오늘'}` 을 그대로 쓰면 빈 상태에서 h1 이 2개가 된다. 반론이 지적한 위험은 실제로 있다.
  올바른 조건은 'failed 일 때만'이다.
- 같은 증상이 있지만 아무 결함 ID 에도 묶이지 않은 셀: `/library/[id]`·`/library/[id]/metrics`·`/providers`·`/streams` 의 error no-h1, `/|error` no-h1(`/` → today 로 추정).
  이 셀들은 AUD-295255 의 범위("오류 상태에서 h1 사라짐, 대상=활동")로 흡수한다.

### 1.3 AUD-68c84e — 결함은 맞다. 다만 "빈 화면"이라는 묘사는 부정확하다
- `routes/coach/[threadId]/+page.ts:22-27` 는 실패를 `errorMessage: string` 하나로만 반환한다. 표준 `Failure`/`toResult`(`lib/loadFailure.ts:6-13,58-64`)를 쓰지 않는다.
- `+page.svelte:194-202` 는 실패의 종류와 상관없이 "대화를 찾을 수 없습니다" 를 보여 준다. 500·네트워크 오류도 404 처럼 보인다.
  그 아래에는 서버 원문 `e.message` 가 그대로 노출된다. `data-testid="error-state"` 도, 재시도 버튼도 없다. 화면이 빈 것은 아니다. 대신 원인을 잘못 알려 준다.
- 채널도 섞여 있다. `+page.svelte:36` `let errorMessage = $state(data.errorMessage)` 가 load 실패 문자열을 액션 오류 채널(74·82·92·170·274)의 초기값으로 쓴다.
- 교차검토 반론은 모두 타당하다(변경량 과소평가, 채널 혼재). 원래 제안된 verify `pytest -k 'frontend or error_state'` 는 프론트 테스트를 하나도 실행하지 않는다.
  프론트 러너는 `frontend/package.json` 의 `test:unit` = `node --test "tests/*.test.mjs"`(Node 24, .ts 직접 import)이다.

### 1.4 AUD-4eee31 — 73d2efc2 는 증상 패치다. 회귀 2건도 만들었다
- 감지기(`scripts/audit/sweep_pw.mjs:35,47`)는 `querySelectorAll('h1').length` 만 센다. 73d2efc2 가 넣은 h1 3개는 모두 `sr-only` 라 감지만 통과한다.
  결함 문제문에 적힌 "sighted users get no context" 는 해결되지 않았다.
- h1 조건을 분기 조건과 따로 복제했다(`data.notFound || !d || !line`, `data.laps.length === 0`). 분기 조건이 바뀌면 둘이 어긋난다.
- 현재 `npm run -s test:unit` 결과: 831 중 829 통과, 2 실패. 2건 모두 73d2efc2 가 원인이다.
  1. `tests/a11yStatic.test.mjs:95` h1 ratchet: laps 가 이제 h1 을 가지므로 `H1_IN_CHILD` 에서 빼야 하는데 빼지 않았다(개선 감지).
  2. `tests/fileSize.test.mjs:20`: `coach/[threadId]/+page.svelte` 가 301줄로 300줄 상한을 넘었다.
- 기존 ratchet 은 "파일 어딘가에 h1 이 있는가"를 검사한다. 분기별 h1 부재는 원리적으로 잡지 못한다. 이번 4건이 통과한 이유가 이것이다.

---

## 2. 공통 근본원인

| # | 근본원인 | 드러난 결함 |
|---|---|---|
| R1 | 페이지 머리(h1·title) 계약이 분기 단위가 아니라 파일 단위다. `PageHead heading={null}` 은 "자식이 h1 을 그린다"는 위임인데, 자식은 성공 분기에만 있다. 오류·빈 분기는 위임받을 곳이 없다. 회귀 테스트도 파일 단위라 잡지 못한다. | 295255, 4eee31(+ library/[id]/*) |
| R2 | load 실패 표현이 라우트마다 다르다. 표준(`Failure`+`LoadFailure`/`ErrorState`)이 있지만 강제되지 않는다. 문자열 `errorMessage` 를 쓰는 라우트가 남아 있고, 이 문자열이 404와 5xx를 뭉개며 액션 오류 채널과도 섞인다. | 68c84e |
| R3 | SvelteKit 의 `AfterNavigate.from.url` 이 타입상 non-null 이지만, SPA 첫 진입에서는 null 이다. null 안전 헬퍼가 없어서 화면마다 가드를 각자 작성한다(한 곳은 맞게, 한 곳은 틀리게). | 8c3aa4 |

세 원인 모두 공용 부품은 이미 있다(PageHead·LoadFailure·loadFailure.ts). 빠진 것은 "어느 분기에서 무엇을 써야 하는가"라는 규약과 이를 강제하는 테스트다.
따라서 공용 컴포넌트(PageHead·ErrorState·LoadFailure)는 수정하지 않는다. 대신 순수 헬퍼 2개와 정적 계약 테스트 2개를 더한다. 영향 범위가 작고 되돌리기 쉽다.

---

## 3. 설계

### 3.1 계약 C1 — 페이지 머리는 모든 분기에서 h1 이 정확히 1개
- 규약: 라우트 파일의 `PageHead` 는 `heading` 을 리터럴 `null` 로 고정하지 않는다. 상태에 따라 계산한 값을 넘긴다.
  - 성공 분기에서 자식이 h1 을 그리는 상태 → `null`
  - 그 외(실패·미존재·자식이 h1 을 안 그리는 빈 상태) → 화면 제목
- 순수 헬퍼 `frontend/src/lib/a11y/pageHeading.ts`(신규):
  `pageHeading(state: 'ok'|'empty'|'failed', title: string, childOwns: readonly ('ok'|'empty'|'failed')[]): string | null`
  - `childOwns.includes(state)` 이면 `null`, 아니면 `title` 을 돌려준다.
  - "자식이 어느 상태에서 h1 을 그리는가"를 라우트 파일에 한 줄로 드러낸다. 분기 조건과 h1 조건이 따로 놀던 복제(73d2efc2)를 없앤다.
- 보이는 h1을 기본으로 한다(sr-only 는 쓰지 않는다). 오류 화면에서 "어느 화면이 실패했는가"는 시각 사용자에게도 필요한 맥락이다. 이 항목은 결정이 필요하다(§5 D1).
- 화면 대상 맥락(날짜·provider·활동명):
  - 제목에 대상이 이미 있는 화면은 그대로 쓴다. sources=`syncProviderName(provider)`, month=`monthLabel`.
  - 대상을 모르는 실패(활동 load 실패)는 일반 제목(`활동 상세`)을 쓰고, 원인은 ErrorState 문구에 둔다. 허위 헤드라인(TodayHero 강제 렌더, 295255 안 C)은 채택하지 않는다.
- 회귀 방어 `frontend/tests/pageHeadContract.test.mjs`(신규, 정적):
  - (a) `src/routes/**/+page.svelte` 중 `heading={null}` 리터럴을 쓰는 파일은 허용 목록에만 있어야 한다. 이 목록은 줄어들 수만 있다(ratchet).
  - (b) 허용 목록에서 빠진 파일이 `heading={null}` 대신 `pageHeading(` 을 쓰는지 확인한다.
  - (c) `sr-only">` 로 시작하는 h1 은 허용 목록에만 둘 수 있다.
  - 최종 판정은 브라우저 스윕(no-h1 0건, h1 1개)이 한다. 정적 테스트는 같은 패턴이 다시 생기는 것을 막는 역할이다.

### 3.2 계약 C2 — load 실패는 `Failure` 하나의 채널로
- 규약: `+page.ts` 는 실패를 `failure: Failure | null` 로 돌려준다(`classifyFailure`). 잘못된 파라미터도 `kind:'not_found'` Failure 로 만든다.
  화면은 `LoadFailure`(404=안내문, 그 외=ErrorState+재시도+상위 링크)를 렌더한다. load 에는 `depends('app:…')` 를 두어 재시도가 `invalidate(key)` 로 동작하게 한다.
- load 실패와 액션 오류는 분리한다. 액션 오류 `$state` 는 `null` 로 시작하고, load 실패 값으로 초기화하지 않는다.
- `lib/loadFailure.ts` 에 `notFoundFailure(code: string): Failure` 를 추가한다(순수 함수). 잘못된 ID 를 표준형으로 바꾸는 데 쓰고, 다른 라우트도 재사용할 수 있다.
- 서버 원문 `e.message` 는 화면에 내보내지 않는다. 대신 `failure.detail`(`500 X`)을 접힌 상세에서만 보여 준다(ErrorState 기존 동작).
- 회귀 방어 `frontend/tests/coachThreadLoad.test.mjs`(신규): `notFoundFailure` 단위 테스트에 더해 정적 검사를 한다.
  `+page.ts` 에 `classifyFailure` 와 `depends(` 가 있고 `errorMessage` 가 없을 것, `+page.svelte` 에 `LoadFailure` 가 있을 것.

### 3.3 계약 C3 — 내비게이션 출처는 null 안전 헬퍼로만 읽는다
- `frontend/src/lib/navFrom.ts`(신규): `navFromPath(from: { url?: URL | null } | null | undefined): string | null`.
  `from?.url?.pathname ?? null` 을 반환한다. 주석에 kit 근거(SPA enter 에서 `from.url=null`)를 남긴다.
- 사용처 2곳을 교체한다. `today/month/[ym]/+page.svelte:57`, `library/[id]/+layout.svelte:23`.
- 회귀 방어 `frontend/tests/navFromGuard.test.mjs`(신규, 정적): `src/**/*.{svelte,ts}` 에 `from?.url.` 또는 `from.url.` 패턴이 0건이어야 한다(`navFrom.ts` 는 제외).
- month 화면 렌더(빈·404 시 '데이터 수집 중')는 이 결함의 범위가 아니다. 다만 같은 셀에 error-state-missing 이 있으므로 §6 에 후속 후보로 적는다.

### 3.4 결함별 변경 파일
| 결함 | 변경 파일 |
|---|---|
| 8c3aa4 | `lib/navFrom.ts`(신규), `routes/today/month/[ym]/+page.svelte`, `routes/library/[id]/+layout.svelte`, `tests/navFrom.test.mjs`(신규), `tests/navFromGuard.test.mjs`(신규) |
| 295255 | `lib/a11y/pageHeading.ts`(신규), `routes/today/+page.svelte`, `routes/library/[id]/+page.svelte`, `routes/library/[id]/{metrics,providers,streams}/+page.svelte`, `tests/pageHeading.test.mjs`·`tests/pageHeadContract.test.mjs`(신규), `tests/a11yStatic.test.mjs`(H1_IN_CHILD 축소) |
| 68c84e | `lib/loadFailure.ts`, `routes/coach/[threadId]/+page.ts`, `routes/coach/[threadId]/+page.svelte`, `tests/coachThreadLoad.test.mjs`(신규), `tests/errorBranchH1.test.mjs` |
| 4eee31 | `tests/a11yStatic.test.mjs`(laps 제거, 회귀 즉시 복구), `routes/data/sources/[provider]/+page.svelte`, `routes/library/[id]/laps/+page.svelte`, `tests/errorBranchH1.test.mjs`(→ 계약 테스트로 흡수 후 삭제) |

### 3.5 점진 적용 순서와 되돌리기
1. 회귀 복구(4eee31-1). 테스트 1개만 고친다. 이 단계가 끝나면 남는 baseline 실패는 fileSize 1건이다.
2. 순수 헬퍼 2개(8c3aa4-1, 295255-1)를 넣는다. 아직 아무도 쓰지 않으므로 화면 영향이 없다.
3. 사용처를 한 단위에 한 화면 묶음씩 교체한다(8c3aa4-2 → 295255-2 → 68c84e-1 → 295255-3/-4 → 4eee31-2).
   계약 테스트의 허용 목록은 화면을 고칠 때마다 함께 줄인다.
4. 공용 컴포넌트(PageHead·ErrorState·LoadFailure)는 바꾸지 않는다. 그래서 22개 사용처가 한꺼번에 영향받을 일이 없다.
- 되돌리기: 단위마다 커밋 1개로 만들고 `git revert <sha>` 로 되돌린다. 화면 단위를 되돌릴 때는 계약 테스트의 허용 목록 축소도 같은 커밋에 있으므로 함께 복원된다.
  헬퍼 단위는 사용처 단위를 먼저 revert 한 뒤에 되돌린다(deps 의 역순).
- 각 화면 단위가 끝나면 브라우저 스윕으로 해당 셀(error/empty × 390/desktop)의 h1 개수=1, error-state 존재, pageerror 0 을 확인한다.
  기존 리뷰 규율(`scripts/autopilot/REVIEW.md`)에 따른다. 단위 verify 는 정적·단위 테스트까지만 다룬다.

---

## 4. 위험 항목
- 스키마·권한·알고리즘·config 변경: 없다. 프론트 표시 계층과 프론트 테스트만 바꾼다. API 계약도 바뀌지 않는다.
- 주의할 점:
  - `ThreadPageData` 에서 `errorMessage` 를 없애면 svelte-check 타입이 바뀐다. 그래서 `+page.ts` 와 `+page.svelte` 는 같은 단위에서 고쳐야 한다(68c84e-1).
  - `coach/[threadId]/+page.svelte` 는 300줄 상한을 이미 넘었다. 오류 분기를 LoadFailure 로 바꾸면 줄 수가 줄어들 것으로 예상한다. 줄지 않으면 분리가 필요하다.

---

## 5. 사용자 결정 필요
- D1. 오류 분기 h1 을 보이게 할지(추천) sr-only 로 유지할지. 보이게 하면 오류 화면 상단에 제목이 새로 생긴다. 4eee31-2 와 295255-2~4 의 표시 방식이 이 결정에 달려 있다.
- D2. today 오류 분기의 제목 문구(`오늘` 또는 `Today`). 문서 title 은 `Today` 다.
- D3. 잘못된 스레드 ID 의 404 문구(현행 "대화를 찾을 수 없습니다" 유지를 추천).

## 6. 범위 밖 후속 후보(큐에 넣지 않음)
- error-state-missing 으로 남은 데이터 화면: `/today/month/[ym]`, `/today/race/races`, `/library/metrics`, `/library/providers(/[group])`, `/library/story/[period]`, `/library/wellness(/[date])`, `/coach/plan/*`, `/data/settings*`.
  C2 계약을 화면별로 적용할 감사가 따로 필요하다. 정적 auth 화면(`/auth/*`, `/landing`, `/welcome`)은 감지 대상에서 제외하는 것을 검토한다.
- 감지기 `sweep_pw.mjs` 가 sr-only h1 과 보이는 h1, 그리고 h1 개수 2 이상을 구분하는 문제. 스크립트 영역이라 이번 설계 밖이다.

---

## 7. 개발 큐 단위

모든 verify 는 저장소 루트에서 실행한다. 테스트 파일은 `import.meta.url` 기준 상대 경로를 쓰므로 cwd 와 무관하게 동작한다.
`node --test frontend/tests/errorBranchH1.test.mjs` 로 루트 실행이 되는 것을 확인했다(3 통과).
전체 `test:unit` 은 현재 2건이 실패한다(§1.4). 그래서 verify 에는 단위별 대상 파일만 넣는다.

- AUD-4eee31-1 — 완료 기준: a11yStatic 전체 통과(H1 ratchet 복구).
- AUD-8c3aa4-1 — 완료 기준: navFromPath 가 null/undefined/url:null/정상 4케이스를 통과.
- AUD-8c3aa4-2 — 완료 기준: src 에 unsafe `from?.url.` 0건, month·library 레이아웃이 헬퍼 사용.
- AUD-295255-1 — 완료 기준: pageHeading 의 ok/empty/failed × childOwns 조합 테스트 통과.
- AUD-295255-2 — 완료 기준: today 가 failed 에서만 제목 h1, empty·ok 는 null(정적 계약 통과).
- AUD-68c84e-1 — 완료 기준: thread load 가 Failure 반환·LoadFailure 렌더·액션 오류 분리, fileSize 통과.
- AUD-295255-3 — 완료 기준: library/[id] 오류 분기에 h1 이 있고 허용 목록에서 제거됨.
- AUD-295255-4 — 완료 기준: metrics/providers/streams 가 pageHeading 을 쓰고 허용 목록에서 제거됨.
- AUD-4eee31-2 — 완료 기준: sources·laps 의 sr-only 복제 h1 이 없어지고 errorBranchH1 이 계약 테스트로 흡수됨.

```jsonl
{"id":"AUD-4eee31-1","parent":"AUD-4eee31","desc":"73d2efc2 회귀 복구: H1_IN_CHILD 에서 laps 제거","deps":[],"scope":["frontend/tests/a11yStatic.test.mjs"],"verify":["node --test frontend/tests/a11yStatic.test.mjs"]}
{"id":"AUD-8c3aa4-1","parent":"AUD-8c3aa4","desc":"null 안전 navFromPath 헬퍼(SPA enter 시 from.url=null) 추가와 단위 테스트","deps":[],"scope":["frontend/src/lib/navFrom.ts","frontend/tests/navFrom.test.mjs"],"verify":["node --test frontend/tests/navFrom.test.mjs"]}
{"id":"AUD-8c3aa4-2","parent":"AUD-8c3aa4","desc":"month·library 레이아웃 afterNavigate 를 navFromPath 로 교체, unsafe 패턴 정적 가드","deps":["AUD-8c3aa4-1"],"scope":["frontend/src/routes/today/month/[ym]/+page.svelte","frontend/src/routes/library/[id]/+layout.svelte","frontend/tests/navFromGuard.test.mjs"],"verify":["node --test frontend/tests/navFrom.test.mjs frontend/tests/navFromGuard.test.mjs frontend/tests/monthNav.test.mjs frontend/tests/fileSize.test.mjs"]}
{"id":"AUD-295255-1","parent":"AUD-295255","desc":"분기별 h1 결정 순수 헬퍼 pageHeading 추가와 단위 테스트","deps":[],"scope":["frontend/src/lib/a11y/pageHeading.ts","frontend/tests/pageHeading.test.mjs"],"verify":["node --test frontend/tests/pageHeading.test.mjs"]}
{"id":"AUD-295255-2","parent":"AUD-295255","desc":"today PageHead 를 pageHeading(failed 만 제목)으로 전환, heading null 허용목록 계약 테스트 신설","deps":["AUD-295255-1","AUD-4eee31-1"],"scope":["frontend/src/routes/today/+page.svelte","frontend/tests/pageHeadContract.test.mjs","frontend/tests/a11yStatic.test.mjs"],"verify":["node --test frontend/tests/pageHeading.test.mjs frontend/tests/pageHeadContract.test.mjs frontend/tests/a11yStatic.test.mjs"]}
{"id":"AUD-68c84e-1","parent":"AUD-68c84e","desc":"coach 스레드 load 를 Failure 채널로 전환하고 LoadFailure 렌더, 액션 오류 채널 분리","deps":["AUD-295255-2"],"scope":["frontend/src/lib/loadFailure.ts","frontend/src/routes/coach/[threadId]/+page.ts","frontend/src/routes/coach/[threadId]/+page.svelte","frontend/tests/coachThreadLoad.test.mjs","frontend/tests/errorBranchH1.test.mjs"],"verify":["node --test frontend/tests/coachThreadLoad.test.mjs frontend/tests/errorBranchH1.test.mjs frontend/tests/pageHeadContract.test.mjs frontend/tests/fileSize.test.mjs frontend/tests/a11yStatic.test.mjs"]}
{"id":"AUD-295255-3","parent":"AUD-295255","desc":"library/[id] 활동 상세 오류 분기에 pageHeading 적용","deps":["AUD-295255-2"],"scope":["frontend/src/routes/library/[id]/+page.svelte","frontend/tests/pageHeadContract.test.mjs","frontend/tests/a11yStatic.test.mjs"],"verify":["node --test frontend/tests/pageHeadContract.test.mjs frontend/tests/a11yStatic.test.mjs frontend/tests/fileSize.test.mjs"]}
{"id":"AUD-295255-4","parent":"AUD-295255","desc":"활동 하위 metrics·providers·streams 오류 분기에 pageHeading 적용","deps":["AUD-295255-3"],"scope":["frontend/src/routes/library/[id]/metrics/+page.svelte","frontend/src/routes/library/[id]/providers/+page.svelte","frontend/src/routes/library/[id]/streams/+page.svelte","frontend/tests/pageHeadContract.test.mjs","frontend/tests/a11yStatic.test.mjs"],"verify":["node --test frontend/tests/pageHeadContract.test.mjs frontend/tests/a11yStatic.test.mjs frontend/tests/fileSize.test.mjs"]}
{"id":"AUD-4eee31-2","parent":"AUD-4eee31","desc":"sources·laps 의 sr-only 복제 h1 을 pageHeading 계약으로 대체, errorBranchH1 흡수","deps":["AUD-295255-2","AUD-68c84e-1"],"scope":["frontend/src/routes/data/sources/[provider]/+page.svelte","frontend/src/routes/library/[id]/laps/+page.svelte","frontend/tests/errorBranchH1.test.mjs","frontend/tests/pageHeadContract.test.mjs","frontend/tests/a11yStatic.test.mjs"],"verify":["node --test frontend/tests/pageHeadContract.test.mjs frontend/tests/a11yStatic.test.mjs frontend/tests/fileSize.test.mjs"]}
```

메모: AUD-295255-2·-3·-4 와 AUD-4eee31-2 의 보이는 h1/sr-only 선택은 §5 D1 결정을 따른다. D1 이 확정되기 전에는 큐에서 실행하지 않는다.
