<script lang="ts">
	// "내 데이터 출처" — 한 줄 요약, 눌러서 소스별 커버리지 펼침.
	import SourceCoverage from './SourceCoverage.svelte';
	import { providerLabel } from '$lib/provider';
	import type { ProviderCoverage, ProviderStatusItem, ProviderKey } from '$lib/types';

	let { coverage, status }: { coverage: ProviderCoverage; status: ProviderStatusItem[] } = $props();
	let open = $state(false);

	const active = $derived(coverage.providers.filter((p) => p.sync_enabled !== false || p.total > 0));
	const summary = $derived(
		active.map((p) => `${providerLabel(p.provider as ProviderKey)} ${p.total}건`).join(' · ')
	);
</script>

<div class="flex flex-col gap-3 rounded-xl border border-border-subtle bg-surface-2 p-3">
	<button
		type="button"
		class="flex w-full items-center justify-between gap-2 text-left"
		aria-expanded={open}
		onclick={() => (open = !open)}
	>
		<span class="text-sm text-fg-secondary">{summary || '연결된 소스 없음'}</span>
		<span class="text-xs text-fg-muted">{open ? '접기' : '자세히'}</span>
	</button>
	{#if open}<SourceCoverage {coverage} {status} />{/if}
</div>
