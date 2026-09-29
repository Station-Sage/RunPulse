<script lang="ts">
	// B7 체력·피로·폼 차트 — 트렌드 3종은 스트리밍. 데이터가 모자라면 블록을 숨기고, 실패는 compact 재시도.
	import type { FormChartData } from '../../routes/today/+page';
	import type { RaceHubData } from '$lib/types';
	import FormChart from '$lib/components/FormChart.svelte';
	import Skeleton from '$lib/components/Skeleton.svelte';
	import ErrorState from '$lib/components/ErrorState.svelte';

	let { chart, raceHub, onMonth, onRetry }: {
		chart: Promise<FormChartData>;
		raceHub: Promise<RaceHubData | null>;
		onMonth: () => void;
		onRetry: () => void;
	} = $props();

	const ready = $derived(Promise.all([chart, raceHub]));
</script>

{#await ready}
	<Skeleton kind="chart" class="min-h-[200px]" />
{:then [c, hub]}
	{#if c.ctl.points.length > 1 && c.tsb.points.length > 1}
		<section class="flex flex-col gap-2 rounded-lg border border-border-subtle bg-surface-2 p-3" aria-label="피트니스·폼">
			<div class="flex items-center justify-between text-xs text-fg-muted">
				<span>체력·피로·폼 · 최근 3개월{hub?.projection ? ' + 레이스 예측' : ''}</span>
				<button type="button" onclick={onMonth} class="hover:text-fg-primary">이번 달 이야기 →</button>
			</div>
			<FormChart
				ctl={c.ctl.points}
				atl={c.atl.points}
				tsb={c.tsb.points}
				projection={hub?.projection ?? null}
				raceDate={hub?.goal?.race_date ?? null}
			/>
		</section>
	{/if}
{:catch}
	<ErrorState compact message="차트를 불러오지 못했어요" {onRetry} />
{/await}
