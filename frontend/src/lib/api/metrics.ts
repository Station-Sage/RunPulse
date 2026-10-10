import { apiFetch } from './client';
import type { MetricBreakdownData, MetricBrowserData, MetricExplainData, MetricTrendData } from '$lib/types';
import { createExplainCache } from '$lib/explainPrefetch';

// 분해 v2(explain=1, §C3.2) — 백엔드 metrics_explain.py가 지원하는 슬러그와 동기화해야 한다.
export const EXPLAIN_SUPPORTED_SLUGS = new Set(['tsb', 'ctl', 'atl', 'utrs', 'cirs', 'rri', 'race_pred_5k_sec', 'race_pred_10k_sec', 'race_pred_half_sec', 'race_pred_marathon_sec']);
// 활동 scope(`@a{id}`)는 별도 목록 — metrics_explain._ACTIVITY_EXPLAINERS와 동기화.
export const EXPLAIN_ACTIVITY_SLUGS = new Set(['trimp']);

export function isExplainSupported(slug: string, scopeType: string): boolean {
	return (scopeType === 'activity' ? EXPLAIN_ACTIVITY_SLUGS : EXPLAIN_SUPPORTED_SLUGS).has(slug);
}

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

const explainCache = createExplainCache((slug: string, date: string) => getMetricExplain(slug, 'daily', date));
export const getDailyExplainCached = explainCache.get;
export const prefetchDailyExplain = explainCache.prefetch;
