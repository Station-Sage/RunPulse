<script lang="ts">
	// 화면 머리글 — 문서 title·h1(PageHead) + 뒤로가기 ‹ + 우측 액션. 뒤로가기 규칙은 $lib/backNav.
	import type { Snippet } from 'svelte';
	import { page } from '$app/state';
	import { base } from '$app/paths';
	import PageHead from '$lib/components/ui/PageHead.svelte';
	import { BACK_GLYPH, backTarget } from '$lib/backNav';

	let {
		title,
		heading,
		back = false,
		backLabel = '이전',
		fallback = '/today',
		actions
	}: {
		title: string;
		heading?: string | null;
		back?: boolean;
		backLabel?: string;
		fallback?: string;
		actions?: Snippet;
	} = $props();

	const rel = $derived(page.url.pathname.startsWith(base) ? page.url.pathname.slice(base.length) : page.url.pathname);
	const href = $derived(`${base}${backTarget(rel, page.url.searchParams.get('from'), base, fallback)}`);
</script>

<header class="flex min-h-14 items-center gap-2 border-b border-border-subtle px-4">
	{#if back}
		<a {href} aria-label="{backLabel} 화면으로 돌아가기" data-testid="page-back" class="tap -ml-2 inline-flex items-center justify-center px-2 text-lg text-fg-secondary">{BACK_GLYPH}</a>
	{/if}
	<div class="min-w-0 flex-1"><PageHead {title} {heading} class="truncate text-base font-semibold text-fg-primary" /></div>
	{#if actions}<div class="flex shrink-0 items-center gap-2">{@render actions()}</div>{/if}
</header>
