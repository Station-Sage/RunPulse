<script lang="ts">
	// SVG 아이콘 세트 — §C8(ux-review-2026-09/10-today/design.md). 이모지·문자 아이콘 금지.
	// source-primary(★)는 D1e — 대표 소스 배지 전용.
	import type { IconName } from '$lib/icon';

	let {
		name,
		class: className = ''
	}: {
		name: IconName;
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
		<path
			d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"
		/>
	{:else if name === 'library'}
		<rect x="3" y="4" width="7" height="7" rx="1" />
		<rect x="14" y="4" width="7" height="7" rx="1" />
		<rect x="3" y="15" width="7" height="5" rx="1" />
		<rect x="14" y="15" width="7" height="5" rx="1" />
	{:else if name === 'coach'}
		<path d="M21 12a8 8 0 0 1-11.6 7.1L4 20l1-4.4A8 8 0 1 1 21 12z" />
	{:else if name === 'metric'}
		<path d="M4 20V10M12 20V4M20 20v-6" />
	{:else if name === 'activity'}
		<path d="M3 12h4l2-7 4 14 2-7h6" />
	{:else if name === 'note'}
		<path d="M6 3h9l5 5v13a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1z" />
		<path d="M14 3v5h5M8 13h8M8 17h5" />
	{:else if name === 'target'}
		<circle cx="12" cy="12" r="8" />
		<circle cx="12" cy="12" r="4" />
		<circle cx="12" cy="12" r="0.5" fill="currentColor" />
	{:else if name === 'trophy'}
		<path
			d="M8 4h8v4a4 4 0 0 1-8 0V4z"
		/>
		<path d="M8 5H5a3 3 0 0 0 3 4M16 5h3a3 3 0 0 1-3 4" />
		<path d="M12 12v3M9 20h6M10 17h4v3h-4z" />
	{:else if name === 'refresh'}
		<path d="M3 12a9 9 0 0 1 15.3-6.4L21 8M21 3v5h-5" />
		<path d="M21 12a9 9 0 0 1-15.3 6.4L3 16M3 21v-5h5" />
	{:else if name === 'warning'}
		<path d="M12 3 2 20h20L12 3z" />
		<path d="M12 10v4M12 17.5v.01" />
	{:else if name === 'close'}
		<path d="M6 6l12 12M18 6L6 18" />
	{:else if name === 'menu'}
		<path d="M4 6h16M4 12h16M4 18h16" />
	{:else if name === 'chevron'}
		<path d="M9 6l6 6-6 6" />
	{:else if name === 'check'}
		<path d="M5 13l4 4L19 7" />
	{:else if name === 'arrow-up'}
		<path d="M12 19V5M6 11l6-6 6 6" />
	{:else if name === 'arrow-down'}
		<path d="M12 5v14M18 13l-6 6-6-6" />
	{:else if name === 'more'}
		<circle cx="5" cy="12" r="1" fill="currentColor" />
		<circle cx="12" cy="12" r="1" fill="currentColor" />
		<circle cx="19" cy="12" r="1" fill="currentColor" />
	{:else if name === 'info'}
		<circle cx="12" cy="12" r="9" />
		<path d="M12 11v5.5M12 7.5v.01" />
	{:else if name === 'search'}
		<circle cx="11" cy="11" r="7" />
		<path d="M21 21l-4.35-4.35" />
	{:else if name === 'source-primary'}
		<path
			d="M12 3l2.6 5.6 6.1.6-4.6 4.1 1.3 6-5.4-3.1-5.4 3.1 1.3-6-4.6-4.1 6.1-.6L12 3z"
			fill="currentColor"
			stroke="none"
		/>
	{/if}
</svg>
