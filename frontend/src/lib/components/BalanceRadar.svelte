<script lang="ts">
	// Training Balance 레이더(순수 SVG) — 현재(실선)·28일 전(점선)·100 기준 링·균형 구간 음영. 기하: $lib/chart/radar.
	// SVG 에는 표(BalanceTable)에 없는 정보를 넣지 않는다 — 스크린리더는 표로 읽는다(설계 §7).
	import type { BalanceAxis, TrainingBalance } from '$lib/types/trainingBalance';
	import { SCORE_MAX, labelAnchor, markerPath, polar, radarShape, ringPoints, shapePoints } from '$lib/chart/radar';
	import { COLLECTING, formatScore, summarySentence } from '$lib/balanceView';

	let {
		data,
		compact = false,
		id = 'balance-radar'
	}: { data: TrainingBalance; compact?: boolean; id?: string } = $props();

	const R = 100;
	const axes = $derived<BalanceAxis[]>(data.axes);
	const n = $derived(axes.length);
	const cur = $derived(radarShape(axes.map((a) => a.score), R));
	const prevScores = $derived(
		axes.map((a) => data.compare?.axes.find((c) => c.key === a.key)?.score ?? null)
	);
	const prev = $derived(compact || !data.compare ? null : radarShape(prevScores, R));
	const bandPath = $derived(
		`M${shapePoints(axes.map((a) => a.band[1]), R)} Z M${shapePoints(axes.map((a) => a.band[0]), R)} Z`
	);
	const summary = $derived(summarySentence(axes));
	const STATUS_FILL: Record<string, string> = {
		low: 'var(--color-status-caution)',
		high: 'var(--color-status-caution)',
		balanced: 'var(--color-status-good)'
	};
</script>

<figure class="flex flex-col items-center gap-1">
	<svg
		viewBox="-185 -155 370 310"
		class={compact ? 'w-full max-w-[260px]' : 'w-full max-w-[420px]'}
		role="img"
		aria-labelledby="{id}-title {id}-desc"
	>
		<title id="{id}-title">훈련 균형 레이더</title>
		<desc id="{id}-desc">{summary}. 자세한 값은 아래 표에 있어요.</desc>
		<path d={bandPath} fill="var(--color-status-good)" fill-opacity="0.12" fill-rule="evenodd" />
		{#each [50, 150] as lv (lv)}
			<polygon points={ringPoints(lv, n, R)} fill="none" stroke="var(--color-border-subtle)" stroke-width="1" />
		{/each}
		<polygon points={ringPoints(100, n, R)} fill="none" stroke="var(--color-border-strong)" stroke-width="1.5" />
		{#each axes as _, i (i)}
			{@const end = polar(i, n, R)}
			<line x1="0" y1="0" x2={end.x} y2={end.y} stroke="var(--color-border-subtle)" stroke-width="1" />
		{/each}
		{#if prev}
			{#each [...prev.solid, ...prev.dashed] as [a, b], k (k)}
				<line x1={a.x} y1={a.y} x2={b.x} y2={b.y} stroke="var(--color-series-2)" stroke-width="1.5" stroke-dasharray="4 3" />
			{/each}
		{/if}
		{#if cur.fill}
			<polygon points={cur.fill} fill="var(--color-series-1)" fill-opacity="0.18" stroke="none" />
		{/if}
		{#each cur.solid as [a, b], k (k)}
			<line x1={a.x} y1={a.y} x2={b.x} y2={b.y} stroke="var(--color-series-1)" stroke-width="2" />
		{/each}
		{#each cur.dashed as [a, b], k (k)}
			<line x1={a.x} y1={a.y} x2={b.x} y2={b.y} stroke="var(--color-series-1)" stroke-width="1.5" stroke-dasharray="2 4" />
		{/each}
		{#each axes as a, i (a.key)}
			{@const v = cur.vertices[i]}
			{@const lab = labelAnchor(i, n, R, 12)}
			{@const gap = compact ? 16 : 14}
			{@const dy = lab.y < -R / 2 ? -gap : gap}
			{#if v}
				{@const mp = markerPath(v, a.status, 5)}
				{#if mp}
					<path d={mp} fill={STATUS_FILL[a.status ?? 'balanced']} />
				{:else}
					<circle cx={v.x} cy={v.y} r="3.5" fill={STATUS_FILL.balanced} />
				{/if}
			{/if}
			<text x={lab.x} y={lab.y} text-anchor={lab.anchor} dominant-baseline="middle" class="fill-fg-secondary" font-size={compact ? 15 : 12}>
				{a.label}
			</text>
			<text x={lab.x} y={lab.y + dy} text-anchor={lab.anchor} dominant-baseline="middle" class={a.score == null ? 'fill-fg-muted' : 'fill-fg-primary'} font-size={compact ? 14 : 11}>
				{a.score == null ? COLLECTING : formatScore(a.score)}
			</text>
		{/each}
	</svg>
	<figcaption class="text-center text-sm text-fg-secondary" data-testid="balance-summary">
		{summary}
		{#if !compact}
			<span class="mt-0.5 block text-xs text-fg-muted">
				굵은 링 = 목표 100 · 음영 = 균형 구간 · 실선 = 현재{#if prev}{' · '}긴 점선 = 28일 전({data.compare?.as_of}){/if}{' · '}▲ 과다 ▼ 부족 (최대 {SCORE_MAX})
			</span>
		{/if}
	</figcaption>
</figure>
