<script lang="ts">
	// 공통 셸 — 하단 3탭(Today/Library/Coach) + 상단 ☰ 메뉴.
	// 03-screen-catalog.md 전 화면 공통. ☰는 40:S0 과도기 드로어(v1 링크)로 활성화 —
	// 우측 SyncStatusPill(Phase 4-1 슬라이스1, 읽기 전용)이 동기화 상태를 보여주고, 드로어는
	// v1↔v2 상호 링크 역할을 한다. 좌측 ☰·우측 Pill은 40-v2-unimplemented/design.md §2.1 결정.
	// E5: 탭바 SVG 아이콘, max-w-3xl 중앙 정렬.
	import './layout.css';
	import { base } from '$app/paths';
	import { page } from '$app/state';
	import Icon from '$lib/components/Icon.svelte';
	import ShellNav from '$lib/components/shell/ShellNav.svelte';
	import ProgressBar from '$lib/components/ProgressBar.svelte';
	import MenuDrawer from '$lib/components/MenuDrawer.svelte';
	import DemoBanner from '$lib/components/DemoBanner.svelte';
	import LiveRegion from '$lib/components/LiveRegion.svelte';
	import UpdateNotice from '$lib/components/UpdateNotice.svelte';
	import { demoActive, isDemoActive } from '$lib/demoMode';
	import SyncStatusPill from '$lib/components/shell/SyncStatusPill.svelte';

	let { children } = $props();
	let menuOpen = $state(false);
	if (isDemoActive()) demoActive.set(true);

	const isLanding = $derived(page.url.pathname.startsWith(`${base}/landing`));
</script>

<a
	href="#main"
	class="sr-only focus:not-sr-only focus:fixed focus:left-2 focus:top-2 focus:z-[90] focus:rounded focus:bg-surface-3 focus:px-3 focus:py-2 focus:text-sm focus:text-fg-primary"
	>본문 바로가기</a
>
<LiveRegion />
<ProgressBar />
<UpdateNotice />
{#if $demoActive}<DemoBanner />{/if}

{#if isLanding}
	<div class="min-h-screen bg-surface-1 text-fg-primary">{@render children()}</div>
{:else}
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

	<ShellNav variant="side" />

	<main
		id="main"
		tabindex="-1"
		class="mx-auto w-full max-w-3xl flex-1 pb-[calc(var(--shell-bottom)+1.5rem)] outline-none lg:max-w-6xl"
	>
		{@render children()}
	</main>

	<ShellNav variant="bottom" />
</div>
{/if}
