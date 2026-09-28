<script lang="ts">
	// 다계열 추세 차트 — 공통 y 범위, y 최대·최소·x 시작·끝 눈금, 포인터 스크럽 판독. 순수 계산: $lib/trendChart.
	import type { TrendSeries } from '$lib/trendChart';
	import { commonRange, nearestPoint, xFraction } from '$lib/trendChart';
	import ChartScrub from '$lib/components/ChartScrub.svelte';

	let {
		series,
		height = 140,
		unit = '',
		interactive = true,
		formatValue = (v: number) => v.toFixed(1)
	}: {
		series: TrendSeries[];
		height?: number;
		unit?: string;
		interactive?: boolean;
		formatValue?: (v: number) => string;
	} = $props();

	const W = 600;
	const range = $derived(commonRange(series));
	const dates = $derived(series.flatMap((s) => s.points.map((p) => p.date)).sort());
	const t0 = $derived(dates[0] ?? '');
	const t1 = $derived(dates[dates.length - 1] ?? '');

	function px(date: string): number {
		return xFraction(date, t0, t1) * W;
	}
	function py(v: number): number {
		if (!range) return 0;
		return (1 - (v - range.min) / (range.max - range.min)) * height;
	}
	function polyline(s: TrendSeries): string {
		return s.points.map((p) => `${px(p.date).toFixed(1)},${py(p.value).toFixed(1)}`).join(' ');
	}

	// §C1 ChartScrub — t0~t1을 일 단위 "포인트"로 근사(키보드 ←/→가 하루씩 움직임). 값 조회는
	// 그대로 frac 기반(nearestPoint)이라 trendChart.ts의 날짜 수학은 손대지 않는다.
	const totalDays = $derived(
		t0 && t1 ? Math.max(1, Math.round((Date.parse(t1) - Date.parse(t0)) / 86_400_000)) : 1
	);
	const pointCount = $derived(totalDays + 1);
	let frac = $state<number | null>(null);
	function onScrubChange(index: number | null) {
		frac = index == null ? null : index / totalDays;
	}

	// 판독: 스크럽 중이면 커서 위치의 최근접 점, 아니면 각 시리즈의 마지막 점
	const readout = $derived(
		series.map((s) => ({
			s,
			p: frac == null ? (s.points[s.points.length - 1] ?? null) : nearestPoint(s.points, frac, t0, t1)
		}))
	);
	const readoutDate = $derived(readout.find((r) => r.p)?.p?.date ?? '');
	// 커서 x: 판독에 쓰인 첫 점의 실제 날짜 위치에 붙인다
	const cursorPct = $derived(
		frac == null || !readoutDate ? null : xFraction(readoutDate, t0, t1) * 100
	);
</script>

{#if !range}
	<span class="text-xs text-fg-muted">데이터 없음</span>
{:else}
	<div class="flex flex-col gap-1">
		<!-- 범례 + 판독 -->
		<div class="flex min-h-[1.25rem] flex-wrap items-center gap-x-3 text-xs">
			{#if interactive || series.length > 1}
				<span class="font-mono text-fg-muted">{readoutDate}</span>
			{/if}
			{#each readout as r (r.s.key)}
				<span class="flex items-center gap-1">
					<span style="color:{r.s.color}">●</span>
					<span class="text-fg-muted">{r.s.label}</span>
					<span class="font-mono text-fg-secondary"
						>{r.p ? formatValue(r.p.value) : '—'}{r.p && unit ? ` ${unit}` : ''}</span
					>
				</span>
			{/each}
		</div>

		<!-- 차트 -->
		{#snippet chartBody(cursorFrac: number | null)}
			<div class="relative" style="height:{height}px; {interactive ? 'touch-action: pan-y;' : ''}">
				<svg
					viewBox="0 0 {W} {height}"
					preserveAspectRatio="none"
					style="width:100%;height:{height}px;display:block"
					aria-hidden="true"
				>
					{#each [0, height / 2, height] as y (y)}
						<line
							x1="0"
							x2={W}
							y1={y}
							y2={y}
							stroke="currentColor"
							stroke-opacity="0.12"
							stroke-width="1"
							vector-effect="non-scaling-stroke"
						/>
					{/each}
					{#each series as s (s.key)}
						<polyline
							points={polyline(s)}
							fill="none"
							stroke={s.color}
							stroke-width="2"
							stroke-linejoin="round"
							stroke-linecap="round"
							vector-effect="non-scaling-stroke"
						/>
					{/each}
				</svg>

				<span class="pointer-events-none absolute left-0 top-0 font-mono text-[10px] text-fg-muted"
					>{formatValue(range.max)}</span
				>
				<span class="pointer-events-none absolute bottom-0 left-0 font-mono text-[10px] text-fg-muted"
					>{formatValue(range.min)}</span
				>

				{#if cursorFrac != null}
					<div
						class="pointer-events-none absolute inset-y-0 w-px bg-fg-muted"
						style="left:{cursorFrac * 100}%"
					></div>
				{/if}
			</div>
		{/snippet}

		{#if interactive}
			<ChartScrub {pointCount} ariaLabel="추세 차트 — 눌러서 날짜별 값 확인" onChange={onScrubChange}>
				{#snippet children()}
					{@render chartBody(cursorPct == null ? null : cursorPct / 100)}
				{/snippet}
			</ChartScrub>
		{:else}
			{@render chartBody(null)}
		{/if}

		<!-- x축 -->
		<div class="flex justify-between font-mono text-[10px] text-fg-muted">
			<span>{t0}</span>
			<span>{t1}</span>
		</div>
	</div>
{/if}
