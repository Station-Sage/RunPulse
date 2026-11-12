// 첫 로드 API 선요청 표(S4-90, cwv-measurement-2026-11.md 후보 ②).
// 키 = SvelteKit 라우트 id, 값 = 그 화면 로더가 "기다리는" GET 경로(API_BASE '/api/v1' 뒤). `{param}` 은 라우트 파라미터 —
// 숫자일 때만 채운다(아니면 선요청 안 함). 경로 문자열은 lib/api/*.ts 의 apiFetch 호출과 **글자 그대로** 같아야
// apiFetch 가 넘겨받는다(다르면 선요청이 버려지고 요청만 한 번 더 나감 — tests/routePreload.test.mjs 가 대조).
// 스트리밍(기다리지 않는) 블록·쿼리스트링이 붙는 목록 요청은 넣지 않는다 — 대역폭을 청크와 나눠 쓰기 때문.

/** 모든 화면: 루트 레이아웃 load 가 기다리는 인증 세션. */
export const BOOT_ALWAYS = ['/auth/session'];

export const BOOT_ROUTES = {
	'/today': ['/today'],
	// coach 로더는 7건을 Promise.all 로 전부 기다린다
	'/coach': ['/coach/threads', '/coach/plan/active', '/today/checkin', '/today/race-hub', '/coach/engine', '/coach/suggestions', '/today'],
	'/coach/plan/[id]': ['/coach/plan/{id}'],
	'/library/[id]': ['/library/activities/{id}'],
	'/data/settings': ['/settings/mcp-tokens']
};
