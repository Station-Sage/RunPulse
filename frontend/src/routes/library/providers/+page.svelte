<script lang="ts">
	// S6 소스 비교 — 같은 러닝을 소스마다 어떻게 계산하는지.
	import type { ProvidersMatrixPageData } from './+page';
	import ProviderMatrix from '$lib/components/ProviderMatrix.svelte';
	import { PERIOD_DAYS, periodHref } from '$lib/providerMatrix';
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { base } from '$app/paths';

	let { data }: { data: ProvidersMatrixPageData } = $props();

	function selectPeriod(days: number) {
		goto(periodHref(page.url.search, days), { replaceState: true, keepFocus: true, noScroll: true });
	}
</script>

<svelte:head><title>소스 비교 · RunPulse</title></svelte:head>

<div class="flex h-12 items-center gap-2 border-b border-border-subtle px-4">
	<a href="{base}/library" class="shrink-0 text-fg-muted" aria-label="Library로">‹</a>
	<nav aria-label="경로" class="flex items-center gap-1.5 text-xs text-fg-muted">
		<a href="{base}/library" class="hover:text-fg-secondary">Library</a>
		<span aria-hidden="true">›</span>
		<h1 class="text-sm font-semibold text-fg-primary">소스 비교</h1>
	</nav>
</div>

<div role="group" aria-label="기간" class="flex gap-2 border-b border-border-subtle px-4 py-2">
	{#each PERIOD_DAYS as p}
		<button
			type="button"
			aria-pressed={data.days === p.days}
			class="rounded-full border px-3 py-1 text-xs {data.days === p.days
				? 'border-semantic-teal bg-semantic-teal/15 text-fg-primary'
				: 'border-border-subtle text-fg-secondary'}"
			onclick={() => selectPeriod(p.days)}
		>
			{p.label}
		</button>
	{/each}
</div>

{#if data.errorMessage && !data.matrix}
	<div class="px-4 py-8 text-center"><p class="text-sm text-fg-secondary">{data.errorMessage}</p></div>
{:else if !data.matrix || data.matrix.state === 'no_data'}
	<div class="px-4 py-8 text-center"><p class="text-sm text-fg-secondary">이 기간에 비교할 러닝이 없어요.</p></div>
{:else}
	<ProviderMatrix data={data.matrix} />
{/if}
