<script lang="ts">
	// AI 초안 — 규칙 일정을 4주 범위에서 다듬어 제안. 검증을 통과한 초안만 적용 가능 (V2-AI-CLAUDE-QUEUE E5-c).
	import { onDestroy, onMount } from 'svelte';
	import { applyPlanDraft, getPlanDraft, startPlanDraft, type PlanDraftState } from '$lib/api/plan';
	import type { ReplanParams, ReplanPreview } from '$lib/types';

	let { params, anchor, disabled = false, onApplied }: {
		params: ReplanParams;
		anchor: string;
		disabled?: boolean;
		onApplied: (r: ReplanPreview) => void;
	} = $props();

	let st = $state<PlanDraftState | null>(null);
	let busy = $state(false);
	let confirm = $state(false);
	let msg = $state('');
	let timer: ReturnType<typeof setTimeout> | undefined;

	async function refresh() {
		st = await getPlanDraft().catch(() => null);
		if (st?.running) timer = setTimeout(refresh, 3000);
	}

	async function start() {
		busy = true;
		msg = '';
		try {
			await startPlanDraft(params);
			await refresh();
		} catch (e) {
			msg = (e as { message?: string }).message ?? 'AI 초안을 시작하지 못했어요';
		} finally {
			busy = false;
		}
	}

	async function apply() {
		busy = true;
		confirm = false;
		msg = '';
		try {
			onApplied(await applyPlanDraft(anchor));
		} catch (e) {
			msg = (e as { message?: string }).message ?? 'AI 초안을 적용하지 못했어요';
		} finally {
			busy = false;
		}
	}

	const fresh = $derived(st?.state === 'ready' && st.anchor_monday === anchor);

	onMount(refresh);
	onDestroy(() => clearTimeout(timer));
</script>

{#if st?.available}
	<section class="space-y-2 rounded-lg bg-surface-2 p-3 text-sm" data-testid="plan-draft" aria-label="AI 초안">
		<p class="font-medium">AI 초안 (선택)</p>
		{#if st.running}
			<p class="text-xs text-fg-secondary" role="status">AI가 앞으로 4주를 다듬고 있어요. 1~3분 걸려요.</p>
		{:else}
			<p class="text-xs text-fg-secondary">위 일정은 규칙으로 계산한 거예요. AI가 쉬운 날·롱런 거리와 설명을 4주 범위에서 ±15%까지 다듬어 제안해요. 날짜·훈련 종류·페이스는 그대로예요.</p>
		{/if}
		{#if fresh}
			<p data-testid="plan-draft-summary">{st.summary} <span class="text-fg-secondary">({st.changed}개 세션 변경)</span></p>
		{:else if st?.state === 'failed'}
			<p class="text-xs text-fg-secondary">이번엔 쓸 만한 초안이 나오지 않았어요{st.reason ? ` (${st.reason})` : ''}. 규칙 일정이 그대로 유지돼요.</p>
		{/if}
		{#if msg}<p class="text-xs text-semantic-red" role="alert">{msg}</p>{/if}
		<div class="flex flex-wrap gap-2">
			<button class="min-h-11 rounded-lg bg-surface-1 px-4" disabled={busy || st.running || disabled} onclick={start}>
				{fresh ? '다시 만들기' : 'AI 초안 만들기'}
			</button>
			{#if fresh}
				<button class="min-h-11 rounded-lg bg-accent px-4" disabled={busy || disabled} onclick={() => (confirm = true)}>초안 적용</button>
			{/if}
		</div>
		{#if confirm}
			<span role="group" aria-label="초안 적용 확인" class="flex flex-wrap items-center gap-2 text-xs">
				<span>규칙 일정 대신 AI 초안을 적용해요. 적용 후 되돌릴 수 있어요.</span>
				<button class="min-h-11 font-medium underline" onclick={apply}>적용 진행</button>
				<button class="min-h-11 underline" onclick={() => (confirm = false)}>취소</button>
			</span>
		{/if}
	</section>
{/if}
