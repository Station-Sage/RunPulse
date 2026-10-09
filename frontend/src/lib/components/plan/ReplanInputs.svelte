<script lang="ts">
	import type { RawInputs } from '$lib/replanView';

	let {
		values = $bindable(),
		errors,
		warnings,
		fields,
		oninput
	}: {
		values: RawInputs;
		errors: Partial<Record<keyof RawInputs, string>>;
		warnings: string[];
		fields: { weekly: boolean; long: boolean; open: boolean };
		oninput: () => void;
	} = $props();

	const all: { key: 'weekly' | 'long'; label: string; ph: string }[] = [
		{ key: 'weekly', label: '최근 주간 거리 (km)', ph: '예: 38' },
		{ key: 'long', label: '최근 가장 긴 러닝 (km)', ph: '예: 18' }
	];
	const shown = $derived(all.filter((f) => fields[f.key]));
</script>

{#if shown.length}
	<details open={fields.open} class="rounded-lg bg-surface-2 p-3 text-xs text-fg-secondary">
		<summary class="min-h-11 cursor-pointer py-3">직접 맞추기</summary>
		<div class="space-y-3 pb-1">
			{#each shown as f (f.key)}
				<label class="block">
					<span class="mb-1 block">{f.label}</span>
					<input
						class="h-11 w-full rounded-lg border border-border bg-surface-1 px-3 text-sm text-fg-primary"
						inputmode="decimal"
						placeholder={f.ph}
						bind:value={values[f.key]}
						oninput={oninput}
					/>
					{#if errors[f.key]}<span class="mt-1 block text-semantic-red">{errors[f.key]}</span>{/if}
				</label>
			{/each}
			{#each warnings as w}<p>{w}</p>{/each}
		</div>
	</details>
{/if}
