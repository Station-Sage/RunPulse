// 03e-coach.md 5-A·5-B — Coach 스레드 목록·상세·메시지 API + 엔진 상태·동의·다시 생성(3-2).
import { apiFetch } from './client';
import type {
	ThreadsListResponse,
	ThreadDetailResponse,
	CreateThreadResponse,
	AddMessageResponse,
	CoachEngine,
	CoachConsent,
	ChatMessage,
	RegenerateResponse,
	CoachActivityContext,
	CoachThreadContext,
	SuggestionsResponse
} from '$lib/types';
import { messageBody, type CoachInput } from '$lib/coachSuggestions';

export function getThreads(): Promise<ThreadsListResponse> {
	return apiFetch<ThreadsListResponse>('/coach/threads');
}

export function getSuggestions(): Promise<SuggestionsResponse> {
	return apiFetch<SuggestionsResponse>('/coach/suggestions');
}

/** 같은 clientMsgId로 다시 보내도 서버가 한 번만 만든다(재전송 멱등). */
export function newClientMsgId(): string {
	return globalThis.crypto?.randomUUID?.() ?? `c-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

export function createThread(
	input: CoachInput,
	clientMsgId?: string,
	context?: CoachThreadContext
): Promise<CreateThreadResponse> {
	return apiFetch<CreateThreadResponse>('/coach/threads', {
		method: 'POST',
		body: JSON.stringify({ ...messageBody(input, 'initial_message'), client_msg_id: clientMsgId, context })
	});
}

export async function getActivityContext(activityId: number): Promise<CoachActivityContext> {
	const res = await apiFetch<{ activity: CoachActivityContext }>(`/coach/activity-context?activity=${activityId}`);
	return res.activity;
}

export function getThread(id: number): Promise<ThreadDetailResponse> {
	return apiFetch<ThreadDetailResponse>(`/coach/threads/${id}`);
}

export function addMessage(threadId: number, input: CoachInput, clientMsgId?: string): Promise<AddMessageResponse> {
	return apiFetch<AddMessageResponse>(`/coach/threads/${threadId}/messages`, {
		method: 'POST',
		body: JSON.stringify({ ...messageBody(input, 'content'), client_msg_id: clientMsgId })
	});
}

/** 폴링용 — 스트림을 잇지 못할 때 최종 상태를 확인한다. */
export async function getMessage(messageId: number): Promise<ChatMessage> {
	const res = await apiFetch<{ message: ChatMessage }>(`/coach/messages/${messageId}`);
	return res.message;
}

export function cancelMessage(messageId: number): Promise<{ status: string }> {
	return apiFetch<{ status: string }>(`/coach/messages/${messageId}/cancel`, { method: 'POST' });
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

/** mode 'ai'(기본) = 같은 엔진으로 다시, 'rule' = 기본(규칙) 답변. 새 pending 메시지를 돌려준다. */
export function regenerateMessage(messageId: number, mode: 'ai' | 'rule' = 'ai'): Promise<RegenerateResponse> {
	return apiFetch<RegenerateResponse>(`/coach/messages/${messageId}/regenerate`, {
		method: 'POST',
		body: JSON.stringify({ mode })
	});
}
