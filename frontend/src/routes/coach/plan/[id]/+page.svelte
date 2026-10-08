<script lang="ts">
	// 03e-coach.md 5-F — 플랜 상세: 진행 중인 훈련 플랜.
	import type { PlanDetailPageData } from './+page';
	import { formatDuration, formatPaceRange, weekProgressLabel, workoutLabel } from '$lib/format';
	import { base } from '$app/paths';
	import MetricBreakdown from '$lib/components/MetricBreakdown.svelte';
	import Icon from '$lib/components/Icon.svelte';
	import AdjustmentCard from '$lib/components/plan/AdjustmentCard.svelte';
	import { invalidateAll } from '$app/navigation';
	import RowActionButton from '$lib/components/plan/RowActionButton.svelte';
	import UserAdjustmentLine from '$lib/components/plan/UserAdjustmentLine.svelte';
	import type { PlannedWorkout } from '$lib/types';

	let { data }: { data: PlanDetailPageData } = $props();

	let drillAcwr = $state(false);
	const ZONE_CLASS: Record<string, string> = {
		적정: 'text-semantic-green',
		정상: 'text-semantic-green',
		저부하: 'text-semantic-amber',
		주의: 'text-semantic-amber',
		경계: 'text-semantic-amber',
		위험: 'text-semantic-red',
		저하: 'text-semantic-red'
	};
	function zoneClass(z: string): string {
		return ZONE_CLASS[z] ?? 'text-fg-secondary';
	}

	const DAY_KO = ['월', '화', '수', '목', '금', '토', '일'];

	function dayLabel(dateStr: string): string {
		const d = new Date(dateStr + 'T00:00:00');
		return DAY_KO[d.getDay() === 0 ? 6 : d.getDay() - 1];
	}


	// 행 상태는 서버(week_compliance)의 날짜별 유효 계획·결과 라벨만 렌더한다 — 프론트에 판정 규칙 없음
	const STATUS_CLS: Record<string, string> = {
		excellent: 'text-semantic-green',
		good: 'text-semantic-teal',
		neutral: 'text-fg-secondary',
		caution: 'text-semantic-amber',
		poor: 'text-semantic-red'
	};
	const dayByDate = $derived(new Map((data.plan?.week?.days ?? []).map((d) => [d.date, d])));

	function statusOf(w: PlannedWorkout): { text: string; cls: string } | null {
		const d = dayByDate.get(w.date);
		if (!d?.effective) return null;
		if (d.effective.id !== w.id) return { text: '대체됨', cls: 'text-fg-muted' };
		if (d.state === 'pre_plan') return { text: '계획 전', cls: 'text-fg-muted' };
		if (!d.status_label) return null;
		return { text: (d.label === 'on_target' ? '✓ ' : '') + d.status_label, cls: STATUS_CLS[d.status ?? 'neutral'] };
	}

	const today = new Date(Date.now() - new Date().getTimezoneOffset() * 60000).toISOString().slice(0, 10);
	const weekKm = $derived(data.plan?.compliance?.volume?.planned_km ?? null);

	function isAlternative(w: PlannedWorkout): boolean {
		const d = dayByDate.get(w.date);
		return !!d?.effective && d.effective.id !== w.id;
	}

</script>

<svelte:head><title>플랜 상세 · RunPulse</title></svelte:head>

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
				{weekProgressLabel(data.plan.week_index, data.plan.goal.plan_weeks)}
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

			{#if data.plan.compliance && data.plan.compliance.sessions.total > 0}
				{@const c = data.plan.compliance}
				<p class="mt-2 flex flex-wrap gap-x-3 text-xs text-fg-muted">
					<span>세션 <span class="font-mono font-medium text-fg-secondary">{c.sessions.done}/{c.sessions.total}일</span></span>
					{#if c.volume.pct != null}
						<span>볼륨 <span class="font-mono font-medium text-fg-secondary">{c.volume.actual_km}/{c.volume.planned_km}km {c.volume.pct}%</span></span>
					{/if}
					{#if c.quality.total > 0}
						<span>품질 세션 <span class="font-mono font-medium text-fg-secondary">{c.quality.done}/{c.quality.total}</span></span>
					{/if}
				</p>
			{/if}
		</div>

		<!-- 오늘 조정 제안·적용 (ADR-035) -->
		{#if data.adjustment?.adjustment}
			<AdjustmentCard
				initial={data.adjustment.state}
				initialAdj={data.adjustment.adjustment}
				via="plan"
				onChange={() => invalidateAll()}
			/>
		{/if}

		<!-- 이번 주 워크아웃 목록 -->
		<div class="border-b border-border-subtle px-4 py-3">
			<p class="mb-2 text-xs uppercase tracking-wide text-fg-muted">이번 주</p>
			{#if data.plan.workouts.length === 0}
				<p class="text-sm text-fg-muted">이번 주 워크아웃이 없습니다.</p>
			{:else}
				<ul class="divide-y divide-border-subtle">
					{#each data.plan.workouts as w (w.id)}
						{@const st = statusOf(w)}
						<li class="flex items-start" class:opacity-50={isAlternative(w)}>
							<a
								href="{base}/coach/plan/{data.plan.goal.id}/session/{w.date}"
								class="flex min-w-0 flex-1 items-start gap-3 py-2.5 hover:bg-surface-2"
							>
								<span class="w-6 shrink-0 text-center text-xs text-fg-muted"
									>{dayLabel(w.date)}</span
								>
								<div class="min-w-0 flex-1">
									<div class="flex items-center gap-2">
										<span class="text-sm font-medium">
											{workoutLabel(w.workout_type)}
										</span>
										{#if w.distance_km}
											<span class="text-xs text-fg-muted">{w.distance_km}km</span>
										{/if}
										{#if formatPaceRange(w.target_pace_min, w.target_pace_max)}
											<span class="text-xs text-fg-muted"
												>{formatPaceRange(w.target_pace_min, w.target_pace_max)}</span
											>
										{/if}
									</div>
									{#if w.description}
										<p class="mt-0.5 text-xs text-fg-secondary">{w.description}</p>
									{/if}
									<UserAdjustmentLine workout={w} />
								</div>
								{#if st}
									<span class="shrink-0 text-xs {st.cls}">{st.text}</span>
								{/if}
							</a>
							<RowActionButton
								workout={w}
								{today}
								via="plan"
								{weekKm}
								crsPending={w.date === today && ['proposed', 'accepted'].includes(data.adjustment?.state ?? '')}
								onChange={() => invalidateAll()}
							/>
						</li>
					{/each}
				</ul>
			{/if}
		</div>

		{#if data.adaptation && (data.adaptation.acwr || data.adaptation.hrv || data.adaptation.fatigue_avg)}
			<div class="border-b border-border-subtle px-4 py-3">
				<p class="mb-2 text-xs uppercase tracking-wide text-fg-muted">적응 상태</p>
				<ul class="flex flex-col gap-2 text-sm">
					{#if data.adaptation.acwr}
						{@const a = data.adaptation.acwr}
						<li>
							<button type="button" onclick={() => (drillAcwr = true)} class="flex w-full items-center gap-2 text-left hover:bg-surface-2">
								<span class="w-24 shrink-0 text-fg-secondary">ACWR</span>
								<span class="font-mono font-medium">{a.value.toFixed(2)}</span>
								<span class="text-xs {zoneClass(a.zone)}">● {a.zone}</span>
								<span class="ml-auto text-xs text-fg-muted">적정 0.8~1.3 ›</span>
							</button>
						</li>
					{/if}
					{#if data.adaptation.hrv}
						{@const h = data.adaptation.hrv}
						<li class="flex items-center gap-2">
							<span class="w-24 shrink-0 text-fg-secondary">HRV</span>
							<span class="font-mono font-medium">{Math.round(h.value)}ms</span>
							{#if h.delta_pct != null && h.zone}
								<span class="text-xs {zoneClass(h.zone)}">● 기준 {h.delta_pct > 0 ? '+' : ''}{h.delta_pct}% ({h.zone})</span>
							{/if}
						</li>
					{/if}
					{#if data.adaptation.fatigue_avg}
						{@const f = data.adaptation.fatigue_avg}
						<li class="flex items-center gap-2">
							<span class="w-24 shrink-0 text-fg-secondary">피로도 주간 평균</span>
							<span class="font-mono font-medium">{f.value.toFixed(1)} / 10</span>
							<span class="text-xs text-fg-muted">({f.n}회 입력)</span>
						</li>
					{/if}
				</ul>
			</div>
		{/if}
	{/if}
</div>

{#if drillAcwr && data.adaptation?.acwr}<MetricBreakdown slug="acwr" scopeType="daily" scopeId={data.adaptation.acwr.date} onClose={() => { drillAcwr = false; }} />{/if}
