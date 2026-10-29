<script lang="ts">
	// NEW-7·8·19 — 체크인 '+ 상태' 토글(아파요·이동·시차·고지대)과 최상단 확인 질문(Level 0).
	import { closeContext, confirmContext, dismissContext, getContext, openContext } from '$lib/api/context';
	import { ALT_BANDS, KIND_LABEL, SEVERITY, SITES, confirmPrompts, isOpen, type ConfirmPrompt, type ContextKind, type ContextList } from '$lib/contextView';
	import ContextEpisodeList from './ContextEpisodeList.svelte';
	import IllnessConsentSheet from './IllnessConsentSheet.svelte';

	let { initial = null, onChange }: { initial?: ContextList | null; onChange?: () => void } = $props();

	let list = $state<ContextList | null>(initial);
	let open = $state(false);
	let pick = $state<ContextKind | null>(null);
	let severity = $state<number | undefined>(undefined);
	let site = $state<string | undefined>(undefined);
	let band = $state<string | undefined>(undefined);
	let busy = $state(false);
	let error = $state<string | null>(null);
	let consentSheet = $state(false);
	let hiddenHealth = $state(false);

	async function reload() {
		try { list = await getContext(); } catch { /* 칩은 부가 기능 — 실패해도 체크인은 유지 */ }
		onChange?.();
	}
	$effect(() => { if (!initial) void reload(); });

	const prompts = $derived(confirmPrompts(list).filter((p) => !(p.key === 'health' && hiddenHealth)));
	const openKinds = $derived(new Set((list?.episodes ?? []).filter(isOpen).map((e) => e.kind)));

	async function run(fn: () => Promise<unknown>) {
		busy = true; error = null;
		try { await fn(); await reload(); } catch (e) { error = e instanceof Error ? e.message : '저장하지 못했어요'; }
		finally { busy = false; }
	}

	async function answer(p: ConfirmPrompt, primary: boolean) {
		if (p.key === 'health') {
			if (primary) { pick = 'illness'; open = true; } else hiddenHealth = true;
			return;
		}
		const id = p.episodeId!;
		if (p.key.startsWith('re-')) await run(() => (primary ? confirmContext(id) : closeContext(id)));
		else await run(() => (primary ? confirmContext(id) : dismissContext(id)));
	}

	async function submit() {
		if (!pick) return;
		const kind = pick;
		const extra: { severity?: number; detail?: Record<string, unknown> } = {};
		if (kind === 'illness') { extra.severity = severity; if (site) extra.detail = { site }; }
		if (kind === 'altitude' && band) extra.detail = { band, altitude_m: ALT_BANDS.find((b) => b.key === band)?.m };
		await run(async () => {
			const r = await openContext(kind, extra);
			if (r.needs_consent_prompt) consentSheet = true;
			pick = null; severity = undefined; site = undefined; band = undefined; open = false;
		});
	}

	const chip = 'min-h-11 rounded border border-border-subtle px-3 text-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-semantic-teal';
</script>

<div class="flex flex-col gap-2">
	{#each prompts as p (p.key)}
		<div class="flex flex-col gap-2 rounded-lg border border-semantic-amber/40 bg-semantic-amber/10 p-3" role="group" aria-label={p.text}>
			<p class="text-sm text-fg-primary">{p.text}</p>
			<div class="flex gap-2">
				<button type="button" class="{chip} bg-surface-1" disabled={busy} onclick={() => answer(p, true)}>{p.primary}</button>
				<button type="button" class="{chip} bg-surface-1" disabled={busy} onclick={() => answer(p, false)}>{p.secondary}</button>
			</div>
		</div>
	{/each}

	<ContextEpisodeList episodes={list?.episodes ?? []} onChange={reload} />

	{#if !open}
		<button type="button" class="self-start text-sm text-fg-secondary hover:text-fg-primary" onclick={() => (open = true)}>+ 상태</button>
	{:else}
		<div class="flex flex-col gap-2 rounded-lg border border-border-subtle bg-surface-1 p-3">
			<div class="flex flex-wrap gap-1" role="group" aria-label="상태 종류">
				{#each Object.entries(KIND_LABEL) as [k, label] (k)}
					<button type="button" aria-pressed={pick === k} disabled={openKinds.has(k as ContextKind)} class="{chip} {pick === k ? 'bg-semantic-teal text-fg-on-accent' : 'bg-surface-2 text-fg-secondary'} disabled:opacity-50" onclick={() => (pick = pick === k ? null : (k as ContextKind))}>{label}</button>
				{/each}
			</div>
			{#if pick === 'illness'}
				<div class="flex flex-wrap gap-1" role="group" aria-label="정도">
					{#each SEVERITY as s (s.value)}
						<button type="button" aria-pressed={severity === s.value} class="{chip} {severity === s.value ? 'bg-semantic-amber text-fg-on-accent' : 'bg-surface-2'}" onclick={() => (severity = severity === s.value ? undefined : s.value)}>{s.label}</button>
					{/each}
				</div>
				<div class="flex flex-wrap gap-1" role="group" aria-label="부위">
					{#each SITES as s (s)}
						<button type="button" aria-pressed={site === s} class="{chip} {site === s ? 'bg-semantic-amber text-fg-on-accent' : 'bg-surface-2'}" onclick={() => (site = site === s ? undefined : s)}>{s}</button>
					{/each}
				</div>
			{:else if pick === 'altitude'}
				<div class="flex flex-wrap gap-1" role="group" aria-label="고도 구간">
					{#each ALT_BANDS as b (b.key)}
						<button type="button" aria-pressed={band === b.key} class="{chip} {band === b.key ? 'bg-semantic-teal text-fg-on-accent' : 'bg-surface-2'}" onclick={() => (band = band === b.key ? undefined : b.key)}>{b.label}</button>
					{/each}
				</div>
			{/if}
			{#if error}<p class="text-xs text-semantic-red">{error}</p>{/if}
			<div class="flex justify-end gap-2">
				<button type="button" class="{chip} bg-surface-2" onclick={() => { open = false; pick = null; }}>닫기</button>
				<button type="button" class="{chip} bg-semantic-teal text-fg-on-accent disabled:opacity-60" disabled={!pick || busy} onclick={submit}>기록</button>
			</div>
		</div>
	{/if}
</div>

{#if consentSheet}<IllnessConsentSheet via="first_input" onClose={() => { consentSheet = false; void reload(); }} />{/if}
