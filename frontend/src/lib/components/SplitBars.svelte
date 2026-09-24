<script lang="ts">
	// km 스플릿 막대 — computeSplits() 결과를 시각화.
	// 빠를수록 막대가 길다. 최고 구간 green·평균보다 빠름 blue·느림 amber.
	// DECISIONS.md [P7-IMPL-ACTIVITY-SPLITS] (3)
	import type { Split } from '$lib/splits';
	import { formatPace } from '$lib/format';

	let {
		splits,
		avgPaceSecKm = null
	}: {
		splits: Split[];
		avgPaceSecKm?: number | null;
	} = $props();

	// 평균 페이스: 외부에서 주어지면 사용, 없으면 거리 가중 평균으로 계산
	const avg = $derived(
		avgPaceSecKm ??
			(splits.length > 0
				? splits.reduce((s, x) => s + x.paceSecKm * (x.distanceM / 1000), 0) /
					splits.reduce((s, x) => s + x.distanceM / 1000, 0)
				: null)
	);

	const minPace = $derived(splits.length > 0 ? Math.min(...splits.map((s) => s.paceSecKm)) : 0);
	const maxPace = $derived(splits.length > 0 ? Math.max(...splits.map((s) => s.paceSecKm)) : 0);

	// 가장 빠른 구간의 인덱스
	const fastestIdx = $derived(
		splits.reduce((best, s, i) => (s.paceSecKm < splits[best].paceSecKm ? i : best), 0)
	);

	// 빠를수록 넓게: 최소 25%, 최대 100%
	function barWidth(pace: number): string {
		if (maxPace === minPace) return '80%';
		return `${(25 + 75 * (1 - (pace - minPace) / (maxPace - minPace))).toFixed(1)}%`;
	}

	// green=#10b981 / blue=#3b82f6 / amber=#f59e0b
	function barColor(pace: number, idx: number): string {
		if (idx === fastestIdx) return '#10b981';
		if (avg != null && pace <= avg) return '#3b82f6';
		return '#f59e0b';
	}

	const hasHr = $derived(splits.some((s) => s.avgHr != null));
	const hasElev = $derived(splits.some((s) => s.elevDelta != null));
</script>

{#if splits.length > 0}
	<section class="flex flex-col gap-2">
		<p class="text-xs uppercase tracking-wide text-fg-muted">
			km 스플릿 <span class="normal-case opacity-60">· 스트림 기반 추정</span>
		</p>
		<div class="flex flex-col gap-1">
			{#each splits as s, i (s.km)}
				<div class="flex items-center gap-2 text-xs">
					<!-- km 번호 -->
					<span class="w-5 shrink-0 text-right font-mono text-fg-muted">{s.km}</span>
					<!-- 막대 + 페이스 레이블 -->
					<div class="min-w-0 flex-1">
						<div
							class="flex h-5 items-center overflow-hidden rounded px-1.5"
							style="width:{barWidth(s.paceSecKm)}; background:{barColor(s.paceSecKm, i)}"
						>
							<span class="shrink-0 font-mono text-[10px] text-white"
								>{formatPace(s.paceSecKm)}</span
							>
						</div>
					</div>
					<!-- 심박 -->
					{#if hasHr}
						<span class="w-14 shrink-0 text-right font-mono text-fg-secondary">
							{s.avgHr != null ? `${s.avgHr} bpm` : '—'}
						</span>
					{/if}
					<!-- 고도 변화 -->
					{#if hasElev}
						<span class="w-10 shrink-0 text-right font-mono text-fg-muted">
							{s.elevDelta != null ? `${s.elevDelta > 0 ? '+' : ''}${s.elevDelta}m` : '—'}
						</span>
					{/if}
				</div>
			{/each}
		</div>
	</section>
{/if}
