# 설계: 오류·재시도 공통 (실패 분류 + 블록 오류 상태 + 재로드 키)

- 대상 증상: S-01, S-02, S-03, S-04 (99-summary 항목 5). E-23 은 ERR-7 결정으로 `overlay-common-behavior.md` 로 이관
- 작성일: 2026-10-10 · 상태: 설계 확정 — ERR-1~7 결정 반영(2026-10-11). 구현 가능
- 변경 이력: 2026-10-11 설계서 동기화(ERR-1~7 결정 반영, "결정 필요" → "결정됨")
- 범위: `frontend/` v2 SPA 만. 서버 API 는 바꾸지 않는다.

## 1. 근본 원인

### 1.1 실패가 분류되지 않고 "없음"으로 뭉개진다 (S-01, S-02)
- `lib/api/client.ts` `apiFetch` 는 `await res.json()` 을 먼저 호출한다. 502 HTML 이면 여기서 `SyntaxError`, abort·오프라인이면 `fetch` 가 `TypeError` 를 던진다. 둘 다 `ApiError` 가 아니어서 status·code 가 사라진다.
- 로드 함수는 이런 실패를 `.catch(() => null)` 로 받거나(`coach/plan/+page.ts` 의 `getActivePlan`), `ApiError` 가 아닌 오류를 고정 문자열 하나로 바꾼다(`library/[id]/+layout.ts`, `streams/+page.ts`, `metrics/[slug]/+page.ts`, `activities/+page.ts`).
- 그래서 화면은 "404 없음"과 "일시 장애"를 구별할 정보를 받지 못한다. 플랜 장애가 "플랜 없음 → 새 프로그램 만들기" 로 보이고(S-01), 활동 요약 500이 "활동을 찾을 수 없습니다" 로 보이는(S-02) 원인이 같다.

### 1.2 재시도 경로가 라우트마다 없거나 제각각이다 (S-03, S-04)
- 공통 `lib/components/ErrorState.svelte`(메시지 + 다시 시도 + 접힌 상세)가 이미 있지만 Today·Library 홈 블록에서만 쓴다. 대상 라우트들은 `<p>…불러올 수 없습니다</p>` 를 인라인으로 직접 그린다.
- 재시도에는 "로드를 다시 실행하는 손잡이"가 필요하다. Today 는 `depends('app:today')` + `invalidate` 로 이를 갖췄지만 대상 라우트의 load 에는 키가 없다. 클라이언트에서 직접 다시 받는 화면(활동 목록, Coach 대화 목록)은 재요청 함수가 있어도 오류 UI 에 연결돼 있지 않다.
- S-04 의 문구 중복은 제목과 `errorMessage` 를 두 줄로 나란히 찍기 때문이다. 대체 문구가 제목과 거의 같은 문장이라 두 번 보인다.

### 1.3 E-23 처리
E-23(DemoBanner 시트 Esc)은 오류·재시도와 원인이 다르다. ERR-7 결정에 따라 이 문서에서 빼고 오버레이 공통 설계(`overlay-common-behavior.md`, `use:modal`)로 일원화했다.

## 2. 설계안 (A안)

### 2.1 전송 계층 정규화: `apiFetch` (수정)
- 모든 실패를 `ApiError` 로 정규화한다. 네트워크·abort 는 `status=0, code='NETWORK'`, JSON 이 아닌 응답은 `status=res.status, code='BAD_RESPONSE'` 로 둔다.
- 사용자의 `AbortController` 취소(`AbortError`)는 오류로 보지 않도록 `code='ABORTED'` 로 따로 표시해 화면이 무시할 수 있게 한다.
- 자동 재시도는 하지 않는다(ERR-3). 재시도는 항상 사용자의 "다시 시도" 버튼으로만 한다.

### 2.2 순수 분류 모듈: `lib/loadFailure.ts` (신규, DOM·Svelte 비의존)
- `classifyFailure(e) → { kind: 'not_found' | 'network' | 'server' | 'aborted', status, code, detail }`. 404 → `not_found`, status 0·`NETWORK` → `network`(연결 끊김), 5xx·`BAD_RESPONSE`·그 밖의 4xx·알 수 없는 예외 → `server`(서버 오류).
- `failureMessage(kind)`: 문구 매핑(ERR-1). **연결 끊김**과 **서버 오류** 두 가지만 둔다. 문구 초안: network "연결이 끊겨 불러오지 못했어요. 연결을 확인하고 다시 시도해 주세요." / server "서버 오류로 불러오지 못했어요. 잠시 후 다시 시도해 주세요." 404 없음은 오류 문구가 아니라 화면별 EmptyState 문구를 쓴다(ERR-6).
- `nullOn404(p)`: 404 일 때만 `null` 로 풀고 나머지 실패는 다시 던진다. 기존 `.catch(() => null)` 중 "없음이 정상인 경우"를 이것으로 바꾼다.
- `LoadResult<T> = { ok: true; data: T } | { ok: false; failure: Failure }`. load 반환 형태를 통일한다. 기존 `errorMessage: string | null` 을 대체한다.

### 2.3 표시: `ErrorState.svelte` 확장 (수정)
- `failure?: Failure` prop 을 추가한다. 주어지면 `kind` 에 따라 2.2 의 두 문구 중 하나를 고른다. 기존 `message/detail` prop 은 그대로 둔다(하위 호환).
- 상세(ERR-4): status/code 는 **"상세 보기" 펼침에 항상** 제공한다(기본 접힘, 개발 모드 한정 아님).
- `retrying` 상태를 둔다. `onRetry` 가 Promise 를 돌려주면 진행 중에 버튼을 비활성화해 연타를 막는다. `secondary` 스니펫으로 "← 목록으로" 같은 보조 링크를 같은 상자 안에 넣는다.
- `compact` prop(ERR-5): 보조 블록용 한 줄 형태(문구 + 다시 시도 + 상세 보기 펼침). 블록 높이를 크게 바꾸지 않는다.
- `not_found` 는 ErrorState 로 그리지 않는다. 라우트 안에서 `EmptyState` 로 표현한다(ERR-6, 구분 원칙은 EmptyState 주석에 있다). `+error.svelte` 경계로 보내지 않는다.

### 2.4 재로드 키: 라우트 load 에 `depends` 추가
- 키 명명: `app:plan-active`, `app:activity:{id}`, `app:activity-streams:{id}`, `app:metric:{slug}`. 재시도는 `invalidate(key)` 로 한다.
- 클라이언트 재요청 화면(활동 목록·대화 목록)은 기존 재요청 함수를 `onRetry` 에 연결한다.
- 보조 블록(ERR-5)은 페이지 전체 키를 무효화하지 않고, 그 블록의 API 함수만 다시 호출한다(블록 단위 재시도).

### 2.5 라우트 적용
| 증상 | 화면 | 변경 |
|---|---|---|
| S-01 | `/coach/plan` | `getActivePlan` 에 `nullOn404` 적용. 404 → 기존 빈 상태(EmptyState + "새 프로그램 만들기"). network/server → ErrorState(재시도) + **"새 프로그램 만들기" 비활성 + 이유 한 줄**("현재 플랜을 확인할 수 없어 새 프로그램을 만들 수 없어요. 다시 시도해 주세요." — 문구 초안, ERR-2) |
| S-01 보조 | `/coach/plan/[id]` 조정·적응·재계획 블록 | `.catch(() => null)` 제거. 실패 시 해당 블록 자리에 compact ErrorState + 블록 단위 재시도(ERR-5). 404(데이터 없음)는 지금처럼 블록 숨김 |
| S-02 | `/library/{id}` 레이아웃 | 404 → 라우트 안 EmptyState("찾을 수 없음 + 목록으로"), network/server → ErrorState(재시도 + 목록으로) |
| S-03 | 스트림·메트릭 탭, `/library/metrics/{slug}` | 인라인 문구를 ErrorState(재시도 + 기존 되돌아가기 링크)로 교체 |
| S-04 | `/coach` 대화 목록, `/library/activities` | ErrorState 한 개만 남겨 중복을 없애고 재요청 함수에 연결 |

## 3. 변경 파일 표 (경로는 `frontend/` 기준)
| 파일 | 신규/수정 | 내용 | 예상 줄 수 |
|---|---|---|---|
| `src/lib/api/client.ts` | 수정 | 비JSON·네트워크·abort 정규화 | +20 (→ 약 55) |
| `src/lib/loadFailure.ts` | 신규 | `classifyFailure`(4종), `failureMessage`(2문구), `nullOn404`, `LoadResult` | 약 65 |
| `src/lib/components/ErrorState.svelte` | 수정 | `failure`·`retrying`·`secondary`·`compact`, 상세 보기 상시 | +30 (→ 약 80) |
| `src/routes/coach/plan/+page.ts`, `+page.svelte` | 수정 | nullOn404 + depends + 오류 분기 + CTA 비활성·이유 | 각 +12 |
| `src/routes/coach/plan/[id]/+page.ts`, `+page.svelte` | 수정 | 보조 블록 실패 노출(compact) + 블록 재시도 | 각 +10 |
| `src/routes/library/[id]/+layout.ts`, `+layout.svelte` | 수정 | LoadResult + 404(EmptyState)/실패 분기 | 각 +10 |
| `src/routes/library/[id]/streams/+page.ts`·`.svelte`, `[id]/metrics/+page.ts`·`.svelte` | 수정 | ErrorState 교체 + depends | 각 ±10 |
| `src/routes/library/metrics/[slug]/+page.ts`·`.svelte` | 수정 | 같음 | 각 ±10 |
| `src/routes/library/activities/+page.ts`·`.svelte` | 수정 | ErrorState + 재요청 연결 | 각 ±10 |
| `src/routes/coach/+page.svelte` | 수정 | **현재 310줄로 규칙(300줄) 초과**. 대화 목록 블록을 아래 컴포넌트로 빼면서 ErrorState 적용 | -60 |
| `src/lib/components/coach/ThreadList.svelte` | 신규 | 최근 대화 목록 + 빈/오류 상태 | 약 70 |
| `tests/loadFailure.test.mjs` | 신규 | 분류(0/404/500/502 HTML/abort/임의 예외 → 4종), 문구 2종 매핑, nullOn404 | 약 75 |
| `tests/apiClient.test.mjs` | 신규 | `fetch` 스텁으로 정규화 검증 | 약 60 |

합계: 신규 4개, 수정 약 16개, 순증 약 +330줄.

## 4. 적용 순서와 검증
1. **전송·분류 (화면 변화 없음)**: `client.ts` 와 `loadFailure.ts` 를 고치고 단위 테스트 2개를 추가한다. 착수 전에 `/coach/plan/active` 가 "플랜 없음"일 때 실제로 404 와 오류 본문을 주는지 서버 응답으로 확인한다. 200+null 이면 `nullOn404` 적용 방식을 바꿔야 한다. 검증: `npm run test:unit`, `python3 -m pytest tests/` 회귀.
2. **ErrorState 확장**: 기존 사용처 5곳(Today·Library 홈)의 모습이 바뀌지 않는지 브라우저로 확인한다(prop 하위 호환). 상세 보기가 운영 빌드에서도 펼쳐지는지 본다.
3. **S-01 플랜**: 리뷰 재현 절차(`/api/v1/coach/plan*` abort → 연결 끊김 문구, 502 HTML → 서버 오류 문구)로 진입해 오류 + 재시도와 비활성 "새 프로그램 만들기"·이유 문구가 나오는지 본다. 재시도에 성공하면 플랜이 표시돼야 한다. 실제로 플랜이 없는 계정(404)은 기존 빈 상태(CTA 활성) 그대로여야 한다. 자동 재요청이 없는지 네트워크 탭으로 본다.
4. **S-01 보조 블록**: `coach/plan/[id]` 의 조정·적응·재계획 API 를 하나씩 abort 해 그 블록만 compact 오류가 나오고, 블록 재시도가 그 API 만 다시 부르는지 본다.
5. **S-02·S-03 활동 상세·메트릭**: abort, 500, 존재하지 않는 id 세 경우를 확인한다. 404 일 때만 라우트 안 "찾을 수 없음"(탭·헤더 유지)이 나와야 하고, 서브탭 전환 때 레이아웃 데이터를 다시 요청하지 않는 기존 동작(P-4)이 유지되는지 네트워크 탭으로 본다.
6. **S-04 목록**: `/api/v1/coach/threads*` 를 abort 하면 문구가 한 번만 나오고 재시도가 동작해야 한다. 활동 목록에서는 필터를 유지한 채 재시도되는지 본다. `coach/+page.svelte` 가 300줄 이하인지 확인한다.
7. `python3 scripts/check_docs.py`, `frontend/src/lib/` GUIDE·docstring 반영.

## 5. 호환성
- `ApiError` 의 `message` 가 네트워크 오류에서도 채워지므로 `e instanceof ApiError ? e.message : 고정문구` 패턴을 쓰는 다른 화면(대상 밖, 예: `[id]/providers/+page.ts`, replan)의 문구가 달라진다. 이 화면들은 동작이 바뀌지 않고 문구만 바뀐다.
- load 반환 필드 `errorMessage` → `LoadResult` 전환은 해당 라우트의 `+page.svelte` 와 함께 바꿔야 한다. 한 라우트씩 원자적으로 바꾼다.
- `SyntaxError` 를 직접 잡는 코드가 있다면 동작이 달라진다. 구현 전에 `grep -rn SyntaxError frontend/src` 로 확인한다.
- `coach/plan/[id]` 보조 블록은 지금 조용히 숨던 실패가 화면에 드러난다(ERR-5 의도된 변화).
- 서버 오류 본문 형식 `{error:{code,message}}` 에 의존한다(서버 API 변경 없음).

## 6. 대안 비교 (기록용 — A안 채택)
| | A. 분류 모듈 + ErrorState 확장 + depends/invalidate (채택) | B. load 에서 SvelteKit `error(status)` throw → `+error.svelte` 경계 |
|---|---|---|
| 블록 단위 오류 | 가능(탭·헤더 유지) | 레이아웃 아래가 통째로 오류 페이지로 바뀌어 탭·헤더가 사라진다 |
| 부분 실패(보조 블록) | 같은 패턴으로 표현 | 표현 불가. 결국 A 가 따로 필요하다 |
| 재시도 | `invalidate(key)` 로 해당 로드만 | `invalidateAll`·전체 재진입 |
| 변경 규모 | 중 | 소(라우트마다 throw) |
404 도 경계로 보내지 않고 라우트 안 EmptyState 로 둔다(ERR-6). B 는 쓰지 않는다.

## 7. 결정됨 (2026-10-11)
1. **ERR-1 문구**: 연결 끊김 / 서버 오류 두 가지로 구분, 404 없음은 별도(EmptyState). 근거: 사용자가 할 일(연결 확인 vs 기다림)이 다름(2.2).
2. **ERR-2 S-01 CTA**: (b) 플랜 장애 시 "새 프로그램 만들기" 비활성 + 이유 설명. 근거: 오조작 방지와 진입로 유지의 절충(2.5).
3. **ERR-3 자동 재시도**: 없음, 수동 재시도 버튼만. 근거: 장애를 숨기지 않고 서버 부하를 늘리지 않음(2.1).
4. **ERR-4 오류 상세**: status/code 를 "상세 보기" 펼침에 항상 제공(기본 접힘)(2.3).
5. **ERR-5 보조 블록 부분 실패**: compact 오류로 노출, 블록 단위 재시도(2.3·2.4·2.5).
6. **ERR-6 404 표현 위치**: 라우트 안 EmptyState. 근거: 탭·헤더 유지(6절).
7. **ERR-7 E-23**: 이 묶음에서 빼고 오버레이 설계(`use:modal`)로 일원화(1.3).

## 8. 범위 밖 메모
- E-23·S-08 Esc/포커스는 `overlay-common-behavior.md` 소관이다.
- `coach/plan/new` 등 이미 오류 문구가 있는 다른 화면의 문구를 ERR-1 두 문구로 통일하는 작업은 별도로 다룬다.
- 오래된 탭 청크 404(E-04)는 배포·라우터 수준 문제라 이 설계에 넣지 않는다.

## 9. 동기화 중 발견한 충돌/확인 필요
- ERR-1 은 문구를 "두 가지로 구분"까지만 정했다. 2.2·2.5 의 실제 문장은 초안이며 확정 문구가 아니다.
- ERR-1 의 두 분류에 4xx(404 제외, 예: 400·409)와 분류할 수 없는 예외가 어느 쪽인지는 결정에 없다. 이 문서는 `server` 쪽에 넣었다.
- `coach/plan/[id]/+page.svelte` 의 현재 줄 수는 확인하지 않았다. ERR-5 반영(+10) 뒤 300줄을 넘는지 구현 전에 확인이 필요하다.
