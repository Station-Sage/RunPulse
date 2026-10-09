<script lang="ts">
	import type { RawInputs } from '$lib/replanView';

	let {
		values = $bindable(),
		errors,
		warnings,
		oninput
	}: {
		values: RawInputs;
		errors: Partial<Record<keyof RawInputs, string>>;
		warnings: string[];
		oninput: () => void;
	} = $props();

	const fields: { key: keyof RawInputs; label: string; ph: string; mode: 'decimal' | 'text' }[] = [
		{ key: 'weekly', label: '최근 주간 거리 (km)', ph: '예: 38', mode: 'decimal' },
		{ key: 'long', label: '최근 가장 긴 러닝 (km)', ph: '예: 18', mode: 'decimal' },
		{ key: 'target', label: '목표 기록', ph: '예: 3:45:00', mode: 'text' }
	];
</script>

<details class="rounded-lg bg-surface-2 p-3 text-xs text-fg-secondary">
	<summary class="min-h-11 cursor-pointer py-3">직접 입력</summary>
	<div class="space-y-3 pb-1">
		{#each fields as f (f.key)}
			<label class="block">
				<span class="mb-1 block">{f.label}</span>
				<input
					class="h-11 w-full rounded-lg border border-border bg-surface-1 px-3 text-sm text-fg-primary"
					inputmode={f.mode}
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
