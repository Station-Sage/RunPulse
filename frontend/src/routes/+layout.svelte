<script lang="ts">
	// 공통 셸 — 하단 3탭(Today/Library/Coach) + 상단 ☰ 메뉴.
	// 03-screen-catalog.md 전 화면 공통. ☰ 메뉴의 실제 내용(/data/*)은 Phase 7d 몫이라
	// 지금은 자리만 있고 비활성 상태다.
	// E5: 탭바 SVG 아이콘, max-w-3xl 중앙 정렬.
	import './layout.css';
	import favicon from '$lib/assets/favicon.svg';
	import { base } from '$app/paths';
	import { page } from '$app/state';
	import Icon from '$lib/components/Icon.svelte';
	import ProgressBar from '$lib/components/ProgressBar.svelte';

	let { children } = $props();

	const tabs = [
		{ href: `${base}/today`, label: 'Today', match: '/today', icon: 'today' as const },
		{ href: `${base}/library`, label: 'Library', match: '/library', icon: 'library' as const },
		{ href: `${base}/coach`, label: 'Coach', match: '/coach', icon: 'coach' as const }
	];

	const isActive = (match: string) => page.url.pathname.startsWith(`${base}${match}`);
</script>

<svelte:head><link rel="icon" href={favicon} /></svelte:head>

<ProgressBar />

<div class="flex min-h-screen flex-col bg-surface-1 text-fg-primary lg:pl-52">
	<header class="border-b border-border-subtle">
		<div class="mx-auto flex max-w-3xl lg:max-w-6xl items-center justify-between px-4 py-3">
			<span class="font-medium">RunPulse</span>
			<button
				type="button"
				disabled
				aria-label="메뉴 (준비 중)"
				class="rounded px-2 py-1 text-fg-muted"
			>
				<Icon name="menu" class="h-5 w-5" />
			</button>
		</div>
	</header>

	<main class="mx-auto w-full max-w-3xl lg:max-w-6xl flex-1 pb-20 lg:pb-6">
		{@render children()}
	</main>

	<nav
		aria-label="주 메뉴"
		class="fixed inset-x-0 bottom-0 border-t border-border-subtle bg-surface-2 lg:inset-y-0 lg:right-auto lg:w-52 lg:border-r lg:border-t-0 lg:pt-16"
	>
		<div class="mx-auto flex w-full max-w-3xl lg:max-w-none lg:flex-col lg:gap-1 lg:px-2">
			{#each tabs as tab (tab.href)}
				<a
					href={tab.href}
					aria-current={isActive(tab.match) ? 'page' : undefined}
					class="flex flex-1 flex-col items-center gap-0.5 py-2 text-[11px] lg:flex-none lg:flex-row lg:gap-3 lg:rounded-lg lg:px-3 lg:py-2.5 lg:text-sm {isActive(tab.match) ? 'text-fg-primary lg:bg-surface-3' : 'text-fg-muted lg:hover:bg-surface-3'}"
				>
					<Icon name={tab.icon} />
					{tab.label}
				</a>
			{/each}
		</div>
	</nav>
</div>
