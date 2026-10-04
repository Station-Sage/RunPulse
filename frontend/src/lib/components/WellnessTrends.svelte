<script lang="ts">
	// 30일 small multiples — 스파크라인 + 평소 범위(p25–p75) 밴드 값. 트렌드는 비동기로 도착한다.
	import Sparkline from '$lib/components/Sparkline.svelte';
	import Skeleton from '$lib/components/Skeleton.svelte';
	import type { WellnessTrendData } from '$lib/types';

	let { trend }: { trend: Promise<WellnessTrendData | null> } = $props();

	const SERIES = [
		['utrs', 'UTRS', 'var(--color-series-1)', false],
		['sleep_score', '수면 점수', 'var(--color-series-2)', false],
		['hrv_last_night', 'HRV (야간)', 'var(--color-semantic-green)', false],
		['resting_hr', '안정 심박', 'var(--color-semantic-amber)', true],
		['body_battery_high', 'Body Battery 최고', 'var(--color-semantic-teal)', false],
		['avg_stress', '평균 스트레스', 'var(--color-fg-secondary)', true]
	] as const;
</script>

<section class="px-4 pb-6" aria-label="30일 추세">
	<h2 class="mb-2 text-xs font-medium uppercase tracking-wide text-fg-muted">30일 추세</h2>
	{#await trend}
		<div class="grid grid-cols-2 gap-2">
			{#each SERIES as s (s[0])}<Skeleton kind="chart" class="!min-h-[84px]" />{/each}
		</div>
	{:then t}
		{#if t && t.dates.length > 1}
			<div class="grid grid-cols-2 gap-2">
				{#each SERIES as [key, label, color, invert] (key)}
					{@const data = t[key]}
					{#if data.some((v) => v != null)}
						<div class="rounded-xl bg-surface-2 p-3">
							<span class="text-xs text-fg-muted">{label}</span>
							<Sparkline {data} height={32} {color} {invert} dates={t.dates} interactive minSpan={1} />
							{#if t.band?.[key]}<p class="mt-1 text-xs text-fg-muted">평소 {t.band[key].p25}–{t.band[key].p75}</p>{/if}
						</div>
					{/if}
				{/each}
			</div>
		{:else}
			<p class="text-sm text-fg-muted">데이터 수집 중</p>
		{/if}
	{/await}
</section>
