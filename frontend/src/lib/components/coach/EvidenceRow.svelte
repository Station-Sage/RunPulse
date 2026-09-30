<script lang="ts">
	// 답변 근거 칩 줄 (30-coach-chat design §4.4·§7.4) — 2~3개 노출 + "+n 근거", 체크인 칩 상시 노출,
	// 반대 신호(caveat)는 점선 테두리 + 라벨, 옛 답변(legacy)은 안내문 + InfoTag(드릴 없음).
	import type { AnswerEvidence, EvidenceQuoteProps } from '$lib/types';
	import EvidenceQuote from '$lib/components/EvidenceQuote.svelte';
	import { chipLabel, chipTarget, splitVisible } from '$lib/answerEvidence';

	let {
		items,
		legacy = false,
		onOpen
	}: {
		items: AnswerEvidence[];
		legacy?: boolean;
		onOpen: (ev: AnswerEvidence) => void;
	} = $props();

	let expanded = $state(false);
	const split = $derived(splitVisible(items));
	const shown = $derived(expanded ? items : split.visible);

	function propsFor(ev: AnswerEvidence): EvidenceQuoteProps {
		const p: EvidenceQuoteProps = {
			type: ev.type === 'user_input' ? 'user_input' : 'metric',
			label: chipLabel(ev),
			metric: { slug: ev.metric, value: ev.value ?? '' },
			caveat: ev.role === 'caveat'
		};
		if (chipTarget(ev) !== 'none') p.onOpen = () => onOpen(ev);
		return p;
	}
</script>

{#if items.length > 0}
	{#if legacy}
		<p class="mt-2 text-[11px] text-fg-muted" data-testid="evidence-legacy-note">
			당시 Today 근거 — 이 답변의 입력과 다를 수 있어요
		</p>
	{/if}
	<div class="mt-2 flex flex-wrap items-center gap-2" data-testid="evidence-row">
		{#each shown as ev (ev.metric)}
			<EvidenceQuote {...propsFor(ev)} />
		{/each}
		{#if split.hidden.length > 0}
			<button
				type="button"
				class="text-xs text-fg-secondary underline"
				data-testid="evidence-more"
				onclick={() => (expanded = !expanded)}
			>{expanded ? '접기' : `+${split.hidden.length} 근거`}</button>
		{/if}
	</div>
{/if}
