<script lang="ts">
	import IconButton from '$lib/components/ui/IconButton.svelte';
	import PageHead from '$lib/components/ui/PageHead.svelte';
	import { otherLine } from '$lib/activityDisplay';
	// /today/month/[ym] — 월간 내러티브 라우트(DESIGN-U17 §4.1). 오버레이가 아니라 페이지다.
	// ‹ › 는 replaceState(히스토리 길이 불변), 닫기(‹ 오늘)는 오늘에서 왔을 때만 뒤로가기(T-23). 칩은 DrillPanel(URL 스택) 하나만 연다.
	import { onMount } from 'svelte';
	import { base } from '$app/paths';
	import { afterNavigate, goto, replaceState } from '$app/navigation';
	import { closeAction, isAtMinMonth, monthSlice } from '$lib/monthNav';
	import type { MonthPageData } from './+page';
	import DrillPanel from '$lib/components/DrillPanel.svelte';
	import { openDrill } from '$lib/drillStack';
	import { EXPLAIN_SUPPORTED_SLUGS } from '$lib/api/metrics';
	import { getTodayNarrative } from '$lib/api/today';
	import { getMetricTrend } from '$lib/api/metrics';
	import MonthLoadSparkline from '$lib/components/MonthLoadSparkline.svelte';
	import EvidenceQuote from '$lib/components/EvidenceQuote.svelte';
	import MetricBreakdown from '$lib/components/MetricBreakdown.svelte';
	import WeekDigestList from '$lib/components/WeekDigestList.svelte';
	import Icon from '$lib/components/Icon.svelte';
	import { milestoneIconName } from '$lib/milestoneIcon';
	import { adaptEvidence, type DrillTarget } from '$lib/evidence';
	import type { NarrativeResponse } from '$lib/types';

	let { data }: { data: MonthPageData } = $props();

	const now = new Date();
	let displayYear = $state(data.year);
	let displayMonth = $state(data.month); // 1-indexed

	let narrativeData = $state<NarrativeResponse | null>(null);
	let loading = $state(true);
	let error = $state<string | null>(null);

	let drillStack = $state<DrillTarget[]>([]);
	const drillTop = $derived(drillStack.length > 0 ? drillStack[drillStack.length - 1] : null);

	function openEvidence(t: DrillTarget) {
		if (t.scopeType === 'daily' && EXPLAIN_SUPPORTED_SLUGS.has(t.slug)) {
			openDrill(t.slug, t.scopeId);
			return;
		}
		drillStack = [...drillStack, t];
	}

	function syncUrl() {
		const ym = `${displayYear}-${String(displayMonth).padStart(2, '0')}`;
		replaceState(`${base}/today/month/${ym}`, {});
	}

	// 들어오기 직전 경로 — 딥링크·새 탭이면 null(T-23).
	let fromPath: string | null = null;
	afterNavigate(({ from }) => {
		if (fromPath === null) fromPath = from?.url.pathname ?? null;
	});

	function close() {
		if (closeAction(fromPath, base) === 'back') history.back();
		else void goto(`${base}/today`, { replaceState: true });
	}

	function handleDrillInput(slug: string) {
		const top = drillStack.length > 0 ? drillStack[drillStack.length - 1] : null;
		drillStack = [...drillStack, {
			slug,
			scopeType: top?.scopeType ?? 'daily',
			scopeId: top?.scopeId ?? ''
		}];
	}

	// T-24: 1년 추세를 한 번 받아 달마다 잘라 쓴다 — 과거 달에서도 영역이 사라지지 않는다.
	type Pt = { date: string; value: number | null };
	let ctlYear = $state<Pt[]>([]);
	let atlYear = $state<Pt[]>([]);
	let sparklineLoading = $state(false);
	let sparklineLoaded = false;

	const isCurrentOrFuture = $derived(
		displayYear > now.getFullYear() ||
			(displayYear === now.getFullYear() && displayMonth >= now.getMonth() + 1)
	);

	const isViewingCurrentMonth = $derived(
		displayYear === now.getFullYear() && displayMonth === now.getMonth() + 1
	);
	const atMin = $derived(isAtMinMonth(displayYear, displayMonth));
	const ctlSlice = $derived(monthSlice(ctlYear, displayYear, displayMonth, isViewingCurrentMonth));
	const atlSlice = $derived(monthSlice(atlYear, displayYear, displayMonth, isViewingCurrentMonth));
	const sparkTitle = $derived(isViewingCurrentMonth ? 'CTL 추세 (최근 4주)' : `CTL 추세 (${displayMonth}월)`);

	const monthLabel = $derived(`${displayYear}년 ${displayMonth}월`);

	async function loadNarrative() {
		loading = true;
		error = null;
		narrativeData = null;
		try {
			narrativeData = await getTodayNarrative(displayYear, displayMonth);
		} catch (e) {
			error = e instanceof Error ? e.message : '내러티브를 불러올 수 없습니다.';
		} finally {
			loading = false;
		}
	}

	async function loadSparklines() {
		if (sparklineLoaded) return; // 이미 로드됨
		sparklineLoaded = true;
		sparklineLoading = true;
		try {
			const [ctl, atl] = await Promise.all([
				getMetricTrend('ctl', '1y'),
				getMetricTrend('atl', '1y'),
			]);
			ctlYear = ctl.points;
			atlYear = atl.points;
		} catch {
			// 스파크라인 실패는 조용히 무시
		} finally {
			sparklineLoading = false;
		}
	}

	function prevMonth() {
		if (atMin) return;
		if (displayMonth === 1) {
			displayYear -= 1;
			displayMonth = 12;
		} else {
			displayMonth -= 1;
		}
		syncUrl();
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
		syncUrl();
		loadNarrative();
	}

	onMount(() => {
		loadNarrative();
		loadSparklines();
	});
</script>

<PageHead title={`${monthLabel}`} heading={null} />

<DrillPanel scopeType="daily" scopeId={`${displayYear}-${String(displayMonth).padStart(2, '0')}-01`} fromTag="today">
<div class="mx-auto flex max-w-2xl flex-col gap-4 px-4 py-4">
	<div class="flex items-center justify-between border-b border-border-subtle pb-3">
		<button onclick={close} class="tap text-sm text-fg-muted hover:text-fg-primary" aria-label="닫기">‹ 오늘</button>
		<div class="flex items-center gap-2">
			<IconButton label="이전 달" onclick={prevMonth} disabled={atMin} class="rounded text-fg-secondary hover:text-fg-primary disabled:cursor-not-allowed disabled:opacity-30">‹</IconButton>
			<h1 class="font-medium" data-testid="month-title">{monthLabel}</h1>
			<IconButton label="다음 달" onclick={nextMonth} disabled={isCurrentOrFuture} class="rounded text-fg-secondary hover:text-fg-primary disabled:cursor-not-allowed disabled:opacity-30">›</IconButton>
		</div>
	</div>

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
		{#if otherLine(h.other)}
			<p class="text-xs text-fg-muted">{otherLine(h.other)}</p>
		{/if}

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

		{#if narrativeData.weeks && narrativeData.weeks.length > 0}
			<WeekDigestList weeks={narrativeData.weeks} />
		{/if}

		<!-- CTL 스파크라인 — 이번 달은 최근 4주, 과거 달은 그 달(1년 추세에서 잘라 씀, T-24). -->
		<MonthLoadSparkline ctl={ctlSlice} atl={atlSlice} title={sparkTitle} loading={sparklineLoading} />

		{#if narrativeData.source === 'rule'}
			<p class="text-xs text-fg-muted">규칙 기반 요약</p>
		{/if}
	{/if}
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
</DrillPanel>
