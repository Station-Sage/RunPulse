// 데이터 영역 API — SyncState 계약(40 design §7.3).
import { apiFetch } from './client';
import type { SyncState } from '$lib/syncState';

export const getSyncState = () => apiFetch<SyncState>('/data/sync-state');
