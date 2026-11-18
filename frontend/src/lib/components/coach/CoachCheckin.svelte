<script lang="ts">
	// 오늘 컨디션 요약 — 입력은 Today 에서만 받고(중복 입력 제거) 여기선 상태와 이동 링크만 보여 준다.
	import { base } from '$app/paths';
	import { checkinSummary } from '$lib/checkinView';
	import type { CheckinRow } from '$lib/types';

	let { initial }: { initial: CheckinRow | null } = $props();

	const summary = $derived(checkinSummary(initial));
</script>

<div class="flex items-center justify-between gap-3 border-t border-border-subtle px-4 py-3" data-testid="coach-checkin-summary">
	<p class="text-xs text-fg-muted">
		{#if summary}오늘 컨디션: {summary}{:else}오늘 컨디션을 아직 입력하지 않았어요{/if}
		— 코치 답변에 반영돼요.
	</p>
	<a href="{base}/today" class="inline-flex min-h-11 shrink-0 items-center text-xs text-fg-secondary underline">{summary ? '수정' : '입력'}하러 가기</a>
</div>
