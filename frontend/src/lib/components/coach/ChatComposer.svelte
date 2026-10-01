<script lang="ts">
	// 대화 입력 바 — 엔진 라벨 + 텍스트 입력. 전송 중에도 입력은 열어 둔다(design §6.2 sending).
	import EngineLine from './EngineLine.svelte';
	import type { CoachEngine } from '$lib/types';

	let {
		engine,
		value = $bindable(''),
		busy = false,
		onSend,
		onOpenScope
	}: {
		engine: CoachEngine | null;
		value: string;
		busy?: boolean;
		onSend: () => void;
		onOpenScope: () => void;
	} = $props();

	function handleKeydown(e: KeyboardEvent) {
		// 한글 IME 조합 중 Enter는 글자 확정용 — 전송하면 마지막 글자가 중복·누락된다.
		if (e.isComposing || e.keyCode === 229) return;
		if (e.key === 'Enter' && !e.shiftKey) {
			e.preventDefault();
			if (!busy) onSend();
		}
	}
</script>

<div class="sticky bottom-14 lg:bottom-0 z-10 flex flex-col gap-1 border-t border-border-subtle bg-surface-1 px-4 py-3">
	<EngineLine {engine} {onOpenScope} />
	<div class="flex items-end gap-2">
		<textarea
			bind:value
			onkeydown={handleKeydown}
			placeholder="메시지 입력…"
			rows={1}
			class="flex-1 resize-none rounded-lg border border-border-subtle bg-surface-2 px-3 py-2 text-sm text-fg-primary placeholder:text-fg-muted focus:outline-none"
			style="min-height:2.25rem; max-height:8rem; overflow-y:auto;"
		></textarea>
		<button
			type="button"
			onclick={onSend}
			disabled={busy || !value.trim()}
			class="rounded-lg bg-fg-primary px-4 py-2 text-sm text-surface-1 disabled:opacity-40"
			aria-label="전송"
		>
			전송
		</button>
	</div>
</div>
