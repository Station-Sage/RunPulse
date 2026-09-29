<script lang="ts">
	// B4/B5 — 계획·조정은 스트리밍이라 도착 전엔 주간 스트립(즉시 표시 가능)+스켈레톤, 실패는 블록 단위 재시도.
	import type { NextSessionData } from '../../routes/today/+page';
	import type { RaceHubData, WeekCompliance } from '$lib/types';
	import NextSessionCard from '$lib/components/NextSessionCard.svelte';
	import WeekStrip from '$lib/components/WeekStrip.svelte';
	import Skeleton from '$lib/components/Skeleton.svelte';
	import ErrorState from '$lib/components/ErrorState.svelte';

	let { nextSession, raceHub, week, today, onRetry }: {
		nextSession: Promise<NextSessionData>;
		raceHub: Promise<RaceHubData | null>;
		week: WeekCompliance | null | undefined;
		today: string;
		onRetry: () => void;
	} = $props();

	// 플랜이 없을 때 대회 목표 안내(planNew 링크)에 raceHub.goal이 필요하다
	const ready = $derived(Promise.all([nextSession, raceHub]));
</script>

{#await ready}
	<WeekStrip {week} />
	<div class="flex flex-col gap-2" aria-busy="true"><Skeleton class="w-24" /><Skeleton kind="chart" class="min-h-[88px]" /></div>
{:then [n, hub]}
	<WeekStrip {week} planId={n.plan?.goal.id ?? null} />
	<div class="flex flex-col gap-2 border-t border-border-subtle pt-3">
		<p class="text-xs uppercase tracking-wide text-fg-muted">다음 세션</p>
		<NextSessionCard plan={n.plan} adjustment={n.adjustment} {today} raceGoal={hub?.goal ?? null} />
	</div>
{:catch}
	<WeekStrip {week} />
	<ErrorState compact message="다음 세션을 불러오지 못했어요" {onRetry} />
{/await}
