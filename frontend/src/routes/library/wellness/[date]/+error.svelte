<script lang="ts">
	import PageHead from '$lib/components/ui/PageHead.svelte';
	// 웰니스 일 상세 오류 — 400(형식 오류·없는 날짜)은 오늘로, 그 외는 다시 시도. M-24: 없는 날짜는 따로 안내.
	import { page } from '$app/state';
	import { base } from '$app/paths';
	import { DATE_ERROR_TEXT } from '$lib/wellnessDay';
	const bad = $derived(page.status === 400);
	const text = $derived(page.error?.message === DATE_ERROR_TEXT.nonexistent.title ? DATE_ERROR_TEXT.nonexistent : DATE_ERROR_TEXT.format);
</script>

<div class="flex flex-col items-center gap-3 px-4 py-16 text-center">
	<PageHead
		title={bad ? text.title : '웰니스를 불러오지 못했어요'}
		class="text-lg font-medium"
	/>
	<p class="max-w-xs text-sm text-fg-secondary">
		{bad ? text.body : '잠시 후 다시 시도해 주세요.'}
	</p>
	<a href="{base}/library/wellness" class="rounded-full bg-surface-3 px-4 py-2 text-sm font-medium text-fg-primary">
		오늘 웰니스 보기
	</a>
</div>
