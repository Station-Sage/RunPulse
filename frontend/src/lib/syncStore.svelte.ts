// 동기화 상태 공유 스토어 — Pill·드로어·패널이 한 번의 폴링을 공유한다.
import { getSyncState } from '$lib/api/data';
import type { SyncState } from '$lib/syncState';

export { pollIntervalMs } from '$lib/syncState';

export const syncStore = $state<{ data: SyncState | null; failed: boolean; panelOpen: boolean }>({
	data: null,
	failed: false,
	panelOpen: false
});

export async function loadSyncState(): Promise<void> {
	try {
		syncStore.data = await getSyncState();
		syncStore.failed = false;
	} catch {
		syncStore.failed = true;
	}
}
