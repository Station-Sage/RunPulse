import { redirect } from '@sveltejs/kit';
import { base } from '$app/paths';

// Today as Gateway — 하단 3탭의 기본 진입점 (00-diagnostic-and-direction.md §5.1).
export function load() {
	redirect(307, `${base}/today`);
}
