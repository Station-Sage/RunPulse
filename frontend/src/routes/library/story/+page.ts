import { redirect } from '@sveltejs/kit';
import { base } from '$app/paths';

// /library/story → 이번 달 이야기로 이동
export function load() {
	const ym = new Date().toLocaleDateString('sv-SE').slice(0, 7);
	redirect(307, `${base}/library/story/${ym}`);
}
