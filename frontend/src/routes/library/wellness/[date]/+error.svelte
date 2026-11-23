<script lang="ts">
	import PageHead from '$lib/components/ui/PageHead.svelte';
	// 웰니스 일 상세 오류 — 400(형식 오류·없는 날짜)은 오늘로, 그 외는 다시 시도. M-24: 없는 날짜는 따로 안내.
	import { page } from '$app/state';
	import { base } from '$app/paths';
	import { invalidateAll } from '$app/navigation';
	import ErrorState from '$lib/components/ErrorState.svelte';
	import { failureMessage } from '$lib/loadFailure';
	import { DATE_ERROR_TEXT } from '$lib/wellnessDay';
	const bad = $derived(page.status === 400);
	const text = $derived(page.error?.message === DATE_ERROR_TEXT.nonexistent.title ? DATE_ERROR_TEXT.nonexistent : DATE_ERROR_TEXT.format);
</script>

<div class="flex flex-col items-center gap-3 px-4 py-16 text-center">
	<PageHead
		title={bad ? text.title : '웰니스를 불러오지 못했어요'}
		class="text-lg font-medium"
	/>
	{#if bad}
		<p class="max-w-xs text-sm text-fg-secondary">{text.body}</p>
	{:else}
		<!-- +error 는 sanitize 된 오류만 받아 원인 분류가 불가 — 서버 오류 문구 + 다시 시도 -->
		<ErrorState message={failureMessage('server')} onRetry={() => invalidateAll()} />
	{/if}
	<a href="{base}/library/wellness" class="rounded-full bg-surface-3 px-4 py-2 text-sm font-medium text-fg-primary">
		오늘 웰니스 보기
	</a>
</div>
