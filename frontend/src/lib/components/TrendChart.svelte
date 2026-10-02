<script lang="ts">
	// 다계열 추세 차트 — 공통 y 범위, y 최대·최소·x 시작·끝 눈금, 포인터 스크럽 판독. 순수 계산: $lib/trendChart.
	import type { TrendSeries } from '$lib/trendChart';
	import { commonRange, movingAverage, nearestPoint, splitOnGaps, trendAriaLabel, xFraction } from '$lib/trendChart';
	import ChartScrub from '$lib/components/ChartScrub.svelte';

	let {
		series,
		height = 140,
		unit = '',
		interactive = true,
		formatValue = (v: number) => v.toFixed(1),
		bands = [],
		baseline = null,
		smooth = false,
		name = '',
		periodLabel = ''
	}: {
		series: TrendSeries[];
		height?: number;
		unit?: string;
		interactive?: boolean;
		formatValue?: (v: number) => string;
		bands?: { from: number | null; to: number | null; status: string; label: string }[];
		baseline?: { mean: number; p25: number; p75: number } | null;
		smooth?: boolean;
		name?: string;
		periodLabel?: string;
	} = $props();

	const STATUS_COLOR: Record<string, string> = {
		excellent: 'var(--color-status-great)',
		good: 'var(--color-status-good)',
		neutral: 'var(--color-status-neutral)',
		caution: 'var(--color-status-caution)',
		poor: 'var(--color-status-danger)'
	};

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
	function polylineOf(pts: { date: string; value: number }[]): string {
		return pts.map((p) => `${px(p.date).toFixed(1)},${py(p.value).toFixed(1)}`).join(' ');
	}
	// 단일 시리즈 + smooth(≥3개월): 일별은 옅게, 7일 이동평균을 굵게
	const useMA = $derived(smooth && series.length === 1);
	// 범위 밖 밴드는 그리지 않고, 하한/상한 없는 끝은 차트 경계까지 확장
	const bandRects = $derived(
		!range
			? []
			: bands
					.map((b) => {
						const lo = b.from ?? range.min;
						const hi = b.to ?? range.max;
						if (hi <= range.min || lo >= range.max) return null;
						const y1 = py(Math.min(hi, range.max));
						const y2 = py(Math.max(lo, range.min));
						return { y: y1, h: y2 - y1, color: STATUS_COLOR[b.status] ?? STATUS_COLOR.neutral, label: b.label };
					})
					.filter((b) => b !== null)
	);
	const ariaLabel = $derived(
		series.length === 1 && name ? trendAriaLabel(name, periodLabel, series[0].points, formatValue) : '추세 차트'
	);

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
					{#each bandRects as b, i (i)}
						<rect x="0" y={b.y} width={W} height={b.h} fill={b.color} fill-opacity="0.08" />
					{/each}
					{#if baseline}
						<rect x="0" y={py(baseline.p75)} width={W} height={py(baseline.p25) - py(baseline.p75)} fill="currentColor" fill-opacity="0.06" />
						<line x1="0" x2={W} y1={py(baseline.mean)} y2={py(baseline.mean)} stroke="currentColor" stroke-opacity="0.35" stroke-width="1" stroke-dasharray="3 3" vector-effect="non-scaling-stroke" />
					{/if}
					{#each series as s (s.key)}
						{#each splitOnGaps(s.points) as seg, i (i)}
							<polyline
								points={polylineOf(seg)}
								fill="none"
								stroke={s.color}
								stroke-width={useMA ? 1 : 2}
								stroke-opacity={useMA ? 0.35 : 1}
								stroke-linejoin="round"
								stroke-linecap="round"
								vector-effect="non-scaling-stroke"
							/>
						{/each}
						{#if useMA}
							<polyline
								points={polylineOf(movingAverage(s.points))}
								fill="none"
								stroke={s.color}
								stroke-width="2.5"
								stroke-linejoin="round"
								stroke-linecap="round"
								vector-effect="non-scaling-stroke"
							/>
						{/if}
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
			<ChartScrub {pointCount} ariaLabel="{ariaLabel} — 눌러서 날짜별 값 확인" onChange={onScrubChange}>
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
