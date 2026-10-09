<script lang="ts">
	// 남은 일정 다시 맞추기 — 미리보기 → 적용 → 되돌리기 (DESIGN-PLAN-A6-REPLAN-UI).
	import { onMount } from 'svelte';
	import { base } from '$app/paths';
	import { applyReplan, getReplanLast, previewReplan, undoReplan } from '$lib/api/plan';
	import ReplanStartCard from '$lib/components/plan/ReplanStartCard.svelte';
	import ReplanInputs from '$lib/components/plan/ReplanInputs.svelte';
	import ReplanNotices from '$lib/components/plan/ReplanNotices.svelte';
	import ReplanWeekTable from '$lib/components/plan/ReplanWeekTable.svelte';
	import {
		anchorLabel, canApply, inputFields, longRunLine, mergeWeeks, startSourceText, startState, targetChangeText, parseReplanInputs, replanErrorView, replanQuery, replanSummary,
		undoUntilLabel, type ErrorAction, type Phase, type RawInputs
	} from '$lib/replanView';
	import type { ReplanPreview } from '$lib/types';

	let values = $state<RawInputs>({ weekly: '', long: '', target: '' });
	let preview = $state<ReplanPreview | null>(null);
	let dirty = $state(false);
	let busy = $state(false);
	let stage = $state<'preview' | 'applied' | 'undone'>('preview');
	let err = $state<{ text: string; action: ErrorAction; phase: Phase } | null>(null);
	let applied = $state<ReplanPreview | null>(null);
	let pendingId = $state<number | null>(null);

	const parsed = $derived(parseReplanInputs(values));
	const hasError = $derived(Object.keys(parsed.errors).length > 0);
	const fields = $derived(inputFields(preview ? startState(preview.basis) : 'A'));
	const targetNote = $derived(targetChangeText(preview?.goal_target_time_sec ?? null, parsed.params.target_time_sec ?? null));
	const rows = $derived(preview ? mergeWeeks(preview.before, preview.after) : []);

	async function fail(e: unknown, phase: Phase) {
		const v = replanErrorView(e as { status?: number; code?: string; details?: unknown }, phase);
		err = { text: v.text, action: v.action, phase };
		if (v.action === 'undo') {
			pendingId = (e as { details?: { last?: { replan_id?: number } } }).details?.last?.replan_id ?? null;
			if (pendingId == null) pendingId = (await getReplanLast().catch(() => null))?.last?.replan_id ?? null;
		}
	}

	async function load() {
		if (hasError) return;
		busy = true;
		err = null;
		try {
			preview = await previewReplan(replanQuery(parsed.params));
			dirty = false;
		} catch (e) {
			preview = null;
			fail(e, 'preview');
		} finally {
			busy = false;
		}
	}

	async function apply() {
		if (!preview || !canApply({ preview, dirty, busy, hasError })) return;
		busy = true;
		err = null;
		try {
			applied = await applyReplan(parsed.params, preview.anchor_monday);
			stage = 'applied';
		} catch (e) {
			fail(e, 'apply');
		} finally {
			busy = false;
		}
	}

	async function undo() {
		const id = applied?.replan_id ?? pendingId;
		if (!id) return;
		busy = true;
		err = null;
		try {
			await undoReplan(id);
			if (stage === 'applied') stage = 'undone';
			else {
				pendingId = null;
				await load();
			}
		} catch (e) {
			fail(e, 'undo');
		} finally {
			busy = false;
		}
	}

	function onAction() {
		if (!err) return;
		const a = err.action;
		if (a === 'retry' || a === 'repreview') {
			if (stage === 'applied') stage = 'preview';
			load();
		}
	}

	const href = {
		plan: `${base}/coach/plan`,
		newGoal: `${base}/coach/plan/new`
	};
	const actionLabel: Record<string, string> = {
		retry: '다시 시도', repreview: '미리보기 다시 보기', newGoal: '목표 만들기', plan: '계획 보기', undo: '되돌리기', back: '계획으로 돌아가기'
	};

	onMount(load);
</script>

<div class="mx-auto max-w-xl space-y-4 p-4 pb-48 lg:pb-32">
	<a href={href.plan} class="inline-flex min-h-11 items-center text-xs text-fg-secondary">← 계획</a>
	<h1 class="text-lg font-semibold">남은 일정 다시 맞추기</h1>

	{#if stage === 'applied' && applied}
		<div class="space-y-3 rounded-lg bg-surface-2 p-3 text-sm">
			<p>{anchorLabel(applied.anchor_monday)}부터 새 일정을 적용했어요. 이 화면에서 {undoUntilLabel(applied.anchor_monday)}까지 되돌릴 수 있어요.</p>
			<div class="flex gap-2">
				<a href={href.plan} class="inline-flex min-h-11 items-center rounded-lg bg-surface-1 px-4">계획 보기</a>
				<button class="min-h-11 rounded-lg px-4 underline" disabled={busy} onclick={undo}>되돌리기</button>
			</div>
		</div>
		<ReplanNotices preview={applied} />
	{:else if stage === 'undone'}
		<div class="space-y-3 rounded-lg bg-surface-2 p-3 text-sm">
			<p>원래 일정으로 돌렸어요.</p>
			<a href={href.plan} class="inline-flex min-h-11 items-center rounded-lg bg-surface-1 px-4">계획 보기</a>
		</div>
	{:else}
		{#if preview}
			<p class="rounded-lg bg-surface-2 p-3 text-sm">
				{replanSummary(preview)}{#if targetNote} {targetNote}{/if}
				{#if longRunLine(preview)}<span class="mt-1 block text-fg-secondary">{longRunLine(preview)}</span>{/if}
			</p>
			<ReplanStartCard {preview} bind:values error={parsed.errors.target} oninput={() => (dirty = true)} />
		{:else if busy}
			<p class="text-xs text-fg-secondary">미리보기를 계산하고 있어요</p>
		{/if}

		{#if preview}
			<ReplanInputs bind:values errors={parsed.errors} warnings={parsed.warnings} {fields} oninput={() => (dirty = true)} />
		{/if}

		{#if preview}
			<ReplanWeekTable {rows} />
			<ReplanNotices {preview} />
			<details class="rounded-lg bg-surface-2 p-3 text-xs text-fg-secondary">
				<summary class="min-h-11 cursor-pointer py-3">어떻게 계산했나요</summary>
				<p>{startSourceText(preview)}</p>
				<p>캘린더 구독(ICS)은 자동으로 새 일정으로 바뀌어요.</p>
			</details>
		{/if}
	{/if}

	{#if err}
		<div role="alert" class="space-y-2 rounded-lg bg-surface-2 p-3 text-xs text-semantic-red">
			<p>{err.text}</p>
			{#if err.action}
				{#if err.action === 'plan' || err.action === 'back'}
					<a class="inline-flex min-h-11 items-center underline" href={href.plan}>{actionLabel[err.action]}</a>
				{:else if err.action === 'newGoal'}
					<a class="inline-flex min-h-11 items-center underline" href={href.newGoal}>{actionLabel.newGoal}</a>
				{:else if err.action === 'undo'}
					<button class="min-h-11 underline" disabled={busy || pendingId == null} onclick={undo}>되돌리기</button>
				{:else}
					<button class="min-h-11 underline" onclick={onAction}>{actionLabel[err.action]}</button>
				{/if}
			{/if}
		</div>
	{/if}
</div>

{#if stage === 'preview' && preview}
	<div class="fixed inset-x-0 bottom-[calc(3.75rem+env(safe-area-inset-bottom))] z-40 space-y-2 border-t border-border bg-surface-1 p-3 lg:bottom-0 lg:left-52">
		{#if preview.external.length}
			<p class="text-xs text-fg-secondary">Garmin 세션 {preview.external.length}개는 직접 지워야 해요</p>
		{/if}
		{#if dirty}
			<p class="text-xs text-fg-secondary">바꾼 값으로 다시 계산해 주세요</p>
		{/if}
		<div class="flex gap-2">
			{#if dirty}
				<button class="min-h-11 flex-1 rounded-lg bg-accent px-4 text-sm" disabled={busy || hasError} onclick={load}>다시 계산</button>
			{/if}
			<button class="min-h-11 flex-1 rounded-lg bg-accent px-4 text-sm disabled:opacity-40" disabled={!canApply({ preview, dirty, busy, hasError })} onclick={apply}>
				{busy ? '적용하고 있어요' : `${anchorLabel(preview.anchor_monday).slice(0, 5)}부터 적용`}
			</button>
			<a href={href.plan} class="inline-flex min-h-11 items-center px-4 text-sm">취소</a>
		</div>
	</div>
{/if}
