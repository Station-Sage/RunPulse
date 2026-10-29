<script lang="ts">
	// 셸 주 메뉴 — variant 로 하단 탭(<lg)·좌측 사이드바(lg)를 각각 렌더(DOM 순서가 달라야 해서 2회 마운트).
	import { base } from '$app/paths';
	import { page } from '$app/state';
	import Icon from '$lib/components/Icon.svelte';
	import { navTabs, isTabActive } from '$lib/shell/navTabs';

	let { variant }: { variant: 'side' | 'bottom' } = $props();
	const tabs = navTabs(base);
	const side = $derived(variant === 'side');
</script>

<nav
	aria-label="주 메뉴"
	data-testid="shell-nav-{variant}"
	class={side
		? 'fixed inset-y-0 left-0 hidden w-52 border-r border-border-subtle bg-surface-2 pt-16 lg:block'
		: 'fixed inset-x-0 bottom-0 border-t border-border-subtle bg-surface-2 pb-[env(safe-area-inset-bottom)] lg:hidden'}
>
	<div class={side ? 'flex flex-col gap-1 px-2' : 'mx-auto flex w-full max-w-3xl'}>
		{#each tabs as tab (tab.href)}
			{@const active = isTabActive(page.url.pathname, base, tab.match)}
			<a
				href={tab.href}
				aria-current={active ? 'page' : undefined}
				class={side
					? `flex items-center gap-3 min-h-11 rounded-lg px-3 py-2.5 text-sm ${active ? 'bg-surface-3 text-fg-primary' : 'text-fg-muted hover:bg-surface-3'}`
					: `flex flex-1 flex-col items-center gap-0.5 py-2 text-[11px] ${active ? 'text-fg-primary' : 'text-fg-muted'}`}
			>
				<Icon name={tab.icon} />
				{tab.label}
			</a>
		{/each}
	</div>
</nav>
