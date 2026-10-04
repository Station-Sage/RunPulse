<script lang="ts">
	// 예측 기록 근거 — 신호별 환산 기록·가중치, 범위·신뢰도, 제한 요인, 마라톤 모델 비교(21 V8).
	import type { MetricExplainTerm, PredictionEvidence } from '$lib/types';
	import { formatDuration } from '$lib/format';

	let { evidence, terms }: { evidence: PredictionEvidence; terms: MetricExplainTerm[] } = $props();

	const conf = $derived(evidence.confidence != null ? Math.round(evidence.confidence * 100) : null);
	const lowConf = $derived(evidence.confidence != null && evidence.confidence < 0.5);
</script>

<section class="flex flex-col gap-3" data-testid="prediction-evidence">
	{#if evidence.range}
		<div class="flex items-baseline justify-between text-sm">
			<span class="text-fg-secondary">예상 범위</span>
			<span class="num">{formatDuration(evidence.range.low)} – {formatDuration(evidence.range.high)}</span>
		</div>
	{/if}
	{#if conf != null}
		<div class="flex flex-col gap-1">
			<div class="flex justify-between text-xs text-fg-muted">
				<span>신뢰도</span><span class="num">{conf}%</span>
			</div>
			<div class="h-1.5 rounded-full bg-surface-3">
				<div class="h-1.5 rounded-full {lowConf ? 'bg-semantic-amber' : 'bg-semantic-teal'}" style="width: {conf}%"></div>
			</div>
			{#if lowConf}<p class="text-[11px] text-semantic-amber">신뢰도가 낮아 범위로 봐주세요.</p>{/if}
		</div>
	{/if}

	{#if terms.length > 0}
		<div class="flex flex-col gap-1.5">
			<p class="text-xs uppercase tracking-wide text-fg-muted">신호별 환산 기록</p>
			{#each terms as t (t.slug)}
				<div class="flex items-center justify-between text-sm">
					<span>{t.label}{#if t.weight != null} <span class="text-[11px] text-fg-muted">· 가중 {Math.round(t.weight * 100)}%</span>{/if}</span>
					<span class="num text-fg-secondary">{typeof t.raw === 'number' ? formatDuration(t.raw) : t.raw}</span>
				</div>
			{/each}
		</div>
	{/if}

	{#if evidence.models}
		<div class="flex flex-col gap-1.5">
			<p class="text-xs uppercase tracking-wide text-fg-muted">모델 비교</p>
			{#each evidence.models as m (m.name)}
				<div class="flex items-center justify-between text-sm">
					<span>{m.name}</span><span class="num text-fg-secondary">{formatDuration(m.sec)}</span>
				</div>
			{/each}
		</div>
	{/if}

	{#if evidence.limiting?.length}
		<div class="flex flex-col gap-1">
			<p class="text-xs uppercase tracking-wide text-fg-muted">신뢰를 낮추는 요인</p>
			<ul class="list-disc pl-4 text-xs text-fg-secondary">
				{#each evidence.limiting as r (r)}<li>{r}</li>{/each}
			</ul>
		</div>
	{/if}
</section>
