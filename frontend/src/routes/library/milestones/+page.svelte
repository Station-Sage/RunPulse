<script lang="ts">
	// 마일스톤 전체 이력(ADR-057) — 종류 필터 칩 · 월별 묶음 · 날짜 = 사건일 · 커서 '더 보기'.
	import PageHead from '$lib/components/ui/PageHead.svelte';
	import ToggleGroup from '$lib/components/ui/ToggleGroup.svelte';
	import Icon from '$lib/components/Icon.svelte';
	import EmptyState from '$lib/components/EmptyState.svelte';
	import LoadFailure from '$lib/components/LoadFailure.svelte';
	import { base } from '$app/paths';
	import { goto } from '$app/navigation';
	import { getMilestoneHistory } from '$lib/api/milestones';
	import { milestoneIconName } from '$lib/milestoneIcon';
	import { PAGE_SIZE, dayLabel, filterChips, groupByMonth } from '$lib/milestoneHistory';
	import type { MilestoneEntry } from '$lib/types';
	import type { MilestonesPageData } from './+page';

	let { data }: { data: MilestonesPageData } = $props();

	let more = $state<MilestoneEntry[]>([]);
	let cursor = $state<string | null>(null);
	let loadingMore = $state(false);
	let moreError = $state<string | null>(null);

	const first = $derived(data.history.ok ? data.history.data : null);
	// 필터·첫 페이지가 바뀌면 이어 불러온 목록을 초기화한다
	$effect(() => {
		more = [];
		cursor = first?.next_before ?? null;
		moreError = null;
	});

	const items = $derived([...(first?.items ?? []), ...more]);
	const groups = $derived(groupByMonth(items));
	const chips = $derived(filterChips(first?.type_counts ?? []));

	function setType(v: string | string[] | null) {
		const t = typeof v === 'string' ? v : null;
		void goto(`${base}/library/milestones${t ? `?type=${t}` : ''}`, { keepFocus: true, noScroll: true });
	}

	async function loadMore() {
		if (!cursor) return;
		loadingMore = true;
		moreError = null;
		try {
			const r = await getMilestoneHistory({ type: data.type, before: cursor, limit: PAGE_SIZE });
			more = [...more, ...r.items];
			cursor = r.next_before;
		} catch {
			moreError = '더 불러오지 못했어요. 다시 시도해 주세요.';
		} finally {
			loadingMore = false;
		}
	}
</script>

<PageHead title="마일스톤 · Library" heading={null} />

<div class="flex h-12 items-center gap-2 border-b border-border-subtle px-4">
	<a href="{base}/library" class="shrink-0 text-fg-muted" aria-label="Library로">‹</a>
	<nav aria-label="경로" class="flex min-w-0 items-center gap-1.5 text-xs text-fg-muted">
		<a href="{base}/library" class="hover:text-fg-secondary">Library</a>
		<span aria-hidden="true">›</span>
		<h1 class="truncate text-sm font-semibold text-fg-primary">마일스톤</h1>
	</nav>
</div>

{#snippet row(m: MilestoneEntry)}
	<Icon name={milestoneIconName(m.type)} class="mt-0.5 h-4 w-4 shrink-0 text-fg-muted" />
	<div class="min-w-0 flex-1">
		<p class="text-sm text-fg-primary">{m.title}</p>
		<p class="text-xs text-fg-muted">{[dayLabel(m.date), m.detail].filter(Boolean).join(' · ')}</p>
	</div>
	{#if m.activity_id != null}<span class="shrink-0 text-fg-muted" aria-hidden="true">›</span>{/if}
{/snippet}

<div class="mx-auto flex max-w-3xl flex-col gap-4 px-4 py-4 pb-24" data-testid="milestone-history">
	{#if !data.history.ok}
		<LoadFailure failure={data.history.failure} retryKey="app:milestones" backHref="{base}/library" backLabel="Library로" />
	{:else}
		{#if chips.length > 1 || data.type}
			<ToggleGroup
				label="마일스톤 종류"
				class="flex flex-wrap gap-1"
				clearable
				items={[{ value: '', label: '전체' }, ...chips]}
				selected={data.type ?? ''}
				onchange={(v) => setType(v === '' ? null : v)}
			/>
		{/if}
		{#if items.length === 0}
			<EmptyState
				icon="trophy"
				title="아직 마일스톤이 없어요"
				description="대회 완주·목표 설정·누적 거리 돌파 같은 순간이 생기면 여기에 쌓여요."
			/>
		{:else}
			{#each groups as g (g.ym)}
				<section aria-labelledby="ms-{g.ym}">
					<h2 id="ms-{g.ym}" class="mb-1 text-xs font-semibold text-fg-secondary">{g.label}</h2>
					<ul class="flex flex-col">
						{#each g.items as m (m.id)}
							<li>
								{#if m.activity_id != null}
									<a href="{base}/library/{m.activity_id}?from=milestones" class="flex min-h-11 items-start gap-2 rounded-lg px-1 py-2 hover:bg-surface-2">{@render row(m)}</a>
								{:else}
									<div class="flex min-h-11 items-start gap-2 px-1 py-2">{@render row(m)}</div>
								{/if}
							</li>
						{/each}
					</ul>
				</section>
			{/each}
			{#if cursor}
				<button type="button" class="min-h-11 self-center rounded border border-border-subtle px-4 text-sm disabled:opacity-60" disabled={loadingMore} onclick={loadMore}>
					{loadingMore ? '불러오는 중…' : '더 보기'}
				</button>
			{/if}
			<p class="text-center text-xs text-semantic-red" aria-live="polite">{moreError ?? ''}</p>
		{/if}
	{/if}
</div>
