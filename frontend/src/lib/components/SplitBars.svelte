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

	// 1km 미만 부분 구간은 스케일·최고 구간 판정에서 뺀다(0.3km 잔여 구간이 최댓값·최고 구간을 가져가던 문제).
	const isPartial = (s: { distanceM: number }) => s.distanceM < 1000;
	const full = $derived(splits.filter((s) => !isPartial(s)));
	const basis = $derived(full.length > 0 ? full : splits);
	const minPace = $derived(basis.length > 0 ? Math.min(...basis.map((s) => s.paceSecKm)) : 0);
	const maxPace = $derived(basis.length > 0 ? Math.max(...basis.map((s) => s.paceSecKm)) : 0);

	// 가장 빠른 온전한 구간의 인덱스(부분 구간 제외)
	const fastestIdx = $derived(
		splits.reduce(
			(best, s, i) =>
				!isPartial(s) && (best < 0 || s.paceSecKm < splits[best].paceSecKm) ? i : best,
			-1
		)
	);

	// 빠를수록 넓게: 최소 25%, 최대 100%
	function barWidth(pace: number): string {
		if (maxPace === minPace) return '80%';
		const frac = Math.min(1, Math.max(0, (pace - minPace) / (maxPace - minPace)));
		return `${(25 + 75 * (1 - frac)).toFixed(1)}%`;
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
			km 스플릿 <span class="normal-case opacity-60">· 이동 시간 기준(정지 제외)</span>
		</p>
		<div class="flex flex-wrap gap-x-3 gap-y-1 text-[10px] text-fg-muted"><span class="flex items-center gap-1"><i class="inline-block h-2 w-2 rounded-sm" style="background:#10b981"></i>최고 구간</span><span class="flex items-center gap-1"><i class="inline-block h-2 w-2 rounded-sm" style="background:#3b82f6"></i>평균보다 빠름</span><span class="flex items-center gap-1"><i class="inline-block h-2 w-2 rounded-sm" style="background:#f59e0b"></i>평균보다 느림</span>{#if hasHr}<span>· 우측: 평균 심박</span>{/if}{#if hasElev}<span>· 고도 변화</span>{/if}</div>
		<div class="flex flex-col gap-1">
			{#each splits as s, i (s.km)}
				<div class="flex items-center gap-2 text-xs">
					<!-- km 번호 -->
					<span class="w-7 shrink-0 text-right font-mono text-fg-muted">{s.distanceM < 1000 ? `${(s.distanceM / 1000).toFixed(1)}` : s.km}</span>
					<!-- 막대 + 페이스 레이블 -->
					<div class="min-w-0 flex-1">
						<div
							class="flex h-5 items-center overflow-hidden rounded px-1.5 {isPartial(s) ? 'opacity-60' : ''}"
							style="width:{barWidth(s.paceSecKm)}; background:{barColor(s.paceSecKm, i)}"
						>
							<span class="shrink-0 font-mono text-[10px] text-white"
								>{formatPace(s.paceSecKm)}</span
							>
						</div>
					</div>
					{#if s.stoppedSec >= 5}
						<span class="shrink-0 font-mono text-[10px] text-fg-muted" title="이 구간의 정지 시간(페이스에서 제외)"
							>⏸ {Math.floor(s.stoppedSec / 60)}:{String(s.stoppedSec % 60).padStart(2, '0')}</span
						>
					{/if}
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
