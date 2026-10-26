<script lang="ts">
	// QuickInput 체크인 섹션 — 저장 상태·오류를 자체 소유한다.
	import { postCheckin } from '$lib/api/today';
	import { toQuickInputExisting } from '$lib/checkinView';
	import type { CheckinRow, PainLevel } from '$lib/types';
	import QuickInput from '$lib/components/QuickInput.svelte';

	let { initial }: { initial: CheckinRow | null } = $props();

	let checkin = $state<CheckinRow | null>(initial);
	let saving = $state(false);
	let error = $state<string | null>(null);

	async function handleSave(value: { fatigue?: number; pain?: PainLevel; note?: string }) {
		saving = true;
		error = null;
		try {
			checkin = await postCheckin(value);
		} catch (e) {
			error = e instanceof Error ? e.message : '저장에 실패했습니다.';
		} finally {
			saving = false;
		}
	}
</script>

<div class="flex flex-col gap-1 border-t border-border-subtle px-4 py-3">
	<QuickInput compact existing={toQuickInputExisting(checkin)} {saving} onSave={handleSave} />
	<p class="text-xs text-fg-muted">입력한 컨디션은 오늘 훈련 답변에 반영됩니다.</p>
	{#if error}
		<p class="text-xs text-semantic-red">{error}</p>
	{/if}
</div>
