<script lang="ts">
	// 03c-library.md 3-G-1 — Provider 정체성 매트릭스 (기본 뷰).
	import type { ProvidersPageData } from './+page';
	import { providerLabel, providerBadgeClass } from '$lib/provider';
	import { goto } from '$app/navigation';
	import { base } from '$app/paths';
	import type { ProviderKey, MatrixRow } from '$lib/types';

	let { data }: { data: ProvidersPageData } = $props();

	const PERIODS = [
		{ key: 28, label: '최근 4주' },
		{ key: 90, label: '3개월' },
		{ key: 180, label: '6개월' }
	];

	function selectPeriod(days: number) {
		goto(`?period=${days}`);
	}

	function cellDisplay(row: MatrixRow, provider: string): string {
		const cell = row.values[provider];
		if (!cell || !cell.available) return '—';
		const v = cell.value;
		if (v == null) return '—';
		if (typeof v === 'number') {
			if (row.unit === 'sec/km' || row.slug.includes('pace')) {
				const total = Math.round(v);
				const min = Math.floor(total / 60);
				const sec = total % 60;
				return `${min}:${String(sec).padStart(2, '0')}`;
			}
			return Number.isInteger(v) ? String(v) : v.toFixed(1);
		}
		return String(v);
	}

	function hasDiscrepancy(row: MatrixRow): boolean {
		return row.discrepancy?.detected === true;
	}
</script>

<!-- 섹션 탭 (Library 홈과 동일 구조) -->
<nav class="flex border-b border-border-subtle">
	<a href="{base}/library" class="flex-1 py-3 text-center text-sm text-fg-muted hover:text-fg-secondary">
		활동
	</a>
	<a href="{base}/library/metrics" class="flex-1 py-3 text-center text-sm text-fg-muted hover:text-fg-secondary">
		메트릭
	</a>
	<a href="{base}/library/wellness" class="flex-1 py-3 text-center text-sm text-fg-muted hover:text-fg-secondary">
		웰니스
	</a>
	<a
		href="{base}/library/providers"
		class="flex-1 border-b-2 border-fg-primary py-3 text-center text-sm font-medium text-fg-primary"
		aria-current="page"
	>
		Provider 비교
	</a>
</nav>

<div class="px-4 py-3">
	<!-- 기간 선택 -->
	<div class="mb-4 flex items-center gap-2">
		<span class="text-xs text-fg-muted">기간:</span>
		{#each PERIODS as p}
			<button
				class="rounded-full border px-3 py-1 text-xs {data.periodDays === p.key
					? 'border-fg-primary bg-surface-2 font-medium text-fg-primary'
					: 'border-border-subtle text-fg-muted hover:border-fg-secondary hover:text-fg-secondary'}"
				onclick={() => selectPeriod(p.key)}
			>
				{p.label}
			</button>
		{/each}
	</div>

	{#if data.error}
		<div class="py-8 text-center text-sm text-fg-secondary">{data.error}</div>
	{:else if !data.matrix || data.matrix.groups.length === 0}
		<div class="py-8 text-center text-sm text-fg-muted">데이터 없음 — 먼저 동기화를 실행하세요.</div>
	{:else}
		<!-- 불일치 요약 -->
		{#if data.matrix.discrepancy_count > 0}
			<div class="mb-3 rounded-lg border border-amber-500/30 bg-amber-500/5 px-3 py-2 text-xs text-amber-600">
				⚠ {data.matrix.discrepancy_count}개 메트릭에서 소스 간 불일치 감지됨
			</div>
		{/if}

		<!-- 매트릭스 테이블 -->
		<div class="overflow-x-auto">
			<table class="w-full min-w-[480px] text-sm">
				<thead>
					<tr class="border-b border-border-subtle">
						<th class="py-2 pl-2 pr-2 text-left text-xs font-medium uppercase tracking-wide text-fg-muted">
							시맨틱 그룹 / 메트릭
						</th>
						{#each data.matrix.providers as provider}
							<th class="px-2 py-2 text-center text-xs font-medium tracking-wide text-fg-muted">
								<span class="rounded px-1.5 py-0.5 text-[10px] text-white {providerBadgeClass(provider as ProviderKey)}">
									{providerLabel(provider as ProviderKey)}
								</span>
							</th>
						{/each}
						<th class="py-2 pl-2 pr-2 text-right text-xs font-medium uppercase tracking-wide text-fg-muted">
							대표값
						</th>
					</tr>
				</thead>
				<tbody>
					{#each data.matrix.groups as group (group.key)}
						<!-- 그룹 헤더 -->
						<tr class="border-b border-border-subtle bg-surface-2/50">
							<td
								colspan={data.matrix.providers.length + 2}
								class="py-1.5 pl-2 text-xs font-semibold uppercase tracking-wide text-fg-muted"
							>
								{group.label}
							</td>
						</tr>

						<!-- 메트릭 행 -->
						{#each group.rows as row (row.slug)}
							<tr
								class="border-b border-border-subtle last:border-0 {hasDiscrepancy(row)
									? 'bg-amber-500/5'
									: ''}"
							>
								<td class="py-2 pl-4 pr-2">
									<div class="flex items-center gap-1">
										<span class="text-xs text-fg-secondary">{row.label}</span>
										{#if hasDiscrepancy(row)}
											<span
												class="text-[10px] text-amber-500"
												title="불일치 {row.discrepancy?.maxDiffPct?.toFixed(1)}%"
											>⚠</span>
										{/if}
									</div>
									{#if row.unit && row.unit !== 'sec/km'}
										<span class="text-[10px] text-fg-muted">{row.unit}</span>
									{/if}
								</td>

								{#each data.matrix.providers as provider}
									<td class="px-2 py-2 text-center">
										<span
											class="font-mono text-xs {row.values[provider]?.available
												? 'text-fg-primary'
												: 'text-fg-muted'}"
										>
											{cellDisplay(row, provider)}
										</span>
									</td>
								{/each}

								<!-- 대표값 -->
								<td class="py-2 pl-2 pr-2 text-right">
									{#if row.preferredProvider}
										<span
											class="inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] text-white {providerBadgeClass(row.preferredProvider as ProviderKey)}"
											title={row.primaryReason?.rule}
										>
											★ {providerLabel(row.preferredProvider as ProviderKey)}
										</span>
									{:else}
										<span class="text-[10px] text-fg-muted">—</span>
									{/if}
								</td>
							</tr>
						{/each}
					{/each}
				</tbody>
			</table>
		</div>

		<!-- 범례 -->
		<div class="mt-3 text-xs text-fg-muted">
			★ = 대표값으로 사용되는 Provider · ⚠ = 소스 간 5% 초과 불일치
		</div>
	{/if}
</div>
