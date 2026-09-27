<script lang="ts">
	// 레이스 예측 3경로 비교(P7-PRED-72): Garmin / RunPulse·기기 심박 기준 / RunPulse·자체 추정 + 차이의 이유.
	// 기본 표시는 3경로. r4 섀도 후보(검토 중 알고리즘)는 접어 두고, 자체 추정의 근거 비중·불확실성도 접는다.
	import type { PredictionCompare } from '$lib/types';
	import { clock, confidenceLabel, contributionLabel, diffVsSelf, rangeLabel } from '$lib/predictionCompare';
	import type { CompareRow } from '$lib/predictionCompare';

	let { compare }: { compare: PredictionCompare } = $props();
	const self = $derived(compare.rows.find((r) => r.key === 'self'));
	const main = $derived(compare.rows.filter((r) => !r.candidate));
	const candidates = $derived(compare.rows.filter((r) => r.candidate));
	const basis = $derived(self?.contributions ? contributionLabel(self.contributions) : null);
	const reasons = $derived(self?.reasons ?? []);
</script>

{#snippet rowItem(row: CompareRow)}
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
{/snippet}

<div class="flex flex-col gap-2" aria-label="예측 비교">
	<span class="text-xs text-fg-muted">예측 비교 · 15℃ 기준</span>
	<ul class="flex flex-col divide-y divide-border-subtle rounded-md border border-border-subtle">
		{#each main as row (row.key)}
			{@render rowItem(row)}
		{/each}
	</ul>
	{#each compare.notes as note}
		<p class="text-[11px] leading-tight text-fg-muted">{note}</p>
	{/each}
	{#if basis || reasons.length}
		<details class="text-[11px] text-fg-muted">
			<summary class="cursor-pointer hover:text-fg-secondary">자체 추정 근거 · 불확실성</summary>
			<div class="mt-1 flex flex-col gap-1">
				{#if basis}<span>근거 비중 · {basis}</span>{/if}
				{#if reasons.length}<span>불확실성 · {reasons.join(' · ')}</span>{/if}
			</div>
		</details>
	{/if}
	{#if candidates.length}
		<details class="text-[11px] text-fg-muted">
			<summary class="cursor-pointer hover:text-fg-secondary">검토 중 알고리즘 {candidates.length}건 (기본값 아님)</summary>
			<ul class="mt-1 flex flex-col divide-y divide-border-subtle rounded-md border border-border-subtle">
				{#each candidates as row (row.key)}
					{@render rowItem(row)}
				{/each}
			</ul>
		</details>
	{/if}
</div>
