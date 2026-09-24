<script lang="ts">
	// 고도 프로필 — 스트림의 altitude_m를 순수 SVG 면적 차트로 그린다.
	// 외부 라이브러리 없음. DECISIONS.md [P7-IMPL-ACTIVITY-SPLITS] (4)
	import type { SplitStream } from '$lib/splits';

	let {
		streams,
		height = 64
	}: {
		streams: Pick<SplitStream, 'altitude_m'>[];
		height?: number;
	} = $props();

	const VW = 600;
	const PAD = 4;

	// null을 걸러낸 (인덱스, 고도) 쌍
	const pts = $derived(
		streams
			.map((s, i) => ({ i, alt: s.altitude_m }))
			.filter((x): x is { i: number; alt: number } => x.alt != null)
	);

	const hasData = $derived(pts.length >= 2);
	const n = $derived(streams.length);
	const minAlt = $derived(hasData ? Math.min(...pts.map((x) => x.alt)) : 0);
	const maxAlt = $derived(hasData ? Math.max(...pts.map((x) => x.alt)) : 0);
	const altRange = $derived(maxAlt - minAlt);

	function toX(idx: number): number {
		return n <= 1 ? 0 : (idx / (n - 1)) * VW;
	}

	function toY(alt: number): number {
		const inner = height - PAD * 2;
		if (altRange === 0) return PAD + inner / 2;
		return PAD + inner - ((alt - minAlt) / altRange) * inner;
	}

	// 닫힌 면적 SVG 경로 (M ... L ... Z)
	const areaPath = $derived((): string => {
		if (!hasData) return '';
		const coords = pts.map((x) => `${toX(x.i).toFixed(1)},${toY(x.alt).toFixed(1)}`);
		const x0 = toX(pts[0].i).toFixed(1);
		const x1 = toX(pts[pts.length - 1].i).toFixed(1);
		const yBottom = height.toFixed(1);
		return `M ${x0},${yBottom} L ${coords.join(' L ')} L ${x1},${yBottom} Z`;
	});
</script>

{#if hasData}
	<section class="flex flex-col gap-1.5">
		<div class="flex items-center justify-between">
			<p class="text-xs uppercase tracking-wide text-fg-muted">고도 프로필</p>
			<span class="text-[10px] text-fg-muted"
				>↑{Math.round(maxAlt)}m &nbsp; ↓{Math.round(minAlt)}m</span
			>
		</div>
		<svg
			viewBox="0 0 {VW} {height}"
			preserveAspectRatio="none"
			style="display:block; width:100%; height:{height}px;"
			aria-hidden="true"
		>
			<path
				d={areaPath()}
				fill="#6366f1"
				fill-opacity="0.25"
				stroke="#6366f1"
				stroke-width="1.5"
				vector-effect="non-scaling-stroke"
			/>
		</svg>
	</section>
{/if}
