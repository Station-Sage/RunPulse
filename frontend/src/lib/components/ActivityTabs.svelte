<script lang="ts">
	// 활동 상세 공용 탭 바 — 03c-library.md 3-C/3-D. 탭마다 별도 라우트라 현재 탭만 <span>, 나머지는 <a>.
	import { base } from '$app/paths';
	let {
		activityId,
		active
	}: { activityId: number; active: 'summary' | 'streams' | 'laps' | 'providers' } = $props();
	const TABS = [
		{ key: 'summary', label: '요약', path: '' },
		{ key: 'streams', label: '스트림', path: '/streams' },
		{ key: 'laps', label: '랩', path: '/laps' },
		{ key: 'providers', label: '소스 비교', path: '/providers' }
	] as const;
</script>
<div class="flex border-b border-border-subtle">
	{#each TABS as tab (tab.key)}
		{#if tab.key === active}
			<span
				aria-current="page"
				class="flex-1 whitespace-nowrap border-b-2 border-fg-primary py-2.5 text-center text-sm font-medium text-fg-primary"
			>{tab.label}</span>
		{:else}
			<a
				href="{base}/library/{activityId}{tab.path}"
				class="flex-1 whitespace-nowrap py-2.5 text-center text-sm text-fg-secondary hover:text-fg-primary"
			>{tab.label}</a>
		{/if}
	{/each}
</div>
