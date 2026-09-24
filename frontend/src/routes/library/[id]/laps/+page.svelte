<script lang="ts">
	// 03c-library.md 3-C 랩 탭 — activity_laps(lap_index 순) 목록 + 랩별 페이스 막대.
	import type { LapsPageData } from './+page';
	import ActivityTabs from '$lib/components/ActivityTabs.svelte';
	import { providerLabel, providerBadgeClass } from '$lib/provider';
	import { formatDistance, formatDuration, formatPace } from '$lib/format';
	import { base } from '$app/paths';
	import type { ActivityLap, ProviderKey } from '$lib/types';

	let { data }: { data: LapsPageData } = $props();

	function lapPace(l: ActivityLap): number | null {
		if (l.avg_pace_sec_km != null && l.avg_pace_sec_km > 0) return l.avg_pace_sec_km;
		if (l.distance_m && l.duration_sec && l.distance_m > 0) return l.duration_sec / (l.distance_m / 1000);
		return null;
	}

	const paces = $derived(data.laps.map(lapPace));
	const fastest = $derived(Math.min(...paces.filter((p): p is number => p != null)));
	const source = $derived(data.laps.length > 0 ? data.laps[0].source : null);

	// 가장 빠른 랩 = 100%. 너무 짧아 안 보이지 않게 최소 8%.
	function barPct(p: number | null): number {
		if (p == null || !Number.isFinite(fastest)) return 0;
		return Math.max(8, Math.round((fastest / p) * 100));
	}
</script>

<div class="flex items-center gap-2 border-b border-border-subtle px-4 py-3">
	<a href="{base}/library/{data.activityId}" class="shrink-0 text-fg-muted" aria-label="활동 상세로">←</a>
	<h1 class="text-base font-semibold">랩</h1>
</div>

<ActivityTabs activityId={data.activityId} active="laps" />

{#if data.errorMessage && data.laps.length === 0}
	<div class="px-4 py-8 text-center">
		<p class="text-sm text-fg-secondary">{data.errorMessage}</p>
		<a href="{base}/library/{data.activityId}" class="mt-2 block text-xs text-fg-muted underline">← 활동으로 돌아가기</a>
	</div>
{:else if data.laps.length === 0}
	<div class="px-4 py-8 text-center">
		<p class="text-sm text-fg-muted">랩 데이터 없음</p>
		<a href="{base}/library/{data.activityId}" class="mt-2 block text-xs text-fg-muted underline">← 활동으로 돌아가기</a>
	</div>
{:else}
	<div class="flex flex-col gap-3 px-4 py-4">
		<div class="flex items-center gap-2 text-xs text-fg-muted">
			{#if source}
				<span class="rounded px-1.5 py-0.5 text-[10px] text-white {providerBadgeClass(source as ProviderKey)}">{providerLabel(source as ProviderKey)}</span>
			{/if}
			<span>{data.laps.length}개 랩{#if Number.isFinite(fastest)}{' · '}가장 빠른 랩 {formatPace(fastest)}{/if}</span>
		</div>
		<ul class="divide-y divide-border-subtle">
			{#each data.laps as lap, i (lap.id)}
				<li class="flex flex-col gap-1 py-2.5">
					<div class="flex items-baseline gap-3 text-sm">
						<span class="w-6 shrink-0 font-mono text-xs text-fg-muted">{i + 1}</span>
						<span class="font-mono font-medium">{lap.distance_m != null ? formatDistance(lap.distance_m) : '—'}</span>
						<span class="font-mono text-fg-secondary">{lap.duration_sec != null ? formatDuration(lap.duration_sec) : '—'}</span>
						<span class="ml-auto font-mono font-medium">{paces[i] != null ? formatPace(paces[i] as number) : '—'}</span>
					</div>
					<div class="flex items-center gap-3 pl-9">
						<div class="h-1.5 flex-1 rounded bg-surface-3">
							<div class="h-1.5 rounded bg-fg-secondary" style="width:{barPct(paces[i])}%"></div>
						</div>
						<span class="flex shrink-0 gap-2 text-xs text-fg-muted">
							{#if lap.avg_hr != null}<span>HR {lap.avg_hr}{#if lap.max_hr != null}/{lap.max_hr}{/if}</span>{/if}
							{#if lap.avg_cadence != null}<span>{Math.round(lap.avg_cadence)}spm</span>{/if}
							{#if lap.avg_power != null}<span>{Math.round(lap.avg_power)}W</span>{/if}
							{#if lap.elevation_gain != null && lap.elevation_gain > 0}<span>↑{Math.round(lap.elevation_gain)}m</span>{/if}
						</span>
					</div>
				</li>
			{/each}
		</ul>
	</div>
{/if}
