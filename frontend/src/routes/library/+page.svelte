<script lang="ts">
	// 03c-library.md 3-A — Library 홈. 섹션 탭 + 최근 활동 + 빠른 메트릭 접근 + 소스 커버리지.
	import type { LibraryHomeData } from './+page';
	import { providerLabel, providerBadgeClass } from '$lib/provider';
	import { providerHint } from '$lib/providerHint';
	import { formatRelativeTime } from '$lib/format';
	import { base } from '$app/paths';
	import type { ProviderKey } from '$lib/types';
	import ActivityRow from '$lib/components/ActivityRow.svelte';
	import ArchiveHero from '$lib/components/ArchiveHero.svelte';
	import SourceCoverage from '$lib/components/SourceCoverage.svelte';

	let { data }: { data: LibraryHomeData } = $props();
</script>

<svelte:head><title>Library · RunPulse</title></svelte:head>

<ArchiveHero archive={data.archive} />

<!-- 최근 활동 -->
<section class="px-4 py-4">
	<div class="mb-2 flex items-center justify-between">
		<h2 class="text-xs font-medium uppercase tracking-wide text-fg-muted">최근 활동</h2>
		<a href="{base}/library/activities" class="text-xs text-fg-muted hover:text-fg-secondary">
			전체 보기 →
		</a>
	</div>

	{#if data.activitiesError && data.recentActivities.length === 0}
		<p class="py-4 text-center text-sm text-fg-muted">{data.activitiesError}</p>
	{:else if data.recentActivities.length === 0}
		<p class="py-4 text-center text-sm text-fg-muted">활동 없음 — 데이터를 동기화해 주세요.</p>
	{:else}
		<ul class="divide-y divide-border-subtle rounded-xl border border-border-subtle bg-surface-2">
			{#each data.recentActivities as act (act.id)}
				<li><ActivityRow {act} from="home" showProvider /></li>
			{/each}
		</ul>
		<div class="mt-2 flex justify-end">
			<a href="{base}/library/activities" class="text-xs text-fg-muted hover:text-fg-secondary">
				활동 전체 보기 →
			</a>
		</div>
	{/if}
</section>

<!-- 빠른 메트릭 접근 -->
<section class="px-4 pb-4">
	<h2 class="mb-2 text-xs font-medium uppercase tracking-wide text-fg-muted">빠른 메트릭 접근</h2>

	{#if data.categories.length === 0}
		<a
			href="{base}/library/metrics"
			class="block py-2 text-sm text-fg-muted hover:text-fg-secondary"
		>
			메트릭 브라우저 →
		</a>
	{:else}
		<div class="flex flex-wrap gap-2">
			{#each data.categories as cat}
				<a
					href="{base}/library/metrics?category={encodeURIComponent(cat.category)}"
					class="rounded-full border border-border-subtle bg-surface-2 px-3 py-1.5 text-xs text-fg-secondary hover:bg-surface-3"
				>
					{cat.label}
				</a>
			{/each}
			<a
				href="{base}/library/metrics"
				class="rounded-full border border-border-subtle bg-surface-2 px-3 py-1.5 text-xs text-fg-muted hover:bg-surface-3"
			>
				전체 →
			</a>
		</div>
	{/if}
</section>

<!-- 소스 커버리지 -->
<section class="px-4 pb-6">
	<h2 class="mb-2 text-xs font-medium uppercase tracking-wide text-fg-muted">소스 커버리지</h2>

	{#if data.coverage}
		<SourceCoverage coverage={data.coverage} status={data.providerStatus} />
	{:else}
		{#if data.providerStatusError && data.providerStatus.length === 0}
			<p class="text-sm text-fg-muted">{data.providerStatusError}</p>
		{:else}
			<ul class="divide-y divide-border-subtle rounded-xl border border-border-subtle bg-surface-2">
				{#each data.providerStatus as item (item.provider)}
					{@const hint = providerHint(item, Date.now())}
					<li class="flex flex-wrap items-center gap-2 px-3 py-2.5">
						<span
							class="shrink-0 rounded px-1.5 py-0.5 text-[10px] text-white {providerBadgeClass(
								item.provider as ProviderKey
							)}"
						>
							{providerLabel(item.provider as ProviderKey)}
						</span>
						{#if item.has_data}
							<span class="text-xs text-fg-primary">●데이터 있음</span>
						{:else}
							<span class="text-xs text-fg-muted">○데이터 없음</span>
						{/if}
						<span class="ml-auto text-xs text-fg-muted">
							{#if item.last_synced_at}
								마지막 동기화 {formatRelativeTime(item.last_synced_at)} ·
							{/if}
							활동 {item.activity_count}건
						</span>
						{#if hint}<p class="w-full text-[11px] text-semantic-amber">{hint}</p>{/if}
					</li>
				{/each}
			</ul>
		{/if}
	{/if}
</section>
