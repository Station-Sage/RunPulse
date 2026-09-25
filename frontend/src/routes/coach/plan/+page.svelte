<script lang="ts">
	// 03e-coach.md 5-C — 플랜 없음 화면.
	import type { PlanGatewayData } from './+page';
	import { base } from '$app/paths';
	import { planNewHref, roadmapLabel } from '$lib/planPrefill';

	let { data }: { data: PlanGatewayData } = $props();
</script>

<svelte:head><title>훈련 플랜 · RunPulse</title></svelte:head>

<div class="flex flex-col items-center justify-center gap-6 px-4 py-16 text-center">
	<div>
		{#if data.goal}
			<p class="text-base font-medium">{data.goal.name} D-{data.goal.days_left}</p>
		{/if}
		<p class="text-base text-fg-secondary">
			목표 레이스를 입력하면 맞춤 프로그램을 만들어드립니다.
		</p>
		{#if data.ctlCurrent != null}
			<p class="mt-2 text-sm text-fg-muted">
				현재 피트니스 수준: CTL {Math.round(data.ctlCurrent)} (분석 완료)
			</p>
		{/if}
	</div>

	<a
		href={data.goal ? planNewHref(base, data.goal) : `${base}/coach/plan/new`}
		class="rounded-lg bg-fg-primary px-6 py-3 text-sm font-medium text-surface-1"
	>
		{data.goal ? roadmapLabel(data.goal.days_left) + ' →' : '새 프로그램 만들기 →'}
	</a>
</div>
