import { apiFetch } from './client';
import type { ProviderComparisonData } from '$lib/types';

export interface ProviderComparisonApiResponse {
	comparison: ProviderComparisonData;
}

export function getProviderComparison(
	activityId: number,
	discrepancyThreshold?: number
): Promise<ProviderComparisonApiResponse> {
	const params = new URLSearchParams();
	if (discrepancyThreshold != null) {
		params.set('discrepancy_threshold', String(discrepancyThreshold));
	}
	const qs = params.toString();
	return apiFetch<ProviderComparisonApiResponse>(
		`/library/activities/${activityId}/providers${qs ? `?${qs}` : ''}`
	);
}
