<script lang="ts">
	// Today L2 월간 내러티브 패널 — MetricBreakdown 오버레이 패턴 재사용.
	// 헤더: '← YYYY년 M월 →' 이전/다음 달 버튼 (다음 달이 미래면 비활성화).
	// 본문: 텍스트 + evidence + 마일스톤 + highlights 통계 행 + CTL 스파크라인.
	// CTL 스파크라인 탭 → 같은 패널 안에서 CTL+ATL 2단 확장 (로컬 $state 토글).
	import { onMount } from 'svelte';
	import { getTodayNarrative } from '$lib/api/today';
	import { getMetricTrend } from '$lib/api/metrics';
	import Sparkline from '$lib/components/Sparkline.svelte';
	import EvidenceQuote from '$lib/components/EvidenceQuote.svelte';
	import MetricBreakdown from '$lib/components/MetricBreakdown.svelte';
	import Icon from '$lib/components/Icon.svelte';
	import { milestoneIconName } from '$lib/milestoneIcon';
	import { adaptEvidence, type DrillTarget } from '$lib/evidence';
	import { formatLoad } from '$lib/format';
	import type { NarrativeResponse } from '$lib/types';

	let { onClose }: { onClose: () => void } = $props();

	const now = new Date();
	let displayYear = $state(now.getFullYear());
	let displayMonth = $state(now.getMonth() + 1); // 1-indexed

	let narrativeData = $state<NarrativeResponse | null>(null);
	let loading = $state(true);
	let error = $state<string | null>(null);

	let drillStack = $state<DrillTarget[]>([]);
	const drillTop = $derived(drillStack.length > 0 ? drillStack[drillStack.length - 1] : null);

	function openEvidence(t: DrillTarget) {
		drillStack = [...drillStack, t];
	}

	function handleDrillInput(slug: string) {
		const top = drillStack.length > 0 ? drillStack[drillStack.length - 1] : null;
		drillStack = [...drillStack, {
			slug,
			scopeType: top?.scopeType ?? 'daily',
			scopeId: top?.scopeId ?? ''
		}];
	}

	let showDualSparkline = $state(false);
	let ctlPoints = $state<(number | null)[]>([]);
	let atlPoints = $state<(number | null)[]>([]);
	let ctlDates = $state<string[]>([]);
	let sparklineLoading = $state(false);

	const isCurrentOrFuture = $derived(
		displayYear > now.getFullYear() ||
			(displayYear === now.getFullYear() && displayMonth >= now.getMonth() + 1)
	);

	// getMetricTrend()는 "오늘 기준 최근 N일"만 지원(임의 과거 달 조회 불가) —
	// 과거 달 조회 시 스파크라인이 그 달과 무관한 오늘 기준 데이터를 보여주는
	// 걸 막기 위해 이번 달을 보고 있을 때만 표시한다.
	const isViewingCurrentMonth = $derived(
		displayYear === now.getFullYear() && displayMonth === now.getMonth() + 1
	);

	const monthLabel = $derived(`${displayYear}년 ${displayMonth}월`);

	async function loadNarrative() {
		loading = true;
		error = null;
		narrativeData = null;
		showDualSparkline = false;
		try {
			narrativeData = await getTodayNarrative(displayYear, displayMonth);
		} catch (e) {
			error = e instanceof Error ? e.message : '내러티브를 불러올 수 없습니다.';
		} finally {
			loading = false;
		}
	}

	async function loadSparklines() {
		if (ctlPoints.length > 0) return; // 이미 로드됨
		sparklineLoading = true;
		try {
			const [ctl, atl] = await Promise.all([
				getMetricTrend('ctl', '4w'),
				getMetricTrend('atl', '4w'),
			]);
			ctlPoints = ctl.points.map((p) => p.value);
			atlPoints = atl.points.map((p) => p.value);
			ctlDates = ctl.points.map((p) => p.date);
		} catch {
			// 스파크라인 실패는 조용히 무시
		} finally {
			sparklineLoading = false;
		}
	}

	function toggleSparkline() {
		showDualSparkline = !showDualSparkline;
	}

	function prevMonth() {
		if (displayMonth === 1) {
			displayYear -= 1;
			displayMonth = 12;
		} else {
			displayMonth -= 1;
		}
		loadNarrative();
	}

	function nextMonth() {
		if (isCurrentOrFuture) return;
		if (displayMonth === 12) {
			displayYear += 1;
			displayMonth = 1;
		} else {
			displayMonth += 1;
		}
		loadNarrative();
	}

	onMount(() => {
		loadNarrative();
		loadSparklines();
	});
</script>

<div class="fixed inset-0 z-50 flex flex-col" role="dialog" aria-modal="true">
	<!-- 배경 오버레이 -->
	<button class="absolute inset-0 bg-black/40" onclick={onClose} aria-label="닫기"></button>

	<!-- 하단 시트 패널 -->
	<div class="absolute inset-x-0 bottom-0 flex max-h-[80vh] flex-col rounded-t-2xl bg-surface-1 shadow-lg">
		<!-- 헤더 — 월 내비게이션 -->
		<div class="flex items-center justify-between border-b border-border-subtle px-4 py-3">
			<button
				onclick={prevMonth}
				class="rounded p-1 text-fg-secondary hover:text-fg-primary"
				aria-label="이전 달"
			>‹</button>
			<h2 class="font-medium">{monthLabel}</h2>
			<div class="flex items-center gap-1">
				<button
					onclick={nextMonth}
					disabled={isCurrentOrFuture}
					class="rounded p-1 text-fg-secondary hover:text-fg-primary disabled:opacity-30 disabled:cursor-not-allowed"
					aria-label="다음 달"
				>›</button>
				<button
					onclick={onClose}
					class="ml-1 rounded p-1 text-fg-secondary hover:text-fg-primary"
					aria-label="닫기"
				><Icon name="close" class="h-4 w-4" /></button>
			</div>
		</div>

		<!-- 본문 -->
		<div class="overflow-y-auto p-4 flex flex-col gap-4">
			{#if loading}
				<p class="text-sm text-fg-muted">불러오는 중…</p>
			{:else if error || !narrativeData}
				<p class="text-sm text-fg-secondary">내러티브를 불러올 수 없습니다.</p>
			{:else}
				<!-- 내러티브 텍스트 -->
				{#each narrativeData.text.split('\n').filter((p) => p.trim()) as paragraph}
					<p class="text-sm leading-relaxed text-fg-primary">{paragraph}</p>
				{/each}

				<!-- Evidence 칩 -->
				{#if narrativeData.evidence.length > 0}
					<div class="flex flex-wrap gap-2">
						{#each narrativeData.evidence as ev}
							<EvidenceQuote {...adaptEvidence(ev, openEvidence)} />
						{/each}
					</div>
				{:else}
					<p class="text-xs text-fg-muted">(데이터 부족 — 추후 업데이트)</p>
				{/if}

				<!-- highlights 통계 행 -->
				{@const h = narrativeData.highlights}
				<div class="grid grid-cols-4 gap-2 rounded-lg bg-surface-2 px-3 py-3">
					<div class="flex flex-col items-center gap-0.5">
						<span class="font-mono text-base font-bold">{h.total_distance_km}</span>
						<span class="text-[10px] text-fg-muted">km</span>
					</div>
					<div class="flex flex-col items-center gap-0.5">
						<span class="font-mono text-base font-bold">{h.activity_count}</span>
						<span class="text-[10px] text-fg-muted">회</span>
					</div>
					<div class="flex flex-col items-center gap-0.5">
						<span class="font-mono text-base font-bold">{h.longest_run_km}</span>
						<span class="text-[10px] text-fg-muted">최장 km</span>
					</div>
					<div class="flex flex-col items-center gap-0.5">
						<span class="font-mono text-base font-bold">{h.peak_ctl ?? '—'}</span>
						<span class="text-[10px] text-fg-muted">최고 CTL</span>
					</div>
				</div>

				<!-- 마일스톤 목록 -->
				{#if narrativeData.milestones.length > 0}
					<div class="flex flex-col gap-1">
						{#each narrativeData.milestones as m (m.id)}
							<div class="flex items-start gap-2 text-sm">
								<Icon name={milestoneIconName(m.type)} class="h-4 w-4 shrink-0 text-fg-muted" />
								<span class="text-fg-muted">{m.date}</span>
								<span class="flex-1">{m.title}</span>
							</div>
						{/each}
					</div>
				{/if}

				<!-- CTL 스파크라인 (탭 → CTL+ATL 2단 확장) — 이번 달 조회일 때만 표시.
				     getMetricTrend()가 "오늘 기준 최근 4주"만 지원해 과거 달에는
				     무관한 데이터가 되므로 숨긴다. -->
				{#if isViewingCurrentMonth}
					<div class="rounded-lg border border-border-subtle bg-surface-2 p-3">
						<button
							class="flex w-full items-center justify-between text-xs text-fg-muted hover:text-fg-secondary"
							onclick={toggleSparkline}
						>
							<span>CTL 추세 (4주)</span>
							<span aria-hidden="true">{showDualSparkline ? '▲' : '▼'}</span>
						</button>

						{#if sparklineLoading}
							<p class="mt-2 text-xs text-fg-muted">불러오는 중…</p>
						{:else if showDualSparkline}
							<div class="mt-2 flex flex-col gap-3">
								<div>
									<p class="mb-1 text-[10px] text-fg-muted">CTL</p>
									<Sparkline
										data={ctlPoints}
										height={40}
										color="var(--color-series-1)"
										interactive
										dates={ctlDates}
										formatValue={formatLoad}
									/>
								</div>
								<div>
									<p class="mb-1 text-[10px] text-fg-muted">ATL</p>
									<Sparkline
										data={atlPoints}
										height={40}
										color="var(--color-semantic-amber)"
										interactive
										dates={ctlDates}
										formatValue={formatLoad}
									/>
								</div>
							</div>
						{:else}
							<div class="mt-2">
								<Sparkline
									data={ctlPoints}
									height={40}
									color="var(--color-series-1)"
									interactive
									dates={ctlDates}
									formatValue={formatLoad}
								/>
							</div>
						{/if}
					</div>
				{/if}

				{#if narrativeData.source === 'rule'}
					<p class="text-xs text-fg-muted">규칙 기반 요약</p>
				{/if}
			{/if}
		</div>
	</div>
</div>

{#if drillTop}
	<MetricBreakdown
		slug={drillTop.slug}
		scopeType={drillTop.scopeType}
		scopeId={drillTop.scopeId}
		onClose={() => { drillStack = []; }}
		onDrillInput={handleDrillInput}
	/>
{/if}
