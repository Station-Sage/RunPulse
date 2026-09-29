interface Entry<T> {
	data: T;
	ts: number;
}

const cache = new Map<string, Entry<unknown>>();

/** 이 시간 안의 재방문은 네트워크 없이 캐시만 보여준다(그 이후 재방문에서만 백그라운드 갱신 1회 트리거). */
export const SWR_STALE_MS = 30_000;

/**
 * stale-while-revalidate 캐시 — 탭 재방문 시 이전 데이터를 즉시 보여주고, staleMs 지난
 * 경우에만 백그라운드에서 새로 받아 invalidateFn(key)로 조용히 갱신한다(02-performance.md P-5).
 * `$app/navigation`의 invalidate는 SvelteKit 런타임에서만 동작하므로 여기선 주입받는다
 * (drillStackCore.ts/drillStack.ts와 같은 순수-로직/프레임워크-연동 분리 패턴, 노드 단위테스트 가능하게).
 * 최초 방문(캐시 없음)은 기존과 동일하게 fetch를 기다린다.
 */
export async function swrLoad<T>(
	key: string,
	fetcher: () => Promise<T>,
	invalidateFn: (key: string) => unknown,
	staleMs: number = SWR_STALE_MS
): Promise<T> {
	const hit = cache.get(key) as Entry<T> | undefined;
	if (hit) {
		if (Date.now() - hit.ts >= staleMs) {
			fetcher()
				.then((fresh) => {
					cache.set(key, { data: fresh, ts: Date.now() });
					return invalidateFn(key);
				})
				.catch(() => {
					/* 백그라운드 갱신 실패는 무시 — 화면엔 이전 캐시가 그대로 남는다 */
				});
		}
		return hit.data;
	}
	const data = await fetcher();
	cache.set(key, { data, ts: Date.now() });
	return data;
}

/** 스트리밍 블록이 실패했을 때 캐시를 비워 "다시 시도"가 실제로 재요청하게 한다. */
export function swrEvict(key: string): void {
	cache.delete(key);
}

/** 테스트 전용 — 모듈 스코프 캐시를 비운다. */
export function _clearSwrCacheForTest(): void {
	cache.clear();
}
