// 컨텍스트 에피소드(질병·여행·고지대) + 질병 AI 동의 — /api/context-episodes (v1 밖, 같은 봉투).
import { ApiError } from './client';
import type { ContextEpisode, ContextKind, ContextList, ConsentState, ConsentAction } from '$lib/contextView';

const BASE = '/api/context-episodes';

async function call<T>(path: string, init?: RequestInit): Promise<T> {
	const res = await fetch(`${BASE}${path}`, { headers: { 'Content-Type': 'application/json' }, ...init });
	const body = await res.json();
	if (!res.ok) throw new ApiError(res.status, body);
	return (body as { data: T }).data;
}

const post = (path: string, body?: unknown) =>
	call<Record<string, unknown>>(path, { method: 'POST', body: JSON.stringify(body ?? {}) });

export const getContext = () => call<ContextList>('');

export const openContext = (
	kind: ContextKind,
	extra: { severity?: number; start_date?: string; detail?: Record<string, unknown> } = {}
) => post('', { kind, ...extra }) as unknown as Promise<{ episode: ContextEpisode; needs_consent_prompt: boolean }>;

export const confirmContext = (id: number) => post(`/${id}/confirm`);
export const dismissContext = (id: number) => post(`/${id}/dismiss`);
export const closeContext = (id: number, end_date?: string) => post(`/${id}/close`, end_date ? { end_date } : {});

export const deleteContext = (id: number, chat_thread_ids?: number[]) =>
	call<unknown>(`/${id}`, { method: 'DELETE', body: JSON.stringify({ chat_thread_ids: chat_thread_ids ?? [] }) });

export const getConsent = () => call<ConsentState>('/consent');
export const postConsent = (action: ConsentAction, via: 'first_input' | 'settings') =>
	post('/consent', { action, via });
