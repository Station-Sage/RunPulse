<script lang="ts">
	// x.taper — 레이스 아침 폼 시나리오 비교(표 + TSB 투영 미니 차트). 값·등급은 서버(race-hub projection) 그대로.
	import { onMount } from 'svelte';
	import { base } from '$app/paths';
	import { replaceState } from '$app/navigation';
	import { page } from '$app/state';
	import { getRaceHub } from '$lib/api/today';
	import { signedTsb } from '$lib/raceHub';
	import type { RaceProjection } from '$lib/types';
	import TrendChart from '$lib/components/TrendChart.svelte';

	const TONE: Record<string, string> = {
		excellent: 'text-semantic-green',
		good: 'text-semantic-teal',
		neutral: 'text-fg-secondary',
		caution: 'text-semantic-amber',
		poor: 'text-semantic-red'
	};

	let proj = $state<RaceProjection | null>(null);
	let loading = $state(true);
	let failed = $state(false);

	onMount(() => {
		getRaceHub()
			.then((h) => (proj = h.projection))
			.catch(() => (failed = true))
			.finally(() => (loading = false));
	});

	const scenarios = $derived(proj?.scenarios ?? []);
	let picked = $state(page.url.searchParams.get('scn'));
	const selKey = $derived(picked ?? scenarios[0]?.key ?? '');
	const cur = $derived(scenarios.find((s) => s.key === selKey) ?? scenarios[0] ?? null);
	const series = $derived(cur ? [{ key: cur.key, label: cur.label, color: 'var(--color-status-good)', points: cur.series }] : []);

	function select(key: string) {
		picked = key;
		const url = new URL(page.url);
		url.searchParams.set('scn', key);
		replaceState(url, page.state);
	}

	const pct = (v: number | null | undefined) => (v == null ? '–' : `${v > 0 ? '+' : v < 0 ? '−' : ''}${Math.abs(v)}%`);
</script>

<div class="flex flex-col gap-3 p-4" data-testid="taper-sheet">
	{#if loading}
		<p class="text-sm text-fg-muted">불러오는 중…</p>
	{:else if failed}
		<p class="text-sm text-fg-secondary">불러오지 못했어요. 잠시 후 다시 시도해 주세요.</p>
	{:else if !proj || !cur}
		<p class="text-sm text-fg-secondary">예측할 목표 레이스나 데이터가 아직 없어요 · 데이터 수집 중</p>
	{:else}
		<p class="text-sm font-semibold">
			레이스 아침 폼 — {cur.label} <span class={TONE[cur.status ?? 'neutral']}>{signedTsb(cur.tsb)} · {cur.status_label ?? ''}</span>
		</p>
		<table class="w-full text-left text-xs">
			<thead class="text-fg-muted">
				<tr><th class="py-1 font-normal">시나리오</th><th class="font-normal">아침 TSB</th><th class="font-normal">CTL 변화</th></tr>
			</thead>
			<tbody>
				{#each scenarios as sc (sc.key)}
					<tr
						class="cursor-pointer border-t border-border-subtle {sc.key === cur.key ? 'bg-surface-2' : ''}"
						data-testid="scn-{sc.key}"
						onclick={() => select(sc.key)}
					>
						<td class="py-1.5">{sc.label}</td>
						<td class="font-mono {TONE[sc.status ?? 'neutral']}">{signedTsb(sc.tsb)} · {sc.status_label ?? ''}</td>
						<td class="font-mono text-fg-secondary">{pct(sc.ctl_change_pct)}</td>
					</tr>
				{/each}
			</tbody>
		</table>
		<TrendChart {series} height={110} name="TSB 투영" formatValue={(v) => signedTsb(v)} />
		<p class="text-[10px] leading-tight text-fg-muted">{proj.assumptions} · 현재 폼 {signedTsb(proj.current.tsb)}</p>
		<a href="{base}/today/race" class="self-start text-sm font-medium text-semantic-teal hover:underline">레이스 허브에서 자세히 ›</a>
	{/if}
</div>
