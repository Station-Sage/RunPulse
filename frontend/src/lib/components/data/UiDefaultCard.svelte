<script lang="ts">
	// 설정 > 화면 — 시작 화면(v1/v2)을 계정별로 고른다(40 design §2.6, ui_default).
	import { getPreferences, patchPreferences, type UiDefault } from '$lib/api/me';
	import { onMount } from 'svelte';

	let value = $state<UiDefault | null>(null);
	let saving = $state(false);
	let error = $state<string | null>(null);

	onMount(async () => {
		try {
			value = (await getPreferences()).ui_default;
		} catch {
			error = '설정을 불러오지 못했어요';
		}
	});

	async function choose(next: UiDefault) {
		if (saving || next === value) return;
		saving = true;
		error = null;
		try {
			value = (await patchPreferences({ ui_default: next })).ui_default;
		} catch {
			error = '저장하지 못했어요. 다시 시도해 주세요';
		} finally {
			saving = false;
		}
	}
</script>

<section class="flex flex-col gap-2 rounded-lg border border-border-subtle bg-surface-2 p-3" data-testid="ui-default-card">
	<span class="text-sm text-fg-primary">시작 화면</span>
	<span class="text-xs text-fg-secondary">앱을 열 때 처음 보이는 화면이에요. 다른 기기에서도 같게 적용돼요.</span>
	<div class="flex gap-2" role="radiogroup" aria-label="시작 화면">
		{#each [['v2', '새 화면'], ['v1', '이전 화면(v1)']] as [id, label] (id)}
			<button
				type="button"
				role="radio"
				aria-checked={value === id}
				disabled={saving || value === null}
				onclick={() => choose(id as UiDefault)}
				data-testid="ui-default-{id}"
				class="flex-1 rounded-lg border px-3 py-2 text-sm disabled:opacity-40 {value === id ? 'border-fg-primary text-fg-primary' : 'border-border-subtle text-fg-secondary'}"
			>
				{label}
			</button>
		{/each}
	</div>
	{#if error}<p class="text-xs text-red-400" role="alert">{error}</p>{/if}
</section>
