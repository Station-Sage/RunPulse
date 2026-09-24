import { apiFetch } from './client';
import type { ProviderComparisonData, ProviderStatusResponse } from '$lib/types';

export interface ProviderComparisonApiResponse {
	comparison: ProviderComparisonData;
}

export function getProviderMatrix(
	days = 28,
	discrepancyThreshold?: number
): Promise<ProviderComparisonApiResponse> {
	const params = new URLSearchParams();
	params.set('days', String(days));
	if (discrepancyThreshold != null)
		params.set('discrepancy_threshold', String(discrepancyThreshold));
	return apiFetch<ProviderComparisonApiResponse>(
		`/library/providers/matrix?${params.toString()}`
	);
}

export function getProviderStatus(): Promise<ProviderStatusResponse> {
	return apiFetch<ProviderStatusResponse>('/library/providers/status');
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
