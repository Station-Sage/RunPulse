<script lang="ts">
	// 03c-library.md 3-G — 웰니스 탭. 코어 카드 + Readiness 요약 + 트렌드 스파크라인.
	import type { WellnessPageData } from './+page';
	import Sparkline from '$lib/components/Sparkline.svelte';
	import { base } from '$app/paths';

	let { data }: { data: WellnessPageData } = $props();

	const core = $derived(data.detail?.core ?? {});
	const readiness = $derived(data.detail?.readiness_summary ?? { utrs: null, cirs: null });
	const trend = $derived(data.trend);

	function fmt(v: number | null | undefined, decimals = 0): string {
		if (v == null) return '—';
		return Number.isInteger(v) || decimals === 0 ? String(Math.round(v)) : v.toFixed(decimals);
	}

	function fmtDuration(sec: number | null | undefined): string {
		if (sec == null) return '—';
		const h = Math.floor(sec / 3600);
		const m = Math.floor((sec % 3600) / 60);
		return h > 0 ? `${h}h ${m}m` : `${m}m`;
	}
</script>

<!-- 헤더 탭 바 -->
<nav class="flex border-b border-border-subtle">
	<a
		href="{base}/library"
		class="flex-1 py-3 text-center text-sm text-fg-muted hover:text-fg-secondary"
	>
		활동
	</a>
	<a
		href="{base}/library/metrics"
		class="flex-1 py-3 text-center text-sm text-fg-muted hover:text-fg-secondary"
	>
		메트릭
	</a>
	<a
		href="{base}/library/wellness"
		class="flex-1 border-b-2 border-fg-primary py-3 text-center text-sm font-medium text-fg-primary"
		aria-current="page"
	>
		웰니스
	</a>
	<span class="flex-1 py-3 text-center text-sm text-fg-muted opacity-40" title="준비 중">
		Provider 비교
	</span>
</nav>

{#if data.errorMessage && !data.detail}
	<div class="px-4 py-8 text-center">
		<p class="text-sm text-fg-secondary">{data.errorMessage}</p>
	</div>
{:else if !data.detail}
	<div class="px-4 py-8 text-center">
		<p class="text-sm text-fg-muted">데이터 수집 중</p>
	</div>
{:else}
	<!-- 날짜 -->
	<div class="px-4 pt-3 pb-1">
		<span class="text-xs text-fg-muted">{data.detail.date}</span>
	</div>

	<!-- Readiness 요약 -->
	<section class="px-4 py-3">
		<h2 class="mb-2 text-xs font-medium uppercase tracking-wide text-fg-muted">준비도</h2>
		<div class="grid grid-cols-2 gap-2">
			<div class="rounded-xl bg-surface-2 p-3">
				<span class="text-xs text-fg-muted">UTRS</span>
				<p class="mt-1 font-mono text-2xl font-semibold leading-none">
					{readiness.utrs != null ? fmt(readiness.utrs.value) : '—'}
				</p>
			</div>
			<div class="rounded-xl bg-surface-2 p-3">
				<span class="text-xs text-fg-muted">CIRS</span>
				<p class="mt-1 font-mono text-2xl font-semibold leading-none">
					{readiness.cirs != null ? fmt(readiness.cirs.value) : '—'}
				</p>
			</div>
		</div>
	</section>

	<!-- 코어 메트릭 카드 -->
	<section class="px-4 pb-3">
		<h2 class="mb-2 text-xs font-medium uppercase tracking-wide text-fg-muted">오늘</h2>
		<div class="grid grid-cols-2 gap-2 sm:grid-cols-3">
			<div class="rounded-xl bg-surface-2 p-3">
				<span class="text-xs text-fg-muted">수면 점수</span>
				<p class="mt-1 font-mono text-lg font-semibold leading-none">{fmt(core.sleep_score)}</p>
			</div>
			<div class="rounded-xl bg-surface-2 p-3">
				<span class="text-xs text-fg-muted">수면 시간</span>
				<p class="mt-1 font-mono text-lg font-semibold leading-none">
					{fmtDuration(core.sleep_duration_sec)}
				</p>
			</div>
			<div class="rounded-xl bg-surface-2 p-3">
				<span class="text-xs text-fg-muted">HRV (야간)</span>
				<p class="mt-1 font-mono text-lg font-semibold leading-none">
					{fmt(core.hrv_last_night, 1)}<span class="ml-0.5 text-xs font-normal text-fg-muted">ms</span>
				</p>
			</div>
			<div class="rounded-xl bg-surface-2 p-3">
				<span class="text-xs text-fg-muted">안정 심박</span>
				<p class="mt-1 font-mono text-lg font-semibold leading-none">
					{fmt(core.resting_hr)}<span class="ml-0.5 text-xs font-normal text-fg-muted">bpm</span>
				</p>
			</div>
			<div class="rounded-xl bg-surface-2 p-3">
				<span class="text-xs text-fg-muted">Body Battery</span>
				<p class="mt-1 font-mono text-lg font-semibold leading-none">{fmt(core.body_battery_high)}</p>
			</div>
			<div class="rounded-xl bg-surface-2 p-3">
				<span class="text-xs text-fg-muted">평균 스트레스</span>
				<p class="mt-1 font-mono text-lg font-semibold leading-none">{fmt(core.avg_stress)}</p>
			</div>
		</div>
	</section>

	<!-- 트렌드 (30일) -->
	{#if trend && trend.dates.length > 1}
		<section class="px-4 pb-6">
			<h2 class="mb-3 text-xs font-medium uppercase tracking-wide text-fg-muted">30일 트렌드</h2>
			<div class="flex flex-col gap-4">
				<div class="rounded-xl bg-surface-2 p-3">
					<span class="text-xs text-fg-muted">수면 점수</span>
					<Sparkline data={trend.sleep_score} height={32} color="#3b82f6" />
				</div>
				<div class="rounded-xl bg-surface-2 p-3">
					<span class="text-xs text-fg-muted">HRV (야간)</span>
					<Sparkline data={trend.hrv_last_night} height={32} color="#10b981" />
				</div>
				<div class="rounded-xl bg-surface-2 p-3">
					<span class="text-xs text-fg-muted">UTRS</span>
					<Sparkline data={trend.utrs} height={32} color="#f59e0b" />
				</div>
			</div>
		</section>
	{/if}
{/if}
