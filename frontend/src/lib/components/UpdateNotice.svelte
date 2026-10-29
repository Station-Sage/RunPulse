<script lang="ts">
	import { say } from '$lib/a11y/say';
	// "새 버전이 있습니다" 알림 (SEC-8 (b), D8). 자동 새로고침은 하지 않고, 사용자가 [새로고침]을 누를 때만 새로고침한다.
	// 문구·위치는 product 영역 — 이 값은 구현 시 임시로 정한 것이며 사용자 확인 대상이다(S3-10).
	// 하단 탭바(모바일)·좌측 사이드바(lg)와 겹치지 않도록 Toast 와 같은 위치 규칙을 쓴다.
	import { updateNoticeVisible } from '$lib/updateNotice';

	function reload() {
		location.reload();
	}
	function dismiss() {
		updateNoticeVisible.set(false);
	}
</script>

{#if $updateNoticeVisible}
	<div
		class="fixed inset-x-4 bottom-20 z-[80] mx-auto flex max-w-sm items-center justify-between gap-3 rounded-lg bg-surface-3 px-4 py-3 text-sm text-fg-primary shadow-lg lg:bottom-6 lg:left-auto lg:right-6 lg:mx-0"
		use:say={{ text: '새 버전이 있어요. 새로고침하면 적용돼요.' }}
	>
		<span>새 버전이 있어요. 새로고침하면 적용돼요.</span>
		<span class="flex shrink-0 items-center gap-3">
			<button type="button" onclick={dismiss} class="text-fg-secondary hover:text-fg-primary">나중에</button>
			<button type="button" onclick={reload} class="font-medium text-series-1 hover:underline">새로고침</button>
		</span>
	</div>
{/if}
