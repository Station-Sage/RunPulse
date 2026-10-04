// 메트릭 브라우저 검색 — 한글명·약어·영문 slug·라벨에 대한 부분 일치(대소문자 무시).
import type { MetricBrowserEntry } from '$lib/types';

export function matchesMetric(m: Pick<MetricBrowserEntry, 'name' | 'label' | 'name_ko' | 'abbr'>, query: string): boolean {
	const q = query.trim().toLowerCase();
	if (!q) return true;
	return [m.name, m.label, m.name_ko, m.abbr].some((v) => (v ?? '').toLowerCase().includes(q));
}
