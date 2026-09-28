<script lang="ts">
	// 피트니스·폼 시그니처 차트 — 위: CTL(체력)·ATL(피로) 공통 스케일, 아래: TSB(폼) 면적 + 레이스 최적 밴드,
	// 오늘 이후는 레이스 아침까지의 TSB 예측(테이퍼/유지 점선). 스크럽으로 날짜별 값 확인.
	// 순수 계산: $lib/formChart. DECISIONS.md [P7-IMPL-FORM-CHART]
	import type { RaceProjection } from '$lib/types';
	import ChartScrub from '$lib/components/ChartScrub.svelte';
	import {
		OPTIMAL_BAND,
		buildFormLayout,
		nearestByFrac,
		toPolyline,
		xFrac,
		yFrac,
		type Pt
	} from '$lib/formChart';

	let {
		ctl,
		atl,
		tsb,
		projection = null,
		raceDate = null
	}: { ctl: Pt[]; atl: Pt[]; tsb: Pt[]; projection?: RaceProjection | null; raceDate?: string | null } = $props();

	const W = 600;
	const TOP_H = 110;
	const BOT_H = 84;
	const uid = Math.random().toString(36).slice(2, 8);

	const SCEN_COLOR: Record<string, string> = { taper: '#22c55e', keep: '#94a3b8' };

	const future = $derived(
		(projection?.scenarios ?? []).map((s) => ({ key: s.key, label: s.label, points: s.series }))
	);
	const layout = $derived(buildFormLayout({ ctl, atl, tsb, future, raceDate }));

	// 미래 점선은 오늘의 실제 TSB에서 이어 그린다
	const lastTsb = $derived(tsb.length ? tsb[tsb.length - 1] : null);
	function futureLine(points: Pt[]): string {
		if (!layout || !lastTsb) return '';
		return toPolyline([lastTsb, ...points], layout, layout.bottom, W, BOT_H);
	}

	const zeroY = $derived(layout ? yFrac(0, layout.bottom) * BOT_H : 0);
	const bandY1 = $derived(layout ? yFrac(OPTIMAL_BAND.hi, layout.bottom) * BOT_H : 0);
	const bandY2 = $derived(layout ? yFrac(OPTIMAL_BAND.lo, layout.bottom) * BOT_H : 0);
	const tsbArea = $derived(
		layout && tsb.length
			? `${toPolyline(tsb, layout, layout.bottom, W, BOT_H)} ${(xFrac(tsb[tsb.length - 1].date, layout.t0, layout.t1) * W).toFixed(1)},${zeroY.toFixed(1)} 0,${zeroY.toFixed(1)}`
			: ''
	);
	const todayPct = $derived(layout ? xFrac(layout.today, layout.t0, layout.t1) * 100 : 0);
	const racePct = $derived(layout && raceDate ? xFrac(raceDate, layout.t0, layout.t1) * 100 : null);

	// §C1 ChartScrub — t0~t1을 일 단위 "포인트"로 취급해 키보드 ←/→가 하루씩 움직이게 한다.
	// pointCount는 날짜 수 기반 근사치이고, 실제 값 조회는 그대로 frac 기반(nearestByFrac)이라
	// formChart.ts의 날짜 수학은 손대지 않는다.
	const totalDays = $derived(
		layout ? Math.max(1, Math.round((Date.parse(layout.t1) - Date.parse(layout.t0)) / 86_400_000)) : 1
	);
	const pointCount = $derived(totalDays + 1);
	let frac = $state<number | null>(null);
	function onScrubChange(index: number | null) {
		frac = index == null ? null : index / totalDays;
	}
	const inFuture = $derived(layout != null && frac != null && frac * 100 > todayPct + 0.5);
	const readout = $derived.by(() => {
		if (!layout) return null;
		if (frac == null) {
			return {
				date: layout.today,
				items: [
					{ label: '체력 CTL', color: '#3b82f6', v: ctl.at(-1)?.value },
					{ label: '피로 ATL', color: '#f59e0b', v: atl.at(-1)?.value },
					{ label: '폼 TSB', color: '#14b8a6', v: tsb.at(-1)?.value }
				]
			};
		}
		if (inFuture) {
			const items = future.map((f) => {
				const p = nearestByFrac(f.points, frac!, layout);
				return { label: `예상 폼 · ${f.label}`, color: SCEN_COLOR[f.key], v: p?.value, date: p?.date };
			});
			return { date: items.find((i) => i.date)?.date ?? '', items };
		}
		const c = nearestByFrac(ctl, frac, layout);
		return {
			date: c?.date ?? '',
			items: [
				{ label: '체력 CTL', color: '#3b82f6', v: c?.value },
				{ label: '피로 ATL', color: '#f59e0b', v: nearestByFrac(atl, frac, layout)?.value },
				{ label: '폼 TSB', color: '#14b8a6', v: nearestByFrac(tsb, frac, layout)?.value }
			]
		};
	});
	const fmt = (v: number | undefined) => (v == null ? '—' : v > 0 && false ? `+${v}` : v.toFixed(1));
	const cursorPct = $derived(frac == null ? null : frac * 100);
</script>

{#if layout}
	<div class="flex flex-col gap-1.5" aria-label="피트니스·폼 차트">
		<div class="flex min-h-[1.25rem] flex-wrap items-center gap-x-3 gap-y-0.5 text-xs">
			<span class="font-mono text-fg-muted">{readout?.date}</span>
			{#each readout?.items ?? [] as it (it.label)}
				<span class="flex items-center gap-1">
					<span style="color:{it.color}">●</span>
					<span class="text-fg-muted">{it.label}</span>
					<span class="font-mono text-fg-secondary">{fmt(it.v)}</span>
				</span>
			{/each}
		</div>

		<ChartScrub {pointCount} ariaLabel="체력·피로·폼 추세 — 눌러서 날짜별 값 확인" onChange={onScrubChange}>
			{#snippet children()}
				<div class="relative" style="touch-action: pan-y">
			<!-- 위 패널: CTL·ATL -->
			<svg viewBox="0 0 {W} {TOP_H}" preserveAspectRatio="none" style="width:100%;height:{TOP_H}px;display:block" aria-hidden="true">
				{#each [0, TOP_H / 2, TOP_H] as y (y)}
					<line x1="0" x2={W} y1={y} y2={y} stroke="currentColor" stroke-opacity="0.1" vector-effect="non-scaling-stroke" />
				{/each}
				<polyline points={toPolyline(atl, layout, layout.top, W, TOP_H)} fill="none" stroke="#f59e0b" stroke-width="2" stroke-linejoin="round" vector-effect="non-scaling-stroke" />
				<polyline points={toPolyline(ctl, layout, layout.top, W, TOP_H)} fill="none" stroke="#3b82f6" stroke-width="2.4" stroke-linejoin="round" vector-effect="non-scaling-stroke" />
			</svg>
			<span class="pointer-events-none absolute left-0 top-0 font-mono text-[10px] text-fg-muted">{Math.round(layout.top.max)}</span>

			<!-- 아래 패널: TSB -->
			<div class="relative mt-2">
				<svg viewBox="0 0 {W} {BOT_H}" preserveAspectRatio="none" style="width:100%;height:{BOT_H}px;display:block" aria-hidden="true">
					<defs>
						<clipPath id="up-{uid}"><rect x="0" y="0" width={W} height={zeroY} /></clipPath>
						<clipPath id="dn-{uid}"><rect x="0" y={zeroY} width={W} height={BOT_H - zeroY} /></clipPath>
					</defs>
					<rect x="0" y={bandY1} width={W} height={bandY2 - bandY1} fill="#22c55e" fill-opacity="0.12" />
					<polygon points={tsbArea} fill="#14b8a6" fill-opacity="0.28" clip-path="url(#up-{uid})" />
					<polygon points={tsbArea} fill="#f59e0b" fill-opacity="0.28" clip-path="url(#dn-{uid})" />
					<line x1="0" x2={W} y1={zeroY} y2={zeroY} stroke="currentColor" stroke-opacity="0.25" vector-effect="non-scaling-stroke" />
					<polyline points={toPolyline(tsb, layout, layout.bottom, W, BOT_H)} fill="none" stroke="#14b8a6" stroke-width="2" stroke-linejoin="round" vector-effect="non-scaling-stroke" />
					{#each future as f (f.key)}
						<polyline points={futureLine(f.points)} fill="none" stroke={SCEN_COLOR[f.key]} stroke-width="2" stroke-dasharray="5 4" stroke-linejoin="round" vector-effect="non-scaling-stroke" />
					{/each}
				</svg>
				<span class="pointer-events-none absolute left-4 font-mono text-[9px] text-semantic-green/80" style="top:{bandY1}px">레이스 최적 +5~+25</span>
				<span class="pointer-events-none absolute left-0 font-mono text-[10px] text-fg-muted" style="top:{Math.max(0, zeroY - 7)}px">0</span>
			</div>

			<!-- 오늘·레이스 세로선, 스크럽 커서 -->
			<div class="pointer-events-none absolute inset-y-0 w-px border-l border-dashed border-fg-muted/50" style="left:{todayPct}%"></div>
			{#if racePct != null}
				<div class="pointer-events-none absolute inset-y-0 w-px bg-semantic-green/60" style="left:{racePct}%"></div>
				<span class="pointer-events-none absolute top-0 -translate-x-full whitespace-nowrap pr-1 text-[10px] font-medium text-semantic-green" style="left:{racePct}%">레이스</span>
			{/if}
			{#if cursorPct != null}
				<div class="pointer-events-none absolute inset-y-0 w-px bg-fg-muted" style="left:{cursorPct}%"></div>
			{/if}
			</div>
			{/snippet}
		</ChartScrub>

		<div class="flex justify-between font-mono text-[10px] text-fg-muted">
			<span>{layout.t0}</span>
			<span>오늘 {layout.today}</span>
			<span>{layout.t1}</span>
		</div>
	</div>
{/if}
