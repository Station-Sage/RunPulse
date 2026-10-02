<script lang="ts">
	// 활동 소스 비교 페이지 — C4 ProviderComparison 를 전체화면으로 렌더링.
	import type { ProvidersPageData } from './+page';
	import ProviderComparison from '$lib/components/ProviderComparison.svelte';
	import { base } from '$app/paths';

	let { data }: { data: ProvidersPageData } = $props();
</script>

<svelte:head><title>소스 비교 · RunPulse</title></svelte:head>

<!-- 본문 -->
{#if data.errorMessage && !data.comparison}
	<div class="px-4 py-8 text-center">
		<p class="text-sm text-fg-secondary">{data.errorMessage}</p>
		<a href="{base}/library/{data.activityId}" class="mt-2 block text-xs text-fg-muted underline">
			← 활동으로 돌아가기
		</a>
	</div>
{:else}
	<ProviderComparison
		data={data.comparison}
		loading={false}
		error={data.errorMessage}
		showPrimaryReason={true}
	/>
{/if}
