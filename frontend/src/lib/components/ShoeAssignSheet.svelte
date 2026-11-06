<script lang="ts">
	// 활동 상세 신발 선택(V2-SHOES T10) — 활성 신발 목록·"신발 없음"·"자동으로 되돌리기". 저장 즉시 반영.
	import { say } from '$lib/a11y/say';
	import { getShoes, resetActivityShoe, setActivityShoe, type ActivityShoe, type Shoe } from '$lib/api/shoes';
	import { toResult, type LoadResult } from '$lib/loadFailure';
	import { methodLabel, shoeWriteError, sourceLabel } from '$lib/shoeView';
	import { base } from '$app/paths';
	import ErrorState from './ErrorState.svelte';

	let { activityId, current, onChanged, onClose }: {
		activityId: number;
		current: ActivityShoe;
		onChanged?: (s: ActivityShoe | null) => void;
		onClose?: () => void;
	} = $props();

	let list = $state<LoadResult<Shoe[]> | null>(null);
	let busy = $state(false);
	let error = $state('');

	async function load() {
		list = null;
		const r = await toResult(getShoes(false));
		list = r.ok ? { ok: true, data: r.data.shoes } : r;
	}
	$effect(() => {
		load();
	});

	async function run(fn: () => Promise<{ shoe: ActivityShoe | null }>) {
		busy = true;
		error = '';
		try {
			const res = await fn();
			onChanged?.(res.shoe);
			onClose?.();
		} catch (e) {
			error = shoeWriteError(e);
		} finally {
			busy = false;
		}
	}
	const btn = 'flex min-h-11 w-full items-center justify-between rounded-lg border px-3 py-2 text-left text-sm disabled:opacity-60';
	const on = (id: number | null) =>
		current.method === 'manual' && current.id === id ? 'border-semantic-teal text-fg-primary' : 'border-border-subtle text-fg-secondary';
</script>

<div class="flex flex-col gap-2 rounded-lg border border-border-subtle bg-surface-2 p-4" data-testid="shoe-assign-sheet">
	<div class="flex items-center justify-between">
		<p class="text-sm font-medium text-fg-primary">이 러닝의 신발</p>
		<button type="button" onclick={onClose} class="h-11 px-2 text-xs text-fg-muted hover:text-fg-primary">닫기</button>
	</div>
	{#if current.conflict && current.conflict_sources.length}
		<p class="text-xs text-semantic-amber">
			소스가 서로 다른 신발을 기록했어요 —
			{current.conflict_sources.map((c) => `${sourceLabel(c.source)}은 ${c.name ?? '알 수 없음'}`).join(', ')}
		</p>
	{/if}
	{#if list === null}
		<p class="text-xs text-fg-muted">불러오는 중…</p>
	{:else if !list.ok}
		<ErrorState compact failure={list.failure} onRetry={load} />
	{:else}
		{#if list.data.length === 0}
			<p class="text-xs text-fg-muted">등록된 신발이 없어요. <a class="underline" href="{base}/library/shoes">신발 추가하기</a></p>
		{/if}
		<ul class="flex flex-col gap-1.5" aria-label="신발 선택">
			{#each list.data as s (s.id)}
				<li>
					<button type="button" class="{btn} {on(s.id)}" disabled={busy} aria-pressed={current.method === 'manual' && current.id === s.id}
						onclick={() => run(() => setActivityShoe(activityId, s.id))}>
						<span class="truncate">{s.name}</span><span class="text-xs text-fg-muted">{Math.round(s.mileage_km)} km</span>
					</button>
				</li>
			{/each}
			<li>
				<button type="button" class="{btn} {on(null)}" disabled={busy} aria-pressed={current.method === 'manual' && current.id === null}
					onclick={() => run(() => setActivityShoe(activityId, null))}>신발 없음</button>
			</li>
		</ul>
		{#if current.method === 'manual'}
			<button type="button" class="min-h-11 self-start text-sm text-fg-secondary underline" disabled={busy} data-testid="shoe-reset"
				onclick={() => run(() => resetActivityShoe(activityId))}>자동으로 되돌리기</button>
		{:else if current.method === 'none'}
			<p class="text-xs text-fg-muted">아직 신발이 정해지지 않았어요. 직접 고르면 다음 동기화가 덮어쓰지 않아요.</p>
		{:else}
			<p class="text-xs text-fg-muted">지금은 자동 배정({methodLabel(current.method, current.source)})이에요. 직접 고르면 다음 동기화가 덮어쓰지 않아요.</p>
		{/if}
	{/if}
	{#if error}<p class="text-xs text-semantic-red" use:say={{ text: error, level: 'assertive' }}>{error}</p>{/if}
</div>
