<script lang="ts">
	// 플랜 섹션 — 진행 중 플랜 링크 또는 새 프로그램 만들기.
	import { base } from '$app/paths';
	import { weekProgressLabel } from '$lib/format';
	import type { ActivePlan } from '$lib/types';

	let { activePlan }: { activePlan: ActivePlan | null } = $props();
</script>

<div class="border-t border-border-subtle px-4 py-3">
	<h2 class="mb-1 text-xs uppercase tracking-wide text-fg-muted">플랜</h2>
	{#if activePlan}
		<a
			href="{base}/coach/plan/{activePlan.goal.id}"
			class="flex items-center justify-between min-h-11 rounded-lg bg-surface-2 px-3 py-2 hover:bg-surface-3"
		>
			<div class="min-w-0">
				<p class="truncate text-sm font-medium">{activePlan.goal.name}</p>
				<p class="text-xs text-fg-muted">
					진행 중: {weekProgressLabel(activePlan.week_index, activePlan.goal.plan_weeks)}
				</p>
			</div>
			<span class="ml-2 shrink-0 text-fg-muted">›</span>
		</a>
	{:else}
		<a href="{base}/coach/plan/new" class="text-sm text-semantic-amber hover:underline">
			새 프로그램 만들기 →
		</a>
	{/if}
</div>
