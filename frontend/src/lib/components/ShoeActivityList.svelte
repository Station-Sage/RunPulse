<script lang="ts">
	// 신발 상세 — 배정 활동 목록(ActivityRow + 배정 방식 태그 "직접/Garmin/기본 규칙" + 충돌 표시), 더 보기.
	import { getShoeActivities, type ShoeActivity, type ShoeActivityPage } from '$lib/api/shoes';
	import { classifyFailure, type Failure, type LoadResult } from '$lib/loadFailure';
	import { methodLabel, sourceLabel } from '$lib/shoeView';
	import ActivityRow from './ActivityRow.svelte';
	import ErrorState from './ErrorState.svelte';

	let { shoeId, first, onRetry }: { shoeId: number; first: LoadResult<ShoeActivityPage>; onRetry: () => void | Promise<unknown> } =
		$props();

	let extra = $state<ShoeActivity[]>([]);
	let cursor = $state<number | null>(null);
	let moreFailure = $state<Failure | null>(null);
	let loading = $state(false);

	$effect(() => {
		extra = [];
		cursor = first.ok ? first.data.next_cursor : null;
	});

	const rows = $derived(first.ok ? [...first.data.activities, ...extra] : []);

	async function more() {
		if (cursor == null) return;
		loading = true;
		moreFailure = null;
		try {
			const page = await getShoeActivities(shoeId, cursor);
			extra = [...extra, ...page.activities];
			cursor = page.next_cursor;
		} catch (e) {
			moreFailure = classifyFailure(e);
		} finally {
			loading = false;
		}
	}
</script>

<section class="flex flex-col gap-2" aria-label="배정된 러닝">
	<h2 class="text-xs font-medium uppercase tracking-wide text-fg-muted">배정된 러닝{first.ok ? ` ${first.data.total}건` : ''}</h2>
	{#if !first.ok}
		<ErrorState compact message="배정된 러닝을 불러오지 못했어요" failure={first.failure} onRetry={onRetry} />
	{:else if rows.length === 0}
		<p class="text-xs text-fg-muted">아직 이 신발로 기록된 러닝이 없어요.</p>
	{:else}
		<ul class="divide-y divide-border-subtle rounded-xl border border-border-subtle bg-surface-2">
			{#each rows as act (act.id)}
				<li>
					<ActivityRow {act} from="list" />
					<div class="flex flex-wrap gap-1.5 px-3 pb-2 text-[10px]">
						<span class="rounded bg-surface-3 px-1.5 py-0.5 text-fg-secondary" data-testid="shoe-method">{methodLabel(act.method, act.method_source)}</span>
						{#if act.conflict}
							<span class="rounded border border-semantic-amber/50 px-1.5 py-0.5 text-semantic-amber">
								소스 불일치: {act.conflict_sources.map((c) => `${sourceLabel(c.source)} ${c.name ?? '?'}`).join(' · ')}
							</span>
						{/if}
					</div>
				</li>
			{/each}
		</ul>
		{#if moreFailure}<ErrorState compact failure={moreFailure} onRetry={more} />{/if}
		{#if cursor != null}
			<button type="button" class="min-h-11 self-center text-sm text-fg-secondary hover:text-fg-primary" disabled={loading} onclick={more}>
				{loading ? '불러오는 중…' : '더 보기'}
			</button>
		{/if}
	{/if}
</section>
