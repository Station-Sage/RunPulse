<script lang="ts">
	// 쓸 수 없는 주소 값 안내(M-20·M-25, E-27 과 같은 처리) — 한 줄을 보이고 그 키를 주소에서 지운다(히스토리는 교체).
	import { onMount } from 'svelte';
	import { replaceState } from '$app/navigation';
	import { page } from '$app/state';
	import { cleanedSearch } from '$lib/metricDetail';

	let { text, dropKeys }: { text: string; dropKeys: string[] } = $props();

	onMount(() => {
		if (!text || !dropKeys.length) return;
		const u = new URL(page.url);
		u.search = cleanedSearch(u.search, dropKeys);
		replaceState(u, page.state);
	});
</script>

{#if text}
	<p class="mx-4 mt-3 rounded-lg bg-surface-3 px-3 py-2 text-xs text-fg-secondary" data-testid="param-notice">{text}</p>
{/if}
