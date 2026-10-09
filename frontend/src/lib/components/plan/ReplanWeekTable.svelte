<script lang="ts">
	import { collapseWeeks, deltaText, type MergedWeek } from '$lib/replanView';

	let { rows }: { rows: MergedWeek[] } = $props();
	let expanded = $state(false);
	const view = $derived(collapseWeeks(rows, 4, expanded));
	const km = (v: number | null) => (v == null ? '—' : String(Math.round(v)));
</script>

<table class="w-full text-xs tabular-nums text-fg-secondary">
	<thead>
		<tr class="text-left"><th class="py-1 font-normal">주</th><th class="font-normal">전 → 후</th><th class="text-right font-normal">차이</th></tr>
	</thead>
	<tbody>
		{#each view.shown as r (r.week_start)}
			<tr>
				<td class="py-1">{r.label}{r.isRace ? ' · 대회 주' : ''}</td>
				<td>{km(r.before)} → {km(r.after)}km</td>
				<td class="text-right">{deltaText(r.delta)}</td>
			</tr>
		{/each}
	</tbody>
</table>
{#if view.hiddenCount > 0}
	<button class="min-h-11 text-xs text-fg-secondary underline" onclick={() => (expanded = true)}>나머지 {view.hiddenCount}주 보기</button>
{/if}
