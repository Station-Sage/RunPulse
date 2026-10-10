<script lang="ts">
	// 공통 셸 — 하단 3탭(Today/Library/Coach) + 상단 ☰ 메뉴.
	// 03-screen-catalog.md 전 화면 공통. ☰는 40:S0 과도기 드로어(v1 링크)로 활성화 —
	// 우측 SyncStatusPill(Phase 4-1 슬라이스1, 읽기 전용)이 동기화 상태를 보여주고, 드로어는
	// v1↔v2 상호 링크 역할을 한다. 좌측 ☰·우측 Pill은 40-v2-unimplemented/design.md §2.1 결정.
	// E5: 탭바 SVG 아이콘, max-w-3xl 중앙 정렬.
	import './layout.css';
	import favicon from '$lib/assets/favicon.svg';
	import { base } from '$app/paths';
	import { page } from '$app/state';
	import Icon from '$lib/components/Icon.svelte';
	import ProgressBar from '$lib/components/ProgressBar.svelte';
	import MenuDrawer from '$lib/components/MenuDrawer.svelte';
	import DemoBanner from '$lib/components/DemoBanner.svelte';
	import { demoActive, isDemoActive } from '$lib/demoMode';
	import SyncStatusPill from '$lib/components/shell/SyncStatusPill.svelte';

	let { children } = $props();
	let menuOpen = $state(false);
	if (isDemoActive()) demoActive.set(true);

	const tabs = [
		{ href: `${base}/today`, label: 'Today', match: '/today', icon: 'today' as const },
		{ href: `${base}/library`, label: 'Library', match: '/library', icon: 'library' as const },
		{ href: `${base}/coach`, label: 'Coach', match: '/coach', icon: 'coach' as const }
	];

	const isActive = (match: string) => page.url.pathname.startsWith(`${base}${match}`);
</script>

<svelte:head><link rel="icon" href={favicon} /></svelte:head>

<ProgressBar />
{#if $demoActive}<DemoBanner />{/if}

<div class="flex min-h-screen flex-col bg-surface-1 text-fg-primary lg:pl-52">
	<header class="border-b border-border-subtle pt-[env(safe-area-inset-top)]">
		<div class="mx-auto flex max-w-3xl items-center gap-2 px-4 py-3 lg:max-w-6xl">
			{#if !$demoActive}<button
				type="button"
				onclick={() => (menuOpen = true)}
				aria-label="메뉴"
				class="-ml-1.5 rounded p-1.5 text-fg-secondary hover:text-fg-primary"
			>
				<Icon name="menu" class="h-5 w-5" />
			</button>{/if}
			<span class="font-medium">RunPulse</span>
			{#if !$demoActive}<SyncStatusPill />{/if}
		</div>
	</header>

	<MenuDrawer open={menuOpen} onClose={() => (menuOpen = false)} />

	<main class="mx-auto w-full max-w-3xl lg:max-w-6xl flex-1 pb-20 lg:pb-6">
		{@render children()}
	</main>

	<nav
		aria-label="주 메뉴"
		class="fixed inset-x-0 bottom-0 border-t border-border-subtle bg-surface-2 pb-[env(safe-area-inset-bottom)] lg:inset-y-0 lg:right-auto lg:w-52 lg:border-r lg:border-t-0 lg:pb-0 lg:pt-16"
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
