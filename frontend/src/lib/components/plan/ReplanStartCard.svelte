<script lang="ts">
	// 시작점 카드 — 첫 주 거리 근거와 목표 기록 바꾸기 (DESIGN-PLAN-A6-REPLAN-UI §11).
	import { fmtTarget, startCardText, type RawInputs } from '$lib/replanView';
	import type { ReplanPreview } from '$lib/types';

	let {
		preview,
		values = $bindable(),
		error,
		oninput
	}: { preview: ReplanPreview; values: RawInputs; error?: string; oninput: () => void } = $props();

	let editing = $state(false);
	const goal = $derived(preview.goal_target_time_sec);
</script>

<section class="space-y-2 rounded-lg bg-surface-2 p-3 text-sm">
	<h2 class="text-xs text-fg-secondary">시작점</h2>
	<p>{startCardText(preview)}</p>
	<div class="text-xs text-fg-secondary">
		{#if !editing}
			<span>목표 기록 {goal ? fmtTarget(goal) : '없음'}</span>
			<button class="ml-2 min-h-11 underline" onclick={() => (editing = true)}>바꾸기</button>
		{:else}
			<label class="block">
				<span class="mb-1 block">목표 기록</span>
				<input
					class="h-11 w-full rounded-lg border border-border bg-surface-1 px-3 text-sm text-fg-primary"
					inputmode="text"
					placeholder={goal ? fmtTarget(goal) : '예: 3:45:00'}
					bind:value={values.target}
					oninput={oninput}
				/>
				{#if error}<span class="mt-1 block text-semantic-red">{error}</span>{/if}
			</label>
		{/if}
	</div>
</section>
