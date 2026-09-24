import { apiFetch } from './client';
import type { CheckinPayload, CheckinResult, CheckinRow, MilestoneEntry, NarrativeResponse, TodayResponse } from '$lib/types';

export function getToday(): Promise<TodayResponse> {
	return apiFetch<TodayResponse>('/today');
}

export function getTodayNarrative(year?: number, month?: number): Promise<NarrativeResponse> {
	const params =
		year != null && month != null ? `?year=${year}&month=${month}` : '';
	return apiFetch<NarrativeResponse>(`/today/narrative${params}`);
}

export function getTodayMilestones(limit = 50): Promise<MilestoneEntry[]> {
	return apiFetch<{ milestones: MilestoneEntry[] }>(`/today/milestones?limit=${limit}`).then(
		(r) => r.milestones
	);
}

export function getTodayCheckin(): Promise<CheckinRow | null> {
	return apiFetch<{ checkin: CheckinRow | null }>('/today/checkin').then((r) => r.checkin);
}

export function postCheckin(payload: CheckinPayload): Promise<CheckinResult> {
	return apiFetch<CheckinResult>('/today/checkin', {
		method: 'POST',
		body: JSON.stringify(payload)
	});
}
