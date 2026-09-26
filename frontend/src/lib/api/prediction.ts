import { apiFetch } from './client';
import type { PredictionProfile, RaceCandidate, RaceEffort } from '$lib/types';

export function getPredictionProfile(): Promise<PredictionProfile> {
	return apiFetch<PredictionProfile>('/prediction/profile');
}

export function getRaceCandidates(): Promise<RaceCandidate[]> {
	return apiFetch<{ items: RaceCandidate[] }>('/races/candidates').then((r) => r.items);
}

export function putRaceConfirm(activityId: number, effort: RaceEffort, officialTimeSec?: number): Promise<unknown> {
	return apiFetch(`/races/${activityId}/confirm`, {
		method: 'PUT',
		body: JSON.stringify({ effort, official_time_sec: officialTimeSec ?? null })
	});
}

export function deleteRaceConfirm(activityId: number): Promise<unknown> {
	return apiFetch(`/races/${activityId}/confirm`, { method: 'DELETE' });
}
