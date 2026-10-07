// 데이터 영역 API — SyncState 계약(40 design §7.3).
import { apiFetch } from './client';
import type { SyncState, TriggerResponse } from '$lib/syncState';

export const getSyncState = () => apiFetch<SyncState>('/data/sync-state');

// POST는 자동 재시도하지 않는다(중복 시작 방지) — 실패 처리는 syncStore.runTrigger.
export const triggerSync = (sources?: string[]) =>
	apiFetch<TriggerResponse>('/data/sync', {
		method: 'POST',
		body: JSON.stringify({ mode: 'incremental', ...(sources ? { sources } : {}) })
	});
