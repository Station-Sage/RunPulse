// 분해 패널 선요청(A-6) — 차트 위 호버/pointerdown에서 같은 (slug,date) explain을 미리 받아 두고 패널이 재사용한다.
export function createExplainCache<T>(fetcher: (slug: string, date: string) => Promise<T>, ttlMs = 30_000, now: () => number = Date.now) {
	const store = new Map<string, { p: Promise<T>; ts: number }>();
	function get(slug: string, date: string): Promise<T> {
		const key = `${slug}|${date}`;
		const hit = store.get(key);
		if (hit && now() - hit.ts < ttlMs) return hit.p;
		const p = fetcher(slug, date);
		store.set(key, { p, ts: now() });
		p.catch(() => store.delete(key)); // 실패는 캐시하지 않는다
		return p;
	}
	return { get, prefetch: (slug: string, date: string) => void get(slug, date).catch(() => {}) };
}
