<script lang="ts">
	// 같은 러닝 쌍의 차이 분포(S6) — 점마다 diff_pct(또는 ratio). 이상치는 속 빈 점.
	import type { ProviderPairsData } from '$lib/types';
	import { pairSeries } from '$lib/providerMatrix';

	let { data }: { data: ProviderPairsData } = $props();

	const W = 320;
	const H = 120;
	const PAD = 12;
	const pts = $derived(pairSeries(data.pairs, data.row.compare));
	const ys = $derived(pts.map((p) => p.y));
	const lo = $derived(Math.min(...ys, data.row.compare === 'scale' ? 1 : 0));
	const hi = $derived(Math.max(...ys, data.row.compare === 'scale' ? 1 : 0));
	const span = $derived(hi - lo || 1);
	const px = (x: number) => PAD + x * (W - 2 * PAD);
	const py = (y: number) => H - PAD - ((y - lo) / span) * (H - 2 * PAD);
	const zero = $derived(py(data.row.compare === 'scale' ? 1 : 0));
</script>

{#if pts.length}
	<svg viewBox="0 0 {W} {H}" class="w-full" role="img" aria-label="소스 간 차이 분포">
		<line x1={PAD} x2={W - PAD} y1={zero} y2={zero} class="stroke-border-subtle" stroke-dasharray="3 3" />
		{#each pts as p}
			<circle cx={px(p.x)} cy={py(p.y)} r="3.5" class={p.outlier ? 'fill-none stroke-semantic-amber' : 'fill-semantic-teal'} stroke-width="1.5" />
		{/each}
	</svg>
{/if}
