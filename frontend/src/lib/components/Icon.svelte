<script lang="ts">
	// SVG 아이콘 세트 — 탭바 3종(today/library/coach). 이모지 대신 인라인 SVG(E5).
	let {
		name,
		class: className = ''
	}: {
		name: 'today' | 'library' | 'coach';
		class?: string;
	} = $props();
</script>

<svg
	viewBox="0 0 24 24"
	fill="none"
	stroke="currentColor"
	stroke-width="1.8"
	stroke-linecap="round"
	stroke-linejoin="round"
	class="h-5 w-5 {className}"
	aria-hidden="true"
>
	{#if name === 'today'}
		<circle cx="12" cy="12" r="4" />
		<path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" />
	{:else if name === 'library'}
		<rect x="3" y="4" width="7" height="7" rx="1" />
		<rect x="14" y="4" width="7" height="7" rx="1" />
		<rect x="3" y="15" width="7" height="5" rx="1" />
		<rect x="14" y="15" width="7" height="5" rx="1" />
	{:else if name === 'coach'}
		<path d="M21 12a8 8 0 0 1-11.6 7.1L4 20l1-4.4A8 8 0 1 1 21 12z" />
	{/if}
</svg>
