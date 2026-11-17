<script lang="ts">
	// 공용 버튼 — variant 로 모양을 고정하고 44px 타깃을 보장한다. href 가 있으면 링크로 그린다.
	import type { Snippet } from 'svelte';
	import { buttonClass, type ButtonVariant } from '$lib/buttonStyle';

	let {
		variant = 'secondary',
		href,
		type = 'button',
		disabled = false,
		busy = false,
		full = false,
		onclick,
		class: cls = '',
		children,
		...rest
	}: {
		variant?: ButtonVariant;
		href?: string;
		type?: 'button' | 'submit';
		disabled?: boolean;
		busy?: boolean;
		full?: boolean;
		onclick?: (e: MouseEvent) => void;
		class?: string;
		children: Snippet;
		[k: string]: unknown;
	} = $props();

	const klass = $derived(`${buttonClass(variant, full)} ${cls}`.trim());
</script>

{#if href && !disabled}
	<a {href} class={klass} {onclick} {...rest}>{@render children()}</a>
{:else}
	<button {type} disabled={disabled || busy} aria-busy={busy || undefined} class={klass} {onclick} {...rest}>{@render children()}</button>
{/if}
