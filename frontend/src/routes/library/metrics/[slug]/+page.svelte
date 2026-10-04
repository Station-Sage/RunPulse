<script lang="ts">
	// 03c-library.md 3-F — 메트릭 상세. 시계열 차트 + 계산 분해 바텀시트.
	import type { MetricTrendPageData } from './+page';
	import TrendChart from '$lib/components/TrendChart.svelte';
	import BreakdownPanel from '$lib/components/BreakdownPanel.svelte';
	import MetricAbout from '$lib/components/MetricAbout.svelte';
	import MetricBreakdown from '$lib/components/MetricBreakdown.svelte';
	import DrillPanel from '$lib/components/DrillPanel.svelte';
	import { changeLabel } from '$lib/trendChart';
	import { goto, replaceState } from '$app/navigation';
	import { page } from '$app/state';
	import { base } from '$app/paths';
	import { EXPLAIN_SUPPORTED_SLUGS } from '$lib/api/metrics';
	import { openDrill, tokenSlug } from '$lib/drillStack';

	let { data }: { data: MetricTrendPageData } = $props();

	// 분해 v2(explain=1, §C3) 지원 슬러그는 DrillPanel(URL 스택), 그 외는 기존 MetricBreakdown 바텀시트.
	const explainSupported = $derived(EXPLAIN_SUPPORTED_SLUGS.has(data.slug));

	const PERIODS = [
		{ key: '4w', label: '4주' },
		{ key: '3m', label: '3개월' },
		{ key: '6m', label: '6개월' },
		{ key: '1y', label: '1년' }
	];

	let breakdownOpen = $state(false);

	const points = $derived(data.trend?.points ?? []);
	const latestDate = $derived(points.at(-1)?.date ?? '');

	// 선택일 = 차트 pin = 분해 기준일. `?date=`는 히스토리를 쌓지 않고 교체한다.
	let pinned = $state<string | null>(data.date);
	$effect(() => {
		pinned = data.date;
	});
	const panelDate = $derived(pinned ?? latestDate);

	function setPinned(d: string | null) {
		pinned = d;
		const u = new URL(page.url);
		if (d) u.searchParams.set('date', d);
		else u.searchParams.delete('date');
		replaceState(u, page.state);
	}

	function selectPeriod(key: string) {
		goto(`?period=${key}${pinned ? `&date=${pinned}` : ''}`);
	}

	// 입력 지표 행 → 같은 날짜·기간으로 그 지표 상세
	function drillTerm(token: string) {
		const slug = tokenSlug(token);
		goto(`${base}/library/metrics/${slug}?period=${data.period}${panelDate ? `&date=${panelDate}` : ''}`);
	}

	function formatPeak(trend: typeof data.trend): string {
		if (!trend?.peak) return '—';
		const v = typeof trend.peak.value === 'number' ? trend.peak.value.toFixed(1) : '—';
		return `${v}${trend.unit ? ' ' + trend.unit : ''} (${trend.peak.date})`;
	}
</script>

<svelte:head><title>{data.trend?.label ?? data.slug} · RunPulse</title></svelte:head>

<DrillPanel scopeType="daily" scopeId={latestDate}>

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

	<div class="grid grid-cols-1 gap-4 px-4 py-4 lg:grid-cols-12">
	<div class="flex flex-col gap-4 lg:col-span-8">
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
				<span class="font-mono text-xl font-bold">{changeLabel(points)}</span>
			</div>
			<div class="flex flex-col gap-0.5 rounded-xl bg-surface-2 p-3">
				<span class="text-xs text-fg-muted">피크</span>
				<span class="text-xs font-medium">{formatPeak(data.trend)}</span>
			</div>
		</div>

		<!-- 추세 차트 (y축·날짜 눈금·스크럽 포함) -->
		{#if points.length > 1}
			<div class="rounded-xl bg-surface-2 p-3">
				<TrendChart
					series={[{ key: data.slug, label: data.trend.label, color: '#3b82f6', points }]}
					unit={data.trend.unit}
					bands={data.trend.bands ?? []}
					baseline={data.trend.baseline ?? null}
					smooth={data.period === '3m' || data.period === '6m' || data.period === '1y'}
					name={data.trend.name_ko ?? data.trend.label}
					periodLabel={PERIODS.find((x) => x.key === data.period)?.label ?? ''}
					selectedDate={pinned}
					onSelect={setPinned}
				/>
			</div>
		{:else}
			<div class="rounded-xl bg-surface-2 p-3 text-center text-sm text-fg-muted">
				데이터 수집 중
			</div>
		{/if}

		{#if explainSupported && panelDate}
			<BreakdownPanel slug={data.slug} date={panelDate} onDrillTerm={drillTerm} onClear={pinned ? () => setPinned(null) : undefined} />
		{/if}

		</div>
		<div class="flex flex-col gap-4 lg:col-span-4">
			<MetricAbout slug={data.slug} trend={data.trend} date={panelDate} {explainSupported} />
		</div>
		<div class="flex flex-col gap-4 lg:col-span-12">
		<!-- 계산 분해 / Provider 비교 버튼 -->
		<div class="flex gap-2">
			<button
				class:hidden={explainSupported}
				class="flex-1 rounded-lg border border-border-subtle bg-surface-2 py-2 text-sm text-fg-secondary"
				onclick={() => (explainSupported ? openDrill(data.slug) : (breakdownOpen = true))}
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
	</div>

	<!-- 계산 분해 바텀시트(v1 — explain=1 미지원 슬러그만) -->
	{#if breakdownOpen && latestDate && !explainSupported}
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

</DrillPanel>
