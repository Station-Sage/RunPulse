<script lang="ts">
	// 수면 카드 — 점수·시간(30일 평균 대비)·단계 막대. 단계가 없으면 "단계 데이터 없음".
	import { base } from '$app/paths';
	import { fmtDur, stageSegments } from '$lib/wellnessDay';
	import type { WellnessDetailData } from '$lib/types';

	let { sleep, date }: { sleep: NonNullable<WellnessDetailData['sleep']>; date: string } = $props();
	const segs = $derived(stageSegments(sleep.stages));
	const STAGE_BG: Record<string, string> = {
		deep: 'var(--color-series-1)',
		light: 'var(--color-surface-3)',
		rem: 'var(--color-semantic-teal)',
		awake: 'var(--color-semantic-amber)'
	};
	const delta = $derived(
		sleep.duration_sec != null && sleep.mean30_sec != null ? sleep.duration_sec - sleep.mean30_sec : null
	);
</script>

<section class="rounded-xl bg-surface-2 p-3" aria-label="수면">
	<div class="flex items-baseline justify-between">
		<a href="{base}/library/metrics/sleep_score?date={date}" class="text-xs text-fg-muted">수면</a>
		<span class="font-mono text-2xl font-semibold leading-none">{sleep.score ?? '—'}<span class="ml-1 text-xs font-normal text-fg-muted">점</span></span>
	</div>
	<p class="mt-2 font-mono text-lg">{fmtDur(sleep.duration_sec)}</p>
	{#if delta != null}
		<p class="text-xs text-fg-muted">30일 평균 {fmtDur(sleep.mean30_sec)} 대비 {delta >= 0 ? '+' : '−'}{fmtDur(Math.abs(delta))}</p>
	{/if}
	{#if segs.length > 0}
		<div class="mt-3 flex h-3 overflow-hidden rounded-full" role="img" aria-label="수면 단계 비율">
			{#each segs as s (s.key)}<div style="width:{s.pct}%;background:{STAGE_BG[s.key]}"></div>{/each}
		</div>
		<ul class="mt-2 flex flex-wrap gap-x-3 gap-y-1 text-xs text-fg-secondary">
			{#each segs as s (s.key)}
				<li><span class="mr-1 inline-block h-2 w-2 rounded-full" style="background:{STAGE_BG[s.key]}"></span>{s.label} {fmtDur(s.sec)}</li>
			{/each}
		</ul>
	{:else}
		<p class="mt-3 text-xs text-fg-muted">단계 데이터 없음</p>
	{/if}
</section>
