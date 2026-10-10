<script lang="ts">
	// 다계열 추세 차트 — 공통 y 범위, y 최대·최소·x 시작·끝 눈금, 포인터 스크럽 판독. 순수 계산: $lib/trendChart.
	import type { TrendSeries } from '$lib/trendChart';
	import { commonRange, dateAtOffset, eventSymbol, markerEvents, movingAverage, nearestPoint, splitOnGaps, monthTicks, trendAriaLabel, weekTicks, xFraction } from '$lib/trendChart';
	import { axisDateLabel } from '$lib/chart/scrub';
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
		periodLabel = '',
		selectedDate = null,
		events = [],
		onSelect,
		onPrefetch
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
		/** 고정(pin)된 선택일 — 차트 커서와 분해 패널 기준일을 공유한다. */
		selectedDate?: string | null;
		/** 차트 위 이벤트 마커(▲ 대회, ◇ 예측 기준 대회 변경, ◆ 계산 버전·출처 변경). 날짜가 x 범위 밖이면 그리지 않는다. */
		events?: { date: string; kind: string; label: string; reason?: string; recomputed?: boolean }[];
		onSelect?: (date: string | null) => void;
		/** 호버/탭 중인 날짜 — 분해 선요청용. */
		onPrefetch?: (date: string) => void;
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
	const lastPt = $derived.by(() => {
		if (series.length !== 1 || !range) return null;
		const p = series[0].points[series[0].points.length - 1];
		return p ? { x: xFraction(p.date, t0, t1) * 100, y: py(p.value), color: series[0].color } : null;
	});
	const ariaLabel = $derived(
		series.length === 1 && name ? trendAriaLabel(name, periodLabel, series[0].points, formatValue) : '추세 차트'
	);

	// §C1 ChartScrub — t0~t1을 일 단위 "포인트"로 근사(키보드 ←/→가 하루씩 움직임). 값 조회는
	// 그대로 frac 기반(nearestPoint)이라 trendChart.ts의 날짜 수학은 손대지 않는다.
	const totalDays = $derived(
		t0 && t1 ? Math.max(1, Math.round((Date.parse(t1) - Date.parse(t0)) / 86_400_000)) : 1
	);
	const pointCount = $derived(totalDays + 1);
	const ticks = $derived(totalDays <= 35 ? weekTicks(t0, t1) : monthTicks(t0, t1, totalDays > 180));
	const tickLabel = (d: string) => (totalDays <= 35 ? d.slice(5) : axisDateLabel(d, totalDays, true));
	let frac = $state<number | null>(null);
	let wasPinned = false;
	function onScrubChange(index: number | null, pinned = false) {
		frac = index == null ? null : index / totalDays;
		if (index != null) onPrefetch?.(dateAtOffset(t0, index));
		if (pinned && index != null) onSelect?.(dateAtOffset(t0, index));
		else if (index == null && wasPinned) onSelect?.(null);
		wasPinned = pinned;
	}
	const effFrac = $derived(
		frac ?? (selectedDate && t0 && selectedDate >= t0 && selectedDate <= t1 ? xFraction(selectedDate, t0, t1) : null)
	);

	// 판독: 스크럽 중이면 커서 위치의 최근접 점, 아니면 각 시리즈의 마지막 점
	const readout = $derived(
		series.map((s) => ({
			s,
			p: effFrac == null ? (s.points[s.points.length - 1] ?? null) : nearestPoint(s.points, effFrac, t0, t1)
		}))
	);
	const readoutDate = $derived(readout.find((r) => r.p)?.p?.date ?? '');
	// 커서 x: 판독에 쓰인 첫 점의 실제 날짜 위치에 붙인다
	const cursorPct = $derived(
		effFrac == null || !readoutDate ? null : xFraction(readoutDate, t0, t1) * 100
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
			{#each events.filter((e) => e.kind !== 'race' && e.date === readoutDate) as e (e.date + e.label)}
				<span class={e.kind === 'version_change' ? 'text-semantic-amber' : 'text-fg-secondary'} data-testid="trend-event-readout">{eventSymbol(e.kind)} {e.label}</span>
				{#if e.reason}
					<span class="basis-full text-fg-muted" data-testid="trend-event-reason">{e.reason}{e.recomputed ? ' · 과거 값도 다시 계산했어요' : ''}</span>
				{/if}
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

				{#if lastPt}
					<span
						class="pointer-events-none absolute size-1.5 -translate-x-1/2 -translate-y-1/2 rounded-full"
						style="left:{lastPt.x}%; top:{lastPt.y}px; background:{lastPt.color}"
					></span>
				{/if}

				{#each markerEvents(events, t0, t1) as e (e.date + e.label)}
					<span
						class="pointer-events-none absolute bottom-0 -translate-x-1/2 text-[10px] leading-none {e.kind === 'basis_change'
							? 'text-fg-secondary'
							: 'text-semantic-amber'}"
						style="left:{xFraction(e.date, t0, t1) * 100}%"
						title="{e.date} {e.label}"
						data-testid="trend-event">{eventSymbol(e.kind)}</span
					>
				{/each}

				{#if cursorFrac != null}
					<div
						class="pointer-events-none absolute inset-y-0 w-px bg-fg-muted"
						style="left:{cursorFrac * 100}%"
					></div>
				{/if}
			</div>
		{/snippet}

		<div class="flex gap-1">
			<div class="relative w-8 shrink-0 font-mono text-[10px] text-fg-muted sm:w-11" style="height:{height}px" aria-hidden="true">
				<span class="absolute right-0 top-0">{formatValue(range.max)}</span>
				<span class="absolute right-0 top-1/2 -translate-y-1/2">{formatValue((range.max + range.min) / 2)}</span>
				<span class="absolute bottom-0 right-0">{formatValue(range.min)}</span>
			</div>
			<div class="min-w-0 flex-1">
		{#if interactive}
			<ChartScrub {pointCount} ariaLabel="{ariaLabel} — 눌러서 날짜별 값 확인" onChange={onScrubChange}>
				{#snippet children()}
					{@render chartBody(cursorPct == null ? null : cursorPct / 100)}
				{/snippet}
			</ChartScrub>
		{:else}
			{@render chartBody(null)}
		{/if}

			</div>
		</div>

		<!-- x축 -->
		<div class="ml-9 flex justify-between font-mono text-[10px] text-fg-muted sm:ml-12">
			<span>{t0}</span>
			<span>{t1}</span>
		</div>
		{#if ticks.length}
			<div class="relative ml-9 h-3 font-mono text-[9px] text-fg-muted sm:ml-12" aria-hidden="true">
				{#each ticks as d (d)}
					<span class="absolute -translate-x-1/2" style="left:{xFraction(d, t0, t1) * 100}%">{tickLabel(d)}</span>
				{/each}
			</div>
		{/if}
	</div>
{/if}
