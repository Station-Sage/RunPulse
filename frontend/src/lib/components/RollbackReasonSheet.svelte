<script lang="ts">
	// G5 게이트 — v1 복귀 사유 한 문항. 선택 즉시 확정, 건너뛰기도 가능. 어떤 경우든 v1로 이동한다.
	import { ROLLBACK_REASONS, NOTE_MAX, type RollbackReason } from '$lib/rollback';
	import { rollback } from '$lib/api/uiEvents';

	let { open, onClose }: { open: boolean; onClose: () => void } = $props();

	let note = $state('');
	let busy = $state(false);

	async function submit(reason: RollbackReason | null) {
		if (busy) return;
		busy = true;
		await rollback(reason, note, (url) => location.assign(url));
	}
</script>

{#if open}
	<div class="fixed inset-0 z-[60] flex items-end justify-center sm:items-center" role="dialog" aria-modal="true" aria-label="이전 화면으로 돌아가기" data-testid="rollback-sheet">
		<button class="absolute inset-0 bg-black/50" onclick={onClose} aria-label="닫기" disabled={busy}></button>
		<div class="relative flex w-full max-w-md flex-col gap-3 rounded-t-xl bg-surface-1 p-4 pb-[calc(1rem+env(safe-area-inset-bottom))] shadow-lg sm:rounded-xl">
			<p class="text-sm font-medium text-fg-primary">이전 화면으로 돌아가는 이유가 궁금해요</p>
			<div class="flex flex-col gap-1">
				{#each ROLLBACK_REASONS as r (r.value)}
					<button type="button" disabled={busy} onclick={() => submit(r.value)}
						class="h-11 rounded border border-border-subtle bg-surface-2 px-3 text-left text-sm text-fg-secondary hover:bg-surface-3 disabled:opacity-40">{r.label}</button>
				{/each}
			</div>
			<details class="text-xs text-fg-muted">
				<summary class="cursor-pointer py-1">자세히 알려주기 (선택)</summary>
				<textarea bind:value={note} maxlength={NOTE_MAX} rows="2" aria-label="추가 의견"
					class="mt-1 w-full rounded border border-border-subtle bg-surface-2 p-2 text-sm text-fg-primary"></textarea>
				<span>사유를 고르면 함께 저장돼요 ({note.length}/{NOTE_MAX})</span>
			</details>
			<div class="flex justify-between">
				<button type="button" onclick={onClose} disabled={busy} class="h-11 px-2 text-sm text-fg-muted hover:text-fg-primary">취소</button>
				<button type="button" onclick={() => submit(null)} disabled={busy} data-testid="rollback-skip"
					class="h-11 px-2 text-sm text-fg-secondary hover:text-fg-primary disabled:opacity-40">건너뛰고 이동</button>
			</div>
		</div>
	</div>
{/if}
