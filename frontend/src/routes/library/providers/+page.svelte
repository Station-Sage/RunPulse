<script lang="ts">
	// 03c-library.md 3-G-1 — Provider 정체성 매트릭스 (기간 집계).
	import type { ProvidersMatrixPageData } from './+page';
	import ProviderComparison from '$lib/components/ProviderComparison.svelte';
	import { goto } from '$app/navigation';
	import { base } from '$app/paths';

	let { data }: { data: ProvidersMatrixPageData } = $props();

	const PERIODS = [
		{ key: 28, label: '4주' },
		{ key: 56, label: '8주' },
		{ key: 84, label: '12주' }
	];

	function selectPeriod(days: number) {
		goto(`?days=${days}`);
	}
</script>

<!-- 헤더 -->
<div class="flex items-center gap-2 border-b border-border-subtle px-4 py-3">
	<a href="{base}/library" class="shrink-0 text-fg-muted" aria-label="Library로">←</a>
	<h1 class="text-base font-semibold">Provider 정체성 매트릭스</h1>
</div>

<!-- 기간 선택 버튼 -->
<div class="flex gap-2 border-b border-border-subtle px-4 py-2">
	{#each PERIODS as p}
		<button
			class="rounded-full px-3 py-1 text-xs {data.days === p.key
				? 'bg-fg-primary text-surface-1'
				: 'bg-surface-2 text-fg-secondary'}"
			onclick={() => selectPeriod(p.key)}
		>
			{p.label}
		</button>
	{/each}
</div>

{#if data.errorMessage && !data.comparison}
	<div class="px-4 py-8 text-center">
		<p class="text-sm text-fg-secondary">{data.errorMessage}</p>
	</div>
{:else if data.comparison?.state === 'no_data'}
	<div class="px-4 py-8 text-center">
		<p class="text-sm text-fg-secondary">이 기간에 비교할 활동이 없습니다.</p>
	</div>
{:else}
	<ProviderComparison data={data.comparison} showPrimaryReason={true} discrepancyThreshold={5} />
{/if}
