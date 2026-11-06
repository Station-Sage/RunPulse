<script lang="ts">
	// V2-SHOES 신발 상세(Level 2) — 상태 문구·마모 막대 → 마일리지 구성 → 소스 비교 → 월별 km → 배정 러닝 → 관리(수정·은퇴·합치기·삭제).
	import PageHead from '$lib/components/ui/PageHead.svelte';
	import type { ShoeDetailPageData } from './+page';
	import { base } from '$app/paths';
	import { goto, invalidate } from '$app/navigation';
	import { deleteShoe, mergeShoe, unlinkGear, updateShoe, type ShoeDetail } from '$lib/api/shoes';
	import { kindLabel, shoeWriteError, sourceLabel, statusMeta } from '$lib/shoeView';
	import { say } from '$lib/a11y/say';
	import { inlineConfirm } from '$lib/overlay';
	import EmptyState from '$lib/components/EmptyState.svelte';
	import ErrorState from '$lib/components/ErrorState.svelte';
	import ShoeWearBar from '$lib/components/ShoeWearBar.svelte';
	import ShoeFormSheet from '$lib/components/ShoeFormSheet.svelte';
	import ShoeActivityList from '$lib/components/ShoeActivityList.svelte';

	let { data }: { data: ShoeDetailPageData } = $props();

	const shoe = $derived(data.shoe.ok ? data.shoe.data : null);
	const meta = $derived(statusMeta(shoe?.status));
	const maxMonth = $derived(Math.max(1, ...(shoe?.monthly_km ?? []).map((m) => m.km)));
	let editing = $state(false);
	let confirmDelete = $state(false);
	let mergeId = $state<number | null>(null);
	let busy = $state(false);
	let error = $state('');
	const reload = () => invalidate('app:shoes');

	async function act(fn: () => Promise<unknown>, after?: () => unknown) {
		busy = true;
		error = '';
		try {
			await fn();
			await (after ? after() : reload());
		} catch (e) {
			error = shoeWriteError(e);
		} finally {
			busy = false;
		}
	}
	const today = () => new Date().toLocaleDateString('sv-SE');
	const toggleRetire = (s: ShoeDetail) => act(() => updateShoe(s.id, { retired_at: s.retired_at ? null : today() }));
	const remove = (s: ShoeDetail) => act(() => deleteShoe(s.id), () => goto(`${base}/library/shoes`, { invalidateAll: true }));
	const merge = (s: ShoeDetail) =>
		mergeId != null &&
		act(() => mergeShoe(s.id, mergeId as number));
	const unlink = (s: ShoeDetail, gearId: number) => act(() => unlinkGear(s.id, gearId));
	const btn = 'min-h-11 rounded-lg border border-border-subtle px-3 py-2 text-sm text-fg-secondary hover:bg-surface-3 disabled:opacity-60';
</script>

<PageHead title={`${shoe?.name ?? '신발'} · 신발`} heading={null} />

<div class="flex h-12 items-center gap-2 border-b border-border-subtle px-4">
	<a href="{base}/library/shoes" class="shrink-0 text-fg-muted" aria-label="신발 목록으로">‹</a>
	<nav aria-label="경로" class="flex min-w-0 items-center gap-1.5 text-xs text-fg-muted">
		<a href="{base}/library" class="hover:text-fg-secondary">Library</a>
		<span aria-hidden="true">›</span>
		<a href="{base}/library/shoes" class="hover:text-fg-secondary">신발</a>
		<span aria-hidden="true">›</span>
		<h1 class="truncate text-sm font-semibold text-fg-primary">{shoe?.name ?? '신발'}</h1>
	</nav>
</div>

<div class="flex flex-col gap-5 px-4 py-4 pb-24">
	{#if !data.shoe.ok && data.shoe.failure.kind === 'not_found'}
		<EmptyState title="신발을 찾을 수 없어요" description="삭제됐거나 합쳐진 신발일 수 있어요." actionLabel="← 목록으로" actionHref="{base}/library/shoes" />
	{:else if !data.shoe.ok}
		<ErrorState failure={data.shoe.failure} onRetry={reload} />
	{:else if shoe}
		<section class="flex flex-col gap-2" aria-label="상태">
			<p class="text-base font-medium {meta.text}" data-testid="shoe-status">{shoe.status === 'retired' ? `${shoe.retired_at} 은퇴` : shoe.message}</p>
			{#if shoe.note}<p class="text-sm text-fg-secondary">{shoe.note}</p>{/if}
			<ShoeWearBar mileage={shoe.mileage_km} retire={shoe.retire_km} status={shoe.status} label={shoe.name} />
			<p class="text-xs text-fg-muted">
				<span class="font-mono text-sm text-fg-primary">{shoe.mileage_km}</span> / {shoe.retire_km} km · {shoe.category_label}
				{#if shoe.default_for} · 기본 신발({kindLabel(shoe.default_for)}, {shoe.default_since}부터){/if}
				{#if shoe.brand || shoe.model} · {[shoe.brand, shoe.model].filter(Boolean).join(' ')}{/if}
			</p>
		</section>

		<section class="flex flex-col gap-1 rounded-lg border border-border-subtle bg-surface-2 p-3 text-sm" aria-label="마일리지 구성" data-testid="shoe-breakdown">
			<h2 class="text-xs tracking-wide text-fg-muted">왜 {shoe.mileage_km} km 인가요</h2>
			<p>시작 거리 <span class="font-mono">{shoe.breakdown.initial_km}</span> km + 배정된 러닝 {shoe.activity_count}건 <span class="font-mono">{shoe.breakdown.assigned_km}</span> km</p>
			<p class="text-xs text-fg-muted">직접 {shoe.breakdown.by_method.manual} km · 소스 기록 {shoe.breakdown.by_method.source} km · 기본 규칙 {shoe.breakdown.by_method.rule} km</p>
			{#each shoe.sources as src (src.gear_id)}
				<div class="flex items-center justify-between gap-2 text-xs text-fg-secondary">
					<span>{sourceLabel(src.source)} 기준 {src.total_km} km — RunPulse {shoe.mileage_km} km{#if src.total_km !== shoe.mileage_km} (차이는 RunPulse 에 없는 활동·비러닝 포함 가능){/if}</span>
					<button type="button" class="min-h-11 shrink-0 px-1 text-fg-muted underline" disabled={busy} onclick={() => unlink(shoe, src.gear_id)}>연결 해제</button>
				</div>
			{/each}
			{#if shoe.conflict_count > 0}<p class="text-xs text-semantic-amber">소스끼리 신발이 다른 러닝 {shoe.conflict_count}건 — 아래 목록에서 확인하세요</p>{/if}
		</section>

		{#if shoe.monthly_km.length > 0}
			<section class="flex flex-col gap-1.5" aria-label="월별 거리">
				<h2 class="text-xs font-medium uppercase tracking-wide text-fg-muted">월별 km</h2>
				{#each shoe.monthly_km.slice(-12) as m (m.month)}
					<div class="flex items-center gap-2 text-xs">
						<span class="w-16 font-mono text-fg-muted">{m.month}</span>
						<div class="h-2 flex-1 rounded bg-surface-3"><div class="h-2 rounded bg-series-1" style="width:{(m.km / maxMonth) * 100}%"></div></div>
						<span class="w-14 text-right font-mono text-fg-secondary">{m.km} km</span>
					</div>
				{/each}
			</section>
		{/if}

		<ShoeActivityList shoeId={shoe.id} first={data.activities} onRetry={reload} />

		<section class="flex flex-col gap-2" aria-label="관리">
			<h2 class="text-xs font-medium uppercase tracking-wide text-fg-muted">관리</h2>
			{#if error}<p class="text-xs text-semantic-red" use:say={{ text: error, level: 'assertive' }}>{error}</p>{/if}
			{#if editing}
				<ShoeFormSheet {shoe} onSaved={() => reload()} onClose={() => (editing = false)} />
			{:else}
				<div class="flex flex-wrap gap-2">
					<button type="button" class={btn} onclick={() => (editing = true)} data-testid="shoe-edit">수정</button>
					<button type="button" class={btn} disabled={busy} onclick={() => toggleRetire(shoe)} data-testid="shoe-retire">{shoe.retired_at ? '다시 사용' : '은퇴시키기'}</button>
					<button type="button" class="{btn} text-semantic-red" onclick={() => (confirmDelete = true)} data-testid="shoe-delete">삭제</button>
				</div>
			{/if}
			{#if confirmDelete}
				<div role="group" aria-label="신발 삭제 확인" use:inlineConfirm={{ onCancel: () => (confirmDelete = false) }} class="flex flex-col gap-2 rounded-lg border border-semantic-red/50 bg-surface-2 p-3 text-sm">
					<p>"{shoe.name}"을 삭제할까요? 직접 지정한 배정도 함께 지워지고, 소스 장비 연결은 풀려요.</p>
					<div class="flex gap-2">
						<button type="button" class="{btn} text-semantic-red" disabled={busy} onclick={() => remove(shoe)} data-testid="shoe-delete-confirm" data-autofocus>삭제</button>
						<button type="button" class={btn} onclick={() => (confirmDelete = false)}>취소</button>
					</div>
				</div>
			{/if}
			{#if data.others.length > 0}
				<div class="flex flex-wrap items-end gap-2">
					<label class="flex flex-col gap-1 text-xs text-fg-secondary">
						같은 신발 합치기 (선택한 신발을 이 신발로 흡수)
						<select bind:value={mergeId} class="min-h-11 rounded border border-border-subtle bg-surface-1 px-2 text-sm text-fg-primary">
							<option value={null}>선택</option>
							{#each data.others as o (o.id)}<option value={o.id}>{o.name}</option>{/each}
						</select>
					</label>
					<button type="button" class={btn} disabled={busy || mergeId == null} onclick={() => merge(shoe)}>합치기</button>
				</div>
			{/if}
		</section>
	{/if}
</div>
