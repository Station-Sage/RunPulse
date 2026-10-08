<script lang="ts">
	// 직접/코치 조정이 적용된 행의 배지 + 원래 계획 한 줄.
	import { workoutLabel } from '$lib/format';
	import { userAdjustmentSummary } from '$lib/rowActionView';
	import type { PlannedWorkout } from '$lib/types';

	let { workout }: { workout: PlannedWorkout } = $props();
	const s = $derived(userAdjustmentSummary(workout, workoutLabel));
</script>

{#if s}
	<p class="mt-0.5 flex items-center gap-1.5 text-xs text-fg-muted" data-testid="user-adjustment-line">
		<span class="rounded-full bg-surface-3 px-1.5 py-0.5 text-fg-secondary">{s.badge}</span>
		<span>{s.original}</span>
	</p>
{/if}
