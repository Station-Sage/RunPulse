import { apiFetch } from './client';
import type { MetricBreakdownData } from '$lib/types';

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
