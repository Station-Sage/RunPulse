<script lang="ts">
	// Library 1단 서브탭 [활동][메트릭][웰니스][소스 비교] — 1단 경로에서만 노출(상세 화면은 자체 헤더).
	import { page } from '$app/state';
	import { base } from '$app/paths';
	import SubTabs from '$lib/components/ui/SubTabs.svelte';

	let { children } = $props();

	const TABS = [
		{ href: '/library', label: '홈' },
		{ href: '/library/activities', label: '활동' },
		{ href: '/library/metrics', label: '메트릭' },
		{ href: '/library/wellness', label: '웰니스' },
		{ href: '/library/story', label: '이야기' },
		{ href: '/library/providers', label: '소스 비교' }
	] as const;

	const path = $derived(page.url.pathname.replace(/\/$/, ''));
	const rel = $derived(path.startsWith(base) ? path.slice(base.length) : path);
	const showTabs = $derived(rel === '/library' || TABS.some((t) => t.href === rel));
	const tabs = TABS.map((t) => ({ href: `${base}${t.href}`, label: t.label }));
	const current = $derived(`${base}${rel}`);
</script>

{#if showTabs}
	<SubTabs {tabs} {current} label="Library 하위 메뉴" />
{/if}

{@render children()}
