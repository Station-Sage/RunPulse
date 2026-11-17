<script lang="ts">
	// Coach 1단 서브탭 [대화][플랜] — 홈·플랜 홈·활성 플랜 상세에서만 노출(대화방·세션·폼은 자체 헤더).
	import { page } from '$app/state';
	import { base } from '$app/paths';
	import SubTabs from '$lib/components/ui/SubTabs.svelte';

	let { children } = $props();

	const tabs = [
		{ href: `${base}/coach`, label: '대화' },
		{ href: `${base}/coach/plan`, label: '플랜' }
	];
	const path = $derived(page.url.pathname.replace(/\/$/, ''));
	const rel = $derived(path.startsWith(base) ? path.slice(base.length) : path);
	const isPlanTop = $derived(rel === '/coach/plan' || /^\/coach\/plan\/\d+$/.test(rel));
	const showTabs = $derived(rel === '/coach' || isPlanTop);
	const current = $derived(`${base}${isPlanTop ? '/coach/plan' : '/coach'}`);
</script>

{#if showTabs}
	<SubTabs {tabs} {current} label="Coach 하위 메뉴" />
{/if}

{@render children()}
