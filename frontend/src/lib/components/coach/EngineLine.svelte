<script lang="ts">
	// 입력창 위 한 줄 — 현재 답변 엔진 + 전송 범위 시트 진입 (30-coach-chat design §7.2).
	import type { CoachEngine } from '$lib/types';
	import { engineLineText } from '$lib/coachEngine';

	let { engine, onOpenScope }: { engine: CoachEngine | null; onOpenScope: () => void } = $props();
	const text = $derived(engineLineText(engine));
</script>

{#if engine}
	<div class="flex items-center justify-between gap-2 text-[11px] text-fg-muted" data-testid="engine-line">
		<span class="min-w-0 truncate">{text}</span>
		<button type="button" onclick={onOpenScope} class="shrink-0 underline">전송 범위 ›</button>
	</div>
{/if}
