<script lang="ts">
	import type { DataHomeData } from './+page';
	import { base } from '$app/paths';
	import StatTile from '$lib/components/data/StatTile.svelte';
	import SourceCard from '$lib/components/data/SourceCard.svelte';
	import SyncRunRow from '$lib/components/data/SyncRunRow.svelte';
	import ErrorState from '$lib/components/ErrorState.svelte';
	import { formatBytes } from '$lib/dataArea';
	import { invalidate } from '$app/navigation';

	let { data }: { data: DataHomeData } = $props();
	const s = $derived(data.summary);
	const stale = $derived(
		(data.sources ?? []).filter((x) => x.state === 'idle-stale' || x.state.startsWith('error-'))
	);
</script>

<svelte:head><title>데이터 · RunPulse</title></svelte:head>

<div class="flex flex-col gap-5 px-4 py-4">
	{#if stale.length > 0}
		<a
			href="{base}/data/sync"
			class="rounded-lg border border-semantic-amber/50 bg-semantic-amber/10 p-3 text-sm text-fg-primary"
		>
			▲ {stale.length}개 소스가 갱신이 필요하거나 오류 상태예요 · 동기화 화면으로
		</a>
	{/if}

	{#if s}
		<section aria-label="요약" class="grid grid-cols-2 gap-2">
			<StatTile label="활동" value={s.activities.toLocaleString()} sub="건" />
			<StatTile label="웰니스" value={s.wellness_days.toLocaleString()} sub="일" />
			<StatTile
				label="기간"
				value={s.period.first ? s.period.first.slice(0, 7) : '-'}
				sub={s.period.last ? `~ ${s.period.last}` : undefined}
			/>
			<StatTile label="저장 용량" value={formatBytes(s.storage_bytes)} />
		</section>
	{:else}
		<ErrorState message="요약을 불러오지 못했어요" onRetry={() => invalidate('app:data-home')} compact />
	{/if}

	<section aria-label="소스">
		<h2 class="mb-2 text-sm font-semibold text-fg-primary">소스</h2>
		{#if data.sources}
			<div class="grid grid-cols-2 gap-2">
				{#each data.sources as src (src.provider)}
					<SourceCard source={src} activityCount={src.activity_count} />
				{/each}
			</div>
		{:else}
			<ErrorState message="소스를 불러오지 못했어요" onRetry={() => invalidate('app:data-home')} compact />
		{/if}
	</section>

	<section aria-label="최근 동기화">
		<div class="mb-1 flex items-center justify-between">
			<h2 class="text-sm font-semibold text-fg-primary">최근 동기화</h2>
			<a href="{base}/data/sync" class="text-xs text-fg-muted hover:text-fg-secondary">전체 보기 ›</a>
		</div>
		{#if s && s.recent_runs.length > 0}
			<ul>{#each s.recent_runs as run (run.id)}<SyncRunRow {run} />{/each}</ul>
		{:else if s}
			<p class="py-4 text-center text-sm text-fg-muted">아직 동기화 기록이 없어요</p>
		{/if}
	</section>
</div>
