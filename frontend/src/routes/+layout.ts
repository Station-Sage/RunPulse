// adapter-static fallback(SPA) 모드 — API 데이터 화면은 프리렌더할 수 없다.
import { installDemo, isDemoActive } from '$lib/demoMode';

export const ssr = false;
export const prerender = false;

// 데모 중 새로고침해도 스냅샷 fetch 층을 다시 건다(실패하면 플래그가 지워져 일반 모드로 돌아간다).
export async function load() {
	if (isDemoActive()) await installDemo().catch(() => undefined);
}
