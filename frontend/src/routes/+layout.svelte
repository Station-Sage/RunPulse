<script lang="ts">
	import IconButton from '$lib/components/ui/IconButton.svelte';
	// 공통 셸 — 하단 3탭(Today/Library/Coach) + 상단 ☰ 메뉴.
	// 03-screen-catalog.md 전 화면 공통. ☰는 40:S0 과도기 드로어(v1 링크)로 활성화 —
	// 우측 SyncStatusPill(Phase 4-1 슬라이스1, 읽기 전용)이 동기화 상태를 보여주고, 드로어는
	// v1↔v2 상호 링크 역할을 한다. 좌측 ☰·우측 Pill은 40-v2-unimplemented/design.md §2.1 결정.
	// E5: 탭바 SVG 아이콘, max-w-3xl 중앙 정렬.
	import './layout.css';
	import { base } from '$app/paths';
	import { navigating, page } from '$app/state';
	import { onMount } from 'svelte';
	import { removeBootSplash } from '$lib/bootSplash';
	import OfflineBanner from '$lib/components/shell/OfflineBanner.svelte';
	import Icon from '$lib/components/Icon.svelte';
	import ShellNav from '$lib/components/shell/ShellNav.svelte';
	import ProgressBar from '$lib/components/ProgressBar.svelte';
	import MenuDrawer from '$lib/components/MenuDrawer.svelte';
	import DemoBanner from '$lib/components/DemoBanner.svelte';
	import LiveRegion from '$lib/components/LiveRegion.svelte';
	import UpdateNotice from '$lib/components/UpdateNotice.svelte';
	import { demoActive, isDemoActive } from '$lib/demoMode';
	import SyncStatusPill from '$lib/components/shell/SyncStatusPill.svelte';
	import { welcomeGuardApplies } from '$lib/onboarding';
	import { redirectToWelcomeIfNew } from '$lib/welcomeRedirect';
	import { navSkeletonKind } from '$lib/navSkeleton';
	import PlanDetailSkeleton from '$lib/components/PlanDetailSkeleton.svelte';

	let { children } = $props();
	let menuOpen = $state(false);
	if (isDemoActive()) demoActive.set(true);

	const isLanding = $derived(
		page.url.pathname.startsWith(`${base}/landing`) || page.url.pathname.startsWith(`${base}/auth/`)
	);

	// E-13, S-21: welcome/404/error 화면에서 SyncStatusPill 숨김
	const isOnboarding = $derived(page.url.pathname === `${base}/welcome`);
	const isErrorPage = $derived(!!page.error);
	const hideSyncPill = $derived(isOnboarding || isErrorPage);

	// S-05: 첫 화면이 그려지면 app.html 정적 로딩 화면 제거. S-06/E-16: 이동 중 본문 aria-busy.
	onMount(() => {
		removeBootSplash(document);
		// S-22: /library·/coach 로 바로 들어와도 신규 계정(소스 0·활동 0·온보딩 대기)은 /welcome 으로
		if (!isDemoActive() && welcomeGuardApplies(page.url.pathname, base)) void redirectToWelcomeIfNew();
	});
	const busy = $derived(!!navigating.to);

	// P-25: 플랜 상세로 이동 중이면 150ms 뒤(진행바 S-06 과 같은 지연) 스켈레톤. 이전 화면은 언마운트하지 않고 숨기기만 한다
	// (이동이 취소·실패해도 상태 유지). 로더는 그대로 — 스트리밍으로 바꾸지 않음.
	const pendingSkeleton = $derived(navSkeletonKind(navigating.from, navigating.to));
	let skeleton = $state<string | null>(null);
	$effect(() => {
		const kind = pendingSkeleton;
		if (!kind) {
			skeleton = null;
			return;
		}
		const t = setTimeout(() => (skeleton = kind), 150);
		return () => clearTimeout(t);
	});
</script>

<a
	href="#main"
	class="sr-only focus:not-sr-only focus:fixed focus:left-2 focus:top-2 focus:z-[90] focus:rounded focus:bg-surface-3 focus:px-3 focus:py-2 focus:text-sm focus:text-fg-primary"
	>본문 바로가기</a
>
<LiveRegion />
<ProgressBar />
<UpdateNotice />
<OfflineBanner />
{#if $demoActive}<DemoBanner />{/if}

{#if isLanding}
	<div class="min-h-screen bg-surface-1 text-fg-primary">{@render children()}</div>
{:else}
<div class="flex min-h-screen flex-col bg-surface-1 text-fg-primary lg:pl-52">
	<header class="border-b border-border-subtle pt-[env(safe-area-inset-top)]">
		<div class="mx-auto flex max-w-3xl items-center gap-2 px-4 py-3 lg:max-w-6xl">
			{#if !$demoActive}<IconButton label="메뉴" onclick={() => (menuOpen = true)} class="-ml-2 rounded text-fg-secondary hover:text-fg-primary"><Icon name="menu" class="h-5 w-5" /></IconButton>{/if}
			<span class="font-medium">RunPulse</span>
			{#if !$demoActive && !hideSyncPill}<SyncStatusPill />{/if}
		</div>
	</header>

	<MenuDrawer open={menuOpen} onClose={() => (menuOpen = false)} />

	<ShellNav variant="side" />

	<main
		id="main"
		tabindex="-1"
		aria-busy={busy}
		class="mx-auto w-full max-w-3xl flex-1 pb-[calc(var(--shell-bottom)+1.5rem)] outline-none lg:max-w-6xl"
	>
		{#if skeleton === 'plan-detail'}<PlanDetailSkeleton />{/if}
		<div class={skeleton ? 'hidden' : 'contents'}>{@render children()}</div>
	</main>

	<ShellNav variant="bottom" />
</div>
{/if}
