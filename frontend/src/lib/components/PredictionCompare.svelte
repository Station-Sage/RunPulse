<script lang="ts">
	// 레이스 예측 3경로 비교(P7-PRED-72): Garmin / RunPulse·기기 심박 기준 / RunPulse·자체 추정 + 차이의 이유.
	import type { PredictionCompare } from '$lib/types';
	import { clock, confidenceLabel, contributionLabel, diffVsSelf, rangeLabel } from '$lib/predictionCompare';

	let { compare }: { compare: PredictionCompare } = $props();
	const self = $derived(compare.rows.find((r) => r.key === 'self'));
</script>

<div class="flex flex-col gap-2" aria-label="예측 비교">
	<span class="text-xs text-fg-muted">예측 비교 · 15℃ 기준</span>
	<ul class="flex flex-col divide-y divide-border-subtle rounded-md border border-border-subtle">
		{#each compare.rows as row (row.key)}
			{@const diff = diffVsSelf(row, self)}
			{@const range = rangeLabel(row)}
			{@const conf = confidenceLabel(row.confidence)}
			<li class="flex items-baseline justify-between gap-3 px-3 py-2">
				<div class="flex min-w-0 flex-col">
					<span class="text-xs {row.key === 'self' ? 'font-semibold' : row.candidate ? 'text-fg-muted italic' : 'text-fg-secondary'}">{row.label}</span>
					{#if row.value_sec != null && (range || conf)}
						<span class="text-[11px] text-fg-muted"
							>{range ? `80% ${range}` : ''}{range && conf ? ' · ' : ''}{conf ? `신뢰도 ${conf}` : ''}</span
						>
					{/if}
					{#if row.key === 'garmin' && row.stale_days != null && row.stale_days > 14}
						<span class="text-[11px] text-semantic-amber">{row.stale_days}일 전 값</span>
					{/if}
				</div>
				<div class="flex shrink-0 items-baseline gap-2">
					<span class="font-mono text-base font-bold">{row.value_sec != null ? clock(row.value_sec) : '—'}</span>
					{#if diff}
						<span class="font-mono text-[11px] text-fg-muted">{diff}</span>
					{/if}
				</div>
			</li>
		{/each}
	</ul>
	{#if self?.contributions}
		{@const c = contributionLabel(self.contributions)}
		{#if c}
			<span class="text-[11px] text-fg-muted">자체 추정 근거 비중 · {c}</span>
		{/if}
	{/if}
	{#if self?.reasons && self.reasons.length}
		<span class="text-[11px] text-fg-muted">불확실성 · {self.reasons.join(' · ')}</span>
	{/if}
	{#each compare.notes as note}
		<p class="text-[11px] leading-tight text-fg-muted">{note}</p>
	{/each}
</div>
