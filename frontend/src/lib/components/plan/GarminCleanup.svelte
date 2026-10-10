<script lang="ts">
	// 재계획으로 지워진 세션의 Garmin 일정 삭제 — 확인 시트 1회, 실패분만 재시도.
	import { cleanupGarmin, type GarminCleanupResult } from '$lib/api/plan';
	import { confirmText, resultText } from '$lib/garminCleanup';

	let { replanId, dates, undone = false }: { replanId: number; dates: string[]; undone?: boolean } = $props();
	let open = $state(false);
	let busy = $state(false);
	let failedDates = $state<string[] | null>(null);
	let result = $state<GarminCleanupResult | null>(null);
	let error = $state('');
	const left = $derived(failedDates ?? dates);

	async function run() {
		busy = true;
		error = '';
		try {
			result = await cleanupGarmin(replanId);
			failedDates = result.failed.length ? result.failed.map((f) => f.date) : [];
			open = false;
		} catch {
			error = 'Garmin 연결에 실패했어요. 잠시 뒤 다시 시도해 주세요.';
		} finally {
			busy = false;
		}
	}
</script>

{#if undone}
	<p class="text-xs text-fg-secondary">Garmin 일정은 복원되지 않아요. 다시 보내려면 내보내기에서 전송하세요.</p>
{:else if left.length || result}
	<div class="space-y-2 rounded-lg bg-surface-2 p-3 text-sm">
		{#if result}<p>{resultText(result)}</p>{:else}<p>이전 일정이 Garmin 캘린더에 남아 있어요.</p>{/if}
		{#if left.length}
			<button class="min-h-11 rounded-lg bg-surface-1 px-4" disabled={busy} onclick={() => (open = true)}>
				{result ? '실패한 일정 다시 지우기' : 'Garmin에서 지우기'}
			</button>
		{/if}
	</div>
{/if}

{#if open}
	<div class="fixed inset-0 z-50 flex items-end bg-black/40 lg:items-center lg:justify-center" role="dialog" aria-modal="true">
		<div class="w-full space-y-3 rounded-t-2xl bg-surface-1 p-4 lg:max-w-md lg:rounded-2xl">
			<p class="text-sm">{confirmText(left)}</p>
			{#if error}<p class="text-xs text-red-500">{error}</p>{/if}
			<div class="flex gap-2">
				<button class="min-h-11 flex-1 rounded-lg bg-surface-2" disabled={busy} onclick={() => (open = false)}>취소</button>
				<button class="min-h-11 flex-1 rounded-lg bg-red-600 text-white" disabled={busy} onclick={run}>삭제</button>
			</div>
		</div>
	</div>
{/if}
