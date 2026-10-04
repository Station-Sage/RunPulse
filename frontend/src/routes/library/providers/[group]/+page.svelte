<script lang="ts">
	import type { ProviderGroupPageData } from './+page';
	import ProviderPairChart from '$lib/components/ProviderPairChart.svelte';
	import ProviderPairList from '$lib/components/ProviderPairList.svelte';
	import { providerName } from '$lib/providerMatrix';
	import { base } from '$app/paths';

	let { data }: { data: ProviderGroupPageData } = $props();
	const label = $derived(data.pairs?.row.label ?? data.group);
	const back = $derived(`${base}/library/providers${data.days === 28 ? '' : `?days=${data.days}`}`);
</script>

<svelte:head><title>{label} · 소스 비교 · RunPulse</title></svelte:head>

<div class="flex h-12 items-center gap-2 border-b border-border-subtle px-4">
	<a href={back} class="shrink-0 text-fg-muted" aria-label="소스 비교로">‹</a>
	<nav aria-label="경로" class="flex min-w-0 items-center gap-1.5 text-xs text-fg-muted">
		<a href="{base}/library" class="hover:text-fg-secondary">Library</a>
		<span aria-hidden="true">›</span>
		<a href={back} class="hover:text-fg-secondary">소스 비교</a>
		<span aria-hidden="true">›</span>
		<h1 class="truncate text-sm font-semibold text-fg-primary">{label}</h1>
	</nav>
</div>

{#if data.errorMessage || !data.pairs}
	<div class="px-4 py-8 text-center">
		<p class="text-sm text-fg-secondary">{data.errorMessage ?? '데이터가 없어요.'}</p>
		<a href={back} class="mt-2 block text-xs text-fg-muted underline">← 소스 비교로</a>
	</div>
{:else}
	<div class="space-y-3 px-4 py-3">
		<p class="text-sm text-fg-primary">{data.pairs.summary_text}</p>
		{#if data.pairs.diff}
			<p class="text-xs text-fg-muted">{data.pairs.diff.label} · {data.pairs.diff.n}건 · 최근 {data.days / 7}주</p>
		{/if}
		<ul class="space-y-0.5 text-xs text-fg-muted">
			{#each Object.entries(data.pairs.definitions) as [p, d]}
				{#if d}<li>{providerName(p)}: {d}</li>{/if}
			{/each}
		</ul>
	</div>
	{#if data.pairs.state === 'ok' || data.pairs.state === 'insufficient'}
		<div class="px-4"><ProviderPairChart data={data.pairs} /></div>
		<ProviderPairList data={data.pairs} />
	{/if}
{/if}
