import { apiFetch, ApiError } from './client';
import type { ActivityFeedback, ActivityFeedbackInput } from '$lib/types';

const path = (id: number) => `/library/activities/${id}/feedback`;

export async function putActivityFeedback(
	id: number,
	input: ActivityFeedbackInput
): Promise<ActivityFeedback | null> {
	const data = await apiFetch<{ feedback: ActivityFeedback | null }>(path(id), {
		method: 'PUT',
		body: JSON.stringify(input)
	});
	return data.feedback;
}

export async function deleteActivityFeedback(id: number): Promise<void> {
	const res = await fetch(`/api/v1${path(id)}`, { method: 'DELETE' });
	if (!res.ok && res.status !== 204) throw new ApiError(res.status, {});
}
