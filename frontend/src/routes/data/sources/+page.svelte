<script lang="ts">
	import type { DataSourcesPageData } from './+page';
	import SourceCard from '$lib/components/data/SourceCard.svelte';
	import ErrorState from '$lib/components/ErrorState.svelte';
	import { invalidateAll } from '$app/navigation';

	let { data }: { data: DataSourcesPageData } = $props();
</script>

<svelte:head><title>소스 · RunPulse</title></svelte:head>

<div class="flex flex-col gap-2 px-4 py-4">
	{#if data.sources}
		{#each data.sources as src (src.provider)}
			<SourceCard source={src} activityCount={src.activity_count} />
		{/each}
	{:else}
		<ErrorState message="소스를 불러오지 못했어요" onRetry={() => invalidateAll()} />
	{/if}
</div>
