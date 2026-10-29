<script lang="ts">
	// 새 대화 입력 폼(textarea + 엔진 줄 + 취소/전송). 입력값은 폼이 소유한다.
	import type { CoachEngine } from '$lib/types';
	import EngineLine from './EngineLine.svelte';

	let {
		engine,
		sending,
		errorMessage,
		onSubmit,
		onCancel,
		onOpenScope
	}: {
		engine: CoachEngine | null;
		sending: boolean;
		errorMessage: string | null;
		onSubmit: (msg: string) => void;
		onCancel: () => void;
		onOpenScope: () => void;
	} = $props();

	let newInput = $state('');

	function submitNew() {
		const msg = newInput.trim();
		if (msg) onSubmit(msg);
	}

	function handleKeydown(e: KeyboardEvent) {
		// 한글 IME 조합 중 Enter는 글자 확정용 — 전송하면 마지막 글자가 중복·누락된다.
		if (e.isComposing || e.keyCode === 229) return;
		if (e.key === 'Enter' && !e.shiftKey) {
			e.preventDefault();
			submitNew();
		}
	}
</script>

<div class="border-t border-border-subtle px-4 py-3">
	<textarea
		bind:value={newInput}
		onkeydown={handleKeydown}
		placeholder="무엇이든 물어보세요…"
		rows={3}
		disabled={sending}
		class="w-full resize-none min-h-11 rounded-lg border border-border-subtle bg-surface-2 px-3 py-2 text-sm text-fg-primary placeholder:text-fg-muted focus:outline-none disabled:opacity-50"
	></textarea>
	<div class="mt-1">
		<EngineLine {engine} {onOpenScope} />
	</div>
	<div class="mt-2 flex justify-end gap-2">
		<button
			type="button"
			onclick={onCancel}
			disabled={sending}
			class="min-h-11 rounded-lg border border-border-subtle px-4 py-2 text-sm text-fg-secondary disabled:opacity-50"
		>
			취소
		</button>
		<button
			type="button"
			onclick={submitNew}
			disabled={sending || !newInput.trim()}
			class="min-h-11 rounded-lg bg-fg-primary px-4 py-2 text-sm text-surface-1 disabled:opacity-40"
		>
			{sending ? '전송 중…' : '전송'}
		</button>
	</div>
	{#if errorMessage}
		<p class="mt-1 text-xs text-semantic-red">{errorMessage}</p>
	{/if}
</div>
