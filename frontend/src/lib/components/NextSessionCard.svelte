<script lang="ts">
	// 03a-today.md 1-A L2 "다음 세션 현황" — 구 Plan "보기" 흡수.
	import type { ActivePlan, TodaysAdjustment } from '$lib/types';
	import { workoutLabel } from '$lib/format';
	import { base } from '$app/paths';

	let {
		plan,
		adjustment,
		today
	}: {
		plan: ActivePlan | null;
		adjustment: TodaysAdjustment | { adjusted: false; adjustment_reason: null } | null;
		today: string;
	} = $props();

	const DOW = ['일', '월', '화', '수', '목', '금', '토'];

	const nextSession = $derived(
		plan?.workouts
			.filter((w) => w.date >= today && w.workout_type !== 'rest')
			.sort((a, b) => a.date.localeCompare(b.date))[0] ?? null
	);

	const weekWork = $derived(plan?.workouts.filter((w) => w.workout_type !== 'rest') ?? []);
	const weekDone = $derived(weekWork.filter((w) => w.completed === 1).length);

	function dayText(date: string): string {
		const diff = Math.round(
			(new Date(date + 'T00:00:00').getTime() - new Date(today + 'T00:00:00').getTime()) /
				86400000
		);
		if (diff === 0) return '오늘';
		if (diff === 1) return '내일';
		return `${date.slice(5)}(${DOW[new Date(date + 'T00:00:00').getDay()]})`;
	}

	const showAdjustment = $derived(
		nextSession !== null &&
			nextSession.date === today &&
			adjustment !== null &&
			'original_type' in adjustment &&
			adjustment.adjusted === true
	);
</script>

{#if plan === null}
	<div class="rounded-xl bg-surface-2 p-3">
		<p class="text-sm text-fg-secondary">활성 훈련 플랜이 없습니다</p>
		<a href="{base}/coach/plan" class="mt-1 block text-sm text-semantic-amber hover:underline"
			>Coach에서 플랜 만들기 →</a
		>
	</div>
{:else if nextSession === null}
	<div class="rounded-xl bg-surface-2 p-3">
		<p class="mb-1 text-xs text-fg-muted">
			{plan.goal.name} · {plan.week_index}주차{plan.goal.plan_weeks
				? ' / ' + plan.goal.plan_weeks + '주'
				: ''}{plan.ctl_current != null ? ' · CTL ' + Math.round(plan.ctl_current) : ''}
		</p>
		<p class="text-sm text-fg-secondary">이번 주 남은 세션이 없습니다</p>
	</div>
{:else}
	<div class="flex flex-col gap-2">
		<p class="text-xs text-fg-muted">
			{plan.goal.name} · {plan.week_index}주차{plan.goal.plan_weeks
				? ' / ' + plan.goal.plan_weeks + '주'
				: ''}{plan.ctl_current != null ? ' · CTL ' + Math.round(plan.ctl_current) : ''}
		</p>

		<div class="rounded-xl bg-surface-2 p-3">
			<div class="flex items-start justify-between gap-2">
				<div class="flex-1">
					<div class="flex items-center gap-2">
						<span class="rounded-full bg-surface-3 px-2 py-0.5 text-xs text-fg-secondary"
							>{dayText(nextSession.date)}</span
						>
						<span class="text-sm font-medium">{workoutLabel(nextSession.workout_type)}</span>
						{#if nextSession.distance_km}
							<span class="text-xs text-fg-muted">{nextSession.distance_km}km</span>
						{/if}
					</div>
					{#if nextSession.description}
						<p class="mt-1 text-xs text-fg-secondary">{nextSession.description}</p>
					{/if}
				</div>
			</div>

			{#if showAdjustment && adjustment && 'original_type' in adjustment}
				<div class="mt-2 rounded-md bg-semantic-amber/10 px-2 py-1.5">
					<p class="text-xs font-medium text-semantic-amber">
						⚠ 상태 조정: {workoutLabel(adjustment.original_type)} →
						{workoutLabel(adjustment.adjusted_type)}
					</p>
					{#if adjustment.adjustment_reason}
						<p class="mt-0.5 text-xs text-fg-secondary">{adjustment.adjustment_reason}</p>
					{/if}
				</div>
			{/if}

			<div class="mt-2 flex gap-3">
				<a
					href="{base}/coach/plan/{plan.goal.id}/session/{nextSession.date}"
					class="text-xs text-fg-secondary hover:text-fg-primary"
				>
					세션 상세 →
				</a>
				<a
					href="{base}/coach/plan/{plan.goal.id}"
					class="text-xs text-fg-secondary hover:text-fg-primary"
				>
					계획 수립·수정은 Coach에서 →
				</a>
			</div>
		</div>

		{#if weekWork.length > 0}
			<p class="text-xs text-fg-muted">
				이번 주 준수율
				{#each weekWork as w}
					<span>{w.completed === 1 ? '●' : '○'}</span>
				{/each}
				{weekDone}/{weekWork.length} 완료
			</p>
		{/if}
	</div>
{/if}
