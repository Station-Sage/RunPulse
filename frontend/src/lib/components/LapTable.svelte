<script lang="ts">
	// 랩 표 — 고정 열 + 발산 막대(160px), 인터벌이면 워크/회복 그룹 뷰가 기본(20 §2-6).
	import type { ActivityLap } from '$lib/types';
	import { formatDistance, formatDuration, formatPace } from '$lib/format';
	import { classifyIntervals, divergence, lapPace } from '$lib/lapGroups';

	let { laps }: { laps: ActivityLap[] } = $props();

	const paces = $derived(laps.map(lapPace));
	const interval = $derived(classifyIntervals(laps));
	let grouped = $state(true);
	const showGroups = $derived(interval != null && grouped);
	const validPaces = $derived(paces.filter((p): p is number => p != null));
	const basePace = $derived(
		interval ? interval.workAvg : validPaces.length ? validPaces.reduce((a, b) => a + b, 0) / validPaces.length : null
	);
	const hideTime = $derived(laps.every((l) => l.lap_trigger === 'distance'));

	// 그룹 뷰: 같은 역할이 이어지는 구간을 하나의 묶음으로.
	const blocks = $derived.by(() => {
		if (!interval) return [];
		const out: { role: 'work' | 'recovery' | null; idx: number[] }[] = [];
		interval.roles.forEach((r, i) => {
			const last = out[out.length - 1];
			if (last && last.role === r) last.idx.push(i);
			else out.push({ role: r, idx: [i] });
		});
		return out;
	});
</script>

{#snippet row(i: number)}
	{@const lap = laps[i]}
	{@const d = divergence(paces[i], basePace)}
	<tr class="border-b border-border-subtle text-sm" data-testid="lap-row">
		<td class="w-8 py-2 pr-2 font-mono text-xs text-fg-muted">{i + 1}</td>
		<td class="py-2 pr-3 text-right font-mono">{lap.distance_m != null ? formatDistance(lap.distance_m, 2) : '—'}</td>
		{#if !hideTime}<td class="py-2 pr-3 text-right font-mono text-fg-secondary">{lap.duration_sec != null ? formatDuration(lap.duration_sec) : '—'}</td>{/if}
		<td class="py-2 pr-3 text-right font-mono font-medium">{paces[i] != null ? formatPace(paces[i] as number) : '—'}</td>
		<td class="hidden w-40 py-2 pr-3 sm:table-cell">
			<div class="relative h-1.5 w-40 rounded bg-surface-3" aria-hidden="true">
				<div class="absolute inset-y-0 left-1/2 w-px bg-border-subtle"></div>
				<div
					class="absolute inset-y-0 rounded bg-fg-secondary"
					style="width:{Math.abs(d) * 50}%; {d >= 0 ? 'left:50%' : `right:50%`}"
				></div>
			</div>
		</td>
		<td class="py-2 pr-3 text-right font-mono text-xs text-fg-muted">{lap.avg_hr != null ? `${lap.avg_hr}${lap.max_hr != null ? `/${lap.max_hr}` : ''}` : '—'}</td>
		<td class="hidden py-2 pr-3 text-right font-mono text-xs text-fg-muted md:table-cell">{lap.avg_cadence != null ? Math.round(lap.avg_cadence) : '—'}</td>
		<td class="hidden py-2 pr-3 text-right font-mono text-xs text-fg-muted md:table-cell">{lap.avg_power != null ? Math.round(lap.avg_power) : '—'}</td>
		<td class="py-2 text-right font-mono text-xs text-fg-muted">{lap.elevation_gain != null && lap.elevation_gain > 0 ? `↑${Math.round(lap.elevation_gain)}` : '—'}</td>
	</tr>
{/snippet}

<div class="flex flex-col gap-2">
	{#if interval}
		<div class="flex flex-wrap items-center gap-2 text-xs text-fg-secondary" data-testid="lap-interval-head">
			<span>워크 평균 {formatPace(interval.workAvg)} · 회복 평균 {formatPace(interval.recoveryAvg)}</span>
			<button
				type="button"
				class="ml-auto rounded border border-border-subtle px-2 py-0.5 text-fg-muted"
				aria-pressed={grouped}
				onclick={() => (grouped = !grouped)}
			>{grouped ? '전체 랩 보기' : '워크/회복 그룹'}</button>
		</div>
	{/if}
	<div class="overflow-x-auto">
		<table class="w-full border-collapse">
			<thead>
				<tr class="border-b border-border-subtle text-left text-[11px] text-fg-muted">
					<th class="py-1.5 pr-2 font-normal">#</th>
					<th class="py-1.5 pr-3 text-right font-normal">거리</th>
					{#if !hideTime}<th class="py-1.5 pr-3 text-right font-normal">시간</th>{/if}
					<th class="py-1.5 pr-3 text-right font-normal">페이스</th>
					<th class="hidden py-1.5 pr-3 font-normal sm:table-cell">평균 대비</th>
					<th class="py-1.5 pr-3 text-right font-normal">HR</th>
					<th class="hidden py-1.5 pr-3 text-right font-normal md:table-cell">spm</th>
					<th class="hidden py-1.5 pr-3 text-right font-normal md:table-cell">W</th>
					<th class="py-1.5 text-right font-normal">상승</th>
				</tr>
			</thead>
			{#if showGroups}
				{#each blocks as b, bi (bi)}
					<tbody data-testid="lap-group" data-role={b.role}>
						<tr>
							<th colspan="9" class="pt-3 pb-1 text-left text-[11px] font-normal text-fg-muted">
								{b.role === 'work' ? '워크' : b.role === 'recovery' ? '회복' : '기타'} · {b.idx.length}개
							</th>
						</tr>
						{#each b.idx as i (i)}{@render row(i)}{/each}
					</tbody>
				{/each}
			{:else}
				<tbody>{#each laps as _, i (i)}{@render row(i)}{/each}</tbody>
			{/if}
		</table>
	</div>
</div>
