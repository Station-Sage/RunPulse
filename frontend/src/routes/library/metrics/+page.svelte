<script lang="ts">
	// 03c-library.md 3-E — 메트릭 브라우저. daily-scope 메트릭 카테고리별 그리드.
	import type { MetricsBrowserPageData } from './+page';
	import Sparkline from '$lib/components/Sparkline.svelte';
	import { base } from '$app/paths';
	import type { MetricBrowserEntry } from '$lib/types';

	let { data }: { data: MetricsBrowserPageData } = $props();

	const categories = $derived(data.browser?.categories ?? []);

	// 카테고리 칩 필터 ('all' + 실제 등장 카테고리) — URL ?category= 로 초기 선택 가능
	let selectedCategory = $state<string>(data.initialCategory);

	const visibleCategories = $derived(
		selectedCategory === 'all'
			? categories
			: categories.filter((c) => c.category === selectedCategory)
	);

	function formatValue(m: MetricBrowserEntry): string {
		if (m.value == null) return '—';
		const v = m.value;
		if (typeof v === 'string') return v;
		return Number.isInteger(v) ? String(v) : Number(v).toFixed(1);
	}
</script>

<!-- 헤더 -->
<div class="flex items-center gap-2 border-b border-border-subtle px-4 py-3">
	<a href="{base}/library" class="shrink-0 text-fg-muted" aria-label="Library로">←</a>
	<h1 class="text-base font-semibold">메트릭 브라우저</h1>
	{#if data.browser?.date}
		<span class="ml-auto text-xs text-fg-muted">{data.browser.date}</span>
	{/if}
</div>

{#if data.errorMessage}
	<div class="px-4 py-8 text-center">
		<p class="text-sm text-fg-secondary">{data.errorMessage}</p>
	</div>
{:else if categories.length === 0}
	<div class="px-4 py-8 text-center">
		<p class="text-sm text-fg-muted">데이터 수집 중</p>
	</div>
{:else}
	<!-- 카테고리 칩 필터 -->
	<div class="flex gap-2 overflow-x-auto border-b border-border-subtle px-4 py-2">
		<button
			class="shrink-0 rounded-full px-3 py-1 text-xs {selectedCategory === 'all'
				? 'bg-fg-primary text-surface-1'
				: 'bg-surface-2 text-fg-secondary'}"
			onclick={() => (selectedCategory = 'all')}
		>
			전체
		</button>
		{#each categories as cat}
			<button
				class="shrink-0 rounded-full px-3 py-1 text-xs {selectedCategory === cat.category
					? 'bg-fg-primary text-surface-1'
					: 'bg-surface-2 text-fg-secondary'}"
				onclick={() => (selectedCategory = cat.category)}
			>
				{cat.label}
			</button>
		{/each}
	</div>

	<!-- 카테고리별 섹션 -->
	<div class="flex flex-col gap-6 px-4 py-4">
		{#each visibleCategories as cat}
			<section>
				<h2 class="mb-2 text-xs font-medium uppercase tracking-wide text-fg-muted">{cat.label}</h2>
				<div class="grid grid-cols-2 gap-2 sm:grid-cols-3">
					{#each cat.metrics as m}
						<a
							href="{base}/library/metrics/{m.name}"
							class="flex flex-col gap-1 rounded-xl bg-surface-2 p-3 active:bg-surface-3"
						>
							<span class="text-xs text-fg-muted truncate">{m.label}</span>
							<span class="font-mono text-lg font-semibold leading-none">
								{formatValue(m)}{#if m.unit}<span class="ml-0.5 text-xs font-normal text-fg-muted">{m.unit}</span>{/if}
							</span>
							{#if m.sparkline.length > 1}
								<Sparkline data={m.sparkline} height={24} color="#3b82f6" />
							{/if}
							{#if m.provider}
								<span class="text-[10px] text-fg-muted">{m.provider}</span>
							{/if}
						</a>
					{/each}
				</div>
			</section>
		{/each}
	</div>
{/if}
