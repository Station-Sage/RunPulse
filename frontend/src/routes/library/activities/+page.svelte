<script lang="ts">
	// 03c-library.md 3-B — 활동 목록. sport/날짜/거리/검색 필터 + 페이지네이션.
	// 모바일: 2-row 레이아웃으로 페이스·심박 항상 표시.
	import type { ActivitiesPageData } from './+page';
	import { getActivities } from '$lib/api/library';
	import { ApiError } from '$lib/api/client';
	import { providerLabel, providerBadgeClass } from '$lib/provider';
	import { formatDistance, formatDuration, formatPace, formatDate } from '$lib/format';
	import { base } from '$app/paths';
	import type { ActivitySummary, ProviderKey } from '$lib/types';

	let { data }: { data: ActivitiesPageData } = $props();

	let activities = $state<ActivitySummary[]>(data.result?.activities ?? []);
	let total = $state(data.result?.total ?? 0);
	let hasMore = $state(data.result?.has_more ?? false);
	let errorMessage = $state(data.errorMessage);

	// 필터 상태
	let filterSport = $state('');
	let filterFrom = $state('');
	let filterTo = $state('');
	let filterSearch = $state('');
	let filterDistMin = $state('');
	let currentPage = $state(1);
	let loading = $state(false);

	let searchTimer: ReturnType<typeof setTimeout> | undefined;

	async function loadPage(page: number, append: boolean) {
		loading = true;
		errorMessage = null;
		try {
			const res = await getActivities({
				sport: filterSport || undefined,
				from: filterFrom || undefined,
				to: filterTo || undefined,
				search: filterSearch || undefined,
				dist_min: filterDistMin ? Number(filterDistMin) : undefined,
				page,
				per_page: 20
			});
			if (append) {
				activities = [...activities, ...res.activities];
			} else {
				activities = res.activities;
			}
			total = res.total;
			hasMore = res.has_more;
			currentPage = page;
		} catch (e) {
			errorMessage = e instanceof ApiError ? e.message : '목록을 불러올 수 없습니다.';
		} finally {
			loading = false;
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

<!-- 헤더 -->
<div class="flex items-center gap-2 border-b border-border-subtle px-4 py-3">
	<a href="{base}/library" class="shrink-0 text-fg-muted" aria-label="Library 홈으로">←</a>
	<h1 class="text-base font-semibold">활동 목록</h1>
	{#if total > 0}
		<span class="ml-auto text-xs text-fg-muted">{total}건</span>
	{/if}
</div>

<div class="flex flex-col gap-0">
	<!-- 필터 바 -->
	<div class="flex flex-wrap items-center gap-2 border-b border-border-subtle px-4 py-3">
		<select
			bind:value={filterSport}
			onchange={applyFilters}
			class="rounded border border-border-subtle bg-surface-2 px-2 py-1 text-sm text-fg-primary"
			aria-label="종목 필터"
		>
			<option value="">모든 종목</option>
			<option value="running">러닝</option>
			<option value="cycling">사이클</option>
			<option value="swimming">수영</option>
			<option value="strength_training">근력</option>
		</select>

		<input
			type="date"
			bind:value={filterFrom}
			onchange={applyFilters}
			class="rounded border border-border-subtle bg-surface-2 px-2 py-1 text-sm text-fg-primary"
			aria-label="시작 날짜"
		/>
		<span class="text-xs text-fg-muted">~</span>
		<input
			type="date"
			bind:value={filterTo}
			onchange={applyFilters}
			class="rounded border border-border-subtle bg-surface-2 px-2 py-1 text-sm text-fg-primary"
			aria-label="종료 날짜"
		/>

		<select
			bind:value={filterDistMin}
			onchange={applyFilters}
			class="rounded border border-border-subtle bg-surface-2 px-2 py-1 text-sm text-fg-primary"
			aria-label="거리 필터"
		>
			<option value="">모든 거리</option>
			<option value="5">5km+</option>
			<option value="10">10km+</option>
			<option value="21.1">하프(21km+)</option>
			<option value="42.2">마라톤(42km+)</option>
		</select>

		<input
			type="search"
			bind:value={filterSearch}
			oninput={onSearchInput}
			placeholder="검색..."
			class="min-w-[8rem] flex-1 rounded border border-border-subtle bg-surface-2 px-2 py-1 text-sm text-fg-primary placeholder:text-fg-muted"
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
		<ul class="divide-y divide-border-subtle">
			{#each activities as act (act.id)}
				<li>
					<a
						href="{base}/library/{act.id}"
						class="flex flex-col gap-0.5 px-4 py-3 hover:bg-surface-2 active:bg-surface-3"
					>
						<!-- 이름 + 뱃지 + 화살표 -->
						<div class="flex items-center gap-2">
							<span class="min-w-0 flex-1 truncate text-sm font-medium">{act.name}</span>
							<span
								class="shrink-0 rounded px-1.5 py-0.5 text-[10px] text-white {providerBadgeClass(
									act.source as ProviderKey
								)}"
							>
								{providerLabel(act.source as ProviderKey)}
							</span>
							<span class="shrink-0 text-fg-muted">›</span>
						</div>
						<!-- 날짜 + 핵심 스탯 (모바일 포함 항상 표시) -->
						<div class="flex flex-wrap items-center gap-x-3 gap-y-0 text-xs text-fg-secondary">
							<span class="text-fg-muted">{formatDate(act.start_time)}</span>
							<span>{act.distance_m != null ? formatDistance(act.distance_m) : '—'}</span>
							<span>{act.duration_sec != null ? formatDuration(act.duration_sec) : '—'}</span>
							<span>{act.avg_pace_sec_km != null ? formatPace(act.avg_pace_sec_km) : '—'}</span>
							{#if act.avg_hr != null}
								<span>HR {act.avg_hr}</span>
							{/if}
						</div>
					</a>
				</li>
			{/each}
		</ul>

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
