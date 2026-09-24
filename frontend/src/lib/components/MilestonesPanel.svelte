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
			const res = await getTodayMilestones(50);
			milestones = res.milestones;
		} catch (e) {
			error = e instanceof Error ? e.message : '마일스톤을 불러올 수 없습니다.';
		} finally {
			loading = false;
		}
	});
</script>

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
		<div class="overflow-y-auto p-4 flex flex-col gap-2">
			{#if loading}
				<p class="text-sm text-fg-muted">불러오는 중…</p>
			{:else if error}
				<p class="text-sm text-fg-secondary">{error}</p>
			{:else if milestones.length === 0}
				<p class="text-sm text-fg-muted">마일스톤이 없습니다.</p>
			{:else}
				{#each milestones as m (m.id)}
					<div class="flex items-start gap-2 py-1.5 text-sm">
						<span aria-hidden="true" class="shrink-0">{milestoneIcon[m.type] ?? '🔖'}</span>
						<span class="shrink-0 text-fg-muted">{m.date}</span>
						<span class="flex-1">{m.title}</span>
						{#if m.type === 'pb' && m.activity_id != null}
							<a
								href="{base}/library/{m.activity_id}"
								class="shrink-0 text-fg-secondary hover:text-fg-primary"
							>→</a>
						{:else if m.type === 'metric_recompute' && m.detail}
							<span class="shrink-0 text-xs text-fg-muted">{m.detail}</span>
						{/if}
					</div>
				{/each}
			{/if}
		</div>
	</div>
</div>
