<script lang="ts">
	// 건강 정보 포함 내보내기 확인 — 취소하면 아무 요청도 보내지 않는다.
	import { modal } from '$lib/overlay';

	let { onConfirm, onCancel }: { onConfirm: () => void; onCancel: () => void } = $props();
</script>

<div class="fixed inset-0 z-50 flex items-end bg-scrim lg:items-center lg:justify-center" role="dialog" aria-modal="true" aria-labelledby="export-confirm-title" use:modal={{ onClose: onCancel }}>
	<div class="w-full space-y-3 rounded-t-2xl bg-surface-1 p-4 lg:max-w-md lg:rounded-2xl">
		<p id="export-confirm-title" class="text-sm font-medium text-fg-primary">건강 정보가 담긴 파일을 만들까요?</p>
		<p class="text-xs text-fg-secondary">아프거나 쉬었던 기록이 파일에 들어가요. 파일은 24시간 뒤 자동으로 지워지니, 받은 뒤 보관에 주의해 주세요.</p>
		<div class="flex gap-2">
			<button type="button" class="min-h-11 flex-1 rounded-lg bg-surface-2" onclick={onCancel}>취소</button>
			<button type="button" class="min-h-11 flex-1 rounded-lg bg-semantic-teal text-fg-on-accent" onclick={onConfirm}>만들기</button>
		</div>
	</div>
</div>
