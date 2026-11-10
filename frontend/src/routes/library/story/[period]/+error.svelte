<script lang="ts">
	import PageHead from '$lib/components/ui/PageHead.svelte';
	// 이야기 기간 오류(M-16) — 볼 수 있는 기간 형식을 알려 주고 이번 달로 보낸다. 그 외 오류는 다시 시도.
	import { page } from '$app/state';
	import { base } from '$app/paths';
	import { thisMonthId } from '$lib/storyPeriod';
	const bad = $derived(page.status === 404);
</script>

<div class="flex flex-col items-center gap-3 px-4 py-16 text-center">
	<PageHead title={bad ? '볼 수 없는 기간이에요' : '이야기를 불러오지 못했어요'} class="text-lg font-medium" />
	<p class="max-w-xs text-sm text-fg-secondary">{bad ? page.error?.message : '잠시 후 다시 시도해 주세요.'}</p>
	<a href="{base}/library/story/{thisMonthId()}" class="rounded-full bg-surface-3 px-4 py-2 text-sm font-medium text-fg-primary">
		이번 달 이야기 보기
	</a>
</div>
