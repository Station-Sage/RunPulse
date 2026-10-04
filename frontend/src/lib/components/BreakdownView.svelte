<script lang="ts">
	// §C3.2 분해 v2 본문 4블록 — explain=1(TSB/CTL/ATL/UTRS/CIRS/RRI)만 이 형태로 온다.
	// ③원천 행 탭(D3, 경로 이동)은 아직 없어 비인터랙티브로 둔다(2-5 범위 밖, 별도 판단 필요).
	import type { MetricExplainData, MetricExplainTerm } from '$lib/types';
	import { statusColorVar } from '$lib/statusColor';
	import { formatChange } from '$lib/format';
	import Icon from '$lib/components/Icon.svelte';

	let {
		data,
		trendHref,
		onDrillTerm
	}: {
		data: MetricExplainData;
		trendHref?: string;
		onDrillTerm?: (token: string) => void;
	} = $props();

	const pinIndex = $derived(data.meaning.bands.findIndex((b) => b.status === data.status));

	// UTRS/CIRS는 loss로 이미 내림차순 정렬돼 온다 — 여기선 순서를 보존만 한다.
	const terms = $derived(data.formula.terms);
	const hasLoss = $derived(terms.length > 0 && terms[0].loss != null);
	const maxAbsContribution = $derived(
		Math.max(1e-9, ...terms.map((t) => Math.abs(t.contribution ?? 0)))
	);

	function barWidthPct(t: MetricExplainTerm): number {
		if (t.role === 'factor') return Math.round((t.ratio ?? 0) * 100);
		return Math.round((Math.abs(t.contribution ?? 0) / maxAbsContribution) * 100);
	}

	function barIsNegative(t: MetricExplainTerm): boolean {
		if (t.role === 'factor') return false;
		return (t.contribution ?? 0) < 0;
	}
</script>

{#snippet row(term: MetricExplainTerm, i: number)}
	<div class="flex flex-1 flex-col gap-1">
		<div class="flex items-center justify-between text-sm">
			<span class="flex items-center gap-1.5">
				{term.label}
				{#if hasLoss && i === 0}
					<span class="rounded bg-surface-3 px-1.5 py-0.5 text-[10px] text-fg-muted"
						>가장 크게 끌어내림</span
					>
				{/if}
			</span>
			<span class="num text-fg-secondary">
				{#if term.role === 'factor'}
					×{Math.round((term.ratio ?? 0) * 100)}%
				{:else if term.contribution != null}
					{term.sign === '-' ? '−' : term.sign === '+' ? '+' : ''}{Math.abs(term.contribution)}
				{/if}
			</span>
		</div>
		<div class="h-1.5 rounded-full bg-surface-3">
			<div
				class="h-1.5 rounded-full {barIsNegative(term) ? 'bg-delta-worse' : 'bg-delta-better'}"
				style="width: {barWidthPct(term)}%"
			></div>
		</div>
	</div>
{/snippet}

<div class="flex flex-col gap-5 p-4">
	<!-- ①의미 -->
	<section class="flex flex-col gap-2">
		<p class="text-sm text-fg-secondary">{data.meaning.what}</p>

		{#if data.meaning.bands.length > 0}
			<div class="flex h-2 overflow-hidden rounded-full" role="img" aria-label="등급 밴드">
				{#each data.meaning.bands as band, i (i)}
					<div class="relative flex-1" style="background-color: {statusColorVar(band.status)}">
						{#if i === pinIndex}
							<div
								class="absolute -top-1.5 left-1/2 h-4 w-4 -translate-x-1/2 rounded-full border-2 border-surface-1 bg-fg-primary"
								aria-hidden="true"
							></div>
						{/if}
					</div>
				{/each}
			</div>
			<div class="flex text-[11px] text-fg-muted">
				{#each data.meaning.bands as band, i (i)}
					<span class="flex-1 truncate text-center">{band.label}</span>
				{/each}
			</div>
		{/if}

		{#if data.meaning.baseline.avg_7d != null}
			<p class="text-xs text-fg-muted">
				7일 평균 {data.meaning.baseline.avg_7d}{#if data.meaning.baseline.delta_1d != null}
					· 어제 대비 {formatChange(data.meaning.baseline.delta_1d, 1)}{/if}
			</p>
		{/if}

		{#if data.meaning.so_what}
			<p class="text-sm font-medium">{data.meaning.so_what}</p>
		{/if}
	</section>

	<!-- ②공식·기여 -->
	{#if terms.length > 0}
		<section class="flex flex-col gap-2">
			<p class="font-mono text-xs text-fg-muted">{data.formula.text}</p>
			<p class="text-[11px] text-fg-muted">
				{data.formula.version} · {data.formula.computed_at}
			</p>
			<div class="flex flex-col gap-1.5">
				{#each terms as term, i (term.slug)}
					{#if term.drill && onDrillTerm}
						{@const drill = term.drill}
						<button
							type="button"
							class="flex w-full items-center gap-2 rounded-lg px-1 py-1 text-left hover:bg-surface-2"
							onclick={() => onDrillTerm(drill)}
						>
							{@render row(term, i)}
							<Icon name="chevron" class="h-3.5 w-3.5 shrink-0 text-fg-muted" />
						</button>
					{:else}
						<div class="flex w-full items-center gap-2 px-1 py-1">
							{@render row(term, i)}
						</div>
					{/if}
				{/each}
			</div>
		</section>
	{/if}

	<!-- ③원천 -->
	{#if data.sources.length > 0}
		<section class="flex flex-col gap-1.5">
			<p class="text-xs uppercase tracking-wide text-fg-muted">원천</p>
			{#each data.sources as src, i (i)}
				<div class="flex items-center justify-between rounded-md bg-surface-2 px-3 py-2 text-sm">
					<div class="flex flex-col">
						{#if src.type === 'activity' && src.id != null && onDrillTerm && src.unit === 'TRIMP'}
							<button type="button" class="text-left text-semantic-teal hover:underline" data-testid="source-activity" onclick={() => onDrillTerm(`m.trimp@a${src.id}`)}>{src.label} ›</button>
						{:else}
							<span>{src.label}</span>
						{/if}
						{#if src.date}<span class="text-[11px] text-fg-muted">{src.date}</span>{/if}
					</div>
					<div class="flex flex-col items-end">
						{#if src.value != null}
							<span class="num text-fg-secondary">{src.value}{src.unit ? ` ${src.unit}` : ''}</span>
						{/if}
						{#if src.effect}<span class="text-[11px] text-fg-muted">{src.effect}</span>{/if}
					</div>
				</div>
			{/each}
		</section>
	{/if}

	{#if terms.length === 0 && data.sources.length === 0}
		<p class="text-sm text-fg-secondary">
			이 지표는 {data.provider.kind === 'runpulse_calc' ? 'RunPulse 계산' : data.provider.kind}에서
			직접 받은 값이에요.
		</p>
	{/if}

	<!-- ④푸터 -->
	<section class="flex flex-col gap-1 border-t border-border-subtle pt-3 text-xs text-fg-muted">
		<span>RunPulse 계산 · {data.provider.version} · {data.provider.computed_at}</span>
		{#if trendHref}
			<a href={trendHref} class="text-fg-secondary underline">추세·과거 보기 →</a>
		{/if}
	</section>
</div>
