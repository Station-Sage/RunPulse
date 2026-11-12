// 첫 로드 API 선요청 인계(S4-90). build/index.html 의 인라인 스크립트(frontend/scripts/route-preload.mjs 생성)가
// HTML 파싱 시점에 쏜 GET 응답을 apiFetch 가 같은 경로로 처음 부를 때 한 번만 넘겨받는다.
// 넘겨받지 않는 경우(→ 평소처럼 새 요청): init 을 준 호출(메서드·본문·signal·헤더 지정), 이미 쓴 경로, 오래된 응답, 상자 없음(데모·테스트).
// 루트 레이아웃 onMount 에서 clearBootPrefetch() — 첫 화면 로더가 끝난 뒤 남은 선요청이 나중 이동에 재사용되지 않게.

export const BOOT_KEY = '__rpBoot';
/** 선요청 응답을 받아 쓸 수 있는 최대 경과(ms, performance.now 기준). 첫 화면 로더는 그 안에 돈다. */
export const BOOT_MAX_AGE_MS = 20000;

interface BootEntry {
	p: Promise<Response>;
	t: number;
}
type BootHost = { [BOOT_KEY]?: Record<string, BootEntry> };

function now(): number {
	return typeof performance !== 'undefined' ? performance.now() : 0;
}

/** `path`(API_BASE 뒤) 의 선요청 응답 Promise. 없거나 조건이 안 맞으면 null. 꺼낸 항목은 지운다(1회용). */
export function takeBootResponse(path: string, init?: RequestInit, host: BootHost = globalThis as BootHost, at = now()): Promise<Response> | null {
	if (init !== undefined) return null;
	const box = host[BOOT_KEY];
	const entry = box?.[path];
	if (!box || !entry) return null;
	delete box[path];
	if (at - entry.t > BOOT_MAX_AGE_MS) return null;
	return entry.p;
}

/** 남은 선요청을 버린다(응답 본문은 읽지 않으므로 그대로 GC). */
export function clearBootPrefetch(host: BootHost = globalThis as BootHost): void {
	delete host[BOOT_KEY];
}
