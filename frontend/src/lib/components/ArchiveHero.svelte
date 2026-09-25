<script lang="ts">
	// Library 홈 최상단 — "내 러닝 아카이브": 누적 거리 히어로 + 월별 거리 + 1년 캘린더 + PB.
	// DECISIONS.md [P7-IMPL-ARCHIVE]: 데이터 소유감(비전 원칙 1)을 화면의 첫 장면으로.
	import type { ArchiveData } from '$lib/types';
	import { monthHeights, monthRange } from '$lib/archive';
	import ActivityHeatmap from './ActivityHeatmap.svelte';
	import PersonalBests from './PersonalBests.svelte';
	import { base } from '$app/paths';

	let { archive }: { archive: ArchiveData | null } = $props();

	const heights = $derived(monthHeights(archive?.monthly ?? []));
	const t = $derived(archive?.totals ?? null);
	const sinceLabel = $derived(t ? t.since.slice(0, 7).replace('-', '.') : '');
</script>

{#if t && archive}
	<section class="flex flex-col gap-4 px-4 pt-4" aria-label="러닝 아카이브">
		<div
			class="flex flex-col gap-3 rounded-xl border border-border-subtle p-4"
			style="background-color: var(--color-surface-2); background-image: radial-gradient(120% 90% at 0% 0%, rgba(20,184,166,0.16), transparent 62%)"
		>
			<p class="text-xs text-fg-muted">{sinceLabel}부터 내가 달린 거리</p>
			<div class="flex items-end gap-2">
				<span class="font-mono text-5xl font-bold leading-none tabular-nums"
					>{Math.round(t.distance_km).toLocaleString('ko-KR')}</span
				>
				<span class="pb-1 text-lg text-fg-muted">km</span>
			</div>
			<p class="text-sm text-fg-secondary">
				<span class="font-mono font-semibold">{t.runs.toLocaleString('ko-KR')}</span>회 ·
				<span class="font-mono font-semibold">{Math.round(t.hours).toLocaleString('ko-KR')}</span>시간 ·
				최근 1년 <span class="font-mono font-semibold">{t.active_days_365}</span>일 러닝
			</p>
			{#if archive.longest}
				<a
					href="{base}/library/{archive.longest.id}"
					class="text-xs text-fg-muted hover:text-fg-secondary"
					>가장 멀리 달린 날 · {archive.longest.name} {archive.longest.distance_km}km ({archive.longest.date}) →</a
				>
			{/if}
		</div>

		<div class="flex flex-col gap-2">
			<p class="text-xs uppercase tracking-wide text-fg-muted">최근 12개월 월별 거리</p>
			<div class="flex h-20 items-end gap-1.5" role="img" aria-label="월별 거리 막대">
				{#each archive.monthly as m, i (m.month)}
					<a href="{base}/library/activities?from={monthRange(m.month).from}&to={monthRange(m.month).to}" class="flex h-full flex-1 flex-col items-center justify-end gap-1" title="{m.month} · {m.km}km · {m.runs}회">
						<div
							class="w-full rounded-t"
							style="height:{Math.max(2, heights[i] * 100)}%; background:{i === archive.monthly.length - 1 ? '#5eead4' : '#12897f'}"
						></div>
					</a>
				{/each}
			</div>
			<div class="flex justify-between font-mono text-[10px] text-fg-muted">
				<span>{archive.monthly[0].month}</span>
				<span>{archive.monthly[archive.monthly.length - 1].month} · {archive.monthly[archive.monthly.length - 1].km}km</span>
			</div>
		</div>

		<div class="flex flex-col gap-2">
			<p class="text-xs uppercase tracking-wide text-fg-muted">최근 1년 러닝 캘린더</p>
			<ActivityHeatmap data={archive.heatmap} endDate={archive.as_of} />
		</div>

		<PersonalBests pbs={archive.personal_bests} />
	</section>
{/if}
