<script lang="ts">
	// 캘린더(히트맵) / 월별 거리 — 한 카드에서 탭 전환.
	import type { ArchiveData } from '$lib/types';
	import { monthHeights } from '$lib/archive';
	import { isMonthInProgress } from '$lib/libraryHome';
	import ActivityHeatmap from './ActivityHeatmap.svelte';
	import { base } from '$app/paths';

	let { archive }: { archive: ArchiveData } = $props();
	let tab: 'calendar' | 'monthly' = $state('calendar');

	const heights = $derived(monthHeights(archive.monthly));
</script>

<section class="flex flex-col gap-3 px-4" aria-label="러닝 기록 보기">
	<div class="flex gap-1" role="tablist">
		{#each [['calendar', '1년 캘린더'], ['monthly', '월별 거리']] as [k, label] (k)}
			<button
				type="button"
				role="tab"
				aria-selected={tab === k}
				class="rounded-full px-3 py-1 text-xs {tab === k ? 'bg-surface-3 text-fg-primary' : 'text-fg-muted'}"
				onclick={() => (tab = k as typeof tab)}>{label}</button
			>
		{/each}
	</div>

	{#if tab === 'calendar'}
		<ActivityHeatmap data={archive.heatmap} endDate={archive.as_of} />
	{:else}
		<div class="flex h-28 items-end gap-1.5" role="img" aria-label="월별 거리 막대">
			{#each archive.monthly as m, i (m.month)}
				{@const live = isMonthInProgress(m.month, archive.as_of)}
				<a
					href="{base}/library/activities?month={m.month}"
					class="flex h-full flex-1 flex-col items-center justify-end gap-0.5"
					title="{m.month} · {m.km}km · {m.runs}회{live ? ' (진행 중)' : ''}"
				>
					<span class="font-mono text-[9px] text-fg-muted">{Math.round(m.km)}</span>
					<div
						class="w-full rounded-t"
						style="height:{Math.max(2, heights[i] * 70)}%; background:{live
							? 'repeating-linear-gradient(135deg,#5eead4 0 3px,#12897f 3px 6px)'
							: '#12897f'}"
					></div>
					<span class="font-mono text-[9px] text-fg-muted">{Number(m.month.slice(5))}</span>
				</a>
			{/each}
		</div>
		<p class="text-[10px] text-fg-muted">막대를 누르면 그 달 활동으로 · 줄무늬는 진행 중인 달</p>
	{/if}
</section>
