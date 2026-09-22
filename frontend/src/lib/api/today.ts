import { apiFetch } from './client';
import type { CheckinPayload, CheckinResult, TodayResponse } from '$lib/types';

export function getToday(): Promise<TodayResponse> {
	return apiFetch<TodayResponse>('/today');
}

export function postCheckin(payload: CheckinPayload): Promise<CheckinResult> {
	return apiFetch<CheckinResult>('/today/checkin', {
		method: 'POST',
		body: JSON.stringify(payload)
	});
}
