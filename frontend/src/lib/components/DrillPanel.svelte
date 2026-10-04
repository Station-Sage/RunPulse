<script lang="ts">
	// §C3.1 드릴다운 시트 컨테이너 — URL(`?drill=`) 스택이 곧 열림 상태다(C3.3).
	// 데스크톱(≥1024px)은 본문 grid를 1fr 420px로 밀어내는 비모달 패널, 모바일은 풀스크린 슬라이드업.
	// 끌어 닫기 제스처(C3.1 "최상위에서만 아래로 끌어 닫기")는 이번 라운드에 구현하지 않음(탭/Esc/뒤로가기로 닫기는 됨) — 별도 판단 필요.
	import type { Snippet } from 'svelte';
	import { base } from '$app/paths';
	import { currentDrillStack, parseDrillToken, pushDrill, popDrill, closeDrill } from '$lib/drillStack';
	import { EXPLAIN_SUPPORTED_SLUGS, getMetricExplain, getMetricTrend } from '$lib/api/metrics';
	import type { AnswerEvidence, MetricExplainData } from '$lib/types';
	import { snapshotLine } from '$lib/answerEvidence';
	import BreakdownView from './BreakdownView.svelte';
	import Icon from './Icon.svelte';

	let {
		scopeType,
		scopeId,
		answerChip = null,
		children
	}: {
		scopeType: string;
		scopeId: string;
		/** Coach 답변 칩에서 연 근거 — 최상위 패널이 그 칩과 같을 때만 답변 당시 스냅샷 줄을 보인다. */
		answerChip?: AnswerEvidence | null;
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
	const snap = $derived(
		answerChip && slugs.length === 1 && answerChip.metric === currentSlug && answerChip.drill?.scope_id === currentScopeId
			? snapshotLine(answerChip)
			: null
	);

	let data = $state<MetricExplainData | null>(null);
	let loading = $state(true);
	let notFound = $state(false);
	let headingEl = $state<HTMLElement | null>(null);
	let labelTick = $state(0);

	$effect(() => {
		const slug = currentSlug;
		const st = scopeType;
		const si = currentScopeId;
		if (!slug) return;
		let cancelled = false;
		if (!EXPLAIN_SUPPORTED_SLUGS.has(slug)) {
			// 분해 미지원 지표 — 한글 이름만 받아 간이 카드 라벨로 쓴다
			if (!labelCache.has(slug)) {
				getMetricTrend(slug, '1m')
					.then((t) => {
						if (!cancelled && t.name_ko) {
							labelCache.set(slug, t.name_ko);
							labelTick++;
						}
					})
					.catch(() => {});
			}
			return () => {
				cancelled = true;
			};
		}
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
		void labelTick;
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
		<div class="flex flex-col gap-3 p-4" data-testid="drill-light">
			<p class="text-sm text-fg-secondary">
				{currentSlug ? breadcrumbLabel(currentSlug) : '이 지표'}은(는) 분해 대신 추세로 볼 수 있어요.
			</p>
			{#if currentSlug}
				<a
					href="{base}/library/metrics/{currentSlug}"
					class="self-start text-sm font-medium text-semantic-teal hover:underline">추세 보기 ›</a
				>
			{/if}
		</div>
	{:else if loading}
		<p class="p-4 text-sm text-fg-muted">불러오는 중…</p>
	{:else if notFound || !data}
		<p class="p-4 text-sm text-fg-secondary">{currentScopeId} 데이터가 아직 없어요 · 데이터 수집 중</p>
	{:else}
		{#if snap}
			<p class="flex items-start gap-1.5 border-b border-border-subtle px-4 py-2 text-xs text-fg-secondary" data-testid="snapshot-line">
				{#if snap.changed}<span class="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-semantic-amber" aria-hidden="true"></span>{/if}
				<span>
					{snap.text}
					{#if snap.changed}<span class="block text-fg-muted">이후 데이터 동기화·재계산으로 값이 바뀌었어요</span>{/if}
				</span>
			</p>
		{/if}
		<BreakdownView
			{data}
			trendHref="{base}/library/metrics/{currentSlug}"
			onDrillTerm={(token) => pushDrill(parseDrillToken(token).slug, currentScopeId)}
		/>
	{/if}
{/snippet}
