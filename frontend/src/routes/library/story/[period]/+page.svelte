<script lang="ts">
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';

	export let data;

	let unitToggle: 'month' | 'week' | 'block' = 'month';
	let copied = false;

	$: ({
		period,
		paragraph,
		chips,
		compare,
		intensity,
		key_sessions: keySessions,
		risk_peak: riskPeak,
		milestones
	} = data);

	function navigatePeriod(offset: number) {
		const currentPeriod = $page.params.period;
		let newPeriod = '';

		if (currentPeriod.includes('-W')) {
			// Week navigation
			const [year, weekStr] = currentPeriod.split('-W');
			const week = parseInt(weekStr) + offset;
			newPeriod = `${year}-W${week.toString().padStart(2, '0')}`;
		} else if (currentPeriod.startsWith('b-')) {
			// Block navigation — not implemented yet
			return;
		} else {
			// Month navigation
			const [year, month] = currentPeriod.split('-');
			const yearNum = parseInt(year);
			const monthNum = parseInt(month) + offset;

			if (monthNum < 1) {
				newPeriod = `${yearNum - 1}-12`;
			} else if (monthNum > 12) {
				newPeriod = `${yearNum + 1}-01`;
			} else {
				newPeriod = `${year}-${monthNum.toString().padStart(2, '0')}`;
			}
		}

		goto(`/library/story/${newPeriod}`);
	}

	function toggleUnit(unit: 'month' | 'week' | 'block') {
		unitToggle = unit;
		// Navigate to same date in different unit (to be implemented)
	}

	function copyToClipboard() {
		const text = `${period.label}\n\n${paragraph}\n\n${
			chips.map((c) => `${c.label}`).join(' · ')
		}`;
		navigator.clipboard.writeText(text);
		copied = true;
		setTimeout(() => (copied = false), 2000);
	}

	function drillToMetric(drill) {
		if (!drill) return;
		// Navigate to metric detail (to be implemented with drill panel)
		console.log('Drill to metric:', drill);
	}

	function drillToSession(sessionId: number) {
		goto(`/library/${sessionId}`);
	}

	function drillToMilestone(milestoneId: number) {
		goto(`/library/${milestoneId}`);
	}
</script>

<div class="story-page">
	<!-- Period Navigation -->
	<div class="period-header sticky top-0 bg-white/95 backdrop-blur z-10 p-4 border-b">
		<div class="flex items-center justify-between mb-3">
			<button class="btn-icon" on:click={() => navigatePeriod(-1)}>‹</button>
			<div class="text-center flex-1">
				<div class="text-xl font-semibold">{period.label}</div>
				<div class="text-xs text-gray-500">{period.start} ~ {period.end}</div>
			</div>
			<button class="btn-icon" on:click={() => navigatePeriod(1)}>›</button>
		</div>

		<!-- Unit Toggle -->
		<div class="flex gap-1 text-sm">
			<button
				class="flex-1 px-2 py-1 rounded transition"
				class:active={unitToggle === 'month'}
				on:click={() => toggleUnit('month')}
			>
				월
			</button>
			<button
				class="flex-1 px-2 py-1 rounded transition"
				class:active={unitToggle === 'week'}
				on:click={() => toggleUnit('week')}
			>
				주
			</button>
			<button
				class="flex-1 px-2 py-1 rounded transition"
				class:active={unitToggle === 'block'}
				on:click={() => toggleUnit('block')}
				disabled
			>
				블록
			</button>
		</div>

		<!-- Copy Button -->
		<button
			class="mt-2 w-full px-3 py-2 text-sm rounded transition"
			class:copied
			on:click={copyToClipboard}
		>
			{copied ? '복사됨' : '텍스트로 복사'}
		</button>
	</div>

	<!-- Main Content -->
	<div class="p-4 max-w-2xl mx-auto">
		<!-- Narrative Paragraph -->
		<div class="mb-6 p-4 bg-gray-50 rounded">
			<p class="text-base leading-relaxed">{paragraph}</p>
		</div>

		<!-- Drill Chips -->
		{#if chips.length > 0}
			<div class="mb-6 flex flex-wrap gap-2">
				{#each chips as chip}
					<button
						class="px-3 py-1 rounded-full text-sm border transition"
						class:drillable={chip.drill}
						on:click={() => chip.drill && drillToMetric(chip.drill)}
					>
						{chip.label}
					</button>
				{/each}
			</div>
		{/if}

		<!-- Compare Section -->
		{#if compare.length > 0}
			<div class="mb-6">
				<h3 class="text-sm font-semibold mb-3">이전 {unitToggle}과 비교</h3>
				<div class="space-y-2">
					{#each compare as item}
						<div class="flex justify-between items-center p-2 bg-gray-50 rounded text-sm">
							<span>{item.label}</span>
							<div class="text-right">
								<div class="font-semibold">{item.value}</div>
								<div class={item.delta_pct >= 0 ? 'text-green-600' : 'text-red-600'}>
									{item.delta_pct >= 0 ? '+' : ''}{item.delta_pct}% ({item.prev})
								</div>
							</div>
						</div>
					{/each}
				</div>
			</div>
		{/if}

		<!-- Intensity Distribution -->
		{#if intensity}
			<div class="mb-6">
				<h3 class="text-sm font-semibold mb-3">강도 분포</h3>
				{#if intensity.status === 'insufficient'}
					<div class="p-3 bg-gray-100 rounded text-sm text-gray-600">존 데이터 부족</div>
				{:else}
					<div class="space-y-2">
						<div class="flex items-center gap-2 text-sm">
							<span class="w-12">Z1-2</span>
							<div class="flex-1 bg-gray-200 rounded h-6">
								<div class="bg-blue-400 h-full rounded" style="width: {intensity.z12_pct}%"></div>
							</div>
							<span class="w-8 text-right">{intensity.z12_pct}%</span>
						</div>
						<div class="flex items-center gap-2 text-sm">
							<span class="w-12">Z3</span>
							<div class="flex-1 bg-gray-200 rounded h-6">
								<div class="bg-yellow-400 h-full rounded" style="width: {intensity.z3_pct}%"></div>
							</div>
							<span class="w-8 text-right">{intensity.z3_pct}%</span>
						</div>
						<div class="flex items-center gap-2 text-sm">
							<span class="w-12">Z4-5</span>
							<div class="flex-1 bg-gray-200 rounded h-6">
								<div class="bg-red-400 h-full rounded" style="width: {intensity.z45_pct}%"></div>
							</div>
							<span class="w-8 text-right">{intensity.z45_pct}%</span>
						</div>
					</div>
				{/if}
			</div>
		{/if}

		<!-- Key Sessions -->
		{#if keySessions.length > 0}
			<div class="mb-6">
				<h3 class="text-sm font-semibold mb-3">대표 세션</h3>
				<div class="space-y-2">
					{#each keySessions as session}
						<button
							class="w-full p-3 bg-gray-50 rounded text-left hover:bg-gray-100 transition text-sm"
							on:click={() => drillToSession(session.id)}
						>
							<div class="font-semibold">{session.name}</div>
							<div class="text-gray-600">{session.date} · {session.distance_km}km</div>
						</button>
					{/each}
				</div>
			</div>
		{/if}

		<!-- Risk Peak -->
		{#if riskPeak}
			<div class="mb-6 p-3 bg-red-50 rounded border border-red-200">
				<div class="text-sm font-semibold text-red-900">위험 최고</div>
				<div class="text-sm text-red-800 mt-1">
					{riskPeak.slug.toUpperCase()} {riskPeak.value} ({riskPeak.date})
				</div>
			</div>
		{/if}

		<!-- Milestones -->
		{#if milestones.length > 0}
			<div class="mb-6">
				<h3 class="text-sm font-semibold mb-3">마일스톤</h3>
				<div class="space-y-2">
					{#each milestones as milestone}
						<button
							class="w-full p-3 bg-gray-50 rounded text-left hover:bg-gray-100 transition text-sm flex items-center gap-2"
							on:click={() => drillToMilestone(milestone.id)}
						>
							<span class="text-lg">◆</span>
							<div class="flex-1">
								<div class="font-semibold">{milestone.title || milestone.label}</div>
								<div class="text-gray-600">{milestone.achieved_date || milestone.date}</div>
							</div>
						</button>
					{/each}
				</div>
			</div>
		{/if}
	</div>
</div>

<style>
	.story-page {
		min-height: 100vh;
		background: #fafafa;
	}

	.btn-icon {
		@apply px-3 py-2 rounded transition hover:bg-gray-100 active:bg-gray-200;
	}

	.active {
		@apply bg-blue-100 text-blue-900 font-semibold;
	}

	.copied {
		@apply bg-green-100 text-green-900;
	}

	.drillable {
		@apply cursor-pointer border-blue-300 hover:bg-blue-50;
	}
</style>
