// 동기화 상태 조회 — 진행 중 요청 공유 + 짧은 재사용(S4-103).
import { apiFetch } from './client.ts';
import type { SyncState } from '../syncState.ts';

// 같은 화면 로드에서 Pill·loader·컴포넌트가 동시에 부르므로 진행 중 요청을 공유하고, 성공 응답은 짧게 재사용한다(S4-103).
// 쓰기(트리거·취소) 직후처럼 최신값이 필요하면 { fresh: true }.
export const SYNC_STATE_TTL_MS = 2000;
let syncInflight: Promise<SyncState> | null = null;
let syncCached: { at: number; value: SyncState } | null = null;

export function resetSyncStateCache(): void {
	syncInflight = null;
	syncCached = null;
}

export function getSyncState(opts: { fresh?: boolean } = {}): Promise<SyncState> {
	if (!opts.fresh) {
		if (syncCached && Date.now() - syncCached.at < SYNC_STATE_TTL_MS) return Promise.resolve(syncCached.value);
		if (syncInflight) return syncInflight;
	}
	const req: Promise<SyncState> = apiFetch<SyncState>('/data/sync-state')
		.then((value) => {
			if (syncInflight === req) syncCached = { at: Date.now(), value };
			return value;
		})
		.finally(() => {
			if (syncInflight === req) syncInflight = null;
		});
	syncInflight = req;
	return req;
}
