<script lang="ts">
	import type { DataSourcePageData } from './+page';
	import { base } from '$app/paths';
	import { invalidateAll } from '$app/navigation';
	import StatTile from '$lib/components/data/StatTile.svelte';
	import SyncRunRow from '$lib/components/data/SyncRunRow.svelte';
	import ErrorState from '$lib/components/ErrorState.svelte';
	import EmptyState from '$lib/components/EmptyState.svelte';
	import { sourceLine, syncProviderName } from '$lib/syncState';
	import { runTrigger, syncStore } from '$lib/syncStore.svelte';

	let { data }: { data: DataSourcePageData } = $props();
	const d = $derived(data.detail);
	const line = $derived(d ? sourceLine(d) : null);
	const maxCount = $derived(d ? Math.max(1, ...d.coverage.months.map((m) => m.count)) : 1);
</script>

<svelte:head><title>{syncProviderName(data.provider)} · RunPulse</title></svelte:head>

<div class="flex flex-col gap-5 px-4 py-4">
	<a href="{base}/data/sources" class="text-xs text-fg-muted hover:text-fg-secondary">‹ 소스</a>

	{#if data.notFound}
		<EmptyState title="알 수 없는 소스예요" actionLabel="소스 목록" actionHref="{base}/data/sources" />
	{:else if !d || !line}
		<ErrorState message="소스를 불러오지 못했어요" onRetry={() => invalidateAll()} />
	{:else}
		<header>
			<h1 class="text-lg font-semibold text-fg-primary">{syncProviderName(d.provider)}</h1>
			<p class="text-sm text-fg-secondary"><span aria-hidden="true">{line.glyph}</span> {line.text}</p>
			{#if d.last_error}<p class="mt-1 text-xs text-semantic-red">{d.last_error.message_ko}</p>{/if}
		</header>

		{#if d.connection === 'connected'}
			<button
				type="button"
				class="rounded-lg bg-fg-primary px-4 py-2.5 text-sm font-medium text-surface-1 disabled:opacity-50"
				disabled={!d.enabled || !!d.running || syncStore.triggering}
				onclick={() => runTrigger([d.provider])}
			>
				{d.running ? '동기화 중…' : '이 소스 동기화'}
			</button>
		{/if}

		<section aria-label="보유 데이터" class="grid grid-cols-2 gap-2">
			<StatTile label="활동" value={d.counts.activities.toLocaleString()} />
			<StatTile label="웰니스" value={d.counts.wellness_days.toLocaleString()} sub="일" />
			<StatTile label="스트림" value={d.counts.streams.toLocaleString()} />
			<StatTile label="랩" value={d.counts.laps.toLocaleString()} />
		</section>

		<section aria-label="12개월 커버리지">
			<h2 class="mb-2 text-sm font-semibold text-fg-primary">최근 12개월</h2>
			{#if d.coverage.months.length === 0}
				<p class="text-sm text-fg-muted">이 기간의 활동이 없어요</p>
			{:else}
				<ul class="flex flex-col gap-1">
					{#each d.coverage.months as m (m.month)}
						<li class="flex items-center gap-2 text-xs">
							<span class="w-14 shrink-0 text-fg-muted tabular-nums">{m.month}</span>
							<span class="h-2 rounded bg-semantic-teal" style="width:{(m.count / maxCount) * 100}%"></span>
							<span class="text-fg-secondary tabular-nums">{m.count}</span>
						</li>
					{/each}
				</ul>
			{/if}
		</section>

		<section aria-label="최근 동기화">
			<h2 class="mb-1 text-sm font-semibold text-fg-primary">최근 동기화</h2>
			{#if d.recent_runs.length === 0}
				<p class="py-2 text-sm text-fg-muted">아직 기록이 없어요</p>
			{:else}
				<ul>{#each d.recent_runs as run (run.id)}<SyncRunRow {run} showProvider={false} />{/each}</ul>
			{/if}
		</section>
	{/if}
</div>
