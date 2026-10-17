<script lang="ts">
	// NEW-12·17 — 질병 정보를 AI 코치와 나눌지 한 번만 묻는다. '동의 안 함' 이후엔 다시 묻지 않는다.
	import { postConsent } from '$lib/api/context';

	let { via, onClose }: { via: 'first_input' | 'settings'; onClose: () => void } = $props();
	let busy = $state(false);
	let error = $state<string | null>(null);

	async function choose(action: 'grant' | 'decline') {
		busy = true; error = null;
		try { await postConsent(action, via); onClose(); }
		catch (e) { error = e instanceof Error ? e.message : '저장하지 못했어요'; busy = false; }
	}
</script>

<div class="fixed inset-0 z-50 flex items-end bg-black/40 lg:items-center lg:justify-center" role="dialog" aria-modal="true" aria-labelledby="illness-consent-title">
	<div class="w-full space-y-3 rounded-t-2xl bg-surface-1 p-4 lg:max-w-md lg:rounded-2xl">
		<p id="illness-consent-title" class="text-sm font-medium text-fg-primary">아팠던 기록을 AI 코치와 나눌까요?</p>
		<p class="text-xs text-fg-secondary">나누면 코치가 컨디션을 더 정확히 이해해요. 나누지 않아도 훈련 조정에는 그대로 쓰이고, AI에는 '컨디션 신호'로만 전달돼요. 설정에서 언제든 바꿀 수 있어요.</p>
		{#if error}<p class="text-xs text-semantic-red">{error}</p>{/if}
		<div class="flex gap-2">
			<button type="button" class="min-h-11 flex-1 rounded-lg bg-surface-2 focus-visible:outline focus-visible:outline-2 focus-visible:outline-semantic-teal" disabled={busy} onclick={() => choose('decline')}>동의 안 함</button>
			<button type="button" class="min-h-11 flex-1 rounded-lg bg-semantic-teal text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-semantic-teal" disabled={busy} onclick={() => choose('grant')}>동의</button>
		</div>
	</div>
</div>
