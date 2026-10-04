<script lang="ts">
	// 쌍 목록(S6) — 날짜·활동·소스별 값·차이. 활동 쌍이면 활동 상세로 링크.
	import type { ProviderPairsData } from '$lib/types';
	import { formatMetric, formatDistance } from '$lib/format';
	import { providerName } from '$lib/providerMatrix';
	import { base } from '$app/paths';

	let { data }: { data: ProviderPairsData } = $props();

	const meta = $derived({
		format: undefined,
		unit: data.row.unit ?? '',
		decimal_places: data.row.format === 'int' ? 0 : Number(/\d/.exec(data.row.format)?.[0] ?? 1)
	});
	const diffText = (p: ProviderPairsData['pairs'][number]) =>
		p.ratio != null ? `×${p.ratio.toFixed(2)}` : p.diff_pct != null ? `${p.diff_pct > 0 ? '+' : ''}${p.diff_pct.toFixed(0)}%` : '';
</script>

<ul class="divide-y divide-border-subtle">
	{#each data.pairs as p (p.date + (p.canonical_id ?? ''))}
		<li class="px-4 py-2 text-xs">
			<div class="flex items-baseline justify-between gap-2">
				{#if p.canonical_id}
					<a href="{base}/library/{p.canonical_id}?from=providers" class="truncate font-medium text-fg-primary underline">{p.date} · {p.name ?? '러닝'}</a>
				{:else}
					<span class="font-medium text-fg-primary">{p.date}</span>
				{/if}
				<span class="shrink-0 tabular-nums {p.outlier ? 'text-semantic-amber' : 'text-fg-secondary'}">{diffText(p)}{p.outlier ? ' · 이상치' : ''}</span>
			</div>
			<div class="mt-0.5 flex flex-wrap gap-x-3 text-fg-muted">
				{#if p.distance_m}<span>{formatDistance(p.distance_m)}</span>{/if}
				{#each Object.entries(p.values) as [prov, v]}
					<span>{providerName(prov)} {formatMetric(meta, v)}</span>
				{/each}
			</div>
		</li>
	{/each}
</ul>
