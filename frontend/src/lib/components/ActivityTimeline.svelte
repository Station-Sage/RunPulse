<script lang="ts">
	// 활동 요약 타임라인 — 페이스(역축)·심박·고도 3트랙, 공유 거리축, ChartScrub 1개로 동시 스크럽.
	import type { ActivitySeries } from '$lib/types';
	import ChartScrub from '$lib/components/ChartScrub.svelte';
	import { formatPace } from '$lib/format';
	import { distanceTicks, flatNote, linePath, meanOf, trackDomain } from '$lib/chart/activityTimeline';

	let {
		series,
		elevGainM = null,
		onCursor
	}: {
		series: ActivitySeries;
		elevGainM?: number | null;
		onCursor?: (distM: number | null) => void;
	} = $props();

	const W = 600;
	const n = $derived(series.dist_m.length);
	const totalM = $derived(series.dist_m[n - 1] ?? 0);
	const ticks = $derived(distanceTicks(totalM));
	const paceDom = $derived(trackDomain(series.pace_sec_km));
	const hrDom = $derived(trackDomain(series.hr));
	const altDom = $derived(trackDomain(series.alt_m, 30));
	const paceMean = $derived(meanOf(series.pace_sec_km));
	const flat = $derived(flatNote(series.alt_m, elevGainM));

	const tracks = $derived([
		{ key: 'pace', label: '페이스', h: 64, dom: paceDom, vals: series.pace_sec_km, invert: true, color: 'var(--color-series-1)', fmt: (v: number) => formatPace(v) },
		{ key: 'hr', label: '심박', h: 48, dom: hrDom, vals: series.hr, invert: false, color: 'var(--color-series-2)', fmt: (v: number) => `${Math.round(v)} bpm` },
		{ key: 'alt', label: '고도', h: 40, dom: altDom, vals: series.alt_m, invert: false, color: 'var(--color-series-3)', fmt: (v: number) => `${Math.round(v)} m` }
	].filter((t) => t.dom !== null && t.vals.some((v) => v != null)));

	function xPct(i: number | null): number {
		return i == null || n < 2 ? 0 : (i / (n - 1)) * 100;
	}
	function yPx(t: (typeof tracks)[number], v: number): number {
		const d = t.dom!;
		const f = (v - d.min) / (d.max - d.min || 1);
		return (t.invert ? f : 1 - f) * t.h;
	}
</script>

{#if n >= 2 && tracks.length > 0}
	<section class="flex flex-col gap-1" aria-label="페이스·심박·고도 타임라인" data-testid="activity-timeline">
		<p class="text-xs uppercase tracking-wide text-fg-muted">구간별 흐름</p>
		<ChartScrub
			pointCount={n}
			ariaLabel="활동 타임라인"
			onChange={(i) => onCursor?.(i == null ? null : series.dist_m[i])}
		>
			{#snippet children(index, pinned)}
				<div class="flex flex-col gap-1">
					{#each tracks as t (t.key)}
						<div class="relative" style="height:{t.h}px">
							<span class="absolute left-0 top-0 z-10 text-[11px] text-fg-muted">{t.label}</span>
							{#if t.key === 'alt' && flat}
								<span class="absolute right-0 top-0 z-10 text-[11px] text-fg-muted">{flat}</span>
							{/if}
							<svg viewBox="0 0 {W} {t.h}" preserveAspectRatio="none" class="h-full w-full" aria-hidden="true">
								{#if t.key === 'pace' && paceMean != null}
									<line x1="0" x2={W} y1={yPx(t, paceMean)} y2={yPx(t, paceMean)} stroke="var(--color-series-2)" stroke-width="1" stroke-dasharray="2 3" vector-effect="non-scaling-stroke" />
								{/if}
								<path d={linePath(t.vals, t.dom!, W, t.h, t.invert)} fill="none" stroke={t.color} stroke-width="1.5" stroke-linejoin="round" vector-effect="non-scaling-stroke" />
							</svg>
							{#if index != null}
								<div class="pointer-events-none absolute bottom-0 top-0 w-px bg-fg-muted" style="left:{xPct(index)}%"></div>
								{#if t.vals[index] != null}
									<span class="num pointer-events-none absolute top-0 z-10 rounded bg-surface-3 px-1 text-[11px] text-fg-primary" style="left:{Math.min(Math.max(xPct(index), 12), 88)}%; transform:translateX(-50%)">{t.fmt(t.vals[index] as number)}</span>
								{/if}
							{/if}
						</div>
					{/each}
					<div class="relative h-4 text-[11px] text-fg-muted" aria-hidden="true">
						{#each ticks as m (m)}
							<span class="absolute -translate-x-1/2" style="left:{totalM > 0 ? (m / totalM) * 100 : 0}%">{m / 1000}</span>
						{/each}
						<span class="absolute right-0 top-0">km</span>
					</div>
					{#if index != null}
						<p class="text-[11px] text-fg-muted" aria-live="polite">{((series.dist_m[index] ?? 0) / 1000).toFixed(2)} km{pinned ? ' · 고정됨' : ''}</p>
					{/if}
				</div>
			{/snippet}
		</ChartScrub>
	</section>
{/if}
