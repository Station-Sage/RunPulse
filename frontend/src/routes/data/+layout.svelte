<script lang="ts">
	// Data 영역 서브탭 [개요|동기화|소스|내보내기|설정] — 40 design §2.4.
	import { page } from '$app/state';
	import { base } from '$app/paths';
	import SubTabs from '$lib/components/SubTabs.svelte';
	import { DATA_TABS, activeDataTab } from '$lib/dataArea';

	let { children } = $props();

	const tabs = DATA_TABS.map((t) => ({ href: `${base}${t.href}`, label: t.label }));
	const path = $derived(page.url.pathname.replace(/\/$/, ''));
	const rel = $derived(path.startsWith(base) ? path.slice(base.length) : path);
	const current = $derived(`${base}${activeDataTab(rel)}`);
</script>

<SubTabs {tabs} {current} />
{@render children()}
