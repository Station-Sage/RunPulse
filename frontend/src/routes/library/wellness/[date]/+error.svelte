<script lang="ts">
	// 웰니스 일 상세 오류 — 400(잘못된 날짜)은 오늘로, 그 외는 다시 시도.
	import { page } from '$app/state';
	import { base } from '$app/paths';
	const bad = $derived(page.status === 400);
</script>

<div class="flex flex-col items-center gap-3 px-4 py-16 text-center">
	<h1 class="text-lg font-medium">{bad ? '날짜 형식이 올바르지 않아요' : '웰니스를 불러오지 못했어요'}</h1>
	<p class="max-w-xs text-sm text-fg-secondary">
		{bad ? 'YYYY-MM-DD 형식의 날짜만 볼 수 있어요.' : '잠시 후 다시 시도해 주세요.'}
	</p>
	<a href="{base}/library/wellness" class="rounded-full bg-surface-3 px-4 py-2 text-sm font-medium text-fg-primary">
		오늘 웰니스 보기
	</a>
</div>
