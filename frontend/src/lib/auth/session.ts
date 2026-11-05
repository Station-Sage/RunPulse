// 인증 세션 — 앱 시작 시 한 번 읽는다. 조회 실패는 가드하지 않는다(null).
import { apiFetch } from '$lib/api/client';
import type { AuthSession } from './guard';

let cached: AuthSession | null = null;

export async function loadAuthSession(force = false): Promise<AuthSession | null> {
	if (cached && !force) return cached;
	try {
		cached = await apiFetch<AuthSession>('/auth/session');
	} catch {
		cached = null;
	}
	return cached;
}

export function setAuthSession(s: AuthSession | null): void {
	cached = s;
}
