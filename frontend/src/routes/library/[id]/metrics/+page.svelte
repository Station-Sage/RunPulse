<script lang="ts">
	// 03c-library.md 3-C 메트릭 탭 — 이 활동의 대표(is_primary) 메트릭 전체를 카테고리별로.
	// 행을 누르면 계산 분해(DrillPanel, scope=activity)가 열린다(P2). 소스는 배지로 항상 표기(P3).
	import type { MetricsTabPageData } from './+page';
	import DrillPanel from '$lib/components/DrillPanel.svelte';
	import { openDrill } from '$lib/drillStack';
	import { providerLabel } from '$lib/provider';
	import { formatMetricValue, metricUnit } from '$lib/metrics';
	import { buildMetricSections, isEstimate } from '$lib/metricSections';
	import { statusColorVar } from '$lib/statusColor';
	import { page } from '$app/state';
	import { base } from '$app/paths';
	import type { ActivityMetric, ProviderKey } from '$lib/types';
	let { data }: { data: MetricsTabPageData } = $props();
	let query = $state('');
	function matches(m: ActivityMetric): boolean {
		const q = query.trim().toLowerCase();
		if (!q) return true;
		return m.metric_name.toLowerCase().includes(q) || m.description.toLowerCase().includes(q);
	}
	const devMode = $derived(page.url.searchParams.get('dev') === '1');
	const sections = $derived(buildMetricSections(data.metricsByCategory, matches, devMode));
	const total = $derived(
		Object.values(data.metricsByCategory).reduce((n, items) => n + items.length, 0)
	);
</script>

<svelte:head><title>활동 메트릭 · RunPulse</title></svelte:head>

<DrillPanel scopeType="activity" scopeId={String(data.activityId)}>

{#if data.errorMessage && total === 0}
	<div class="px-4 py-8 text-center">
		<p class="text-sm text-fg-secondary">{data.errorMessage}</p>
		<a href="{base}/library/{data.activityId}" class="mt-2 block text-xs text-fg-muted underline">← 활동으로 돌아가기</a>
	</div>
{:else if total === 0}
	<div class="px-4 py-8 text-center">
		<p class="text-sm text-fg-muted">메트릭 데이터 수집 중</p>
	</div>
{:else}
	<div class="flex flex-col gap-3 px-4 py-4">
		<input type="search" bind:value={query} placeholder="메트릭 검색 (이름·설명)" class="w-full rounded-lg border border-border-subtle bg-surface-2 px-3 py-2 text-sm text-fg-primary placeholder:text-fg-muted focus:outline-none" />
		<p class="text-xs text-fg-muted">{total}개 메트릭</p>
		{#if sections.length === 0}
			<p class="text-sm text-fg-muted">일치하는 메트릭이 없습니다.</p>
		{:else}
			{#each sections as s (s.key)}
				<section class="rounded-lg border border-border-subtle" data-testid="metric-section" data-section={s.key}>
					<header class="flex items-baseline justify-between gap-2 px-3 py-2">
						<h3 class="text-sm font-semibold">{s.label}</h3>
						<span class="text-xs text-fg-secondary" data-testid="metric-section-conclusion">{s.conclusion}</span>
					</header>
					<ul class="divide-y divide-border-subtle px-3">
						{#each s.items as m (m.metric_name)}
							<li>
								<button type="button" onclick={() => openDrill(m.metric_name)} class="flex w-full flex-col gap-0.5 py-2.5 text-left hover:bg-surface-2" data-testid="metric-row">
									<span class="flex w-full items-center gap-2">
										{#if m.status}<span class="h-2 w-2 shrink-0 rounded-full" style="background:{statusColorVar(m.status)}" aria-hidden="true"></span>{/if}
										<span class="min-w-0 flex-1 truncate text-sm">{m.description || m.metric_name}</span>
										<span class="shrink-0 font-mono text-sm font-medium">{formatMetricValue(m)}{#if metricUnit(m)}<span class="ml-0.5 text-xs font-normal text-fg-secondary">{metricUnit(m)}</span>{/if}</span>
										<span class="shrink-0 rounded border border-border-subtle px-1 text-[10px] text-fg-secondary" title={providerLabel(m.provider as ProviderKey | null)} aria-label={providerLabel(m.provider as ProviderKey | null)}>{providerLabel(m.provider as ProviderKey | null).charAt(0)}</span>
										<span class="shrink-0 text-fg-muted">›</span>
									</span>
									{#if m.status_label || isEstimate(m)}
										<span class="pl-4 text-xs text-fg-secondary">{m.status_label ?? ''}{#if isEstimate(m)} <span class="rounded border border-border-subtle px-1 text-[10px]">추정</span>{/if}</span>
									{/if}
								</button>
							</li>
						{/each}
					</ul>
				</section>
			{/each}
		{/if}
	</div>
{/if}
</DrillPanel>
