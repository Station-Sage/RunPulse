<script lang="ts">
	// 오늘 화면 최상단 레이스 허브 — D-day 히어로, 예측 vs 목표, 예측 추이.
	// DECISIONS.md [P7-IMPL-RACE-HUB-UI]: 목표 있으면 D-day, 없으면 등록 유도 카드.
	import type { RaceHubData } from '$lib/types';
	import TrendChart from './TrendChart.svelte';
	import { gapTone, formatGap, predictionToSeries } from '$lib/raceHub';
	import { formatDuration } from '$lib/format';
	import { base } from '$app/paths';

	let { data }: { data: RaceHubData | null } = $props();

	const TONE_COLOR: Record<string, string> = {
		green: '#22c55e',
		teal: '#14b8a6',
		amber: '#f59e0b'
	};
	const TONE_CLASS: Record<string, string> = {
		green: 'text-semantic-green',
		teal: 'text-semantic-teal',
		amber: 'text-semantic-amber'
	};

	const tone = $derived(data?.prediction != null ? gapTone(data.prediction.gap_sec) : 'teal');
	const predSeries = $derived(
		data?.prediction && data.prediction.history.length > 1
			? [predictionToSeries(data.prediction.history, TONE_COLOR[tone])]
			: []
	);
</script>

{#if !data?.goal}
	<a
		href="{base}/coach/plan/new"
		class="flex items-center justify-between rounded-lg border border-dashed border-border-subtle px-4 py-3 text-sm text-fg-secondary hover:border-fg-muted hover:text-fg-primary"
	>
		<span>목표 레이스를 등록하면 D-day와 예측 기록을 볼 수 있어요.</span>
		<span class="ml-2 shrink-0">→</span>
	</a>
{:else}
	{@const goal = data.goal}
	{@const pred = data.prediction}
	<div class="flex flex-col gap-2 rounded-lg border border-border-subtle bg-surface-2 p-4">
		<!-- 헤더: 레이스 이름 + D-day 히어로 -->
		<div class="flex items-baseline justify-between gap-2">
			<span class="truncate text-sm font-medium text-fg-primary">{goal.name}</span>
			<span class="shrink-0 font-mono text-4xl font-bold tabular-nums text-fg-primary"
				>D-{goal.days_left}</span
			>
		</div>
		<span class="text-xs text-fg-muted">{goal.race_date} · {goal.distance_km}km</span>

		{#if pred}
			<!-- 예측 vs 목표 vs 격차 -->
			<div class="mt-1 flex flex-wrap items-baseline gap-x-4 gap-y-1">
				<div class="flex flex-col">
					<span class="text-[10px] uppercase tracking-wide text-fg-muted">예측</span>
					<span class="font-mono text-xl font-semibold text-fg-primary"
						>{formatDuration(pred.value_sec)}</span
					>
				</div>
				{#if goal.target_time_sec != null}
					<div class="flex flex-col">
						<span class="text-[10px] uppercase tracking-wide text-fg-muted">목표</span>
						<span class="font-mono text-xl font-semibold text-fg-secondary"
							>{formatDuration(goal.target_time_sec)}</span
						>
					</div>
					{#if pred.gap_sec != null}
						<div class="flex flex-col">
							<span class="text-[10px] uppercase tracking-wide text-fg-muted">격차</span>
							<span class="font-mono text-xl font-semibold {TONE_CLASS[tone]}"
								>{formatGap(pred.gap_sec)}</span
							>
						</div>
					{/if}
				{/if}
			</div>

			<!-- 예측 추이 차트 (90일, 비인터랙티브) -->
			{#if predSeries.length > 0}
				<div class="mt-1">
					<p class="mb-1 text-[10px] uppercase tracking-wide text-fg-muted">90일 예측 추이</p>
					<TrendChart
						series={predSeries}
						height={64}
						interactive={false}
						formatValue={(v) => formatDuration(v)}
					/>
				</div>
			{/if}
		{:else}
			<p class="text-xs text-fg-muted">데이터 수집 중</p>
		{/if}
	</div>
{/if}
