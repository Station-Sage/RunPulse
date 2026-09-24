<script lang="ts">
	// 03c-library.md 3-C — 활동 상세 요약 탭. 나머지 탭은 별도 라우트(ActivityTabs).
	import type { ActivityPageData } from './+page';
	import ActivityTabs from '$lib/components/ActivityTabs.svelte';
	import MetricCell from '$lib/components/MetricCell.svelte';
	import MetricBreakdown from '$lib/components/MetricBreakdown.svelte';
	import Sparkline from '$lib/components/Sparkline.svelte';
	import EnvContextCard from '$lib/components/EnvContextCard.svelte';
	import { providerLabel, providerBadgeClass } from '$lib/provider';
	import { formatDistance, formatDuration, formatPace, formatDate, formatUnitValue } from '$lib/format';
	import { formatMetricValue, hrZoneShares, metricUnit, pickKeyMetrics } from '$lib/metrics';
	import { base } from '$app/paths';
	import type { DrillTarget } from '$lib/evidence';
	import type { ActivityMetric, ProviderKey } from '$lib/types';

	let { data }: { data: ActivityPageData } = $props();

	const core = $derived(data.activity?.core ?? null);
	const metricsByCategory = $derived(data.activity?.metrics_by_category ?? {});
	const streams = $derived(data.activity?.streams ?? null);

	const keyMetrics = $derived(pickKeyMetrics(metricsByCategory));
	const zoneData = $derived(hrZoneShares(metricsByCategory));
	const ZONE_COLORS = ['#38bdf8', '#10b981', '#f59e0b', '#f97316', '#ef4444'];
	// streams 행은 elapsed_sec 순 — 페이스(초/km)는 speed_ms에서 환산, null은 선을 끊는다.
	const paceSeries = $derived((streams ?? []).map((p) => (p.speed_ms != null && p.speed_ms > 0 ? 1000 / p.speed_ms : null)));
	const hrSeries = $derived((streams ?? []).map((p) => p.heart_rate));
	const streamSource = $derived(streams && streams.length > 0 ? streams[0].source : null);
	let drillStack = $state<DrillTarget[]>([]);
	const drillTop = $derived(drillStack.length > 0 ? drillStack[drillStack.length - 1] : null);
	function openMetric(slug: string) {
		if (!core) return;
		drillStack = [...drillStack, { slug, scopeType: 'activity', scopeId: String(core.id) }];
	}
	function handleDrillInput(slug: string) {
		const top = drillStack.length > 0 ? drillStack[drillStack.length - 1] : null;
		drillStack = [...drillStack, { slug, scopeType: top?.scopeType ?? 'activity', scopeId: top?.scopeId ?? String(core?.id ?? '') }];
	}
</script>

<svelte:head><title>{core?.name ?? '활동 상세'} · RunPulse</title></svelte:head>

{#if !core}
	<div class="flex flex-col items-center gap-3 px-4 py-20 text-center">
		<p class="text-lg text-fg-secondary">활동을 찾을 수 없습니다</p>
		{#if data.errorMessage}
			<p class="text-xs text-fg-muted">{data.errorMessage}</p>
		{/if}
		<a href="{base}/library/activities" class="text-sm text-fg-secondary underline">← 목록으로</a>
	</div>
{:else}
	<!-- 헤더: 이름 + 날짜 + 소스 배지 -->
	<div class="flex items-start gap-2 border-b border-border-subtle px-4 py-3">
		<a href="{base}/library/activities" class="mt-0.5 shrink-0 text-fg-muted" aria-label="목록으로">←</a>
		<div class="flex min-w-0 flex-1 flex-col gap-0.5">
			<div class="flex items-center gap-2">
				<h1 class="truncate text-base font-semibold">{core.name}</h1>
				<span
					class="shrink-0 rounded px-1.5 py-0.5 text-[10px] text-white {providerBadgeClass(
						core.source as ProviderKey
					)}"
				>
					{providerLabel(core.source as ProviderKey)}
				</span>
			</div>
			<p class="text-xs text-fg-muted">{formatDate(core.start_time)}</p>
		</div>
	</div>

	<!-- 탭 -->
	<ActivityTabs activityId={core.id} active="summary" />

	<!-- 요약 탭 본문 -->
	<div class="flex flex-col gap-5 px-4 py-4">

		<!-- 핵심 통계 바 -->
		<div class="flex flex-wrap gap-x-5 gap-y-1 rounded-lg border border-border-subtle bg-surface-2 px-4 py-3">
			{#if core.distance_m != null}
				<span class="text-sm"><span class="font-mono font-bold">{formatDistance(core.distance_m)}</span></span>
			{/if}
			{#if core.duration_sec != null}
				<span class="text-sm"><span class="font-mono font-bold">{formatDuration(core.duration_sec)}</span></span>
			{/if}
			{#if core.avg_pace_sec_km != null}
				<span class="text-sm"><span class="font-mono font-bold">{formatPace(core.avg_pace_sec_km)}</span></span>
			{/if}
			{#if core.avg_hr != null}
				<span class="text-sm">HR <span class="font-mono font-bold">{core.avg_hr}</span> <span class="text-fg-muted">bpm</span></span>
			{/if}
			{#if core.elevation_gain != null && (core.elevation_gain as number) > 0}
				{@const elev = formatUnitValue(core.elevation_gain as number, 'm')}
				<span class="text-sm">↑<span class="font-mono font-bold">{elev.display}</span> <span class="text-fg-muted">{elev.unit}</span></span>
			{/if}
		</div>

		<!-- 핵심 메트릭 그리드 (최대 8개) -->
		{#if keyMetrics.length > 0}
			<section class="flex flex-col gap-2">
				<div class="flex items-center justify-between"><p class="text-xs uppercase tracking-wide text-fg-muted">핵심 메트릭</p><a href="{base}/library/{core.id}/metrics" class="text-xs text-fg-secondary hover:text-fg-primary">전체 메트릭 보기 →</a></div>
				<div class="grid grid-cols-2 gap-2 sm:grid-cols-4">
					{#each keyMetrics as m (m.metric_name)}
						<MetricCell
							slug={m.metric_name}
							label={m.description || m.metric_name}
							value={formatMetricValue(m)}
							unit={metricUnit(m) || undefined}
							provider={(m.provider as ProviderKey) ?? null}
							drillable={true}
							onDrill={(p) => openMetric(p.slug)}
							unavailable={m.numeric_value == null}
						/>
					{/each}
				</div>
			</section>
		{/if}

		{#if paceSeries.some((v) => v != null) || hrSeries.some((v) => v != null)}
			<section class="flex flex-col gap-2">
				<div class="flex items-center justify-between">
					<p class="text-xs uppercase tracking-wide text-fg-muted">페이스 · 심박 흐름</p>
					<a href="{base}/library/{core.id}/streams" class="text-xs text-fg-secondary hover:text-fg-primary">스트림 탭에서 전체 보기 →</a>
				</div>
				{#if paceSeries.some((v) => v != null)}
					<div>
						<p class="mb-0.5 text-[10px] text-fg-muted">페이스</p>
						<Sparkline data={paceSeries} height={40} color="#3b82f6" />
					</div>
				{/if}
				{#if hrSeries.some((v) => v != null)}
					<div>
						<p class="mb-0.5 text-[10px] text-fg-muted">심박</p>
						<Sparkline data={hrSeries} height={40} color="#ef4444" />
					</div>
				{/if}
				<p class="text-xs text-fg-muted">{(streams ?? []).length.toLocaleString('ko-KR')}개 포인트{#if streamSource}{' · '}소스: {providerLabel(streamSource as ProviderKey)}{/if}</p>
			</section>
		{:else}
			<p class="text-xs text-fg-muted">스트림 데이터 없음</p>
		{/if}
		{#if zoneData}
			<section class="flex flex-col gap-2">
				<div class="flex items-center justify-between">
					<p class="text-xs uppercase tracking-wide text-fg-muted">HR 존 분포</p>
					<span class="rounded px-1.5 py-0.5 text-[10px] text-white {providerBadgeClass(zoneData.provider as ProviderKey | null)}">{providerLabel(zoneData.provider as ProviderKey | null)}</span>
				</div>
				<div class="flex flex-col gap-1.5">
					{#each zoneData.zones as z (z.zone)}
						<div class="flex items-center gap-2 text-xs">
							<span class="w-5 font-mono text-fg-secondary">Z{z.zone}</span>
							<div class="h-2 flex-1 rounded bg-surface-3">
								<div class="h-2 rounded" style="width:{z.pct}%; background:{ZONE_COLORS[z.zone - 1]}"></div>
							</div>
							<span class="w-20 text-right font-mono text-fg-secondary">{z.pct}% · {formatDuration(z.sec)}</span>
						</div>
					{/each}
				</div>
			</section>
		{/if}
		<EnvContextCard metrics={metricsByCategory.weather ?? []} />

	</div>
{/if}
{#if drillTop}<MetricBreakdown slug={drillTop.slug} scopeType={drillTop.scopeType} scopeId={drillTop.scopeId} onClose={() => { drillStack = []; }} onDrillInput={handleDrillInput} />{/if}
