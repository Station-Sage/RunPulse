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

// 중지 요청은 멱등 — 이미 끝난 작업이면 현재 상태만 돌려준다.
export const cancelSyncRun = (id: string | number) =>
	apiFetch<{ id: string; provider: string; state: string; requested: boolean }>(
		`/data/sync/runs/${encodeURIComponent(String(id))}/cancel`,
		{ method: 'POST' }
	);
