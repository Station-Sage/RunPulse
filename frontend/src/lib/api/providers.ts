import { apiFetch } from './client';
import type { ProviderComparisonData, ProviderMatrixData } from '$lib/types';

export interface ProviderComparisonApiResponse {
	comparison: ProviderComparisonData;
}

export interface ProviderMatrixApiResponse {
	period_days: number;
	providers: string[];
	groups: ProviderMatrixData['groups'];
	discrepancy_count: number;
}

export function getProviderMatrix(
	periodDays?: number,
	discrepancyThreshold?: number
): Promise<ProviderMatrixApiResponse> {
	const params = new URLSearchParams();
	if (periodDays != null) params.set('period_days', String(periodDays));
	if (discrepancyThreshold != null)
		params.set('discrepancy_threshold', String(discrepancyThreshold));
	const qs = params.toString();
	return apiFetch<ProviderMatrixApiResponse>(
		`/library/providers/matrix${qs ? `?${qs}` : ''}`
	);
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
