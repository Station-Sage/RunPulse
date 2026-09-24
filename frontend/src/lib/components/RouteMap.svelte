<script lang="ts">
	// GPS 좌표를 타일 없이 SVG 폴리라인으로 그리는 경로 지도.
	// 색: 페이스(파랑→주황) 또는 심박(청록→빨강) — 5~95퍼센타일 정규화.
	// 순수 계산: $lib/routeGeometry (routePoints · downsample · projectRoute · robustRange · segmentColor).
	import type { ActivityStreamPoint } from '$lib/types';
	import { routePoints, downsample, projectRoute, robustRange, segmentColor } from '$lib/routeGeometry';

	const MAX_POINTS = 300;

	let {
		streams,
		mode = 'pace',
		size = 300,
		pad = 8
	}: {
		streams: ActivityStreamPoint[] | null;
		mode?: 'pace' | 'hr';
		size?: number;
		pad?: number;
	} = $props();

	const rawPoints = $derived(streams ? routePoints(streams) : []);

	const route = $derived.by(() => {
		if (rawPoints.length < 2) return null;
		const sampled = downsample(rawPoints, MAX_POINTS);
		return projectRoute(sampled, size, pad);
	});

	const colorRange = $derived.by(() => {
		if (!route) return null;
		return robustRange(route.points.map((p) => (mode === 'pace' ? p.pace : p.hr)));
	});

	const segments = $derived.by(() => {
		if (!route || route.points.length < 2) return [];
		const segs: { x1: string; y1: string; x2: string; y2: string; color: string }[] = [];
		for (let i = 0; i + 1 < route.points.length; i++) {
			const a = route.points[i];
			const b = route.points[i + 1];
			segs.push({
				x1: a.x.toFixed(2),
				y1: a.y.toFixed(2),
				x2: b.x.toFixed(2),
				y2: b.y.toFixed(2),
				color: segmentColor(mode === 'pace' ? a.pace : a.hr, colorRange, mode)
			});
		}
		return segs;
	});
</script>

{#if route && segments.length > 0}
	<div class="flex flex-col gap-1">
		<svg
			viewBox="0 0 {route.width} {route.height}"
			style="display:block; max-width:100%; height:auto;"
			role="img"
			aria-label="GPS 경로 지도"
		>
			{#each segments as seg}
				<line
					x1={seg.x1}
					y1={seg.y1}
					x2={seg.x2}
					y2={seg.y2}
					stroke={seg.color}
					stroke-width="2"
					stroke-linecap="round"
					vector-effect="non-scaling-stroke"
				/>
			{/each}
			<!-- 시작점(초록) -->
			<circle
				cx={route.points[0].x.toFixed(2)}
				cy={route.points[0].y.toFixed(2)}
				r="4"
				fill="#22c55e"
				stroke="white"
				stroke-width="1.5"
				vector-effect="non-scaling-stroke"
			/>
			<!-- 끝점(회색) -->
			<circle
				cx={route.points[route.points.length - 1].x.toFixed(2)}
				cy={route.points[route.points.length - 1].y.toFixed(2)}
				r="4"
				fill="#64748b"
				stroke="white"
				stroke-width="1.5"
				vector-effect="non-scaling-stroke"
			/>
		</svg>
		<p class="text-[10px] text-fg-muted">
			GPS {rawPoints.length.toLocaleString('ko-KR')}점{rawPoints.length > MAX_POINTS
				? ` (${MAX_POINTS}점으로 다운샘플)`
				: ''}
		</p>
	</div>
{/if}
