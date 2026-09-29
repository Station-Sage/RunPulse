<script lang="ts">
	// B5 주간 스트립 — design 10-today §C7 상태 기호. 판정은 서버(week_compliance)가 하고 여기선 표기만 한다.
	import { base } from '$app/paths';
	import type { WeekCompliance } from '$lib/types';
	import { dayCell, weekSummary, hasWeekPlan } from '$lib/weekStrip';

	let { week, planId = null }: { week: WeekCompliance | null | undefined; planId?: number | null } = $props();

	const cells = $derived(hasWeekPlan(week) ? week.days.map(dayCell) : []);
	const planHref = $derived(planId != null ? `${base}/coach/plan/${planId}` : null);
	const TONE: Record<string, string> = {
		done: 'text-semantic-green',
		partial: 'text-semantic-amber',
		missed: 'text-semantic-red',
		today: 'text-semantic-teal',
		upcoming: 'text-fg-muted border-dashed',
		rest: 'text-fg-muted',
		pre_plan: 'text-fg-muted opacity-50'
	};
</script>

{#if hasWeekPlan(week)}
	<section class="flex flex-col gap-2" aria-label="이번 주 계획 진행">
		<div class="flex items-center justify-between text-xs">
			<span class="text-fg-secondary">{weekSummary(week)}</span>
			{#if planHref}<a href={planHref} class="text-fg-muted hover:text-fg-primary">전체 계획 →</a>{/if}
		</div>
		<ol class="grid grid-cols-7 gap-1" title="● 이행 · ◐ 부족 · ○ 놓침 · ⟳ 대체 · ◉ 오늘 · ┄ 휴식 · ◌ 예정">
			{#each cells as c (c.date)}
				{@const href = c.linkable && planId != null ? `${base}/coach/plan/${planId}/session/${c.date}` : null}
				<li class="min-w-0">
					<svelte:element
						this={href ? 'a' : 'div'}
						{href}
						title={c.title}
						class="flex flex-col items-center gap-0.5 rounded-md border border-border-subtle px-0.5 py-1.5 text-center {TONE[c.tone]} {href ? 'hover:bg-surface-3' : ''} {c.tone === 'today' ? 'bg-surface-2' : ''}"
					>
						<span class="text-[10px] text-fg-muted">{c.dow}</span>
						{#if c.symbol}<span class="text-base leading-none" aria-hidden="true">{c.symbol}</span>{/if}
						<span class="max-w-full truncate text-[10px] {c.symbol ? '' : 'py-1'}">{c.label}</span>
					</svelte:element>
				</li>
			{/each}
		</ol>
	</section>
{/if}
