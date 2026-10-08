<script lang="ts">
	import type { DataSyncPageData } from './+page';
	import { invalidate } from '$app/navigation';
	import { base } from '$app/paths';
	import RangeSyncForm from '$lib/components/data/RangeSyncForm.svelte';
	import AutoSyncRow from '$lib/components/data/AutoSyncRow.svelte';
	import SyncRunRow from '$lib/components/data/SyncRunRow.svelte';
	import ErrorState from '$lib/components/ErrorState.svelte';
	import { rowAction, sourceLine, syncProviderName } from '$lib/syncState';
	import Toast from '$lib/components/Toast.svelte';
	import { patchSourceEnabled } from '$lib/api/data';
	import { cancelRun, loadSyncState, runTrigger, syncStore } from '$lib/syncStore.svelte';

	let { data }: { data: DataSyncPageData } = $props();
	const sources = $derived(syncStore.data?.sources ?? []);
	const anyRunning = $derived(sources.some((x) => x.state === 'running'));
	const connected = $derived(sources.filter((x) => x.connection === 'connected' && x.enabled));

	let toast = $state<{ message: string; undo: (() => void) | null } | null>(null);
	let toggling = $state<string | null>(null);

	async function toggle(provider: string, enable: boolean, undoable: boolean) {
		toggling = provider;
		try {
			await patchSourceEnabled(provider, enable);
			const name = syncProviderName(provider);
			toast = {
				message: enable ? `${name}를 동기화에 다시 포함했어요` : `${name}를 동기화에서 제외했어요`,
				undo: undoable ? () => void toggle(provider, !enable, false) : null
			};
			await loadSyncState();
		} catch {
			toast = { message: '변경하지 못했어요 · 잠시 후 다시 시도해 주세요', undo: null };
		} finally {
			toggling = null;
		}
	}

	// 실행이 끝나면 기록 표를 다시 읽는다
	let wasRunning = false;
	$effect(() => {
		if (wasRunning && !anyRunning) invalidate('app:data-sync');
		wasRunning = anyRunning;
	});
</script>

<svelte:head><title>동기화 · RunPulse</title></svelte:head>

<div class="flex flex-col gap-5 px-4 py-4">
	<section aria-label="소스 상태" class="flex flex-col gap-2">
		{#each sources as src (src.provider)}
			{@const line = sourceLine(src)}
			{@const action = rowAction(src)}
			<div class="flex items-center justify-between rounded-lg border border-border-subtle bg-surface-2 p-3">
				<div class="min-w-0">
					<a href="{base}/data/sources/{src.provider}" class="text-sm font-medium text-fg-primary">
						{syncProviderName(src.provider)}
					</a>
					<div class="text-xs text-fg-secondary"><span aria-hidden="true">{line.glyph}</span> {line.text}</div>
				</div>
				{#if action && !src.running}
					<button
						type="button"
						class="rounded border border-border-subtle px-2 py-1 text-xs"
						disabled={toggling === src.provider}
						onclick={() => toggle(src.provider, action.enable, !action.enable)}>{action.label}</button
					>
				{/if}
				{#if src.running}
					<button
						type="button"
						class="rounded border border-border-subtle px-2 py-1 text-xs"
						disabled={syncStore.cancelling.includes(src.provider)}
						onclick={() => src.running && cancelRun(src.provider, src.running.job_id)}>중지</button
					>
				{/if}
			</div>
		{/each}
	</section>

	<div>
		<button
			type="button"
			class="w-full rounded-lg bg-fg-primary px-4 py-2.5 text-sm font-medium text-surface-1 disabled:opacity-50"
			disabled={syncStore.triggering || anyRunning || connected.length === 0}
			onclick={() => runTrigger()}
		>
			{anyRunning ? '동기화 중…' : '지금 동기화'}
		</button>
		{#if connected.length === 0 && sources.some((x) => !x.enabled)}
			<p class="mt-2 text-xs text-fg-secondary">동기화할 소스가 없어요 · 위에서 [다시 포함]을 눌러 켜세요</p>
		{/if}
		{#if syncStore.notice}<p class="mt-2 text-xs text-fg-secondary" role="status">{syncStore.notice}</p>{/if}
	</div>

	{#if connected.length > 0}<RangeSyncForm providers={connected.map((x) => x.provider)} />{/if}

	{#if data.auto}<AutoSyncRow settings={data.auto} />{/if}

	<section aria-label="동기화 기록">
		<h2 class="mb-1 text-sm font-semibold text-fg-primary">기록</h2>
		{#if data.runs === null}
			<ErrorState message="기록을 불러오지 못했어요" onRetry={() => invalidate('app:data-sync')} compact />
		{:else if data.runs.length === 0}
			<p class="py-4 text-center text-sm text-fg-muted">아직 동기화 기록이 없어요</p>
		{:else}
			<ul>{#each data.runs as run (run.id)}<SyncRunRow {run} />{/each}</ul>
		{/if}
	</section>
</div>

<Toast open={toast !== null} message={toast?.message ?? ''} onUndo={toast?.undo ?? undefined} onDismiss={() => (toast = null)} />
