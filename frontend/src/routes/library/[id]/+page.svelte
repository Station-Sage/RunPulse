<script lang="ts">
	// 03c-library.md 3-C — 활동 상세, 요약 탭만(Phase 7a).
	// 스트림·랩·메트릭 탭은 범위 밖(API 없음 또는 7b 몫).
	import type { ActivityPageData } from './+page';
	import MetricCell from '$lib/components/MetricCell.svelte';
	import { providerLabel, providerBadgeClass } from '$lib/provider';
	import { formatDistance, formatDuration, formatPace, formatDate } from '$lib/format';
	import { base } from '$app/paths';
	import type { ActivityMetric, ProviderKey } from '$lib/types';

	let { data }: { data: ActivityPageData } = $props();

	const core = $derived(data.activity?.core ?? null);
	const metricsByCategory = $derived(data.activity?.metrics_by_category ?? {});
	const streams = $derived(data.activity?.streams ?? null);

	// 모든 카테고리에서 numeric_value가 있는 메트릭을 모아 최대 8개 선택.
	// 순서: performance → running → 나머지 카테고리 순.
	const CATEGORY_ORDER = ['performance', 'running', 'fitness', 'wellness', 'power', 'environment'];

	const keyMetrics = $derived((): ActivityMetric[] => {
		const ordered: ActivityMetric[] = [];
		const seen = new Set<string>();

		for (const cat of [...CATEGORY_ORDER, ...Object.keys(metricsByCategory)]) {
			const items = metricsByCategory[cat] ?? [];
			for (const m of items) {
				if (!seen.has(m.metric_name) && m.numeric_value != null) {
					seen.add(m.metric_name);
					ordered.push(m);
					if (ordered.length >= 8) return ordered;
				}
			}
		}
		return ordered;
	});

	function metricDisplayValue(m: ActivityMetric): string {
		if (m.numeric_value == null) return '—';
		const v = m.numeric_value;
		// 페이스 관련 메트릭(초/km)은 mm:ss 형식
		if (m.metric_name.includes('pace') || m.unit === 'sec/km') {
			return formatPace(v);
		}
		// 소수점 1자리까지만
		return Number.isInteger(v) ? String(v) : v.toFixed(1);
	}
</script>

{#if !core}
	<div class="flex flex-col items-center gap-3 px-4 py-20 text-center">
		<p class="text-lg text-fg-secondary">활동을 찾을 수 없습니다</p>
		{#if data.errorMessage}
			<p class="text-xs text-fg-muted">{data.errorMessage}</p>
		{/if}
		<a href="{base}/library" class="text-sm text-fg-secondary underline">← 목록으로</a>
	</div>
{:else}
	<!-- 헤더: 이름 + 날짜 + 소스 배지 -->
	<div class="flex items-start gap-2 border-b border-border-subtle px-4 py-3">
		<a href="{base}/library" class="mt-0.5 shrink-0 text-fg-muted" aria-label="목록으로">←</a>
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

	<!-- 탭 — 요약(활성), 소스 비교(링크), 나머지는 비활성 표시 (범위 밖) -->
	<div class="flex border-b border-border-subtle">
		<span class="flex-1 border-b-2 border-fg-primary py-2.5 text-center text-sm font-medium text-fg-primary">
			요약
		</span>
		<a
			href="{base}/library/{core.id}/providers"
			class="flex-1 py-2.5 text-center text-sm text-fg-secondary hover:text-fg-primary"
		>
			소스 비교
		</a>
		{#each ['스트림', '랩', '메트릭'] as label}
			<button type="button" disabled class="flex-1 py-2.5 text-sm text-fg-muted">{label}</button>
		{/each}
	</div>

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
				<span class="text-sm">↑<span class="font-mono font-bold">{core.elevation_gain}</span> <span class="text-fg-muted">m</span></span>
			{/if}
		</div>

		<!-- 핵심 메트릭 그리드 (최대 8개) -->
		{#if keyMetrics().length > 0}
			<section class="flex flex-col gap-2">
				<p class="text-xs uppercase tracking-wide text-fg-muted">핵심 메트릭</p>
				<div class="grid grid-cols-2 gap-2 sm:grid-cols-4">
					{#each keyMetrics() as m (m.metric_name)}
						<MetricCell
							slug={m.metric_name}
							label={m.description || m.metric_name}
							value={metricDisplayValue(m)}
							unit={m.unit && !m.metric_name.includes('pace') ? m.unit : undefined}
							provider={(m.provider as ProviderKey) ?? null}
							drillable={false}
							unavailable={m.numeric_value == null}
						/>
					{/each}
				</div>
			</section>
		{/if}

		<!-- 스트림 요약 (존재 여부 + 포인트 수) -->
		<section class="flex flex-col gap-1 rounded-lg border border-border-subtle bg-surface-2 px-4 py-3">
			<p class="text-xs uppercase tracking-wide text-fg-muted">스트림 데이터</p>
			{#if streams && streams.length > 0}
				<p class="text-sm text-fg-secondary">{streams.length.toLocaleString('ko-KR')}개 포인트</p>
				<p class="text-xs text-fg-muted">스트림 차트는 Phase 7b에서 제공됩니다.</p>
			{:else}
				<p class="text-sm text-fg-muted">스트림 데이터 없음</p>
			{/if}
		</section>

	</div>
{/if}
