<script lang="ts">
	// 2/4 가져올 기간 — 기본 90일 추천, 소스별 추정 시간 표시.
	import { onMount } from 'svelte';
	import { estimateSync, getSyncState, triggerRangeSync } from '$lib/api/data';
	import { RANGES, etaLabel, rangeFor, type RangeKey } from '$lib/onboarding';

	let { onStarted }: { onStarted: () => void } = $props();
	let choice = $state<RangeKey>('90d');
	let sources = $state<string[]>([]);
	let eta = $state<Record<string, number | null>>({});
	let busy = $state(false);
	let error = $state<string | null>(null);

	onMount(async () => {
		try {
			const s = await getSyncState();
			sources = s.sources.filter((x) => x.connection === 'connected').map((x) => x.provider);
		} catch {
			return;
		}
		for (const r of RANGES) {
			const { from, to } = rangeFor(r.key);
			const est = await Promise.all(sources.map((p) => estimateSync(p, from, to).catch(() => null)));
			eta[r.key] = est.reduce((a, e) => a + (e?.requests ?? 0), 0) || null;
		}
	});

	async function start() {
		busy = true;
		error = null;
		try {
			const { from, to } = rangeFor(choice);
			await triggerRangeSync(sources, from, to);
			onStarted();
		} catch {
			error = '가져오기를 시작하지 못했어요. 다시 시도하거나 건너뛰세요.';
		} finally {
			busy = false;
		}
	}
</script>

<div class="flex flex-col gap-3">
	<h2 class="text-base font-semibold text-fg-primary">2/4 · 가져올 기간</h2>
	{#if sources.length === 0}
		<p class="text-xs text-fg-muted">연결된 소스가 없어요. 이전 단계에서 연결하거나 건너뛰세요.</p>
	{:else}
		{#each RANGES as r (r.key)}
			<label class="flex items-center gap-2 rounded-lg border border-border-subtle bg-surface-2 p-3 text-sm">
				<input type="radio" name="range" value={r.key} bind:group={choice} />
				{etaLabel(r.label, eta[r.key])}{r.recommended ? ' (추천)' : ''}
			</label>
		{/each}
		<button type="button" class="rounded-lg bg-fg-primary px-4 py-2 text-sm text-surface-1 disabled:opacity-50" disabled={busy} onclick={start}>가져오기 시작</button>
	{/if}
	{#if error}<p class="text-xs text-semantic-red">{error}</p>{/if}
</div>
