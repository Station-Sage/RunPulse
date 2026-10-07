// 동기화 상태 공유 스토어 — Pill·드로어·패널이 한 번의 폴링을 공유하고, 수동 트리거도 여기서 처리한다.
import { invalidate } from '$app/navigation';
import { ApiError } from '$lib/api/client';
import { getSyncState, triggerSync } from '$lib/api/data';
import {
	completionSummary,
	outcomeFromError,
	outcomeFromResponse,
	pollIntervalMs,
	type SyncState,
	type TriggerOutcome,
	type TriggerSkip
} from '$lib/syncState';

export { pollIntervalMs } from '$lib/syncState';

export const syncStore = $state<{
	data: SyncState | null;
	failed: boolean;
	panelOpen: boolean;
	triggering: boolean;
	triggeredAt: number | null;
	cooldownUntil: number | null;
	notice: string | null;
	skipped: TriggerSkip[];
	summary: string | null;
}>({
	data: null,
	failed: false,
	panelOpen: false,
	triggering: false,
	triggeredAt: null,
	cooldownUntil: null,
	notice: null,
	skipped: [],
	summary: null
});

// 완료 직후엔 지표 재계산이 아직 안 끝났을 수 있어 한 번 더 갱신한다(40 design §4)
const REFETCH_DELAY_MS = 10000;
const REFRESH_KEYS = ['app:today', 'app:library-home', 'app:race-hub'];
let refetchTimer: ReturnType<typeof setTimeout> | undefined;

function refreshData() {
	for (const k of REFRESH_KEYS) invalidate(k);
}

function onFinished(summary: string) {
	syncStore.summary = summary;
	syncStore.triggeredAt = null;
	refreshData();
	clearTimeout(refetchTimer);
	refetchTimer = setTimeout(refreshData, REFETCH_DELAY_MS);
}

export async function loadSyncState(): Promise<void> {
	try {
		const next = await getSyncState();
		const summary = completionSummary(syncStore.data, next);
		syncStore.data = next;
		syncStore.failed = false;
		if (summary) onFinished(summary);
	} catch {
		syncStore.failed = true;
	}
}

let timer: ReturnType<typeof setTimeout> | undefined;

function schedule(delay: number) {
	clearTimeout(timer);
	timer = setTimeout(async () => {
		await loadSyncState();
		schedule(pollIntervalMs(syncStore.data, syncStore.triggeredAt));
	}, delay);
}

/** 대기 중인 타이머를 취소하고 즉시 갱신한 뒤 주기를 다시 잡는다 */
export async function kick(): Promise<void> {
	clearTimeout(timer);
	await loadSyncState();
	schedule(pollIntervalMs(syncStore.data, syncStore.triggeredAt));
}

/** 헤더 Pill이 마운트될 때 한 번 호출 — 해제 함수를 돌려준다 */
export function startSyncPolling(): () => void {
	loadSyncState();
	schedule(60000);
	return () => clearTimeout(timer);
}

function apply(o: TriggerOutcome) {
	syncStore.notice = o.notice;
	syncStore.skipped = o.skipped;
	if (o.cooldownSec !== null) syncStore.cooldownUntil = Date.now() + o.cooldownSec * 1000;
}

/** "지금 동기화" — POST는 자동 재시도하지 않는다(누르면 한 번만 보낸다) */
export async function runTrigger(sources?: string[]): Promise<void> {
	if (syncStore.triggering) return;
	syncStore.triggering = true;
	syncStore.notice = null;
	syncStore.summary = null;
	syncStore.skipped = [];
	let outcome: TriggerOutcome;
	try {
		outcome = outcomeFromResponse(await triggerSync(sources));
	} catch (e) {
		outcome = e instanceof ApiError ? outcomeFromError(e.status, e.details) : outcomeFromError(0, null);
	}
	syncStore.triggering = false;
	apply(outcome);
	if (outcome.kick) {
		syncStore.triggeredAt = Date.now();
		await kick();
	}
}
