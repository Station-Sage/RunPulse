import { redirect } from '@sveltejs/kit';
import { base } from '$app/paths';
import { installDemo } from '$lib/demoMode';

// /demo 진입 — 스냅샷 fetch 층을 건 뒤 Today(S3)로 보낸다. 스냅샷을 못 읽으면 오류 화면.
export async function load() {
	try {
		await installDemo();
	} catch {
		return { failed: true };
	}
	redirect(307, `${base}/today`);
}
