<script lang="ts">
	// 진행 중 답변의 상태 줄 — 단계 문구·[중단]·느림 안내·재연결 안내 (30-coach-chat design §6.2·§7.1).
	import { stageLine } from '$lib/coachStream';
	import type { LiveEntry } from '$lib/coachLive.svelte';

	let {
		live,
		onCancel,
		onKeepWaiting,
		onRuleAnswer
	}: {
		live: LiveEntry;
		onCancel: () => void;
		onKeepWaiting: () => void;
		onRuleAnswer: () => void;
	} = $props();

	const stream = $derived(live.stream);
	const writing = $derived(stream.phase === 'streaming');
</script>

<div class="mt-1 space-y-1 text-xs text-fg-secondary" data-testid="stream-status">
	{#if stream.fallbackReason}
		<p class="rounded-lg border border-semantic-amber/40 bg-semantic-amber/10 px-2 py-1" data-testid="stream-fallback">
			AI 연결에 실패해 기본 규칙으로 답하는 중이에요
		</p>
	{/if}
	<p class="flex items-center gap-2" aria-live="polite">
		<span class="animate-pulse" aria-hidden="true">◌</span>
		<span data-testid="stage-line">{writing ? '답변 작성 중…' : stageLine(stream)}</span>
		<button type="button" class="ml-auto underline" data-testid="cancel-stream" onclick={onCancel}>중단</button>
	</p>
	{#if live.reconnecting}
		<p class="text-semantic-amber" data-testid="reconnecting">연결을 다시 잇는 중…</p>
	{/if}
	{#if live.slow}
		<p data-testid="slow-hint">
			평소보다 오래 걸려요 ·
			<button type="button" class="underline" onclick={onKeepWaiting}>계속 기다리기</button> ·
			<button type="button" class="underline" data-testid="rule-answer" onclick={onRuleAnswer}>기본 답변 받기</button>
		</p>
	{/if}
</div>
