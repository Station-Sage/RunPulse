<script lang="ts">
	import type { ProfilePageData } from './+page';
	import type { ProfileRow } from '$lib/api/data';
	import BaselineRow from '$lib/components/data/BaselineRow.svelte';
	import ErrorState from '$lib/components/ErrorState.svelte';
	import { invalidateAll } from '$app/navigation';

	let { data }: { data: ProfilePageData } = $props();
	let saved = $state<ProfileRow[] | null>(null);
	const rows = $derived(saved ?? data.rows);
</script>

<svelte:head><title>러너 기준값 · RunPulse</title></svelte:head>

<div class="flex flex-col gap-2 px-4 py-4">
	{#if rows}
		<p class="text-xs text-fg-muted">
			존·페이스 계산에 쓸 값을 골라요. 바꾼 값은 이후 계산부터 적용돼요.
		</p>
		{#each rows as row (row.key)}
			<BaselineRow {row} onSaved={(r) => (saved = r)} />
		{/each}
	{:else}
		<ErrorState message="기준값을 불러오지 못했어요" onRetry={() => invalidateAll()} />
	{/if}
</div>
