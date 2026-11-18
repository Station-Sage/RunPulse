<script lang="ts">
	// 오늘 훈련 상세 분석 — 큐 사용 가능할 때만 노출. 시작 → 진행(단계·조회 도구·경과) → 결과 (V2-AI-CLAUDE-QUEUE E5-d).
	import { onDestroy, onMount } from 'svelte';
	import { cancelDeepAnalysis, getDeepAnalysis, startDeepAnalysis, type DeepState } from '$lib/api/deepAnalysis';
	import type { CoachInput } from '$lib/coachSuggestions';

	let { onAsk }: { onAsk?: (input: CoachInput) => void } = $props();

	let st = $state<DeepState | null>(null);
	let busy = $state(false);
	let msg = $state('');
	let timer: ReturnType<typeof setTimeout> | undefined;

	const running = $derived(st?.run?.state === 'running');
	const STAGE: Record<string, string> = { queued: '대기 중', thinking: '생각하는 중', analyzing: '데이터를 살펴보는 중' };

	async function refresh() {
		st = await getDeepAnalysis().catch(() => null);
		clearTimeout(timer);
		if (st?.run?.state === 'running') timer = setTimeout(refresh, 2000);
	}

	async function start() {
		busy = true;
		msg = '';
		try {
			await startDeepAnalysis(st?.activity_id ?? undefined);
			await refresh();
		} catch (e) {
			msg = (e as { message?: string }).message ?? '분석을 시작하지 못했어요';
		} finally {
			busy = false;
		}
	}

	async function cancel() {
		await cancelDeepAnalysis().catch(() => null);
		await refresh();
	}

	onMount(refresh);
	onDestroy(() => clearTimeout(timer));
</script>

{#if st?.available && st.activity_id}
	<section class="mx-4 my-3 space-y-2 rounded-lg bg-surface-2 p-3 text-sm" data-testid="deep-analysis" aria-label="오늘 훈련 상세 분석">
		<p class="font-medium">오늘 훈련 상세 분석</p>
		{#if running && st.run}
			<p class="text-xs text-fg-secondary" role="status" data-testid="deep-progress">
				{STAGE[st.run.stage] ?? '분석 중'} · {st.run.elapsed}초
				{#if st.run.tools.length}· 조회: {[...new Set(st.run.tools)].join(', ')}{/if}
			</p>
			<button class="min-h-11 rounded-lg bg-surface-1 px-4" onclick={cancel}>취소</button>
		{:else}
			{#if st.run?.state === 'failed'}
				<p class="text-xs text-fg-secondary">이번엔 분석을 완료하지 못했어요{st.run.reason ? ` (${st.run.reason})` : ''}.</p>
			{:else if st.run?.state === 'cancelled'}
				<p class="text-xs text-fg-secondary">분석을 취소했어요.</p>
			{/if}
			{#if st.result}
				<p class="whitespace-pre-wrap" data-testid="deep-result">{st.result.text}</p>
				{#if st.result.suggestions.length && onAsk}
					<div class="flex flex-wrap gap-2">
						{#each st.result.suggestions as s (s)}
							<button class="min-h-11 rounded-full border border-border-subtle px-3 text-xs" onclick={() => onAsk(s)}>{s}</button>
						{/each}
					</div>
				{/if}
			{:else if !st.run}
				<p class="text-xs text-fg-secondary">최근 러닝을 AI가 심박·페이스·랩까지 살펴보고 풀이해요. 1~3분 걸려요.</p>
			{/if}
			{#if msg}<p class="text-xs text-semantic-red" role="alert">{msg}</p>{/if}
			<button class="min-h-11 rounded-lg bg-surface-1 px-4" disabled={busy} onclick={start}>{st.result ? '다시 분석' : '분석 시작'}</button>
		{/if}
	</section>
{/if}
