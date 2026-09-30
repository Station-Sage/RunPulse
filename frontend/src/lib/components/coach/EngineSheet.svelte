<script lang="ts">
	// "원인 보기" — 이 답변이 왜 규칙으로 나갔는지 (30-coach-chat design §7.2).
	import { base } from '$app/paths';
	import type { EngineView } from '$lib/types';
	import { reasonText } from '$lib/coachEngine';

	let { engine, attempted = null, onClose }: {
		engine: EngineView;
		attempted?: { provider: string; model?: string | null } | null;
		onClose: () => void;
	} = $props();
	const shown = $derived(engine.status === 'fallback' ? attempted : engine.provider ? engine : null);
</script>

<div class="fixed inset-0 z-50 flex flex-col" role="dialog" aria-modal="true" aria-label="답변 엔진 상세">
	<button class="absolute inset-0 bg-black/40" onclick={onClose} aria-label="닫기"></button>
	<div class="absolute inset-x-0 bottom-0 flex max-h-[80vh] flex-col gap-3 rounded-t-2xl bg-surface-1 p-4 shadow-lg">
		<h2 class="font-medium">이 답변의 엔진</h2>
		<dl class="grid grid-cols-[5rem_1fr] gap-y-1 text-sm">
			<dt class="text-fg-muted">표시</dt><dd>{engine.label}</dd>
			{#if shown}
				<dt class="text-fg-muted">시도</dt><dd>{shown.provider}{shown.model ? ` · ${shown.model}` : ''}</dd>
			{/if}
			{#if engine.reason}
				<dt class="text-fg-muted">원인</dt><dd>{reasonText(engine.reason)}</dd>
			{/if}
		</dl>
		<div class="flex justify-between text-sm">
			<a href="{base}/settings" class="underline">AI 설정 ›</a>
			<button type="button" onclick={onClose} class="text-fg-secondary">닫기</button>
		</div>
	</div>
</div>
