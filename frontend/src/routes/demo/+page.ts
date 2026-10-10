import { redirect } from '@sveltejs/kit';
import { base } from '$app/paths';
import { installDemo } from '$lib/demoMode';

// /demo 진입 — 스냅샷 fetch 층을 건 뒤 Today(S3)로 보낸다. 스냅샷을 못 읽으면 오류 화면.
export async function load({ url }: { url: URL }) {
	try {
		await installDemo();
	} catch {
		return { failed: true };
	}
	const to = url.searchParams.get('to') ?? '';
	redirect(307, `${base}${/^\/[a-z0-9/_-]*$/i.test(to) ? to : '/today'}`);
}
