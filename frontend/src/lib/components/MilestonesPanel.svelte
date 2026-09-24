<script lang="ts">
	// 03a-today.md 1-D — Today "전체 마일스톤" 우측/하단 시트 패널.
	// MonthNarrative.svelte과 동일한 fixed inset-0 오버레이 + 하단 시트 패턴.
	import { onMount } from 'svelte';
	import { getTodayMilestones } from '$lib/api/today';
	import { base } from '$app/paths';
	import type { MilestoneEntry } from '$lib/types';

	let { onClose }: { onClose: () => void } = $props();

	let milestones = $state<MilestoneEntry[]>([]);
	let loading = $state(true);
	let error = $state<string | null>(null);

	const milestoneIcon: Record<string, string> = {
		distance_threshold: '🎯',
		pb: '🏃',
		metric_recompute: '🔄'
	};

	onMount(async () => {
		try {
			milestones = await getTodayMilestones(50);
		} catch (e) {
			error = e instanceof Error ? e.message : '마일스톤을 불러올 수 없습니다.';
		} finally {
			loading = false;
		}
	});
</script>

{#snippet row(m: MilestoneEntry)}
	<span aria-hidden="true" class="shrink-0">{milestoneIcon[m.type] ?? '🔖'}</span>
	<div class="min-w-0 flex-1">
		<div class="flex items-baseline gap-2 text-sm">
			<span class="shrink-0 text-fg-muted">{m.date}</span>
			<span class="flex-1">{m.title}</span>
		</div>
		{#if m.detail}
			<p class="text-xs text-fg-muted">{m.detail}</p>
		{/if}
	</div>
	{#if m.activity_id != null}
		<span class="shrink-0 text-fg-muted">›</span>
	{/if}
{/snippet}

<div class="fixed inset-0 z-50 flex flex-col" role="dialog" aria-modal="true">
	<!-- 배경 오버레이 -->
	<button class="absolute inset-0 bg-black/40" onclick={onClose} aria-label="닫기"></button>

	<!-- 하단 시트 패널 -->
	<div class="absolute inset-x-0 bottom-0 flex max-h-[80vh] flex-col rounded-t-2xl bg-surface-1 shadow-lg">
		<!-- 헤더 -->
		<div class="flex items-center justify-between border-b border-border-subtle px-4 py-3">
			<h2 class="font-medium">전체 마일스톤</h2>
			<button
				onclick={onClose}
				class="rounded p-1 text-fg-secondary hover:text-fg-primary"
				aria-label="닫기"
			>✕</button>
		</div>

		<!-- 본문 -->
		<div class="flex flex-col gap-3 overflow-y-auto p-4">
			{#if loading}
				<p class="text-sm text-fg-muted">불러오는 중…</p>
			{:else if error}
				<p class="text-sm text-fg-secondary">마일스톤을 불러올 수 없습니다.</p>
			{:else if milestones.length === 0}
				<p class="text-sm text-fg-muted">아직 마일스톤이 없습니다.</p>
			{:else}
				{#each milestones as m (m.id)}
					{#if m.activity_id != null}
						<a
							href="{base}/library/{m.activity_id}"
							class="flex items-start gap-2 rounded-lg py-1.5 hover:bg-surface-2"
						>{@render row(m)}</a>
					{:else}
						<div class="flex items-start gap-2 py-1.5">{@render row(m)}</div>
					{/if}
				{/each}
			{/if}
		</div>
	</div>
</div>
