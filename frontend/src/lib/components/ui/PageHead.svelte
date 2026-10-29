<script lang="ts">
	// 문서 title + 보이는 h1 을 한곳에서 출력한다. h1 을 다른 컴포넌트가 그리면 heading={null}.
	import { pageTitle } from '$lib/a11y/pageTitle';

	let {
		title,
		heading,
		headingHidden = false,
		class: cls = 'text-lg font-semibold text-fg-primary'
	}: {
		title: string;
		heading?: string | null;
		headingHidden?: boolean;
		class?: string;
	} = $props();

	const text = $derived(heading === undefined ? title : heading);
</script>

<svelte:head><title>{pageTitle(title)}</title></svelte:head>
{#if text}
	<h1 class={headingHidden ? 'sr-only' : cls}>{text}</h1>
{/if}
