<script lang="ts">
	// 메트릭 상세 "이 지표는" 블록 — 의미 한 줄 + 해석 구간 + 좋은 방향. 데스크톱은 우측 열, 모바일은 접힘.
	import { getMetricExplain } from '$lib/api/metrics';
	import type { MetricTrendData } from '$lib/types';

	let {
		slug,
		trend,
		date,
		explainSupported
	}: { slug: string; trend: MetricTrendData; date: string; explainSupported: boolean } = $props();

	let what = $state<string | null>(null);
	let open = $state(false);

	$effect(() => {
		const s = slug;
		const d = date;
		if (!explainSupported || !d) {
			what = null;
			return;
		}
		let cancelled = false;
		getMetricExplain(s, 'daily', d)
			.then((r) => {
				if (!cancelled) what = r.meaning?.what ?? null;
			})
			.catch(() => {
				if (!cancelled) what = null;
			});
		return () => {
			cancelled = true;
		};
	});

	const direction = $derived(
		trend.higher_is_better === true ? '높을수록 좋아요' : trend.higher_is_better === false ? '낮을수록 좋아요' : null
	);
	const bands = $derived(trend.bands ?? []);
	const hasContent = $derived(!!what || !!direction || bands.length > 0);
</script>

{#if hasContent}
	<section class="rounded-xl bg-surface-2" data-testid="metric-about">
		<button
			type="button"
			class="flex w-full items-center justify-between px-4 py-2 text-sm font-semibold lg:pointer-events-none"
			aria-expanded={open}
			onclick={() => (open = !open)}
		>
			이 지표는
			<span class="text-fg-muted lg:hidden" aria-hidden="true">{open ? '−' : '+'}</span>
		</button>
		<div class="{open ? 'flex' : 'hidden'} flex-col gap-2 px-4 pb-3 text-sm text-fg-secondary lg:flex">
			{#if what}<p>{what}</p>{/if}
			{#if direction}<p class="text-xs text-fg-muted">{direction}</p>{/if}
			{#if bands.length > 0}
				<ul class="flex flex-col gap-1 text-xs">
					{#each bands as b, i (i)}
						<li class="flex justify-between">
							<span>{b.label}</span>
							<span class="font-mono text-fg-muted">{b.from ?? ''}–{b.to ?? ''}</span>
						</li>
					{/each}
				</ul>
			{/if}
		</div>
	</section>
{/if}
