<script lang="ts">
	// 예측에 쓰는 대회 확인 — 노력도 표시가 예측에 반영된다. 변경 시 토스트 + 되돌리기.
	import { base } from '$app/paths';
	import { invalidate } from '$app/navigation';
	import RaceConfirmList from '$lib/components/RaceConfirmList.svelte';
	import Toast from '$lib/components/Toast.svelte';

	let toastOpen = $state(false);
	let undoFn: (() => Promise<void>) | null = null;

	function onChanged(undo: () => Promise<void>) {
		undoFn = undo;
		toastOpen = true;
		// 허브 예측이 바뀌었으니 다음 방문 때 새로 받도록 무효화.
		void invalidate('app:race-hub');
		void invalidate('app:today');
	}
	async function doUndo() {
		toastOpen = false;
		try {
			await undoFn?.();
			void invalidate('app:race-hub');
			void invalidate('app:today');
		} catch {
			/* 되돌리기 실패는 목록 재진입 시 서버 상태로 보정된다 */
		}
	}
</script>

<div class="mx-auto flex max-w-2xl flex-col gap-4 p-4">
	<div class="flex items-center justify-between">
		<a href="{base}/today/race" class="text-sm text-fg-muted hover:text-fg-primary">‹ 레이스 허브</a>
		<h1 class="text-base font-semibold">예측에 쓰는 대회</h1>
		<span class="w-10"></span>
	</div>
	<p class="text-xs text-fg-muted">'전력'으로 표시한 대회만 예측의 기준으로 쓰여요. 표시를 바꾸면 예측이 즉시 달라질 수 있어요.</p>
	<RaceConfirmList {onChanged} />
</div>
<Toast open={toastOpen} message="대회 표시를 저장했어요 · 예측에 반영됩니다" onUndo={doUndo} onDismiss={() => (toastOpen = false)} />
