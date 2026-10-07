// 동기화 상태 공유 스토어 — Pill·드로어·패널이 한 번의 폴링을 공유하고, 수동 트리거도 여기서 처리한다.
import { invalidate } from '$app/navigation';
import { ApiError } from '$lib/api/client';
import { cancelSyncRun, getSyncState, triggerRangeSync, triggerSync } from '$lib/api/data';
import {
	completionSummary,
	outcomeFromError,
	outcomeFromResponse,
	pollIntervalMs,
	type SyncState,
	type TriggerOutcome,
	type TriggerResponse,
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
	cancelling: string[];
}>({
	data: null,
	failed: false,
	panelOpen: false,
	triggering: false,
	triggeredAt: null,
	cooldownUntil: null,
	notice: null,
	skipped: [],
	summary: null,
	cancelling: []
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

async function runWith(send: () => Promise<TriggerResponse>): Promise<void> {
	if (syncStore.triggering) return;
	syncStore.triggering = true;
	syncStore.notice = null;
	syncStore.summary = null;
	syncStore.skipped = [];
	let outcome: TriggerOutcome;
	try {
		outcome = outcomeFromResponse(await send());
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

/** "지금 동기화" — POST는 자동 재시도하지 않는다(누르면 한 번만 보낸다) */
export const runTrigger = (sources?: string[]) => runWith(() => triggerSync(sources));

/** 기간 동기화 — 같은 결과 처리, 요청만 다르다 */
export const runRangeTrigger = (source: string, from: string, to: string) =>
	runWith(() => triggerRangeSync([source], from, to));

/** 진행 중인 소스 동기화 중지 요청 — 반영은 다음 폴링에서 확인한다 */
export async function cancelRun(provider: string, jobId: string | number): Promise<void> {
	if (syncStore.cancelling.includes(provider)) return;
	syncStore.cancelling = [...syncStore.cancelling, provider];
	syncStore.notice = null;
	try {
		await cancelSyncRun(jobId);
	} catch {
		syncStore.notice = '중지하지 못했어요. 잠시 후 다시 시도해 주세요';
	}
	await kick();
	syncStore.cancelling = syncStore.cancelling.filter((p) => p !== provider);
}
