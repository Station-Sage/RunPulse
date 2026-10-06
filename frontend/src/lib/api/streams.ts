import { apiFetch } from './client';
import type { ActivityStreamsResponse } from '$lib/types';

export function getActivityStreams(activityId: number): Promise<ActivityStreamsResponse> {
	return apiFetch<ActivityStreamsResponse>(`/library/activities/${activityId}/streams`);
}
