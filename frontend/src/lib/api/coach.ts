// 03e-coach.md 5-A·5-B — Coach 스레드 목록·상세·메시지 API + 엔진 상태·동의·다시 생성(3-2).
import { apiFetch } from './client';
import type {
	ThreadsListResponse,
	ThreadDetailResponse,
	CreateThreadResponse,
	AddMessageResponse,
	CoachEngine,
	CoachConsent,
	RegenerateResponse
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

export function getEngine(): Promise<CoachEngine> {
	return apiFetch<CoachEngine>('/coach/engine');
}

export type ConsentInput = Pick<CoachConsent, 'provider' | 'exclude_notes' | 'tools_enabled' | 'fallback_enabled'>;

export async function putConsent(input: ConsentInput): Promise<CoachConsent> {
	const res = await apiFetch<{ consent: CoachConsent }>('/coach/consent', {
		method: 'PUT',
		body: JSON.stringify(input)
	});
	return res.consent;
}

export function regenerateMessage(threadId: number, messageId: number): Promise<RegenerateResponse> {
	return apiFetch<RegenerateResponse>(`/coach/threads/${threadId}/messages/${messageId}/regenerate`, {
		method: 'POST'
	});
}
