<script lang="ts">
	// 오늘 화면 최상단 레이스 허브 — D-day 히어로, 예측 vs 목표, 예측 추이, 현재 폼.
	// DECISIONS.md [P7-IMPL-RACE-HUB-UI]: 목표 있으면 D-day, 없으면 등록 유도 카드.
	import type { RaceHubData } from '$lib/types';
	import TrendChart from './TrendChart.svelte';
	import PredictionCompare from './PredictionCompare.svelte';
	import PredictionBasis from './PredictionBasis.svelte';
	import RaceConfirmList from './RaceConfirmList.svelte';
	import { rangeLabel, confidenceLabel } from '$lib/predictionCompare';
	import { countdownLabel, distanceLabel, gapVerdict, signedTsb } from '$lib/raceHub';
	import { formatDuration } from '$lib/format';
	import { base } from '$app/paths';

	let { data }: { data: RaceHubData | null } = $props();

	const TONE_CLASS: Record<string, string> = {
		ahead: 'text-semantic-green',
		on: 'text-semantic-teal',
		behind: 'text-semantic-amber',
		unknown: 'text-fg-muted font-normal text-xs'
	};

	const verdict = $derived(data?.prediction ? gapVerdict(data.prediction.gap_sec) : null);
	const selfRow = $derived(data?.prediction?.compare?.rows.find((r) => r.key === 'self') ?? null);
	const tsb = $derived(data?.form?.tsb ?? null);
	const proj = $derived(data?.projection ?? null);
	// 서버 등급 status(bands.py) → 색
	const FORM_TONE: Record<string, string> = {
		excellent: 'text-semantic-green',
		good: 'text-semantic-teal',
		neutral: 'text-fg-secondary',
		caution: 'text-semantic-amber',
		poor: 'text-semantic-red'
	};
	const SCENARIO_COLOR: Record<string, string> = { taper: '#22c55e', keep: '#64748b' };
</script>

{#if !data?.goal}
	<a
		href="{base}/coach/plan/new"
		class="flex flex-col gap-1 rounded-lg border border-dashed border-border-subtle bg-surface-2 p-4 hover:bg-surface-3"
	>
		<span class="text-sm font-semibold">목표 레이스를 등록해 보세요</span>
		<span class="text-xs text-fg-muted"
			>D-day, 예측 기록, 목표까지의 격차와 준비도 추이를 여기서 계속 볼 수 있어요 →</span
		>
	</a>
{:else}
	{@const goal = data.goal}
	{@const pred = data.prediction}
	<section
		aria-label="목표 레이스"
		class="flex flex-col gap-3 rounded-lg border border-border-subtle bg-surface-2 p-4"
	>
		<div class="flex items-center gap-3">
			<span class="font-mono text-4xl font-bold leading-none">{countdownLabel(goal.days_left)}</span>
			<div class="flex min-w-0 flex-1 flex-col">
				<span class="truncate text-sm font-medium">{goal.name ?? distanceLabel(goal.distance_km)}</span>
				<span class="text-xs text-fg-muted"
					>{goal.race_date} · {distanceLabel(goal.distance_km)}{goal.weeks_left > 0
						? ` · ${goal.weeks_left}주 남음`
						: ''}</span
				>
			</div>
		</div>

		<div class="grid grid-cols-2 gap-3">
			<div class="flex flex-col gap-0.5">
				<span class="text-xs text-fg-muted">예측 기록</span>
				<span class="font-mono text-2xl font-bold">{pred ? formatDuration(pred.value_sec) : '—'}</span>
			</div>
			<div class="flex flex-col gap-0.5">
				<span class="text-xs text-fg-muted">목표</span>
				{#if goal.target_time_sec != null}
					<span class="font-mono text-2xl font-bold">{formatDuration(goal.target_time_sec)}</span>
				{:else}
					<span class="font-mono text-lg text-fg-muted">미설정</span>
				{/if}
			</div>
		</div>

		{#if verdict}
			<p class="text-sm font-medium {TONE_CLASS[verdict.tone]}">{verdict.label}</p>
		{/if}

		{#if selfRow && (rangeLabel(selfRow) || confidenceLabel(selfRow.confidence))}
			<p class="text-xs text-fg-muted">
				{rangeLabel(selfRow) ? `80% 범위 ${rangeLabel(selfRow)}` : ''}{rangeLabel(selfRow) && confidenceLabel(selfRow.confidence)
					? ' · '
					: ''}{confidenceLabel(selfRow.confidence) ? `신뢰도 ${confidenceLabel(selfRow.confidence)}` : ''} · 15℃ 기준
			</p>
		{/if}

		{#if pred?.compare}
			<PredictionCompare compare={pred.compare} />
		{/if}

		{#if pred || proj}
			<details class="group border-t border-border-subtle pt-3">
				<summary class="cursor-pointer list-none text-xs text-fg-muted hover:text-fg-primary">예측 추이 · 근거 · 레이스 아침 폼 보기 ▾</summary>
				<div class="flex flex-col gap-4 pt-3">
					<PredictionBasis />
					<RaceConfirmList />
				</div>
				{#if pred && pred.history.length > 1}
					<div class="flex flex-col gap-1">
						<span class="text-xs text-fg-muted">예측 기록 추이 · 최근 90일</span>
						<TrendChart
							series={[{ key: 'pred', label: '예측', color: '#14b8a6', points: pred.history }]}
							height={72}
							formatValue={(v) => formatDuration(Math.round(v))}
						/>
					</div>
				{/if}

				{#if proj}
					<div class="flex flex-col gap-2">
						<span class="text-xs text-fg-muted">레이스 아침 예상 폼 (TSB)</span>
						<div class="grid grid-cols-2 gap-3">
							{#each proj.scenarios as sc (sc.key)}
								<div class="flex flex-col gap-0.5">
									<span class="text-[11px] text-fg-muted">{sc.label}</span>
									<span class="font-mono text-2xl font-bold {FORM_TONE[sc.status ?? 'neutral']}">{signedTsb(sc.tsb)}</span>
									<span class="text-[11px] {FORM_TONE[sc.status ?? 'neutral']}">{sc.status_label ?? ''}</span>
								</div>
							{/each}
						</div>
						<TrendChart
							series={proj.scenarios.map((sc) => ({
								key: sc.key,
								label: sc.label,
								color: SCENARIO_COLOR[sc.key],
								points: sc.series
							}))}
							height={88}
							formatValue={(v) => signedTsb(v)}
						/>
						<p class="text-[10px] leading-tight text-fg-muted">
							{proj.assumptions} · 현재 폼 {signedTsb(proj.current.tsb)}
						</p>
					</div>
				{/if}
			</details>
		{/if}

		{#if tsb != null && !proj}
			<p class="text-xs text-fg-muted">현재 폼(TSB) {tsb > 0 ? '+' : ''}{Math.round(tsb)}</p>
		{/if}
	</section>
{/if}
