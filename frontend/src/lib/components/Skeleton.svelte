<script lang="ts">
	// §C5 — 블록 스켈레톤 프리미티브 4종. 최종 레이아웃과 같은 높이를 예약해 CLS를 막는다.
	// shimmer 1.2s, prefers-reduced-motion이면 정지(고정 반투명 블록).
	let {
		kind = 'text',
		class: className = ''
	}: {
		kind?: 'text' | 'circle' | 'chart' | 'chip';
		class?: string;
	} = $props();
</script>

{#if kind === 'text'}
	<div class="skeleton-shimmer h-3 rounded bg-surface-3 {className}"></div>
{:else if kind === 'circle'}
	<div class="skeleton-shimmer aspect-square rounded-full bg-surface-3 {className}"></div>
{:else if kind === 'chart'}
	<div class="skeleton-shimmer min-h-[120px] rounded-lg bg-surface-3 {className}"></div>
{:else if kind === 'chip'}
	<div class="skeleton-shimmer h-8 w-20 rounded-full bg-surface-3 {className}"></div>
{/if}

<style>
	.skeleton-shimmer {
		position: relative;
		overflow: hidden;
	}
	.skeleton-shimmer::after {
		content: '';
		position: absolute;
		inset: 0;
		transform: translateX(-100%);
		background: linear-gradient(90deg, transparent, rgb(255 255 255 / 0.06), transparent);
		animation: skeleton-sweep 1.2s ease-in-out infinite;
	}
	@media (prefers-reduced-motion: reduce) {
		.skeleton-shimmer::after {
			animation: none;
			display: none;
		}
	}
	@keyframes skeleton-sweep {
		100% {
			transform: translateX(100%);
		}
	}
</style>
