<script lang="ts">
	// 03c-library.md 3-C 랩 탭 — activity_laps 고정 열 표(LapTable, 인터벌 그룹 뷰).
	import type { LapsPageData } from './+page';
	import { providerLabel, providerBadgeClass } from '$lib/provider';
	import { formatPace } from '$lib/format';
	import { lapPace } from '$lib/lapGroups';
	import LapTable from '$lib/components/LapTable.svelte';
	import { base } from '$app/paths';
	import type { ProviderKey } from '$lib/types';

	let { data }: { data: LapsPageData } = $props();

	const fastest = $derived(Math.min(...data.laps.map(lapPace).filter((p): p is number => p != null)));
	const source = $derived(data.laps.length > 0 ? data.laps[0].source : null);
</script>

<svelte:head><title>랩 · RunPulse</title></svelte:head>

{#if data.errorMessage && data.laps.length === 0}
	<div class="px-4 py-8 text-center">
		<p class="text-sm text-fg-secondary">{data.errorMessage}</p>
		<a href="{base}/library/{data.activityId}" class="mt-2 block text-xs text-fg-muted underline">← 활동으로 돌아가기</a>
	</div>
{:else if data.laps.length === 0}
	<div class="px-4 py-8 text-center">
		<p class="text-sm text-fg-muted">랩 데이터 없음</p>
		<a href="{base}/library/{data.activityId}" class="mt-2 block text-xs text-fg-muted underline">← 활동으로 돌아가기</a>
	</div>
{:else}
	<div class="flex flex-col gap-3 px-4 py-4">
		<div class="flex items-center gap-2 text-xs text-fg-muted">
			{#if source}
				<span class="rounded px-1.5 py-0.5 text-[10px] text-white {providerBadgeClass(source as ProviderKey)}">{providerLabel(source as ProviderKey)}</span>
			{/if}
			<span>{data.laps.length}개 랩{#if Number.isFinite(fastest)}{' · '}가장 빠른 랩 {formatPace(fastest)}{/if}</span>
		</div>
		<LapTable laps={data.laps} />
	</div>
{/if}
