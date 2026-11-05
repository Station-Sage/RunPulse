// adapter-static fallback(SPA) 모드 — API 데이터 화면은 프리렌더할 수 없다.
import { redirect } from '@sveltejs/kit';
import { base } from '$app/paths';
import { installDemo, isDemoActive } from '$lib/demoMode';
import { authRedirect } from '$lib/auth/guard';
import { loadAuthSession } from '$lib/auth/session';

export const ssr = false;
export const prerender = false;

// 데모 중 새로고침해도 스냅샷 fetch 층을 다시 건다(실패하면 플래그가 지워져 일반 모드로 돌아간다).
export async function load({ url }: { url: URL }) {
	const demo = isDemoActive();
	if (demo) await installDemo().catch(() => undefined);
	const session = demo ? null : await loadAuthSession();
	const path = url.pathname.startsWith(base) ? url.pathname.slice(base.length) || '/' : url.pathname;
	const to = authRedirect(session, path, demo);
	if (to) redirect(307, `${base}${to}`);
	return { auth: session };
}
