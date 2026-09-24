<script lang="ts">
	// 고도 프로필 — 거리(km) 축의 순수 SVG 면적 차트. 외부 라이브러리 없음.
	// DECISIONS.md [P7-IMPL-ACTIVITY-SPLITS] (4)
	import type { ActivityStreamPoint } from '$lib/types';
	import { cumulativeDistance } from '$lib/splits';

	let {
		streams,
		totalSec,
		totalDistM,
		height = 80
	}: {
		streams: ActivityStreamPoint[];
		totalSec: number;
		totalDistM: number;
		height?: number;
	} = $props();

	const VW = 600;

	const dist = $derived(cumulativeDistance(streams, totalSec, totalDistM));
	const valid = $derived(
		streams
			.map((s, i) => ({ d: dist[i] ?? 0, alt: s.altitude_m }))
			.filter((x): x is { d: number; alt: number } => x.alt != null)
	);
	const minAlt = $derived(valid.length ? Math.min(...valid.map((v) => v.alt)) : 0);
	const maxAlt = $derived(valid.length ? Math.max(...valid.map((v) => v.alt)) : 0);
	const show = $derived(valid.length >= 10 && maxAlt - minAlt >= 3);
	const endD = $derived(dist.length ? dist[dist.length - 1] : 0);

	// 최대 200점으로 균등 다운샘플, y는 (max-min)에 5% 여백
	const pts = $derived.by(() => {
		if (!show || endD <= 0) return [] as { x: number; y: number }[];
		const step = Math.max(1, Math.ceil(valid.length / 200));
		const pad = (maxAlt - minAlt) * 0.05;
		const lo = minAlt - pad;
		const span = maxAlt + pad - lo;
		const out: { x: number; y: number }[] = [];
		for (let i = 0; i < valid.length; i += step) {
			out.push({ x: (valid[i].d / endD) * VW, y: (1 - (valid[i].alt - lo) / span) * height });
		}
		const last = valid[valid.length - 1];
		out.push({ x: (last.d / endD) * VW, y: (1 - (last.alt - lo) / span) * height });
		return out;
	});
	const line = $derived(pts.map((p) => `${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' '));
	const area = $derived(
		pts.length ? `0,${height} ${line} ${pts[pts.length - 1].x.toFixed(1)},${height}` : ''
	);
</script>

{#if pts.length > 1}
	<section class="flex flex-col gap-2" aria-label="고도 프로필">
		<div class="flex items-center justify-between">
			<p class="text-xs uppercase tracking-wide text-fg-muted">고도 프로필</p>
			<span class="text-[10px] text-fg-muted">{Math.round(minAlt)}~{Math.round(maxAlt)} m</span>
		</div>
		<div class="rounded-lg border border-border-subtle bg-surface-2 p-2">
			<svg
				viewBox="0 0 {VW} {height}"
				preserveAspectRatio="none"
				style="width:100%;height:{height}px;display:block"
				aria-hidden="true"
			>
				<polygon points={area} fill="#38bdf8" fill-opacity="0.18" />
				<polyline
					points={line}
					fill="none"
					stroke="#38bdf8"
					stroke-width="2"
					vector-effect="non-scaling-stroke"
				/>
			</svg>
			<div class="flex justify-between font-mono text-[10px] text-fg-muted">
				<span>0</span>
				<span>{(endD / 1000).toFixed(1)}km</span>
			</div>
		</div>
	</section>
{/if}
