<script lang="ts">
	// 03c-library.md 3-B — 활동 목록. sport/날짜/거리/검색 필터 + 페이지네이션.
	// 모바일: 2-row 레이아웃으로 페이스·심박 항상 표시.
	import type { ActivitiesPageData } from './+page';
	import { getActivities } from '$lib/api/library';
	import { ApiError } from '$lib/api/client';
	import { providerLabel, providerBadgeClass } from '$lib/provider';
	import { showSourceBadge } from '$lib/providerHint';
	import { formatDuration, formatPace } from '$lib/format';
	import { weekGroups, dayLabel } from '$lib/activityList';
	import RouteThumb from '$lib/components/RouteThumb.svelte';
	import { base } from '$app/paths';
	import type { ActivitySummary, ProviderKey } from '$lib/types';

	let { data }: { data: ActivitiesPageData } = $props();

	let activities = $state<ActivitySummary[]>(data.result?.activities ?? []);
	let total = $state(data.result?.total ?? 0);
	let hasMore = $state(data.result?.has_more ?? false);
	let errorMessage = $state(data.errorMessage);

	// 필터 상태 (기간 필터는 후속 — 네이티브 date input 제거)
	let filterSport = $state('');
	let filterSearch = $state('');
	let filterDistMin = $state('');
	let currentPage = $state(1);
	let loading = $state(false);

	const SPORTS = [
		['', '전체'],
		['running', '러닝'],
		['swimming', '수영'],
		['strength_training', '근력']
	] as const;
	const DISTS = [
		['', '전 거리'],
		['5', '5km+'],
		['10', '10km+'],
		['21.1', '하프+'],
		['42.2', '풀']
	] as const;

	function pick(kind: 'sport' | 'dist', value: string) {
		if (kind === 'sport') filterSport = value;
		else filterDistMin = value;
		applyFilters();
	}

	const groups = $derived(weekGroups(activities));
	const showBadge = $derived(showSourceBadge(activities.map((a) => a.source)));
	const maxKm = $derived(Math.max(1, ...groups.map((g) => g.km)));

	let searchTimer: ReturnType<typeof setTimeout> | undefined;
	// 요청 번호 — 검색을 빠르게 타이핑할 때 늦게 도착한 이전 응답이 최신 결과를 덮지 않게 무시한다.
	let reqSeq = 0;

	async function loadPage(page: number, append: boolean) {
		loading = true;
		errorMessage = null;
		const seq = ++reqSeq;
		try {
			const res = await getActivities({
				sport: filterSport || undefined,
				search: filterSearch || undefined,
				dist_min: filterDistMin ? Number(filterDistMin) : undefined,
				page,
				per_page: 20
			});
			if (seq !== reqSeq) return;
			if (append) {
				activities = [...activities, ...res.activities];
			} else {
				activities = res.activities;
			}
			total = res.total;
			hasMore = res.has_more;
			currentPage = page;
		} catch (e) {
			if (seq !== reqSeq) return;
			errorMessage = e instanceof ApiError ? e.message : '목록을 불러올 수 없습니다.';
		} finally {
			if (seq === reqSeq) loading = false;
		}
	}

	function applyFilters() {
		loadPage(1, false);
	}

	function onSearchInput() {
		clearTimeout(searchTimer);
		searchTimer = setTimeout(() => applyFilters(), 300);
	}

	function loadMore() {
		loadPage(currentPage + 1, true);
	}
</script>

<svelte:head><title>활동 목록 · RunPulse</title></svelte:head>

<!-- 헤더 -->
<div class="flex items-center gap-2 border-b border-border-subtle px-4 py-3">
	<a href="{base}/library" class="shrink-0 text-fg-muted" aria-label="Library 홈으로">←</a>
	<h1 class="text-base font-semibold">활동 목록</h1>
	{#if total > 0}
		<span class="ml-auto text-xs text-fg-muted">{total}건</span>
	{/if}
</div>

<div class="flex flex-col gap-0">
	<!-- 필터: 종목·거리 칩 + 검색 -->
	<div class="flex flex-col gap-2 border-b border-border-subtle px-4 py-3">
		<div class="flex flex-wrap gap-1.5" role="group" aria-label="종목">
			{#each SPORTS as [v, label] (v)}
				<button
					type="button"
					aria-pressed={filterSport === v}
					onclick={() => pick('sport', v)}
					class="rounded-full border px-3 py-1 text-xs {filterSport === v
						? 'border-semantic-teal bg-semantic-teal/15 text-fg-primary'
						: 'border-border-subtle text-fg-muted hover:text-fg-secondary'}">{label}</button
				>
			{/each}
		</div>
		<div class="flex flex-wrap gap-1.5" role="group" aria-label="거리">
			{#each DISTS as [v, label] (v)}
				<button
					type="button"
					aria-pressed={filterDistMin === v}
					onclick={() => pick('dist', v)}
					class="rounded-full border px-3 py-1 text-xs {filterDistMin === v
						? 'border-semantic-teal bg-semantic-teal/15 text-fg-primary'
						: 'border-border-subtle text-fg-muted hover:text-fg-secondary'}">{label}</button
				>
			{/each}
		</div>
		<input
			type="search"
			bind:value={filterSearch}
			oninput={onSearchInput}
			placeholder="활동 이름 검색"
			class="rounded-lg border border-border-subtle bg-surface-2 px-3 py-2 text-sm text-fg-primary placeholder:text-fg-muted"
			aria-label="활동 검색"
		/>
	</div>

	<!-- 목록 -->
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
	{:else}
		{#each groups as g, gi (g.key)}
			{#if gi === 0 || groups[gi - 1].year !== g.year}
				<p class="px-4 pt-4 text-xs font-medium text-fg-muted">{g.year}</p>
			{/if}
			<section aria-label="{g.label} 주">
				<div class="flex flex-col gap-1 bg-surface-1 px-4 pb-1 pt-4">
					<div class="flex items-baseline justify-between">
						<span class="text-xs font-medium text-fg-secondary">{g.label}</span>
						<span class="font-mono text-xs text-fg-muted"
							>{g.runs}회 · {g.km.toFixed(1)}km{g.seconds > 0 ? ` · ${formatDuration(g.seconds)}` : ''}</span
						>
					</div>
					<div class="h-1 rounded bg-surface-3">
						<div class="h-1 rounded bg-semantic-teal" style="width:{Math.max(g.km > 0 ? 3 : 0, (g.km / maxKm) * 100)}%"></div>
					</div>
				</div>
				<ul class="divide-y divide-border-subtle">
					{#each g.items as act (act.id)}
						<li>
							<a
								href="{base}/library/{act.id}"
								class="flex items-center gap-3 px-4 py-2.5 hover:bg-surface-2 active:bg-surface-3"
							>
								<RouteThumb route={act.route} />
								<div class="flex min-w-0 flex-1 flex-col gap-0.5">
									<span class="truncate text-sm font-medium">{act.name}</span>
									<div class="flex flex-wrap items-center gap-x-2 text-xs text-fg-muted">
										<span>{dayLabel(act.start_time)}</span>
										{#if act.avg_pace_sec_km != null}<span class="font-mono">{formatPace(act.avg_pace_sec_km)}</span>{/if}
										{#if act.avg_hr != null}<span class="font-mono">HR {act.avg_hr}</span>{/if}
										{#if showBadge}<span
											class="rounded px-1 py-px text-[9px] text-white {providerBadgeClass(act.source as ProviderKey)}"
											>{providerLabel(act.source as ProviderKey)}</span
										>{/if}
									</div>
								</div>
								<div class="flex shrink-0 flex-col items-end">
									<span class="font-mono text-lg font-bold leading-tight"
										>{act.distance_m != null ? (act.distance_m / 1000).toFixed(1) : '—'}<span class="text-[10px] font-normal text-fg-muted"> km</span></span
									>
									<span class="font-mono text-xs text-fg-muted">{act.duration_sec != null ? formatDuration(act.duration_sec) : '—'}</span>
								</div>
							</a>
						</li>
					{/each}
				</ul>
			</section>
		{/each}

		{#if hasMore}
			<div class="flex justify-center px-4 py-4">
				<button
					type="button"
					onclick={loadMore}
					disabled={loading}
					class="rounded-lg border border-border-subtle bg-surface-2 px-6 py-2 text-sm text-fg-secondary disabled:opacity-50"
				>
					{loading ? '불러오는 중…' : '더 불러오기'}
				</button>
			</div>
		{/if}

		{#if errorMessage}
			<p class="px-4 py-2 text-xs text-semantic-red">{errorMessage}</p>
		{/if}
	{/if}

	{#if loading && activities.length === 0}
		<div class="flex justify-center py-16">
			<p class="text-sm text-fg-muted">불러오는 중…</p>
		</div>
	{/if}
</div>
