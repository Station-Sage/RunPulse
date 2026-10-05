<script lang="ts">
	// U15d — 활동 상세 `⋯` 메뉴(F8): 메모·RPE 기록 / 원본 열기 / GPX 내려받기 / 코치에게 묻기.
	import { base } from '$app/paths';
	import type { ActivityMenuInfo } from '$lib/types';
	import { gpxUrl } from '$lib/activityExport';

	let { activityId, menu, onFeedback }: {
		activityId: number;
		menu?: ActivityMenuInfo;
		onFeedback: () => void;
	} = $props();

	let open = $state(false);
	const item = 'flex h-11 w-full items-center px-4 text-left text-sm text-fg-primary hover:bg-surface-3';
</script>

<div class="relative">
	<button type="button" aria-label="더보기" aria-haspopup="menu" aria-expanded={open}
		onclick={() => (open = !open)} data-testid="activity-more"
		class="h-11 w-11 rounded-full border border-border-subtle text-lg text-fg-secondary hover:text-fg-primary">⋯</button>
	{#if open}
		<div role="menu" class="absolute right-0 z-30 mt-1 w-56 overflow-hidden rounded-lg border border-border-subtle bg-surface-1 shadow-lg">
			<button type="button" role="menuitem" class={item} data-testid="menu-feedback"
				onclick={() => { open = false; onFeedback(); }}>메모·RPE 기록</button>
			{#each menu?.source_links ?? [] as l (l.provider)}
				<a role="menuitem" class={item} href={l.url} target="_blank" rel="noopener noreferrer" onclick={() => (open = false)}>{l.label_ko}</a>
			{/each}
			{#if menu?.has_gps}
				<a role="menuitem" class={item} href={gpxUrl(activityId)} download data-testid="menu-gpx" onclick={() => (open = false)}>GPX 내려받기</a>
			{:else}
				<span role="menuitem" aria-disabled="true" class="{item} cursor-default text-fg-muted">GPX 내려받기 · 위치 기록 없음</span>
			{/if}
			<a role="menuitem" class={item} href="{base}/coach/new?activity={activityId}" onclick={() => (open = false)}>코치에게 묻기</a>
		</div>
	{/if}
</div>
