import { apiFetch } from './client';

export interface AiQueueStatus { enabled: boolean; worker_up: boolean; available: boolean }
export const getAiQueue = () => apiFetch<AiQueueStatus>('/ai/queue');
export const pingAiQueue = () =>
	apiFetch<AiQueueStatus & { ok: boolean; reason: string | null; text?: string; queue_ms?: number | null }>(
		'/ai/queue/ping', { method: 'POST' });
