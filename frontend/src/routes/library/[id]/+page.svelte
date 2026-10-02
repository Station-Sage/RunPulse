<script lang="ts">
	// 03c-library.md 3-C — 활동 상세 요약 탭. 나머지 탭은 별도 라우트(ActivityTabs).
	import type { ActivityPageData } from './+page';
	import RouteMap from '$lib/components/RouteMap.svelte';
	import MetricCell from '$lib/components/MetricCell.svelte';
	import MetricBreakdown from '$lib/components/MetricBreakdown.svelte';
	import { providerLabel } from '$lib/provider';
	import { formatDuration, formatPace, formatUnitValue } from '$lib/format';
	import { formatMetricValue, metricUnit, pickKeyMetrics } from '$lib/metrics';
	import { base } from '$app/paths';
	import type { DrillTarget } from '$lib/evidence';
	import type { ProviderKey } from '$lib/types';
	import ActivityVerdict from '$lib/components/ActivityVerdict.svelte';
	import SplitBars from '$lib/components/SplitBars.svelte';
	import ActivityTimeline from '$lib/components/ActivityTimeline.svelte';
	import { impactLines } from '$lib/activityImpact';
	import { createActivitySelection } from '$lib/stores/activitySelection';

	let { data }: { data: ActivityPageData } = $props();

	const core = $derived(data.activity?.core ?? null);
	const metricsByCategory = $derived(data.activity?.metrics_by_category ?? {});
	const splits = $derived(data.activity?.splits ?? []);
	const series = $derived(data.activity?.series ?? null);
	const env = $derived(data.activity?.environment ?? null);
	const zones = $derived(data.activity?.hr_zones ?? null);
	const sourceDiffs = $derived((data.activity?.source_diffs ?? []).filter((d) => d.significant));
	const keyMetrics = $derived(pickKeyMetrics(metricsByCategory));
	const impactList = $derived(data.activity?.impact ? impactLines(data.activity.impact) : []);

	const selection = createActivitySelection();
	const zoneTotal = $derived(zones ? zones.sec.reduce((a, b) => a + b, 0) : 0);
	const ZONE_OPACITY = ['opacity-30', 'opacity-45', 'opacity-60', 'opacity-80', 'opacity-100'];

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
	<!-- 요약 탭 본문 -->
	<div class="flex flex-col gap-5 px-4 py-4">

		<!-- 히어로 통계 -->
		<section class="flex flex-col gap-3" aria-label="활동 요약">
			{#if core.distance_m != null}
				<div class="flex items-end gap-2">
					<span class="font-mono text-5xl font-bold leading-none">{(core.distance_m / 1000).toFixed(2)}</span>
					<span class="pb-1 text-lg text-fg-muted">km</span>
				</div>
			{/if}
			<div class="grid grid-cols-3 gap-3 rounded-lg border border-border-subtle bg-surface-2 px-4 py-3">
				<div class="flex flex-col gap-0.5">
					<span class="text-[11px] text-fg-muted">시간</span>
					<span class="font-mono text-xl font-bold">{core.duration_sec != null ? formatDuration(core.duration_sec) : '—'}</span>
				</div>
				<div class="flex flex-col gap-0.5">
					<span class="text-[11px] text-fg-muted">평균 페이스</span>
					<span class="font-mono text-xl font-bold">{core.avg_pace_sec_km != null ? formatPace(core.avg_pace_sec_km).replace('/km', '') : '—'}<span class="text-xs font-normal text-fg-muted"> /km</span></span>
				</div>
				<div class="flex flex-col gap-0.5">
					<span class="text-[11px] text-fg-muted">평균 심박</span>
					<span class="font-mono text-xl font-bold">{core.avg_hr ?? '—'}<span class="text-xs font-normal text-fg-muted"> bpm</span></span>
				</div>
			</div>
			{#if core.elevation_gain != null && (core.elevation_gain as number) > 0}
				{@const elev = formatUnitValue(core.elevation_gain as number, 'm')}
				<p class="text-xs text-fg-muted">누적 상승 <span class="font-mono font-bold text-fg-secondary">{elev.display}</span> {elev.unit}</p>
			{/if}
		</section>

		<ActivityVerdict verdict={data.activity?.verdict} onDrill={openMetric} />

		<div class="grid grid-cols-1 gap-4 md:grid-cols-2">
			{#if series}
				<RouteMap {series} selectedSeg={$selection.seg} cursorDist={$selection.cursorDist} onSelect={(seg) => selection.update((s) => ({ ...s, seg }))} />
			{/if}
			{#if splits.length > 0}
				<SplitBars {splits} selectedSeg={$selection.seg} onSelect={(seg) => selection.update((s) => ({ ...s, seg }))} />
			{/if}
		</div>

		{#if series}
			<ActivityTimeline {series} elevGainM={(core.elevation_gain as number | null) ?? null} onCursor={(d) => selection.update((s) => ({ ...s, cursorDist: d }))} />
		{:else}
			<p class="text-xs text-fg-muted">스트림 데이터 없음</p>
		{/if}

		{#if env && (env.temp_c != null || env.fearp_sec_km != null)}
			<section class="flex flex-wrap gap-x-4 gap-y-1 rounded-lg border border-border-subtle bg-surface-2 px-3 py-2 text-sm" data-testid="env-line" aria-label="환경">
				<span class="text-xs uppercase tracking-wide text-fg-muted">환경</span>
				{#if env.temp_c != null}<span>기온 <span class="font-mono">{Math.round(env.temp_c)}°C</span></span>{/if}
				{#if env.dew_point_c != null}<span>이슬점 <span class="font-mono">{Math.round(env.dew_point_c)}°C</span></span>{/if}
				{#if env.pace_effect_sec_km != null && env.pace_effect_sec_km !== 0}<span>페이스 영향 <span class="font-mono">{env.pace_effect_sec_km > 0 ? '+' : ''}{Math.round(env.pace_effect_sec_km)}초/km</span></span>{/if}
			</section>
		{/if}

		<!-- 이 러닝의 의미 -->
		{#if impactList.length > 0}<section class="flex flex-col gap-1 rounded-lg border border-border-subtle bg-surface-2 p-3"><p class="text-xs uppercase tracking-wide text-fg-muted">이 러닝의 의미</p>{#each impactList as line}<p class="text-sm text-fg-primary">{line}</p>{/each}</section>{/if}

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
							status={m.status}
							note={m.status_label}
						/>
					{/each}
				</div>
			</section>
		{/if}

		{#if zones && zoneTotal > 0}
			<section class="flex flex-col gap-2" data-testid="hr-zones">
				<div class="flex items-center justify-between">
					<p class="text-xs uppercase tracking-wide text-fg-muted">HR 존 분포</p>
					<span class="text-xs text-fg-muted">{providerLabel(zones.provider as ProviderKey)} · {zones.basis === 'intervals_zones' ? '개인 존' : '기기 존'}</span>
				</div>
				<div class="flex flex-col gap-1.5">
					{#each zones.sec as sec, i (i)}
						{@const pct = Math.round((sec / zoneTotal) * 100)}
						<div class="flex items-center gap-2 text-xs">
							<span class="w-5 font-mono text-fg-secondary">Z{i + 1}</span>
							<div class="h-2 flex-1 rounded bg-surface-3">
								<div class="h-2 rounded bg-series-1 {ZONE_OPACITY[i] ?? 'opacity-100'}" style="width:{pct}%"></div>
							</div>
							<span class="w-24 text-right font-mono text-fg-secondary">{pct}% · {formatDuration(sec)}</span>
						</div>
					{/each}
				</div>
			</section>
		{/if}

		<div class="flex flex-wrap items-center gap-3 text-xs">
			{#if sourceDiffs.length > 0}
				<a href="{base}/library/{core.id}/providers" class="rounded-full border border-border-subtle px-3 py-1 text-fg-secondary hover:text-fg-primary" data-testid="source-diff-chip">소스 차이 {sourceDiffs.length}건</a>
			{/if}
			<a href="{base}/coach" class="rounded-full border border-border-subtle px-3 py-1 text-fg-secondary hover:text-fg-primary" data-testid="ask-coach">코치에게 물어보기</a>
		</div>

	</div>
{/if}
{#if drillTop}<MetricBreakdown slug={drillTop.slug} scopeType={drillTop.scopeType} scopeId={drillTop.scopeId} onClose={() => { drillStack = []; }} onDrillInput={handleDrillInput} />{/if}
