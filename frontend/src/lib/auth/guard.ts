// 인증 라우트 가드 — 순수 함수(DOM·Svelte 비의존). design-2026-11-auth §E.
export type AuthState = 'anonymous' | 'pending' | 'active';
export interface AuthSession {
	mode: 'legacy' | 'registry';
	state: AuthState;
	email: string | null;
}

const PUBLIC_PREFIXES = ['/landing', '/demo', '/auth'];

export function isPublicRoute(path: string): boolean {
	return PUBLIC_PREFIXES.some((p) => path === p || path.startsWith(`${p}/`));
}

/** `path` 는 base(/v2) 를 뗀 경로. 이동이 필요하면 base 없는 목적지를, 아니면 null. legacy 모드·데모는 가드하지 않는다. */
export function authRedirect(session: AuthSession | null, path: string, demo: boolean): string | null {
	if (!session || session.mode !== 'registry' || demo) return null;
	if (session.state === 'active') return path === '/landing' || path.startsWith('/auth/') ? '/today' : null;
	if (session.state === 'pending') return path === '/auth/pending' || path === '/landing' || path === '/demo' ? null : '/auth/pending';
	return isPublicRoute(path) ? null : '/landing';
}

/** 로그인 후 돌아올 경로 — 서버 safe_next 와 같은 규칙(`/v2/` 아래 안전 문자만). */
export function loginHref(next: string): string {
	const ok = /^\/v2\/[A-Za-z0-9/_-]*$/.test(next) && !next.includes('//');
	return `/auth/start?next=${encodeURIComponent(ok ? next : '/v2/today')}`;
}

export function inviteErrorMessage(status: number, code: string): string {
	if (code === 'INVITE_INVALID') return '초대코드가 올바르지 않거나 이미 사용됐어요.';
	if (code === 'RATE_LIMITED') return '시도가 너무 많아요. 잠시 후 다시 시도해 주세요.';
	if (code === 'SIGNUP_CAP') return '오늘 가입 가능 인원이 가득 찼어요. 내일 다시 시도해 주세요.';
	if (code === 'NOT_ALLOWED') return '가입이 허용되지 않은 계정이에요.';
	if (status === 503) return '계정 준비에 실패했어요. 잠시 후 다시 시도해 주세요.';
	return '코드를 확인하지 못했어요. 다시 시도해 주세요.';
}
