<script lang="ts">
	// Training Balance 표 — 레이더와 같은 정보를 항상 보이게 렌더링(접근성 대안, 토글로 숨기지 않음). 설계 §7.
	// compact=true(브라우저 카드)는 레이더에 그려진 정보(축·점수·상태)만 보여 준다.
	import type { TrainingBalance } from '$lib/types/trainingBalance';
	import { noteTexts, tableRows } from '$lib/balanceView';

	let { data, compact = false }: { data: TrainingBalance; compact?: boolean } = $props();

	const rows = $derived(tableRows(data));
	const notes = $derived(compact ? [] : noteTexts(data));
	const fmt = (v: number | null, d = 1) => (v == null ? '—' : v.toFixed(d));
</script>

<div class="w-full overflow-x-auto">
	<table class="w-full border-collapse text-left text-xs" data-testid="balance-table">
		<caption class="pb-1 text-left text-xs text-fg-muted">
			훈련 균형 {data.as_of} 기준 · 최근 {data.window_weeks}주 · 점수 100 = 목표 도달{#if !compact && data.compare}{' · '}28일 전 = {data.compare.as_of}{/if}
		</caption>
		<thead>
			<tr class="whitespace-nowrap border-b border-border-subtle text-fg-muted">
				<th scope="col" class="py-1.5 pr-2 font-medium">축</th>
				{#if !compact}
					<th scope="col" class="py-1.5 pr-2 font-medium">현재</th>
					<th scope="col" class="py-1.5 pr-2 font-medium">목표 (기준)</th>
				{/if}
				<th scope="col" class="py-1.5 pr-2 text-right font-medium">점수</th>
				<th scope="col" class="py-1.5 pr-2 font-medium">상태</th>
				{#if !compact && data.compare}
					<th scope="col" class="whitespace-nowrap py-1.5 text-right font-medium">28일 전</th>
				{/if}
			</tr>
		</thead>
		<tbody>
			{#each rows as r (r.key)}
				<tr class="border-b border-border-subtle align-top">
					<th scope="row" class="whitespace-nowrap py-1.5 pr-2 font-medium text-fg-primary">{r.label}</th>
					{#if !compact}
						<td class="whitespace-nowrap py-1.5 pr-2 font-mono text-fg-primary">{r.actual}</td>
						<td class="py-1.5 pr-2 text-fg-secondary"><span class="whitespace-nowrap font-mono">{r.target}</span><span class="block whitespace-nowrap text-fg-muted">{r.basis}</span></td>
					{/if}
					<td class="whitespace-nowrap py-1.5 pr-2 text-right font-mono text-fg-primary">{r.score}</td>
					<td class="py-1.5 pr-2">
						<span class="whitespace-nowrap {r.statusClass}">{#if r.mark}<span aria-hidden="true">{r.mark} </span>{/if}{r.status}</span>
						{#if r.reason && !compact}<span class="block text-fg-muted">{r.reason}</span>{/if}
						{#if r.stale}<span class="block text-fg-muted">{data.stale_text}</span>{/if}
					</td>
					{#if !compact && data.compare}
						<td class="py-1.5 text-right font-mono text-fg-secondary">{r.compare}</td>
					{/if}
				</tr>
			{/each}
		</tbody>
	</table>
	{#if !compact}
		<dl class="mt-3 grid grid-cols-2 gap-x-4 gap-y-1 text-xs sm:grid-cols-4" data-testid="balance-aux">
			<div><dt class="text-fg-muted">TSB</dt><dd class="font-mono text-fg-primary">{fmt(data.aux.tsb)}</dd></div>
			<div><dt class="text-fg-muted">단조로움</dt><dd class="font-mono text-fg-primary">{fmt(data.aux.monotony, 2)}</dd></div>
			<div><dt class="text-fg-muted">Tanda 필요 볼륨</dt><dd class="font-mono text-fg-primary">{fmt(data.aux.tanda_required_km)}{#if data.aux.tanda_required_km != null}{' km/주'}{/if}</dd></div>
			<div><dt class="text-fg-muted">강도 분포 패턴</dt><dd class="text-fg-primary">{data.aux.tids_pattern ?? '—'}</dd></div>
		</dl>
		{#if notes.length}
			<ul class="mt-3 flex list-disc flex-col gap-1 pl-4 text-xs text-fg-muted" data-testid="balance-notes">
				{#each notes as t (t)}<li>{t}</li>{/each}
			</ul>
		{/if}
	{/if}
</div>
