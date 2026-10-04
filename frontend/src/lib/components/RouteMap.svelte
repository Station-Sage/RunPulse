<script lang="ts">
	// GPS 경로(타일 없음, 로컬 퍼스트) — 서버 series lat/lon 사용. 페이스(5~95퍼센타일)/심박 색, km 마커,
	// 스플릿 선택·타임라인 커서와 양방향 연동. 색은 토큰 color-mix.
	import type { ActivitySeries } from '$lib/types';
	import {
		kmMarkers,
		inSegment,
		mixColor,
		nearestDistIndex,
		rangesOf,
		routeFromSeries,
		valueFraction
	} from '$lib/chart/routeSeries';

	let {
		series,
		selectedSeg = null,
		cursorDist = null,
		onSelect,
		initialMode = 'pace',
		onModeChange
	}: {
		series: ActivitySeries | null | undefined;
		selectedSeg?: number | null;
		cursorDist?: number | null;
		onSelect?: (seg: number | null) => void;
		initialMode?: 'pace' | 'hr';
		onModeChange?: (mode: 'pace' | 'hr') => void;
	} = $props();

	// svelte-ignore state_referenced_locally
	let mode = $state<'pace' | 'hr'>(initialMode);

	const sr = $derived(routeFromSeries(series));
	const ranges = $derived(sr ? rangesOf(sr) : null);
	const canToggle = $derived(ranges?.hr != null);
	const activeMode = $derived(canToggle ? mode : 'pace');
	const range = $derived(ranges ? ranges[activeMode] : null);
	const markers = $derived(sr ? kmMarkers(sr) : []);

	const segments = $derived.by(() => {
		if (!sr) return [];
		const pts = sr.route.points;
		return pts.slice(1).map((p, i) => {
			const q = pts[i];
			const a = activeMode === 'pace' ? q.pace : q.hr;
			const b = activeMode === 'pace' ? p.pace : p.hr;
			const v = a != null && b != null ? (a + b) / 2 : (a ?? b);
			return {
				x1: q.x, y1: q.y, x2: p.x, y2: p.y,
				color: mixColor(valueFraction(v, range), activeMode),
				on: inSegment(sr.dists[i + 1], selectedSeg)
			};
		});
	});

	const cursor = $derived(
		sr && cursorDist != null ? sr.route.points[nearestDistIndex(sr.dists, cursorDist)] : null
	);
</script>

{#if !sr}
	<section class="flex flex-col gap-2" aria-label="경로" data-testid="route-map">
		<p class="text-xs uppercase tracking-wide text-fg-muted">경로</p>
		<p class="rounded-lg border border-border-subtle bg-surface-2 p-4 text-sm text-fg-muted" data-testid="route-indoor">
			실내 · 경로 없음
		</p>
	</section>
{:else}
	<section class="flex flex-col gap-2" aria-label="경로" data-testid="route-map">
		<div class="flex items-center justify-between">
			<p class="text-xs uppercase tracking-wide text-fg-muted">경로</p>
			{#if canToggle}
				<div class="flex gap-3">
					{#each [['pace', '페이스'], ['hr', '심박']] as [key, label] (key)}
						<button
							type="button"
							aria-pressed={mode === key}
							onclick={() => {
							mode = key as 'pace' | 'hr';
							onModeChange?.(mode);
						}}
							class="min-h-7 text-xs {mode === key ? 'text-fg-primary underline' : 'text-fg-muted'}"
							>{label}</button
						>
					{/each}
				</div>
			{/if}
		</div>
		<div class="flex justify-center rounded-lg border border-border-subtle bg-surface-2 p-3">
			<svg
				viewBox="0 0 {sr.route.width} {sr.route.height}"
				class="w-full"
				style="max-height:280px;aspect-ratio:{sr.route.width}/{sr.route.height}"
				role="img"
				aria-label="활동 경로 지도(타일 없음)"
			>
				{#each segments as s, i (i)}
					<line
						x1={s.x1} y1={s.y1} x2={s.x2} y2={s.y2}
						stroke={s.color}
						stroke-width={s.on ? 5 : 3}
						stroke-linecap="round"
						opacity={selectedSeg != null && !s.on ? 0.3 : 1}
					/>
				{/each}
				{#each markers as m (m.km)}
					<g
						role="button"
						tabindex="-1"
						aria-label="{m.km}km 구간 선택"
						class="cursor-pointer"
						onclick={() => onSelect?.(selectedSeg === m.km ? null : m.km)}
						onkeydown={() => {}}
					>
						<circle cx={m.x} cy={m.y} r="7" fill="var(--color-surface-1)" stroke="var(--color-fg-muted)" stroke-width="1" />
						<text x={m.x} y={m.y + 3.5} text-anchor="middle" font-size="9" fill="var(--color-fg-primary)">{m.km}</text>
					</g>
				{/each}
				{#if cursor}
					<circle cx={cursor.x} cy={cursor.y} r="5" fill="var(--color-fg-primary)" stroke="var(--color-surface-1)" stroke-width="2" data-testid="route-cursor" />
				{/if}
			</svg>
		</div>
		<div class="flex items-center gap-2 text-xs text-fg-muted">
			{#if activeMode === 'pace'}
				<span>빠름</span>
				<span class="h-1.5 flex-1 rounded" style="background: linear-gradient(to right, var(--color-delta-better), var(--color-delta-worse))"></span>
				<span>느림</span>
			{:else}
				<span>낮음</span>
				<span class="h-1.5 flex-1 rounded" style="background: linear-gradient(to right, var(--color-series-3), var(--color-series-1))"></span>
				<span>높음</span>
			{/if}
		</div>
		<p class="text-xs text-fg-muted">타일 없이 GPS 좌표만으로 그린 경로 · 북쪽이 위 · 색은 5~95퍼센타일 기준</p>
	</section>
{/if}
