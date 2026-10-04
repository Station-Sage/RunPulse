// Library 2단 화면 뒤로가기 — 메트릭 브라우저의 마지막 필터 URL 기억(sessionStorage) + from=today 칩.
const KEY = 'rp.library.metrics.search';

export function saveMetricsSearch(search: string, store: Pick<Storage, 'setItem' | 'removeItem'> | undefined = safeStore()) {
	try {
		if (search && search !== '?') store?.setItem(KEY, search);
		else store?.removeItem(KEY);
	} catch {
		/* 저장 불가 환경은 무시 */
	}
}

export function metricsBackHref(base: string, store: Pick<Storage, 'getItem'> | undefined = safeStore()): string {
	let saved = '';
	try {
		saved = store?.getItem(KEY) ?? '';
	} catch {
		saved = '';
	}
	return `${base}/library/metrics${saved.startsWith('?') ? saved : ''}`;
}

export const fromToday = (search: string) => new URLSearchParams(search).get('from') === 'today';

function safeStore(): Storage | undefined {
	try {
		return typeof sessionStorage === 'undefined' ? undefined : sessionStorage;
	} catch {
		return undefined;
	}
}
