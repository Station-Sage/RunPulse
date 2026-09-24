<script lang="ts">
	// 링 게이지 — UTRS/CIRS/TSB 등 상태 수치를 채움 비율과 의미 색으로 표현.
	// ringFraction·ringDash는 $lib/scoreRing(main에 선반영, 수정 금지).
	import { ringFraction, ringDash } from '$lib/scoreRing';
	import { providerLabelCompact, providerBadgeClass } from '$lib/provider';
	import type { SemanticStatus, ProviderKey } from '$lib/types';

	let {
		slug,
		label,
		value,
		min = 0,
		max = 100,
		decimals = 0,
		provider,
		status,
		unavailable = false,
		onDrill
	}: {
		slug: string;
		label: string;
		value: number | null;
		min?: number;
		max?: number;
		decimals?: number;
		provider: ProviderKey | null;
		status?: SemanticStatus;
		unavailable?: boolean;
		onDrill?: (p: { slug: string; provider: ProviderKey | null }) => void;
	} = $props();

	const ringColor = $derived(
		status
			? ({
					excellent: '#22c55e',
					good: '#14b8a6',
					neutral: '#94a3b8',
					caution: '#f59e0b',
					poor: '#ef4444'
				} as Record<SemanticStatus, string>)[status] ?? '#94a3b8'
			: '#94a3b8'
	);

	const statusLabel = $derived(
		status
			? ({
					excellent: '매우 좋음',
					good: '양호',
					neutral: '보통',
					caution: '주의',
					poor: '나쁨'
				} as Record<SemanticStatus, string>)[status] ?? ''
			: ''
	);

	const interactive = $derived(!!onDrill && !unavailable && value !== null);

	function handleClick() {
		if (interactive && onDrill) onDrill({ slug, provider });
	}
</script>

<!-- svelte-ignore a11y_no_noninteractive_tabindex -->
<div
	role={interactive ? 'button' : undefined}
	tabindex={interactive ? 0 : undefined}
	aria-label={interactive ? `${label} ${value?.toFixed(decimals)} — 눌러서 계산 근거 보기` : undefined}
	onclick={interactive ? handleClick : undefined}
	onkeydown={interactive
		? (e: KeyboardEvent) => (e.key === 'Enter' || e.key === ' ') && handleClick()
		: undefined}
	class="flex flex-col items-center gap-1.5 rounded-lg border border-border-subtle bg-surface-2 p-3 {interactive ? 'cursor-pointer hover:bg-surface-3' : ''}"
>
	<div class="relative">
		<svg viewBox="0 0 64 64" class="h-16 w-16 -rotate-90">
			<circle cx="32" cy="32" r="26" fill="none" stroke-width="6" class="stroke-surface-3" />
			{#if !unavailable && value !== null}
				<circle
					cx="32"
					cy="32"
					r="26"
					fill="none"
					stroke-width="6"
					stroke-linecap="round"
					stroke-dasharray={ringDash(ringFraction(value, min, max), 26)}
					style="stroke:{ringColor}"
				/>
			{/if}
		</svg>
		<div class="absolute inset-0 flex items-center justify-center font-mono text-lg font-bold">
			{#if unavailable || value === null}
				<span class="text-fg-muted">—</span>
			{:else}
				{value.toFixed(decimals)}
			{/if}
		</div>
	</div>
	<span class="text-xs font-medium">{label}</span>
	{#if !unavailable && status}
		<span class="text-[11px]" style="color:{ringColor}">{statusLabel}</span>
	{/if}
	{#if provider}
		<span class="rounded px-1.5 py-0.5 text-[10px] text-white {providerBadgeClass(provider)}"
			>{providerLabelCompact(provider)}</span
		>
	{/if}
</div>
