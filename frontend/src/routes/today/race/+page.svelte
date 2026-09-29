<script lang="ts">
	// 레이스 허브 — 오늘 탭에서 분리된 상세(design 10-today §3). 데스크톱 2열: ①②③ | ④⑤⑥.
	import { onMount } from 'svelte';
	import { base } from '$app/paths';
	import { invalidate } from '$app/navigation';
	import ErrorState from '$lib/components/ErrorState.svelte';
	import RacePredictionSummary from '$lib/components/RacePredictionSummary.svelte';
	import RaceMorningForm from '$lib/components/RaceMorningForm.svelte';
	import PredictionCompare from '$lib/components/PredictionCompare.svelte';
	import PredictionBasis from '$lib/components/PredictionBasis.svelte';
	import type { RaceHubPageData } from './+page';

	let { data }: { data: RaceHubPageData } = $props();

	const KEY = 'runpulse:showCandidates';
	let showCandidates = $state(false);
	onMount(() => {
		try {
			showCandidates = localStorage.getItem(KEY) === '1';
		} catch {
			/* 저장소 접근 불가 — 기본값 유지 */
		}
	});
	function toggle(e: Event) {
		showCandidates = (e.currentTarget as HTMLInputElement).checked;
		try {
			localStorage.setItem(KEY, showCandidates ? '1' : '0');
		} catch {
			/* noop */
		}
	}
</script>

<div class="mx-auto flex max-w-5xl flex-col gap-4 p-4">
	<div class="flex items-center justify-between">
		<a href="{base}/today" class="text-sm text-fg-muted hover:text-fg-primary">‹ 오늘</a>
		<h1 class="text-base font-semibold">레이스 허브</h1>
		<span class="w-10"></span>
	</div>

	{#if data.failed}
		<ErrorState message="레이스 예측을 불러오지 못했어요" onRetry={() => invalidate('app:race-hub')} />
	{:else if !data.hub?.goal}
		<a
			href="{base}/coach/plan/new"
			class="flex flex-col gap-1 rounded-lg border border-dashed border-border-subtle bg-surface-2 p-4 hover:bg-surface-3"
		>
			<span class="text-sm font-semibold">목표 레이스를 등록해 보세요</span>
			<span class="text-xs text-fg-muted">D-day, 예측 기록, 목표까지의 격차와 준비도 추이를 여기서 볼 수 있어요 →</span>
		</a>
	{:else}
		{@const hub = data.hub}
		<div class="grid grid-cols-1 gap-4 lg:grid-cols-2">
			<div class="flex flex-col gap-4">
				<RacePredictionSummary goal={hub.goal!} pred={hub.prediction} />
				<PredictionBasis />
			</div>
			<div class="flex flex-col gap-4">
				{#if hub.prediction?.compare}
					<section class="flex flex-col gap-2 rounded-lg border border-border-subtle bg-surface-2 p-4">
						<PredictionCompare compare={hub.prediction.compare} {showCandidates} />
						<label class="flex items-center gap-2 text-[11px] text-fg-muted">
							<input type="checkbox" checked={showCandidates} onchange={toggle} />
							검토 중 알고리즘 표시
						</label>
					</section>
				{/if}
				{#if hub.projection}<RaceMorningForm proj={hub.projection} />{/if}
				<a
					href="{base}/today/race/races"
					class="flex items-center justify-between rounded-lg border border-border-subtle bg-surface-2 px-4 py-3 text-sm hover:bg-surface-3"
				>
					<span>예측에 쓰는 대회 · 수정</span><span class="text-fg-muted">›</span>
				</a>
			</div>
		</div>
	{/if}
</div>
