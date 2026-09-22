// 03e-coach.md 5-A·5-B — Coach 스레드 목록·상세·메시지 API.
import { apiFetch } from './client';
import type {
	ThreadsListResponse,
	ThreadDetailResponse,
	CreateThreadResponse,
	AddMessageResponse
} from '$lib/types';

export function getThreads(): Promise<ThreadsListResponse> {
	return apiFetch<ThreadsListResponse>('/coach/threads');
}

export function createThread(initialMessage: string): Promise<CreateThreadResponse> {
	return apiFetch<CreateThreadResponse>('/coach/threads', {
		method: 'POST',
		body: JSON.stringify({ initial_message: initialMessage })
	});
}

export function getThread(id: number): Promise<ThreadDetailResponse> {
	return apiFetch<ThreadDetailResponse>(`/coach/threads/${id}`);
}

export function addMessage(threadId: number, content: string): Promise<AddMessageResponse> {
	return apiFetch<AddMessageResponse>(`/coach/threads/${threadId}/messages`, {
		method: 'POST',
		body: JSON.stringify({ content })
	});
}
