<script lang="ts">
	// 허브 ①②: 목표 헤더 + 예측 vs 목표 격차 + 90일 추이(design 10-today §3 ①②).
	import type { RaceHubGoal, RaceHubPrediction } from '$lib/types';
	import TrendChart from './TrendChart.svelte';
	import { rangeLabel, confidenceLabel } from '$lib/predictionCompare';
	import { countdownLabel, distanceLabel, gapVerdict, requiredImprovement, trendDelta } from '$lib/raceHub';
	import { formatDuration } from '$lib/format';

	let { goal, pred }: { goal: RaceHubGoal; pred: RaceHubPrediction | null } = $props();

	const TONE_CLASS: Record<string, string> = {
		ahead: 'text-semantic-green',
		on: 'text-semantic-teal',
		behind: 'text-semantic-amber',
		unknown: 'text-fg-muted font-normal text-xs'
	};
	const verdict = $derived(pred ? gapVerdict(pred.gap_sec) : null);
	const selfRow = $derived(pred?.compare?.rows.find((r) => r.key === 'self') ?? null);
	const need = $derived(pred ? requiredImprovement(pred.gap_sec, pred.value_sec, selfRow?.confidence) : null);
	const delta = $derived(pred ? trendDelta(pred.history) : null);
</script>

<section aria-label="레이스 예측 요약" class="flex flex-col gap-3 rounded-lg border border-border-subtle bg-surface-2 p-4">
	<div class="flex items-center gap-3">
		<span class="font-mono text-4xl font-bold leading-none">{countdownLabel(goal.days_left)}</span>
		<div class="flex min-w-0 flex-1 flex-col">
			<span class="truncate text-sm font-medium">{goal.name ?? distanceLabel(goal.distance_km)}</span>
			<span class="text-xs text-fg-muted"
				>{goal.race_date} · {distanceLabel(goal.distance_km)}{goal.weeks_left > 0 ? ` · ${goal.weeks_left}주 남음` : ''}</span
			>
		</div>
	</div>

	<div class="grid grid-cols-2 gap-3">
		<div class="flex flex-col gap-0.5">
			<span class="text-xs text-fg-muted">예측 기록</span>
			<span class="font-mono text-2xl font-bold">{pred ? formatDuration(pred.value_sec) : '예측 수집 중'}</span>
		</div>
		<div class="flex flex-col gap-0.5">
			<span class="text-xs text-fg-muted">목표</span>
			{#if goal.target_time_sec != null}
				<span class="font-mono text-2xl font-bold">{formatDuration(goal.target_time_sec)}</span>
			{:else}
				<span class="font-mono text-lg text-fg-muted">미설정</span>
			{/if}
		</div>
	</div>

	{#if verdict}
		<p class="text-sm font-medium {TONE_CLASS[verdict.tone]}">{verdict.label}</p>
		{#if need}<p class="text-xs text-fg-muted" data-testid="required-improvement">{need.label}</p>{/if}
	{/if}

	{#if selfRow && (rangeLabel(selfRow) || confidenceLabel(selfRow.confidence))}
		<p class="text-xs text-fg-muted">
			{rangeLabel(selfRow) ? `모델 범위 ${rangeLabel(selfRow)}` : ''}{rangeLabel(selfRow) && confidenceLabel(selfRow.confidence)
				? ' · '
				: ''}{confidenceLabel(selfRow.confidence) ? `신뢰도 ${confidenceLabel(selfRow.confidence)}` : ''} · 15℃ 기준
		</p>
	{/if}

	{#if pred && pred.history.length > 1}
		<div class="flex flex-col gap-1 border-t border-border-subtle pt-3">
			<div class="flex items-baseline justify-between">
				<span class="text-xs text-fg-muted">예측 기록 추이 · 최근 90일</span>
				{#if delta}<span class="text-xs {delta.deltaSec < -30 ? 'text-semantic-green' : 'text-fg-muted'}">{delta.label}</span>{/if}
			</div>
			<TrendChart
				series={[{ key: 'pred', label: '예측', color: '#14b8a6', points: pred.history }]}
				height={72}
				formatValue={(v) => formatDuration(Math.round(v))}
			/>
		</div>
	{/if}
</section>
