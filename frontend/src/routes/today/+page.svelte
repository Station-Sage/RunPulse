<script lang="ts">
	// 03a-today.md 1-A' — L0(QuickInput+RecommendationCard) + L1(MetricCell×3 + 최근 활동) + L2(내러티브).
	// Phase 7b: MetricCell 드릴다운 → MetricBreakdown 패널, L2 실데이터 연결.
	import type { TodayPageData } from './+page';
	import ScoreRing from '$lib/components/ScoreRing.svelte';
	import MetricBreakdown from '$lib/components/MetricBreakdown.svelte';
	import DrillPanel from '$lib/components/DrillPanel.svelte';
	import { EXPLAIN_SUPPORTED_SLUGS } from '$lib/api/metrics';
	import { openDrill } from '$lib/drillStack';
	import MilestonesPanel from '$lib/components/MilestonesPanel.svelte';
	import MonthNarrative from '$lib/components/MonthNarrative.svelte';
	import NextSessionCard from '$lib/components/NextSessionCard.svelte';
	import QuickInput from '$lib/components/QuickInput.svelte';
	import RouteThumb from '$lib/components/RouteThumb.svelte';
	import RaceHub from '$lib/components/RaceHub.svelte';
	import { loadCoverageNotice } from '$lib/healthNotice';
	import RecommendationCard from '$lib/components/RecommendationCard.svelte';
	import EvidenceQuote from '$lib/components/EvidenceQuote.svelte';
	import FormChart from '$lib/components/FormChart.svelte';
	import Icon from '$lib/components/Icon.svelte';
	import { milestoneIconName } from '$lib/milestoneIcon';
	import { postCheckin } from '$lib/api/today';
	import { providerLabel, providerBadgeClass } from '$lib/provider';
	import { formatDistance, formatDuration, formatRelativeDay } from '$lib/format';
	import { base } from '$app/paths';
	import { adaptEvidence, type DrillTarget } from '$lib/evidence';
	import type { PainLevel, ProviderKey } from '$lib/types';
	import { asOfLabel, localDateString } from '$lib/asOf';

	let { data }: { data: TodayPageData } = $props();

	let checkin = $state(data.today?.checkin ?? null);
	let savingCheckin = $state(false);
	let checkinError = $state<string | null>(null);

	// MetricBreakdown 드릴다운 스택 — DrillTarget 목록, 마지막 항목이 현재 표시 패널.
	// onDrillInput으로 push, onClose로 전체 비움.
	let drillStack = $state<DrillTarget[]>([]);
	let showMonthNarrative = $state(false);
	let showMilestonesPanel = $state(false);

	const todayDate = $derived(data.today?.status.date ?? '');
	const drillTop = $derived(drillStack.length > 0 ? drillStack[drillStack.length - 1] : null);

	// ScoreRing 3개(UTRS/CIRS/TSB)는 explain=1 지원 슬러그라 새 DrillPanel(§C3, URL 스택)로.
	// EvidenceQuote 칩·onDrillInput 캐스케이드는 임의 슬러그·scope라 기존 MetricBreakdown 유지.
	function handleDrill(payload: { slug: string; provider: ProviderKey | null }) {
		if (EXPLAIN_SUPPORTED_SLUGS.has(payload.slug)) {
			openDrill(payload.slug);
			return;
		}
		drillStack = [...drillStack, { slug: payload.slug, scopeType: 'daily', scopeId: todayDate }];
	}

	function handleDrillInput(slug: string) {
		const top = drillStack.length > 0 ? drillStack[drillStack.length - 1] : null;
		drillStack = [...drillStack, {
			slug,
			scopeType: top?.scopeType ?? 'daily',
			scopeId: top?.scopeId ?? todayDate
		}];
	}

	function closeDrill() {
		drillStack = [];
	}

	function openEvidence(t: DrillTarget) {
		drillStack = [...drillStack, t];
	}

	async function handleSaveCheckin(value: { fatigue?: number; pain?: PainLevel; note?: string }) {
		savingCheckin = true;
		checkinError = null;
		try {
			checkin = await postCheckin(value);
		} catch (e) {
			checkinError = e instanceof Error ? e.message : '저장에 실패했습니다.';
		} finally {
			savingCheckin = false;
		}
	}

</script>

<svelte:head><title>Today · RunPulse</title></svelte:head>

{#if !data.today}
	<!-- 1-E: 데이터 없음 상태 -->
	<div class="flex flex-col items-center gap-3 px-4 py-20 text-center">
		<p class="text-lg">아직 데이터가 없습니다</p>
		<p class="text-sm text-fg-secondary">
			Garmin, Strava 등 소스를 연결하면 오늘 상태 분석이 시작됩니다.
		</p>
		{#if data.errorMessage}
			<p class="text-xs text-fg-muted">{data.errorMessage}</p>
		{/if}
	</div>
{:else}
	{@const status = data.today.status}
	{@const briefing = data.today.briefing}
	{@const narrative = data.narrative}

<DrillPanel scopeType="daily" scopeId={todayDate}>

	<!-- 데스크톱은 좌·우 독립 열(행 정렬로 생기던 빈 공간 제거), 모바일은 wrapper 를 풀고 order 로 L0→L1→L2→다음 세션→L3 -->
	<div class="flex flex-col gap-6 px-4 py-4 lg:grid lg:grid-cols-2 lg:items-start lg:gap-x-8">
		<div class="contents lg:flex lg:flex-col lg:gap-6">
		<!-- ══ L0 — 즉시 브리핑 ══ -->
		<section class="order-1 flex flex-col gap-3">
			{#if loadCoverageNotice(data.today?.data_health)}
				<p class="rounded-lg border border-semantic-amber/40 bg-semantic-amber/10 px-3 py-2 text-xs text-fg-secondary" role="note">{loadCoverageNotice(data.today?.data_health)}</p>
			{/if}
			<!-- 레이스 허브: 최상단 (DECISIONS.md [P7-IMPL-RACE-HUB-UI]) -->
			<RaceHub data={data.raceHub} />

			<RecommendationCard
				recommendation={{
					body: briefing.headline,
					evidence: briefing.evidence.map((ev) => adaptEvidence(ev, openEvidence))
				}}
				actions={[{ label: 'Coach에게 더 묻기 →', href: `${base}/coach`, variant: 'ghost' }]}
			/>

			<QuickInput
				compact={true}
				existing={checkin
					? {
							fatigue: checkin.fatigue ?? undefined,
							pain: checkin.pain ?? undefined,
							note: checkin.note ?? undefined,
							timestamp: checkin.created_at
						}
					: undefined}
				saving={savingCheckin}
				onSave={handleSaveCheckin}
			/>
			{#if checkinError}
				<p class="text-xs text-semantic-red">{checkinError}</p>
			{/if}
		</section>

		<!-- 다음 세션 현황 (L2 — 구 Plan "보기" 흡수) -->
		<div class="order-4 flex flex-col gap-2 border-t border-border-subtle pt-3">
			<p class="text-xs uppercase tracking-wide text-fg-muted">다음 세션</p>
			<NextSessionCard plan={data.plan} adjustment={data.adjustment} today={status.date} raceGoal={data.raceHub?.goal ?? null} />
		</div>
		</div>

		<div class="contents lg:flex lg:flex-col lg:gap-6">
		<!-- ══ L1 — 내 상태 요약 ══ -->
		<section class="order-2 flex flex-col gap-3">
			<p class="text-[11px] text-fg-muted">{asOfLabel(status.date, localDateString())}</p>
			<div class="grid grid-cols-3 gap-2">
				<ScoreRing
					slug="utrs"
					label="UTRS"
					value={status.readiness.utrs?.value ?? null}
					min={0}
					max={100}
					decimals={0}
					provider={status.providers.utrs ?? null}
					status={status.readiness.utrs?.status ?? undefined}
					statusText={status.readiness.utrs?.level ?? undefined}
					unavailable={!status.readiness.utrs}
					onDrill={handleDrill}
				/>
				<ScoreRing
					slug="cirs"
					label="CIRS"
					value={status.readiness.cirs?.value ?? null}
					min={0}
					max={100}
					decimals={0}
					provider={status.providers.cirs ?? null}
					status={status.readiness.cirs?.status ?? undefined}
					statusText={status.readiness.cirs?.level ?? undefined}
					unavailable={!status.readiness.cirs}
					onDrill={handleDrill}
				/>
				<ScoreRing
					slug="tsb"
					label="TSB"
					value={status.training_status.tsb ?? null}
					min={-40}
					max={40}
					decimals={0}
					provider={status.providers.tsb ?? null}
					status={status.training_status.grades?.tsb?.status}
					statusText={status.training_status.grades?.tsb?.label}
					unavailable={status.training_status.tsb === null}
					onDrill={handleDrill}
				/>
			</div>

			<div class="flex flex-col gap-1 rounded-lg border border-border-subtle bg-surface-2 p-3">
				<p class="mb-1 text-xs text-fg-muted">최근 활동</p>
				{#if data.today.recent_activities.length === 0}
					<p class="text-sm text-fg-muted">아직 활동이 없습니다.</p>
				{:else}
					{#each data.today.recent_activities as act (act.id)}
						<a
							href="{base}/library/{act.id}"
							class="-mx-1 flex min-h-11 items-center gap-2 rounded px-1 py-1.5 text-sm hover:bg-surface-3 active:bg-surface-3"
						>
							<RouteThumb route={act.route} size={32} />
							<span class="w-14 shrink-0 text-fg-secondary">{formatRelativeDay(act.start_time)}</span>
							<span class="flex-1 truncate">{act.name}</span>
							<span class="text-fg-secondary">{formatDistance(act.distance_m)}</span>
							<span class="text-fg-secondary">{formatDuration(act.duration_sec)}</span>
							<span
								class="rounded px-1.5 py-0.5 text-[10px] text-white {providerBadgeClass(
									act.source as ProviderKey
								)}"
							>
								{providerLabel(act.source as ProviderKey)}
							</span>
							<span class="text-fg-muted" aria-hidden="true">›</span>
						</a>
					{/each}
					<a href="{base}/library/activities" class="mt-1 text-xs text-fg-secondary hover:text-fg-primary">
						활동 전체 →
					</a>
				{/if}
			</div>
		</section>

		<!-- ══ L2 — 흐름·훈련·성장 ══ -->
		<section class="order-3 flex flex-col gap-3 border-t border-border-subtle pt-4">
			<p class="text-xs uppercase tracking-wide text-fg-muted">흐름 · 훈련 · 성장</p>

			{#if narrative}
				<!-- 내러티브 텍스트 -->
				{#each narrative.text.split('\n').filter((p) => p.trim()) as paragraph}
					<p class="text-sm leading-relaxed text-fg-primary">{paragraph}</p>
				{/each}

				<!-- Evidence 칩 -->
				{#if narrative.evidence.length > 0}
					<div class="flex flex-wrap gap-2">
						{#each narrative.evidence as ev}
							<EvidenceQuote {...adaptEvidence(ev, openEvidence)} />
						{/each}
					</div>
				{:else}
					<p class="text-xs text-fg-muted">(데이터 부족 — 추후 업데이트)</p>
				{/if}

				<!-- 피트니스·폼 시그니처 차트 (1-A) — 이력 90일 + 레이스 아침까지 TSB 예측. 스크럽으로 값 확인, 헤더 링크로 이번 달 이야기(1-C) -->
				{#if (data.ctlTrend?.points.length ?? 0) > 1 && (data.tsbTrend?.points.length ?? 0) > 1}
					<section class="flex flex-col gap-2 rounded-lg border border-border-subtle bg-surface-2 p-3" aria-label="피트니스·폼">
						<div class="flex items-center justify-between text-xs text-fg-muted">
							<span>체력·피로·폼 · 최근 3개월{data.raceHub?.projection ? ' + 레이스 예측' : ''}</span>
							<button type="button" onclick={() => { showMonthNarrative = true; }} class="hover:text-fg-primary">이번 달 이야기 →</button>
						</div>
						<FormChart
							ctl={data.ctlTrend?.points ?? []}
							atl={data.atlTrend?.points ?? []}
							tsb={data.tsbTrend?.points ?? []}
							projection={data.raceHub?.projection ?? null}
							raceDate={data.raceHub?.goal?.race_date ?? null}
						/>
					</section>
				{/if}

				<!-- 마일스톤 목록 -->
				{#if narrative.milestones.length > 0}
					<div class="flex flex-col gap-1">
						{#each narrative.milestones as m (m.id)}
							{#if m.activity_id != null}
								<a
									href="{base}/library/{m.activity_id}"
									class="flex items-start gap-2 text-sm hover:text-fg-primary"
								>
									<Icon name={milestoneIconName(m.type)} class="h-4 w-4 shrink-0 text-fg-muted" />
									<span class="text-fg-muted">{m.date}</span>
									<span class="flex-1">{m.title}</span>
									<span class="shrink-0 text-fg-muted">›</span>
								</a>
							{:else}
								<div class="flex items-start gap-2 text-sm">
									<Icon name={milestoneIconName(m.type)} class="h-4 w-4 shrink-0 text-fg-muted" />
									<span class="text-fg-muted">{m.date}</span>
									<span class="flex-1">{m.title}</span>
								</div>
							{/if}
						{/each}
					</div>
					<button
						class="self-start text-sm text-fg-secondary hover:text-fg-primary"
						onclick={() => { showMilestonesPanel = true; }}
					>전체 마일스톤 →</button>
				{/if}

				{#if narrative.source === 'rule'}
					<p class="text-xs text-fg-muted">규칙 기반 요약</p>
				{/if}

				<!-- 월간 전체 이야기 패널 열기 -->
				<button
					class="self-start text-sm text-fg-secondary hover:text-fg-primary"
					onclick={() => { showMonthNarrative = true; }}
				>이번 달 전체 이야기 보기 →</button>
			{:else}
				<!-- 내러티브 로딩 실패 또는 미제공 시 fallback 스텁 -->
				<p class="text-sm text-fg-secondary">
					현재 CTL {status.training_status.ctl ?? '—'} ·
					<span class="text-fg-muted">상세 이야기를 불러올 수 없습니다.</span>
				</p>
			{/if}
		</section>

		</div>

		<!-- ══ L3 — 데이터 드릴다운 ══ -->
		<section class="order-5 flex flex-col gap-2 border-t border-border-subtle pt-4 lg:col-span-2">
			<p class="text-xs uppercase tracking-wide text-fg-muted">원본 데이터</p>
			<a href="{base}/library" class="text-sm text-fg-secondary hover:text-fg-primary">
				Library에서 전체 탐색 →
			</a>
		</section>
	</div>

	<!-- MetricBreakdown 드릴다운 패널 -->
	{#if drillTop}
		<MetricBreakdown
			slug={drillTop.slug}
			scopeType={drillTop.scopeType}
			scopeId={drillTop.scopeId}
			onClose={closeDrill}
			onDrillInput={handleDrillInput}
		/>
	{/if}

	<!-- MonthNarrative 월간 이야기 패널 -->
	{#if showMonthNarrative}
		<MonthNarrative onClose={() => { showMonthNarrative = false; }} />
	{/if}

	<!-- MilestonesPanel 전체 마일스톤 패널 -->
	{#if showMilestonesPanel}
		<MilestonesPanel onClose={() => { showMilestonesPanel = false; }} />
	{/if}
</DrillPanel>
{/if}
