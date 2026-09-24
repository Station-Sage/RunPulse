<script lang="ts">
	// C3 축소판 — 04-component-catalog.md 기준이나 실제 API 응답에 맞춰 축소.
	// children: 평평한 목록(재귀 없음), inputs: 드릴다운 가능(onDrillInput 콜백).
	import { getMetricBreakdown } from '$lib/api/metrics';
	import { providerLabel } from '$lib/provider';
	import type { MetricBreakdownData } from '$lib/types';

	let {
		slug,
		scopeType,
		scopeId,
		onClose,
		onDrillInput
	}: {
		slug: string;
		scopeType: string;
		scopeId: string;
		onClose: () => void;
		onDrillInput?: (slug: string) => void;
	} = $props();

	let data = $state<MetricBreakdownData | null>(null);
	let loading = $state(true);
	let error = $state<string | null>(null);

	$effect(() => {
		const s = slug, t = scopeType, i = scopeId;
		let cancelled = false;
		loading = true;
		error = null;
		data = null;
		getMetricBreakdown(s, t, i).then((d) => {
			if (!cancelled) data = d;
		}).catch((e) => {
			if (!cancelled) error = e instanceof Error ? e.message : '계산 데이터를 불러올 수 없습니다.';
		}).finally(() => {
			if (!cancelled) loading = false;
		});
		return () => { cancelled = true; };
	});
</script>

<div class="fixed inset-0 z-50 flex flex-col" role="dialog" aria-modal="true">
	<!-- 배경 오버레이 -->
	<button
		class="absolute inset-0 bg-black/40"
		onclick={onClose}
		aria-label="닫기"
	></button>

	<!-- 하단 시트 패널 -->
	<div class="absolute inset-x-0 bottom-0 flex max-h-[70vh] flex-col rounded-t-2xl bg-surface-1 shadow-lg">
		<!-- 헤더 -->
		<div class="flex items-center justify-between border-b border-border-subtle px-4 py-3">
			<h2 class="font-medium">
				{#if data}{data.label}{:else}{slug}{/if}
			</h2>
			<button
				onclick={onClose}
				class="rounded p-1 text-fg-secondary hover:text-fg-primary"
				aria-label="닫기"
			>✕</button>
		</div>

		<!-- 본문 -->
		<div class="overflow-y-auto p-4">
			{#if loading}
				<p class="text-sm text-fg-muted">불러오는 중…</p>
			{:else if error || !data}
				<p class="text-sm text-fg-secondary">계산 데이터를 불러올 수 없습니다.</p>
			{:else}
				<!-- 주값 -->
				<div class="mb-4 flex items-baseline gap-2">
					<span class="font-mono text-3xl font-bold">{data.value ?? '—'}</span>
					{#if data.unit}
						<span class="text-sm text-fg-muted">{data.unit}</span>
					{/if}
					{#if data.provider}
						<span class="text-xs text-fg-muted">{providerLabel(data.provider)}</span>
					{/if}
				</div>

				<!-- 구성 요소 (children — 평평한 목록) -->
				{#if data.children.length > 0}
					<div class="mb-4">
						<p class="mb-2 text-xs uppercase tracking-wide text-fg-muted">구성 요소</p>
						<div class="flex flex-col gap-1">
							{#each data.children as child (child.name)}
								<div class="flex items-center justify-between rounded-md bg-surface-2 px-3 py-2">
									<span class="text-sm">{child.label}</span>
									<span class="text-sm text-fg-secondary">
										{child.value ?? '—'}{#if child.unit}<span class="ml-0.5 text-xs text-fg-muted">{child.unit}</span>{/if}
									</span>
								</div>
							{/each}
						</div>
					</div>
				{/if}

				<!-- 입력 메트릭 (inputs — 드릴다운 가능) -->
				{#if data.inputs.length > 0}
					<div>
						<p class="mb-2 text-xs uppercase tracking-wide text-fg-muted">입력 메트릭</p>
						<div class="flex flex-col gap-1">
							{#each data.inputs as input (input.name)}
								<button
									class="flex w-full items-center justify-between rounded-md bg-surface-2 px-3 py-2 text-left {onDrillInput
										? 'cursor-pointer hover:bg-surface-3'
										: 'cursor-default'}"
									onclick={() => onDrillInput?.(input.name)}
									disabled={!onDrillInput}
								>
									<span class="text-sm">{input.label}</span>
									<span class="flex items-center gap-1 text-sm text-fg-secondary">
										{input.value ?? '—'}{#if input.unit}<span class="ml-0.5 text-xs text-fg-muted">{input.unit}</span>{/if}
										{#if onDrillInput}<span class="ml-1 text-fg-muted">›</span>{/if}
									</span>
								</button>
							{/each}
						</div>
					</div>
				{/if}
			{/if}
		</div>
	</div>
</div>
