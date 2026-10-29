<script lang="ts">
	// 토글 칩 — single 은 radio(aria-checked), multi 는 aria-pressed. 선택은 배경이 아닌 테두리·반전으로 표시한다(A11Y-14).
	import type { Snippet } from 'svelte';

	let {
		mode,
		selected,
		disabled = false,
		tabindex,
		onclick,
		onkeydown,
		el = $bindable(),
		children
	}: {
		mode: 'single' | 'multi';
		selected: boolean;
		disabled?: boolean;
		tabindex?: number;
		onclick?: () => void;
		onkeydown?: (e: KeyboardEvent) => void;
		el?: HTMLButtonElement;
		children: Snippet;
	} = $props();

	const look = $derived(
		selected
			? mode === 'single'
				? 'border-fg-primary bg-fg-primary text-surface-1'
				: 'border-2 border-fg-primary bg-surface-2 text-fg-primary'
			: 'border-border-strong text-fg-secondary hover:bg-surface-3'
	);
</script>

<button
	bind:this={el}
	type="button"
	role={mode === 'single' ? 'radio' : undefined}
	aria-checked={mode === 'single' ? selected : undefined}
	aria-pressed={mode === 'multi' ? selected : undefined}
	{disabled}
	{tabindex}
	{onclick}
	{onkeydown}
	class="tap inline-flex items-center justify-center rounded-lg border px-3 text-sm disabled:opacity-50 {look}"
>
	{@render children()}
</button>
