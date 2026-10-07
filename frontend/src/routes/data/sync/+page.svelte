<script lang="ts">
	import type { DataSyncPageData } from './+page';
	import { invalidate } from '$app/navigation';
	import { base } from '$app/paths';
	import SyncRunRow from '$lib/components/data/SyncRunRow.svelte';
	import ErrorState from '$lib/components/ErrorState.svelte';
	import { sourceLine, syncProviderName } from '$lib/syncState';
	import { cancelRun, runTrigger, syncStore } from '$lib/syncStore.svelte';

	let { data }: { data: DataSyncPageData } = $props();
	const sources = $derived(syncStore.data?.sources ?? []);
	const anyRunning = $derived(sources.some((x) => x.state === 'running'));
	const connected = $derived(sources.filter((x) => x.connection === 'connected' && x.enabled));

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
			<div class="flex items-center justify-between rounded-lg border border-border-subtle bg-surface-2 p-3">
				<div class="min-w-0">
					<a href="{base}/data/sources/{src.provider}" class="text-sm font-medium text-fg-primary">
						{syncProviderName(src.provider)}
					</a>
					<div class="text-xs text-fg-secondary"><span aria-hidden="true">{line.glyph}</span> {line.text}</div>
				</div>
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
		{#if syncStore.notice}<p class="mt-2 text-xs text-fg-secondary" role="status">{syncStore.notice}</p>{/if}
	</div>

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
