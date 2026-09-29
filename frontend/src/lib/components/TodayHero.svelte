<script lang="ts">
	// B1 히어로 — briefing.state(7종)별 오늘의 한 줄 권고. 판정·문구 재료는 서버, 여기서는 조립만.
	import { base } from '$app/paths';
	import type { TodayBriefing, BriefingStateFields, RaceHubGoal, ProviderKey } from '$lib/types';
	import EvidenceQuote from '$lib/components/EvidenceQuote.svelte';
	import ErrorState from '$lib/components/ErrorState.svelte';
	import { heroView, caveatText } from '$lib/todayHero';
	import { providerLabel } from '$lib/provider';
	import { planNewHref } from '$lib/planPrefill';
	import { adaptEvidence, type DrillTarget } from '$lib/evidence';

	let { briefing, goal = null, onEvidence, onRetry }: {
		briefing: TodayBriefing & Partial<BriefingStateFields>;
		goal?: RaceHubGoal | null;
		onEvidence: (t: DrillTarget) => void;
		onRetry?: () => void;
	} = $props();

	const view = $derived(
		briefing.state
			? heroView(briefing as BriefingStateFields)
			: null
	);
	// 판정(state)도 서술(headline)도 없으면 서버가 권고를 못 만든 것 — 빈 카드 대신 오류+재시도(design §6).
	const broken = $derived(!briefing.state && !briefing.headline);
	const planHref = $derived(goal ? planNewHref(base, goal) : `${base}/coach/plan/new`);
	const toneClass = $derived(
		view?.tone === 'caution' ? 'border-semantic-amber/50' : view?.tone === 'done' ? 'border-semantic-green/40' : 'border-border-subtle'
	);
</script>

<section class="flex min-h-[260px] flex-col gap-3 rounded-xl border bg-surface-2 p-4 {toneClass}" aria-label="오늘의 권고">
	{#if broken}
		<ErrorState message="오늘 권고를 불러오지 못했어요" {onRetry} />
	{/if}
	{#if view}
		<h1 class="text-xl font-semibold leading-snug">{view.headline}</h1>
		{#if view.sub}<p class="text-sm text-fg-secondary">{view.sub}</p>{/if}
		{#if view.adjustment}
			<p class="rounded-md bg-semantic-amber/10 px-2.5 py-1.5 text-sm text-semantic-amber" data-testid="hero-adjustment">{view.adjustment}</p>
		{/if}
		{#if view.cta === 'plan_new'}
			<a href={planHref} class="self-start rounded-md bg-surface-3 px-3 py-1.5 text-sm font-medium hover:bg-border-subtle">계획 만들기 ›</a>
		{:else if view.cta === 'session'}
			<a href="{base}/coach/plan" class="self-start text-sm text-fg-secondary hover:text-fg-primary">세션 상세 ›</a>
		{:else if view.cta === 'activity' && briefing.today_result}
			<a href="{base}/library/{briefing.today_result.activity_id}" class="self-start text-sm text-fg-secondary hover:text-fg-primary">활동 보기 ›</a>
		{/if}
		{#if (briefing.state === 'done' || briefing.state === 'extra' || briefing.state === 'rest') && briefing.session?.date}
			<p class="text-xs text-fg-muted" data-testid="hero-next">
				다음 · {briefing.session.date.slice(5).replace('-', '/')} {briefing.session.title}
			</p>
		{/if}
	{/if}

	{#if briefing.headline}
		<p class="text-sm leading-relaxed text-fg-primary">{briefing.headline}</p>
	{/if}
	{#if briefing.evidence.length > 0}
		<div class="flex flex-wrap gap-2">
			{#each briefing.evidence as ev}
				<EvidenceQuote {...adaptEvidence(ev, onEvidence)} />
			{/each}
		</div>
	{/if}

	{#each briefing.caveats ?? [] as c}
		<p class="text-xs text-fg-muted" role="note">
			{caveatText(c, (k) => providerLabel(k as ProviderKey))}
		</p>
	{/each}
</section>
