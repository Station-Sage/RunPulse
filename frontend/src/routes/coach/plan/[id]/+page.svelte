<script lang="ts">
	// 03e-coach.md 5-F — 플랜 상세: 진행 중인 훈련 플랜.
	import type { PlanDetailPageData } from './+page';
	import { formatDuration } from '$lib/format';
	import { base } from '$app/paths';

	let { data }: { data: PlanDetailPageData } = $props();

	const WORKOUT_LABELS: Record<string, string> = {
		rest: '휴식',
		recovery: '회복',
		easy: '쉬운 달리기',
		long: '장거리',
		tempo: '템포',
		interval: '인터벌'
	};

	const DAY_KO = ['월', '화', '수', '목', '금', '토', '일'];

	function dayLabel(dateStr: string): string {
		const d = new Date(dateStr + 'T00:00:00');
		return DAY_KO[d.getDay() === 0 ? 6 : d.getDay() - 1];
	}

	function paceRange(min: number | null, max: number | null): string {
		if (min == null && max == null) return '';
		const fmt = (s: number) => {
			const m = Math.floor(s);
			const sec = Math.round((s - m) * 60);
			return `${m}:${String(sec).padStart(2, '0')}`;
		};
		if (min != null && max != null) return `${fmt(min)}–${fmt(max)}/km`;
		if (min != null) return `>${fmt(min)}/km`;
		return `<${fmt(max!)}/km`;
	}
</script>

<div class="flex flex-col">
	{#if data.errorMessage && !data.plan}
		<div class="flex flex-col items-center gap-2 px-4 py-10 text-center">
			<p class="text-fg-secondary">플랜을 불러올 수 없습니다</p>
			<p class="text-xs text-fg-muted">{data.errorMessage}</p>
			<a href="{base}/coach" class="mt-2 text-sm text-semantic-amber hover:underline">← 코치 홈</a>
		</div>
	{:else if data.plan}
		<!-- 헤더 -->
		<div class="border-b border-border-subtle px-4 py-4">
			<div class="mb-1 flex items-center gap-2">
				<a href="{base}/coach" class="text-xs text-fg-muted hover:underline">← 코치</a>
			</div>
			<h1 class="text-base font-semibold">{data.plan.goal.name}</h1>
			<p class="text-sm text-fg-secondary">
				{data.plan.week_index}주차{data.plan.goal.plan_weeks
					? ` / ${data.plan.goal.plan_weeks}주`
					: ''}
				{#if data.plan.goal.race_date}
					· 레이스 {data.plan.goal.race_date}
				{/if}
				{#if data.plan.goal.target_time_sec}
					· 목표 {formatDuration(data.plan.goal.target_time_sec)}
				{/if}
			</p>

			<!-- CTL 현황 -->
			{#if data.plan.ctl_current != null}
				<div class="mt-3">
					<div class="mb-1 flex items-center justify-between text-xs text-fg-muted">
						<span>현재 CTL</span>
						<span class="font-medium text-fg-secondary">{Math.round(data.plan.ctl_current)}</span>
					</div>
					<div class="h-1.5 w-full overflow-hidden rounded-full bg-surface-3">
						<div
							class="h-full rounded-full bg-semantic-teal"
							style="width: {Math.min(100, (data.plan.ctl_current / 100) * 100)}%"
						></div>
					</div>
				</div>
			{/if}

			{#if data.plan.compliance_pct != null}
				<p class="mt-2 text-xs text-fg-muted">
					달성률 <span class="font-medium text-fg-secondary">{data.plan.compliance_pct}%</span>
				</p>
			{/if}
		</div>

		<!-- 오늘 조정 경고 -->
		{#if data.adjustment?.adjusted}
			<div class="border-b border-border-subtle bg-surface-2 px-4 py-3">
				<p class="text-xs font-medium text-semantic-amber">⚠ 오늘 조정됨</p>
				{#if data.adjustment.adjustment_reason}
					<p class="mt-0.5 text-xs text-fg-secondary">{data.adjustment.adjustment_reason}</p>
				{/if}
				<p class="mt-0.5 text-xs text-fg-muted">
					{WORKOUT_LABELS[data.adjustment.original_type] ?? data.adjustment.original_type} →
					{WORKOUT_LABELS[data.adjustment.adjusted_type] ?? data.adjustment.adjusted_type}
				</p>
			</div>
		{/if}

		<!-- 이번 주 워크아웃 목록 -->
		<div class="border-b border-border-subtle px-4 py-3">
			<p class="mb-2 text-xs uppercase tracking-wide text-fg-muted">이번 주</p>
			{#if data.plan.workouts.length === 0}
				<p class="text-sm text-fg-muted">이번 주 워크아웃이 없습니다.</p>
			{:else}
				<ul class="divide-y divide-border-subtle">
					{#each data.plan.workouts as w (w.id)}
						<li>
							<a
								href="{base}/coach/plan/{data.plan.goal.id}/session/{w.date}"
								class="flex items-start gap-3 py-2.5 hover:bg-surface-2"
							>
								<span class="w-6 shrink-0 text-center text-xs text-fg-muted"
									>{dayLabel(w.date)}</span
								>
								<div class="min-w-0 flex-1">
									<div class="flex items-center gap-2">
										<span class="text-sm font-medium">
											{WORKOUT_LABELS[w.workout_type] ?? w.workout_type}
										</span>
										{#if w.distance_km}
											<span class="text-xs text-fg-muted">{w.distance_km}km</span>
										{/if}
										{#if paceRange(w.target_pace_min, w.target_pace_max)}
											<span class="text-xs text-fg-muted"
												>{paceRange(w.target_pace_min, w.target_pace_max)}</span
											>
										{/if}
									</div>
									{#if w.description}
										<p class="mt-0.5 text-xs text-fg-secondary">{w.description}</p>
									{/if}
								</div>
								{#if w.completed}
									<span class="shrink-0 text-xs text-semantic-green">✓</span>
								{/if}
							</a>
						</li>
					{/each}
				</ul>
			{/if}
		</div>
	{/if}
</div>
