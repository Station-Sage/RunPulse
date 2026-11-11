<script lang="ts">
	// NEW-7·8·19 — 체크인 '+ 상태' 토글(아파요·이동·시차·고지대)과 최상단 확인 질문(Level 0).
	import { closeContext, confirmContext, dismissContext, getContext, openContext } from '$lib/api/context';
	import { ALT_BANDS, KIND_LABEL, SEVERITY, SITES, confirmPrompts, isOpen, type ConfirmPrompt, type ContextKind, type ContextList } from '$lib/contextView';
	import ContextEpisodeList from './ContextEpisodeList.svelte';
	import ToggleGroup from './ui/ToggleGroup.svelte';
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

	async function fetchList() {
		try { list = await getContext(); } catch { /* 칩은 부가 기능 — 실패해도 체크인은 유지 */ }
	}
	// 사용자가 상태를 바꾼 뒤에만 onChange — 첫 조회에서 부르면 오늘 화면 전체를 한 번 더 불러온다(S4-89 CWV).
	async function reload() {
		await fetchList();
		onChange?.();
	}
	$effect(() => { if (!initial) void fetchList(); });

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

	const chip = 'min-h-11 rounded border border-border-subtle px-3 text-sm';
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
			<ToggleGroup
				label="상태 종류"
				class="flex flex-wrap gap-1"
				clearable
				items={Object.entries(KIND_LABEL).map(([k, label]) => ({ value: k, label, disabled: openKinds.has(k as ContextKind) }))}
				selected={pick}
				onchange={(v) => (pick = (v as ContextKind | null) ?? null)}
			/>
			{#if pick === 'illness'}
				<ToggleGroup
					label="정도"
					class="flex flex-wrap gap-1"
					clearable
					items={SEVERITY.map((x) => ({ value: String(x.value), label: x.label }))}
					selected={severity === undefined ? null : String(severity)}
					onchange={(v) => (severity = v ? Number(v) : undefined)}
				/>
				<ToggleGroup
					label="부위"
					class="flex flex-wrap gap-1"
					clearable
					items={SITES.map((x) => ({ value: x, label: x }))}
					selected={site ?? null}
					onchange={(v) => (site = (v as string) ?? undefined)}
				/>
			{:else if pick === 'altitude'}
				<ToggleGroup
					label="고도 구간"
					class="flex flex-wrap gap-1"
					clearable
					items={ALT_BANDS.map((b) => ({ value: b.key, label: b.label }))}
					selected={band ?? null}
					onchange={(v) => (band = (v as string) ?? undefined)}
				/>
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
