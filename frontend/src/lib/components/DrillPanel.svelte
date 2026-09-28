<script lang="ts">
	// §C3.1 드릴다운 시트 컨테이너 — URL(`?drill=`) 스택이 곧 열림 상태다(C3.3).
	// 데스크톱(≥1024px)은 본문 grid를 1fr 420px로 밀어내는 비모달 패널, 모바일은 풀스크린 슬라이드업.
	// 끌어 닫기 제스처(C3.1 "최상위에서만 아래로 끌어 닫기")는 이번 라운드에 구현하지 않음(탭/Esc/뒤로가기로 닫기는 됨) — 별도 판단 필요.
	import type { Snippet } from 'svelte';
	import { base } from '$app/paths';
	import { currentDrillStack, parseDrillToken, pushDrill, popDrill, closeDrill } from '$lib/drillStack';
	import { EXPLAIN_SUPPORTED_SLUGS, getMetricExplain } from '$lib/api/metrics';
	import type { MetricExplainData } from '$lib/types';
	import BreakdownView from './BreakdownView.svelte';
	import Icon from './Icon.svelte';

	let {
		scopeType,
		scopeId,
		children
	}: {
		scopeType: string;
		scopeId: string;
		children: Snippet;
	} = $props();

	// 스택 라벨은 드릴다운 이동 시마다 채워진다(딥링크로 바로 들어온 조상 단계는 슬러그로 폴백).
	const labelCache = new Map<string, string>();

	// D1d: 토큰마다 `@scope`가 있을 수 있다(예: Coach 근거 칩이 연 과거 날짜) — 없으면 페이지 기본 scopeId.
	const parsedStack = $derived(currentDrillStack().map(parseDrillToken));
	const slugs = $derived(parsedStack.map((p) => p.slug));
	const currentSlug = $derived(parsedStack.at(-1)?.slug ?? null);
	const currentScopeId = $derived(parsedStack.at(-1)?.scope ?? scopeId);
	const isOpen = $derived(slugs.length > 0);

	let data = $state<MetricExplainData | null>(null);
	let loading = $state(true);
	let notFound = $state(false);
	let headingEl = $state<HTMLElement | null>(null);

	$effect(() => {
		const slug = currentSlug;
		const st = scopeType;
		const si = currentScopeId;
		if (!slug) return;
		let cancelled = false;
		loading = true;
		notFound = false;
		data = null;
		getMetricExplain(slug, st, si)
			.then((d) => {
				if (cancelled) return;
				if (!d.formula) {
					notFound = true;
					return;
				}
				data = d;
				labelCache.set(slug, d.name_ko);
			})
			.catch(() => {
				if (!cancelled) notFound = true;
			})
			.finally(() => {
				if (!cancelled) loading = false;
			});
		return () => {
			cancelled = true;
		};
	});

	$effect(() => {
		if (isOpen) headingEl?.focus();
	});

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Escape') {
			e.stopPropagation();
			popDrill();
		}
	}

	function breadcrumbLabel(slug: string): string {
		return labelCache.get(slug) ?? slug.toUpperCase();
	}
</script>

<svelte:window onkeydown={isOpen ? handleKeydown : undefined} />

<div class="lg:grid lg:h-full {isOpen ? 'lg:grid-cols-[1fr_420px]' : 'lg:grid-cols-1'}">
	<div class="min-w-0">
		{@render children()}
	</div>

	{#if isOpen}
		<!-- 모바일: 풀스크린 슬라이드업 -->
		<div class="fixed inset-0 z-50 flex flex-col lg:hidden" role="dialog" aria-modal="true">
			<button class="absolute inset-0 bg-black/40" onclick={closeDrill} aria-label="닫기"></button>
			<div
				class="relative mt-auto flex max-h-[85vh] flex-col overflow-hidden rounded-t-2xl bg-surface-1 pb-[env(safe-area-inset-bottom)] shadow-lg"
			>
				{@render header()}
				<div class="overflow-y-auto">
					{@render body()}
				</div>
			</div>
		</div>

		<!-- 데스크톱: 비모달 사이드 패널 -->
		<div class="hidden lg:flex lg:h-full lg:flex-col lg:border-l lg:border-border-subtle lg:bg-surface-1">
			{@render header()}
			<div class="flex-1 overflow-y-auto">
				{@render body()}
			</div>
		</div>
	{/if}
</div>

{#snippet header()}
	<div class="flex items-center gap-2 border-b border-border-subtle px-4 py-3">
		{#if slugs.length >= 2}
			<button onclick={popDrill} aria-label="이전으로" class="shrink-0 text-fg-secondary">
				<Icon name="chevron" class="h-4 w-4 rotate-180" />
			</button>
		{/if}
		<div class="min-w-0 flex-1">
			<h2 tabindex="-1" bind:this={headingEl} class="truncate text-sm font-semibold outline-none">
				{slugs.map(breadcrumbLabel).join(' › ')}
			</h2>
			<p class="text-[11px] text-fg-muted">{currentScopeId} 아침 기준</p>
		</div>
		<button onclick={closeDrill} aria-label="닫기" class="shrink-0 text-fg-secondary hover:text-fg-primary">
			<Icon name="close" class="h-4 w-4" />
		</button>
	</div>
{/snippet}

{#snippet body()}
	{#if !currentSlug || !EXPLAIN_SUPPORTED_SLUGS.has(currentSlug)}
		<p class="p-4 text-sm text-fg-secondary">이 지표는 아직 분해 보기를 지원하지 않아요.</p>
	{:else if loading}
		<p class="p-4 text-sm text-fg-muted">불러오는 중…</p>
	{:else if notFound || !data}
		<p class="p-4 text-sm text-fg-secondary">{currentScopeId} 데이터가 아직 없어요 · 데이터 수집 중</p>
	{:else}
		<BreakdownView
			{data}
			trendHref="{base}/library/metrics/{currentSlug}"
			onDrillTerm={(token) => pushDrill(parseDrillToken(token).slug, currentScopeId)}
		/>
	{/if}
{/snippet}
