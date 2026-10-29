<script lang="ts">
	// 이름 있는 입력 — label 필수, labelHidden 이면 sr-only. placeholder 는 보조로만 쓴다.
	import type { HTMLInputAttributes } from 'svelte/elements';

	let {
		label,
		labelHidden = false,
		value = $bindable(''),
		multiline = false,
		rows = 3,
		id,
		class: cls = '',
		...rest
	}: {
		label: string;
		labelHidden?: boolean;
		value?: string;
		multiline?: boolean;
		rows?: number;
		id?: string;
		class?: string;
	} & Omit<HTMLInputAttributes, 'value' | 'class' | 'id'> = $props();

	const uid = $props.id();
	const fid = $derived(id ?? `tf-${uid}`);
</script>

<label for={fid} class={labelHidden ? 'sr-only' : 'mb-1 block text-xs text-fg-secondary'}>{label}</label>
{#if multiline}
	<textarea id={fid} {rows} bind:value class="min-h-11 {cls}" {...rest as object}></textarea>
{:else}
	<input id={fid} bind:value class="min-h-11 {cls}" {...rest} />
{/if}
