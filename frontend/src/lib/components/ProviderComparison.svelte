<script lang="ts">
	// C4 ProviderComparison — 04-component-catalog.md 기준.
	// 활동 그룹 내 소스별 메트릭 비교 테이블. 불일치 감지 + 대표값(★) 표시.
	import { providerLabel, providerLabelCompact, providerBadgeClass } from '$lib/provider';
	import { formatUnitValue } from '$lib/format';
	import Icon from '$lib/components/Icon.svelte';
	import type { ProviderComparisonData, ComparisonRow, ProviderKey } from '$lib/types';

	let {
		data,
		loading = false,
		error = null,
		discrepancyThreshold = 5,
		showPrimaryReason = false
	}: {
		data: ProviderComparisonData | null;
		loading?: boolean;
		error?: string | null;
		discrepancyThreshold?: number;
		showPrimaryReason?: boolean;
		ondrill?: (slug: string) => void;
	} = $props();

	// 실제 데이터가 있는 provider 열만 추출 (순서 유지)
	const providers = $derived((): string[] => {
		if (!data || data.rows.length === 0) return [];
		const seen = new Set<string>();
		for (const row of data.rows) {
			for (const [p, cell] of Object.entries(row.values)) {
				if (cell.available) seen.add(p);
			}
		}
		// 원래 순서(API가 정렬해서 내려줌)를 유지하기 위해 첫 행 키 순서 기준
		const firstRowKeys = data.rows[0] ? Object.keys(data.rows[0].values) : [];
		return firstRowKeys.filter((p) => seen.has(p));
	});

	// 불일치 행 여부
	function hasDiscrepancy(row: ComparisonRow): boolean {
		return row.discrepancy?.detected === true;
	}

	function cellDisplayValue(row: ComparisonRow, provider: string): string {
		const cell = row.values[provider];
		if (!cell || !cell.available) return '—';
		const v = cell.value;
		if (v == null) return '—';
		if (typeof v === 'number') {
			const effectiveUnit =
				row.unit === 'sec/km' || row.slug.includes('pace') ? 'sec/km' : (row.unit ?? '');
			return formatUnitValue(v, effectiveUnit).display;
		}
		return String(v);
	}

	// 변환 후 단위 — 첫 번째 사용 가능한 값으로 결정 (m→km 등)
	function rowDisplayUnit(row: ComparisonRow): string {
		if (!row.unit) return '';
		if (row.unit === 'sec/km' || row.slug.includes('pace')) return '';
		const firstVal = Object.values(row.values).find(
			(c) => c.available && typeof c.value === 'number'
		)?.value;
		if (typeof firstVal === 'number') {
			return formatUnitValue(firstVal, row.unit).unit;
		}
		if (row.unit === 'sec') return '';
		return row.unit;
	}

	function isPrimary(row: ComparisonRow, provider: string): boolean {
		return row.preferredProvider === provider;
	}
</script>

{#if loading}
	<!-- 스켈레톤 -->
	<div class="flex flex-col gap-2 px-4 py-4">
		{#each Array(4) as _}
			<div class="h-10 animate-pulse rounded-md bg-surface-2"></div>
		{/each}
	</div>
{:else if error}
	<div class="px-4 py-6 text-center text-sm text-fg-secondary">{error}</div>
{:else if !data}
	<div class="px-4 py-6 text-center text-sm text-fg-muted">데이터 없음</div>
{:else if data.state === 'single_provider'}
	<div class="px-4 py-8 text-center">
		<p class="text-sm text-fg-secondary">비교할 추가 소스가 없습니다.</p>
		<p class="mt-1 text-xs text-fg-muted">이 활동은 단일 소스에서만 기록되었습니다.</p>
	</div>
{:else}
	<!-- 비교 테이블 -->
	<div class="overflow-x-auto">
		<table class="w-full text-sm">
			<thead>
				<tr class="border-b border-border-subtle">
					<th class="py-2 pl-4 pr-2 text-left text-xs font-medium uppercase tracking-wide text-fg-muted">
						메트릭
					</th>
					{#each providers() as provider}
						<th class="px-2 py-2 text-center text-xs font-medium tracking-wide text-fg-muted">
							<span class="rounded px-1.5 py-0.5 text-[10px] text-white {providerBadgeClass(provider as ProviderKey)}">
								{providerLabelCompact(provider as ProviderKey)}
							</span>
						</th>
					{/each}
				</tr>
			</thead>
			<tbody>
				{#each data.rows as row (row.slug)}
					<tr
						class="border-b border-border-subtle last:border-0 {hasDiscrepancy(row)
							? 'bg-amber-500/5'
							: ''}"
					>
						<!-- 메트릭 이름 -->
						<td class="py-2.5 pl-4 pr-2">
							<div class="flex items-center gap-1.5">
								<span class="text-sm">{row.label}</span>
								{#if hasDiscrepancy(row)}
									<span
										class="text-semantic-amber"
										title="불일치 {row.discrepancy?.maxDiffPct?.toFixed(1)}%"
									><Icon name="warning" class="h-3.5 w-3.5" /></span>
								{/if}
							</div>
							{#if rowDisplayUnit(row)}
								<span class="text-[10px] text-fg-muted">{rowDisplayUnit(row)}</span>
							{/if}
						</td>

						<!-- 각 provider 값 — 대표 소스 셀에 ★ 표시 + primaryReason을 title로 -->
						{#each providers() as provider}
							<td
								class="px-2 py-2.5 text-center"
								title={isPrimary(row, provider) && showPrimaryReason && row.primaryReason
									? row.primaryReason.rule
									: undefined}
							>
								<span
									class="font-mono text-sm {row.values[provider]?.available
										? 'text-fg-primary'
										: 'text-fg-muted'}"
								>
									{#if isPrimary(row, provider)}<Icon name="source-primary" class="inline h-3 w-3 text-amber-500 align-baseline" /> {/if}{cellDisplayValue(row, provider)}
								</span>
							</td>
						{/each}
					</tr>
				{/each}
			</tbody>
		</table>
	</div>

	<div class="mt-2 px-4 text-xs text-fg-muted"><Icon name="source-primary" class="inline h-3 w-3 text-amber-500 align-baseline" /> 대표값(우선 소스)</div>

	<!-- 불일치 범례 -->
	{#if data.rows.some((r) => hasDiscrepancy(r))}
		<div class="mt-2 px-4 pb-2 text-xs text-fg-muted">
			<Icon name="warning" class="inline h-3.5 w-3.5 text-semantic-amber align-baseline" /> 소스 간 실제 측정 차이(고도 10m·기온 2°C·시간·거리 1%·기타 {discrepancyThreshold}% 초과)
		</div>
	{/if}
{/if}
