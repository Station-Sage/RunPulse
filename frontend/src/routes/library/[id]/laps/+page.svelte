<script lang="ts">
	import PageHead from '$lib/components/ui/PageHead.svelte';
	// 03c-library.md 3-C 랩 탭 — activity_laps 고정 열 표(LapTable, 인터벌 그룹 뷰).
	import type { LapsPageData } from './+page';
	import { providerLabel, providerBadgeClass } from '$lib/provider';
	import { formatPace } from '$lib/format';
	import { fastestLap, lapPaceBasisDiffers } from '$lib/lapGroups';
	import { emptyDataNote } from '$lib/activityDetailView';

	import LapTable from '$lib/components/LapTable.svelte';
	import { base } from '$app/paths';
	import type { ProviderKey } from '$lib/types';
	import LoadFailure from '$lib/components/LoadFailure.svelte';

	let { data }: { data: LapsPageData } = $props();

	const fastest = $derived(fastestLap(data.laps));
	const basisNote = $derived(lapPaceBasisDiffers(data.laps));
	const note = $derived(emptyDataNote('laps', data.activity));
	const source = $derived(data.laps.length > 0 ? data.laps[0].source : null);
</script>

<PageHead title="랩" heading={null} />

{#if data.failure && data.laps.length === 0}
	<LoadFailure failure={data.failure} retryKey={`app:activity:${data.activityId}`} backHref="{base}/library/{data.activityId}" backLabel="← 활동으로 돌아가기" notFoundText="활동을 찾을 수 없어요" />
{:else if data.laps.length === 0}
	<div class="px-4 py-8 text-center">
		<p class="text-sm text-fg-muted">랩 데이터 없음</p>
		<p class="mt-1 text-xs text-fg-muted" data-testid="empty-reason">{note.reason}</p>
		{#if note.action}<a href="{base}{note.action.path}" class="mt-2 inline-block text-xs text-fg-secondary underline">{note.action.label}</a>{/if}
		<a href="{base}/library/{data.activityId}" class="mt-2 block text-xs text-fg-muted underline">← 활동으로 돌아가기</a>
	</div>
{:else}
	<div class="flex flex-col gap-3 px-4 py-4">
		<div class="flex items-center gap-2 text-xs text-fg-muted">
			{#if source}
				<span class="rounded px-1.5 py-0.5 text-[10px] {providerBadgeClass(source as ProviderKey)}">{providerLabel(source as ProviderKey)}</span>
			{/if}
			<span>{data.laps.length}개 랩{#if fastest}{' · '}가장 빠른 랩 {formatPace(fastest.pace)} (#{fastest.index + 1}){/if}</span>
		</div>
		<LapTable laps={data.laps} />
		{#if basisNote}<p class="text-xs text-fg-muted" data-testid="lap-basis-note">시간은 랩 전체 시간, 페이스는 이동 시간 기준이라 1~2초 다를 수 있어요.</p>{/if}
	</div>
{/if}
