<script lang="ts">
	// 03a-today.md 1-A' — L0(QuickInput+RecommendationCard) + L1(MetricCell×3 + 최근 활동) + L2(내러티브).
	// Phase 7b: MetricCell 드릴다운 → MetricBreakdown 패널, L2 실데이터 연결.
	import type { TodayPageData } from './+page';
	import MetricCell from '$lib/components/MetricCell.svelte';
	import MetricBreakdown from '$lib/components/MetricBreakdown.svelte';
	import MonthNarrative from '$lib/components/MonthNarrative.svelte';
	import QuickInput from '$lib/components/QuickInput.svelte';
	import RecommendationCard from '$lib/components/RecommendationCard.svelte';
	import EvidenceQuote from '$lib/components/EvidenceQuote.svelte';
	import { postCheckin } from '$lib/api/today';
	import { providerLabel, providerBadgeClass } from '$lib/provider';
	import { readinessStatus, tsbStatus } from '$lib/status';
	import { formatDistance, formatDuration, formatRelativeDay } from '$lib/format';
	import { base } from '$app/paths';
	import type { BriefingEvidence, EvidenceQuoteProps, PainLevel, ProviderKey } from '$lib/types';

	let { data }: { data: TodayPageData } = $props();

	let checkin = $state(data.today?.checkin ?? null);
	let savingCheckin = $state(false);
	let checkinError = $state<string | null>(null);

	// MetricBreakdown 드릴다운 스택 — slug 목록, 마지막 항목이 현재 표시 패널.
	// onDrillInput으로 push, onClose로 전체 비움.
	let drillStack = $state<string[]>([]);
	let showMonthNarrative = $state(false);

	const drillSlug = $derived(drillStack.length > 0 ? drillStack[drillStack.length - 1] : null);

	function handleDrill(payload: { slug: string; provider: ProviderKey | null }) {
		drillStack = [...drillStack, payload.slug];
	}

	function handleDrillInput(slug: string) {
		drillStack = [...drillStack, slug];
	}

	function closeDrill() {
		drillStack = [];
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

	// today_service.get_today_briefing()의 evidence 형태({type,metric,value,label})를
	// EvidenceQuoteProps({type, metric:{slug,value}, label})로 변환 — 04 컴포넌트 스펙과
	// 실제 서비스 응답 형태가 달라서 필요한 프론트 전용 매핑(백엔드는 안 건드림).
	function adaptEvidence(ev: BriefingEvidence): EvidenceQuoteProps {
		return { type: 'metric', label: ev.label, metric: { slug: ev.metric, value: ev.value } };
	}

	// 마일스톤 타입별 아이콘
	const milestoneIcon: Record<string, string> = {
		distance_threshold: '🎯',
		pb: '🏃',
		metric_recompute: '🔄'
	};
</script>

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

	<div class="flex flex-col gap-6 px-4 py-4">
		<!-- ══ L0 — 즉시 브리핑 ══ -->
		<section class="flex flex-col gap-3">
			<QuickInput
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

			<RecommendationCard
				recommendation={{
					body: briefing.headline,
					evidence: briefing.evidence.map(adaptEvidence)
				}}
				actions={[{ label: 'Coach에게 더 묻기 →', href: `${base}/coach`, variant: 'ghost' }]}
			/>
		</section>

		<!-- ══ L1 — 내 상태 요약 ══ -->
		<section class="flex flex-col gap-3">
			<div class="grid grid-cols-3 gap-2">
				<MetricCell
					slug="utrs"
					label="UTRS"
					value={status.readiness.utrs?.value ?? null}
					provider={status.providers.utrs ?? null}
					status={readinessStatus('utrs', status.readiness.utrs?.level)}
					unavailable={!status.readiness.utrs}
					drillable={true}
					onDrill={handleDrill}
				/>
				<MetricCell
					slug="cirs"
					label="CIRS"
					value={status.readiness.cirs?.value ?? null}
					provider={status.providers.cirs ?? null}
					status={readinessStatus('cirs', status.readiness.cirs?.level)}
					unavailable={!status.readiness.cirs}
					drillable={true}
					onDrill={handleDrill}
				/>
				<MetricCell
					slug="tsb"
					label="TSB"
					value={status.training_status.tsb ?? null}
					provider={status.providers.tsb ?? null}
					status={tsbStatus(status.training_status.tsb)}
					unavailable={status.training_status.tsb === null}
					drillable={true}
					onDrill={handleDrill}
				/>
			</div>

			<div class="flex flex-col gap-1 rounded-lg border border-border-subtle bg-surface-2 p-3">
				<p class="mb-1 text-xs text-fg-muted">최근 활동</p>
				{#if data.today.recent_activities.length === 0}
					<p class="text-sm text-fg-muted">아직 활동이 없습니다.</p>
				{:else}
					{#each data.today.recent_activities as act (act.id)}
						<div class="flex items-center gap-2 py-1.5 text-sm">
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
						</div>
					{/each}
				{/if}
			</div>
		</section>

		<!-- ══ L2 — 흐름·훈련·성장 ══ -->
		<section class="flex flex-col gap-3 border-t border-border-subtle pt-4">
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
							<EvidenceQuote {...adaptEvidence(ev)} />
						{/each}
					</div>
				{/if}

				<!-- 마일스톤 목록 -->
				{#if narrative.milestones.length > 0}
					<div class="flex flex-col gap-1">
						{#each narrative.milestones as m (m.id)}
							<div class="flex items-start gap-2 text-sm">
								<span aria-hidden="true">{milestoneIcon[m.type] ?? '🔖'}</span>
								<span class="text-fg-muted">{m.date}</span>
								<span class="flex-1">{m.title}</span>
							</div>
						{/each}
					</div>
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
					<span class="text-fg-muted">상세 이야기·계획 연동을 불러올 수 없습니다.</span>
				</p>
			{/if}
		</section>
	</div>

	<!-- MetricBreakdown 드릴다운 패널 -->
	{#if drillSlug}
		<MetricBreakdown
			slug={drillSlug}
			scopeType="daily"
			scopeId={status.date}
			onClose={closeDrill}
			onDrillInput={handleDrillInput}
		/>
	{/if}

	<!-- MonthNarrative 월간 이야기 패널 -->
	{#if showMonthNarrative}
		<MonthNarrative onClose={() => { showMonthNarrative = false; }} />
	{/if}
{/if}
