# 설계: 오류·재시도 공통 (실패 분류 + 블록 오류 상태 + 재로드 키)

- 대상 증상: S-01, S-02, S-03, S-04 (99-summary 항목 5), E-23(아래 1.3 참고)
- 작성일: 2026-10-10 · 상태: 초안 (구현 전 사용자 결정 필요 항목 있음)
- 범위: `frontend/` v2 SPA 만. 서버 API·v1 템플릿은 바꾸지 않는다.

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
E-23(DemoBanner 시트 Esc)은 오류·재시도와 원인이 다르다. 오버레이 공통 설계(`overlay-common-behavior.md`, `use:modal`)에서 이미 적용 대상으로 잡혀 있으므로 이 문서에서는 설계하지 않는다. 묶음에서 빼고 그쪽으로 옮길지는 결정 필요 #7 에 둔다.

## 2. 설계안 (추천: A안)

### 2.1 전송 계층 정규화: `apiFetch` (수정)
- 모든 실패를 `ApiError` 로 정규화한다. 네트워크·abort 는 `status=0, code='NETWORK'`, JSON 이 아닌 응답은 `status=res.status, code='BAD_RESPONSE'` 로 둔다.
- 사용자의 `AbortController` 취소(`AbortError`)는 오류로 보지 않도록 `code='ABORTED'` 로 따로 표시해 화면이 무시할 수 있게 한다.

### 2.2 순수 분류 모듈: `lib/loadFailure.ts` (신규, DOM·Svelte 비의존)
- `classifyFailure(e) → { kind: 'not_found' | 'failed' | 'aborted', status, code, detail }`. 404 만 `not_found` 이고, 0·5xx·BAD_RESPONSE·알 수 없는 예외는 모두 `failed` 이다.
- `nullOn404(p)`: 404 일 때만 `null` 로 풀고 나머지 실패는 다시 던진다. 기존 `.catch(() => null)` 중 "없음이 정상인 경우"를 이것으로 바꾼다.
- `LoadResult<T> = { ok: true; data: T } | { ok: false; failure: Failure }`. load 반환 형태를 통일한다. 기존 `errorMessage: string | null` 을 대체한다.

### 2.3 표시: `ErrorState.svelte` 확장 (수정)
- `failure?: Failure` prop 을 추가한다. 주어지면 `kind` 에 따라 기본 문구와 상세(status/code)를 고른다. 기존 `message/detail` prop 은 그대로 둔다(하위 호환).
- `retrying` 상태를 둔다. `onRetry` 가 Promise 를 돌려주면 진행 중에 버튼을 비활성화해 연타를 막는다. `secondary` 스니펫으로 "← 목록으로" 같은 보조 링크를 같은 상자 안에 넣는다.
- `not_found` 는 재시도 대신 `EmptyState` 쪽 표현을 쓴다(구분 원칙은 이미 EmptyState 주석에 있다).

### 2.4 재로드 키: 라우트 load 에 `depends` 추가
- 키 명명: `app:plan-active`, `app:activity:{id}`, `app:activity-streams:{id}`, `app:metric:{slug}`. 재시도는 `invalidate(key)` 로 한다.
- 클라이언트 재요청 화면(활동 목록·대화 목록)은 기존 재요청 함수를 `onRetry` 에 연결한다.

### 2.5 라우트 적용
| 증상 | 화면 | 변경 |
|---|---|---|
| S-01 | `/coach/plan` | `getActivePlan` 에 `nullOn404` 적용. `failed` 면 ErrorState(재시도)를 보여주고, 빈 상태 CTA 처리는 결정 #2 에 따른다 |
| S-02 | `/library/{id}` 레이아웃 | 404 → "찾을 수 없음 + 목록으로", failed → ErrorState(재시도 + 목록으로) |
| S-03 | 스트림·메트릭 탭, `/library/metrics/{slug}` | 인라인 문구를 ErrorState(재시도 + 기존 되돌아가기 링크)로 교체 |
| S-04 | `/coach` 대화 목록, `/library/activities` | ErrorState 한 개만 남겨 중복을 없애고 재요청 함수에 연결 |

## 3. 변경 파일 표 (경로는 `frontend/` 기준)
| 파일 | 신규/수정 | 내용 | 예상 줄 수 |
|---|---|---|---|
| `src/lib/api/client.ts` | 수정 | 비JSON·네트워크·abort 정규화 | +20 (→ 약 55) |
| `src/lib/loadFailure.ts` | 신규 | `classifyFailure`, `nullOn404`, `LoadResult`, 기본 문구 매핑 | 약 60 |
| `src/lib/components/ErrorState.svelte` | 수정 | `failure`·`retrying`·`secondary` | +25 (→ 약 75) |
| `src/routes/coach/plan/+page.ts`, `+page.svelte` | 수정 | nullOn404 + depends + 오류 분기 | 각 +10 |
| `src/routes/library/[id]/+layout.ts`, `+layout.svelte` | 수정 | LoadResult + 404/failed 분기 | 각 +10 |
| `src/routes/library/[id]/streams/+page.ts`·`.svelte`, `[id]/metrics/+page.ts`·`.svelte` | 수정 | ErrorState 교체 + depends | 각 ±10 |
| `src/routes/library/metrics/[slug]/+page.ts`·`.svelte` | 수정 | 같음 | 각 ±10 |
| `src/routes/library/activities/+page.ts`·`.svelte` | 수정 | ErrorState + 재요청 연결 | 각 ±10 |
| `src/routes/coach/+page.svelte` | 수정 | **현재 310줄로 규칙(300줄) 초과**. 대화 목록 블록을 아래 컴포넌트로 빼면서 ErrorState 적용 | -60 |
| `src/lib/components/coach/ThreadList.svelte` | 신규 | 최근 대화 목록 + 빈/오류 상태 | 약 70 |
| `tests/loadFailure.test.mjs` | 신규 | 분류(0/404/500/502 HTML/abort/임의 예외), nullOn404 | 약 70 |
| `tests/apiClient.test.mjs` | 신규 | `fetch` 스텁으로 정규화 검증 | 약 60 |

합계: 신규 4개, 수정 약 14개, 순증 약 +300줄.

## 4. 적용 순서와 검증
1. **전송·분류 (화면 변화 없음)**: `client.ts` 와 `loadFailure.ts` 를 고치고 단위 테스트 2개를 추가한다. 착수 전에 `/coach/plan/active` 가 "플랜 없음"일 때 실제로 404 와 오류 본문을 주는지 서버 응답으로 확인한다. 200+null 이면 `nullOn404` 적용 방식을 바꿔야 한다. 검증: `npm run test:unit`, `python3 -m pytest tests/` 회귀.
2. **ErrorState 확장**: 기존 사용처 5곳(Today·Library 홈)의 모습이 바뀌지 않는지 브라우저로 확인한다(prop 하위 호환).
3. **S-01 플랜**: 리뷰 재현 절차(`/api/v1/coach/plan*` abort, 502 HTML)로 진입해 빈 상태 CTA 대신 오류 + 재시도가 나오는지 본다. 재시도에 성공하면 플랜이 표시돼야 한다. 실제로 플랜이 없는 계정(404)은 기존 빈 상태 그대로여야 한다.
4. **S-02·S-03 활동 상세·메트릭**: abort, 500, 존재하지 않는 id 세 경우를 확인한다. 404 일 때만 "찾을 수 없음"이 나와야 하고, 서브탭 전환 때 레이아웃 데이터를 다시 요청하지 않는 기존 동작(P-4)이 유지되는지 네트워크 탭으로 본다.
5. **S-04 목록**: `/api/v1/coach/threads*` 를 abort 하면 문구가 한 번만 나오고 재시도가 동작해야 한다. 활동 목록에서는 필터를 유지한 채 재시도되는지 본다. `coach/+page.svelte` 가 300줄 이하인지 확인한다.
6. `python3 scripts/check_docs.py`, `frontend/src/lib/` GUIDE·docstring 반영.

## 5. 호환성·v1 의존
- `ApiError` 의 `message` 가 네트워크 오류에서도 채워지므로 `e instanceof ApiError ? e.message : 고정문구` 패턴을 쓰는 다른 화면(대상 밖, 예: `[id]/providers/+page.ts`, replan)의 문구가 달라진다. 이 화면들은 동작이 바뀌지 않고 문구만 바뀐다.
- load 반환 필드 `errorMessage` → `LoadResult` 전환은 해당 라우트의 `+page.svelte` 와 함께 바꿔야 한다. 한 라우트씩 원자적으로 바꾼다.
- `SyntaxError` 를 직접 잡는 코드가 있다면 동작이 달라진다. 구현 전에 `grep -rn SyntaxError frontend/src` 로 확인한다.
- v1(Flask 템플릿)은 건드리지 않는다. 서버 오류 본문 형식 `{error:{code,message}}` 에 의존하지만 v1 전용은 아니다. v1 이 제거돼도 영향이 없다.

## 6. 대안 비교
| | A. 분류 모듈 + ErrorState 확장 + depends/invalidate (추천) | B. load 에서 SvelteKit `error(status)` throw → `+error.svelte` 경계 |
|---|---|---|
| 블록 단위 오류 | 가능(탭·헤더 유지) | 레이아웃 아래가 통째로 오류 페이지로 바뀌어 탭·헤더가 사라진다 |
| 부분 실패(보조 블록) | 같은 패턴으로 표현 | 표현 불가. 결국 A 가 따로 필요하다 |
| 재시도 | `invalidate(key)` 로 해당 로드만 | `invalidateAll`·전체 재진입 |
| 변경 규모 | 중 | 소(라우트마다 throw) |
B 는 404 전용 경계로만 일부 섞어 쓸 수 있다(결정 #6).

## 7. 결정 필요
1. **문구**: 장애·없음·네트워크 끊김별 문구. 기존 "불러오지 못했어요" 하나로 통일할지, 원인(연결 끊김 / 서버 오류)을 구분해 보일지 정해야 한다. 구분하면 정확하지만 문구 관리가 늘어난다.
2. **S-01 플랜 장애 시 "새 프로그램 만들기" CTA**: (a) 숨김: 오조작은 막지만 진입로가 사라진다. (b) 비활성 + 설명: 이유가 드러나지만 화면이 복잡해진다. (c) 경고 문구와 함께 유지: 자유도는 높지만 S-01 위험이 남는다.
3. **자동 재시도**: 수동 버튼만 둘지, 첫 실패 뒤 백오프 1회를 자동으로 할지 정해야 한다. 자동은 일시 장애를 감추지만 응답이 늦어지고 서버 부하가 늘어난다.
4. **오류 상세 노출**: status/code 를 "상세 보기"에 계속 보일지, 개발 모드에서만 보일지 정해야 한다.
5. **보조 블록 부분 실패**(`coach/plan/[id]` 의 조정·적응·재계획 `.catch(() => null)`): 이번에 compact 오류로 드러낼지, 지금처럼 조용히 숨길지 정해야 한다. 드러내면 투명해지지만 오류 노출이 늘어난다.
6. **404 표현 위치**: 라우트 안 EmptyState 로 둘지, `+error.svelte` 경계로 보낼지 정해야 한다.
7. **E-23**: 이 묶음에서 빼고 오버레이 공통 설계로 일원화할지 정해야 한다.

## 8. 범위 밖 메모
- E-23·S-08 Esc/포커스는 `overlay-common-behavior.md` 소관이다.
- `coach/plan/new` 등 이미 오류 문구가 있는 다른 화면의 문구 통일은 결정 #1 이후 별도로 다룬다.
- 오래된 탭 청크 404(E-04)는 배포·라우터 수준 문제라 이 설계에 넣지 않는다.
