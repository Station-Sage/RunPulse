<script lang="ts">
	// 미배정 러닝 일괄 배정(V2-SHOES US8) — 최근 미배정 러닝을 골라 한 신발로 직접 배정한다(최대 200건).
	import { say } from '$lib/a11y/say';
	import { assignShoe, getUnassignedRuns, type Shoe, type ShoeActivityPage } from '$lib/api/shoes';
	import { toResult, type LoadResult } from '$lib/loadFailure';
	import { shoeWriteError } from '$lib/shoeView';
	import { formatDuration } from '$lib/format';
	import ErrorState from './ErrorState.svelte';

	let { shoes, onDone, onClose }: { shoes: Shoe[]; onDone?: (n: number) => void; onClose?: () => void } = $props();

	let page = $state<LoadResult<ShoeActivityPage> | null>(null);
	let picked = $state<number[]>([]);
	// svelte-ignore state_referenced_locally
	let shoeId = $state<number | null>(shoes[0]?.id ?? null);
	let busy = $state(false);
	let error = $state('');

	async function load() {
		page = null;
		page = await toResult(getUnassignedRuns(0, 100));
		if (page.ok) picked = page.data.activities.map((a) => a.id);
	}
	$effect(() => {
		load();
	});

	const toggle = (id: number) => (picked = picked.includes(id) ? picked.filter((x) => x !== id) : [...picked, id]);

	async function submit() {
		if (shoeId == null || picked.length === 0) return;
		busy = true;
		error = '';
		try {
			const r = await assignShoe(shoeId, picked.slice(0, 200));
			onDone?.(r.assigned);
			onClose?.();
		} catch (e) {
			error = shoeWriteError(e);
		} finally {
			busy = false;
		}
	}
</script>

<div class="flex flex-col gap-3 rounded-lg border border-border-subtle bg-surface-2 p-4" data-testid="shoe-bulk-sheet">
	<div class="flex items-center justify-between">
		<p class="text-sm font-medium text-fg-primary">미배정 러닝에 신발 지정</p>
		<button type="button" onclick={onClose} class="h-11 px-2 text-xs text-fg-muted hover:text-fg-primary">닫기</button>
	</div>
	<label class="flex flex-col gap-1 text-xs text-fg-secondary">
		신발
		<select bind:value={shoeId} class="min-h-11 rounded border border-border-subtle bg-surface-1 px-2 text-sm text-fg-primary">
			{#each shoes as s (s.id)}<option value={s.id}>{s.name}</option>{/each}
		</select>
	</label>
	{#if page === null}
		<p class="text-xs text-fg-muted">불러오는 중…</p>
	{:else if !page.ok}
		<ErrorState compact failure={page.failure} onRetry={load} />
	{:else if page.data.activities.length === 0}
		<p class="text-xs text-fg-muted">미배정 러닝이 없어요.</p>
	{:else}
		<p class="text-xs text-fg-muted">최근 {page.data.activities.length}건{page.data.total > page.data.activities.length ? ` (전체 ${page.data.total}건)` : ''} · 선택 {picked.length}건</p>
		<ul class="max-h-72 divide-y divide-border-subtle overflow-y-auto rounded border border-border-subtle" aria-label="미배정 러닝">
			{#each page.data.activities as a (a.id)}
				<li>
					<label class="flex min-h-11 items-center gap-3 px-3 py-2 text-sm">
						<input type="checkbox" checked={picked.includes(a.id)} onchange={() => toggle(a.id)} class="h-4 w-4" />
						<span class="w-24 shrink-0 font-mono text-xs text-fg-muted">{a.start_time.slice(0, 10)}</span>
						<span class="min-w-0 flex-1 truncate text-fg-primary">{a.display_title ?? a.name}</span>
						<span class="shrink-0 font-mono text-xs text-fg-secondary">{a.distance_m != null ? (a.distance_m / 1000).toFixed(1) : '—'} km</span>
						<span class="hidden shrink-0 font-mono text-xs text-fg-muted sm:inline">{a.duration_sec != null ? formatDuration(a.duration_sec) : ''}</span>
					</label>
				</li>
			{/each}
		</ul>
	{/if}
	{#if error}<p class="text-xs text-semantic-red" use:say={{ text: error, level: 'assertive' }}>{error}</p>{/if}
	<div class="flex justify-end">
		<button type="button" onclick={submit} disabled={busy || shoeId == null || picked.length === 0} data-testid="shoe-bulk-submit"
			class="h-11 rounded bg-semantic-teal px-5 text-sm font-medium text-fg-on-accent disabled:opacity-60">{busy ? '배정 중…' : `${picked.length}건 배정`}</button>
	</div>
</div>
