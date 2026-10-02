<script lang="ts">
	// km 스플릿 — 평균 대비 발산 막대(고정 ±30s/km). 빠름=왼쪽, 느림=오른쪽. 서버 splits 사용.
	import type { ActivitySplit } from '$lib/types';
	import { formatPace } from '$lib/format';
	import {
		SPLIT_DOMAIN_SEC,
		averagePace,
		buildSplitRows,
		divergence,
		fastestRow
	} from '$lib/chart/splitBars';

	let {
		splits,
		selectedSeg = null,
		onSelect
	}: {
		splits: ActivitySplit[];
		selectedSeg?: number | null;
		onSelect?: (seg: number | null) => void;
	} = $props();

	const rows = $derived(buildSplitRows(splits));
	const avg = $derived(averagePace(rows));
	const best = $derived(fastestRow(rows));
	const hasHr = $derived(rows.some((r) => r.avg_hr != null));
	const hasElev = $derived(rows.some((r) => r.elev_gain_m != null));
	const isSel = (segs: number[]) => selectedSeg != null && segs.includes(selectedSeg);

	function pick(segs: number[]) {
		onSelect?.(isSel(segs) ? null : segs[0]);
	}
	const fmtStop = (s: number) => `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`;
</script>

{#if rows.length > 0}
	<section class="flex flex-col gap-2" data-testid="split-bars">
		<p class="text-xs uppercase tracking-wide text-fg-muted">
			km 스플릿
			<span class="normal-case opacity-70">
				· 이동 시간 기준{avg != null ? ` · 평균 ${formatPace(avg)}` : ''}{rows.length > 0 &&
				rows[0].segs.length > 1
					? ' · 5km 묶음'
					: ''}
			</span>
		</p>
		<div class="flex flex-wrap gap-x-3 gap-y-1 text-xs text-fg-muted">
			<span class="flex items-center gap-1"><i class="inline-block h-2 w-2 rounded-sm bg-delta-better"></i>평균보다 빠름</span>
			<span class="flex items-center gap-1"><i class="inline-block h-2 w-2 rounded-sm bg-delta-worse"></i>평균보다 느림</span>
			<span>눈금 ±{SPLIT_DOMAIN_SEC}초</span>
		</div>
		<div class="flex flex-col gap-1" role="list">
			{#each rows as r, i (r.idx)}
				{@const dv = divergence(r.pace_sec_km, avg)}
				{@const delta = r.pace_sec_km != null && avg != null ? Math.round(r.pace_sec_km - avg) : null}
				<button
					type="button"
					role="listitem"
					class="flex min-h-7 items-center gap-2 rounded px-1 text-xs hover:bg-surface-2 {isSel(r.segs) ? 'bg-surface-2 ring-1 ring-fg-muted' : ''}"
					aria-pressed={isSel(r.segs)}
					aria-label="{r.label}km {r.pace_sec_km != null ? formatPace(r.pace_sec_km) : '페이스 없음'}{r.partial ? ' (부분 구간)' : ''}"
					data-testid="split-row"
					onclick={() => pick(r.segs)}
				>
					<span class="w-9 shrink-0 text-right font-mono text-fg-muted">{r.label}</span>
					<span class="w-12 shrink-0 text-right font-mono text-fg-primary">
						{r.pace_sec_km != null ? formatPace(r.pace_sec_km) : '—'}
					</span>
					<span class="relative h-4 min-w-0 flex-1" aria-hidden="true">
						<span class="absolute inset-y-0 left-1/2 w-px bg-fg-muted opacity-60"></span>
						{#if r.pace_sec_km != null}
							<span
								class="absolute inset-y-0.5 {dv.frac < 0 ? 'bg-delta-better' : 'bg-delta-worse'} {r.partial ? 'opacity-60' : ''} {i === best ? 'outline outline-1 outline-fg-primary' : ''}"
								style="{dv.frac < 0 ? `right:50%` : `left:50%`}; width:{Math.abs(dv.frac) * 50}%; {r.partial
									? 'border:1px dashed currentColor; background:transparent;'
									: ''}"
							></span>
						{/if}
					</span>
					<span class="w-9 shrink-0 text-right font-mono text-fg-muted">
						{delta != null && !r.partial ? `${delta > 0 ? '+' : ''}${delta}${dv.clipped ? '+' : ''}` : ''}
					</span>
					{#if r.stop_sec >= 5}
						<span class="shrink-0 font-mono text-fg-muted" title="이 구간의 정지 시간(페이스에서 제외)">정지 {fmtStop(r.stop_sec)}</span>
					{/if}
					{#if hasHr}
						<span class="w-14 shrink-0 text-right font-mono text-fg-secondary">{r.avg_hr != null ? `${r.avg_hr} bpm` : '—'}</span>
					{/if}
					{#if hasElev}
						<span class="w-10 shrink-0 text-right font-mono text-fg-muted">{r.elev_gain_m != null ? `+${Math.round(r.elev_gain_m)}m` : '—'}</span>
					{/if}
				</button>
			{/each}
		</div>
	</section>
{/if}
