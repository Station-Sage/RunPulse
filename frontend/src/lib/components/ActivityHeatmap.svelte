<script lang="ts">
	// 최근 53주 러닝 캘린더 — 고정 크기 셀(가로 스크롤, 최신 쪽에서 시작), 탭/호버/방향키 팝오버. 순수 배치: $lib/archive.
	import { buildHeatmap } from '$lib/archive';
	import { heatCellLabel, moveHeatCell } from '$lib/libraryHome';
	import { goto } from '$app/navigation';
	import { base } from '$app/paths';

	let { data, endDate }: { data: { date: string; km: number }[]; endDate: string } = $props();

	const CELL = 11;
	const GAP = 2;
	const STEP = CELL + GAP;
	const TOP = 14;
	const COLORS = ['#1a2536', '#0f5f5a', '#12897f', '#14b8a6', '#5eead4'];

	const grid = $derived(buildHeatmap(data, endDate, 53));
	const width = $derived(grid.columns * STEP - GAP);
	const height = TOP + 7 * STEP - GAP;
	let sel = $state(-1);
	const cell = $derived(sel >= 0 ? grid.cells[sel] : null);
	let scroller: HTMLElement | undefined = $state();

	$effect(() => {
		if (scroller) scroller.scrollLeft = scroller.scrollWidth;
	});

	function open(c: { date: string }) {
		goto(`${base}/library/activities?from=${c.date}&to=${c.date}`);
	}

	function onKey(e: KeyboardEvent) {
		if (e.key === 'Escape') sel = -1;
		else if (e.key === 'Enter' && cell) open(cell);
		else if (e.key.startsWith('Arrow')) {
			e.preventDefault();
			sel = moveHeatCell(grid.cells, sel < 0 ? grid.cells.length - 1 : sel, e.key);
		}
	}
</script>

<div class="flex flex-col gap-1.5">
	<!-- svelte-ignore a11y_no_noninteractive_element_interactions, a11y_no_noninteractive_tabindex -->
	<div
		bind:this={scroller}
		class="relative overflow-x-auto pb-1"
		tabindex="0"
		role="application"
		aria-label="최근 1년 러닝 캘린더. 방향키로 날짜 이동, Enter로 그날 활동 보기"
		onkeydown={onKey}
	>
		<div class="relative" style="width:{width}px;height:{height}px">
			<svg {width} {height} role="img" aria-label="최근 1년 러닝 캘린더">
				{#each grid.months as m (m.col)}
					<text x={m.col * STEP} y="9" font-size="9" fill="currentColor" opacity="0.55">{m.label}</text>
				{/each}
				{#each grid.cells as c, i (c.date)}
					<!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_static_element_interactions -->
					<rect
						x={c.col * STEP}
						y={TOP + c.row * STEP}
						width={CELL}
						height={CELL}
						rx="2"
						fill={COLORS[c.level]}
						stroke={sel === i ? '#fff' : 'none'}
						onclick={() => (sel = sel === i ? -1 : i)}
						onmouseenter={() => (sel = i)}
					/>
				{/each}
			</svg>
			{#if cell}
				<div
					class="absolute z-10 -translate-x-1/2 whitespace-nowrap rounded-md border border-border-subtle bg-surface-3 px-2 py-1 text-xs text-fg-primary shadow"
					style="left:{Math.min(Math.max(cell.col * STEP + CELL / 2, 70), width - 70)}px;top:{Math.max(0, TOP + cell.row * STEP - 30)}px"
					role="status"
				>
					{heatCellLabel(cell.date, cell.km)}
					{#if cell.km > 0}
						<a href="{base}/library/activities?from={cell.date}&to={cell.date}" class="ml-1 text-fg-secondary">›</a>
					{/if}
				</div>
			{/if}
		</div>
	</div>
	<div class="flex items-center justify-end gap-1 text-[10px] text-fg-muted">
		<span>적음</span>
		{#each COLORS as col, i (i)}
			<span class="inline-block h-2 w-2 rounded-sm" style="background:{col}"></span>
		{/each}
		<span>많음</span>
	</div>
</div>
