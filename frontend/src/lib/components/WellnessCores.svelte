<script lang="ts">
	// 핵심 카드 2열 — HRV(밴드)·안정 심박(p25–p75)·Body Battery(최고/최저/충전)·스트레스·걸음. 기준선 n<7은 수집 중 문구.
	import { base } from '$app/paths';
	import { baselineNote } from '$lib/wellnessDay';
	import type { WellnessDetailData } from '$lib/types';

	let { detail }: { detail: WellnessDetailData } = $props();
	const core = $derived(detail.core);
	const bl = $derived(detail.baselines);
	const bb = $derived(detail.body_battery);
	const hrv = $derived(bl.hrv_last_night);
	const rhr = $derived(bl.resting_hr);
	const href = (slug: string) => `${base}/library/metrics/${slug}?date=${detail.date}`;
	const hrvInBand = $derived(
		hrv?.garmin_band && core.hrv_last_night != null
			? core.hrv_last_night >= hrv.garmin_band[0] && core.hrv_last_night <= hrv.garmin_band[1]
			: null
	);
</script>

<div class="grid grid-cols-2 gap-2">
	{#if core.hrv_last_night != null}
		<a href={href('hrv_last_night')} class="rounded-xl bg-surface-2 p-3">
			<span class="text-xs text-fg-muted">HRV (야간)</span>
			<p class="mt-1 font-mono text-lg font-semibold leading-none">{Math.round(core.hrv_last_night)}<span class="ml-0.5 text-xs font-normal text-fg-muted">ms</span></p>
			{#if hrv?.garmin_band}
				<p class="mt-1 text-xs text-fg-muted">
					Garmin 범위 {hrv.garmin_band[0]}–{hrv.garmin_band[1]}{hrvInBand != null ? (hrvInBand ? ' · 범위 안' : ' · 범위 밖') : ''}
				</p>
			{:else if hrv}
				<p class="mt-1 text-xs text-fg-muted">평소 {hrv.p25}–{hrv.p75}</p>
			{:else}
				<p class="mt-1 text-xs text-fg-muted">기준선 수집 중</p>
			{/if}
		</a>
	{/if}
	{#if core.resting_hr != null}
		<a href={href('resting_hr')} class="rounded-xl bg-surface-2 p-3">
			<span class="text-xs text-fg-muted">안정 심박</span>
			<p class="mt-1 font-mono text-lg font-semibold leading-none">{Math.round(core.resting_hr)}<span class="ml-0.5 text-xs font-normal text-fg-muted">bpm</span></p>
			<p class="mt-1 text-xs text-fg-muted">{rhr ? `평소 ${rhr.p25}–${rhr.p75}` : '기준선 수집 중'}</p>
		</a>
	{/if}
	{#if bb && (bb.high != null || bb.low != null)}
		<a href={href('body_battery_high')} class="rounded-xl bg-surface-2 p-3">
			<span class="text-xs text-fg-muted">Body Battery</span>
			<p class="mt-1 font-mono text-lg font-semibold leading-none">
				{bb.high ?? '—'}<span class="ml-1 text-xs font-normal text-fg-muted">최고</span>
			</p>
			<p class="mt-1 text-xs text-fg-muted">
				최저 {bb.low ?? '—'}{bb.charged != null ? ` · 수면 중 +${Math.round(bb.charged)}` : ''}
			</p>
		</a>
	{/if}
	{#if core.avg_stress != null}
		<a href={href('avg_stress')} class="rounded-xl bg-surface-2 p-3">
			<span class="text-xs text-fg-muted">평균 스트레스</span>
			<p class="mt-1 font-mono text-lg font-semibold leading-none">{Math.round(core.avg_stress)}</p>
			{#if detail.as_of}<p class="mt-1 text-xs text-fg-muted">{detail.as_of.avg_stress} 기준</p>{/if}
		</a>
	{/if}
	{#if core.steps != null}
		<div class="rounded-xl bg-surface-2 p-3">
			<span class="text-xs text-fg-muted">걸음수</span>
			<p class="mt-1 font-mono text-lg font-semibold leading-none">{core.steps.toLocaleString('ko-KR')}</p>
			{#if detail.as_of}<p class="mt-1 text-xs text-fg-muted">{detail.as_of.steps} 기준</p>{/if}
		</div>
	{/if}
</div>
{#if hrv && baselineNote(hrv.n)}<p class="mt-1 text-xs text-fg-muted">{baselineNote(hrv.n)}</p>{/if}
