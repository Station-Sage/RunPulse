<script lang="ts">
	// 대회 캘린더 — 확인 필요 / 다가오는 / 지난 / 취소됨 구역과 대회 추가·상세·플랜 반영 시트 (RC-d).
	import { base } from '$app/paths';
	import { invalidate } from '$app/navigation';
	import ErrorState from '$lib/components/ErrorState.svelte';
	import Toast from '$lib/components/Toast.svelte';
	import RaceEntrySheet from '$lib/components/RaceEntrySheet.svelte';
	import RaceDetailSheet from '$lib/components/RaceDetailSheet.svelte';
	import RacePlanPrompt from '$lib/components/RacePlanPrompt.svelte';
	import type { RaceRow } from '$lib/api/raceCalendar';
	import { chipOf, dDayLabel, goalLine, kmLabel } from '$lib/raceCalendarView';
	import type { RaceCalendarPageData } from './+page';

	let { data }: { data: RaceCalendarPageData } = $props();
	const z = $derived(data.zones);

	type Sheet = null | { kind: 'entry'; race: RaceRow | null } | { kind: 'detail'; race: RaceRow; review: boolean } | { kind: 'plan'; race: RaceRow };
	let sheet = $state<Sheet>(null);
	let showCancelled = $state(false);
	let toast = $state<string | null>(null);

	const refresh = () => invalidate('app:race-calendar');
	function done(message: string) {
		sheet = null;
		toast = message;
		refresh();
	}
	function saved(r: RaceRow, created: boolean) {
		const ask = created && r.status === 'planned' && r.priority !== 'A' && r.adapt_choice === 'unasked';
		toast = created ? `${r.name}을 추가했어요` : `${r.name}을 수정했어요`;
		sheet = ask ? { kind: 'plan', race: r } : null;
		refresh();
	}
	const open = (race: RaceRow, review = false) => (sheet = { kind: 'detail', race, review });
</script>

{#snippet row(r: RaceRow, review: boolean)}
	<li>
		<button type="button" class="flex min-h-11 w-full items-center justify-between gap-2 min-h-11 rounded-lg border border-border-subtle bg-surface-2 px-3 py-2 text-left text-sm hover:bg-surface-3 focus-visible:outline focus-visible:outline-2 focus-visible:outline-semantic-teal" onclick={() => open(r, review)}>
			<span class="min-w-0">
				<span class="block truncate text-fg-primary"><span class="mr-1 text-xs text-fg-muted">{r.priority}</span>{r.name}</span>
				<span class="block text-xs text-fg-secondary">{r.race_date}{review || !z ? '' : ` · ${dDayLabel(r.race_date, z.today)}`} · {kmLabel(r.distance_km)}{goalLine(r) ? ` · ${goalLine(r)}` : ''}</span>
			</span>
			<span class="shrink-0 rounded-full bg-surface-3 px-2 py-0.5 text-xs text-fg-secondary">{review ? '확인 필요' : chipOf(r, r.id === z?.goal_race_id)}</span>
		</button>
	</li>
{/snippet}

<div class="space-y-4 p-4">
	<header class="flex items-center justify-between gap-2">
		<a href="{base}/today/race" class="flex min-h-11 min-w-11 items-center text-fg-secondary" aria-label="레이스 허브로">‹</a>
		<h1 class="flex-1 text-lg font-semibold text-fg-primary">대회 캘린더</h1>
		<button type="button" class="min-h-11 rounded-lg bg-semantic-teal px-3 text-sm text-fg-on-accent focus-visible:outline focus-visible:outline-2 focus-visible:outline-semantic-teal" onclick={() => (sheet = { kind: 'entry', race: null })}>대회 추가</button>
	</header>

	{#if data.failed || !z}
		<ErrorState onRetry={refresh} />
	{:else}
		{#if z.needs_review.length}
			<section class="space-y-2" aria-label="확인 필요"><h2 class="text-sm font-medium text-semantic-amber">확인 필요 {z.needs_review.length}</h2><ul class="space-y-2">{#each z.needs_review as r (r.id)}{@render row(r, true)}{/each}</ul></section>
		{/if}
		<section class="space-y-2" aria-label="다가오는 대회">
			<h2 class="text-sm font-medium text-fg-primary">다가오는 대회</h2>
			{#if z.upcoming.length}<ul class="space-y-2">{#each z.upcoming as r (r.id)}{@render row(r, false)}{/each}</ul>
			{:else}<p class="rounded-lg border border-dashed border-border-subtle p-4 text-sm text-fg-muted">예정된 대회가 없어요. 대회를 추가하면 훈련 계획과 예측에 반영할 수 있어요.</p>{/if}
		</section>
		{#if z.past.length}
			<section class="space-y-2" aria-label="지난 대회"><h2 class="text-sm font-medium text-fg-primary">지난 대회</h2><ul class="space-y-2">{#each z.past as r (r.id)}{@render row(r, false)}{/each}</ul></section>
		{/if}
		{#if z.cancelled.length}
			<section class="space-y-2" aria-label="취소된 대회">
				<button type="button" class="flex min-h-11 w-full items-center justify-between text-sm font-medium text-fg-secondary" aria-expanded={showCancelled} onclick={() => (showCancelled = !showCancelled)}>
					<span>취소됨 {z.cancelled.length}</span><span>{showCancelled ? '▾' : '▸'}</span>
				</button>
				{#if showCancelled}<ul class="space-y-2">{#each z.cancelled as r (r.id)}{@render row(r, false)}{/each}</ul>{/if}
			</section>
		{/if}
	{/if}
</div>

{#if sheet?.kind === 'entry'}
	<RaceEntrySheet race={sheet.race} today={z?.today ?? ''} onClose={() => (sheet = null)} onSaved={saved} />
{:else if sheet?.kind === 'detail'}
	{@const s = sheet}
	<RaceDetailSheet race={s.race} today={z?.today ?? ''} goalLinked={s.race.id === z?.goal_race_id} needsReview={s.review} onClose={() => (sheet = null)}
		onEdit={() => (sheet = { kind: 'entry', race: s.race })} onPlan={() => (sheet = { kind: 'plan', race: s.race })} onChanged={done} />
{:else if sheet?.kind === 'plan'}
	<RacePlanPrompt race={sheet.race} onClose={() => (sheet = null)} onDone={(r) => done(`${r.name} 플랜 설정을 저장했어요`)} />
{/if}
<Toast open={toast !== null} message={toast ?? ''} onDismiss={() => (toast = null)} />
