<script lang="ts">
	// 03c-library.md 3-E — 메트릭 브라우저. daily-scope 메트릭 카테고리별 그리드.
	// P3 Provider Transparency: 카드 Provider 배지 + [모든 Provider] 칩 필터.
	import type { MetricsBrowserPageData } from './+page';
	import Sparkline from '$lib/components/Sparkline.svelte';
	import { base } from '$app/paths';
	import type { MetricBrowserEntry, ProviderKey } from '$lib/types';
	import { providerLabel, providerLabelCompact, providerBadgeClass } from '$lib/provider';
	import { formatUnitValue } from '$lib/format';
	import { matchesMetric } from '$lib/metricSearch';
	import { replaceState } from '$app/navigation';
	import { page as pageState } from '$app/state';
	import { displayLabel, isComponentMetric, isFlat, STATUS_TEXT_CLASS, STATUS_DOT_COLOR, sparkCaption } from '$lib/metricMeaning';

	let { data }: { data: MetricsBrowserPageData } = $props();

	const categories = $derived(data.browser?.categories ?? []);

	// 카테고리 칩 필터 ('all' + 실제 등장 카테고리) — URL ?category= 로 초기 선택 가능
	let selectedCategory = $state<string>(data.initialCategory);

	// 검색어 — URL ?q= 와 동기화, `/` 키로 포커스. 검색 중에는 핵심/접힘 구성을 풀고 일치 항목만 평면 표시.
	let query = $state(data.initialQuery);
	let searchEl = $state<HTMLInputElement | null>(null);
	const searching = $derived(query.trim().length > 0);

	function syncQuery() {
		const u = new URL(pageState.url);
		if (query.trim()) u.searchParams.set('q', query.trim());
		else u.searchParams.delete('q');
		replaceState(u, pageState.state);
	}
	function onKey(e: KeyboardEvent) {
		const t = e.target as HTMLElement | null;
		if (e.key !== '/' || e.metaKey || e.ctrlKey || e.altKey) return;
		if (t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.tagName === 'SELECT' || t.isContentEditable)) return;
		e.preventDefault();
		searchEl?.focus();
	}

	// Provider 칩 필터 — P3 Provider Transparency. 등장 provider가 2종 이상일 때만 행을 보인다.
	let selectedProvider = $state<string>('all');

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

	// 핵심 지표 — 전체 보기에서 맨 위에 크게. 나머지는 카테고리별, 보조 카테고리(수면·심박 세부·환경)는 접어 둔다.
	const CORE = ['race_pred_marathon_sec', 'race_pred_half_sec', 'race_pred_10k_sec', 'race_pred_5k_sec', 'ctl', 'tsb', 'utrs', 'cirs'];
	const COLLAPSED = new Set(['sleep', 'hr', 'weather']);
	const showCore = $derived(selectedCategory === 'all' && selectedProvider === 'all' && !searching);
	const coreMetrics = $derived(
		showCore
			? CORE.map((n) => categories.flatMap((c) => c.metrics).find((m) => m.name === n)).filter(
					(m): m is MetricBrowserEntry => m != null
				)
			: []
	);

	const visibleCategories = $derived(
		(selectedCategory === 'all'
			? categories
			: categories.filter((c) => c.category === selectedCategory)
		)
			.map((cat) => ({
				...cat,
				metrics: (
					selectedProvider === 'all'
						? cat.metrics
						: cat.metrics.filter(
								(m) => (m.provider ?? '').split(':')[0] === selectedProvider
							)
				).filter((m) => !isComponentMetric(m.label) && !(showCore && CORE.includes(m.name)) && matchesMetric(m, query))
			}))
			.filter((cat) => cat.metrics.length > 0)
	);

	function formatValue(m: MetricBrowserEntry): string {
		if (m.value == null) return '—';
		if (typeof m.value === 'string') return m.value;
		return formatUnitValue(Number(m.value), m.unit).display;
	}
	function valueUnit(m: MetricBrowserEntry): string {
		if (m.value == null || typeof m.value === 'string') return m.unit;
		return formatUnitValue(Number(m.value), m.unit).unit;
	}
</script>

{#snippet card(m: MetricBrowserEntry, big: boolean)}
	<a
		href="{base}/library/metrics/{m.name}"
		class="flex flex-col gap-1 rounded-xl bg-surface-2 p-3 active:bg-surface-3 {big ? 'ring-1 ring-border-subtle' : ''}"
	>
		<span class="text-xs leading-snug text-fg-muted">{displayLabel({ name_ko: m.name_ko ?? m.label, abbr: m.abbr })}</span>
		<div class="flex items-baseline justify-between gap-1">
			<span class="font-mono {big ? 'text-2xl' : 'text-lg'} font-semibold leading-none">
				{formatValue(m)}{#if valueUnit(m)}<span class="ml-0.5 text-xs font-normal text-fg-muted"
						>{valueUnit(m)}</span
					>{/if}
			</span>
			{#if m.provider && availableProviders.length > 1}
				<span
					class="shrink-0 rounded px-1.5 py-0.5 text-[10px] text-white {providerBadgeClass(
						m.provider as ProviderKey
					)}"
					title={providerLabel(m.provider as ProviderKey)}
				>
					{providerLabelCompact(m.provider as ProviderKey)}
				</span>
			{/if}
		</div>
		{#if m.last_value_date && data.browser?.date && m.last_value_date < data.browser.date}<span class="text-[10px] text-fg-muted">{m.last_value_date.slice(5)} 기준</span>{/if}
		{#if m.status}<span class="text-[11px] {STATUS_TEXT_CLASS[m.status]}">● {m.status_label}</span>{/if}
		{#if m.sparkline.length > 1 && !isFlat(m.sparkline)}<Sparkline data={m.sparkline} height={big ? 40 : 24} color="var(--color-series-1)" minSpan={m.min_span ?? 0} endColor={m.status ? STATUS_DOT_COLOR[m.status] : undefined} />{#if sparkCaption(m.change)}<span class="text-[10px] text-fg-muted">{sparkCaption(m.change)}</span>{/if}{:else if m.sparkline.length > 1}<span class="text-[10px] text-fg-muted">변동 없음</span>{/if}
	</a>
{/snippet}

<svelte:head><title>메트릭 브라우저 · RunPulse</title></svelte:head>

<!-- 헤더 -->
<div class="flex items-center gap-2 border-b border-border-subtle px-4 py-3">
	<h1 class="text-base font-semibold">메트릭 브라우저</h1>
	{#if data.browser?.date}
		<span class="ml-auto text-xs text-fg-muted">{data.browser.date}</span>
	{/if}
</div>

<svelte:window onkeydown={onKey} />

{#if data.errorMessage}
	<div class="px-4 py-8 text-center">
		<p class="text-sm text-fg-secondary">{data.errorMessage}</p>
	</div>
{:else if categories.length === 0}
	<div class="px-4 py-8 text-center">
		<p class="text-sm text-fg-muted">데이터 수집 중</p>
	</div>
{:else}
	<div class="border-b border-border-subtle px-4 py-2">
		<input
			bind:this={searchEl}
			type="search"
			bind:value={query}
			oninput={syncQuery}
			placeholder="지표 검색 ( / )"
			aria-label="지표 검색"
			class="w-full rounded-lg border border-border-subtle bg-surface-2 px-3 py-2 text-sm text-fg-primary placeholder:text-fg-muted"
		/>
	</div>

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

	<!-- Provider 칩 필터 — P3 Provider Transparency (provider 1종뿐이면 숨김) -->
	{#if availableProviders.length > 1}
		<div class="flex gap-2 overflow-x-auto border-b border-border-subtle px-4 py-2">
			<button
				class="shrink-0 rounded-full px-3 py-1 text-xs {selectedProvider === 'all'
					? 'bg-fg-primary text-surface-1'
					: 'bg-surface-2 text-fg-secondary'}"
				onclick={() => (selectedProvider = 'all')}>모든 Provider</button
			>
			{#each availableProviders as key}
				<button
					class="shrink-0 rounded-full px-3 py-1 text-xs {selectedProvider === key
						? 'bg-fg-primary text-surface-1'
						: 'bg-surface-2 text-fg-secondary'}"
					onclick={() => (selectedProvider = key)}>{providerLabel(key as ProviderKey)}</button
				>
			{/each}
		</div>
	{/if}

	<!-- 카테고리별 섹션 -->
	<div class="flex flex-col gap-6 px-4 py-4">
		{#if searching && visibleCategories.length === 0}
			<p class="py-8 text-center text-sm text-fg-muted">‘{query.trim()}’에 맞는 지표가 없습니다.</p>
		{/if}
		{#if coreMetrics.length}
			<section>
				<h2 class="mb-2 text-xs font-medium uppercase tracking-wide text-fg-muted">핵심 지표</h2>
				<div class="grid grid-cols-2 gap-2 lg:grid-cols-4">
					{#each coreMetrics as m}
						{@render card(m, true)}
					{/each}
				</div>
			</section>
		{/if}
		{#each visibleCategories as cat}
			{#if showCore && !searching && COLLAPSED.has(cat.category)}
				<details>
					<summary class="cursor-pointer text-xs font-medium uppercase tracking-wide text-fg-muted hover:text-fg-secondary"
						>{cat.label} ({cat.metrics.length}) — 세부 지표</summary
					>
					<div class="mt-2 grid grid-cols-2 gap-2 sm:grid-cols-3">
						{#each cat.metrics as m}
							{@render card(m, false)}
						{/each}
					</div>
				</details>
			{:else}
				<section>
					<h2 class="mb-2 text-xs font-medium uppercase tracking-wide text-fg-muted">{cat.label}</h2>
					<div class="grid grid-cols-2 gap-2 sm:grid-cols-3">
						{#each cat.metrics as m}
							{@render card(m, false)}
						{/each}
					</div>
				</section>
			{/if}
		{/each}
	</div>
{/if}
