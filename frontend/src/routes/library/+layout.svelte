<script lang="ts">
	// Library 1단 서브탭 [활동][메트릭][웰니스][소스 비교] — 1단 경로에서만 노출(상세 화면은 자체 헤더).
	import { page } from '$app/state';
	import { base } from '$app/paths';

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
	const isActive = (t: (typeof TABS)[number]) => rel === t.href || ('also' in t && rel === t.also);
</script>

{#if showTabs}
	<nav class="flex h-11 border-b border-border-subtle" aria-label="Library 섹션">
		{#each TABS as t (t.href)}
			<a
				href="{base}{t.href}"
				aria-current={isActive(t) ? 'page' : undefined}
				class="flex flex-1 items-center justify-center text-sm {isActive(t)
					? 'border-b-2 border-fg-primary font-medium text-fg-primary'
					: 'text-fg-muted hover:text-fg-secondary'}">{t.label}</a
			>
		{/each}
	</nav>
{/if}

{@render children()}
