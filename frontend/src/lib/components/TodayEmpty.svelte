<script lang="ts">
	// Today 빈 상태(S2a/S2c) — 생애주기별 다음 행동 1개 + 체크인 입력 노출(DESIGN-P7-REVIEW03 §2.5).
	import { base } from '$app/paths';
	import { onMount } from 'svelte';
	import EmptyState from '$lib/components/EmptyState.svelte';
	import QuickInput from '$lib/components/QuickInput.svelte';
	import { getSyncState } from '$lib/api/data';
	import { redirectToWelcomeIfNew } from '$lib/welcomeRedirect';
	import { postCheckin } from '$lib/api/today';
	import { lifecycleOf, todayEmptyCopy, type Lifecycle } from '$lib/states';

	let life = $state<Lifecycle>('unconnected');
	let saving = $state(false);
	let error = $state<string | null>(null);

	onMount(() => {
		getSyncState()
			.then(async (s) => {
				life = lifecycleOf(s);
				await redirectToWelcomeIfNew();
			})
			.catch(() => {});
	});

	const copy = $derived(todayEmptyCopy(life));

	async function save(value: { fatigue?: number; pain?: import('$lib/types').PainLevel; note?: string }) {
		saving = true;
		error = null;
		try {
			await postCheckin(value);
		} catch (e) {
			error = e instanceof Error ? e.message : '저장에 실패했습니다.';
		} finally {
			saving = false;
		}
	}
</script>

<div class="flex flex-col gap-4 px-4 py-10">
	<EmptyState title={copy.title} description={copy.description} actionLabel={copy.actionLabel} actionHref="{base}{copy.href}" />
	<QuickInput compact={true} saving={saving} dismissDate="" onSave={save} />
	{#if error}<p class="text-center text-xs text-semantic-red">{error}</p>{/if}
</div>
