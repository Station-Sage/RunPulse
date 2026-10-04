import { apiFetch } from './client';
import type {
	ProviderComparisonData,
	ProviderCoverage,
	ProviderMatrixData,
	ProviderPairsData,
	ProviderStatusResponse
} from '$lib/types';

export interface ProviderComparisonApiResponse {
	comparison: ProviderComparisonData;
}

export function getProviderMatrix(days = 28): Promise<ProviderMatrixData> {
	return apiFetch<ProviderMatrixData>(`/library/providers/matrix?days=${days}`);
}

export function getProviderPairs(group: string, days = 28): Promise<ProviderPairsData> {
	return apiFetch<ProviderPairsData>(
		`/library/providers/pairs/${encodeURIComponent(group)}?days=${days}`
	);
}

export function getProviderStatus(): Promise<ProviderStatusResponse> {
	return apiFetch<ProviderStatusResponse>('/library/providers/status');
}

export function getProviderCoverage(): Promise<ProviderCoverage> {
	return apiFetch<ProviderCoverage>('/library/providers/coverage');
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
