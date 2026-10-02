<script lang="ts">
	// 활동 상세 공용 탭 바(sticky 44px) — 탭 전환은 history를 쌓지 않는다(replaceState, F-UX-05).
	import { base } from '$app/paths';
	let {
		activityId,
		active,
		search = ''
	}: {
		activityId: number;
		active: 'summary' | 'streams' | 'laps' | 'metrics' | 'providers';
		/** 탭 이동 시 유지할 쿼리(?from=…). */
		search?: string;
	} = $props();
	const TABS = [
		{ key: 'summary', label: '요약', path: '' },
		{ key: 'streams', label: '스트림', path: '/streams' },
		{ key: 'laps', label: '랩', path: '/laps' },
		{ key: 'metrics', label: '메트릭', path: '/metrics' },
		{ key: 'providers', label: '소스 비교', path: '/providers' }
	] as const;
</script>

<nav class="flex h-11 border-b border-border-subtle bg-surface-1" aria-label="활동 상세 탭">
	{#each TABS as tab (tab.key)}
		{#if tab.key === active}
			<span
				aria-current="page"
				class="flex flex-1 items-center justify-center whitespace-nowrap border-b-2 border-fg-primary text-sm font-medium text-fg-primary"
			>{tab.label}</span>
		{:else}
			<a
				href="{base}/library/{activityId}{tab.path}{search}"
				data-sveltekit-replacestate
				class="flex flex-1 items-center justify-center whitespace-nowrap text-sm text-fg-secondary hover:text-fg-primary"
			>{tab.label}</a>
		{/if}
	{/each}
</nav>
