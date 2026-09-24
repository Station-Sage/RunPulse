<script lang="ts">
	// 최근 53주 러닝 캘린더 히트맵 — 하루 거리 단계(0~4)로 색. 순수 배치: $lib/archive.
	import { buildHeatmap } from '$lib/archive';

	let { data, endDate }: { data: { date: string; km: number }[]; endDate: string } = $props();

	const CELL = 5.4;
	const GAP = 1.6;
	const STEP = CELL + GAP;
	const LEFT = 0;
	const TOP = 12;
	// 단계 색: 없음 → 많음 (teal 계열)
	const COLORS = ['#1a2536', '#0f5f5a', '#12897f', '#14b8a6', '#5eead4'];

	const grid = $derived(buildHeatmap(data, endDate, 53));
	const width = $derived(LEFT + grid.columns * STEP - GAP);
	const height = TOP + 7 * STEP - GAP;
</script>

<div class="flex flex-col gap-1.5">
	<svg
		viewBox="0 0 {width} {height}"
		class="w-full"
		style="aspect-ratio:{width}/{height}"
		role="img"
		aria-label="최근 1년 러닝 캘린더"
	>
		{#each grid.months as m (m.col)}
			<text x={LEFT + m.col * STEP} y="8" font-size="6" fill="currentColor" opacity="0.55">{m.label}</text>
		{/each}
		{#each grid.cells as c (c.date)}
			<rect
				x={LEFT + c.col * STEP}
				y={TOP + c.row * STEP}
				width={CELL}
				height={CELL}
				rx="1.2"
				fill={COLORS[c.level]}
			>
				<title>{c.date}{c.km > 0 ? ` · ${c.km}km` : ''}</title>
			</rect>
		{/each}
	</svg>
	<div class="flex items-center justify-end gap-1 text-[10px] text-fg-muted">
		<span>적음</span>
		{#each COLORS as col, i (i)}
			<span class="inline-block h-2 w-2 rounded-sm" style="background:{col}"></span>
		{/each}
		<span>많음</span>
	</div>
</div>
