<script lang="ts">
	// 플랜 상세 — 적응 상태(ACWR·HRV·피로도). P-25: 로더가 기다리지 않는 보조 데이터라 도착 전엔 자리 표시.
	import ErrorState from '$lib/components/ErrorState.svelte';
	import MetricBreakdown from '$lib/components/MetricBreakdown.svelte';
	import Skeleton from '$lib/components/Skeleton.svelte';
	import type { LoadResult } from '$lib/loadFailure';
	import type { PlanAdaptation } from '$lib/types';
	import { acwrRangeText } from '$lib/planDetailView';

	let {
		ready,
		result,
		onRetry
	}: { ready: boolean; result: LoadResult<PlanAdaptation> | null | undefined; onRetry: () => void } = $props();

	let drillAcwr = $state(false);
	const ZONE_CLASS: Record<string, string> = {
		적정: 'text-semantic-green',
		정상: 'text-semantic-green',
		저부하: 'text-semantic-amber',
		주의: 'text-semantic-amber',
		경계: 'text-semantic-amber',
		위험: 'text-semantic-red',
		저하: 'text-semantic-red'
	};
	function zoneClass(z: string): string {
		return ZONE_CLASS[z] ?? 'text-fg-secondary';
	}
	const adaptation = $derived(result?.ok ? result.data : null);
</script>

{#if !ready}
	<div class="border-b border-border-subtle px-4 py-3" aria-busy="true" data-testid="plan-adaptation-skeleton">
		<span class="sr-only">적응 지표를 불러오는 중</span>
		<Skeleton class="mb-3 w-20" />
		<div class="flex flex-col gap-2"><Skeleton class="w-48" /><Skeleton class="w-40" /></div>
	</div>
{:else if result && !result.ok}
	<div class="px-4 py-2"><ErrorState compact message="적응 지표를 불러오지 못했어요" failure={result.failure} {onRetry} /></div>
{:else if adaptation && (adaptation.acwr || adaptation.hrv || adaptation.fatigue_avg)}
	<div class="border-b border-border-subtle px-4 py-3">
		<h2 class="mb-2 text-xs uppercase tracking-wide text-fg-muted">적응 상태</h2>
		<ul class="flex flex-col gap-2 text-sm">
			{#if adaptation.acwr}
				{@const a = adaptation.acwr}
				<li>
					<button type="button" onclick={() => (drillAcwr = true)} class="flex w-full items-center gap-2 text-left hover:bg-surface-2">
						<span class="w-24 shrink-0 text-fg-secondary">ACWR</span>
						<span class="font-mono font-medium">{a.value.toFixed(2)}</span>
						<span class="text-xs {zoneClass(a.zone)}">● {a.zone}</span>
						<span class="ml-auto text-xs text-fg-muted">{acwrRangeText(a.optimal_range) ?? ''} ›</span>
					</button>
				</li>
			{/if}
			{#if adaptation.hrv}
				{@const h = adaptation.hrv}
				<li class="flex items-center gap-2">
					<span class="w-24 shrink-0 text-fg-secondary">HRV</span>
					<span class="font-mono font-medium">{Math.round(h.value)}ms</span>
					{#if h.delta_pct != null && h.zone}
						<span class="text-xs {zoneClass(h.zone)}">● 기준 {h.delta_pct > 0 ? '+' : ''}{h.delta_pct}% ({h.zone})</span>
					{/if}
				</li>
			{/if}
			{#if adaptation.fatigue_avg}
				{@const f = adaptation.fatigue_avg}
				<li class="flex items-center gap-2">
					<span class="w-24 shrink-0 text-fg-secondary">피로도 주간 평균</span>
					<span class="font-mono font-medium">{f.value.toFixed(1)} / 10</span>
					<span class="text-xs text-fg-muted">({f.n}회 입력)</span>
				</li>
			{/if}
		</ul>
	</div>
{/if}

{#if drillAcwr && adaptation?.acwr}<MetricBreakdown slug="acwr" scopeType="daily" scopeId={adaptation.acwr.date} onClose={() => { drillAcwr = false; }} />{/if}
