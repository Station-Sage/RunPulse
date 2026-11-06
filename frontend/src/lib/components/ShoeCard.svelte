<script lang="ts">
	// 신발 카드(Level 1) — 이름·카테고리·마모 막대·km·마지막 사용일·기본 신발 배지. 상세로 이동.
	import { base } from '$app/paths';
	import type { Shoe } from '$lib/api/shoes';
	import { kindLabel, statusMeta } from '$lib/shoeView';
	import ShoeWearBar from './ShoeWearBar.svelte';

	let { shoe }: { shoe: Shoe } = $props();
	const meta = $derived(statusMeta(shoe.status));
	const kind = $derived(kindLabel(shoe.default_for));
</script>

<a
	href="{base}/library/shoes/{shoe.id}"
	data-testid="shoe-card"
	class="flex flex-col gap-2 rounded-xl border border-border-subtle bg-surface-2 p-3 hover:bg-surface-3"
>
	<div class="flex items-center gap-2">
		<span class="truncate text-sm font-medium text-fg-primary">{shoe.name}</span>
		<span class="shrink-0 rounded bg-surface-3 px-1.5 py-0.5 text-[10px] text-fg-secondary">{shoe.category_label}</span>
		{#if kind}<span class="shrink-0 rounded border border-semantic-teal/50 px-1.5 py-0.5 text-[10px] text-semantic-teal">기본 · {kind}</span>{/if}
		<span class="ml-auto shrink-0 text-xs {meta.text}">{meta.label}</span>
	</div>
	<ShoeWearBar mileage={shoe.mileage_km} retire={shoe.retire_km} status={shoe.status} label={shoe.name} />
	<div class="flex items-baseline justify-between text-xs text-fg-muted">
		<span><span class="font-mono text-sm text-fg-primary">{Math.round(shoe.mileage_km)}</span> / {shoe.retire_km}<span class="text-[10px]"> km</span></span>
		<span>{shoe.last_used ? `마지막 ${shoe.last_used}` : '아직 신지 않음'}</span>
	</div>
	{#if shoe.message && shoe.status !== 'ok'}<p class="text-xs {meta.text}">{shoe.message}</p>{/if}
	{#if shoe.note}<p class="text-xs text-fg-secondary">{shoe.note}</p>{/if}
</a>
