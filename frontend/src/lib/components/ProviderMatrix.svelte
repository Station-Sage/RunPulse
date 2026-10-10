<script lang="ts">
	// 소스 비교 매트릭스(S6) — 섹션별 행 × 소스 열. 판정(status)·문구는 서버가 만든 값을 그대로 표시.
	import type { ProviderMatrixData } from '$lib/types';
	import { cellText, providerName, rowHref, visibleProviders } from '$lib/providerMatrix';
	import { base } from '$app/paths';

	let { data }: { data: ProviderMatrixData } = $props();

	const TONE: Record<string, string> = {
		differs: 'text-semantic-amber',
		similar: 'text-fg-muted',
		scale: 'text-fg-secondary',
		insufficient: 'text-fg-muted'
	};
</script>

<p class="px-4 pt-3 text-xs text-fg-muted">{data.header_text}</p>
<p class="px-4 pb-2 text-xs text-fg-muted">{data.caption}</p>

{#each data.sections as section (section.key)}
	{@const cols = visibleProviders(data.providers, section.rows)}
	<section class="px-4 pb-4" aria-label={section.label}>
		<h2 class="py-2 text-sm font-semibold">{section.label}</h2>
		<div class="overflow-x-auto rounded-lg border border-border-subtle">
			<table class="w-full text-left text-xs">
				<thead class="bg-surface-2 text-fg-muted">
					<tr>
						<th class="sticky left-0 z-10 bg-surface-2 px-3 py-2 font-medium">지표</th>
						{#each cols as p}<th class="px-3 py-2 font-medium">{providerName(p)}</th>{/each}
						<th class="sticky right-0 z-10 bg-surface-2 px-3 py-2 font-medium shadow-[-6px_0_6px_-6px_rgba(0,0,0,0.25)]">차이</th>
					</tr>
				</thead>
				<tbody>
					{#each section.rows as row (row.key)}
						{@const href = rowHref(base, row, data.days)}
						<tr class="border-t border-border-subtle align-top">
							<th scope="row" class="sticky left-0 z-10 bg-surface-1 px-3 py-2 font-medium text-fg-primary">
								{row.label}{#if row.unit}<span class="ml-1 text-fg-muted">({row.unit})</span>{/if}
							</th>
							{#each cols as p}
								{@const t = cellText(row, row.cells[p])}
								<td class="px-3 py-2">
									<span class="tabular-nums text-fg-primary">{t.main}</span>
									{#if row.preferred?.provider === p}<span class="text-semantic-teal" title={row.preferred.reason_text} aria-label="기본 소스">★</span>{/if}
									{#if t.note}<span class="block text-fg-muted">{t.note}</span>{/if}
									{#if row.definitions[p]}<span class="block text-fg-muted">{row.definitions[p]}</span>{/if}
								</td>
							{/each}
							<td class="px-3 py-2">
								{#if row.diff}
									{#if href}
										<a {href} class="underline {TONE[row.diff.status]}">{row.diff.status_label}</a>
									{:else}
										<span class={TONE[row.diff.status]}>{row.diff.status_label}</span>
									{/if}
									<span class="block text-fg-muted">{row.diff.label} · {row.diff.n}건</span>
								{:else}
									<span class="text-fg-muted">비교 안 함</span>
								{/if}
							</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
	</section>
{/each}

{#if data.single_source.length}
	<details class="px-4 pb-6">
		<summary class="cursor-pointer text-xs text-fg-secondary">비교 상대가 없는 지표 {data.single_source.length}개 ›</summary>
		<ul class="mt-2 space-y-1 text-xs text-fg-muted">
			{#each data.single_source as s (s.key)}
				{@const t = cellText(s, s.cell)}
				<li>{s.label} · {s.provider_label} {t.main}{t.note ? ` (${t.note})` : ''}</li>
			{/each}
		</ul>
	</details>
{/if}
