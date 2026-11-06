<script lang="ts">
	// Training Balance 상세(07 §7d) — 레이더 + 바로 아래 같은 정보 표(항상 보임) + 편향 주석. 설계 balance-radar §7.
	import PageHead from '$lib/components/ui/PageHead.svelte';
	import { base } from '$app/paths';
	import type { BalancePageData } from './+page';
	import { COLLECTING } from '$lib/balanceView';
	import BalanceRadar from '$lib/components/BalanceRadar.svelte';
	import BalanceTable from '$lib/components/BalanceTable.svelte';
	import EmptyState from '$lib/components/EmptyState.svelte';
	import LoadFailure from '$lib/components/LoadFailure.svelte';

	let { data }: { data: BalancePageData } = $props();

	const bal = $derived(data.balance.ok ? data.balance.data : null);
	const reasons = $derived(
		bal ? bal.axes.filter((a) => a.score == null).map((a) => `${a.label}: ${a.reason_text ?? COLLECTING}`) : []
	);
</script>

<PageHead title="훈련 균형 · Library" heading={null} />

<div class="flex h-12 items-center gap-2 border-b border-border-subtle px-4">
	<a href="{base}/library/metrics" class="shrink-0 text-fg-muted" aria-label="메트릭 브라우저로">‹</a>
	<nav aria-label="경로" class="flex min-w-0 items-center gap-1.5 text-xs text-fg-muted">
		<a href="{base}/library" class="hover:text-fg-secondary">Library</a>
		<span aria-hidden="true">›</span>
		<a href="{base}/library/metrics" class="hover:text-fg-secondary">메트릭</a>
		<span aria-hidden="true">›</span>
		<h1 class="truncate text-sm font-semibold text-fg-primary">훈련 균형</h1>
	</nav>
</div>

<div class="mx-auto flex max-w-3xl flex-col gap-4 px-4 py-4 pb-24">
	{#if !data.balance.ok}
		<LoadFailure failure={data.balance.failure} retryKey="app:balance" backHref="{base}/library/metrics" backLabel="메트릭 브라우저로" />
	{:else if bal && bal.state === 'collecting'}
		<EmptyState title={COLLECTING} description="훈련·컨디션 기록이 더 쌓이면 균형 레이더를 보여 드려요." />
		<ul class="flex flex-col gap-1 text-sm text-fg-secondary" data-testid="balance-reasons">
			{#each reasons as t (t)}<li>{t}</li>{/each}
		</ul>
		<BalanceTable data={bal} />
	{:else if bal}
		<p class="text-sm text-fg-secondary">
			최근 {bal.window_weeks}주 훈련 구성이 목표 대비 얼마나 채워졌는지 보여 줘요. 100 이 목표, 균형 구간 밖이면 부족·과다로 표시해요.
		</p>
		<BalanceRadar data={bal} />
		<BalanceTable data={bal} />
	{/if}
</div>
