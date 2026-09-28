<script lang="ts">
	// §C5 — 셸 상단 2px 진행바. 150ms 지연 후 표시(빠른 전환은 깜빡임 없음), 완료 시 페이드.
	import { navigating } from '$app/state';

	let visible = $state(false);
	let timer: ReturnType<typeof setTimeout> | undefined;

	$effect(() => {
		if (navigating.to) {
			timer = setTimeout(() => {
				visible = true;
			}, 150);
		} else {
			clearTimeout(timer);
			visible = false;
		}
		return () => clearTimeout(timer);
	});
</script>

{#if visible}
	<div class="pointer-events-none fixed inset-x-0 top-0 z-[60] h-0.5 overflow-hidden bg-transparent">
		<div class="h-full w-full origin-left animate-[progress-sweep_1.1s_ease-in-out_infinite] bg-series-1"></div>
	</div>
{/if}

<style>
	@keyframes progress-sweep {
		0% {
			transform: scaleX(0);
			opacity: 1;
		}
		60% {
			transform: scaleX(0.7);
		}
		100% {
			transform: scaleX(1);
			opacity: 0;
		}
	}
	@media (prefers-reduced-motion: reduce) {
		div > div {
			animation: none;
			transform: scaleX(0.6);
			opacity: 1;
		}
	}
</style>
