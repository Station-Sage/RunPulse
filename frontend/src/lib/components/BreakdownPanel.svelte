<script lang="ts">
	// 메트릭 상세의 인라인 분해 패널 — 선택일(slug, date)의 explain을 불러 BreakdownView로 그린다.
	import { getMetricExplain } from '$lib/api/metrics';
	import type { MetricExplainData } from '$lib/types';
	import BreakdownView from './BreakdownView.svelte';
	import Icon from './Icon.svelte';

	let {
		slug,
		date,
		compareGroup,
		onDrillTerm,
		onClear
	}: {
		slug: string;
		date: string;
		compareGroup?: { key: string; label: string; provider: string } | null;
		onDrillTerm?: (token: string) => void;
		onClear?: () => void;
	} = $props();

	let data = $state<MetricExplainData | null>(null);
	let status = $state<'loading' | 'ok' | 'none'>('loading');

	$effect(() => {
		const s = slug;
		const d = date;
		let cancelled = false;
		status = 'loading';
		getMetricExplain(s, 'daily', d)
			.then((r) => {
				if (cancelled) return;
				data = r.formula ? r : null;
				status = r.formula ? 'ok' : 'none';
			})
			.catch(() => {
				if (!cancelled) status = 'none';
			});
		return () => {
			cancelled = true;
		};
	});
</script>

<section class="min-h-[22rem] rounded-xl bg-surface-2" aria-label="{date} 분해" data-testid="breakdown-panel">
	<div class="flex items-center justify-between border-b border-border-subtle px-4 py-2">
		<h2 class="text-sm font-semibold">{Number(date.slice(5, 7))}월 {Number(date.slice(8, 10))}일 분해</h2>
		{#if onClear}
			<button type="button" class="text-fg-muted" aria-label="선택 해제" onclick={onClear}>
				<Icon name="close" class="h-4 w-4" />
			</button>
		{/if}
	</div>
	{#if status === 'loading'}
		<p class="p-4 text-sm text-fg-muted">불러오는 중…</p>
	{:else if status === 'ok' && data}
		<BreakdownView {data} {compareGroup} {onDrillTerm} />
	{:else}
		<p class="p-4 text-sm text-fg-muted">이 날은 분해할 계산 값이 없어요.</p>
	{/if}
</section>
