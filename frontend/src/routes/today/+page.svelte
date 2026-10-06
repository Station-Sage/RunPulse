<script lang="ts">
	// 10-today design §2 — B1 히어로 → B2 체크인 → B3 게이지 → B4 다음 세션 → B6 최근 활동 → B7 차트/내러티브.
	import type { TodayPageData } from './+page';
	import { goto, invalidate } from '$app/navigation';
	import ReadinessGauge from '$lib/components/ReadinessGauge.svelte';
	import TodayHero from '$lib/components/TodayHero.svelte';
	import TodayRecent from '$lib/components/TodayRecent.svelte';
	import TodayNarrative from '$lib/components/TodayNarrative.svelte';
	import ErrorState from '$lib/components/ErrorState.svelte';
	import MetricBreakdown from '$lib/components/MetricBreakdown.svelte';
	import DrillPanel from '$lib/components/DrillPanel.svelte';
	import MilestonesPanel from '$lib/components/MilestonesPanel.svelte';
	import TodayNextSession from '$lib/components/TodayNextSession.svelte';
	import TodayFormChart from '$lib/components/TodayFormChart.svelte';
	import QuickInput from '$lib/components/QuickInput.svelte';
	import RaceSummaryLine from '$lib/components/RaceSummaryLine.svelte';
	import { EXPLAIN_SUPPORTED_SLUGS } from '$lib/api/metrics';
	import { openDrill } from '$lib/drillStack';
	import { swrEvict } from '$lib/loadCache';
	import { loadCoverageNotice } from '$lib/healthNotice';
	import { postCheckin } from '$lib/api/today';
	import { morningAsOf } from '$lib/todayHero';
	import { base } from '$app/paths';
	import type { DrillTarget } from '$lib/evidence';
	import type { PainLevel } from '$lib/types';

	let { data }: { data: TodayPageData } = $props();

	let checkin = $state(data.today?.checkin ?? null);
	let savingCheckin = $state(false);
	let checkinError = $state<string | null>(null);

	// 임의 슬러그·scope 드릴(EvidenceQuote 칩)은 기존 MetricBreakdown 스택, 게이지 3종은 DrillPanel(URL 스택).
	let drillStack = $state<DrillTarget[]>([]);
	let showMilestonesPanel = $state(false);

	const todayDate = $derived(data.today?.status.date ?? '');
	const drillTop = $derived(drillStack.length > 0 ? drillStack[drillStack.length - 1] : null);

	function handleDrillInput(slug: string) {
		const top = drillTop;
		drillStack = [...drillStack, { slug, scopeType: top?.scopeType ?? 'daily', scopeId: top?.scopeId ?? todayDate }];
	}

	function openEvidence(t: DrillTarget) {
		if (t.scopeType === 'daily' && EXPLAIN_SUPPORTED_SLUGS.has(t.slug)) {
			openDrill(t.slug, t.scopeId);
			return;
		}
		drillStack = [...drillStack, t];
	}

	function openMonth() {
		const d = new Date();
		void goto(`${base}/today/month/${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`);
	}

	const retry = () => { swrEvict('app:today'); return invalidate('app:today'); };

	async function handleSaveCheckin(value: { fatigue?: number; pain?: PainLevel; note?: string }) {
		savingCheckin = true;
		checkinError = null;
		try {
			checkin = await postCheckin(value);
			// 피로 입력은 히어로 판정에 반영된다 — 캐시를 비우고 다시 불러온다(design §3 B2 "저장 후 invalidate").
			swrEvict('app:today');
			void invalidate('app:today');
		} catch (e) {
			checkinError = e instanceof Error ? e.message : '저장에 실패했습니다.';
		} finally {
			savingCheckin = false;
		}
	}
</script>

<svelte:head><title>Today · RunPulse</title></svelte:head>

{#if !data.today}
	{#if data.errorKind === 'failed'}
		<div class="px-4 py-10">
			<ErrorState message="오늘 권고를 불러오지 못했어요" detail={data.errorMessage ?? undefined} onRetry={() => invalidate('app:today')} />
		</div>
	{:else}
		<div class="flex flex-col items-center gap-3 px-4 py-20 text-center">
			<p class="text-lg">아직 데이터가 없습니다</p>
			<p class="text-sm text-fg-secondary">Garmin, Strava 등 소스를 연결하면 오늘 상태 분석이 시작됩니다.</p>
			<a href="{base}/settings" class="text-sm text-fg-secondary hover:text-fg-primary">소스 연결하기 ›</a>
		</div>
	{/if}
{:else}
	{@const status = data.today.status}
	{@const briefing = data.today.briefing}
	{@const readiness = data.today.readiness}

<DrillPanel scopeType="daily" scopeId={todayDate} fromTag="today">
	<div class="flex flex-col gap-6 px-4 py-4 lg:grid lg:grid-cols-2 lg:items-start lg:gap-x-8">
		<div class="contents lg:flex lg:flex-col lg:gap-6">
			<section class="order-1 flex flex-col gap-3">
				{#if loadCoverageNotice(data.today.data_health)}
					<p class="rounded-lg border border-semantic-amber/40 bg-semantic-amber/10 px-3 py-2 text-xs text-fg-secondary" role="note">{loadCoverageNotice(data.today.data_health)}</p>
				{/if}
				{#await data.raceHub}
					<TodayHero {briefing} goal={null} onEvidence={openEvidence} onRetry={retry} />
				{:then hub}
					<TodayHero {briefing} goal={hub?.goal ?? null} onEvidence={openEvidence} onRetry={retry} />
				{/await}
				<RaceSummaryLine summary={data.today.race_summary} onRetry={() => invalidate('app:today')} />
				<QuickInput
					compact={true}
					existing={checkin
						? { fatigue: checkin.fatigue ?? undefined, pain: checkin.pain ?? undefined, note: checkin.note ?? undefined, timestamp: checkin.created_at }
						: undefined}
					saving={savingCheckin}
					dismissDate={todayDate}
					onSave={handleSaveCheckin}
				/>
				{#if checkinError}<p class="text-xs text-semantic-red">{checkinError}</p>{/if}
			</section>

			<div class="order-4 flex flex-col gap-3 border-t border-border-subtle pt-3">
				<TodayNextSession nextSession={data.nextSession} raceHub={data.raceHub} week={data.today.week_compliance} today={status.date} onRetry={retry} />
			</div>
		</div>

		<div class="contents lg:flex lg:flex-col lg:gap-6">
			<section class="order-2 flex flex-col gap-3">
				<div class="flex items-center justify-between text-[11px] text-fg-muted">
					<span>{morningAsOf(data.today.as_of?.date ?? status.date)}</span>
					<span class="rounded bg-surface-3 px-1.5 py-0.5">RunPulse 계산</span>
				</div>
				<div class="grid grid-cols-3 gap-2">
					<ReadinessGauge slug="utrs" label="UTRS" kind="ring" entry={readiness?.utrs ?? null} />
					<ReadinessGauge slug="cirs" label="CIRS" kind="track" entry={readiness?.cirs ?? null} />
					<ReadinessGauge slug="tsb" label="TSB" kind="bipolar" entry={readiness?.tsb ?? null} />
				</div>
				<TodayRecent activities={data.today.recent_activities} />
			</section>

			<section class="order-3 flex flex-col gap-3 border-t border-border-subtle pt-4">
				<p class="text-xs uppercase tracking-wide text-fg-muted">흐름 · 훈련 · 성장</p>
				<TodayFormChart chart={data.formChart} raceHub={data.raceHub} onMonth={openMonth} onRetry={retry} />
				<TodayNarrative
					narrative={data.narrative}
					ctl={status.training_status.ctl ?? null}
					onEvidence={openEvidence}
					onMonth={openMonth}
					onMilestones={() => { showMilestonesPanel = true; }}
				/>
			</section>
		</div>

		<section class="order-5 flex flex-col gap-2 border-t border-border-subtle pt-4 lg:col-span-2">
			<p class="text-xs uppercase tracking-wide text-fg-muted">원본 데이터</p>
			<a href="{base}/library" class="text-sm text-fg-secondary hover:text-fg-primary">Library에서 전체 탐색 →</a>
		</section>
	</div>

	{#if drillTop}
		<MetricBreakdown slug={drillTop.slug} scopeType={drillTop.scopeType} scopeId={drillTop.scopeId} onClose={() => { drillStack = []; }} onDrillInput={handleDrillInput} />
	{/if}
	{#if showMilestonesPanel}<MilestonesPanel onClose={() => { showMilestonesPanel = false; }} />{/if}
</DrillPanel>
{/if}
