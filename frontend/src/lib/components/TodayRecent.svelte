<script lang="ts">
	// 최근 활동 목록(B6) — 행 전체가 활동 상세 링크.
	import ActivityRow from '$lib/components/ActivityRow.svelte';
	import { base } from '$app/paths';
	import type { TodayResponse } from '$lib/types';

	let { activities }: { activities: TodayResponse['recent_activities'] } = $props();
</script>

<div class="flex flex-col gap-1 rounded-lg border border-border-subtle bg-surface-2 p-3">
	<p class="mb-1 text-xs text-fg-muted">최근 활동</p>
	{#if activities.length === 0}
		<p class="text-sm text-fg-muted">아직 활동이 없습니다.</p>
	{:else}
		{#each activities as act (act.id)}
			<ActivityRow {act} from="today" showProvider thumbSize={32} />
		{/each}
		<a href="{base}/library/activities" class="mt-1 text-xs text-fg-secondary hover:text-fg-primary">활동 전체 →</a>
	{/if}
</div>
