<script lang="ts">
	// 메트릭 브라우저 상단 Training Balance 요약 카드 — 작은 레이더 + 같은 정보 표 + 상세 링크(설계 §7).
	// 자체 로드(LoadResult). collecting 이면 EmptyState "데이터 수집 중" + 축별 사유.
	import { onMount } from 'svelte';
	import { base } from '$app/paths';
	import { getTrainingBalance } from '$lib/api/balance';
	import { toResult, type LoadResult } from '$lib/loadFailure';
	import type { TrainingBalance } from '$lib/types/trainingBalance';
	import { COLLECTING } from '$lib/balanceView';
	import BalanceRadar from '$lib/components/BalanceRadar.svelte';
	import BalanceTable from '$lib/components/BalanceTable.svelte';
	import EmptyState from '$lib/components/EmptyState.svelte';
	import ErrorState from '$lib/components/ErrorState.svelte';
	import Skeleton from '$lib/components/Skeleton.svelte';

	let result = $state<LoadResult<TrainingBalance> | null>(null);

	async function load() {
		result = await toResult(getTrainingBalance(null, 0));
	}
	onMount(load);

	const data = $derived(result?.ok ? result.data : null);
	const reasons = $derived(
		data ? data.axes.filter((a) => a.score == null).map((a) => `${a.label}: ${a.reason_text ?? COLLECTING}`) : []
	);
</script>

<section aria-labelledby="balance-card-h" class="rounded-xl bg-surface-2 p-3" data-testid="balance-card">
	<div class="mb-2 flex items-center justify-between gap-2">
		<h2 id="balance-card-h" class="text-xs font-medium uppercase tracking-wide text-fg-muted">훈련 균형</h2>
		<a href="{base}/library/balance" class="flex min-h-11 items-center text-xs text-semantic-teal">자세히 보기 ›</a>
	</div>
	{#if result === null}
		<Skeleton kind="chart" />
	{:else if !result.ok}
		<ErrorState failure={result.failure} onRetry={load} compact />
	{:else if data && data.state === 'collecting'}
		<EmptyState title={COLLECTING} description="훈련·컨디션 기록이 더 쌓이면 균형 레이더를 보여 드려요." />
		<ul class="flex flex-col gap-0.5 text-xs text-fg-muted" data-testid="balance-reasons">
			{#each reasons as t (t)}<li>{t}</li>{/each}
		</ul>
	{:else if data}
		<div class="flex flex-col items-center gap-3 sm:flex-row sm:items-start">
			<div class="w-full sm:w-1/2"><BalanceRadar {data} compact id="balance-card-radar" /></div>
			<div class="w-full sm:w-1/2"><BalanceTable {data} compact /></div>
		</div>
	{/if}
</section>
