<script lang="ts">
	// 활동 행 공용 컴포넌트 — 2줄(이름 / 날짜·페이스·HR·플래그) + 우측 거리·시간 + ›. 행 전체가 상세 링크(?from=).
	import RouteThumb from '$lib/components/RouteThumb.svelte';
	import Icon from '$lib/components/Icon.svelte';
	import { providerLabel, providerBadgeClass } from '$lib/provider';
	import { formatDuration } from '$lib/format';
	import { dayLabel } from '$lib/activityList';
	import { activityDetailHref, rowFigures, type ActivityOrigin } from '$lib/activityRow';
	import type { ActivityFlag } from '$lib/activityFlags';
	import type { ActivityDisplay, ProviderKey } from '$lib/types';
	import { base } from '$app/paths';

	interface RowActivity {
		id: number;
		name: string;
		display_title?: string;
		workout_label?: string | null;
		is_race?: boolean;
		rpe?: number | null;
		start_time: string;
		distance_m?: number | null;
		duration_sec?: number | null;
		avg_hr?: number | null;
		avg_pace_sec_km?: number | null;
		source_count?: number;
		source?: string;
		route?: [number, number][] | null;
		sport_family?: string;
		sport_label?: string;
		display?: ActivityDisplay | null;
	}

	let {
		act,
		from,
		flag = null,
		showProvider = false,
		thumbSize = 40
	}: {
		act: RowActivity;
		from: ActivityOrigin;
		flag?: ActivityFlag | null;
		showProvider?: boolean;
		thumbSize?: number;
	} = $props();

	// 종목별 거리·페이스(A-31: 수영 /100m·m, 사이클 km/h, 근력·기타는 거리 대신 시간)
	const fig = $derived(rowFigures(act));
</script>

<a
	href={activityDetailHref(base, act.id, from)}
	class="flex min-h-11 items-center gap-3 px-4 py-2.5 hover:bg-surface-2 active:bg-surface-3"
	data-testid="activity-row"
>
	<RouteThumb route={act.route} size={thumbSize} />
	<div class="flex min-w-0 flex-1 flex-col gap-0.5">
		<div class="flex min-w-0 items-center gap-1.5">
			{#if act.sport_family && act.sport_family !== 'running'}<span class="shrink-0 rounded bg-semantic-teal/15 px-1.5 py-0.5 text-[10px] font-medium text-semantic-teal" data-testid="sport-chip">{act.sport_label ?? '기타'}</span>{/if}
			<span class="truncate text-sm font-medium">{act.display_title ?? act.name}</span>
			{#if act.workout_label}<span class="shrink-0 rounded px-1.5 py-0.5 text-[10px] {act.is_race ? 'bg-semantic-amber/20 text-semantic-amber' : 'bg-surface-3 text-fg-secondary'}">{act.workout_label}</span>{/if}
			{#if act.rpe}<span class="shrink-0 rounded bg-surface-3 px-1.5 py-0.5 text-[10px] text-fg-secondary" data-testid="rpe-badge">RPE {act.rpe}</span>{/if}
		</div>
		<div class="flex flex-wrap items-center gap-x-2 text-xs text-fg-muted">
			<span>{dayLabel(act.start_time)}</span>
			{#if fig.pace}<span class="font-mono">{fig.pace}</span>{/if}
			{#if act.avg_hr != null}<span class="font-mono">HR {act.avg_hr}</span>{/if}
			{#if (act.source_count ?? 1) > 1}<span class="rounded border border-semantic-teal/50 px-1 py-px text-[9px] text-semantic-teal" data-testid="merged-badge">{act.source_count}소스 병합</span>{/if}
			{#if flag}<span class="flex items-center gap-0.5 text-[10px] text-semantic-amber" title={flag.title}><Icon name="warning" class="h-3 w-3" /> {flag.label}</span>{/if}
			{#if showProvider && act.source}
				<span class="rounded px-1.5 py-0.5 text-[10px] {providerBadgeClass(act.source as ProviderKey)}">{providerLabel(act.source as ProviderKey)}</span>
			{/if}
		</div>
	</div>
	<div class="flex shrink-0 flex-col items-end">
		{#if fig.distance}
			<span class="font-mono text-lg font-bold leading-tight"
				>{fig.distance.value}<span class="text-[10px] font-normal text-fg-muted"> {fig.distance.unit}</span></span
			>
			<span class="font-mono text-xs text-fg-muted">{act.duration_sec != null ? formatDuration(act.duration_sec) : '—'}</span>
		{:else}
			<span class="font-mono text-lg font-bold leading-tight">{act.duration_sec != null ? formatDuration(act.duration_sec) : '—'}</span>
		{/if}
	</div>
	<span class="text-fg-muted" aria-hidden="true">›</span>
</a>
