<script lang="ts">
	// 월 모드 헤더 — ‹ 2026년 8월 › [✕ 8월] + 요약 한 줄(횟수·거리·유형 분포·전월 대비).
	import type { ActivityListSummary } from '$lib/types';

	let {
		month,
		summary,
		canNext,
		onshift,
		onclear
	}: {
		month: string;
		summary: ActivityListSummary['month'] | undefined;
		canNext: boolean;
		onshift: (delta: number) => void;
		onclear: () => void;
	} = $props();

	const label = $derived(`${month.slice(0, 4)}년 ${Number(month.slice(5))}월`);
	const pct = $derived(summary?.prev_month_pct);
</script>

<div class="flex flex-col gap-1 border-b border-border-subtle bg-surface-1 px-4 py-3" data-testid="month-header">
	<div class="flex items-center gap-2">
		<button type="button" aria-label="이전 달" onclick={() => onshift(-1)} class="h-8 w-8 rounded-full text-fg-secondary hover:bg-surface-3">‹</button>
		<span class="text-sm font-semibold">{label}</span>
		<button type="button" aria-label="다음 달" disabled={!canNext} onclick={() => onshift(1)} class="h-8 w-8 rounded-full text-fg-secondary hover:bg-surface-3 disabled:opacity-30">›</button>
		<button type="button" onclick={onclear} class="ml-auto rounded-full border border-border-subtle px-3 py-1 text-xs text-fg-muted hover:text-fg-secondary">✕ {Number(month.slice(5))}월</button>
	</div>
	{#if summary}
		<p class="text-xs text-fg-muted">
			{summary.n}회 · {summary.km.toFixed(1)}km{#each summary.by_class as c (c.key)} · {c.label} {c.n}{/each}{#if pct != null}
				· 전월 대비 {pct > 0 ? '+' : ''}{Math.round(pct)}%{/if}
		</p>
	{/if}
</div>
