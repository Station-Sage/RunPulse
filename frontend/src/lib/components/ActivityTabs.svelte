<script lang="ts">
	// 활동 상세 공용 탭 바(sticky 44px) — 탭 전환은 history를 쌓지 않는다(replaceState, F-UX-05).
	import { base } from '$app/paths';
	let {
		activityId,
		active,
		search = '',
		empty = []
	}: {
		activityId: number;
		active: 'summary' | 'streams' | 'laps' | 'metrics' | 'providers';
		/** 탭 이동 시 유지할 쿼리(?from=…). */
		search?: string;
		/** 데이터가 없는 탭 — 누르기 전에 '없음'을 보인다(S-16). 탭은 눌러서 이유를 볼 수 있게 남긴다. */
		empty?: string[];
	} = $props();
	const TABS = [
		{ key: 'summary', label: '요약', path: '' },
		{ key: 'streams', label: '스트림', path: '/streams' },
		{ key: 'laps', label: '랩', path: '/laps' },
		{ key: 'metrics', label: '메트릭', path: '/metrics' },
		{ key: 'providers', label: '소스 비교', path: '/providers' }
	] as const;
</script>

<nav class="flex h-11 border-b border-border-subtle bg-surface-1" aria-label="활동 상세 하위 메뉴">
	{#each TABS as tab (tab.key)}
		{@const none = empty.includes(tab.key)}
		{#if tab.key === active}
			<span
				aria-current="page"
				class="flex flex-1 items-center justify-center whitespace-nowrap border-b-2 border-fg-primary text-sm font-medium text-fg-primary"
			>{tab.label}{#if none}<span class="ml-0.5 text-[10px] font-normal text-fg-muted" data-testid="tab-empty">없음</span>{/if}</span>
		{:else}
			<a
				href="{base}/library/{activityId}{tab.path}{search}"
				data-sveltekit-replacestate
				class="flex flex-1 items-center justify-center whitespace-nowrap text-sm {none ? 'text-fg-muted' : 'text-fg-secondary'} hover:text-fg-primary"
			>{tab.label}{#if none}<span class="ml-0.5 text-[10px]" data-testid="tab-empty">없음</span>{/if}</a>
		{/if}
	{/each}
</nav>
