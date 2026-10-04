<script lang="ts">
	// 03c-library.md 3-B / 20-library-activities §2-3 — 활동 목록. 필터(URL 동기화)·월 헤더·주 헤더(12주 평균 눈금)·
	// 연-월 스크러버·무한 스크롤. 정렬이 최신순이 아니면 주 그룹 없이 평면 목록.
	import type { ActivitiesPageData } from './+page';
	import { replaceState } from '$app/navigation';
	import { page as pageState } from '$app/state';
	import { tick, untrack } from 'svelte';
	import { presetRange, monthRange, recentMonths, serializeFilters, type PeriodPreset } from '$lib/activityFilters';
	import { getActivities, getActivityFacets, getActivitySummary } from '$lib/api/library';
	import { ApiError } from '$lib/api/client';
	import { formatDuration } from '$lib/format';
	import { weekGroups } from '$lib/activityList';
	import { toApiFilters, jumpLoadCount, weekMap, shiftMonth, PER_PAGE } from '$lib/activityListQuery';
	import { activityFlag, medianPace } from '$lib/activityFlags';
	import ActivityRow from '$lib/components/ActivityRow.svelte';
	import ActivityFilters from '$lib/components/activities/ActivityFilters.svelte';
	import MonthHeader from '$lib/components/activities/MonthHeader.svelte';
	import YearMonthScrubber from '$lib/components/activities/YearMonthScrubber.svelte';
	import type { ActivitySummary, ActivityFacets, ActivityListSummary } from '$lib/types';

	let { data }: { data: ActivitiesPageData } = $props();
	const seed = untrack(() => data);

	let activities = $state<ActivitySummary[]>(seed.result?.activities ?? []);
	let total = $state(seed.result?.total ?? 0);
	let hasMore = $state(seed.result?.has_more ?? false);
	let facets = $state<ActivityFacets | null>(seed.facets);
	let summary = $state<ActivityListSummary | null>(seed.summary);
	let errorMessage = $state(seed.errorMessage);
	let period = $state<{ from?: string; to?: string }>({ from: seed.filters.from, to: seed.filters.to });
	let preset = $state<PeriodPreset | null>(seed.filters.preset);
	let month = $state(seed.filters.month);
	let sport = $state(seed.filters.sport);
	let type = $state(seed.filters.type);
	let sort = $state(seed.filters.sort);
	let distMin = $state(seed.filters.distMin);
	let q = $state(seed.filters.q);
	let at = $state('');
	let loading = $state(false);
	let sentinel: HTMLElement | undefined = $state();

	const months = recentMonths(seed.today, 12);
	const cur = () => ({ preset, month, from: period.from, to: period.to, sport, type, sort, distMin, q });
	const chronological = $derived(!sort || sort === 'date');
	const groups = $derived(weekGroups(activities));
	const weeks = $derived(weekMap(summary?.weeks));
	const median = $derived(medianPace(activities));
	const avg = $derived(summary?.avg_week_km_12w ?? null);
	const maxKm = $derived(Math.max(1, avg ?? 0, ...groups.map((g) => weeks.get(g.key)?.km ?? g.km)));
	const lastMonth = $derived(facets?.months[0]?.month ?? '');

	function syncUrl() {
		const u = new URL(pageState.url);
		const qs = serializeFilters(cur());
		u.search = at ? `${qs}${qs ? '&' : '?'}at=${at}` : qs;
		replaceState(u, pageState.state);
	}

	// 요청 번호 — 늦게 도착한 이전 응답이 최신 결과를 덮지 않게 무시한다.
	let reqSeq = 0;

	async function reload(perPage = PER_PAGE) {
		const seq = ++reqSeq;
		loading = true;
		errorMessage = null;
		const api = toApiFilters(cur());
		try {
			const [res, f, s] = await Promise.all([
				getActivities({ ...api, page: 1, per_page: perPage }),
				getActivityFacets(api).catch(() => null),
				getActivitySummary(api).catch(() => null)
			]);
			if (seq !== reqSeq) return false;
			activities = res.activities;
			total = res.total;
			hasMore = res.has_more;
			facets = f;
			summary = s;
			return true;
		} catch (e) {
			if (seq === reqSeq) errorMessage = e instanceof ApiError ? e.message : '목록을 불러올 수 없습니다.';
			return false;
		} finally {
			if (seq === reqSeq) loading = false;
		}
	}

	async function applyFilters() {
		at = '';
		syncUrl();
		window.scrollTo({ top: 0 });
		await reload();
	}

	async function loadMore() {
		if (loading || !hasMore) return;
		const seq = ++reqSeq;
		loading = true;
		try {
			const res = await getActivities({ ...toApiFilters(cur()), page: Math.floor(activities.length / PER_PAGE) + 1, per_page: PER_PAGE });
			if (seq !== reqSeq) return;
			activities = [...activities, ...res.activities];
			total = res.total;
			hasMore = res.has_more;
		} catch (e) {
			if (seq === reqSeq) errorMessage = e instanceof ApiError ? e.message : '목록을 불러올 수 없습니다.';
		} finally {
			if (seq === reqSeq) loading = false;
		}
	}

	$effect(() => {
		if (!sentinel) return;
		const io = new IntersectionObserver((e) => e[0].isIntersecting && loadMore(), { rootMargin: '600px' });
		io.observe(sentinel);
		return () => io.disconnect();
	});

	function pickPreset(p: PeriodPreset) {
		preset = p;
		month = '';
		period = presetRange(p, seed.today);
		applyFilters();
	}

	function pickMonth(m: string) {
		if (!m) return pickPreset('all');
		preset = null;
		month = m;
		period = monthRange(m);
		applyFilters();
	}

	function pick(kind: 'sport' | 'type' | 'dist' | 'sort', value: string) {
		if (kind === 'sport') {
			sport = value;
			type = '';
		} else if (kind === 'type') type = value;
		else if (kind === 'dist') distMin = value;
		else sort = value;
		applyFilters();
	}

	let searchTimer: ReturnType<typeof setTimeout> | undefined;
	const onSearch = () => {
		clearTimeout(searchTimer);
		searchTimer = setTimeout(applyFilters, 300);
	};

	async function jumpTo(target: string) {
		const need = jumpLoadCount(facets?.months ?? [], target);
		if (need > activities.length && !(await reload(need))) return;
		await tick();
		const el = [...document.querySelectorAll<HTMLElement>('[data-date]')].find((n) => (n.dataset.date ?? '').slice(0, 7) <= target);
		el?.scrollIntoView({ block: 'start' });
		at = target;
		syncUrl();
	}

	let raf = 0;
	function onScroll() {
		cancelAnimationFrame(raf);
		raf = requestAnimationFrame(() => {
			const el = [...document.querySelectorAll<HTMLElement>('[data-date]')].find((n) => n.getBoundingClientRect().bottom > 120);
			const m = el?.dataset.date?.slice(0, 7);
			if (m && m !== at) at = m;
		});
	}

	export const snapshot = {
		capture: () => ({ activities, total, hasMore, facets, summary, y: window.scrollY }),
		restore: async (v: { activities: ActivitySummary[]; total: number; hasMore: boolean; facets: ActivityFacets | null; summary: ActivityListSummary | null; y: number }) => {
			({ activities, total, hasMore, facets, summary } = v);
			await tick();
			window.scrollTo({ top: v.y });
		}
	};
</script>

<svelte:head><title>활동 목록 · RunPulse</title></svelte:head>
<svelte:window onscroll={onScroll} />

<div class="flex items-center gap-2 border-b border-border-subtle px-4 py-3">
	<h1 class="text-base font-semibold">활동 목록</h1>
	{#if total > 0}
		<span class="ml-auto text-xs text-fg-muted" data-testid="shown-count">표시 {activities.length} / {total}</span>
	{/if}
</div>

<div class="flex flex-col gap-0">
	<ActivityFilters {facets} {preset} {month} {months} {sport} {type} {distMin} {sort} bind:q onpreset={pickPreset} onmonth={pickMonth} onpick={pick} onsearch={onSearch} />
	{#if preset === null && !month && period.from}
		<p class="px-4 pt-2 text-xs text-fg-muted">{period.from} ~ {period.to ?? ''}</p>
	{/if}

	{#if month}
		<MonthHeader {month} summary={summary?.month} canNext={!!lastMonth && month < lastMonth} onshift={(d) => pickMonth(shiftMonth(month, d))} onclear={() => pickPreset('all')} />
	{/if}

	{#if errorMessage && activities.length === 0}
		<div class="flex flex-col items-center gap-2 px-4 py-16 text-center">
			<p class="text-lg text-fg-secondary">활동을 불러올 수 없습니다</p>
			<p class="text-xs text-fg-muted">{errorMessage}</p>
		</div>
	{:else if activities.length === 0 && !loading}
		<div class="flex flex-col items-center gap-2 px-4 py-16 text-center">
			<p class="text-lg text-fg-secondary">활동이 없습니다</p>
			<p class="text-sm text-fg-muted">필터를 조정하거나 데이터를 동기화해 주세요.</p>
		</div>
	{:else if chronological}
		{#each groups as g, gi (g.key)}
			{@const w = weeks.get(g.key)}
			{@const km = w?.km ?? g.km}
			{#if gi === 0 || groups[gi - 1].year !== g.year}
				<p class="sticky top-0 z-10 bg-surface-1 px-4 pt-4 text-xs font-medium text-fg-muted">{g.year}</p>
			{/if}
			<section aria-label="{g.label} 주">
				<div class="flex flex-col gap-1 bg-surface-1 px-4 pb-1 pt-4" data-testid="week-header">
					<div class="flex items-baseline justify-between">
						<span class="text-xs font-medium text-fg-secondary">{g.label}{#if w?.inRangeOnly} <span class="text-fg-muted">({g.items[0].start_time.slice(5, 7).replace(/^0/, '')}월분만)</span>{/if}</span>
						<span class="font-mono text-xs text-fg-muted">{w?.n ?? g.runs}회 · {km.toFixed(1)}km{(w?.sec ?? g.seconds) > 0 ? ` · ${formatDuration(w?.sec ?? g.seconds)}` : ''}</span>
					</div>
					<div class="relative h-1 rounded bg-surface-3">
						<div class="h-1 rounded bg-semantic-teal" style="width:{Math.max(km > 0 ? 3 : 0, (km / maxKm) * 100)}%"></div>
						{#if avg}<div class="absolute -top-0.5 h-2 w-px bg-fg-muted" style="left:{(avg / maxKm) * 100}%" title="최근 12주 평균 {avg}km"></div>{/if}
					</div>
				</div>
				<ul class="divide-y divide-border-subtle">
					{#each g.items as act (act.id)}
						<li data-date={act.start_time}><ActivityRow {act} from="list" flag={activityFlag(act, median)} /></li>
					{/each}
				</ul>
			</section>
		{/each}
	{:else}
		<ul class="divide-y divide-border-subtle">
			{#each activities as act (act.id)}
				<li data-date={act.start_time}><ActivityRow {act} from="list" flag={activityFlag(act, median)} /></li>
			{/each}
		</ul>
	{/if}

	{#if hasMore}
		<div bind:this={sentinel} class="flex justify-center px-4 py-6">
			<button type="button" onclick={loadMore} disabled={loading} class="rounded-lg border border-border-subtle bg-surface-2 px-6 py-2 text-sm text-fg-secondary disabled:opacity-50">
				{loading ? '불러오는 중…' : '더 불러오기'}
			</button>
		</div>
	{:else if activities.length > 0}
		<p class="px-4 py-6 text-center text-xs text-fg-muted">전체 {total}건을 모두 불러왔어요</p>
	{/if}
	{#if errorMessage && activities.length > 0}<p class="px-4 py-2 text-xs text-semantic-red">{errorMessage}</p>{/if}
	{#if loading && activities.length === 0}<div class="flex justify-center py-16"><p class="text-sm text-fg-muted">불러오는 중…</p></div>{/if}
</div>

{#if chronological && !month}
	<YearMonthScrubber months={facets?.months ?? []} current={at} onjump={jumpTo} />
{/if}
