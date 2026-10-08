<script lang="ts">
	// 계획 조정 제안·적용 카드 (ADR-035). 수락/되돌리기 후 호출부에 onChange 로 알린다.
	import { ApiError } from '$lib/api/client';
	import { acceptAdjustment, getTodaysAdjustment, revertAdjustment } from '$lib/api/plan';
	import { workoutLabel } from '$lib/format';
	import Icon from '$lib/components/Icon.svelte';
	import {
		adjustmentActions,
		adjustmentDelta,
		adjustmentHeadline,
		adjustmentStateText
	} from '$lib/adjustmentView';
	import type { AdjustmentState, PlanAdjustment, TodaysAdjustment } from '$lib/types';

	let {
		initial,
		initialAdj,
		via,
		onChange
	}: {
		initial: AdjustmentState | undefined;
		initialAdj: PlanAdjustment | null | undefined;
		via: 'plan' | 'session' | 'today' | 'coach';
		onChange?: () => void;
	} = $props();

	let cur = $state<AdjustmentState | undefined>(undefined);
	let adj = $state<PlanAdjustment | null | undefined>(undefined);
	let busy = $state(false);
	let error = $state<string | null>(null);
	let synced = false;

	$effect(() => {
		if (!synced) {
			cur = initial;
			adj = initialAdj;
			synced = true;
		}
	});

	async function refresh() {
		const t = (await getTodaysAdjustment()) as TodaysAdjustment;
		cur = t.state;
		adj = t.adjustment ?? null;
	}

	async function run(fn: () => Promise<{ adjustment: PlanAdjustment }>) {
		if (busy) return;
		busy = true;
		error = null;
		try {
			const r = await fn();
			adj = r.adjustment;
			cur = r.adjustment.state;
			onChange?.();
		} catch (e) {
			if (e instanceof ApiError && e.status === 409) {
				await refresh().catch(() => {});
				error = '다른 곳에서 상태가 바뀌어 최신 내용으로 갱신했어요';
				onChange?.();
			} else {
				error = '처리하지 못했어요 · 잠시 후 다시 시도해 주세요';
			}
		} finally {
			busy = false;
		}
	}

	const actions = $derived(adjustmentActions(cur));
	const headline = $derived(adjustmentHeadline(cur));
	const note = $derived(adjustmentStateText(cur));
</script>

{#if adj && (headline || note)}
	<div class="border-b border-border-subtle bg-surface-2 px-4 py-3" data-testid="adjustment-card">
		{#if headline}
			<p class="flex items-center gap-1 text-xs font-medium text-semantic-amber">
				<Icon name="warning" class="h-3.5 w-3.5 shrink-0" />
				{headline}
			</p>
			<p class="mt-0.5 text-xs text-fg-secondary">{adjustmentDelta(adj, workoutLabel)}</p>
			{#each adj.reasons as r (r.label)}
				<p class="mt-0.5 text-xs text-fg-muted">{r.label}</p>
			{/each}
		{:else if note}
			<p class="text-xs text-fg-muted">{note}</p>
		{/if}
		{#if actions === 'decide'}
			<div class="mt-2 flex gap-2">
				<button
					type="button"
					class="rounded bg-fg-primary px-3 py-1 text-xs font-medium text-surface-1 disabled:opacity-50"
					disabled={busy}
					onclick={() => run(() => acceptAdjustment(adj!.id, adj!.rev, via))}>수락</button
				>
				<button
					type="button"
					class="rounded border border-border-subtle px-3 py-1 text-xs disabled:opacity-50"
					disabled={busy}
					onclick={() => run(() => revertAdjustment(adj!.id, via))}>거절</button
				>
			</div>
		{:else if actions === 'undo'}
			<button
				type="button"
				class="mt-2 rounded border border-border-subtle px-3 py-1 text-xs disabled:opacity-50"
				disabled={busy}
				onclick={() => run(() => revertAdjustment(adj!.id, via))}>되돌리기</button
			>
		{/if}
		{#if error}<p class="mt-1 text-xs text-semantic-red" role="alert">{error}</p>{/if}
	</div>
{/if}
