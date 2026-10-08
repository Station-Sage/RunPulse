<script lang="ts">
	// 03e-coach.md 5-E — 프로그램 비교: 템플릿 카드 3개, 선택 시 플랜 생성.
	import { goto } from '$app/navigation';
	import { base } from '$app/paths';
	import { createPlan } from '$lib/api/plan';
	import ScenarioCompareTable from '$lib/components/plan/ScenarioCompareTable.svelte';
	import type { ComparePlanData } from './+page';

	let { data }: { data: ComparePlanData } = $props();

	let loading = $state<number | null>(null);
	let error = $state<string | null>(null);
	// 생성 후 경고가 있으면 이동 전에 보여 준다(설계 §5.2-5 준비도 경고)
	let created = $state<{ goalId: number; warnings: string[] } | null>(null);

	async function handleSelect(weeks: number) {
		loading = weeks;
		error = null;
		try {
			const res = await createPlan({
				distance_km: data.distanceKm,
				race_date: data.raceDate,
				weeks,
				...(data.targetTimeSec != null ? { target_time_sec: data.targetTimeSec } : {}),
				...(data.recentWeeklyKm != null ? { recent_weekly_km: data.recentWeeklyKm } : {}),
				...(data.recentLongKm != null ? { recent_long_km: data.recentLongKm } : {})
			});
			if (res.warnings.length > 0) {
				created = { goalId: res.goal_id, warnings: res.warnings };
				return;
			}
			await goto(`${base}/coach/plan/${res.goal_id}`);
		} catch {
			error = '플랜 생성에 실패했습니다. 다시 시도해주세요.';
		} finally {
			loading = null;
		}
	}
</script>

<svelte:head><title>플랜 비교 · RunPulse</title></svelte:head>

<div class="flex flex-col">
	<div class="border-b border-border-subtle px-4 py-3">
		<div class="mb-1">
			<a href="{base}/coach/plan/new" class="text-xs text-fg-muted hover:underline">← 새 프로그램</a>
		</div>
		<h1 class="text-base font-semibold">프로그램 비교</h1>
		<p class="text-xs text-fg-muted">단계 3/3 — 원하는 프로그램을 선택하세요</p>
	</div>

	<div class="flex flex-col gap-4 px-4 py-5">
		{#if created}
			<div class="rounded-xl border border-semantic-amber bg-surface-2 p-4" role="alert" data-testid="plan-warnings">
				<p class="mb-2 text-sm font-semibold text-fg-primary">프로그램을 만들었어요. 확인할 점이 있어요</p>
				<ul class="mb-3 list-disc pl-4 text-xs text-fg-secondary">
					{#each created.warnings as w}
						<li>{w}</li>
					{/each}
				</ul>
				<a
					href="{base}/coach/plan/{created.goalId}"
					class="inline-block rounded-lg bg-fg-primary px-4 py-2 text-sm font-medium text-surface-1"
				>
					계획 보기 →
				</a>
			</div>
		{/if}
		<ScenarioCompareTable
			templates={data.templates}
			{loading}
			disabled={loading != null || created != null}
			onselect={handleSelect}
		/>

		{#if error}
			<p class="text-sm text-semantic-red">{error}</p>
		{/if}
	</div>
</div>
