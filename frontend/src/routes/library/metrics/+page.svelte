<script lang="ts">
	// 03c-library.md 3-E — 메트릭 브라우저. daily-scope 메트릭 카테고리별 그리드.
	// P3 Provider Transparency: 카드 Provider 배지 + [모든 Provider ▾] 드롭다운 필터.
	import type { MetricsBrowserPageData } from './+page';
	import Sparkline from '$lib/components/Sparkline.svelte';
	import { base } from '$app/paths';
	import type { MetricBrowserEntry, ProviderKey } from '$lib/types';
	import { providerLabel, providerBadgeClass } from '$lib/provider';

	let { data }: { data: MetricsBrowserPageData } = $props();

	const categories = $derived(data.browser?.categories ?? []);

	// 카테고리 칩 필터 ('all' + 실제 등장 카테고리) — URL ?category= 로 초기 선택 가능
	let selectedCategory = $state<string>(data.initialCategory);

	// Provider 드롭다운 필터 — P3 Provider Transparency
	let selectedProvider = $state<string>('all');
	let providerDropdownOpen = $state(false);

	// 데이터에 등장하는 고유 Provider 목록 (base 키 기준, 빈 문자열 제외)
	const availableProviders = $derived(
		[
			...new Set(
				categories
					.flatMap((cat) => cat.metrics.map((m) => (m.provider ?? '').split(':')[0]))
					.filter((k) => k.length > 0)
			)
		].sort()
	);

	const visibleCategories = $derived(
		(selectedCategory === 'all'
			? categories
			: categories.filter((c) => c.category === selectedCategory)
		)
			.map((cat) => ({
				...cat,
				metrics:
					selectedProvider === 'all'
						? cat.metrics
						: cat.metrics.filter(
								(m) => (m.provider ?? '').split(':')[0] === selectedProvider
							)
			}))
			.filter((cat) => cat.metrics.length > 0)
	);

	const selectedProviderLabel = $derived(
		selectedProvider === 'all'
			? '모든 Provider'
			: providerLabel(selectedProvider as ProviderKey)
	);

	function formatValue(m: MetricBrowserEntry): string {
		if (m.value == null) return '—';
		const v = m.value;
		if (typeof v === 'string') return v;
		return Number.isInteger(v) ? String(v) : Number(v).toFixed(1);
	}

	function selectProvider(key: string) {
		selectedProvider = key;
		providerDropdownOpen = false;
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

	<!-- Provider 드롭다운 필터 — P3 Provider Transparency -->
	<div class="relative border-b border-border-subtle px-4 py-2">
		<button
			class="flex items-center gap-1 rounded-lg bg-surface-2 px-3 py-1.5 text-xs text-fg-secondary"
			onclick={() => (providerDropdownOpen = !providerDropdownOpen)}
			aria-expanded={providerDropdownOpen}
			aria-haspopup="listbox"
		>
			<span>{selectedProviderLabel}</span>
			<span aria-hidden="true">▾</span>
		</button>
		{#if providerDropdownOpen}
			<!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
			<div
				class="fixed inset-0 z-0"
				onclick={() => (providerDropdownOpen = false)}
				aria-hidden="true"
			></div>
			<ul
				role="listbox"
				aria-label="Provider 필터"
				class="absolute left-4 top-full z-10 mt-1 min-w-[10rem] rounded-xl border border-border-subtle bg-surface-1 py-1 shadow-lg"
			>
				<li role="option" aria-selected={selectedProvider === 'all'}>
					<button
						class="w-full px-4 py-2 text-left text-xs {selectedProvider === 'all'
							? 'font-semibold text-fg-primary'
							: 'text-fg-secondary'}"
						onclick={() => selectProvider('all')}
					>
						모든 Provider
					</button>
				</li>
				{#each availableProviders as key}
					<li role="option" aria-selected={selectedProvider === key}>
						<button
							class="flex w-full items-center gap-2 px-4 py-2 text-left {selectedProvider === key
								? 'font-semibold'
								: ''}"
							onclick={() => selectProvider(key)}
						>
							<span
								class="rounded px-1.5 py-0.5 text-[10px] text-white {providerBadgeClass(
									key as ProviderKey
								)}"
							>
								{providerLabel(key as ProviderKey)}
							</span>
						</button>
					</li>
				{/each}
			</ul>
		{/if}
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
							<div class="flex items-start justify-between gap-1">
								<span class="truncate text-xs text-fg-muted">{m.label}</span>
								{#if m.provider}
									<span
										class="shrink-0 rounded px-1.5 py-0.5 text-[10px] text-white {providerBadgeClass(
											m.provider as ProviderKey
										)}"
									>
										{providerLabel(m.provider as ProviderKey)}
									</span>
								{/if}
							</div>
							<span class="font-mono text-lg font-semibold leading-none">
								{formatValue(m)}{#if m.unit}<span class="ml-0.5 text-xs font-normal text-fg-muted"
										>{m.unit}</span
									>{/if}
							</span>
							{#if m.sparkline.length > 1}
								<Sparkline data={m.sparkline} height={24} color="#3b82f6" />
							{/if}
						</a>
					{/each}
				</div>
			</section>
		{/each}
	</div>
{/if}
