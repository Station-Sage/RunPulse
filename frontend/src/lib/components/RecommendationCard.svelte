<script lang="ts">
	// C6 — 04-component-catalog.md. AI 권고 + 근거 칩 집합 + 액션.
	// body는 이번 1차엔 평문(줄바꿈만 보존)으로 렌더링한다 — 마크다운 서브셋 파싱은
	// TimelineNarrative(C7, 7b 몫)에서 같이 붙이는 게 낫다고 판단해 미룸.
	import type { RecommendationCardProps } from '$lib/types';
	import EvidenceQuote from './EvidenceQuote.svelte';

	let { recommendation, actions = [], variant = 'default', loading = false }: RecommendationCardProps =
		$props();

	const variantClass = $derived(
		{
			default: 'border-border-subtle',
			warning: 'border-semantic-amber bg-semantic-amber/5',
			positive: 'border-semantic-green bg-semantic-green/5'
		}[variant]
	);
</script>

<div class="flex flex-col gap-3 rounded-lg border-l-4 bg-surface-2 p-4 {variantClass}">
	{#if loading}
		<div class="h-4 w-3/4 animate-pulse rounded bg-surface-3"></div>
		<div class="h-4 w-full animate-pulse rounded bg-surface-3"></div>
		<div class="h-4 w-2/3 animate-pulse rounded bg-surface-3"></div>
		<div class="flex gap-2">
			<div class="h-6 w-20 animate-pulse rounded-full bg-surface-3"></div>
			<div class="h-6 w-20 animate-pulse rounded-full bg-surface-3"></div>
		</div>
	{:else}
		{#if recommendation.title}
			<p class="font-medium text-fg-primary">{recommendation.title}</p>
		{/if}
		<p class="whitespace-pre-wrap text-fg-primary">{recommendation.body}</p>

		{#if recommendation.evidence.length > 0}
			<div class="flex flex-wrap gap-1.5">
				{#each recommendation.evidence as ev, i (i)}
					<EvidenceQuote {...ev} />
				{/each}
			</div>
		{/if}

		{#if actions.length > 0}
			<div class="flex justify-end gap-2">
				{#each actions as action, i (i)}
					{#if action.href}
						<a
							href={action.href}
							class="rounded px-3 py-1.5 text-sm {action.variant === 'primary'
								? 'bg-semantic-teal text-white'
								: 'text-fg-secondary hover:text-fg-primary'}"
						>
							{action.label}
						</a>
					{:else}
						<button
							type="button"
							onclick={action.onClick}
							class="rounded px-3 py-1.5 text-sm {action.variant === 'primary'
								? 'bg-semantic-teal text-white'
								: 'text-fg-secondary hover:text-fg-primary'}"
						>
							{action.label}
						</button>
					{/if}
				{/each}
			</div>
		{/if}
	{/if}
</div>
