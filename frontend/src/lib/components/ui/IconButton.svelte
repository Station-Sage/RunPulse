<script lang="ts">
	// 아이콘 전용 버튼 — 이름(label)이 필수이고 44px 타깃(.tap)을 보장한다.
	import type { Snippet } from 'svelte';

	let {
		label,
		onclick,
		type = 'button',
		disabled = false,
		class: cls = '',
		children
	}: {
		label: string;
		onclick?: (e: MouseEvent) => void;
		type?: 'button' | 'submit';
		disabled?: boolean;
		class?: string;
		children: Snippet;
	} = $props();
</script>

<button {type} {disabled} aria-label={label} {onclick} class="tap inline-flex items-center justify-center {cls}">
	{@render children()}
</button>
