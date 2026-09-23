<script lang="ts">
	// 활동 소스 비교 페이지 — C4 ProviderComparison 를 전체화면으로 렌더링.
	import type { ProvidersPageData } from './+page';
	import ProviderComparison from '$lib/components/ProviderComparison.svelte';
	import { base } from '$app/paths';

	let { data }: { data: ProvidersPageData } = $props();
</script>

<!-- 헤더 -->
<div class="flex items-center gap-2 border-b border-border-subtle px-4 py-3">
	<a
		href="{base}/library/{data.activityId}"
		class="shrink-0 text-fg-muted"
		aria-label="활동 상세로"
	>←</a>
	<h1 class="text-base font-semibold">소스 비교</h1>
</div>

<!-- 탭 표시 (소스 비교 탭만 활성) -->
<div class="flex border-b border-border-subtle">
	<a
		href="{base}/library/{data.activityId}"
		class="flex-1 py-2.5 text-center text-sm text-fg-muted"
	>요약</a>
	<span class="flex-1 border-b-2 border-fg-primary py-2.5 text-center text-sm font-medium text-fg-primary">
		소스 비교
	</span>
</div>

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
