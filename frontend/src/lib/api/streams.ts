import { apiFetch } from './client';
import type { ActivityStreamPoint } from '$lib/types';

export function getActivityStreams(activityId: number): Promise<ActivityStreamPoint[]> {
	return apiFetch<{ streams: ActivityStreamPoint[] }>(
		`/library/activities/${activityId}/streams`
	).then((r) => r.streams);
}
