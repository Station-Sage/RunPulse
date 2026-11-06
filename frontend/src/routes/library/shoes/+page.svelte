<script lang="ts">
	// V2-SHOES 신발 목록 — Level 0 한 줄 → 미배정 배지·가져오기 제안 → 카드(replace→soon→ok) → 접힌 은퇴 신발.
	import PageHead from '$lib/components/ui/PageHead.svelte';
	import type { ShoesPageData } from './+page';
	import { base } from '$app/paths';
	import { invalidate } from '$app/navigation';
	import { importGear } from '$lib/api/shoes';
	import { shoeWriteError, sourceLabel } from '$lib/shoeView';
	import { say } from '$lib/a11y/say';
	import EmptyState from '$lib/components/EmptyState.svelte';
	import ErrorState from '$lib/components/ErrorState.svelte';
	import ShoeCard from '$lib/components/ShoeCard.svelte';
	import ShoeFormSheet from '$lib/components/ShoeFormSheet.svelte';
	import ShoeBulkAssignSheet from '$lib/components/ShoeBulkAssignSheet.svelte';

	let { data }: { data: ShoesPageData } = $props();

	let formOpen = $state(false);
	let bulkOpen = $state(false);
	let showRetired = $state(false);
	let importing = $state(false);
	let notice = $state('');
	let error = $state('');

	const list = $derived(data.list.ok ? data.list.data : null);
	const active = $derived(list?.shoes.filter((s) => s.status !== 'retired') ?? []);
	const retired = $derived(list?.shoes.filter((s) => s.status === 'retired') ?? []);
	const suggestions = $derived(list?.suggestions ?? []);
	const reload = () => invalidate('app:shoes');

	async function runImport() {
		importing = true;
		error = '';
		try {
			const r = await importGear();
			notice = `신발 ${r.created}켤레를 가져왔어요`;
			await reload();
		} catch (e) {
			error = shoeWriteError(e);
		} finally {
			importing = false;
		}
	}
</script>

<PageHead title="신발 · Library" heading={null} />

<div class="flex h-12 items-center gap-2 border-b border-border-subtle px-4">
	<a href="{base}/library" class="shrink-0 text-fg-muted" aria-label="Library 로">‹</a>
	<nav aria-label="경로" class="flex min-w-0 items-center gap-1.5 text-xs text-fg-muted">
		<a href="{base}/library" class="hover:text-fg-secondary">Library</a>
		<span aria-hidden="true">›</span>
		<h1 class="truncate text-sm font-semibold text-fg-primary">신발</h1>
	</nav>
	{#if list && !formOpen}
		<button type="button" class="ml-auto min-h-11 px-2 text-sm text-fg-secondary hover:text-fg-primary" onclick={() => (formOpen = true)} data-testid="shoe-add">신발 추가</button>
	{/if}
</div>

<div class="flex flex-col gap-4 px-4 py-4 pb-24">
	{#if !data.list.ok}
		<ErrorState failure={data.list.failure} onRetry={reload} />
	{:else if list}
		{#if notice}<p class="text-xs text-semantic-teal" use:say={{ text: notice }}>{notice}</p>{/if}
		{#if error}<p class="text-xs text-semantic-red" use:say={{ text: error, level: 'assertive' }}>{error}</p>{/if}
		{#if formOpen}
			<ShoeFormSheet onSaved={() => reload()} onClose={() => (formOpen = false)} />
		{/if}

		{#if list.shoes.length === 0 && !formOpen}
			{#if suggestions.length > 0}
				<EmptyState icon="activity" title="Strava·Garmin 에 신발 {suggestions.length}켤레가 있어요"
					description="한 번에 가져오면 이름이 같은 신발은 한 켤레로 묶어요." actionLabel={importing ? '가져오는 중…' : '가져오기'} onAction={runImport} />
				<button type="button" class="min-h-11 self-center text-sm text-fg-secondary underline" onclick={() => (formOpen = true)}>직접 추가</button>
			{:else}
				<EmptyState icon="activity" title="아직 등록한 신발이 없어요"
					description="신발을 등록하면 마일리지와 교체 시기를 알려드려요." actionLabel="신발 추가" onAction={() => (formOpen = true)} />
			{/if}
		{:else if list.shoes.length > 0}
			{#if list.headline}
				<p class="text-base font-medium text-fg-primary" data-testid="shoe-headline">{list.headline}</p>
			{/if}
			{#if list.unassigned_count > 0 && active.length > 0}
				{#if bulkOpen}
					<ShoeBulkAssignSheet shoes={active} onDone={(n) => { notice = `${n}건에 신발을 지정했어요`; reload(); }} onClose={() => (bulkOpen = false)} />
				{:else}
					<button type="button" onclick={() => (bulkOpen = true)} data-testid="shoe-unassigned"
						class="flex min-h-11 items-center justify-between rounded-lg border border-semantic-amber/50 bg-surface-2 px-3 py-2 text-left text-sm text-fg-secondary hover:bg-surface-3">
						<span>신발이 정해지지 않은 러닝 {list.unassigned_count}건</span><span class="text-xs text-fg-primary">한 번에 지정 →</span>
					</button>
				{/if}
			{/if}
			{#if suggestions.length > 0}
				<div class="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-border-subtle bg-surface-2 px-3 py-2 text-sm" data-testid="shoe-suggestions">
					<span class="text-fg-secondary">연결 안 된 소스 신발 {suggestions.length}켤레 ({[...new Set(suggestions.flatMap((s) => s.sources))].map(sourceLabel).join('·')})</span>
					<button type="button" class="min-h-11 px-2 text-sm text-fg-primary underline" disabled={importing} onclick={runImport}>{importing ? '가져오는 중…' : '가져오기'}</button>
				</div>
			{/if}
			<ul class="flex flex-col gap-2" aria-label="사용 중인 신발">
				{#each active as s (s.id)}<li><ShoeCard shoe={s} /></li>{/each}
			</ul>
			{#if retired.length > 0}
				<button type="button" class="min-h-11 self-start text-sm text-fg-muted hover:text-fg-secondary" aria-expanded={showRetired}
					onclick={() => (showRetired = !showRetired)}>은퇴한 신발 {retired.length}켤레 {showRetired ? '접기' : '보기'}</button>
				{#if showRetired}
					<ul class="flex flex-col gap-2 opacity-80" aria-label="은퇴한 신발">
						{#each retired as s (s.id)}<li><ShoeCard shoe={s} /></li>{/each}
					</ul>
				{/if}
			{/if}
		{/if}
	{/if}
</div>
