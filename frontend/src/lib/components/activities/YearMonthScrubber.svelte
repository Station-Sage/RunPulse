<script lang="ts">
	// 우측 연-월 스크러버 — 세로 띠를 누르거나 끌면 해당 월로 점프. 연도 경계에 연도 라벨.
	let {
		months,
		current,
		onjump
	}: {
		months: { month: string; n: number }[];
		current: string;
		onjump: (month: string) => void;
	} = $props();

	let strip: HTMLElement | undefined = $state();
	let dragging = $state(false);
	let hint = $state('');

	function monthAt(clientY: number): string | null {
		if (!strip || !months.length) return null;
		const r = strip.getBoundingClientRect();
		const f = Math.min(0.999, Math.max(0, (clientY - r.top) / Math.max(1, r.height)));
		return months[Math.floor(f * months.length)].month;
	}
	function move(e: PointerEvent) {
		const m = monthAt(e.clientY);
		if (m) hint = m;
	}
	function down(e: PointerEvent) {
		dragging = true;
		(e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
		move(e);
	}
	function up(e: PointerEvent) {
		if (!dragging) return;
		dragging = false;
		const m = monthAt(e.clientY);
		hint = '';
		if (m) onjump(m);
	}
	const marks = $derived(
		[...new Set(months.map((m) => m.month.slice(0, 4)))].map((y) => ({
			y,
			top: (months.findIndex((m) => m.month.startsWith(y)) / months.length) * 100
		}))
	);
</script>

{#if months.length > 1}
	<div
		bind:this={strip}
		class="fixed bottom-20 right-0 top-40 z-20 w-5 touch-none select-none"
		role="slider"
		aria-label="연월 이동"
		aria-valuetext={current}
		aria-valuenow={months.findIndex((m) => m.month === current)}
		tabindex="0"
		data-testid="scrubber"
		onpointerdown={down}
		onpointermove={dragging ? move : undefined}
		onpointerup={up}
		onpointercancel={() => ((dragging = false), (hint = ''))}
	>
		{#each marks as k (k.y)}
			<span class="absolute inset-x-0 text-center text-[9px] leading-none {current.startsWith(k.y) ? 'text-semantic-teal' : 'text-fg-muted'}" style="top:{k.top}%">{k.y.slice(2)}</span>
		{/each}
	</div>
	{#if hint}
		<div class="fixed right-8 top-1/2 z-30 rounded-lg bg-surface-3 px-3 py-1.5 text-sm font-mono shadow">{hint}</div>
	{/if}
{/if}
