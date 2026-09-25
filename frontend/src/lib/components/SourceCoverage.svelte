<script lang="ts">
	import { coverageLevels, coverageNote } from '$lib/coverage';
	import { providerLabel, providerBadgeClass } from '$lib/provider';
	import { providerHint } from '$lib/providerHint';
	import type { ProviderCoverage, ProviderStatusItem, ProviderKey } from '$lib/types';

	const LEVEL_COLOR = ['#1f2937', '#0f766e', '#14b8a6', '#5eead4'] as const;

	let { coverage, status }: { coverage: ProviderCoverage; status: ProviderStatusItem[] } = $props();

	function statusFor(provider: string): ProviderStatusItem | undefined {
		return status.find((s) => s.provider === provider);
	}
</script>

<div class="flex flex-col gap-4">
	{#each coverage.providers as item (item.provider)}
		{@const levels = coverageLevels(item.counts)}
		{@const note = coverageNote(item.counts)}
		{@const statusItem = statusFor(item.provider)}
		{@const hint = statusItem ? providerHint(statusItem, Date.now()) : null}
		<div class="flex flex-col gap-1">
			<!-- 헤더 -->
			<div class="flex items-center gap-2">
				<span
					class="shrink-0 rounded px-1.5 py-0.5 text-[10px] text-white {providerBadgeClass(
						item.provider as ProviderKey
					)}"
				>
					{providerLabel(item.provider as ProviderKey)}
				</span>
				<span class="ml-auto text-xs text-fg-muted">활동 {item.total}건</span>
			</div>

			{#if item.total === 0}
				<p class="text-xs text-fg-muted">연동 없음 또는 아직 가져온 활동이 없어요.</p>
			{:else}
				<!-- 월 셀 띠 -->
				<div
					class="flex h-3 gap-px"
					role="img"
					aria-label="{providerLabel(item.provider as ProviderKey)} 월별 활동 커버리지"
				>
					{#each coverage.months as month, i}
						<div
							class="flex-1 rounded-[2px]"
							style="background:{LEVEL_COLOR[levels[i]]}"
							title="{month} · {item.counts[i]}건"
						></div>
					{/each}
				</div>

				<!-- 띠 양끝 라벨 -->
				<div class="flex justify-between">
					<span class="font-mono text-[10px] text-fg-muted">{coverage.months[0]}</span>
					<span class="font-mono text-[10px] text-fg-muted"
						>{coverage.months[coverage.months.length - 1]}</span
					>
				</div>

				<!-- 안내 문구 -->
				{#if note}
					<p class="text-[11px] text-semantic-amber">{note}</p>
				{:else if hint}
					<p class="text-[11px] text-semantic-amber">{hint}</p>
				{/if}
			{/if}
		</div>
	{/each}
</div>
