<script lang="ts">
	// 03c-library.md 3-F — 메트릭 상세. 시계열 차트 + 계산 분해 바텀시트.
	import type { MetricTrendPageData } from './+page';
	import TrendChart from '$lib/components/TrendChart.svelte';
	import BreakdownPanel from '$lib/components/BreakdownPanel.svelte';
	import MetricTerm from '$lib/components/MetricTerm.svelte';
	import MetricAbout from '$lib/components/MetricAbout.svelte';
	import DrillPanel from '$lib/components/DrillPanel.svelte';
	import { changeLabel, periodChange } from '$lib/trendChart';
	import { displayUnit, formatMetric } from '$lib/format';
	import { goto, replaceState } from '$app/navigation';
	import { page } from '$app/state';
	import { base } from '$app/paths';
	import { EXPLAIN_SUPPORTED_SLUGS } from '$lib/api/metrics';
	import { openDrill, parseDrillToken } from '$lib/drillStack';
	import { metricsBackHref, fromToday } from '$lib/libraryNav';

	let { data }: { data: MetricTrendPageData } = $props();

	// 분해 v2(explain=1, §C3) 지원 슬러그는 DrillPanel(URL 스택), 그 외는 기존 MetricBreakdown 바텀시트.
	const explainSupported = $derived(EXPLAIN_SUPPORTED_SLUGS.has(data.slug));

	const PERIODS = [
		{ key: '4w', label: '4주' },
		{ key: '3m', label: '3개월' },
		{ key: '6m', label: '6개월' },
		{ key: '1y', label: '1년' }
	];

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
		const from = page.url.searchParams.get('from');
		goto(`?period=${key}${pinned ? `&date=${pinned}` : ''}${from ? `&from=${from}` : ''}`, { replaceState: true, keepFocus: true });
	}

	// 입력 지표 행 → 같은 날짜·기간으로 그 지표 상세
	function drillTerm(token: string) {
		const { slug, scope } = parseDrillToken(token);
		const act = scope ? /^a(\d+)$/.exec(scope) : null;
		if (act) {
			goto(`${base}/library/${act[1]}?from=metric`);
			return;
		}
		goto(`${base}/library/metrics/${slug}?period=${data.period}${panelDate ? `&date=${panelDate}` : ''}`);
	}

	const change = $derived(periodChange(points));
	const changeMain = $derived(
		change ? (change.pct != null ? `${change.delta >= 0 ? '+' : '−'}${Math.abs(change.pct).toFixed(1)}%` : changeLabel(points)) : '—'
	);
	const changeSub = $derived.by(() => {
		if (!change || !data.trend) return '';
		const signed = data.trend.format === 'signed';
		const v = formatMetric(data.trend, signed ? change.delta : Math.abs(change.delta));
		return `${signed ? '' : change.delta >= 0 ? '+' : '−'}${v} ${displayUnit(data.trend.unit)}`.trim();
	});
	const changeTone = $derived.by(() => {
		const hib = data.trend?.higher_is_better;
		if (!change || hib == null || change.delta === 0) return '';
		return change.delta > 0 === hib ? 'text-delta-better' : 'text-delta-worse';
	});
	const peakDate = $derived.by(() => {
		const d = data.trend?.peak?.date;
		if (!d) return '';
		const [, m, day] = d.split('-');
		return `${Number(m)}월 ${Number(day)}일`;
	});
</script>

<svelte:head><title>{data.trend?.label ?? data.slug} · RunPulse</title></svelte:head>

<DrillPanel scopeType="daily" scopeId={latestDate}>

<!-- 헤더: 2단 브레드크럼(48px) -->
<div class="flex h-12 items-center gap-2 border-b border-border-subtle px-4">
	<a href="{metricsBackHref(base)}" class="shrink-0 text-fg-muted" aria-label="메트릭 브라우저로">‹</a>
	<nav aria-label="경로" class="flex min-w-0 items-center gap-1.5 text-xs text-fg-muted">
		<a href="{base}/library" class="hover:text-fg-secondary">Library</a>
		<span aria-hidden="true">›</span>
		<a href="{metricsBackHref(base)}" class="hover:text-fg-secondary">메트릭</a>
		<span aria-hidden="true">›</span>
		<h1 class="truncate text-sm font-semibold text-fg-primary">{data.trend?.label ?? data.slug}</h1>
		{#if data.trend?.description_short}<MetricTerm slug={data.slug} label={data.trend.label} fallback={data.trend.description_short} date={panelDate} />{/if}
	</nav>
	{#if displayUnit(data.trend?.unit)}
		<span class="shrink-0 text-xs text-fg-muted">({displayUnit(data.trend?.unit)})</span>
	{/if}
	{#if data.trend?.compare_group}
		<a href="{base}/library/providers/{data.trend.compare_group.key}" class="ml-auto shrink-0 rounded-full border border-border-subtle px-2.5 py-1 text-xs text-fg-secondary">소스 비교</a>
	{/if}
	{#if fromToday(page.url.search)}
		<a href="{base}/today" class="ml-auto shrink-0 rounded-full border border-border-subtle px-2.5 py-1 text-xs text-fg-secondary">‹ Today로</a>
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
			<div class="flex min-w-0 flex-col gap-0.5 rounded-xl bg-surface-2 p-3">
				<span class="text-xs text-fg-secondary">현재</span>
				<span class="font-mono text-xl font-bold tabular-nums">{formatMetric(data.trend, data.trend.current)}</span>
				<span class="text-xs text-fg-muted">{displayUnit(data.trend.unit) || '\u00a0'}</span>
			</div>
			<div class="flex min-w-0 flex-col gap-0.5 rounded-xl bg-surface-2 p-3">
				<span class="text-xs text-fg-secondary">선택 기간 변화</span>
				<span class="font-mono text-xl font-bold tabular-nums {changeTone}">{changeMain}</span>
				<span class="text-xs text-fg-muted">{changeSub || '\u00a0'}</span>
			</div>
			<div class="flex min-w-0 flex-col gap-0.5 rounded-xl bg-surface-2 p-3">
				<span class="text-xs text-fg-secondary">피크</span>
				<span class="font-mono text-xl font-bold tabular-nums">{formatMetric(data.trend, data.trend.peak?.value)}</span>
				<span class="text-xs text-fg-muted">{peakDate || '\u00a0'}</span>
			</div>
		</div>

		<!-- 추세 차트 (y축·날짜 눈금·스크럽 포함) -->
		{#if points.length > 1}
			<div class="rounded-xl bg-surface-2 p-3">
				<TrendChart
					series={[{ key: data.slug, label: data.trend.label, color: 'var(--color-series-1)', points }]}
					unit={displayUnit(data.trend.unit)}
					formatValue={(v) => formatMetric(data.trend!, v)}
					events={data.trend.events ?? []}
					bands={data.trend.bands ?? []}
					baseline={data.trend.baseline ?? null}
					smooth={data.period === '3m' || data.period === '6m' || data.period === '1y'}
					name={data.trend.name_ko ?? data.trend.label}
					periodLabel={PERIODS.find((x) => x.key === data.period)?.label ?? ''}
					selectedDate={pinned}
					onSelect={setPinned}
				/>
				{#if data.trend.recompute_note}
					<p class="mt-2 text-xs text-fg-muted" data-testid="recompute-note">{data.trend.recompute_note.text}</p>
				{/if}
			</div>
		{:else}
			<div class="rounded-xl bg-surface-2 p-3 text-center text-sm text-fg-muted">
				데이터 수집 중
			</div>
		{/if}

		{#if explainSupported && panelDate}
			<BreakdownPanel slug={data.slug} date={panelDate} compareGroup={data.trend?.compare_group ?? null} onDrillTerm={drillTerm} onClear={pinned ? () => setPinned(null) : undefined} />
		{/if}

		</div>
		<div class="flex flex-col gap-4 lg:col-span-4">
			<MetricAbout slug={data.slug} trend={data.trend} date={panelDate} {explainSupported} />
		</div>
		<div class="flex flex-col gap-4 lg:col-span-12">
		<!-- 계산 분해 / Provider 비교 버튼 -->
		<div class="flex gap-2">
			<button
				class="flex-1 rounded-lg border border-border-subtle bg-surface-2 py-2 text-sm text-fg-secondary"
				onclick={() => openDrill(data.slug)}
				disabled={!latestDate}
			>
				계산 분해 보기
			</button>
		</div>
		</div>
	</div>

{:else}
	<div class="px-4 py-8 text-center">
		<p class="text-sm text-fg-muted">데이터 수집 중</p>
	</div>
{/if}

</DrillPanel>
