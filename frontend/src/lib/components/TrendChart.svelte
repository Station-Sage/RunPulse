<script lang="ts">
	// 다계열 추세 차트 — 공통 y 범위, y축·x축 눈금, 포인터 스크럽.
	// interactive=false 시 정적으로 렌더링된다 (Today L2 인라인 차트 용).
	import type { ChartSeries } from '$lib/trendChart';
	import { sharedYRange } from '$lib/trendChart';

	let {
		series,
		dates,
		height = 120,
		interactive = true
	}: {
		series: ChartSeries[];
		dates: string[];
		height?: number;
		interactive?: boolean;
	} = $props();

	// SVG viewBox — preserveAspectRatio="none" 이므로 내부 좌표계
	const W = 600;
	const AXIS_LEFT = 40; // y축 레이블 공간
	const AXIS_BOTTOM = 16; // x축 레이블 공간

	const chartW = $derived(W - AXIS_LEFT);
	const chartH = $derived(height - AXIS_BOTTOM);
	const range = $derived(sharedYRange(series));
	const n = $derived(dates.length);

	function toX(i: number): number {
		return n <= 1 ? chartW / 2 : (i / (n - 1)) * chartW;
	}

	function toY(v: number): number {
		const { min, max } = range;
		const span = max - min;
		return span === 0 ? chartH / 2 : chartH - ((v - min) / span) * chartH;
	}

	// 각 계열의 null-끊김 polyline 세그먼트 생성
	function makeSegments(values: (number | null)[]): string[] {
		const segs: string[] = [];
		let current: string[] = [];
		for (let i = 0; i < values.length; i++) {
			const v = values[i];
			if (v == null) {
				if (current.length >= 2) segs.push(current.join(' '));
				current = [];
			} else {
				current.push(`${(AXIS_LEFT + toX(i)).toFixed(1)},${toY(v).toFixed(1)}`);
			}
		}
		if (current.length >= 2) segs.push(current.join(' '));
		return segs;
	}

	// 스크럽 상태
	let scrubIdx = $state<number | null>(null);

	function handlePointerMove(e: PointerEvent) {
		const svg = e.currentTarget as SVGSVGElement;
		const rect = svg.getBoundingClientRect();
		const xRel = ((e.clientX - rect.left) / rect.width) * W - AXIS_LEFT;
		if (n <= 1) {
			scrubIdx = 0;
			return;
		}
		const rawIdx = (xRel / chartW) * (n - 1);
		scrubIdx = Math.max(0, Math.min(n - 1, Math.round(rawIdx)));
	}

	const scrubX = $derived(scrubIdx != null ? AXIS_LEFT + toX(scrubIdx) : null);
</script>

{#if n === 0 || series.length === 0}
	<span class="text-xs text-fg-muted">데이터 없음</span>
{:else}
	<svg
		viewBox="0 0 {W} {height}"
		preserveAspectRatio="none"
		style="display:block; width:100%; height:{height}px; cursor:{interactive
			? 'crosshair'
			: 'default'};"
		aria-hidden="true"
		onpointermove={interactive ? handlePointerMove : undefined}
		onpointerleave={interactive ? () => { scrubIdx = null; } : undefined}
	>
		<!-- y축: 최댓값·최솟값 눈금 -->
		<text x={AXIS_LEFT - 4} y={10} text-anchor="end" font-size="9" fill="currentColor" opacity="0.5"
			>{range.max.toFixed(0)}</text
		>
		<text
			x={AXIS_LEFT - 4}
			y={chartH}
			text-anchor="end"
			font-size="9"
			fill="currentColor"
			opacity="0.5">{range.min.toFixed(0)}</text
		>

		<!-- x축: 시작·끝 날짜 -->
		{#if dates.length >= 2}
			<text
				x={AXIS_LEFT}
				y={height - 2}
				text-anchor="start"
				font-size="9"
				fill="currentColor"
				opacity="0.5">{dates[0]}</text
			>
			<text x={W} y={height - 2} text-anchor="end" font-size="9" fill="currentColor" opacity="0.5"
				>{dates[dates.length - 1]}</text
			>
		{/if}

		<!-- 계열별 선 -->
		{#each series as s}
			{#each makeSegments(s.values) as pts}
				<polyline
					points={pts}
					fill="none"
					stroke={s.color}
					stroke-width="2"
					stroke-linecap="round"
					stroke-linejoin="round"
				/>
			{/each}
		{/each}

		<!-- 스크럽 (interactive=true 시만) -->
		{#if interactive && scrubIdx != null && scrubX != null}
			{@const tipX = scrubX > W * 0.7 ? scrubX - 4 : scrubX + 4}
			{@const anchor = scrubX > W * 0.7 ? 'end' : 'start'}

			<!-- 수직 가이드선 -->
			<line
				x1={scrubX}
				y1={0}
				x2={scrubX}
				y2={chartH}
				stroke="currentColor"
				stroke-width="1"
				opacity="0.25"
				stroke-dasharray="3 2"
			/>

			<!-- 각 계열 포인트 마커 -->
			{#each series as s}
				{@const val = s.values[scrubIdx]}
				{#if val != null}
					<circle cx={scrubX} cy={toY(val)} r="3" fill={s.color} />
				{/if}
			{/each}

			<!-- 날짜 + 값 레이블 -->
			<text x={tipX} y={12} text-anchor={anchor} font-size="9" fill="currentColor" opacity="0.8">
				{dates[scrubIdx]}
			</text>
			{#each series as s, si}
				{@const val = s.values[scrubIdx]}
				{#if val != null}
					<text
						x={tipX}
						y={12 + (si + 1) * 11}
						text-anchor={anchor}
						font-size="9"
						fill={s.color}
						opacity="0.9">{s.label ? `${s.label}: ` : ''}{val.toFixed(1)}</text
					>
				{/if}
			{/each}
		{/if}
	</svg>
{/if}
