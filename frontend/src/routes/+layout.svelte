<script lang="ts">
	// 공통 셸 — 하단 3탭(Today/Library/Coach) + 상단 ☰ 메뉴.
	// 03-screen-catalog.md 전 화면 공통. ☰ 메뉴의 실제 내용(/data/*)은 Phase 7d 몫이라
	// 지금은 자리만 있고 비활성 상태다.
	import './layout.css';
	import favicon from '$lib/assets/favicon.svg';
	import { base } from '$app/paths';
	import { page } from '$app/state';

	let { children } = $props();

	const tabs = [
		{ href: `${base}/today`, label: 'Today', match: '/today' },
		{ href: `${base}/library`, label: 'Library', match: '/library' },
		{ href: `${base}/coach`, label: 'Coach', match: '/coach' }
	];

	const isActive = (match: string) => page.url.pathname.startsWith(`${base}${match}`);
</script>

<svelte:head><link rel="icon" href={favicon} /></svelte:head>

<div class="flex min-h-screen flex-col bg-surface-1 text-fg-primary">
	<header
		class="flex items-center justify-between border-b border-border-subtle px-4 py-3"
	>
		<span class="font-medium">RunPulse</span>
		<button
			type="button"
			disabled
			aria-label="메뉴 (준비 중)"
			class="rounded px-2 py-1 text-fg-muted"
		>
			☰
		</button>
	</header>

	<main class="flex-1 pb-20">
		{@render children()}
	</main>

	<nav
		aria-label="주 메뉴"
		class="fixed inset-x-0 bottom-0 flex border-t border-border-subtle bg-surface-2"
	>
		{#each tabs as tab (tab.href)}
			<a
				href={tab.href}
				aria-current={isActive(tab.match) ? 'page' : undefined}
				class="flex-1 py-3 text-center text-sm {isActive(tab.match)
					? 'text-fg-primary'
					: 'text-fg-muted'}"
			>
				{tab.label}
			</a>
		{/each}
	</nav>
</div>
