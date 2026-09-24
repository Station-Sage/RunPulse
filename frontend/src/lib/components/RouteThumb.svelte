<script lang="ts">
	// 목록용 경로 썸네일 — 32점 [lat,lng]를 등장방형 투영해 한 색 폴리라인으로. 타일 없음.
	import { projectRoute } from '$lib/routeGeometry';

	let { route, size = 44 }: { route: [number, number][] | null | undefined; size?: number } = $props();

	const proj = $derived(
		route && route.length >= 2
			? projectRoute(route.map(([lat, lng]) => ({ lat, lng, pace: null, hr: null })), size, 4)
			: null
	);
	const line = $derived(proj ? proj.points.map((p) => `${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ') : '');
</script>

<div
	class="flex shrink-0 items-center justify-center rounded-md bg-surface-3"
	style="width:{size}px;height:{size}px"
	aria-hidden="true"
>
	{#if proj}
		<svg viewBox="0 0 {proj.width} {proj.height}" style="width:{proj.width}px;height:{proj.height}px;max-width:100%;max-height:100%">
			<polyline points={line} fill="none" stroke="#2dd4bf" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
		</svg>
	{:else}
		<span class="h-1.5 w-1.5 rounded-full bg-fg-muted"></span>
	{/if}
</div>
