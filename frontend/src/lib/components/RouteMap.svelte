<script lang="ts">
	// GPS 좌표를 타일 없이 SVG 폴리라인으로 그리는 경로 지도 — 페이스(파랑→주황)/심박(청록→빨강).
	// 순수 계산: $lib/routeGeometry. DECISIONS.md [P7-IMPL-ROUTE-MAP]: 외부 타일 요청 없음(로컬 퍼스트).
	import type { ActivityStreamPoint } from '$lib/types';
	import {
		routePoints,
		downsample,
		projectRoute,
		robustRange,
		segmentColor
	} from '$lib/routeGeometry';

	let { streams }: { streams: ActivityStreamPoint[] } = $props();

	let mode = $state<'pace' | 'hr'>('pace');

	const raw = $derived(routePoints(streams));
	const route = $derived(projectRoute(downsample(raw, 300), 320, 12));
	const hrRange = $derived(robustRange(route ? route.points.map((p) => p.hr) : []));
	const paceRange = $derived(robustRange(route ? route.points.map((p) => p.pace) : []));
	// 심박이 없으면 토글을 숨기고 페이스로 고정
	const canToggle = $derived(hrRange != null);
	const activeMode = $derived(canToggle ? mode : 'pace');
	const range = $derived(activeMode === 'pace' ? paceRange : hrRange);

	function pairValue(a: number | null, b: number | null): number | null {
		if (a != null && b != null) return (a + b) / 2;
		return a ?? b;
	}

	const segments = $derived(
		route
			? route.points.slice(1).map((p, i) => {
					const q = route.points[i];
					const v =
						activeMode === 'pace' ? pairValue(q.pace, p.pace) : pairValue(q.hr, p.hr);
					return { x1: q.x, y1: q.y, x2: p.x, y2: p.y, color: segmentColor(v, range, activeMode) };
				})
			: []
	);
</script>

{#if route}
	<section class="flex flex-col gap-2" aria-label="경로">
		<div class="flex items-center justify-between">
			<p class="text-xs uppercase tracking-wide text-fg-muted">경로</p>
			{#if canToggle}
				<div class="flex gap-3">
					{#each [['pace', '페이스'], ['hr', '심박']] as [key, label] (key)}
						<button
							type="button"
							aria-pressed={mode === key}
							onclick={() => (mode = key as 'pace' | 'hr')}
							class="text-xs {mode === key ? 'text-fg-primary underline' : 'text-fg-muted'}"
							>{label}</button
						>
					{/each}
				</div>
			{/if}
		</div>
		<div class="flex justify-center rounded-lg border border-border-subtle bg-surface-2 p-3">
			<svg
				viewBox="0 0 {route.width} {route.height}"
				class="w-full"
				style="max-height:280px;aspect-ratio:{route.width}/{route.height}"
				role="img"
				aria-label="활동 경로 지도(타일 없음)"
			>
				{#each segments as s, i (i)}
					<line
						x1={s.x1}
						y1={s.y1}
						x2={s.x2}
						y2={s.y2}
						stroke={s.color}
						stroke-width="3"
						stroke-linecap="round"
					/>
				{/each}
				<circle
					cx={route.points[0].x}
					cy={route.points[0].y}
					r="5"
					fill="#22c55e"
					stroke="#0b1220"
					stroke-width="2"
				/>
				<circle
					cx={route.points[route.points.length - 1].x}
					cy={route.points[route.points.length - 1].y}
					r="5"
					fill="#f8fafc"
					stroke="#0b1220"
					stroke-width="2"
				/>
			</svg>
		</div>
		<div class="flex items-center gap-2 text-[10px] text-fg-muted">
			{#if activeMode === 'pace'}
				<span>빠름</span>
				<span
					class="h-1.5 flex-1 rounded"
					style="background: linear-gradient(to right, #3b82f6, #f97316)"
				></span>
				<span>느림</span>
			{:else}
				<span>낮음</span>
				<span
					class="h-1.5 flex-1 rounded"
					style="background: linear-gradient(to right, #14b8a6, #ef4444)"
				></span>
				<span>높음</span>
			{/if}
		</div>
		<p class="text-[10px] text-fg-muted">지도 타일 없이 GPS 좌표만으로 그린 경로 · 북쪽이 위</p>
	</section>
{/if}
