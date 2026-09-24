<script lang="ts">
	// Coach 어시스턴트 답변 마크다운 렌더러 — {@html} 금지, Svelte 텍스트 노드 전용.
	import { parseMarkdown } from '$lib/markdownLite';

	let { content }: { content: string } = $props();

	const tokens = $derived(parseMarkdown(content));
</script>

<div class="flex flex-col gap-0.5">
	{#each tokens as token}
		{#if token.type === 'heading'}
			<p class="font-semibold{token.level === 1 ? ' text-sm' : ''} leading-snug">
				{#each token.spans as span}{#if span.type === 'bold'}<strong>{span.text}</strong>{:else}{span.text}{/if}{/each}
			</p>
		{:else if token.type === 'list_item'}
			<p class="flex gap-1 leading-snug">
				<span class="shrink-0 text-fg-muted">·</span><span
					>{#each token.spans as span}{#if span.type === 'bold'}<strong>{span.text}</strong>{:else}{span.text}{/if}{/each}</span
				>
			</p>
		{:else if token.type === 'paragraph'}
			<p class="leading-snug">
				{#each token.spans as span}{#if span.type === 'bold'}<strong>{span.text}</strong>{:else}{span.text}{/if}{/each}
			</p>
		{/if}
	{/each}
</div>
