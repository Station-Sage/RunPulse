<script lang="ts">
	// 활동 목록 필터 — 기간 프리셋·월 / 종목·유형(facets 건수 칩) / 거리 / 정렬 / 검색.
	import { PRESETS, type PeriodPreset } from '$lib/activityFilters';
	import type { ActivityFacets } from '$lib/types';
	import ToggleGroup from '$lib/components/ui/ToggleGroup.svelte';

	let {
		facets,
		preset,
		month,
		months,
		sport,
		type,
		distMin,
		sort,
		q = $bindable(),
		onpreset,
		onmonth,
		onpick,
		onsearch
	}: {
		facets: ActivityFacets | null;
		preset: PeriodPreset | null;
		month: string;
		months: string[];
		sport: string;
		type: string;
		distMin: string;
		sort: string;
		q: string;
		onpreset: (p: PeriodPreset) => void;
		onmonth: (m: string) => void;
		onpick: (kind: 'sport' | 'type' | 'dist' | 'sort', value: string) => void;
		onsearch: () => void;
	} = $props();

	const DISTS = [['', '전 거리'], ['5', '5km+'], ['10', '10km+'], ['21.1', '하프+'], ['42.2', '풀']] as const;
	const SORTS = [['date', '최신순'], ['distance', '거리순'], ['pace', '페이스순'], ['load', '부하순']] as const;
	const monthLabel = (m: string) => `${m.slice(0, 4)}년 ${Number(m.slice(5))}월`;
	const chip = (on: boolean) =>
		`inline-flex min-h-11 items-center rounded-full border px-3 py-1 text-xs ${on ? 'border-semantic-teal bg-semantic-teal/15 text-fg-primary' : 'border-border-subtle text-fg-muted hover:text-fg-secondary'}`;
	const sports = $derived(facets?.sports.length ? facets.sports : [{ key: 'running', label: '러닝', n: 0 }]);
</script>

<div class="flex flex-wrap items-center gap-1.5 px-4 pt-3">
	<ToggleGroup
		label="기간"
		class="flex flex-wrap gap-1.5"
		items={PRESETS.map(([v, l]) => ({ value: v, label: l }))}
		selected={preset}
		onchange={(v) => v && onpreset(v as PeriodPreset)}
	/>
	<select aria-label="월 선택" value={month} onchange={(e) => onmonth(e.currentTarget.value)} class="{chip(!!month)} bg-transparent">
		<option value="">월 선택</option>
		{#each months as m (m)}<option value={m}>{monthLabel(m)}</option>{/each}
	</select>
</div>

<div class="flex flex-col gap-2 border-b border-border-subtle px-4 py-3">
	<ToggleGroup
		label="종목"
		class="flex flex-wrap gap-1.5"
		items={[{ value: '', label: '전체' }, ...sports.map((s) => ({ value: s.key, label: `${s.label}${s.n ? ` ${s.n}` : ''}` }))]}
		selected={sport}
		onchange={(v) => onpick('sport', (v as string) ?? '')}
	/>
	{#if facets?.types.length}
		<ToggleGroup
			label="유형"
			class="flex flex-wrap gap-1.5"
			items={[{ value: '', label: '전 유형' }, ...facets.types.map((t) => ({ value: t.key, label: `${t.label} ${t.n}` }))]}
			selected={type}
			onchange={(v) => onpick('type', (v as string) ?? '')}
		/>
	{/if}
	<ToggleGroup
		label="거리"
		class="flex flex-wrap gap-1.5"
		items={DISTS.map(([v, l]) => ({ value: v, label: l }))}
		selected={distMin}
		onchange={(v) => onpick('dist', (v as string) ?? '')}
	/>
	<div class="flex gap-2">
		<input
			type="search"
			bind:value={q}
			oninput={onsearch}
			placeholder="활동 이름 검색"
			class="min-w-0 flex-1 min-h-11 rounded-lg border border-border-subtle bg-surface-2 px-3 py-2 text-sm text-fg-primary placeholder:text-fg-muted"
			aria-label="활동 검색"
		/>
		<select
			aria-label="정렬"
			value={sort || 'date'}
			onchange={(e) => onpick('sort', e.currentTarget.value === 'date' ? '' : e.currentTarget.value)}
			class="rounded-lg border border-border-subtle bg-surface-2 px-2 py-2 text-xs text-fg-secondary"
		>
			{#each SORTS as [v, label] (v)}<option value={v}>{label}</option>{/each}
		</select>
	</div>
</div>
