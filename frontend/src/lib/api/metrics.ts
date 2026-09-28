import { apiFetch } from './client';
import type { MetricBreakdownData, MetricBrowserData, MetricExplainData, MetricTrendData } from '$lib/types';

// 분해 v2(explain=1, §C3.2) — 백엔드 metrics_explain.py가 지원하는 슬러그와 동기화해야 한다.
export const EXPLAIN_SUPPORTED_SLUGS = new Set(['tsb', 'ctl', 'atl', 'utrs', 'cirs', 'rri']);

export function getMetricExplain(
	slug: string,
	scopeType: string,
	scopeId: string
): Promise<MetricExplainData> {
	const params = new URLSearchParams({ scope_type: scopeType, scope_id: scopeId, explain: '1' });
	return apiFetch<{ metric: MetricExplainData }>(
		`/library/metrics/${slug}?${params}`
	).then((r) => r.metric);
}

export function getMetricBreakdown(
	slug: string,
	scopeType: string,
	scopeId: string
): Promise<MetricBreakdownData> {
	const params = new URLSearchParams({ scope_type: scopeType, scope_id: scopeId });
	return apiFetch<{ metric: MetricBreakdownData }>(
		`/library/metrics/${slug}?${params}`
	).then((r) => r.metric);
}

export function getMetricsBrowser(date?: string): Promise<MetricBrowserData> {
	const params = date ? `?date=${encodeURIComponent(date)}` : '';
	return apiFetch<MetricBrowserData>(`/library/metrics${params}`);
}

export function getMetricTrend(slug: string, period?: string): Promise<MetricTrendData> {
	const params = period ? `?period=${encodeURIComponent(period)}` : '';
	return apiFetch<MetricTrendData>(`/library/metrics/${slug}/trend${params}`);
}
