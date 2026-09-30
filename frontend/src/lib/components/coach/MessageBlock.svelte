<script lang="ts">
	// Coach 답변 말풍선 — 엔진 라벨, 폴백/AI 미설정/오류 배너, 근거 칩 (30-coach-chat design §7.2).
	import { base } from '$app/paths';
	import type { AnswerEvidence, ChatMessage } from '$lib/types';
	import ChatBody from '$lib/components/ChatBody.svelte';
	import EvidenceRow from './EvidenceRow.svelte';
	import { driftText } from '$lib/answerEvidence';
	import { bannerFor, reasonText } from '$lib/coachEngine';

	let {
		msg,
		regenerating = false,
		onEvidence,
		onRegenerate,
		onShowReason
	}: {
		msg: ChatMessage;
		regenerating?: boolean;
		onEvidence: (ev: AnswerEvidence) => void;
		onRegenerate: (id: number) => void;
		onShowReason: (msg: ChatMessage) => void;
	} = $props();

	const engine = $derived(msg.engine);
	const banner = $derived(bannerFor(engine));
	const label = $derived(engine?.label ?? '');
	const drift = $derived(driftText(msg.evidence));
</script>

<div class="flex justify-start">
	<div class="max-w-[80%] rounded-2xl rounded-bl-sm border border-border-subtle bg-surface-2 px-3 py-2 text-sm text-fg-primary">
		<ChatBody content={msg.content} />
		{#if label}
			<p class="mt-1 text-[11px] font-medium text-fg-secondary" data-testid="engine-label">{label}</p>
		{/if}

		{#if banner === 'fallback'}
			<div
				class="mt-2 rounded-lg border border-semantic-amber/40 bg-semantic-amber/10 px-3 py-2 text-xs text-fg-secondary"
				data-testid="fallback-banner"
			>
				AI 연결에 실패해 기본 규칙으로 답했어요 · {reasonText(engine?.reason)}
				<div class="mt-1 flex gap-3">
					<button type="button" class="underline disabled:opacity-40" disabled={regenerating}
						data-testid="regenerate" onclick={() => onRegenerate(msg.id)}
					>{regenerating ? '다시 생성 중…' : 'AI로 다시 생성'}</button>
					<button type="button" class="underline" onclick={() => onShowReason(msg)}>원인 보기 ›</button>
				</div>
			</div>
		{:else if banner === 'rule_only'}
			<a href="{base}/settings" class="mt-1 inline-block text-[11px] underline text-fg-secondary">AI 설정 ›</a>
		{:else if banner === 'error'}
			<p class="mt-1 text-[11px] text-semantic-red">
				답변을 만들지 못했어요 ({reasonText(engine?.reason)}) ·
				<button type="button" class="underline" disabled={regenerating} onclick={() => onRegenerate(msg.id)}>↻ 다시 생성</button>
			</p>
		{/if}
		{#if msg.as_of}
			<p class="mt-0.5 text-[10px] text-fg-muted">{msg.as_of} 기준</p>
		{/if}

		{#if msg.evidence && msg.evidence.length > 0}
			<EvidenceRow items={msg.evidence} legacy={msg.evidence_legacy} onOpen={onEvidence} />
		{/if}
		{#if drift}
			<p
				class="mt-2 rounded-lg border border-semantic-amber/40 bg-semantic-amber/10 px-3 py-1.5 text-xs text-fg-secondary"
				data-testid="drift-banner"
			>{drift}</p>
		{/if}
	</div>
</div>
