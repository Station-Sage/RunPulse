import { apiFetch } from './client';
import type { MetricBreakdownData, MetricBrowserData, MetricTrendData } from '$lib/types';

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
