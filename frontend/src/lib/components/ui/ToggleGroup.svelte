<script lang="ts">
	// 토글 그룹 — single=radiogroup(화살표 키 roving), multi=group+aria-pressed. label 필수.
	import ToggleChip from './ToggleChip.svelte';
	import { nextIndex } from '$lib/a11y/rovingIndex';

	type Item = { value: string; label: string; disabled?: boolean };

	let {
		label,
		items,
		mode = 'single',
		selected = $bindable(mode === 'single' ? null : []),
		onchange,
		class: cls = 'flex flex-wrap gap-2'
	}: {
		label: string;
		items: Item[];
		mode?: 'single' | 'multi';
		selected?: string | string[] | null;
		onchange?: (v: string | string[] | null) => void;
		class?: string;
	} = $props();

	const uid = $props.id();
	let els: (HTMLButtonElement | undefined)[] = $state([]);

	const isOn = (v: string) =>
		mode === 'single' ? selected === v : Array.isArray(selected) && selected.includes(v);
	const activeIdx = $derived.by(() => {
		const i = items.findIndex((it) => isOn(it.value) && !it.disabled);
		return i >= 0 ? i : items.findIndex((it) => !it.disabled);
	});

	function pick(v: string) {
		if (mode === 'single') selected = v;
		else {
			const cur = Array.isArray(selected) ? selected : [];
			selected = cur.includes(v) ? cur.filter((x) => x !== v) : [...cur, v];
		}
		onchange?.(selected);
	}

	function key(e: KeyboardEvent, i: number) {
		if (mode !== 'single') return;
		const to = nextIndex(i, e.key, items.length, items.map((it) => !!it.disabled));
		if (to === i) return;
		e.preventDefault();
		els[to]?.focus();
		pick(items[to].value);
	}
</script>

<div
	role={mode === 'single' ? 'radiogroup' : 'group'}
	aria-labelledby="tg-{uid}"
	class={cls}
>
	<span id="tg-{uid}" class="sr-only">{label}</span>
	{#each items as it, i (it.value)}
		<ToggleChip
			{mode}
			selected={isOn(it.value)}
			disabled={it.disabled}
			tabindex={mode === 'single' ? (i === activeIdx ? 0 : -1) : undefined}
			bind:el={els[i]}
			onclick={() => pick(it.value)}
			onkeydown={(e) => key(e, i)}
		>
			{it.label}
		</ToggleChip>
	{/each}
</div>
