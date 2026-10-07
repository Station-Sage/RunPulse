<script lang="ts">
	import { estimateSync, type SyncEstimate } from '$lib/api/data';
	import { estimateView, validateRange } from '$lib/rangeSync';
	import { syncProviderName } from '$lib/syncState';
	import { runRangeTrigger, syncStore } from '$lib/syncStore.svelte';

	let { providers }: { providers: string[] } = $props();
	const today = new Date().toISOString().slice(0, 10);
	let provider = $state('');
	let from = $state('');
	let to = $state(today);
	let est = $state<SyncEstimate | null>(null);
	let busy = $state(false);
	let err = $state<string | null>(null);
	let open = $state(false);

	const current = $derived(provider || providers[0] || '');
	const view = $derived(est ? estimateView(est) : null);

	async function check() {
		est = null;
		err = validateRange(from, to, today);
		if (err || !current) return;
		busy = true;
		try {
			est = await estimateSync(current, from, to);
		} catch {
			err = '추정하지 못했어요. 다시 눌러 주세요';
		}
		busy = false;
	}

	async function start() {
		await runRangeTrigger(current, from, to);
		est = null;
	}
</script>

<section aria-label="기간 지정 동기화" class="rounded-lg border border-border-subtle bg-surface-2 p-3">
	<button type="button" class="w-full text-left text-sm font-semibold text-fg-primary" aria-expanded={open}
		onclick={() => (open = !open)}>기간 지정 동기화 {open ? '▴' : '▾'}</button>
	{#if open}
		<div class="mt-3 flex flex-col gap-2 text-sm">
			<label class="flex flex-col gap-1 text-xs text-fg-secondary">소스
				<select class="rounded border border-border-subtle bg-surface-1 p-2 text-sm text-fg-primary"
					bind:value={provider} onchange={() => (est = null)}>
					{#each providers as p (p)}<option value={p}>{syncProviderName(p)}</option>{/each}
				</select>
			</label>
			<div class="flex gap-2">
				<label class="flex flex-1 flex-col gap-1 text-xs text-fg-secondary">시작일
					<input type="date" max={today} bind:value={from} oninput={() => (est = null)}
						class="rounded border border-border-subtle bg-surface-1 p-2 text-sm text-fg-primary" />
				</label>
				<label class="flex flex-1 flex-col gap-1 text-xs text-fg-secondary">종료일
					<input type="date" max={today} bind:value={to} oninput={() => (est = null)}
						class="rounded border border-border-subtle bg-surface-1 p-2 text-sm text-fg-primary" />
				</label>
			</div>
			{#if err}<p class="text-xs text-fg-secondary" role="alert">{err}</p>{/if}
			{#if view}
				<ul class="text-xs text-fg-secondary" aria-label="추정 결과">{#each view.lines as l}<li>{l}</li>{/each}</ul>
			{/if}
			{#if view?.canStart}
				<button type="button" class="rounded-lg bg-fg-primary px-4 py-2 text-sm font-medium text-surface-1 disabled:opacity-50"
					disabled={syncStore.triggering} onclick={start}>이 기간 동기화 시작</button>
			{:else}
				<button type="button" class="rounded-lg border border-border-subtle px-4 py-2 text-sm disabled:opacity-50"
					disabled={busy || !current} onclick={check}>{busy ? '확인 중…' : '요청 수 확인'}</button>
			{/if}
		</div>
	{/if}
</section>
