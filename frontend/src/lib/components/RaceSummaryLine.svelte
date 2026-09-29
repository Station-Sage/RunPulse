<script lang="ts">
	// B4 레이스 한 줄 — `D-56 · 예측 3:40 (모델 범위 3:26–4:03) · 목표 3:19 ›` → 레이스 허브.
	// 10-today design §2.6: 목표 없음은 등록 유도, 조회 실패는 재시도(값 없음과 실패 분리).
	import type { RaceSummary } from '$lib/types';
	import { raceSummaryParts } from '$lib/raceHub';
	import { base } from '$app/paths';

	let { summary, onRetry }: { summary: RaceSummary | null | undefined; onRetry?: () => void } = $props();

	const parts = $derived(summary ? raceSummaryParts(summary) : []);
	const cls = 'flex items-center justify-between gap-2 rounded-lg border border-border-subtle bg-surface-2 px-3 py-2 text-sm';
</script>

{#if summary === undefined}
	<div class={cls} role="alert">
		<span class="text-fg-secondary">예측을 불러오지 못했어요</span>
		{#if onRetry}
			<button type="button" class="text-fg-primary underline underline-offset-2" onclick={onRetry}>다시 시도</button>
		{/if}
	</div>
{:else if summary === null}
	<a href="{base}/coach/plan/new" class="{cls} text-fg-secondary hover:bg-surface-3">
		<span>목표 레이스 등록</span><span aria-hidden="true">›</span>
	</a>
{:else}
	<a href="{base}/today/race" class="{cls} hover:bg-surface-3" aria-label="레이스 허브 열기">
		<span class="flex flex-wrap gap-x-2 tabular-nums text-fg-primary">
			{#each parts as p, i (i)}
				{#if i > 0}<span class="text-fg-muted" aria-hidden="true">·</span>{/if}
				<span class={i === 0 ? 'font-semibold' : ''}>{p}</span>
			{/each}
		</span>
		<span class="text-fg-muted" aria-hidden="true">›</span>
	</a>
{/if}
