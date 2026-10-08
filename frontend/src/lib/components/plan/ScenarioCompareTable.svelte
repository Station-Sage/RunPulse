<script lang="ts">
	// 프로그램 비교 표 — 데스크톱은 열 비교, 모바일은 가로 스냅 카드. 다른 값만 굵게.
	import { buildCompareRows, isRecommended, riskClass } from '$lib/planCompare';
	import type { PlanTemplate } from '$lib/types';

	let {
		templates,
		loading = null,
		disabled = false,
		onselect
	}: {
		templates: PlanTemplate[];
		loading?: number | null;
		disabled?: boolean;
		onselect: (weeks: number) => void;
	} = $props();

	const rows = $derived(buildCompareRows(templates));
</script>

<div
	class="flex snap-x snap-mandatory gap-3 overflow-x-auto pb-2 md:grid md:overflow-visible"
	style="--cols: {templates.length}"
	data-testid="scenario-compare"
>
	{#each templates as t, i (t.weeks)}
		<section
			class="min-w-[80%] shrink-0 snap-center rounded-xl border bg-surface-2 p-4 md:min-w-0
				{isRecommended(t) ? 'border-fg-primary' : 'border-border-subtle'}"
			aria-label="{t.label} {t.weeks}주 프로그램"
		>
			<div class="mb-3 flex items-center justify-between">
				<p class="text-sm font-semibold text-fg-primary">{t.label}</p>
				{#if isRecommended(t)}
					<span class="rounded-full bg-fg-primary px-2 py-0.5 text-[10px] font-medium text-surface-1">추천</span>
				{/if}
			</div>
			<dl class="mb-3 flex flex-col gap-2 text-xs">
				{#each rows as r (r.key)}
					<div class="flex items-baseline justify-between gap-2">
						<dt class="text-fg-muted">{r.label}</dt>
						<dd
							class="{r.differs ? 'font-semibold text-fg-primary' : 'font-normal text-fg-muted'}
								{r.key === 'risk' && r.differs ? riskClass(t.risk_level) : ''}"
						>
							{r.cells[i]}
						</dd>
					</div>
				{/each}
			</dl>
			{#if t.status_summary}
				<p class="mb-3 text-xs text-fg-muted">{t.status_summary}</p>
			{/if}
			<button
				type="button"
				onclick={() => onselect(t.weeks)}
				{disabled}
				class="w-full rounded-lg bg-fg-primary py-2 text-sm font-medium text-surface-1 disabled:opacity-40"
			>
				{loading === t.weeks ? '생성 중…' : '이 프로그램 선택'}
			</button>
		</section>
	{/each}
</div>

<style>
	@media (min-width: 768px) {
		[data-testid='scenario-compare'] {
			grid-template-columns: repeat(var(--cols), minmax(0, 1fr));
		}
	}
</style>
