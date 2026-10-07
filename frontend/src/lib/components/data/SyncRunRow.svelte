<script lang="ts">
	// 동기화 기록 한 줄 — 소스·범위·상태·건수·시각.
	import { relativeAgo, syncProviderName } from '$lib/syncState';
	import { runIsBad, runRange, runStatusLabel } from '$lib/dataArea';
	import type { DataRun } from '$lib/api/data';

	let { run, showProvider = true }: { run: DataRun; showProvider?: boolean } = $props();
	const when = $derived(relativeAgo(run.finished_at ?? run.started_at, new Date()));
</script>

<li class="flex items-center justify-between gap-2 border-b border-border-subtle py-2 text-sm last:border-0">
	<div class="min-w-0">
		<div class="text-fg-primary">
			{#if showProvider}{syncProviderName(run.provider)} · {/if}{runRange(run.from_date, run.to_date)}
		</div>
		{#if runIsBad(run.status) && run.last_error}
			<div class="truncate text-xs text-semantic-red">{run.last_error}</div>
		{/if}
	</div>
	<div class="shrink-0 text-right text-xs">
		<div class={runIsBad(run.status) ? 'text-semantic-red' : 'text-fg-secondary'}>
			{runStatusLabel(run.status)}{run.status === 'completed' ? ` · ${run.synced_count}건` : ''}
		</div>
		{#if when}<div class="text-fg-muted">{when}</div>{/if}
	</div>
</li>
