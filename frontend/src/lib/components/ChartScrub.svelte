<script lang="ts">
	// §C1 ChartScrub 인터랙션 레이어(ux-review-2026-09/10-today/design.md) — 포인터·키보드 공통 로직.
	// 데스크톱 hover=미리보기, click=고정(같은 점 재클릭=해제). 모바일 tap=고정, drag=스크럽(손을
	// 떼도 유지 — pointerup에서 해제하지 않는다). 키보드 ←/→ 1점, Shift+←/→ 7점, Home/End, Esc 해제.
	// 렌더링(마커·툴팁)은 호출부가 snippet으로 담당 — 이 컴포넌트는 "어느 인덱스가 선택됐는가"만 안다.
	import type { Snippet } from 'svelte';
	import { clamp01 } from '$lib/chart/scrub';

	let {
		pointCount,
		ariaLabel = '차트 스크럽',
		onChange,
		children
	}: {
		pointCount: number;
		ariaLabel?: string;
		onChange?: (index: number | null, pinned: boolean) => void;
		children?: Snippet<[number | null, boolean]>;
	} = $props();

	let index = $state<number | null>(null);
	let pinned = $state(false);
	let containerEl: HTMLDivElement | undefined = $state();

	function set(i: number | null, p: boolean) {
		index = i;
		pinned = p;
		onChange?.(i, p);
	}

	function indexAt(clientX: number): number {
		if (!containerEl || pointCount <= 1) return 0;
		const rect = containerEl.getBoundingClientRect();
		const frac = clamp01((clientX - rect.left) / rect.width);
		return Math.round(frac * (pointCount - 1));
	}

	function onPointerDown(e: PointerEvent) {
		const i = indexAt(e.clientX);
		if (pinned && i === index) {
			set(null, false); // 같은 점 재탭 → 해제
		} else {
			set(i, true);
		}
		containerEl?.setPointerCapture(e.pointerId);
	}

	function onPointerMove(e: PointerEvent) {
		if (e.buttons > 0) {
			set(indexAt(e.clientX), true); // 드래그 스크럽
		} else if (!pinned) {
			set(indexAt(e.clientX), false); // 데스크톱 hover 미리보기
		}
	}

	function onPointerLeave() {
		if (!pinned) set(null, false);
	}

	function onKeydown(e: KeyboardEvent) {
		const step = e.shiftKey ? 7 : 1;
		const current = index ?? 0;
		if (e.key === 'ArrowLeft') {
			set(Math.max(0, current - step), true);
			e.preventDefault();
		} else if (e.key === 'ArrowRight') {
			set(Math.min(pointCount - 1, current + step), true);
			e.preventDefault();
		} else if (e.key === 'Home') {
			set(0, true);
			e.preventDefault();
		} else if (e.key === 'End') {
			set(pointCount - 1, true);
			e.preventDefault();
		} else if (e.key === 'Escape') {
			set(null, false);
		}
	}
</script>

<div
	bind:this={containerEl}
	class="relative"
	style="touch-action: pan-y"
	tabindex="0"
	role="slider"
	aria-label={ariaLabel}
	aria-valuemin={0}
	aria-valuemax={Math.max(0, pointCount - 1)}
	aria-valuenow={index ?? undefined}
	onpointerdown={onPointerDown}
	onpointermove={onPointerMove}
	onpointerleave={onPointerLeave}
	onkeydown={onKeydown}
>
	{@render children?.(index, pinned)}
</div>
