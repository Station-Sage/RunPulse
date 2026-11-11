<script lang="ts">
	// 4/4 기준값(선택) — 최대심박·역치 페이스. 비우면 기록에서 추정.
	import { getProfile, patchProfile } from '$lib/api/data';
	import { onMount } from 'svelte';
	import { ApiError } from '$lib/api/client';
	import { checkProfileInput, formatProfileValue } from '$lib/profileRows';

	let hrmax = $state('');
	let pace = $state('');
	let msg = $state<string | null>(null);
	onMount(async () => {
		try {
			const rows = (await getProfile()).rows;
			const cur = (k: string) => rows.find((r) => r.key === k);
			hrmax = String(cur('hrmax')?.manual?.value ?? '');
			const p = cur('threshold_pace')?.manual?.value;
			pace = p != null ? formatProfileValue('threshold_pace', p).replace('/km', '') : '';
		} catch {
			/* 기준값은 선택 항목 */
		}
	});
	// S-19: 칸마다 범위·형식 검사 — 틀린 칸을 바로 알리고 저장을 막는다(서버 범위와 같은 값)
	const hr = $derived(checkProfileInput('hrmax', hrmax));
	const tp = $derived(checkProfileInput('threshold_pace', pace));
	const canSave = $derived(!hr.error && !tp.error && (hr.value != null || tp.value != null));
	async function save() {
		if (!canSave) return;
		const overrides: Record<string, number> = {};
		if (hr.value != null) overrides.hrmax = hr.value;
		if (tp.value != null) overrides.threshold_pace = tp.value;
		try {
			await patchProfile({ overrides });
			msg = '저장했어요';
		} catch (e) {
			msg = e instanceof ApiError && e.status === 400 ? `저장하지 못했어요: ${e.message}` : '저장하지 못했어요. 나중에 설정에서 입력할 수 있어요.';
		}
	}
</script>

<div class="flex flex-col gap-3">
	<h2 class="text-base font-semibold text-fg-primary">4/4 · 기준값 (선택)</h2>
	<p class="text-xs text-fg-muted">모르면 비워두세요. 기록에서 추정해요.</p>
	<label class="text-xs text-fg-secondary">최대심박 (bpm)
		<input class="mt-1 min-h-11 w-full rounded border border-border-subtle bg-surface-1 p-2 text-sm" inputmode="numeric" placeholder="예: 185"
			aria-invalid={!!hr.error} bind:value={hrmax} />
		{#if hr.error}<span class="mt-1 block text-semantic-red" data-testid="hrmax-error">{hr.error}</span>{/if}
	</label>
	<label class="text-xs text-fg-secondary">역치 페이스 (분:초/km)
		<input class="mt-1 min-h-11 w-full rounded border border-border-subtle bg-surface-1 p-2 text-sm" inputmode="text" placeholder="예: 5:10"
			aria-invalid={!!tp.error} bind:value={pace} />
		{#if tp.error}<span class="mt-1 block text-semantic-red" data-testid="pace-error">{tp.error}</span>{/if}
	</label>
	<button type="button" class="min-h-11 self-start rounded-lg bg-surface-3 px-3 py-1.5 text-sm disabled:opacity-40" disabled={!canSave} onclick={save}>저장</button>
	{#if msg}<p class="text-xs text-fg-muted">{msg}</p>{/if}
</div>
