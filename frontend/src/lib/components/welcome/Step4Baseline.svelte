<script lang="ts">
	// 4/4 기준값(선택) — 최대심박·역치 페이스. 비우면 기록에서 추정.
	import { getProfile, patchProfile } from '$lib/api/data';
	import { onMount } from 'svelte';

	let hrmax = $state('');
	let pace = $state('');
	let msg = $state<string | null>(null);
	onMount(async () => {
		try {
			const rows = (await getProfile()).rows;
			const cur = (k: string) => rows.find((r) => r.key === k);
			hrmax = String(cur('hrmax')?.manual?.value ?? '');
			pace = String(cur('threshold_pace')?.manual?.value ?? '');
		} catch {
			/* 기준값은 선택 항목 */
		}
	});
	async function save() {
		const overrides: Record<string, number> = {};
		if (Number(hrmax) > 0) overrides.hrmax = Number(hrmax);
		if (Number(pace) > 0) overrides.threshold_pace = Number(pace);
		try {
			await patchProfile({ overrides });
			msg = '저장했어요';
		} catch {
			msg = '저장하지 못했어요. 나중에 설정에서 입력할 수 있어요.';
		}
	}
</script>

<div class="flex flex-col gap-3">
	<h2 class="text-base font-semibold text-fg-primary">4/4 · 기준값 (선택)</h2>
	<p class="text-xs text-fg-muted">모르면 비워두세요. 기록에서 추정해요.</p>
	<label class="text-xs text-fg-secondary">최대심박 (bpm)
		<input class="mt-1 w-full rounded border border-border-subtle bg-surface-1 p-2 text-sm" inputmode="numeric" bind:value={hrmax} />
	</label>
	<label class="text-xs text-fg-secondary">역치 페이스 (초/km)
		<input class="mt-1 w-full rounded border border-border-subtle bg-surface-1 p-2 text-sm" inputmode="numeric" bind:value={pace} />
	</label>
	<button type="button" class="self-start rounded-lg bg-surface-3 px-3 py-1.5 text-sm" onclick={save}>저장</button>
	{#if msg}<p class="text-xs text-fg-muted">{msg}</p>{/if}
</div>
