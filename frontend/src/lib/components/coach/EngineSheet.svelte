<script lang="ts">
	// "원인 보기" — 이 답변이 왜 규칙으로 나갔는지 (30-coach-chat design §7.2).
	import { base } from '$app/paths';
	import type { EngineView } from '$lib/types';
	import { modal } from '$lib/overlay';
	import { attemptLines, reasonText } from '$lib/coachEngine';

	let { engine, attempted = null, onClose }: {
		engine: EngineView;
		attempted?: { provider: string; model?: string | null } | null;
		onClose: () => void;
	} = $props();
	const shown = $derived(engine.status === 'fallback' ? attempted : engine.provider ? { provider: engine.provider, model: engine.model } : null);
	// S4-87: 실제 시도 목록(재시도 포함). 서버가 attempts 를 주지 않는 옛 응답만 추정(shown) 한 줄.
	const lines = $derived(attemptLines(engine.attempts, shown));
</script>

<div class="fixed inset-0 z-50 flex flex-col" role="dialog" aria-modal="true" aria-labelledby="engine-sheet-h" use:modal={{ onClose }}>
	<button class="absolute inset-0 bg-scrim" onclick={onClose} aria-label="닫기"></button>
	<div class="absolute inset-x-0 bottom-0 sheet-bottom flex flex-col gap-3 rounded-t-2xl bg-surface-1 p-4 shadow-lg">
		<h2 id="engine-sheet-h" class="font-medium">이 답변의 엔진</h2>
		<dl class="grid grid-cols-[5rem_1fr] gap-y-1 text-sm">
			<dt class="text-fg-muted">표시</dt><dd>{engine.label}</dd>
			{#if lines.length}
				<dt class="text-fg-muted">시도</dt>
				<dd>{#each lines as l, i (i)}<span class="block">{l}</span>{/each}</dd>
			{/if}
			{#if engine.reason && !(engine.status === 'ok' && lines.length)}
				<!-- S4-88: 재시도로 성공한 답변은 위 시도 줄이 실패 사유를 이미 보여 준다(중복 행 숨김) -->
				<dt class="text-fg-muted">원인</dt><dd>{reasonText(engine.reason)}</dd>
			{/if}
		</dl>
		<div class="flex justify-between text-sm">
			<a href="{base}/data/settings/ai" class="underline">AI 설정 ›</a>
			<button type="button" onclick={onClose} class="text-fg-secondary">닫기</button>
		</div>
	</div>
</div>
