<script lang="ts">
	import LoadFailure from '$lib/components/LoadFailure.svelte';
	// 활동 소스 비교 페이지 — C4 ProviderComparison 를 전체화면으로 렌더링.
	import type { ProvidersPageData } from './+page';
	import ProviderComparison from '$lib/components/ProviderComparison.svelte';
	import { base } from '$app/paths';

	let { data }: { data: ProvidersPageData } = $props();
</script>

<svelte:head><title>소스 비교 · RunPulse</title></svelte:head>

<!-- 본문 -->
{#if data.failure && !data.comparison}
	<LoadFailure failure={data.failure} retryKey={`app:activity:${data.activityId}`} backHref="{base}/library/{data.activityId}" backLabel="← 활동으로 돌아가기" notFoundText="활동을 찾을 수 없어요" />
{:else}
	<ProviderComparison
		data={data.comparison}
		loading={false}
		error={data.errorMessage}
		showPrimaryReason={true}
	/>
{/if}
