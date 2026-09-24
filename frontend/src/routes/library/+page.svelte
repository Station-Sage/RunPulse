<script lang="ts">
	// 03c-library.md 3-A — Library 홈. 섹션 탭 + 최근 활동 + 빠른 메트릭 접근 + Provider 현황.
	import type { LibraryHomeData } from './+page';
	import { providerLabel, providerBadgeClass } from '$lib/provider';
	import { formatDistance, formatDuration, formatPace, formatDate } from '$lib/format';
	import { base } from '$app/paths';
	import type { ProviderKey } from '$lib/types';
	import { formatRelativeTime } from '$lib/format';

	let { data }: { data: LibraryHomeData } = $props();
</script>

<!-- 섹션 탭 -->
<nav class="flex border-b border-border-subtle">
	<a
		href="{base}/library"
		class="flex-1 border-b-2 border-fg-primary py-3 text-center text-sm font-medium text-fg-primary"
		aria-current="page"
	>
		활동
	</a>
	<a
		href="{base}/library/metrics"
		class="flex-1 py-3 text-center text-sm text-fg-muted hover:text-fg-secondary"
	>
		메트릭
	</a>
	<a
		href="{base}/library/wellness"
		class="flex-1 py-3 text-center text-sm text-fg-muted hover:text-fg-secondary"
	>
		웰니스
	</a>
	<a
		href="{base}/library/providers"
		class="flex-1 py-3 text-center text-sm text-fg-muted hover:text-fg-secondary"
	>
		Provider 비교
	</a>
</nav>

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
				<li>
					<a
						href="{base}/library/{act.id}"
						class="flex items-center gap-2 px-3 py-2.5 hover:bg-surface-3 active:bg-surface-3"
					>
						<span class="w-20 shrink-0 text-xs text-fg-muted">{formatDate(act.start_time)}</span>
						<span class="min-w-0 flex-1 truncate text-sm font-medium">{act.name}</span>
						<span class="hidden text-sm text-fg-secondary sm:inline">
							{act.distance_m != null ? formatDistance(act.distance_m) : '—'}
						</span>
						<span class="hidden text-sm text-fg-secondary sm:inline">
							{act.duration_sec != null ? formatDuration(act.duration_sec) : '—'}
						</span>
						<span class="hidden text-xs text-fg-secondary sm:inline">
							{act.avg_pace_sec_km != null ? formatPace(act.avg_pace_sec_km) : ''}
						</span>
						<span
							class="shrink-0 rounded px-1.5 py-0.5 text-[10px] text-white {providerBadgeClass(
								act.source as ProviderKey
							)}"
						>
							{providerLabel(act.source as ProviderKey)}
						</span>
						<span class="text-fg-muted">›</span>
					</a>
				</li>
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

<!-- Provider 데이터 현황 -->
<section class="px-4 pb-6">
	<h2 class="mb-2 text-xs font-medium uppercase tracking-wide text-fg-muted">Provider 현황</h2>

	{#if data.providerStatusError && data.providerStatus.length === 0}
		<p class="text-sm text-fg-muted">{data.providerStatusError}</p>
	{:else}
		<ul class="divide-y divide-border-subtle rounded-xl border border-border-subtle bg-surface-2">
			{#each data.providerStatus as item (item.provider)}
				<li class="flex items-center gap-2 px-3 py-2.5">
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
				</li>
			{/each}
		</ul>
	{/if}
</section>
