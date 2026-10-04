<script lang="ts">
	// 활동 목록 필터 — 기간 프리셋·월 / 종목·유형(facets 건수 칩) / 거리 / 정렬 / 검색.
	import { PRESETS, type PeriodPreset } from '$lib/activityFilters';
	import type { ActivityFacets } from '$lib/types';

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
		`rounded-full border px-3 py-1 text-xs ${on ? 'border-semantic-teal bg-semantic-teal/15 text-fg-primary' : 'border-border-subtle text-fg-muted hover:text-fg-secondary'}`;
	const sports = $derived(facets?.sports.length ? facets.sports : [{ key: 'running', label: '러닝', n: 0 }]);
</script>

<div class="flex flex-wrap items-center gap-1.5 px-4 pt-3" role="group" aria-label="기간">
	{#each PRESETS as [v, label] (v)}
		<button type="button" aria-pressed={preset === v} onclick={() => onpreset(v)} class={chip(preset === v)}>{label}</button>
	{/each}
	<select aria-label="월 선택" value={month} onchange={(e) => onmonth(e.currentTarget.value)} class="{chip(!!month)} bg-transparent">
		<option value="">월 선택</option>
		{#each months as m (m)}<option value={m}>{monthLabel(m)}</option>{/each}
	</select>
</div>

<div class="flex flex-col gap-2 border-b border-border-subtle px-4 py-3">
	<div class="flex flex-wrap gap-1.5" role="group" aria-label="종목">
		<button type="button" aria-pressed={sport === ''} onclick={() => onpick('sport', '')} class={chip(sport === '')}>전체</button>
		{#each sports as s (s.key)}
			<button type="button" aria-pressed={sport === s.key} onclick={() => onpick('sport', s.key)} class={chip(sport === s.key)}
				>{s.label}{s.n ? ` ${s.n}` : ''}</button
			>
		{/each}
	</div>
	{#if facets?.types.length}
		<div class="flex flex-wrap gap-1.5" role="group" aria-label="유형">
			<button type="button" aria-pressed={type === ''} onclick={() => onpick('type', '')} class={chip(type === '')}>전 유형</button>
			{#each facets.types as t (t.key)}
				<button type="button" aria-pressed={type === t.key} onclick={() => onpick('type', t.key)} class={chip(type === t.key)}
					>{t.label} {t.n}</button
				>
			{/each}
		</div>
	{/if}
	<div class="flex flex-wrap gap-1.5" role="group" aria-label="거리">
		{#each DISTS as [v, label] (v)}
			<button type="button" aria-pressed={distMin === v} onclick={() => onpick('dist', v)} class={chip(distMin === v)}>{label}</button>
		{/each}
	</div>
	<div class="flex gap-2">
		<input
			type="search"
			bind:value={q}
			oninput={onsearch}
			placeholder="활동 이름 검색"
			class="min-w-0 flex-1 rounded-lg border border-border-subtle bg-surface-2 px-3 py-2 text-sm text-fg-primary placeholder:text-fg-muted"
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
