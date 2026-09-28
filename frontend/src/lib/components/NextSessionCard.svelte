<script lang="ts">
	// 03a-today.md 1-A L2 "다음 세션 현황" — 구 Plan "보기" 흡수.
	import type { ActivePlan, TodaysAdjustment } from '$lib/types';
	import { weekProgressLabel, workoutLabel } from '$lib/format';
	import { base } from '$app/paths';
	import { planNewHref, roadmapLabel } from '$lib/planPrefill';

	let {
		plan,
		adjustment,
		today,
		raceGoal = null
	}: {
		plan: ActivePlan | null;
		adjustment: TodaysAdjustment | { adjusted: false; adjustment_reason: null } | null;
		today: string;
		raceGoal?: { name: string; days_left: number; distance_km: number; race_date: string; target_time_sec: number | null } | null;
	} = $props();

	const DOW = ['일', '월', '화', '수', '목', '금', '토'];

	// 서버가 준 다음 세션(다음 주 포함) 우선, 없으면 이번 주 목록에서 찾는다
	const nextSession = $derived(
		plan?.next_session ??
			plan?.workouts
				.filter((w) => w.date >= today && w.workout_type !== 'rest' && !w.superseded && !w.completed)
				.sort((a, b) => a.date.localeCompare(b.date))[0] ??
			null
	);

	// 날짜별 유효 계획 상태(서버 week_compliance) — 휴식·계획 전 날은 세지 않는다
	const weekDays = $derived(plan?.week?.days.filter((d) => d.state !== 'rest' && d.state !== 'pre_plan') ?? []);
	const weekSessions = $derived(plan?.week?.compliance.sessions);
	const DAY_MARK: Record<string, string> = { done: '●', partial: '◐', missed: '○', upcoming: '◌' };

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
		{#if raceGoal}
			<a href={planNewHref(base, raceGoal)} class="flex flex-col gap-1 rounded-xl border border-semantic-amber/40 bg-semantic-amber/10 p-3 hover:bg-semantic-amber/20">
				<span class="text-sm font-semibold">{raceGoal.name} D-{raceGoal.days_left} — {roadmapLabel(raceGoal.days_left)}</span>
				<span class="text-xs text-fg-secondary">목표 레이스 정보가 미리 채워집니다 →</span>
			</a>
		{:else}
			<p class="text-sm text-fg-secondary">활성 훈련 플랜이 없습니다</p>
			<a href="{base}/coach/plan" class="mt-1 block text-sm text-semantic-amber hover:underline"
				>Coach에서 플랜 만들기 →</a
			>
		{/if}
	</div>
{:else if nextSession === null}
	<div class="rounded-xl bg-surface-2 p-3">
		<p class="mb-1 text-xs text-fg-muted">
			{plan.goal.name} · {weekProgressLabel(plan.week_index, plan.goal.plan_weeks)}{plan.ctl_current != null ? ' · CTL ' + Math.round(plan.ctl_current) : ''}
		</p>
		<p class="text-sm text-fg-secondary">이번 주 남은 세션이 없습니다</p>
	</div>
{:else}
	<div class="flex flex-col gap-2">
		<p class="text-xs text-fg-muted">
			{plan.goal.name} · {weekProgressLabel(plan.week_index, plan.goal.plan_weeks)}{plan.ctl_current != null ? ' · CTL ' + Math.round(plan.ctl_current) : ''}
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
					전체 계획 보기 →
				</a>
			</div>
		</div>

		{#if weekDays.length > 0}
			<p class="text-xs text-fg-muted" title="● 이행 · ◐ 부족 · ○ 놓침 · ◌ 예정">
				이번 주
				{#each weekDays as d (d.date)}
					<span class:font-bold={d.today}>{DAY_MARK[d.state] ?? '◌'}</span>
				{/each}
				{#if weekSessions && weekSessions.total > 0}{weekSessions.done}/{weekSessions.total}일 이행{/if}
			</p>
		{/if}
	</div>
{/if}
