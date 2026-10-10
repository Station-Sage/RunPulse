<script lang="ts">
	// S2b 히어로 — 활동이 소량일 때 최근 활동 요약과 "곧 열려요" 진행도(DESIGN-P7-REVIEW03 §2.0).
	import { base } from '$app/paths';
	import { coldStartSummary } from '$lib/coldStart';
	import type { RecentActivity } from '$lib/types';

	let { activities }: { activities: RecentActivity[] } = $props();
	const sum = $derived(coldStartSummary(activities));
</script>

{#if sum}
	<section class="flex flex-col gap-2 rounded-xl border border-border-subtle bg-surface-2 p-4" aria-label="첫 기록 요약" data-testid="cold-start">
		<h1 class="text-xl font-semibold">{sum.headline}</h1>
		<p class="text-sm text-fg-secondary">{sum.stats}</p>
		<p class="text-xs text-fg-muted">기록이 쌓이면 오늘의 권고와 상태 지표가 열려요.</p>
		<a href="{base}/library/{sum.activityId}?from=today" class="self-start text-sm text-fg-secondary hover:text-fg-primary">활동 보기 ›</a>
	</section>
{/if}
