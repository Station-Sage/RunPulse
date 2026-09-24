<script lang="ts">
	// 03c-library.md 3-F — 메트릭 상세. 시계열 차트 + 계산 분해 바텀시트.
	import type { MetricTrendPageData } from './+page';
	import Sparkline from '$lib/components/Sparkline.svelte';
	import MetricBreakdown from '$lib/components/MetricBreakdown.svelte';
	import { goto } from '$app/navigation';
	import { base } from '$app/paths';

	let { data }: { data: MetricTrendPageData } = $props();

	const PERIODS = [
		{ key: '4w', label: '4주' },
		{ key: '3m', label: '3개월' },
		{ key: '6m', label: '6개월' },
		{ key: '1y', label: '1년' }
	];

	let breakdownOpen = $state(false);

	const points = $derived(data.trend?.points ?? []);
	const latestDate = $derived(points.at(-1)?.date ?? '');

	function selectPeriod(key: string) {
		goto(`?period=${key}`);
	}

	function formatChangePct(v: number | null): string {
		if (v == null) return '—';
		const sign = v >= 0 ? '+' : '';
		return `${sign}${v.toFixed(1)}%`;
	}

	function formatPeak(trend: typeof data.trend): string {
		if (!trend?.peak) return '—';
		const v = typeof trend.peak.value === 'number' ? trend.peak.value.toFixed(1) : '—';
		return `${v}${trend.unit ? ' ' + trend.unit : ''} (${trend.peak.date})`;
	}
</script>

<svelte:head><title>{data.trend?.label ?? data.slug} · RunPulse</title></svelte:head>

<!-- 헤더 -->
<div class="flex items-center gap-2 border-b border-border-subtle px-4 py-3">
	<a href="{base}/library/metrics" class="shrink-0 text-fg-muted" aria-label="메트릭 브라우저로">←</a>
	<h1 class="text-base font-semibold">{data.trend?.label ?? data.slug}</h1>
	{#if data.trend?.unit}
		<span class="text-xs text-fg-muted">({data.trend.unit})</span>
	{/if}
</div>

{#if data.errorMessage && !data.trend}
	<div class="px-4 py-8 text-center">
		<p class="text-sm text-fg-secondary">{data.errorMessage}</p>
		<a href="{base}/library/metrics" class="mt-2 block text-xs text-fg-muted underline">← 메트릭 브라우저로</a>
	</div>
{:else if data.trend}
	<!-- 기간 선택 버튼 -->
	<div class="flex gap-2 border-b border-border-subtle px-4 py-2">
		{#each PERIODS as p}
			<button
				class="rounded-full px-3 py-1 text-xs {data.period === p.key
					? 'bg-fg-primary text-surface-1'
					: 'bg-surface-2 text-fg-secondary'}"
				onclick={() => selectPeriod(p.key)}
			>
				{p.label}
			</button>
		{/each}
	</div>

	<div class="flex flex-col gap-4 px-4 py-4">
		<!-- 현재값·변화율·피크 요약 -->
		<div class="grid grid-cols-3 gap-2">
			<div class="flex flex-col gap-0.5 rounded-xl bg-surface-2 p-3">
				<span class="text-xs text-fg-muted">현재</span>
				<span class="font-mono text-xl font-bold">
					{data.trend.current != null ? data.trend.current.toFixed(1) : '—'}
				</span>
				{#if data.trend.unit}
					<span class="text-xs text-fg-muted">{data.trend.unit}</span>
				{/if}
			</div>
			<div class="flex flex-col gap-0.5 rounded-xl bg-surface-2 p-3">
				<span class="text-xs text-fg-muted">30일 변화</span>
				<span class="font-mono text-xl font-bold">{formatChangePct(data.trend.change_pct)}</span>
			</div>
			<div class="flex flex-col gap-0.5 rounded-xl bg-surface-2 p-3">
				<span class="text-xs text-fg-muted">피크</span>
				<span class="text-xs font-medium">{formatPeak(data.trend)}</span>
			</div>
		</div>

		<!-- 스파크라인 (큰 차트) -->
		{#if points.length > 1}
			<div class="rounded-xl bg-surface-2 p-3">
				<Sparkline data={points.map((p) => p.value)} height={120} color="#3b82f6" />
				<div class="mt-1 flex justify-between text-[10px] text-fg-muted">
					<span>{points[0]?.date ?? ''}</span>
					<span>{points.at(-1)?.date ?? ''}</span>
				</div>
			</div>
		{:else}
			<div class="rounded-xl bg-surface-2 p-3 text-center text-sm text-fg-muted">
				데이터 수집 중
			</div>
		{/if}

		<!-- 계산 분해 / Provider 비교 버튼 -->
		<div class="flex gap-2">
			<button
				class="flex-1 rounded-lg border border-border-subtle bg-surface-2 py-2 text-sm text-fg-secondary"
				onclick={() => (breakdownOpen = true)}
				disabled={!latestDate}
			>
				계산 분해 보기
			</button>
			<a
				href="{base}/library/providers"
				class="flex-1 rounded-lg border border-border-subtle bg-surface-2 py-2 text-center text-sm text-fg-secondary"
			>
				Provider 비교
			</a>
		</div>
	</div>

	<!-- 계산 분해 바텀시트 -->
	{#if breakdownOpen && latestDate}
		<MetricBreakdown
			slug={data.slug}
			scopeType="daily"
			scopeId={latestDate}
			onClose={() => (breakdownOpen = false)}
		/>
	{/if}
{:else}
	<div class="px-4 py-8 text-center">
		<p class="text-sm text-fg-muted">데이터 수집 중</p>
	</div>
{/if}
